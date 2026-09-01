"""ROBoy Emotion V2 - Phase 7 Behavior Execution Engine.

Provides a deterministic, non-blocking, timeline/sequence execution layer
on top of the frozen V2 BehaviorChoreographer.

Architecture:
    BehaviorEngine (behavior_engine.py - Phase 7 Orchestrator)
          | (Action scheduling, timeline queue, residual dt cascade)
          v
    BehaviorChoreographer (choreography.py - Frozen Phase 6 Coordinator)
          | (Layered composition, eligibility rules, sub-controllers)
          v
    TransitionController | LookController | BlinkController (Frozen Phases 1-5)
          | (Live pose & composed FaceSpec)
          v
    V2 Renderer (renderer.py - Frozen Renderer)

Key Principles:
1. Orchestrator Only:
   - BehaviorEngine decides WHAT action happens, WHEN it starts, and WHEN it completes.
   - It never calculates facial geometry, Bezier curves, gaze offsets, or blink weights.
2. Pure Determinism:
   - Driven entirely by update(dt). No threads, no asyncio, no sleep, no system clocks.
3. Exact Residual Time (dt) Cascading:
   - Overshoot in an action's completion boundary is never discarded; residual time
     immediately advances subsequent queued actions in the exact same update tick.
4. Seamless Interruption:
   - Interrupting an active sequence preserves the live interpolated face pose
     without snapping or resetting.
5. Idle Stillness:
   - When the queue is empty and no action is active, the engine remains completely still.
"""

from __future__ import annotations

import collections
from enum import Enum
import math
from typing import Callable, Deque, Dict, List, Optional, Sequence, Tuple, Union

import config as cfg
import emotions as em
import face as fc
from blink_controller import BlinkType, BlinkState, BlinkController
from look_controller import LookController, GAZE_DIRECTIONS
from choreography import BehaviorChoreographer


class ActionState(Enum):
    """Lifecycle states for an Action."""
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ===========================================================================
# Base Action Model
# ===========================================================================

class Action:
    """Base class for all discrete timeline actions."""

    def __init__(self, name: str = "", is_blocking: bool = True):
        self.name: str = name or self.__class__.__name__
        self.is_blocking: bool = is_blocking
        self.state: ActionState = ActionState.NOT_STARTED
        self.elapsed: float = 0.0
        self.total_duration: float = 0.0

    def start(self, choreographer: BehaviorChoreographer) -> None:
        """Initialize and trigger the action on the choreographer."""
        self.state = ActionState.ACTIVE
        self.elapsed = 0.0
        self._on_start(choreographer)

    def compute_step(self, residual_dt: float) -> float:
        """Calculate and accumulate the time step this action can consume from residual_dt."""
        if residual_dt <= 0.0:
            return 0.0
        time_needed = max(0.0, self.total_duration - self.elapsed)
        step_dt = min(residual_dt, time_needed)
        self.elapsed += step_dt
        return step_dt

    def is_complete(self, choreographer: BehaviorChoreographer) -> bool:
        """Check whether action has completed its timeline and underlying controller conditions."""
        return self.elapsed >= self.total_duration - 1e-7

    def finish(self) -> None:
        """Mark action as completed."""
        self.state = ActionState.COMPLETED

    def cancel(self, choreographer: BehaviorChoreographer) -> None:
        """Cancel an in-flight action without resetting facial pose."""
        if self.state == ActionState.ACTIVE:
            self.state = ActionState.CANCELLED
            self._on_cancel(choreographer)

    def get_progress(self) -> float:
        """Return execution progress in [0.0, 1.0]."""
        if self.total_duration <= 1e-7:
            return 1.0 if self.state == ActionState.COMPLETED else 0.0
        return min(1.0, max(0.0, self.elapsed / self.total_duration))

    # Subclass hooks
    def _on_start(self, choreographer: BehaviorChoreographer) -> None:
        pass

    def _on_cancel(self, choreographer: BehaviorChoreographer) -> None:
        pass


# ===========================================================================
# Concrete Action Implementations
# ===========================================================================

