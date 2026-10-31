"""Bolt hole dimensions and clear distances, AISC 360-22 Sections J3.3 to J3.5 and J3.11."""

from __future__ import annotations

from enum import Enum

from steel_design.units import Q_, require_length


class HoleType(Enum):
    """Hole types of Table J3.3."""

    STANDARD = "standard"
    OVERSIZE = "oversize"
    SHORT_SLOT = "short slot"
    LONG_SLOT = "long slot"


#: Oversize hole diameters for d = 1/2 to 1 in. (Table J3.3).
_OVERSIZE = {0.5: 0.625, 0.625: 0.8125, 0.75: 0.9375, 0.875: 1.0625, 1.0: 1.25}
#: Short-slot lengths for d = 1/2 to 1 in. (Table J3.3).
_SHORT_SLOT_LENGTH = {0.5: 0.6875, 0.625: 0.875, 0.75: 1.0, 0.875: 1.125, 1.0: 1.3125}
#: Minimum edge distance from a standard hole, d = 1/2 to 1-1/4 in. (Table J3.4).
_MIN_EDGE = {0.5: 0.75, 0.625: 0.875, 0.75: 1.0, 0.875: 1.125, 1.0: 1.25, 1.125: 1.5, 1.25: 1.625}


def _lookup(table: dict[float, float], d: float) -> float | None:
    for key, value in table.items():
        if abs(key - d) < 1e-6:
            return value
    return None


def hole_dimensions(diameter, hole: HoleType = HoleType.STANDARD):
    """Width and length of a hole for a bolt of nominal ``diameter`` (Table J3.3).

    Returns:
        ``(width, length)`` as length quantities in inches. Round holes have equal values.

    Raises:
        ValueError: For diameters below 1/2 in. that are not tabulated.
    """
    d = require_length(diameter, "diameter").m
    if d < 0.5 - 1e-9:
        raise ValueError("Table J3.3 starts at a 1/2 in. bolt")
    standard = d + 1 / 16 if d < 1 - 1e-9 else d + 1 / 8
    if hole is HoleType.STANDARD:
        width = length = standard
    elif hole is HoleType.OVERSIZE:
        width = length = _lookup(_OVERSIZE, d) or d + 5 / 16
    elif hole is HoleType.SHORT_SLOT:
        width, length = standard, _lookup(_SHORT_SLOT_LENGTH, d) or d + 3 / 8
    else:
        width, length = standard, 2.5 * d
    return Q_(width, "in"), Q_(length, "in")


def min_edge_distance(diameter, hole: HoleType = HoleType.STANDARD):
    """Minimum edge distance from the hole center (Tables J3.4 and J3.5).

    For oversize and slotted holes the Table J3.5 increment ``C2`` is added, using the long axis
    perpendicular to the edge (the more demanding case).
    """
    d = require_length(diameter, "diameter").m
    base = _lookup(_MIN_EDGE, d) or 1.25 * d
    if hole is HoleType.STANDARD:
        return Q_(base, "in")
    if hole is HoleType.OVERSIZE:
        c2 = 1 / 16 if d <= 0.875 else 1 / 8
    elif hole is HoleType.SHORT_SLOT:
        c2 = 1 / 8 if d < 1.125 else 3 / 16
    else:
        c2 = 0.75 * d
    return Q_(base + c2, "in")


def min_spacing(diameter):
    """Minimum center-to-center spacing, ``2 2/3 d`` (Section J3.3); ``3 d`` is preferred."""
    d = require_length(diameter, "diameter")
    return (8 / 3) * d


def lc_from_edge(edge_distance, hole_length_in_load_direction):
    """Clear distance ``lc`` from a hole to a plate edge: edge distance less half the hole."""
    e = require_length(edge_distance, "edge_distance")
    h = require_length(hole_length_in_load_direction, "hole_length_in_load_direction")
    return e - h / 2


def lc_from_spacing(spacing, hole_length_in_load_direction):
    """Clear distance ``lc`` between adjacent holes: spacing less one hole length."""
    s = require_length(spacing, "spacing")
    h = require_length(hole_length_in_load_direction, "hole_length_in_load_direction")
    return s - h


__all__ = [
    "HoleType",
    "hole_dimensions",
    "lc_from_edge",
    "lc_from_spacing",
    "min_edge_distance",
    "min_spacing",
]
