"""ASTM A36: Fy = 36 ksi, Fu = 58 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A36(SteelMaterial):
    """ASTM A36.

    Minimum specified Fy = 36 ksi and Fu = 58 ksi.
    """

    name = "A36"
    astm = "ASTM A36"
    Fy = Q_(36, "ksi")
    Fu = Q_(58, "ksi")
