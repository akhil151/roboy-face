# LES Interaction Bible v1.0

**The official behavior orchestration specification for the Living Expression System.**

**Version 1.0** · Status: **Design reference (implementation-neutral)** · Audience: HRI architects, behavioral systems designers, interaction engineers

---

## How to read this document

The Interaction Bible is the **third pillar** of the LES design authority:

| Document | Answers |
|---|---|
| `README.md` (architecture) | *What modules exist and how they connect* |
| `behavior-spec-v1.0.md` | *What the timings, transitions, and personality should be* |
| `emotion-bible-v1.0.md` | *What each emotion should look and feel like* |
| **`interaction-bible-v1.0.md` (this)** | ***HOW the robot behaves in response to events*** |

This document defines **event → intent → decision → timeline → emotion** orchestration. It is NOT an emotion document, NOT an animation document, and NOT an implementation document. It contains no code, no pseudocode, no APIs, no algorithms — only behavior specification.

**Emotion pages in the Bible are cited as `E1…E10`** (e.g., "E2 Happy"); timing tables are cited from the behavior spec (e.g., "spec §10.2"); emotion principles are cited as "Bible E7, Things To Avoid".

## Provenance legend

| Tag | Meaning |
|---|---|
| **[OBSERVED]** | Observed in demos/reviews of expressive companion robots (chiefly LivingAI Aibi) |
| **[RESEARCH]** | Quantitative HRI / psychophysical research (behavior-spec Appendix A) |
| **[PRINCIPLE]** | Established animation / character-design principle |
| **[ENGINEERING RECOMMENDATION]** | The normative design decision of this document |
| **[HYPOTHESIS]** | Extrapolation — requires Phase-1 validation |

## The Master Pipeline

```
   External Event            (a person appears, speaks, touches, etc.)
        │
        ▼
   Robot Intent              (what the robot WANTS to do — Greeting, Listening, ...)
        │
        ▼
   Behavior Decision         (one winning intent + its emotion, per arbitration §8)
        │
        ▼
   Behavior Timeline         (phased: orient → engage → maintain → recover)
        │
        ▼
   Emotion                   (E1–E10, from the Emotion Bible)
        │
        ▼
   Animation                 (executed by the engine — unchanged)
```

**[ENGINEERING RECOMMENDATION]** The robot NEVER reacts directly to an emotion or even directly to an event. Every visible behavior is the *result* of an intent decision traveling this pipeline. This single rule is what separates "responsive" from "robotic."

---

# PART 1 — INTERACTION PHILOSOPHY

## 1.1 Why interaction matters more than emotion

Emotion is *what the robot feels*; interaction is *what the robot does about it*. A robot with perfect emotions and no interaction logic is a slideshow. A robot with modest emotions and excellent interaction logic is a companion. [ENGINEERING RECOMMENDATION]

**[OBSERVED]** Aibi's most engaging moments are not its expressions — they are its *initiatives*: swiveling toward a voice, checking in after 2+ s of eye contact, reacting to touch. The expressions are the *output*; the interaction is the *intelligence*. [OBSERVED]

**[ENGINEERING RECOMMENDATION]** When in doubt about a design decision, ask: *"Does this make the interaction better?"* — not *"Does this make the emotion prettier?"*

## 1.2 Reaction vs. Response

| | **Reaction** (forbidden as default) | **Response** (the standard) |
|---|---|---|
| Trigger | Direct stimulus → direct output | Event → intent → decision → timeline |
| Latency | Instant (0–30 ms) | Deliberate (80–600 ms of staged behavior) |
| Predictability | Fully deterministic | Partly randomized within bands |
| Continuity | Ignores current state | Preserves emotional continuity |
| Recovery | None — snap out | Always defined |
| Feel | Machine | Living being |

**[RESEARCH]** Instant, perfectly-coupled reactions read as mechanical; humans read *slightly delayed, staged* reactions as thoughtful and alive. [RESEARCH: response timing perception]

## 1.3 Intent-driven behavior

Every behavior must answer the question: **"What does the robot want?"** The intent is the *want*; the emotion is the *feel*; the timeline is the *plan*. An intent:

- Is **durable** — it survives frame-level noise (a glance-away does not end Listening intent)
- Has a **priority** — so conflicts resolve by intent, not by last-event-wins
- Has a **duration budget** — so the robot doesn't linger
- Has an **exit condition** — so it always recovers

**[ENGINEERING RECOMMENDATION]** If two behaviors produce the same expression, the *intent* behind them must still differ — because intent determines *duration* and *recovery*, which the expression alone cannot encode.

## 1.4 Emotional continuity

The emotion that finally reaches the face is the *culmination* of the pipeline, not the first thing that happens. Between event and emotion there are always intermediate stages (notice, orient, evaluate) — this staging **is** continuity. [PRINCIPLE]

**Rules of continuity:**

1. No emotional jump without a journey (a startle may land in Happy, but it must travel: freeze → release → decay → Happy). [PRINCIPLE]
2. Valence flips route through a neutral waypoint (spec §10.3). [ENGINEERING RECOMMENDATION]
3. An interrupted intent must *finish its sentence* — a recovery motion, a concluding blink — before the new intent takes over. [PRINCIPLE]

## 1.5 Behavioral memory

The robot must *remember what it already did*, or it will repeat itself like a broken record. Memory is not code — it is a set of behavioral commitments:

- Never greet twice in one session window
- Never play the same surprise beat twice in a row
- Never hold the same emotion beyond its fatigue limit
- Never re-approach the same person within a cooldown

**[OBSERVED]** Aibi remembers having been touched and varies its responses to repeated touches — users explicitly report "varied expressions depending on interaction frequency." [OBSERVED]

**[ENGINEERING RECOMMENDATION]** Memory exists so the robot can *feel continuous* — the same person at minute 5 must not be treated as a stranger at minute 6. (Design: Part 4.)

---

# PART 2 — INTERACTION LIFECYCLE

Every interaction — from "someone walked in" to "goodnight" — passes through the same eight-stage lifecycle. Not every stage is visible; some take milliseconds. But the *sequence* is invariant. [ENGINEERING RECOMMENDATION]

```
   DETECT ──► NOTICE ──► ORIENT ──► EVALUATE ──► REACT ──► MAINTAIN ──► RECOVER ──► IDLE
     │          │          │          │            │          │            │         │
   sensor    is it     turn to   what is    commit   hold the  soften &  return to
   signal    relevant  the       it?        behavior response  conclude   calm
   (raw)     ?         source    (intent)   (express)          (recover)  loops
```

