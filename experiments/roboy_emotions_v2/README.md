# ROBoy Emotion V2 — isolated prototype

A brand-new, **isolated** visual-expression design iteration for the ROBoy face.
This folder does **not** touch, import, or replace the existing production
animation system (`eyes/`, `face/`, `les/`). It is a self-contained experiment
that tries to reproduce the reference image's robot-expression language:

- black background, clean cyan/turquoise elements
- simple geometric, deliberately shaped eyes
- minimal mouth geometry
- strong silhouette-based expressions
- no chassis, border, camera, or HUD clutter

## Files

| File         | Responsibility                                              |
|--------------|-------------------------------------------------------------|
| `config.py`  | All tunable parameters (sizes, colours, timings)            |
| `geometry.py`| Normalized→pixel transform and drawing primitives            |
| `animations.py` | Deterministic time-based motion helpers (sine/modulo)   |
| `face.py`    | `FaceSpec` model + per-emotion geometry builders            |
| `overlays.py`| THINKING `?` and SLEEPY `ZZZ` lifecycle builders            |
| `emotions.py`| 14-emotion registry + showcase key mapping                  |
| `renderer.py`| Draws a `FaceSpec` onto a pygame surface                    |
| `showcase.py`| Interactive window with keyboard controls + CLI options     |
| `verify.py`  | Headless verification suite                                  |

## The 14 emotions

`neutral, happy, excited, sad, surprised, thinking, confused, wink, love,
tired, sleepy, angry, fearful, disgusted`

Every emotion has deliberate, hand-tuned geometry (not a rotated circle):

- **angry** — slanted `\_` / `__/` eye polygons with the inner corner dropped
- **sleepy** — relaxed `‿` (U-shaped) closed eyes + drifting `ZZZ`
- **thinking** — `?` anchored to the eye's outer-top perimeter, never between eyes
- **love** — heart-shaped eye elements
- **wink** — one open eye, one closed arc, playful smile
- **sad / surprised / excited / happy / tired / confused / fearful / disgusted**
  each use distinct eye arcs, lids, or asymmetry.

## Run the showcase

```
py showcase.py
```

Launch straight into an emotion / static mode:

```
py showcase.py --emotion sleepy --static
py showcase.py --emotion angry
```

### Controls

| Key | Action |
|-----|--------|
| 1-9 | neutral, happy, excited, sad, surprised, thinking, confused, wink, love |
| 0   | tired |
| A   | sleepy |
| S   | angry |
| D   | fearful |
| F   | disgusted |
| SPACE | replay current emotion (reset time) |
| R   | reset |
| P   | toggle PAUSED / STATIC (freeze base geometry for comparison) |
| H   | toggle HUD (OFF by default) |
| ESC | exit |

## Comparison mode

Press **P** to freeze the animation and inspect the static base geometry
against the reference. `--static` starts frozen.

## Visual review sheet

```
py visual_review.py
```

Renders all 14 emotions in a grid using the same V2 renderer. `SPACE`
toggles STATIC (frozen geometry, `t=0`) vs ANIMATED; `H` toggles labels.
This is an inspection-only tool, not production code.

The showcase (`showcase.py`) also has a STATIC comparison mode: `P` freezes
the animation so you can inspect the pure base geometry (no breathing,
blinking, drifting, or overlay motion).

## Verify

```
py verify.py
```

Checks that all 14 emotions build/render, stay in bounds, keep the `?`/`ZZZ`
clear of the eyes, that ZZZ sizes/alpha decrease and repeat, that angry eyes
slant inward-downward, that wink has one closed eye, love has two hearts, the
animation is deterministic, and that no production files were added elsewhere.

## Notes / limitations

- Hearts, `?` and `Z` keep the cyan palette for a cohesive look (no red hearts).
- Visual quality is judged from the actual window, not from the tests.
- Not yet integrated with LES; this is a visual-design probe only.
