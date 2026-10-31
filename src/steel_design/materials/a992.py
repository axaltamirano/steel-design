"""ASTM A992: Fy = 50 ksi, Fu = 65 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A992(SteelMaterial):
    """ASTM A992.

    Minimum specified Fy = 50 ksi and Fu = 65 ksi.
    """

    name = "A992"
    astm = "ASTM A992"
    Fy = Q_(50, "ksi")
    Fu = Q_(65, "ksi")
