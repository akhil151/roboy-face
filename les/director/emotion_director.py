"""
Emotion Director - determines the robot's INTERNAL emotional state.

The Emotion Director is NOT a detector, NOT a behavior selector, NOT a
scheduler, and NOT the animation engine. Its ONLY responsibility is to
determine "what is the robot currently feeling?" from the current world
state and recent behavioral memory, applying the configurable rules of the
Emotion Policy.

Pipeline position:

    World State -> Behavior Memory -> Emotion Policy -> Emotion Director
                                                          -> Internal Emotion State

The director NEVER schedules behaviors, chooses blink types, controls
servos or gaze, selects animations, makes interaction decisions, speaks,
or tracks faces. It ONLY determines internal emotion.

Data contracts (unchanged, backward compatible):
    * ``EmotionInput``    - a detection produced by an external source.
    * ``EmotionIntent``   - the director's decision about current feeling.
    * ``EmotionDirector`` - the interface (ABC).

Concrete orchestration:
    * ``DefaultEmotionDirector`` - reads World State + Behavior Memory,
      applies ``EmotionPolicy``, and exposes ``InternalEmotionState``.

Design notes
------------
* All time is internal: ``update(dt_ms)`` advances the director's own
  clock; memory records use that same clock (caller never supplies it).
* The director writes its determined emotion into Behavior Memory via
  ``record_emotion`` so memory stays the shared store of record and the
  emotional persistence/history lives in ONE place.
* Flicker prevention is layered: persistence gate + transition hysteresis
  + recovery cooldown + confidence margin + valence waypoint routing.

Responsibility notes
--------------------
* Reads: ``WorldState`` (perception.detected_emotion + confidence, quality).
* Reads: ``BehaviorMemory`` (current/previous emotion, persistence).
* Writes: ``BehaviorMemory.record_emotion`` (its own output channel only).
* Never reads or writes anything else.

Extension notes (LES-Phase-1+)
------------------------------
* A personality-derived policy can replace ``EmotionPolicy`` wholesale
  (the director only reads the policy; it never writes it).
* Additional inputs (manual override, voice sentiment) enter via
  ``ingest()`` without changing orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional

from ..config.defaults import DirectorConfig
from ..memory.behavior_memory import BehaviorMemory
from ..world.value_quality import ValueQuality
from ..world.world_state import WorldState
from .emotion_policy import EmotionPolicy


@dataclass(frozen=True)
class EmotionInput:
    """A single emotion detection produced by an external source.

    Attributes:
        source: e.g. "vision", "voice", "sensor", "manual".
        emotion: a raw detector label or an engine state name.
        confidence: in [0, 1].
        timestamp_ms: when the detection happened (source clock).
    """

    source: str
    emotion: str
    confidence: float
    timestamp_ms: float


@dataclass(frozen=True)
class EmotionIntent:
    """The director's decision about what the robot currently feels."""

    emotion: str
    confidence: float
    priority: float
    urgency: float
    expires_ms: float


@dataclass(frozen=True)
class EmotionTransition:
    """One recorded emotion transition (reported to listeners + memory)."""

    from_emotion: Optional[str]
    to_emotion: str
    reason: str
    confidence: float
    timestamp_ms: float


@dataclass(frozen=True)
class InternalEmotionState:
    """Snapshot of the director's internal emotional state at one instant.

    Attributes:
        emotion: the current internal emotion (``None`` = neutral).
        previous_emotion: the emotion before the current one.
        confidence: how strongly the current emotion is held, in [0, 1].
        stability: how settled the emotion is, in [0, 1] (grows with
            persistence and confidence).
        persistence_ms: how long the current emotion has been held.
        transition_in_progress: a transition happened on this tick.
        transition_allowed: the candidate was accepted this tick (either a
            transition or a same-emotion confirmation).
        transition_blocked: a change was requested but denied.
        blocked_reason: why the change was denied (see update() reasons).
        recovery_state: "neutral" | "holding" | "transitioning".
        transition_reason: why the last transition happened.
        timestamp_ms: the director clock at which this state was captured.
    """

    emotion: Optional[str]
    previous_emotion: Optional[str]
    confidence: float
    stability: float
    persistence_ms: float
    transition_in_progress: bool
    transition_allowed: bool
    transition_blocked: bool
    blocked_reason: Optional[str]
    recovery_state: str
    transition_reason: Optional[str]
    timestamp_ms: float


