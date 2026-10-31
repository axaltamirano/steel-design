"""Flexural members, AISC 360-22 Chapter F.

Each ``*_strength`` function below implements one family of sections from Chapter F and returns
a :class:`FlexureStrength` holding every limit state checked. The section classes choose the
function and supply their properties; the local buckling classification comes from the section
(Table B4.1b), so the limits used here are always those of :meth:`Section.classify_flexure`.

======================================  ==========================================================
Function                                Sections
======================================  ==========================================================
:func:`i_shape_major_axis_f2_f3`        Doubly symmetric I-shapes with compact webs, and channels
                                        (F2, F3), major axis
:func:`i_shape_major_axis_f4_f5`        I-shapes with noncompact or slender webs, and singly
                                        symmetric I-shapes (F4, F5), major axis
:func:`i_shape_minor_axis`              I-shapes and channels, minor axis (F6)
:func:`rectangular_hss_strength`        Rectangular HSS and box sections (F7)
:func:`round_hss_strength`              Round HSS and pipe (F8)
:func:`tee_strength`                    Tees and double angles in the plane of symmetry (F9)
:func:`single_angle_strength`           Single angles (F10), built from the helpers in this module
======================================  ==========================================================

Not included: bars (F11) and unsymmetrical shapes (F12), which the library has no sections for;
the reduction for holes in the tension flange (F13.1); and channels with noncompact or slender
elements, tees and double angles in minor-axis bending, and rectangular HSS or box sections that
mix slender flanges with slender webs (all outside the scope of the Chapter F equations).

The lateral-torsional buckling modification factor ``Cb`` is supplied by the user (default 1.0);
:func:`cb` evaluates Eq. F1-1 from moments along the unbraced length.

Internally the equations work on floats in kips, inches and ksi; results are pint quantities.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pint

from steel_design.classification import ElementClassification, Slenderness, kc as kc_factor
from steel_design.materials.base import SteelMaterial
from steel_design.resistance_factors import ResistanceFactors
from steel_design.units import Q_, require_length

#: Cb is limited to 1.5 for single angles (Section F10.2).
ANGLE_CB_LIMIT = 1.5


# --- result types ---------------------------------------------------------------------


@dataclass(frozen=True)
class FlexureLimitState:
    """Nominal flexural strength for one limit state.

    Attributes:
        name: Limit state, e.g. ``"lateral-torsional buckling"``.
        reference: Equations used.
        Mn: Nominal flexural strength in kip-ft.
        phi: Resistance factor, from :class:`~steel_design.resistance_factors.ResistanceFactors`.
    """

    name: str
    reference: str
    Mn: pint.Quantity
    phi: float = ResistanceFactors.FLEXURE

    @property
    def design_strength(self) -> pint.Quantity:
        """Design strength, ``phi_b Mn``, in kip-ft."""
        return (self.phi * self.Mn).to("kip*ft")


@dataclass(frozen=True)
class FlexureStrength:
    """Flexural strength of a member about one axis: the lowest of its limit states.

    Attributes:
        axis: Axis of bending.
        limit_states: One entry per limit state that can apply.
        Mp: Plastic moment (or the yielding strength used as ``Mp``), when defined.
        Lp: Limiting unbraced length for the limit state of yielding, when defined.
        Lr: Limiting unbraced length for inelastic lateral-torsional buckling, when defined.
        Cb: Lateral-torsional buckling modification factor used.
    """

    axis: str
    limit_states: tuple[FlexureLimitState, ...]
    Mp: pint.Quantity | None = None
    Lp: pint.Quantity | None = None
    Lr: pint.Quantity | None = None
    Cb: float = 1.0

    @property
    def design_strength(self) -> pint.Quantity:
        """Governing design strength, ``phi_b Mn``, in kip-ft."""
        return min(ls.design_strength for ls in self.limit_states)

    @property
    def governing(self) -> FlexureLimitState:
        """The limit state with the lowest design strength."""
        return min(self.limit_states, key=lambda ls: ls.design_strength)


# --- helpers --------------------------------------------------------------------------


def _moment(value: float | pint.Quantity) -> float:
    """Absolute value of a moment in kip-ft; plain numbers are taken as kip-ft."""
    if isinstance(value, pint.Quantity):
        return abs(float(value.to("kip*ft").magnitude))
    return abs(float(value))


def cb(Mmax: float | pint.Quantity, MA: float | pint.Quantity, MB: float | pint.Quantity, MC: float | pint.Quantity) -> float:
    """Lateral-torsional buckling modification factor for nonuniform moment (Eq. F1-1).

    ``Cb = 12.5 Mmax / (2.5 Mmax + 3 MA + 4 MB + 3 MC)``, with the absolute values of the
    maximum moment and of the moments at the quarter point, centerline and three-quarter point of
    the unbraced segment. Plain numbers are taken as kip-ft.

    Raises:
        ValueError: If ``Mmax`` is zero.
    """
    m_max, m_a, m_b, m_c = _moment(Mmax), _moment(MA), _moment(MB), _moment(MC)
    if m_max == 0:
        raise ValueError("Mmax must be nonzero")
    return 12.5 * m_max / (2.5 * m_max + 3 * m_a + 4 * m_b + 3 * m_c)


def _length(value, name: str) -> float:
    """A positive unbraced length in inches."""
    length = require_length(value, name)
    if length.magnitude <= 0:
        raise ValueError(f"{name} must be positive")
    return float(length.magnitude)


def check_Cb(Cb: float) -> float:
    """Validate a Cb value.

    Raises:
        ValueError: If ``Cb`` is not positive.
    """
    if Cb <= 0:
        raise ValueError("Cb must be positive")
    return float(Cb)


def _state(name: str, reference: str, Mn_kip_in: float) -> FlexureLimitState:
    return FlexureLimitState(name, reference, Q_(Mn_kip_in, "kip*in").to("kip*ft"))


def _q(value: float, unit: str) -> pint.Quantity:
    return Q_(value, unit)


def _f(quantity: pint.Quantity, unit: str) -> float:
    return float(quantity.to(unit).magnitude)


def _interp(upper: float, lower: float, lam: float, lam_p: float, lam_r: float) -> float:
    """Linear transition ``upper - (upper - lower)(lam - lam_p)/(lam_r - lam_p)``."""
    return upper - (upper - lower) * (lam - lam_p) / (lam_r - lam_p)


# --- F2, F3: doubly symmetric I-shapes and channels, major axis ---------------------------


def i_shape_major_axis_f2_f3(
    material: type[SteelMaterial],
    Lb: pint.Quantity,
    Cb: float,
    *,
    Zx: pint.Quantity,
    Sx: pint.Quantity,
    ry: pint.Quantity,
    rts: pint.Quantity,
    J: pint.Quantity,
    ho: pint.Quantity,
    flange: ElementClassification,
    h_tw: float,
    c: float = 1.0,
) -> FlexureStrength:
    """Major-axis flexure of doubly symmetric I-shapes and channels with compact webs.

    Implements yielding (F2-1), lateral-torsional buckling (F2-2, F2-3, F2-4) and, for a
    noncompact or slender flange, compression flange local buckling (F3-1, F3-2).

    Args:
        material: Steel material.
        Lb: Unbraced length.
        Cb: Lateral-torsional buckling modification factor.
        Zx, Sx: Plastic and elastic section moduli about the x-axis.
        ry: Radius of gyration about the y-axis.
        rts: Effective radius of gyration for lateral-torsional buckling (Eq. F2-7).
        J: Torsional constant.
        ho: Distance between flange centroids.
        flange: Classification of the flange (Table B4.1b).
        h_tw: Web slenderness ``h/tw``, which sets ``kc`` for slender flanges.
        c: 1 for doubly symmetric I-shapes; for channels ``(ho/2) sqrt(Iy/Cw)`` (Eq. F2-8b).
    """
    Fy, E = _f(material.Fy, "ksi"), _f(material.E, "ksi")
    Lb_, Cb = _length(Lb, "Lb"), check_Cb(Cb)
    Zx_, Sx_, ry_, rts_ = _f(Zx, "in**3"), _f(Sx, "in**3"), _f(ry, "in"), _f(rts, "in")
    J_, ho_ = _f(J, "in**4"), _f(ho, "in")

    Mp = Fy * Zx_
    Lp = 1.76 * ry_ * math.sqrt(E / Fy)
    jc = J_ * c / (Sx_ * ho_)
    Lr = 1.95 * rts_ * E / (0.7 * Fy) * math.sqrt(jc + math.sqrt(jc**2 + 6.76 * (0.7 * Fy / E) ** 2))

    states = [_state("yielding", "Eq. F2-1", Mp)]
    if Lb_ > Lp:
        if Lb_ <= Lr:
            mn = min(Mp, Cb * _interp(Mp, 0.7 * Fy * Sx_, Lb_, Lp, Lr))
            states.append(_state("lateral-torsional buckling", "Eq. F2-2", mn))
        else:
            fcr = Cb * math.pi**2 * E / (Lb_ / rts_) ** 2 * math.sqrt(1 + 0.078 * jc * (Lb_ / rts_) ** 2)
            states.append(_state("lateral-torsional buckling", "Eq. F2-3, F2-4", min(fcr * Sx_, Mp)))

    if flange.classification is not Slenderness.COMPACT:
        lam = flange.ratio
        if flange.classification is Slenderness.NONCOMPACT:
            mn = _interp(Mp, 0.7 * Fy * Sx_, lam, flange.limit_p, flange.limit_r)
            states.append(_state("compression flange local buckling", "Eq. F3-1", mn))
        else:
            mn = 0.9 * E * kc_factor(h_tw) * Sx_ / lam**2
            states.append(_state("compression flange local buckling", "Eq. F3-2", mn))
    return FlexureStrength("x", tuple(states), _q(Mp, "kip*in").to("kip*ft"), _q(Lp, "in"), _q(Lr, "in"), Cb)


# --- F4, F5: I-shapes with noncompact or slender webs, major axis ------------------------


def _plastification_factor(M_ratio: float, lam: float, lam_pw: float, lam_rw: float) -> float:
    """Web plastification factor ``Rpc`` or ``Rpt`` (Eqs. F4-9 and F4-10, F4-15 and F4-16).

    ``M_ratio`` is ``Mp/My`` for the flange concerned.
    """
    if lam <= lam_pw:
        return M_ratio
    return min(M_ratio, M_ratio - (M_ratio - 1) * (lam - lam_pw) / (lam_rw - lam_pw))


def i_shape_major_axis_f4_f5(
    material: type[SteelMaterial],
    Lb: pint.Quantity,
    Cb: float,
    *,
    Zx: pint.Quantity,
    Sxc: pint.Quantity,
    Sxt: pint.Quantity,
    Iy: pint.Quantity,
    Iyc: pint.Quantity,
    J: pint.Quantity,
    ho: pint.Quantity,
    tw: pint.Quantity,
    bfc: pint.Quantity,
    tfc: pint.Quantity,
    h_tw: float,
    flange: ElementClassification,
    web: ElementClassification,
) -> FlexureStrength:
    """Major-axis flexure of I-shapes with noncompact or slender webs, and of singly symmetric
    I-shapes with compact or noncompact webs (F4); and with slender webs (F5).

    The web classification is that of Table B4.1b, with ``web.ratio = hc/tw``. Limit states are
    compression flange yielding (F4-1, F5-1), lateral-torsional buckling (F4-2 to F4-5, F5-2 to
    F5-4), compression flange local buckling (F4-12, F4-13, F5-7 to F5-9) and, when the tension
    flange is the smaller (``Sxt < Sxc``), tension flange yielding (F4-14, F5-10).

    Args:
        material: Steel material.
        Lb: Unbraced length.
        Cb: Lateral-torsional buckling modification factor.
        Zx: Plastic section modulus about the x-axis.
        Sxc, Sxt: Elastic section moduli referred to the compression and tension flanges.
        Iy: Moment of inertia about the y-axis.
        Iyc: Moment of inertia of the compression flange about the y-axis.
        J: Torsional constant.
        ho: Distance between flange centroids.
        tw: Web thickness.
        bfc, tfc: Width and thickness of the compression flange.
        h_tw: Web slenderness ``h/tw``, which sets ``kc``.
        flange: Classification of the compression flange (Table B4.1b).
        web: Classification of the web, ``ratio = hc/tw``.
    """
    Fy, E = _f(material.Fy, "ksi"), _f(material.E, "ksi")
    Lb_, Cb = _length(Lb, "Lb"), check_Cb(Cb)
    Zx_, Sxc_, Sxt_ = _f(Zx, "in**3"), _f(Sxc, "in**3"), _f(Sxt, "in**3")
    Iy_, Iyc_, J_, ho_ = _f(Iy, "in**4"), _f(Iyc, "in**4"), _f(J, "in**4"), _f(ho, "in")
    tw_, bfc_, tfc_ = _f(tw, "in"), _f(bfc, "in"), _f(tfc, "in")
    kc = kc_factor(h_tw)
    slender_web = web.classification is Slenderness.SLENDER
    lam_w = web.ratio
    hc = lam_w * tw_
    aw = hc * tw_ / (bfc_ * tfc_)
    sqrt_e_fy = math.sqrt(E / Fy)

    Myc = Fy * Sxc_
    Mp = min(Fy * Zx_, 1.6 * Myc)
    rt = bfc_ / math.sqrt(12 * (1 + aw / 6))
    Lp = 1.1 * rt * sqrt_e_fy
    sxt_sxc = Sxt_ / Sxc_
    FL = 0.7 * Fy if sxt_sxc >= 0.7 else max(Fy * sxt_sxc, 0.5 * Fy)
    J_ltb = 0.0 if Iyc_ / Iy_ <= 0.23 else J_
    jc = J_ltb / (Sxc_ * ho_)

    def fcr_elastic() -> float:
        ratio = Lb_ / rt
        return Cb * math.pi**2 * E / ratio**2 * math.sqrt(1 + 0.078 * jc * ratio**2)

    states: list[FlexureLimitState] = []
    if slender_web:
        # F5
        aw5 = min(aw, 10.0)
        Rpg = min(1.0, 1 - aw5 / (1200 + 300 * aw5) * (lam_w - 5.7 * sqrt_e_fy))
        Lr = math.pi * rt * math.sqrt(E / (0.7 * Fy))
        states.append(_state("compression flange yielding", "Eq. F5-1", Rpg * Fy * Sxc_))
        if Lb_ > Lp:
            if Lb_ <= Lr:
                fcr = min(Fy, Cb * (Fy - 0.3 * Fy * (Lb_ - Lp) / (Lr - Lp)))
                states.append(_state("lateral-torsional buckling", "Eq. F5-2, F5-3", Rpg * fcr * Sxc_))
            else:
                fcr = min(Fy, Cb * math.pi**2 * E / (Lb_ / rt) ** 2)
                states.append(_state("lateral-torsional buckling", "Eq. F5-2, F5-4", Rpg * fcr * Sxc_))
        if flange.classification is Slenderness.NONCOMPACT:
            fcr = _interp(Fy, 0.7 * Fy, flange.ratio, flange.limit_p, flange.limit_r)
            states.append(_state("compression flange local buckling", "Eq. F5-7, F5-8", Rpg * fcr * Sxc_))
        elif flange.classification is Slenderness.SLENDER:
            fcr = 0.9 * E * kc / flange.ratio**2
            states.append(_state("compression flange local buckling", "Eq. F5-7, F5-9", Rpg * fcr * Sxc_))
        if Sxt_ < Sxc_:
            states.append(_state("tension flange yielding", "Eq. F5-10", Fy * Sxt_))
        return FlexureStrength("x", tuple(states), _q(Fy * Zx_, "kip*in").to("kip*ft"), _q(Lp, "in"), _q(Lr, "in"), Cb)

    # F4
    Rpc = 1.0 if Iyc_ / Iy_ <= 0.23 else _plastification_factor(Mp / Myc, lam_w, web.limit_p, web.limit_r)
    Mn_yield = Rpc * Myc
    Lr = (
        1.95
        * rt
        * E
        / FL
        * math.sqrt(J_ / (Sxc_ * ho_) + math.sqrt((J_ / (Sxc_ * ho_)) ** 2 + 6.76 * (FL / E) ** 2))
    )
    states.append(_state("compression flange yielding", "Eq. F4-1", Mn_yield))
    if Lb_ > Lp:
        if Lb_ <= Lr:
            mn = min(Mn_yield, Cb * _interp(Mn_yield, FL * Sxc_, Lb_, Lp, Lr))
            states.append(_state("lateral-torsional buckling", "Eq. F4-2", mn))
        else:
            states.append(_state("lateral-torsional buckling", "Eq. F4-3, F4-5", min(fcr_elastic() * Sxc_, Mn_yield)))
    if flange.classification is Slenderness.NONCOMPACT:
        mn = _interp(Mn_yield, FL * Sxc_, flange.ratio, flange.limit_p, flange.limit_r)
        states.append(_state("compression flange local buckling", "Eq. F4-12", mn))
    elif flange.classification is Slenderness.SLENDER:
        states.append(_state("compression flange local buckling", "Eq. F4-13", 0.9 * E * kc * Sxc_ / flange.ratio**2))
    if Sxt_ < Sxc_:
        Myt = Fy * Sxt_
        Mp_t = min(Fy * Zx_, 1.6 * Myt)
        Rpt = _plastification_factor(Mp_t / Myt, lam_w, web.limit_p, web.limit_r)
        states.append(_state("tension flange yielding", "Eq. F4-14", Rpt * Myt))
    return FlexureStrength("x", tuple(states), _q(Mp, "kip*in").to("kip*ft"), _q(Lp, "in"), _q(Lr, "in"), Cb)


# --- F6: I-shapes and channels, minor axis ---------------------------------------------


def i_shape_minor_axis(
    material: type[SteelMaterial],
    *,
    Zy: pint.Quantity,
    Sy: pint.Quantity,
    flanges: dict[str, ElementClassification],
) -> FlexureStrength:
    """Minor-axis flexure of I-shapes and channels (Section F6).

    There is no lateral-torsional buckling. The limit states are yielding (F6-1) and flange
    local buckling (F6-2, F6-3) for each flange in compression.

    Args:
        material: Steel material.
        Zy, Sy: Plastic and elastic section moduli about the y-axis.
        flanges: Flange classifications keyed by flange name (one entry per flange that can be
            in compression); ``ratio`` is ``b/tf``.
    """
    Fy, E = _f(material.Fy, "ksi"), _f(material.E, "ksi")
    Zy_, Sy_ = _f(Zy, "in**3"), _f(Sy, "in**3")
    Mp = min(Fy * Zy_, 1.6 * Fy * Sy_)
    states = [_state("yielding", "Eq. F6-1", Mp)]
    for name, flange in flanges.items():
        suffix = f" ({name})" if len(flanges) > 1 else ""
        if flange.classification is Slenderness.NONCOMPACT:
            mn = _interp(Mp, 0.7 * Fy * Sy_, flange.ratio, flange.limit_p, flange.limit_r)
            states.append(_state("flange local buckling" + suffix, "Eq. F6-2", mn))
        elif flange.classification is Slenderness.SLENDER:
            mn = 0.69 * E / flange.ratio**2 * Sy_
            states.append(_state("flange local buckling" + suffix, "Eq. F6-3, F6-4", mn))
    return FlexureStrength("y", tuple(states), _q(Mp, "kip*in").to("kip*ft"))


# --- F7: rectangular HSS and box sections ---------------------------------------------


def effective_section_modulus(
    I: pint.Quantity,
    A: pint.Quantity,
    depth: pint.Quantity,
    t_flange: pint.Quantity,
    b_flat: pint.Quantity,
    b_effective: pint.Quantity,
) -> pint.Quantity:
    """Elastic section modulus of a rectangular tube with a reduced compression flange (F7.2(c)).

    The ineffective part of the compression flange, ``(b - be) t``, is removed at the flange
    centerline, and the modulus is taken to the extreme compression fiber of the new centroid.

    Args:
        I: Moment of inertia of the full section about the axis of bending.
        A: Gross area.
        depth: Overall dimension in the plane of bending.
        t_flange: Thickness of the compression flange.
        b_flat: Flat width of the compression flange.
        b_effective: Effective width ``be``.
    """
    I_, A_, H, t = _f(I, "in**4"), _f(A, "in**2"), _f(depth, "in"), _f(t_flange, "in")
    a = (_f(b_flat, "in") - _f(b_effective, "in")) * t
    y = H / 2 - t / 2
    I_new = I_ - a * y**2 - a**2 * y**2 / (A_ - a)
    c_top = H / 2 + a * y / (A_ - a)
    return _q(I_new / c_top, "in**3")


def rectangular_hss_strength(
    material: type[SteelMaterial],
    axis: str,
    Lb: pint.Quantity | None,
    Cb: float,
    *,
    Z: pint.Quantity,
    S: pint.Quantity,
    I: pint.Quantity,
    A: pint.Quantity,
    ry: pint.Quantity,
    J: pint.Quantity,
    depth: pint.Quantity,
    t_flange: pint.Quantity,
    t_web: pint.Quantity,
    flange: ElementClassification,
    web: ElementClassification,
    box: bool = False,
    ltb: bool = True,
) -> FlexureStrength:
    """Flexure of rectangular HSS and box sections about either axis (Section F7).

    Limit states are yielding (F7-1), flange local buckling (F7-2, F7-3, F7-4 with the effective
    width of F7-5), web local buckling (F7-6, F7-7) and, about the major axis of a section that
    is not square, lateral-torsional buckling (F7-10 to F7-12).

    Args:
        material: Steel material.
        axis: ``"x"`` or ``"y"``.
        Lb: Unbraced length; required when ``ltb`` is true.
        Cb: Lateral-torsional buckling modification factor.
        Z, S, I: Plastic and elastic section moduli and moment of inertia about the axis.
        A: Gross area.
        ry: Radius of gyration about the y-axis (used for lateral-torsional buckling).
        J: Torsional constant.
        depth: Overall dimension in the plane of bending.
        t_flange, t_web: Thickness of the walls in compression (flanges) and of the walls parallel
            to the plane of bending (webs).
        flange, web: Classifications of the flange and the web (Table B4.1b), ratios ``b/t`` and ``h/t``.
        box: True for built-up boxes (coefficient 0.34 in Eq. F7-5), false for HSS (0.38).
        ltb: Whether lateral-torsional buckling applies (major axis, not a square section).
    """
    Fy, E = _f(material.Fy, "ksi"), _f(material.E, "ksi")
    Cb = check_Cb(Cb)
    Z_, S_ = _f(Z, "in**3"), _f(S, "in**3")
    Mp = Fy * Z_
    sqrt_e_fy = math.sqrt(E / Fy)
    states = [_state("yielding", "Eq. F7-1", Mp)]

    if flange.classification is Slenderness.NONCOMPACT:
        mn = min(Mp, _interp(Mp, Fy * S_, flange.ratio, flange.limit_p, flange.limit_r))
        states.append(_state("flange local buckling", "Eq. F7-2", mn))
    elif flange.classification is Slenderness.SLENDER:
        lam = flange.ratio
        coefficient = 0.34 if box else 0.38
        t_f = _f(t_flange, "in")
        b_flat = lam * t_f
        be = min(b_flat, 1.92 * t_f * sqrt_e_fy * (1 - coefficient / lam * sqrt_e_fy))
        Se = effective_section_modulus(I, A, depth, t_flange, _q(b_flat, "in"), _q(be, "in"))
        states.append(_state("flange local buckling", "Eq. F7-3, F7-4", Fy * _f(Se, "in**3")))

    if web.classification is Slenderness.NONCOMPACT:
        mn = min(Mp, _interp(Mp, Fy * S_, web.ratio, web.limit_p, web.limit_r))
        states.append(_state("web local buckling", "Eq. F7-6", mn))
    elif web.classification is Slenderness.SLENDER:
        t_w, t_f = _f(t_web, "in"), _f(t_flange, "in")
        hw = web.ratio * t_w
        b_flat = flange.ratio * t_f
        aw = min(2 * hw * t_w / (b_flat * t_f), 10.0)
        Rpg = min(1.0, 1 - aw / (1200 + 300 * aw) * (web.ratio - 5.7 * sqrt_e_fy))
        states.append(_state("web local buckling", "Eq. F7-7, F5-6", Rpg * Fy * S_))

    Lp = Lr = None
    if ltb:
        if Lb is None:
            raise ValueError("Lb is required for lateral-torsional buckling")
        Lb_ = _length(Lb, "Lb")
        ry_, J_, A_ = _f(ry, "in"), _f(J, "in**4"), _f(A, "in**2")
        root = E * ry_ * math.sqrt(J_ * A_)
        Lp_ = 0.13 * root / Mp
        Lr_ = 2.0 * root / (0.7 * Fy * S_)
        Lp, Lr = _q(Lp_, "in"), _q(Lr_, "in")
        if Lb_ > Lp_:
            if Lb_ <= Lr_:
                mn = min(Mp, Cb * _interp(Mp, 0.7 * Fy * S_, Lb_, Lp_, Lr_))
                states.append(_state("lateral-torsional buckling", "Eq. F7-10", mn))
            else:
                mn = min(Mp, 2 * E * Cb * ry_ * math.sqrt(J_ * A_) / Lb_)
                states.append(_state("lateral-torsional buckling", "Eq. F7-11", mn))
    return FlexureStrength(axis, tuple(states), _q(Mp, "kip*in").to("kip*ft"), Lp, Lr, Cb)


# --- F8: round HSS and pipe -----------------------------------------------------------


def round_hss_strength(
    material: type[SteelMaterial],
    *,
    Z: pint.Quantity,
    S: pint.Quantity,
    wall: ElementClassification,
) -> FlexureStrength:
    """Flexure of round HSS and pipe (Section F8). There is no lateral-torsional buckling.

    Raises:
        ValueError: If ``D/t`` is not below ``0.45 E/Fy``, the upper limit of Section F8.
    """
    Fy, E = _f(material.Fy, "ksi"), _f(material.E, "ksi")
    Z_, S_ = _f(Z, "in**3"), _f(S, "in**3")
    Mp = Fy * Z_
    lam = wall.ratio
    if lam >= 0.45 * E / Fy:
        raise ValueError(f"D/t = {lam:.1f} is not below 0.45 E/Fy = {0.45 * E / Fy:.1f}")
    states = [_state("yielding", "Eq. F8-1", Mp)]
    if wall.classification is Slenderness.NONCOMPACT:
        states.append(_state("local buckling", "Eq. F8-2", (0.021 * E / lam + Fy) * S_))
    elif wall.classification is Slenderness.SLENDER:
        states.append(_state("local buckling", "Eq. F8-3, F8-4", 0.33 * E / lam * S_))
    return FlexureStrength("x", tuple(states), _q(Mp, "kip*in").to("kip*ft"))


# --- F9: tees and double angles -------------------------------------------------------


def _tee_mcr(E: float, Lb: float, Iy: float, J: float, d: float, stem_in_tension: bool) -> float:
    """Elastic lateral-torsional buckling moment of a tee or double angle (Eqs. F9-4 and F9-5)."""
    B = (1 if stem_in_tension else -1) * 2.3 * (d / Lb) * math.sqrt(Iy / J)
    return 1.95 * E / Lb * math.sqrt(Iy * J) * (B + math.sqrt(1 + B**2))


def _tee_limits(Fy: float, E: float, ry: float, Iy: float, J: float, Sx: float, d: float) -> tuple[float, float]:
    """Lp (Eq. F9-5) and Lr (Eq. F9-6) of tees and double angles."""
    Lp = 1.76 * ry * math.sqrt(E / Fy)
    Lr = 1.95 * (E / Fy) * (math.sqrt(Iy * J) / Sx) * math.sqrt(2.36 * (Fy / E) * (d * Sx / J) + 1)
    return Lp, Lr


def _leg_local_buckling(Fy: float, E: float, Sc: float, lam: float, lam_p: float, lam_r: float) -> tuple[str, float] | None:
    """Leg local buckling of angle legs in flexural compression (Eqs. F10-7 to F10-9).

    Returns the equation reference and ``Mn``, or ``None`` for a compact leg."""
    if lam <= lam_p:
        return None
    if lam <= lam_r:
        return "Eq. F10-7", Fy * Sc * (2.43 - 1.72 * lam * math.sqrt(Fy / E))
    return "Eq. F10-8, F10-9", 0.71 * E / lam**2 * Sc


def tee_strength(
    material: type[SteelMaterial],
    Lb: pint.Quantity,
    *,
    Zx: pint.Quantity,
    Sx: pint.Quantity,
    Sxc: pint.Quantity,
    Iy: pint.Quantity,
    J: pint.Quantity,
    d: pint.Quantity,
    ry: pint.Quantity,
    stem_in_tension: bool,
    flange: ElementClassification,
    stem: ElementClassification,
) -> FlexureStrength:
    """Flexure of tees loaded in the plane of symmetry (Section F9). There is no ``Cb`` in F9.

    With the stem in tension the limit states are yielding (F9-1), lateral-torsional buckling
    (F9-2, F9-3) and flange local buckling (F9-6 to F9-8). With the stem in compression they
    are yielding (``Mp = My``), lateral-torsional buckling (F9-4 with ``Mn <= My``) and stem
    local buckling (F9-9 to F9-11).

    Args:
        material: Steel material.
        Lb: Unbraced length.
        Zx: Plastic section modulus.
        Sx: Elastic section modulus to the tip of the stem (the smaller modulus).
        Sxc: Elastic section modulus to the flange, ``Ix/y``.
        Iy, J: Moment of inertia about the y-axis and torsional constant.
        d: Overall depth of the tee.
        ry: Radius of gyration about the y-axis.
        stem_in_tension: True if the stem is in flexural tension (flange in compression).
        flange, stem: Classifications of the flange and the stem (Table B4.1b).
    """
    Fy, E = _f(material.Fy, "ksi"), _f(material.E, "ksi")
    Lb_ = _length(Lb, "Lb")
    Zx_, Sx_, Sxc_ = _f(Zx, "in**3"), _f(Sx, "in**3"), _f(Sxc, "in**3")
    Iy_, J_, d_, ry_ = _f(Iy, "in**4"), _f(J, "in**4"), _f(d, "in"), _f(ry, "in")
    My = Fy * Sx_
    Lp, Lr = _tee_limits(Fy, E, ry_, Iy_, J_, Sx_, d_)
    Mcr = _tee_mcr(E, Lb_, Iy_, J_, d_, stem_in_tension)

    if stem_in_tension:
        Mp = min(Fy * Zx_, 1.6 * My)
        states = [_state("yielding", "Eq. F9-1", Mp)]
        if Lb_ > Lp:
            if Lb_ <= Lr:
                states.append(_state("lateral-torsional buckling", "Eq. F9-2", Mp - (Mp - My) * (Lb_ - Lp) / (Lr - Lp)))
            else:
                states.append(_state("lateral-torsional buckling", "Eq. F9-3, F9-4", min(Mcr, Mp)))
        if flange.classification is Slenderness.NONCOMPACT:
            mn = min(1.6 * My, _interp(Mp, 0.7 * Fy * Sxc_, flange.ratio, flange.limit_p, flange.limit_r))
            states.append(_state("flange local buckling", "Eq. F9-6", mn))
        elif flange.classification is Slenderness.SLENDER:
            states.append(_state("flange local buckling", "Eq. F9-7", 0.7 * E * Sxc_ / flange.ratio**2))
    else:
        Mp = My
        states = [
            _state("yielding", "Eq. F9-1 (Mp = My)", My),
            _state("lateral-torsional buckling", "Eq. F9-3, F9-4", min(Mcr, My)),
        ]
        lam, root = stem.ratio, math.sqrt(Fy / E)
        if lam > 0.84 * math.sqrt(E / Fy):
            if lam <= 1.52 * math.sqrt(E / Fy):
                fcr = (1.43 - 0.515 * lam * root) * Fy
                ref = "Eq. F9-9, F9-10"
            else:
                fcr = 1.52 * E / lam**2
                ref = "Eq. F9-9, F9-11"
            states.append(_state("stem local buckling", ref, fcr * Sx_))
    return FlexureStrength("x", tuple(states), _q(Mp, "kip*in").to("kip*ft"), _q(Lp, "in"), _q(Lr, "in"))


def double_angle_strength(
    material: type[SteelMaterial],
    Lb: pint.Quantity,
    *,
    Zx: pint.Quantity,
    Sx: pint.Quantity,
    Sxc: pint.Quantity,
    Iy: pint.Quantity,
    J: pint.Quantity,
    d: pint.Quantity,
    ry: pint.Quantity,
    web_legs_in_tension: bool,
    flange_leg: ElementClassification,
    web_leg: ElementClassification,
) -> FlexureStrength:
    """Flexure of double angles loaded in the plane of symmetry (Sections F9 and F10.3).

    With the web legs in tension (flange legs in compression) the limit states are yielding
    (F9-1), lateral-torsional buckling (F9-2, F9-3, F9-4) and local buckling of the flange legs
    (F10-7 to F10-9). With the web legs in compression they are yielding with ``Mp = 1.5 My``,
    lateral-torsional buckling by Eqs. F10-2 and F10-3 with the ``Mcr`` of Eq. F9-4, and local
    buckling of the web legs.

    Args:
        material: Steel material.
        Lb: Unbraced length.
        Zx: Plastic section modulus.
        Sx: Elastic section modulus to the toe of the web legs (the smaller modulus).
        Sxc: Elastic section modulus to the flange legs, ``Ix/y``.
        Iy, J: Moment of inertia about the y-axis and torsional constant.
        d: Width of the web legs (back to back).
        ry: Radius of gyration about the y-axis.
        web_legs_in_tension: True if the web legs are in flexural tension.
        flange_leg, web_leg: Classifications of the outstanding (flange) legs and the web legs,
            ratios ``b/t`` and ``d/t`` (Table B4.1b Case 12).
    """
    Fy, E = _f(material.Fy, "ksi"), _f(material.E, "ksi")
    Lb_ = _length(Lb, "Lb")
    Zx_, Sx_, Sxc_ = _f(Zx, "in**3"), _f(Sx, "in**3"), _f(Sxc, "in**3")
    Iy_, J_, d_, ry_ = _f(Iy, "in**4"), _f(J, "in**4"), _f(d, "in"), _f(ry, "in")
    My = Fy * Sx_
    Lp, Lr = _tee_limits(Fy, E, ry_, Iy_, J_, Sx_, d_)

    if web_legs_in_tension:
        Mp = min(Fy * Zx_, 1.6 * My)
        Mcr = _tee_mcr(E, Lb_, Iy_, J_, d_, True)
        states = [_state("yielding", "Eq. F9-1", Mp)]
        if Lb_ > Lp:
            if Lb_ <= Lr:
                states.append(_state("lateral-torsional buckling", "Eq. F9-2", Mp - (Mp - My) * (Lb_ - Lp) / (Lr - Lp)))
            else:
                states.append(_state("lateral-torsional buckling", "Eq. F9-3, F9-4", min(Mcr, Mp)))
        local = _leg_local_buckling(Fy, E, Sxc_, flange_leg.ratio, flange_leg.limit_p, flange_leg.limit_r)
        local_name = "flange leg local buckling"
    else:
        Mp = 1.5 * My
        Mcr = _tee_mcr(E, Lb_, Iy_, J_, d_, False)
        states = [
            _state("yielding", "Eq. F9-1 (Mp = 1.5 My)", Mp),
            _state("lateral-torsional buckling", "Eq. F10-2, F10-3, F9-4", _angle_ltb(My, Mcr)),
        ]
        local = _leg_local_buckling(Fy, E, Sx_, web_leg.ratio, web_leg.limit_p, web_leg.limit_r)
        local_name = "web leg local buckling"
    if local is not None:
        states.append(_state(local_name, local[0], local[1]))
    return FlexureStrength("x", tuple(states), _q(Mp, "kip*in").to("kip*ft"), _q(Lp, "in"), _q(Lr, "in"))


# --- F10: single angles ---------------------------------------------------------------


def _angle_ltb(My: float, Mcr: float) -> float:
    """Lateral-torsional buckling strength of angles (Eqs. F10-2 and F10-3)."""
    if My / Mcr <= 1.0:
        return min(1.5 * My, (1.92 - 1.17 * math.sqrt(My / Mcr)) * My)
    return (0.92 - 0.17 * Mcr / My) * Mcr


def principal_axis_mcr(
    E: pint.Quantity,
    A: pint.Quantity,
    rz: pint.Quantity,
    t: pint.Quantity,
    Lb: pint.Quantity,
    Cb: float,
    beta_w: pint.Quantity,
) -> pint.Quantity:
    """Elastic lateral-torsional buckling moment for bending about the major principal axis of a
    single angle (Eq. F10-4).

    ``beta_w`` is positive when the short legs are in compression and negative when the long
    legs are in compression; it is zero for equal-leg angles.
    """
    E_, A_, rz_, t_ = _f(E, "ksi"), _f(A, "in**2"), _f(rz, "in"), _f(t, "in")
    Lb_, bw = _length(Lb, "Lb"), _f(beta_w, "in")
    term = 4.4 * bw * rz_ / (Lb_ * t_)
    Mcr = 9 * E_ * A_ * rz_ * t_ * Cb / (8 * Lb_) * (math.sqrt(1 + term**2) + term)
    return _q(Mcr, "kip*in")


def geometric_axis_mcr(
    E: pint.Quantity,
    b: pint.Quantity,
    t: pint.Quantity,
    Lb: pint.Quantity,
    Cb: float,
    toe_in_compression: bool,
    restrained: bool,
) -> pint.Quantity:
    """Elastic lateral-torsional buckling moment for bending about a geometric axis of an
    equal-leg angle (Eqs. F10-5a and F10-5b), 1.25 times larger with lateral-torsional restraint
    at the point of maximum moment only."""
    E_, b_, t_, Lb_ = _f(E, "ksi"), _f(b, "in"), _f(t, "in"), _length(Lb, "Lb")
    sign = -1.0 if toe_in_compression else 1.0
    Mcr = 0.58 * E_ * b_**4 * t_ * Cb / Lb_**2 * (math.sqrt(1 + 0.88 * (Lb_ * t_ / b_**2) ** 2) + sign)
    return _q(1.25 * Mcr if restrained else Mcr, "kip*in")


def single_angle_strength(
    material: type[SteelMaterial],
    axis: str,
    *,
    My: pint.Quantity,
    Cb: float = 1.0,
    ltb_My: pint.Quantity | None = None,
    Mcr: pint.Quantity | None = None,
    legs: dict[str, tuple[pint.Quantity, ElementClassification]] | None = None,
) -> FlexureStrength:
    """Flexure of a single angle (Section F10) from its yield moments and buckling moment.

    The limit states are yielding, ``Mn = 1.5 My`` (F10-1), lateral-torsional buckling (F10-2,
    F10-3) when ``Mcr`` is given, and leg local buckling (F10-7 to F10-9) for each leg whose toe is
    in compression.

    Args:
        material: Steel material.
        axis: Axis of bending, for the result.
        My: Yield moment about the axis of bending.
        Cb: The factor used (reported only).
        ltb_My: Yield moment to use in the lateral-torsional buckling equations, when different
            from ``My`` (0.8 of the geometric-axis value of an equal-leg angle without restraint).
        Mcr: Elastic lateral-torsional buckling moment, or ``None`` if the limit state does not apply.
        legs: For each leg with its toe in compression, the elastic section modulus to that toe and
            the leg classification (``ratio = b/t``).
    """
    Fy, E = _f(material.Fy, "ksi"), _f(material.E, "ksi")
    My_ = _f(My, "kip*in")
    states = [_state("yielding", "Eq. F10-1", 1.5 * My_)]
    if Mcr is not None:
        ltb_my = _f(ltb_My if ltb_My is not None else My, "kip*in")
        states.append(_state("lateral-torsional buckling", "Eq. F10-2, F10-3", _angle_ltb(ltb_my, _f(Mcr, "kip*in"))))
    for name, (Sc, leg) in (legs or {}).items():
        local = _leg_local_buckling(Fy, E, _f(Sc, "in**3"), leg.ratio, leg.limit_p, leg.limit_r)
        if local is not None:
            states.append(_state(f"leg local buckling ({name})", local[0], local[1]))
    return FlexureStrength(axis, tuple(states), _q(1.5 * My_, "kip*in").to("kip*ft"), None, None, Cb)
