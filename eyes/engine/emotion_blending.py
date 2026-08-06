"""
Emotion blending system - smooth cinematic transitions between emotional states.

Blends EVERY animatable parameter (22 properties per eye x 2 eyes = 44 channels)
across state transitions, with per-property-group easing curves (from motion_curves)
and a default 350-500ms cinematic blend duration.

Design notes:
  * The existing AnimationMixer already provides top-level state transitions via
    _ActiveTransition.  This module enhances that pipeline by providing:
      - Per-property cinematic_delta curves with anticipation/overshoot
      - A reusable Blender class that works on arbitrary EyePair snapshots
      - Utilities for cross-blending N-way emotion "layers" (e.g. base emotion
        + 20% caring + 10% surprise = blended output)
  * Default transition length: 400ms (within the requested 350-500ms range).
  * Transitions NEVER jump.  Even under interrupt / re-trigger, the blender
    starts from the CURRENT output value rather than the original "from" snapshot,
    so the path through parameter space is always C0 continuous.

Phase 2B states will NOT need to use this module directly - it's wired into the
ExpressiveAnimation base class (provided separately) which integrates with the
existing StateMachine / AnimationMixer architecture.  They will simply call
``set_state("happy")`` with an optional duration override.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .eye import EyeParams
from .eye_pair import EyePair
from .easing import EasingFunction, ease_in_out_cubic, ease_out_cubic, clamp01, lerp
from .motion_curves import PROPERTY_CURVES, get_curve, cinematic_delta
from .motion_primitives import EmotionMorphConfig, apply_emotion_morph_pair


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


DEFAULT_BLEND_MS: float = 400.0
MIN_BLEND_MS: float = 40.0
MAX_BLEND_MS: float = 5000.0


# ---------------------------------------------------------------------------
# N-way emotion layer blending
# ---------------------------------------------------------------------------


@dataclass
class EmotionLayer:
    """A single emotion contribution at a given weight.

    ``pose`` is the canonical target pose for this emotion.
    ``weight`` is the contribution weight in [0,1] that this emotion
    contributes to the final blend.
    """
    name: str
    pose: EyePair
    weight: float = 0.0
    # Optional per-layer transition duration override for this layer only.
    blend_ms: Optional[float] = None


# ---------------------------------------------------------------------------
# Cinematic blender
# ---------------------------------------------------------------------------


class CinematicBlender:
    """Performs cinematic blends between EyePair snapshots.

    Unlike a plain linear lerp, CinematicBlender:
      * Uses per-property motion curves from motion_curves with anticipation
        and overshoot.
      * Applies per-group easing via an optional EmotionMorphConfig.
      * Can blend a stack of N emotion layers with a normalized weight sum.
      * Respects a global "cinematic scale" multiplier for anticipation and
        overshoot (states with low calmness will show more cinematic flair).
    """

    def __init__(
        self,
        default_duration_ms: float = DEFAULT_BLEND_MS,
        morph_cfg: Optional[EmotionMorphConfig] = None,
        cinematic_scale: float = 1.0,
    ) -> None:
        self._default_ms = clamp_duration(default_duration_ms)
        self._morph_cfg = morph_cfg or EmotionMorphConfig()
        self._cinematic_scale = clamp01(cinematic_scale)

        # Internal: current FROM and TO snapshots.
        self._from_pose: Optional[EyePair] = None
        self._to_pose: Optional[EyePair] = None
        self._elapsed_ms: float = 0.0
        self._duration_ms: float = self._default_ms
        self._active: bool = False

    # ------------------------------------------------------------------
    @property
    def active(self) -> bool:
        return self._active

    @property
    def progress(self) -> float:
        if not self._active:
            return 1.0
        if self._duration_ms <= 0:
            return 1.0
        return clamp01(self._elapsed_ms / self._duration_ms)

    def set_cinematic_scale(self, scale: float) -> None:
        """Scale anticipation/overshoot globally (0 = vanilla blend, >1 = expressive)."""
        self._cinematic_scale = clamp01(scale)

    def set_default_duration(self, duration_ms: float) -> None:
        self._default_ms = clamp_duration(duration_ms)

    def set_morph_config(self, cfg: EmotionMorphConfig) -> None:
        self._morph_cfg = cfg

    # ------------------------------------------------------------------
    def start(
        self,
        from_pose: EyePair,
        to_pose: EyePair,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Begin a new cinematic blend from a snapshot.

        Even when interrupting a prior blend mid-flight, call start() with
        the *current output* as ``from_pose`` - this guarantees the blend
        path never jumps (C0 continuity)."""
        self._from_pose = from_pose.copy()
        self._to_pose = to_pose.copy()
        self._elapsed_ms = 0.0
        self._duration_ms = clamp_duration(duration_ms or self._default_ms)
        self._active = True

    def update(self, dt_ms: float, dst: EyePair) -> float:
        """Advance the active blend by dt_ms and write the result into dst.

        Returns the current blend progress in [0,1].  If no blend is active,
        dst is left unchanged and 1.0 is returned."""
        if not self._active or self._from_pose is None or self._to_pose is None:
            return 1.0
        self._elapsed_ms += dt_ms
        t_raw = self.progress
        if t_raw >= 1.0:
            # Blend finished - snap to target pose and deactivate.
            dst.copy_from(self._to_pose)
            self._active = False
            return 1.0

        # 1. First pass: apply_emotion_morph_pair handles per-group easing.
        apply_emotion_morph_pair(dst, self._from_pose, self._to_pose, t_raw, self._morph_cfg)

        # 2. Second pass: cinematic per-property delta (anticipation + overshoot)
        #    applied on top of the per-group easing for extra filmic feel.
        cscale = self._cinematic_scale
        self._apply_cinematic_overlay(dst, self._from_pose, self._to_pose, t_raw, cscale)

        return t_raw

    # ------------------------------------------------------------------
    @staticmethod
    def _apply_cinematic_overlay(
        dst: EyePair,
        from_pose: EyePair,
        to_pose: EyePair,
        t_raw: float,
        cinematic_scale: float,
    ) -> None:
        """Per-property cinematic_delta overlay on top of the base blend."""
        for side in ("left", "right"):
            dst_e: EyeParams = getattr(dst, side)
            from_e: EyeParams = getattr(from_pose, side)
            to_e: EyeParams = getattr(to_pose, side)
            for prop_name, curve in PROPERTY_CURVES.items():
                fv = getattr(from_e, prop_name)
                tv = getattr(to_e, prop_name)
                if fv == tv:
                    continue
                blended = cinematic_delta(
                    curve,
                    fv,
                    tv,
                    t_raw,
                    global_anticipation_scale=cinematic_scale,
                    global_overshoot_scale=cinematic_scale,
                )
                # We REPLACE the base blend's value for this property with
                # the cinematic version, since cinematic_delta already includes
                # the base interpolation plus filmic corrections.
                setattr(dst_e, prop_name, blended)


