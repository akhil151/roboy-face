"""
LES personality package.

Defines the stable LES-level personality model:

    * traits.py   - the six LES personality axes (data shape).
    * profiles.py - named profiles + a provider protocol.

Interfaces only. The deterministic mapping of LES traits onto the engine's
six-axis personality system (eyes.engine.personality.PersonalityProfile)
is LES Phase 1 work.
"""

from __future__ import annotations

from .traits import PersonalityTraits
from .profiles import PersonalityProfile, PersonalityProvider

__all__ = ["PersonalityTraits", "PersonalityProfile", "PersonalityProvider"]
