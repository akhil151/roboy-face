"""
Personality trait contracts.

LES-level personality traits are the stable characteristics that shape
behavior selection and timing. They are DISTINCT from - but mapped onto -
the engine's six-axis ``PersonalityProfile`` in ``eyes.engine.personality``
(energy, warmth, attention, calmness, amplitude, blink_tendency).

Planned LES trait -> engine axis mapping (Phase 1, not yet implemented):

    LES trait          engine axis (approx.)
    ----------------   ---------------------------------
    curiosity          attention (+ look scan frequency)
    sociability        warmth (+ blink tendency)
    energy             energy
    expressiveness     amplitude (+ blink tendency)
    calmness           calmness
    focus              attention

This module defines only the data shape - the mapping itself is a Phase 1
responsibility (see TODO below).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonalityTraits:
    """Stable LES personality axes. All values in [0, 1]; 0.5 = neutral."""

    curiosity: float = 0.5
    sociability: float = 0.5
    energy: float = 0.5
    expressiveness: float = 0.5
    calmness: float = 0.5
    focus: float = 0.5

    # TODO(LES-Phase-1): add a deterministic mapping method, e.g.
    #   def to_engine_profile(self) -> "eyes.engine.personality.PersonalityProfile":
    #       ...  # map LES axes onto energy/warmth/attention/calmness/
    #            # amplitude/blink_tendency


__all__ = ["PersonalityTraits"]
