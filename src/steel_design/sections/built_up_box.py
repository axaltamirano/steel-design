"""Built-up rectangular box section."""

from __future__ import annotations

import math
from functools import cached_property

from steel_design.compression import (
    OTHER_ELEMENTS,
    STIFFENED_ELEMENTS,
    flexural_buckling_mode,
    slender_element,
)
from steel_design.classification import (
    SectionClassification,
    check_axis,
    compression_element,
    flexure_element,
    kc,
    sqrt_E_Fy,
)
from steel_design.flexure import FlexureStrength, rectangular_hss_strength
from steel_design.materials.base import SteelMaterial
from steel_design.materials.defaults import default_material_for
from steel_design.sections.base import Section
from steel_design.units import Q_, require_length
from steel_design.shear import KV_BOX, ShearStrength, plate_shear


class BuiltUpBox(Section):
    """Box from four plates, with no fillets (welds ignored).

    Two flange plates of full outside width `B` and thickness `tf` span between two
    web plates of thickness `tw`; `Ht` is the overall outside depth. Warping is
    neglected (Cw = 0), which is standard for closed sections.

    By default the web plates are flush with the flange edges, giving a hollow rectangle. With
    ``inset_web_PL`` the web plates are moved inward by that distance, so each flange plate
    overhangs the outside face of a web by ``inset_web_PL``. The section properties, the
    slenderness classification and the shear and compression checks account for the overhangs.
    Flexural strength (Section F7) is not defined for the overhanging geometry and is not
    available when ``inset_web_PL`` is greater than zero.
    """

    family = "BUILT_UP_BOX"

    def __init__(
        self,
        Ht,
        B,
        tf,
        tw,
        material: type[SteelMaterial] | None = None,
        name: str | None = None,
        inset_web_PL=None,
    ):
        """Create a box section.

        Args:
            Ht: Overall outside depth (length quantity).
            B: Overall outside width (length quantity).
            tf: Flange plate thickness (length quantity).
            tw: Web plate thickness (length quantity).
            material: Material class; defaults to the ``BUILT_UP_BOX`` default.
            name: Optional label; generated from the dimensions when omitted.
            inset_web_PL: Optional distance (length quantity, default zero) that each web plate is
                moved inward from the flange plate edge. The web's outside face is then
                ``inset_web_PL`` from the edge of the flange, which overhangs as an outstanding element.

        Raises:
            TypeError: If a dimension is not a pint quantity.
            ValueError: If a dimension is non-positive or negative inset, or the plates leave no
                interior.
        """
        self.Ht = require_length(Ht, "Ht")
        self.B = require_length(B, "B")
        self.tf = require_length(tf, "tf")
        self.tw = require_length(tw, "tw")
        if min(self.Ht.m, self.B.m, self.tf.m, self.tw.m) <= 0:
            raise ValueError("All dimensions must be positive")
        if 2 * self.tf >= self.Ht or 2 * self.tw >= self.B:
            raise ValueError("Plate thicknesses must leave an open interior")
        self.inset_web_PL = require_length(
            Q_(0, "in") if inset_web_PL is None else inset_web_PL, "inset_web_PL"
        )
        if self.inset_web_PL.m < 0:
            raise ValueError("inset_web_PL must not be negative")
        if 2 * (self.inset_web_PL + self.tw) >= self.B:
            raise ValueError("Inset web plates must leave an open interior")
        self.material = material or default_material_for(self.family)
        label = f"BOX{self.Ht.m:g}x{self.B.m:g}(f{self.tf.m:g},w{self.tw.m:g}"
        if self.inset_web_PL.m:
            label += f",inset{self.inset_web_PL.to('in').m:g}"
        self.name = name or label + ")"

    @cached_property
    def h(self):
        """Clear web height between flange plates."""
        return self.Ht - 2 * self.tf

    @cached_property
    def b(self):
        """Clear flange width between the web plates."""
        return self.B - 2 * self.inset_web_PL - 2 * self.tw

    @cached_property
    def web_spacing(self):
        """Distance between the centerlines of the web plates."""
        return self.B - 2 * self.inset_web_PL - self.tw

    @cached_property
    def A(self):
        """Cross-sectional area."""
        return (2 * self.B * self.tf + 2 * self.tw * self.h).to("in**2")

    @cached_property
    def weight(self):
        """Weight per unit length, from the material unit weight."""
        return (self.A * self.material.density).to("lbf/ft")

    @cached_property
    def Ix(self):
        """Moment of inertia about the x-axis (strong axis)."""
        return ((self.B * self.Ht**3 - (self.B - 2 * self.tw) * self.h**3) / 12).to("in**4")

    @cached_property
    def Iy(self):
        """Moment of inertia about the y-axis (weak axis)."""
        web_offset = self.web_spacing / 2
        flanges = 2 * self.tf * self.B**3 / 12
        webs = 2 * (self.h * self.tw**3 / 12 + self.h * self.tw * web_offset**2)
        return (flanges + webs).to("in**4")

    @cached_property
    def Sx(self):
        """Elastic section modulus about the x-axis."""
        return (2 * self.Ix / self.Ht).to("in**3")

    @cached_property
    def Sy(self):
        """Elastic section modulus about the y-axis."""
        return (2 * self.Iy / self.B).to("in**3")

    @cached_property
    def Zx(self):
        """Plastic section modulus about the x-axis."""
        return (self.B * self.tf * (self.h + self.tf) + self.tw * self.h**2 / 2).to("in**3")

    @cached_property
    def Zy(self):
        """Plastic section modulus about the y-axis."""
        return (self.tf * self.B**2 / 2 + self.tw * self.h * self.web_spacing).to("in**3")

    @cached_property
    def rx(self):
        """Radius of gyration about the x-axis."""
        return ((self.Ix / self.A) ** 0.5).to("in")

    @cached_property
    def ry(self):
        """Radius of gyration about the y-axis."""
        return ((self.Iy / self.A) ** 0.5).to("in")

    @cached_property
    def Ab(self):
        """Area enclosed by the plate centerlines."""
        return (self.web_spacing * (self.Ht - self.tf)).to("in**2")

    @cached_property
    def J(self):
        """Torsional constant by Bredt's formula, 4*Ab^2 / sum(length/thickness).

        The four flange overhangs add the open-section term ``b t^3 / 3`` each.
        """
        perimeter_ratio = 2 * self.web_spacing / self.tf + 2 * (self.Ht - self.tf) / self.tw
        closed = 4 * self.Ab**2 / perimeter_ratio
        overhangs = 4 * self.inset_web_PL * self.tf**3 / 3
        return (closed + overhangs).to("in**4")

    @cached_property
    def C(self):
        """Torsional shear constant, 2*Ab*t_min, so that tau = T / C (AISC 360-22 Sect. H3)."""
        return (2 * self.Ab * min(self.tf, self.tw)).to("in**3")

    @cached_property
    def Cw(self):
        """Warping constant; zero because warping is neglected for closed sections."""
        return Q_(0, "in**6")  # warping neglected for closed sections

    @cached_property
    def b_tf(self):
        """Flange slenderness, clear width ``b`` over ``tf`` (dimensionless)."""
        return float(self.b / self.tf)

    @cached_property
    def h_tw(self):
        """Web slenderness, clear height ``h`` over ``tw`` (dimensionless)."""
        return float(self.h / self.tw)

    @cached_property
    def overhang_tf(self):
        """Slenderness of the flange overhang, ``inset_web_PL / tf`` (dimensionless)."""
        return float(self.inset_web_PL / self.tf)

    def classify_compression(self) -> SectionClassification:
        """Flanges and webs are stiffened elements, Case 8 (1.49 sqrt(E/Fy)) of Table B4.1a."""
        r = sqrt_E_Fy(self.material)
        limit = 1.49 * r
        elements = (
            compression_element("flange", self.b_tf, limit, "Table B4.1a Case 8"),
            compression_element("web", self.h_tw, limit, "Table B4.1a Case 8"),
        )
        if self.inset_web_PL.m:
            overhang_limit = 0.64 * math.sqrt(kc(self.h_tw)) * r
            elements += (
                compression_element(
                    "flange overhang", self.overhang_tf, overhang_limit, "Table B4.1a Case 2"
                ),
            )
        return SectionClassification(elements)

    def buckling_modes(self, Lcx, Lcy, Lcz):
        """Flexural buckling about x and y (Eq. E3-4); torsion does not govern closed sections."""
        E = self.material.E
        return (
            flexural_buckling_mode("x-axis", E, Lcx, self.rx),
            flexural_buckling_mode("y-axis", E, Lcy, self.ry),
        )

    def slender_elements(self):
        """Flange plates (width ``b``) and web plates (width ``h``), stiffened (Table E7.1 (a))."""
        c = self.compression_slenderness
        limit = c["flange"].limit_r
        elements = (
            slender_element("flange", self.b, self.tf, 2, limit, STIFFENED_ELEMENTS),
            slender_element("web", self.h, self.tw, 2, limit, STIFFENED_ELEMENTS),
        )
        if self.inset_web_PL.m:
            elements += (
                slender_element(
                    "flange overhang", self.inset_web_PL, self.tf, 4,
                    c["flange overhang"].limit_r, OTHER_ELEMENTS,
                ),
            )
        return elements

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Flange Case 21 (1.12 and 1.49 sqrt(E/Fy)) and web Case 19 (2.42 and 5.70 sqrt(E/Fy)).

        The ratios use the clear distances between the plates providing stiffening (Section
        B4.1b(e)). For minor-axis bending the roles of flange and web are reversed.
        """
        r = sqrt_E_Fy(self.material)
        major = check_axis(axis) == "x"
        flange_ratio, web_ratio = (self.b_tf, self.h_tw) if major else (self.h_tw, self.b_tf)
        elements = (
            flexure_element("flange", flange_ratio, 1.12 * r, 1.49 * r, "Table B4.1b Case 21"),
            flexure_element("web", web_ratio, 2.42 * r, 5.70 * r, "Table B4.1b Case 19"),
        )
        if self.inset_web_PL.m and major:
            # Outstanding flange plate as for a built-up I-shape flange (Case 11), with FL = 0.7 Fy
            lam_r = 0.95 * math.sqrt(kc(self.h_tw) / 0.7) * r
            elements += (
                flexure_element("flange overhang", self.overhang_tf, 0.38 * r, lam_r, "Table B4.1b Case 11"),
            )
        return SectionClassification(elements)

    def flexure_strength(self, axis: str = "x", Lb=None, Cb: float = 1.0) -> FlexureStrength:
        """Flexural strength per AISC 360-22 Section F7 (box sections use the coefficient 0.34 for
        the effective width of slender flanges).

        Lateral-torsional buckling applies only to strong-axis bending of a section that is not
        square, and then ``Lb`` is required; it is ignored otherwise. For minor-axis bending the
        flanges are the walls of thickness ``tw`` and the webs those of thickness ``tf``.

        Args:
            axis: ``"x"`` or ``"y"``.
            Lb: Unbraced length (pint length).
            Cb: Lateral-torsional buckling modification factor; defaults to 1.0.

        Raises:
            ValueError: For an invalid ``axis`` or a missing ``Lb`` where required.
            NotImplementedError: If ``inset_web_PL`` is greater than zero.
        """
        axis = check_axis(axis)
        if self.inset_web_PL.m:
            raise NotImplementedError(
                "Flexural strength is not implemented for a box with inset web plates"
            )
        c = self.classify_flexure(axis)
        major = axis == "x"
        return rectangular_hss_strength(
            self.material, axis, Lb, Cb,
            Z=self.Zx if major else self.Zy, S=self.Sx if major else self.Sy,
            I=self.Ix if major else self.Iy, A=self.A, ry=self.ry, J=self.J,
            depth=self.Ht if major else self.B,
            t_flange=self.tf if major else self.tw, t_web=self.tw if major else self.tf,
            flange=c["flange"], web=c["web"], box=True,
            ltb=major and self.Ht != self.B,
        )

    def __repr__(self) -> str:
        return f"<BuiltUpBox {self.name} ({self.material.name})>"

    def shear_strength(self, axis: str = "x") -> ShearStrength:
        """Shear strength per AISC 360-22 Section G4: two plates, ``Aw = 2 h t``, ``kv = 5``.

        Args:
            axis: ``"x"`` for shear resisted by the web plates (clear height ``h``), ``"y"``
                for shear resisted by the flange plates (clear width ``b``).

        Raises:
            ValueError: For an invalid ``axis``.
        """
        if check_axis(axis) == "x":
            return plate_shear(self.material, "x", length=self.h, thickness=self.tw, kv=KV_BOX, count=2, reference="Eq. G4-1")
        return plate_shear(self.material, "y", length=self.b, thickness=self.tf, kv=KV_BOX, count=2, reference="Eq. G4-1")
