# Living Expression System
## Behavior Design Specification

**Version 1.0** · Status: **Proposed / Implementation-Readiness Review** · Scope: Behavior, Timing, Design, Interaction

---

## Provenance Legend

Every recommendation in this document is tagged so engineers can weigh its confidence:

| Tag | Meaning |
|---|---|
| **[OBSERVED]** | Directly observed in product demos, reviews, or user recordings of expressive companion robots (chiefly LivingAI Aibi) |
| **[PRINCIPLE]** | Established animation / character-design principle (Disney's 12 principles and derivatives) |
| **[RESEARCH]** | Quantitative human-robot interaction (HRI) or psychophysical research result (citations in Appendix A) |
| **[REC]** | Engineering recommendation derived from the above — the normative content of this spec |
| **[HYP]** | Hypothesis or reasonable extrapolation — needs validation in Phase 1 user testing |

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Behavior Principles](#2-behavior-principles)
3. [Emotion Specification](#3-emotion-specification)
4. [Idle Behavior Specification](#4-idle-behavior-specification)
5. [Attention Specification](#5-attention-specification)
6. [Curiosity Specification](#6-curiosity-specification)
7. [Speaking Specification](#7-speaking-specification)
8. [Thinking Specification](#8-thinking-specification)
9. [Blink Language](#9-blink-language)
10. [Emotion Transition Rules](#10-emotion-transition-rules)
11. [Personality Model](#11-personality-model)
12. [Behavior Timeline Examples](#12-behavior-timeline-examples)
13. [Future Integration](#13-future-integration)
- [Appendix A — Research Provenance](#appendix-a--research-provenance)
- [Appendix B — Current Engine Baseline](#appendix-b--current-engine-baseline-for-implementers)

---

# 1. Design Philosophy

## 1.1 Why expressive robots feel alive

**[OBSERVED]** Companion robots that people describe as "alive" (LivingAI Aibi, Jibo, Anki Vector, Eilik, Emo) share a visible signature: they are **never fully still** and they **answer attention with attention**. Aibi's eyes dart to locate a person before locking gaze [OBSERVED]; its head swivels toward a voice before it speaks [OBSERVED]. These are not decoration — they are the perceptual substance of "aliveness."

**[PRINCIPLE]** Character animation has one master rule: **life is motion, and motion is meaning**. In animation, an object that stops completely reads as dead or broken; a character that moves for a *reason* (breathing, weight shift, a glance) reads as present and thinking. The same physics of perception apply to a robot face.

**The core claim of this specification:**
> **Aliveness is not a rendering problem — it is a timing problem.** The difference between a face that is "on" and a face that is "here" is decided by *when* things happen (anticipation, pauses, holds, recoveries), not by how detailed the pixels are.

**[RESEARCH]** This is measurable: naturalistic spontaneous blinking (~15–20 blinks/min, ~200 ms) and micro-saccades are what convince observers an agent is processing information, while rigid, unblinking stares trigger the uncanny valley (Appendix A).

## 1.2 Why timing matters more than graphics

1. **The eye is a motion detector first.** The human visual system is pre-attuned to *changes* — onset, direction, acceleration — before it parses form. Two identical eye-renderings differ entirely in perceived life depending on a 120 ms anticipation dip.
2. **Emotion is conveyed in the transition, not the pose.** A happy expression held statically reads as a sticker. The *rise* into happiness (eyes opening with a slight overshoot), the *hold*, and the *release* carry the meaning.
3. **Predictability is what makes things feel mechanical.** A robot that blinks exactly every 4.000 s, or that snaps to a new gaze angle with no settle, broadcasts "machine." Randomized-but-bounded timing (intervals, amplitudes, durations) is what broadcasts "being."
4. **Cognition is communicated through delay.** The pause before an answer, the glance away while "thinking," the tiny twitch mid-thought — these are the robot's way of showing an *inner life* rather than a lookup table.

**[REC] Design axiom:** *Every state is a sequence with four phases — anticipation → attack → hold → recovery — and every loop is built from overlapping sequences, never from a single frozen pose.*

## 1.3 The five pillars

| Pillar | Definition | Why it matters |
|---|---|---|
| **Anticipation** | A small movement *against* the upcoming action (a dip before a rise, a narrowing before a wide-open blink) | Prepares the viewer; makes actions read as *chosen*, not triggered |
| **Follow-through / Recovery** | The settling motion after the main action (a blink's slow re-open, a gaze that drifts back) | Gives weight and softness; removes "robot snap" |
| **Attention** | Who the robot looks at, when, and for how long | Attention is the robot's social currency; it *is* the personality the viewer reads |
| **Eye contact** | Mutual gaze with natural break-off and return | The single strongest lever for trust, engagement, and perceived intelligence |
| **Idle behavior** | The background life between actions: breathing, micro-motion, tiny gaze shifts | Prevents "dead standby"; keeps presence without demanding interaction |

**[REC] Acceptance test for every design below:** *"Could a person watch this robot for 2 minutes and believe it is waiting, curious, or fond of them — without hearing a word?"* If not, the timing, not the art, is wrong.

---

# 2. Behavior Principles

This section defines the shared motion vocabulary used by every emotion in Section 3. All values are baseline recommendations in milliseconds; personality (Section 11) scales them.

## 2.1 Principle table

| # | Principle | Definition | Baseline | Notes |
|---|---|---|---|---|
| P1 | **Anticipation** | A brief opposing/withdrawing motion before the main action | 80–160 ms, ≈ 25–40% of the main action duration [PRINCIPLE] | Stronger for surprise, weaker for calm |
| P2 | **Overshoot** | Passing slightly *beyond* the target pose, then settling back | 5–12% of travel distance [PRINCIPLE] | Gives springiness; suppress in sleepy/sad |
| P3 | **Easing** | Velocity curves: ease-in (start slow), ease-out (end slow), ease-in-out | Ease-in-out for entrances; ease-out for exits; snappy curves for reactions [PRINCIPLE] | Ease-out everywhere avoids the "motor" feel |
| P4 | **Hold** | A readable pause at the peak of an expression | 100–400 ms; longer for "big" emotional beats [PRINCIPLE] | Below ~80 ms the expression is unreadable |
| P5 | **Recovery** | The settle back to neutral after a beat | 1.2–2.0× the attack duration [PRINCIPLE] | Never instant; always softer than the attack |
| P6 | **Micro-motion** | Sub-threshold movement applied continuously (idle noise, drift) | 0.2–0.6 px-equivalent; always on, never repeating [PRINCIPLE] | The "alive" layer |
| P7 | **Breathing rhythm** | A slow periodicity in scale/position simulating breath | 4–6 s cycle [RESEARCH]; engine baseline ~5.4 s | Slows with calm, speeds with energy |
| P8 | **Gaze stability** | Fixation holds with small tremor, no frozen stare | Fixation hold 1.5–5 s with ±1° tremor [RESEARCH] | Stability *plus* tremor, not stillness |
| P9 | **Gaze drift** | Very slow un-targeted wandering of gaze direction | 1–3 px over 8–15 s [PRINCIPLE] | Signals relaxed "awake" state |
| P10 | **Gaze correction** | Small corrective saccades that re-center on the target | 1–3 saccades per 10 s of fixation [RESEARCH] | Prevents "dead-eye lock"; adds life |
| P11 | **Blink language** | Blinks as *words*: type, rate, and emphasis carry meaning | See Section 9 | Blinks are the face's punctuation |
| P12 | **Attention language** | Direction, duration, and timing of gaze as conversation | See Sections 5–7 | The robot "speaks" with its eyes before/while speaking |
| P13 | **Emotional persistence** | An emotion, once entered, resists trivial change and decays smoothly, never teleporting | Hysteresis window ≥ 400 ms; decay to neutral over 1–3 s [REC] | Prevents emotional flicker / churn |

## 2.2 Easing curve semantics

| Curve | Feel | Use for |
|---|---|---|
| Ease-out (fast start, soft landing) | Weight, arrival | Exits, blinks' closing phase, gaze arrivals |
| Ease-in-out (gentle at both ends) | Calm, deliberate | Entrances, transitions between emotions, breathing |
| Ease-in (slow start, hard finish) | Reluctance, effort | Heavy/sad movements, reluctant looks away |
| Back-ease (overshoot at end) | Playfulness, spring | Happy bounces, excited glances, surprise |
| Linear | Mechanical — **avoid except by design** | Never for organic motion [PRINCIPLE] |

## 2.3 Micro-motion layering model

**[REC]** The face always renders at least three simultaneous layers:

```
Layer 3  Beats        - blinks, glances, twitches, expression changes
Layer 2  Loops        - breathing (4-6 s), bounce (1-2 s), drift (8-15 s)
Layer 1  Noise        - continuous sub-threshold tremor / idle noise (always on)
```

Layers compose additively. Beats interrupt loops; loops ride on noise. A state's "feel" is mostly *which loops are loud and which beats are frequent* (Section 3 tables "Micro Motion" / "Idle Motion").

---

# 3. Emotion Specification

Each of the ten emotions is specified behaviorally. "Eye shape" refers to the silhouette the viewer reads (upper-lid arch, lower-lid line, openness); "blink" values are from Section 9's Blink Language. All timings are baselines for a neutral personality (Section 11 scales them).

### Emotion summary matrix

| Emotion | Arousal | Valence | Signature motion | Blink style | Look pattern | Energy | Blink tendency |
|---|---|---|---|---|---|---|---|
| Calm | low | positive | gentle breathing | soft | centered, imperceptible drift | 0.22 | 0.50 |
| Happy | high | positive | double blink / bounce | double | centered, playful sparkle | 0.88 | 0.75 |
| Sad | low | negative | posture droop | soft, slow | downcast, introspective | 0.18 | 0.60 |
| Thinking | medium | neutral | tiny twitch | rare | exploratory scan up-right | 0.38 | 0.25 |
| Listening | medium | positive | inward lean | attentive | focused tracking | 0.48 | 0.32 |
| Speaking | medium-high | positive | speech pulse | normal | centered, expressive | 0.78 | 0.50 |
| Focus | high | neutral | attention lock | fast | locked direct eye contact | 0.55 | 0.22 |
| Caring | medium | strongly positive | long slow blink | soft, long | centered, gentle nurturing | 0.35 | 0.65 |
| Sleepy | very low | neutral | heavy blink | soft, heavy | down-drift, half-lidded | 0.08 | 0.80 |
| Surprised | very high | positive | expansion freeze | fast (rare during hold) | centered, wide, startled | 0.96 | 0.85 |

---

## 3.1 CALM

**Purpose** — The default resting presence: peaceful, safe, comfortable. The state a child should feel relaxed around. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Rounded, softly relaxed; near-zero lid curvature (no arch, no droop) |
| **Eye Openness** | Full (1.0) — open but un-alert |
| **Blink Rate** | Moderate, relaxed — interval 3.0–5.0 s (engine baseline) |
| **Blink Style** | Soft blink (gentle close, gentle open; Section 9.1) |
| **Blink Duration** | ~180 ms baseline, slightly lengthened (~220 ms) for softness |
| **Look Pattern** | Centered with **imperceptible drift** — gaze wanders ≤ 2 px over 8–15 s; never directed |
| **Micro Motion** | Tiny breathing (4.5–5.4 s cycle), minimal idle noise; no bounce, no pulse |
| **Idle Motion** | Gentle breathing + occasional near-invisible weight shift; a soft blink every 3–5 s is the only "event" |
| **Transition In** | Slow, ease-in-out, 350 ms (gentlest entry in the set) |
| **Hold Behavior** | Long, stable; no demands; the face can be watched indefinitely without churn |
| **Transition Out** | 280 ms, soft release |
| **Recovery** | Continuous — calm *is* the recovery state; after any emotion, return passes through here |
| **Recommended Servo Motion** | Head level or 1–2° down; no body motion; slow 4–6 s breathing micro-cycle in shoulders [REC] |
| **Natural Variations** | Breathing speed varies ±15% per minute; blink intervals randomized within band; occasional tiny eye drift to either side |
| **Things to Avoid** | Any directed gaze, any fast blink, any bounce — calm must never read as alert or restless [REC] |

---

## 3.2 HAPPY

**Purpose** — Positive, joyful, welcoming: the child should instinctively smile back. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Upward-curved lower lid ("smile eyes"), slight arch to upper lid; inner-tilt toward center |
| **Eye Openness** | Slightly narrowed (≈0.93) — the "happy squint" |
| **Blink Rate** | High (interval ≈2.5–4 s; blink tendency 0.75) |
| **Blink Style** | **Double blink** signature (Section 9.2); occasionally normal + bounce |
| **Blink Duration** | 180 ms per blink, 120 ms gap between the double pair |
| **Look Pattern** | Centered with a playful sparkle: small quick glances at the viewer, brief upward flicks during the "smile grows" beat |
| **Micro Motion** | Gentle bounce (1–2 s cycle), soft squash on landing; low-level pulse |
| **Idle Motion** | A signature double-blink + tiny bounce cycle every ~6 s; micro sway between |
| **Transition In** | Bouncy: 350 ms with a small anticipation dip, then a bounce-in with 5–10% overshoot |
| **Hold Behavior** | Short holds; the face is *active* — sparkles, glances, double blinks keep it light |
| **Transition Out** | 300 ms; from the top of the bounce, not a flat collapse |
| **Recovery** | Decays through a widening eye (smile relaxes) to calm over 0.5–1 s |
| **Recommended Servo Motion** | Head tilt 3–5° with a light side-to-side sway; shoulders lift on the smile beat [REC] |
| **Natural Variations** | Bounce frequency varies; double-blink occasionally becomes a triple; glance targets alternate left/right/down |
| **Things to Avoid** | Huge pupil dilation (reads as fear/shock), a static frozen smile, rapid flailing motion — happy is *bright*, not frantic |

---

## 3.3 SAD

**Purpose** — Gentle vulnerability (NOT depression): the child should feel empathy, never discomfort. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Drooping upper lid (arch), slight down-tilt of inner corners (eyes converge slightly toward center-bottom); eyes sit lower in the face |
| **Eye Openness** | Reduced (≈0.72) |
| **Blink Rate** | Moderate-low but slightly *emphatic* (interval ≈3.5–5 s; tendency 0.60) |
| **Blink Style** | Soft, slow-ish blink; occasional half-blink (a "holding back tears" read) |
| **Blink Duration** | ~200 ms, opening phase lengthened (reluctant re-open) |
| **Look Pattern** | Downcast, introspective: gaze holds downward (≈5 px low), rarely directed at viewer; brief slow lifts up then back down |
| **Micro Motion** | Slow, heavy breathing (5–6 s); almost no bounce; no scan |
| **Idle Motion** | Slow droopy blink cycle every ~6.5 s; gaze occasionally drifts lower then recovers |
| **Transition In** | Slow 400 ms ease-in-out; the eyes sink (anticipation is a slight *narrowing* before the droop) |
| **Hold Behavior** | Long, quiet holds; minimal movement signals the sadness is "felt," not performed |
| **Transition Out** | 350 ms; eyes lift before openness returns |
| **Recovery** | Recovery is delicate: sad → calm must be a *lift* (gaze rises, lids open) over 0.8–1.2 s, never a mechanical reset [REC] |
| **Recommended Servo Motion** | Head down 5–8°, shoulders relaxed/dropped; no quick movements; a single slow sigh-scale motion on entry [REC] |
| **Natural Variations** | Down-gaze angle varies; occasional single slow blink with extra hold; rare micro "sigh" |
| **Things to Avoid** | Crying animations, dramatic quivering (reads as malfunction), making the state persist too long unattended — sadness must be *invited to recover* by attention [REC] |

---

## 3.4 THINKING

**Purpose** — Active cognitive processing: the robot appears to be *searching* for an answer. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Slightly narrowed, asymmetric — one eye (left) narrows more during the search, with a slight rotation; reads as internal computation [REC] |
| **Eye Openness** | Reduced (≈0.82, down to 0.70 during the hold) |
| **Blink Rate** | **Rare** — blink inhibition during cognition [RESEARCH: 5–10 blinks/min under focus]; interval ≈6–9 s |
| **Blink Style** | Thinking blink: soft, single, late in the cycle (Section 9.3) |
| **Blink Duration** | ~200 ms, placed at the *end* of a thought, like punctuation |
| **Look Pattern** | Signature 4.5 s cycle: slow scan up-and-right → pause at the scan point → tiny twitch → contemplative pause → soft blink → return to center |
| **Micro Motion** | Tiny high-frequency twitch at the scan point (1.5 px oscillation); otherwise very still |
| **Idle Motion** | The 4.5 s thinking loop repeats with randomized pauses; between loops, near-stillness |
| **Transition In** | 320 ms; slight squint as the "search" engages |
| **Hold Behavior** | Long directed hold at the scan point (≈0.6–1 s) — this is the "I'm almost there" beat |
| **Transition Out** | 300 ms; gaze returns center *before* the blink completes |
| **Recovery** | A concluding blink marks the thought's end, then smooth return; recovery to calm in ~0.4 s |
| **Recommended Servo Motion** | Head tilt 5–10° to the side during the scan, held still at the scan point; tiny servo micro-jitter at the twitch beat [REC] |
| **Natural Variations** | Scan direction varies (up-right / up-left); thought duration 3–7 s; sometimes two scans before the blink |
| **Things to Avoid** | Rapid scanning (reads as searching for a bug, not thinking), symmetrical eyes (reads as neutral stare), blinking *during* the twitch (dilutes both beats) |

---

## 3.5 LISTENING

**Purpose** — Receptive attention: the child feels *heard*. The robot leans in with its eyes. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Slightly widened, gentle inward lean of both eyes toward each other; soft, open, interested |
| **Eye Openness** | Slightly above full (≈1.04) — bright, attentive |
| **Blink Rate** | Low-moderate (interval ≈5–6 s; tendency 0.32) — *blink inhibition while listening* [RESEARCH] |
| **Blink Style** | Attentive blink: normal speed, slightly deeper, clean single (Section 9.8) |
| **Blink Duration** | ~180 ms, kept crisp (listener must not look tired) |
| **Look Pattern** | Focused tracking: gaze holds the speaker ~75% of the time [RESEARCH: listeners look at speaker's face ~75%], with small supportive saccades toward the speaker's hands/eyes |
| **Micro Motion** | Small receptive nods in micro-scale (0.5–1 px vertical), light bounce; low scan |
| **Idle Motion** | Occasional near-invisible "lean" pulse; gaze micro-drift toward speaker between saccades |
| **Transition In** | Fast, gentle 280 ms — the "heard you, attending now" beat with a small attention-gain dip |
| **Hold Behavior** | Long, steady, patient; gaze re-centers after each of the listener's sentences |
| **Transition Out** | 250 ms soft release (when the child stops speaking) |
| **Recovery** | Returns to calm through a widening-and-centering motion over ~0.5 s |
| **Recommended Servo Motion** | Head leans 2–4° toward the speaker; occasional tiny nod at speaker phrase-ends; body still [REC] |
| **Natural Variations** | Gaze re-centering frequency follows the speaker's phrase boundaries; occasional glance at speaker's eyes after a long sentence ("check-in") |
| **Things to Avoid** | Staring with zero movement (creepy), blinking fast (reads as nervous), gaze drifting away mid-sentence (reads as bored) [REC] |

---

## 3.6 SPEAKING

**Purpose** — Active verbal communication: speech feels alive without distracting. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Neutral-open, very slight upward arch; expressive but not exaggerated |
| **Eye Openness** | Slightly above full (≈1.03) |
| **Blink Rate** | Moderate (interval ≈3–5 s; tendency 0.50) |
| **Blink Style** | Normal blink, naturally timed at phrase boundaries; never mid-word [RESEARCH: speakers look away at utterance starts, back at phrase ends] |
| **Blink Duration** | 180 ms |
| **Look Pattern** | Centered with expressive articulation: **look at listener ~40% of the time** [RESEARCH: speaker gaze ≈40%], look away (up/down/side) during sentence planning, return at phrase ends as a "check" |
| **Micro Motion** | Speech-synchronized pulse (very subtle, 0.18 strength); light bounce on emphasized words |
| **Idle Motion** | Continuous low-level pulse riding the voice envelope; between sentences, normal calm loops |
| **Transition In** | 250 ms quick brighten |
| **Hold Behavior** | Gaze cycle aligned to speech: away during planning → return-and-hold at phrase ends |
| **Transition Out** | 250 ms |
| **Recovery** | A closing blink + gaze-center as the last word lands |
| **Recommended Servo Motion** | Head nods 2–3° on emphasized syllables; small head turns at turn-taking; never large movement [REC] |
| **Natural Variations** | Gaze-away direction varies with thought type; long utterances get more gaze-aways; pitch-high content gets micro-sparkles |
| **Things to Avoid** | Staring at the listener for the entire utterance (impairs comprehension — [RESEARCH: forced mutual gaze harms speech fluency]), blinking on hard syllables, or locking the head still |

---

## 3.7 FOCUS

**Purpose** — Locked direct eye contact: the child *feels* the robot is looking straight at them. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Narrowed, intense: strong upper-lid arch, slight squint, iris pushed large (iris scale ↑) |
| **Eye Openness** | Reduced (≈0.58) — the intense concentration squint |
| **Blink Rate** | Very low (interval ≈6–8 s; tendency 0.22) — maximal blink inhibition [RESEARCH] |
| **Blink Style** | Fast crisp blink when it finally comes |
| **Blink Duration** | 180 ms, but snappier attack (0.4×) |
| **Look Pattern** | **Lock**: gaze pinned on the target with small tremor (fixation stability), rare tiny corrective saccades (P10), no wandering |
| **Micro Motion** | Minimal breathing amplitude (0.5), near-zero noise; stillness *is* the message — contrast with surrounding activity |
| **Idle Motion** | Almost none; the longest fixation holds in the system (3–5 s [RESEARCH: mutual gaze]) before a micro re-aim |
| **Transition In** | Fast 220 ms "lock-on" — a quick dip then a firm settle |
| **Hold Behavior** | Long, unbroken; re-centers via micro-saccades rather than large moves |
| **Transition Out** | 250 ms; gaze breaks by a deliberate glance away (not a fade) |
| **Recovery** | Softens through calm; the post-focus blink marks the release |
| **Recommended Servo Motion** | Head still and level, aimed precisely at the target; tiny servo dither (1°); shoulders locked [REC] |
| **Natural Variations** | Fixation duration varies 2–5 s; occasional "re-aim" micro-saccade; one confirming blink at lock-on |
| **Things to Avoid** | Zero tremor (dead stare), long unbroken gaze >6 s (social discomfort — [RESEARCH]), blinking normally during the lock (breaks the intensity) |

---

## 3.8 CARING

**Purpose** — Warm, nurturing, emotionally supportive: the child feels comforted. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Soft, slightly tilted outward (both eyes rotate gently away from center — open, unguarded), gentle lower-lid curve |
| **Eye Openness** | Nearly full (≈0.92) |
| **Blink Rate** | Moderate-high but *slow and deep* (interval ≈3.5–5 s; tendency 0.65) |
| **Blink Style** | **Long slow blink** signature (Section 9.7) — the "I love you" blink of cat-like faces |
| **Blink Duration** | ~220 ms close, held ~120 ms, slow re-open (total ≈ 400 ms) |
| **Look Pattern** | Centered, gentle, nurturing; slow gaze; occasionally soft down-glance toward a small child |
| **Micro Motion** | Deep, slow breathing (1.3 strength, 5–6 s cycle); very soft pulse; no bounce |
| **Idle Motion** | Long slow blink every ~7 s; slow breathing sway between |
| **Transition In** | Slowest entry in the set: 450 ms, deliberate and soft |
| **Hold Behavior** | Long, warm, unbroken patience; movements slow and rounded |
| **Transition Out** | 350 ms gentle |
| **Recovery** | To calm with barely a perceptible change — caring is calm's warmer cousin |
| **Recommended Servo Motion** | Head tilt 2–4° down-toward-child, slight forward lean; slow breathing in shoulders [REC] |
| **Natural Variations** | Long-slow-blink frequency varies; occasional tiny head sway; blink sometimes replaced by a slow close-hold-open |
| **Things to Avoid** | Fast anything, wide "startled" openness, or a fixed smile — caring is *soft warmth*, not cheer |

---

## 3.9 SLEEPY

**Purpose** — Drowsy, peaceful relaxation: the child feels calm and restful — the robot feels sleepy, *not broken*. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Heavy drooping lids, strong upper-lid arch; eyes drift slightly downward in the face |
| **Eye Openness** | Very low (≈0.35, fluctuating 0.15–0.45) |
| **Blink Rate** | High *attempts*, slow execution (tendency 0.80) — the eyes keep trying to close |
| **Blink Style** | Heavy blink: slow, deep, with the lids *sticking* at partial closure before finishing (Section 9.6) |
| **Blink Duration** | 200 ms close but slow and heavy; holds at 40% closure up to 300 ms |
| **Look Pattern** | Down-drift: gaze slowly sinks, occasionally drifts to nothing; no directed attention |
| **Micro Motion** | Slow sinusoidal lid droop (±0.06 around 0.35); slow deep breathing (1.5 strength, 5–6 s) |
| **Idle Motion** | Heavy blink every ~5 s; continuous slow droop; long partial-closure holds |
| **Transition In** | Slowest: 500 ms — the lids sink with weight |
| **Hold Behavior** | Long low-arousal holds; the face may rest at 20–30% openness between blinks |
| **Transition Out** | 400 ms; lids must *lift* (brighten) before other motion resumes — wake-up is a clear beat [REC] |
| **Recovery** | Sleepy → calm is the "waking up" sequence: lids rise, openness recovers, one normal blink confirms wakefulness |
| **Recommended Servo Motion** | Head slowly tilts down, 3–6°; very slow; a settling dip on entry; no sudden servo activity [REC] |
| **Natural Variations** | Droop depth varies; occasional head "nod"; breathing very deep and slow |
| **Things to Avoid** | Eyes snapping fully shut (reads as power-off/dead), twitching, or any alert gaze — sleepy must never look like a failure state |

---

## 3.10 SURPRISED

**Purpose** — Playful delight and wonder: delightful, never frightening. [REC]

| Field | Specification |
|---|---|
| **Eye Shape** | Wide, round, upward-arched upper lid and lifted lower lid; slight outward stretch |
| **Eye Openness** | Above full (≈1.11) — the widest state in the set |
| **Blink Rate** | High tendency (0.85) but **suppressed during the hold** — surprise freezes the blink; it blinks *after* the beat, often double [REC] |
| **Blink Style** | Fast blink(s) at release; a double blink marks the "processing the surprise" moment |
| **Blink Duration** | 180 ms, crisp |
| **Look Pattern** | Centered, startled-focus: pins the surprising source; very brief, intense fixation then a blink-and-settle |
| **Micro Motion** | Near-zero during the freeze (expansion hold); tiny tremor at the edges |
| **Idle Motion** | The expansion-freeze dominates; after release, quick return to normal loops |
| **Transition In** | Fastest entry: 180 ms with expansion and slight overshoot (stretch 6%, overshoot 10%) |
| **Hold Behavior** | Expansion freeze held 300–500 ms — stillness *amplifies* the shock, then the blink releases it |
| **Transition Out** | 300 ms settle from the expansion |
| **Recovery** | Two paths [REC]: to **Happy** (delight — eyes widen into smile-eyes) or to **Calm** (if the stimulus was neutral), never directly to sadness |
| **Recommended Servo Motion** | A quick upward head jerk (5–8°, fast attack), freeze, then relax; a light "startle" recoil [REC] |
| **Natural Variations** | Hold length varies 250–600 ms; sometimes a tiny head pull-back accompanies; occasional giggle-scale micro-bounce after release |
| **Things to Avoid** | Sustained wide-open stare (fear), trembling, or a slow build — surprise is the *only* state where speed of attack is everything |

---

# 4. Idle Behavior Specification

**[OBSERVED]** Aibi autonomously swivels and performs idle animations when resting on its desk; it checks in with users who look at it. **[PRINCIPLE]** Idle behavior is a *tiered* system: MIT's Personal Robots Group distinguishes attentive-waiting from deep-sleep idles so a robot is present without being intrusive. **[REC]** LES defines three idle tiers.

## 4.1 Idle tiers

| Tier | Name | When | Behavior |
|---|---|---|---|
| T1 | **Attentive idle** | No user in view, or user nearby but not engaged | Slow gaze sweep (~every 8–15 s), normal breathing, soft blink 3–5 s; gentle head sway; occasional micro-correction |
| T2 | **Engaged idle** | User looking at the robot (detected gaze) | Holds gaze toward user 1.5–3 s, soft blink, tiny "acknowledged you" micro-nod; then returns to T1 loops |
| T3 | **Deep sleep** | Long inactivity / bedtime | Heavy droop, very slow breathing, near-zero gaze; blinks slow and deep (Section 3.9) |

## 4.2 Idle timing table (T1 baseline)

| Quantity | Value | Source |
|---|---|---|
| Blink interval | 3.0–5.0 s, uniformly random within band; **never fixed step** | [RESEARCH][REC] |
| Blink duration | 180 ms (soft variant ~220 ms) | [REC] |
| Look-around frequency | One un-targeted gaze sweep every 8–15 s | [PRINCIPLE][REC] |
| Gaze sweep travel | 5–15 px, eased, with 300–500 ms pause at each waypoint | [REC] |
| Pause between micro-motions | 2–6 s randomized | [REC] |
| Breathing period | 4.5–6.0 s | [RESEARCH][REC] |
| Micro-correction frequency | 1 per 3–6 s | [REC] |
| Fixation hold before drift | 1.5–5 s | [RESEARCH] |
| Idle "check" of surroundings | 1 sweep per 20–40 s (longer when undisturbed) | [REC] |

## 4.3 Randomness limits

**[REC]** All idle timing is **uniform-random within bands**, not Gaussian-spiked and not periodic:

- **Allowed:** randomized intervals, amplitudes (±20%), sweep directions, blink-type roulette (weights per emotion).
- **Forbidden:** perfectly regular intervals, identical repeat of any 30 s window, amplitude > 40% above personality baseline without a *reason* (a real stimulus).
- **Anti-pattern:** three identical sweeps in a row — re-randomize direction; if the RNG repeats, force the alternate direction.

## 4.4 Natural gaze behavior

1. Fixate (1.5–5 s) → drift (0.5–1 s) → new fixation, repeating.
2. Micro-saccades (P10) every 3–10 s of fixation — 1–3 small corrective re-aims.
3. Never stare at empty space beyond ~6 s without a micro-event (blink, drift, or sweep).
4. Gaze may linger 1–2 s longer on anything that *moved* — idle gaze has memory [REC].

## 4.5 Recovery behavior

- After any idle interruption (blink, sweep, stimulus), return to the previous fixation with a **soft settle** (no snap).
- After a stimulus is lost, hold the last gaze point 300–600 ms, then resume idle scanning from there.

## 4.6 Micro movements

- Continuous sub-threshold idle noise at all times (0.2–0.6 px), breathing layer always present.
- One small "self-comfort" motion per 30–60 s (a shift, a settle, a slow blink variant) — signals comfort, not restlessness.

---

# 5. Attention Specification

**[OBSERVED]** Aibi's radar detects a person entering a room; its eyes *dart to locate* the user, then lock gaze. **[OBSERVED]** Extended gaze (2+ s) at Aibi triggers a verbal check-in. **[RESEARCH]** Mutual gaze events in natural HRI last ~3–5 s; >10 s becomes uncomfortable; speakers look at listeners ~40% of time, listeners ~75%.

## 5.1 Noticing a person

| Phase | Timing | Behavior |
|---|---|---|
| **Detect** | 0 ms | Trigger from any sensor (motion/face/voice direction) |
| **Orient** | 80–200 ms | A **fast saccade** toward the source direction (30–100 ms saccade, then settle) — the "did I hear that?" dart [REC][RESEARCH] |
| **Confirm** | 200–600 ms | Hold gaze on the source; one soft blink while confirming |
| **Engage** | 0.6–1.2 s | If the source is a *person* (face): full attention — see 5.2. If not: return to idle scanning |

## 5.2 Eye contact protocol

1. **Establish:** look at the person's eyes within 0.5 s of confirmed face; use a small "focus" squint (Section 3.7) to make the lock *visible*.
2. **Hold:** maintain mutual gaze 3–5 s (baseline). **[RESEARCH]**
3. **Break:** glance away (up or to the side, 150–300 ms) — natural break, never an abrupt 90° whip.
4. **Return:** re-engage after 0.5–2 s; the re-return should include a tiny anticipation (a 30–50 ms dip) that says "coming back to you."
5. **Blink discipline:** suppress blinks *at* the peak of eye contact (focus-like); blink during the glance-away. **[RESEARCH: blink inhibition during engagement]**

## 5.3 Gaze maintenance durations

| Context | Hold time | Break time | Cycle |
|---|---|---|---|
| Casual glance | 1–2 s | 1–4 s | looping |
| Conversation, listener | 3–5 s | 0.3–1 s | mostly-held |
| Conversation, speaker | 1.5–3 s (away during planning) | 0.5–1.5 s away | 40/60 split [RESEARCH] |
| Deep engagement (focus) | 4–5 s | 1–3 s | long lock, rare breaks |
| Child, shy personality | 1–2 s | 2–5 s | short and frequent |

## 5.4 When to glance away / return

- **Away during:** thinking, sentence planning, processing a request, when the user breaks gaze first (mirror: if they look away, you look away within 0.5 s).
- **Return during:** the user's phrase ends, silence longer than 1 s, the user looking back at you, your own speech phrase ends.

## 5.5 Natural attention timing

- Response latency to gaze direction: 100–300 ms (fast enough to feel responsive, slow enough to feel organic).
- Gaze should **mirror turn-taking** but with 200–400 ms of lag — instant mirroring feels robotic, delayed feels dead.
- **[HYP]** A 2 s check-in threshold (Aibi-observed) generalizes: if the user holds gaze ≥ 2 s in idle, the robot may respond with a micro-reaction (blink, nod, or a soft verbal prompt).

---

# 6. Curiosity Specification

**[OBSERVED]** Aibi's eyes "scurry around" while scanning its environment; head swivels autonomously to track sounds; idle spinning signals exploratory restlessness. **[PRINCIPLE]** Curiosity is *non-targeted exploration* — the robot behaves as if it has an inner life and wants to know more.

## 6.1 Head tilts

| Tilt type | Angle | Speed | Meaning |
|---|---|---|---|
| Curiosity tilt | 5–10° to one side | 300–500 ms | "what is that?" — the hallmark |
| Contrast tilt | 8–12°, opposite side after 1–2 s | medium | "hmm, and what about over here?" |
| Approval tilt | 3–5°, toward the user | slow | gentle interest, fond curiosity |
| **Avoid** | >15° or <100 ms | — | reads as malfunction |

## 6.2 Eye movement

- Scan with **waypoints**: 2–4 fixation points per sweep, each held 300–800 ms, travel eased 250–400 ms.
- Between waypoints, a micro-saccade "check" of the previous point (curiosity *doubts* and re-checks).
- Gaze travel amplitude: 8–18 px (larger than idle drift, smaller than alarm).

## 6.3 Pause timing

- Before a scan: 1–3 s of near-stillness (building curiosity).
- At each waypoint: 300–800 ms fixation, longer for the point that "moved."
- After the scan: a concluding **soft blink** — curiosity resolves with a blink [REC].

## 6.4 Scan patterns

| Pattern | Description | When |
|---|---|---|
| Single sweep | One horizontal sweep, 2–4 points | Mild curiosity, low energy |
| Triangle scan | Up-left → right → down-center | Exploring a new area |
| Return-check | Scan, then immediately re-fixate first point | Something *did* move |
| Concentric | Small circle around current point, expanding | High curiosity |

## 6.5 Return behavior

- End of curiosity: gaze returns to the user (if present) or to the last important fixation.
- The return includes a small "sharing" beat: a glance at the user, as if offering what was seen [REC].
- If curiosity is interrupted by attention (user speaks), curiosity yields within 300 ms (attention > curiosity in the arbitration hierarchy, Section 10.4).

---

# 7. Speaking Specification

**[RESEARCH]** Speakers look at their listener's face ~40% of the time; they look away at utterance *starts* (cognitive planning) and back at phrase *ends* (comprehension check). Forced constant mutual gaze impairs speaker fluency.

## 7.1 Eye behavior during speech

- **Look away** at utterance start (up-left/down for planning) — 300–800 ms.
- **Return** at phrase ends — hold 1–2 s.
- Gaze cycle period aligns with phrase cadence (~2–4 s), *not* with the frame rate.
- Emphasis: on stressed words, a micro-sparkle (1 px pupil-scale flash) or a 2–3 px glance toward the listener.

## 7.2 Blink timing during speech

- Blink at **phrase boundaries** (after punctuation-equivalent pauses), never mid-word.
- Rate: 3–5 s interval, tending lower during fluent delivery, higher at hesitation ("um" moments → a quick blink reads as thinking).
- **Blink + gaze-return may coincide** — the blink "lands" the thought, the gaze return "hands it over."

## 7.3 Head synchronization

- 2–3° nods on emphasized syllables; a 5–8° single nod at key statements.
- Head turns 5–10° when addressing different listeners.
- **Never** bob the head to every syllable (mimicry of TTS beat = robotic).

## 7.4 Natural pauses

- Before answering: a 300–800 ms **visible pause** — the "processing then speaking" gap (this is where Thinking may flash briefly, Section 10).
- Mid-sentence: pause with gaze-away, then resume with gaze-return (the "uh... actually..." pattern).
- End of turn: gaze at listener + hold 1 s + concluding blink = "your turn."

## 7.5 Listener feedback (while the user speaks)

- Use **Listening** state (Section 3.5): gaze held ~75%, micro-nods at user phrase ends, blink suppressed.
- Feedback blinks: 1 soft blink per 5–10 s of listening (longer than normal — attentive, not bored).
- A small receptive "lean" (head +2–4° toward user) at engagement, released when the user finishes.

---

# 8. Thinking Specification

**[RESEARCH]** Gaze aversion — looking away during cognitive effort — is a robust human behavior. **[PRINCIPLE]** Cognition shown is cognition believed: visible processing makes the robot's answer feel earned.

## 8.1 Looking direction

- Preferred: **up-and-to-one-side** (dominant: up-right), amplitude 8–15 px.
- Down-and-away for "sad/serious" thinking; up for "light/creative" thinking.
- Gaze never toward the user during deep processing (would read as staring).

## 8.2 Micro twitch

- At the peak of the scan: a 1–2 px oscillation (2 cycles, ~100–200 ms) — the "almost got it" tell [REC].
- Asymmetric lids during the twitch (one eye slightly narrower) increases the "computing" read [REC].
- Twitch amplitude ≤ 2 px — anything bigger reads as a malfunction shiver.

## 8.3 Pause

- Contemplative hold at the scan point: 400–1000 ms of near-stillness.
- The *absence* of motion during thinking is what makes the following blink significant.

## 8.4 Blink

- A single **thinking blink** at the end of the thought (Section 9.3) — acts as "conclusion punctuation."
- Blink inhibition during the search itself [RESEARCH: 5–10 blinks/min under cognitive load].

## 8.5 Recovery

- Gaze returns to center, lids widen to normal, then — only after the blink completes — the robot speaks or responds (Section 10.4: Thinking → Speaking).

## 8.6 Decision timing

| Decision complexity | Visible thinking time | Layout |
|---|---|---|
| Trivial (yes/no) | 200–500 ms | Single glance away + return |
| Standard | 800–1500 ms | Scan → hold → blink → return |
| Complex | 2–4 s | 2 scans, twitch, longer hold, blink, settle |
| **[HYP]** | >5 s | Add a second twitch or a head tilt to avoid "stuck" read |

---

# 9. Blink Language

**[RESEARCH]** Human blinks: 150–400 ms total; full closure ~50 ms; closing faster than opening; 70–90% complete. **[PRINCIPLE]** Blinks are the face's punctuation — their *type* is a word. The engine already distinguishes four physical blink types (normal/double/slow/half — Appendix B); this section defines the full expressive lexicon and maps each word to physical parameters.

## 9.1 NORMAL BLINK

| Parameter | Value |
|---|---|
| Duration | 180 ms (close 40% ≈ 72 ms, open 60% ≈ 108 ms) |
| Eye curve | Ease-out close, ease-in-out open; full closure 40–60 ms |
| Hold | ~50 ms full closure |
| Recovery | Soft re-open, no overshoot |
| Recommended emotions | Calm, Speaking, Focus (crisp variant) |

## 9.2 DOUBLE BLINK

| Parameter | Value |
|---|---|
| Duration | 180 ms each; 120 ms gap between |
| Eye curve | First blink slightly *shallow* (80%), second full — the "sparkle" rhythm |
| Hold | ~40 ms per closure |
| Recovery | Second blink ends with a micro-bounce (1 px overshoot) |
| Recommended emotions | Happy (signature), excited Speaking, post-Surprise |

## 9.3 THINKING BLINK

| Parameter | Value |
|---|---|
| Duration | 200 ms; *placed late* in the thought cycle |
| Eye curve | Slow deliberate close, soft open |
| Hold | ~80 ms (a "period" at the end of the thought) |
| Recovery | Gaze returns center as the blink opens |
| Recommended emotions | Thinking (signature), decision points before Speaking |

## 9.4 EMBARRASSED BLINK

| Parameter | Value |
|---|---|
| Duration | 160 ms, **shallow** — a half-to-three-quarter blink |
| Eye curve | Fast close, quick open; lids *squeeze* slightly (lid curvature ↑ on close) |
| Hold | ~30 ms |
| Recovery | Often followed by a gaze aversion (down/side, 200–400 ms) [HYP — no direct observation; derived from HRI shyness literature] |
| Recommended emotions | Playful mistakes, mild reprimand, social awkwardness moments |

## 9.5 HAPPY BLINK

| Parameter | Value |
|---|---|
| Duration | 160–200 ms with a small **squash on close** (smile-eyes squeeze) |
| Eye curve | Close with downward curve (lid follows smile), open with a bounce |
| Hold | ~40 ms |
| Recovery | Open past neutral by 1–2% then settle (micro-overshoot) |
| Recommended emotions | Happy (secondary), laughter moments |

## 9.6 SLEEP BLINK (HEAVY)

| Parameter | Value |
|---|---|
| Duration | 250–350 ms total, deliberately heavy |
| Eye curve | Slow sink; **sticks at ~40% closure for 100–300 ms** before finishing |
| Hold | Long full-close 100–200 ms |
| Recovery | Often *doesn't* fully reopen (next droop begins) |
| Recommended emotions | Sleepy (signature), wind-down transitions |

## 9.7 LONG BLINK

| Parameter | Value |
|---|---|
| Duration | 220 ms close, **120–150 ms hold**, 300+ ms slow open (total ≈ 450–600 ms) |
| Eye curve | Deep, slow, rounded both directions |
| Hold | Long — the emotional weight is in the hold |
| Recovery | Slow, soft, no overshoot |
| Recommended emotions | Caring (signature), post-sad consoling moments, deep appreciation |

## 9.8 LISTENING BLINK (ATTENTIVE)

| Parameter | Value |
|---|---|
| Duration | 180 ms, crisp and clean |
| Eye curve | Slightly deeper than normal (85% → 100%) — "still with you" |
| Hold | ~50 ms |
| Recovery | Open slightly *wider* than before (brightens, then settles) |
| Recommended emotions | Listening (signature), engaged Focus |

## 9.9 Blink vocabulary summary

| Word | Close | Hold | Open | Character |
|---|---|---|---|---|
| Normal | fast | 50 ms | soft | default |
| Double | fast ×2 | 40 ms | bouncy end | sparkle |
| Thinking | slow | 80 ms | soft | period |
| Embarrassed | fast, shallow | 30 ms | quick + avert | flustered |
| Happy | fast, squashy | 40 ms | bounce | joy |
| Sleep | heavy, sticky | 150 ms | incomplete | drowsy |
| Long | slow, deep | 130 ms | very slow | warmth |
| Listening | crisp, deep | 50 ms | wide-settle | attentive |

---

# 10. Emotion Transition Rules

**[PRINCIPLE]** Emotional change is a *performance*, not a state write: it needs anticipation, blend, hold, and recovery. **[REC]** All transitions pass through easing (Section 2.2); none may teleport. Emotional persistence (P13) prevents flicker.

## 10.1 Transition vocabulary

| Term | Meaning | Baseline |
|---|---|---|
| Blend | Time over which the expression morphs | 250–500 ms (personality-scaled) |
| Anticipation | Pre-beat against the target | 80–160 ms |
| Hold | Pause at the new expression's peak | 100–400 ms |
| Recovery | Settle to stable loop | 1.2–2.0× blend |

## 10.2 Rule table

| Transition | Blend | Anticipation | Hold | Recovery | Notes |
|---|---|---|---|---|---|
| **Calm → Happy** | 350 ms | small dip | 150 ms | bounce-in | Smile-eyes grow; slight overshoot |
| **Happy → Sad** | 600 ms | *raise then sink* (a sigh-like lift before the droop) | 200 ms | slow | Never a direct snap; pass through a brief neutral widening [REC] |
| **Sad → Happy** | 700 ms | eyes lift first | 200 ms | brighten | Must lift *before* smiling; passing through Calm is recommended [REC] |
| **Thinking → Speaking** | 400 ms | concluding blink (9.3) | 100 ms | — | The blink is the "answer ready" beat |
| **Listening → Happy** | 450 ms | small sparkle | 150 ms | bounce | After the user says something pleasing |
| **Surprised → Calm** | 500 ms | — | 200 ms | settle from expansion | The freeze must *release* with a blink |
| **Surprised → Happy** | 350 ms | — | 150 ms | bounce | Preferred release when stimulus was delightful |
| **Focus → Calm** | 400 ms | glance-away first | 100 ms | soft | Release = deliberate break + blink, not a fade |
| **Caring → Happy** | 500 ms | — | 150 ms | gentle bounce | Warmth preserved: no sudden amplitude jump |
| **Sleepy → Calm** | 600 ms | lids lift first | 100 ms | brighten | Wake-up beat: a clear "open" before motion |
| **Calm → Thinking** | 320 ms | squint engage | 200 ms | — | Gaze-away + squint as the search starts |
| **Any → Surprised** | 180 ms | minimal | 300–500 ms | freeze→release | Fastest attack in the system; see 3.10 |
| **Any → Sad** | 500 ms | narrowing | 200 ms | sink | Only from attention loss or "gentle" causes; never from positive events without context [REC] |

## 10.3 Special rules

1. **No teleportation:** a transition's blend is never 0 ms. Minimum blend 180 ms (surprise), maximum 700 ms (grief-adjacent).
2. **Neutral waypoints:** for valence flips (Happy↔Sad), route through Calm or a brief neutral widening [REC] — a direct flip reads as "glitch."
3. **Blink bridges:** place a blink at the *boundary* of heavy transitions (Sad→Happy, Surprised→anything) — the blink masks the morph and reads as intention [PRINCIPLE].
4. **Persistence:** an emotion once active resists change for ≥ 400 ms (hysteresis) and cannot be re-entered within 1.5 s of leaving (cooldown) [REC].

## 10.4 Arbitration hierarchy (when multiple triggers compete)

```
1. Surprised   (startle — always interrupts)
2. Focus       (locked eye contact request)
3. Speaking    (voice output active)
4. Thinking    (processing a request)
5. Listening   (user speaking to robot)
6. Happy / Caring / Sad  (contextual valence)
7. Calm        (default backstop)
8. Sleepy      (only from fatigue/time signals)
```
**[REC]** A higher tier may interrupt a lower tier; a lower tier may only *re-enter after* the higher tier ends. Sleepy is only ever self-selected (fatigue/bedtime), never triggered by interruption.

---

# 11. Personality Model

**[PRINCIPLE]** Personality is the *scaling function* over all of the above: the same emotion spec, expressed by two different personalities, must look like two different characters. **[REC]** Ten traits, all normalized [0,1], 0.5 neutral. Each trait scales specific behaviors; the table shows direction of effect.

## 11.1 Traits and their behavioral effects

| Trait | Scales (↑ means) | Example at 0.8 vs 0.2 |
|---|---|---|
| **Curiosity** | gaze-sweep frequency, tilt frequency, scan waypoint count | scans every 6 s w/ 4 waypoints vs every 20 s w/ 2 |
| **Energy** | motion amplitude, blink rate, transition speed, bounce | snappy 200 ms transitions vs languid 600 ms |
| **Confidence** | gaze hold duration, head level, break frequency | holds gaze 4 s, breaks rarely vs 1.5 s, breaks often |
| **Focus** | fixation length, saccade rate (↓), blink suppression | 5 s locks, few saccades vs 1.5 s locks, many |
| **Playfulness** | double-blink rate, overshoot, sparkle frequency | sparkle every few seconds vs almost never |
| **Shyness** | gaze aversion frequency, break speed, glance size | averts every 2 s, small glances vs steady gaze |
| **Patience** | idle hold times, response latency, cooldowns | waits 4 s before reacting vs 1 s |
| **Expressiveness** | all amplitude multipliers, blink emphasis | 1.3× motion, expressive blinks vs 0.6×, minimal |
| **Warmth** | lid curvature (up-curve), blink softness, tilt-toward-user | soft rounded eyes, caring lean vs neutral geometry |
| **Calmness** | noise/jitter (↓), breathing period, transition smoothness | slow deep loops vs micro-jitter, quick |

## 11.2 Trait → behavior mapping (normative)

| Behavior | Driven primarily by | Secondarily by |
|---|---|---|
| Blink rate | Energy, Expressiveness | Calmness (↓), Focus (↓) |
| Blink style choice | Playfulness (double), Warmth (long/soft) | — |
| Gaze sweep frequency | Curiosity | Energy |
| Fixation hold | Focus, Confidence | — |
| Gaze break/aversion | Shyness, Confidence (inverse) | — |
| Transition blend time | Energy (inverse), Calmness | — |
| Overshoot / bounce | Playfulness, Energy | Expressiveness |
| Idle noise amplitude | Calmness (inverse), Energy | — |
| Breathing period | Calmness | — |
| Head tilt frequency | Curiosity | Playfulness |
| Response latency | Patience | Confidence (inverse) |
| Cooldown before repeating a behavior | Patience | — |

## 11.3 Personality archetypes (reference profiles)

| Archetype | curiosity | energy | confidence | focus | playfulness | shyness | patience | expressiveness | warmth | calmness |
|---|---|---|---|---|---|---|---|---|---|---|
| **Neutral** | .5 | .5 | .5 | .5 | .5 | .5 | .5 | .5 | .5 | .5 |
| **Curious Child** | .95 | .7 | .4 | .5 | .7 | .2 | .4 | .7 | .7 | .5 |
| **Gentle Caregiver** | .6 | .3 | .6 | .6 | .3 | .3 | .8 | .5 | .95 | .85 |
| **Playful Buddy** | .8 | .9 | .7 | .4 | .95 | .2 | .4 | .85 | .8 | .4 |
| **Quiet Thinker** | .7 | .3 | .5 | .8 | .2 | .7 | .8 | .4 | .5 | .8 |
| **Steady Guide** | .5 | .5 | .9 | .8 | .3 | .2 | .9 | .5 | .6 | .7 |

**[HYP]** These profiles are design starting points; Phase 1 user testing should validate that distinct profiles are *perceivably distinct* to children (e.g., paired-comparison test with 30 s clips).

---

# 12. Behavior Timeline Examples

**[PRINCIPLE]** Every emotion beat is a sequence with a readable spine. Timelines below are baseline for a neutral personality; `B` = blink, `G` = gaze, `S` = smile/squint.

## 12.1 Happy (given example, confirmed as normative)

```
HAPPY
  0 ms      Eyes open (calm baseline)
  80 ms     Smile grows: lower lids curve up, slight squint begins
 250 ms     Blink (happy variant — double blink begins)
 350 ms     Second blink of the double pair, with micro-bounce
 600 ms     Playful glance: gaze flicks 6 px to the side, sparkle
 750 ms     Return gaze to viewer with a small overshoot
 900 ms     Recover: soft settle into the happy loop (bounce ~1.5 s)
```

## 12.2 Calm

```
CALM
   0 ms     Soft eyes (baseline loop: breathing 4.5-5.4 s)
 3000 ms    Soft blink (normal)
 4000 ms    Imperceptible gaze drift (2 px over 4 s)
 8500 ms    Micro-correction re-aim
 12000 ms   Second soft blink; breathing continues throughout
```

## 12.3 Sad

```
SAD
   0 ms     Eyes begin to narrow (anticipation)
 200 ms     Eyes sink: gaze drops 5 px, lids droop
 450 ms     Hold the downcast pose
 1200 ms    Slow droopy blink (soft, 200 ms)
 3500 ms    Gaze drifts further down, then a slow lift-and-re-drop
 6500 ms    Concluding soft blink; returns to the droop loop
```

## 12.4 Thinking

```
THINKING
   0 ms     Squint engages, gaze begins slow scan up-right
  900 ms    Scan point reached; asymmetric lids (left narrower)
 1300 ms    Pause at scan point (contemplative hold)
 2000 ms    Tiny twitch (1.5 px, 2 cycles)
 2400 ms    Contemplative pause continues
 3000 ms    Thinking blink (conclusion)
 3300 ms    Gaze returns center, lids widen
 3800 ms    [Optional] hand-off: begin Speaking (see 12.7)
```

## 12.5 Listening

```
LISTENING
   0 ms     Attention gain: eyes widen slightly, inward lean begins
 200 ms     Lean settled; gaze holds the speaker
 1000 ms    Micro-nod at user phrase end
 2600 ms    Re-center gaze; blink suppressed during hold
 5200 ms    Attentive blink (crisp)
 7000 ms    [When user stops] release lean, return toward calm
```

## 12.6 Speaking

```
SPEAKING
   0 ms     Brighten; gaze away (planning)
 400 ms     Return gaze to listener at phrase end
 1200 ms    Gaze away again (next sentence planning); blink at boundary
 1800 ms    Return + hold; emphasized-word micro-nod
 3600 ms    Turn-taking: gaze at listener, hold 1 s
 4200 ms    Concluding blink; hand turn back to listener
```

## 12.7 Focus

```
FOCUS
   0 ms     Lock-on: quick dip then firm settle (fast 220 ms)
 120 ms     Squint established (openness ~0.58)
 1800 ms    Fixation hold with tremor; micro re-aim at 1.9 s
 4200 ms    [Blink suppressed throughout]
 4300 ms    Deliberate glance-away (release), then blink
 4700 ms    Settle to calm
```

## 12.8 Caring

```
CARING
   0 ms     Slow entry begins (450 ms, softest in set)
 450 ms     Long slow blink #1 (220 ms close, 130 ms hold, slow open)
 3600 ms    Deep breathing sway; gentle down-glance
 5200 ms    Long slow blink #2
 7000 ms    Slow settle; warmth preserved through hold
```

## 12.9 Sleepy

```
SLEEPY
   0 ms     Lids begin to sink (500 ms heavy entry)
 500 ms     Openness at ~0.5, gaze down-drift
 1500 ms    Heavy blink: sticks at 40% closure ~200 ms
 2000 ms    Partial re-open to 0.3; droop sine continues
 3800 ms    Deep breathing; near-zero motion
 5200 ms    Second heavy blink, lids rest near closed
```

## 12.10 Surprised

```
SURPRISED
   0 ms     Expansion freeze begins (fastest attack: 180 ms)
 180 ms     Eyes at full expansion (openness ~1.11), hold 300-500 ms
 450 ms     [Freeze held — no blink]
 600 ms     Release: double blink begins
 700 ms     Second blink; settle from expansion
 1100 ms    Decay to Happy (delight) or Calm (neutral) — see 10.2
```

---

# 13. Future Integration

**[REC]** LES produces **decisions, not rendering**. The behavior layer must remain fully decoupled so each downstream channel can be attached without touching any other. The integration contract below is behavioral — each channel consumes the same *decisions* (emotion, gaze target, blink event, transition, personality state) that this document specifies.

## 13.1 Integration model

```
          ┌──────────────────────────────────────────────┐
          │               LES Behavior Layer             │
          │  decides: emotion · gaze · blink · transition│
          │            personality · timing              │
          └──────────────┬───────────────────────────────┘
                         │ one decision stream
        ┌────────────────┼───────────────────────────────┐
        │                │                               │
   ┌────▼────┐     ┌─────▼─────┐     ┌──────────────────▼──────────┐
   │ Face    │     │  Servo    │     │  Extensions (ROS · Voice ·  │
   │ Engine  │     │Controller │     │  Touch · LLM)               │
   │ (v1.0)  │     │  (future) │     │  subscribe, never modify    │
   └─────────┘     └───────────┘     └─────────────────────────────┘
```

## 13.2 Channel-by-channel

| Channel | Consumes | Rule |
|---|---|---|
| **Face Engine (existing)** | Emotion state, gaze target, blink event, transition spec | The only channel *required* today. Emits state/look/blink requests into the stable engine; the engine's blending remains the executor. Engine stays untouched. |
| **Servo Controller (future)** | Head tilt angle, nod beat, lean direction (Sections 3–8) | Each servo motion is derived from the *same* behavior beat as the face motion so they arrive together. Servo layer owns physics (limits, speeds); LES owns intent. |
| **ROS (future)** | Behavior events, gaze targets, state changes | Publish LES decisions as ROS messages/actions. ROS never calls into LES internals; it consumes events. No engine knowledge crosses this boundary. |
| **Voice (future)** | Utterance start/end, phrase boundaries, emphasis beats | Speaking state (Section 7) aligns gaze/blink with TTS phrase events. Voice is a *producer* of phrase events and a *consumer* of the same timing; neither side owns the other. |
| **Touch (future)** | Touch events → reaction triggers (Surprised, Happy, Embarrassed) | Touch becomes another *input* to the arbitration hierarchy (10.4). Reactions follow the same transition rules. |
| **LLM (future)** | Utterance requests, intent, emotion labels | The LLM produces content and coarse emotion; LES converts emotion to *timing* and *expression* via this spec. The LLM never dictates servo positions or pixel parameters. |

## 13.3 Invariants (must hold in every future integration)

1. **The engine is never modified, wrapped, or bypassed** for existing features.
2. **LES never renders** — every output is a decision (state, gaze, blink, transition, servo target).
3. **Every channel is additive** — adding ROS, voice, or touch changes nothing in the face channel.
4. **Timing lives in one place** — this spec's baseline timings, scaled by personality (Section 11), are the single source of truth for all channels.
5. **Backward compatibility** — with no channels attached, the face behaves exactly as the v1.0 engine does today.

---

# Appendix A — Research Provenance

## A.1 Product observations (LivingAI Aibi)

- Official product page and demo materials: gaze darting to locate users, head swivel toward voice (3-microphone array), idle spinning on desk, facial recognition reactions, touch-triggered animations, sleep ritual (green eyes slowly closing, red hue shift, purring sound). — living.ai/aibi; independent reviews (mia-cat.com, virtual-paws.com); LivingAI community forums (firmware/interaction logs).
- Extended-gaze check-in: 2+ s eye contact prompts a verbal check-in **[OBSERVED, HYP for generalization]**.

## A.2 HRI & psychophysical research

- Mutual gaze 3–5 s typical; >10 s uncomfortable. — Andrist et al., *Conversational Gaze Aversion for Humanlike Robots*, HRI 2014.
- Speaker looks at listener ~40%; listener at speaker ~75%. — Andrist et al. (above); Admoni & Scassellati, *Social Eye Gaze in Human-Robot Interaction: A Review*, J. HRI 2017.
- Blink: 150–400 ms total, ~50 ms full closure; 15–20 blinks/min resting; closing faster than opening; 70–90% complete; inhibition under focus (5–10/min). — Nyström et al., *What is a blink?*, Behavior Research Methods 2024; Stern et al., *The endogenous eye blink*, Psychophysiology 1984.
- Saccades 30–100 ms, 3–4 per second during exploration. — eye-tracking literature (Stern et al.; standard saccade references).
- Gaze-contingent mutual gaze improves engagement/trust. — Kompatsiari et al.; Xu et al., *See You See Me*, ACM TiiS 2016.
- Forced mutual gaze impairs speech fluency. — Andrist et al. 2014.

## A.3 Companion-robot design literature

- User-centered idle tiers for social robots in the home. — Arias, Jeong, Park, Breazeal (MIT Personal Robots Group).
- Disney 12 principles applied to robots: Anki Vector's animators (Mooly Segal, Carlos Baena) — anticipation, follow-through, squash/stretch in hardware; Vector's ~981 micro-animations in decision trees. — press/interviews (Medium, Kickstarter features).
- Coordinated multimodal expression (Jibo): body motors + screen + light + voice as one voice (SOUL framework). — Robohub / MIT Media Lab documentation.
- Semantic-free sound as auditory micro-motion. — Robinson, Bown, Velonaki, *Designing Sound for Social Robots*, Int. J. Social Robotics.

## A.4 Animation principles

- 12 principles: Lasseter, *Principles of Traditional Animation Applied to 3D Computer Animation*, SIGGRAPH 1987. Timing conventions (anticipation ≈ ¼–½ of main action; overshoot 5–12%; hold readability) follow classic animation practice and animator references.

---

# Appendix B — Current Engine Baseline (for implementers)

The v1.0 engine (unchanged) already implements many of this spec's parameters. LES should target these values as the *execution baseline* and treat the spec's tables as the *behavioral target*.

| Parameter | Current engine value | Spec target |
|---|---|---|
| State transition blend | 350 ms default | 250–500 ms per rule (10.2) |
| Blink interval | 3.0–5.0 s random | 3.0–5.0 s (idle) / per-emotion bands (Sec 3) |
| Blink duration | 180 ms | 180 ms (normal), per lexicon (Sec 9) |
| Double-blink gap | 120 ms | 120 ms (9.2) |
| Slow-blink multiplier | 2.5× | Long blink ≈ 2.5–3× (9.7) |
| Half-blink ratio | 0.5 | Embarrassed ≈ 0.5–0.75 (9.4) |
| Blink-type chances | double 12%, slow 5%, half 8% | weighted per emotion (Sec 3 tables) |
| Breathing period | ~5.4 s (motion cfg); personality-derived 4.5 s+ | 4–6 s (P7) |
| Personality axes | energy, warmth, attention, calmness, amplitude, blink_tendency | superset: 10 LES traits map onto these (11.2) |
| Micro-motion layers | idle noise, drift, bounce, scan, breathing, micro-correction all exist | layer model in 2.3 matches existing primitives |
| Emotion states | calm, happy, sad, thinking, listening, speaking, focus, caring, sleepy, surprised | identical 10-state set (Section 3) |

**Implementation note:** the engine's existing architecture (declarative state personality, motion-primitive adaptors, procedural blink controller, eased transitions) already satisfies most of this spec's *physics*. The remaining work is behavioral: per-emotion timing policies, the blink lexicon, attention/curiosity sequences, the arbitration hierarchy, and personality scaling — i.e., the decision layer LES is designed to own.

---

*End of specification. Version 1.0 — proposed for Phase 1 review and validation.*
