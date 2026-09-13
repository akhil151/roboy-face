# ELO Face V3 (Experiment 3) Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a completely independent, modular Pygame foundation in `experiment-3/` for the ELO Face V3 "Big Eyes" system with circle-to-pill squash morphing, gaze offset, scale modulation, smooth easing, and 60 FPS performance at 800x480 resolution.

**Architecture:** A lightweight, decoupled architecture containing centralized configuration (`config.py`), organic mathematical easing functions (`easing.py`), an eye model and geometry calculator (`eye.py`), a pure Pygame renderer (`renderer.py`), an organic animation controller (`animation.py`), an interactive showcase app (`showcase.py`), and a headless test suite (`verify.py`).

**Tech Stack:** Python 3.10+, Pygame 2.x, Math/Dataclasses.

**Spec:** `docs/superpowers/specs/2026-09-13-elo-face-v3-foundation-design.md`

## Global Constraints
- Target resolution: 800x480.
- Platform: Desktop & Raspberry Pi 5.
- Background: Black `(0, 0, 0)`.
- Eyes: Solid white `(255, 255, 255)` with no pupils, no sclera, no separate eyelids, no outlines.
- Morphing: Continuous vertical squash between full circle ($o=1.0$) and rounded pill/stadium ($o < 1.0$).
- Strict isolation: All files reside exclusively in `experiment-3/`. Zero imports or edits to `experiment-2/` or legacy directories.

---

### Task 1: Configuration & Easing Primitives

**Files:**
- Create: `experiment-3/config.py`
- Create: `experiment-3/easing.py`

**Interfaces:**
- Produces:
  - `config`: `WINDOW_WIDTH`, `WINDOW_HEIGHT`, `FPS`, `COLOR_BG`, `COLOR_EYE`, `COLOR_ACCENT`, `LEFT_EYE_CENTER`, `RIGHT_EYE_CENTER`, `BASE_RADIUS`, `MIN_OPEN_RATIO`, `MAX_LOOK_OFFSET_X`, `MAX_LOOK_OFFSET_Y`, `MIN_SCALE`, `MAX_SCALE`, `DEFAULT_BLINK_DURATION`, etc.
  - `easing.py`: `smoothstep(t)`, `smootherstep(t)`, `cubic_in_out(t)`, `quad_out(t)`, `elastic_out(t)`, `exp_decay(current, target, rate, dt)`.

- [ ] **Step 1: Write `experiment-3/config.py`**
- [ ] **Step 2: Write `experiment-3/easing.py`**
- [ ] **Step 3: Test easing curves and configuration exports**

---

### Task 2: Eye Model & Parametric Geometry

**Files:**
- Create: `experiment-3/eye.py`

**Interfaces:**
- Consumes: `config.py`, `easing.py`
- Produces:
  - `Eye`: Dataclass/object with `base_cx`, `base_cy`, `radius`, `open_amount`, `look_x`, `look_y`, `scale_x`, `scale_y`, `tilt_deg`.
  - `Eye.get_geometry()` -> returns `(cx, cy, width, height, corner_radius)`
  - `EyePair`: Manages left and right eyes, synchronized or independent gaze/morph/scale.

- [ ] **Step 1: Implement `Eye` and `EyePair` classes**
- [ ] **Step 2: Implement `get_geometry()` producing exact circle when $o=1.0$ and stadium pill when $o<1.0$**
- [ ] **Step 3: Test geometry calculation against mathematical bounds**

---

### Task 3: Pygame Rendering Engine

**Files:**
- Create: `experiment-3/renderer.py`

**Interfaces:**
- Consumes: `config.py`, `eye.py`
- Produces:
  - `Renderer`: `__init__(width, height)`, `draw_eye(surface, eye)`, `render_frame(eye_pair)` -> `pygame.Surface`
  - Clean anti-aliased or border-radius drawing of stadium shapes and circles on black canvas.

- [ ] **Step 1: Implement `Renderer` class with Pygame surface operations**
- [ ] **Step 2: Implement `render_frame` handling background clearance and dual-eye drawing**
- [ ] **Step 3: Test rendering headless with `SDL_VIDEODRIVER=dummy`**

---

### Task 4: Organic Animation & State Controller

**Files:**
- Create: `experiment-3/animation.py`

**Interfaces:**
- Consumes: `config.py`, `easing.py`, `eye.py`
- Produces:
  - `FaceController`: Coordinates continuous eye parameters with target smoothing (look offset, scale, opening).
  - Handles automatic breathing idle micro-scale, realistic blinks, saccade shifts, and manual override targets.
  - `update(dt: float)`: Updates all physics/easing values by elapsed seconds.

- [ ] **Step 1: Implement `FaceController` with exponential decay smoothing**
- [ ] **Step 2: Implement natural blink trigger and breathing cycle**
- [ ] **Step 3: Test delta-time progression and target convergence**

---

### Task 5: Interactive Showcase Application

**Files:**
- Create: `experiment-3/showcase.py`

**Interfaces:**
- Consumes: `config.py`, `eye.py`, `renderer.py`, `animation.py`
- Produces:
  - Interactive Pygame main loop running at 60 FPS on 800x480.
  - Keybindings for manual test:
    - `UP / DOWN / LEFT / RIGHT`: Look offsets
    - `C`: Center look
    - `SPACE`: Trigger natural blink
    - `O`: Toggle open/close morphing
    - `S`: Trigger surprise scale bump
    - `A`: Toggle auto-idle/demo choreography
    - `H`: Toggle debug HUD (FPS, parameters)
    - `ESC / Q`: Quit

- [ ] **Step 1: Implement showcase event handling and render loop**
- [ ] **Step 2: Implement debug HUD displaying real-time metrics**
- [ ] **Step 3: Support `--headless` and `--demo` CLI flags**

---

### Task 6: Headless Verification Suite & Documentation

**Files:**
- Create: `experiment-3/verify.py`
- Create: `experiment-3/README.md`

**Interfaces:**
- Produces:
  - `verify.py`: Runs automated headless assertions checking:
    1. Independent execution with no `experiment-2` dependencies.
    2. 800x480 display surface creation.
    3. Eye circle-to-pill geometric morphing correctness.
    4. Gaze offset and scale modulation calculations.
    5. Delta-time animation stability.
  - `README.md`: Architecture overview, mathematical principles, run instructions, and keybindings.

- [ ] **Step 1: Implement `verify.py` comprehensive test suite**
- [ ] **Step 2: Run `verify.py` and ensure 100% passing tests**
- [ ] **Step 3: Write complete `README.md`**
- [ ] **Step 4: Verify git status confirms zero changes to `experiment-2/`**
