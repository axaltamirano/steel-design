"""Rectangular and square HSS shapes."""

from __future__ import annotations

from pint import Quantity

from steel_design.compression import (
    HSS_WALLS,
    flexural_buckling_mode,
    slender_element,
)
from steel_design.classification import (
    SectionClassification,
    check_axis,
    compression_element,
    flexure_element,
    sqrt_E_Fy,
)
from steel_design.flexure import FlexureStrength, rectangular_hss_strength
from steel_design.sections.database import DatabaseShape


class HSSRect(DatabaseShape):
    """Rectangular or square HSS, e.g. ``HSS6X4X1/4``."""

    family = "HSS_RECT"

    #: Shape designation per the AISC EDI naming convention.
    EDI_Std_Nomenclature: str
    #: Shape designation as shown in the Steel Construction Manual.
    AISC_Manual_Label: str
    #: Nominal weight per unit length, lb/ft.
    weight: Quantity
    #: Cross-sectional area, in.².
    A: Quantity
    #: Overall depth of square HSS or longer wall of rectangular HSS, in.
    Ht: Quantity
    #: Depth of the flat wall of square HSS or longer flat wall of rectangular HSS, in.
    h: Quantity
    #: Overall width of square HSS or shorter wall of rectangular HSS, in.
    B: Quantity
    #: Width of the flat wall of square HSS or the shorter flat wall of rectangular HSS, in.
    b: Quantity
    #: Nominal wall thickness, in.
    tnom: Quantity
    #: Design wall thickness, in.
    tdes: Quantity
    #: Slenderness ratio of the shorter wall, b/tdes.
    b_tdes: float
    #: Slenderness ratio of the longer wall, h/tdes.
    h_tdes: float
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
    #: HSS torsional constant, in.³.
    C: Quantity

    def classify_compression(self) -> SectionClassification:
        """Both walls Case 6 (1.40 sqrt(E/Fy)) of Table B4.1a."""
        limit = 1.40 * sqrt_E_Fy(self.material)
        return SectionClassification(
            (
                compression_element("short wall", self.b_tdes, limit, "Table B4.1a Case 6"),
                compression_element("long wall", self.h_tdes, limit, "Table B4.1a Case 6"),
            )
        )

    def buckling_modes(self, Lcx, Lcy, Lcz):
        """Flexural buckling about x and y (Eq. E3-4); torsion does not govern closed sections."""
        E = self.material.E
        return (
            flexural_buckling_mode("x-axis", E, Lcx, self.rx),
            flexural_buckling_mode("y-axis", E, Lcy, self.ry),
        )

    def slender_elements(self):
        """Clear walls ``b`` and ``h`` with the HSS factors of Table E7.1."""
        limit = self.compression_slenderness["short wall"].limit_r
        return (
            slender_element("short wall", self.b_tdes * self.tdes, self.tdes, 2, limit, HSS_WALLS),
            slender_element("long wall", self.h_tdes * self.tdes, self.tdes, 2, limit, HSS_WALLS),
        )

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Flange Case 17 (1.12 and 1.40 sqrt(E/Fy)) and web Case 19 (2.42 and 5.70 sqrt(E/Fy)).

        For major-axis bending the flanges are the ``B`` walls (``b/tdes``) and the webs the
        ``Ht`` walls (``h/tdes``); the roles reverse for minor-axis bending.
        """
        r = sqrt_E_Fy(self.material)
        major = check_axis(axis) == "x"
        flange_ratio, web_ratio = (self.b_tdes, self.h_tdes) if major else (self.h_tdes, self.b_tdes)
        return SectionClassification(
            (
                flexure_element("flange", flange_ratio, 1.12 * r, 1.40 * r, "Table B4.1b Case 17"),
                flexure_element("web", web_ratio, 2.42 * r, 5.70 * r, "Table B4.1b Case 19"),
            )
        )

    def flexure_strength(self, axis: str = "x", Lb=None, Cb: float = 1.0) -> FlexureStrength:
        """Flexural strength per AISC 360-22 Section F7.

        Lateral-torsional buckling applies only to strong-axis bending of a section that is not
        square, and then ``Lb`` is required; it is ignored otherwise.

        Args:
            axis: ``"x"`` or ``"y"``.
            Lb: Unbraced length (pint length).
            Cb: Lateral-torsional buckling modification factor; defaults to 1.0.

        Raises:
            ValueError: For an invalid ``axis`` or a missing ``Lb`` where required.
        """
        axis = check_axis(axis)
        c = self.classify_flexure(axis)
        major = axis == "x"
        return rectangular_hss_strength(
            self.material, axis, Lb, Cb,
            Z=self.Zx if major else self.Zy, S=self.Sx if major else self.Sy,
            I=self.Ix if major else self.Iy, A=self.A, ry=self.ry, J=self.J,
            depth=self.Ht if major else self.B, t_flange=self.tdes, t_web=self.tdes,
            flange=c["flange"], web=c["web"], box=False,
            ltb=major and self.Ht != self.B,
        )