# ---------------------------------------------------------------------------
# N-emotion layer compositor
# ---------------------------------------------------------------------------


class EmotionLayerCompositor:
    """Blend N emotion layers with user-provided weights.

    Useful when an animation state wants to compose multiple "influences"
    (e.g. 70% calm + 20% happy + 10% surprised) instead of picking a single
    state.  Weights are normalized automatically if their sum exceeds 1.0.

    Usage:
        comp = EmotionLayerCompositor()
        comp.set_neutral(neutral_pose)          # optional reference
        comp.set_layer("calm", calm_pose, 0.7)
        comp.set_layer("happy", happy_pose, 0.2)
        comp.update(16.0)                       # advance any internal timers
        comp.blend_into(output_pose)            # weighted sum across all layers.
    """

    def __init__(self) -> None:
        self._layers: Dict[str, EmotionLayer] = {}
        self._neutral_pose: Optional[EyePair] = None

    # ------------------------------------------------------------------
    def set_neutral(self, pose: EyePair) -> None:
        """Store a reference neutral pose used to fill partial-weight blends.

        Convenience method so callers can pass a neutral pose once and have
        blend_into() automatically use it instead of passing it each call.
        """
        self._neutral_pose = pose

    def update(self, dt_ms: float) -> None:  # noqa: ARG002
        """Advance any internal layer timers by dt_ms.

        Currently a no-op since layers hold static weights.  Provided as a
        forward-compatible slot so code that calls update() each frame will
        not need modification if per-layer animation is added later.
        """
        # Forward-compatible slot: no per-frame layer animation yet.

    def set_layer(
        self,
        name: str,
        pose: EyePair,
        weight: float,
        blend_ms: Optional[float] = None,
    ) -> None:
        weight = max(0.0, weight)
        if name in self._layers:
            layer = self._layers[name]
            layer.pose.copy_from(pose)
            layer.weight = weight
            layer.blend_ms = blend_ms
        else:
            self._layers[name] = EmotionLayer(
                name=name, pose=pose.copy(), weight=weight, blend_ms=blend_ms
            )

    def remove_layer(self, name: str) -> None:
        self._layers.pop(name, None)

    def clear(self) -> None:
        self._layers.clear()

    @property
    def layer_names(self) -> list[str]:
        return sorted(self._layers.keys())

    def weight_sum(self) -> float:
        return sum(l.weight for l in self._layers.values())

    # ------------------------------------------------------------------
    def blend_into(self, dst: EyePair, neutral_pose: Optional[EyePair] = None) -> float:
        """Weighted-blend all layers into dst.  Returns the total weight used.

        If no layers exist or weights sum to 0, dst is left untouched and 0.0
        is returned.  If a ``neutral_pose`` is provided and weights sum to < 1,
        the remainder is filled by the neutral pose (useful for partial layer
        coverage)."""
        # Fall back to the stored neutral (set_neutral) when none is passed.
        neutral_pose = neutral_pose or self._neutral_pose
        if not self._layers:
            return 0.0
        total = self.weight_sum()
        if total <= 0.0:
            return 0.0

        # Mathematically correct weighted blend: every layer contributes in
        # proportion to its configured weight.  (Previously the first layer
        # was seeded at full influence and the rest accumulated via repeated
        # lerp, so configured weights were not honored.)
        active = [(l.pose, l.weight) for l in self._layers.values() if l.weight > 0.0]
        if not active:
            return 0.0

        # Running weighted average: dst = sum(w_i * pose_i) / sum(w_i).
        # With each step t = w_i / (accum_w + w_i), dst.lerp_into maintains
        # the exact weighted mean, deterministically in layer order.
        first_pose, first_w = active[0]
        dst.copy_from(first_pose)
        accum_w = first_w
        for pose, w in active[1:]:
            if w <= 0.0:
                continue
            dst.lerp_into(dst, pose, w / (accum_w + w))
            accum_w += w

        if total > 1.0:
            # Weights normalized automatically: the accumulator already
            # produced the convex combination of the layers.
            pass
        elif neutral_pose is not None:
            # Weights sum to < 1: fill the remainder with the neutral pose so
            # the blend is a full convex combination.
            dst.lerp_into(neutral_pose, dst, total)
        # else: partial-weight layer blend used as-is (no neutral available).

        return min(1.0, total)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def clamp_duration(ms: float) -> float:
    if ms < MIN_BLEND_MS:
        return MIN_BLEND_MS
    if ms > MAX_BLEND_MS:
        return MAX_BLEND_MS
    return ms


