"""ROBoy Emotion V2 - Phase 5 Gaze / Look Controller.

Provides smooth, bounded, interruptible eye gaze control for ROBoy V2.
Controls WHERE ROBoy looks without modifying WHAT emotion ROBoy expresses.

Principles:
1. Emotion Separation:
   - Gaze translates eye centers rigidly without altering emotion curves, thicknesses, or styles.
2. Bounded & Safe:
   - Max offsets are strictly bounded to prevent eye crossing, mouth overlap, or canvas clipping.
3. Smooth & Non-Snapping:
   - Perlin smootherstep interpolation guarantees zero velocity & acceleration at endpoints.
4. Seamless Interruption:
   - Re-targeting mid-saccade captures the current position as new origin with zero teleportation.
5. Deterministic:
   - Driven entirely by update(dt) with zero threads, sleeping, or background clocks.
"""

from __future__ import annotations

import copy
import math
from typing import Dict, Optional, Tuple

import config as cfg
import face as fc


# Maximum gaze displacement in normalized face coordinates [0, 1]
# Sized appropriately relative to base eye radius (cfg.EYE_R = 0.072)
MAX_GAZE_OFFSET_X = 0.024   # ~33% of base eye radius
MAX_GAZE_OFFSET_Y = 0.018   # ~25% of base eye radius

