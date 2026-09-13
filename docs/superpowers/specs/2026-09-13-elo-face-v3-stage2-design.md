# ELO Face V3 — Stage 2: Intro + Emotion Sequencing Design Specification

**Date:** 2026-09-13
**Target Platform:** Raspberry Pi 5 / Desktop Pygame (800x480, 60 FPS)
**Scope:** Stage 2 — 62-second automated timeline sequence with Intro + 11 expressive emotional behaviors.

---

## 1. Sequence Overview & Timing Architecture

The total timeline duration is exactly 62.0 seconds, structured into 12 distinct segments:

| # | Segment Name | Duration | Description |
|---|---|---|---|
| 1 | `intro` | 10.0s | Polished typewriter: "Hii" → fade → "This is ELO." → fade → smooth transition to face |
| 2 | `settle` | 3.5s | Both eyes fully open ($o=1.0$), centered, subtle organic breathing baseline |
| 3 | `blink` | 3.5s | Two slow, organic natural blinks in succession (both eyes together) |
| 4 | `look_horizontal` | 5.0s | Smooth horizontal gaze sweep: Center → Left → Hold → Right → Hold → Center |
| 5 | `look_vertical` | 4.5s | Smooth vertical gaze sweep: Center → Up → Hold → Down → Hold → Center |
| 6 | `surprise` | 3.5s | Big eyes reaction: Quick smooth scale growth ($1.35\times$) with slight elastic ease → Hold → Return |
| 7 | `wink` | 3.5s | Single eye wink: One eye stays open, the other smoothly squashes closed, holds, reopens |
| 8 | `playful_double_wink`| 4.5s | Alternating winks: Right wink → Brief neutral → Left wink → Return neutral |
| 9 | `happy_bounce` | 4.5s | Rhythmic vertical hopping with decaying amplitude and natural settling |
| 10| `cute_blush` | 5.0s | Soft pink rounded stadium strokes beneath both eyes: Fade-in → Hold → Fade-out |
| 11| `drowsy` | 5.0s | Eyes droop to half-closed ($o \approx 0.45$) with subtle sleepy settling wobble |
| 12| `sleep` | 9.5s | Eyes fully close ($o \to 0.0$); floating upward drifting 'z' particles spawn & loop |
| — | **Total Loop** | **62.0s** | Seamless loop back to Intro (or Settle in demo loop mode) |

---

## 2. Component Details

### A. Intro Typewriter System
- Phase A (0.0s – 4.2s): "Hii"
  - Typewriter character reveal (0.0s – 0.6s)
  - Blinking cursor & hold (0.6s – 3.2s)
  - Smooth alpha fade out (3.2s – 4.2s)
- Phase B (4.2s – 8.8s): "This is ELO."
  - Typewriter reveal (4.2s – 5.4s)
  - Hold & cursor (5.4s – 7.8s)
  - Smooth alpha fade out (7.8s – 8.8s)
- Phase C (8.8s – 10.0s): Smooth transition / face fade-in into Settle.

### B. Emotion Handlers & Mathematical Curves
- **Horizontal Look:** Cubic in-out trajectory along $dx \in [-55, +55]$ px.
- **Vertical Look:** Restrained trajectory along $dy \in [-35, +35]$ px.
- **Surprise:** Scale pulse $s(t) = 1.0 + 0.35 \cdot \text{smootherstep}(...)$.
- **Wink & Double Wink:** Asymmetric `open_amount` targeting per eye ($o_L, o_R$).
- **Happy Bounce:** Damped harmonic vertical hop $y(t) = -A \cdot e^{-\lambda t} \cdot |\sin(\omega t)|$.
- **Cute Blush:** Dual rounded pink stadium shapes rendered beneath eyes with smooth alpha curve.
- **Drowsy:** Eye open amount droops to $0.45$ with subtle low-frequency head nod / wobble ($dy \approx 4 \cdot \sin(2\pi f t)$).
- **Sleep:** Eye open amount reaches $0.0$, subtle breathing slows down, and floating 'Z' particles spawn periodically, drift upward with gentle horizontal sine sway, and fade out.

---

## 3. Architecture & Separation

All code remains strictly inside `experiment-3/`:
- `config.py`: Centralized timing table and effect presets.
- `effects.py`: Intro text renderer, Blush overlay, and Floating sleep particle manager.
- `timeline.py`: Data-driven timeline sequencer and state manager.
- `animation.py`: Dedicated segment update routines.
- `renderer.py`: Layered rendering (Background → Eyes → Blush → Sleep Particles → Intro Text → HUD).
- `showcase.py`: Full demo playback with timeline jumping keys (1-9, 0, J, K, Space).
- `verify.py`: Headless test suite verifying timeline durations, transitions, and math.
