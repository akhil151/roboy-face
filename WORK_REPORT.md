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

**Phase 12 (LES-09B.1, uncommitted):** Emotion Expression Choreography —
`les/choreography/` (beats model, data-driven CALM/HAPPY/SAD/THINKING
choreographies + Bible variants, `EmotionChoreographyDirector` with bounded
seeded variation, `EmotionChoreographyBridge` + `EmotionChoreographyRunner`
over the existing scheduler); `_verify_les09b1_choreography.py`;
`_show_les09b1_choreography.py`. Re-exported from `les/__init__.py`.

**Phase 13 (LES-09B.2, uncommitted):** Expression Cue & Thinking Polish —
`OverlayConfig` in `eyes/engine/config.py`, config-driven thinking/sleepy
cues in `eyes/engine/overlay_renderer.py`, richer THINKING/HAPPY/SAD
beats, `build_fallback()`; `_verify_les09b2_expression_polish.py`;
`_show_les09b2_expression_polish.py`.

**Phase 14 (LES-09B.3, uncommitted):** Dedicated Sleepy Choreography —
SLEEPY joins `SUPPORTED_EMOTIONS` with an authored 8-beat drowsy-descent
choreography (variants `deep_sleep` / `gentle_doze`), attention
preservation in the director + runner; `_verify_les09b3_sleepy.py`;
showcase extended (sleepy diagnostics, A/W keys). See section 14.

---

## 12. LES-09B.1 — Emotion Expression Choreography (uncommitted)

### 12.1 What it is

The first real Expression Choreography layer for exactly four emotions
(calm, happy, sad, thinking). The problem it solves: emotions previously
read as "change eye geometry + optional visual effect = emotion". The
choreography layer makes each emotion UNFOLD over time as a deliberate
sequence of expressive beats (onset → attention/gaze → blink → hold →
variation → recovery), using ONLY the existing engine vocabulary
(`set_state` / `blink` / `look_at`) and the existing Scheduler as the
execution authority.

Pipeline (the intended direction, nothing bypassed):

    World State → Emotion Director → EmotionChoreographyRunner
        → EmotionChoreographyBridge → DefaultScheduler → EngineCommand
        → RealEngineDriver → FaceEngine

### 12.2 Architecture (`les/choreography/`)

| File | Contents |
|---|---|
| `beats.py` | `BeatKind`, `ExpressionBeat` (bounded timing band per beat), `EmotionChoreography`, `VariantMod` (Bible A/B/C/D variants), `ResolvedBeat`, `ChoreographyPlan`, `validate_choreography()` (data invariants) |
| `emotions.py` | The four data-driven choreographies + variants, each beat citing the Emotion Bible page (E1/E2/E3/E4) and the behavior spec §10 transition tables |
| `director.py` | `EmotionChoreographyDirector` — variant selection (seeded, avoid-recent), uniform sampling within bands (bounded), gaze-target overrides, `PlanStep` resolution; personality hook via an optional timing scale |
| `execution.py` | `EmotionChoreographyBridge` (registers variant steps into the scheduler registry, mirrors `IdleExecutionBridge`) + `EmotionChoreographyRunner` (reacts to `InternalEmotionState`, schedules only on real transitions) |

Design decisions:
* **Variation is bounded + seeded** — every gap is sampled uniformly within
  its band by one injectable `random.Random`; the same seed + call sequence
  reproduces byte-identical plans. Variants stay inside each emotion's
  identity envelope (timing scales clamped to [0.5, 1.5]).
* **Transitions are NOT reimplemented** — the Emotion Director's existing
  gates (persistence, hysteresis, recovery cooldown) and its **valence
  waypoint** route HAPPY→SAD through calm automatically. The runner simply
  follows the director's decisions.
* **Recovery is the next emotion's ONSET** — a choreography plan never
  fires `set_state("calm")` on its own (`recovery_behavior=None`); the
  director's neutral fallback (or the user's request) transitions to calm
  and the calm choreography's onset IS the recovery beat.
* **Thinking builds around the existing 4.5 s engine loop** — the engine's
  scan→twitch→blink→return sequence stays authoritative; the choreography
  adds a gaze-away emphasis beat, the late conclusion blink and the
  conclusion/return beat.
