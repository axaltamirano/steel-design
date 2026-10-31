"""Built-up rectangular box section."""

from __future__ import annotations

from functools import cached_property

from steel_design.materials.base import SteelMaterial
from steel_design.materials.defaults import default_material_for
from steel_design.sections.base import Section
from steel_design.units import Q_, require_length


class BuiltUpBox(Section):
    """Box from four plates, with no fillets (welds ignored).

    Two flange plates of full outside width `B` and thickness `tf` span between two
    web plates of thickness `tw`; `Ht` is the overall outside depth. Warping is
    neglected (Cw = 0), which is standard for closed sections.
    """

    family = "BUILT_UP_BOX"

    def __init__(self, Ht, B, tf, tw, material: type[SteelMaterial] | None = None, name: str | None = None):
        """Create a box section.

        Args:
            Ht: Overall outside depth (length quantity).
            B: Overall outside width (length quantity).
            tf: Flange plate thickness (length quantity).
            tw: Web plate thickness (length quantity).
            material: Material class; defaults to the ``BUILT_UP_BOX`` default.
            name: Optional label; generated from the dimensions when omitted.

        Raises:
            TypeError: If a dimension is not a pint quantity.
            ValueError: If a dimension is non-positive or the plates leave no interior.
        """
        self.Ht = require_length(Ht, "Ht")
        self.B = require_length(B, "B")
        self.tf = require_length(tf, "tf")
        self.tw = require_length(tw, "tw")
        if min(self.Ht.m, self.B.m, self.tf.m, self.tw.m) <= 0:
            raise ValueError("All dimensions must be positive")
        if 2 * self.tf >= self.Ht or 2 * self.tw >= self.B:
            raise ValueError("Plate thicknesses must leave an open interior")
        self.material = material or default_material_for(self.family)
        self.name = name or f"BOX{self.Ht.m:g}x{self.B.m:g}(f{self.tf.m:g},w{self.tw.m:g})"

    @cached_property
    def h(self):
        """Clear web height between flange plates."""
        return self.Ht - 2 * self.tf

    @cached_property
    def b(self):
        """Clear flange width between web plates."""
        return self.B - 2 * self.tw

    @cached_property
    def A(self):
        """Cross-sectional area."""
        return (self.B * self.Ht - self.b * self.h).to("in**2")

    @cached_property
    def weight(self):
        """Weight per unit length, from the material unit weight."""
        return (self.A * self.material.density).to("lbf/ft")

    @cached_property
    def Ix(self):
        """Moment of inertia about the x-axis (strong axis)."""
        return ((self.B * self.Ht**3 - self.b * self.h**3) / 12).to("in**4")

    @cached_property
    def Iy(self):
        """Moment of inertia about the y-axis (weak axis)."""
        return ((self.Ht * self.B**3 - self.h * self.b**3) / 12).to("in**4")

    @cached_property
    def Sx(self):
        """Elastic section modulus about the x-axis."""
        return (2 * self.Ix / self.Ht).to("in**3")

    @cached_property
    def Sy(self):
        """Elastic section modulus about the y-axis."""
        return (2 * self.Iy / self.B).to("in**3")

    @cached_property
    def Zx(self):
        """Plastic section modulus about the x-axis."""
        return ((self.B * self.Ht**2 - self.b * self.h**2) / 4).to("in**3")

    @cached_property
    def Zy(self):
        """Plastic section modulus about the y-axis."""
        return ((self.Ht * self.B**2 - self.h * self.b**2) / 4).to("in**3")

    @cached_property
    def rx(self):
        """Radius of gyration about the x-axis."""
        return ((self.Ix / self.A) ** 0.5).to("in")

    @cached_property
    def ry(self):
        """Radius of gyration about the y-axis."""
        return ((self.Iy / self.A) ** 0.5).to("in")

    @cached_property
    def Ab(self):
        """Area enclosed by the plate centerlines."""
        return ((self.B - self.tw) * (self.Ht - self.tf)).to("in**2")

    @cached_property
    def J(self):
        """Torsional constant by Bredt's formula, 4*Ab^2 / sum(length/thickness)."""
        perimeter_ratio = 2 * (self.B - self.tw) / self.tf + 2 * (self.Ht - self.tf) / self.tw
        return (4 * self.Ab**2 / perimeter_ratio).to("in**4")

    @cached_property
    def C(self):
        """Torsional shear constant, 2*Ab*t_min, so that tau = T / C (AISC 360-22 Sect. H3)."""
        return (2 * self.Ab * min(self.tf, self.tw)).to("in**3")

    @cached_property
    def Cw(self):
        """Warping constant; zero because warping is neglected for closed sections."""
        return Q_(0, "in**6")  # warping neglected for closed sections

    @cached_property
    def b_tf(self):
        """Flange slenderness, clear width ``b`` over ``tf`` (dimensionless)."""
        return float(self.b / self.tf)

    @cached_property
    def h_tw(self):
        """Web slenderness, clear height ``h`` over ``tw`` (dimensionless)."""
        return float(self.h / self.tw)

    def __repr__(self) -> str:
        return f"<BuiltUpBox {self.name} ({self.material.name})>"