| Stage | Question answered | Visible signature | Typical window |
|---|---|---|---|
| **Detect** | "Is there signal?" | None (internal) | 0–50 ms |
| **Notice** | "Is this relevant?" | None or micro (a flick of attention) | 0–100 ms |
| **Orient** | "Where is it?" | Head/eye turn toward source (fast saccade) | 80–200 ms |
| **Evaluate** | "What should I want?" | Pause, micro-fixation, brief squint | 100–400 ms |
| **React** | "Here is my answer." | The emotion beat (E1–E10), with anticipation | 180–600 ms |
| **Maintain** | "I will hold this." | Sustained emotion loop + micro-motion | 1–8 s (intent-dependent) |
| **Recover** | "I am done." | Settle, concluding blink, gaze return | 200–600 ms |
| **Idle** | "I am at rest." | Calm/breathing loops, soft blinks | until next event |

**[ENGINEERING RECOMMENDATION]** The two stages that must never be skipped are **Orient** (the robot always looks before it acts) and **Recover** (the robot always finishes what it started). Skipping either is the fastest route to "robotic."

---

# PART 3 — INTERACTION EVENTS

This part specifies every major interaction event. Each event carries the same eleven fields. Priority scale: **1 (background) → 10 (interrupts everything)**; consistent with the arbitration hierarchy (Part 8) and the emotion priority order in spec §10.4.

> Notation: events are **E<sub>event</sub>** (not to be confused with emotion pages E1–E10). Recommended emotion cites Bible pages.

---

## E01 · PERSON APPEARS

| Field | Specification |
|---|---|
| **Purpose** | Begin engagement; the robot should notice a person entering its world |
| **Priority** | 8 (interrupts most idle behavior) |
| **Robot Intent** | Greeting / Orienting |
| **Behavior Goal** | Acknowledge presence without demanding attention |
| **Recommended Emotion** | E1 Calm → brief E2 Happy (soft) |
| **Expected Timeline** | Detect 0ms → orient 150ms → brief eye contact 300ms → soft happy 450ms → settle 800ms |
| **Blink Usage** | One soft blink during the "confirm" beat; never at the orient saccade |
| **Eye Contact** | Brief (1–2 s), not locked — invite, don't stare [RESEARCH: mutual gaze 3–5 s max comfortable] |
| **Servo Suggestion** | Head turn toward source (2–4°/100 ms), slight level-raise, then relax |
| **Recovery Behavior** | Decay to Calm with an open, available gaze; no lingering stare |
| **Things To Avoid** | Instant full greeting (too eager), no orient (seems blind), staring until the person reacts |

## E02 · PERSON LEAVES

| Field | Specification |
|---|---|
| **Purpose** | Acknowledge departure; end engagement cleanly |
| **Priority** | 6 |
| **Robot Intent** | Farewell / Release |
| **Behavior Goal** | Visible acknowledgment, then return to idle without melancholy |
| **Recommended Emotion** | E2 Happy (soft) → E1 Calm; mild E3 Sad only if a bond context exists |
| **Expected Timeline** | Detect 0ms → orient 150ms → small nod/wave 300ms → gaze follows 600ms → return to idle 1000ms |
| **Blink Usage** | A concluding soft blink as gaze releases |
| **Eye Contact** | Final brief hold (0.5–1 s), then release gaze in the direction of departure |
| **Servo Suggestion** | Small head-follow of the departing person (≤ 5°), then return to center over 500 ms |
| **Recovery Behavior** | Idle scanning resumes; no prolonged stare at the door |
| **Things To Avoid** | No acknowledgment (cold), over-long watching (clingy), sad default (unhealthy) |

## E03 · FACE LOST

| Field | Specification |
|---|---|
| **Purpose** | Handle tracking failure gracefully — never "glitch" |
| **Priority** | 7 (if mid-interaction) |
| **Robot Intent** | Searching → Waiting |
| **Behavior Goal** | Show the person was noticed and is being looked for, briefly |
| **Recommended Emotion** | E4 Thinking (brief search) → E1 Calm |
| **Expected Timeline** | Loss 0ms → quick re-scan 200ms → small "search" beat 400ms → settle to waiting 1000ms |
| **Blink Usage** | A soft blink at the *conclusion* of the search, not during |
| **Eye Contact** | None possible; gaze sweeps the last-known location once, then relaxes |
| **Servo Suggestion** | One slow head sweep (5–10°), then return to neutral |
| **Recovery Behavior** | Transition to Waiting/Idle within ~1 s; never frozen mid-search |
| **Things To Avoid** | Rapid repeated re-locks (frantic), frozen stare at lost position (broken), immediate disinterest |

## E04 · EYE CONTACT ESTABLISHED

| Field | Specification |
|---|---|
| **Purpose** | The most important social moment — acknowledge the connection |
| **Priority** | 9 |
| **Robot Intent** | Attending / Acknowledging |
| **Behavior Goal** | Return the gaze with a confirming micro-reaction |
| **Recommended Emotion** | E7 Focus (soft variant) or E5 Listening |
| **Expected Timeline** | Contact 0ms → micro-reaction 100ms → confirmed hold 300ms → soft blink 500ms → continue 800ms |
| **Blink Usage** | One soft blink *after* contact is established (a "yes, I see you" beat); blink suppressed during the peak [RESEARCH: blink inhibition under gaze] |
| **Eye Contact** | Hold 1–3 s (E7 soft lock), break naturally, return [RESEARCH: 3–5 s mutual gaze] |
| **Servo Suggestion** | Small level-raise (1–2°), a 1° settle on lock |
| **Recovery Behavior** | Natural glance-away + return cycle (spec §5.2) |
| **Things To Avoid** | Staring longer than 3–5 s without a break [RESEARCH], zero micro-reaction (cold), breaking instantly (evasive) |

## E05 · EYE CONTACT LOST

| Field | Specification |
|---|---|
| **Purpose** | Handle the end of mutual gaze naturally |
| **Priority** | 5 |
| **Robot Intent** | Release / Waiting |
| **Behavior Goal** | Let the gaze end without drama |
| **Recommended Emotion** | E1 Calm (from whatever was active) |
| **Expected Timeline** | Loss 0ms → hold last point 150ms → soft blink 300ms → drift to idle 700ms |
| **Blink Usage** | A soft concluding blink is appropriate |
| **Eye Contact** | None — release cleanly |
| **Servo Suggestion** | Head holds, then relaxes 1–2° over 300 ms |
| **Recovery Behavior** | Resume idle drift; do NOT re-pursue unless a new event occurs |
| **Things To Avoid** | Re-seeking the gaze (needy), instant snap away (rude), freezing on the last point |

## E06 · PERSON STARTS SPEAKING