class EmotionDirector(ABC):
    """Interface for the component that turns detections into intents."""

    @abstractmethod
    def ingest(self, detection: EmotionInput) -> None:
        """Feed one emotion detection into the director."""
        ...

    @abstractmethod
    def update(self, dt_ms: float) -> None:
        """Advance internal state (expiry, hysteresis). Called once per tick."""
        ...

    @abstractmethod
    def current_intent(self) -> Optional[EmotionIntent]:
        """Return the current intent, or None while the robot is neutral."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Return to a neutral state (e.g. shutdown / robot reset)."""
        ...


class DefaultEmotionDirector(EmotionDirector):
    """Concrete Emotion Director: reads world + memory, applies policy.

    Orchestration (called once per tick via ``update(dt_ms)``):

    1. Resolve a candidate detection from World State (quality VALID) or
       from an ``ingest()``ed detection (whichever is freshest).
    2. Reject weak detections (confidence < ``policy.min_confidence``).
    3. If the candidate equals the current emotion -> CONFIRM (raise
       confidence, keep persistence going). No transition.
    4. Otherwise the candidate must pass, in order:
         a. persistence gate   - current emotion held >= persistence_ms
         b. hysteresis gate    - not within hysteresis_ms of last transition
         c. recovery cooldown  - candidate != previous emotion within
                                 recovery_cooldown_ms of leaving it
         d. valence waypoint   - a direct valence flip routes through the
                                 neutral emotion first (continuity)
         e. confidence margin  - candidate closes the gap to the held
                                 confidence within the policy margin
    5. Any failed gate blocks the change (transition_blocked + reason);
       the held emotion continues. Passing all gates performs the
       transition (transition_in_progress + reason).

    Reasons used: "detection", "confirmation" (no transition), "recovery"
    (neutral fallback), "valence_waypoint", and blocked reasons
    "persistence", "hysteresis", "recovery_cooldown", "insufficient_confidence".

    Args:
        world: the World State facade (read-only here).
        memory: the Behavior Memory facade (read + emotion recording).
        policy: the EmotionPolicy to apply (default policy if omitted).
        config: optional DirectorConfig; seeds the policy when ``policy``
            is omitted (config.intent_hysteresis_ms -> persistence).
    """

    def __init__(
        self,
        world: WorldState,
        memory: BehaviorMemory,
        policy: Optional[EmotionPolicy] = None,
        config: Optional[DirectorConfig] = None,
    ) -> None:
        self._world = world
        self._memory = memory
        self._policy = policy if policy is not None else EmotionPolicy.from_config(config)

        # Director-owned clock and internal emotional bookkeeping.
        self._now_ms: float = 0.0
        self._current_confidence: float = 0.0
        self._last_valid_detection_ms: float = float("-inf")
        self._last_transition_ms: float = float("-inf")
        self._pending_detection: Optional[EmotionInput] = None
        self._last_transition: Optional[EmotionTransition] = None
        self._transition_listeners: list[Callable[[EmotionTransition], None]] = []

        # Per-tick evaluation artifacts (reset by update()).
        self._tick_transitioned: bool = False
        self._tick_allowed: bool = False
        self._tick_blocked_reason: Optional[str] = None
        self._tick_reason: Optional[str] = None

    # ------------------------------------------------------------------
    # EmotionDirector interface
    # ------------------------------------------------------------------

    def ingest(self, detection: EmotionInput) -> None:
        """Queue one detection from an external source.

        The queued detection is consumed on the next ``update()`` if it is
        fresher than the world's current perception (or if the world has no
        valid detection).
        """
        self._pending_detection = detection

    def update(self, dt_ms: float) -> None:
        """Advance the director by one tick: re-evaluate internal emotion."""
        dt_ms = max(0.0, dt_ms)
        self._now_ms += dt_ms
        now = self._now_ms
        policy = self._policy

        # Reset per-tick artifacts.
        self._tick_transitioned = False
        self._tick_allowed = False
        self._tick_blocked_reason = None
        self._tick_reason = None

        candidate = self._resolve_candidate()

        current = self._memory.emotional.emotion
        persisted_ms = (
            self._memory.emotional.emotion_elapsed_ms(now) if current is not None else 0.0
        )

        # --- Weak / absent detection: decay + possible neutral recovery. ---
        if candidate is None:
            self._decay_confidence(dt_ms)
            if current is not None and current != policy.neutral_emotion:
                if (now - self._last_valid_detection_ms) >= policy.neutral_fallback_after_ms:
                    self._perform_transition(
                        to_emotion=policy.neutral_emotion,
                        confidence=policy.neutral_confidence,
                        reason="recovery",
                    )
            return

        self._last_valid_detection_ms = now
        candidate_emotion, candidate_conf = candidate

        # --- Same emotion -> confirm (no transition). ---
        if candidate_emotion == current:
            self._current_confidence = max(self._current_confidence, candidate_conf)
            self._tick_allowed = True
            return

        # --- A different emotion: apply the gate chain. ---
        if current is None:
            self._perform_transition(
                to_emotion=candidate_emotion,
                confidence=candidate_conf,
                reason="detection",
            )
            return

        # a. Persistence gate.
        if persisted_ms < policy.persistence_ms:
            self._tick_blocked_reason = "persistence"
            return

        # b. Hysteresis gate (no rapid re-transitions).
        if (now - self._last_transition_ms) < policy.hysteresis_ms:
            self._tick_blocked_reason = "hysteresis"
            return

        # c. Recovery cooldown (A -> B -> A flicker prevention). Runs
        # before the waypoint so routing through neutral can never be used
        # to bypass A -> neutral -> A flicker suppression.
        if (
            candidate_emotion == self._memory.emotional.previous_emotion
            and (now - self._last_transition_ms) < policy.recovery_cooldown_ms
        ):
            self._tick_blocked_reason = "recovery_cooldown"
            return

        # d. Valence waypoint: a direct valence flip routes through neutral
        #    first (continuity). Checked BEFORE the confidence margin because
        #    moving toward neutral is always safe - continuity outranks the
        #    candidate's strength; the final leg (neutral -> candidate) still
        #    has to clear the margin gate.
        if (
            policy.valence_of(current) != 0
            and policy.valence_of(candidate_emotion) == -policy.valence_of(current)
            and current != policy.neutral_emotion
        ):
            self._perform_transition(
                to_emotion=policy.neutral_emotion,
                confidence=policy.neutral_confidence,
                reason="valence_waypoint",
            )
            return

        # e. Confidence margin: the candidate must close the gap to the
        #    held confidence, i.e. candidate_conf + margin >= held_conf.
        #    (The margin is the slack a candidate may have below the held
        #    confidence and still displace it; higher-priority emotions get
        #    more slack, lower-priority ones less. Comparing the candidate
        #    AGAINST the held value would make the gate unreachable once
        #    the held confidence is high - the robot could never change
        #    emotion - so the candidate is never required to beat it by the
        #    margin on top.)
        margin = policy.transition_margin(current, candidate_emotion)
        if candidate_conf + margin < self._current_confidence:
            self._tick_blocked_reason = "insufficient_confidence"
            return

        # All gates passed -> transition.
        self._perform_transition(
            to_emotion=candidate_emotion,
            confidence=candidate_conf,
            reason="detection",
        )

    def current_intent(self) -> Optional[EmotionIntent]:
        """Expose the current feeling as an intent (None while neutral)."""
        current = self._memory.emotional.emotion
        if current is None:
            return None
        policy = self._policy
        return EmotionIntent(
            emotion=current,
            confidence=self._current_confidence,
            priority=policy.priority_of(current),
            urgency=1.0 if self._tick_transitioned else 0.5,
            expires_ms=(
                self._now_ms + policy.intent_ttl_ms if policy.intent_ttl_ms >= 0 else -1.0
            ),
        )

    def reset(self) -> None:
        """Return to neutral: clears internal clock, state, and listeners
        stay registered (config). Memory emotional state is reset too so the
        shared store stays consistent with the director's neutral state."""
        self._now_ms = 0.0
        self._current_confidence = 0.0
        self._last_valid_detection_ms = float("-inf")
        self._last_transition_ms = float("-inf")
        self._pending_detection = None
        self._last_transition = None
        self._tick_transitioned = False
        self._tick_allowed = False
        self._tick_blocked_reason = None
        self._tick_reason = None
        self._memory.emotional.reset()

    # ------------------------------------------------------------------
    # Director-specific API
    # ------------------------------------------------------------------

    def internal_state(self) -> InternalEmotionState:
        """Snapshot of the current internal emotional state."""
        now = self._now_ms
        current = self._memory.emotional.emotion
        previous = self._memory.emotional.previous_emotion
        persisted_ms = (
            self._memory.emotional.emotion_elapsed_ms(now) if current is not None else 0.0
        )
        policy = self._policy

        stability = min(1.0, persisted_ms / policy.stability_ramp_ms) * self._current_confidence

        if current is None:
            recovery_state = "neutral"
        else:
            recovery_state = "transitioning" if self._tick_transitioned else "holding"

        return InternalEmotionState(
            emotion=current,
            previous_emotion=previous,
            confidence=self._current_confidence,
            stability=stability,
            persistence_ms=persisted_ms,
            transition_in_progress=self._tick_transitioned,
            transition_allowed=self._tick_allowed,
            transition_blocked=self._tick_blocked_reason is not None,
            blocked_reason=self._tick_blocked_reason,
            recovery_state=recovery_state,
            transition_reason=self._tick_reason,
            timestamp_ms=now,
        )

    def last_transition(self) -> Optional[EmotionTransition]:
        """The most recent emotion transition, or ``None`` if none yet."""
        return self._last_transition

    def add_transition_listener(
        self, listener: Callable[[EmotionTransition], None]
    ) -> None:
        """Register a callback invoked with every emotion transition."""
        self._transition_listeners.append(listener)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_candidate(self) -> Optional[tuple[str, float]]:
        """Resolve the freshest valid candidate: ingest() or World State.

        An ``ingest``ed detection wins when it is newer than the world's
        perception timestamp (or when the world has no valid detection).
        A candidate must have quality VALID and confidence above
        ``policy.min_confidence`` to be considered - anything weaker is
        treated as "no candidate" (weak detections are ignored).
        """
        world = self._world
        world_candidate: Optional[tuple[str, float]] = None
        sv_emotion = world.perception.detected_emotion
        sv_confidence = world.perception.emotion_confidence
        if (
            sv_emotion.quality is ValueQuality.VALID
            and sv_confidence.quality is ValueQuality.VALID
            and sv_emotion.value is not None
            and sv_confidence.value is not None
        ):
            world_candidate = (sv_emotion.value, sv_confidence.value)

        pending = self._pending_detection
        self._pending_detection = None  # consume the queue regardless
        if pending is not None and pending.timestamp_ms >= world.timestamp_ms:
            candidate = (pending.emotion, pending.confidence)
        else:
            candidate = world_candidate

        if candidate is None:
            return None
        emotion, confidence = candidate
        if confidence < self._policy.min_confidence:
            return None
        return candidate

    def _decay_confidence(self, dt_ms: float) -> None:
        """Decay the held confidence while no valid detection is present."""
        rate = self._policy.confidence_decay_per_sec
        if rate <= 0.0 or self._current_confidence <= self._policy.neutral_confidence:
            return
        decay = rate * (dt_ms / 1000.0)
        floor = self._policy.neutral_confidence
        self._current_confidence = max(floor, self._current_confidence - decay)

    def _perform_transition(self, to_emotion: str, confidence: float, reason: str) -> None:
        """Record a transition: update memory, fire listeners, set artifacts."""
        now = self._now_ms
        from_emotion = self._memory.emotional.emotion
        self._memory.record_emotion(to_emotion, now)

        transition = EmotionTransition(
            from_emotion=from_emotion,
            to_emotion=to_emotion,
            reason=reason,
            confidence=confidence,
            timestamp_ms=now,
        )
        self._last_transition = transition
        self._last_transition_ms = now
        self._current_confidence = confidence
        self._tick_transitioned = True
        self._tick_allowed = True
        self._tick_reason = reason
        for listener in self._transition_listeners:
            listener(transition)


__all__ = [
    "EmotionInput",
    "EmotionIntent",
    "EmotionTransition",
    "InternalEmotionState",
    "EmotionDirector",
    "DefaultEmotionDirector",
]
