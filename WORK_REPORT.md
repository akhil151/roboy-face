# Roboy Face Engine — Complete Work Report

**Branch:** `feature/living-expression-system`
**Date:** 2026-08-08
**Report status:** Current — reflects the working tree today. All five verification suites re-run and green on this date.

---

## 1. What this project is

The **Roboy Face Engine** is a Python animation + behavior system for a robotic
face. It is layered:

```
LES (Living Expression System)   les/      ← decides WHAT the robot feels & does
        ↓
Animation Engine (v1.0 STABLE)   eyes/     ← decides HOW feelings are drawn
        ↓
Face / Mouth rendering           face/     ← draws them
```

| Layer | Role | Status |
|---|---|---|
| `eyes/` | Emotion animation engine (eye states, blends, motion primitives, personality) | v1.0 STABLE (frozen) |
| `face/` | Face composer + mouth system (lip shapes, speech sync) | Implemented |
| `les/` | Behavior & emotion orchestration (directors, memory, world state, timeline, scheduler, engine integration, idle decision + execution layers) | **Active work** — orchestration committed; idle decision + execution layers implemented, uncommitted |

---

## 2. Git history — phases of work

The branch contains **11 commits**. Each maps to a work phase:

| Commit | Message | Phase |
|---|---|---|
| `822a300` | first commit | **Phase 1** — Eyes foundation: `eyes/__init__.py`, animation base class, the 11 emotion animations, demo. |
| `29d6604` | second commit | **Phase 2** — Engine evolution: richer `base.py`, emotion polish. |
| `22ca290` | third commit | **Phase 2** — Core engine: `expressive.py`, `engine/` package (`animation_clips`, `emotion_blending`, `micro_behaviours`, `motion_curves`, `motion_primitives`, `personality`). |
| `f4daaa8` | fourth push | **Phase 3** — Animation refactor: all 11 emotion files reworked onto the new engine. |
| `b65a5f0` | five commit | **Phase 4** — Animation polish: richer per-emotion motion. |
| `102970b` | before alter: | **Phase 5** — `eyes/showcase.py` (~1,100 lines) — visual showcase/verification harness. |
| `385f77a` | seven push | **Phase 6** — Final polish: thinking / surprised / caring / happy / focus refinements. |
| `c742b8b` | review before | **Phase 7** — Mouth system: `face/mouth/` + face renderers + `test_mouth_phase4a_verify.py`. |
| `b9a490e` | feat(LES): complete behavior orchestration architecture | **Phase 8** — The `les/` package: directors, policies, memory, world state, personalities, behaviors, transitions + `_verify_behavior.py`. |
| `c814d9c` | feat(LES): implement timeline scheduler | **Phase 9 (LES-08)** — `Timeline` + `Scheduler` + `EngineCommand` / `EngineDriver` boundary + `_verify_les08_timeline_scheduler.py`. |
| `3fd8c8e` | feat(LES): integrate scheduler with real face engine | **Phase 9.5 (LES-08.5)** — `RealEngineDriver` adapter + `les_demo.py` + `_verify_les08_5_integration.py`. |

**Phase 10 (LES-09A.1, uncommitted):** the Natural Idle Decision Layer —
`les/behaviors/idle_policy.py` + `les/behaviors/idle_behavior.py`,
re-exported from `les.behaviors`, plus `_verify_les09a_idle.py`.

**Phase 11 (LES-09A.2, uncommitted):** Real Idle Execution Integration —
`les/behaviors/idle_execution.py` (`IdleExecutionBridge`) wires the idle
decisions into the existing Timeline → Scheduler → EngineCommand →
RealEngineDriver → FaceEngine pipeline; idle demo mode in `les_demo.py`;
`_verify_les09a2_idle_integration.py`.

---

## 3. `eyes/` — animation engine (v1.0 STABLE)

Frozen, stable layer. **Never modified by LES.**

- **Animations (11 emotions):** calm, caring, expressive, focus, happy,
  listening, sad, sleepy, speaking, surprised, thinking — each a class with
  its visual identity (openness, gaze drift, blink language, motion).
- **Engine subsystems:** animation clips, mixer, emotion blending, motion
  primitives, motion curves, micro behaviours, micro motion, blink controller,
  look controller, choreography, personality, spring/tween/easing, state
  machine, overlay renderer, render context.
