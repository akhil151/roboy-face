# LES — Living Expression System (Architecture Scaffold)

**Status:** Scaffold — interfaces + documentation only, no behavior, no logic
**Version:** 0.1.0
**Layer:** sits *above* the stable animation engine v1.0 (`eyes/`)

**Design references**

| Document | Role |
|---|---|
| [`behavior-spec-v1.0.md`](behavior-spec-v1.0.md) | Behavior Design Specification v1.0 — timing tables, transition rules, personality model, timelines, future integration. |
| [`emotion-bible-v1.0.md`](emotion-bible-v1.0.md) | **Emotion Bible v1.0** — the permanent per-emotion animation & behavior reference: visual identity, eye/blink language, variants, timelines, comparison matrix, design rules. |
| [`interaction-bible-v1.0.md`](interaction-bible-v1.0.md) | **Interaction Bible v1.0** — behavior orchestration: event→intent→decision→timeline→emotion pipeline, 26 interaction events, behavior memory, attention model, 14 intents, arbitration, 24 design rules. |

---

## 1. What LES is

LES is the next-generation behaviour layer for the Roboy Face Engine. It
sits **above** the animation engine and will eventually **drive** it:

- LES decides *what the robot feels and does* — emotions, behaviors, timing.
- The animation engine decides *how feelings are drawn* — states, blends,
  motion primitives.
- The renderer draws them.

## 2. What LES is NOT

- LES does **not** replace the animation engine.
- LES does **not** modify the engine, its emotions, renderer, motion
  primitives, emotion blending, public APIs, or demos.
- LES does **not** implement behaviors yet — only their contracts.
- LES does **not** connect hardware, servos, ROS, or voice.
- LES does **not** import `pygame` or the engine at runtime.

## 3. Guarantees

| Guarantee | Where enforced |
|---|---|
| Engine never modified | No existing file under `eyes/`, `face/` or root is touched |
| Engine never imported at runtime | Only `TYPE_CHECKING` type hints reference `eyes.*` |
| No behavior logic | Every method body is `...` (abstract) — no algorithms |
| No pygame dependency | Zero `import pygame` in the `les/` tree |
| Type-safe contracts | Full type hints + `from __future__ import annotations` |

## 4. Architecture

```
Emotion Detector (external, future)
        |
        v
LES Emotion Director ................ les/director/emotion_director.py
        |   (EmotionInput -> EmotionIntent)
        v
LES Behavior Director ............... les/director/behavior_director.py
        |   (EmotionIntent -> BehaviorRequest)
        v
Behavior Timeline ................... les/timeline/timeline.py
        |   (TimelineEvent queue)
        v
Scheduler -> EngineCommands ......... les/timeline/scheduler.py
        |   (EngineDriver protocol boundary)
        v
Animation Engine (v1.0 STABLE) ...... eyes/  (untouched, runtime-free here)
        v
Renderer
```

Future flow (as specified):

```
Emotion Detector
        ↓
LES Emotion Director
        ↓
Behavior Timeline
        ↓
Animation Engine
        ↓
Renderer
```

## 5. Folder tree

```
les/
    __init__.py                 package facade + version + re-exports
    config/
        __init__.py
        defaults.py             LESConfig / DirectorConfig / TimelineConfig / BehaviorConfig
    director/
        __init__.py
        emotion_director.py     EmotionInput, EmotionIntent, EmotionDirector
        behavior_director.py    BehaviorRequest, BehaviorDirector
    timeline/
        __init__.py
        timeline.py             TimelineEvent, Timeline
        scheduler.py            EngineCommand, EngineDriver, Scheduler
    behaviors/
        __init__.py             Behavior (ABC), BehaviorContext, facade
        idle.py                 IdleBehavior
        attention.py            AttentionBehavior
        curiosity.py            CuriosityBehavior
        blink.py                BlinkBehavior
    personality/
        __init__.py
        traits.py               PersonalityTraits
        profiles.py             PersonalityProfile, PersonalityProvider
    transitions/
        __init__.py
        transition_director.py  TransitionSpec, TransitionDirector
    docs/
        README.md               this document
        behavior-spec-v1.0.md   behavior spec - timing, transitions, personality, timelines
        emotion-bible-v1.0.md   emotion bible - the permanent per-emotion animation reference
        interaction-bible-v1.0.md  interaction bible - event-driven behavior orchestration
```

## 6. Purpose of every module