* **The `?` overlay is untouched** — enlarging it requires modifying
  `eyes/engine/overlay_renderer.py` (frozen engine layer), which is out of
  scope; reported as a limitation (engine task / LES-09B.2).

### 12.3 Contrast (behavioral signatures)

| Emotion | Span | Actions | Signature beats |
|---|---|---|---|
| CALM | ~10-14 s | 2-4 | settle blink, micro re-center, long stillness |
| HAPPY | ~1.6-4.1 s | 5-6 | double blink, playful glance, return, warm hold |
| SAD | ~7-13 s | 4-6 | downward settle gaze, slow droopy blink, lift-and-redrop, slow close |
| THINKING | ~3.7-7.5 s | 4-5 | gaze-away, cognitive hold, late conclusion blink, return |

### 12.4 Verification

`_verify_les09b1_choreography.py`: **244 checks, 0 failed** (2026-08-10),
covering the 20-point mission checklist (construction, timing invariants,
ordering, command vocabulary, per-emotion behaviour, Happy-vs-Sad contrast,
Thinking gaze-away, Calm restraint, all 8 transitions schedulable,
interruption, recovery, determinism, bounded variation, architecture guards,
real-engine pipeline, showcase smoke) plus all 6 existing regression suites
(`_verify_behavior`, `_verify_les08_timeline_scheduler`,
`_verify_les08_5_integration`, `_verify_les09a_idle`,
`_verify_les09a2_idle_integration`, `_verify_les09a3_motion`).

### 12.5 Visual status

**HUMAN VISUAL VALIDATION REQUIRED.** Automated tests prove correctness,
not good animation. Run:

    py _show_les09b1_choreography.py            # windowed
    py _show_les09b1_choreography.py --smoke    # headless self-check

Keys: 1-4 = CALM/HAPPY/SAD/THINKING; C/S/D/T/R = the five prescribed
transitions (S = Happy→Sad routes through calm); N = release the detection
to watch the neutral-fallback recovery to calm; ESC quits.

Suggested next steps:
1. Human visual review of `_show_les09b1_choreography.py` (blocking).
2. LES-09B.2: remaining six emotions + the `?` overlay sizing (needs an
   engine change first - see 12.2).
3. Commit the LES-09A.1/2 + LES-09B.1 working tree.

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

## 13. LES-09B.2 — Expression Cue & Thinking Polish (uncommitted)

### 13.1 What it is

A focused visual-polish phase addressing human-identified weaknesses in the
LES-09B.1 emotion choreography showcase. The four emotions were already
behaviorally distinct — this phase makes them LOOK better without changing
the architecture.

### 13.2 Changes

| File | Change | Reason |
|---|---|---|
| `eyes/engine/config.py` | Added `OverlayConfig` with `thinking_cue_scale=22.0`, `thinking_cue_anchor_y_ratio=0.95`, `sleepy_cue_scale_base=16.0`, orbital amplitudes, fade-in/out durations, sleepy position bands | Move all cue magic numbers to config so the choreography layer can influence them without touching the renderer |
| `eyes/engine/overlay_renderer.py` | Added `thinking_anchor()` helper, `set_overlay_config()` method; uses config values instead of hardcoded magic numbers; `_draw_thinking()` uses the helper | Single source of truth for "?" position; enable Q toggle in showcase; config-driven rendering |
| `les/choreography/beats.py` | Added `KNOWN_ENGINE_STATES` (11 states), `build_fallback()` function | Non-choreographed emotions (sleepy, surprised, etc.) get a safe `set_state` + blink instead of doing nothing |
| `les/choreography/emotions.py` | THINKING: added preparation + subtle correction beat. HAPPY: added extra gaze variation + soft settling. SAD: extended holds, longer settle + tail | Make the emotional narrative richer (thinking prep), give Happy more eye movement, extend Sad stillness |
| `les/choreography/execution.py` | Runner fallback path for non-choreographed emotions via `build_fallback()` | Sleepy etc. now work through the pipeline |

### 13.3 Thinking "?" cue

| Property | Old (LES-09B.1) | New (LES-09B.2) |
|---|---|---|
| Scale | 18.0 | 22.0 (+22%) |
| Y anchor ratio | 0.85 (hidden behind eye) | 0.95 (shifted down, visible) |
| Distance from eye center | 79.9 px | 90.8 px (clearly separated) |
| Fade-in | instant | 400 ms |
| Fade-out | instant | 500 ms |
| Orbital drift | 6 px / 4 px | 10 px / 6 px (subtle, not distracting) |

