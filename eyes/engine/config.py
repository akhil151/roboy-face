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
    eye_radius: float = 75.0
    eye_spacing: float = 280.0
    iris_radius_ratio: float = 0.42
    highlight_radius_ratio: float = 0.12
    highlight_offset_ratio: float = 0.25
    look_max_offset: float = 35.0


@dataclass(frozen=True)
class SafeRegionConfig:
    margin_ratio: float = 0.025
    min_eye_spacing_ratio: float = 0.22
    max_eye_spacing_ratio: float = 0.48
    min_eye_radius_ratio: float = 0.02
    max_eye_radius_ratio: float = 0.23
    max_look_offset_ratio: float = 0.075
    max_bounce_ratio: float = 0.055
    max_stretch: float = 0.35
    max_squash: float = 0.40
    min_scale: float = 0.10
    max_scale: float = 1.35
    max_rotation: float = 0.35
    soft_damping_factor: float = 0.85


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
    amplitude: float = 0.6
    breathe_amplitude: float = 0.6
    sway_amplitude: float = 0.25
    drift_amplitude: float = 0.18
    breathe_period_seconds: float = 5.4
    sway_period_seconds: float = 9.0
    drift_period_seconds: float = 15.0
    phase_offset: float = 0.0


@dataclass
class EngineConfig:
    display: DisplayConfig = field(default_factory=DisplayConfig)
    layout: EyeLayoutConfig = field(default_factory=EyeLayoutConfig)
    safe_region: SafeRegionConfig = field(default_factory=SafeRegionConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    micro_motion: MicroMotionConfig = field(default_factory=MicroMotionConfig)

