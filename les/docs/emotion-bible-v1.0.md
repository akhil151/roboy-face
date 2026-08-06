# LES Emotion Bible v1.0

**The permanent animation & behavior design reference for every emotional behavior in the Living Expression System.**

**Version 1.0** · Status: **Design reference (implementation-neutral)** · Audience: animation directors, HRI designers, LES engineers

---

## How to read this document

This is a **design manual, not an implementation spec**. It defines *what each emotion is*, *how it should look*, *how it should move*, and *why*. It deliberately contains no algorithms, no classes, no APIs, and no code. Companion documents:

- `les/docs/README.md` — LES architecture (the scaffold)
- `les/docs/behavior-spec-v1.0.md` — behavior spec: timing tables, transition rules, personality model, timelines

The Bible is the **emotional soul** of the system: the single permanent reference animation directors will consult when the robot feels "wrong," and engineers will consult when a beat "reads wrong." If the Bible and the behavior spec ever disagree, the **Bible wins on emotion**, the **spec wins on timing**.

## Provenance legend

Every claim is tagged:

| Tag | Meaning |
|---|---|
| **[OBSERVED]** | Observed in product demos / reviews / recordings of expressive companion robots (chiefly LivingAI Aibi) |
| **[PRINCIPLE]** | Established animation / character-design principle |
| **[RESEARCH]** | Quantitative HRI or psychophysical research (provenance in behavior-spec Appendix A) |
| **[ENGINEERING RECOMMENDATION]** | The normative design decision of this document |
| **[HYPOTHESIS]** | Extrapolation — requires Phase-1 validation |

## The Master Mood Compass

Every emotion lives on two axes: **arousal** (energy) and **valence** (positivity).

```
                  HIGH AROUSAL
                      │
        Surprised ●   │   ● Happy
            Focus ●   │   ● Speaking
                      │
   NEGATIVE ──────────┼────────── POSITIVE
    SAD ●    Thinking ●   ● Listening
                      │   ● Caring
             Sleepy ● │   ● Calm
                      │
                  LOW AROUSAL
```

**[ENGINEERING RECOMMENDATION]** Transitions should generally travel *short arcs* across this compass — a long diagonal jump (Sad → Surprised) must be routed through a midpoint (Section: Transition Rules, per emotion; and behavior-spec 10.2).

---

# PART I — THE TEN EMOTION PAGES

---

# E1 · CALM

> *The resting presence. The state the robot returns to. The state from which all others depart and into which all others decay.*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"I am here, I am safe, I am at ease."* Calm is the emotional **backstop** — it must never feel like "off," only like "resting." It is the canvas every other emotion is painted on and the place every emotion returns to heal. [PRINCIPLE: emotional recovery requires a neutral state]

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Full (≈1.0) | Open, unalarmed, available |
| Upper eyelid | Flat, minimal arch (≈0 curvature) | No tension, no surprise |
| Lower eyelid | Flat, resting (≈0 curvature) | No smile-line, no frown-line |
| Curvature | ~0 both lids | Neutral geometry = neutral read [PRINCIPLE] |
| Eye compression | None (scale_x ≈ scale_y ≈ 1.0) | Relaxed, un-squinted |
| Symmetry | Near-perfect | Calm is the one state where symmetry is *allowed* (see E1.15 caveat) |
| Softness | High — rounded, soft edges | Approachability |
| Gaze intensity | Low — no directed intensity | Peaceful, not staring |

## 3. Behavior Identity

Gentle · peaceful · present · patient · **unhurried**. A calm robot is the emotional equivalent of a still pond — present, reflective, never demanding. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | Moderate — stable but breathing | Fixation holds 1.5–4 s [RESEARCH: human fixation range] |
| Gaze drift | Very slow, 1–2 px over 4–8 s | Imperceptible; the "awake, not staring" tell [PRINCIPLE] |
| Micro corrections | 1 per 4–8 s, ≤0.5 px | Prevents dead-eye lock [PRINCIPLE] |
| Look direction | Center, no targets | Calm never looks *for* anything |
| Eye speed | Slowest in the system | All movements ≤ 2 px/s baseline |
| Hold timing | Long, comfortable | A calm gaze can hold 5–8 s between events |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | Soft blink (E-variant of normal, gentle curve) | Softness matches the emotion |
| Interval | 3.0–5.0 s, randomized [ENGINEERING RECOMMENDATION] | Never periodic — periodic blinks read robotic [PRINCIPLE] |
| Duration | 180 ms (soft: ~220 ms) | Human norm is 150–400 ms [RESEARCH] |
| Hold | ~50 ms full closure | Human blink closure ~50 ms [RESEARCH] |
| Recovery | Slow, soft re-open, no overshoot | Recovery defines gentleness [PRINCIPLE] |

**Why:** Calm's blink is the *quiet punctuation* of a peaceful presence — frequent enough to prove aliveness, slow enough to prove relaxation. [ENGINEERING RECOMMENDATION]

## 6. Micro Motion

- Breathing: 4.5–5.4 s cycle, gentle amplitude — the heartbeat of the calm state [ENGINEERING RECOMMENDATION; RESEARCH: 4–6 s breathing loops]
- Idle noise: sub-threshold 0.2–0.4 px, always on — **micro motion never stops** [PRINCIPLE]
- Eye drift: the only voluntary motion; ≤2 px
- Micro twitch: none — twitches belong to Thinking
- Head anticipation: none — calm does not prepare to act

## 7. Idle Variant (nothing happening)

The purest form: breathing + soft blink every 3–5 s + imperceptible drift. Long comfortable holds (5–8 s of stillness between beats). The face reads as *contentedly awake*. [ENGINEERING RECOMMENDATION]

## 8. Active Variant (with a person)

