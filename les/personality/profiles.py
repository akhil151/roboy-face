"""
Personality profile contracts.

A ``PersonalityProfile`` pairs a name / description with a set of
``PersonalityTraits``. In Phase 1, profiles will gain a deterministic
mapping onto the engine's ``PersonalityProfile`` so behaviors can adapt
their timing and amplitude to the robot's personality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .traits import PersonalityTraits


@dataclass(frozen=True)
class PersonalityProfile:
    """A named, reusable combination of personality traits."""

    name: str
    traits: PersonalityTraits = field(default_factory=PersonalityTraits)
    description: str = ""

    # TODO(LES-Phase-1):
    #   def to_engine_profile(self) -> "eyes.engine.personality.PersonalityProfile":
    #       """Map this LES profile onto the engine's six axes (deterministic)."""
    #       ...


class PersonalityProvider(Protocol):
    """Anything that can supply the current personality profile.

    Future implementations: robot configuration, user-selected profile,
    dynamic mood adaptation.
    """

    def get_profile(self) -> PersonalityProfile:
        ...


__all__ = ["PersonalityProfile", "PersonalityProvider"]
