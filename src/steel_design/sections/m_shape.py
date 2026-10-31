"""Miscellaneous (M) shapes."""

from __future__ import annotations

from pint import Quantity

from steel_design.sections.shape_groups import RolledIShape


class MShape(RolledIShape):
    """Miscellaneous I-shape (M), e.g. ``M12X10``."""

    family = "M"

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
    #: Distance from web centerline to flange toe of fillet, used for detailing, in.
    k1: Quantity
    #: Flange slenderness ratio, bf/2tf.
    bf_2tf: float
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
    #: Statical moment for a point in the flange directly above the vertical edge of the web (Design Guide 9), in.³.
    Qf: Quantity
    #: Statical moment for a point at mid-depth of the cross section (Design Guide 9), in.³.
    Qw: Quantity
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