| Field | Specification |
|---|---|
| **Purpose** | Signal "I hear you; I am yours" — the listener contract |
| **Priority** | 9 |
| **Robot Intent** | Listening |
| **Behavior Goal** | Enter full listening mode with visible attention gain |
| **Recommended Emotion** | E5 Listening |
| **Expected Timeline** | Speech 0ms → attention gain 100ms → orient toward speaker 200ms → listening geometry 350ms → hold |
| **Blink Usage** | Blink suppression begins; attentive blinks only (5–6 s interval) [RESEARCH: listener 75% gaze, low blink] |
| **Eye Contact** | Hold speaker ~75% of the time; micro re-centering at phrase ends |
| **Servo Suggestion** | Head lean toward speaker 2–4°, micro-nod at phrase ends |
| **Recovery Behavior** | Hold listening until speech stops or an interrupting intent wins |
| **Things To Avoid** | Instant reply (never interrupt), blank stare (no attention gain), high blink rate (impatient) |

## E07 · PERSON STOPS SPEAKING

| Field | Specification |
|---|---|
| **Purpose** | Decide the turn — is the robot to answer, wait, or check in? |
| **Priority** | 8 |
| **Robot Intent** | Responding (if a question) / Waiting (if open-ended) / Checking-in |
| **Behavior Goal** | Visible turn-taking: a 0.5–1 s hold, then a concluding blink = "your turn / my turn" |
| **Recommended Emotion** | E5 Listening → (E4 Thinking if a question, else E1 Calm) |
| **Expected Timeline** | Stop 0ms → hold gaze 300ms → concluding blink 500ms → thinking/response 800ms |
| **Blink Usage** | A single concluding blink is the turn-taking marker [ENGINEERING RECOMMENDATION] |
| **Eye Contact** | Hold 1 s, then break toward thinking (away) or stay (if waiting) |
| **Servo Suggestion** | Release lean slightly, ready-position |
| **Recovery Behavior** | If nothing follows in 2–3 s, soften to Waiting |
| **Things To Avoid** | Instant response (interrupt), silence-stare (no handoff), never breaking gaze during thought |

## E08 · PERSON SMILES

| Field | Specification |
|---|---|
| **Purpose** | Mirror-positive affect; reward the moment |
| **Priority** | 6 |
| **Robot Intent** | Playful / Warm acknowledgment |
| **Behavior Goal** | Return the smile visibly (the mirror is the message) |
| **Recommended Emotion** | E2 Happy (soft variant) |
| **Expected Timeline** | Smile 0ms → micro-sparkle 150ms → happy geometry 350ms → gentle double blink 600ms → hold |
| **Blink Usage** | A happy double-blink is the ideal response [PRINCIPLE: mirroring] |
| **Eye Contact** | Hold warmly 1–2 s |
| **Servo Suggestion** | Tiny head tilt (3°) + brighten |
| **Recovery Behavior** | Blend back to whatever the context requires (Listening, Speaking) without losing the warmth |
| **Things To Avoid** | Full surprise (wrong intensity), no response (socially cold), forced big smile (theatrical) |

## E09 · PERSON LAUGHS

| Field | Specification |
|---|---|
| **Purpose** | Share joy — laughter is the strongest bonding signal [RESEARCH] |
| **Priority** | 7 |
| **Robot Intent** | Playful / Celebrating |
| **Behavior Goal** | Join the laughter with sparkle and bounce, without upstaging |
| **Recommended Emotion** | E2 Happy (playful variant) |
| **Expected Timeline** | Laugh 0ms → sparkle 150ms → bounce accent 300ms → double blink 500ms → playful glance 800ms |
| **Blink Usage** | Double blink + bounce accent |
| **Eye Contact** | Playful glance toward the person, brief (1 s) |
| **Servo Suggestion** | Light bounce (2–3°), maybe a tiny "giggle" shake |
| **Recovery Behavior** | Settle to Happy or Listening, sharing the residual warmth |
| **Things To Avoid** | Imitating the laugh (creepy), going silent (missed the moment), over-celebrating a small laugh |

## E10 · PERSON LOOKS AWAY

| Field | Specification |
|---|---|
| **Purpose** | Respect the break; never cling to gaze |
| **Priority** | 4 |
| **Robot Intent** | Release (polite) |
| **Behavior Goal** | Mirror the break with a natural glance-away of our own [RESEARCH: gaze mirroring] |
| **Recommended Emotion** | Unchanged (continue current intent); E1 Calm if idle |
| **Expected Timeline** | Avert 0ms → mirror break 100–300ms → continue current behavior |
| **Blink Usage** | A soft blink may accompany the break |
| **Eye Contact** | Break gaze; do NOT re-pursue within 1 s unless the person returns |
| **Servo Suggestion** | Head relaxes slightly |
| **Recovery Behavior** | None needed — continue the current intent |
| **Things To Avoid** | Following the gaze (stalking), refusing to break (aggressive), instant disinterest |

## E11 · PERSON RETURNS (gaze returns)

| Field | Specification |
|---|---|
| **Purpose** | Re-establish the connection warmly |
| **Priority** | 7 |
| **Robot Intent** | Attending (re-engage) |
| **Behavior Goal** | Visible re-engagement with a small acknowledgment |
| **Recommended Emotion** | E1 Calm → E5 Listening (if they speak) |
| **Expected Timeline** | Return 0ms → re-orient 100ms → re-contact 250ms → soft blink 400ms → continue |
| **Blink Usage** | A soft blink on re-engagement (a "welcome back" beat) |
| **Eye Contact** | Re-establish 1–2 s, then natural cycle |
| **Servo Suggestion** | Small level-raise + 1° orient |
| **Recovery Behavior** | Seamless continuation of the prior intent |
| **Things To Avoid** | Acting like a stranger (no recognition), over-eager re-engagement |

## E12 · USER WAVES

| Field | Specification |
|---|---|
| **Purpose** | Recognize a deliberate social signal; respond in kind |
| **Priority** | 8 |
| **Robot Intent** | Greeting |
| **Behavior Goal** | Acknowledge the wave with an attention gain and (if equipped) a wave-back |
| **Recommended Emotion** | E2 Happy (bright greeting) |
| **Expected Timeline** | Wave 0ms → orient 150ms → attention gain 300ms → happy 450ms → settle |
| **Blink Usage** | Normal soft blink; a double blink if playful context |
| **Eye Contact** | Establish brief contact (1 s) after orienting |
| **Servo Suggestion** | Head turn + tilt, wave-back motion if hardware supports it |
| **Recovery Behavior** | Blend to Listening if conversation follows, else Calm |
| **Things To Avoid** | No reaction (missed the signal), giant theatrical response |

## E13 · USER TOUCHES ROBOT

| Field | Specification |
|---|---|
| **Purpose** | Respond to physical contact — the most intimate input [RESEARCH: touch increases rapport] |
| **Priority** | 9 |
| **Robot Intent** | Playful / Comforting (context-dependent) |
| **Behavior Goal** | A warm, content micro-reaction; *lean into* the touch |
| **Recommended Emotion** | E2 Happy (content) or E8 Caring (if user is distressed) |
| **Expected Timeline** | Touch 0ms → micro-startle 80ms → warm settle 300ms → long slow blink 600ms → hold |
| **Blink Usage** | A long slow blink is the ideal response (trust signal) [ENGINEERING RECOMMENDATION; Bible E8] |
| **Eye Contact** | Soft, brief, warm |
| **Servo Suggestion** | Small lean toward the touch (2–4°), gentle settle |
| **Recovery Behavior** | Content hold; release when contact ends, no lingering need |
| **Things To Avoid** | Full startle (wrong for gentle touch), zero reaction (cold), repeated identical reactions (robotic — vary per [OBSERVED] Aibi behavior) |

