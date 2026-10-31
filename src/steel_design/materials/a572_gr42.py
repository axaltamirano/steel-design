"""ASTM A572 Grade 42: Fy = 42 ksi, Fu = 60 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A572Gr42(SteelMaterial):
    """ASTM A572 Grade 42.

    Minimum specified Fy = 42 ksi and Fu = 60 ksi.
    """

    name = "A572 Gr. 42"
    astm = "ASTM A572 Grade 42"
    Fy = Q_(42, "ksi")
    Fu = Q_(60, "ksi")
