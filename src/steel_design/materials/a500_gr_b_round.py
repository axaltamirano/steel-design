"""ASTM A500 Grade B, round HSS: Fy = 42 ksi, Fu = 58 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A500GrBRound(SteelMaterial):
    """ASTM A500 Grade B, round HSS.

    Minimum specified Fy = 42 ksi and Fu = 58 ksi.
    """

    name = "A500 Gr. B (round)"
    astm = "ASTM A500 Grade B, round HSS"
    Fy = Q_(42, "ksi")
    Fu = Q_(58, "ksi")