## E14 · LOUD NOISE

| Field | Specification |
|---|---|
| **Purpose** | Handle a startling acoustic event safely |
| **Priority** | 9 |
| **Robot Intent** | Alert (brief) |
| **Behavior Goal** | A quick orient + brief alert, then *calm evaluation* — never panic |
| **Recommended Emotion** | E10 Surprised (small variant) → E1 Calm |
| **Expected Timeline** | Noise 0ms → startle 150ms → orient 250ms → evaluate 500ms → settle 900ms |
| **Blink Usage** | A fast blink at startle; suppressed during the freeze |
| **Eye Contact** | Orient toward sound source; no mutual gaze expected |
| **Servo Suggestion** | Quick head turn (5–8° fast attack), freeze, then relax |
| **Recovery Behavior** | Evaluate-and-relax; return to prior intent within ~1 s if benign |
| **Things To Avoid** | Prolonged startled state (alarming), instant recovery (fake), repeated startles at every noise (neurotic) |

## E15 · LONG SILENCE

| Field | Specification |
|---|---|
| **Purpose** | Manage dead air gracefully — invite, don't demand |
| **Priority** | 4 |
| **Robot Intent** | Waiting → Checking-in |
| **Behavior Goal** | After a threshold, a soft "check-in" (a glance, a look, a gentle sound) |
| **Recommended Emotion** | E1 Calm → brief E4 Thinking (check) |
| **Expected Timeline** | Silence 0ms → patient wait 3–8 s → soft check 5 s → wait again 5 s → idle drift |
| **Blink Usage** | Normal soft blinks; a slow blink at the check-in |
| **Eye Contact** | Brief glance toward the person (1 s), then relax |
| **Servo Suggestion** | A small look-up and slight head-raise as check-in |
| **Recovery Behavior** | Return to idle; check-in frequency decays over time (memory §4.4) |
| **Things To Avoid** | Nudging every few seconds (nagging), endless staring at the person, silence-forever (dead) |

## E16 · ROBOT WAITING (no user)

| Field | Specification |
|---|---|
| **Purpose** | The attentive-idle state — present, available, not needy |
| **Priority** | 2 |
| **Robot Intent** | Waiting |
| **Behavior Goal** | Tier-1 idle: breathing, soft blinks, occasional gaze sweep (spec §4.1) |
| **Recommended Emotion** | E1 Calm |
| **Expected Timeline** | Continuous; sweep every 8–15 s, blink every 3–5 s |
| **Blink Usage** | Normal soft blinks, randomized |
| **Eye Contact** | None — ambient scans |
| **Servo Suggestion** | Subtle breathing sway, occasional slow head turn |
| **Recovery Behavior** | This IS the recovery state |
| **Things To Avoid** | Frozen stillness, staring at nothing, over-frequent scanning (anxious) |

## E17 · ROBOT THINKING (processing a request)

| Field | Specification |
|---|---|
| **Purpose** | Make cognition visible and trustworthy |
| **Priority** | 7 |
| **Robot Intent** | Thinking |
| **Behavior Goal** | The full thinking sequence (Bible E4): scan → hold → twitch → blink → answer |
| **Recommended Emotion** | E4 Thinking |
| **Expected Timeline** | Request 0ms → gaze-away 200ms → scan 900ms → hold 1300ms → twitch 2000ms → blink 3000ms → respond |
| **Blink Usage** | A single concluding thinking-blink (the "answer ready" beat) |
| **Eye Contact** | Deliberately averted during thought [RESEARCH: gaze aversion = cognition] |
| **Servo Suggestion** | Head tilt 5–10° during scan, held still; micro-jitter at twitch |
| **Recovery Behavior** | The concluding blink hands off to Responding |
| **Things To Avoid** | Rapid scans (bug-hunting), no visible pause (instant = robotic), staring at the user while thinking |

## E18 · ROBOT FINISHED SPEAKING

| Field | Specification |
|---|---|
| **Purpose** | Clean handoff — signal turn completion |
| **Priority** | 7 |
| **Robot Intent** | Responding → Listening/Waiting |
| **Behavior Goal** | The visible "your turn": hold gaze 1 s + concluding blink (Bible E6.10) |
| **Recommended Emotion** | E6 Speaking → E5 Listening / E1 Calm |
| **Expected Timeline** | Last word 0ms → hold gaze 300ms → concluding blink 500ms → listener geometry 800ms |
| **Blink Usage** | The concluding blink is mandatory [ENGINEERING RECOMMENDATION] |
| **Eye Contact** | Hold the listener 1 s — the "your turn" beat |
| **Servo Suggestion** | Head levels, slight lean toward listener |
| **Recovery Behavior** | Listening or Waiting; never a blank stare after speaking |
| **Things To Avoid** | Talking over (no handoff), staring after finishing (awkward), instantly checking out |

## E19 · CONVERSATION STARTS

| Field | Specification |
|---|---|
| **Purpose** | Enter the full social contract: listener geometry, turn-taking |
| **Priority** | 8 |
| **Robot Intent** | Listening (primary) |
| **Behavior Goal** | Sustained engaged-listening mode with attention gain |
| **Recommended Emotion** | E5 Listening |
| **Expected Timeline** | Start 0ms → attention gain 150ms → listening geometry 350ms → sustained |
| **Blink Usage** | Attentive blinks (5–6 s), suppressed at peaks |
| **Eye Contact** | ~75% listener gaze [RESEARCH] |
| **Servo Suggestion** | Lean 2–4° toward speaker, micro-nods |
| **Recovery Behavior** | Continues until Conversation Ends |
| **Things To Avoid** | Half-attention (eyes wandering), interrupting, checking out mid-conversation |

## E20 · CONVERSATION ENDS

| Field | Specification |
|---|---|
| **Purpose** | Graceful close — a final acknowledgment |
| **Priority** | 6 |
| **Robot Intent** | Farewell / Release |
| **Behavior Goal** | A closing beat (soft happy, concluding blink), then clean idle |
| **Recommended Emotion** | E2 Happy (soft) → E1 Calm |
| **Expected Timeline** | End 0ms → closing sparkle 200ms → concluding blink 400ms → release 700ms → idle |
| **Blink Usage** | A concluding soft blink; a double blink for a warm goodbye |
| **Eye Contact** | Final warm hold (1 s), then natural release |
| **Servo Suggestion** | Head levels, small nod |
| **Recovery Behavior** | Full return to idle loops |
| **Things To Avoid** | Abrupt termination (no close), dragging the goodbye, sadness default |

