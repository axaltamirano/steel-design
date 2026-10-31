"""Built-up (plate-fabricated) I-shaped section, doubly or singly symmetric."""

from __future__ import annotations

import math
from functools import cached_property

from steel_design.compression import (
    OTHER_ELEMENTS,
    STIFFENED_ELEMENTS,
    elastic_buckling_stress,
    flexural_buckling_mode,
    flexural_torsional_buckling_mode,
    slender_element,
    torsional_buckling_mode,
)
from steel_design.classification import (
    SectionClassification,
    Slenderness,
    check_axis,
    compression_element,
    E_Fy,
    flexure_element,
    kc,
    sqrt_E_Fy,
)
from steel_design.flexure import (
    FlexureStrength,
    i_shape_major_axis_f2_f3,
    i_shape_major_axis_f4_f5,
    i_shape_minor_axis,
)
from steel_design.materials.base import SteelMaterial
from steel_design.materials.defaults import default_material_for
from steel_design.sections.base import Section
from steel_design.units import Q_, require_length


def _abs_moment(y0: float, y1: float, yp: float) -> float:
    """Integral of |y - yp| dy over [y0, y1]."""
    if yp <= y0:
        return ((y1 - yp) ** 2 - (y0 - yp) ** 2) / 2
    if yp >= y1:
        return ((yp - y0) ** 2 - (yp - y1) ** 2) / 2
    return ((yp - y0) ** 2 + (y1 - yp) ** 2) / 2
from dataclasses import replace
from steel_design.shear import KV_LEG, ShearStrength, i_shape_web_shear, plate_shear


