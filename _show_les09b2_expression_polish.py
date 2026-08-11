"""
_show_les09b2_expression_polish.py  --  TEMPORARY VISUAL VALIDATION SHOWCASE (LES-09B.2 + LES-09B.3)
========================================================================================

A human-facing validation harness for the Emotion Expression Choreography
layer, extended with LES-09B.2 polish features and the LES-09B.3 SLEEPY
choreography:

    * Thinking "?" cue: scale is DERIVED from the eye geometry
      (thinking_cue_scale_ratio * eye_radius -> ~74 px on a 150 px eye:
      approximately half the eye height), with a configurable clearance
      margin and a fade-in/out cycle.
    * LES-09B.4 SPATIAL FIX: both the thinking "?" and the sleepy ZZZ are
      now placed in FACE SPACE derived from the actual eye layout, and
      both guarantee a configurable clearance margin from the rendered
      eye silhouettes at every gaze target (never inside/behind an eye).
      The thinking scale is a RATIO of the real eye radius (~half the eye
      height), not a hard-coded pixel size.
    * LES-09B.5 PERIMETER ANCHOR: the thinking "?" size is UNCHANGED;
      only its placement changed - it is anchored to the RIGHT eye's
      OUTER TOP corner (eye perimeter -> small clearance -> "?"), so it
      feels attached to the eye's expressive language, follows every
      gaze movement, and stays outside both eye silhouettes (it is no
      longer centred above the face). The sleepy ZZZ is untouched.
    * Thinking preparation beat + subtle correction beat (richer narrative).
    * Happy extra gaze variation + soft settling beat.
    * Sad extended stillness holds.
    * Sleepy ZZZ cue: larger (16.0 vs 12.0).
    * LES-09B.3: SLEEPY is now a dedicated authored choreography
      (drowsy descent: heavy eyes -> gaze sinks -> sleepy blink -> quiet
      hold -> second heavy blink -> tiny settling -> sleepy idle), with
      two Bible variants (deep_sleep / gentle_doze) - no longer a
      fallback plan. The engine's own droop loop + ZZZ overlay remain
      authoritative; the choreography sequences WHEN/WHY.
    * Key Q toggles between POLISHED (default, LES-09B.5 perimeter-
      anchored with clearance) and LEGACY cue sizes (the old 18 px
      thinking scale + zero clearance, and the old ZZZ band that
      overlapped the eye - for direct comparison). NOTE: in LEGACY mode
      the cue can intentionally hug/overlap the eye silhouette - that is
      the old bug being demonstrated, not a defect.
    * Arrow keys override the GAZE (up/down/left/right, diagonals too):
      while held, the engine's look controller is driven to the extreme
      target each frame so the cue placement can be inspected while the
      eyes move. Release to hand gaze back to the choreography.
    * Key A toggles ATTENTION-PRESERVATION mode: while active, gaze
      beats are suppressed (the LES-09A.2 idle contract - attention
      always beats autonomous gaze) so the sleepy downward gaze never
      overwrites a meaningful attention target.
    * HUD shows thinking cue diagnostics (visible, scale, position) and
      sleepy diagnostics (ZZZ particles, gaze target, blink weight).

It drives the real full pipeline:

    World State -> Emotion Director -> EmotionChoreographyRunner
        -> EmotionChoreographyBridge -> DefaultScheduler
        -> EngineCommand -> RealEngineDriver -> FaceEngine (real, frozen)

The face is the visual focus. The HUD shows the CURRENT EMOTION, the
CURRENT CHOREOGRAPHY (variant), the CURRENT BEAT and the ELAPSED BEAT TIME,
plus diagnostics (requested target / blocked reason / gaze target / blink
weight / engine state / thinking cue info).

Keys:
    1..5   CALM  HAPPY  SAD  THINKING  SLEEPY   (direct emotion request)
    C      Calm -> Happy transition request
    S      Happy -> Sad   (routes through calm - existing valence waypoint)
    D      Sad -> Calm    (recovery)
    T      Calm -> Thinking
    R      Thinking -> Calm (recovery)
    W      SLEEPY -> CALM (wake-up request)
    N      RELEASE - stop the detection (the director's neutral fallback
           recovers to calm after ~2 s of no detection - watch recovery)
    Q      Toggle POLISHED (default, LES-09B.5 perimeter-anchored with
           clearance) / LEGACY cue sizes (old 18 px scale + zero clearance,
           old overlapping ZZZ band)
    A      Toggle ATTENTION-PRESERVATION mode (gaze beats suppressed -
           the LES-09A.2 idle contract; watch the sleepy gaze stay put)
    ARROWS Hold to override the GAZE to the extreme (up/down/left/right,
           diagonals combine) - inspect the cues while the eyes move
    ESC    quit

Note on the Emotion Director: it gates every change (persistence 400 ms,
hysteresis 400 ms, recovery cooldown 1500 ms, valence waypoint). Rapid key
presses are honestly BLOCKED and the HUD shows why - that is the existing
transition engine doing its job, not a defect. HAPPY -> SAD always routes
through calm (the existing valence-waypoint rule).

Run:
    py _show_les09b2_expression_polish.py                # windowed, until ESC
    py _show_les09b2_expression_polish.py --seconds 120  # auto-quit
    py _show_les09b2_expression_polish.py --smoke 2.0    # headless: all emotions
                                                          # + transitions, no window

This showcase makes NO claims about animation quality - it exists so a
human can judge whether the polish changes improve the visual narrative.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import pygame

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from les.choreography import (  # noqa: E402
    ChoreographyPlan,
    EmotionChoreographyBridge,
    EmotionChoreographyDirector,
    EmotionChoreographyRunner,
)
from les.director.emotion_director import (  # noqa: E402
    DefaultEmotionDirector,
    EmotionInput,
)
from les.integration import RealEngineDriver  # noqa: E402
from les.memory.behavior_memory import BehaviorMemory  # noqa: E402
from les.world.world_state import WorldState  # noqa: E402
from eyes.engine.config import OverlayConfig  # noqa: E402

EMOTION_KEYS = {"1": "calm", "2": "happy", "3": "sad", "4": "thinking", "5": "sleepy"}
TRANSITION_KEYS = {
    "c": "happy",    # Calm -> Happy
    "s": "sad",      # Happy -> Sad (routes through calm)
    "d": "calm",     # Sad -> Calm
    "t": "thinking",  # Calm -> Thinking
    "r": "calm",     # Thinking -> Calm
    "w": "calm",     # SLEEPY -> Calm (wake-up)
}
EMOTION_LABELS = {"calm": "1 CALM", "happy": "2 HAPPY", "sad": "3 SAD",
                  "thinking": "4 THINKING", "sleepy": "5 SLEEPY"}
SHOWCASE_SEED = 20260810

# Legacy cue configuration (before LES-09B.4's spatial fix), expressed
# in the LES-09B.5 OverlayConfig schema.
#
# Reproduced faithfully in the NEW schema: the old 18 px thinking scale
# (ratio 18/75 at eye_radius 75), ZERO clearance margin (the old anchor
# sat right at the eye silhouette - the overlap bug), and the old ZZZ
# band that overlapped the eye region. Q compares this against the
# LES-09B.5 perimeter-anchored, clearance-margin placement.
LEGACY_OVERLAY = OverlayConfig(
    thinking_cue_scale_ratio=0.24,      # 18.0 px at eye_radius 75
    thinking_cue_eye="right",
    thinking_cue_perimeter="outer_top",
    thinking_cue_clearance_ratio=0.0,   # old: no clearance margin
    thinking_orbital_amplitude_x=6.0,
    thinking_orbital_amplitude_y=4.0,
    thinking_cue_lifetime_ms=0.0,
    thinking_cue_fade_in_ms=400.0,
    thinking_cue_fade_out_ms=500.0,
    sleepy_cue_scale_base=12.0,
    sleepy_cue_min_lifetime_s=2.0,
    sleepy_cue_max_lifetime_s=3.0,
    sleepy_cue_x_min_ratio=0.3,         # old band: overlapped the eye
    sleepy_cue_x_max_ratio=0.9,
    sleepy_cue_y_min_ratio=0.0,
    sleepy_cue_y_max_ratio=0.3,
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def _load_font(size: int) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("consolas,monospace,courier", size)
    except Exception:
        return pygame.font.Font(None, size)


class ChoreographyShowcase:
    """Windowed (or headless) harness for the LES-09B.2 pipeline."""

    def __init__(self, headless: bool = False, seed: int = SHOWCASE_SEED) -> None:
        pygame.init()
        self.headless = headless

        # --- Real engine + the full LES pipeline ---------------------------
        self.driver = RealEngineDriver.for_face()
        self.engine = self.driver.engine  # type: ignore[assignment]

        self.world = WorldState()
        self.memory = BehaviorMemory()
        self.emotion_director = DefaultEmotionDirector(self.world, self.memory)
        self.runner = EmotionChoreographyRunner(
            director=EmotionChoreographyDirector(rng=random.Random(seed)),
            bridge=EmotionChoreographyBridge(),
        )
        self.runner.bridge.attach(self.driver)

        # --- Legacy / polished cue toggle ---------------------------------
        self.legacy_cues = False
        self._polished_overlay = self.engine.config.overlay

        # LES-09B.3: attention-preservation demo (gaze beats suppressed).
        self.attention_active = False

        # --- Display -------------------------------------------------------
        if headless:
            w, h = self.engine.config.display.width, self.engine.config.display.height
            self.screen = pygame.Surface((w, h))
            self.engine.composer.attach_surface(self.screen)
        else:
            self.engine.init_video(windowed=True)
            self.screen = self.engine.composer._screen  # type: ignore[assignment]
            pygame.display.set_caption(
                "LES-09B.2 + LES-09B.3 Expression Polish Showcase "
                "(real FaceEngine, Sleepy choreography)"
            )

        self.font = _load_font(14)
        self.clock = pygame.time.Clock()

        # --- Clock / state -------------------------------------------------
        self.elapsed_ms = 0.0
        self.elapsed_s = 0.0
        self.requested: Optional[str] = "calm"   # held target (ingested/tick)
        self.last_plan: Optional[ChoreographyPlan] = None
        self.plan_start_ms = 0.0
        self.observed: List[str] = [str(self.engine.current_state)]
        self.command_log: List[Tuple[float, str]] = []

    # ------------------------------------------------------------------
    # Read-only engine telemetry
    # ------------------------------------------------------------------
    def _eye_engine(self):
        return self.engine.mixer.eye_engine._engine  # type: ignore[attr-defined]

    def _gaze_now(self) -> Tuple[float, float]:
        return self._eye_engine().look_controller.current_normalized

    def _blink_weight(self) -> float:
        return self._eye_engine().blink_controller.blink_weight

    def _overlay_renderer(self):
        """The eyes-engine OverlayRenderer actually used by the composer.

        Honest path: FaceComposer -> FaceOverlayRenderer -> eye_overlay
        (face/effects/overlay_renderer.py wraps the eyes OverlayRenderer
        and composes it every frame in face_composer.compose()).
        """
        return self.engine.composer.overlay_renderer.eye_overlay

    def _thinking_cue_info(self) -> Tuple[bool, float, Tuple[float, float]]:
        """(visible, scale, anchor_position) for the thinking '?' cue.

        scale is DERIVED from the real eye geometry (LES-09B.4:
        ratio * eye_radius, ~half the eye height). The anchor is the
        pose-derived face-space position the renderer uses this frame.
        """
        try:
            overlay = self._overlay_renderer()
            visible = (
                overlay._thinking_particle is not None
                and not overlay._thinking_particle.dead
                and self.engine.current_state == "thinking"
            )
            scale = overlay.thinking_scale()
            pose = self.engine.mixer.get_final_pose()
            ax, ay = overlay.thinking_anchor(pose)
            return (visible, scale, (ax, ay))
        except Exception:
            return (False, 0.0, (0.0, 0.0))

    def _sleepy_cue_info(self) -> Tuple[int, float]:
        """(zzz_particle_count, zzz_scale_base) for the sleepy ZZZ cue.

        Read-only engine telemetry: the ZZZ particles live in the engine's
        OverlayRenderer (never touched by LES). The count tells a human
        reviewer whether the cue is active while sleepy.
        """
        try:
            overlay = self._overlay_renderer()
            alive = [p for p in overlay._sleepy_particles if not p.dead]
            return (len(alive), overlay.overlay_config.sleepy_cue_scale_base)
        except Exception:
            return (0, 0.0)

    # ------------------------------------------------------------------
    # Requests
    # ------------------------------------------------------------------
    def request(self, emotion: str) -> None:
        self.requested = emotion
        _log(f"[showcase] t={self.elapsed_s:7.2f}s  REQUEST -> {emotion.upper()}")

    def release(self) -> None:
        self.requested = None
        _log(f"[showcase] t={self.elapsed_s:7.2f}s  RELEASE - no detection "
             "(neutral fallback will recover to calm)")

    def toggle_cues(self) -> None:
        """Toggle between polished (default) and legacy cue sizes."""
        self.legacy_cues = not self.legacy_cues
        overlay = self._polished_overlay
        if self.legacy_cues:
            overlay = LEGACY_OVERLAY
        self.engine.config.overlay = overlay
        # Hot-swap the live composer overlay renderer as well.
        try:
            self._overlay_renderer().set_overlay_config(overlay)
        except Exception:
            pass
        label = ("LEGACY (18px scale, zero clearance, old ZZZ band - "
                 "intentional old-overlap demo)" if self.legacy_cues
                 else "POLISHED (LES-09B.5 perimeter-anchored, "
                       "clearance-margin)")
        _log(f"[showcase] t={self.elapsed_s:7.2f}s  CUES: {label}")

    def toggle_attention(self) -> None:
        """Toggle attention-preservation mode (LES-09A.2 idle contract)."""
        self.attention_active = not self.attention_active
        # Honest note: the flag applies to plans scheduled from now on - a
        # plan already on the timeline (e.g. a sleepy plan scheduled before
        # the toggle) keeps its already-planned steps until replaced.
        mode = ("PRESERVED (gaze beats suppressed - applies to plans "
                "scheduled from now on)" if self.attention_active
                else "FREE (autonomous gaze allowed)")
        _log(f"[showcase] t={self.elapsed_s:7.2f}s  ATTENTION: {mode}")

    # ------------------------------------------------------------------
    # Manual gaze override (arrow keys) - LES-09B.4 inspection tool
    # ------------------------------------------------------------------
    def _gaze_override_from_keys(self, keys) -> Optional[Tuple[float, float]]:
        """Extreme gaze target from held arrow keys, or None when idle.

        Arrows map to the normalized look_at extremes; diagonals combine
        (e.g. UP+LEFT -> (0.0, 0.0)). The target is applied every frame
        while held, so the engine's look spring drives the eyes there and
        the cue placement can be inspected while the eyes are moving.
        """
        x, y, changed = 0.5, 0.5, False
        if keys[pygame.K_LEFT]:
            x, changed = 0.0, True
        if keys[pygame.K_RIGHT]:
            x, changed = 1.0, True
        if keys[pygame.K_UP]:
            y, changed = 0.0, True
        if keys[pygame.K_DOWN]:
            y, changed = 1.0, True
        return (x, y) if changed else None

    # ------------------------------------------------------------------
    # One frame
    # ------------------------------------------------------------------
    def frame(self, dt_ms: float, gaze_override: Optional[Tuple[float, float]] = None) -> None:
        self.gaze_override_active = gaze_override is not None
        self.elapsed_ms += dt_ms
        self.elapsed_s = self.elapsed_ms / 1000.0

        # 1. Advance the caller clock + world, feed the held detection.
        self.world.set_timestamp(self.elapsed_ms)
        if self.requested is not None:
            self.emotion_director.ingest(
                EmotionInput(
                    source="showcase",
                    emotion=self.requested,
                    confidence=1.0,
                    timestamp_ms=self.elapsed_ms,
                )
            )

        # 2. The pipeline tick: director -> runner -> scheduler -> engine.
        self.emotion_director.update(dt_ms)
        internal = self.emotion_director.internal_state()
        plan = self.runner.update(internal, attention_active=self.attention_active)
        if plan is not None:
            self.last_plan = plan
            self.plan_start_ms = self.elapsed_ms
            _log(
                f"[choreo] t={self.elapsed_s:7.2f}s  plan={plan.emotion} "
                f"variant={plan.variant} total={plan.total_duration_ms:.0f}ms "
                f"steps={len(plan.steps)}"
            )

        commands = self.runner.bridge.scheduler.advance(dt_ms)
        if commands:
            self.runner.bridge.apply_commands(commands)
            for cmd in commands:
                self.command_log.append((self.elapsed_s, f"{cmd.command}{cmd.args}"))
                _log(f"[engine] t={self.elapsed_s:7.2f}s  EngineCommand -> {cmd.command}{cmd.args}")

        # 2b. Manual gaze override (arrow keys): while held, drive the
        # engine's look controller to the extreme target AFTER the
        # scheduler, so the override wins this frame and the cue
        # placement can be inspected at every gaze position.
        if gaze_override is not None:
            self._eye_engine().look_controller.look_at(*gaze_override)

        # 3. Step + render the real engine (existing engine APIs only).
        eye_pose, mouth_params, ctx = self.engine.step(dt_ms)
        self.engine.composer.compose(self.screen, eye_pose, mouth_params, ctx)

        if not self.headless:
            self._draw_hud(internal)
            pygame.display.flip()

        if self.engine.current_state != self.observed[-1]:
            self.observed.append(str(self.engine.current_state))
            _log(
                f"[showcase] t={self.elapsed_s:7.2f}s  TRANSITION "
                f"{self.observed[-2]} -> {self.engine.current_state}"
            )

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def _current_beat(self):
        """(index, beat, elapsed_within_beat_ms) for the active plan.

        Returns ``None`` when there is no plan at all. When the current
        plan carries ZERO choreography beats (a fallback plan - e.g. a
        genuinely non-choreographed emotion such as surprised - it has
        scheduler steps but no authored beats), returns
        ``("fallback", None, 0.0)`` so the HUD can report the plan
        honestly instead of indexing into an empty beat collection.
        """
        if self.last_plan is None:
            return None
        if not self.last_plan.beats:
            return ("fallback", None, 0.0)
        t = self.elapsed_ms - self.plan_start_ms
        idx, beat = 0, self.last_plan.beats[0]
        for i, b in enumerate(self.last_plan.beats):
            if b.offset_ms <= t:
                idx, beat = i, b
            else:
                break
        return (idx, beat, max(0.0, t - beat.offset_ms))

    def _draw_hud(self, internal) -> None:
        bright = (0, 230, 150)
        text = (185, 190, 205)
        dim = (95, 105, 120)
        cyan = (120, 200, 255)
        yel = (235, 215, 120)
        red = (255, 120, 120)
        orange = (255, 180, 80)

        emotion = internal.emotion
        lines: List[Tuple[str, Tuple[int, int, int]]] = []
        lines.append((f"LES-09B.2 + LES-09B.3  EXPRESSION POLISH  "
                      f"(real FaceEngine)", bright))
        lines.append((
            f"emotion={str(emotion).upper():9s}  engine_state={self.engine.current_state.upper():9s}  "
            f"t={self.elapsed_s:6.1f}s",
            text,
        ))
        lines.append((
            f"requested={str(self.requested).upper():9s}"
            + (f"  (held)" if self.requested is not None else "  (released -> auto-recovery)"),
            yel if self.requested is not None else dim,
        ))
        if internal.transition_blocked:
            lines.append((f"transition BLOCKED: {internal.blocked_reason}", red))
        elif internal.transition_in_progress:
            lines.append((f"transition: {internal.transition_reason}", cyan))
        else:
            lines.append((f"holding (confidence {internal.confidence:.2f})", dim))

        if self.last_plan is not None:
            plan = self.last_plan
            lines.append((
                f"choreography={plan.emotion}  variant={plan.variant}  "
                f"total={plan.total_duration_ms / 1000.0:.1f}s  "
                f"beats={len(plan.beats)}",
                bright,
            ))
            beat_info = self._current_beat()
            if beat_info is None:
                # No plan beat to show (should not happen when a plan
                # exists, but stay defensive - never crash the HUD).
                lines.append(("beat: (no beat data)", dim))
            elif beat_info[1] is None:
                # Fallback plan (e.g. surprised): the plan has scheduler
                # steps but zero authored choreography beats. Report that
                # honestly - never fabricate a beat for the HUD.
                lines.append((
                    "beat: fallback / no choreography beats "
                    "(engine-state execution)",
                    dim,
                ))
            else:
                idx, beat, within = beat_info
                lines.append((
                    f"beat {idx + 1}/{len(plan.beats)}: {beat.label}  "
                    f"({beat.kind.value})",
                    cyan,
                ))
                lines.append((
                    f"elapsed_in_beat={within / 1000.0:5.2f}s   "
                    f"beat_offset={beat.offset_ms / 1000.0:.2f}s   "
                    f"command={beat.command or 'hold'}",
                    text,
                ))
        else:
            lines.append(("choreography=(none yet)", dim))

        # Thinking cue diagnostics (only when thinking).
        if self.engine.current_state == "thinking":
            q_visible, q_scale, (q_ax, q_ay) = self._thinking_cue_info()
            oc_live = self._overlay_renderer().overlay_config
            lines.append((
                f"? cue visible={q_visible}   scale={q_scale:.0f}  "
                f"anchor=({q_ax:.0f},{q_ay:.0f})  "
                f"[{oc_live.thinking_cue_eye}/{oc_live.thinking_cue_perimeter}]",
                orange if q_visible else dim,
            ))

        gx, gy = self._gaze_now()

        # Sleepy diagnostics (LES-09B.3): ZZZ particles + gaze + blink.
        if self.engine.current_state == "sleepy":
            z_count, z_scale = self._sleepy_cue_info()
            lines.append((
                f"ZZZ particles={z_count}  scale_base={z_scale:.0f}  "
                f"gaze=({gx:.2f},{gy:.2f})  blink_w={self._blink_weight():.3f}",
                orange if z_count > 0 else dim,
            ))

        if self.attention_active:
            lines.append(("attention: PRESERVED - gaze beats suppressed on "
                          "plans scheduled from now on (LES-09A.2 idle "
                          "contract)", yel))

        if self.gaze_override_active:
            lines.append(("gaze OVERRIDE active - arrow key held "
                          "(manual inspection; release to hand gaze back "
                          "to the choreography)", yel))

        lines.append((
            f"gaze=({gx:.2f},{gy:.2f})  blink_w={self._blink_weight():.3f}  "
            f"active_plan={self.runner.bridge.scheduler.active_behavior}  "
            f"cues={'LEGACY' if self.legacy_cues else 'POLISHED'}",
            dim,
        ))

        for i, (txt, col) in enumerate(lines):
            surf = self.font.render(txt, True, col)
            self.screen.blit(surf, (14, 12 + i * 18))

        help1 = ("1 CALM  2 HAPPY  3 SAD  4 THINKING  5 SLEEPY    "
                 "C calm->happy  S happy->sad  D sad->calm  T calm->thinking  "
                 "R thinking->calm  W wake sleepy->calm")
        help2 = "N release  Q cue sizes  A attention  ARROWS hold=extreme gaze  ESC quit"
        h1 = self.font.render(help1, True, dim)
        h2 = self.font.render(help2, True, dim)
        self.screen.blit(h1, (14, self.engine.config.display.height - 34))
        self.screen.blit(h2, (14, self.engine.config.display.height - 16))

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------
    def handle_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False
        ch = pygame.key.name(key)
        if ch in EMOTION_KEYS:
            self.request(EMOTION_KEYS[ch])
        elif ch in TRANSITION_KEYS:
            self.request(TRANSITION_KEYS[ch])
        elif ch == "n":
            self.release()
        elif ch == "q":
            self.toggle_cues()
        elif ch == "a":
            self.toggle_attention()
        return True


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def run_windowed(seconds: Optional[float] = None) -> int:
    show = ChoreographyShowcase(headless=False)
    running = True
    _log("[showcase] WINDOWED - real FaceEngine + full LES pipeline "
         "(EmotionDirector -> Choreography -> Scheduler -> Driver)")
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if not show.handle_key(event.key):
                    running = False
        if not running:
            break
        dt_ms = min(show.clock.tick(60), 66.0)
        gaze = show._gaze_override_from_keys(pygame.key.get_pressed())
        show.frame(dt_ms, gaze_override=gaze)
        if seconds is not None and show.elapsed_s >= seconds:
            _log(f"[showcase] --seconds {seconds} reached, quitting")
            running = False
    pygame.quit()
    return 0


def run_smoke(seconds_per_emotion: float = 2.0) -> int:
    """Headless verification: every emotion + every transition key + release.

    Exercises the identical frame path (ingest -> director -> runner ->
    scheduler -> commands -> engine.step -> compose) with no window, and
    asserts the engine actually reaches the requested states.

    LES-09B.3: sleepy now produces an AUTHORED choreography (named
    variant, real beats) - the zero-beat fallback HUD path is verified
    with a genuinely non-choreographed emotion (surprised) instead.
    """
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    show = ChoreographyShowcase(headless=True)
    fails: List[str] = []

    def run_until(requested: str, condition, max_s: float = 12.0) -> bool:
        show.request(requested)
        deadline = show.elapsed_s + max_s
        while show.elapsed_s < deadline:
            show.frame(16.0)
            if condition():
                return True
        return False

    _log(f"[smoke] headless run: {seconds_per_emotion}s per emotion + transitions (real FaceEngine)")
    for emotion in ("calm", "happy", "sad", "thinking", "sleepy"):
        frames = int(seconds_per_emotion * 60.0)
        show.request(emotion)
        for _ in range(frames):
            show.frame(16.0)
        reached = show.engine.current_state == emotion
        _log(f"[smoke] {emotion:9s} engine_state={show.engine.current_state.upper():9s} "
             f"choreo={show.runner.last_plan.emotion if show.runner.last_plan else 'none'}"
             f"{'  ok' if reached else '  FAIL'}")
        if not reached:
            fails.append(emotion)

    # Transition pass (each via a real request through the Emotion Director).
    for src, dst in [("calm", "happy"), ("happy", "sad"), ("sad", "calm"),
                     ("calm", "thinking"), ("thinking", "calm")]:
        ok = run_until(dst, lambda d=dst: show.engine.current_state == d)
        _log(f"[smoke] transition {src:8s} -> {dst:8s}: {'ok' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"{src}->{dst}")

    # Release: neutral fallback should recover to calm without any request.
    ok = run_until("sad", lambda: show.engine.current_state == "sad")
    show.release()
    deadline = show.elapsed_s + 8.0
    recovery_ok = False
    while show.elapsed_s < deadline:
        show.frame(16.0)
        if show.engine.current_state == "calm":
            recovery_ok = True
            break
    _log(f"[smoke] release -> auto-recovery to calm: {'ok' if recovery_ok else 'FAIL'}")
    if not recovery_ok:
        fails.append("auto-recovery")

    # LES-09B.3: sleepy must now produce an AUTHORED choreography (named
    # variant, real beats), and the HUD must render it without crashing.
    ok = run_until("sleepy", lambda: show.engine.current_state == "sleepy")
    sleepy_plan = show.runner.last_plan
    _log(f"[smoke] sleepy authored plan: variant={sleepy_plan.variant if sleepy_plan else 'none'} "
         f"beats={len(sleepy_plan.beats) if sleepy_plan else 0} "
         f"steps={len(sleepy_plan.steps) if sleepy_plan else 0}")
    sleepy_ok = (
        sleepy_plan is not None
        and sleepy_plan.variant != "fallback"
        and len(sleepy_plan.beats) > 0
    )
    if not sleepy_ok:
        fails.append("sleepy-authored-plan")
        _log("[smoke] sleepy authored plan: FAIL (expected named variant + beats)")
    else:
        try:
            beat_info = show._current_beat()
            _log(f"[smoke] sleepy HUD: _current_beat -> {beat_info}")
            show._draw_hud(show.emotion_director.internal_state())
            _log("[smoke] sleepy HUD: drew authored beats without crashing - ok")
        except Exception as exc:
            fails.append("sleepy-hud")
            _log(f"[smoke] sleepy HUD: EXCEPTION {type(exc).__name__}: {exc} - FAIL")

    # Fallback-plan HUD coverage (LES-09B.2 behavior preserved): a
    # genuinely NON-choreographed emotion (surprised) runs a FALLBACK plan
    # (scheduler steps, zero choreography beats). The HUD must report it
    # honestly and must NEVER crash on ``beats[0]`` of an empty collection.
    ok = run_until("surprised", lambda: show.engine.current_state == "surprised")
    fb_plan = show.runner.last_plan
    _log(f"[smoke] surprised fallback plan: variant={fb_plan.variant if fb_plan else 'none'} "
         f"beats={len(fb_plan.beats) if fb_plan else 0} "
         f"steps={len(fb_plan.steps) if fb_plan else 0}")
    hud_ok = True
    if fb_plan is None or fb_plan.variant != "fallback" or len(fb_plan.beats) != 0:
        hud_ok = False
        _log("[smoke] fallback-plan HUD: surprised did not produce a zero-beat fallback plan - FAIL")
    else:
        try:
            beat_info = show._current_beat()
            if beat_info is None or beat_info[1] is not None:
                hud_ok = False
                _log(f"[smoke] fallback-plan HUD: _current_beat returned {beat_info} - FAIL")
            else:
                _log(f"[smoke] fallback-plan HUD: _current_beat -> {beat_info} (no crash)")
            # Exercise the exact HUD draw path on the fallback plan.
            show._draw_hud(show.emotion_director.internal_state())
        except Exception as exc:
            hud_ok = False
            _log(f"[smoke] fallback-plan HUD: EXCEPTION {type(exc).__name__}: {exc} - FAIL")
    _log(f"[smoke] fallback-plan HUD (surprised): {'ok' if hud_ok else 'FAIL'}")
    if not hud_ok:
        fails.append("fallback-hud")

    # Q toggle sanity (LES-09B.4 schema: scale is a ratio of eye radius).
    show.toggle_cues()
    _log(f"[smoke] Q toggle -> legacy cues: {show.legacy_cues}  "
         f"thinking_scale_ratio={show._polished_overlay.thinking_cue_scale_ratio}  "
         f"clearance={show._polished_overlay.thinking_cue_clearance_ratio}")
    show.toggle_cues()
    _log(f"[smoke] Q toggle -> polished cues: {not show.legacy_cues}  "
         f"thinking_scale_ratio={show._polished_overlay.thinking_cue_scale_ratio}  "
         f"clearance={show._polished_overlay.thinking_cue_clearance_ratio}")

    # LES-09B.4 gaze-override path: while an extreme target is held, the
    # engine's look controller must be driven there and the frame must not
    # crash (the HUD reads the pose-derived thinking anchor every frame).
    ee = show._eye_engine()
    before = ee.look_controller.current_normalized
    gaze_ok = True
    for _ in range(40):
        show.frame(16.0, gaze_override=(0.0, 0.0))
    after = ee.look_controller.current_normalized
    dist_moved = max(abs(before[0] - after[0]), abs(before[1] - after[1]))
    gaze_ok = dist_moved > 0.15
    _log(f"[smoke] gaze override (0,0): normalized {tuple(round(v, 2) for v in before)} -> "
         f"{tuple(round(v, 2) for v in after)}  dist={dist_moved:.2f}  "
         f"{'ok' if gaze_ok else 'FAIL'}")
    if not gaze_ok:
        fails.append("gaze-override")

    _log(f"[smoke] observed states: {' -> '.join(show.observed)}")
    _log(f"[smoke] RESULT: {'OK' if not fails else 'FAILED: ' + str(fails)}")
    pygame.quit()
    return 1 if fails else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="LES-09B.2 expression polish visual validation showcase"
    )
    parser.add_argument("--seconds", type=float, default=None,
                        help="windowed: auto-quit after N seconds (default: until ESC)")
    parser.add_argument("--smoke", nargs="?", const=2.0, type=float, default=None,
                        metavar="SECONDS", help="headless: all emotions + transitions, no window")
    args = parser.parse_args(argv)
    if args.smoke is not None:
        return run_smoke(seconds_per_emotion=float(args.smoke))
    return run_windowed(seconds=args.seconds)


if __name__ == "__main__":
    sys.exit(main())