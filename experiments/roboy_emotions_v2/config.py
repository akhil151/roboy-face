"""ROBoy Emotion V2 - configuration.

All tunable parameters live here. The renderer and geometry builders never
scatter magic numbers; everything is read from this module so the visual
design can be adjusted in one place.

Coordinates are NORMALIZED inside a square "face region":
    x = 0.0 -> left edge of the face square
    x = 1.0 -> right edge
    y = 0.0 -> top edge
    y = 1.0 -> bottom edge
The face square is centred inside the window and scaled by FACE_SCALE.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Colours (R, G, B)
# ---------------------------------------------------------------------------
BG_COLOR = (0, 0, 0)             # black canvas
FACE_COLOR = (255, 255, 255)     # pure white facial elements (reference)
FACE_COLOR_DIM = (255, 255, 255) # white; kept white for a monochrome look
ACCENT_COLOR = (255, 255, 255)   # white

# ---------------------------------------------------------------------------
# Window / canvas
# ---------------------------------------------------------------------------
WINDOW_W = 760
WINDOW_H = 760
FACE_SCALE = 0.86    # face square edge as a fraction of min(window size)

# ---------------------------------------------------------------------------
# Eye layout (normalized within the face square)
# ---------------------------------------------------------------------------
EYE_CY = 0.40          # vertical centre of both eyes
EYE_DX = 0.155         # horizontal offset of each eye from face centre x=0.5
EYE_R = 0.072          # base eye radius
EYE_THICK = 0.020      # stroke thickness for arc / line / curve eyes

# ---------------------------------------------------------------------------
# Mouth layout
# ---------------------------------------------------------------------------
MOUTH_CY = 0.65          # raised to compress the eye->mouth gap (more compact)
MOUTH_W = 0.20
MOUTH_THICK = 0.022

# ---------------------------------------------------------------------------
# Global animation (deterministic, sine / modulo based)
# ---------------------------------------------------------------------------
BREATH_PERIOD = 5.0          # seconds for one breathing cycle
BREATH_AMP = 0.025           # fractional scale modulation of the eyes
BLINK_PERIOD = 4.2           # seconds between blinks
BLINK_DURATION = 0.13        # seconds the blink takes (close + open)
BLINK_DEPTH = 0.85           # how strongly the eye squashes vertically

# ---------------------------------------------------------------------------
# Thinking "?" / Thought cloud overlay
# ---------------------------------------------------------------------------
Q_EYE_SIDE = "right"     # which eye the ? relates to ("left" / "right")
Q_DIST = 0.155           # distance of ? centre from the eye centre (normalized)
Q_ANGLE_DEG = 52.0       # direction from the eye centre (toward outer-top)
Q_SIZE = 0.086           # glyph size (~half eye height, +~19% for prominence)
Q_BOB_AMP = 0.012        # subtle vertical bob amplitude (normalized)
Q_BOB_PERIOD = 3.2       # seconds for one bob cycle
Q_FADE_PERIOD = 4.0      # seconds for one fade-in / fade-out cycle
Q_FADE_MIN = 120         # minimum alpha (0..255) at the dimmest point

CLOUD_EYE_SIDE = "right"
CLOUD_DIST = 0.155
CLOUD_ANGLE_DEG = 52.0
CLOUD_SIZE = 0.14          # increased from 0.086 for more prominence
CLOUD_BOB_AMP = 0.025      # stronger bob for clearly visible motion (was 0.018)
CLOUD_BOB_PERIOD = 3.2
CLOUD_FADE_PERIOD = 4.0
CLOUD_FADE_MIN = 120
CLOUD_CYCLE = 4.5          # full grow/fade cycle (seconds)
CLOUD_GROW_PHASE = 1.2     # dot grows to cloud—EXTENDED for more visible emergence (was 1.0)
CLOUD_PEAK_PHASE = 1.2     # cloud at full size—SHORTENED to show fade sooner (was 1.5)
CLOUD_FADE_PHASE = 2.1     # cloud fades—EXTENDED for perceptible fade (was 2.0)
CLOUD_ALPHA_MIN = 60       # minimum alpha during fade (makes fade more visible)

# ---------------------------------------------------------------------------
# Listening overlay & eyes
# ---------------------------------------------------------------------------
LISTENING_EYE_R = 0.076          # attentive, slightly open/alert eyes (cfg.EYE_R * ~1.05)
LISTENING_PULSE_PERIOD = 3.2
LISTENING_PULSE_AMP = 0.018
LISTENING_WAVES_EYE_SIDE = "right"    # anchor to right eye (like Thinking cloud and Sleepy Z)
LISTENING_WAVES_DIST = 0.140           # distance from right eye center to signal origin (upper-right)
LISTENING_WAVES_ANGLE_DEG = 48.0       # angle upward from horizontal (matches ZZZ aesthetic)
LISTENING_WAVES_ANGLE_TILT = 12.0      # rightward tilt (degrees, subtle rotation toward right)
LISTENING_WAVES_R0 = 0.035             # inner radius of first arc
LISTENING_WAVES_SPACING = 0.020        # spacing between arc radii
LISTENING_WAVES_SPAN_DEG = 90.0        # upward curved arc spread (90 deg = full semicircle)
LISTENING_WAVES_PERIOD = 2.4           # ripple / pulse animation cycle
LISTENING_WAVES_THICK = 0.011          # stroke thickness for listening arcs
LISTENING_WAVES_FADE_PERIOD = 3.0      # fade/pulse cycle (seconds)
LISTENING_WAVES_ALPHA_RANGE = (80, 220)  # (min, max) alpha for fade envelope—INCREASED visibility (was implicit)

# ---------------------------------------------------------------------------
# Sleepy "ZZZ" overlay
# ---------------------------------------------------------------------------
ZZZ_EYE_SIDE = "right"
ZZZ_DIST0 = 0.150         # base distance of the first Z from the eye centre
ZZZ_ANGLE_DEG = 48.0      # direction from the eye centre (toward outer-top)
ZZZ_RISE = 0.05           # gentle upward drift per Z over its life
ZZZ_CYCLE = 4.0           # full repeating cycle (seconds)
ZZZ_LIFE = 2.3            # lifetime of a single Z inside the cycle (slower)
ZZZ_STAGGER = 1.33        # spawn offset between successive Z's (= CYCLE/3)
ZZZ_SIZE0 = 0.086         # first Z glyph size (+~19% for prominence)
ZZZ_SIZE_STEP = 0.78      # per-Z size multiplier (decreasing)
ZZZ_ALPHA0 = 235          # first Z peak alpha
ZZZ_ALPHA_STEP = 0.80     # per-Z peak alpha multiplier (decreasing)
ZZZ_DRIFT_X = 0.01        # tiny horizontal drift per Z
ZZZ_SPREAD_X = 0.06       # static diagonal spacing between successive Z's (right)
ZZZ_SPREAD_Y = 0.10       # static diagonal spacing between successive Z's (up)

# ---------------------------------------------------------------------------
# Love heart sizing
# ---------------------------------------------------------------------------
HEART_SCALE = 1.45        # heart size relative to EYE_R

# ---------------------------------------------------------------------------
# Per-emotion animation knobs (kept here, not scattered in builders)
# ---------------------------------------------------------------------------
SAD_SETTLE_PERIOD = 6.5
SAD_LID_BASE = 0.44
SAD_LID_TILT = 0.16       # eyelid tilt: inner corner higher, outer corner lower
SAD_LID_AMP = 0.04        # gentle settle modulation of lid
TIRED_LID_BASE = 0.42     # baseline fraction of the eye covered by the lid
TIRED_LID_AMP = 0.10      # slow oscillation of the lid
TIRED_LID_PERIOD = 7.0
ANGRY_TENSION_AMP = 0.02
ANGRY_TENSION_PERIOD = 3.0
EXCITED_PERIOD = 1.6
FEARFUL_PERIOD = 0.9      # small, fast, low-amplitude nervous motion
FEARFUL_AMP = 0.010
SLEEPY_RELAX_PERIOD = 5.5
SLEEPY_RELAX_AMP = 0.18   # gentle variation of the cup depth
LOVE_PULSE_PERIOD = 2.4
LOVE_PULSE_AMP = 0.06
WINK_PERIOD = 3.0         # right eye open/closed cycle
CONFUSED_PERIOD = 2.7


# ---------------------------------------------------------------------------
# Transition timing & easing
# ---------------------------------------------------------------------------
TRANSITION_DURATION = 0.55       # default transition duration (seconds, ~550 ms)
TRANSITION_EASING = "smootherstep" # smooth acceleration and deceleration


@dataclass
class Config:
    """Bundled configuration so callers can override a single object."""

    bg_color = BG_COLOR
    face_color = FACE_COLOR
    face_color_dim = FACE_COLOR_DIM
    window_w = WINDOW_W
    window_h = WINDOW_H
    face_scale = FACE_SCALE
    eye_cy = EYE_CY
    eye_dx = EYE_DX
    eye_r = EYE_R
    eye_thick = EYE_THICK
    mouth_cy = MOUTH_CY
    mouth_w = MOUTH_W
    mouth_thick = MOUTH_THICK
    transition_duration = TRANSITION_DURATION


def default_config() -> Config:
    return Config()

