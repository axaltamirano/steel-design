"""A single bolt and its AISC 360-22 Section J3 strengths (LRFD)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

import pint

from steel_design.bolts.holes import HoleType, hole_dimensions
from steel_design.bolts.materials import BoltMaterial
from steel_design.resistance_factors import ResistanceFactors as phi_
from steel_design.units import Q_, require_length


class SlipClass(Enum):
    """Faying surface classes and mean slip coefficients ``mu`` (Section J3.9)."""

    A = 0.30
    B = 0.50


@dataclass(frozen=True)
class BoltStrength:
    """Nominal and design strength of one bolt for one limit state.

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


@dataclass(frozen=True)
class Ply:
    """A connected ply at a bolt for the bearing and tearout check (Section J3.11).

    Attributes:
        t: Ply thickness.
        Fu: Minimum tensile strength of the ply.
        Lc: Clear distance, in the direction of the force, from the edge of the hole to the edge
            of the hole or the material.
    """

    t: pint.Quantity
    Fu: pint.Quantity
    Lc: pint.Quantity

    def __post_init__(self) -> None:
        object.__setattr__(self, "t", require_length(self.t, "t"))
        object.__setattr__(self, "Lc", require_length(self.Lc, "Lc"))
        if not isinstance(self.Fu, pint.Quantity):
            raise TypeError("Fu must be a pint Quantity with stress units")


