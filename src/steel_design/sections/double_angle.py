"""Double angle (2L) shapes."""

from __future__ import annotations

import re
from functools import cached_property

from pint import Quantity

from steel_design.compression import (
    OTHER_ELEMENTS,
    elastic_buckling_stress,
    flexural_buckling_mode,
    flexural_torsional_buckling_mode,
    slender_element,
)
from steel_design.units import Q_
from steel_design.classification import (
    check_axis,
    compression_element,
    flexure_element,
    SectionClassification,
    sqrt_E_Fy,
)
from steel_design.materials.base import SteelMaterial
from steel_design.sections.angle import Angle
from steel_design.sections.database import DatabaseShape


class DoubleAngle(DatabaseShape):
    """Double angles, back to back (2L), one database row per back-to-back spacing and
    configuration, e.g. ``2L4X4X1/2X3/8LLBB``.

    ``continuous_contact`` records how the outstanding legs are connected: False (default) for
    angles with separators or intermittent connectors (Table B4.1a Case 3), True for angles
    connected with continuous contact (Table B4.1a Case 1)."""

    family = "2L"

    #: Shape designation per the AISC EDI naming convention.
    EDI_Std_Nomenclature: str
    #: Shape designation as shown in the Steel Construction Manual.
    AISC_Manual_Label: str
    #: Nominal weight per unit length of the pair, lb/ft.
    weight: Quantity
    #: Cross-sectional area of the pair, in.².
    A: Quantity
    #: Width of the legs that are back to back, in.
    d: Quantity
    #: Width of the outstanding legs, in.
    b: Quantity
    #: Thickness of angle leg, in.
    t: Quantity
    #: Vertical distance from the designated edge (Manual Part 1) to the center of gravity, in.
    y: Quantity
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
    #: Radius of gyration about the y-axis, including the back-to-back separation, in.
    ry: Quantity
    #: Polar radius of gyration about the shear center, in.
    ro: Quantity
    #: Flexural constant.
    H: float

    def __init__(
        self,
        label: str,
        material: type[SteelMaterial] | None = None,
        continuous_contact: bool = False,
    ):
        """See :class:`DatabaseShape`; ``continuous_contact`` selects the Table B4.1a case."""
        super().__init__(label, material)
        self.continuous_contact = continuous_contact

    def classify_compression(self) -> SectionClassification:
        """Outstanding legs: Case 1 (0.56 sqrt(E/Fy)) with continuous contact, otherwise Case 3
        (0.45 sqrt(E/Fy)). The database ``b/t`` uses the longer leg, which governs."""
        if self.continuous_contact:
            limit, ref = 0.56 * sqrt_E_Fy(self.material), "Table B4.1a Case 1"
        else:
            limit, ref = 0.45 * sqrt_E_Fy(self.material), "Table B4.1a Case 3"
        return SectionClassification((compression_element("leg", self.b_t, limit, ref),))

    @cached_property
    def J(self):
        """Torsional constant, twice that of one angle (the single angle is read from the
        database; the AISC database gives no J for double angles)."""
        parts = re.sub(r"(LLBB|SLBB)$", "", self.name[2:]).split("X")
        return 2 * Angle("L" + "X".join(parts[:3])).J

    def buckling_modes(self, Lcx, Lcy, Lcz):
        """Flexural buckling about x (Eq. E3-4) and flexural-torsional buckling about the axis of
        symmetry y (Eqs. E4-3 and E4-7), omitting the warping term as permitted for double angles."""
        E, G = self.material.E, self.material.G
        Fey = elastic_buckling_stress(E, Lcy, self.ry)
        return (
            flexural_buckling_mode("x-axis", E, Lcx, self.rx),
            flexural_torsional_buckling_mode(E, G, Q_(0, "in**6"), self.J, Lcz, self.A, self.ro, self.H, Fey),
        )

    def slender_elements(self):
        """Outstanding legs ``b`` and back-to-back legs ``d`` (two of each), unstiffened (Table E7.1 (c))."""
        limit = self.compression_slenderness["leg"].limit_r
        return (
            slender_element("outstanding leg", self.b, self.t, 2, limit, OTHER_ELEMENTS),
            slender_element("back-to-back leg", self.d, self.t, 2, limit, OTHER_ELEMENTS),
        )

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Leg Case 12 (0.54 and 0.91 sqrt(E/Fy)) (Table B4.1b). Double angles reuse the
        single-angle limits."""
        check_axis(axis)
        r = sqrt_E_Fy(self.material)
        return SectionClassification(
            (flexure_element("leg", self.b_t, 0.54 * r, 0.91 * r, "Table B4.1b Case 12"),)
        )
