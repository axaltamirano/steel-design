"""Bolt material grades, AISC 360-22 Tables J3.1 and J3.2.

Each grade is a class that holds single values, like the structural steel grades. Classes are
used directly and never instantiated.
"""

from __future__ import annotations

from typing import ClassVar

from steel_design.units import Q_


class BoltMaterial:
    """Constants of one bolt grade. Each subclass defines one grade.

    Attributes:
        name: Display name.
        astm: ASTM designation.
        Fnt: Nominal tensile stress (Table J3.2).
        Fnv_N: Nominal shear stress, threads not excluded from the shear planes (N).
        Fnv_X: Nominal shear stress, threads excluded from the shear planes (X). Equal to
            ``Fnv_N`` for A307, for which threads are assumed in the shear plane.
        Fu: Minimum specified tensile strength.
        pretension: Minimum pretension ``Tb`` in kips by nominal diameter in inches (Table J3.1);
            empty for grades that are not pretensioned.
    """

    name: ClassVar[str]
    astm: ClassVar[str]
    Fnt: ClassVar
    Fnv_N: ClassVar
    Fnv_X: ClassVar
    Fu: ClassVar
    pretension: ClassVar[dict[float, float]]

    def __init__(self) -> None:
        """Always raises ``TypeError``: bolt materials are used as classes."""
        raise TypeError(f"{type(self).__name__} is used as a class; do not instantiate it")

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Require every grade to define its strengths and pretension table."""
        super().__init_subclass__(**kwargs)
        for attr in ("name", "astm", "Fnt", "Fnv_N", "Fnv_X", "Fu", "pretension"):
            if not hasattr(cls, attr):
                raise TypeError(f"{cls.__name__} must define {attr!r}")

    @classmethod
    def Tb(cls, diameter: float):
        """Minimum pretension for a nominal diameter in inches.

        Raises:
            ValueError: If the grade is not pretensioned or the diameter is not tabulated.
        """
        if not cls.pretension:
            raise ValueError(f"{cls.name} bolts have no specified minimum pretension (Table J3.1)")
        for d, value in cls.pretension.items():
            if abs(d - diameter) < 1e-6:
                return Q_(value, "kip")
        raise ValueError(f"No Table J3.1 pretension for a {diameter:g} in. {cls.name} bolt")


class A307(BoltMaterial):
    """ASTM A307 bolts: Fnt = 45 ksi, Fnv = 27 ksi (threads assumed in the shear plane)."""

    name = "A307"
    astm = "ASTM A307"
    Fnt = Q_(45, "ksi")
    Fnv_N = Q_(27, "ksi")
    Fnv_X = Q_(27, "ksi")
    Fu = Q_(60, "ksi")
    pretension: ClassVar[dict[float, float]] = {}


class Group120(BoltMaterial):
    """Group 120 bolts, such as ASTM A325 and F1852: Fnt = 90 ksi, Fnv = 54 ksi (N) or 68 ksi (X)."""

    name = "Group 120 (A325)"
    astm = "ASTM F3125 Grade A325"
    Fnt = Q_(90, "ksi")
    Fnv_N = Q_(54, "ksi")
    Fnv_X = Q_(68, "ksi")
    Fu = Q_(120, "ksi")
    pretension: ClassVar[dict[float, float]] = {
        0.5: 12, 0.625: 19, 0.75: 28, 0.875: 39, 1.0: 51, 1.125: 64, 1.25: 81, 1.375: 97, 1.5: 118,
    }  # fmt: skip


class Group150(BoltMaterial):
    """Group 150 bolts, such as ASTM A490 and F2280: Fnt = 113 ksi, Fnv = 68 ksi (N) or 84 ksi (X)."""

    name = "Group 150 (A490)"
    astm = "ASTM F3125 Grade A490"
    Fnt = Q_(113, "ksi")
    Fnv_N = Q_(68, "ksi")
    Fnv_X = Q_(84, "ksi")
    Fu = Q_(150, "ksi")
    pretension: ClassVar[dict[float, float]] = {
        0.5: 15, 0.625: 24, 0.75: 35, 0.875: 49, 1.0: 64, 1.125: 80, 1.25: 102, 1.375: 121, 1.5: 148,
    }  # fmt: skip


#: Common aliases by ASTM designation.
A325 = Group120
A490 = Group150

__all__ = ["A307", "A325", "A490", "BoltMaterial", "Group120", "Group150"]