| Module | Purpose |
|---|---|
| `les/__init__.py` | Facade. Documents the LES pipeline, holds `__version__` / `__status__` / `__frozen__`, re-exports every public contract. |
| `les/config/defaults.py` | Typed configuration surface (frozen dataclasses). Architectural defaults only — to be tuned in Phase 1. |
| `les/director/emotion_director.py` | Entry point. Turns external emotion detections (`EmotionInput`) into a decision (`EmotionIntent`). |
| `les/director/behavior_director.py` | Selection layer. Turns `EmotionIntent` into a `BehaviorRequest`. |
| `les/timeline/timeline.py` | Time-ordered event queue of behavior moments (`TimelineEvent`). |
| `les/timeline/scheduler.py` | **Engine boundary.** Consumes requests, plans events, emits `EngineCommand` via the `EngineDriver` protocol. |
| `les/behaviors/__init__.py` | `Behavior` ABC + `BehaviorContext` snapshot. Canonical behavior interface. |
| `les/behaviors/idle.py` | Calm baseline behavior (backstop). |
| `les/behaviors/attention.py` | Directed-focus behavior (gaze at targets). |
| `les/behaviors/curiosity.py` | Exploratory behavior (scan / tilt). |
| `les/behaviors/blink.py` | Natural blink scheduling at LES level (requests only — engine executes). |
| `les/personality/traits.py` | Six LES personality axes (data shape). |
| `les/personality/profiles.py` | Named personality profiles + provider protocol. |
| `les/transitions/transition_director.py` | Decides *how* states change (target, blend, easing) → engine `set_state()`. |
| `les/docs/behavior-spec-v1.0.md` | Behavior Design Spec — timing, transitions, personality, integration (design reference, not code). |
| `les/docs/emotion-bible-v1.0.md` | Emotion Bible — the permanent per-emotion animation reference (design reference, not code). |
| `les/docs/interaction-bible-v1.0.md` | Interaction Bible — event-driven behavior orchestration spec (design reference, not code). |

## 7. Public interfaces (summary)

- **Config:** `LESConfig`, `DirectorConfig`, `TimelineConfig`, `BehaviorConfig`
- **Personality:** `PersonalityTraits`, `PersonalityProfile`, `PersonalityProvider`
- **Directors:** `EmotionDirector`, `EmotionInput`, `EmotionIntent`,
  `BehaviorDirector`, `BehaviorRequest`
- **Timeline / scheduler:** `Timeline`, `TimelineEvent`, `Scheduler`,
  `EngineCommand`, `EngineCommandName`, `EngineDriver`
- **Behaviors:** `Behavior`, `BehaviorContext`, `IdleBehavior`,
  `AttentionBehavior`, `CuriosityBehavior`, `BlinkBehavior`
- **Transitions:** `TransitionDirector`, `TransitionSpec`

## 8. Data flow (future, Phase 1)

1. An external Emotion Detector emits `EmotionInput` (source, emotion, confidence, timestamp).
2. `EmotionDirector.ingest()` filters/smooths it and exposes a `current_intent()`.
3. `BehaviorDirector.submit_intent()` asks every registered behavior to
   `evaluate()` the `BehaviorContext` and arbitrates → one `BehaviorRequest`.
4. `Scheduler.schedule()` plans `TimelineEvent`s on the `Timeline`.
5. Each tick, `Scheduler.advance()` collects due events and `drain_commands()`
   emits `EngineCommand`s (set_state / blink / trigger_blink_type / look_at).
6. `TransitionDirector` shapes the emotional transitions with blend duration
   and easing.
7. The engine executes — unchanged.

## 9. Future responsibilities (Phase 1)

- **Emotion Director:** detection smoothing, hysteresis, label→state mapping.
- **Behavior Director:** behavior registry, arbitration by priority/urgency/context.
- **Timeline:** ordered insertion, interruption, capacity management.
- **Scheduler:** request→event planning, event→engine-command translation.
- **Behaviors:** real `evaluate`/`should_run`/`plan` logic for idle,
  attention, curiosity, blink.
- **Personality:** deterministic LES-trait → engine-profile mapping
  (energy, warmth, attention, calmness, amplitude, blink_tendency).
- **Transitions:** blend-duration heuristics from urgency/personality.

## 10. Non-goals

Hardware, servos, ROS, voice, vision processing, and any rendering live
outside LES. LES produces decisions only.

## 11. Conventions

- Full type hints everywhere; `from __future__ import annotations` at the top.
- Interfaces: `ABC` + `@abstractmethod` (bodies are `...`), `Protocol` for
  duck-typed boundaries, frozen `dataclass` for data contracts.
- TODO markers use the form `# TODO(LES-Phase-1): ...`.
- No runtime imports of `eyes` or `pygame` — engine types appear only under
  `if TYPE_CHECKING:`.
