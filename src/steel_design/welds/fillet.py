"""Single fillet weld strength and limitations, AISC 360-22 Section J2."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pint

from steel_design.resistance_factors import ResistanceFactors as phi_
from steel_design.units import Q_, require_length
from steel_design.welds.electrodes import E70XX, Electrode

#: Effective throat of an equal-leg fillet weld per unit leg size, ``1/sqrt(2)``.
THROAT_FACTOR = 0.707


@dataclass(frozen=True)
class WeldStrength:
    """Nominal and design strength of a weld for one limit state.

    Attributes:
        name: Limit state.
        Rn: Nominal strength (kip).
        phi: LRFD resistance factor.
        reference: Specification equation or section.
    """

    name: str
    Rn: pint.Quantity
    phi: float
    reference: str

    @property
    def design_strength(self) -> pint.Quantity:
        """``phi * Rn``."""
        return self.phi * self.Rn


def directional_factor(angle: float) -> float:
    """Directional strength increase ``kds = 1.0 + 0.50 sin^1.5(theta)`` (Eq. J2-5).

    Args:
        angle: Angle between the line of action of the force and the weld axis, degrees.
    """
    return 1.0 + 0.5 * math.sin(math.radians(angle)) ** 1.5


def min_fillet_size(thickness) -> pint.Quantity:
    """Minimum fillet weld leg size for the thinner part joined (Table J2.4)."""
    t = require_length(thickness, "thickness").m
    if t <= 0.25:
        return Q_(0.125, "in")
    if t <= 0.5:
        return Q_(0.1875, "in")
    if t <= 0.75:
        return Q_(0.25, "in")
    return Q_(0.3125, "in")


def max_fillet_size(thickness) -> pint.Quantity:
    """Maximum fillet weld leg size along the edge of a part (Section J2.2b(b))."""
    t = require_length(thickness, "thickness")
    return t if t.m < 0.25 else t - Q_(1 / 16, "in")


class FilletWeld:
    """A straight fillet weld of uniform leg size.

    Args:
        size: Leg size ``w``.
        length: Actual weld length.
        electrode: Electrode class; E70XX by default.
        angle: Angle between the force and the weld axis, degrees (0 = longitudinal, 90 =
            transverse).
        directional: Apply the directional strength increase of Eq. J2-5. Permitted only when
            strain compatibility is considered, for example a linear weld group loaded through its
            center of gravity; use ``False`` (the default) for the conservative ``kds = 1.0``.
    """

    def __init__(self, size, length, electrode: type[Electrode] = E70XX, angle: float = 0.0, directional: bool = False):
        self.size = require_length(size, "size")
        self.length = require_length(length, "length")
        if self.size.m <= 0 or self.length.m <= 0:
            raise ValueError("size and length must be positive")
        self.electrode = electrode
        self.angle = float(angle)
        self.directional = directional

    @property
    def throat(self) -> pint.Quantity:
        """Effective throat, ``0.707 w`` (Section J2.2a)."""
        return THROAT_FACTOR * self.size

    @property
    def effective_length(self) -> pint.Quantity:
        """Effective length of an end-loaded weld (Section J2.2b(d)); the actual length otherwise.

        Applied only to longitudinally loaded welds (``angle == 0``).
        """
        if self.angle != 0.0:
            return self.length
        ratio = float((self.length / self.size).to("dimensionless").m)
        if ratio <= 100:
            return self.length
        if ratio > 300:
            return 180 * self.size
        return (1.2 - 0.002 * ratio) * self.length

    @property
    def Awe(self) -> pint.Quantity:
        """Effective area, effective throat times effective length."""
        return (self.throat * self.effective_length).to("in**2")

    def strength(self) -> WeldStrength:
        """Weld metal rupture, ``Rn = Fnw Awe kds`` (Eq. J2-4), phi = 0.75."""
        kds = directional_factor(self.angle) if self.directional else 1.0
        rn = (self.electrode.Fnw() * self.Awe * kds).to("kip")
        return WeldStrength("weld metal rupture", rn, phi_.FILLET_WELD, "Eq. J2-4")

    def design_strength(self) -> pint.Quantity:
        """``phi Rn`` of the weld."""
        return self.strength().design_strength

    def minimum_length(self) -> pint.Quantity:
        """Minimum length of a weld designed on strength, four times the size (Section J2.2b(c))."""
        return 4 * self.size

    def __repr__(self) -> str:
        return f"<FilletWeld {self.size.m:g} in. x {self.length.m:g} in. {self.electrode.name}>"


__all__ = [
    "FilletWeld",
    "THROAT_FACTOR",
    "WeldStrength",
    "directional_factor",
    "max_fillet_size",
    "min_fillet_size",
]
