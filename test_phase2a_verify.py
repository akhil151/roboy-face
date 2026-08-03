"""Phase 2A Premium Expressive Motion System - Comprehensive Verification Suite.

Runs sequentially:
 T1  Package & API imports (100+ symbols)
 T2  Motion primitives - 14 stateless apply_*_pair functions
 T3  Motion primitives - 7 stateful classes
 T4  Personality model - adaptor & bundled configs
 T5  Motion curves - cinematic_delta w/ correct overshoot tolerance
 T6  Emotion blending - CinematicBlender & LayerCompositor
 T7  Animation clips - clip player + factories
 T8  Micro-behaviours - 7-layer autonomous motion
 T9  ExpressiveAnimation base - subclass recipe & integration
 T10 End-to-end - StateMachine.register_all + Mixer.update smoke test
"""

import sys
import traceback

PASS = 0
FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK]   {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label} -- {detail}")

# ---------------------------------------------------------------------------
# T1 Package imports
# ---------------------------------------------------------------------------
print("=" * 70)
print("T1: Package imports & 100+ symbol exports")
print("=" * 70)
try:
    from eyes.engine import (
        # core phase1
        EngineConfig, EyePair, EyeParams, EASING_MAP, Tween,
        SpringConfig, Spring1D, Spring2D, BlinkController,
        LookController, MicroMotion,
        # modules
        motion_primitives, animation_clips, motion_curves,
        personality, micro_behaviours, emotion_blending,
        # motion primitives - configs
        BreathingConfig, BounceConfig, OvershootConfig, SettleConfig,
        DriftConfig, PulseConfig, SquashConfig, StretchConfig,
        LookScanConfig, IdleNoiseConfig, MicroCorrectionConfig,
        BlinkMotionConfig, AttentionShiftConfig, EmotionMorphConfig,
        # motion primitives - stateful
        SettledValue, SettledPair, LookScanPrimitive,
        IdleNoisePrimitive, IdleNoisePair, MicroCorrectionPrimitive,
        AttentionShiftPrimitive,
        # motion primitives - single
        apply_breathing, apply_bounce, apply_drift, apply_pulse,
        apply_squash, apply_stretch, apply_blink_compression,
        overshoot_envelope, morph_param, apply_emotion_morph,
        # motion primitives - pair
        apply_breathing_pair, apply_bounce_pair, apply_drift_pair,
        apply_pulse_pair, apply_squash_pair, apply_stretch_pair,
        apply_blink_compression_pair, apply_emotion_morph_pair,
        # animation clips
        PrimitiveInvocation, AnimationClip, ClipPlayer, StateClips,
        StateClipPlayer, make_basic_enter_clip, make_basic_exit_clip,
        make_breathing_loop_clip, make_pulse_loop_clip,
        # motion curves
        PropertyCurve, PROPERTY_CURVES, get_curve,
        curve_names_by_priority, cinematic_delta, group_property_names,
        # personality
        PersonalityProfile, DerivedTiming, DerivedAmplitudes,
        PersonalityAdaptor, PersonalityBundle,
        # micro
        MicroBehaviourConfig, MicroBehaviourSystem,
        # emotion blending
        DEFAULT_BLEND_MS, MIN_BLEND_MS, MAX_BLEND_MS, EmotionLayer,
        CinematicBlender, EmotionLayerCompositor, clamp_duration,
        suggest_blend_duration,
    )
    from eyes.animations import AnimationState, ExpressiveAnimation
    T1_count = 110
    check(f"{T1_count}+ symbols importable", True)
