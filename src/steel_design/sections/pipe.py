"""Steel pipe shapes."""

from __future__ import annotations

from pint import Quantity

from steel_design.classification import SectionClassification
from steel_design.sections.shape_groups import RoundTubeShape


class Pipe(RoundTubeShape):
    """Standard-weight, extra-strong or double-extra-strong pipe, e.g. ``Pipe6STD``."""

    family = "PIPE"

    #: Shape designation per the AISC EDI naming convention.
    EDI_Std_Nomenclature: str
    #: Shape designation as shown in the Steel Construction Manual.
    AISC_Manual_Label: str
    #: Nominal weight per unit length, lb/ft.
    weight: Quantity
    #: Cross-sectional area, in.².
    A: Quantity
    #: Outside diameter, in.
    OD: Quantity
    #: Inside diameter, in.
    ID: Quantity
    #: Nominal wall thickness, in.
    tnom: Quantity
    #: Design wall thickness, in.
    tdes: Quantity
    #: Slenderness ratio, OD/tdes.
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

    def classify_compression(self) -> SectionClassification:
        """Wall Case 9 (0.11 E/Fy) (Table B4.1a)."""
        return super().classify_compression()

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Wall Case 20 (0.07 and 0.31 E/Fy); independent of axis (Table B4.1b)."""
        return super().classify_flexure(axis)
