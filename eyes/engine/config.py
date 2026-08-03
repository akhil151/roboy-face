"""
Global configuration constants for the eye animation engine.

Contains resolution, eye layout, timing, and physics tuning parameters.
All values are centralized for easy tuning during development and Phase 2 animation work.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DisplayConfig:
    width: int = 800
    height: int = 480
    fps: int = 60
    background_color: tuple[int, int, int] = (0, 0, 0)
    eye_color: tuple[int, int, int] = (255, 255, 255)
    iris_color: tuple[int, int, int] = (20, 20, 20)
    lid_color: tuple[int, int, int] = (0, 0, 0)
    highlight_color: tuple[int, int, int] = (255, 255, 255)
    title: str = "ELO Eyes"


@dataclass(frozen=True)
class EyeLayoutConfig:
    center_y: float = 240.0
    eye_radius: float = 90.0
    eye_spacing: float = 280.0
    iris_radius_ratio: float = 0.42
    highlight_radius_ratio: float = 0.12
    highlight_offset_ratio: float = 0.25
    look_max_offset: float = 35.0


@dataclass(frozen=True)
class TimingConfig:
    state_transition_ms: float = 350.0
    blink_interval_min_ms: float = 3000.0
    blink_interval_max_ms: float = 5000.0
    blink_duration_ms: float = 180.0
    double_blink_gap_ms: float = 120.0
    slow_blink_multiplier: float = 2.5
    half_blink_ratio: float = 0.5
    double_blink_chance: float = 0.12
    slow_blink_chance: float = 0.05
    half_blink_chance: float = 0.08
    state_cycle_demo_seconds: float = 3.0


@dataclass(frozen=True)
class MicroMotionConfig:
    amplitude: float = 2.0
    breathe_amplitude: float = 1.0
    sway_amplitude: float = 1.5
    drift_amplitude: float = 1.2
    breathe_period_seconds: float = 5.0
    sway_period_seconds: float = 7.3
    drift_period_seconds: float = 11.0
    phase_offset: float = 0.0


@dataclass
class EngineConfig:
    display: DisplayConfig = field(default_factory=DisplayConfig)
    layout: EyeLayoutConfig = field(default_factory=EyeLayoutConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    micro_motion: MicroMotionConfig = field(default_factory=MicroMotionConfig)
