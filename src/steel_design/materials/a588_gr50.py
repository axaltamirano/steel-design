"""ASTM A588 Grade 50: Fy = 50 ksi, Fu = 70 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A588Gr50(SteelMaterial):
    """ASTM A588 Grade 50.

    Minimum specified Fy = 50 ksi and Fu = 70 ksi.
    """

    name = "A588 Gr. 50"
    astm = "ASTM A588 Grade 50"
    Fy = Q_(50, "ksi")
    Fu = Q_(70, "ksi")
