"""Tees cut from W-shapes (WT)."""

from __future__ import annotations

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
from steel_design.flexure import FlexureStrength, tee_strength
from steel_design.sections.database import DatabaseShape
from steel_design.shear import KV_LEG, ShearStrength, plate_shear


class WT(DatabaseShape):
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
        r = sqrt_E_Fy(self.material)
        return SectionClassification(
            (
                compression_element("flange", self.bf_2tf, 0.56 * r, "Table B4.1a Case 1"),
                compression_element("stem", self.D_t, 0.75 * r, "Table B4.1a Case 4"),
            )
        )

    def buckling_modes(self, Lcx, Lcy, Lcz):
        """Flexural buckling about x (Eq. E3-4) and flexural-torsional buckling about the axis of
        symmetry y (Eqs. E4-3 and E4-7), omitting the warping term as permitted for tees."""
        E, G = self.material.E, self.material.G
        Fey = elastic_buckling_stress(E, Lcy, self.ry)
        return (
            flexural_buckling_mode("x-axis", E, Lcx, self.rx),
            flexural_torsional_buckling_mode(E, G, Q_(0, "in**6"), self.J, Lcz, self.A, self.ro, self.H, Fey),
        )

    def slender_elements(self):
        """Flange (outstanding, b = bf/2) and stem (outstanding, b = d) for Section E7."""
        c = self.compression_slenderness
        return (
            slender_element("flange", self.bf / 2, self.tf, 2, c["flange"].limit_r, OTHER_ELEMENTS),
            slender_element("stem", self.d, self.tw, 1, c["stem"].limit_r, OTHER_ELEMENTS),
        )

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Flange Case 10 and stem Case 14 (0.84 and 1.52 sqrt(E/Fy)) about the x-axis (Section
        F9), where the stem limit applies when the stem is in flexural compression. The y-axis
        checks the flange only (Table B4.1b)."""
        axis = check_axis(axis)
        r = sqrt_E_Fy(self.material)
        flange = flexure_element("flange", self.bf_2tf, 0.38 * r, 1.0 * r, "Table B4.1b Case 10")
        if axis == "y":
            return SectionClassification((flange,))
        stem = flexure_element("stem", self.D_t, 0.84 * r, 1.52 * r, "Table B4.1b Case 14")
        return SectionClassification((flange, stem))

    def flexure_strength(self, axis: str = "x", Lb=None, Cb: float = 1.0, stem: str = "tension") -> FlexureStrength:
        """Flexural strength per AISC 360-22 Section F9, for loading in the plane of symmetry.

        Args:
            axis: ``"x"``. Bending about the y-axis is outside Section F9.
            Lb: Unbraced length (pint length), required.
            Cb: Accepted for a uniform interface; Section F9 has no ``Cb``.
            stem: ``"tension"`` if the stem is in flexural tension (flange in compression), or
                ``"compression"`` if the stem is in flexural compression.

        Raises:
            NotImplementedError: For ``axis="y"``.
            ValueError: For an invalid ``axis`` or ``stem``, or a missing ``Lb``.
        """
        if check_axis(axis) == "y":
            raise NotImplementedError("Section F9 covers tees loaded in the plane of symmetry only (axis 'x')")
        if stem not in ("tension", "compression"):
            raise ValueError("stem must be 'tension' or 'compression'")
        if Lb is None:
            raise ValueError("Lb is required for flexure of tees")
        c = self.classify_flexure("x")
        return tee_strength(
            self.material, Lb, Zx=self.Zx, Sx=self.Sx, Sxc=self.Ix / self.y, Iy=self.Iy, J=self.J,
            d=self.d, ry=self.ry, stem_in_tension=stem == "tension", flange=c["flange"], stem=c["stem"],
        )

    def shear_strength(self, axis: str = "x") -> ShearStrength:
        """Shear strength per AISC 360-22 Chapter G.

        Strong-axis shear uses the stem (Section G3, ``b = d``, ``kv = 1.2``). Minor-axis shear
        uses the flange (Section G6, ``h/tw = bf/(2 tf)``).

        Args:
            axis: ``"x"`` for shear parallel to the stem, ``"y"`` for shear parallel to the flange.

        Raises:
            ValueError: For an invalid ``axis``.
        """
        if check_axis(axis) == "x":
            return plate_shear(self.material, "x", length=self.d, thickness=self.tw, kv=KV_LEG, reference="Eq. G3-1")
        return plate_shear(
            self.material, "y", length=self.bf, thickness=self.tf, kv=KV_LEG,
            slenderness=float(self.bf / (2 * self.tf)), reference="Eq. G6-1",
        )
