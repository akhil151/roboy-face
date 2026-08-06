"""
Attention facts for the LES World State.

Represents the CURRENT attention situation: where the robot is looking, what
it is attending to, whether eye contact exists, and the state of face/body
tracking.

This is a pure fact holder - it stores ONLY the current attention state and
never makes decisions about what the robot should attend to.

Design notes
------------
* ``primary_attention_target`` is what the robot is currently attending to
  (the "who/what", e.g. the primary face); ``gaze_position`` is where the
  robot's eyes are pointing. They can differ (looking at a hand, then the
  face).
* Positions are normalised ``(x, y)`` tuples in [0, 1] per axis.
* ``tracking_active`` and ``tracking_lost`` are separate facts: a tracker
  can be active but lost (searching), or inactive and not lost (idle).

Extension notes (LES-Phase-1+)
------------------------------
* Attention history / persistence deliberately do NOT live here - they
  belong to Behavior Memory (``les.memory``). This state holds only the
  current instant.

Architecture notes
------------------
* This module is one of three World State sub-states composed by the
  ``WorldState`` facade. It holds the robot-side attention facts; the
  person-side facts (faces, emotion) live in ``PerceptionState``.

Responsibility notes
--------------------
* AttentionState stores what the attention/tracking layer reports. It
  never chooses what to attend to, never decides when to switch, and never
  holds attention over time - those are decision-layer / memory concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from .value_quality import SensorValue


@dataclass
class AttentionState:
    """Current attention facts. Only current state - never history.

    Attributes:
        primary_attention_target: what the robot currently attends to.
        gaze_position: where the robot's gaze currently points.
        eye_contact: whether mutual eye contact currently exists.
        tracking_active: whether the tracker is currently running.
        tracking_lost: whether tracking is currently considered lost.
    """

    primary_attention_target: SensorValue[Tuple[float, float]] = field(default_factory=SensorValue.unknown)
    gaze_position: SensorValue[Tuple[float, float]] = field(default_factory=SensorValue.unknown)
    eye_contact: SensorValue[bool] = field(default_factory=SensorValue.unknown)
    tracking_active: SensorValue[bool] = field(default_factory=SensorValue.unknown)
    tracking_lost: SensorValue[bool] = field(default_factory=SensorValue.unknown)

    # ------------------------------------------------------------------
    # Update methods - callers report facts; this state only stores them.
    # ------------------------------------------------------------------

    def update_attention_target(self, target: Optional[Tuple[float, float]]) -> None:
        """Record the current primary attention target.

        ``None`` releases attention (the field reads UNAVAILABLE).
        """
        if target is None:
            self.primary_attention_target = SensorValue.unavailable()
        else:
            self.primary_attention_target = SensorValue.valid(target)

    def update_gaze_position(self, position: Optional[Tuple[float, float]]) -> None:
        """Record where the robot's gaze currently points."""
        if position is None:
            self.gaze_position = SensorValue.unavailable()
        else:
            self.gaze_position = SensorValue.valid(position)

    def update_eye_contact(self, exists: bool) -> None:
        """Record whether mutual eye contact currently exists."""
        self.eye_contact = SensorValue.valid(exists)

    def update_tracking(self, active: bool, lost: bool) -> None:
        """Record the current tracking facts.

        Args:
            active: whether the tracker is currently running.
            lost: whether tracking is currently considered lost.
        """
        self.tracking_active = SensorValue.valid(active)
        self.tracking_lost = SensorValue.valid(lost)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Restore the default (all-unknown) attention state."""
        self.primary_attention_target = SensorValue.unknown()
        self.gaze_position = SensorValue.unknown()
        self.eye_contact = SensorValue.unknown()
        self.tracking_active = SensorValue.unknown()
        self.tracking_lost = SensorValue.unknown()


__all__ = ["AttentionState"]
