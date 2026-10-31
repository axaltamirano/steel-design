"""Single angle (L) shapes from the AISC Shapes Database."""

from __future__ import annotations

import math
from functools import cached_property

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
from steel_design.flexure import (
    ANGLE_CB_LIMIT,
    FlexureStrength,
    check_Cb,
    geometric_axis_mcr,
    principal_axis_mcr,
    single_angle_strength,
)
from steel_design.sections.database import DatabaseShape
from steel_design.units import Q_
from steel_design.shear import KV_LEG, ShearStrength, plate_shear


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

    @cached_property
    def beta_w(self) -> Quantity:
        """Section property ``beta_w`` for the major principal axis (Commentary to Section F10),
        ``(1/Iw) * integral of z (w^2 + z^2) dA - 2 zo``, as a magnitude in inches.

        The Shapes Database does not list ``beta_w``; it is integrated here over the two legs as
        rectangles of thickness ``t`` (fillets and toe radii ignored) from the database ``x``,
        ``y``, ``tan(alpha)`` and ``Iw``, with the shear center at the heel. The result is an
        approximation that should agree with the Steel Construction Manual value to within a
        few percent. It is zero for equal-leg angles. Section F10 takes it as positive with the
        short legs in compression and negative with the long legs in compression, which
        :meth:`flexure_strength` applies. Pass ``beta_w`` to override it.
        """
        b, d, t = (self.b.to("in").m, self.d.to("in").m, self.t.to("in").m)
        if math.isclose(b, d):
            return Q_(0.0, "in")
        xc, yc = self.x.to("in").m, self.y.to("in").m
        alpha = math.atan(self.tan_alpha)

        def principal(x: float, y: float) -> tuple[float, float]:
            dx, dy = x - xc, y - yc
            return dx * math.cos(alpha) + dy * math.sin(alpha), -dx * math.sin(alpha) + dy * math.cos(alpha)

        # The long leg runs along y and the short leg along x, from the heel at the origin;
        # two-point Gauss quadrature is exact for the cubic integrand.
        gauss = (-1 / math.sqrt(3), 1 / math.sqrt(3))
        total = 0.0
        for x0, x1, y0, y1 in ((0.0, t, 0.0, b), (t, d, 0.0, t)):
            hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
            for gx in gauss:
                for gy in gauss:
                    w, z = principal((x0 + x1) / 2 + hx * gx, (y0 + y1) / 2 + hy * gy)
                    total += z * (w * w + z * z) * hx * hy
        _, z_shear_center = principal(t / 2, t / 2)
        return Q_(abs(total / self.Iw.to("in**4").m - 2 * z_shear_center), "in")

    def get_Mnw(self, Lb=None, Cb: float = 1.0, **options):
        """Nominal flexural strength about the major principal axis, in kip-ft. See :meth:`flexure_strength`."""
        return self.flexure_strength("w", Lb, Cb, **options).governing.Mn.to("kip*ft")

    def get_phiMnw(self, Lb=None, Cb: float = 1.0, **options):
        """Design flexural strength about the major principal axis, in kip-ft. See :meth:`flexure_strength`."""
        return self.flexure_strength("w", Lb, Cb, **options).design_strength.to("kip*ft")

    def get_Mnz(self, Lb=None, Cb: float = 1.0, **options):
        """Nominal flexural strength about the minor principal axis, in kip-ft. See :meth:`flexure_strength`."""
        return self.flexure_strength("z", Lb, Cb, **options).governing.Mn.to("kip*ft")

    def get_phiMnz(self, Lb=None, Cb: float = 1.0, **options):
        """Design flexural strength about the minor principal axis, in kip-ft. See :meth:`flexure_strength`."""
        return self.flexure_strength("z", Lb, Cb, **options).design_strength.to("kip*ft")

    def flexure_strength(
        self,
        axis: str = "w",
        Lb=None,
        Cb: float = 1.0,
        compression_leg: str = "long",
        toe_in_compression: bool = True,
        lateral_restraint: bool = False,
        beta_w=None,
    ) -> FlexureStrength:
        """Flexural strength of a single angle per AISC 360-22 Section F10.

        Limit states are yielding (``1.5 My``), lateral-torsional buckling (about the major
        principal axis and, for equal-leg angles, the geometric axes) and leg local buckling
        for legs whose toe is in compression. Moment about both axes, or with axial force, is a
        Chapter H matter.

        Args:
            axis: ``"w"`` (major principal axis, default), ``"z"`` (minor principal axis), or
                ``"x"`` / ``"y"`` (geometric axes, equal-leg angles only).
            Lb: Unbraced length (pint length). Required for the ``"w"``, ``"x"`` and ``"y"`` axes.
            Cb: Lateral-torsional buckling modification factor, limited to 1.5 (Section F10.2).
            compression_leg: For ``"w"``: ``"long"`` (default, the conservative case, negative
                ``beta_w``) or ``"short"``, the leg whose toe is in flexural compression.
            toe_in_compression: For ``"z"``, ``"x"`` and ``"y"``: whether the toes are in
                flexural compression, which makes leg local buckling apply (default True). For
                the geometric axes it also selects Eq. F10-5a or F10-5b.
            lateral_restraint: For ``"x"`` and ``"y"``: lateral-torsional restraint at the point of
                maximum moment only (``Mcr`` increased by 1.25, full ``My``).
            beta_w: Override of :attr:`beta_w`, a pint length (signed as in Eq. F10-4).

        Raises:
            ValueError: For an invalid option, a missing ``Lb``, or geometric axes of an angle
                with unequal legs.
        """
        axis = axis.lower()
        if axis not in ("w", "z", "x", "y"):
            raise ValueError("axis must be 'w', 'z', 'x' or 'y'")
        if compression_leg not in ("long", "short"):
            raise ValueError("compression_leg must be 'long' or 'short'")
        Cb = min(check_Cb(Cb), ANGLE_CB_LIMIT)
        Fy = self.material.Fy
        leg = self.classify_flexure()["leg"]
        long_leg = flexure_element("long leg", float(self.b / self.t), leg.limit_p, leg.limit_r, leg.reference)
        short_leg = flexure_element("short leg", float(self.d / self.t), leg.limit_p, leg.limit_r, leg.reference)

        if axis == "z":
            My = Fy * min(s for s in (self.SzA, self.SzB, self.SzC) if s is not None)
            legs = {"short leg toe": (self.SzA, short_leg), "long leg toe": (self.SzC, long_leg)} if toe_in_compression else {}
            return single_angle_strength(self.material, "z", My=My, Cb=Cb, legs=legs)

        if Lb is None:
            raise ValueError(f"Lb is required for flexure about the {axis}-axis")
        if axis == "w":
            My = Fy * min(s for s in (self.SwA, self.SwB, self.SwC) if s is not None)
            bw = beta_w if beta_w is not None else (-self.beta_w if compression_leg == "long" else self.beta_w)
            Mcr = principal_axis_mcr(self.material.E, self.A, self.rz, self.t, Lb, Cb, bw)
            legs = {"long leg toe": (self.SwC, long_leg)} if compression_leg == "long" else {"short leg toe": (self.SwA, short_leg)}
            return single_angle_strength(self.material, "w", My=My, Cb=Cb, Mcr=Mcr, legs=legs)

        if not math.isclose(self.b.m, self.d.m):
            raise ValueError("Geometric-axis flexure applies to equal-leg angles only; use axis 'w' or 'z'")
        My = Fy * self.Sx
        Mcr = geometric_axis_mcr(self.material.E, self.b, self.t, Lb, Cb, toe_in_compression, lateral_restraint)
        ltb_My = My if lateral_restraint else 0.8 * My
        Sc = self.Sx if lateral_restraint else 0.8 * self.Sx
        legs = {"leg": (Sc, long_leg)} if toe_in_compression else {}
        return single_angle_strength(self.material, axis, My=My, Cb=Cb, ltb_My=ltb_My, Mcr=Mcr, legs=legs)

    def shear_strength(self, axis: str = "x", leg: str = "long") -> ShearStrength:
        """Shear strength per AISC 360-22 Section G3 for the leg resisting the shear (``kv = 1.2``).

        Args:
            axis: ``"x"`` or ``"y"``. Accepted for a uniform interface; the leg is selected
                with ``leg``.
            leg: ``"long"`` or ``"short"``, the leg parallel to the shear force.

        Raises:
            ValueError: For an invalid ``axis`` or ``leg``.
        """
        check_axis(axis)
        if leg not in ("long", "short"):
            raise ValueError("leg must be 'long' or 'short'")
        b = max(self.d, self.b) if leg == "long" else min(self.d, self.b)
        return plate_shear(self.material, axis, length=b, thickness=self.t, kv=KV_LEG, reference="Eq. G3-1")
