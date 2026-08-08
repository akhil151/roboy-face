"""
Real engine integration for LES (LES-08.5).

This package holds the ONLY code that connects the LES execution pipeline
(BehaviorIntent -> Timeline -> Scheduler -> EngineCommand) to the real,
frozen animation engine (``eyes/`` + ``face/``).

    * ``real_engine_driver.py`` - the smallest EngineDriver adapter over
      the existing engines. Translation only: no animation logic, no new
      behavior, no engine modifications.
    * ``les_demo.py`` - an optional pygame demo driven entirely by the LES
      pipeline (windowed or headless).

Importing this package imports the real engine (and therefore pygame). The
core ``les`` package never imports this package - integration is opt-in.
"""

from __future__ import annotations

from .real_engine_driver import RealEngineDriver

__all__ = ["RealEngineDriver"]
