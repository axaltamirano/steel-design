"""Shared bases for database shape families that classify identically.

Each concrete family class (``WideFlange``, ``Channel``, ...) inherits the Section B4
slenderness checks from one of these groups and declares its own database properties.
"""

from __future__ import annotations

from steel_design.classification import (
    SectionClassification,
    check_axis,
    compression_element,
    E_Fy,
    flexure_element,
    sqrt_E_Fy,
)
from steel_design.sections.database import DatabaseShape


class RolledIShape(DatabaseShape):
    """Rolled I-shapes (W, M, S, HP): doubly symmetric, flanges and web."""

    def classify_compression(self) -> SectionClassification:
        """Flange Case 1 (0.56 sqrt(E/Fy)) and web Case 5 (1.49 sqrt(E/Fy)) of Table B4.1a."""
        r = sqrt_E_Fy(self.material)
        return SectionClassification(
            (
                compression_element("flange", self.bf_2tf, 0.56 * r, "Table B4.1a Case 1"),
                compression_element("web", self.h_tw, 1.49 * r, "Table B4.1a Case 5"),
            )
        )

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Major axis: flange Case 10 and web Case 15. Minor axis: flange Case 13 only."""
        axis = check_axis(axis)
        r = sqrt_E_Fy(self.material)
        if axis == "y":  # minor-axis bending: webs are not in flexure
            return SectionClassification(
                (flexure_element("flange", self.bf_2tf, 0.38 * r, 1.0 * r, "Table B4.1b Case 13"),)
            )
        return SectionClassification(
            (
                flexure_element("flange", self.bf_2tf, 0.38 * r, 1.0 * r, "Table B4.1b Case 10"),
                flexure_element("web", self.h_tw, 3.76 * r, 5.70 * r, "Table B4.1b Case 15"),
            )
        )


class ChannelShape(DatabaseShape):
    """Channels (C, MC): one flange element on each side of the web."""

    def classify_compression(self) -> SectionClassification:
        """Flange Case 1 and web Case 5 of Table B4.1a."""
        r = sqrt_E_Fy(self.material)
        return SectionClassification(
            (
                compression_element("flange", self.b_t, 0.56 * r, "Table B4.1a Case 1"),
                compression_element("web", self.h_tw, 1.49 * r, "Table B4.1a Case 5"),
            )
        )

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Major axis: flange Case 10 and web Case 15. Minor axis: flange Case 13 only."""
        axis = check_axis(axis)
        r = sqrt_E_Fy(self.material)
        if axis == "y":
            return SectionClassification(
                (flexure_element("flange", self.b_t, 0.38 * r, 1.0 * r, "Table B4.1b Case 13"),)
            )
        return SectionClassification(
            (
                flexure_element("flange", self.b_t, 0.38 * r, 1.0 * r, "Table B4.1b Case 10"),
                flexure_element("web", self.h_tw, 3.76 * r, 5.70 * r, "Table B4.1b Case 15"),
            )
        )


class TeeShape(DatabaseShape):
    """Structural tees (WT, MT, ST): a flange and a stem."""

    def classify_compression(self) -> SectionClassification:
        """Flange Case 1 and stem Case 4 (0.75 sqrt(E/Fy)) of Table B4.1a."""
        r = sqrt_E_Fy(self.material)
        return SectionClassification(
            (
                compression_element("flange", self.bf_2tf, 0.56 * r, "Table B4.1a Case 1"),
                compression_element("stem", self.D_t, 0.75 * r, "Table B4.1a Case 4"),
            )
        )

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Axis x is bending in the plane of symmetry (Section F9) and checks flange Case 10 and
        stem Case 14, as the stem limit applies when the stem is in flexural compression.
        Axis y checks the flange only."""
        axis = check_axis(axis)
        r = sqrt_E_Fy(self.material)
        flange = flexure_element("flange", self.bf_2tf, 0.38 * r, 1.0 * r, "Table B4.1b Case 10")
        if axis == "y":
            return SectionClassification((flange,))
        stem = flexure_element("stem", self.D_t, 0.84 * r, 1.52 * r, "Table B4.1b Case 14")
        return SectionClassification((flange, stem))


class RoundTubeShape(DatabaseShape):
    """Round HSS and pipe: a single circular wall, independent of bending axis."""

    def classify_compression(self) -> SectionClassification:
        """Wall Case 9 (0.11 E/Fy) of Table B4.1a."""
        return SectionClassification(
            (compression_element("wall", self.D_t, 0.11 * E_Fy(self.material), "Table B4.1a Case 9"),)
        )

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Wall Case 20 (0.07 and 0.31 E/Fy) of Table B4.1b."""
        check_axis(axis)
        e = E_Fy(self.material)
        return SectionClassification(
            (flexure_element("wall", self.D_t, 0.07 * e, 0.31 * e, "Table B4.1b Case 20"),)
        )


class AngleShape(DatabaseShape):
    """Single and double angles, which share the flexure check."""

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Leg Case 12 (0.54 and 0.91 sqrt(E/Fy)) of Table B4.1b. Double angles reuse the
        single-angle limits."""
        check_axis(axis)
        r = sqrt_E_Fy(self.material)
        return SectionClassification(
            (flexure_element("leg", self.b_t, 0.54 * r, 0.91 * r, "Table B4.1b Case 12"),)
        )
