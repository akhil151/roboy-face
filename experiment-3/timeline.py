"""Data-driven animation timeline sequencer for ELO Face V3.

Manages the 12-segment 62-second automated emotion experience.
Allows smooth automatic progression, looping, manual segment jumping,
and pause/resume controls.
"""

from typing import List, Tuple, Optional, Callable
from config import TIMELINE_SEGMENTS, TOTAL_TIMELINE_DURATION
from easing import clamp


class TimelineSegment:
    """Represents a single segment in the timeline."""

    def __init__(self, name: str, duration: float) -> None:
        self.name: str = name
        self.duration: float = max(0.1, duration)


class TimelineController:
    """Orchestrates segment progression, loop timing, and transitions."""

    def __init__(
        self,
        segments: Optional[List[Tuple[str, float]]] = None,
        on_segment_change: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        raw_segments = segments or TIMELINE_SEGMENTS
        self.segments: List[TimelineSegment] = [
            TimelineSegment(name, dur) for name, dur in raw_segments
        ]
        self.total_duration: float = sum(s.duration for s in self.segments)

        self.current_index: int = 0
        self.segment_elapsed: float = 0.0
        self.total_elapsed: float = 0.0
        self.is_paused: bool = False
        self.loop_count: int = 0

        # Callback hook: on_segment_change(old_segment_name, new_segment_name)
        self.on_segment_change: Optional[Callable[[str, str], None]] = on_segment_change

    @property
    def current_segment(self) -> TimelineSegment:
        return self.segments[self.current_index]

    @property
    def current_name(self) -> str:
        return self.current_segment.name

    @property
    def current_duration(self) -> float:
        return self.current_segment.duration

    @property
    def progress(self) -> float:
        """Normalized progress of current segment in [0.0, 1.0]."""
        return clamp(self.segment_elapsed / self.current_duration, 0.0, 1.0)

    @property
    def overall_progress(self) -> float:
        """Normalized progress of the entire 62-second loop in [0.0, 1.0]."""
        if self.total_duration <= 0.0:
            return 0.0
        return clamp(self.total_elapsed / self.total_duration, 0.0, 1.0)

    def reset(self) -> None:
        """Reset timeline to the very beginning (Intro)."""
        old_name = self.current_name
        self.current_index = 0
        self.segment_elapsed = 0.0
        self.total_elapsed = 0.0
        self.loop_count = 0
        if self.on_segment_change and old_name != self.current_name:
            self.on_segment_change(old_name, self.current_name)

    def jump_to(self, target: str | int) -> None:
        """Jump directly to a specific segment by name or integer index."""
        old_name = self.current_name
        if isinstance(target, int):
            new_index = max(0, min(len(self.segments) - 1, target))
        else:
            target_str = str(target).lower().strip()
            found_idx = None
            for idx, seg in enumerate(self.segments):
                if seg.name.lower() == target_str:
                    found_idx = idx
                    break
            if found_idx is None:
                raise ValueError(f"Unknown timeline segment: '{target}'")
            new_index = found_idx

        self.current_index = new_index
        self.segment_elapsed = 0.0

        # Recalculate total_elapsed up to this segment
        self.total_elapsed = sum(self.segments[i].duration for i in range(new_index))

        if self.on_segment_change:
            self.on_segment_change(old_name, self.current_name)

    def next_segment(self) -> None:
        """Advance immediately to the next segment."""
        next_idx = (self.current_index + 1) % len(self.segments)
        self.jump_to(next_idx)

    def prev_segment(self) -> None:
        """Jump back to previous segment."""
        prev_idx = (self.current_index - 1) % len(self.segments)
        self.jump_to(prev_idx)

    def toggle_pause(self) -> None:
        self.is_paused = not self.is_paused

    def update(self, dt: float) -> Tuple[str, float, float]:
        """Advances timeline by dt seconds and returns (segment_name, progress, dt)."""
        if self.is_paused or dt <= 0.0:
            return self.current_name, self.progress, 0.0

        self.segment_elapsed += dt
        self.total_elapsed += dt

        # Check if current segment completed
        while self.segment_elapsed >= self.current_duration:
            excess_time = self.segment_elapsed - self.current_duration
            old_name = self.current_name
            self.current_index = (self.current_index + 1) % len(self.segments)

            if self.current_index == 0:
                self.loop_count += 1
                self.total_elapsed = excess_time
            else:
                self.segment_elapsed = excess_time

            self.segment_elapsed = excess_time
            if self.on_segment_change:
                self.on_segment_change(old_name, self.current_name)

        return self.current_name, self.progress, dt
