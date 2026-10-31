"""Common base for all cross sections (database and built-up)."""

from __future__ import annotations

from steel_design.classification import SectionClassification
from steel_design.materials.base import SteelMaterial


class Section:
    """A cross section with a material. Property names follow the AISC Shapes Database
    (`A`, `d`, `Ix`, `Zx`, `Sx`, `rx`, `Iy`, `J`, `Cw`, ...) and values are pint quantities.

    Every section classifies its elements for local buckling (AISC 360-22 Section B4) against
    the Fy of its material. The results are exposed as the :attr:`compression_slenderness`,
    :attr:`flexure_slenderness_x` and :attr:`flexure_slenderness_y` properties.
    """

    name: str
    family: str
    material: type[SteelMaterial]

    def classify_compression(self) -> SectionClassification:
        """Classify each element for axial compression (Table B4.1a).

        Raises:
            NotImplementedError: If the section type does not implement it.
        """
        raise NotImplementedError(f"Compression classification not implemented for {type(self).__name__}")

    def classify_flexure(self, axis: str = "x") -> SectionClassification:
        """Classify each element for flexure about ``axis`` (Table B4.1b).

        Args:
            axis: ``"x"`` for strong-axis or ``"y"`` for weak-axis bending.

        Raises:
            NotImplementedError: If the section type does not implement it.
            ValueError: For an invalid ``axis``.
        """
        raise NotImplementedError(f"Flexure classification not implemented for {type(self).__name__}")

    @property
    def compression_slenderness(self) -> SectionClassification:
        """Element classifications for axial compression, nonslender or slender (Table B4.1a)."""
        return self.classify_compression()

    @property
    def flexure_slenderness_x(self) -> SectionClassification:
        """Element classifications for strong-axis flexure: compact, noncompact or slender (Table B4.1b)."""
        return self.classify_flexure("x")

    @property
    def flexure_slenderness_y(self) -> SectionClassification:
        """Element classifications for weak-axis flexure: compact, noncompact or slender (Table B4.1b)."""
        return self.classify_flexure("y")
