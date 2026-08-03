"""
Eyes engine package.

Core procedural animation engine for ELO robot eye display.
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

__all__ = [
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
]
