"""ROBoy Emotion V2 - Phase 6 Behavior Choreography & Composition Layer.

Coordinates emotion states, live emotion transitions, gaze/look directions,
and eyelid blinks into a unified, composed FaceSpec.

Architecture:
    V2 Emotion State (emotions.py / face.py)
          |
    V2 Transition Engine (transition.py - authoritative)
          | (base FaceSpec)
    Behavior Composition Layer (choreography.py)
          +-- LookController (gaze translation)
          +-- BlinkController (eyelid closure)
          |
    Composed FaceSpec (normalized coordinates)
          |
    V2 Renderer (renderer.py)

Priority Hierarchy:
    1. EMOTION & TRANSITION (Priority 1 - Foundation)
       - Determines base facial geometry, eye contours, mouth shapes, and transition morphing.
    2. GAZE / LOOK (Priority 2 - Spatial Offset)
       - Rigidly translates eye centers without modifying curvature or emotion contours.
    3. BLINK (Priority 3 - Closure Modulation)
       - Smoothly closes and reopens eyelids on top of the live emotion and gaze pose.
    4. OVERLAYS (Priority 4 - Contextual Cues)
       - Coordinated placement for Thinking '?' and Sleepy 'ZZZ' cues.
"""

from __future__ import annotations

import copy
from typing import Optional, Tuple

import config as cfg
import face as fc
import emotions as em
import transition as tr
from blink_controller import BlinkController, BlinkType, BlinkState, apply_blink_to_eye
from look_controller import LookController, apply_gaze_to_eye


def compose_face(
    base_spec: fc.FaceSpec,
    look_ctrl: LookController,
    blink_ctrl: BlinkController,
) -> fc.FaceSpec:
    """Compose a base V2 FaceSpec with active gaze offset and blink closure.

    Invariants:
    - If gaze=(0,0) and blink_weight=0, returns exact identical FaceSpec.
    - If gaze active, translates eye geometry rigidly.
    - If blink active, compresses eye openness while preserving emotion contours.
    - Preserves asymmetric Wink emotion and all overlay cues.
    """
    off_x, off_y = look_ctrl.get_spatial_offset()
    blink_w = blink_ctrl.blink_weight
    is_wink = (base_spec.emotion == "wink")

    # Fast-path: no active behavior modifiers
    if abs(off_x) < 1e-6 and abs(off_y) < 1e-6 and blink_w <= 0.0001:
        return base_spec

    composed_eyes = []
    for i, eye in enumerate(base_spec.eyes):
        side = "left" if i == 0 else "right"
        # 1. Apply gaze translation
        eye_gazed = apply_gaze_to_eye(eye, off_x, off_y)
        # 2. Apply blink closure
        eye_composed = apply_blink_to_eye(eye_gazed, blink_w, side=side, is_wink=is_wink)
        composed_eyes.append(eye_composed)

    return fc.FaceSpec(
        base_spec.emotion,
        composed_eyes,
        base_spec.mouth,
        base_spec.overlays,
    )


