"""Single angle (L) shapes from the AISC Shapes Database."""

from __future__ import annotations

from pint import Quantity

from steel_design.classification import SectionClassification, compression_element, sqrt_E_Fy
from steel_design.sections.shape_groups import AngleShape


class Angle(AngleShape):
    """Single angle (L), e.g. ``L4X4X1/2``."""

    family = "L"

    #: Shape designation per the AISC EDI naming convention.
    EDI_Std_Nomenclature: str
    #: Shape designation as shown in the Steel Construction Manual.
    AISC_Manual_Label: str
    #: Nominal weight per unit length, lb/ft.
    weight: Quantity
    #: Cross-sectional area, in.².
    A: Quantity
    #: Width of the longer leg, in.
    d: Quantity
    #: Width of the shorter leg, in.
    b: Quantity
    #: Thickness of angle leg, in.
    t: Quantity
    #: Distance from outer face of leg to toe of fillet, used for design, in.
    kdes: Quantity
    #: Distance from outer face of leg to toe of fillet, used for detailing, in.
    kdet: Quantity
    #: Horizontal distance from the designated edge (Manual Part 1) to the center of gravity, in.
    x: Quantity
    #: Vertical distance from the designated edge (Manual Part 1) to the center of gravity, in.
    y: Quantity
    #: Horizontal distance from the designated edge (Manual Part 1) to the plastic neutral axis, in.
    xp: Quantity
    #: Vertical distance from the designated edge (Manual Part 1) to the plastic neutral axis, in.
    yp: Quantity
    #: Leg slenderness ratio, b/t.
    b_t: float
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
    #: Moment of inertia about the z-axis, in.⁴.
    Iz: Quantity
    #: Radius of gyration about the z-axis, in.
    rz: Quantity
    #: Elastic section modulus about the z-axis. For single angles, see SzA, SzB and SzC, in.³.
    Sz: Quantity
    #: Torsional constant, in.⁴.
    J: Quantity
    #: Warping constant, in.⁶.
    Cw: Quantity
    #: Polar radius of gyration about the shear center, in.
    ro: Quantity
    #: Flexural constant.
    H: float | None
    #: Tangent of the angle between the y-y and z-z axes.
    tan_alpha: float
    #: Moment of inertia about the w-axis, in.⁴.
    Iw: Quantity
    #: Distance from point A to the center of gravity along the z-axis (Manual Figure 3), in.
    zA: Quantity
    #: Distance from point B to the center of gravity along the z-axis (Manual Figure 3), in.
    zB: Quantity
    #: Distance from point C to the center of gravity along the z-axis (Manual Figure 3), in.
    zC: Quantity
    #: Distance from point A to the center of gravity along the w-axis (Manual Figure 3), in.
    wA: Quantity
    #: Distance from point B to the center of gravity along the w-axis (Manual Figure 3), in.
    wB: Quantity
    #: Distance from point C to the center of gravity along the w-axis (Manual Figure 3), in.
    wC: Quantity
    #: Elastic section modulus about the w-axis at point A of the cross section (Manual Figure 3), in.³.
    SwA: Quantity
    #: Elastic section modulus about the w-axis at point B of the cross section (Manual Figure 3), in.³.
    SwB: Quantity | None
    #: Elastic section modulus about the w-axis at point C of the cross section (Manual Figure 3), in.³.
    SwC: Quantity
    #: Elastic section modulus about the z-axis at point A of the cross section (Manual Figure 3), in.³.
    SzA: Quantity
    #: Elastic section modulus about the z-axis at point B of the cross section (Manual Figure 3), in.³.
    SzB: Quantity
    #: Elastic section modulus about the z-axis at point C of the cross section (Manual Figure 3), in.³.
    SzC: Quantity
    #: Shape perimeter minus one flange surface (short leg surface for a single angle), as used in Design Guide 19, in.
    PA: Quantity
    #: Single angle shape perimeter minus long leg surface, as used in Design Guide 19, in.
    PA2: Quantity
    #: Shape perimeter, as used in Design Guide 19, in.
    PB: Quantity

    def classify_compression(self) -> SectionClassification:
        """Leg Case 3 (0.45 sqrt(E/Fy)) of Table B4.1a."""
        return SectionClassification(
            (compression_element("leg", self.b_t, 0.45 * sqrt_E_Fy(self.material), "Table B4.1a Case 3"),)
        )