class WaitAction(Action):
    """Consumes deterministic timeline duration without issuing facial commands."""

    def __init__(self, duration: float, name: str = ""):
        if duration < 0.0:
            raise ValueError(f"WaitAction duration must be non-negative, got {duration}")
        super().__init__(name=name or f"Wait({duration:.2f}s)")
        self.duration: float = float(duration)
        self.total_duration = self.duration

    def _on_start(self, choreographer: BehaviorChoreographer) -> None:
        self.total_duration = self.duration


class EmotionAction(Action):
    """Requests a transition to a target emotion, with optional morph duration and hold time."""

    def __init__(
        self,
        emotion: str,
        duration: Optional[float] = None,
        hold_time: float = 0.0,
        name: str = "",
    ):
        if emotion not in em.EMOTION_ORDER:
            raise ValueError(f"Unknown emotion '{emotion}'. Valid emotions: {em.EMOTION_ORDER}")
        if duration is not None and duration < 0.0:
            raise ValueError(f"EmotionAction duration must be non-negative, got {duration}")
        if hold_time < 0.0:
            raise ValueError(f"EmotionAction hold_time must be non-negative, got {hold_time}")

        super().__init__(name=name or f"Emotion({emotion})")
        self.emotion: str = emotion
        self.duration: Optional[float] = float(duration) if duration is not None else None
        self.hold_time: float = float(hold_time)

        # Expected default duration if not specified
        default_dur = getattr(cfg, "TRANSITION_DURATION", 0.55)
        self._expected_morph_dur: float = self.duration if self.duration is not None else default_dur
        self.total_duration = self._expected_morph_dur + self.hold_time

    def _on_start(self, choreographer: BehaviorChoreographer) -> None:
        req_dur = max(0.0001, self.duration) if self.duration is not None else None

        # If already at target emotion and not transitioning, transition is instant (0 duration)
        if choreographer.current_emotion == self.emotion and not choreographer.is_transitioning:
            self._expected_morph_dur = 0.0
            self.total_duration = self.hold_time
            choreographer.request_emotion(self.emotion, duration=req_dur, reset_time=True)
        else:
            choreographer.request_emotion(self.emotion, duration=req_dur, reset_time=True)
            default_dur = getattr(cfg, "TRANSITION_DURATION", 0.55)
            self._expected_morph_dur = req_dur if req_dur is not None else default_dur
            self.total_duration = self._expected_morph_dur + self.hold_time

    def is_complete(self, choreographer: BehaviorChoreographer) -> bool:
        time_done = (self.elapsed >= self.total_duration - 1e-7)
        trans_done = (not choreographer.is_transitioning) or (choreographer.current_emotion == self.emotion)
        return time_done and trans_done


class GazeAction(Action):
    """Directs eye gaze toward a named direction or (x, y) target vector."""

    def __init__(
        self,
        direction: Optional[str] = None,
        target: Optional[Tuple[float, float]] = None,
        duration: Optional[float] = None,
        hold_time: float = 0.0,
        name: str = "",
    ):
        if direction is None and target is None:
            raise ValueError("GazeAction requires either 'direction' or 'target' to be specified.")

        if direction is not None:
            dir_lower = direction.lower()
            if dir_lower not in GAZE_DIRECTIONS:
                raise ValueError(
                    f"Unknown gaze direction '{direction}'. Available: {list(GAZE_DIRECTIONS.keys())}"
                )
            self.direction: Optional[str] = dir_lower
        else:
            self.direction = None

        if target is not None:
            if len(target) != 2:
                raise ValueError(f"Gaze target must be a (x, y) tuple, got {target}")
            tx = float(target[0])
            ty = float(target[1])
            if not (-1.0 <= tx <= 1.0 and -1.0 <= ty <= 1.0):
                raise ValueError(f"Gaze target coordinates must be in [-1.0, 1.0], got ({tx}, {ty})")
            self.target: Optional[Tuple[float, float]] = (tx, ty)
        else:
            self.target = None

        if duration is not None and duration < 0.0:
            raise ValueError(f"GazeAction duration must be non-negative, got {duration}")
        if hold_time < 0.0:
            raise ValueError(f"GazeAction hold_time must be non-negative, got {hold_time}")

        super().__init__(name=name or f"Gaze({self.direction or self.target})")
        self.duration: Optional[float] = float(duration) if duration is not None else None
        self.hold_time: float = float(hold_time)
        self._saccade_dur: float = self.duration if self.duration is not None else 0.18
        self.total_duration = self._saccade_dur + self.hold_time

    def _on_start(self, choreographer: BehaviorChoreographer) -> None:
        req_dur = max(0.0001, self.duration) if self.duration is not None else None
        if self.direction is not None:
            choreographer.look_direction(self.direction, duration=req_dur)
        elif self.target is not None:
            choreographer.look_at(self.target[0], self.target[1], duration=req_dur)

        # Query actual duration calculated by LookController (which scales by distance)
        self._saccade_dur = req_dur if req_dur is not None else choreographer.look_controller.duration
        self.total_duration = self._saccade_dur + self.hold_time

    def is_complete(self, choreographer: BehaviorChoreographer) -> bool:
        time_done = (self.elapsed >= self.total_duration - 1e-7)
        gaze_done = not choreographer.look_controller.is_moving
        return time_done and gaze_done


