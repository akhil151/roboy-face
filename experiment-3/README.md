# ELO Face V3 — Automated Emotion Timeline & Expanded Expression Engine (Stage 3)

A clean, modular, independent Pygame animation engine implementing the "Big Eyes" minimalist visual identity, automated 103-second expression timeline, and comprehensive 20-expression emotional vocabulary for the ELO robotic face.

Designed for an **800x480** display on **Raspberry Pi 5** and desktop environments at **60 FPS**.

---

## Complete 103-Second Timeline Experience (21 Segments)

The system plays a synchronized 103.0-second automated sequence across 21 distinct segments:

| # | Segment | Duration | Visual & Emotional Behavior |
|---|---|---|---|
| 1 | `intro` | 10.0s | Typewriter "Hii" -> hold -> fade -> "This is ELO." -> hold -> fade -> face fade-in |
| 2 | `settle` | 3.5s | Baseline neutral open eyes ($o = 1.0$), centered gaze, subtle organic breathing |
| 3 | `blink` | 3.5s | Two slow natural eyelid blinks in succession via pure vertical squash morphing |
| 4 | `look_horizontal` | 5.0s | Center -> Glance Left -> Hold -> Glance Right -> Hold -> Center |
| 5 | `look_vertical` | 4.5s | Center -> Glance Up -> Hold -> Glance Down -> Hold -> Center |
| 6 | `curious` | 4.5s | Inquisitive gaze shift right ($dx=+35, dy=-10$), asymmetric squint ($o_L=1.0, o_R=0.82$), micro-inspection |
| 7 | `confused` | 4.5s | Hesitant look left with left squint ($o_L=0.82$) -> center -> look right with right squint ($o_R=0.82$) |
| 8 | `surprise` | 3.5s | Big eyes reaction: rapid scale burst to $1.35\times$ -> hold -> smooth settle |
| 9 | `excited` | 4.5s | High-energy scale burst to $1.25\times$ with fast vertical bouncing ($3.2\text{ Hz}$) and synchronous pulsing |
| 10 | `happy_bounce` | 4.5s | Vertical rhythmic hopping ($2.2\text{ Hz}$) with exponentially decaying amplitude at base scale ($1.0\times$) |
| 11 | `wink` | 3.5s | Asymmetric wink: Left eye open ($1.0$), Right eye squashes closed ($0.0$) -> reopens |
| 12 | `playful_double_wink` | 4.5s | Alternating winks: Right eye wink -> neutral -> Left eye wink -> neutral |
| 13 | `shy` | 4.5s | Bashful downward/side glance ($dx=-22, dy=+28$), gentle eyelid droop ($o=0.65$), subtle soft blush ($\alpha \le 70$) |
| 14 | `cute_blush` | 5.0s | Soft pink rounded stadium strokes beneath eyes with full alpha envelope ($\alpha = 180$) |
| 15 | `thinking` | 5.0s | Contemplative upward & sideways gaze drift ($dx=+24, dy=-34$) with thoughtful squint ($o=0.40$) |
| 16 | `suspicious` | 4.5s | Skeptical side-eye ($dx=+50, dy=+5$), deliberate moderate eye narrowing ($o=0.48$) |
| 17 | `angry` | 4.5s | High horizontal squash into narrow slits ($o=0.30$), compact scale ($0.94\times$), locked downward focus, tension pulsing ($5\text{ Hz}$) |
| 18 | `scared_nervous` | 4.5s | Rapid elastic scale expansion ($1.28\times$) combined with high-frequency micro-tremor jitter ($14\text{ Hz}$) |
| 19 | `sad` | 5.0s | Deflated scale ($0.94\times$), heavy downward gaze ($dy=+34$), melancholic eyelid droop ($o=0.52$), sluggish breathing |
| 20 | `drowsy` | 5.0s | Eyelids droop to half-closed ($o \approx 0.38$) with gentle sleepy wobble & head nod |
| 21 | `sleep` | 9.0s | Eyes smoothly close ($o = 0.0$), floating 'Z' particles drift upward with sine sway |
| — | `loop` | — | Automatically loops back to segment 1 seamlessly |

