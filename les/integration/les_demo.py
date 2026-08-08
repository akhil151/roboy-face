"""
LES integration demo (LES-08.5) - the LES pipeline driving the REAL engine.

The demo executes the mission sequence entirely through the LES pipeline:

    BehaviorIntent -> schedule() -> Timeline -> Scheduler.advance()
        -> EngineCommand -> RealEngineDriver -> FaceEngine (real, frozen)

Visible sequence:
    1. Calm      2. Happy (with blink)   3. Blink
    4. Calm      5. Surprised            6. Calm

Rendering reuses the existing FaceEngine compositor - nothing is
duplicated, and eyes/ + face/ are never modified.

Modes:
    * windowed (default): pygame window, HUD overlay, ESC / close to quit.
    * --headless: renders offscreen, saves a screenshot per phase, and
      prints timestamped telemetry (state / blink weight / look target).
      Use for CI - nothing is claimed visually.

Run:
    py les/integration/les_demo.py [--seconds 12] [--headless] [--outdir path]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import pygame

# Ensure repository root is importable (mirrors eyes/demo.py and face/demo.py,
# which use absolute imports because they are run as top-level scripts).
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from les.director.behavior_director import BehaviorIntent
from les.timeline.scheduler import BehaviorPlan, DefaultScheduler, PlanStep
from les.integration import RealEngineDriver

# ---------------------------------------------------------------------------
# Demo content - plan steps use ONLY the documented engine vocabulary and
# the real engine's official states (calm / happy / surprised). No geometry.
# ---------------------------------------------------------------------------

DEMO_PLANS: dict = {
    "calm_start": BehaviorPlan(
        name="calm_start",
        steps=(PlanStep(0.0, "set_state", ("calm", 350.0)),),
    ),
    "happy_beat": BehaviorPlan(
        name="happy_beat",
        steps=(
            PlanStep(0.0, "set_state", ("happy", 350.0)),
            PlanStep(600.0, "blink"),
        ),
    ),
    "blink_beat": BehaviorPlan(
        name="blink_beat",
        steps=(PlanStep(0.0, "blink"),),
    ),
    "calm_mid": BehaviorPlan(
        name="calm_mid",
        steps=(PlanStep(0.0, "set_state", ("calm", 300.0)),),
    ),
    "surprised_beat": BehaviorPlan(
        name="surprised_beat",
        steps=(PlanStep(0.0, "set_state", ("surprised", 180.0)),),
    ),
    "calm_end": BehaviorPlan(
        name="calm_end",
        steps=(PlanStep(0.0, "set_state", ("calm", 400.0)),),
    ),
}

# (intent, wall-clock seconds after start)
DEMO_PHASES: List[Tuple[str, float]] = [
    ("calm_start", 0.0),
    ("happy_beat", 1.5),
    ("blink_beat", 3.0),
    ("calm_mid", 4.0),
    ("surprised_beat", 5.5),
    ("calm_end", 7.0),
]


def _load_font(size: int) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("consolas,monospace,courier", size)
    except Exception:
        return pygame.font.Font(None, size)


def run_demo(seconds: float = 12.0, headless: bool = False, outdir: Optional[Path] = None) -> int:
    """Run the LES-driven demo for ``seconds`` wall-clock seconds.

    Returns the number of observed state transitions (0 = failed to run).
    """
    pygame.init()

    # --- Real engine + LES pipeline (the ONLY driver of the face) ----------
    face = RealEngineDriver.for_face()  # wraps a real FaceEngine
    engine = face.engine  # type: ignore[assignment]
    scheduler = DefaultScheduler(plans=DEMO_PLANS)
    scheduler.attach(face)

    # --- Display -----------------------------------------------------------
    screen: Optional[pygame.Surface]
    if headless:
        w, h = engine.config.display.width, engine.config.display.height
        screen = pygame.Surface((w, h))
        engine.composer.attach_surface(screen)
        print(f"[demo] HEADLESS mode - offscreen {w}x{h}, screenshots -> {outdir or 'stdout telemetry only'}")
    else:
        engine.init_video(windowed=True)
        screen = engine.composer._screen
        pygame.display.set_caption("LES -> Real Engine Integration Demo (LES-08.5)")
        print("[demo] WINDOWED mode - ESC or close to quit")

    clock = pygame.time.Clock()
    font = _load_font(14)

    phase_index = 0
    elapsed_s = 0.0
    scheduler_clock_ms = 0.0
    running = True
    observed: List[str] = []
    last_state: Optional[str] = engine.current_state
    last_telemetry_s = -1.0
    saved_phases: set[str] = set()

    print("[demo] LES pipeline driving the REAL FaceEngine")
    print("[demo] phases:", [(name, t) for name, t in DEMO_PHASES])
    observed.append(str(last_state))

    while running and elapsed_s < seconds:
        # --- Events (windowed) --------------------------------------------
        if not headless:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
            if not running:
                break

        # --- Wall-clock timing (caller-owned; drives the LES clock) --------
        dt_ms = min(clock.tick(60), 66.0)
        dt_s = dt_ms / 1000.0
        elapsed_s += dt_s
        scheduler_clock_ms += dt_ms

        # --- Schedule the next phase when its wall time arrives ------------
        while phase_index < len(DEMO_PHASES) and elapsed_s >= DEMO_PHASES[phase_index][1]:
            name, _t = DEMO_PHASES[phase_index]
            scheduler.schedule(
                BehaviorIntent(behavior_name=name, priority=0.5, urgency=1.0)
            )
            print(f"[demo] t={elapsed_s:6.2f}s  schedule intent={name!r}")
            phase_index += 1

        # --- The pipeline tick: advance -> EngineCommands -> real engine ----
        commands = scheduler.advance(dt_ms)
        if commands:
            scheduler.apply_commands(commands)
            for cmd in commands:
                print(f"[demo] t={elapsed_s:6.2f}s  EngineCommand -> {cmd.command}{cmd.args}")

        # --- Step + render the real engine (existing engine APIs only) -----
        eye_pose, mouth_params, ctx = engine.step(dt_ms)
        assert screen is not None
        engine.composer.compose(screen, eye_pose, mouth_params, ctx)

        if headless:
            # Screenshot per phase (named after the phase just scheduled,
            # whose plan is now executing), then telemetry.
            if phase_index > 0 and phase_index - 1 < len(DEMO_PHASES):
                current_phase = DEMO_PHASES[phase_index - 1][0]
            else:
                current_phase = DEMO_PHASES[0][0]
            if current_phase not in saved_phases and phase_index > 0:
                saved_phases.add(current_phase)
                if outdir is not None:
                    outdir.mkdir(parents=True, exist_ok=True)
                    path = outdir / f"phase_{phase_index}_{current_phase}.png"
                    pygame.image.save(screen, str(path))
                    print(f"[demo] saved screenshot -> {path}")
            if int(elapsed_s) != last_telemetry_s:
                last_telemetry_s = int(elapsed_s)
                bw = engine.mixer.eye_engine._engine.blink_controller.blink_weight
                look = engine.mixer.eye_engine._engine.look_controller.current_normalized
                print(
                    f"[demo] t={elapsed_s:6.2f}s  state={engine.current_state.upper():9s}"
                    f"  blink_w={bw:5.3f}  look=({look[0]:.2f},{look[1]:.2f})"
                )
        else:
            # HUD overlay (windowed only) + flip.
            hud = font.render(
                f"LES -> REAL ENGINE   phase {phase_index}/{len(DEMO_PHASES)}  "
                f"state={engine.current_state.upper()}  sched={scheduler_clock_ms:7.0f}ms",
                True,
                (0, 230, 150),
            )
            screen.blit(hud, (16, 12))
            hint = font.render("ESC quit", True, (95, 95, 110))
            screen.blit(hint, (16, 34))
            pygame.display.flip()

        # --- Track observed transitions -------------------------------------
        if engine.current_state != last_state:
            print(f"[demo] t={elapsed_s:6.2f}s  TRANSITION {last_state} -> {engine.current_state}")
            observed.append(str(engine.current_state))
            last_state = engine.current_state

    pygame.quit()

    print("[demo] observed transitions:", " -> ".join(observed))
    return max(0, len(observed) - 1)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="LES -> Real Engine integration demo")
    parser.add_argument("--seconds", type=float, default=12.0, help="run duration (s)")
    parser.add_argument("--headless", action="store_true", help="offscreen render + telemetry")
    parser.add_argument("--outdir", type=Path, default=None, help="screenshot output dir (headless)")
    args = parser.parse_args(argv)
    return run_demo(seconds=args.seconds, headless=args.headless, outdir=args.outdir)


if __name__ == "__main__":
    sys.exit(main())