class Bolt:
    """One bolt with its material, size and hole.

    The LRFD limit states are tension rupture (Eq. J3-1), shear rupture (Eq. J3-1), combined
    tension and shear (Eq. J3-2), slip resistance (Eq. J3-4) and bearing and tearout (J3.11).
    """

    def __init__(
        self,
        diameter,
        material: type[BoltMaterial],
        threads_excluded: bool = False,
        shear_planes: int = 1,
        hole: HoleType = HoleType.STANDARD,
    ):
        """Create a bolt.

        Args:
            diameter: Nominal diameter (length quantity).
            material: Bolt grade class, e.g. ``A325`` or ``Group150``.
            threads_excluded: True when threads are excluded from the shear planes (X);
                otherwise threads are assumed in the shear planes (N).
            shear_planes: Number of shear planes, 1 or more.
            hole: Hole type in the connected plies.

        Raises:
            TypeError: If ``diameter`` is not a length quantity.
            ValueError: For a non-positive diameter or fewer than one shear plane.
        """
        self.diameter = require_length(diameter, "diameter")
        if self.diameter.m <= 0:
            raise ValueError("diameter must be positive")
        if shear_planes < 1:
            raise ValueError("shear_planes must be at least 1")
        self.material = material
        self.threads_excluded = threads_excluded
        self.shear_planes = int(shear_planes)
        self.hole = hole

    @property
    def Ab(self) -> pint.Quantity:
        """Nominal unthreaded body area, ``pi d^2 / 4``."""
        return (math.pi * self.diameter**2 / 4).to("in**2")

    @property
    def Fnv(self) -> pint.Quantity:
        """Nominal shear stress for the selected thread condition (Table J3.2)."""
        return self.material.Fnv_X if self.threads_excluded else self.material.Fnv_N

    @property
    def Tb(self) -> pint.Quantity:
        """Minimum pretension (Table J3.1)."""
        return self.material.Tb(self.diameter.m)

    @property
    def hole_dimensions(self):
        """``(width, length)`` of the hole (Table J3.3)."""
        return hole_dimensions(self.diameter, self.hole)

    def tension_strength(self) -> BoltStrength:
        """Tension rupture, ``Rn = Fnt Ab`` (Eq. J3-1), phi = 0.75."""
        return BoltStrength("tension rupture", (self.material.Fnt * self.Ab).to("kip"), phi_.BOLT_RUPTURE, "Eq. J3-1")

    def shear_strength(self, pattern_length=None, grip_length=None) -> BoltStrength:
        """Shear rupture, ``Rn = Fnv Ab ns`` (Eq. J3-1), phi = 0.75.

        Args:
            pattern_length: Fastener pattern length parallel to the load. Above 38 in., ``Fnv``
                is reduced to 83.3% (Table J3.2 note c).
            grip_length: Grip length of an A307 bolt. ``Fnv`` is reduced 1% for each 1/16 in. over
                five diameters (Table J3.2 note d).
        """
        factor = 1.0
        if pattern_length is not None and require_length(pattern_length, "pattern_length").m > 38:
            factor *= 0.833
        if grip_length is not None and self.material.name == "A307":
            excess = require_length(grip_length, "grip_length").m - 5 * self.diameter.m
            if excess > 0:
                factor *= max(0.0, 1 - 0.01 * math.ceil(excess * 16 - 1e-9))
        rn = factor * self.Fnv * self.Ab * self.shear_planes
        return BoltStrength("shear rupture", rn.to("kip"), phi_.BOLT_RUPTURE, "Eq. J3-1")

    def tension_with_shear(self, Vu) -> BoltStrength:
        """Tensile strength reduced by the required shear ``Vu`` on the bolt (Eqs. J3-2, J3-3a).

        ``frv`` is ``Vu / (Ab ns)``. ``F'nt = 1.3 Fnt - Fnt frv / (phi Fnv) <= Fnt``.

        Raises:
            ValueError: If ``frv`` exceeds the design shear stress ``phi Fnv``.
        """
        frv = (Q_(Vu.to("kip").m, "kip") / (self.Ab * self.shear_planes)).to("ksi")
        fnv = self.Fnv
        if frv > phi_.BOLT_RUPTURE * fnv:
            raise ValueError("The required shear stress exceeds the available shear stress of the bolt")
        fnt = self.material.Fnt
        fnt_mod = min(fnt, 1.3 * fnt - fnt / (phi_.BOLT_COMBINED * fnv) * frv)
        rn = max(fnt_mod, Q_(0, "ksi")) * self.Ab
        return BoltStrength("tension with shear", rn.to("kip"), phi_.BOLT_COMBINED, "Eqs. J3-2, J3-3a")

    def slip_resistance(
        self,
        surface: SlipClass | float = SlipClass.A,
        Du: float = 1.13,
        fillers: int = 0,
        slip_planes: int | None = None,
        Tu=None,
        n_tension_bolts: int = 1,
    ) -> BoltStrength:
        """Slip resistance of a pretensioned bolt, ``Rn = mu Du hf Tb ns ksc`` (Eqs. J3-4, J3-5a).

        Args:
            surface: :class:`SlipClass` or an explicit mean slip coefficient.
            Du: Pretension multiplier; 1.13 unless otherwise approved.
            fillers: Number of fillers between the connected parts; ``hf`` is 0.85 for two or more.
            slip_planes: ``ns``; defaults to the bolt's ``shear_planes``.
            Tu: Required tension on the connection that reduces clamping force (kip), if any.
            n_tension_bolts: ``nb``, the number of bolts carrying ``Tu``.

        Raises:
            ValueError: If the bolt grade has no specified pretension.
        """
        mu = surface.value if isinstance(surface, SlipClass) else float(surface)
        hf = 0.85 if fillers >= 2 else 1.0
        ns = self.shear_planes if slip_planes is None else slip_planes
        ksc = 1.0
        if Tu is not None:
            ksc = max(0.0, 1 - float(Tu.to("kip").m) / (Du * self.Tb.m * n_tension_bolts))
        if self.hole is HoleType.STANDARD:
            phi = phi_.SLIP_STANDARD
        elif self.hole is HoleType.LONG_SLOT:
            phi = phi_.SLIP_LONG_SLOT
        else:
            phi = phi_.SLIP_OVERSIZED
        rn = mu * Du * hf * self.Tb * ns * ksc
        return BoltStrength("slip resistance", rn.to("kip"), phi, "Eq. J3-4")

    def bearing_tearout_strength(
        self,
        ply: Ply,
        deformation_considered: bool = True,
        long_slot_perpendicular: bool = False,
    ) -> BoltStrength:
        """Bearing and tearout at one ply, the lesser of Eqs. J3-6a/b and J3-6c/d, phi = 0.75.

        Args:
            ply: Connected ply thickness, ``Fu`` and clear distance ``Lc``.
            deformation_considered: True when hole deformation at service load is a design
                consideration (coefficients 2.4 and 1.2); false uses 3.0 and 1.5.
            long_slot_perpendicular: True for a long slot perpendicular to the force (Eqs. J3-6e/f).
        """
        d, t, fu, lc = self.diameter, ply.t, ply.Fu, ply.Lc
        if lc.m < 0:
            raise ValueError("Lc must not be negative")
        if long_slot_perpendicular:
            bearing, tearout, ref = 2.0 * d * t * fu, 1.0 * lc * t * fu, "Eqs. J3-6e, J3-6f"
        elif deformation_considered:
            bearing, tearout, ref = 2.4 * d * t * fu, 1.2 * lc * t * fu, "Eqs. J3-6a, J3-6c"
        else:
            bearing, tearout, ref = 3.0 * d * t * fu, 1.5 * lc * t * fu, "Eqs. J3-6b, J3-6d"
        bearing, tearout = bearing.to("kip"), tearout.to("kip")
        name = "bearing" if bearing <= tearout else "tearout"
        return BoltStrength(name, min(bearing, tearout), phi_.BEARING_TEAROUT, ref)

    def effective_strength(
        self,
        plies: Ply | Iterable[Ply] | None = None,
        deformation_considered: bool = True,
        pattern_length=None,
        grip_length=None,
        long_slot_perpendicular: bool = False,
    ) -> BoltStrength:
        """Lesser of shear rupture and bearing/tearout at every ply (Section J3.7 User Note).

        With no ``plies`` this is the shear strength alone.
        """
        candidates = [self.shear_strength(pattern_length, grip_length)]
        if plies is not None:
            plies = (plies,) if isinstance(plies, Ply) else tuple(plies)
            candidates += [
                self.bearing_tearout_strength(p, deformation_considered, long_slot_perpendicular) for p in plies
            ]
        return min(candidates, key=lambda r: r.design_strength.m)

    def get_Rnt(self):
        """Nominal tensile strength."""
        return self.tension_strength().Rn

    def get_phiRnt(self):
        """Design tensile strength."""
        return self.tension_strength().design_strength

    def get_Rnv(self):
        """Nominal shear strength."""
        return self.shear_strength().Rn

    def get_phiRnv(self):
        """Design shear strength."""
        return self.shear_strength().design_strength

    def __repr__(self) -> str:
        return f"<Bolt {self.diameter.m:g} in. {self.material.name} ({'X' if self.threads_excluded else 'N'}, {self.shear_planes} plane)>"


__all__ = ["Bolt", "BoltStrength", "Ply", "SlipClass"]