def suggest_blend_duration(
    energy: float = 0.5,
    calmness: float = 0.5,
    magnitude: float = 0.5,
) -> float:
    """Suggest a cinematic blend duration given personality/state parameters.

    High-energy, low-calmness states get snappier (shorter) blends;
    low-energy, high-calmness states get gentler (longer) blends.
    Magnitude reflects the size of the parameter delta - bigger jumps
    warrant slightly longer blends so the viewer can follow.
    """
    e = clamp01(energy)
    c = clamp01(calmness)
    m = clamp01(magnitude)
    # Base 350-500 range.
    base = lerp(500.0, 350.0, 0.5)  # 425 midpoint
    # Energy pulls toward shorter (down to 280 at e=1).
    base -= e * 160.0
    # Calmness pulls toward longer (up to 540 at c=1).
    base += c * 120.0
    # Magnitude adds a little for bigger jumps.
    base += m * 80.0
    return clamp_duration(base)


# ---------------------------------------------------------------------------
# Emotion Transition Policy & Emotional Memory
# ---------------------------------------------------------------------------


class EmotionTransitionPolicy:
    """Defines preferred transition paths and emotional memory decay between states.

    Prevents abrupt emotional jumps by providing:
      * Adjacency check & optimal transition durations.
      * Intermediate routing for distant emotional states (e.g. sad -> calm via caring).
      * Emotional memory residual calculation for smooth cross-state decay.
    """

    # Preferred direct adjacent transitions and custom blend durations (ms).
    PREFERRED_TRANSITIONS: Dict[Tuple[str, str], float] = {
        ("calm", "listening"): 300.0,
        ("listening", "thinking"): 350.0,
        ("thinking", "speaking"): 280.0,
        ("speaking", "happy"): 320.0,
        ("happy", "caring"): 400.0,
        ("caring", "calm"): 420.0,
        ("surprised", "happy"): 300.0,
        ("focus", "speaking"): 250.0,
        ("calm", "focus"): 280.0,
        ("listening", "focus"): 260.0,
        ("happy", "calm"): 380.0,
        ("surprised", "calm"): 350.0,
        ("sad", "caring"): 450.0,
        ("sleepy", "calm"): 500.0,
    }

    # Recommended intermediate routing for non-adjacent transitions.
    ROUTED_TRANSITIONS: Dict[Tuple[str, str], list[str]] = {
        ("sad", "calm"): ["caring"],
        ("sad", "happy"): ["caring", "calm"],
        ("sleepy", "surprised"): ["calm", "listening"],
        ("sleepy", "speaking"): ["calm", "listening"],
    }

    @classmethod
    def get_transition_duration(cls, from_state: str, to_state: str) -> float:
        """Return the optimal transition duration in ms for a state pair."""
        key = (from_state.lower(), to_state.lower())
        if key in cls.PREFERRED_TRANSITIONS:
            return cls.PREFERRED_TRANSITIONS[key]
        return DEFAULT_BLEND_MS

    @classmethod
    def get_intermediate_path(cls, from_state: str, to_state: str) -> list[str]:
        """Return intermediate states to route through to prevent abrupt jumps."""
        key = (from_state.lower(), to_state.lower())
        return cls.ROUTED_TRANSITIONS.get(key, [])

    @classmethod
    def calculate_emotional_memory_weight(cls, blend_progress: float, residual_amount: float = 0.15) -> float:
        """Calculate the decaying emotional memory residual of the outgoing state.

        t in [0, 1]. At entry start, residual is residual_amount (~15%) and decays
        smoothly to 0 as entry completes, preserving emotional continuity.
        """
        p = clamp01(blend_progress)
        return (1.0 - ease_out_cubic(p)) * residual_amount


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_BLEND_MS",
    "MIN_BLEND_MS",
    "MAX_BLEND_MS",
    "EmotionLayer",
    "CinematicBlender",
    "EmotionLayerCompositor",
    "EmotionTransitionPolicy",
    "clamp_duration",
    "suggest_blend_duration",
]

