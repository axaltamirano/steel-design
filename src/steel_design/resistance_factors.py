"""LRFD resistance factors, AISC 360-22.

The library uses LRFD only. Every phi factor is defined here, once, and the strength modules
refer to this class.
"""

from __future__ import annotations

from typing import Final


class ResistanceFactors:
    """Resistance factors ``phi`` for LRFD, by chapter and limit state."""

    #: Tensile yielding in the gross section (Section D2).
    TENSION_YIELDING: Final = 0.90
    #: Tensile rupture in the net section (Section D2).
    TENSION_RUPTURE: Final = 0.75
    #: Compression, all buckling limit states (Section E1).
    COMPRESSION: Final = 0.90
