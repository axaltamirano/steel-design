"""ASTM A572 Grade 55: Fy = 55 ksi, Fu = 70 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A572Gr55(SteelMaterial):
    """ASTM A572 Grade 55.

    Minimum specified Fy = 55 ksi and Fu = 70 ksi.
    """

    name = "A572 Gr. 55"
    astm = "ASTM A572 Grade 55"
    Fy = Q_(55, "ksi")
    Fu = Q_(70, "ksi")
