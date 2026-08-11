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


@dataclass(frozen=True)
class OverlayConfig:
    """Configuration for procedural overlay cues (LES-09B.2 + LES-09B.4).

    LES-09B.2 moved the cue magic numbers into configuration so the
    choreography layer can influence overlay appearance without touching
    the renderer. LES-09B.4 fixed the SPATIAL PLACEMENT: both cues are now
    anchored in FACE SPACE (derived from the actual eye layout geometry),
    never in the moving eye's local frame, and both guarantee a
    configurable clearance margin from the eye silhouettes.

    LES-09B.5 changed ONLY the thinking "?" PLACEMENT (its scale is
    untouched): the cue is no longer centred above the face but anchored
    to an eye's OUTER PERIMETER corner (``thinking_cue_eye`` +
    ``thinking_cue_perimeter``) - it grows from the eye corner through a
    small configurable clearance, exactly hugging the silhouette and
    following every gaze movement. The sleepy ZZZ is completely
    untouched by LES-09B.5.

    Eye-geometry facts this config is derived from (eyes/engine/config.py
    ``EyeLayoutConfig`` + eyes/engine/renderer.py ``_effective_radius``):
        * eye_radius = 75 px  ->  rendered eye height = 2 * 75 = 150 px.
        * look_max_offset = 35 px is the maximum gaze displacement.
        * The rendered eye centre is pos + look + micro + bounce offsets.

    Thinking "?" attributes (LES-09B.5 perimeter anchor):
        thinking_cue_scale_ratio: the "?" scale = ratio * eye_radius, so
            the size is DERIVED from the actual eye geometry, never a
            hard-coded pixel value. UNCHANGED from LES-09B.4 (0.85) - the
            human-approved size. The glyph's visual height is ~1.16x its
            scale, so ratio 0.85 -> scale 63.75 px -> glyph ~74 px vs the
            ~150 px eye height: approximately HALF the eye size, and
            visually subordinate to the eyes.
        thinking_cue_eye: which eye's OUTER PERIMETER the cue is anchored
            to - "right" (default, the human-approved direction matching
            the "?"-grows-from-the-eye-corner sketch) or "left".
        thinking_cue_perimeter: which corner of that eye's rendered
            silhouette the cue originates from - "outer_top" (default:
            the eye's outer top corner) or "outer_bottom".
        thinking_cue_clearance_ratio: the small configurable gap between
            the cue's bounding box and the eye silhouette corner, as a
            fraction of eye radius. The anchor is recomputed every frame
            from the ACTUAL composed pose, so the cue HUGS the selected
            eye's outer corner at exactly this margin, follows every
            gaze/look movement, and can never overlap the silhouette
            (configurable - not a hidden magic number).
        thinking_orbital_amplitude_x/y: orbital drift around the anchor
            (px). Kept smaller than the clearance so the drifting glyph
            can never approach the eyes.
        thinking_cue_lifetime_ms: how long the ? remains visible per
            cycle (ms); 0 = persistent while state == thinking.
        thinking_cue_fade_in_ms / fade_out_ms: fade durations (ms).

    Sleepy ZZZ attributes:
        sleepy_cue_scale_base: base Z scale. UNCHANGED from LES-09B.2
            (16.0) - the ZZZ was already readable; only its placement was
            wrong, so it must not be enlarged.
        sleepy_cue_x_min_ratio / x_max_ratio: the Z spawn band, in eye
            radii, offset RIGHT of the right eye's rest centre in face
            space. The band never follows gaze and clears the right eye's
            FULL worst-case excursion: rest radius + max look offset (35)
            + max bounce offset (26, the eye.py clamp) + max micro offset
            + worst rotation inflation (safe_region.max_rotation) + the
            glyph's stroke-extended half-width + a margin.
        sleepy_cue_y_min_ratio / y_max_ratio: the Z spawn band, in eye
            radii, offset ABOVE the right eye's rest centre (screen y
            grows downward, so "above" subtracts). Clears the same
            worst-case excursion upward (look up + bounce up + rotation
            inflation + glyph half-height). Together the band sits in the
            free space up-and-right of the face.
        sleepy_cue_min_lifetime_s / max_lifetime_s: Z particle lifetime.
    """

    # --- Thinking "?" (LES-09B.5 perimeter anchor; scale UNCHANGED) ---
    thinking_cue_scale_ratio: float = 0.85   # UNCHANGED (human-approved size)
    thinking_cue_eye: str = "right"          # which eye's outer perimeter the cue grows from
    thinking_cue_perimeter: str = "outer_top"  # silhouette corner the cue originates from
    thinking_cue_clearance_ratio: float = 0.4   # small configurable gap from the eye perimeter
    thinking_orbital_amplitude_x: float = 5.0
    thinking_orbital_amplitude_y: float = 3.0
    thinking_cue_lifetime_ms: float = 0.0  # 0 = persistent
    thinking_cue_fade_in_ms: float = 400.0
    thinking_cue_fade_out_ms: float = 500.0

    # --- Sleepy ZZZ (LES-09B.4 spatial fix; scale preserved) ---
    sleepy_cue_scale_base: float = 16.0
    sleepy_cue_min_lifetime_s: float = 2.0
    sleepy_cue_max_lifetime_s: float = 3.0
    sleepy_cue_x_min_ratio: float = 2.40
    sleepy_cue_x_max_ratio: float = 2.85
    sleepy_cue_y_min_ratio: float = 2.40
    sleepy_cue_y_max_ratio: float = 2.70


@dataclass
class EngineConfig:
    display: DisplayConfig = field(default_factory=DisplayConfig)
    layout: EyeLayoutConfig = field(default_factory=EyeLayoutConfig)
    safe_region: SafeRegionConfig = field(default_factory=SafeRegionConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    micro_motion: MicroMotionConfig = field(default_factory=MicroMotionConfig)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)

