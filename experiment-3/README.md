# ELO Face V3 — Automated Emotion Timeline & Expression Engine (Stage 2)

A clean, modular, independent Pygame animation engine implementing the "Big Eyes" minimalist visual identity and automated 62-second expression timeline for the ELO robotic face.

Designed for an **800x480** display on **Raspberry Pi 5** and desktop environments at **60 FPS**.

---

## Complete 62-Second Timeline Experience

The system plays a synchronized 62.0-second automated loop with 12 distinct segments:

| # | Segment | Duration | Visual & Emotional Behavior |
|---|---|---|---|
| 1 | `intro` | 10.0s | Typewriter "Hii" -> hold -> fade -> "This is ELO." -> hold -> fade -> face fade-in |
| 2 | `settle` | 3.5s | Baseline neutral open eyes ($o = 1.0$), centered gaze, subtle organic breathing |
| 3 | `blink` | 3.5s | Two slow natural eyelid blinks in succession via pure vertical squash morphing |
| 4 | `look_horizontal` | 5.0s | Center -> Glance Left -> Hold -> Glance Right -> Hold -> Center |
| 5 | `look_vertical` | 4.5s | Center -> Glance Up -> Hold -> Glance Down -> Hold -> Center |
| 6 | `surprise` | 3.5s | Big eyes reaction: rapid scale burst to $1.35\times$ -> hold -> smooth settle |
| 7 | `wink` | 3.5s | Asymmetric wink: Left eye open ($1.0$), Right eye squashes closed ($0.0$) -> reopens |
| 8 | `playful_double_wink` | 4.5s | Alternating winks: Right eye wink -> neutral -> Left eye wink -> neutral |
| 9 | `happy_bounce` | 4.5s | Vertical rhythmic hopping ($2.2\text{ Hz}$) with exponentially decaying amplitude |
| 10 | `cute_blush` | 5.0s | Soft pink rounded stadium strokes beneath eyes with smooth alpha envelope |
| 11 | `drowsy` | 5.0s | Eyelids droop to half-closed ($o \approx 0.42$) with gentle sleepy wobble & head nod |
| 12 | `sleep` | 9.5s | Eyes smoothly close ($o = 0.0$), floating 'Z' particles drift upward with sine sway |
| 13 | `loop` | — | Automatically loops back to segment 1 seamlessly |

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
- **Soft Accent Overlays:** Layered blush cheeks (`(255, 160, 185)`) and floating sleep particles (`z`) rendered with per-pixel alpha transparency.

---

## Architecture & File Structure

```
experiment-3/
├── config.py         # Centralized configuration (display, layout, colors, timeline segments, limits)
├── easing.py         # Mathematical easing curves and framerate-independent smoothing
├── eye.py            # Eye & EyePair data models and parametric stadium/circle geometry
├── effects.py        # Intro typewriter state, blush opacity envelope, and sleep 'Z' particles
├── timeline.py       # Data-driven 12-segment 62s timeline sequencer with jump/pause controls
├── renderer.py       # Layered Pygame rendering engine (eyes, blush, particles, typewriter text, HUD)
├── animation.py      # FaceController coordinator & 11 emotional behavior handlers
├── showcase.py       # Interactive 60 FPS Pygame application with manual jump keys & HUD
├── verify.py         # Automated headless test suite (math, timing, curves, full 62s simulation)
└── README.md         # Documentation and usage guide
```

---

## How to Run

### Interactive Showcase
```bash
python experiment-3/showcase.py
```

### Start Directly at a Specific Segment
```bash
python experiment-3/showcase.py --start-at sleep
python experiment-3/showcase.py --start-at cute_blush
python experiment-3/showcase.py --start-at happy_bounce
```

### Headless Verification Test
```bash
python experiment-3/verify.py
```

---

## Interactive Controls (Showcase)

| Key | Action |
|---|---|
| **1** | Jump to `intro` (10.0s) |
| **2** | Jump to `settle` (3.5s) |
| **3** | Jump to `blink` (3.5s) |
| **4** | Jump to `look_horizontal` (5.0s) |
| **5** | Jump to `look_vertical` (4.5s) |
| **6** | Jump to `surprise` (3.5s) |
| **7** | Jump to `wink` (3.5s) |
| **8** | Jump to `playful_double_wink` (4.5s) |
| **9** | Jump to `happy_bounce` (4.5s) |
| **0** | Jump to `cute_blush` (5.0s) |
| **-** | Jump to `drowsy` (5.0s) |
| **=** | Jump to `sleep` (9.5s) |
| **RIGHT** / **N** | Advance immediately to next segment |
| **LEFT** / **P** | Jump back to previous segment |
| **SPACE** | Toggle Pause / Resume timeline progression |
| **R** | Restart timeline from Intro |
| **H** | Toggle on-screen debug HUD overlay |
| **ESC** / **Q** | Quit |

---

## Module Independence & Safety Guarantees

- **100% Isolated from V2:** Zero imports or couplings to `experiment-2/` or legacy files.
- **Framerate Agnostic:** All animation physics, eases, and timeline updates compute with elapsed delta time (`dt`).
- **Headless Verified:** Runs off-screen with dummy SDL video drivers for automated CI/CD validation.
