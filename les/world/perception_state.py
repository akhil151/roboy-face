"""
Perception facts for the LES World State.

Represents what the robot's SENSORS currently report about the world:
faces, emotion detections, speech, motion, and sensor availability.

This is a pure fact holder - it stores ONLY the current perception state.
It never stores history, never reasons, never predicts, never decides.

Design notes
------------
* Every field is a ``SensorValue`` carrying an explicit quality label
  (``value_quality``): UNKNOWN until first reported, VALID once reported,
  SENSOR_UNAVAILABLE when the source sensor is absent.
* Positions are normalised ``(x, y)`` tuples in [0, 1] per axis (matching
  the LES look-target convention); callers may choose any consistent space
  but should document it.

Extension notes (LES-Phase-1+)
------------------------------
* New perception sources (depth camera, lidar, ultrasonic, IMU) do not
  belong here - add them via ``WorldState``'s generic sensor registry
  (``world_state.SensorValueRegistry``) without redesigning this module.

Architecture notes
------------------
* This module is one of three World State sub-states (perception,
  attention, interaction) composed by the ``WorldState`` facade. It is
  deliberately kept free of time handling - the facade owns the clock.

Responsibility notes
--------------------
* PerceptionState stores what sensors report. It never interprets: it does
  not decide whether a face is "known", whether an emotion is stable, or
  whether a sensor is trustworthy - those are decision-layer concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from .value_quality import SensorValue, ValueQuality


@dataclass
class PerceptionState:
    """Current perception facts. Only current state - never history.

    Attributes:
        face_present: whether a face is currently detected.
        visible_faces: how many faces are currently visible.
        face_position: normalised (x, y) position of the primary face.
        detector_confidence: confidence of the current face detection.
        detected_emotion: emotion label currently detected on the face.
        emotion_confidence: confidence of the emotion detection.
        speech_detected: whether speech is currently detected in the audio.
        motion_detected: whether motion is currently detected.
        camera_available: whether the camera input is available.
        microphone_available: whether the microphone input is available.
    """

    face_present: SensorValue[bool] = field(default_factory=SensorValue.unknown)
    visible_faces: SensorValue[int] = field(default_factory=SensorValue.unknown)
    face_position: SensorValue[Tuple[float, float]] = field(default_factory=SensorValue.unknown)
    detector_confidence: SensorValue[float] = field(default_factory=SensorValue.unknown)
    detected_emotion: SensorValue[str] = field(default_factory=SensorValue.unknown)
    emotion_confidence: SensorValue[float] = field(default_factory=SensorValue.unknown)
    speech_detected: SensorValue[bool] = field(default_factory=SensorValue.unknown)
    motion_detected: SensorValue[bool] = field(default_factory=SensorValue.unknown)
    camera_available: bool = False
    microphone_available: bool = False

    # ------------------------------------------------------------------
    # Update methods - callers report facts; this state only stores them.
    # ------------------------------------------------------------------

    def update_face(
        self,
        face_present: bool,
        position: Optional[Tuple[float, float]],
        confidence: float,
    ) -> None:
        """Record the current face-detection facts.

        Args:
            face_present: whether a face is currently detected.
            position: normalised (x, y) position, or ``None`` when no face
                is present (the field then reads UNAVAILABLE).
            confidence: detection confidence in [0, 1].
        """
        # NOTE: detector_confidence is stored as VALID even when no face is
        # present - the detector did report a confidence for its "no face"
        # result. Consumers should read face_present first and only use
        # confidence as face-related evidence when face_present is True.
        self.face_present = SensorValue.valid(face_present)
        self.detector_confidence = SensorValue.valid(confidence)
        if position is None:
            self.face_position = SensorValue.unavailable()
        else:
            self.face_position = SensorValue.valid(position)

    def update_face_count(self, visible_faces: int) -> None:
        """Record how many faces are currently visible."""
        self.visible_faces = SensorValue.valid(visible_faces)

    def update_emotion(self, emotion: str, confidence: float) -> None:
        """Record the currently-detected emotion label and confidence."""
        self.detected_emotion = SensorValue.valid(emotion)
        self.emotion_confidence = SensorValue.valid(confidence)

    def update_speech(self, detected: bool) -> None:
        """Record whether speech is currently detected."""
        self.speech_detected = SensorValue.valid(detected)

    def update_motion(self, detected: bool) -> None:
        """Record whether motion is currently detected."""
        self.motion_detected = SensorValue.valid(detected)

    def set_camera_available(self, available: bool) -> None:
        """Record whether the camera input is available."""
        self.camera_available = available
        if not available:
            self._mark_camera_derived_unavailable()

    def set_microphone_available(self, available: bool) -> None:
        """Record whether the microphone input is available."""
        self.microphone_available = available
        if not available:
            self._mark_microphone_derived_unavailable()

    def _mark_camera_derived_unavailable(self) -> None:
        """Mark all camera-derived fields as SENSOR_UNAVAILABLE.

        A reporting convenience (not a decision): when the camera is gone,
        face/emotion fields cannot be measured and should never read as
        UNKNOWN (they would look "not yet measured" instead of "impossible").
        """
        self.face_present = SensorValue.sensor_unavailable()
        self.visible_faces = SensorValue.sensor_unavailable()
        self.face_position = SensorValue.sensor_unavailable()
        self.detector_confidence = SensorValue.sensor_unavailable()
        self.detected_emotion = SensorValue.sensor_unavailable()
        self.emotion_confidence = SensorValue.sensor_unavailable()

    def _mark_microphone_derived_unavailable(self) -> None:
        """Mark all microphone-derived fields as SENSOR_UNAVAILABLE."""
        self.speech_detected = SensorValue.sensor_unavailable()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Restore the default (all-unknown, sensors unavailable) state."""
        self.face_present = SensorValue.unknown()
        self.visible_faces = SensorValue.unknown()
        self.face_position = SensorValue.unknown()
        self.detector_confidence = SensorValue.unknown()
        self.detected_emotion = SensorValue.unknown()
        self.emotion_confidence = SensorValue.unknown()
        self.speech_detected = SensorValue.unknown()
        self.motion_detected = SensorValue.unknown()
        self.camera_available = False
        self.microphone_available = False


__all__ = ["PerceptionState"]