### 13.4 Thinking choreography (LES-09B.2 additions)

```
previous state
    ↓
thinking onset (320 ms)
    ↓
preparation: brief downward glance (NEW)
    ↓
gaze-away during scan
    ↓
cognitive hold
    ↓
subtle correction: micro re-aim during pause (NEW)
    ↓
conclusion blink
    ↓
conclusion/return
    ↓
continued thought
```

### 13.5 Happy & Sad contrast (LES-09B.2)

| Emotion | Span | Actions | Signature |
|---|---|---|---|
| HAPPY | ~2.2-5.0 s | 6-7 | double blink, playful glance, **gaze variation**, warm hold, **soft settling** |
| SAD | ~15-17 s | 5-6 | **longer settle**, downward gaze, **extended hold**, slow droopy blink, lift-and-redrop, **longer tail** |
| CALM | ~10-14 s | 2-4 | unchanged (still restrained) |

### 13.6 Verification

`_verify_les09b2_expression_polish.py`: **111 checks, 0 failed** (2026-08-10),
covering all 18 required points (existing choreography constructs, thinking
gaze-away preserved, cue config valid, scale bounded, position separated,
sleepy bounded, all schedulable, architecture guards, determinism,
build_fallback runner fallback, all regression suites).

### 13.7 Visual status

**HUMAN VISUAL VALIDATION REQUIRED.** Automated tests prove correctness,
not visual quality. Run:

    py _show_les09b2_expression_polish.py            # windowed
    py _show_les09b2_expression_polish.py --smoke    # headless self-check

Keys: 1-5 = CALM/HAPPY/SAD/THINKING/SLEEPY; C/S/D/T/R = transitions;
N = release; Q = toggle legacy/polished cue sizes; ESC = quit.

---

## 14. LES-09B.3 — Dedicated Sleepy Expression Choreography (uncommitted)

### 14.1 What it is

Human visual review of the LES-09B.2 showcase identified SLEEPY as the one
unfinished emotion: it ran the safe ``build_fallback`` plan
(``variant=fallback``, ``beats=0``) — a static sleepy preset, not a
behavior. LES-09B.3 replaces that fallback with a real authored Sleepy
choreography (E9 Sleepy) that sequences a believable drowsy-descent
narrative while keeping the engine's own sleepy state (droop sine, heavy
blink loop, ZZZ overlay) authoritative. **No eyes/ engine changes were
needed** — everything lives in ``les/choreography/`` + the existing
EngineCommand vocabulary (``set_state`` / ``blink`` / ``look_at``).

### 14.2 Changes

| File | Change | Reason |
|---|---|---|
| `les/choreography/beats.py` | `SUPPORTED_EMOTIONS` now includes `sleepy` (5 choreographed emotions) | Sleepy becomes a first-class authored choreography; the validator accepts its ONSET |
| `les/choreography/emotions.py` | Added `SLEEPY_BEATS` (8 beats, E9.13 timeline), `deep_sleep` + `gentle_doze` variants (Bible E9.14 A/C), registered in `CHOREOGRAPHIES` | The dedicated Sleepy choreography (no more fallback) |
| `les/choreography/director.py` | `build(..., preserve_attention=False)` — when True, `look_at` beats resolve without commands (marked "attention preserved" on the HUD) | The LES-09A.2 idle contract: attention always beats autonomous gaze (interaction-bible Part 8.3) |
| `les/choreography/execution.py` | `runner.update(internal, attention_active=False)` forwards attention to the director | Sleepy never blindly overwrites an active attention target |
| `les/choreography/__init__.py` | Scope docstring updated (five emotions) | Documentation |
| `_verify_les09b1_choreography.py` | 5-emotion scope in construction/validation/command loops + Sleepy signature checks (9d-9h) | Keep the LES-09B.1 suite green with the extended scope |
| `_verify_les09b2_expression_polish.py` | 5-emotion scope; runner-fallback test now uses `surprised`; sleepy asserted to build an authored plan | The old "sleepy is fallback" assertions tested the behavior this phase replaces |
| `_show_les09b2_expression_polish.py` | Sleepy HUD diagnostics (ZZZ particles, gaze, blink weight), `A` key = attention-preservation toggle, `W` key = wake (sleepy→calm), smoke updated | Make the Sleepy behavior easy to inspect repeatedly |
| `_verify_les09b3_sleepy.py` | **New** 96-check suite (the 20 required points + real-engine pipeline + all regression suites) | Prove the mission checklist |
| `WORK_REPORT.md` | This section | Documentation |

