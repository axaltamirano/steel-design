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
    #: Flexure, all limit states (Section F1).
    FLEXURE: Final = 0.90
    #: Shear, all provisions of Chapter G except Section G2.1(a) (Section G1).
    SHEAR: Final = 0.90
    #: Shear of rolled I-shaped webs with h/tw <= 2.24 sqrt(E/Fy) (Section G2.1(a)).
    SHEAR_ROLLED_I: Final = 1.00
    #: Tension rupture and shear rupture of bolts and threaded parts (Section J3.7).
    BOLT_RUPTURE: Final = 0.75
    #: Combined tension and shear in bearing-type connections (Section J3.8).
    BOLT_COMBINED: Final = 0.75
    #: Slip resistance, standard and short-slotted holes perpendicular to the load (Section J3.9(a)).
    SLIP_STANDARD: Final = 1.00
    #: Slip resistance, oversized and short-slotted holes parallel to the load (Section J3.9(b)).
    SLIP_OVERSIZED: Final = 0.85
    #: Slip resistance, long-slotted holes (Section J3.9(c)).
    SLIP_LONG_SLOT: Final = 0.70
    #: Bearing and tearout strength at bolt holes (Section J3.11).
    BEARING_TEAROUT: Final = 0.75
