"""Tension members, AISC 360-22 Chapter D (Sections D1 to D3).

Covers the slenderness recommendation (D1), tensile yielding in the gross section and tensile
rupture in the net section (D2), and the effective net area (D3). The shear lag factor ``U``
of Table D3.1 is always supplied by the user. Pin-connected members, eyebars (D5, D6) and
block shear rupture (J4.3) are not included.
"""

from __future__ import annotations

from dataclasses import dataclass

import pint

from steel_design.resistance_factors import ResistanceFactors
from steel_design.units import require_length

#: Recommended maximum slenderness ratio for members designed on the basis of tension (D1 User Note).
MAX_RECOMMENDED_SLENDERNESS = 300


@dataclass(frozen=True)
class TensionLimitState:
    """Strength of a tension member for one limit state.

    Attributes:
        name: Limit state name.
        Pn: Nominal tensile strength.
        phi: Resistance factor, from :class:`~steel_design.resistance_factors.ResistanceFactors`.
        reference: Specification equation.
    """

    name: str
    Pn: pint.Quantity
    phi: float
    reference: str

    @property
    def design_strength(self) -> pint.Quantity:
        """Design strength, ``phi * Pn``, in kips."""
        return (self.phi * self.Pn).to("kip")


@dataclass(frozen=True)
class TensionStrength:
    """Tensile strength of a member: the lower of yielding and rupture (Section D2).

    Attributes:
        Ag: Gross area.
        An: Net area.
        U: Shear lag factor.
        Ae: Effective net area, ``An * U``.
        yielding: Tensile yielding in the gross section.
        rupture: Tensile rupture in the net section.
    """

    Ag: pint.Quantity
    An: pint.Quantity
    U: float
    Ae: pint.Quantity
    yielding: TensionLimitState
    rupture: TensionLimitState

    @property
    def limit_states(self) -> tuple[TensionLimitState, TensionLimitState]:
        """Both limit states."""
        return (self.yielding, self.rupture)

    @property
    def design_strength(self) -> pint.Quantity:
        """Governing design strength, ``phi_t * Pn``, in kips."""
        return min(ls.design_strength for ls in self.limit_states)

    @property
    def governing(self) -> TensionLimitState:
        """The limit state with the lower design strength."""
        return min(self.limit_states, key=lambda ls: ls.design_strength)


def _area(value: object, name: str) -> pint.Quantity:
    """Return ``value`` as an area in in^2, rejecting bare numbers and non-area quantities."""
    if not isinstance(value, pint.Quantity):
        raise TypeError(f"{name} must be a pint Quantity with area units, e.g. Q_(10, 'in**2'); got {value!r}")
    if not value.check("[length] ** 2"):
        raise ValueError(f"{name} must have area dimensions; got {value.units}")
    return value.to("in**2")


def effective_net_area(An: pint.Quantity, U: float = 1.0) -> pint.Quantity:
    """Effective net area, ``Ae = An * U`` (Eq. D3-1).

    Args:
        An: Net area per Section B4.3.
        U: Shear lag factor from Table D3.1, ``0 < U <= 1``.

    Raises:
        ValueError: If ``U`` is outside ``(0, 1]``.
    """
    if not 0 < U <= 1:
        raise ValueError(f"U must satisfy 0 < U <= 1; got {U}")
    return _area(An, "An") * U


def tensile_yielding(Ag: pint.Quantity, Fy: pint.Quantity) -> TensionLimitState:
    """Tensile yielding in the gross section, ``Pn = Fy * Ag`` (Eq. D2-1)."""
    return TensionLimitState(
        "tensile yielding", (Fy * _area(Ag, "Ag")).to("kip"), ResistanceFactors.TENSION_YIELDING, "Eq. D2-1"
    )


def tensile_rupture(Ae: pint.Quantity, Fu: pint.Quantity) -> TensionLimitState:
    """Tensile rupture in the net section, ``Pn = Fu * Ae`` (Eq. D2-2)."""
    return TensionLimitState(
        "tensile rupture", (Fu * _area(Ae, "Ae")).to("kip"), ResistanceFactors.TENSION_RUPTURE, "Eq. D2-2"
    )


def tension_strength(
    Ag: pint.Quantity,
    Fy: pint.Quantity,
    Fu: pint.Quantity,
    An: pint.Quantity | None = None,
    U: float = 1.0,
) -> TensionStrength:
    """Tensile strength from areas and material strengths (Sections D2 and D3).

    Args:
        Ag: Gross area.
        Fy: Specified minimum yield stress.
        Fu: Specified minimum tensile strength.
        An: Net area; defaults to ``Ag`` (no holes).
        U: Shear lag factor from Table D3.1; defaults to 1.0.

    Raises:
        TypeError: If an area is not a pint quantity.
        ValueError: If ``An`` exceeds ``Ag`` or ``U`` is outside ``(0, 1]``.
    """
    Ag = _area(Ag, "Ag")
    An = Ag if An is None else _area(An, "An")
    if An > Ag:
        raise ValueError("An cannot exceed Ag")
    Ae = effective_net_area(An, U)
    return TensionStrength(Ag, An, U, Ae, tensile_yielding(Ag, Fy), tensile_rupture(Ae, Fu))


def slenderness_ratio(length: pint.Quantity, r: pint.Quantity) -> float:
    """Slenderness ratio ``L / r`` (dimensionless)."""
    return float(require_length(length, "length") / require_length(r, "r"))


def exceeds_recommended_slenderness(length: pint.Quantity, r: pint.Quantity) -> bool:
    """True if ``L / r`` exceeds the D1 recommended maximum of 300."""
    return slenderness_ratio(length, r) > MAX_RECOMMENDED_SLENDERNESS


__all__ = [
    "MAX_RECOMMENDED_SLENDERNESS",
    "TensionLimitState",
    "TensionStrength",
    "effective_net_area",
    "exceeds_recommended_slenderness",
    "slenderness_ratio",
    "tensile_rupture",
    "tensile_yielding",
    "tension_strength",
]