- **Showcase:** `eyes/showcase.py` — visual verification of the engine.

Verification scripts: `test_choreography_verify.py`, `test_phase2a_verify.py`,
`test_phase2b4_verify.py`, `test_official_states_verify.py`,
`test_visual_identity_verify.py`.

---

## 4. `face/` — face composer + mouth system

- `face_composer.py`, `face_engine.py`, `face_mixer.py`, `face_renderer.py`,
  `face_showcase.py`, `render_context.py`.
- `mouth/`: `mouth_animation.py`, `mouth_renderer.py`, `mouth_shapes.py`,
  `speech_sync.py` — lip shapes + speech-lip sync (Phase 4a).
- Verification: `test_mouth_phase4a_verify.py`.

---

## 5. `les/` — Living Expression System (the current work)

**Status:** ~6,290 lines of Python across 35 files (plus 3 design bibles,
~3,550 lines of docs). The orchestration pipeline (Phases 8–9.5) is
committed; the idle decision layer (Phase 10) is implemented and awaiting
commit.

### 5.1 Architecture (as implemented)

```
World State ──────────────► Emotion Policy ──► Emotion Director
     │                                                │
     │                                        internal emotional state
     ▼                                                ▼
Behavior Memory ◄────── Behavior Policy ◄──── Behavior Director
     │                                                │
     └──────── record behavior/cooldowns              ▼
                                             BehaviorIntent / BehaviorRequest
                                                      │
                                                      ▼
                          Timeline ◄──── Scheduler ────► EngineCommand
                                                      │
                                                      ▼
                                          EngineDriver (protocol)
                                                      │
                                          RealEngineDriver (adapter)
                                                      ▼
                                     eyes/ + face/ (real, frozen engine)
```

### 5.2 Phase 8 — Behavior orchestration (committed `b9a490e`)

| Package | Files | Purpose |
|---|---|---|
| `les/__init__.py` | 184 | Facade, re-exports all contracts, `__version__ 0.1.0` |
| `config/` | `defaults.py` (60) | `LESConfig`, `DirectorConfig`, `TimelineConfig`, `BehaviorConfig` |
| `director/` | `emotion_director.py` (502) | EmotionDirector — hysteresis, persistence gates, confidence margin, valence waypoint, flicker prevention |
| | `emotion_policy.py` (170) | EmotionPolicy — priority, valence, transition margins |
| | `behavior_director.py` (619) | BehaviorDirector — arbitration, persistence/continuation, urgent interruption, max-hold anti-freeze, variant rotation |
| | `behavior_policy.py` (285) | BehaviorPolicy + `BehaviorRule` + 12-intent default ladder + `VariantRotation` |
| `memory/` | `behavior_memory.py` (377) | Facade: history + cooldowns + emotional state + context scalars |
| | `cooldowns.py` (119) | Named cooldown timers |
| | `emotional_state.py` (118) | Current/previous emotion + persistence |
| | `interaction_history.py` (150) | Time-ordered event history |
| `world/` | `world_state.py` (313) | Facade over perception/attention/interaction + sensor registry |
| | `perception_state.py`, `attention_state.py`, `interaction_state.py`, `value_quality.py` | SensorValue/ValueQuality model — every fact carries VALID/INVALID/UNKNOWN |
| `behaviors/` | idle, attention, curiosity, blink + ABC | Behavior interface contracts |
| `personality/` | `traits.py`, `profiles.py` | 6 trait axes + named profiles + provider protocol |
| `timeline/` | `timeline.py`, `scheduler.py` | TimelineEvent queue + Scheduler/EngineCommand/EngineDriver boundary |
| `transitions/` | `transition_director.py` | TransitionSpec + blend-duration heuristics |
| `docs/` | 3 design bibles + README | Behavior Spec, Emotion Bible, Interaction Bible — the design authority |

**The default behavior ladder** (tuned to the Interaction Bible Part 6):

| Intent | Priority | Preconditions |
|---|---|---|
| alert | 0.95 | emotion = surprised (non-interruptible, 600 ms) |
| listening | 0.95 | speech detected (up to 60 s) |
| comforting | 0.88 | touch active (non-interruptible, 1.5 s) |
| responding | 0.85 | robot speaking (non-interruptible, 30 s) |
| greeting | 0.80 | person + eye contact (non-interruptible, 800 ms) |
| thinking | 0.70 | emotion = thinking |
| playful | 0.60 | emotion = happy |
| celebrating | 0.60 | happy + speech |
| searching | 0.55 | face lost |
| confused | 0.45 | emotionally neutral |
| curious | 0.40 | person present |
| waiting | 0.30 | emotionally neutral |
| **idle** | — | **fallback only** (never a scored competitor) |