---

## Visual Design Language & Emotion Distinctions

- **Minimalist & Clean:** Pure black background `(0, 0, 0)` with two solid white eyes `(255, 255, 255)`.
- **Zero Clutter:** No pupils, no sclera, no separate eyelid shapes, no eyebrows, no face outlines or chassis graphics.
- **Single Rounded Shape:** Each eye is rendered as a single continuous rounded geometric shape.
- **Continuous Squash Morphing:** Eye opening/closing is a pure vertical squash morph:
  - **Open ($o = 1.0$):** Perfect geometric circle ($W = H = 2R$, corner radius $r = R$).
  - **Closed ($o = 0.0$):** Horizontally elongated rounded capsule / stadium pill ($W > H$, corner radius $r = H/2$).
- **No Eyebrows Needed:** Strong emotions like Anger are communicated through high horizontal squash ($o = 0.30$), compact scale ($0.94\times$), locked forward/downward focus, and tension micro-pulsing.
- **Nuanced Pairwise Differentiation:**
  - *Curious vs. Confused:* Curious is focused to one side with steady inspection asymmetry; Confused hesitates left then right with alternating squints.
  - *Happy Bounce vs. Excited:* Happy Bounce uses decaying hops at baseline scale; Excited maintains sustained scale enlargement ($1.25\times$) with rapid bounce ($3.2\text{ Hz}$) and pulsing.
  - *Angry vs. Suspicious:* Angry narrows severely ($o = 0.30$) with compact scale; Suspicious narrows moderately ($o = 0.48$) with heavy lateral side-eye ($dx = +50$).
  - *Surprise vs. Scared/Nervous:* Surprise has a clean, wide, motionless gaze; Scared/Nervous adds high-frequency tremor jitter.
  - *Shy vs. Sad:* Shy glances sideways/down with soft blush accent; Sad gazes straight down with deflated scale and no blush.
  - *Drowsy vs. Sad:* Drowsy droops eyes to $0.38$ with nodding wobble at normal scale; Sad droops to $0.52$ with heavier downward gaze and deflated scale.

---

## Architecture & File Structure

```
experiment-3/
├── config.py         # Centralized configuration (display, layout, colors, 21 timeline segments, limits)
├── easing.py         # Mathematical easing curves (cubic, quad, elastic) and framerate-independent smoothing
├── eye.py            # Eye & EyePair data models and parametric stadium/circle geometry
├── effects.py        # Intro typewriter state, blush opacity envelope, and sleep 'Z' particles
├── timeline.py       # Data-driven 21-segment 103s timeline sequencer with jump/pause controls
├── renderer.py       # Layered Pygame rendering engine (eyes, blush, particles, typewriter text, HUD)
├── animation.py      # FaceController coordinator & 20 emotional behavior handlers
├── showcase.py       # Interactive 60 FPS Pygame application with manual jump keys & HUD
├── verify.py         # Automated headless test suite (math, timing, pairwise distinctions, full 103s simulation)
└── README.md         # Documentation and usage guide
```

---

## How to Run

### Interactive Showcase
```bash
python experiment-3/showcase.py
```

### Start Directly at Any Specific Segment
```bash
python experiment-3/showcase.py --start-at curious
python experiment-3/showcase.py --start-at angry
python experiment-3/showcase.py --start-at scared_nervous
python experiment-3/showcase.py --start-at excited
python experiment-3/showcase.py --start-at sleep
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
| **6** | Jump to `curious` (4.5s) |
| **7** | Jump to `confused` (4.5s) |
| **8** | Jump to `surprise` (3.5s) |
| **9** | Jump to `excited` (4.5s) |
| **0** | Jump to `happy_bounce` (4.5s) |
| **-** | Jump to `drowsy` (5.0s) |
| **=** | Jump to `sleep` (9.0s) |
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
