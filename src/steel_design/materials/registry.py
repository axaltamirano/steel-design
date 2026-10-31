"""Lookup of materials by name."""

from __future__ import annotations

import re

from steel_design.materials.a36 import A36
from steel_design.materials.a53_gr_b import A53GrB
from steel_design.materials.a500_gr_b_rect import A500GrBRect
from steel_design.materials.a500_gr_b_round import A500GrBRound
from steel_design.materials.a500_gr_c_rect import A500GrCRect
from steel_design.materials.a500_gr_c_round import A500GrCRound
from steel_design.materials.a529_gr50 import A529Gr50
from steel_design.materials.a529_gr55 import A529Gr55
from steel_design.materials.a572_gr42 import A572Gr42
from steel_design.materials.a572_gr50 import A572Gr50
from steel_design.materials.a572_gr55 import A572Gr55
from steel_design.materials.a572_gr60 import A572Gr60
from steel_design.materials.a572_gr65 import A572Gr65
from steel_design.materials.a588_gr50 import A588Gr50
from steel_design.materials.a913_gr50 import A913Gr50
from steel_design.materials.a913_gr60 import A913Gr60
from steel_design.materials.a913_gr65 import A913Gr65
from steel_design.materials.a913_gr70 import A913Gr70
from steel_design.materials.a992 import A992
from steel_design.materials.a1085 import A1085
from steel_design.materials.base import SteelMaterial

#: Every defined grade, in display order.
ALL_MATERIALS: tuple[type[SteelMaterial], ...] = (
    A992, A36,
    A572Gr42, A572Gr50, A572Gr55, A572Gr60, A572Gr65,
    A588Gr50,
    A913Gr50, A913Gr60, A913Gr65, A913Gr70,
    A500GrBRound, A500GrBRect, A500GrCRound, A500GrCRect,
    A53GrB, A529Gr50, A529Gr55, A1085,
)  # fmt: skip


def _key(text: str) -> str:
    """Normalize a name for lookup: lowercase with everything but letters and digits removed."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


_REGISTRY = {_key(m.name): m for m in ALL_MATERIALS} | {_key(m.__name__): m for m in ALL_MATERIALS}


def get_material(name: str) -> type[SteelMaterial]:
    """Look up by display name or class name, ignoring case, spaces and punctuation."""
    try:
        return _REGISTRY[_key(name)]
    except KeyError:
        raise KeyError(f"Unknown material {name!r}; known: {[m.name for m in ALL_MATERIALS]}") from None