**Key mechanisms:** cooldowns with active-intent exemption; continuation
bonus (+0.12 in a 1.2 s window); urgent interruption (≥0.20 margin);
max-hold anti-freeze (checked before non-interruptible continuation);
emotion-paired transition recommendation; variant rotation (CYCLIC /
STICKY / AVOID_RECENT); idle fallback with `idle_fallback` reason; layered
emotion gates (persistence, hysteresis, recovery cooldown, valence
waypoint, confidence margin).

### 5.3 Phase 9 — Timeline Scheduler (committed `c814d9c`, LES-08)

- **`Timeline` / `DefaultTimeline`** — bounded, deterministic, time-ordered
  event queue. Strict `(start_ms, insertion-order)` ordering, caller-owned
  time (`advance(dt_ms)` only), capacity + horizon limits with loud rejection
  (never silent eviction), cancellation/replacement support. Carries no
  engine knowledge — `priority` is data, never arbitration.
- **`Scheduler` / `DefaultScheduler`** — the engine boundary. Pipeline:
  `BehaviorRequest → plan registry (behavior + variant → PlanStep) →
  TimelineEvent → EngineCommand` with delay support, deterministic drain,
  safe cancellation. Re-scheduling the same behavior while pending is a
  no-op (continuation); a different behavior replaces the timeline
  (interruption). The director's `recovery_behavior` instruction is
  *represented*, never invented.
- **`EngineCommand` / `EngineCommandName`** — a guarded 5-verb vocabulary
  (`set_state`, `blink`, `trigger_blink_type`, `look_at`, `step`) derived
  from a single `Literal`, so the guard can never drift from the docs.
  Unknown commands raise `ValueError` — no silent vocabulary expansion.
- **`EngineDriver` (Protocol)** — the ONLY way LES talks to the engine;
  never imports `eyes/`/`face/` at runtime.
- **`DEFAULT_BEHAVIOR_PLANS`** — conservative starter plans mapping every
  intent to documented engine states (greeting → happy, listening →
  listening, alert → surprised, comforting → caring, etc.), fully
  overridable by injecting a custom registry.

### 5.4 Phase 9.5 — Real engine integration (committed `3fd8c8e`, LES-08.5)

- **`RealEngineDriver`** — the smallest possible `EngineDriver` adapter over
  the *real, frozen* engines. `for_face()` wraps `FaceEngine`
  (eyes+mouth+FX; no `trigger_blink_type`), `for_eyes()` wraps a
  fully-registered `AnimationEngine` (full protocol). Capability adaptation
  is introspection-only; unsupported verbs raise loudly via `supports()`.
  Contains **zero animation logic** (verified: no geometry/easing/tween
  tokens).
- **`les_demo.py`** — end-to-end demo: `BehaviorIntent → schedule() →
  Timeline → advance() → EngineCommand → RealEngineDriver → FaceEngine`,
  windowed or `--headless` (CI-friendly screenshots + telemetry).

### 5.5 Phase 10 — Natural Idle Decision Layer (uncommitted, LES-09A.1)

Pipeline: `IdleContext → IdlePolicy → IdleBehavior → IdleDecision`.

- **`idle_policy.py`** — the *values* layer (never decides):
  - `IdleTier` — the three doc-sourced tiers: ATTENTIVE (T1), ENGAGED (T2),
    DEEP (T3).
  - `IdleAction` — behavioral vocabulary: NONE / BLINK / GAZE_DRIFT /
    MICRO_CORRECTION / CURIOUS_GLANCE (decisions, not animation).
  - Uniform-random timing bands per tier × action (T1 values doc-sourced
    from behavior-spec §4.2: blink 3–5 s, sweep 8–15 s, check 20–40 s);
    action weights; per-emotion modifiers (surprised → zero idle actions);
    personality trait gains; cooldown names; the 11 high-priority behaviors
    and engaged interaction modes idle must yield to.
