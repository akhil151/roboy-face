"""
LES transitions package.

Owns HOW the robot moves between emotional states (the TransitionDirector).
Interfaces only - the engine performs the actual blending.
"""

from __future__ import annotations

from .transition_director import TransitionDirector, TransitionSpec

__all__ = ["TransitionDirector", "TransitionSpec"]
