"""Single angle (L) shapes from the AISC Shapes Database."""

from __future__ import annotations

import math

from pint import Quantity

from steel_design.compression import (
    BucklingMode,
    OTHER_ELEMENTS,
    flexural_buckling_mode,
    single_angle_effective_slenderness,
    slender_element,
)
from steel_design.units import require_length
from steel_design.classification import (
    check_axis,
    compression_element,
    flexure_element,
    SectionClassification,
    sqrt_E_Fy,
)
from steel_design.sections.database import DatabaseShape


class Angle(DatabaseShape):
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
    #: Width of the shorter leg, in.
    d: Quantity
    #: Width of the longer leg, in.
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

    def buckling_modes(self, Lcx, Lcy, Lcz):
        """Flexural buckling about the major (``Lcx``) and minor (``Lcz`` is unused, ``Lcy``)
        principal axes (Eq. E3-4). Flexural-torsional buckling is not checked: it only matters
        when ``b/t > 0.71 sqrt(E/Fy)``, and such an angle is slender, for which Section E7 takes
        ``Fn`` from Section E3 only."""
        E = self.material.E
        return (
            flexural_buckling_mode("major principal axis", E, Lcx, (self.Iw / self.A) ** 0.5),
            flexural_buckling_mode("minor principal axis", E, Lcy, self.rz),
        )

    def slender_elements(self):
        """Longer leg ``b`` and shorter leg ``d``, both unstiffened (Table E7.1 (c))."""
        limit = self.compression_slenderness["leg"].limit_r
        return (
            slender_element("long leg", self.b, self.t, 1, limit, OTHER_ELEMENTS),
            slender_element("short leg", self.d, self.t, 1, limit, OTHER_ELEMENTS),
        )

    def get_Pnc(self, L, K: float = 1.0, e5: str | None = None, connected_leg: str = "long"):
        """Nominal compressive strength ``Pn`` of the governing limit state, in kips.
        See :meth:`compression_strength` for the arguments."""
        return self.compression_strength(L, K, e5, connected_leg).governing.Pn.to("kip")

    def get_phiPnc(self, L, K: float = 1.0, e5: str | None = None, connected_leg: str = "long"):
        """Governing compressive design strength ``phi_c Pn``, in kips.
        See :meth:`compression_strength` for the arguments."""
        return self.compression_strength(L, K, e5, connected_leg).design_strength.to("kip")

    def compression_strength(self, L, K: float = 1.0, e5: str | None = None, connected_leg: str = "long"):
        """Compressive strength of a single angle (Chapter E).

        Args:
            L: Unbraced length (pint length). For ``e5`` it is the length between work points.
            K: Effective length factor.
            e5: ``None`` for flexural buckling about the principal axes with ``K L``, or use the
                effective slenderness of Section E5: ``"planar"`` for individual members and
                planar truss webs (E5(a)) or ``"box"`` for box and space truss webs (E5(b)).
                The user is responsible for the E5 conditions on end connection and loading.
            connected_leg: ``"long"`` or ``"short"`` leg connected, for ``e5``.

        Raises:
            ValueError: With ``e5``, if ``bl/bs >= 1.7`` or the effective slenderness exceeds 200.
        """
        L = require_length(L, "L")
        if L.magnitude <= 0 or K <= 0:
            raise ValueError("L and K must be positive")
        if e5 is None:
            return self._compression(self.buckling_modes(K * L, K * L, K * L))
        ra = self.rx if connected_leg == "long" else self.ry
        ratio = single_angle_effective_slenderness(L, ra, self.rz, self.b, self.d, e5, connected_leg)
        Fe = math.pi**2 * self.material.E / ratio**2
        eq = "Eq. E5-1/E5-2" if e5 == "planar" else "Eq. E5-3/E5-4"
        return self._compression((BucklingMode("flexural buckling, effective slenderness", Fe.to("ksi"), eq, ratio),))

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Leg Case 12 (0.54 and 0.91 sqrt(E/Fy)) (Table B4.1b). Double angles reuse the
        single-angle limits."""
        check_axis(axis)
        r = sqrt_E_Fy(self.material)
        return SectionClassification(
            (flexure_element("leg", self.b_t, 0.54 * r, 0.91 * r, "Table B4.1b Case 12"),)
        )
