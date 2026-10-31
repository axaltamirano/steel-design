"""Design of members for shear, AISC 360-22 Chapter G.

Each function below implements one family of sections from Chapter G and returns a
:class:`ShearStrength`. The section classes choose the function and supply their geometry.

======================================  ==========================================================
Function                                Sections
======================================  ==========================================================
:func:`i_shape_web_shear`               Webs of I-shapes and channels (G2.1, G2.2)
:func:`plate_shear`                     Tee stems and angle legs (G3), HSS and box walls and
                                        other webs (G4), flanges in minor-axis shear (G6)
:func:`round_hss_shear`                 Round HSS and pipe (G5)
======================================  ==========================================================

The ``axis`` of a result is the axis of bending that the shear accompanies: ``"x"`` is shear
parallel to the web (strong axis), ``"y"`` is shear parallel to the flanges (minor axis).

Not included: end web panels with tension field action (G2.3), the design of transverse
stiffeners (G2.4), and beams with web openings (G7).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pint

from steel_design.materials.base import SteelMaterial
from steel_design.resistance_factors import ResistanceFactors
from steel_design.units import Q_

#: Web plate shear buckling coefficient for webs without transverse stiffeners (Eq. G2-5).
KV_UNSTIFFENED = 5.34
#: Shear buckling coefficient for tee stems, angle legs and flanges (G3, G6).
KV_LEG = 1.2
#: Shear buckling coefficient for the walls of HSS and box sections and other webs (G4).
KV_BOX = 5.0
#: Largest h/tw of a rolled I-shape web for which phi_v = 1.00 and Cv1 = 1.0 (G2.1(a)).
ROLLED_WEB_LIMIT = 2.24
#: Largest a/h for which tension field action may be used (G2.2) and kv exceeds 5.34 (G2-5).
MAX_PANEL_ASPECT = 3.0
#: Largest ``2 Aw / (Afc + Aft)`` for Eq. G2-7 (G2.2(b)(1)).
MAX_AREA_RATIO = 2.5
#: Largest ``h / bf`` for Eq. G2-7 (G2.2(b)(1)).
MAX_FLANGE_SLENDERNESS = 6.0


@dataclass(frozen=True)
class ShearStrength:
    """Shear strength of a member for one direction of shear.

    Attributes:
        axis: Axis of bending that the shear accompanies (``"x"`` or ``"y"``).
        name: Limit state, e.g. ``"shear yielding"``, ``"shear buckling"`` or
            ``"tension field action"``.
        reference: Equations used.
        Vn: Nominal shear strength in kips.
        phi: Resistance factor, from :class:`~steel_design.resistance_factors.ResistanceFactors`.
        Cv: Web (or element) shear coefficient, ``Cv1`` or ``Cv2``, when defined.
        kv: Shear buckling coefficient, when defined.
    """

    axis: str
    name: str
    reference: str
    Vn: pint.Quantity
    phi: float = ResistanceFactors.SHEAR
    Cv: float | None = None
    kv: float | None = None

    @property
    def design_strength(self) -> pint.Quantity:
        """Design strength, ``phi_v Vn``, in kips."""
        return (self.phi * self.Vn).to("kip")


# --- helpers --------------------------------------------------------------------------


def _inches(value: pint.Quantity, name: str) -> float:
    """A positive length in inches."""
    v = float(value.to("inch").magnitude)
    if v <= 0:
        raise ValueError(f"{name} must be positive")
    return v


def _fy_e(material: type[SteelMaterial]) -> tuple[float, float]:
    return float(material.Fy.to("ksi").magnitude), float(material.E.to("ksi").magnitude)


def kv_stiffened(a_over_h: float | None) -> float:
    """Web plate shear buckling coefficient of an I-shape or channel web (Eq. G2-5).

    ``kv = 5.34 + 4/(a/h)^2``, and 5.34 for a web without transverse stiffeners or ``a/h > 3``.
    """
    if a_over_h is None or a_over_h > MAX_PANEL_ASPECT:
        return KV_UNSTIFFENED
    if a_over_h <= 0:
        raise ValueError("Stiffener spacing a must be positive")
    return KV_UNSTIFFENED + 4.0 / a_over_h**2


def cv1(material: type[SteelMaterial], h_tw: float, kv: float) -> float:
    """Web shear strength coefficient ``Cv1`` (Eqs. G2-3 and G2-4)."""
    Fy, E = _fy_e(material)
    limit = 1.10 * math.sqrt(kv * E / Fy)
    return 1.0 if h_tw <= limit else limit / h_tw


def cv2(material: type[SteelMaterial], h_tw: float, kv: float) -> float:
    """Web shear buckling strength coefficient ``Cv2`` (Eqs. G2-9 to G2-11)."""
    Fy, E = _fy_e(material)
    root = math.sqrt(kv * E / Fy)
    if h_tw <= 1.10 * root:
        return 1.0
    if h_tw <= 1.37 * root:
        return 1.10 * root / h_tw
    return 1.51 * kv * E / (h_tw**2 * Fy)


# --- G2: I-shaped members and channels ------------------------------------------------


def i_shape_web_shear(
    material: type[SteelMaterial],
    axis: str,
    *,
    d: pint.Quantity,
    tw: pint.Quantity,
    h: pint.Quantity,
    rolled_i_shape: bool = False,
    a: pint.Quantity | None = None,
    flanges: tuple[tuple[pint.Quantity, pint.Quantity], ...] | None = None,
) -> ShearStrength:
    """Shear strength of the web of an I-shape or channel (Section G2).

    ``Vn = 0.6 Fy Aw Cv1`` (Eq. G2-1) with ``Aw = d tw``. A rolled I-shape with
    ``h/tw <= 2.24 sqrt(E/Fy)`` has ``Cv1 = 1.0`` and ``phi_v = 1.00`` (G2.1(a)); every other
    web uses G2.1(b) with ``phi_v = 0.90``. When the stiffener spacing ``a`` is given, ``kv``
    follows Eq. G2-5 and, if ``a/h <= 3``, tension field action (G2.2) is used when it gives a
    larger strength.

    Args:
        material: Material class.
        axis: Axis of bending the shear accompanies.
        d: Overall depth.
        tw: Web thickness.
        h: Clear distance between flanges (less the fillets of a rolled shape; the distance
            between fastener lines for a bolted built-up shape).
        rolled_i_shape: ``True`` for rolled W, M, S and HP shapes (not channels).
        a: Clear distance between transverse stiffeners, or ``None`` if unstiffened.
        flanges: ``((bf, tf), (bf, tf))`` of the two flanges. Required for tension field action.

    Raises:
        ValueError: For non-positive dimensions.
    """
    Fy, E = _fy_e(material)
    d_in, tw_in, h_in = _inches(d, "d"), _inches(tw, "tw"), _inches(h, "h")
    Aw = d_in * tw_in
    h_tw = h_in / tw_in
    if rolled_i_shape and h_tw <= ROLLED_WEB_LIMIT * math.sqrt(E / Fy):
        return ShearStrength(
            axis, "shear yielding", "Eq. G2-1, G2.1(a)", Q_(0.6 * Fy * Aw, "kip"),
            phi=ResistanceFactors.SHEAR_ROLLED_I, Cv=1.0, kv=KV_UNSTIFFENED,
        )
    a_h = None if a is None else _inches(a, "a") / h_in
    kv = kv_stiffened(a_h)
    c1 = cv1(material, h_tw, kv)
    best = ShearStrength(
        axis, "shear yielding" if c1 == 1.0 else "shear buckling", "Eq. G2-1, G2.1(b)",
        Q_(0.6 * Fy * Aw * c1, "kip"), Cv=c1, kv=kv,
    )
    if a_h is None or a_h > MAX_PANEL_ASPECT or flanges is None:
        return best
    if h_tw <= 1.10 * math.sqrt(kv * E / Fy):
        return best  # G2-6 equals G2-1 with Cv1 = 1.0
    (bf1, tf1), (bf2, tf2) = ((_inches(b, "bf"), _inches(t, "tf")) for b, t in flanges)
    c2 = cv2(material, h_tw, kv)
    if 2 * Aw / (bf1 * tf1 + bf2 * tf2) <= MAX_AREA_RATIO and h_in / bf1 <= MAX_FLANGE_SLENDERNESS and h_in / bf2 <= MAX_FLANGE_SLENDERNESS:
        post = (1 - c2) / (1.15 * math.sqrt(1 + a_h**2))
        eq = "Eq. G2-7"
    else:
        post = (1 - c2) / (1.15 * (a_h + math.sqrt(1 + a_h**2)))
        eq = "Eq. G2-8"
    tfa = 0.6 * Fy * Aw * (c2 + post)
    if tfa > best.Vn.magnitude:
        return ShearStrength(axis, "tension field action", f"{eq}, G2.2", Q_(tfa, "kip"), Cv=c2, kv=kv)
    return best


# --- G3, G4, G6: plate-like shear resisting elements ----------------------------------


def plate_shear(
    material: type[SteelMaterial],
    axis: str,
    *,
    length: pint.Quantity,
    thickness: pint.Quantity,
    kv: float,
    count: int = 1,
    reference: str,
    slenderness: float | None = None,
) -> ShearStrength:
    """Shear strength of one or more identical shear resisting elements.

    ``Vn = count 0.6 Fy b t Cv2`` (Eqs. G3-1, G4-1 and G6-1), ``phi_v = 0.90``.

    Args:
        material: Material class.
        axis: Axis of bending the shear accompanies.
        length: Width ``b`` (or clear height ``h``) of the element resisting the shear.
        thickness: Thickness ``t``.
        kv: Shear buckling coefficient: 1.2 (G3, G6), 5 (G4).
        count: Number of identical elements (two webs of an HSS, two flanges, two angles).
        reference: Equations used.
        slenderness: ``h/tw`` for ``Cv2`` when it is not ``length / thickness``, as for a
            flange pair taken as ``bf / (2 tf)`` in Section G6.
    """
    Fy, _ = _fy_e(material)
    b, t = _inches(length, "length"), _inches(thickness, "thickness")
    ratio = b / t if slenderness is None else slenderness
    c2 = cv2(material, ratio, kv)
    Vn = count * 0.6 * Fy * b * t * c2
    name = "shear yielding" if c2 == 1.0 else "shear buckling"
    return ShearStrength(axis, name, reference, Q_(Vn, "kip"), Cv=c2, kv=kv)


# --- G5: round HSS --------------------------------------------------------------------


def round_hss_shear(
    material: type[SteelMaterial],
    axis: str,
    *,
    D: pint.Quantity,
    t: pint.Quantity,
    Ag: pint.Quantity,
    Lv: pint.Quantity | None = None,
) -> ShearStrength:
    """Shear strength of a round HSS or pipe (Section G5): ``Vn = Fcr Ag / 2`` (Eq. G5-1).

    ``Fcr`` is the larger of Eqs. G5-2a and G5-2b, at most ``0.6 Fy``. Without ``Lv`` only
    Eq. G5-2b is evaluated, which is conservative because G5-2a only raises ``Fcr``.

    Args:
        material: Material class.
        axis: Axis of bending the shear accompanies.
        D: Outside diameter.
        t: Design wall thickness.
        Ag: Gross area.
        Lv: Distance from maximum to zero shear force, when known.
    """
    Fy, E = _fy_e(material)
    D_in, t_in = _inches(D, "D"), _inches(t, "t")
    Fcr = 0.78 * E / (D_in / t_in) ** 1.5
    if Lv is not None:
        Fcr = max(Fcr, 1.60 * E / (math.sqrt(_inches(Lv, "Lv") / D_in) * (D_in / t_in) ** 1.25))
    yielding = 0.6 * Fy
    Fcr = min(Fcr, yielding)
    name = "shear yielding" if Fcr == yielding else "shear buckling"
    return ShearStrength(axis, name, "Eq. G5-1, G5-2", Q_(Fcr * float(Ag.to("inch**2").magnitude) / 2, "kip"))
