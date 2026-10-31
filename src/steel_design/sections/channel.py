"""American standard channel (C) shapes."""

from __future__ import annotations

from pint import Quantity

from steel_design.classification import (
    check_axis,
    compression_element,
    flexure_element,
    SectionClassification,
    sqrt_E_Fy,
)
from steel_design.sections.database import DatabaseShape


class Channel(DatabaseShape):
    """American standard channel (C), e.g. ``C15X50``."""

    family = "C"

    #: Shape designation per the AISC EDI naming convention.
    EDI_Std_Nomenclature: str
    #: Shape designation as shown in the Steel Construction Manual.
    AISC_Manual_Label: str
    #: Nominal weight per unit length, lb/ft.
    weight: Quantity
    #: Cross-sectional area, in.².
    A: Quantity
    #: Overall depth of member, in.
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
    #: Horizontal distance from the designated edge (Manual Part 1) to the center of gravity, in.
    x: Quantity
    #: Horizontal distance from the designated edge (Manual Part 1) to the shear center, in.
    eo: Quantity
    #: Horizontal distance from the designated edge (Manual Part 1) to the plastic neutral axis, in.
    xp: Quantity
    #: Flange slenderness ratio, bf/tf.
    b_t: float
    #: Web slenderness ratio, h/tw.
    h_tw: float
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
    #: Normalized warping function, as used in Design Guide 9, in.².
    Wno: Quantity
    #: Warping statical moment at point 1 of the cross section (Design Guide 9), in.⁴.
    Sw1: Quantity
    #: Warping statical moment at point 2 of the cross section (Design Guide 9), in.⁴.
    Sw2: Quantity
    #: Warping statical moment at point 3 of the cross section (Design Guide 9), in.⁴.
    Sw3: Quantity
    #: Statical moment for a point in the flange directly above the vertical edge of the web (Design Guide 9), in.³.
    Qf: Quantity
    #: Statical moment for a point at mid-depth of the cross section (Design Guide 9), in.³.
    Qw: Quantity
    #: Polar radius of gyration about the shear center, in.
    ro: Quantity
    #: Flexural constant.
    H: float
    #: Effective radius of gyration for lateral-torsional buckling, in.
    rts: Quantity
    #: Distance between the flange centroids, in.
    ho: Quantity
    #: Shape perimeter minus one flange surface (short leg surface for a single angle), as used in Design Guide 19, in.
    PA: Quantity
    #: Shape perimeter, as used in Design Guide 19, in.
    PB: Quantity
    #: Box perimeter minus one flange surface, as used in Design Guide 19, in.
    PC: Quantity
    #: Box perimeter, as used in Design Guide 19, in.
    PD: Quantity
    #: Distance between web toes of fillets at top and bottom of web, in.
    T: Quantity
    #: Workable gage for the inner fastener holes in the flange, in.
    WGi: Quantity | None

    def classify_compression(self) -> SectionClassification:
        """Flange Case 1 (0.56 sqrt(E/Fy)) and web Case 5 (1.49 sqrt(E/Fy)) (Table B4.1a)."""
        r = sqrt_E_Fy(self.material)
        return SectionClassification(
            (
                compression_element("flange", self.b_t, 0.56 * r, "Table B4.1a Case 1"),
                compression_element("web", self.h_tw, 1.49 * r, "Table B4.1a Case 5"),
            )
        )

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Major axis: flange Case 10 (0.38 and 1.0 sqrt(E/Fy)) and web Case 15 (3.76 and 5.70
        sqrt(E/Fy)). Minor axis: flange Case 13 only (Table B4.1b)."""
        axis = check_axis(axis)
        r = sqrt_E_Fy(self.material)
        if axis == "y":  # minor-axis bending: the web is not in flexure
            return SectionClassification(
                (flexure_element("flange", self.b_t, 0.38 * r, 1.0 * r, "Table B4.1b Case 13"),)
            )
        return SectionClassification(
            (
                flexure_element("flange", self.b_t, 0.38 * r, 1.0 * r, "Table B4.1b Case 10"),
                flexure_element("web", self.h_tw, 3.76 * r, 5.70 * r, "Table B4.1b Case 15"),
            )
        )
