"""
Eyes engine package.

Core procedural animation engine for ELO robot eye display.

Phase 2 expressive motion modules (new):
  * motion_primitives - 18 reusable motion primitives
  * animation_clips   - Enter/Loop/Exit cinematic clip system
  * motion_curves     - Per-property cinematic motion metadata
  * personality       - 6-axis expressive personality model
  * micro_behaviours  - 7-layer always-on autonomous motion
  * emotion_blending  - Cinematic emotion state blender
"""

from .config import EngineConfig, DisplayConfig, EyeLayoutConfig, TimingConfig, MicroMotionConfig
from .eye import EyeParams, blend_params
from .eye_pair import EyePair, blend_eye_pair
from .easing import EasingFunction, EASING_MAP, get_easing, lerp, lerp_clamped, clamp01
from .tween import Tween, TweenEngine
from .spring import SpringConfig, Spring1D, Spring2D
from .blink_controller import BlinkController, BlinkType
from .look_controller import LookController
from .micro_motion import MicroMotion

from . import motion_primitives
from . import animation_clips
from . import motion_curves
from . import personality
from . import micro_behaviours
from . import emotion_blending

from .motion_primitives import (
    BreathingConfig,
    BounceConfig,
    OvershootConfig,
    SettleConfig,
    DriftConfig,
    PulseConfig,
    SquashConfig,
    StretchConfig,
    LookScanConfig,
    IdleNoiseConfig,
    MicroCorrectionConfig,
    BlinkMotionConfig,
    AttentionShiftConfig,
    EmotionMorphConfig,
    SettledValue,
    SettledPair,
    LookScanPrimitive,
    IdleNoisePrimitive,
    IdleNoisePair,
    MicroCorrectionPrimitive,
    AttentionShiftPrimitive,
    apply_breathing,
    apply_bounce,
    apply_drift,
    apply_pulse,
    apply_squash,
    apply_stretch,
    apply_blink_compression,
    apply_breathing_pair,
    apply_bounce_pair,
    apply_drift_pair,
    apply_pulse_pair,
    apply_squash_pair,
    apply_stretch_pair,
    apply_blink_compression_pair,
    apply_emotion_morph,
    apply_emotion_morph_pair,
    overshoot_envelope,
    morph_param,
)
from .animation_clips import (
    PrimitiveInvocation,
    AnimationClip,
    ClipPlayer,
    StateClips,
    StateClipPlayer,
    make_basic_enter_clip,
    make_basic_exit_clip,
    make_breathing_loop_clip,
    make_pulse_loop_clip,
)
from .motion_curves import (
    PropertyCurve,
    PROPERTY_CURVES,
    get_curve,
    curve_names_by_priority,
    cinematic_delta,
    group_property_names,
)
from .personality import (
    PersonalityProfile,
    DerivedTiming,
    DerivedAmplitudes,
    PersonalityAdaptor,
    PersonalityBundle,
)
from .micro_behaviours import (
    MicroBehaviourConfig,
    MicroBehaviourSystem,
)
from .emotion_blending import (
    DEFAULT_BLEND_MS,
    MIN_BLEND_MS,
    MAX_BLEND_MS,
    EmotionLayer,
    CinematicBlender,
    EmotionLayerCompositor,
    clamp_duration,
    suggest_blend_duration,
)

__all__ = [
    # Core Phase 1
    "EngineConfig",
    "DisplayConfig",
    "EyeLayoutConfig",
    "TimingConfig",
    "MicroMotionConfig",
    "EyeParams",
    "EyePair",
    "blend_params",
    "blend_eye_pair",
    "EasingFunction",
    "EASING_MAP",
    "get_easing",
    "lerp",
    "lerp_clamped",
    "clamp01",
    "Tween",
    "TweenEngine",
    "SpringConfig",
    "Spring1D",
    "Spring2D",
    "BlinkController",
    "BlinkType",
    "LookController",
    "MicroMotion",
    # Module references
    "motion_primitives",
    "animation_clips",
    "motion_curves",
    "personality",
    "micro_behaviours",
    "emotion_blending",
    # Motion primitives - configs
    "BreathingConfig",
    "BounceConfig",
    "OvershootConfig",
    "SettleConfig",
    "DriftConfig",
    "PulseConfig",
    "SquashConfig",
    "StretchConfig",
    "LookScanConfig",
    "IdleNoiseConfig",
    "MicroCorrectionConfig",
    "BlinkMotionConfig",
    "AttentionShiftConfig",
    "EmotionMorphConfig",
    # Motion primitives - stateful
    "SettledValue",
    "SettledPair",
    "LookScanPrimitive",
    "IdleNoisePrimitive",
    "IdleNoisePair",
    "MicroCorrectionPrimitive",
    "AttentionShiftPrimitive",
    # Motion primitives - single eye
    "apply_breathing",
    "apply_bounce",
    "apply_drift",
    "apply_pulse",
    "apply_squash",
    "apply_stretch",
    "apply_blink_compression",
    "overshoot_envelope",
    "morph_param",
    "apply_emotion_morph",
    # Motion primitives - pair
    "apply_breathing_pair",
    "apply_bounce_pair",
    "apply_drift_pair",
    "apply_pulse_pair",
    "apply_squash_pair",
    "apply_stretch_pair",
    "apply_blink_compression_pair",
    "apply_emotion_morph_pair",
    # Animation clips
    "PrimitiveInvocation",
    "AnimationClip",
    "ClipPlayer",
    "StateClips",
    "StateClipPlayer",
    "make_basic_enter_clip",
    "make_basic_exit_clip",
    "make_breathing_loop_clip",
    "make_pulse_loop_clip",
    # Motion curves
    "PropertyCurve",
    "PROPERTY_CURVES",
    "get_curve",
    "curve_names_by_priority",
    "cinematic_delta",
    "group_property_names",
    # Personality model
    "PersonalityProfile",
    "DerivedTiming",
    "DerivedAmplitudes",
    "PersonalityAdaptor",
    "PersonalityBundle",
    # Micro-behaviours
    "MicroBehaviourConfig",
    "MicroBehaviourSystem",
    # Emotion blending
    "DEFAULT_BLEND_MS",
    "MIN_BLEND_MS",
    "MAX_BLEND_MS",
    "EmotionLayer",
    "CinematicBlender",
    "EmotionLayerCompositor",
    "clamp_duration",
    "suggest_blend_duration",
]