- **`idle_behavior.py`** — the *orchestrator*:
  - `IdleContext` — immutable situational snapshot (caller-supplied time
    only — no wall-clock APIs anywhere).
  - `IdleDecision` — action, tier, reason, `next_ms` (when to decide again).
  - Yields to high-priority behaviors / engaged modes / speaking / touch;
    surprise triggers a recovery quiet band; sleepy forces DEEP tier;
    anti-periodicity (bounded uniform bands, no fixed timers, no immediate
    repetition of non-blink actions, "NONE is a valid decision").
  - Deterministic under an injectable `random.Random`; records to the
    injected `BehaviorMemory` (cooldowns, blink records); maps decisions to
    `BehaviorIntent` for the LES-09A.2 integration layer (variant preserved,
    e.g. `idle:attentive_blink`).
  - Deliberately does **not** use the `Behavior` ABC — that is the
    BehaviorDirector's registry contract and belongs to LES-09A.2.

### 5.6 Phase 11 — Real Idle Execution Integration (uncommitted, LES-09A.2)

Pipeline: `IdleContext → IdleBehavior.decide() → IdleDecision →
(IdleExecutionBridge) → BehaviorIntent → DefaultScheduler.schedule() →
Timeline → advance() → EngineCommand → RealEngineDriver → FaceEngine`.

- **`idle_execution.py` / `IdleExecutionBridge`** — the ONLY glue between
  the idle decision layer and the scheduler. It maps a decision onto a
  `BehaviorIntent` (variant preserved), registers the variant's concrete
  engine steps into the scheduler's plan registry, and schedules. The
  existing `DefaultScheduler` remains the execution authority; no parallel
  scheduler/timer/clock exists (verified: no `while True`, `sleep`,
  `threading`, wall clocks anywhere).

**Per-action mapping** (documented `EngineCommand` vocabulary only):

| IdleAction | EngineCommands | Notes |
|---|---|---|
| NONE | *(none — nothing scheduled)* | No dummy command, no state change. |
| BLINK | `blink` | The existing blink controller stays authoritative; typed blinks (`trigger_blink_type`) unused because the default `FaceEngine` driver does not support them. |
| GAZE_DRIFT | `look_at(x, y)` | Target is a pure deterministic function of the decision (tier/action/`decided_at_ms`), bounded in [0,1] — the engine owns the actual gaze movement. |
| MICRO_CORRECTION | `look_at(0.5, 0.5)` | Smallest existing representation (deterministic re-centering). Documented limitation: not sized relative to current gaze (LES never reads engine internals). |
| CURIOUS_GLANCE | `look_at(glance)` at t=0, `look_at(0.5, 0.5)` at t=450 ms | Look away, brief hold, return toward neutral — two documented commands, no new animation. |

**Emotion preservation:** idle plans NEVER emit `set_state` — idle is
behavior, not an emotional reset (a happy robot stays happy while it
blinks/drifts). The bridge clears the intent's `recovery_behavior` so the
scheduler's recovery machinery can never fire `set_state("calm")` after an
idle action. Verified on the real engine: state stays HAPPY through all
four idle actions.

**Attention preservation:** when the context carries a concrete attention
target or active tracking, gaze actions (GAZE_DRIFT / MICRO_CORRECTION /
CURIOUS_GLANCE) are not scheduled (`idle:attention_preserved`) — idle
never blindly overwrites a meaningful gaze target (Bible Part 8.3:
attention always beats idle). BLINK and NONE are unaffected. Eye contact
alone carries no target and simply selects the ENGAGED tier (existing rule
— no new attention rule invented).

**Interruption / recovery:** interruption is the scheduler's existing
replacement semantics — a higher-priority `BehaviorIntent` (e.g. greeting)
scheduled while idle is pending replaces the idle timeline. Recovery to
idle is simply the next `IdleDecision`; idle itself yields through the
decision layer. Deterministic end-to-end scenario verified: calm → idle
NONE → idle BLINK → idle GAZE_DRIFT → idle NONE → GREETING interrupts →
idle resumes.

**Demo:** `les_demo.py --idle` demonstrates calm entry, idle NONE, idle
blink, idle gaze drift, recovery, and a greeting interruption through the
real FaceEngine (windowed or `--headless`).

---

## 6. Verification status (all re-run 2026-08-08, all green)

