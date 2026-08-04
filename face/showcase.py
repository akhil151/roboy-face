"""
Entry point for python face/showcase.py.
Launches the ELO Face Engine Interactive Studio Showcase.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from face.face_showcase import main

if __name__ == "__main__":
    main()
