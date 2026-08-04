"""
Multi-Parameter Procedural Speech Sync Subsystem.

Speech amplitude (0.0 to 1.0) drives mouth height, width, opening, corner roundness,
upper/lower curvature, and phonetic stretch/squash simultaneously in real time.
Zero keyframes, zero animation clips — fully organic, procedural articulation.
"""

from __future__ import annotations

import math
from .mouth_shapes import MouthParams


class SpeechSync:
    """Procedural multi-parameter speech driver."""

    def __init__(self) -> None:
        self._target_pulse: float = 0.0
        self._current_pulse: float = 0.0
        self._envelope: float = 0.0
        self._phoneme_phase: float = 0.0

        # Attack and decay rates (smooth articulation response)
        self._attack_rate: float = 24.0  # Fast attack for crisp consonants
        self._decay_rate: float = 12.0   # Organic decay for vowels

    @property
    def current_pulse(self) -> float:
        return self._current_pulse

    @property
    def envelope(self) -> float:
        return self._envelope

    def set_speech_pulse(self, pulse: float) -> None:
        """Set raw input speech pulse in range [0.0, 1.0]."""
        self._target_pulse = max(0.0, min(1.0, pulse))

    def update(self, dt_s: float) -> None:
        """Advance speech envelope and phoneme oscillation phase."""
        if dt_s <= 0.0:
            return

        # Smooth envelope follower (attack / decay)
        if self._target_pulse > self._envelope:
            rate = self._attack_rate
        else:
            rate = self._decay_rate

        self._envelope += (self._target_pulse - self._envelope) * min(1.0, dt_s * rate)
        self._current_pulse = self._envelope

        # Advance internal phoneme oscillation phase when speech is active
        if self._envelope > 0.02:
            self._phoneme_phase += dt_s * (14.0 + self._envelope * 8.0)

    def apply(self, params: MouthParams) -> None:
        """Procedurally modulate multiple MouthParams simultaneously based on speech pulse."""
        p = self._envelope
        if p <= 0.001:
            return

        # Rhythmic cadence oscillation simulating vowel/consonant shape variations
        cadence = math.sin(self._phoneme_phase)
        cadence_fast = math.cos(self._phoneme_phase * 1.5)

        # 1. Height expansion (up to +70% opening height)
        height_mult = 1.0 + p * 0.70 + cadence * 0.15 * p
        params.height *= height_mult

        # 2. Cavity opening (drives dark cavity mask visibility)
        params.opening = max(params.opening, min(1.0, p * 0.85 + cadence_fast * 0.12 * p))

        # 3. Width dynamic modulation (-15% on rounded vowels, +25% on wide open vowels)
        width_mod = (0.05 + 0.20 * cadence) * p
        params.width *= (1.0 + width_mod)

        # 4. Phonetic Stretch & Squash
        params.stretch += (0.15 * cadence) * p
        params.squash += (0.20 * (1.0 - abs(cadence))) * p

        # 5. Corner Roundness adjustment (tightens slightly during open speech for crisp lip shape)
        params.corner_roundness = max(0.4, params.corner_roundness - 0.25 * p)

        # 6. Upper & Lower Curvature articulation
        params.upper_curvature += (0.12 * cadence) * p
        params.lower_curvature += (0.15 * (1.0 - cadence)) * p

        params.clamp_safe()
