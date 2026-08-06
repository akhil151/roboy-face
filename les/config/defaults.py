"""
Configuration contracts for the Living Expression System.

Defines the typed configuration surface LES subsystems will read at
runtime. The values below are ARCHITECTURAL DEFAULTS ONLY - they are not
consumed by any behaviour yet and are expected to be tuned during LES
Phase 1 (behaviour implementation phase).

This module mirrors the composition style of
``eyes.engine.config.EngineConfig``: one root config object composed of
smaller frozen dataclasses. It contains data shapes only - no logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DirectorConfig:
    """Tuning surface for the emotion / behaviour directors."""

    tick_hz: float = 30.0
    # TODO(LES-Phase-1): tune the decision cadence. Directors should not run
    # every frame - one decision per tick is enough for believable behaviour.
    intent_hysteresis_ms: float = 400.0
    # TODO(LES-Phase-1): minimum time an emotion intent must persist before it
    # may change the active behaviour (prevents flicker / emotional churn).


@dataclass(frozen=True)
class TimelineConfig:
    """Tuning surface for the behaviour timeline."""

    capacity: int = 128
    # TODO(LES-Phase-1): cap on queued TimelineEvents before dropping the
    # lowest-priority pending event.
    max_horizon_ms: float = 60_000.0
    # TODO(LES-Phase-1): furthest-future event the timeline will accept.


@dataclass(frozen=True)
class BehaviorConfig:
    """Tuning surface shared by behaviour modules."""

    default_cooldown_ms: float = 1500.0
    # TODO(LES-Phase-1): once each behaviour gains real evaluation rules, its
    # per-behaviour cooldowns should be declared here.


@dataclass(frozen=True)
class LESConfig:
    """Root LES configuration - composed of subsystem configs."""

    director: DirectorConfig = field(default_factory=DirectorConfig)
    timeline: TimelineConfig = field(default_factory=TimelineConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)


__all__ = ["DirectorConfig", "TimelineConfig", "BehaviorConfig", "LESConfig"]
