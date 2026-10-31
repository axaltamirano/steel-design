"""Compression members, AISC 360-22 Chapter E.

Implements flexural buckling (E3), torsional and flexural-torsional buckling (E4), the
effective slenderness of single angles (E5) and the effective-width reduction for members with
slender elements (E7). Each section type supplies its own buckling modes and slender elements
(``elastic_buckling_modes`` and ``effective_area``); this module holds the equations and the
result types.

Not included: built-up member connector spacing and modified slenderness (E6), bracing offset
from the shear center (E4(d) to (f)), and the lowest-root solution for unsymmetric members
(E4-4), which no section type in the library needs.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

import pint

from steel_design.materials.base import SteelMaterial
from steel_design.units import require_length

PHI_COMPRESSION: Final = 0.90
OMEGA_COMPRESSION: Final = 1.67

#: Recommended maximum effective slenderness ratio, KL/r (E2 User Note).
MAX_RECOMMENDED_SLENDERNESS: Final = 200

#: Fy/Fe above which Eq. E3-3 replaces Eq. E3-2 (equivalent to KL/r > 4.71 sqrt(E/Fy)).
FY_FE_LIMIT: Final = 2.25

#: Table E7.1 (c1, c2): stiffened elements except walls of square and rectangular HSS.
STIFFENED_ELEMENTS: Final = (0.18, 1.31)
#: Table E7.1 (c1, c2): walls of square and rectangular HSS.
HSS_WALLS: Final = (0.20, 1.38)
#: Table E7.1 (c1, c2): all other elements.
OTHER_ELEMENTS: Final = (0.22, 1.49)


# --- E3, E4: elastic buckling stresses and nominal stress ------------------------------


def _ratio(numerator: pint.Quantity, denominator: pint.Quantity) -> float:
    """Dimensionless ratio of two quantities."""
    return float((numerator / denominator).to("dimensionless").magnitude)


def elastic_buckling_stress(E: pint.Quantity, Lc: pint.Quantity, r: pint.Quantity) -> pint.Quantity:
    """Elastic flexural buckling stress, ``Fe = pi^2 E / (Lc/r)^2`` (Eq. E3-4)."""
    return (math.pi**2 * E / _ratio(Lc, r) ** 2).to("ksi")


def nominal_stress(Fy: pint.Quantity, Fe: pint.Quantity) -> pint.Quantity:
    """Nominal compressive stress Fn (Eqs. E3-2 and E3-3).

    ``Fn = 0.658^(Fy/Fe) Fy`` when ``Fy/Fe <= 2.25``, otherwise ``Fn = 0.877 Fe``.
    """
    if _ratio(Fy, Fe) <= FY_FE_LIMIT:
        return (0.658 ** _ratio(Fy, Fe) * Fy).to("ksi")
    return (0.877 * Fe).to("ksi")


def torsional_buckling_stress(
    E: pint.Quantity,
    G: pint.Quantity,
    Cw: pint.Quantity,
    J: pint.Quantity,
    Lcz: pint.Quantity,
    A: pint.Quantity,
    ro: pint.Quantity,
) -> pint.Quantity:
    """Elastic torsional buckling stress Fez (Eq. E4-7).

    For doubly symmetric members ``A ro^2 = Ix + Iy`` and this is Eq. E4-2.
    """
    return ((math.pi**2 * E * Cw / Lcz**2 + G * J) / (A * ro**2)).to("ksi")


def flexural_torsional_buckling_stress(Fe_flexural: pint.Quantity, Fez: pint.Quantity, H: float) -> pint.Quantity:
    """Elastic flexural-torsional buckling stress of a singly symmetric member (Eq. E4-3).

    Args:
        Fe_flexural: Flexural buckling stress about the axis of symmetry (``Fey`` for a member
            symmetric about y, ``Fex`` for a channel).
        Fez: Torsional buckling stress, Eq. E4-7.
        H: Flexural constant.
    """
    total = Fe_flexural + Fez
    root = math.sqrt(max(0.0, 1 - 4 * _ratio(Fe_flexural * Fez * H, total**2)))
    return (total / (2 * H) * (1 - root)).to("ksi")


@dataclass(frozen=True)
class BucklingMode:
    """One elastic buckling mode of a compression member.

    Attributes:
        name: Mode name, e.g. ``"flexural buckling about y-axis"``.
        Fe: Elastic buckling stress.
        reference: Equation that gives ``Fe``.
        slenderness: Effective slenderness ``Lc/r`` for flexural modes, otherwise ``None``.
    """

    name: str
    Fe: pint.Quantity
    reference: str
    slenderness: float | None = None


def flexural_buckling_mode(axis: str, E: pint.Quantity, Lc: pint.Quantity, r: pint.Quantity) -> BucklingMode:
    """Flexural buckling about ``axis`` (``"x-axis"``, ``"y-axis"``, ...), Eq. E3-4."""
    return BucklingMode(
        f"flexural buckling about {axis}", elastic_buckling_stress(E, Lc, r), "Eq. E3-4", _ratio(Lc, r)
    )


def torsional_buckling_mode(
    E: pint.Quantity,
    G: pint.Quantity,
    Cw: pint.Quantity,
    J: pint.Quantity,
    Lcz: pint.Quantity,
    Ix: pint.Quantity,
    Iy: pint.Quantity,
) -> BucklingMode:
    """Torsional buckling of a doubly symmetric member twisting about its shear center (Eq. E4-2)."""
    Fe = ((math.pi**2 * E * Cw / Lcz**2 + G * J) / (Ix + Iy)).to("ksi")
    return BucklingMode("torsional buckling", Fe, "Eq. E4-2")


def flexural_torsional_buckling_mode(
    E: pint.Quantity,
    G: pint.Quantity,
    Cw: pint.Quantity,
    J: pint.Quantity,
    Lcz: pint.Quantity,
    A: pint.Quantity,
    ro: pint.Quantity,
    H: float,
    Fe_flexural: pint.Quantity,
) -> BucklingMode:
    """Flexural-torsional buckling of a singly symmetric member (Eqs. E4-3 and E4-7)."""
    Fez = torsional_buckling_stress(E, G, Cw, J, Lcz, A, ro)
    return BucklingMode("flexural-torsional buckling", flexural_torsional_buckling_stress(Fe_flexural, Fez, H), "Eq. E4-3")


# --- E5: single angles ------------------------------------------------------------------


def single_angle_effective_slenderness(
    L: pint.Quantity,
    ra: pint.Quantity,
    rz: pint.Quantity,
    bl: pint.Quantity,
    bs: pint.Quantity,
    truss: str = "planar",
    connected_leg: str = "long",
) -> float:
    """Effective slenderness ``Lc/r`` of a single-angle compression member (Section E5).

    Args:
        L: Length of the member between work points at the truss chord centerlines.
        ra: Radius of gyration about the geometric axis parallel to the connected leg.
        rz: Radius of gyration about the minor principal axis.
        bl: Length of the longer leg.
        bs: Length of the shorter leg.
        truss: ``"planar"`` for individual members and web members of planar trusses with
            adjacent web members on the same side of the gusset (E5(a), Eqs. E5-1 and E5-2) or
            ``"box"`` for web members of box or space trusses (E5(b), Eqs. E5-3 and E5-4).
        connected_leg: ``"long"`` or ``"short"``. Equal-leg angles are treated as ``"long"``.

    Raises:
        ValueError: For an invalid option, an unequal-leg angle with ``bl/bs >= 1.7``, or a
            result above 200, since the Section E5 requirements are then not met and Chapter H
            applies.
    """
    if truss not in ("planar", "box"):
        raise ValueError("truss must be 'planar' or 'box'")
    if connected_leg not in ("long", "short"):
        raise ValueError("connected_leg must be 'long' or 'short'")
    leg_ratio = _ratio(bl, bs)
    if leg_ratio >= 1.7:
        raise ValueError("Section E5 requires bl/bs < 1.7; evaluate the angle with Chapter H")
    L_ra = _ratio(L, ra)
    if truss == "planar":
        base = 72 + 0.75 * L_ra if L_ra <= 80 else 32 + 1.25 * L_ra
        add, floor = 4 * (leg_ratio**2 - 1), 0.95
    else:
        base = 60 + 0.80 * L_ra if L_ra <= 75 else 45 + L_ra
        add, floor = 6 * (leg_ratio**2 - 1), 0.82
    slenderness = base
    if connected_leg == "short" and leg_ratio > 1:
        slenderness = max(base + add, floor * _ratio(L, rz))
    if slenderness > 200:
        raise ValueError(f"Section E5 requires Lc/r <= 200; got {slenderness:.1f}. Use Chapter H")
    return slenderness


# --- E7: slender elements ---------------------------------------------------------------


@dataclass(frozen=True)
class SlenderElement:
    """A plate element of a cross section checked for local buckling in compression (Section E7).

    Attributes:
        name: Element name.
        b: Element width as defined in Table B4.1a (``h`` for webs, ``d`` for tee stems).
        t: Element thickness.
        count: Number of identical elements in the cross section.
        ratio: Width-to-thickness ratio ``lambda``.
        limit: Limiting ratio ``lambda_r`` from Table B4.1a.
        c1: Effective width imperfection adjustment factor, Table E7.1.
        c2: Effective width imperfection adjustment factor, Table E7.1.
    """

    name: str
    b: pint.Quantity
    t: pint.Quantity
    count: int
    ratio: float
    limit: float
    c1: float
    c2: float


def slender_element(
    name: str,
    b: pint.Quantity,
    t: pint.Quantity,
    count: int,
    limit: float,
    factors: tuple[float, float],
) -> SlenderElement:
    """Build a :class:`SlenderElement`, with ``lambda = b/t``.

    Args:
        name: Element name.
        b: Element width as defined in Table B4.1a.
        t: Element thickness.
        count: Number of identical elements.
        limit: ``lambda_r`` from Table B4.1a.
        factors: ``(c1, c2)`` from Table E7.1: :data:`STIFFENED_ELEMENTS`, :data:`HSS_WALLS`
            or :data:`OTHER_ELEMENTS`.
    """
    return SlenderElement(name, b, t, count, _ratio(b, t), limit, *factors)


@dataclass(frozen=True)
class ElementReduction:
    """Effective width of one slender element.

    Attributes:
        name: Element name.
        b: Full width.
        be: Effective width, ``be <= b``.
        count: Number of identical elements.
    """

    name: str
    b: pint.Quantity
    be: pint.Quantity
    count: int


@dataclass(frozen=True)
class EffectiveArea:
    """Effective area ``Ae`` and the element reductions that produced it."""

    Ae: pint.Quantity
    reductions: tuple[ElementReduction, ...] = ()


def effective_width(element: SlenderElement, Fy: pint.Quantity, Fn: pint.Quantity) -> pint.Quantity:
    """Effective width ``be`` of a slender element (Eqs. E7-2, E7-3 and E7-5).

    ``be = b`` when ``lambda <= lambda_r sqrt(Fy/Fn)``, otherwise
    ``be = b (1 - c1 sqrt(Fel/Fn)) sqrt(Fel/Fn)`` with ``Fel = (c2 lambda_r / lambda)^2 Fy``.
    """
    if element.ratio <= element.limit * math.sqrt(_ratio(Fy, Fn)):
        return element.b.to("in")
    Fel = (element.c2 * element.limit / element.ratio) ** 2 * Fy
    k = math.sqrt(_ratio(Fel, Fn))
    return (element.b * (1 - element.c1 * k) * k).to("in")


def reduce_slender_elements(
    Ag: pint.Quantity, elements: Sequence[SlenderElement], Fy: pint.Quantity, Fn: pint.Quantity
) -> EffectiveArea:
    """Effective area ``Ae = Ag - sum[count (b - be) t]`` for a set of slender elements (Section E7.1)."""
    reductions = tuple(ElementReduction(e.name, e.b.to("in"), effective_width(e, Fy, Fn), e.count) for e in elements)
    lost = sum(
        (r.count * (r.b - r.be) * e.t for r, e in zip(reductions, elements)),
        start=0 * Ag.units,
    )
    return EffectiveArea((Ag - lost).to("in**2"), reductions)


def round_hss_effective_area(
    Ag: pint.Quantity, D: pint.Quantity, t: pint.Quantity, E: pint.Quantity, Fy: pint.Quantity
) -> EffectiveArea:
    """Effective area of round HSS and pipe (Eqs. E7-6 and E7-7).

    Raises:
        ValueError: If ``D/t`` is not below ``0.45 E/Fy``, the upper limit of Section E7.2.
    """
    lam, e_fy = _ratio(D, t), _ratio(E, Fy)
    if lam <= 0.11 * e_fy:
        return EffectiveArea(Ag.to("in**2"))
    if lam < 0.45 * e_fy:
        return EffectiveArea(((0.038 * e_fy / lam + 2 / 3) * Ag).to("in**2"))
    raise ValueError(f"D/t = {lam:.1f} is not below 0.45 E/Fy = {0.45 * e_fy:.1f}")


# --- E1: strength -----------------------------------------------------------------------


@dataclass(frozen=True)
class CompressionLimitState:
    """Compressive strength for one buckling mode.

    Attributes:
        name: Buckling mode.
        reference: Equations used.
        Fe: Elastic buckling stress.
        Fn: Nominal compressive stress, Eq. E3-2 or E3-3.
        Ae: Area used: the gross area, or the effective area for slender elements (Section E7).
        Pn: Nominal compressive strength, ``Fn Ae``.
        slenderness: Effective slenderness ``Lc/r`` for flexural modes, otherwise ``None``.
        reductions: Effective widths of the slender elements, empty when the area is not reduced.
        phi: Resistance factor (LRFD).
        omega: Safety factor (ASD).
    """

    name: str
    reference: str
    Fe: pint.Quantity
    Fn: pint.Quantity
    Ae: pint.Quantity
    Pn: pint.Quantity
    slenderness: float | None = None
    reductions: tuple[ElementReduction, ...] = ()
    phi: float = PHI_COMPRESSION
    omega: float = OMEGA_COMPRESSION

    @property
    def design_strength(self) -> pint.Quantity:
        """LRFD design strength, ``phi_c Pn``, in kips."""
        return (self.phi * self.Pn).to("kip")

    @property
    def allowable_strength(self) -> pint.Quantity:
        """ASD allowable strength, ``Pn / omega_c``, in kips."""
        return (self.Pn / self.omega).to("kip")


@dataclass(frozen=True)
class CompressionStrength:
    """Compressive strength of a member: the lowest of its buckling modes (Section E1).

    Attributes:
        Ag: Gross area.
        limit_states: One entry per buckling mode considered.
        has_slender_elements: True if any element is slender per Table B4.1a, so Section E7 applies.
    """

    Ag: pint.Quantity
    limit_states: tuple[CompressionLimitState, ...]
    has_slender_elements: bool = False

    @property
    def design_strength(self) -> pint.Quantity:
        """Governing LRFD design strength, ``phi_c Pn``, in kips."""
        return min(ls.design_strength for ls in self.limit_states)

    @property
    def allowable_strength(self) -> pint.Quantity:
        """Governing ASD allowable strength, ``Pn / omega_c``, in kips."""
        return min(ls.allowable_strength for ls in self.limit_states)

    @property
    def governing_lrfd(self) -> CompressionLimitState:
        """The limit state with the lowest LRFD design strength."""
        return min(self.limit_states, key=lambda ls: ls.design_strength)

    @property
    def governing_asd(self) -> CompressionLimitState:
        """The limit state with the lowest ASD allowable strength."""
        return min(self.limit_states, key=lambda ls: ls.allowable_strength)

    @property
    def slenderness_ratio(self) -> float | None:
        """Largest effective slenderness ``Lc/r`` among the flexural modes."""
        ratios = [ls.slenderness for ls in self.limit_states if ls.slenderness is not None]
        return max(ratios) if ratios else None

    @property
    def exceeds_recommended_slenderness(self) -> bool:
        """True if ``Lc/r`` exceeds the E2 recommended maximum of 200."""
        ratio = self.slenderness_ratio
        return ratio is not None and ratio > MAX_RECOMMENDED_SLENDERNESS


def effective_lengths(
    Lx: pint.Quantity,
    Ly: pint.Quantity | None = None,
    Lz: pint.Quantity | None = None,
    Kx: float = 1.0,
    Ky: float = 1.0,
    Kz: float = 1.0,
) -> tuple[pint.Quantity, pint.Quantity, pint.Quantity]:
    """Effective lengths ``(Lcx, Lcy, Lcz) = (Kx Lx, Ky Ly, Kz Lz)`` (Section E2).

    ``Ly`` defaults to ``Lx`` and ``Lz`` defaults to ``Ly``.

    Raises:
        TypeError: If a length is not a pint quantity.
        ValueError: If a length or K factor is not positive.
    """
    Lx = require_length(Lx, "Lx")
    Ly = Lx if Ly is None else require_length(Ly, "Ly")
    Lz = Ly if Lz is None else require_length(Lz, "Lz")
    out = []
    for name, L, K in (("x", Lx, Kx), ("y", Ly, Ky), ("z", Lz, Kz)):
        if L.magnitude <= 0:
            raise ValueError(f"L{name} must be positive")
        if K <= 0:
            raise ValueError(f"K{name} must be positive")
        out.append(K * L)
    return tuple(out)  # type: ignore[return-value]


def compression_strength(
    Ag: pint.Quantity,
    material: type[SteelMaterial],
    modes: Sequence[BucklingMode],
    effective_area: Callable[[pint.Quantity], EffectiveArea] | None = None,
    has_slender_elements: bool = False,
) -> CompressionStrength:
    """Compressive strength from a member's buckling modes (Sections E1, E3, E4 and E7).

    Args:
        Ag: Gross area.
        material: Steel material, supplying Fy.
        modes: Elastic buckling modes to check.
        effective_area: Function of ``Fn`` returning the effective area for members with slender
            elements. Omit for members without slender elements, for which ``Pn = Fn Ag`` (E3-1).
        has_slender_elements: Whether Section E7 applies, which sets the equation reference.
    """
    Fy = material.Fy
    states = []
    for mode in modes:
        Fn = nominal_stress(Fy, mode.Fe)
        fn_eq = "E3-2" if _ratio(Fy, mode.Fe) <= FY_FE_LIMIT else "E3-3"
        if has_slender_elements and effective_area is not None:
            area = effective_area(Fn)
            pn_eq = "E7-1"
        else:
            area = EffectiveArea(Ag.to("in**2"))
            pn_eq = "E3-1"
        states.append(
            CompressionLimitState(
                mode.name,
                f"{mode.reference}, Eq. {fn_eq}, Eq. {pn_eq}",
                mode.Fe,
                Fn,
                area.Ae,
                (Fn * area.Ae).to("kip"),
                mode.slenderness,
                area.reductions,
            )
        )
    return CompressionStrength(Ag.to("in**2"), tuple(states), has_slender_elements)
