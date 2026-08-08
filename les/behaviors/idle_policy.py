"""
Idle policy for the LES Natural Idle Decision Layer (LES-09A.1).

The policy is the CONFIGURABLE VALUES LAYER of the idle pipeline:

    Idle Context -> Idle Policy -> Idle Behavior -> Idle Decision

It contains only policy VALUES: the idle tiers, the idle action vocabulary,
per-tier timing bands, per-tier action weights, emotion modifiers,
personality influence knobs, cooldown names/durations, and the
high-priority behaviors idle must never override. It NEVER decides - the
``IdleBehavior`` in ``idle_behavior.py`` owns orchestration and consults
this policy for every rule it applies.

Design notes
------------
* Idle is a BEHAVIORAL MODE, not an emotion (behavior-spec v1.0 section 4).
  The three tiers below are the tiers defined by the design authority:
      T1 Attentive idle .... behavior-spec v1.0 section 4.1
                             (no user engaged / nearby but not engaged)
      T2 Engaged idle ...... behavior-spec v1.0 section 4.1
                             (user looking at the robot - detected gaze)
      T3 Deep idle ......... behavior-spec v1.0 section 4.1 ("deep sleep":
                             long inactivity / bedtime)
* Timing bands are taken from the design documents WHERE THE DOCUMENT
  SPECIFIES a value (behavior-spec v1.0 section 4.2 idle timing table).
  Values the documents do NOT specify are marked ``[ENGINEERING
  RECOMMENDATION]`` in the comments - they are tuning defaults, NOT Aibi
  reproductions.
* Randomness is bounded: every interval is sampled UNIFORMLY within its
  band (behavior-spec v1.0 section 4.3: "uniform-random within bands, not
  Gaussian-spiked and not periodic"). There is NO fixed periodic timer
  anywhere in this module - "every N seconds -> action" is deliberately
  impossible here.
* Personality: the policy exposes per-action trait influences (curiosity,
  energy, expressiveness, calmness, focus) and an activity scale driven by
  energy vs calmness. It does NOT redefine personality - it reads the
  existing ``PersonalityTraits`` contract (les/personality/traits.py).
* The policy never hardcodes any specific robot. It is a plain data object
  that a personality-derived policy can replace wholesale later.

Responsibility notes
--------------------
* This module holds VALUES ONLY. It must stay import-light (stdlib only)
  so the policy can be swapped, serialized, or user-tuned without touching
  orchestration code. No pygame, no eyes, no face, no ROS, no hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from ..personality.traits import PersonalityTraits


class IdleTier(str, Enum):
    """The three idle tiers defined by behavior-spec v1.0 section 4.1.

    Members:
        ATTENTIVE: T1 - low activity, stable gaze, occasional natural
            blink, small gaze drift, long quiet periods.
        ENGAGED: T2 - somewhat more active; occasional curiosity glance,
            slightly greater gaze variation (user looking at the robot).
        DEEP: T3 - very low activity, longer pauses, reduced gaze movement,
            slower/less frequent blink opportunities (long inactivity).
    """

    ATTENTIVE = "attentive"
    ENGAGED = "engaged"
    DEEP = "deep"


class IdleAction(str, Enum):
    """The behavioral actions the idle decision layer may produce.

    These are BEHAVIORAL ACTIONS - decisions, not animation. They carry no
    geometry, easing, or servo movement; the animation layer (LES-09A.2+)
    decides how each action looks through the engine.

    Members:
        NONE: remain idle - "nothing happens" is a valid idle decision.
        BLINK: a natural soft blink opportunity.
        GAZE_DRIFT: a slow, un-targeted gaze wander / sweep.
        MICRO_CORRECTION: a tiny re-centering of gaze.
        CURIOUS_GLANCE: a brief exploratory glance at the surroundings.
    """

    NONE = "none"
    BLINK = "blink"
    GAZE_DRIFT = "gaze_drift"
    MICRO_CORRECTION = "micro_correction"
    CURIOUS_GLANCE = "curious_glance"


@dataclass(frozen=True)
class ActionBand:
    """A uniform-random timing band in milliseconds.

    ``min_ms <= interval < max_ms``. Bands are always non-degenerate
    (``min_ms < max_ms``) so no fixed interval can emerge.
    """

    min_ms: float
    max_ms: float


# ---------------------------------------------------------------------------
# Default timing bands (milliseconds).
#
# T1 values are DOC-SOURCED from behavior-spec v1.0 section 4.2:
#     blink interval ............ 3.0-5.0 s (uniform random, never fixed)
#     one gaze sweep ............ every 8-15 s
#     pause between micro-motions  2-6 s
#     idle "check" of surroundings 1 sweep per 20-40 s
# T2/T3 values are [ENGINEERING RECOMMENDATION] guided by section 4.1
# (engaged holds gaze 1.5-3 s; deep sleep blinks slow and deep, near-zero
# gaze) - the documents do not give numeric bands for those tiers.
# ---------------------------------------------------------------------------

DEFAULT_ACTION_BANDS: Mapping[IdleTier, Mapping[IdleAction, ActionBand]] = {
    IdleTier.ATTENTIVE: {
        IdleAction.NONE: ActionBand(2000.0, 6000.0),          # doc 4.2: 2-6 s pause
        IdleAction.BLINK: ActionBand(3000.0, 5000.0),         # doc 4.2: 3.0-5.0 s
        IdleAction.GAZE_DRIFT: ActionBand(8000.0, 15000.0),   # doc 4.2: sweep 8-15 s
        IdleAction.MICRO_CORRECTION: ActionBand(2000.0, 6000.0),  # doc 4.2: 2-6 s
        IdleAction.CURIOUS_GLANCE: ActionBand(20000.0, 40000.0),  # doc 4.2: 20-40 s check
    },
    IdleTier.ENGAGED: {
        IdleAction.NONE: ActionBand(2000.0, 5000.0),              # [ENGINEERING RECOMMENDATION]
        IdleAction.BLINK: ActionBand(3000.0, 5000.0),             # soft blink shared with T1
        IdleAction.GAZE_DRIFT: ActionBand(1500.0, 3000.0),        # doc 4.1: holds gaze 1.5-3 s
        IdleAction.MICRO_CORRECTION: ActionBand(2000.0, 6000.0),  # [ENGINEERING RECOMMENDATION]
        IdleAction.CURIOUS_GLANCE: ActionBand(8000.0, 15000.0),   # [ENGINEERING RECOMMENDATION]
    },
    IdleTier.DEEP: {
        IdleAction.NONE: ActionBand(4000.0, 9000.0),              # [ENGINEERING RECOMMENDATION]
        IdleAction.BLINK: ActionBand(5000.0, 8000.0),             # doc 3.9: slow droopy blink ~6.5-7 s cycle
        IdleAction.GAZE_DRIFT: ActionBand(15000.0, 30000.0),      # doc 4.1: near-zero gaze
        IdleAction.MICRO_CORRECTION: ActionBand(10000.0, 20000.0),  # [ENGINEERING RECOMMENDATION]
        IdleAction.CURIOUS_GLANCE: ActionBand(60000.0, 120000.0),  # [ENGINEERING RECOMMENDATION]
    },
}

# ---------------------------------------------------------------------------
# Default action weights per tier.
# [ENGINEERING RECOMMENDATION] - the documents specify frequencies ("blink
# 3-5 s", "sweep 8-15 s", "check 20-40 s") but not exact choice weights.
# Weights are shaped to match those frequencies: blinks are the most common
# idle event, gaze sweeps and curiosity glances are rare, deep idle is
# dominated by "nothing happens".
# ---------------------------------------------------------------------------

DEFAULT_ACTION_WEIGHTS: Mapping[IdleTier, Mapping[IdleAction, float]] = {
    IdleTier.ATTENTIVE: {
        IdleAction.NONE: 4.0,
        IdleAction.BLINK: 3.5,
        IdleAction.GAZE_DRIFT: 1.0,
        IdleAction.MICRO_CORRECTION: 1.5,
        IdleAction.CURIOUS_GLANCE: 0.4,
    },
    IdleTier.ENGAGED: {
        IdleAction.NONE: 3.0,
        IdleAction.BLINK: 3.0,
        IdleAction.GAZE_DRIFT: 1.2,
        IdleAction.MICRO_CORRECTION: 1.0,
        IdleAction.CURIOUS_GLANCE: 1.2,
    },
    IdleTier.DEEP: {
        IdleAction.NONE: 8.0,
        IdleAction.BLINK: 1.5,
        IdleAction.GAZE_DRIFT: 0.3,
        IdleAction.MICRO_CORRECTION: 0.2,
        IdleAction.CURIOUS_GLANCE: 0.05,
    },
}

# ---------------------------------------------------------------------------
# Emotion modifiers: per-emotion action weight multipliers (1.0 = neutral).
# [ENGINEERING RECOMMENDATION] - behavioral relationships from the mission:
# calm -> attentive idle; happy -> warmer/more expressive; sad -> quieter /
# reduced activity; thinking -> thinking-compatible idle; sleepy -> deep
# idle; surprised -> no idle action (recovery first, handled by the
# behavior). The policy never creates emotions - it only shapes idle
# activity around the existing internal emotion labels.
# ---------------------------------------------------------------------------

DEFAULT_EMOTION_MODIFIERS: Mapping[str, Mapping[IdleAction, float]] = {
    "calm": {a: 1.0 for a in IdleAction},
    "happy": {
        IdleAction.NONE: 0.85,
        IdleAction.BLINK: 1.05,
        IdleAction.GAZE_DRIFT: 1.35,
        IdleAction.MICRO_CORRECTION: 1.15,
        IdleAction.CURIOUS_GLANCE: 1.60,
    },
    "sad": {
        IdleAction.NONE: 1.50,
        IdleAction.BLINK: 0.60,
        IdleAction.GAZE_DRIFT: 0.45,
        IdleAction.MICRO_CORRECTION: 0.70,
        IdleAction.CURIOUS_GLANCE: 0.20,
    },
    "thinking": {
        IdleAction.NONE: 1.30,
        IdleAction.BLINK: 0.90,
        IdleAction.GAZE_DRIFT: 0.55,
        IdleAction.MICRO_CORRECTION: 1.25,
        IdleAction.CURIOUS_GLANCE: 0.30,
    },
    "listening": {
        IdleAction.NONE: 1.00,
        IdleAction.BLINK: 1.00,
        IdleAction.GAZE_DRIFT: 0.90,
        IdleAction.MICRO_CORRECTION: 1.00,
        IdleAction.CURIOUS_GLANCE: 0.60,
    },
    "speaking": {
        IdleAction.NONE: 1.00,
        IdleAction.BLINK: 1.10,
        IdleAction.GAZE_DRIFT: 0.80,
        IdleAction.MICRO_CORRECTION: 1.00,
        IdleAction.CURIOUS_GLANCE: 0.40,
    },
    "focus": {
        IdleAction.NONE: 1.10,
        IdleAction.BLINK: 0.95,
        IdleAction.GAZE_DRIFT: 0.60,
        IdleAction.MICRO_CORRECTION: 1.40,
        IdleAction.CURIOUS_GLANCE: 0.50,
    },
    "caring": {
        IdleAction.NONE: 1.10,
        IdleAction.BLINK: 0.95,
        IdleAction.GAZE_DRIFT: 0.85,
        IdleAction.MICRO_CORRECTION: 1.10,
        IdleAction.CURIOUS_GLANCE: 0.70,
    },
    "sleepy": {
        IdleAction.NONE: 1.40,
        IdleAction.BLINK: 0.70,
        IdleAction.GAZE_DRIFT: 0.40,
        IdleAction.MICRO_CORRECTION: 0.50,
        IdleAction.CURIOUS_GLANCE: 0.05,
    },
    "surprised": {
        IdleAction.NONE: 1.00,
        IdleAction.BLINK: 0.00,
        IdleAction.GAZE_DRIFT: 0.00,
        IdleAction.MICRO_CORRECTION: 0.00,
        IdleAction.CURIOUS_GLANCE: 0.00,
    },
}

# ---------------------------------------------------------------------------
# Personality influence.
# Each idle action leans on one existing LES trait (les/personality/traits.py:
# curiosity, sociability, energy, expressiveness, calmness, focus - all
# [0, 1], 0.5 neutral). The per-action gain scales how strongly the trait
# moves the action's weight: trait t in [0, 1] with neutral 0.5 yields a
# factor ``1 + (t - 0.5) * 2 * gain``, so weight stays within [1-gain, 1+gain].
# [ENGINEERING RECOMMENDATION] - trait-to-idle mappings; the personality
# model itself is the existing one, never redefined.
# ---------------------------------------------------------------------------

DEFAULT_PERSONALITY_ACTION_TRAIT: Mapping[IdleAction, str] = {
    IdleAction.NONE: "calmness",
    IdleAction.BLINK: "energy",
    IdleAction.GAZE_DRIFT: "expressiveness",
    IdleAction.MICRO_CORRECTION: "focus",
    IdleAction.CURIOUS_GLANCE: "curiosity",
}

DEFAULT_PERSONALITY_ACTION_GAIN: Mapping[IdleAction, float] = {
    IdleAction.NONE: 0.7,
    IdleAction.BLINK: 0.6,
    IdleAction.GAZE_DRIFT: 0.6,
    IdleAction.MICRO_CORRECTION: 0.5,
    IdleAction.CURIOUS_GLANCE: 0.9,
}

# Cooldown names (BehaviorMemory owns the timers) + durations in ms.
# [ENGINEERING RECOMMENDATION] - cross-system re-entry guards. The timing
# BANDS are the primary anti-periodicity mechanism; cooldowns stop other
# LES systems (or repeated triggers) from stacking the same action on top
# of a just-performed one.
DEFAULT_COOLDOWN_MS: Mapping[str, float] = {
    "idle_blink": 2500.0,
    "idle_glance": 4000.0,
    "idle_curiosity": 8000.0,
    "idle_micro": 1500.0,
}

# High-priority behaviors idle must NEVER override (interaction-bible v1.0
# Part 8.3: "Attention always beats idle; idle is the default, not a
# competitor"). Names are the BehaviorDirector's intent vocabulary
# (les/director/behavior_policy.py). ``waiting`` is deliberately absent: it
# IS the attentive-idle state (E16). ``idle`` is this layer itself.
DEFAULT_YIELD_BEHAVIORS: frozenset[str] = frozenset(
    {
        "alert",
        "listening",
        "comforting",
        "responding",
        "greeting",
        "thinking",
        "playful",
        "celebrating",
        "searching",
        "confused",
        "curious",
    }
)

# Interaction modes that are NOT idle-compatible (any mode other than idle /
# waiting / sleep means the robot is engaged in something -> yield). Values
# are InteractionMode members (les/world/interaction_state.py).
DEFAULT_YIELD_MODES: frozenset[str] = frozenset(
    {
        "greeting",
        "listening",
        "responding",
        "thinking",
        "searching",
        "curious",
        "playful",
        "comforting",
        "alert",
        "celebrating",
        "confused",
        "wake",
    }
)


@dataclass(frozen=True)
class IdlePolicy:
    """Configurable idle rules consulted by the ``IdleBehavior``.

    All values are plain data; the policy never decides. Defaults are drawn
    from the design documents where they specify values; everything else is
    a clearly-marked engineering recommendation (see module docstring).

    Attributes:
        action_bands: per-tier, per-action uniform-random timing bands (ms).
        action_weights: per-tier, per-action base choice weights.
        emotion_modifiers: per-emotion action weight multipliers.
        personality_action_trait: which trait each action leans on.
        personality_action_gain: how strongly that trait moves the weight.
        activity_gain_energy: how much energy raises overall activity.
        activity_gain_calmness: how much calmness lowers overall activity.
        cooldown_ms: named cooldown durations (BehaviorMemory timers).
        yield_behavior_names: behaviors idle must yield to.
        yield_mode_values: interaction-mode values idle must yield to.
        deep_idle_after_ms: inactivity threshold for deep idle
            [ENGINEERING RECOMMENDATION - doc says "long inactivity" only].
        surprise_quiet_ms: recovery band after a surprise emotion
            [ENGINEERING RECOMMENDATION].
        yield_recheck_ms: how soon to re-check after yielding
            [ENGINEERING RECOMMENDATION].
        anti_repeat_window: recent-action window used to suppress immediate
            repetition (behavior-spec 4.3: no three identical in a row).
        min_stability_for_activity: below this emotion stability, idle
            activity is damped (recent emotional change = be conservative).
    """

    action_bands: Mapping[IdleTier, Mapping[IdleAction, ActionBand]] = field(
        default_factory=lambda: {t: dict(b) for t, b in DEFAULT_ACTION_BANDS.items()}
    )
    action_weights: Mapping[IdleTier, Mapping[IdleAction, float]] = field(
        default_factory=lambda: {t: dict(w) for t, w in DEFAULT_ACTION_WEIGHTS.items()}
    )
    emotion_modifiers: Mapping[str, Mapping[IdleAction, float]] = field(
        default_factory=lambda: {e: dict(m) for e, m in DEFAULT_EMOTION_MODIFIERS.items()}
    )
    personality_action_trait: Mapping[IdleAction, str] = field(
        default_factory=lambda: dict(DEFAULT_PERSONALITY_ACTION_TRAIT)
    )
    personality_action_gain: Mapping[IdleAction, float] = field(
        default_factory=lambda: dict(DEFAULT_PERSONALITY_ACTION_GAIN)
    )
    activity_gain_energy: float = 0.5
    activity_gain_calmness: float = 0.5
    cooldown_ms: Mapping[str, float] = field(
        default_factory=lambda: dict(DEFAULT_COOLDOWN_MS)
    )
    yield_behavior_names: frozenset[str] = DEFAULT_YIELD_BEHAVIORS
    yield_mode_values: frozenset[str] = DEFAULT_YIELD_MODES
    deep_idle_after_ms: float = 120_000.0
    surprise_quiet_ms: ActionBand = ActionBand(1500.0, 3000.0)
    yield_recheck_ms: ActionBand = ActionBand(250.0, 1000.0)
    anti_repeat_window: int = 3
    min_stability_for_activity: float = 0.4

    # ------------------------------------------------------------------
    # Tiny pure accessors (values only - no decisions).
    # ------------------------------------------------------------------

    def band_for(self, tier: IdleTier, action: IdleAction) -> ActionBand:
        """The timing band for an action in a tier (bounded fallback)."""
        return self.action_bands.get(tier, {}).get(
            action, ActionBand(2000.0, 6000.0)
        )

    def weight_for(self, tier: IdleTier, action: IdleAction) -> float:
        """The base choice weight for an action in a tier (0 if unknown)."""
        return self.action_weights.get(tier, {}).get(action, 0.0)

    def emotion_modifier_for(
        self, emotion: str, action: IdleAction
    ) -> float:
        """The emotion->action weight multiplier (1.0 when not configured)."""
        return self.emotion_modifiers.get(emotion, {}).get(action, 1.0)

    def action_trait_factor(self, action: IdleAction, traits: PersonalityTraits) -> float:
        """Personality factor for an action: ``1 + (trait-0.5)*2*gain``.

        Neutral trait (0.5) leaves the weight unchanged; the factor stays
        within ``[1 - gain, 1 + gain]`` for traits in [0, 1].
        """
        trait_name = self.personality_action_trait.get(action, "calmness")
        gain = self.personality_action_gain.get(action, 0.0)
        trait_value = getattr(traits, trait_name, 0.5)
        return 1.0 + (trait_value - 0.5) * 2.0 * gain

    def activity_scale(self, traits: PersonalityTraits) -> float:
        """Overall idle activity scale from energy vs calmness, in [0.5, 1.5].

        Higher energy raises activity (non-NONE actions become more likely),
        higher calmness lowers it. Pure value math - no decisions.
        """
        energy_term = (traits.energy - 0.5) * 2.0 * self.activity_gain_energy
        calm_term = (traits.calmness - 0.5) * 2.0 * self.activity_gain_calmness
        return max(0.5, min(1.5, 1.0 + energy_term - calm_term))

    def cooldown_key(self, action: IdleAction) -> str:
        """The BehaviorMemory cooldown name guarding an action."""
        return {
            IdleAction.BLINK: "idle_blink",
            IdleAction.GAZE_DRIFT: "idle_glance",
            IdleAction.MICRO_CORRECTION: "idle_micro",
            IdleAction.CURIOUS_GLANCE: "idle_curiosity",
        }.get(action, "idle_action")

    def cooldown_for(self, action: IdleAction) -> float:
        """Duration of the cooldown guarding an action (ms)."""
        return self.cooldown_ms.get(self.cooldown_key(action), 0.0)


__all__ = [
    "IdleTier",
    "IdleAction",
    "ActionBand",
    "IdlePolicy",
    "DEFAULT_ACTION_BANDS",
    "DEFAULT_ACTION_WEIGHTS",
    "DEFAULT_EMOTION_MODIFIERS",
    "DEFAULT_PERSONALITY_ACTION_TRAIT",
    "DEFAULT_PERSONALITY_ACTION_GAIN",
    "DEFAULT_COOLDOWN_MS",
    "DEFAULT_YIELD_BEHAVIORS",
    "DEFAULT_YIELD_MODES",
]