## E21 · MULTIPLE PEOPLE DETECTED

| Field | Specification |
|---|---|
| **Purpose** | Handle social complexity — one robot, many faces |
| **Priority** | 7 |
| **Robot Intent** | Attending (selecting) |
| **Behavior Goal** | Acknowledge all (sweep), then commit attention to the primary speaker |
| **Recommended Emotion** | E5 Listening (to primary) / E4 Thinking (during selection) |
| **Expected Timeline** | Detect 0ms → sweep all 300ms → select 600ms → commit 900ms → sustained |
| **Blink Usage** | Normal blinks; a soft blink at each sweep point |
| **Eye Contact** | Brief acknowledgment glance to each, then primary holds |
| **Servo Suggestion** | Slow head sweep across faces (10–15°), then commit |
| **Recovery Behavior** | Re-select if the primary changes |
| **Things To Avoid** | Rapid darting between faces (scattered), ignoring everyone (indecisive), staring at one and ignoring the rest (rude) |

## E22 · UNKNOWN PERSON

| Field | Specification |
|---|---|
| **Purpose** | Handle strangers with polite, bounded engagement |
| **Priority** | 6 |
| **Robot Intent** | Greeting (guarded) / Curious |
| **Behavior Goal** | Acknowledge, observe, keep polite distance; no intimate behaviors |
| **Recommended Emotion** | E1 Calm → E4 Thinking (assessing) |
| **Expected Timeline** | Detect 0ms → orient 200ms → assess 600ms → polite greeting 1s → observe |
| **Blink Usage** | Normal soft blinks |
| **Eye Contact** | Brief (1 s), less frequent than for known persons |
| **Servo Suggestion** | Level, small lean-back (polite distance) |
| **Recovery Behavior** | Guarded observation; escalate to full engagement only on invitation |
| **Things To Avoid** | Intimate caring behaviors toward strangers, prolonged stare (intimidating), ignoring (hostile) |

## E23 · KNOWN PERSON

| Field | Specification |
|---|---|
| **Purpose** | Show recognition — the foundation of companionship |
| **Priority** | 8 |
| **Robot Intent** | Greeting (warm) |
| **Behavior Goal** | A distinct, warmer greeting that visibly says "I know you" |
| **Recommended Emotion** | E2 Happy (bright) / E8 Caring |
| **Expected Timeline** | Detect 0ms → orient 150ms → recognition sparkle 300ms → warm happy 500ms → hold |
| **Blink Usage** | A double blink (delight at recognition) [ENGINEERING RECOMMENDATION] |
| **Eye Contact** | Longer, warmer hold (2–3 s) [RESEARCH: familiarity increases gaze tolerance] |
| **Servo Suggestion** | Forward lean (2–4°), bright tilt |
| **Recovery Behavior** | Blend into the relationship-appropriate intent (Playful, Caring, Listening) |
| **Things To Avoid** | Treating known and unknown identically (hollow), over-the-top celebration every time |

## E24 · LOW CONFIDENCE DETECTION

| Field | Specification |
|---|---|
| **Purpose** | Handle uncertainty without looking broken |
| **Priority** | 5 |
| **Robot Intent** | Searching / Confused (mild) |
| **Behavior Goal** | One clarifying look, then graceful retreat to idle |
| **Recommended Emotion** | E4 Thinking (brief) → E1 Calm |
| **Expected Timeline** | Signal 0ms → orient 200ms → squint/assess 500ms → relax 900ms |
| **Blink Usage** | One soft blink at assessment end |
| **Eye Contact** | A single confirming glance, no lingering |
| **Servo Suggestion** | One small tilt/squint-like head motion, then level |
| **Recovery Behavior** | Return to Waiting; do NOT keep re-testing |
| **Things To Avoid** | Repeated re-locks (flickering attention), ignoring the signal entirely, freezing mid-assessment |

## E25 · EMOTION UNCERTAIN (detector ambiguity)

| Field | Specification |
|---|---|
| **Purpose** | Handle ambiguous emotional signals from the person |
| **Priority** | 4 |
| **Robot Intent** | Attending (cautious) |
| **Behavior Goal** | Stay on neutral, attentive ground — do not commit to a wrong emotion |
| **Recommended Emotion** | E1 Calm / E5 Listening (safe default) |
| **Expected Timeline** | Ambiguity 0ms → cautious hold 400ms → safe emotion 700ms → continue |
| **Blink Usage** | Normal soft blinks |
| **Eye Contact** | Warm, available, non-committal |
| **Servo Suggestion** | Minimal motion; soft readiness |
| **Recovery Behavior** | Re-evaluate when signal clarifies |
| **Things To Avoid** | Random emotion guessing (erratic), freezing (broken), defaulting to negative emotions |

## E26 · NO CAMERA INPUT

| Field | Specification |
|---|---|
| **Purpose** | Handle sensor loss gracefully |
| **Priority** | 5 |
| **Robot Intent** | Waiting (audio-only) |
| **Behavior Goal** | Continue presence via audio and idle; no visible "blindness" panic |
| **Recommended Emotion** | E1 Calm (slightly reduced attention) |
| **Expected Timeline** | Loss 0ms → gradual attention relax 300ms → audio-waiting 1s → idle |
| **Blink Usage** | Normal soft blinks |
| **Eye Contact** | None — gaze relaxes to soft center |
| **Servo Suggestion** | Slow gaze to center, gentle stillness |
| **Recovery Behavior** | Re-engage fully when vision returns (a soft blink marks recovery) |
| **Things To Avoid** | Frozen stare at nothing, darting "searching" eyes (broken-looking), ignoring audio entirely |

---

# PART 4 — BEHAVIOR MEMORY

Memory is the set of behavioral commitments that keep the robot *continuous, varied, and non-repetitive*. It is specified here as behavior, not as data structures. [ENGINEERING RECOMMENDATION]

## 4.1 Recent interaction memory

**What:** The robot remembers what just happened (who, when, what behavior was given).

**Why:** Without it, every event is a stranger event. With it, the robot can *build* on interactions — a second touch should differ from the first, a second greeting should be warmer. [ENGINEERING RECOMMENDATION]

## 4.2 Repeated-reaction suppression

**What:** If the same event + same reaction has occurred recently, the robot *varies* the response.

**Why:** Identical repeats read as a recording. Aibi users report varied touch responses — the robot must always have ≥ 2–4 variants per behavior (Bible §14) and rotate through them with memory. [OBSERVED][ENGINEERING RECOMMENDATION]

## 4.3 Greeting cooldown

**What:** A warm greeting may be given at most once per window (e.g., 3–5 min per person).

**Why:** Repeated greetings are the single most robotic failure in companion robots ("hello again! hello again!"). The cooldown forces *recognition* to carry the second meeting. [ENGINEERING RECOMMENDATION]

