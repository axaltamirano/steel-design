"""Section classification for local buckling, AISC 360-22 Section B4 (Tables B4.1a and B4.1b).

`classify_compression(section)` -> nonslender / slender per element (Table B4.1a).
`classify_flexure(section, axis)` -> compact / noncompact / slender per element (Table B4.1b).

Limits are checked against Fy of the section's material. Case numbers and limits in the
`reference` strings were checked against AISC 360-22 (August 1, 2022), Tables B4.1a and B4.1b.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from functools import singledispatch

from steel_design.sections.angle import Angle
from steel_design.sections.base import Section
from steel_design.sections.built_up_box import BuiltUpBox
from steel_design.sections.built_up_wide_flange import BuiltUpWideFlange
from steel_design.sections.channel import Channel
from steel_design.sections.double_angle import DoubleAngle
from steel_design.sections.hp import HP
from steel_design.sections.hss_rect import HSSRect
from steel_design.sections.hss_round import HSSRound
from steel_design.sections.m_channel import MChannel
from steel_design.sections.m_shape import MShape
from steel_design.sections.mt import MT
from steel_design.sections.pipe import Pipe
from steel_design.sections.s_shape import SShape
from steel_design.sections.st import ST
from steel_design.sections.wt import WT
from steel_design.sections.wide_flange import WideFlange


class Slenderness(str, Enum):
    """Local-buckling classification of an element or section."""

    COMPACT = "compact"
    NONCOMPACT = "noncompact"
    NONSLENDER = "nonslender"
    SLENDER = "slender"


@dataclass(frozen=True)
class ElementClassification:
    """Classification of one plate element.

    Attributes:
        element: Element name, e.g. ``"flange"`` or ``"web"``.
        ratio: Width-to-thickness ratio of the element.
        limit_p: Compact/noncompact limit (flexure only, otherwise ``None``).
        limit_r: Noncompact/slender limit in flexure, or nonslender/slender limit in compression.
        classification: The resulting :class:`Slenderness`.
        reference: Table B4.1a or B4.1b case used.
    """
    element: str
    ratio: float  # width-to-thickness ratio of the element
    limit_p: float | None  # lambda_p (flexure only)
    limit_r: float  # lambda_r (flexure) or lambda_r for slender check (compression)
    classification: Slenderness
    reference: str


@dataclass(frozen=True)
class SectionClassification:
    """The classifications of all elements of a section, with lookup by element name."""
    elements: tuple[ElementClassification, ...]

    def __getitem__(self, element: str) -> ElementClassification:
        """Return the named element; raises ``KeyError`` if absent."""
        for e in self.elements:
            if e.element == element:
                return e
        raise KeyError(element)

    @property
    def governing(self) -> Slenderness:
        """The least favorable classification among the elements."""
        order = (Slenderness.COMPACT, Slenderness.NONSLENDER, Slenderness.NONCOMPACT, Slenderness.SLENDER)
        return max((e.classification for e in self.elements), key=order.index)


def _sqrt_E_Fy(section: Section) -> float:
    """sqrt(E/Fy) for the section material."""
    return math.sqrt((section.material.E / section.material.Fy).to("dimensionless").m)


def _E_Fy(section: Section) -> float:
    """E/Fy for the section material."""
    return (section.material.E / section.material.Fy).to("dimensionless").m


def _compression(element: str, ratio: float, limit: float, ref: str) -> ElementClassification:
    """Build a nonslender/slender result against the Table B4.1a limit."""
    cls = Slenderness.NONSLENDER if ratio <= limit else Slenderness.SLENDER
    return ElementClassification(element, ratio, None, limit, cls, ref)


def _flexure(element: str, ratio: float, lp: float, lr: float, ref: str) -> ElementClassification:
    """Build a compact/noncompact/slender result against the Table B4.1b limits."""
    if ratio <= lp:
        cls = Slenderness.COMPACT
    elif ratio <= lr:
        cls = Slenderness.NONCOMPACT
    else:
        cls = Slenderness.SLENDER
    return ElementClassification(element, ratio, lp, lr, cls, ref)


def _kc(h_tw: float) -> float:
    """kc = 4/sqrt(h/tw) for built-up I-shape flanges, limited to 0.35-0.76 (Tables B4.1a/b)."""
    return min(max(4 / math.sqrt(h_tw), 0.35), 0.76)


def _check_axis(axis: str) -> str:
    """Normalize and validate an axis argument (``"x"`` strong, ``"y"`` weak)."""
    axis = axis.lower()
    if axis not in ("x", "y"):
        raise ValueError("axis must be 'x' (major) or 'y' (minor)")
    return axis


@singledispatch
def classify_compression(section: Section) -> SectionClassification:
    """Classify each element of a section for axial compression (Table B4.1a).

    Dispatches on the section type.

    Raises:
        NotImplementedError: For section types without a registered implementation.
    """
    raise NotImplementedError(f"Compression classification not implemented for {type(section).__name__}")


@singledispatch
def classify_flexure(section: Section, axis: str = "x") -> SectionClassification:
    """Classify each element of a section for flexure (Table B4.1b).

    Dispatches on the section type.

    Args:
        section: Any section with a registered implementation.
        axis: ``"x"`` for strong-axis or ``"y"`` for weak-axis bending.
        compression_flange: Singly symmetric built-up I-shapes only (``"top"`` or ``"bottom"``): the
            flange in compression for major-axis bending.

    Raises:
        NotImplementedError: For section types without a registered implementation.
        ValueError: For an invalid ``axis`` or ``compression_flange``.
    """
    raise NotImplementedError(f"Flexure classification not implemented for {type(section).__name__}")


# --- Rolled I-shapes: W, M, S, HP -------------------------------------------------


@classify_compression.register(WideFlange)
@classify_compression.register(MShape)
@classify_compression.register(SShape)
@classify_compression.register(HP)
def _(section) -> SectionClassification:
    r = _sqrt_E_Fy(section)
    return SectionClassification(
        (
            _compression("flange", section.bf_2tf, 0.56 * r, "Table B4.1a Case 1"),
            _compression("web", section.h_tw, 1.49 * r, "Table B4.1a Case 5"),
        )
    )


@classify_flexure.register(WideFlange)
@classify_flexure.register(MShape)
@classify_flexure.register(SShape)
@classify_flexure.register(HP)
def _(section, axis: str = "x") -> SectionClassification:
    axis = _check_axis(axis)
    r = _sqrt_E_Fy(section)
    if axis == "y":  # minor-axis bending: webs are not in flexure
        return SectionClassification(
            (_flexure("flange", section.bf_2tf, 0.38 * r, 1.0 * r, "Table B4.1b Case 13"),)
        )
    flange = _flexure("flange", section.bf_2tf, 0.38 * r, 1.0 * r, "Table B4.1b Case 10")
    web = _flexure("web", section.h_tw, 3.76 * r, 5.70 * r, "Table B4.1b Case 15")
    return SectionClassification((flange, web))


# --- Built-up I-shape ------------------------------------------------------------


def _fl_ratio(section: BuiltUpWideFlange, compression_flange: str, web_slender: bool) -> float:
    """FL / Fy per Table B4.1b footnote [b] and Eqs. F4-6a/b."""
    if web_slender:
        return 0.7
    sxc, sxt = (
        (section.Sx_top, section.Sx_bottom) if compression_flange == "top" else (section.Sx_bottom, section.Sx_top)
    )
    ratio = float(sxt / sxc)
    return 0.7 if ratio >= 0.7 else max(ratio, 0.5)


@classify_compression.register(BuiltUpWideFlange)
def _(section) -> SectionClassification:
    r = _sqrt_E_Fy(section)
    kc = _kc(section.h_tw)
    limit = 0.64 * math.sqrt(kc) * r
    if section.is_doubly_symmetric:
        return SectionClassification(
            (
                _compression("flange", section.bf_2tf, limit, "Table B4.1a Case 2"),
                _compression("web", section.h_tw, 1.49 * r, "Table B4.1a Case 5"),
            )
        )
    # Singly symmetric: either flange can be in compression; the web is a "other stiffened element".
    return SectionClassification(
        (
            _compression("top flange", section.bf_2tf, limit, "Table B4.1a Case 2"),
            _compression("bottom flange", section.bf_2tf_bottom, limit, "Table B4.1a Case 2"),
            _compression("web", section.h_tw, 1.49 * r, "Table B4.1a Case 8"),
        )
    )


@classify_flexure.register(BuiltUpWideFlange)
def _(section, axis: str = "x", compression_flange: str = "top") -> SectionClassification:
    """For singly symmetric sections, `compression_flange` ("top" or "bottom") is the flange
    in flexural compression for major-axis bending. For minor-axis bending both flanges are checked."""
    axis = _check_axis(axis)
    if compression_flange not in ("top", "bottom"):
        raise ValueError("compression_flange must be 'top' or 'bottom'")
    e_fy, r = _E_Fy(section), _sqrt_E_Fy(section)

    if axis == "y":
        case13 = "Table B4.1b Case 13"
        if section.is_doubly_symmetric:
            return SectionClassification((_flexure("flange", section.bf_2tf, 0.38 * r, 1.0 * r, case13),))
        return SectionClassification(
            (
                _flexure("top flange", section.bf_2tf, 0.38 * r, 1.0 * r, case13),
                _flexure("bottom flange", section.bf_2tf_bottom, 0.38 * r, 1.0 * r, case13),
            )
        )

    kc = _kc(section.h_tw)
    lam_r_web = 5.70 * r
    if section.is_doubly_symmetric:
        web = _flexure("web", section.h_tw, 3.76 * r, lam_r_web, "Table B4.1b Case 15")
        fl = 0.7
        flange_ratio = section.bf_2tf
    else:
        hc = section.hc(compression_flange).to("in").m
        hp = section.hp(compression_flange).to("in").m
        mp_my = float(section.Zx / section.Sx)
        lam_p = (hc / hp) * r / (0.54 * mp_my - 0.09) ** 2 if hp > 0 else lam_r_web
        web = _flexure(
            "web", hc / section.tw.to("in").m, min(lam_p, lam_r_web), lam_r_web, "Table B4.1b Case 16"
        )
        fl = _fl_ratio(section, compression_flange, web.classification is Slenderness.SLENDER)
        flange_ratio = section.bf_2tf if compression_flange == "top" else section.bf_2tf_bottom
    lam_r = 0.95 * math.sqrt(kc * e_fy / fl)
    flange = _flexure("flange", flange_ratio, 0.38 * r, lam_r, "Table B4.1b Case 11")
    return SectionClassification((flange, web))


# --- Rectangular HSS and built-up box --------------------------------------------


@classify_compression.register(HSSRect)
def _(section) -> SectionClassification:
    limit = 1.40 * _sqrt_E_Fy(section)
    return SectionClassification(
        (
            _compression("short wall", section.b_tdes, limit, "Table B4.1a Case 6"),
            _compression("long wall", section.h_tdes, limit, "Table B4.1a Case 6"),
        )
    )


@classify_compression.register(BuiltUpBox)
def _(section) -> SectionClassification:
    limit = 1.49 * _sqrt_E_Fy(section)  # Case 8, all other stiffened elements
    return SectionClassification(
        (
            _compression("flange", section.b_tf, limit, "Table B4.1a Case 8"),
            _compression("web", section.h_tw, limit, "Table B4.1a Case 8"),
        )
    )


@classify_flexure.register(HSSRect)
def _(section, axis: str = "x") -> SectionClassification:
    # Major axis: flanges are the B walls (b/t), webs the Ht walls (h/t); reversed for minor axis.
    r = _sqrt_E_Fy(section)
    major = _check_axis(axis) == "x"
    flange_ratio, web_ratio = (section.b_tdes, section.h_tdes) if major else (section.h_tdes, section.b_tdes)
    return SectionClassification(
        (
            _flexure("flange", flange_ratio, 1.12 * r, 1.40 * r, "Table B4.1b Case 17"),
            _flexure("web", web_ratio, 2.42 * r, 5.70 * r, "Table B4.1b Case 19"),
        )
    )


@classify_flexure.register(BuiltUpBox)
def _(section, axis: str = "x") -> SectionClassification:
    # b/t and h/t use the clear distances between the plates providing stiffening (Sect. B4.1b(e)).
    r = _sqrt_E_Fy(section)
    major = _check_axis(axis) == "x"
    flange_ratio, web_ratio = (section.b_tf, section.h_tw) if major else (section.h_tw, section.b_tf)
    return SectionClassification(
        (
            _flexure("flange", flange_ratio, 1.12 * r, 1.49 * r, "Table B4.1b Case 21"),
            _flexure("web", web_ratio, 2.42 * r, 5.70 * r, "Table B4.1b Case 19"),
        )
    )


# --- Round HSS and pipe ----------------------------------------------------------


@classify_compression.register(HSSRound)
@classify_compression.register(Pipe)
def _(section) -> SectionClassification:
    return SectionClassification(
        (_compression("wall", section.D_t, 0.11 * _E_Fy(section), "Table B4.1a Case 9"),)
    )


@classify_flexure.register(HSSRound)
@classify_flexure.register(Pipe)
def _(section, axis: str = "x") -> SectionClassification:
    _check_axis(axis)
    e = _E_Fy(section)
    return SectionClassification(
        (_flexure("wall", section.D_t, 0.07 * e, 0.31 * e, "Table B4.1b Case 20"),)
    )


# --- Channels ----------------------------------------------------------------------


@classify_compression.register(Channel)
@classify_compression.register(MChannel)
def _(section) -> SectionClassification:
    r = _sqrt_E_Fy(section)
    return SectionClassification(
        (
            _compression("flange", section.b_t, 0.56 * r, "Table B4.1a Case 1"),
            _compression("web", section.h_tw, 1.49 * r, "Table B4.1a Case 5"),
        )
    )


@classify_flexure.register(Channel)
@classify_flexure.register(MChannel)
def _(section, axis: str = "x") -> SectionClassification:
    axis = _check_axis(axis)
    r = _sqrt_E_Fy(section)
    flange = _flexure("flange", section.b_t, 0.38 * r, 1.0 * r, "Table B4.1b Case 10")
    if axis == "y":
        flange = _flexure("flange", section.b_t, 0.38 * r, 1.0 * r, "Table B4.1b Case 13")
        return SectionClassification((flange,))
    web = _flexure("web", section.h_tw, 3.76 * r, 5.70 * r, "Table B4.1b Case 15")
    return SectionClassification((flange, web))


# --- Tees ---------------------------------------------------------------------------


@classify_compression.register(WT)
@classify_compression.register(MT)
@classify_compression.register(ST)
def _(section) -> SectionClassification:
    r = _sqrt_E_Fy(section)
    return SectionClassification(
        (
            _compression("flange", section.bf_2tf, 0.56 * r, "Table B4.1a Case 1"),
            _compression("stem", section.D_t, 0.75 * r, "Table B4.1a Case 4"),
        )
    )


@classify_flexure.register(WT)
@classify_flexure.register(MT)
@classify_flexure.register(ST)
def _(section, axis: str = "x") -> SectionClassification:
    """Axis x is bending in the plane of symmetry (Section F9); the stem limit applies when
    the stem is in flexural compression. Axis y checks the flange only."""
    axis = _check_axis(axis)
    r = _sqrt_E_Fy(section)
    flange = _flexure("flange", section.bf_2tf, 0.38 * r, 1.0 * r, "Table B4.1b Case 10")
    if axis == "y":
        return SectionClassification((flange,))
    stem = _flexure("stem", section.D_t, 0.84 * r, 1.52 * r, "Table B4.1b Case 14")
    return SectionClassification((flange, stem))


# --- Angles -------------------------------------------------------------------------


@classify_compression.register(Angle)
def _(section) -> SectionClassification:
    return SectionClassification(
        (_compression("leg", section.b_t, 0.45 * _sqrt_E_Fy(section), "Table B4.1a Case 3"),)
    )


@classify_compression.register(DoubleAngle)
def _(section) -> SectionClassification:
    """Outstanding legs: Case 1 (0.56) with continuous contact, Case 3 (0.45) with separators.
    The database b/t uses the longer leg, which governs."""
    if section.continuous_contact:
        limit, ref = 0.56 * _sqrt_E_Fy(section), "Table B4.1a Case 1"
    else:
        limit, ref = 0.45 * _sqrt_E_Fy(section), "Table B4.1a Case 3"
    return SectionClassification((_compression("leg", section.b_t, limit, ref),))


@classify_flexure.register(Angle)
@classify_flexure.register(DoubleAngle)
def _(section, axis: str = "x") -> SectionClassification:
    _check_axis(axis)
    r = _sqrt_E_Fy(section)
    return SectionClassification(
        (_flexure("leg", section.b_t, 0.54 * r, 0.91 * r, "Table B4.1b Case 12"),)
    )
