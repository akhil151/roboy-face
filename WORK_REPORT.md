# Roboy Face Engine — Complete Work Report

**Branch:** `feature/living-expression-system`
**Date:** 2026-08-06
**Report status:** Current — reflects the state of the working tree today.

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
| `les/` | Behavior & emotion orchestration (directors, memory, world state, policies) | **Active work — implemented, uncommitted** |

---

## 2. Git history — phases of work

The branch contains 8 commits. Each maps to a work phase:

| Commit | Message | Phase |
|---|---|---|
| `822a300` | first commit | **Phase 1** — Eyes foundation: `eyes/__init__.py`, animation base class, the 11 emotion animations (calm, caring, focus, happy, listening, sad, sleepy, speaking, surprised, thinking), demo. |
| `29d6604` | second commit | **Phase 2** — Engine evolution: richer `base.py`, emotion polish across all animations. |
| `22ca290` | third commit | **Phase 2** — Core engine: `expressive.py`, `engine/` package with `animation_clips`, `emotion_blending`, `micro_behaviours`, `motion_curves`, `motion_primitives`, `personality`. |
| `f4daaa8` | fourth push | **Phase 3** — Animation refactor: all 11 emotion files reworked to use the new engine. |
| `b65a5f0` | five commit | **Phase 4** — Animation polish: richer per-emotion motion (happy 86 lines, caring 66, etc.). |
| `102970b` | before alter: | **Phase 5** — `eyes/showcase.py` (1,112 lines) — the visual showcase/verification harness. |
| `385f77a` | seven push | **Phase 6** — Final polish: `thinking`, `surprised`, `caring`, `happy`, `focus` refinements. |
| `c742b8b` | review before | **Phase 7** — Mouth system: `face/mouth/` (`mouth_animation`, `mouth_renderer`, `mouth_shapes`) + `face/` renderers + `test_mouth_phase4a_verify.py`. |

**Phase 8 (current, uncommitted):** the entire `les/` Living Expression System
package + `_verify_behavior.py` acceptance script.

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

Verification scripts (committed earlier):
`test_choreography_verify.py`, `test_phase2a_verify.py`, `test_phase2b4_verify.py`,
`test_official_states_verify.py`, `test_visual_identity_verify.py`.

---

## 4. `face/` — face composer + mouth system

- `face_composer.py`, `face_engine.py`, `face_mixer.py`, `face_renderer.py`,
  `face_showcase.py`, `render_context.py`.
- `mouth/`: `mouth_animation.py`, `mouth_renderer.py`, `mouth_shapes.py`,
  `speech_sync.py` — lip shapes + speech-lip sync (Phase 4a).
- Verification: `test_mouth_phase4a_verify.py`.

---

## 5. `les/` — Living Expression System (the current work)

**Status:** implemented, ~4,209 lines of Python across 31 files, **not yet
committed** (`git status` shows `?? les/` and `?? _verify_behavior.py`).

### 5.1 Architecture (as implemented)

```
World State ──────────────► Emotion Policy ──► Emotion Director
     │                                                │
     │                                        internal emotional state
     ▼                                                ▼
Behavior Memory ◄────── Behavior Policy ◄──── Behavior Director
     │                                                │
     └──────── record behavior/cooldowns              │
                                                      ▼
                                             BehaviorIntent / BehaviorRequest
                                                      │
                                             (future) Timeline → Scheduler → Engine
```

### 5.2 Module inventory

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
| `docs/` | 3 design bibles + README (~3,553 lines) | Behavior Spec, Emotion Bible, Interaction Bible — the design authority |

### 5.3 The default behavior ladder (tuned to the Interaction Bible Part 6)

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

### 5.4 Key mechanisms

- **Cooldowns:** prevent re-selection after a behavior ends (greeting 4 s,
  alert 2.5 s, comforting 3 s). The **active** intent is exempt from its own
  cooldown so behaviors finish naturally.
- **Continuation / persistence:** +0.12 score bonus for the active intent
  within a 1.2 s window — "finish what you started".
- **Urgent interruption:** a competitor beating the active intent by ≥0.20
  displaces it mid-continuation (speech → listening interrupts playful).
- **Max-hold anti-freeze:** no intent may run forever (checked before
  non-interruptible continuation) — the robot never freezes.
- **Emotion pairing:** the intent matched to the current emotion gets a bonus
  (happy → playful, surprised → alert) and is recommended as the next
  transition target.
- **Variant rotation:** CYCLIC / STICKY / AVOID_RECENT over named variants
  (`happy_a`, `happy_b`, …) — the director emits variant *names*, never
  animation details.
