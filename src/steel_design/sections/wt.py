"""Tees cut from W-shapes (WT)."""

from __future__ import annotations

from pint import Quantity

from steel_design.classification import SectionClassification
from steel_design.sections.shape_groups import TeeShape


class WT(TeeShape):
    """Tee cut from a W-shape (WT), e.g. ``WT7X34``."""

    family = "WT"

    #: Shape designation per the AISC EDI naming convention.
    EDI_Std_Nomenclature: str
    #: Shape designation as shown in the Steel Construction Manual.
    AISC_Manual_Label: str
    #: Special-note flag, ``"T"`` or ``"F"``.
    T_F: str
    #: Nominal weight per unit length, lb/ft.
    weight: Quantity
    #: Cross-sectional area, in.².
    A: Quantity
    #: Overall depth of the tee, in.
    d: Quantity
    #: Detailing value of member depth, in.
    ddet: Quantity
    #: Width of flange, in.
    bf: Quantity
    #: Detailing value of flange width, in.
    bfdet: Quantity
    #: Thickness of web, in.
    tw: Quantity
    #: Detailing value of web thickness, in.
    twdet: Quantity
    #: Detailing value of tw/2, in.
    twdet_2: Quantity
    #: Thickness of flange, in.
    tf: Quantity
    #: Detailing value of flange thickness, in.
    tfdet: Quantity
    #: Distance from outer face of flange to web toe of fillet, used for design, in.
    kdes: Quantity
    #: Distance from outer face of flange to web toe of fillet, used for detailing, in.
    kdet: Quantity
    #: Vertical distance from the designated edge (Manual Part 1) to the center of gravity, in.
    y: Quantity
    #: Vertical distance from the designated edge (Manual Part 1) to the plastic neutral axis, in.
    yp: Quantity
    #: Flange slenderness ratio, bf/2tf.
    bf_2tf: float
    #: Stem slenderness ratio, d/tw.
    D_t: float
    #: Moment of inertia about the x-axis, in.⁴.
    Ix: Quantity
    #: Plastic section modulus about the x-axis, in.³.
    Zx: Quantity
    #: Elastic section modulus about the x-axis, in.³.
    Sx: Quantity
    #: Radius of gyration about the x-axis, in.
    rx: Quantity
    #: Moment of inertia about the y-axis, in.⁴.
    Iy: Quantity
    #: Plastic section modulus about the y-axis, in.³.
    Zy: Quantity
    #: Elastic section modulus about the y-axis, in.³.
    Sy: Quantity
    #: Radius of gyration about the y-axis, in.
    ry: Quantity
    #: Torsional constant, in.⁴.
    J: Quantity
    #: Warping constant, in.⁶.
    Cw: Quantity
    #: Polar radius of gyration about the shear center, in.
    ro: Quantity
    #: Flexural constant.
    H: float
    #: Shape perimeter minus one flange surface (short leg surface for a single angle), as used in Design Guide 19, in.
    PA: Quantity
    #: Shape perimeter, as used in Design Guide 19, in.
    PB: Quantity
    #: Box perimeter minus one flange surface, as used in Design Guide 19, in.
    PC: Quantity
    #: Box perimeter, as used in Design Guide 19, in.
    PD: Quantity
    #: Workable gage for the inner fastener holes in the flange, in.
    WGi: Quantity
    #: Bolt spacing between inner and outer fastener holes when the workable gage fits four holes across the flange, in.
    WGo: Quantity | None

    def classify_compression(self) -> SectionClassification:
        """Flange Case 1 (0.56 sqrt(E/Fy)) and stem Case 4 (0.75 sqrt(E/Fy)) (Table B4.1a)."""
        return super().classify_compression()

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Flange Case 10 and stem Case 14 (0.84 and 1.52 sqrt(E/Fy)) about the x-axis (Section F9); the y-axis checks the flange only (Table B4.1b)."""
        return super().classify_flexure(axis)
