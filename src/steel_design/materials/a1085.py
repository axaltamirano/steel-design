"""ASTM A1085: Fy = 50 ksi, Fu = 65 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A1085(SteelMaterial):
    """ASTM A1085.

    Minimum specified Fy = 50 ksi and Fu = 65 ksi.
    """

    name = "A1085"
    astm = "ASTM A1085"
    Fy = Q_(50, "ksi")
    Fu = Q_(65, "ksi")