- **Idle fallback:** when nothing is eligible, `scores` is empty and the
  director emits `idle` with reason `idle_fallback` — idle is the default,
  not a competitor (Interaction Bible Part 8.3).
- **Emotion gates:** persistence, hysteresis, recovery cooldown, valence
  waypoint (direct flips route through neutral), confidence margin — layered
  flicker prevention.

---

## 6. Verification session (this session's fix work)

`_verify_behavior.py` is the acceptance contract for the Behavior Director
(16 scenarios, 30 checks). It was written against the design contract.

### 6.1 Initial state

**17 passed / 13 failed.** Root causes found:

1. **Idle fallback never fired.** `waiting` (0.35) and `idle` (0.20) were both
   self-sustaining scored rules → `scores` was never empty → `idle_fallback`
   reason never emitted. → **Fixed:** `idle` removed from the ruleset (fallback
   only); `waiting` now requires emotional neutrality.
2. **Ladder contradicted the Interaction Bible.** `celebrating` (0.82) beat
   `listening` (0.80) on speech; `curious` (0.55) beat `playful` (0.50) on
   happy; `greeting` (0.90 + bonuses = 1.05) beat `alert` (0.95) on surprise.
   → **Fixed:** retuned the full ladder to Bible Part 6 ordering.
3. **Cooldowns blocked persistence.** A cooldown started on selection gated the
   active intent out of its own continuation (`playful → waiting` flicker).
   → **Fixed:** the active intent is exempt from its own cooldown gate.
4. **Max-hold yielded too late.** The max-hold anti-freeze check ran *after*
   non-interruptible continuation, so non-interruptible behaviors (greeting)
   could overstay their cap once cooldown-exempt. → **Fixed:** max-hold is now
   checked first (step a), so even non-interruptible behaviors yield at their
   cap.
5. **Variant rotation never advanced.** CYCLIC read the "last variant" from
   memory, but `record_behavior` stores no variant → always returned `happy_a`.
   → **Fixed:** rotation is based on the director's own last-emitted variant
   (`_active_variant`), falling back to memory history.
6. **Listener test** failed because first selection was `waiting`, not `idle` —
   resolved by fix 1.

### 6.2 Files changed in the fix session

| File | Change |
|---|---|
| `les/director/behavior_policy.py` | Retuned `DEFAULT_INTENT_RULES` to the Bible ladder; removed the `idle` rule; `waiting` → `requires_no_emotion`; documented the alert/listening tie-break order. |
| `les/director/behavior_director.py` | Cooldown gate exempts active intent; max-hold check moved before non-interruptible continuation; `_select_variant` bases rotation on `_active_variant`; docstrings updated. |

### 6.3 Final state

```
RESULT: 30 passed, 0 failed
ALL CHECKS PASSED
```

All 16 scenarios green:
1. Independence (no pygame/engine/ROS imports, ABC abstract) ✅
2. Idle fallback with `idle_fallback` reason ✅
3. Touch → comforting (non-interruptible) ✅
4. Speech → listening ✅
5. Robot speaking → responding ✅
6. Greeting wins on eye contact, yields on max-hold, cooldown respected ✅
7. Persistence / continuation with urgency decay ✅
8. Speech interrupts playful mid-continuation ✅
9. Non-interruptible alert holds during its window ✅
10. Happy → playful with emotion-paired transition recommendation ✅
11. Variant rotation CYCLIC (`happy_a` → `happy_b`) ✅
12. Variant rotation STICKY ✅
13. Policy replacement drives selection ✅
14. `from_config` seeds cooldowns ✅
15. Intent listeners fire on change ✅
16. `reset()` restores neutral arbitration state ✅

---

## 7. Current state & next steps

- **Committed:** 8 commits through Phase 7 (eyes + mouth).
- **Uncommitted (needs commit):** `les/` (31 files, ~4,209 lines) and
  `_verify_behavior.py`.
- **Validation:** `py _verify_behavior.py` → 30/30 pass; all `les/` modules
  compile (`py_compile` OK); `import les` works with `__version__ 0.1.0`.

Suggested next steps:
1. Commit `les/` + `_verify_behavior.py` to the branch.
2. Wire the Behavior Director output into the `eyes/` engine (scheduler →
   EngineDriver boundary exists but is not yet connected end-to-end).
3. Add unit tests for `EmotionDirector` gates (persistence/hysteresis/waypoint)
   and the `WorldState`/`BehaviorMemory` facades.
4. Update `les/__init__.py` status from `"scaffold"` to reflect the now-working
   implementation.
