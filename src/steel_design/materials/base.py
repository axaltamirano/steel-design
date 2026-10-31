"""Base class for structural steel materials."""

from __future__ import annotations

from typing import ClassVar

from steel_design.units import Q_


class SteelMaterial:
    """Constants shared by all structural steels. Each subclass defines one grade.

    Grades whose strengths depend on thickness or group get a separate subclass
    per strength level. Materials are used as classes and are not instantiated.
    """

    #: Modulus of elasticity, 29,000 ksi.
    E = Q_(29000, "ksi")
    #: Shear modulus of elasticity, 11,200 ksi.
    G = Q_(11200, "ksi")
    #: Poisson's ratio.
    nu = 0.3
    #: Unit weight of steel, 490 lbf/ft^3.
    density = Q_(490, "lbf/ft**3")
    #: Coefficient of thermal expansion, per degree F.
    alpha = 6.5e-6

    #: Display name, e.g. ``"A572 Gr. 50"``.
    name: ClassVar[str]
    #: Full ASTM designation.
    astm: ClassVar[str]
    #: Minimum specified yield stress (pint quantity in ksi).
    Fy: ClassVar
    #: Minimum specified tensile strength (pint quantity in ksi).
    Fu: ClassVar

    def __init__(self) -> None:
        """Always raises ``TypeError``: materials are used as classes, not instances."""
        raise TypeError(f"{type(self).__name__} is used as a class; do not instantiate it")

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Require every grade subclass to define ``name``, ``astm``, ``Fy`` and ``Fu``."""
        super().__init_subclass__(**kwargs)
        for attr in ("name", "astm", "Fy", "Fu"):
            if not hasattr(cls, attr):
                raise TypeError(f"{cls.__name__} must define {attr!r}")
