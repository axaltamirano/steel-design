"""Local-buckling classification types and helpers, AISC 360-22 Section B4.

The classification itself is implemented by the shape classes: every section provides
`compression_slenderness` (Table B4.1a), `flexure_slenderness_x` and `flexure_slenderness_y`
(Table B4.1b) properties, backed by `classify_compression()` and `classify_flexure(axis)`.
This module defines the result types and the shared helpers those implementations use.

Limits are checked against Fy of the section's material. Case numbers and limits in the
`reference` strings were checked against AISC 360-22 (August 1, 2022), Tables B4.1a and B4.1b.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from steel_design.materials.base import SteelMaterial


class Slenderness(str, Enum):
    """Local-buckling classification of an element or section."""

    COMPACT = "compact"
    NONCOMPACT = "noncompact"
    NONSLENDER = "nonslender"
    SLENDER = "slender"


@dataclass(frozen=True)
class ElementClassification:
    """Classification of one plate element.

    Attributes:
        element: Element name, e.g. ``"flange"`` or ``"web"``.
        ratio: Width-to-thickness ratio of the element.
        limit_p: Compact/noncompact limit (flexure only, otherwise ``None``).
        limit_r: Noncompact/slender limit in flexure, or nonslender/slender limit in compression.
        classification: The resulting :class:`Slenderness`.
        reference: Table B4.1a or B4.1b case used.
    """
    element: str
    ratio: float  # width-to-thickness ratio of the element
    limit_p: float | None  # lambda_p (flexure only)
    limit_r: float  # lambda_r (flexure) or lambda_r for slender check (compression)
    classification: Slenderness
    reference: str


@dataclass(frozen=True)
class SectionClassification:
    """The classifications of all elements of a section, with lookup by element name."""
    elements: tuple[ElementClassification, ...]

    def __getitem__(self, element: str) -> ElementClassification:
        """Return the named element; raises ``KeyError`` if absent."""
        for e in self.elements:
            if e.element == element:
                return e
        raise KeyError(element)

    @property
    def governing(self) -> Slenderness:
        """The least favorable classification among the elements."""
        order = (Slenderness.COMPACT, Slenderness.NONSLENDER, Slenderness.NONCOMPACT, Slenderness.SLENDER)
        return max((e.classification for e in self.elements), key=order.index)


def sqrt_E_Fy(material: type[SteelMaterial]) -> float:
    """sqrt(E/Fy) for a material."""
    return math.sqrt((material.E / material.Fy).to("dimensionless").m)


def E_Fy(material: type[SteelMaterial]) -> float:
    """E/Fy for a material."""
    return (material.E / material.Fy).to("dimensionless").m


def compression_element(element: str, ratio: float, limit: float, ref: str) -> ElementClassification:
    """Build a nonslender/slender result against the Table B4.1a limit."""
    cls = Slenderness.NONSLENDER if ratio <= limit else Slenderness.SLENDER
    return ElementClassification(element, ratio, None, limit, cls, ref)


def flexure_element(element: str, ratio: float, lp: float, lr: float, ref: str) -> ElementClassification:
    """Build a compact/noncompact/slender result against the Table B4.1b limits."""
    if ratio <= lp:
        cls = Slenderness.COMPACT
    elif ratio <= lr:
        cls = Slenderness.NONCOMPACT
    else:
        cls = Slenderness.SLENDER
    return ElementClassification(element, ratio, lp, lr, cls, ref)


def kc(h_tw: float) -> float:
    """kc = 4/sqrt(h/tw) for built-up I-shape flanges, limited to 0.35-0.76 (Tables B4.1a/b)."""
    return min(max(4 / math.sqrt(h_tw), 0.35), 0.76)


def check_axis(axis: str) -> str:
    """Normalize and validate an axis argument (``"x"`` strong, ``"y"`` weak)."""
    axis = axis.lower()
    if axis not in ("x", "y"):
        raise ValueError("axis must be 'x' (major) or 'y' (minor)")
    return axis
