"""ASTM A913 Grade 60: Fy = 60 ksi, Fu = 75 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A913Gr60(SteelMaterial):
    """ASTM A913 Grade 60.

    Minimum specified Fy = 60 ksi and Fu = 75 ksi.
    """

    name = "A913 Gr. 60"
    astm = "ASTM A913 Grade 60"
    Fy = Q_(60, "ksi")
    Fu = Q_(75, "ksi")
