# ELO Face V3 (Experiment 3) Foundation Design Specification

**Date:** 2026-09-13
**Target Platform:** Raspberry Pi 5 / Desktop Pygame (800x480, 60 FPS)
**Scope:** V3 Foundation Engine — Pure "Big Eyes" Morphing, Gaze, and Scale System

---

## 1. Executive Summary & Goals

The ELO Face V3 project introduces a minimalist "Big Eyes" robotic visual identity designed for an 800x480 display on Raspberry Pi 5.

### Key Visual & Mechanical Rules:
- **Zero graphical clutter:** Black background, two solid white eye shapes, no pupils, no sclera, no separate eyelids, no eyebrows, no face borders.
- **Morphing Principle:** Eye opening/closing is a continuous vertical squash morph between a full circle ($W=H=2R$) and a horizontally elongated rounded pill / stadium ($W > H$, with corner radius $r = H/2$).
- **Gaze & Scale:** Smooth gaze offsets ($dx, dy$) and scale modulation ($s$) layered cleanly over base eye coordinates.
- **Organic Motion:** High-quality easing, smooth dampening, and micro-idling to prevent robotic stiffness.
- **Strict Isolation:** Completely isolated in `experiment-3/` with no coupling to `experiment-2/` or legacy directories.

---

## 2. Architecture & File Structure

All code lives in `experiment-3/`:

```
experiment-3/
├── config.py         # Centralized configuration (display, colors, geometry, timing)
├── easing.py         # Easing curves (smoothstep, cubic_in_out, damp, exponential decay)
├── eye.py            # Eye & EyePair data models + parametric geometry calculator
├── renderer.py       # Pygame rendering engine (800x480, anti-aliased pill drawing, clean canvas)
├── animation.py      # Animation controller & state sequencer (blinking, gaze, breathing, transitions)
├── showcase.py       # Main interactive Pygame entry point with demo & debug controls
├── verify.py         # Automated headless test suite verifying all 12 core requirements
└── README.md         # Documentation, run instructions, keybindings, and architectural overview
```

---

## 3. Mathematical Model for Eye Geometry

Each eye is defined parametrically:
- **Base Center:** $(cx_0, cy_0)$ (configured for 800x480 display, e.g. Left eye at $x=270, y=240$, Right eye at $x=530, y=240$)
- **Base Radius:** $R$ (e.g. $85$ px)
- **Open Amount:** $o \in [0.0, 1.0]$ where $1.0$ is full circle, $0.0$ is closed pill / flat slit
- **Look Offset:** $(dx, dy)$ in pixels or normalized units
- **Scale Multiplier:** $s \in [0.5, 1.5]$ (default $1.0$)
- **Aspect Ratio Modifiers:** $w_{factor}, h_{factor}$ (allowing slight horizontal expansion during blink squash)

### Geometry Calculation:
1. Current Center:
   $$cx = cx_0 + dx$$
   $$cy = cy_0 + dy$$
2. Dimensions:
   $$W = 2 \cdot R \cdot s \cdot (1.0 + (1.0 - o) \cdot 0.15)$$
   $$H = 2 \cdot R \cdot s \cdot (h_{min} + (1.0 - h_{min}) \cdot o)$$
   where $h_{min} \approx 0.08$ (ensuring closed state is a sleek thin pill line).
3. Corner Radius:
   $$r_{corner} = \min(W/2, H/2) = H/2$$
   When $o = 1.0$, $W \approx 2R \cdot s$ and $H = 2R \cdot s \implies r_{corner} = R \cdot s$, producing an exact geometric circle.
   When $o < 1.0$, $H < W \implies$ the shape smoothly squashes into a rounded stadium pill.

---

## 4. Animation & Easing Engine

To achieve an organic feel:
- **Critically Damped Spring / Exp Decay Smoothing:** Gaze target changes and scale adjustments use frame-rate independent exponential smoothing:
  $$x_{current} \leftarrow x_{current} + (x_{target} - x_{current}) \cdot (1 - e^{-\lambda \cdot dt})$$
- **Blink Cycle:** Parametric asymmetric cubic bezier / smoothstep curve:
  - Close phase: Fast, crisp ($~0.08$ s)
  - Hold closed: Sub-frame / minimal ($~0.02$ s)
  - Re-open phase: Smooth, elastic settle ($~0.14$ s)
- **Natural Micro-Movement:** Subtle idle breathing modulation ($~0.015$ scale variation at $0.25$ Hz) and occasional gaze micro-saccades.

---

## 5. Renderer Specifications

- Display: 800x480 32-bit RGB.
- Surface Double-Buffering at 60 FPS.
- Eye Drawing: Uses `pygame.draw.rect(surface, color, rect, border_radius=int(r))` with sub-pixel rounding accuracy.
- Clean separation: Renderer takes an `EyePair` snapshot and outputs the frame without modifying animation state.

---

## 6. Verification & Quality Gates

The test suite in `experiment-3/verify.py` will validate:
1. **Independence:** Zero imports or file references to `experiment-2/` or legacy engines.
2. **Headless Execution:** Fully runnable under `SDL_VIDEODRIVER=dummy`.
3. **Display Integrity:** Correct 800x480 surface dimensions and black background clearance.
4. **Morphing Correctness:** Open amount values smoothly transition geometry $H \in [H_{min}, 2R]$.
5. **Gaze & Offset Bounds:** Look offsets accurately track targets within safe bounding limits.
6. **Scale Integrity:** Scale multipliers dynamically expand/contract bounding rects accurately.
7. **Framerate Stability:** Delta-time calculation handles 60 FPS smoothly.
