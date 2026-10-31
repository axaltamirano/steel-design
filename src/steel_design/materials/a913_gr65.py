"""ASTM A913 Grade 65: Fy = 65 ksi, Fu = 80 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A913Gr65(SteelMaterial):
    """ASTM A913 Grade 65.

    Minimum specified Fy = 65 ksi and Fu = 80 ksi.
    """

    name = "A913 Gr. 65"
    astm = "ASTM A913 Grade 65"
    Fy = Q_(65, "ksi")
    Fu = Q_(80, "ksi")
