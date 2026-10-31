"""ASTM A53 Grade B: Fy = 35 ksi, Fu = 60 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A53GrB(SteelMaterial):
    """ASTM A53 Grade B.

    Minimum specified Fy = 35 ksi and Fu = 60 ksi.
    """

    name = "A53 Gr. B"
    astm = "ASTM A53 Grade B"
    Fy = Q_(35, "ksi")
    Fu = Q_(60, "ksi")
