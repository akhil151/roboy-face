"""
Interaction facts for the LES World State.

Represents the CURRENT interaction situation: which interaction mode the
robot is in, whether the robot is currently speaking, and whether touch is
active.

This is a pure fact holder - it stores ONLY the current interaction state
and never chooses a mode on its own.

Design notes
------------
* ``InteractionMode`` mirrors the Intent Library of the Interaction Bible
  v1.0 (Part 6) so World State and the decision layers speak the same
  vocabulary: Greeting, Listening, Responding, Thinking, Searching,
  Waiting, Curious, Playful, Comforting, Alert, Celebrating, Confused,
  Sleep, Wake. ``IDLE`` is the resting default.
* The mode is reported BY the decision layer - World State only stores it.

Architecture notes
------------------
* Session-level status (BOOTING / ACTIVE / ...) lives on the ``WorldState``
  facade (``world_state.py``), not here - it is world-scoped, not
  interaction-scoped.

Extension notes (LES-Phase-1+)
------------------------------
* Additional interaction facts (e.g. who is being addressed, voice-input
  intent, active gesture) can be added as new fields without changing the
  existing update methods.

Responsibility notes
--------------------
* InteractionState stores what the decision layer reports. It never
  chooses a mode, never ends an interaction, and never decides whether the
  robot should speak - it only records those facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .value_quality import SensorValue


class InteractionMode(Enum):
    """The robot's current interaction mode (matches the Intent Library)."""

    IDLE = "idle"
    GREETING = "greeting"
    LISTENING = "listening"
    RESPONDING = "responding"
    THINKING = "thinking"
    SEARCHING = "searching"
    WAITING = "waiting"
    CURIOUS = "curious"
    PLAYFUL = "playful"
    COMFORTING = "comforting"
    ALERT = "alert"
    CELEBRATING = "celebrating"
    CONFUSED = "confused"
    SLEEP = "sleep"
    WAKE = "wake"


@dataclass
class InteractionState:
    """Current interaction facts. Only current state - never history.

    Attributes:
        interaction_mode: the mode the robot is currently in.
        robot_speaking: whether the robot is currently producing speech.
        touch_active: whether a touch is currently active on the robot.
    """

    interaction_mode: InteractionMode = InteractionMode.IDLE
    robot_speaking: SensorValue[bool] = field(default_factory=SensorValue.unknown)
    touch_active: SensorValue[bool] = field(default_factory=SensorValue.unknown)

    # ------------------------------------------------------------------
    # Update methods - callers report facts; this state only stores them.
    # ------------------------------------------------------------------

    def update_interaction_mode(self, mode: InteractionMode) -> None:
        """Record the current interaction mode (reported by the decision layer)."""
        self.interaction_mode = mode

    def update_robot_speaking(self, speaking: bool) -> None:
        """Record whether the robot is currently speaking."""
        self.robot_speaking = SensorValue.valid(speaking)

    def update_touch(self, active: bool) -> None:
        """Record whether a touch is currently active."""
        self.touch_active = SensorValue.valid(active)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Restore the default interaction state (IDLE, unknowns)."""
        self.interaction_mode = InteractionMode.IDLE
        self.robot_speaking = SensorValue.unknown()
        self.touch_active = SensorValue.unknown()


__all__ = ["InteractionMode", "InteractionState"]
