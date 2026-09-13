# ELO Face V3 — Experiment 3 Foundation Engine

A clean, modular, independent Pygame animation engine implementing the "Big Eyes" minimalist visual identity for the ELO robotic face.

Designed for an **800x480** display on **Raspberry Pi 5** and desktop environments at **60 FPS**.

---

## Visual Design Language

- **Minimalist & Clean:** Pure black background `(0, 0, 0)` with two solid white eyes `(255, 255, 255)`.
- **Zero Clutter:** No pupils, no sclera, no separate eyelid shapes, no eyebrows, no face outlines or chassis graphics.
- **Single Rounded Shape:** Each eye is rendered as a single continuous rounded geometric shape.
- **Continuous Squash Morphing:** Eye opening/closing is a pure vertical squash morph:
  - **Open ($o = 1.0$):** Perfect geometric circle ($W = H = 2R$, corner radius $r = R$).
  - **Closed ($o = 0.0$):** Horizontally elongated rounded capsule / stadium pill ($W > H$, corner radius $r = H/2$).
- **Gaze & Scale Mechanics:** Smooth gaze displacement ($(dx, dy)$) and scale modulation ($s$) layer seamlessly over base eye coordinates.
- **Organic Motion:** Uses framerate-independent exponential decay smoothing (`exp_decay`), natural asymmetric eyelid blinks, and subtle idle breathing oscillations.

---

## Architecture & File Structure

```
experiment-3/
├── config.py         # Centralized configuration (display, layout, colors, limits, timing)
├── easing.py         # Mathematical easing curves and framerate-independent smoothing
├── eye.py            # Eye & EyePair data models and parametric stadium/circle geometry
├── renderer.py       # Pure Pygame rendering engine (draws solid rounded eyes and HUD)
├── animation.py      # Motion controller (blinking, gaze smoothing, scale, breathing, auto-idle)
├── showcase.py       # Interactive Pygame application with manual and auto controls
├── verify.py         # Automated headless test suite verifying all foundation requirements
└── README.md         # Documentation and usage guide
```

---

## How to Run

### Interactive Showcase
```bash
python experiment-3/showcase.py
```

### Auto-Idle Demo Mode
```bash
python experiment-3/showcase.py --demo
```

### Headless Verification Test
```bash
python experiment-3/verify.py
```

---

## Interactive Controls (Showcase)

| Key | Action |
|---|---|
| **Arrow Keys** (`↑` `↓` `←` `→`) | Shift gaze direction (Look Up, Down, Left, Right) |
| **C** | Center gaze `(0, 0)` |
| **SPACE** | Trigger organic eyelid blink |
| **O** | Toggle full circle $\leftrightarrow$ closed pill morph |
| **1 / 2 / 3 / 4** | Set open state ($1.0$, $0.60$, $0.25$, $0.0$) |
| **S** | Trigger surprise scale burst ($1.30\times$) |
| **+** / **=** | Increase eye scale |
| **-** | Decrease eye scale |
| **A** | Toggle auto-idle / demo choreography |
| **B** | Toggle subtle breathing pulse |
| **R** | Reset all parameters to default state |
| **H** | Toggle on-screen debug HUD overlay |
| **ESC** / **Q** | Quit |

---

## Extensibility for Future V3 Expressions

The foundation decouples geometry calculation (`eye.py`), rendering (`renderer.py`), and animation sequencing (`animation.py`). Future expression sequences (happy, surprised, sleepy, blush accents) can easily be added by:
1. Defining target parameter presets (e.g. `open_amount`, `look_x`, `look_y`, `scale`, `tilt`) in an emotion registry.
2. Invoking `controller.set_target_*()` or sequencing keyframes in `animation.py`.
3. Rendering soft pink blush accents using `config.COLOR_ACCENT` without altering the core eye geometry.
