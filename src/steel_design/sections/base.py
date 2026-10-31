"""Common base for all cross sections (database and built-up)."""

from __future__ import annotations

from steel_design.classification import SectionClassification, Slenderness
from steel_design.compression import (
    BucklingMode,
    CompressionStrength,
    EffectiveArea,
    SlenderElement,
    compression_strength,
    effective_lengths,
    reduce_slender_elements,
)
from steel_design.materials.base import SteelMaterial
from steel_design.tension import TensionStrength, slenderness_ratio, tension_strength


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

    def tension_strength(self, An=None, U: float = 1.0) -> TensionStrength:
        """Tensile strength per AISC 360-22 Chapter D: yielding in the gross section (D2-1)
        and rupture in the effective net section (D2-2, D3-1).

        Args:
            An: Net area (pint area quantity); defaults to the gross area ``A`` (no holes).
            U: Shear lag factor from Table D3.1; defaults to 1.0.
        """
        return tension_strength(self.A, self.material.Fy, self.material.Fu, An, U)

    def tension_slenderness_ratio(self, length) -> float:
        """Slenderness ratio ``L / r`` using the least radius of gyration of the section (D1).

        The recommended maximum is 300 (:data:`steel_design.tension.MAX_RECOMMENDED_SLENDERNESS`).
        """
        radii = [getattr(self, n, None) for n in ("rx", "ry", "rz")]
        return slenderness_ratio(length, min(r for r in radii if r is not None))

    def buckling_modes(self, Lcx, Lcy, Lcz) -> tuple[BucklingMode, ...]:
        """Elastic buckling modes to check in compression (Sections E3 and E4).

        Args:
            Lcx: Effective length for buckling about the x-axis.
            Lcy: Effective length for buckling about the y-axis.
            Lcz: Effective length for twist.

        Raises:
            NotImplementedError: If the section type does not implement it.
        """
        raise NotImplementedError(f"Compression not implemented for {type(self).__name__}")

    def slender_elements(self) -> tuple[SlenderElement, ...]:
        """Plate elements reduced by Section E7 when the section has slender elements.

        Raises:
            NotImplementedError: If the section type does not implement it.
        """
        raise NotImplementedError(f"Compression not implemented for {type(self).__name__}")

    def effective_area(self, Fn) -> EffectiveArea:
        """Effective area ``Ae`` for a nominal stress ``Fn`` (Section E7.1)."""
        return reduce_slender_elements(self.A, self.slender_elements(), self.material.Fy, Fn)

    def compression_strength(self, Lx, Ly=None, Lz=None, Kx: float = 1.0, Ky: float = 1.0, Kz: float = 1.0) -> CompressionStrength:
        """Compressive strength per AISC 360-22 Chapter E: flexural (E3), torsional and
        flexural-torsional (E4) buckling, with the slender-element reduction of Section E7.

        Args:
            Lx: Unbraced length for buckling about the x-axis (pint length).
            Ly: Unbraced length for buckling about the y-axis; defaults to ``Lx``.
            Lz: Unbraced length for twist; defaults to ``Ly``.
            Kx: Effective length factor for the x-axis.
            Ky: Effective length factor for the y-axis.
            Kz: Effective length factor for twist.
        """
        Lcx, Lcy, Lcz = effective_lengths(Lx, Ly, Lz, Kx, Ky, Kz)
        return self._compression(self.buckling_modes(Lcx, Lcy, Lcz))

    def _compression(self, modes) -> CompressionStrength:
        slender = self.compression_slenderness.governing == Slenderness.SLENDER
        return compression_strength(self.A, self.material, modes, self.effective_area if slender else None, slender)
