"""Common base for all cross sections (database and built-up)."""

from __future__ import annotations

from steel_design.materials.base import SteelMaterial


class Section:
    """A cross section with a material. Property names follow the AISC Shapes Database
    (`A`, `d`, `Ix`, `Zx`, `Sx`, `rx`, `Iy`, `J`, `Cw`, ...) and values are pint quantities.
    """

    name: str
    family: str
    material: type[SteelMaterial]