### 14.3 The Sleepy choreography (exact)

Data (``les/choreography/emotions.py``, `SLEEPY_BEATS`, each beat citing
Bible E9):

```
 0 ms      ONSET     set_state("sleepy", 500)      E9.12 slowest entry - lids sink with weight
 ~0.5-0.7 s SETTLE   (no command)                  heavy eyes settle (E9.13)
 ~0.5-0.7 s GAZE     look_at(0.5, 0.57)            down-drift, attention dissolving (E9.4)
 ~1.3-1.9 s BLINK    blink                         heavy sleepy blink (E9.13 at 1500 ms)
 ~3.7-4.9 s HOLD     (no command, 2.4 s)           quiet hold - near-zero motion (E9.13)
 ~5.0-6.7 s BLINK    blink                         second heavy blink (E9.13 at 5200 ms)
 ~5.0-6.7 s VARIATION look_at(0.5, 0.60)           tiny settling movement (E9.4 gravity wins)
 ~7.0-9.5 s HOLD     (no command, 2.0 s)           sleepy idle - engine droop loop + ZZZ take over
```

Span ≈ 9.4-11.8 s (scaled by variant). The plan runs ONCE per sleepy
onset; then the engine's own sleepy state (droop sine ±0.06, heavy
soft-blink every 5 s, automatic ZZZ) continues indefinitely — the
choreography never loops on itself.

### 14.4 Behavior summary

| Aspect | Design |
|---|---|
| Entry | Gradual: onset → heavy eyes settle → gaze sinks → first blink at ~1.3-1.9 s (not instant full sleepy) |
| Blink | `blink` beats at the Bible's 1500 ms / 5200 ms marks; the heavy droopy blink LOOK is the engine's own sleepy loop (FaceEngine has no `trigger_blink_type`, so no typed blink is fabricated) |
| Gaze | Soft center-x downward drift only (y 0.54-0.63); no saccades, no wandering — losing energy, not searching the room |
| Quiet hold | ≥2 s command-free gap between the two heavy blinks — the stillness IS the drowsiness |
| ZZZ | Engine-owned: the overlay spawns Z particles while state == sleepy (config-driven, LES-09B.2 values preserved, scale 16.0 unchanged). The choreography integrates it by TIMING (state persists through the holds) — no second rendering system |
| Variants | Two, Bible E9.14: `deep_sleep` (slower 1.25×, gaze deeper 0.60/0.63) and `gentle_doze` (lighter 0.85×, gaze 0.54/0.56, extra soft blink). Quality over quantity — the interactive *Fighting Sleep* and the *Waking* transition variant stay director/engine-owned |
| Wake/recovery | NOT re-implemented: release → Emotion Director neutral fallback → calm choreography ONSET = the wake-up (E9.12 leave + E9.13 waking blink are the calm entry). No forced `set_state("calm")` from Sleepy |
| Interruption | Existing scheduler replacement semantics: sleepy→happy / sleepy→thinking replace the pending sleepy timeline (verified on the real engine) |
| Attention | `runner.update(..., attention_active=True)` suppresses the sleepy gaze beats entirely (the LES-09A.2 idle contract); onset + blinks unaffected |

### 14.5 Verification

`_verify_les09b3_sleepy.py`: **96 checks, 0 failed** (2026-08-11),
covering the 20-point checklist (authored choreography, no fallback for
normal sleepy, real beats, valid scheduler steps, ONSET entry, blink,
gaze, quiet hold, no unsupported commands, no duplicate scheduling,
determinism, interruption, recovery, attention preservation, ZZZ engine
control, no renderer duplication, no clocks, all regression suites) plus
the real FaceEngine pipeline (sleepy set_state / gaze / blink / recovery /
interruptions all reach the real engine) and the showcase smoke.

Regression status (all green): `_verify_les09b1_choreography.py` **307**,
`_verify_les09b2_expression_polish.py` **121**, `_verify_les09b3_sleepy.py`
**96**, `_verify_behavior.py`, `_verify_les08_timeline_scheduler.py`,
`_verify_les08_5_integration.py`, `_verify_les09a_idle.py`,
`_verify_les09a2_idle_integration.py`, `_verify_les09a3_motion.py`.

