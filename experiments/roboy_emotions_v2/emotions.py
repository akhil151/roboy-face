"""ROBoy Emotion V2 - emotion registry & showcase key mapping."""


# Canonical order of the 14 V2 emotions.
EMOTION_ORDER = [
    "neutral",
    "happy",
    "excited",
    "sad",
    "surprised",
    "thinking",
    "confused",
    "wink",
    "love",
    "tired",
    "sleepy",
    "angry",
    "fearful",
    "disgusted",
]

# Showcase keyboard mapping.
# 1-9 cover the first nine; 0 is the extra slot; a/s/d/f cover the rest.
KEY_MAP = {
    "1": "neutral",
    "2": "happy",
    "3": "excited",
    "4": "sad",
    "5": "surprised",
    "6": "thinking",
    "7": "confused",
    "8": "wink",
    "9": "love",
    "0": "tired",
    "a": "sleepy",
    "s": "angry",
    "d": "fearful",
    "f": "disgusted",
}

# Reverse lookup for printing the active mapping.
INVERSE_KEY_MAP = {v: k for k, v in KEY_MAP.items()}


def emotion_for_key(key):
    return KEY_MAP.get(key.lower())


def mapping_lines():
    lines = []
    for key in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "a", "s", "d", "f"]:
        lines.append(f"  {key.upper()}  -> {KEY_MAP[key]}")
    return lines


# Short human descriptions used by the HUD / README.
DESCRIPTIONS = {
    "neutral": "calm default - round open eyes, soft line mouth",
    "happy": "upward eye arcs, smiling mouth",
    "excited": "wide round open eyes, wide open smile",
    "sad": "downward eye arcs, frowning mouth",
    "surprised": "wide open eyes, open mouth",
    "thinking": "gaze + perimeter '?' cue",
    "confused": "asymmetric eyes, uneven mouth",
    "wink": "one open eye, one closed, playful smile",
    "love": "heart eyes, soft smile",
    "tired": "heavy lids, neutral mouth",
    "sleepy": "relaxed U eyes, drifting ZZZ",
    "angry": "slanted angry eye geometry, flat closed mouth",
    "fearful": "wide uneasy eyes, nervous mouth",
    "disgusted": "narrowed uneven eyes, curled mouth",
}
