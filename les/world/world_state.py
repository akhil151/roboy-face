"""
World State facade for the Living Expression System.

World State is the robot's CURRENT understanding of the environment - a set
of facts that are true RIGHT NOW. It is the read model that future LES
systems (Emotion Director, Behavior Director, Timeline, Scheduler) will
consume to make decisions. World State itself NEVER decides.

STRICT RULES (design authority: this package's spec):
    * Stores ONLY current facts - NEVER history, NEVER previous events.
    * NEVER stores cooldowns or persistence (that is Behavior Memory).
    * NEVER performs reasoning, prediction, or arbitration.
    * NEVER chooses behaviors, modifies emotions, or modifies memory.
    * No pygame, no animation engine, no renderer, no hardware drivers,
      no ROS, no servo code, no OpenCV / MediaPipe / Whisper / LLM.

World State vs Behavior Memory:
    * Behavior Memory answers "What happened?" (history, cooldowns).
    * World State answers "What is true right now?" (current facts).
    * The two never overlap: memory stores the past, world stores the now.

Design notes
------------
* Every fact carries an explicit quality (see ``value_quality``) so
  consumers never confuse "unknown" with "unavailable" with "invalid".
* Time is caller-supplied: ``set_timestamp(now_ms)`` records the current
  world timestamp; ``snapshot(now_ms)`` refreshes it before capturing.
* Extensibility: a generic ``SensorValueRegistry`` (``sensors``) allows
  future sensors (depth camera, IMU, battery, lidar, ultrasonic,
  environmental, network, ROS topics, LLM state, vision models) to store
  their current values WITHOUT redesigning this subsystem.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Tuple

from .attention_state import AttentionState
from .interaction_state import InteractionMode, InteractionState
from .perception_state import PerceptionState
from .value_quality import SensorValue, ValueQuality


class SessionStatus(str, Enum):
    """The robot's current session status (vocabulary only, no logic).

    Members: BOOTING, ACTIVE, PAUSED, SLEEPING, ENDED.
    """

    BOOTING = "booting"
    ACTIVE = "active"
    PAUSED = "paused"
    SLEEPING = "sleeping"
    ENDED = "ended"


@dataclass
class SensorValueRegistry:
    """Generic store of CURRENT values from any future sensor source.

    Each entry is one name -> one current ``SensorValue``. Storing a new
    name automatically creates the slot - no redesign needed for depth
    cameras, IMUs, batteries, lidar, ultrasonic, environmental sensors,
    network status, ROS topics, LLM state, or vision models.

    Attributes:
        _values: name -> current value (internal; use the methods).
    """

    _values: Dict[str, SensorValue[object]] = field(default_factory=dict)

    def set(self, name: str, value: object, quality: ValueQuality = ValueQuality.VALID) -> None:
        """Record the current value for ``name`` (creates the slot if new)."""
        self._values[name] = SensorValue[object](value=value, quality=quality)

    def get(self, name: str) -> SensorValue[object]:
        """Return the current value for ``name`` (UNKNOWN if never set)."""
        return self._values.get(name, SensorValue.unknown())

    def has(self, name: str) -> bool:
        """True when ``name`` has a recorded current value."""
        return name in self._values

    def names(self) -> tuple[str, ...]:
        """Names of all currently-recorded sensors (sorted)."""
        return tuple(sorted(self._values))

    def copy(self) -> "SensorValueRegistry":
        """A detached copy of this registry (values are frozen - sharing is safe)."""
        return SensorValueRegistry(dict(self._values))

    def clear(self) -> None:
        """Clear every recorded sensor value (configuration is not stored)."""
        self._values.clear()


@dataclass(frozen=True)
class WorldSnapshot:
    """Immutable, complete view of the current world at one instant.

    Created by ``WorldState.snapshot()``. Frozen and shallow-copied so a
    consumer can read a consistent picture without holding the live state.
    Never used for writing - it is a read-only view.

    Attributes:
        timestamp_ms: world time at which the snapshot was taken.
        session_status: current session status.
        perception: current perception facts (faces, emotion, speech...).
        attention: current attention facts (target, gaze, eye contact...).
        interaction: current interaction facts (mode, speaking, touch...).
        environment_state: current environmental label (e.g. "normal").
        sensors: current generic sensor values (extensible registry).
    """

    timestamp_ms: float
    session_status: SessionStatus
    perception: PerceptionState
    attention: AttentionState
    interaction: InteractionState
    environment_state: SensorValue[str]
    sensors: SensorValueRegistry


class WorldState:
    """Facade over the robot's current understanding of the world.

    Compose + expose current facts. This class NEVER decides - it is a
    pure read/write store where callers report facts and consumers read
    them.

    Args:
        perception: optional shared ``PerceptionState`` (injected).
        attention: optional shared ``AttentionState`` (injected).
        interaction: optional shared ``InteractionState`` (injected).
        sensors: optional shared ``SensorValueRegistry`` (injected).
        timestamp_ms: initial world timestamp (0 = unset).
        session_status: initial session status.
    """

    def __init__(
        self,
        perception: Optional[PerceptionState] = None,
        attention: Optional[AttentionState] = None,
        interaction: Optional[InteractionState] = None,
        sensors: Optional[SensorValueRegistry] = None,
        timestamp_ms: float = 0.0,
        session_status: SessionStatus = SessionStatus.BOOTING,
    ) -> None:
        self.perception = perception if perception is not None else PerceptionState()
        self.attention = attention if attention is not None else AttentionState()
        self.interaction = interaction if interaction is not None else InteractionState()
        self.sensors = sensors if sensors is not None else SensorValueRegistry()
        self.timestamp_ms = timestamp_ms
        self.session_status = session_status
        self._environment_state: SensorValue[str] = SensorValue.unknown()

    # ------------------------------------------------------------------
    # Time / session - callers report facts; this store only records them.
    # ------------------------------------------------------------------

    def set_timestamp(self, now_ms: float) -> None:
        """Record the current world timestamp (caller-supplied clock)."""
        self.timestamp_ms = now_ms

    def set_session_status(self, status: SessionStatus) -> None:
        """Record the current session status (one of ``SessionStatus``)."""
        self.session_status = status

    # ------------------------------------------------------------------
    # Update methods - thin delegation to the sub-states.
    # ------------------------------------------------------------------

    def update_face(
        self,
        face_present: bool,
        position: Optional[Tuple[float, float]],
        confidence: float,
    ) -> None:
        """Record current face-detection facts (delegates to perception)."""
        self.perception.update_face(face_present, position, confidence)

    def update_face_count(self, visible_faces: int) -> None:
        """Record how many faces are currently visible."""
        self.perception.update_face_count(visible_faces)

    def update_emotion(self, emotion: str, confidence: float) -> None:
        """Record the currently-detected emotion label and confidence."""
        self.perception.update_emotion(emotion, confidence)

    def update_speech(self, detected: bool) -> None:
        """Record whether speech is currently detected."""
        self.perception.update_speech(detected)

    def update_motion(self, detected: bool) -> None:
        """Record whether motion is currently detected."""
        self.perception.update_motion(detected)

    def update_camera_available(self, available: bool) -> None:
        """Record whether the camera input is available."""
        self.perception.set_camera_available(available)

    def update_microphone_available(self, available: bool) -> None:
        """Record whether the microphone input is available."""
        self.perception.set_microphone_available(available)

    def update_attention_target(self, target: Optional[Tuple[float, float]]) -> None:
        """Record the current primary attention target."""
        self.attention.update_attention_target(target)

    def update_gaze_position(self, position: Optional[Tuple[float, float]]) -> None:
        """Record where the robot's gaze currently points."""
        self.attention.update_gaze_position(position)

    def update_eye_contact(self, exists: bool) -> None:
        """Record whether mutual eye contact currently exists."""
        self.attention.update_eye_contact(exists)

    def update_tracking(self, active: bool, lost: bool) -> None:
        """Record the current tracking facts."""
        self.attention.update_tracking(active, lost)

    def update_interaction_mode(self, mode: InteractionMode) -> None:
        """Record the current interaction mode (reported by decision layer)."""
        self.interaction.update_interaction_mode(mode)

    def update_robot_speaking(self, speaking: bool) -> None:
        """Record whether the robot is currently speaking."""
        self.interaction.update_robot_speaking(speaking)

    def update_touch(self, active: bool) -> None:
        """Record whether a touch is currently active."""
        self.interaction.update_touch(active)

    def update_environment_state(self, label: str) -> None:
        """Record the current environmental state label (e.g. "normal",
        "dark", "noisy"). The label vocabulary is caller-chosen."""
        self._environment_state = SensorValue.valid(label)

    # ------------------------------------------------------------------
    # Generic sensor registry - future sensors, no redesign.
    # ------------------------------------------------------------------

    def set_sensor_value(
        self, name: str, value: object, quality: ValueQuality = ValueQuality.VALID
    ) -> None:
        """Record a current value from any (future) sensor source.

        Examples of future names: "depth_camera", "imu", "battery_level",
        "lidar", "ultrasonic", "environment_temperature", "network_status",
        "ros_topic:...", "llm_state", "vision_model:...".
        """
        self.sensors.set(name, value, quality)

    def get_sensor_value(self, name: str) -> SensorValue[object]:
        """Read the current value for a sensor name (UNKNOWN if never set)."""
        return self.sensors.get(name)

    def sensor_names(self) -> tuple[str, ...]:
        """Names of all sensors with a recorded current value."""
        return self.sensors.names()

    # ------------------------------------------------------------------
    # Queries / lifecycle
    # ------------------------------------------------------------------

    def current(self) -> WorldSnapshot:
        """Immutable read-only view of the current world (alias of snapshot)."""
        return self.snapshot()

    def snapshot(self, now_ms: Optional[float] = None) -> WorldSnapshot:
        """Capture an immutable snapshot of the current world.

        The sub-states are COPIED (shallow), not referenced: every field of
        ``PerceptionState`` / ``AttentionState`` / ``InteractionState`` is a
        frozen ``SensorValue`` (or a plain bool / enum), so the shallow copy
        is effectively immutable - later live-world updates cannot change a
        snapshot a consumer is holding.

        Args:
            now_ms: optional caller clock; refreshes ``timestamp_ms`` first.
        """
        if now_ms is not None:
            self.timestamp_ms = now_ms
        return WorldSnapshot(
            timestamp_ms=self.timestamp_ms,
            session_status=self.session_status,
            perception=copy.copy(self.perception),
            attention=copy.copy(self.attention),
            interaction=copy.copy(self.interaction),
            environment_state=self._environment_state,
            sensors=self.sensors.copy(),
        )

    def reset(self) -> None:
        """Restore the default world: sub-states reset, session to BOOTING,
        timestamp to 0, sensor registry cleared.

        Configuration (injected sub-states, if any) is preserved - reset
        clears recorded facts, not wiring.
        """
        self.perception.reset()
        self.attention.reset()
        self.interaction.reset()
        self.sensors.clear()
        self._environment_state = SensorValue.unknown()
        self.timestamp_ms = 0.0
        self.session_status = SessionStatus.BOOTING


__all__ = ["WorldState", "WorldSnapshot", "SessionStatus", "SensorValueRegistry"]
