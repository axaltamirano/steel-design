"""Default material per shape family (Steel Construction Manual, 16th Ed., Table 2-4 preferred grades)."""

from __future__ import annotations

from steel_design.materials.a36 import A36
from steel_design.materials.a53_gr_b import A53GrB
from steel_design.materials.a500_gr_c_rect import A500GrCRect
from steel_design.materials.a500_gr_c_round import A500GrCRound
from steel_design.materials.a572_gr50 import A572Gr50
from steel_design.materials.a992 import A992
from steel_design.materials.base import SteelMaterial

#: Default material per shape family. Built-up shapes are fabricated from plate, where A992
#: is not available, so they default to A572 Gr. 50. Replace entries to set office standards.
DEFAULT_MATERIALS: dict[str, type[SteelMaterial]] = {
    "W": A992,
    "M": A36,
    "S": A36,
    "HP": A572Gr50,
    "C": A36,
    "MC": A36,
    "L": A36,
    "2L": A36,
    "WT": A992,
    "MT": A36,
    "ST": A36,
    "HSS_RECT": A500GrCRect,
    "HSS_ROUND": A500GrCRound,
    "PIPE": A53GrB,
    "BUILT_UP_WF": A572Gr50,
    "BUILT_UP_BOX": A572Gr50,
}


def default_material_for(shape_family: str) -> type[SteelMaterial]:
    """Return the default material class for a shape family key.

    Args:
        shape_family: A key of :data:`DEFAULT_MATERIALS`, case-insensitive (e.g. ``"W"``,
            ``"HSS_RECT"``, ``"BUILT_UP_WF"``).

    Raises:
        KeyError: If the family has no default.
    """
    try:
        return DEFAULT_MATERIALS[shape_family.upper()]
    except KeyError:
        raise KeyError(
            f"No default material for shape family {shape_family!r}; known: {sorted(DEFAULT_MATERIALS)}"
        ) from None