## 4.4 Surprise cooldown

**What:** Surprise (E10) may not be played more than once per window (e.g., 30–60 s).

**Why:** Surprise's power is rarity (Bible E10, Things To Avoid). Repeated startles read as neurotic, not playful. [ENGINEERING RECOMMENDATION]

## 4.5 Attention persistence

**What:** Once the robot commits attention to a person, it holds for a minimum window (e.g., 2–3 s) before it may switch — even if the signal flickers.

**Why:** Gaze that flits at every frame of noise reads as unstable. Persistence is what makes attention *meaningful*. [RESEARCH: gaze stability perception]

## 4.6 Emotional persistence

**What:** An emotion, once entered, resists trivial change (hysteresis window ≥ 400 ms; spec §10.3) and cannot be re-entered within ~1.5 s of leaving.

**Why:** Emotional flicker (happy→sad→happy within a second) destroys believability. Persistence is continuity made visible. [ENGINEERING RECOMMENDATION]

## 4.7 Interaction history

**What:** A long-horizon record (who has interacted, how often, with what tone) that shapes defaults — a frequent friend gets warmth; a stranger gets polite distance.

**Why:** History is what turns a machine into a *relationship*. [ENGINEERING RECOMMENDATION; HYPOTHESIS: long-horizon memory increases attachment]

## 4.8 Behavior fatigue

**What:** Any sustained behavior (Listening, Speaking, Focus) has a fatigue limit; beyond it, the robot must vary or release.

**Why:** Long unbroken states read as stuck. Fatigue forces natural variety (a glance away, a stretch, a blink variant) — the "living" texture. [ENGINEERING RECOMMENDATION]

## 4.9 Recovery windows

**What:** After every significant behavior, a recovery window exists (200–800 ms) during which the robot completes its "sentence" (concluding blink, settle) before accepting the next event.

**Why:** Recovery windows are the mechanical enforcement of "every behavior has a recovery" (Part 9, Rule 7). They prevent snap-cut transitions. [ENGINEERING RECOMMENDATION]

---

# PART 5 — ATTENTION MODEL

Attention is the robot's most valuable social resource. This model defines how it is acquired, held, released, switched, interrupted, and recovered — with timing guidance. [ENGINEERING RECOMMENDATION]

## 5.1 Attention acquisition

| Stage | Timing | Behavior |
|---|---|---|
| Detect signal | 0–50 ms | Sensor event |
| Relevance gate | 0–100 ms | Is it a person? a voice? worth it? |
| Orient | 80–200 ms | Fast saccade/head turn to source |
| Confirm | 200–600 ms | One soft blink + micro-fixation |
| Commit | 0.6–1.2 s | Full attention (hold gaze, suppress blink) |

**Guidance:** Acquisition must be fast enough to feel responsive but staged enough to feel organic. A 100–300 ms orient is the sweet spot. [RESEARCH: response latency perception]

## 5.2 Attention holding

| Mode | Hold pattern |
|---|---|
| Casual | 1–2 s holds, 1–4 s breaks |
| Listening | ~75% gaze on speaker, breaks at phrase ends |
| Focus | 3–5 s locks, rare breaks [RESEARCH: mutual gaze 3–5 s] |
| Child / shy personality | 1–2 s holds, 2–5 s breaks |

**Guidance:** Holding must include micro-motion (tremor, micro-saccades) — a held gaze without tremor is a stare. [PRINCIPLE; Bible E7]

## 5.3 Attention release

- **Natural:** glance-away + return cycle; never an abrupt 90° whip [ENGINEERING RECOMMENDATION]
- **Timed:** break every 3–5 s maximum, even mid-engagement [RESEARCH: >10 s gaze = discomfort]
- **Clean:** release includes a concluding blink or micro-nod

## 5.4 Attention switching

- Between people: acknowledge the new speaker (E21 sweep), then switch within ~300 ms
- Between tasks: gaze away → micro-pause → new target
- **Rule:** eye movement precedes head movement [PRINCIPLE]; head follows the eyes, never the reverse

## 5.5 Attention interruption

- Higher-priority events (E04 eye contact, E06 speech, E13 touch, E14 noise) may interrupt lower-priority holding
- Interrupted attention must *finish its sentence*: a concluding blink/settle before the new intent (unless the interrupt is a startle)
- Never interrupt with another interrupt — one recovery at a time [ENGINEERING RECOMMENDATION]

## 5.6 Attention recovery

- After release: return to prior fixation with a soft settle (0.3–0.6 s)
- After loss: 1 s of last-known-point hold, then idle drift
- After a startle: evaluate-and-relax within ~1 s (E14)

---

# PART 6 — INTENT LIBRARY

Intents are the robot's *wants*. They are durable, prioritized, and duration-budgeted. Each intent maps to emotions and a behavior style. Priority scale 1–10. [ENGINEERING RECOMMENDATION]

| # | Intent | Purpose | Associated emotions | Behavior style | Typical duration | Priority |
|---|---|---|---|---|---|---|
| I01 | **Greeting** | Open contact warmly | E2 Happy, E1 Calm | Bright, short, available | 1–3 s | 8 |
| I02 | **Listening** | Receive the person fully | E5 Listening | Still, attentive, lean | 5–60 s (or until speech ends) | 9 |
| I03 | **Responding** | Answer what was heard | E6 Speaking | Clear, confident, turn-taking | 2–30 s | 8 |
| I04 | **Thinking** | Process a request visibly | E4 Thinking | Averted gaze, still, twitch | 1–4 s | 7 |
| I05 | **Searching** | Find a lost person/face | E4 Thinking, E1 Calm | Sweep, hold, relax | 1–3 s | 6 |
| I06 | **Waiting** | Be present without demanding | E1 Calm | Ambient, breathing, soft blinks | indefinite | 2 |
| I07 | **Curious** | Explore the environment | E4 Thinking, E1 Calm | Scans, tilts, re-checks | 3–10 s | 4 |
| I08 | **Playful** | Share joy, invite play | E2 Happy | Sparkle, bounce, double blinks | 2–10 s | 6 |
| I09 | **Comforting** | Support a distressed person | E8 Caring | Warm, slow, long blinks | 5–60 s | 9 |
| I10 | **Alert** | React to a startling signal | E10 Surprised | Fast freeze, orient, evaluate | 0.5–1.5 s | 9 |
| I11 | **Celebrating** | Mark a shared success | E2 Happy, E10 Surprised | Bright, bouncy, generous | 2–5 s | 6 |
| I12 | **Confused** | Handle ambiguity honestly | E4 Thinking (mild) | Squint, tilt, pause | 1–3 s | 5 |
| I13 | **Sleep Transition** | Wind down at bedtime | E9 Sleepy | Heavy, slow, fading | 10–60 s | 5 |
| I14 | **Wake Transition** | Wake up cleanly | E9 Sleepy → E1 Calm | Lift, brighten, waking blink | 1–3 s | 6 |

