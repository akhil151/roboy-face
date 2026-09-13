# ELO Face V3 (Experiment 3) — Stage 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Stage 2 of ELO Face V3 — the complete 62-second automated timeline experience (Intro, Settle, 2x Blinks, Look H/V, Surprise, Wink, Playful Double Wink, Happy Bounce, Cute Blush, Drowsy, Sleep with floating Z particles, and Loop).

**Architecture:** Extend `experiment-3/` with `effects.py` (Intro typewriter, Blush strokes, Sleep particles), `timeline.py` (data-driven 12-segment sequencer), updated `config.py`, updated `renderer.py` (layered multi-pass rendering), updated `animation.py` (dedicated segment handlers), and enhanced `showcase.py` & `verify.py`.

**Tech Stack:** Python 3.10+, Pygame 2.x.

**Spec:** `docs/superpowers/specs/2026-09-13-elo-face-v3-stage2-design.md`

## Global Constraints
- Strictly in `experiment-3/`.
- No edits or dependencies on `experiment-2/` or legacy modules.
- Target: 800x480 @ 60 FPS.
- Total timeline duration: 62.0 seconds.

---

### Task 1: Update Configuration with Stage 2 Timings & Effects

**Files:**
- Modify: `experiment-3/config.py`

**Interfaces:**
- Produces:
  - `TIMELINE_SEGMENTS`: List of `(name, duration)` totaling 62.0s.
  - `BLUSH_WIDTH`, `BLUSH_HEIGHT`, `BLUSH_OFFSET_Y`, `BLUSH_COLOR`.
  - `SLEEP_PARTICLE_MAX`, `SLEEP_PARTICLE_SPAWN_RATE`, `SLEEP_PARTICLE_SPEED`.
  - `INTRO_TEXT_1`, `INTRO_TEXT_2`.

- [ ] **Step 1: Add all Stage 2 constants to `config.py`**
- [ ] **Step 2: Verify total segment duration equals 62.0s**

---

### Task 2: Implement Overlay & Particle Effects Module

**Files:**
- Create: `experiment-3/effects.py`

**Interfaces:**
- Produces:
  - `IntroState`: Manages "Hii" and "This is ELO." typewriter reveal, cursor blink, and alpha fade.
  - `BlushState`: Manages fade-in/out alpha for blush stadium strokes under eyes.
  - `SleepZParticles`: Manages spawning, upward drift, sinusoidal sway, and alpha fading of 'Z' particles.

- [ ] **Step 1: Implement `IntroState`**
- [ ] **Step 2: Implement `BlushState`**
- [ ] **Step 3: Implement `SleepZParticles`**
- [ ] **Step 4: Unit test effects states and update loops**

---

### Task 3: Implement Data-Driven Timeline Sequencer

**Files:**
- Create: `experiment-3/timeline.py`

**Interfaces:**
- Consumes: `config.py`, `effects.py`
- Produces:
  - `TimelineController`: Tracks current segment index, segment elapsed time, normalized segment progress $u \in [0.0, 1.0]$, total time, and handles smooth transitions between segments.
  - Methods: `update(dt)`, `jump_to_segment(name_or_index)`, `next_segment()`, `prev_segment()`, `pause()`, `resume()`.

- [ ] **Step 1: Implement `TimelineController`**
- [ ] **Step 2: Implement segment boundary event hooks and parameter resets**
- [ ] **Step 3: Test timeline progression and looping**

---

### Task 4: Implement Emotion Handlers in Animation Controller

**Files:**
- Modify: `experiment-3/animation.py`

**Interfaces:**
- Consumes: `config.py`, `easing.py`, `eye.py`, `timeline.py`, `effects.py`
- Produces:
  - Handlers:
    - `_update_intro(u, dt)`
    - `_update_settle(u, dt)`
    - `_update_blink(u, dt)`
    - `_update_look_horizontal(u, dt)`
    - `_update_look_vertical(u, dt)`
    - `_update_surprise(u, dt)`
    - `_update_wink(u, dt)`
    - `_update_playful_double_wink(u, dt)`
    - `_update_happy_bounce(u, dt)`
    - `_update_cute_blush(u, dt)`
    - `_update_drowsy(u, dt)`
    - `_update_sleep(u, dt)`

- [ ] **Step 1: Implement all 12 emotion handlers in `FaceController`**
- [ ] **Step 2: Integrate `TimelineController` with `FaceController`**
- [ ] **Step 3: Test continuous transitions across segment boundaries**

---

### Task 5: Enhance Renderer for Multi-Layer Effects & Intro Text

**Files:**
- Modify: `experiment-3/renderer.py`

**Interfaces:**
- Consumes: `config.py`, `eye.py`, `effects.py`
- Produces:
  - `render_blush(surface, blush_state, eye_pair)`
  - `render_sleep_particles(surface, particles)`
  - `render_intro(surface, intro_state)`
  - Layered composite in `render_frame(...)`.

- [ ] **Step 1: Implement blush drawing beneath eyes**
- [ ] **Step 2: Implement sleep 'Z' particle drawing**
- [ ] **Step 3: Implement intro typewriter text drawing**
- [ ] **Step 4: Verify rendering headless with `SDL_VIDEODRIVER=dummy`**

---

### Task 6: Update Interactive Showcase & Hotkeys

**Files:**
- Modify: `experiment-3/showcase.py`

**Interfaces:**
- Supports:
  - Full automatic 62-second sequence playback
  - Hotkeys 1-9, 0, -, = to jump directly to any emotion segment
  - Space to restart / pause, H for timeline & HUD overlay
  - `--demo` mode playing the sequence automatically

- [ ] **Step 1: Update event loop and hotkeys in `showcase.py`**
- [ ] **Step 2: Enhance HUD to show current timeline segment name and progress**
- [ ] **Step 3: Test `--headless` and `--demo` execution**

---

### Task 7: Comprehensive Verification & Documentation

**Files:**
- Modify: `experiment-3/verify.py`
- Modify: `experiment-3/README.md`

- [ ] **Step 1: Add automated tests for all 12 segments, 62s duration, blush alpha, particles, and winks in `verify.py`**
- [ ] **Step 2: Run `verify.py` and ensure 100% pass rate**
- [ ] **Step 3: Run full 62s headless demo simulation**
- [ ] **Step 4: Update `README.md` with complete Stage 2 sequence reference**
- [ ] **Step 5: Verify git status confirms zero modifications to `experiment-2/`**
