"""Find database shapes by label."""

from __future__ import annotations

from steel_design.materials.base import SteelMaterial
from steel_design.sections.database import DatabaseShape, _load
from steel_design.sections.wide_flange import WideFlange
from steel_design.sections.m_shape import MShape
from steel_design.sections.s_shape import SShape
from steel_design.sections.hp import HP
from steel_design.sections.channel import Channel
from steel_design.sections.m_channel import MChannel
from steel_design.sections.angle import Angle
from steel_design.sections.double_angle import DoubleAngle
from steel_design.sections.wt import WT
from steel_design.sections.mt import MT
from steel_design.sections.st import ST
from steel_design.sections.hss_rect import HSSRect
from steel_design.sections.hss_round import HSSRound
from steel_design.sections.pipe import Pipe

SHAPE_CLASSES: dict[str, type[DatabaseShape]] = {
    cls.family: cls for cls in (WideFlange, MShape, SShape, HP, Channel, MChannel, Angle, DoubleAngle, WT, MT, ST, HSSRect, HSSRound, Pipe)
}


def get_shape(
    label: str,
    family: str | None = None,
    material: type[SteelMaterial] | None = None,
    **options,
) -> DatabaseShape:
    """Find a shape by AISC Manual label or EDI name, e.g. `get_shape("W14X90")`.

    `family` is required only when a label exists in several families. Extra keyword
    options are passed to the shape class (e.g. `continuous_contact=True` for double angles).
    """
    key = label.strip().upper()
    families = [family.upper()] if family else list(SHAPE_CLASSES)
    matches = [fam for fam in families if key in _load(fam)]
    if not matches:
        raise KeyError(f"Shape {label!r} not found" + (f" in {family}" if family else ""))
    if len(matches) > 1:
        raise KeyError(f"{label!r} is ambiguous; specify family from {matches}")
    return SHAPE_CLASSES[matches[0]](label, material, **options)
