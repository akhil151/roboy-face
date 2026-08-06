"""
Value-quality model for the LES World State.

Every fact stored in World State carries an explicit quality label so
consumers never have to guess what a value means. This module defines the
quality vocabulary and the generic ``SensorValue`` wrapper that pairs a
value with its quality.

Design notes
------------
* Five unambiguous qualities (``ValueQuality``):
    VALID              - a real, current measured/derived value
    UNKNOWN            - never measured this session (factory default)
    UNAVAILABLE        - the source exists but is not reporting right now
    SENSOR_UNAVAILABLE - the sensor itself is unavailable (e.g. no camera)
    INVALID            - measured but rejected / out of range / stale
* ``SensorValue`` is frozen and generic - it can wrap any payload type
  (bool, float, position tuple, label string, ...).

Architecture notes
------------------
* This module is the shared "state quality" vocabulary used by every
  World State sub-state and by the ``WorldState`` facade.

Responsibility notes
--------------------
* World State ONLY labels and stores quality; it never decides which
  quality applies. Callers (perception layers) report quality explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class ValueQuality(Enum):
    """Unambiguous quality label for one stored fact."""

    VALID = "valid"
    UNKNOWN = "unknown"
    UNAVAILABLE = "unavailable"
    SENSOR_UNAVAILABLE = "sensor_unavailable"
    INVALID = "invalid"


@dataclass(frozen=True)
class SensorValue(Generic[T]):
    """One current fact paired with its quality.

    Attributes:
        value: the payload, or ``None`` when no value is carried.
        quality: how the value must be interpreted (never ambiguous).
    """

    value: Optional[T] = None
    quality: ValueQuality = ValueQuality.UNKNOWN

    @classmethod
    def valid(cls, value: T) -> "SensorValue[T]":
        """A real, current value."""
        return cls(value=value, quality=ValueQuality.VALID)

    @classmethod
    def unknown(cls) -> "SensorValue[T]":
        """No information yet (factory default for every field)."""
        return cls(value=None, quality=ValueQuality.UNKNOWN)

    @classmethod
    def unavailable(cls) -> "SensorValue[T]":
        """Source exists but is not reporting (e.g. no face visible)."""
        return cls(value=None, quality=ValueQuality.UNAVAILABLE)

    @classmethod
    def sensor_unavailable(cls) -> "SensorValue[T]":
        """The sensor itself is unavailable (e.g. no camera connected)."""
        return cls(value=None, quality=ValueQuality.SENSOR_UNAVAILABLE)

    @classmethod
    def invalid(cls, value: Optional[T] = None) -> "SensorValue[T]":
        """Measured but rejected / out of range / stale."""
        return cls(value=value, quality=ValueQuality.INVALID)

    @property
    def is_valid(self) -> bool:
        """True when this fact is a real, current value."""
        return self.quality is ValueQuality.VALID

    @property
    def is_known(self) -> bool:
        """True when a value is present (valid or invalid - not empty)."""
        return self.quality in (ValueQuality.VALID, ValueQuality.INVALID)


__all__ = ["ValueQuality", "SensorValue"]