| Suite | Scope | Result |
|---|---|---|
| `_verify_behavior.py` | Behavior Director acceptance (16 scenarios: idle fallback, cooldowns, continuation, interruption, max-hold, variant rotation, listeners, reset) | **30 passed / 0 failed** |
| `_verify_les08_timeline_scheduler.py` | Timeline + Scheduler (ordering, same-time FIFO, delays, capacity/horizon, command generation, draining, cancellation, determinism, variant preservation, recovery events, vocabulary guard, EngineDriver boundary, no forbidden imports) | **65 passed / 0 failed** |
| `_verify_les08_5_integration.py` | Real engine integration (constructs FaceEngine + AnimationEngine drivers, set_state / blink / typed blink / look_at / step reach the real engines, 3 full pipeline scenarios with exact command logs + state traces, determinism, no duplicate animation logic) | **34 passed / 0 failed** |
| `_verify_les09a_idle.py` | Natural Idle Decision Layer (tiers, NONE is valid, yields to 11 intents + engaged modes + speaking + touch, emotion/attention shaping, sleepy → DEEP, surprise recovery, cooldowns, anti-repetition, personality influence, injectable seeded determinism, anti-periodicity, quiet periods, no wall-clock / forbidden imports, decision → BehaviorIntent handoff, not_due guard, reset) | **24 passed / 0 failed** |
| `_verify_les09a2_idle_integration.py` | Real Idle Execution Integration (valid decisions, NONE → no commands, BLINK → real blink, GAZE_DRIFT → real look_at, CURIOUS_GLANCE look-hold-return, MICRO_CORRECTION smallest representation, emotion preservation on the real engine, no direct engine calls / no pygame / eyes / face imports, timeline timing, scheduler ordering, deterministic commands, seeded determinism, quiet periods, sequential actions, interruption, recovery, no set_state, attention preservation, anti-periodicity, deterministic end-to-end scenario through the real scheduler + driver) | **104 passed / 0 failed** |

**Total: 257 verification checks green across 5 suites.** All `les/`
modules compile and `import les` works.

Note: the scripts are run with the `py` launcher on this machine
(`py _verify_*.py`), not `python`.

### 6.1 Earlier fix session (Phase 8, from `_verify_behavior.py`)

The behavior director acceptance suite was originally written against the
design contract at **17 passed / 13 failed**; the following defects were
fixed in the Phase 8 session (all in `les/director/`):

1. **Idle fallback never fired** — `idle` removed from the scored ruleset
   (fallback only); `waiting` now requires emotional neutrality.
2. **Ladder contradicted the Interaction Bible** — retuned the full ladder
   to Bible Part 6 ordering (celebrating/listening, curious/playful,
   greeting/alert conflicts).
3. **Cooldowns blocked persistence** — the active intent is now exempt from
   its own cooldown gate.
4. **Max-hold yielded too late** — max-hold is now checked *before*
   non-interruptible continuation.
5. **Variant rotation never advanced** — rotation now bases on the
   director's own last-emitted variant.
6. **Listener test** — resolved by fix 1.

---

## 7. Current state & next steps

- **Committed:** 11 commits through Phase 9.5 (eyes + mouth + LES
  orchestration + timeline scheduler + real engine integration).
- **Uncommitted (needs commit):** the LES-09A.1 Natural Idle Decision Layer
  (`idle_policy.py`, `idle_behavior.py`, `_verify_les09a_idle.py`), the
  LES-09A.2 Real Idle Execution Integration (`idle_execution.py`,
  `_verify_les09a2_idle_integration.py`, the `--idle` demo mode in
  `les_demo.py`), plus the `les/behaviors/__init__.py` re-export changes.
  (Only `*.pyc` files are otherwise dirty.)
- **Validation:** all 5 suites green (257 checks); verified today.

Suggested next steps:

1. **Commit the LES-09A.1 + LES-09A.2 idle layers** to the branch.
2. **Unit tests** for the `EmotionDirector` gates and the
   `WorldState`/`BehaviorMemory` facades (only verification scripts exist so
   far; no `pytest` suite yet).
3. **Housekeeping** — update `les/__init__.py` `__status__` from
   `"scaffold"` to reflect the now-working implementation, and add a
   `.gitignore` entry for `__pycache__/` (the working tree currently shows
   many `*.pyc` files as modified).
