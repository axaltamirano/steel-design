"""ASTM A500 Grade C, round HSS: Fy = 46 ksi, Fu = 62 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A500GrCRound(SteelMaterial):
    """ASTM A500 Grade C, round HSS.

    Minimum specified Fy = 46 ksi and Fu = 62 ksi.
    """

    name = "A500 Gr. C (round)"
    astm = "ASTM A500 Grade C, round HSS"
    Fy = Q_(46, "ksi")
    Fu = Q_(62, "ksi")
