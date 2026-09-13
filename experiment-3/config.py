"""Centralized configuration for ELO Face V3 (Experiment 3).

All display, geometry, color, timing, and timeline constants are defined here.
No magic numbers should be scattered in rendering or animation logic.
"""

from typing import Tuple, List

# ---------------------------------------------------------------------------
# Display & Canvas
# ---------------------------------------------------------------------------
WINDOW_WIDTH: int = 800
WINDOW_HEIGHT: int = 480
TARGET_FPS: int = 60

# ---------------------------------------------------------------------------
# Color Palette (R, G, B)
# ---------------------------------------------------------------------------
COLOR_BG: Tuple[int, int, int] = (0, 0, 0)             # Pure black background
COLOR_EYE: Tuple[int, int, int] = (255, 255, 255)       # Solid pure white eyes
COLOR_ACCENT: Tuple[int, int, int] = (255, 160, 185)   # Soft warm pink for cute blush accents
COLOR_TEXT: Tuple[int, int, int] = (255, 255, 255)     # White intro text

# ---------------------------------------------------------------------------
# Eye Baseline Layout & Dimensions
# ---------------------------------------------------------------------------
BASE_RADIUS: float = 85.0            # Base eye radius in pixels (diameter = 170px)
LEFT_EYE_BASE_X: float = 270.0       # Center X of left eye
RIGHT_EYE_BASE_X: float = 530.0      # Center X of right eye
EYE_BASE_Y: float = 240.0            # Vertical center Y of both eyes

# ---------------------------------------------------------------------------
# Morphing & Squash Parameters
# ---------------------------------------------------------------------------
# open_amount = 1.0 -> Full geometric circle (height = 2 * radius)
# open_amount = 0.0 -> Minimum slit/pill (height = 2 * radius * MIN_OPEN_RATIO)
MIN_OPEN_RATIO: float = 0.06         # Height multiplier when fully closed / blinked
SQUASH_WIDTH_EXPANSION: float = 0.12 # Slight horizontal widening when squashed/closed

# ---------------------------------------------------------------------------
# Gaze & Movement Bounds (in pixels)
# ---------------------------------------------------------------------------
MAX_LOOK_OFFSET_X: float = 65.0      # Maximum horizontal look displacement
MAX_LOOK_OFFSET_Y: float = 45.0      # Maximum vertical look displacement

# ---------------------------------------------------------------------------
# Scale Limits
# ---------------------------------------------------------------------------
MIN_SCALE: float = 0.5               # Minimum scale multiplier
MAX_SCALE: float = 1.5               # Maximum scale multiplier
DEFAULT_SCALE: float = 1.0

# ---------------------------------------------------------------------------
# Animation & Timing Defaults (seconds)
# ---------------------------------------------------------------------------
DEFAULT_BLINK_DURATION: float = 0.18 # Total time for close + open
BLINK_CLOSE_RATIO: float = 0.40      # Fraction of blink duration spent closing
BLINK_HOLD_TIME: float = 0.02        # Time held at peak closed state

BREATH_PERIOD: float = 4.0           # Seconds per subtle idle breathing cycle
BREATH_SCALE_AMP: float = 0.020      # Breathing scale oscillation amplitude

# Motion Smoothing Rates (lambda for exponential decay: rate = 1 - exp(-lambda * dt))
SMOOTH_RATE_LOOK: float = 12.0       # Crisp yet organic gaze tracking
SMOOTH_RATE_SCALE: float = 10.0      # Smooth scale expansion/contraction
SMOOTH_RATE_OPEN: float = 24.0       # Responsive eyelid/squash morphing

# ---------------------------------------------------------------------------
# Stage 2 Timeline Segments (Name, Duration in Seconds)
# Total sequence duration: 62.0 seconds
# ---------------------------------------------------------------------------
TIMELINE_SEGMENTS: List[Tuple[str, float]] = [
    ("intro", 10.0),
    ("settle", 3.5),
    ("blink", 3.5),
    ("look_horizontal", 5.0),
    ("look_vertical", 4.5),
    ("surprise", 3.5),
    ("wink", 3.5),
    ("playful_double_wink", 4.5),
    ("happy_bounce", 4.5),
    ("cute_blush", 5.0),
    ("drowsy", 5.0),
    ("sleep", 9.5),
]

TOTAL_TIMELINE_DURATION: float = sum(dur for _, dur in TIMELINE_SEGMENTS)

# ---------------------------------------------------------------------------
# Cute Blush Accent Parameters
# ---------------------------------------------------------------------------
BLUSH_WIDTH: float = 48.0            # Width of horizontal pink blush capsule
BLUSH_HEIGHT: float = 12.0           # Height of pink blush capsule
BLUSH_OFFSET_Y: float = 115.0        # Y offset from eye center (e.g. 240 + 115 = 355)
BLUSH_MAX_ALPHA: int = 180           # Maximum opacity (0-255) for soft look

# ---------------------------------------------------------------------------
# Sleep Floating 'Z' Particle Parameters
# ---------------------------------------------------------------------------
SLEEP_PARTICLE_SPAWN_INTERVAL: float = 1.3 # Seconds between new 'Z' particles
SLEEP_PARTICLE_LIFETIME: float = 2.8       # Lifetime of each drifting 'Z'
SLEEP_PARTICLE_SPEED_Y: float = 42.0       # Upward velocity in pixels/second
SLEEP_PARTICLE_DRIFT_AMP: float = 15.0     # Amplitude of horizontal sine sway
SLEEP_PARTICLE_DRIFT_FREQ: float = 0.8     # Frequency of horizontal sway (Hz)
SLEEP_SPAWN_X_MIN: float = 580.0           # Spawn zone X min (near right eye outer side)
SLEEP_SPAWN_X_MAX: float = 630.0           # Spawn zone X max
SLEEP_SPAWN_Y: float = 230.0               # Spawn Y level