class BlinkAction(Action):
    """Triggers an eyelid blink of a specified BlinkType with optional duration multiplier."""

    def __init__(
        self,
        blink_type: Union[BlinkType, str] = BlinkType.NORMAL,
        duration_multiplier: float = 1.0,
        hold_time: float = 0.0,
        name: str = "",
    ):
        if isinstance(blink_type, str):
            try:
                self.blink_type = BlinkType(blink_type.lower())
            except ValueError:
                raise ValueError(
                    f"Unknown blink_type string '{blink_type}'. Valid: {[b.value for b in BlinkType]}"
                )
        elif isinstance(blink_type, BlinkType):
            self.blink_type = blink_type
        else:
            raise TypeError(f"blink_type must be BlinkType or str, got {type(blink_type)}")

        if duration_multiplier <= 0.0:
            raise ValueError(f"duration_multiplier must be strictly positive, got {duration_multiplier}")
        if hold_time < 0.0:
            raise ValueError(f"BlinkAction hold_time must be non-negative, got {hold_time}")

        super().__init__(name=name or f"Blink({self.blink_type.value})")
        self.duration_multiplier: float = float(duration_multiplier)
        self.hold_time: float = float(hold_time)

        # Baseline single cycle estimation
        self._expected_blink_dur: float = (0.065 + 0.025 + 0.080) * self.duration_multiplier
        if self.blink_type == BlinkType.DOUBLE:
            self._expected_blink_dur = (0.065 + 0.025 + 0.080) * (0.75 * self.duration_multiplier) * 2 + 0.05
        elif self.blink_type == BlinkType.QUICK:
            self._expected_blink_dur *= 0.65
        elif self.blink_type == BlinkType.SLOW:
            self._expected_blink_dur *= 1.80

        self.total_duration = self._expected_blink_dur + self.hold_time

    def _on_start(self, choreographer: BehaviorChoreographer) -> None:
        choreographer.blink(blink_type=self.blink_type, duration_multiplier=self.duration_multiplier)
        b_ctrl = choreographer.blink_controller
        single_dur = (b_ctrl.close_duration + b_ctrl.hold_duration + b_ctrl.open_duration)
        if self.blink_type == BlinkType.DOUBLE:
            self._expected_blink_dur = single_dur * 2 + getattr(b_ctrl, "_inter_blink_gap", 0.05)
        else:
            self._expected_blink_dur = single_dur
        self.total_duration = self._expected_blink_dur + self.hold_time

    def is_complete(self, choreographer: BehaviorChoreographer) -> bool:
        time_done = (self.elapsed >= self.total_duration - 1e-7)
        blink_done = (not choreographer.blink_controller.is_blinking) and (choreographer.blink_controller.blink_weight < 0.001)
        return time_done and blink_done


