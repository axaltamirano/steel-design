"""ASTM A572 Grade 65: Fy = 65 ksi, Fu = 80 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A572Gr65(SteelMaterial):
    """ASTM A572 Grade 65.

    Minimum specified Fy = 65 ksi and Fu = 80 ksi.
    """

    name = "A572 Gr. 65"
    astm = "ASTM A572 Grade 65"
    Fy = Q_(65, "ksi")
    Fu = Q_(80, "ksi")
