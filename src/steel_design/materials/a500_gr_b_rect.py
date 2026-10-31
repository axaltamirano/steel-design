"""ASTM A500 Grade B, rectangular/square HSS: Fy = 46 ksi, Fu = 58 ksi."""

from steel_design.materials.base import SteelMaterial
from steel_design.units import Q_


class A500GrBRect(SteelMaterial):
    """ASTM A500 Grade B, rectangular/square HSS.

    Minimum specified Fy = 46 ksi and Fu = 58 ksi.
    """

    name = "A500 Gr. B (rect)"
    astm = "ASTM A500 Grade B, rectangular/square HSS"
    Fy = Q_(46, "ksi")
    Fu = Q_(58, "ksi")