class ParallelAction(Action):
    """Executes multiple child actions concurrently within a single timeline step."""

    def __init__(self, actions: Sequence[Action], policy: str = "all", name: str = ""):
        if not actions:
            raise ValueError("ParallelAction requires at least one child action.")
        for a in actions:
            if not isinstance(a, Action):
                raise TypeError(f"All children of ParallelAction must be Action instances, got {type(a)}")

        if policy not in ("all", "first"):
            raise ValueError(f"ParallelAction policy must be 'all' or 'first', got '{policy}'")

        super().__init__(name=name or f"Parallel({len(actions)} actions)")
        self.actions: List[Action] = list(actions)
        self.policy: str = policy
        self.total_duration = 0.0

    def _on_start(self, choreographer: BehaviorChoreographer) -> None:
        for a in self.actions:
            a.start(choreographer)

        durations = [a.total_duration for a in self.actions]
        if self.policy == "all":
            self.total_duration = max(durations) if durations else 0.0
        else:
            self.total_duration = min(durations) if durations else 0.0

    def compute_step(self, residual_dt: float) -> float:
        if residual_dt <= 0.0:
            return 0.0
        time_needed = max(0.0, self.total_duration - self.elapsed)
        step_dt = min(residual_dt, time_needed)
        self.elapsed += step_dt
        for a in self.actions:
            a.elapsed = min(a.total_duration, a.elapsed + step_dt)
        return step_dt

    def is_complete(self, choreographer: BehaviorChoreographer) -> bool:
        time_done = (self.elapsed >= self.total_duration - 1e-7)
        if self.policy == "all":
            children_done = all(a.is_complete(choreographer) for a in self.actions)
        else:
            children_done = any(a.is_complete(choreographer) for a in self.actions)
        return time_done and children_done

    def finish(self) -> None:
        super().finish()
        for a in self.actions:
            a.finish()

    def _on_cancel(self, choreographer: BehaviorChoreographer) -> None:
        for a in self.actions:
            a.cancel(choreographer)


# ===========================================================================
# Behavior Execution Engine
# ===========================================================================

