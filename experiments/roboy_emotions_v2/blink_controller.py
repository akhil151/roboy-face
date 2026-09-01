"""ROBoy Emotion V2 - Phase 4 Blink Controller.

Provides deterministic, state-machine-driven blinking for all ROBoy V2 eye shapes.
Operates strictly in normalized face coordinates and preserves underlying emotion geometry.

Principles:
1. Emotion Preservation:
   - When blinking, vertical openness is reduced smoothly.
   - When blink completes, geometry returns exactly to the underlying V2 emotion.
2. State Machine:
   - OPEN -> CLOSING -> CLOSED (hold) -> OPENING -> OPEN.
3. Deterministic:
   - Driven entirely by update(dt) with zero threads, sleeping, or background clocks.
4. Smooth & Continuous:
   - Uses Perlin smootherstep easing for non-snapping lid closure.
"""

from __future__ import annotations

import copy
import math
from enum import Enum
from typing import Optional, Tuple

import config as cfg
import face as fc
import transition as tr


class BlinkState(Enum):
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    OPENING = "opening"


class BlinkType(Enum):
    NORMAL = "normal"
    QUICK = "quick"
    SLOW = "slow"
    HALF = "half"
    DOUBLE = "double"


# Default timing parameters in seconds (deterministic)
DEFAULT_CLOSE_DURATION = 0.065
DEFAULT_HOLD_DURATION = 0.025
DEFAULT_OPEN_DURATION = 0.080


def smootherstep(u: float) -> float:
    """Perlin smootherstep: 6u^5 - 15u^4 + 10u^3 (clamped to 0..1)."""
    u = max(0.0, min(1.0, u))
    return u * u * u * (u * (u * 6.0 - 15.0) + 10.0)


def is_open_eye(eye: fc.EyeSpec) -> bool:
    """Determine whether an EyeSpec represents a genuinely open eye eligible for gaze and blinking.

    Returns True for:
      - 'circle' with sufficient vertical openness (ry >= EYE_THICK * 0.75, lid < 0.90)
      - 'angry' (filled angular open eye)
      - 'heart' (filled open shape)

    Returns False for:
      - 'arc' (curved stroke arcs: happy, sad, disgusted, wink arc, confused arc)
      - 'sleepy_u' (relaxed/closed U curves: sleepy)
      - 'quad_curve' / 'line'
      - flattened/collapsed stroke circles
    """
    if eye is None:
        return False

    shape = getattr(eye, "shape", None)
    if shape in ("arc", "sleepy_u", "quad_curve", "line"):
        return False

    if shape == "circle":
        ry = getattr(eye, "ry", None) or getattr(eye, "rx", None) or cfg.EYE_R
        lid = getattr(eye, "lid", 0.0) or 0.0
        min_open_ry = (getattr(eye, "thickness", None) or cfg.EYE_THICK) * 0.75
        if ry < min_open_ry or lid >= 0.90:
            return False
        return True

    if shape in ("angry", "heart"):
        return True

    return False


def apply_blink_to_eye(eye: fc.EyeSpec, weight: float, side: str = "left", is_wink: bool = False) -> fc.EyeSpec:
    """Apply blink closure weight (0.0 = fully open, 1.0 = fully closed) to an open V2 eye.

    Non-open/blended eyes (arcs, sleepy U, winked eyes) are ineligible and returned unchanged.
    """
    if weight <= 0.0001:
        return copy.copy(eye)

    # Ineligible / blended / non-open eye: untouched
    if not is_open_eye(eye):
        return copy.copy(eye)

    # Special case: intentional Wink emotion already has right eye closed/arc
    if is_wink and side == "right":
        return copy.copy(eye)

    weight = min(1.0, max(0.0, weight))
    thick = getattr(eye, "thickness", None) or cfg.EYE_THICK
    min_ry = thick / 2.0

    if eye.shape == "circle":
        rx = getattr(eye, "rx", None) or cfg.EYE_R
        ry = getattr(eye, "ry", None) or rx
        lid = getattr(eye, "lid", 0.0) or 0.0
        # Smoothly flatten vertical radius towards minimum stroke thickness
        ry_new = max(min_ry, ry * (1.0 - weight) + min_ry * weight)
        return fc.EyeSpec(
            "circle",
            eye.cx,
            eye.cy,
            rx=rx,
            ry=ry_new,
            lid=lid,
            thickness=thick,
            color=eye.color,
        )

    elif eye.shape == "arc":
        l_pt, r_pt, top_c, bot_c, p1_mid, is_upward = tr.get_canonical_eye_anchors(eye, side)
        y_base = (l_pt[1] + r_pt[1]) / 2.0
        p1_flat = (eye.cx, y_base)
        # Apex moves towards baseline as weight increases
        p1_y = p1_mid[1] * (1.0 - weight) + p1_flat[1] * weight
        p1 = (eye.cx, p1_y)
        return fc.EyeSpec(
            "sleepy_u",
            eye.cx,
            eye.cy,
            p0=l_pt,
            p1=p1,
            p2=r_pt,
            thickness=thick,
            color=eye.color,
        )

    elif eye.shape == "sleepy_u" or eye.shape == "quad_curve":
        s = cfg.EYE_R * 1.00
        p0 = getattr(eye, "p0", (eye.cx - s, eye.cy - 0.14 * s))
        p1 = getattr(eye, "p1", (eye.cx, eye.cy + 0.50 * s))
        p2 = getattr(eye, "p2", (eye.cx + s, eye.cy - 0.14 * s))
        y_base = (p0[1] + p2[1]) / 2.0
        p1_y = p1[1] * (1.0 - weight) + y_base * weight
        p1_cur = (p1[0], p1_y)
        return fc.EyeSpec(
            "sleepy_u",
            eye.cx,
            eye.cy,
            p0=p0,
            p1=p1_cur,
            p2=p2,
            thickness=thick,
            color=eye.color,
        )

    elif eye.shape == "angry":
        a = eye.curve_a
        b = eye.curve_b
        t = eye.curve_t
        u = eye.curve_u
        # Baseline midpoint between corners
        m_ab = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        t_cur = (t[0] * (1.0 - weight) + m_ab[0] * weight, t[1] * (1.0 - weight) + m_ab[1] * weight)
        u_cur = (u[0] * (1.0 - weight) + m_ab[0] * weight, u[1] * (1.0 - weight) + m_ab[1] * weight)
        return fc.EyeSpec(
            "angry",
            eye.cx,
            eye.cy,
            curve_a=a,
            curve_t=t_cur,
            curve_b=b,
            curve_u=u_cur,
            thickness=thick,
            color=eye.color,
        )

    elif eye.shape == "heart":
        hs = getattr(eye, "heart_scale", cfg.EYE_R * cfg.HEART_SCALE)
        # Flatten heart scale vertically
        hs_new = hs * (1.0 - 0.90 * weight)
        return fc.EyeSpec(
            "heart",
            eye.cx,
            eye.cy,
            heart_scale=hs_new,
            thickness=thick,
            color=eye.color,
        )

    return copy.copy(eye)


