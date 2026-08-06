"""
LES configuration package.

Exposes the typed configuration contracts defined in ``defaults.py``.
Values are architectural defaults only - they are not consumed by any
behaviour yet and will be tuned during LES Phase 1.
"""

from __future__ import annotations

from .defaults import BehaviorConfig, DirectorConfig, LESConfig, TimelineConfig

__all__ = ["DirectorConfig", "TimelineConfig", "BehaviorConfig", "LESConfig"]