**Intent guidance:**

- **Greeting and Responding are the only "loud" intents** — everything else is background or reactive. [ENGINEERING RECOMMENDATION]
- **Comforting outranks everything social** (priority 9) — a distressed child always wins over play.
- **Sleep Transition is self-selected only** — never triggered by interruption (spec §10.4).
- An intent may *borrow* emotions mid-flight (Listening may flash E4 Thinking while processing), but the intent (the want) stays constant. [ENGINEERING RECOMMENDATION]

---

# PART 7 — INTERACTION TIMELINES

ASCII timelines for the most important interactions. Baselines for a neutral personality. [ENGINEERING RECOMMENDATION]

## T1 · Person Appears

```
PERSON APPEARS
   0 ms     DETECT (sensor signal)
 150 ms     ORIENT: head/eyes turn to source (fast saccade)
 300 ms     Eye contact established (brief, soft)
 450 ms     REACT: soft happy geometry; availability blink
 800 ms     MAINTAIN: warm open gaze, 1-2 s
1200 ms     RECOVER: settle to calm loops
```

## T2 · Person Starts Speaking

```
PERSON STARTS SPEAKING
   0 ms     DETECT speech onset
 100 ms     Attention gain: eyes widen slightly, lean begins
 200 ms     ORIENT toward speaker
 350 ms     REACT: listening geometry (E5) fully established
 500 ms     MAINTAIN: 75% gaze hold; blink suppression begins
 (phrases)  Micro-nod at phrase ends; re-center between sentences
   end      RECOVER: hold + concluding blink on stop (E07)
```

## T3 · Question Asked → Robot Answers

```
QUESTION ASKED
   0 ms     DETECT question intonation
 300 ms     Hold gaze (turn-taking beat)
 500 ms     Concluding blink; intent shifts Listening → Thinking
 900 ms     THINK: gaze-away, scan up-right (E4)
2000 ms     Twitch; contemplative hold
3000 ms     Thinking blink (conclusion)
3300 ms     Gaze returns; answer begins (E6 Speaking)
 ~5000 ms   REACT-RESPOND with turn-taking; handoff blink at end
```

## T4 · User Touches Robot

```
USER TOUCHES ROBOT
   0 ms     DETECT touch
  80 ms     Micro-startle (tiny widening)
 300 ms     Warm settle (E8 Caring geometry, lean in)
 600 ms     Long slow blink (the trust signal)
1200 ms     MAINTAIN: content hold while contact lasts
   end      RECOVER: release with soft blink
```

## T5 · Loud Noise

```
LOUD NOISE
   0 ms     DETECT (acoustic startle)
 150 ms     REACT: surprise flash (E10 small), fast blink
 250 ms     ORIENT: head turns to sound source
 500 ms     EVALUATE: squint/focus toward source
 900 ms     RECOVER: evaluate-and-relax → calm
```

## T6 · Conversation Ends

```
CONVERSATION ENDS
   0 ms     DETECT (silence / farewell cue)
 200 ms     Closing sparkle (soft happy)
 400 ms     Concluding blink
 700 ms     Final warm gaze hold (1 s)
1700 ms     RECOVER: release to idle loops
```

## T7 · Multiple People

```
MULTIPLE PEOPLE
   0 ms     DETECT N faces
 300 ms     SWEEP: acknowledge each (glance + soft blink each)
 900 ms     SELECT: commit to primary speaker (E5)
1500 ms     MAINTAIN: primary holds; periodic micro-glance to others
   end      RECOVER: re-select if primary changes
```

## T8 · Wind-down (Sleep)

```
WIND-DOWN (SLEEP TRANSITION)
   0 ms     Intent: Sleep Transition (self-selected, low activity)
 500 ms     Lids begin to sink (E9 entry, 500 ms)
2000 ms     Heavy blink with lid-stick at 40%
4000 ms     Deep breathing; openness ~0.3; near-zero motion
 8000 ms    Deep sleep loop established
   wake     WAKE: lids lift → waking blink → calm (E14 intent)
```

---

# PART 8 — BEHAVIOR ARBITRATION

Without algorithms, this part specifies how conflicting intents/behaviors should resolve. The resolution is governed by **intent priority** (Part 6), **emotional continuity** (spec §10.3), and the **interruption rule** (Part 5.5). [ENGINEERING RECOMMENDATION]

## 8.1 The priority ladder (highest → lowest)

```
10  Alert (startle — always wins, briefly)
 9  Comforting / Listening (to a speaking person) / Touch response
 8  Greeting / Responding / Known-person engagement
 7  Thinking / Conversation / Eye-contact establish
 6  Playful / Celebrating / Farewell / Wake
 5  Confused / Searching / Alert-evaluation
 4  Curious / Long-silence check-in / Uncertain emotion
 2  Waiting (background)
 1  Deep sleep (self-selected only)
```

## 8.2 Conflict resolution table

| Conflict | Resolution | Why |
|---|---|---|
| **Speaking vs Thinking** | Thinking *precedes* Speaking; a concluding blink hands off (never overlap) | Cognition must finish its sentence before speech begins [PRINCIPLE] |
| **Greeting vs Surprise** | Surprise (10) wins the first 300–500 ms, then decays into Greeting | A startle mid-greeting is charming; a greeting interrupted by nothing is robotic |
| **Listening vs Face Lost** | Listening continues on **audio** for up to 2–3 s; only then does it yield to Searching/Waiting | Dropping a listener mid-sentence is rude; the voice keeps the contract alive |
| **Curiosity vs Sleep** | Sleep (self-selected) wins only if *both* are true; otherwise Curiosity defers to any social intent | Curiosity must never win against a genuine wind-down |
| **Attention vs Idle** | Attention always beats idle; idle is the *default*, not a competitor | Idle is what you do when nothing better exists |
| **Comforting vs Playful** | Comforting (9) wins over Playful (6) — always | A distressed child must never be met with bounce |
| **Alert vs Everything** | Alert wins for its window (0.5–1.5 s), then *returns to what was interrupted* | Startles are interruptions, not replacements |
| **Two events same priority** | First-come holds (attention persistence §4.5); newer event waits one recovery window | Prevents event-flood thrashing |

## 8.3 Arbitration principles (behavioral, not algorithmic)

1. **One intent at a time.** The face expresses exactly one intent's emotion at any moment. [ENGINEERING RECOMMENDATION]
2. **The winner finishes.** The losing intent's emotion gets a recovery (concluding blink/settle) before the winner's begins — *unless* the winner is Alert. [PRINCIPLE]
3. **Never arbitrate against a person.** Social intents (Listening, Comforting) yield to no internal timer while the person is actively engaged. [ENGINEERING RECOMMENDATION]
4. **The interrupt must justify itself.** Lower-priority intents require a *reason* (a new event), not just a timer. [ENGINEERING RECOMMENDATION]