# Standard named gaze directions mapped to normalized (gx, gy) in [-1.0, 1.0]
GAZE_DIRECTIONS: Dict[str, Tuple[float, float]] = {
    "center": (0.0, 0.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
    "up": (0.0, -1.0),
    "down": (0.0, 1.0),
    "up_left": (-0.7071, -0.7071),
    "up_right": (0.7071, -0.7071),
    "down_left": (-0.7071, 0.7071),
    "down_right": (0.7071, 0.7071),
}

DEFAULT_GAZE_DURATION = 0.18   # Standard natural saccade duration (seconds)


def smootherstep(u: float) -> float:
    """Perlin smootherstep: 6u^5 - 15u^4 + 10u^3 (clamped to 0..1)."""
    u = max(0.0, min(1.0, u))
    return u * u * u * (u * (u * 6.0 - 15.0) + 10.0)


from blink_controller import is_open_eye


def apply_gaze_to_eye(eye: fc.EyeSpec, offset_x: float, offset_y: float) -> fc.EyeSpec:
    """Translate an open V2 EyeSpec rigidly by (offset_x, offset_y) normalized coordinates.

    Non-open/blended eyes (arcs, sleepy U) are ineligible and returned unchanged.
    """
    if abs(offset_x) < 1e-6 and abs(offset_y) < 1e-6:
        return copy.copy(eye)

    # Ineligible / blended / non-open eye: untouched
    if not is_open_eye(eye):
        return copy.copy(eye)

    new_cx = eye.cx + offset_x
    new_cy = eye.cy + offset_y

    if eye.shape == "circle":
        return fc.EyeSpec(
            "circle",
            new_cx,
            new_cy,
            rx=eye.rx,
            ry=eye.ry,
            lid=eye.lid,
            thickness=eye.thickness,
            color=eye.color,
        )

    elif eye.shape == "arc":
        return fc.EyeSpec(
            "arc",
            new_cx,
            new_cy,
            r=eye.r,
            a0=eye.a0,
            a1=eye.a1,
            thickness=eye.thickness,
            color=eye.color,
        )

    elif eye.shape == "sleepy_u" or eye.shape == "quad_curve":
        p0 = eye.p0
        p1 = eye.p1
        p2 = eye.p2
        p0_new = (p0[0] + offset_x, p0[1] + offset_y) if p0 else None
        p1_new = (p1[0] + offset_x, p1[1] + offset_y) if p1 else None
        p2_new = (p2[0] + offset_x, p2[1] + offset_y) if p2 else None
        return fc.EyeSpec(
            eye.shape,
            new_cx,
            new_cy,
            p0=p0_new,
            p1=p1_new,
            p2=p2_new,
            thickness=eye.thickness,
            color=eye.color,
        )

    elif eye.shape == "angry":
        ca = eye.curve_a
        ct = eye.curve_t
        cb = eye.curve_b
        cu = eye.curve_u
        ca_new = (ca[0] + offset_x, ca[1] + offset_y) if ca else None
        ct_new = (ct[0] + offset_x, ct[1] + offset_y) if ct else None
        cb_new = (cb[0] + offset_x, cb[1] + offset_y) if cb else None
        cu_new = (cu[0] + offset_x, cu[1] + offset_y) if cu else None
        return fc.EyeSpec(
            "angry",
            new_cx,
            new_cy,
            curve_a=ca_new,
            curve_t=ct_new,
            curve_b=cb_new,
            curve_u=cu_new,
            thickness=eye.thickness,
            color=eye.color,
        )

    elif eye.shape == "heart":
        return fc.EyeSpec(
            "heart",
            new_cx,
            new_cy,
            heart_scale=eye.heart_scale,
            thickness=eye.thickness,
            color=eye.color,
        )

    # Fallback
    res = copy.copy(eye)
    res.cx = new_cx
    res.cy = new_cy
    return res


class LookController:
    """Deterministic smooth gaze controller for ROBoy V2."""

    def __init__(
        self,
        max_offset_x: float = MAX_GAZE_OFFSET_X,
        max_offset_y: float = MAX_GAZE_OFFSET_Y,
        default_duration: float = DEFAULT_GAZE_DURATION,
    ):
        self.max_offset_x = max_offset_x
        self.max_offset_y = max_offset_y
        self.default_duration = default_duration

        # Current normalized direction in [-1.0, 1.0]
        self.cur_x: float = 0.0
        self.cur_y: float = 0.0

        # Start and target for active saccade
        self.start_x: float = 0.0
        self.start_y: float = 0.0
        self.target_x: float = 0.0
        self.target_y: float = 0.0

        self.duration: float = default_duration
        self.elapsed: float = 0.0
        self.is_active: bool = False

    @property
    def is_moving(self) -> bool:
        return self.is_active

    @property
    def gaze_direction(self) -> Tuple[float, float]:
        """Return current normalized gaze (gx, gy) in [-1.0, 1.0]."""
        return (self.cur_x, self.cur_y)

    @property
    def target_direction(self) -> Tuple[float, float]:
        return (self.target_x, self.target_y)

    def get_spatial_offset(self) -> Tuple[float, float]:
        """Return actual face coordinate displacement (dx, dy) in [-max_offset, +max_offset]."""
        return (self.cur_x * self.max_offset_x, self.cur_y * self.max_offset_y)

    def look_direction(self, direction: str, duration: Optional[float] = None) -> None:
        """Look in a named direction ('center', 'left', 'right', 'up', 'down', etc.)."""
        dir_lower = direction.lower()
        if dir_lower not in GAZE_DIRECTIONS:
            raise ValueError(f"Unknown gaze direction '{direction}'. Available: {list(GAZE_DIRECTIONS.keys())}")
        tx, ty = GAZE_DIRECTIONS[dir_lower]
        self.look_at(tx, ty, duration=duration)

    def look_at(self, x: float, y: float, duration: Optional[float] = None) -> None:
        """Look at normalized target coordinates (x, y) in [-1.0, 1.0].

        Seamlessly captures current interpolated position if interrupted mid-flight.
        """
        tx = max(-1.0, min(1.0, float(x)))
        ty = max(-1.0, min(1.0, float(y)))

        # If already at target, no-op
        if abs(tx - self.cur_x) < 1e-4 and abs(ty - self.cur_y) < 1e-4 and not self.is_active:
            self.target_x = tx
            self.target_y = ty
            return

        # Interruption: capture current live pose as starting point
        self.start_x = self.cur_x
        self.start_y = self.cur_y
        self.target_x = tx
        self.target_y = ty

        # Distance-scaled duration for organic saccade timing
        dist = math.hypot(tx - self.start_x, ty - self.start_y)
        if duration is not None:
            self.duration = max(0.01, duration)
        else:
            self.duration = max(0.10, min(0.30, 0.12 + dist * 0.08))

        self.elapsed = 0.0
        self.is_active = True

    def update(self, dt: float) -> Tuple[float, float]:
        """Advance gaze motion by dt seconds. Returns current (gx, gy)."""
        if dt <= 0.0 or not self.is_active:
            return (self.cur_x, self.cur_y)

        self.elapsed += dt
        u = min(1.0, self.elapsed / max(0.0001, self.duration))
        eased_u = smootherstep(u)

        self.cur_x = self.start_x + (self.target_x - self.start_x) * eased_u
        self.cur_y = self.start_y + (self.target_y - self.start_y) * eased_u

        if u >= 1.0:
            self.is_active = False
            self.cur_x = self.target_x
            self.cur_y = self.target_y

        return (self.cur_x, self.cur_y)

    def reset(self, x: float = 0.0, y: float = 0.0) -> None:
        """Immediately center or set gaze without transition."""
        self.cur_x = max(-1.0, min(1.0, float(x)))
        self.cur_y = max(-1.0, min(1.0, float(y)))
        self.start_x = self.cur_x
        self.start_y = self.cur_y
        self.target_x = self.cur_x
        self.target_y = self.cur_y
        self.is_active = False
        self.elapsed = 0.0