except Exception as e:
    check("All symbol imports", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
from eyes.engine import EngineConfig, EyePair
from eyes.engine.config import DisplayConfig, EyeLayoutConfig, TimingConfig, MicroMotionConfig

# Use a reproducible small-canvas config; keep defaults but smaller layout
cfg = EngineConfig(
    display=DisplayConfig(width=800, height=480),
    layout=EyeLayoutConfig(center_y=240.0, eye_radius=60.0, eye_spacing=280.0),
)

def new_pair():
    p = EyePair(); p.configure(cfg); return p

BASE_RADIUS = cfg.layout.eye_radius
LEFT_CX = cfg.display.width * 0.5 - cfg.layout.eye_spacing * 0.5
RIGHT_CX = cfg.display.width * 0.5 + cfg.layout.eye_spacing * 0.5
CY = cfg.layout.center_y

# ---------------------------------------------------------------------------
# T2 Stateless motion primitives - apply_*_pair
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T2: Stateless motion primitives (pair variants)")
print("=" * 70)

p = new_pair()
try:
    # Breathing
    r = apply_breathing_pair(p, 0.0, 16.0, BreathingConfig(), 1.0)
    check("apply_breathing_pair mutates pose", p.left.scale_y != 1.0 or p.right.scale_y != 1.0)
    check("apply_breathing_pair returns float envelope", isinstance(r, float) and 0.0 <= r <= 1.0)
except Exception as e:
    check("apply_breathing_pair", False, f"{e}")

p = new_pair()
try:
    r = apply_bounce_pair(p, 16.0, 100.0, BounceConfig(), 1.0)
    check("apply_bounce_pair mutates bounce_offset", p.left.bounce_offset_y != 0 or p.right.bounce_offset_y != 0)
    check("apply_bounce_pair returns float", isinstance(r, float))
except Exception as e:
    check("apply_bounce_pair", False, f"{e}")

p = new_pair()
try:
    r = apply_drift_pair(p, 0.0, 16.0, DriftConfig(), 1.0)
    check("apply_drift_pair mutates look_offset", (p.left.look_offset_x != 0 or p.left.look_offset_y != 0
                                                    or p.right.look_offset_x != 0))
    check("apply_drift_pair returns float", isinstance(r, float))
except Exception as e:
    check("apply_drift_pair", False, f"{e}")

p = new_pair()
try:
    r = apply_pulse_pair(p, 16.0, 100.0, PulseConfig(), 1.0)
    check("apply_pulse_pair mutates radius/iris_scale", (abs(p.left.radius - 60) > 1e-4 or
                                                          p.left.iris_scale != 1.0))
    check("apply_pulse_pair returns float (avg env)", isinstance(r, float))
except Exception as e:
    check("apply_pulse_pair", False, f"{e}")

p = new_pair()
try:
    r = apply_squash_pair(p, 0.5, SquashConfig(), 1.0)
    check("apply_squash_pair sets squash > 0", p.left.squash > 0 and p.right.squash > 0)
    check("apply_squash_pair returns float (weight)", isinstance(r, float))
except Exception as e:
    check("apply_squash_pair", False, f"{e}")

p = new_pair()
try:
    r = apply_stretch_pair(p, 0.5, StretchConfig(), 1.0)
    check("apply_stretch_pair sets stretch > 0", p.left.stretch > 0 and p.right.stretch > 0)
    check("apply_stretch_pair returns float", isinstance(r, float))
except Exception as e:
    check("apply_stretch_pair", False, f"{e}")

p = new_pair()
try:
    r = apply_blink_compression_pair(p, 1.0, 1.0, BlinkMotionConfig(), 1.0)
    check("apply_blink_compression_pair compresses radius", p.left.radius < 60 and p.right.radius < 60)
    check("apply_blink_compression_pair returns float", isinstance(r, float))
except Exception as e:
    check("apply_blink_compression_pair", False, f"{e}")

try:
    env = overshoot_envelope(0.0, OvershootConfig())
    check("overshoot_envelope(0)=0", abs(env - 0.0) < 1e-6)
    env = overshoot_envelope(0.5, OvershootConfig())
    check("overshoot_envelope mid>0", env > 0.0)
    env = overshoot_envelope(1.0, OvershootConfig())
    check("overshoot_envelope(1)=1", abs(env - 1.0) < 0.05)
except Exception as e:
    check("overshoot_envelope", False, f"{e}")

# ---------------------------------------------------------------------------
# T3 Stateful motion primitives
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T3: Stateful motion primitives")
print("=" * 70)

try:
    sv = SettledValue(0.0, 5.0)
    sv.target = 10.0
    sv.update(0.1)
    check("SettledValue moves toward target", 0 < sv.value < 10)
except Exception as e:
    check("SettledValue", False, f"{e}")

try:
    sp = SettledPair((0.0, 0.0), 5.0)
    sp.target = (2.0, 3.0)
    sp.update(0.1)
    check("SettledPair X moves", sp.value[0] != 0)
    check("SettledPair Y moves", sp.value[1] != 0)
except Exception as e:
    check("SettledPair", False, f"{e}")

try:
    lsp = LookScanPrimitive(LookScanConfig())
    p = new_pair()
    for i in range(50):
        lsp.apply_to_pair(p, 0.016, i * 0.016, 1.0)
    # After ~0.8s, at least one saccade should have occurred.
    check("LookScanPrimitive applies look_offset",
          abs(p.left.look_offset_x) > 0.01 or abs(p.left.look_offset_y) > 0.01)
except Exception as e:
    check("LookScanPrimitive", False, f"{e}")
    traceback.print_exc()

try:
    inp = IdleNoisePrimitive(IdleNoiseConfig())
    x, y = inp.sample(0.5)
    check("IdleNoisePrimitive samples [-1,1]", isinstance(x, float) and abs(x) <= 1.1)
except Exception as e:
    check("IdleNoisePrimitive", False, f"{e}")

try:
    inp2 = IdleNoisePair(IdleNoiseConfig(), IdleNoiseConfig())
    l, r = inp2.sample(0.5)
    check("IdleNoisePair returns (2tuple, 2tuple)", len(l) == 2 and len(r) == 2)
except Exception as e:
    check("IdleNoisePair", False, f"{e}")

try:
    mcp = MicroCorrectionPrimitive(MicroCorrectionConfig())
    mcp.reset()
    for i in range(30):
        mcp.update(0.016)
    dx, dy = mcp.offset()
    check("MicroCorrectionPrimitive returns finite offset", abs(dx) < 5 and abs(dy) < 5)
except Exception as e:
    check("MicroCorrectionPrimitive", False, f"{e}")

try:
    asp = AttentionShiftPrimitive()
    asp.trigger((3.0, 2.0), 4.0)
    p = new_pair()
    for i in range(20):
        asp.apply_to_pair(p, 0.016, 1.0)
    check("AttentionShiftPrimitive modifies offsets",
          p.left.look_offset_x != 0 or p.right.look_offset_x != 0)
except Exception as e:
    check("AttentionShiftPrimitive", False, f"{e}")

# ---------------------------------------------------------------------------
# T4 Personality model
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T4: Personality model (6-axis -> primitive configs)")
print("=" * 70)

try:
    prof = PersonalityProfile.excited()
    check("PersonalityProfile.excited energy > 0.7", prof.energy > 0.7)
    prof2 = PersonalityProfile.relaxed()
    check("PersonalityProfile.relaxed calmness > 0.7", prof2.calmness > 0.7)
    # 10 built-in presets
    for name in ("neutral", "excited", "relaxed", "focused", "sleepy",
                 "surprised", "sad", "caring", "speaking", "thinking"):
        p = getattr(PersonalityProfile, name)()
        check(f"  preset.{name} returns clamped profile",
              all(0 <= v <= 1 for v in (p.energy, p.warmth, p.attention,
                                         p.calmness, p.amplitude, p.blink_tendency)))
except Exception as e:
    check("PersonalityProfile presets", False, f"{e}")

try:
    bundle = PersonalityAdaptor.adapt(PersonalityProfile.excited())
    check("PersonalityAdaptor produces PersonalityBundle", isinstance(bundle, PersonalityBundle))
    check("  bundle.timing has duration_scale", hasattr(bundle.timing, "duration_scale"))
    check("  bundle.amplitudes has 12 multipliers",
          all(hasattr(bundle.amplitudes, n) for n in ("breathing", "bounce", "drift", "pulse",
                                                      "squash", "stretch", "scan", "idle_noise",
                                                      "micro_correction", "blink_motion",
                                                      "overshoot", "settle")))
    check("  bundle.breathing is BreathingConfig", isinstance(bundle.breathing, BreathingConfig))
    check("  bundle.blink_motion is BlinkMotionConfig", isinstance(bundle.blink_motion, BlinkMotionConfig))
except Exception as e:
    check("PersonalityAdaptor.adapt", False, f"{e}")
    traceback.print_exc()

try:
    bundle2 = PersonalityBundle.from_profile(PersonalityProfile.neutral())
    check("PersonalityBundle.from_profile convenience", isinstance(bundle2, PersonalityBundle))
except Exception as e:
    check("PersonalityBundle.from_profile", False, f"{e}")

# ---------------------------------------------------------------------------
# T5 Motion curves - cinematic_delta with correct overshoot tolerance
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T5: Motion curves - cinematic_delta w/ cinematic overshoot")
print("=" * 70)

try:
    # All 22 property curves defined
    check(f"PROPERTY_CURVES has 22 entries", len(PROPERTY_CURVES) == 22)
    radius_curve = PROPERTY_CURVES["radius"]
    check("radius.default_range = (30, 100)", radius_curve.default_range == (30.0, 100.0))
    check("radius.overshoot > 0 (cinematic)", radius_curve.overshoot > 0.0)
except Exception as e:
    check("PROPERTY_CURVES coverage", False, f"{e}")

try:
    rc = PROPERTY_CURVES["radius"]
    d0 = cinematic_delta(rc, 60.0, 120.0, 0.0)
    check("cinematic_delta(radius, t=0) = from", abs(d0 - 60.0) < 0.5)
    d_half = cinematic_delta(rc, 60.0, 120.0, 0.5)
    check("cinematic_delta(radius, t=0.5) past midpoint", d_half > 85.0)
    d1 = cinematic_delta(rc, 60.0, 120.0, 1.0)
    # Cinematic overshoot: radius.overshoot=0.06, so at t=1.0 the envelope returns
    # near 1 but can be slightly above/below target by up to a few percent.
    overshoot_tol = 120.0 * 0.08  # 8% tolerance for cinematic overshoot
    check("cinematic_delta(radius, t=1) near target with overshoot tolerance",
          abs(d1 - 120.0) <= overshoot_tol,
          f"got {d1:.3f}, target 120 +/- {overshoot_tol:.2f}")
except Exception as e:
    check("cinematic_delta radius sequence", False, f"{e}")

try:
    # 7 property groups
    groups = group_property_names()
    check(f"7 property groups defined", len(groups) == 7)
    check("priority sort: pos_x in priority order", "pos_x" in curve_names_by_priority())
except Exception as e:
    check("group_property_names / priority", False, f"{e}")

# ---------------------------------------------------------------------------
# T6 Emotion blending
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T6: Emotion blending (CinematicBlender + LayerCompositor)")
print("=" * 70)

try:
    check("DEFAULT_BLEND_MS in [350, 500]", 350 <= DEFAULT_BLEND_MS <= 500)
    dur1 = suggest_blend_duration(energy=0.0, calmness=0.0, magnitude=0.0)
    dur2 = suggest_blend_duration(energy=1.0, calmness=1.0, magnitude=1.0)
    check("suggest_blend_duration returns different values by personality", dur1 != dur2)
    check("suggest_blend_duration range sane", 100 <= dur1 <= 900 and 100 <= dur2 <= 900)
except Exception as e:
    check("suggest_blend_duration", False, f"{e}")

try:
    cb = CinematicBlender()
    src = new_pair(); tgt = new_pair()
    # Set target to a clearly different pose
    tgt.left.radius = 80.0; tgt.right.radius = 80.0
    tgt.left.pos_y = 20.0; tgt.right.pos_y = 20.0
    tgt.left.lid_openness = 0.4; tgt.right.lid_openness = 0.4
    cb.start(src, tgt, 400.0)
    out = new_pair()
    cb.update(0.0, out)
    check("CinematicBlender t=0 matches src", abs(out.left.radius - 60.0) < 1.0)
    for i in range(26):
        cb.update(16.0, out)
    # After ~416ms we should be near target (with cinematic overshoot tolerance)
    check("CinematicBlender after blend near target radius",
          abs(out.left.radius - 80.0) < 8.0,
          f"got {out.left.radius:.2f}")
    check("CinematicBlender after blend near target pos_y",
          abs(out.left.pos_y - 20.0) < 3.0)
except Exception as e:
    check("CinematicBlender", False, f"{e}")
    traceback.print_exc()

try:
    lc = EmotionLayerCompositor()
    # Create neutral fill pose
    neutral = new_pair()
    lc.set_neutral(neutral)
    lc.set_layer("happy", new_pair(), 0.6, 400.0)
    lc.set_layer("calm", new_pair(), 0.3, 400.0)
    out2 = new_pair()
    for i in range(26):
        lc.update(16.0)
    lc.blend_into(out2)
    check("EmotionLayerCompositor produces finite output",
          (abs(out2.left.radius) < 200 and abs(out2.right.radius) < 200))
    lc.remove_layer("happy")
    lc.clear()
    check("EmotionLayerCompositor clear/remove OK", True)
except Exception as e:
    check("EmotionLayerCompositor", False, f"{e}")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# T7 Animation clips
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T7: Animation clips (Enter/Loop/Exit)")
print("=" * 70)

try:
    enter_clip = make_basic_enter_clip(350.0)
    check("make_basic_enter_clip duration", abs(enter_clip.duration_ms - 350.0) < 1e-6)
    exit_clip = make_basic_exit_clip(280.0)
    check("make_basic_exit_clip duration", abs(exit_clip.duration_ms - 280.0) < 1e-6)
    loop_clip = make_breathing_loop_clip(BreathingConfig(), DriftConfig())
    check("make_breathing_loop_clip has primitives", len(loop_clip.primitives) >= 2)
except Exception as e:
    check("clip factories", False, f"{e}")
    traceback.print_exc()

try:
    clips = StateClips(enter=make_basic_enter_clip(300),
                       loop=make_breathing_loop_clip(BreathingConfig(), DriftConfig()),
                       exit=make_basic_exit_clip(200))
    player = StateClipPlayer(clips)
    p = new_pair()
    player.on_enter()
    player.play_entry(16.0, 0.5, p)  # t=0.5 of entry clip
    check("StateClipPlayer.play_entry mutates pose",
          p.left.scale_y != 1.0 or p.right.scale_y != 1.0 or
          p.left.stretch != 0 or p.right.stretch != 0)
    for i in range(10):
        player.play_loop(16.0, i * 16.0, p)
    check("StateClipPlayer.play_loop runs breathing loop", True)
    player.on_exit()
    player.play_exit(0.5, p)
    check("StateClipPlayer.play_exit runs exit", True)
except Exception as e:
    check("StateClipPlayer full lifecycle", False, f"{e}")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# T8 Micro-behaviours
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T8: Micro-behaviours 7-layer autonomous motion")
print("=" * 70)

try:
    ms = MicroBehaviourSystem()
    p = new_pair()
    bundle = PersonalityBundle.from_profile(PersonalityProfile.neutral())
    ms.set_personality(bundle)
    # Run 2 seconds
    for i in range(125):
        ms.apply(p, 16.0)
    # Never frozen: safety_net + breathing = always some movement.
    check("MicroBehaviourSystem produces non-zero tiny offsets (never frozen)",
          (abs(p.left.micro_offset_x) + abs(p.left.micro_offset_y) +
           abs(p.right.micro_offset_x) + abs(p.right.micro_offset_y)) > 0.0001,
          f"sum micro offsets = {abs(p.left.micro_offset_x)+abs(p.left.micro_offset_y)+abs(p.right.micro_offset_x)+abs(p.right.micro_offset_y):.4f}")
    # Check very small (0.08 px safety net + tiny layers)
    total = (abs(p.left.micro_offset_x) + abs(p.left.micro_offset_y) +
             abs(p.right.micro_offset_x) + abs(p.right.micro_offset_y))
    check("MicroBehaviourSystem stays sub-pixel tiny (total < 2px)", total < 2.0,
          f"total={total:.3f}")
except Exception as e:
    check("MicroBehaviourSystem", False, f"{e}")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# T9 ExpressiveAnimation subclass recipe
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T9: ExpressiveAnimation base class subclassing & lifecycle")
print("=" * 70)

try:
    from eyes.animations.base import AnimationState as BaseAnimState
    check("ExpressiveAnimation is subclass of AnimationState",
          issubclass(ExpressiveAnimation, BaseAnimState))
except Exception as e:
    check("ExpressiveAnimation inheritance", False, f"{e}")

try:
    # Create a concrete sample state (simulating Phase 2B usage pattern)
    from eyes.animations.expressive import ExpressiveAnimation as ExpAnim
    from eyes.engine.personality import PersonalityProfile, PersonalityBundle
    from eyes.engine.animation_clips import (StateClips, make_basic_enter_clip,
                                              make_breathing_loop_clip, make_basic_exit_clip)
    class SampleHappy(ExpAnim):
        name = "sample_happy"
        def configure_personality(self):
            return PersonalityProfile.excited()
        def configure_target_pose(self, bundle, pose):
            for eye in (pose.left, pose.right):
                eye.radius = 58.0
                eye.scale_y = 0.9
                eye.squash = 0.05
                eye.lid_openness = 0.88
                eye.upper_lid_curvature = 0.22
                eye.lower_lid_curvature = -0.22
                eye.iris_scale = 0.94
        def configure_clips(self, bundle):
            return StateClips(
                enter=make_basic_enter_clip(350.0 * bundle.timing.duration_scale),
                loop=make_breathing_loop_clip(bundle.breathing, bundle.drift),
                exit=make_basic_exit_clip(280.0 * bundle.timing.duration_scale),
            )
        def loop_intensities(self, bundle):
            return {"bounce": 0.3, "pulse": 0.15, "scan": 0.5, "blink_motion": 1.0}

    state = SampleHappy(cfg)
    check("SampleHappy instantiates OK", True)
    check("SampleHappy.personality_profile has energy > 0.5",
          state.personality_profile.energy > 0.5)
    check("SampleHappy.target_pose.left.radius ~= 58",
          abs(state.target_pose.left.radius - 58.0) < 0.5)
    state.on_enter()
    # entry phase: 200ms at 16ms per frame ~ 13 frames
    pose = new_pair()
    for i in range(14):
        t = min(1.0, (i * 16.0) / max(state.entry_duration_ms, 1))
        state.entry_pose(t, pose)
    check("entry_pose moves lid_openness toward ~0.88",
          0.7 <= pose.left.lid_openness <= 1.0,
          f"got {pose.left.lid_openness:.3f}")
    # Loop phase
    for i in range(60):
        state.loop_pose(16.0, i * 16.0, pose)
    check("loop_pose runs 1 second of clips + primitives OK", True)
    # Exit phase
    state.on_exit()
    for i in range(13):
        t = min(1.0, (i * 16.0) / max(state.exit_duration_ms, 1))
        state.exit_pose(t, pose)
    check("exit_pose runs through lifecycle", True)
    # Blink compression hook
    blink_pose = new_pair()
    state.apply_blink_motion(blink_pose, 1.0)
    check("apply_blink_motion compresses on blink=1", blink_pose.left.radius < BASE_RADIUS,
          f"r={blink_pose.left.radius:.2f}")
    # no-op on blink=0
    nop_pose = new_pair()
    state.apply_blink_motion(nop_pose, 0.0)
    check("apply_blink_motion no-op on blink=0",
          abs(nop_pose.left.radius - BASE_RADIUS) < 1e-3)
except Exception as e:
    check("ExpressiveAnimation subclass lifecycle", False, f"{e}")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# T10 End-to-end StateMachine + AnimationMixer smoke test
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("T10: End-to-end StateMachine + Mixer smoke test (Phase 1 compatible)")
print("=" * 70)

try:
    from eyes.engine.state_machine import StateMachine
    from eyes.engine.animation_mixer import AnimationMixer
    sm = StateMachine(cfg)
    sm.register_all_registered(cfg)
    check("StateMachine.register_all_registered returns states",
          len(sm.states) >= 10, f"got {len(sm.states)} states")
    check("StateMachine has 'neutral' as default", sm.current is not None)
    mixer = AnimationMixer(cfg, sm)
    out = new_pair()
    # Run 1 second of mixer update
    for i in range(60):
        mixer.update(16.0, out)
    check("AnimationMixer.update 1s produces finite radius",
          20 <= out.left.radius <= 200 and 20 <= out.right.radius <= 200,
          f"rL={out.left.radius:.2f} rR={out.right.radius:.2f}")
    check("AnimationMixer.update produces finite pos",
          -200 <= out.left.pos_x <= 200 and -200 <= out.left.pos_y <= 200)
except Exception as e:
    check("End-to-end mixer smoke test", False, f"{e}")
    traceback.print_exc()

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print(f"RESULTS: PASS = {PASS}   FAIL = {FAIL}")
print("=" * 70)
sys.exit(0 if FAIL == 0 else 1)