class BlinkController:
    """Deterministic state-machine blink controller for ROBoy V2."""

    def __init__(
        self,
        close_duration: float = DEFAULT_CLOSE_DURATION,
        hold_duration: float = DEFAULT_HOLD_DURATION,
        open_duration: float = DEFAULT_OPEN_DURATION,
    ):
        self.close_duration = close_duration
        self.hold_duration = hold_duration
        self.open_duration = open_duration

        self.state: BlinkState = BlinkState.OPEN
        self.weight: float = 0.0
        self.target_weight: float = 1.0
        self.elapsed: float = 0.0

        # Optional multi-blink queue (e.g. double blink)
        self._pending_blinks: int = 0
        self._inter_blink_gap: float = 0.05
        self._gap_elapsed: float = 0.0

    @property
    def is_blinking(self) -> bool:
        return self.state != BlinkState.OPEN or self._pending_blinks > 0

    @property
    def blink_weight(self) -> float:
        return self.weight

    def trigger_blink(
        self,
        blink_type: BlinkType = BlinkType.NORMAL,
        duration_multiplier: float = 1.0,
    ) -> None:
        """Trigger a deterministic blink cycle."""
        if blink_type == BlinkType.QUICK:
            mult = 0.65 * duration_multiplier
            self.target_weight = 1.0
        elif blink_type == BlinkType.SLOW:
            mult = 1.80 * duration_multiplier
            self.target_weight = 1.0
        elif blink_type == BlinkType.HALF:
            mult = 1.0 * duration_multiplier
            self.target_weight = 0.50
        elif blink_type == BlinkType.DOUBLE:
            mult = 0.75 * duration_multiplier
            self.target_weight = 1.0
            self._pending_blinks = 1
        else:
            mult = 1.0 * duration_multiplier
            self.target_weight = 1.0

        self.close_duration = DEFAULT_CLOSE_DURATION * mult
        self.hold_duration = DEFAULT_HOLD_DURATION * mult
        self.open_duration = DEFAULT_OPEN_DURATION * mult

        # If already closing or closed, seamlessly continue
        if self.state == BlinkState.OPEN:
            self.state = BlinkState.CLOSING
            self.elapsed = 0.0
            self.weight = 0.0
        elif self.state == BlinkState.OPENING:
            # Reverse direction seamlessly from current weight
            self.state = BlinkState.CLOSING
            self.elapsed = (1.0 - (self.weight / max(0.001, self.target_weight))) * self.close_duration

    def update(self, dt: float) -> float:
        """Advance blink state machine by dt seconds. Returns current blink weight (0..1)."""
        if dt <= 0.0:
            return self.weight

        if self.state == BlinkState.OPEN:
            if self._pending_blinks > 0:
                self._gap_elapsed += dt
                if self._gap_elapsed >= self._inter_blink_gap:
                    self._pending_blinks -= 1
                    self._gap_elapsed = 0.0
                    self.state = BlinkState.CLOSING
                    self.elapsed = 0.0
                    self.weight = 0.0
            else:
                self.weight = 0.0
            return self.weight

        self.elapsed += dt

        if self.state == BlinkState.CLOSING:
            dur = max(0.0001, self.close_duration)
            u = min(1.0, self.elapsed / dur)
            self.weight = smootherstep(u) * self.target_weight
            if u >= 1.0:
                self.state = BlinkState.CLOSED
                self.elapsed = 0.0
                self.weight = self.target_weight

        elif self.state == BlinkState.CLOSED:
            self.weight = self.target_weight
            if self.elapsed >= self.hold_duration:
                self.state = BlinkState.OPENING
                self.elapsed = 0.0

        elif self.state == BlinkState.OPENING:
            dur = max(0.0001, self.open_duration)
            u = min(1.0, self.elapsed / dur)
            self.weight = (1.0 - smootherstep(u)) * self.target_weight
            if u >= 1.0:
                self.state = BlinkState.OPEN
                self.elapsed = 0.0
                self.weight = 0.0
                self._gap_elapsed = 0.0

        return self.weight

    def reset(self) -> None:
        """Reset blink controller immediately to open state."""
        self.state = BlinkState.OPEN
        self.weight = 0.0
        self.elapsed = 0.0
        self._pending_blinks = 0
        self._gap_elapsed = 0.0
