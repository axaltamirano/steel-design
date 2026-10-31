"""ASTM A500 Grade C, rectangular/square HSS: Fy = 50 ksi, Fu = 62 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A500GrCRect(SteelMaterial):
    """ASTM A500 Grade C, rectangular/square HSS.

    Minimum specified Fy = 50 ksi and Fu = 62 ksi.
    """

    name = "A500 Gr. C (rect)"
    astm = "ASTM A500 Grade C, rectangular/square HSS"
    Fy = Q_(50, "ksi")
    Fu = Q_(62, "ksi")