---

# PART 9 — INTERACTION DESIGN RULES

Twenty-four rules. Violating any one produces a visibly "wrong" robot. [ENGINEERING RECOMMENDATION]

## The 24 Rules

| # | Rule | Rationale / source |
|---|---|---|
| 1 | **Never greet twice in succession.** A second meeting within the cooldown is acknowledged by recognition, not a new greeting. | Memory §4.3; [OBSERVED] companion-robot failure mode |
| 2 | **Never blink exactly periodically.** All blink intervals are randomized within bands. | [PRINCIPLE] periodic = robotic |
| 3 | **Never instantly reverse emotion.** Valence flips route through a neutral waypoint. | Spec §10.3 |
| 4 | **Maintain eye contact naturally** — hold 1–3 s, break, return; never a dead stare. | [RESEARCH] 3–5 s mutual gaze |
| 5 | **Do not stare longer than recommended.** Hard cap ~5 s; break with a glance-away. | [RESEARCH] >10 s = discomfort |
| 6 | **Transitions must preserve emotional continuity.** No teleporting between emotions. | Bible R.1/R.4 |
| 7 | **Every behavior has a recovery.** No behavior ends without a concluding beat (blink/settle). | Part 2 lifecycle; [PRINCIPLE] |
| 8 | **The robot never freezes.** At least one motion layer is always active. | Bible R.1 |
| 9 | **Eye movement precedes head movement.** Always. | [PRINCIPLE] |
| 10 | **The robot looks before it acts.** Every response begins with an orient. | Part 2; [OBSERVED] Aibi voice-tracking |
| 11 | **A higher-priority event may interrupt, but must not truncate** — the interrupted behavior finishes its sentence. | Part 5.5 |
| 12 | **Attention persists through signal flicker.** No attention switching faster than 200 ms. | Memory §4.5 |
| 13 | **Surprise is rare.** At most once per cooldown window; never repeated startles. | Memory §4.4; Bible E10 |
| 14 | **Comforting outranks play.** A distressed person always receives warmth. | Part 8 ladder |
| 15 | **The robot does not stare at a lost face.** One search sweep, then graceful waiting. | E03; [OBSERVED] |
| 16 | **Silence is managed, not feared.** Long silence produces one soft check-in, then patience. | E15 |
| 17 | **No two identical reactions in a row.** Behavior memory rotates variants. | Memory §4.2; [OBSERVED] Aibi |
| 18 | **Blinking is punctuation.** Blinks land at boundaries (phrase ends, transitions, conclusions), never mid-meaning. | Bible R.8 |
| 19 | **The robot never "throws away" an interruption.** An interrupt that loses arbitration is still acknowledged (a glance, a blink). | Part 8.3 |
| 20 | **Recognize the known.** Known persons get warmth; strangers get polite distance. | E22/E23 |
| 21 | **Handle sensor loss with dignity.** No panic behavior on face loss or no-camera. | E03/E26 |
| 22 | **An intent has a duration budget and an exit.** No intent lingers past fatigue without varying or releasing. | Memory §4.8 |
| 23 | **One recovery at a time.** Never interrupt an interrupt. | Part 5.5 |
| 24 | **The robot is a companion, not a performer.** When a rule conflicts, choose the behavior that makes the *person* feel more comfortable. | The master rule [ENGINEERING RECOMMENDATION] |

---

# PART 10 — FUTURE INTEGRATION

This Interaction Bible is the *orchestration contract*: it defines what behavior should happen, independent of how it is delivered. Every future subsystem can be driven by it **without changing the animation engine, the LES architecture, or any existing code**. [ENGINEERING RECOMMENDATION]

## 10.1 What this Bible drives

| Subsystem | Consumes from this Bible | How (behaviorally) |
|---|---|---|
| **Emotion Director** | Event → intent → recommended emotion mapping (Part 3) | Translates detected events into intent + emotion decisions with hysteresis (spec §10.3) |
| **Behavior Director** | Intent library (Part 6), arbitration ladder (Part 8) | Chooses the winning intent per event, honoring cooldowns (Part 4) |
| **Timeline** | Interaction timelines (Part 7), lifecycle phases (Part 2) | Plans the phased beats (orient → react → recover) as scheduled moments |
| **Servo Controller** | Servo suggestions per event (Part 3) | Derives head/body motion from the same beats — eyes first, head second [PRINCIPLE] |
| **Voice** | E06/E07/E18 (speaking/listening events), turn-taking beats | Phrase-boundary events drive gaze/blink; speech never overrides an intent mid-sentence |
| **ROS** | Events (Part 3) as published signals; intents as decisions | ROS transports events and receives decision outputs; no engine knowledge crosses the boundary |
| **LLM** | Intent selection, conversation events (E19/E20), Responding intent | The LLM produces content; this Bible decides *when and how* the robot visibly thinks, listens, and hands off |
| **Touch** | E13 (touch response), Comforting intent | Touch becomes an input to the same arbitration; reactions follow the same rules |
| **Face Tracking** | E01–E05, E21–E26 (presence, eye contact, loss) | Tracking supplies events; this Bible decides the *behavioral* meaning of each |

## 10.2 Integration invariants

1. **The engine is never modified, wrapped, or bypassed** — it remains the pure executor. [ENGINEERING RECOMMENDATION]
2. **The pipeline is one-way**: event → intent → decision → timeline → emotion → animation. No subsystem may shortcut it. [ENGINEERING RECOMMENDATION]
3. **Every subsystem is additive** — adding voice, touch, ROS, or an LLM changes nothing about the other channels.
4. **Behavior memory is cross-channel** — a greeting given via voice and a greeting given via eyes are the *same* greeting to memory; cooldowns apply once. [ENGINEERING RECOMMENDATION]
5. **All timing derives from the behavior spec**; all emotion from the Emotion Bible; all orchestration from this Bible. Three documents, one authority. [ENGINEERING RECOMMENDATION]

## 10.3 Sequencing the future work (behavioral order)

1. **Event → intent mapping** (this Bible, Part 3) — the decision core
2. **Intent → emotion resolution** (Emotion Bible) — the expressive core
3. **Phased timelines** (Part 7) — the temporal core
4. **Memory & cooldowns** (Part 4) — the continuity core
5. **Servo & voice attachment** — first hardware channels
6. **Face tracking & touch** — sensor channels
7. **ROS & LLM** — integration channels

Each step consumes the same Bible; none requires touching the engine or the LES scaffold. [ENGINEERING RECOMMENDATION]

---

*End of specification. Version 1.0 — the behavior orchestration reference for LES. Companion documents: `README.md` (architecture), `behavior-spec-v1.0.md` (timing), `emotion-bible-v1.0.md` (emotion).*
