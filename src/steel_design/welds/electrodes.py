"""Weld metal (filler metal) classifications, AISC 360-22 Table J2.5 and Manual Table 8-3.

Each electrode is a class that holds single values; classes are used directly and never
instantiated, like the steel grades and bolt grades.
"""

from __future__ import annotations

from typing import ClassVar

from steel_design.units import Q_


class Electrode:
    """Constants of one filler metal classification.

    Attributes:
        name: Classification, e.g. ``"E70XX"``.
        FEXX: Classification strength.

    :meth:`Fnw` gives the nominal weld metal stress and :meth:`C1` the electrode strength
    coefficient of Manual Table 8-3.
    """

    name: ClassVar[str]
    FEXX: ClassVar

    def __init__(self) -> None:
        """Always raises ``TypeError``: electrodes are used as classes."""
        raise TypeError(f"{type(self).__name__} is used as a class; do not instantiate it")

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Require every electrode to define its name and classification strength."""
        super().__init_subclass__(**kwargs)
        for attr in ("name", "FEXX"):
            if not hasattr(cls, attr):
                raise TypeError(f"{cls.__name__} must define {attr!r}")

    @classmethod
    def Fnw(cls):
        """Nominal weld metal stress, ``0.60 FEXX``."""
        return 0.60 * cls.FEXX

    @classmethod
    def C1(cls) -> float:
        """Electrode strength coefficient ``C1`` (1.00 for E70XX)."""
        return float(cls.FEXX.to("ksi").m) / 70.0


class E60XX(Electrode):
    """E60XX electrode."""

    name = "E60XX"
    FEXX = Q_(60.0, "ksi")


class E70XX(Electrode):
    """E70XX electrode."""

    name = "E70XX"
    FEXX = Q_(70.0, "ksi")


class E80XX(Electrode):
    """E80XX electrode."""

    name = "E80XX"
    FEXX = Q_(80.0, "ksi")


class E90XX(Electrode):
    """E90XX electrode."""

    name = "E90XX"
    FEXX = Q_(90.0, "ksi")


class E100XX(Electrode):
    """E100XX electrode."""

    name = "E100XX"
    FEXX = Q_(100.0, "ksi")


class E110XX(Electrode):
    """E110XX electrode."""

    name = "E110XX"
    FEXX = Q_(110.0, "ksi")


__all__ = ["E60XX", "E70XX", "E80XX", "E90XX", "E100XX", "E110XX", "Electrode"]