### 14.6 Visual status

**HUMAN VISUAL VALIDATION REQUIRED.** Automated tests prove correctness,
not good animation. Run:

    py _show_les09b2_expression_polish.py                # windowed
    py _show_les09b2_expression_polish.py --smoke 2.0    # headless self-check

Keys: 1-5 = CALM/HAPPY/SAD/THINKING/SLEEPY; C/S/D/T/R = transitions;
**W = wake sleepy→calm**; N = release; Q = cue sizes;
**A = attention-preservation toggle** (sleepy gaze beats suppressed);
ESC = quit.

Known limitations:
* The heavy droopy blink LOOK is the engine's sleepy loop, not a typed
  slow blink — the real FaceEngine path has no `trigger_blink_type`, and
  inventing a fake typed blink was out of scope (the `blink` verb + engine
  loop is the existing representation).
* ZZZ appears shortly after sleepy onset (the overlay is state-driven) —
  the choreography cannot delay the first Z beyond the engine's own
  cooldown without modifying the frozen engine layer.
* The plan's authored window is ~9.4-14.5 s (variant-dependent); the
  quiet holds dominate by design. Entry beats finish by ~2 s.

---

## 15. LES-09B.4 — Overlay Cue Spatial Placement Fix (uncommitted)

### 15.1 What it is

A surgical spatial fix for the two overlay cues identified in human
review: the THINKING "?" could overlap/enter the eye silhouette, and the
SLEEPY ZZZ could approach the eye region during eye movement. Both cues
are now anchored in FACE SPACE derived from the actual eye layout and
both guarantee a configurable clearance margin from the rendered eye
silhouettes at every gaze target. No expressions, choreographies,
scheduler, directors, or behavior layers were changed.

### 15.2 Root cause

* Thinking "?": the old anchor was a fixed offset from the MOVING right
eye's local frame (`0.75/0.95 * radius`) with NO clearance guarantee, so
the glyph could enter the eye silhouette when the eye moved.
* Sleepy ZZZ: the old spawn band (x 0.3-0.9, y 0.0-0.3 eye radii from the
moving right eye) sat INSIDE the eye's own region.
* Both scales were hard-coded pixels (22.0 / 16.0) with no relation to
the real 150 px eye height.

### 15.3 Changes (smallest necessary set)

