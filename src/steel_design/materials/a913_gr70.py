"""ASTM A913 Grade 70: Fy = 70 ksi, Fu = 90 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A913Gr70(SteelMaterial):
    """ASTM A913 Grade 70.

    Minimum specified Fy = 70 ksi and Fu = 90 ksi.
    """

    name = "A913 Gr. 70"
    astm = "ASTM A913 Grade 70"
    Fy = Q_(70, "ksi")
    Fu = Q_(90, "ksi")