class BehaviorEngine:
    """Deterministic timeline sequence execution engine for ROBoy Emotion V2."""

    def __init__(
        self,
        initial_emotion: str = "neutral",
        choreographer: Optional[BehaviorChoreographer] = None,
    ):
        # Underlying authoritative V2 choreographer
        self._choreographer: BehaviorChoreographer = choreographer or BehaviorChoreographer(
            initial_emotion=initial_emotion
        )

        # Execution Queue & State
        self._queue: Deque[Action] = collections.deque()
        self._current_action: Optional[Action] = None
        self._sequence_name: Optional[str] = None
        self._completed_action_count: int = 0

        # Named Behavior Template Registry (name -> factory callable)
        self._behavior_registry: Dict[str, Callable[[], List[Action]]] = {}

    # -----------------------------------------------------------------------
    # Properties & Status
    # -----------------------------------------------------------------------

    @property
    def choreographer(self) -> BehaviorChoreographer:
        """Access underlying BehaviorChoreographer."""
        return self._choreographer

    @property
    def is_busy(self) -> bool:
        """Return True if an action is currently active or actions are queued."""
        return self._current_action is not None or len(self._queue) > 0

    @property
    def queue_length(self) -> int:
        """Return number of pending actions in the queue (excluding active action)."""
        return len(self._queue)

    @property
    def current_action(self) -> Optional[Action]:
        """Return active Action instance or None if idle."""
        return self._current_action

    @property
    def sequence_name(self) -> Optional[str]:
        """Return label of currently playing sequence if set."""
        return self._sequence_name

    @property
    def completed_action_count(self) -> int:
        """Return count of completed actions in current execution run."""
        return self._completed_action_count

    def get_status(self) -> dict:
        """Return comprehensive telemetry and diagnostic status."""
        cur = self._current_action
        return {
            "is_busy": self.is_busy,
            "sequence_name": self._sequence_name,
            "queue_length": len(self._queue),
            "completed_action_count": self._completed_action_count,
            "current_action_name": getattr(cur, "name", None) if cur else None,
            "current_action_type": cur.__class__.__name__ if cur else None,
            "current_action_elapsed": getattr(cur, "elapsed", 0.0) if cur else 0.0,
            "current_action_duration": getattr(cur, "total_duration", 0.0) if cur else 0.0,
            "current_action_progress": cur.get_progress() if cur else 0.0,
            "choreographer": self._choreographer.get_status(),
        }

    # -----------------------------------------------------------------------
    # Queue & Playback Control
    # -----------------------------------------------------------------------

    def play_sequence(self, actions: Sequence[Action], name: Optional[str] = None) -> None:
        """Replace current queue and start a new action sequence immediately."""
        if not isinstance(actions, (list, tuple)):
            raise TypeError(f"actions must be a list or tuple of Action, got {type(actions)}")
        for i, a in enumerate(actions):
            if not isinstance(a, Action):
                raise TypeError(f"Element at index {i} is not an Action instance: {a}")

        self.interrupt(clear_queue=True)
        self._sequence_name = name
        self._completed_action_count = 0
        for a in actions:
            self._queue.append(a)

    def queue_action(self, action: Action) -> None:
        """Append a single Action to the end of the existing queue without interrupting active action."""
        if not isinstance(action, Action):
            raise TypeError(f"action must be an Action instance, got {type(action)}")
        self._queue.append(action)

    def queue_sequence(self, actions: Sequence[Action]) -> None:
        """Append a sequence of Actions to the end of the existing queue."""
        if not isinstance(actions, (list, tuple)):
            raise TypeError(f"actions must be a list or tuple of Action, got {type(actions)}")
        for i, a in enumerate(actions):
            if not isinstance(a, Action):
                raise TypeError(f"Element at index {i} is not an Action instance: {a}")
            self._queue.append(a)

    def clear_queue(self) -> None:
        """Remove all pending actions from the queue; active action runs to completion."""
        self._queue.clear()

    def interrupt(self, clear_queue: bool = True) -> None:
        """Cancel current action and optionally clear queue without resetting facial pose."""
        if self._current_action is not None:
            self._current_action.cancel(self._choreographer)
            self._current_action = None
        if clear_queue:
            self._queue.clear()
            self._sequence_name = None

    def reset(self, emotion: str = "neutral") -> None:
        """Completely reset engine queue and underlying choreographer to baseline emotion."""
        self.interrupt(clear_queue=True)
        self._completed_action_count = 0
        self._sequence_name = None
        self._choreographer.reset(emotion=emotion)

    # -----------------------------------------------------------------------
    # Named Behavior Registry
    # -----------------------------------------------------------------------

    def register_behavior(self, name: str, factory: Callable[[], List[Action]]) -> None:
        """Register a template factory producing fresh Action instances."""
        if not name or not isinstance(name, str):
            raise ValueError(f"Behavior name must be a non-empty string, got {name}")
        if not callable(factory):
            raise TypeError(f"Behavior factory for '{name}' must be callable, got {type(factory)}")
        self._behavior_registry[name.lower()] = factory

    def trigger_behavior(self, name: str) -> None:
        """Instantiate and play a registered named behavior template."""
        key = name.lower()
        if key not in self._behavior_registry:
            raise KeyError(
                f"Unknown behavior '{name}'. Registered behaviors: {list(self._behavior_registry.keys())}"
            )
        actions = self._behavior_registry[key]()
        self.play_sequence(actions, name=name)

    def list_behaviors(self) -> List[str]:
        """Return list of registered behavior template names."""
        return list(self._behavior_registry.keys())

    # -----------------------------------------------------------------------
    # Deterministic Frame Update Loop
    # -----------------------------------------------------------------------

    def update(self, dt: float) -> fc.FaceSpec:
        """Advance the behavior timeline by dt seconds and return the composed FaceSpec.

        Handles exact residual time cascading across action boundaries within the same frame.
        """
        if dt < 0.0:
            raise ValueError(f"dt must be non-negative, got {dt}")

        residual_dt = dt
        iterations = 0
        MAX_ITERATIONS = 100  # Guard against infinite loops with zero-duration actions

        while residual_dt > 0.0 and (self._current_action is not None or len(self._queue) > 0):
            iterations += 1
            if iterations > MAX_ITERATIONS:
                break

            if self._current_action is None:
                if len(self._queue) == 0:
                    break
                self._current_action = self._queue.popleft()
                self._current_action.start(self._choreographer)

            step_dt = self._current_action.compute_step(residual_dt)
            if step_dt > 0.0:
                self._choreographer.update(step_dt)
                residual_dt -= step_dt

            if self._current_action.is_complete(self._choreographer):
                self._current_action.finish()
                self._completed_action_count += 1
                self._current_action = None

        # Advance choreographer for remaining idle dt (or zero-dt inspection)
        if residual_dt > 0.0:
            self._choreographer.update(residual_dt)
        elif dt == 0.0:
            self._choreographer.update(0.0)

        return self._choreographer.get_current_spec()

    def get_current_spec(self) -> fc.FaceSpec:
        """Return the most recently computed composed FaceSpec."""
        return self._choreographer.get_current_spec()