| File | Change |
|---|---|
| `eyes/engine/config.py` | `OverlayConfig` reworked: `thinking_cue_scale_ratio` (0.85 — scale DERIVED from eye radius), `thinking_cue_clearance_ratio` (0.4 — configurable margin, replaces the old `thinking_cue_anchor_y_ratio`), face-space sleepy band ratios (x 2.40-2.85, y 2.40-2.70 eye radii from the right eye's REST centre) |
| `eyes/engine/overlay_renderer.py` | New face-space geometry helpers (`eye_silhouette_region` mirroring `Renderer._effective_pos/_effective_radius` + rotation inflation; `eye_pair_regions`, `regions_intersect`, `thinking_scale`, `thinking_cue_region`/`z_cue_region` including glyph stroke width = conservative boxes, `thinking_anchor(pose)`, `sleepy_spawn_band(pose)`); `_draw_thinking` re-anchors every frame from the composed pose; `_draw_sleepy` spawns in the face-space band |
| `_verify_les09b4_cue_placement.py` | NEW suite, 180 checks |
| `_verify_les09b2_expression_polish.py` | Cue checks updated to the new schema (ratio, clearance, geometric separation) |
| `_show_les09b2_expression_polish.py` | Honest overlay path via `composer.overlay_renderer.eye_overlay`; ARROW-key extreme-gaze override; LEGACY Q-config reproduces the old bug for comparison; HUD + smoke updated |

### 15.4 Placement calculations

Thinking "?": `anchor_x = left.pos_x + anchor_x_ratio * (right.pos_x - left.pos_x)`
(face centre by default); `anchor_y = min(eye tops) - 0.61*scale - clearance`,
recomputed every frame from the ACTUAL composed pose, so the margin holds at
every gaze target and every thinking beat. Scale = `0.85 * 75 = 63.75 px`;
glyph height ~1.16x scale ~74 px vs the 150 px eye height = approximately
HALF the eye, subordinate to the eyes.

Sleepy ZZZ: spawn band in face space at `x = right.pos_x + 2.40..2.85 * r`,
`y = right.pos_y - 2.40..2.70 * r` (up-right free space). The band clears
the full worst-case excursion: rest radius + look (35) + bounce (26, the
`eye.py` clamp) + micro (0.6) + rotation inflation + the stroke-extended
glyph half-extent. The band never follows gaze; particles drift up-right,
away from the eyes. ZZZ scale_base stays 16.0 (unchanged - it was readable).

### 15.5 Verification

`_verify_les09b4_cue_placement.py`: **180 checks, 0 failed** — geometry
source-match vs the renderer; half-eye scale derivation; no-intersection
of the thinking cue and the ZZZ band vs BOTH eye regions across 9 gaze
targets x 4 pose variants (stretch/squash/rotation, config-derived worst
micro/bounce); cue validity through seeded THINKING and SLEEPY
choreographies; live overlay draw with particle evolution; real-engine
pipeline (thinking + sleepy reach the FaceEngine); showcase smoke; all
three LES-09B suites green (which gate the six older regression suites).
`py_compile` passes on every changed file.

### 15.6 Known limitations

* The ZZZ band now sits further out (up-right corner) than the old
  near-eye position — required by the never-overlap guarantee; human
  review should judge whether the distance reads as intentional free-space
  placement.
* The bounding boxes include the glyph stroke width, but line JOIN/cap
  rounding adds sub-pixel variance — irrelevant given the >= 10 px margins.
* Windowed visual inspection is still required (the smoke is headless).

### 15.7 Visual status

**HUMAN VISUAL VALIDATION REQUIRED.** Run
`py _show_les09b2_expression_polish.py`, press 4 (thinking) and 5
(sleepy), hold the ARROW keys to drive extreme gaze, and press Q to
compare the LEGACY (intentionally overlapping) vs POLISHED placement.
No visual-quality claim is made until a human inspects the render.

---

## 16. LES-09B.5 — Perimeter-Anchored Thinking Cue (uncommitted)

### 16.1 What it is

A placement-only change to the THINKING "?" cue, driven by human visual
feedback. The "?" SIZE was approved and is byte-identical to LES-09B.4
(``thinking_cue_scale_ratio`` 0.85 -> scale 63.75 px -> glyph ~74 px vs
the 150 px eye height). The rejected look was the cue floating CENTRED
above the face, detached from the eye language; the approved look is the
"?" growing from an eye's OUTER PERIMETER/CORNER:

```
        ?              (was)        ?
       )                            
      👁                     👁       👁
```

The cue is anchored to the right eye's OUTER TOP corner by default
(configurable: ``thinking_cue_eye`` left/right, ``thinking_cue_perimeter``
outer_top/outer_bottom), sits exactly ``clearance`` beyond the corner
(eye perimeter -> small configurable clearance -> "?"), is recomputed
from the ACTUAL composed pose every frame, and can never overlap either
eye silhouette. **The sleepy ZZZ is completely untouched.** No scheduler,
timeline, directors, choreographies, mouth, ROS or hardware layers were
changed; the overlay system was not redesigned.

### 16.2 Changes (smallest necessary set)

| File | Change | Reason |
|---|---|---|
| `eyes/engine/config.py` | `OverlayConfig`: removed the centred ``thinking_cue_anchor_x_ratio``; added ``thinking_cue_eye`` ("right" default) + ``thinking_cue_perimeter`` ("outer_top" default). Scale (0.85), clearance (0.4), orbital amplitudes, lifetimes, fades and ALL ZZZ fields byte-identical to LES-09B.4 | Express the perimeter anchor model; the centred placement was the rejected design |
| `eyes/engine/overlay_renderer.py` | `thinking_anchor()` rewritten: anchor = (eye outer edge +/− (clearance + 0.42*scale), eye top − clearance − 0.61*scale), reusing the single LES-09B.4 ``eye_silhouette_region`` eye-bound calculation; docstrings updated | Reuse the existing geometry - no second eye-bound calculation; draw path, scale and ZZZ untouched |
| `_verify_les09b2_expression_polish.py` | Cue checks updated to the perimeter model (eye/corner fields, no-longer-centred, exact-clearance hug) | The old checks asserted the centred placement this phase replaces |
| `_verify_les09b5_perimeter_cue.py` | **New** suite, 111 checks (the 11-point mission checklist + config/pipeline/bonus) | Prove the checklist |
| `_show_les09b2_expression_polish.py` | LEGACY Q-config expressed in the new schema (18 px scale, zero clearance, old overlapping ZZZ band); docstrings/labels/HUD updated (anchor mode shown as right/outer_top) | Keep the old-bug comparison honest under the new schema |
| `WORK_REPORT.md` | This section | Documentation |

### 16.3 Placement (exact)

``OverlayRenderer.thinking_anchor(pose)`` — one calculation, reused from
LES-09B.4 (the same AABB that carries the collision guarantees):

```
region     = eye_silhouette_region(pose.right)   # composed AABB: pos + look
                                                  # + micro + bounce + squash/
                                                  # stretch + rotation inflation
outer_x    = region.right                         # right eye's outer edge
anchor_x   = outer_x + clearance + 0.42 * scale   # glyph LEFT starts exactly
                                                  # one clearance beyond the eye
anchor_y   = region.top - clearance - 0.61 * scale# glyph BOTTOM starts exactly
                                                  # one clearance above the top
```

So the conservative glyph box (which already includes the stroke width)
sits exactly ``clearance`` (0.4 * 75 = 30 px) beyond the eye's outer top
corner at every pose; the actual stroke ink is >= clearance − 0.07*scale
(~25 px) away. Because the region is derived from the composed pose each
frame, the cue hugs the eye and follows every gaze/look movement; because
it grows outward from the eye, it can never enter the silhouette.

### 16.4 Verification (all executed 2026-08-11)

* ``_verify_les09b5_perimeter_cue.py``: **111 checks, 0 failed** — scale
  byte-identical to LES-09B.4; centred model removed from config; cue
  outside the eye-pair span (no longer centred); anchored to the right
  eye's outer-top corner at exactly the configured clearance; no
  intersection with BOTH eye regions across 9 gaze targets x 4 pose
  variants (stretch/squash-droop/rotation + worst-case micro/bounce);
  clearance exact at every gaze direction; anchor delta == composed-eye
  delta (follows movement) incl. bounce-offset composed AABB; safe at
  every THINKING-choreography gaze target (5 seeds); ZZZ scale/band
  byte-identical to LES-09B.4 and still clear; left-eye / outer-bottom
  options collision-safe; real-engine pipeline reaches thinking through
  the verified OverlayRenderer; LES-09B.4 suite, LES-09B.3 suite and
  showcase smoke all green.
* ``_verify_les09b4_cue_placement.py`` (LES-09B.4 collision guarantees):
  **green (exits 0)** — unchanged, proves the LES-09B.4 never-overlap
  contract is preserved under the new placement.
* ``_verify_les09b2_expression_polish.py`` (updated): **129 checks, 0
  failed** — gates b1, ``_verify_behavior``, ``_verify_les08_timeline_scheduler``,
  ``_verify_les08_5_integration``, ``_verify_les09a_idle``,
  ``_verify_les09a2_idle_integration``, ``_verify_les09a3_motion`` (all green).
* ``py_compile`` passes on every changed file.

### 16.5 Known limitations

* Pre-existing (NOT a regression): during the transient worst-case upward
  bounce/micro excursion at extreme up-gaze, the glyph box top can briefly
  clip the screen top by a few px — identical behaviour to the LES-09B.4
  centred model, since the anchor maths share the same composition.
* The Q LEGACY demo now expresses the old bug as "zero clearance + old
  ZZZ band" (the old local-frame centred math is gone by design and was
  not re-implemented); the overlap risk is still visible via the zero
  clearance and the overlapping ZZZ band.
* Windowed visual inspection is still required (the smoke is headless).

### 16.6 Visual status

**HUMAN VISUAL VALIDATION REQUIRED.** Run
``py _show_les09b2_expression_polish.py``, press 4 (thinking) and watch
the "?" grow from the right eye's outer top corner, hold the ARROW keys
to drive extreme gaze (the cue must follow and stay outside), and press Q
to compare LEGACY (zero clearance / old ZZZ band) vs POLISHED. No
visual-quality claim is made until a human inspects the render.

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