class BehaviorChoreographer:
    """Unified behavior coordinator managing transitions, gaze, and blinks for ROBoy V2."""

    def __init__(
        self,
        initial_emotion: str = "neutral",
        transition_duration: Optional[float] = None,
    ):
        # Authoritative V2 transition engine
        self.transition_controller = tr.TransitionController(
            initial_emotion=initial_emotion,
            duration=transition_duration,
        )
        # Additive behavior controllers
        self.blink_controller = BlinkController()
        self.look_controller = LookController()

        # Current composed face spec
        self._current_composed_spec: fc.FaceSpec = self.transition_controller.get_current_spec()

    # -----------------------------------------------------------------------
    # Emotion & Transition API
    # -----------------------------------------------------------------------

    @property
    def current_emotion(self) -> str:
        return self.transition_controller.current_emotion

    @property
    def target_emotion(self) -> Optional[str]:
        return self.transition_controller.target_emotion

    @property
    def is_transitioning(self) -> bool:
        return self.transition_controller.is_transitioning()

    @property
    def transition_progress(self) -> float:
        return self.transition_controller.get_progress()

    def request_emotion(
        self,
        new_emotion: str,
        duration: Optional[float] = None,
        reset_time: bool = True,
    ) -> None:
        """Request a transition to new_emotion using the authoritative V2 transition engine.

        If a transition is already in progress, seamlessly interrupts from current pose.
        """
        self.transition_controller.request_emotion(new_emotion, duration=duration, reset_time=reset_time)

    # -----------------------------------------------------------------------
    # Blink API
    # -----------------------------------------------------------------------

    @property
    def is_blinking(self) -> bool:
        return self.blink_controller.is_blinking

    @property
    def blink_weight(self) -> float:
        return self.blink_controller.blink_weight

    def blink(
        self,
        blink_type: BlinkType = BlinkType.NORMAL,
        duration_multiplier: float = 1.0,
    ) -> None:
        """Trigger an organic eyelid blink."""
        self.blink_controller.trigger_blink(blink_type=blink_type, duration_multiplier=duration_multiplier)

    # -----------------------------------------------------------------------
    # Gaze / Look API
    # -----------------------------------------------------------------------

    @property
    def is_looking(self) -> bool:
        return self.look_controller.is_moving

    @property
    def gaze_direction(self) -> Tuple[float, float]:
        return self.look_controller.gaze_direction

    def look_direction(self, direction: str, duration: Optional[float] = None) -> None:
        """Direct gaze toward a named direction ('center', 'left', 'right', 'up', 'down', etc.)."""
        self.look_controller.look_direction(direction, duration=duration)

    def look_at(self, x: float, y: float, duration: Optional[float] = None) -> None:
        """Direct gaze toward normalized coordinates (x, y) in [-1.0, 1.0]."""
        self.look_controller.look_at(x, y, duration=duration)

    def center_gaze(self, duration: Optional[float] = None) -> None:
        """Return gaze smoothly to center (0, 0)."""
        self.look_controller.look_direction("center", duration=duration)

    # -----------------------------------------------------------------------
    # Expressive Combos / Winks
    # -----------------------------------------------------------------------

    def wink(self, duration: Optional[float] = None) -> None:
        """Expressive wink shortcut: requests Wink emotion or triggers asymmetric blink."""
        if self.current_emotion != "wink":
            self.request_emotion("wink", duration=duration or 0.35)

    # -----------------------------------------------------------------------
    # Main Deterministic Update Loop
    # -----------------------------------------------------------------------

    def update(self, dt: float) -> fc.FaceSpec:
        """Advance time by dt seconds, update all layers, and return composed FaceSpec."""
        # 1. Base emotion / transition pose (authoritative V2)
        base_face = self.transition_controller.update(dt)

        # 2. Additive behaviors
        self.blink_controller.update(dt)
        self.look_controller.update(dt)

        # 3. Layered composition
        self._current_composed_spec = compose_face(
            base_face,
            self.look_controller,
            self.blink_controller,
        )
        return self._current_composed_spec

    def get_current_spec(self) -> fc.FaceSpec:
        """Return the most recently computed composed FaceSpec."""
        return self._current_composed_spec

    def get_status(self) -> dict:
        """Return comprehensive status dictionary for diagnostics and telemetry."""
        tr_status = self.transition_controller.get_status()
        return {
            "emotion": tr_status["current"],
            "target_emotion": tr_status["target"],
            "is_transitioning": tr_status["is_transitioning"],
            "transition_progress": tr_status["progress"],
            "transition_elapsed": tr_status["elapsed"],
            "is_blinking": self.blink_controller.is_blinking,
            "blink_state": self.blink_controller.state.value,
            "blink_weight": self.blink_controller.blink_weight,
            "is_looking": self.look_controller.is_moving,
            "gaze_x": self.look_controller.cur_x,
            "gaze_y": self.look_controller.cur_y,
            "gaze_target_x": self.look_controller.target_x,
            "gaze_target_y": self.look_controller.target_y,
        }

    def reset(self, emotion: str = "neutral") -> None:
        """Reset all layers immediately."""
        self.transition_controller.reset(emotion=emotion)
        self.blink_controller.reset()
        self.look_controller.reset(0.0, 0.0)
        self._current_composed_spec = self.transition_controller.get_current_spec()


# Alias for backward and forward compatibility
ChoreographyController = BehaviorChoreographer