class BuiltUpWideFlange(Section):
    """I-shape from three plates, with no fillets (welds ignored).

    Parameters are pint length quantities: overall depth `d`, web thickness `tw`, and the
    top flange `bf` x `tf`. The bottom flange defaults to the top flange (doubly symmetric);
    pass `bf_bottom` and/or `tf_bottom` for a singly symmetric section. Flanges are centered
    on the web. Property names match the AISC database where one exists.
    """

    family = "BUILT_UP_WF"

    def __init__(
        self,
        d,
        bf,
        tf,
        tw,
        material: type[SteelMaterial] | None = None,
        name: str | None = None,
        bf_bottom=None,
        tf_bottom=None,
    ):
        """Create an I-shape.

        Args:
            d: Overall depth (length quantity).
            bf: Top flange width (length quantity).
            tf: Top flange thickness (length quantity).
            tw: Web thickness (length quantity).
            material: Material class; defaults to the ``BUILT_UP_WF`` default.
            name: Optional label; generated from the dimensions when omitted.
            bf_bottom: Bottom flange width; defaults to ``bf``.
            tf_bottom: Bottom flange thickness; defaults to ``tf``.

        Raises:
            TypeError: If a dimension is not a pint quantity.
            ValueError: If a dimension is non-positive or the plates do not fit together.
        """
        self.d = require_length(d, "d")
        self.bf = require_length(bf, "bf")
        self.tf = require_length(tf, "tf")
        self.tw = require_length(tw, "tw")
        self.bf_bottom = self.bf if bf_bottom is None else require_length(bf_bottom, "bf_bottom")
        self.tf_bottom = self.tf if tf_bottom is None else require_length(tf_bottom, "tf_bottom")
        dims = (self.d, self.bf, self.tf, self.tw, self.bf_bottom, self.tf_bottom)
        if min(x.m for x in dims) <= 0:
            raise ValueError("All dimensions must be positive")
        if self.tf + self.tf_bottom >= self.d:
            raise ValueError("Flanges must be thinner than the overall depth d")
        if self.tw >= min(self.bf, self.bf_bottom):
            raise ValueError("Web thickness tw must be less than both flange widths")
        self.material = material or default_material_for(self.family)
        if name is None:
            flange = f"{self.bf.m:g}x{self.tf.m:g}"
            if not self.is_doubly_symmetric:
                flange += f"/{self.bf_bottom.m:g}x{self.tf_bottom.m:g}"
            name = f"PG{self.d.m:g}x{self.tw.m:g}/{flange}"
        self.name = name

    # --- plain-inch geometry used by the property formulas -------------------------

    @cached_property
    def _g(self) -> dict[str, float]:
        """Dimensions as plain inch floats; keys d, tw, bt/tt (top flange), bb/tb (bottom flange), h."""
        d, tw = self.d.to("in").m, self.tw.to("in").m
        bt, tt = self.bf.to("in").m, self.tf.to("in").m
        bb, tb = self.bf_bottom.to("in").m, self.tf_bottom.to("in").m
        return {"d": d, "tw": tw, "bt": bt, "tt": tt, "bb": bb, "tb": tb, "h": d - tt - tb}

    @cached_property
    def _pieces(self) -> list[tuple[float, float, float]]:
        """(width, y0, y1) of each plate, measured up from the bottom of the section."""
        g = self._g
        return [
            (g["bb"], 0.0, g["tb"]),
            (g["tw"], g["tb"], g["tb"] + g["h"]),
            (g["bt"], g["tb"] + g["h"], g["d"]),
        ]

    @cached_property
    def _area(self) -> float:
        """Area in square inches."""
        return sum(w * (y1 - y0) for w, y0, y1 in self._pieces)

    @cached_property
    def _ybar(self) -> float:
        """Elastic centroid, measured from the bottom face."""
        return sum(w * (y1 - y0) * (y0 + y1) / 2 for w, y0, y1 in self._pieces) / self._area

    @cached_property
    def _yp(self) -> float:
        """Plastic neutral axis, measured from the bottom face."""
        half, acc = self._area / 2, 0.0
        for w, y0, y1 in self._pieces:
            if acc + w * (y1 - y0) >= half:
                return y0 + (half - acc) / w
            acc += w * (y1 - y0)
        raise AssertionError("unreachable")

    @cached_property
    def _Ix(self) -> float:
        """Major-axis moment of inertia in in^4, by the parallel-axis theorem."""
        return sum(
            w * (y1 - y0) ** 3 / 12 + w * (y1 - y0) * ((y0 + y1) / 2 - self._ybar) ** 2
            for w, y0, y1 in self._pieces
        )

    @cached_property
    def _Iy(self) -> float:
        """Minor-axis moment of inertia in in^4."""
        g = self._g
        return (g["tt"] * g["bt"] ** 3 + g["tb"] * g["bb"] ** 3 + g["h"] * g["tw"] ** 3) / 12

    # --- geometry ------------------------------------------------------------------

    @cached_property
    def is_doubly_symmetric(self) -> bool:
        """True when the top and bottom flanges have equal width and thickness."""
        return bool(self.bf == self.bf_bottom and self.tf == self.tf_bottom)

    @cached_property
    def h(self):
        """Clear distance between flanges."""
        return Q_(self._g["h"], "in")

    @cached_property
    def ho(self):
        """Distance between flange centroids."""
        g = self._g
        return Q_(g["d"] - (g["tt"] + g["tb"]) / 2, "in")

    # --- section properties --------------------------------------------------------

    @cached_property
    def A(self):
        """Cross-sectional area."""
        return Q_(self._area, "in**2")

    @cached_property
    def weight(self):
        """Weight per unit length, from the material unit weight."""
        return (self.A * self.material.density).to("lbf/ft")

    @cached_property
    def y_bar(self):
        """Elastic neutral axis, measured from the bottom face."""
        return Q_(self._ybar, "in")

    @cached_property
    def y_p(self):
        """Plastic neutral axis, measured from the bottom face."""
        return Q_(self._yp, "in")

    @cached_property
    def Ix(self):
        """Moment of inertia about the x-axis (strong axis)."""
        return Q_(self._Ix, "in**4")

    @cached_property
    def Sx_top(self):
        """Elastic section modulus referred to the top flange."""
        return Q_(self._Ix / (self._g["d"] - self._ybar), "in**3")

    @cached_property
    def Sx_bottom(self):
        """Elastic section modulus referred to the bottom flange."""
        return Q_(self._Ix / self._ybar, "in**3")

    @cached_property
    def Sx(self):
        """Smaller of the two elastic moduli (first yield)."""
        return min(self.Sx_top, self.Sx_bottom)

    @cached_property
    def Zx(self):
        """Plastic section modulus about the x-axis, taken about the plastic neutral axis."""
        return Q_(sum(w * _abs_moment(y0, y1, self._yp) for w, y0, y1 in self._pieces), "in**3")

    @cached_property
    def Iy(self):
        """Moment of inertia about the y-axis (weak axis)."""
        return Q_(self._Iy, "in**4")

    @cached_property
    def Sy(self):
        """Elastic section modulus about the y-axis, referred to the wider flange."""
        return Q_(2 * self._Iy / max(self._g["bt"], self._g["bb"]), "in**3")

    @cached_property
    def Zy(self):
        """Plastic section modulus about the y-axis."""
        g = self._g
        return Q_((g["tt"] * g["bt"] ** 2 + g["tb"] * g["bb"] ** 2 + g["h"] * g["tw"] ** 2) / 4, "in**3")

    @cached_property
    def rx(self):
        """Radius of gyration about the x-axis."""
        return ((self.Ix / self.A) ** 0.5).to("in")

    @cached_property
    def ry(self):
        """Radius of gyration about the y-axis."""
        return ((self.Iy / self.A) ** 0.5).to("in")

    @cached_property
    def J(self):
        """Torsional constant, sum of b*t^3/3 over the three plates."""
        g = self._g
        return Q_((g["bt"] * g["tt"] ** 3 + g["bb"] * g["tb"] ** 3 + g["h"] * g["tw"] ** 3) / 3, "in**4")

    @cached_property
    def Cw(self):
        """Warping constant. The web's Iy is split equally between the flanges, which reduces
        to Iy*ho^2/4 for doubly symmetric sections."""
        g = self._g
        iyw = g["h"] * g["tw"] ** 3 / 12
        it = g["tt"] * g["bt"] ** 3 / 12 + iyw / 2
        ib = g["tb"] * g["bb"] ** 3 / 12 + iyw / 2
        return Q_(it * ib / (it + ib) * self.ho.m**2, "in**6")

    @cached_property
    def rts(self):
        """Effective radius of gyration for LTB, AISC 360-22 Eq. F2-7 (doubly symmetric only)."""
        if not self.is_doubly_symmetric:
            raise NotImplementedError("rts (Eq. F2-7) applies to doubly symmetric sections; use rt from Sect. F4")
        return (((self.Iy * self.Cw) ** 0.5 / self.Sx) ** 0.5).to("in")

    @cached_property
    def bf_2tf(self):
        """Top-flange slenderness; see `bf_2tf_bottom` for the bottom flange."""
        return float(self.bf / (2 * self.tf))

    @cached_property
    def bf_2tf_bottom(self):
        """Bottom-flange slenderness, ``bf_bottom / (2 tf_bottom)`` (dimensionless)."""
        return float(self.bf_bottom / (2 * self.tf_bottom))

    @cached_property
    def h_tw(self):
        """Web slenderness, clear height ``h`` over ``tw`` (dimensionless)."""
        return float(self.h / self.tw)

    # --- web properties relative to the compression flange -------------------------

    def hc(self, compression_flange: str = "top"):
        """Twice the distance from the elastic centroid to the inside face of the compression flange.

        Args:
            compression_flange: ``"top"`` or ``"bottom"``.
        """
        return self._web_depth(compression_flange, self._ybar)

    def hp(self, compression_flange: str = "top"):
        """Twice the distance from the plastic neutral axis to the inside face of the compression flange.

        Args:
            compression_flange: ``"top"`` or ``"bottom"``.
        """
        return self._web_depth(compression_flange, self._yp)

    def _web_depth(self, compression_flange: str, y: float):
        """Twice the distance from height ``y`` (above the bottom face) to the inside face of the chosen flange."""
        g = self._g
        if compression_flange == "top":
            return Q_(2 * (g["d"] - g["tt"] - y), "in")
        if compression_flange == "bottom":
            return Q_(2 * (y - g["tb"]), "in")
        raise ValueError("compression_flange must be 'top' or 'bottom'")

    @cached_property
    def shear_center_offset(self):
        """Distance ``yo`` from the centroid to the shear center, positive toward the top flange.
        The shear center lies at ``ho It / (It + Ib)`` from the bottom flange centroid, using the
        same flange inertias as :attr:`Cw`."""
        g = self._g
        iyw = g["h"] * g["tw"] ** 3 / 12
        it = g["tt"] * g["bt"] ** 3 / 12 + iyw / 2
        ib = g["tb"] * g["bb"] ** 3 / 12 + iyw / 2
        return Q_(g["tb"] / 2 + self.ho.m * it / (it + ib) - self._ybar, "in")

    @cached_property
    def ro(self):
        """Polar radius of gyration about the shear center, ``sqrt(yo^2 + (Ix + Iy)/A)``."""
        return ((self.shear_center_offset**2 + (self.Ix + self.Iy) / self.A) ** 0.5).to("in")

    @cached_property
    def H(self):
        """Flexural constant, ``1 - yo^2/ro^2``."""
        return float(1 - (self.shear_center_offset / self.ro) ** 2)

    def buckling_modes(self, Lcx, Lcy, Lcz):
        """Flexural buckling about x and y (Eq. E3-4) plus torsional buckling (Eq. E4-2) when
        doubly symmetric, or flexural-torsional buckling about the axis of symmetry y
        (Eqs. E4-3 and E4-7) when singly symmetric."""
        E, G = self.material.E, self.material.G
        modes = [flexural_buckling_mode("x-axis", E, Lcx, self.rx)]
        if self.is_doubly_symmetric:
            modes.append(flexural_buckling_mode("y-axis", E, Lcy, self.ry))
            modes.append(torsional_buckling_mode(E, G, self.Cw, self.J, Lcz, self.Ix, self.Iy))
        else:
            Fey = elastic_buckling_stress(E, Lcy, self.ry)
            modes.append(
                flexural_torsional_buckling_mode(E, G, self.Cw, self.J, Lcz, self.A, self.ro, self.H, Fey)
            )
        return tuple(modes)

    def slender_elements(self):
        """Flanges (outstanding, Table E7.1 (c)) and web (``h``, stiffened, Table E7.1 (a))."""
        c = self.compression_slenderness
        if self.is_doubly_symmetric:
            return (
                slender_element("flange", self.bf / 2, self.tf, 4, c["flange"].limit_r, OTHER_ELEMENTS),
                slender_element("web", self.h, self.tw, 1, c["web"].limit_r, STIFFENED_ELEMENTS),
            )
        return (
            slender_element("top flange", self.bf / 2, self.tf, 2, c["top flange"].limit_r, OTHER_ELEMENTS),
            slender_element("bottom flange", self.bf_bottom / 2, self.tf_bottom, 2, c["bottom flange"].limit_r, OTHER_ELEMENTS),
            slender_element("web", self.h, self.tw, 1, c["web"].limit_r, STIFFENED_ELEMENTS),
        )

    def classify_compression(self) -> SectionClassification:
        """Flange Case 2 (0.64 sqrt(kc E/Fy)) of Table B4.1a.

        The web is Case 5 (1.49 sqrt(E/Fy)) when doubly symmetric and Case 8 otherwise. Singly
        symmetric sections report both flanges as ``"top flange"`` and ``"bottom flange"``.
        """
        r = sqrt_E_Fy(self.material)
        limit = 0.64 * math.sqrt(kc(self.h_tw)) * r
        if self.is_doubly_symmetric:
            return SectionClassification(
                (
                    compression_element("flange", self.bf_2tf, limit, "Table B4.1a Case 2"),
                    compression_element("web", self.h_tw, 1.49 * r, "Table B4.1a Case 5"),
                )
            )
        return SectionClassification(
            (
                compression_element("top flange", self.bf_2tf, limit, "Table B4.1a Case 2"),
                compression_element("bottom flange", self.bf_2tf_bottom, limit, "Table B4.1a Case 2"),
                compression_element("web", self.h_tw, 1.49 * r, "Table B4.1a Case 8"),
            )
        )

    def classify_flexure(self, axis: str = "x", compression_flange: str = "top") -> SectionClassification:
        """Flange Case 11 and web Case 15 (doubly symmetric) or Case 16 (singly symmetric) of Table B4.1b.

        Args:
            axis: ``"x"`` or ``"y"``. Minor-axis bending checks the flange(s) only, Case 13.
            compression_flange: ``"top"`` or ``"bottom"``, the flange in flexural compression for
                major-axis bending. It matters only for singly symmetric sections.

        Raises:
            ValueError: For an invalid ``axis`` or ``compression_flange``.
        """
        axis = check_axis(axis)
        if compression_flange not in ("top", "bottom"):
            raise ValueError("compression_flange must be 'top' or 'bottom'")
        e_fy, r = E_Fy(self.material), sqrt_E_Fy(self.material)

        if axis == "y":
            case13 = "Table B4.1b Case 13"
            if self.is_doubly_symmetric:
                return SectionClassification((flexure_element("flange", self.bf_2tf, 0.38 * r, 1.0 * r, case13),))
            return SectionClassification(
                (
                    flexure_element("top flange", self.bf_2tf, 0.38 * r, 1.0 * r, case13),
                    flexure_element("bottom flange", self.bf_2tf_bottom, 0.38 * r, 1.0 * r, case13),
                )
            )

        kc_ = kc(self.h_tw)
        lam_r_web = 5.70 * r
        if self.is_doubly_symmetric:
            web = flexure_element("web", self.h_tw, 3.76 * r, lam_r_web, "Table B4.1b Case 15")
            fl = 0.7
            flange_ratio = self.bf_2tf
        else:
            hc = self.hc(compression_flange).to("in").m
            hp = self.hp(compression_flange).to("in").m
            mp_my = float(self.Zx / self.Sx)
            lam_p = (hc / hp) * r / (0.54 * mp_my - 0.09) ** 2 if hp > 0 else lam_r_web
            web = flexure_element(
                "web", hc / self.tw.to("in").m, min(lam_p, lam_r_web), lam_r_web, "Table B4.1b Case 16"
            )
            fl = self._fl_ratio(compression_flange, web.classification is Slenderness.SLENDER)
            flange_ratio = self.bf_2tf if compression_flange == "top" else self.bf_2tf_bottom
        lam_r = 0.95 * math.sqrt(kc_ * e_fy / fl)
        flange = flexure_element("flange", flange_ratio, 0.38 * r, lam_r, "Table B4.1b Case 11")
        return SectionClassification((flange, web))

    def _fl_ratio(self, compression_flange: str, web_slender: bool) -> float:
        """FL / Fy per Table B4.1b footnote [b] and Eqs. F4-6a/b."""
        if web_slender:
            return 0.7
        sxc, sxt = (
            (self.Sx_top, self.Sx_bottom) if compression_flange == "top" else (self.Sx_bottom, self.Sx_top)
        )
        ratio = float(sxt / sxc)
        return 0.7 if ratio >= 0.7 else max(ratio, 0.5)

    @property
    def flexure_slenderness_x_bottom(self) -> SectionClassification:
        """Strong-axis flexure classification with the bottom flange in compression.

        :attr:`flexure_slenderness_x` assumes the top flange is in compression; the two differ
        only for singly symmetric sections.
        """
        return self.classify_flexure("x", compression_flange="bottom")

    def flexure_strength(
        self, axis: str = "x", Lb=None, Cb: float = 1.0, compression_flange: str = "top"
    ) -> FlexureStrength:
        """Flexural strength per AISC 360-22 Chapter F.

        Strong-axis bending of doubly symmetric sections with compact webs uses Sections F2 and F3.
        Other sections (noncompact or slender webs, or singly symmetric) use Sections F4 and F5,
        with the web and flange classifications of :meth:`classify_flexure`. Weak-axis bending
        uses Section F6, checking both flanges of a singly symmetric section.

        Args:
            axis: ``"x"`` or ``"y"``.
            Lb: Unbraced length (pint length), required for strong-axis bending.
            Cb: Lateral-torsional buckling modification factor; defaults to 1.0.
            compression_flange: ``"top"`` or ``"bottom"``, the flange in flexural compression
                for strong-axis bending. It matters only for singly symmetric sections, and
                members in reverse curvature need both cases checked (Section F1(d)).

        Raises:
            ValueError: For an invalid ``axis`` or ``compression_flange``, or a missing ``Lb``.
        """
        axis = check_axis(axis)
        c = self.classify_flexure(axis, compression_flange)
        if axis == "y":
            flanges = (
                {"flange": c["flange"]}
                if self.is_doubly_symmetric
                else {"top flange": c["top flange"], "bottom flange": c["bottom flange"]}
            )
            return i_shape_minor_axis(self.material, Zy=self.Zy, Sy=self.Sy, flanges=flanges)
        if Lb is None:
            raise ValueError("Lb is required for strong-axis flexure")
        web = c["web"]
        if self.is_doubly_symmetric and web.classification is Slenderness.COMPACT:
            return i_shape_major_axis_f2_f3(
                self.material, Lb, Cb, Zx=self.Zx, Sx=self.Sx, ry=self.ry, rts=self.rts, J=self.J,
                ho=self.ho, flange=c["flange"], h_tw=self.h_tw,
            )
        if self.is_doubly_symmetric:
            Sxc, Sxt, bfc, tfc, Iyc = self.Sx, self.Sx, self.bf, self.tf, self.Iy / 2
        elif compression_flange == "top":
            Sxc, Sxt, bfc, tfc = self.Sx_top, self.Sx_bottom, self.bf, self.tf
            Iyc = self.tf * self.bf**3 / 12
        else:
            Sxc, Sxt, bfc, tfc = self.Sx_bottom, self.Sx_top, self.bf_bottom, self.tf_bottom
            Iyc = self.tf_bottom * self.bf_bottom**3 / 12
        return i_shape_major_axis_f4_f5(
            self.material, Lb, Cb, Zx=self.Zx, Sxc=Sxc, Sxt=Sxt, Iy=self.Iy, Iyc=Iyc, J=self.J,
            ho=self.ho, tw=self.tw, bfc=bfc, tfc=tfc, h_tw=self.h_tw, flange=c["flange"], web=web,
        )

    def __repr__(self) -> str:
        return f"<BuiltUpWideFlange {self.name} ({self.material.name})>"

    def shear_strength(self, axis: str = "x", a=None) -> ShearStrength:
        """Shear strength per AISC 360-22 Chapter G.

        Strong-axis shear uses Section G2.1(b) (``phi_v = 0.90``, ``h`` the clear distance
        between flanges) and, with transverse stiffeners, G2.2. Minor-axis shear sums
        Section G6 over the two flanges.

        Args:
            axis: ``"x"`` for shear parallel to the web, ``"y"`` for shear parallel to the flanges.
            a: Clear distance between transverse stiffeners (pint length), if any.

        Raises:
            ValueError: For an invalid ``axis``.
        """
        if check_axis(axis) == "x":
            return i_shape_web_shear(
                self.material, "x", d=self.d, tw=self.tw, h=self.h, a=a,
                flanges=((self.bf, self.tf), (self.bf_bottom, self.tf_bottom)),
            )
        parts = [
            plate_shear(
                self.material, "y", length=bf, thickness=tf, kv=KV_LEG,
                slenderness=float(bf / (2 * tf)), reference="Eq. G6-1",
            )
            for bf, tf in ((self.bf, self.tf), (self.bf_bottom, self.tf_bottom))
        ]
        return replace(parts[0], Vn=parts[0].Vn + parts[1].Vn, name="shear buckling" if any(p.Cv < 1 for p in parts) else "shear yielding", Cv=None)
