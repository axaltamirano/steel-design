"""ASTM A913 Grade 50: Fy = 50 ksi, Fu = 65 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A913Gr50(SteelMaterial):
    """ASTM A913 Grade 50.

    Minimum specified Fy = 50 ksi and Fu = 65 ksi.
    """

    name = "A913 Gr. 50"
    astm = "ASTM A913 Grade 50"
    Fy = Q_(50, "ksi")
    Fu = Q_(65, "ksi")
