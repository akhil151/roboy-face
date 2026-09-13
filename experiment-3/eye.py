"""Eye and EyePair data models and parametric geometry calculator for ELO Face V3.

Implements the single rounded shape circle-to-pill squash morphing, gaze offset,
and scale modulation.
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Any

from config import (
    BASE_RADIUS,
    LEFT_EYE_BASE_X,
    RIGHT_EYE_BASE_X,
    EYE_BASE_Y,
    MIN_OPEN_RATIO,
    SQUASH_WIDTH_EXPANSION,
    MAX_LOOK_OFFSET_X,
    MAX_LOOK_OFFSET_Y,
    MIN_SCALE,
    MAX_SCALE,
    DEFAULT_SCALE,
)
from easing import clamp


@dataclass(frozen=True)
class EyeGeometry:
    """Computed pixel geometry for rendering a single eye."""
    cx: float
    cy: float
    width: float
    height: float
    corner_radius: float
    rect_x: float
    rect_y: float

    @property
    def bounding_rect_tuple(self) -> Tuple[int, int, int, int]:
        """Integer (x, y, w, h) for Pygame rect drawing."""
        return (
            int(round(self.rect_x)),
            int(round(self.rect_y)),
            int(round(self.width)),
            int(round(self.height)),
        )

    @property
    def is_circle(self) -> bool:
        """True if width and height are effectively equal."""
        return abs(self.width - self.height) < 0.5


class Eye:
    """Represents a single ELO robotic eye."""

    def __init__(
        self,
        base_cx: float,
        base_cy: float = EYE_BASE_Y,
        radius: float = BASE_RADIUS,
    ) -> None:
        self.base_cx: float = float(base_cx)
        self.base_cy: float = float(base_cy)
        self.radius: float = float(radius)

        # Dynamic state parameters
        self.open_amount: float = 1.0   # 1.0 = fully open circle, 0.0 = closed stadium pill
        self.look_x: float = 0.0        # Horizontal pixel displacement
        self.look_y: float = 0.0        # Vertical pixel displacement
        self.scale: float = DEFAULT_SCALE # Overall scale multiplier
        self.tilt_deg: float = 0.0      # Optional angular tilt in degrees

    def set_open(self, amount: float) -> None:
        """Set the eye open amount in [0.0, 1.0]."""
        self.open_amount = clamp(amount, 0.0, 1.0)

    def set_look(self, dx: float, dy: float) -> None:
        """Set the gaze offset clamped to maximum allowed travel."""
        self.look_x = clamp(dx, -MAX_LOOK_OFFSET_X, MAX_LOOK_OFFSET_X)
        self.look_y = clamp(dy, -MAX_LOOK_OFFSET_Y, MAX_LOOK_OFFSET_Y)

    def set_scale(self, scale: float) -> None:
        """Set the eye scale multiplier clamped to [MIN_SCALE, MAX_SCALE]."""
        self.scale = clamp(scale, MIN_SCALE, MAX_SCALE)

    def compute_geometry(self) -> EyeGeometry:
        """Calculates current pixel dimensions and rounded pill geometry.

        Morphing logic:
        - When open_amount == 1.0:
            Width = 2 * radius * scale
            Height = 2 * radius * scale
            Corner Radius = Height / 2 = radius * scale -> Perfect circle
        - When open_amount < 1.0:
            Height vertically squashes down to 2 * radius * scale * MIN_OPEN_RATIO
            Width slightly expands horizontally (SQUASH_WIDTH_EXPANSION)
            Corner Radius = Height / 2 -> Smoothly rounded capsule / pill
        """
        cx = self.base_cx + self.look_x
        cy = self.base_cy + self.look_y

        # Width expansion when squashed gives a realistic, organic blink deformation
        squash_factor = 1.0 - self.open_amount
        w_multiplier = 1.0 + squash_factor * SQUASH_WIDTH_EXPANSION
        width = 2.0 * self.radius * self.scale * w_multiplier

        # Vertical height morph
        h_ratio = MIN_OPEN_RATIO + (1.0 - MIN_OPEN_RATIO) * self.open_amount
        height = 2.0 * self.radius * self.scale * h_ratio

        # Corner radius for capsule/pill: min(width/2, height/2) = height / 2
        corner_radius = min(width / 2.0, height / 2.0)

        rect_x = cx - width / 2.0
        rect_y = cy - height / 2.0

        return EyeGeometry(
            cx=cx,
            cy=cy,
            width=width,
            height=height,
            corner_radius=corner_radius,
            rect_x=rect_x,
            rect_y=rect_y,
        )


class EyePair:
    """Manages the synchronized or asymmetric state of left and right eyes."""

    def __init__(
        self,
        left_base_x: float = LEFT_EYE_BASE_X,
        right_base_x: float = RIGHT_EYE_BASE_X,
        base_y: float = EYE_BASE_Y,
        radius: float = BASE_RADIUS,
    ) -> None:
        self.left_eye: Eye = Eye(left_base_x, base_y, radius)
        self.right_eye: Eye = Eye(right_base_x, base_y, radius)

    def set_open(self, left: float, right: float | None = None) -> None:
        """Set open amounts for left and right eyes (or both if right is None)."""
        self.left_eye.set_open(left)
        self.right_eye.set_open(left if right is None else right)

    def set_look(self, dx: float, dy: float) -> None:
        """Set shared gaze displacement for both eyes."""
        self.left_eye.set_look(dx, dy)
        self.right_eye.set_look(dx, dy)

    def set_scale(self, scale: float) -> None:
        """Set shared scale for both eyes."""
        self.left_eye.set_scale(scale)
        self.right_eye.set_scale(scale)

    def get_geometries(self) -> Tuple[EyeGeometry, EyeGeometry]:
        """Compute geometries for both left and right eyes."""
        return self.left_eye.compute_geometry(), self.right_eye.compute_geometry()

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot dict of both eyes for debugging or recording."""
        l_geom, r_geom = self.get_geometries()
        return {
            "left": {
                "open": self.left_eye.open_amount,
                "look": (self.left_eye.look_x, self.left_eye.look_y),
                "scale": self.left_eye.scale,
                "geometry": l_geom,
            },
            "right": {
                "open": self.right_eye.open_amount,
                "look": (self.right_eye.look_x, self.right_eye.look_y),
                "scale": self.right_eye.scale,
                "geometry": r_geom,
            },
        }