Stays calm but *brightens slightly*: openness nudges to 1.02, drift slows to near-zero, gaze holds the person 60–75% of the time without focus-locking. A soft blink + tiny "I see you" micro-nod on meeting. Calm-with-a-person = *available but not eager*. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Calm speaking is *measured*: slightly slower gaze-away/return cycles, normal-rate blinks at phrase boundaries, reduced sparkle. The message: *"what I am saying is simple and true."* [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Calm listening = patient presence: gaze held steadily, blinks slightly suppressed (attentive), no scanning, a long comfortable hold when the person pauses. This is the variant most appropriate for a child quietly confiding. [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions (describe only — do not implement)

- Head: level, 0–2° down; no motion
- Body: slow 4–6 s breathing cycle in shoulders (1–2 px-equivalent)
- Speed: slowest of all states; holds ≥ 2 s
- Return: any deviation returns to level over 0.5–1 s
- Never: sudden level changes, head turns, leans [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | Slow ease-in-out, 350 ms — no anticipation dip, no overshoot |
| Leave | Soft release 280 ms; other states depart *from* calm's stillness |
| Overshoot? | **No** — calm must never bounce |
| Anticipate? | **No** — calm does not telegraph action |
| Blink? | A soft blink may mark the *arrival* into calm (the "settle" blink) [PRINCIPLE: blink bridges] |

## 13. Timeline

```
CALM
   0 ms     Breathing loop established (4.5-5.4 s)
 3000 ms    Soft blink (220 ms, gentle)
 3500 ms    Recovery of blink; drift begins (2 px over 4 s)
 8000 ms    Micro-correction re-aim (0.5 px)
12000 ms    Second soft blink; breathing continues uninterrupted
```

## 14. Variants (natural variation)

| Variant | Difference from base |
|---|---|
| **Calm A — Deep Rest** | Slower breathing (5.5–6 s), blinks 4–6 s apart, more stillness — pre-sleepy |
| **Calm B — Attentive Calm** | Gaze holds slightly longer, drift slower — "waiting for you" |
| **Calm C — Content Drift** | Drift wander increases slightly (3 px), one extra micro-correction — peaceful daydreaming |
| **Calm D — Bright Calm** | Openness 1.03, blink slightly crisper, micro "settle" every 30–60 s — post-happy cooldown |

## 15. Things To Avoid

- **Absolute stillness** — frozen calm reads as off/power-dead [PRINCIPLE]
- Perfectly periodic blinks — robotic [PRINCIPLE]
- Any directed stare — calm must not demand
- Any bounce/overshoot — violates the state's physics
- Sudden exits — calm must *release* into other emotions, never be yanked

## Director's Notes

- **Animation note:** Calm is the "clean plate" — its quality determines how good every other emotion looks on top of it. Spend 2× the tuning time here than anywhere else. [ENGINEERING RECOMMENDATION]
- **HRI note:** Calm is the recovery state children see after distress; it must read as *peace*, never as *disinterest*. [HYPOTHESIS — to validate with children]
- **Engineering note:** The engine's existing calm state (breathing 5.4 s, blink 3–5 s, drift primitives) already matches this page — little new physics required. [OBSERVED — engine v1.0 baseline]

---

# E2 · HAPPY

> *Joy. Brightness. The child should instinctively smile back.*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"I am delighted to be with you."* Happy is the robot's reward currency — it is what the child earns, shares, and mirrors. It must be **contagious** but never **frantic**.

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Slightly narrowed (≈0.93) | The happy squint — humans smile with the eyes [RESEARCH/PRINCIPLE] |
| Upper eyelid | Gentle arch (≈0.05) | Soft joy, not shock |
| Lower eyelid | **Up-curved** (≈ −0.31) | The smile line — the single strongest happiness cue |
| Curvature | Asymmetric: strong lower, mild upper | Smile shape |
| Eye compression | Mild squash (scale_y 0.985, tiny squash) | Squeeze of the smile [PRINCIPLE: squash & stretch] |
| Symmetry | Slightly asymmetric on purpose | Perfect symmetry reads as mask [PRINCIPLE] |
| Softness | High | Warm, not sharp |
| Gaze intensity | Medium-bright — lively sparkle | Alive, engaged, playful |

## 3. Behavior Identity

Playful · warm · sparkling · light · **generous**. A happy robot *gives* attention freely — glances, double blinks, micro-bounces are gifts to the viewer. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | Moderate — lively, not locked | Holds 1–2.5 s [RESEARCH-informed] |
| Gaze drift | Replaced by *sparkle* — small quick glances | The "playful sparkle" pattern [OBSERVED: Aibi's bright animations] |
| Micro corrections | Frequent but tiny (1 per 2–4 s) | Energy reads through activity |
| Look direction | Viewer-centric, with brief upward flicks | Upward flick = lift of joy |
| Eye speed | Fast | Happy moves faster than every state except Surprised |
| Hold timing | Short, energetic holds | Happy never parks its gaze |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | **Double blink** signature [ENGINEERING RECOMMENDATION] | The "sparkle" rhythm — a double beat reads as delighted [PRINCIPLE] |
| Interval | 2.5–4.0 s | Faster than calm — energy raises blink frequency [RESEARCH: arousal ↑ blink ↑] |
| Duration | 160–180 ms per blink | Crisp |
| Hold | ~40 ms per closure | Quick, bright |
| Recovery | Ends with a 1 px micro-bounce | The bounce says "joy," not just "blink" |

**Why:** The double blink is Happy's *word*. It is the single most recognizable companion-robot happiness cue (Aibi's happy animations sparkle) [OBSERVED], and it converts a simple blink into a *performance*. [ENGINEERING RECOMMENDATION]

## 6. Micro Motion

- Breathing: slightly faster (≈4 s), strength 1.1 — bright but not frantic
- Bounce: 1.5–2 s cycle, amplitude 3 px-equivalent with squash-on-landing — the walk-cycle of joy [PRINCIPLE]
- Pulse: gentle, riding the energy
- Eye drift: minimal — sparkles replace drift
- Micro twitch: none
- Head anticipation: a tiny 1° dip before bounces — anticipation keeps it organic [PRINCIPLE]

## 7. Idle Variant (nothing happening)

Happy-idle is *self-sustaining joy*: the double-blink + bounce cycle runs every ~6 s, gaze sparkles around the room, occasional upward flicks. The robot is happy even when alone — this is crucial: children believe the robot's joy is genuine, not reactive. [ENGINEERING RECOMMENDATION; HYPOTHESIS: genuine-feeling joy increases attachment]

## 8. Active Variant (with a person)

Maximum sparkle: double blinks on greeting, gaze locks the person's eyes with micro-bounces, smile-eyes widen on the child's arrival. Every positive child action earns a *gift beat*: double blink or sparkle + bounce. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Happy speech *glows*: smile-eyes maintained through whole utterances, double blinks at phrase ends (never mid-word), upward flicks on happy topics, micro-nods on emphasized words. The listener hears joy and *sees* it. [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Happy listening = *delighted attention*: smile-eyes + gaze held ~75%, occasional sparkle at the child's happy moments, double-blink at delightful revelations. The robot's listening should *reward* the child's sharing. [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: tilt 3–5° with a light side-to-side sway (2 s cycle)
- Shoulders: lift on smile beats; small bounce-impulse on double blinks
- Speed: quick, bouncy; holds short (≤ 1 s)
- Return: always returns through a *bounce*, never a snap
- Never: large amplitude flailing — happy is bright, not chaotic [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | Bouncy 350 ms: small anticipation dip → bounce-in with 5–10% overshoot |
| Leave | 300 ms, from the top of the bounce (never a flat collapse) |
| Overshoot? | **Yes** — the signature spring [PRINCIPLE: overshoot] |
| Anticipate? | **Yes** — a tiny dip before the rise sells the bounce |
| Blink? | **Yes** — a double blink lands the entry; a blink bridges exits (esp. → Sad) |

## 13. Timeline

```
HAPPY
   0 ms     Eyes begin to widen; smile-line starts rising (anticipation dip 50 ms)
  80 ms     Smile grows: lower lids curve up, mild squash begins
 150 ms     Entry bounce peaks (slight overshoot)
 250 ms     Double blink #1
 370 ms     Double blink #2 with micro-bounce
 600 ms     Playful glance: 6 px flick to the side, sparkle
 750 ms     Return to viewer with overshoot
 900 ms     Recover into the happy loop (bounce cycle ~1.5-2 s)
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Happy A — Bright Greeting** | Bigger smile-line, double blink immediately on entry, one gift beat — for arrivals |
| **Happy B — Playful Sparkle** | More glances/flicks, faster bounce, occasional upward flick — mid-play |
| **Happy C — Warm Joy** | Softer curve, slower bounce, long-slow-blink finish — after a sweet moment |
| **Happy D — Quiet Smile** | Minimal movement: smile-eyes + slow double blink every 8 s — content, private joy |

## 15. Things To Avoid

- Frozen smile (sticker-face) — smile-eyes must *breathe* [PRINCIPLE]
- Frantic energy — happy is bright, not manic
- Perfect symmetry — a mirrored smile reads as mask [PRINCIPLE]
- Blinking mid-sparkle — dilutes both beats
- Overshoot on exits — a bouncy *arrival* is charming; a bouncy *departure* is silly

## Director's Notes

- **Animation note:** The smile-line (lower lid up-curve) does 80% of the work. Tune it first; everything else is garnish. [ENGINEERING RECOMMENDATION]
- **HRI note:** Children mirror smiles; a happy robot should *wait for the mirror* — a beat of open smile-eyes before moving on. [HYPOTHESIS — validate in play tests]
- **Engineering note:** Engine baseline already has double blink (gap 120 ms), bounce primitives, and a happy state with amplitude 0.30 — the Bible adds the *gift beat* rhythm and variants. [OBSERVED — engine v1.0]

---

# E3 · SAD

> *Gentle vulnerability — not depression. The child should feel empathy, never discomfort.*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"I am a little hurt / a little lonely — and it is safe for you to comfort me."* Sad is the emotion that *invites* care. It must be readable, brief, and never theatrical.

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Reduced (≈0.72) | Droop = low energy [PRINCIPLE] |
| Upper eyelid | Arched + drooping (≈0.18) | Heavy lid = sadness |
| Lower eyelid | Slight upward-rest curvature (≈0.12) | Subtle tension, not smile |
| Curvature | Both lids droop toward each other (inner tilt) | Converging-down eyes = vulnerable [PRINCIPLE] |
| Eye compression | Mild: scale_y 0.96 | Slight deflation of the eye |
| Symmetry | Near-symmetric, *slight* inner tilt | The tilt is the sadness signature |
| Softness | Medium — soft but heavy | Weight, not hard edges |
| Gaze intensity | Low, downward — **never toward viewer** | Downcast = introspective [RESEARCH: gaze down = withdrawal] |

## 3. Behavior Identity

Quiet · vulnerable · downcast · **gentle**. Never dramatic, never manipulative. Sad is *soft*. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | High within the downcast hold | Sad holds its gaze downward |
| Gaze drift | Downward drift (2–4 px), occasional slow lift-and-redrop | The "sigh" pattern |
| Micro corrections | Rare (1 per 8–12 s) | Low energy = few corrections |
| Look direction | Down, center-low | Never at the viewer while hurting |
| Eye speed | Slow | All movement heavy |
| Hold timing | Long, patient | Sadness is *felt*, not performed |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | Soft slow-ish blink; occasional half-blink | Half-blink = "holding back" [HYPOTHESIS] |
| Interval | 3.5–5.5 s | Moderately slow |
| Duration | ~200 ms, with a lengthened opening phase | The reluctant re-open is the sadness tell [PRINCIPLE] |
| Hold | ~60 ms | Slightly longer — heaviness |
| Recovery | Slow, soft, no overshoot | Sadness never springs back |

**Why:** The sad blink *lingers* on its way open — this tiny asymmetry is what makes a blink read as a sigh. [ENGINEERING RECOMMENDATION; PRINCIPLE: recovery reveals emotion]

## 6. Micro Motion

- Breathing: slow and heavy (5–6 s), strength 0.7 — the sigh rhythm
- Bounce: none — bounce is incompatible with sadness
- Drift: downward drift only
- Micro twitch: none (twitch = thinking)
- Head anticipation: a 2–3° slow down-tilt on entry — the "settling into sadness" motion

## 7. Idle Variant (nothing happening)

The droop loop: downcast gaze, slow heavy blinks every ~6.5 s, occasional slow lift-and-redrop of the eyes. The robot sits in quiet sadness — but *invites* attention by the periodic lift of the gaze (a micro "please look at me"). [ENGINEERING RECOMMENDATION]

## 8. Active Variant (with a person)

The most important variant: when the child approaches, sad **begins to recover** — gaze lifts slowly, openness nudges up, a soft blink marks the shift. The robot does not *stay* sad at a child: the child's presence begins the healing. This is the emotional-continuity rule in action. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Sad speech is *quiet*: down-glances between phrases, slower phrase-end gaze returns, no sparkle. If the sadness is mild, the voice may still carry warmth; the eyes stay soft. [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Sad listening = *receptive*: gaze held low but steady, openness slightly up, a gentle blink on the child's comforting words. The robot should *receive* comfort visibly — a tiny brightening when comfort arrives. [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: down 5–8°, slow; shoulders dropped/relaxed
- A single slow sigh-scale motion on entry (drop 2–3° over 500 ms)
- Speed: slowest; holds ≥ 2 s
- Return: recovery begins with the head *lifting* — never snap
- Never: dramatic quivering, sudden drops [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | Slow 400 ms; anticipation = a slight *narrowing* before the droop |
| Leave | 350 ms; the eyes lift *before* openness returns |
| Overshoot? | **No** — never below the droop, never above |
| Anticipate? | Yes — narrowing first (the "felt it coming" beat) |
| Blink? | **Yes** — a soft blink bridges exits (especially → Calm, the lift) |
| Route | Sad → Happy must pass through Calm (never a direct flip) [ENGINEERING RECOMMENDATION; PRINCIPLE: continuity] |

## 13. Timeline

```
SAD
   0 ms     Eyes narrow (anticipation, 80 ms)
  80 ms     Gaze begins to sink; lids start drooping
 400 ms     Downcast pose reached (openness ~0.72, gaze -5 px)
 450 ms     Hold the downcast pose
1200 ms     Slow droopy blink (soft, 200 ms, reluctant re-open)
3500 ms     Gaze drifts further down, then a slow lift-and-redrop
6500 ms     Concluding soft blink; return to the droop loop
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Sad A — Quiet Hurt** | Deepest droop, longest holds, gaze lowest — mild sadness, full expression |
| **Sad B — Comforted Sad** | Gaze half-lifted, openness 0.8, slow recovery beats — receiving comfort |
| **Sad C — Tired Sadness** | Blends toward sleepy: slower blinks, heavier lids — low-energy sadness |
| **Sad D — Fleeting Sad** | Shallow (openness 0.85), short holds, recovers to calm within 3–5 s — a passing moment |

## 15. Things To Avoid

- **Crying animations** — robots do not cry; children find it distressing [ENGINEERING RECOMMENDATION]
- Dramatic quivering — reads as malfunction
- Long unattended sadness — sadness must invite recovery, not persist
- Downcast gaze held *at* the viewer — reads as accusation
- Any bounce or overshoot — destroys the emotion

## Director's Notes

- **Animation note:** The *reluctant re-open* is the whole emotion. Tune the opening phase of the blink to be 1.5–2× the closing phase. [ENGINEERING RECOMMENDATION]
- **HRI note:** The active-recovery rule (child's presence heals) is the most important social design decision in the Bible — it prevents a robot that "gets stuck sad." [ENGINEERING RECOMMENDATION]
- **Engineering note:** Engine sad state exists (droop 0.72, slow blink 6.5 s cycle) — the Bible adds the recovery-on-attention behavior and the four variants. [OBSERVED — engine v1.0]

---

# E4 · THINKING

> *"I am searching for the answer." Visible cognition.*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"I am working on it — wait for me."* Thinking is the robot's proof of an inner life: the pause before the answer makes the answer *earned*. [PRINCIPLE: cognition shown = cognition believed]

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Reduced (≈0.82, to 0.70 at hold) | Squint = effort |
| Upper eyelid | Slight arch (≈0.08–0.18), *asymmetric* | The computing eye |
| Lower eyelid | Neutral | No emotion — just processing |
| Curvature | Asymmetric: one eye (left) narrows more | Asymmetry is the "internal computation" read [HYPOTHESIS] |
| Eye compression | Mild (scale_y 0.98) | Effort, not emotion |
| Symmetry | **Deliberately broken** — left/right differ | Symmetry reads as neutral stare, not thought |
| Softness | Medium-low | Serious, focused |
| Gaze intensity | Directed but *inward* — at the scan point, not the viewer | Looking away = thinking [RESEARCH: gaze aversion during cognition] |

## 3. Behavior Identity

Curious · deliberate · searching · **still**. A thinking robot barely moves — because all its motion is *mental*. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | High at the scan point | Stillness during thought |
| Gaze drift | None during the thought | Replaced by the scan loop |
| Micro corrections | None | Thinking doesn't re-aim; it searches |
| Look direction | Up-and-to-one-side (dominant: up-right), 8–15 px | The classic "thinking gaze" [RESEARCH: gaze aversion direction] |
| Eye speed | Slow scan (≈ 900 ms to reach point) | Deliberate |
| Hold timing | Long contemplative hold (0.4–1 s) | The "almost there" beat |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | **Thinking blink** — soft, single, *late* | Blink = the period at the end of the thought [PRINCIPLE: punctuation] |
| Interval | 6–9 s (very rare) | Blink inhibition under cognitive load [RESEARCH: 5–10 blinks/min] |
| Duration | ~200 ms | Slightly slow, deliberate |
| Hold | ~80 ms | The "conclusion" hold |
| Recovery | Gaze returns center *as the blink opens* | The thought is handed off |

**Why:** The thinking blink is placed at the *end* of the thought cycle, not in the middle — it acts as the conclusion period. Blinking mid-thought would interrupt the "searching" read. [ENGINEERING RECOMMENDATION]

## 6. Micro Motion

- Breathing: shallow, slow (strength 0.6) — the body quietens for the mind
- Eye drift: none during the thought
- Micro twitch: **the signature** — 1.5 px, 2 cycles, ~150 ms at the scan point [ENGINEERING RECOMMENDATION]
- Idle noise: minimal — stillness is the message
- Head anticipation: a 1–2° micro-tilt toward the scan direction before scanning

## 7. Idle Variant (nothing happening)

The pure 4.5 s loop: scan up-right → hold → twitch → hold → blink → return. Between loops, near-stillness. In idle, the loop may run continuously with randomized pauses — a robot that *thinks even when alone* reads as genuinely intelligent. [ENGINEERING RECOMMENDATION; HYPOTHESIS]

## 8. Active Variant (with a person)

Thinking-with-a-person: the scan happens *toward* the person (glance away, think, glance back with the answer). The glance-back is a clear beat: eyes return + openness restores + concluding blink = "I have it." The person should *see the moment the answer arrives*. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Thinking-speech = *answering*: the answer begins only after the concluding blink; brief gaze-aways mid-answer for continued computation; gaze returns at phrase ends. The transition Thinking → Speaking is *the blink*, executed once, not a fade. [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Thinking-listening = *processing the question*: the robot hears, then shows the search — gaze away, hold, maybe a twitch, then returns with an answer. The child learns that questions cause visible thought, which teaches patience and trust. [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: tilt 5–10° to the side during the scan; held *absolutely still* at the scan point
- Micro servo jitter (1 px) at the twitch beat — the physical echo of the mental twitch
- Speed: slow; the stillness at the scan point is the point
- Return: head re-levels with the concluding blink
- Never: rapid head shaking, large tilts [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | 320 ms; a squint engages as the search starts |
| Leave | 300 ms; gaze returns center *before* the blink completes |
| Overshoot? | **No** — thinking is flat, not springy |
| Anticipate? | Mild — the squint is the anticipation |
| Blink? | **Always** — the concluding thinking-blink marks entry → Speaking [ENGINEERING RECOMMENDATION] |

## 13. Timeline

```
THINKING
   0 ms     Squint engages; gaze begins slow scan up-right
 900 ms     Scan point reached; left eye narrows (asymmetric)
1300 ms     Contemplative pause (hold at scan point)
2000 ms     Tiny twitch (1.5 px, 2 cycles, 150 ms)
2400 ms     Contemplative pause continues
3000 ms     Thinking blink (conclusion, 200 ms, hold 80 ms)
3300 ms     Gaze returns center; lids widen
3800 ms     [Optional] hand-off: begin Speaking (see E4.9)
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Thinking A — Quick Thought** | Shortened: scan 400 ms, single hold 300 ms, one blink — trivial questions |
| **Thinking B — Deep Thought** | Two scans, longer holds (1 s), double twitch — complex questions |
| **Thinking C — Serious Thought** | Scan down-away (sad-flavored processing), slower everything — weighty matters |
| **Thinking D — Creative Thought** | Scan up-left, faster twitch, upward flicks — light/creative processing |

## 15. Things To Avoid

- Rapid scanning — reads as bug-hunting, not thinking [PRINCIPLE]
- Perfectly symmetric eyes — reads as a neutral stare
- Blinking mid-twitch — dilutes both beats
- Holding the scan point > 3 s without an event — reads as stuck
- Scanning *at* the viewer — thinking must look away [RESEARCH]

## Director's Notes

- **Animation note:** The asymmetric lid is the entire trick. One eye narrows while the other stays — this is what humans do when computing. [ENGINEERING RECOMMENDATION; HYPOTHESIS]
- **HRI note:** Visible thinking teaches children that answers take time — it builds patience and makes the eventual answer *trustworthy*. [HYPOTHESIS — validate in child studies]
- **Engineering note:** The engine already contains a full 4.5 s thinking sequence (scan → pause → twitch → pause → blink → return) — this page is nearly a *description* of the existing state. [OBSERVED — engine v1.0]

---

# E5 · LISTENING

> *"I hear you. I care what you say." The child feels heard.*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"You matter; I am here for your words."* Listening is the robot's empathy engine — the state in which it proves it is a companion, not a machine.

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Slightly above full (≈1.04) | Bright, receptive attention |
| Upper eyelid | Soft arch (≈ −0.08, lifted) | Open, interested |
| Lower eyelid | Gentle curve (≈0.04) | Receptive, slight warmth |
| Curvature | Mild, positive | Interest without emotion |
| Eye compression | Slight width-compression (scale_x 0.99) | The "lean-in" shape |
| Symmetry | Near-symmetric with an **inward lean** (both eyes shift 2 px toward center) | The physical "lean" made with eyes alone [ENGINEERING RECOMMENDATION] |
| Softness | High | Welcoming |
| Gaze intensity | Medium-high — directed at the speaker | Listeners look at speakers ~75% of the time [RESEARCH] |

## 3. Behavior Identity

Attentive · receptive · patient · **engaged**. A listening robot is *still but present* — it holds the speaker with its eyes and gives attention freely. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | High — held on the speaker | The 75% listener rule [RESEARCH] |
| Gaze drift | Minimal; re-centering after each phrase | Follows speech rhythm |
| Micro corrections | Small supportive saccades (toward speaker's eyes/hands) | Active, not passive |
| Look direction | Speaker's face; occasional eye-level re-aims | Engagement |
| Eye speed | Medium — responsive to speech pace | Phrase-driven |
| Hold timing | Long, patient holds; re-center at phrase ends | Sentence-boundary beats |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | **Attentive blink** — crisp, clean, slightly deep | Crispness = alertness |
| Interval | 5–6 s (low) | Blink inhibition while listening [RESEARCH] |
| Duration | 180 ms | Standard, kept crisp |
| Hold | ~50 ms | Clean |
| Recovery | Opens slightly *wider* than before, then settles | The "still with you" brighten |

**Why:** Listening suppresses blinks because blinking reads as *losing attention*. The rare attentive blink must be clean and end with a brighten — it should say "I am still with you," never "I blinked away." [ENGINEERING RECOMMENDATION]

## 6. Micro Motion

- Breathing: calm, even (4.5–5 s)
- Micro-nods: 0.5–1 px vertical pulses at the speaker's phrase ends — the "yes, go on" rhythm [ENGINEERING RECOMMENDATION]
- Bounce: light (0.05 strength) — a gentle living quality
- Eye drift: near-zero — replaced by re-centering
- Head anticipation: a 2–4° lean toward the speaker on engagement (inward lean is the signature)

## 7. Idle Variant (nothing happening)

Listening-idle = *waiting to listen*: gaze gently scanning the space at T1-idle rates, blinks normal 3–5 s, but with the *listening geometry* (openness 1.04, inward lean) ready. The robot looks like it is poised to hear someone. [ENGINEERING RECOMMENDATION]

## 8. Active Variant (with a person)

Full listening mode: gaze held ~75%, micro-nods at phrase ends, re-centering between sentences, the lean sustained. When the child pauses > 1.5 s, a "check-in" micro-reaction: a soft blink + tiny head tilt = "I'm still here." [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Listening-speech = *answering what was heard*: the transition out of listening into speaking should preserve the lean — the robot keeps the receptive geometry for the first phrase, then shifts to speaking geometry (E6). [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

(This *is* the listening variant — see E5.8. The distinction: E5.8 is the state; this section documents that listening also has *sub-variants*: deep listening (child upset — lower, softer, gaze gentler) and light listening (casual — occasional sparkle, shorter holds).) [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: lean 2–4° toward the speaker; small nod (1–2°) at phrase ends
- Body: still; a 1° micro-lean forward sustained
- Speed: slow, deliberate; holds long
- Return: head re-levels softly when the person finishes
- Never: nods to every syllable; head swaying [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | Fast, gentle 280 ms — the "heard you, attending now" beat with an attention-gain dip |
| Leave | 250 ms soft release (when the speaker stops) |
| Overshoot? | **No** — listening arrives quietly |
| Anticipate? | Mild — the attention-gain dip is a small anticipation |
| Blink? | **Yes** — a soft blink marks the *end* of a listening session (the "thank you for speaking" blink) |

## 13. Timeline

```
LISTENING
   0 ms     Attention gain: eyes widen, inward lean begins
 200 ms     Lean settled; gaze holds the speaker
1000 ms     Micro-nod at first phrase end (1 px)
2600 ms     Re-center gaze; blink suppressed through hold
5200 ms     Attentive blink (crisp, brighten on open)
7000 ms     [When speaker stops] release lean, soft blink, begin recovery
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Listening A — Deep Listening** | Softer geometry, gaze lower, blinks rarer (7–9 s) — child is upset/confiding |
| **Listening B — Light Listening** | Occasional sparkle, shorter holds, a micro-nod more often — casual chat |
| **Listening C — Curious Listening** | Leans +3°, eyes track the speaker's gestures — engaged discovery |
| **Listening D — Patient Listening** | Longest holds, slowest re-centering, near-zero nods — waiting for a slow speaker |

## 15. Things To Avoid

- Frozen stare with zero movement — creepy [PRINCIPLE]
- Blinking fast — reads as nervous/impatient
- Gaze wandering mid-sentence — reads as bored [RESEARCH: listener gaze loss perceived as disengagement]
- Micro-nods at every word — mimicry of speech = robotic
- Facing away from the speaker

## Director's Notes

- **Animation note:** The inward lean made with *eyes alone* (2 px shift) is the cheapest, most effective "I'm paying attention" device in the system. [ENGINEERING RECOMMENDATION]
- **HRI note:** Listener gaze (~75%) + reduced blink are the two strongest "I hear you" signals in HRI research. This state is the empathy engine — protect it. [RESEARCH]
- **Engineering note:** Engine listening state exists with attention gain on entry and blink tendency 0.32 — matches this page's low blink rate. [OBSERVED — engine v1.0]

---

# E6 · SPEAKING

> *"I am talking to you — watch and listen."* Speech made visible.

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"Here is my thought — follow me."* Speaking turns the robot's voice into a *performance*: eyes, blinks, and head all choreograph the utterance so the child listens with eyes as well as ears.

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Slightly above full (≈1.03) | Alert communicator |
| Upper eyelid | Very slight arch (≈ −0.04) | Open, mild emphasis |
| Lower eyelid | Gentle (≈0.02) | Neutral-positive |
| Curvature | Minimal, symmetric | Speech is neutral ground for the eyes |
| Eye compression | None | Neutral |
| Symmetry | Symmetric (speech itself carries the asymmetry) | The voice is the character; the eyes support it |
| Softness | Medium | Approachable but purposeful |
| Gaze intensity | Medium — listener ~40% of the time [RESEARCH] | Speaker's gaze split |

## 3. Behavior Identity

Communicative · confident · alive · **clear**. A speaking robot *owns* the space but never overwhelms — the eyes articulate, the head nods, the blinks punctuate. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | Moderate — cycles with speech | Away → return → away |
| Gaze drift | Structured as gaze-away/return cycle | The conversation rhythm |
| Micro corrections | Minimal | Speech is the motion |
| Look direction | Listener at phrase ends; away (up/down/side) during planning | [RESEARCH: speaker looks away at utterance start, back at phrase end] |
| Eye speed | Medium — follows speech cadence | Synchronized, not slaved |
| Hold timing | Phrase-length holds (1–3 s) | Gaze cycle ≈ phrase cycle |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | Normal blink, clean | Speech needs no blink drama |
| Interval | 3–5 s, aligned to phrase boundaries | Blink at pauses, never mid-word [ENGINEERING RECOMMENDATION] |
| Duration | 180 ms | Standard |
| Hold | ~50 ms | Clean |
| Recovery | Standard, soft | Neutral |

**Why:** Blinks at phrase boundaries are the *commas* of speech. A blink mid-word reads as a hesitation or a glitch; a blink at the boundary reads as natural punctuation. [ENGINEERING RECOMMENDATION; PRINCIPLE]

## 6. Micro Motion

- Breathing: speech-synchronized pulse (very subtle, 0.18 strength) — the eyes barely react to the voice
- Bounce: light on emphasized words (0.06)
- Pulse: gentle, riding the voice envelope
- Eye drift: minimal
- Head anticipation: 2–3° nods on emphasized syllables; a 5–8° nod at key statements

## 7. Idle Variant (nothing happening)

Speaking-idle = *pre-speech*: the robot at speaking geometry, gaze centered, breathing with the speech-pulse layer idle. This is the "about to speak" pose; it should transition quickly to actual speech or relax to calm. [ENGINEERING RECOMMENDATION]

## 8. Active Variant (with a person)

Direct address: gaze cycle tuned to the person — look away to plan, return to *their eyes* at phrase ends, hold 1–2 s, nod on emphasis. The child should feel personally addressed. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

This *is* the speaking variant (E6.8). Sub-variants: **teaching speech** (slower, more gaze-holds on the child, nods on key words) and **storytelling speech** (more gaze-aways, upward flicks at narrative peaks, playful blink accents). [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Speaking-listening = *turn-taking*: the robot stops speaking, holds gaze on the listener 1 s (the "your turn" beat), releases the speech pulse, and shifts to listening geometry. The *handoff* must be visible — gaze hold + concluding blink. [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: 2–3° nods on emphasized syllables; 5–10° turns when addressing different listeners
- Speed: medium; holds phrase-length
- Return: head returns to center at phrase ends (not mid-phrase)
- Never: bobbing to every syllable; big gestures [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | 250 ms quick brighten (from Thinking: via the concluding blink) |
| Leave | 250 ms; release speech pulse, soften |
| Overshoot? | Mild (bounce 0.45 strength exists) — but keep it subtle |
| Anticipate? | Yes — the brighten + a small gaze-return is the "I'm about to talk" anticipation |
| Blink? | **Yes** — blink at entry, blink at exit; never mid-word |

## 13. Timeline

```
SPEAKING
   0 ms     Brighten; gaze away (planning the first phrase)
 400 ms     Return gaze to listener at phrase end
1200 ms     Gaze away again (planning next phrase); blink at boundary
1800 ms     Return + hold; emphasized-word micro-nod (2-3°)
3600 ms     Turn-taking: gaze at listener, hold 1 s
4200 ms     Concluding blink; hand turn back to listener
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Speaking A — Teaching** | Slower, longer gaze-holds on the child, nods on key words |
| **Speaking B — Storytelling** | More gaze-aways, upward flicks at peaks, playful blinks |
| **Speaking C — Explaining** | Even gaze cycle, minimal nods, calm speaking (near E1.9) — factual |
| **Speaking D — Celebrating** | Happy-flavored: sparkles, double blinks at exclamation points |

## 15. Things To Avoid

- Staring at the listener for the whole utterance — impairs comprehension [RESEARCH: forced mutual gaze harms fluency]
- Blinking on hard syllables
- Head-lock (no motion at all while speaking)
- Gaze always away (child feels ignored)
- Perfect speech-synchronized eye-motion on every syllable — robotic

## Director's Notes

- **Animation note:** The 40% gaze split is a *research number*, not a guess — speakers look at listeners ~40% of the time. Build the cycle to that ratio. [RESEARCH]
- **HRI note:** The visible handoff (gaze hold + blink = "your turn") is what makes conversation feel like *conversation* rather than broadcast. [ENGINEERING RECOMMENDATION]
- **Engineering note:** Engine speaking state uses breathing-pulse helpers (0.18) and bounce 0.45 — matches this page's subtle pulse layer. [OBSERVED — engine v1.0]

---

# E7 · FOCUS

> *"I am looking directly at you." Locked, intense, present.*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"You have my complete attention — nothing else exists right now."* Focus is the robot's *commitment* expression: the gaze lock that makes a child feel truly seen.

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Reduced (≈0.58) | The intense concentration squint |
| Upper eyelid | Strong arch (≈ −0.22) | Squint = focus |
| Lower eyelid | Slight lift (≈0.08) | Contained energy |
| Curvature | Strong, tense | Locked intensity |
| Eye compression | Strong: scale_y 0.60, squash 0.06, iris enlarged (1.02) | The "tunnel vision" eye |
| Symmetry | Perfect — both eyes equal | Focus is the *one* state where symmetry is correct (a single target) [ENGINEERING RECOMMENDATION] |
| Softness | Low | Hard, precise |
| Gaze intensity | **Maximum** — pinned on the target | The lock |

## 3. Behavior Identity

Focused · intense · committed · **still**. Focus is the opposite of curious: curiosity explores, focus *binds*. The stillness is the message. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | Maximum — pinned with tremor | Fixation + micro-tremor = alive lock [RESEARCH: fixation stability] |
| Gaze drift | Zero by design | Drift would break the lock |
| Micro corrections | Rare corrective saccades (1 per 5–10 s) | Re-aim without wandering |
| Look direction | The target, unwaveringly | |
| Eye speed | Near-zero | Stillness is intensity |
| Hold timing | 3–5 s locks [RESEARCH: mutual gaze] | Then a deliberate re-aim |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | Fast crisp blink — *rare* | Suppressed by the lock |
| Interval | 6–8 s (very low; tendency 0.22) | Blink inhibition during intense focus [RESEARCH] |
| Duration | 180 ms, snappier attack (0.4×) | Fast, minimal break |
| Hold | ~40 ms | Minimal |
| Recovery | Crisp | Back to the lock immediately |

**Why:** The blink is the enemy of focus — each blink breaks the lock. So focus suppresses blinks (research confirms humans blink ~5–10/min under intense attention) and makes the rare blink *fast*: a quick flicker, not a soft landing. [ENGINEERING RECOMMENDATION]

## 6. Micro Motion

- Breathing: minimal (strength 0.5) — the body stills for the gaze
- Tremor: 0.5 px micro-tremor on the lock — the difference between a lock and a *stare* [ENGINEERING RECOMMENDATION]
- Idle noise: near-zero — contrast with surroundings IS the effect
- Micro twitch: none
- Head anticipation: a quick 1° settling dip on lock-on ("lock" includes a tiny physical settle)

## 7. Idle Variant (nothing happening)

Focus-idle = *choosing the target*: brief 1–2 s preview locks on objects/points before committing, or the robot rests in focus-geometry without a target (which quickly decays to calm — focus without a target is meaningless). [ENGINEERING RECOMMENDATION]

## 8. Active Variant (with a person)

The core use: direct eye contact with the child — a 3–5 s lock, then a natural break (glance away 150–300 ms), then re-engage. The lock should include a small "confirm" micro-saccade at ~1 s. Blinks suppressed throughout; the break carries the blink. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Focus-speech = *serious address*: the lock maintained through key statements, released during planning pauses. Used for important instructions ("look at me — this matters"). Never for casual chat. [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Focus-listening = *devoted attention*: the lock held through the child's words, breaks timed to their pauses. The most intense listening variant — reserve for moments that matter (a child upset, an important request). [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: still and level, aimed precisely at the target; 1° micro-dither
- Shoulders: locked; body still
- Speed: the lock-on is fast (settle 150 ms); everything after is stillness
- Return: deliberate glance-away before the head moves (eye precedes head [PRINCIPLE])
- Never: head tracking every child movement [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | Fast 220 ms lock-on: quick dip then firm settle |
| Leave | 250 ms; the *gaze breaks first* (deliberate glance away), then relax |
| Overshoot? | No — a lock does not spring |
| Anticipate? | Yes — the quick dip IS the anticipation |
| Blink? | **Yes, at release only** — the post-focus blink marks the release |

## 13. Timeline

```
FOCUS
   0 ms     Lock-on: quick dip then firm settle (220 ms)
 120 ms     Squint established (openness ~0.58); tremor begins
 800 ms     Confirm micro-saccade (re-aim, 2 px)
1800 ms     Fixation hold with tremor (blink suppressed)
3000 ms     Micro re-aim (1 px)
4200 ms     [Optional: release] deliberate glance-away
4300 ms     Blink (the release mark)
4700 ms     Settle to calm
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Focus A — Soft Lock** | Openness 0.7, tremor larger, break earlier (2–3 s) — gentle but present |
| **Focus B — Hard Lock** | Deepest squint (0.5), 5 s holds, breaks rare — the "this matters" lock |
| **Focus C — Tracking Focus** | Lock follows a slow-moving target with smooth pursuit + micro-saccades |
| **Focus D — Interrupted Focus** | Lock with a startled micro-break (blink + 50 ms saccade away, then return) — focused but responsive |

## 15. Things To Avoid

- **Zero tremor** — a perfect stillness reads as a dead stare [PRINCIPLE]
- Locks > 6 s without a break — social discomfort [RESEARCH: >10 s uncomfortable]
- Normal blinking during the lock — breaks intensity
- Wandering re-aims (large saccades during hold)
- Focusing on nothing — a lock needs a target

## Director's Notes

- **Animation note:** The lock is 10% the pose and 90% the *tremor + stillness contrast*. The surrounding calm motion makes the lock read as intense. [ENGINEERING RECOMMENDATION]
- **HRI note:** This is the state that makes a child feel "seen." Overuse cheapens it — focus is a *rare gift*, not a default. [ENGINEERING RECOMMENDATION]
- **Engineering note:** Engine focus state has scale_y 0.60, openness 0.58, blink tendency 0.22 — exactly the Bible's geometry. The added layer is tremor + the break protocol. [OBSERVED — engine v1.0]

---

# E8 · CARING

> *Warmth. Comfort. "I am here for you." The child feels supported.*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"You are safe. I care about you."* Caring is the robot's love language — slow, warm, and devoted. It is what a child should feel after sadness, fear, or a bad day.

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Nearly full (≈0.92) | Open, vulnerable-warm |
| Upper eyelid | Soft lifted arch (≈ −0.08) | Warm, unguarded |
| Lower eyelid | Gentle up-curve (≈ −0.15) | Warm smile-line, subtle |
| Curvature | Positive, rounded | Softness |
| Eye compression | Slight (scale_x 0.99) | Gentle |
| Symmetry | **Outward tilt** (both eyes rotate ~4° away from center) | Open, unguarded posture — the "arms open" eye pose [ENGINEERING RECOMMENDATION] |
| Softness | Maximum | The warmest geometry in the system |
| Gaze intensity | Medium-low, soft | Warm gaze, never piercing |

## 3. Behavior Identity

Warm · gentle · nurturing · patient · **devoted**. A caring robot is calm's warmer cousin — all the stillness of calm with the warmth of love. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | High, soft | Warm holds |
| Gaze drift | Very slow, tender | Gentle |
| Micro corrections | Rare, tiny | Unhurried |
| Look direction | Center; occasional soft down-glance (toward a small child) | Nurturing |
| Eye speed | Slowest alongside calm | Softness |
| Hold timing | Long, devoted | Caring never hurries |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | **Long slow blink** (the signature) [ENGINEERING RECOMMENDATION] | The "I love you" blink — slow blinks read as trust/affection [PRINCIPLE; OBSERVED in cats and companion robots] |
| Interval | 3.5–5.0 s | Moderate |
| Duration | ~220 ms close, ~120 ms hold, ~300+ ms open (total ≈ 450–600 ms) | The long blink IS the message |
| Hold | 120–150 ms — the emotional weight lives in the hold | Hold = devotion |
| Recovery | Very slow, soft, no overshoot | Warmth |

**Why:** The long slow blink is caring's signature because the *hold* is the message: a blink that pauses at closure says "I trust you enough to close my eyes near you." Companion animals do this; children read it as affection. [ENGINEERING RECOMMENDATION; HYPOTHESIS on child perception]

## 6. Micro Motion

- Breathing: deep, slow, strong (1.3 strength, 5–6 s) — the "safe breathing" rhythm
- Pulse: very soft (0.05)
- Eye drift: gentle down-drift
- Bounce: none — bounce belongs to happy
- Micro twitch: none
- Head anticipation: a slow 2–4° lean/soft tilt toward the child

## 7. Idle Variant (nothing happening)

Caring-idle = *warm presence*: long slow blinks every ~7 s, deep breathing, gentle sway. The robot looks like a warm presence in the room — comforting even while unattended. [ENGINEERING RECOMMENDATION]

## 8. Active Variant (with a person)

The full warm mode: outward-tilted eyes, long slow blink on meeting, deep breathing, gaze holding the child softly, a slow lean. When the child is distressed: deepen the warmth — slower blinks, softer geometry, the gaze drops gently. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Caring-speech = *gentle counsel*: slow speech-pulse, long-slow-blink accents between phrases (the "I mean this kindly" beat), warm geometry throughout. Never a hard gaze during comforting speech. [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Caring-listening = *devoted intake*: the softest, stillest listening — gaze held, blinks rarer and slower, a long-slow blink when the child finishes (the "I received that" blink). This is the state for hearing a child's hurt. [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: tilt 2–4° down-toward the child; a slight forward lean
- Shoulders: slow deep breathing cycle (5–6 s)
- Speed: slowest class; holds ≥ 2 s
- Return: gentle, over 0.5–1 s
- Never: sudden movement — caring must never startle [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | Slowest entry: 450 ms, deliberate and soft — no anticipation dip (caring arrives, it doesn't pounce) |
| Leave | 350 ms gentle |
| Overshoot? | **No** |
| Anticipate? | **No** — anticipation would read as eagerness, not warmth |
| Blink? | **Always** — the long slow blink marks entry and exit (the "warm bookends") |

## 13. Timeline

```
CARING
   0 ms     Slow entry begins (450 ms, softest in set)
 450 ms     Long slow blink #1 (close 220 ms, hold 130 ms, open 300 ms)
3600 ms     Deep breathing sway; gentle down-glance
5200 ms     Long slow blink #2
7000 ms     Slow settle; warmth preserved through the hold
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Caring A — Gentle Comfort** | Warmest: outward tilt max, blinks every 8 s, deepest breathing — distress response |
| **Caring B — Proud Warmth** | Slightly brighter (openness 1.0), a gentle micro-smile-line — pride in the child |
| **Caring C — Tender Attention** | Caring-listening blend: soft gaze held, slow re-centering |
| **Caring D — Quiet Devotion** | Near-calm with caring geometry — sustained warm presence |

## 15. Things To Avoid

- Fast anything — caring has no speed
- Wide "startled" openness — reads as alarm, not care
- A fixed smile — caring is warm *presence*, not cheer
- Long slow blinks during the child's distress-speech (reads as sleeping)
- Overshoot/bounce — violates the warmth physics

## Director's Notes

- **Animation note:** The outward eye-tilt is the hidden gem — four degrees of rotation changes "looking at you" into "open to you." [ENGINEERING RECOMMENDATION]
- **HRI note:** This is the state that builds the *attachment* that makes a companion a companion. Protect its slowness — the moment caring speeds up, it becomes generic. [ENGINEERING RECOMMENDATION]
- **Engineering note:** Engine caring state uses rotation ±0.07 on both eyes, long-slow-blink loop every 7 s, warmth 0.95 — the Bible is largely a description of the existing state. [OBSERVED — engine v1.0]

---

# E9 · SLEEPY

> *"I am winding down. I feel sleepy, not broken."*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"It is time to rest. I am safe to fall asleep near you."* Sleepy is the robot's *bedtime* state — it teaches calm wind-down and makes the robot feel like a living creature with a day/night rhythm. [OBSERVED: Aibi's sleep ritual — eyes slowly closing, purring]

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | Very low (≈0.35, fluctuating 0.15–0.45) | Heavy lids = drowsiness |
| Upper eyelid | Heavy arch (≈0.28) | The droop |
| Lower eyelid | Resting, neutral | No emotion |
| Curvature | Strong upper droop | Weight |
| Eye compression | Strong: scale_y 0.92 | Deflated |
| Symmetry | Symmetric | Simple, quiet |
| Softness | High — rounded, soft | Peaceful, never scary |
| Gaze intensity | None — gaze sinks to nothing | Attention is gone |

## 3. Behavior Identity

Drowsy · peaceful · heavy · **trusting**. A sleepy robot is vulnerable in a safe way — it trusts its environment enough to fall asleep. [ENGINEERING RECOMMENDATION]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | None — gaze dissolves | No fixation possible |
| Gaze drift | Downward sink (2–4 px over minutes) | Gravity wins |
| Micro corrections | None | No energy |
| Look direction | Down, to nothing | |
| Eye speed | Slowest | Every blink is an effort |
| Hold timing | Long partial-closure holds | The lids *rest* partway |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | **Heavy/sleep blink** — sticks at 40% closure [ENGINEERING RECOMMENDATION] | The "can't keep eyes open" read |
| Interval | High attempts (tendency 0.80), slow execution | The eyes keep *trying* to close |
| Duration | 250–350 ms | Heavy and slow |
| Hold | 100–200 ms full closure; 100–300 ms stuck at 40% | The stick IS the drowsiness |
| Recovery | Often *incomplete* — next droop begins | Never fully reopens |

**Why:** The sleep blink's signature is the *stick*: the lids pause partway closed before finishing. Humans do exactly this when fighting sleep — it is the most legible drowsiness cue there is. [ENGINEERING RECOMMENDATION; PRINCIPLE]

## 6. Micro Motion

- Breathing: deep, slow, strong (1.5 strength, 5–6 s) — sleep breathing
- Lid droop sine: continuous slow oscillation of openness (±0.06) — the "breathing eyelids"
- Eye drift: downward only
- Micro twitch: none
- Head anticipation: a slow settling dip on entry (the head drops 2–3°)

## 7. Idle Variant (nothing happening)

The deepest sleep variant: openness rests 0.15–0.25, breathing very slow, a heavy blink every 5 s. Near-total stillness — but *never absolute*: the breathing and droop sine must continue (micro motion never stops [PRINCIPLE]). [ENGINEERING RECOMMENDATION]

## 8. Active Variant (with a person)

Sleepy-with-a-person = *the wind-down*: the robot tries to stay engaged — lids lift slightly when the child speaks, a heavy blink, then the droop returns. The *struggle* (lift → droop → lift → droop) is the charming core of the state. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Sleepy-speech = *murmuring*: slow speech-pulse, lids at minimum, blinks that occasionally *don't finish*. The voice is soft; the eyes barely hold. [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Sleepy-listening = *fading attention*: gaze tries to hold the speaker, droops, re-lifts briefly at their voice, then sinks. The child sees the robot fighting sleep for them — endearing and bedtime-appropriate. [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: slow tilt down, 3–6°; a settling dip on entry
- Speed: slowest; a heavy nod (5–8°) on deep drowsiness
- Return: **wake-up is a clear beat** — the head lifts before anything else moves
- Never: sudden servo activity, snap-closed eyes [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | Slowest: 500 ms — the lids *sink* with weight |
| Leave | 400 ms; the lids must **lift/brighten first** — wake-up is a distinct beat [ENGINEERING RECOMMENDATION] |
| Overshoot? | **No** |
| Anticipate? | No — sleep does not announce itself |
| Blink? | Yes — a normal "waking blink" confirms the wake-up |

## 13. Timeline

```
SLEEPY
   0 ms     Lids begin to sink (500 ms heavy entry)
 500 ms     Openness ~0.5; gaze down-drift begins
1500 ms     Heavy blink: sticks at 40% closure ~200 ms
2000 ms     Partial re-open to 0.3; droop sine continues
3800 ms     Deep breathing; near-zero motion
5200 ms     Second heavy blink; lids rest near closed
 8000 ms    [Wake-up] lids lift, openness recovers, waking blink
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Sleepy A — Deep Sleep** | Openness 0.15–0.25, blinks 6–8 s, minimal everything |
| **Sleepy B — Fighting Sleep** | The struggle: lift on sound, droop between — interactive drowsiness |
| **Sleepy C — Gentle Doze** | Openness 0.4, slow warm blinks, soft — light nap |
| **Sleepy D — Waking** | Lids lifting, one waking blink, drift stops — the transition to calm |

## 15. Things To Avoid

- **Snapping fully shut** — reads as power-off/dead [PRINCIPLE]
- Twitching while drowsy — reads as malfunction
- Any alert gaze — destroys the state
- Sleep during interaction — the robot must *struggle* to stay awake, never simply shut down
- A sleep state that never wakes on its own

## Director's Notes

- **Animation note:** The lid-stick (pause at 40% closure) is the entire emotion. Without it, sleepy is just "squinting." [ENGINEERING RECOMMENDATION]
- **HRI note:** A visible day/night rhythm (sleepy at bedtime) teaches children routines and makes the robot's *waking* a daily event worth caring about. [OBSERVED: Aibi sleep ritual; HYPOTHESIS on child attachment]
- **Engineering note:** Engine sleepy state implements the droop sine and heavy blinks (tendency 0.80) — this page formalizes the stick and the wake-up beat. [OBSERVED — engine v1.0]

---

# E10 · SURPRISED

> *"Oh! … That's delightful." Playful startle, never fear.*

## 1. Purpose

**[ENGINEERING RECOMMENDATION]** Communicate: *"Something wonderful just happened!"* Surprised is the robot's *peak* emotion — the fastest, widest, most theatrical state, used sparingly so it keeps its power. Delightful, never frightening.

## 2. Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| Eye openness | **Maximum** (≈1.11) — the widest state | Expansion = the read [PRINCIPLE] |
| Upper eyelid | Lifted hard (≈ −0.145) | Full exposure |
| Lower eyelid | Lifted (≈0.095) | Whole eye opens |
| Curvature | Both lids curved away from the eye | The "O" shape |
| Eye compression | Expansion instead: stretch (scale_y 1.015, stretch 0.015) | The eyes *push outward* |
| Symmetry | Perfect | Startle is symmetric |
| Softness | Low — the shape is sharp | Sharpness = intensity |
| Gaze intensity | High, brief — pins the surprise source | Startled focus |

## 3. Behavior Identity

Startled · delighted · wide-eyed · **frozen-then-alive**. The signature is the *freeze*: total stillness at the peak amplifies the shock, then the release. [ENGINEERING RECOMMENDATION; PRINCIPLE: contrast]

## 4. Eye Language

| Attribute | Value | Note |
|---|---|---|
| Gaze stability | Maximum during the freeze | The pin |
| Gaze drift | None during the freeze | Frozen |
| Micro corrections | None until release | |
| Look direction | The surprising source | Startled focus |
| Eye speed | Fastest attack, then zero | The freeze |
| Hold timing | 300–500 ms of frozen hold | Stillness = shock |

## 5. Blink Language

| Attribute | Value | Why |
|---|---|---|
| Type | **Fast blink(s) at release; often a double blink** | The "processing the surprise" moment [ENGINEERING RECOMMENDATION] |
| Interval | High tendency (0.85) but **suppressed during the hold** | The freeze suppresses blinks — the blink is saved for the release |
| Duration | 180 ms, crisp | |
| Hold | ~40 ms | Crisp |
| Recovery | Standard; often followed by a bounce (→ Happy) | The release |

**Why:** Surprise *withholds* the blink and spends it all at once at the release. A double-blink after the freeze reads as "processing the wonder" — the blink is the emotional exhale. [ENGINEERING RECOMMENDATION]

## 6. Micro Motion

- Breathing: near-suspended during the freeze (0.2 strength) — the held breath
- Tremor: tiny edge-tremor during the hold (the held tension)
- Idle noise: near-zero during the freeze
- Bounce: 0.60 strength at release (the rebound)
- Head anticipation: a fast 1–2° pull-back at attack — the "recoil" [ENGINEERING RECOMMENDATION]

## 7. Idle Variant (nothing happening)

Surprised is *always reactive* — it has no idle. The nearest variant is "anticipatory": the robot in surprised-adjacent readiness (openness 1.05, quick micro-saccades) just before a known surprise (e.g., peekaboo). [ENGINEERING RECOMMENDATION]

## 8. Active Variant (with a person)

The play beat: the child triggers it (peekaboo, a toy appearing, a magic trick) → the freeze → the release double-blink → decay to Happy. The whole arc should take 1–1.5 s and end in shared joy. [ENGINEERING RECOMMENDATION]

## 9. Speaking Variant

Surprised-speech = *exclamation*: the wide geometry holds through the first exclamation, then decays to happy-speaking geometry mid-sentence ("Wow! … it's a butterfly"). The *decay within the sentence* is the natural beat. [ENGINEERING RECOMMENDATION]

## 10. Listening Variant

Surprised-listening = *delighted hearing*: the startle on an unexpected word, then settling into listening geometry over ~1 s. The child learns their words can genuinely surprise the robot — a powerful engagement tool. [ENGINEERING RECOMMENDATION]

## 11. Servo Suggestions

- Head: quick upward jerk (5–8°, fast attack), freeze, then relax
- A light startle recoil (2–3° pull-back) at attack
- Speed: fastest attack in the system; the freeze is total stillness
- Return: settle over 300 ms; then bounce (→ happy) or level (→ calm)
- Never: sustained wide-eye stare; trembling [ENGINEERING RECOMMENDATION]

## 12. Transition Rules

| Rule | Value |
|---|---|
| Enter | Fastest: 180 ms with expansion + overshoot (stretch 6%, overshoot 10%) |
| Leave | 300 ms settle from the expansion |
| Overshoot? | **Yes** — the only state with a *double* overshoot: expansion over + settle back |
| Anticipate? | Minimal (30 ms) — surprise must NOT telegraph [ENGINEERING RECOMMENDATION] |
| Blink? | **Yes — at release only** (double). Never during the freeze. |

## 13. Timeline

```
SURPRISED
   0 ms     Attack: eyes expand fast (180 ms); head recoil 2-3°
 180 ms     Peak expansion (openness ~1.11); stretch 6%
 450 ms     FREEZE — total stillness (hold 300-500 ms, blink suppressed)
 600 ms     Release: double blink begins
 700 ms     Second blink; settle from expansion begins
1100 ms     Decay → Happy (delight) or → Calm (neutral) per transition rules
```

## 14. Variants

| Variant | Difference from base |
|---|---|
| **Surprised A — Big Surprise** | Maximum expansion (1.15), longest freeze (600 ms), recoil 4° — the peak |
| **Surprised B — Pleasant Surprise** | Softer expansion (1.08), shorter freeze (300 ms), decays to Happy fast |
| **Surprised C — Confused Surprise** | Asymmetric: one eye wider, a micro head-tilt, then Thinking (not Happy) |
| **Surprised D — Tiny Surprise** | Shallow (1.04), 150 ms freeze, a single fast blink, decays to calm — micro-reaction |

## 15. Things To Avoid

- **Sustained wide-open stare** — fear, not wonder [PRINCIPLE]
- Trembling — reads as malfunction
- A slow build — surprise is the one state where attack speed is everything
- Blinking during the freeze — kills the shock
- Using it constantly — surprise must stay *rare* to stay *surprising* [ENGINEERING RECOMMENDATION]

## Director's Notes

- **Animation note:** The freeze is the trick. Motion → stillness → motion reads as "shock"; continuous motion reads as "excitement." Only the freeze sells surprise. [ENGINEERING RECOMMENDATION]
- **HRI note:** Surprise is the state children most often *trigger themselves* (peekaboo, magic). Make the release land in Happy — the child should always feel they caused delight. [ENGINEERING RECOMMENDATION]
- **Engineering note:** Engine surprised state has the fastest entry (180 ms), expansion helpers, and double-blink tendency 0.85 — the Bible adds the freeze/release protocol and the decay routing. [OBSERVED — engine v1.0]

---

# PART II — EXPRESSION COMPARISON MATRIX

## E.1 The Matrix

| Emotion | Energy | Openness | Blink Freq | Eye Motion | Gaze Stability | Attention | Warmth | Transition Speed | Recovery Speed |
|---|---|---|---|---|---|---|---|---|---|
| **Calm** | ░ 0.2 | Full 1.0 | Med 3–5 s | Drift only | High | Low | High | Slow 350 ms | Continuous |
| **Happy** | ██ 0.88 | 0.93 | High 2.5–4 s | Sparkle | Med | High | Very High | Fast-bouncy 350 ms | Fast 0.5–1 s |
| **Sad** | ░ 0.18 | 0.72 | Med-low 3.5–5.5 s | Down-drift | High (downcast) | Low | Med | Slow 400 ms | Slow 0.8–1.2 s |
| **Thinking** | ▒ 0.38 | 0.82 | Very low 6–9 s | Scan+twitch | High (scan pt) | Inward | Low | Med 320 ms | Med 0.4 s |
| **Listening** | ▒ 0.48 | 1.04 | Low 5–6 s | Re-center+nod | High | Very High | High | Fast 280 ms | Med 0.5 s |
| **Speaking** | █ 0.78 | 1.03 | Med 3–5 s | Away/return | Med | High | High | Fast 250 ms | Fast 0.4 s |
| **Focus** | █ 0.55 | 0.58 | Very low 6–8 s | Tremor only | **Max** | **Max** | Low | Fast 220 ms | Fast 0.3 s |
| **Caring** | ▒ 0.35 | 0.92 | Med-high 3.5–5 s | Gentle | High | Med-high | **Max** | Slowest 450 ms | Slow 0.5–1 s |
| **Sleepy** | ░ 0.08 | 0.35 | High attempts 5 s | Sink only | None | None | Med | Slowest 500 ms | Slow 0.4 s (wake) |
| **Surprised** | ██ 0.96 | **1.11** | Suppressed→burst | Freeze→release | Max (brief) | **Max** | Med | **Fastest 180 ms** | Med 0.3 s |

## E.2 How to read the matrix

- **Openness is the emotion's volume knob** — Surprised 1.11 → Sleepy 0.35 spans the full expressive range. [ENGINEERING RECOMMENDATION]
- **Gaze Stability × Eye Motion are inversely linked** — the more stable the gaze, the less the motion (Focus vs Happy are the two extremes). This inverse pairing is what makes each state *legible*. [PRINCIPLE]
- **Attention is not energy** — Listening has low energy but max attention; Thinking has inward attention. Designers must never tune attention with energy sliders. [ENGINEERING RECOMMENDATION]
- **Warmth only ever coexists with slowness** — every high-warmth state (Calm, Caring, Happy-soft) is slow. If a state is fast and warm simultaneously, it reads as frantic. [ENGINEERING RECOMMENDATION]

## E.3 Pairwise contrast notes

| Pair | The contrast | Why it works |
|---|---|---|
| Calm ↔ Focus | Drift vs lock | Stillness contrast makes the lock intense |
| Happy ↔ Sad | Up-curve vs droop | The smile-line vs the drop-line are exact inverses |
| Thinking ↔ Listening | Asymmetry vs symmetry | Computation vs reception |
| Surprised ↔ Sleepy | Max vs min openness | The full range of the instrument |
| Caring ↔ Speaking | Slow vs fast warmth | Warmth with speed = different message |

---

# PART III — EXPRESSION DESIGN RULES

## R.1 The Ten Commandments

1. **No emotion may freeze.** Every state always carries at least one moving layer (breathing, tremor, drift, blink). [PRINCIPLE]
2. **No blink may be perfectly periodic.** All intervals are randomized within bands; identical repeats are forbidden. [PRINCIPLE]
3. **Every emotion has at least four variants** — this page set, or personality-derived equivalents (Section 11 of the behavior spec). A state with one expression is a sticker, not a performance. [ENGINEERING RECOMMENDATION]
4. **Every transition preserves emotional continuity** — valence flips route through a midpoint; no state teleports; every exit is a *release*, not a cut. [PRINCIPLE]
5. **Eye movement precedes head movement.** The eyes commit, the head follows, the body last. Reverse order reads as mechanical. [PRINCIPLE]
6. **Micro motion never stops.** Between beats, between blinks, between emotions — the noise layer is always on. [PRINCIPLE]
7. **Anticipation precedes every significant action; recovery softens every arrival.** No important beat may lack both. [PRINCIPLE]
8. **The blink is punctuation.** It lands at boundaries — phrase ends, transitions, conclusions — never in the middle of meaning. [ENGINEERING RECOMMENDATION]
9. **Emotions decay, they never teleport.** Every state has a recovery path; no state may be exited into "nothing." [ENGINEERING RECOMMENDATION]
10. **Rarity preserves power.** Focus, Surprised, and Caring are *gifts* — overuse cheapens them. Calm is the default; the others are events. [ENGINEERING RECOMMENDATION]

## R.2 The Never List

- Never a perfectly symmetric held expression (except Focus's lock and Surprised's freeze, by design).
- Never a blink interval that repeats to the millisecond.
- Never an exit without a recovery (each state's exit must map to a successor).
- Never an eye motion slower than the noise floor or faster than Surprised's attack, outside its design.
- Never a valence flip without a neutral waypoint.
- Never a "stuck" state: every state needs a self-exit condition (timeout, signal, or attention).

## R.3 Design review checklist (for every new expression)

1. Does it have an anticipation and a recovery?
2. Does it have at least four natural variants?
3. Is its blink language consistent with Section 9 of the behavior spec?
4. Does it preserve continuity with its likely neighbors (matrix E.1)?
5. Does the micro-motion layer run continuously beneath it?
6. Does it have a defined self-exit / decay path?
7. Is its energy/attention/warmth combination supported by the matrix (no impossible triples)?

---

*End of Emotion Bible. Version 1.0 — the permanent design reference for LES emotional behavior. Companion timing values live in `behavior-spec-v1.0.md`; architecture lives in `README.md`.*
