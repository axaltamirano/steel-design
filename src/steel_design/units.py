"""Shared pint registry. All quantities in the library use US customary units."""

from __future__ import annotations

import pint

#: The shared registry. Always create quantities from this registry (or :data:`Q_`).
ureg = pint.UnitRegistry()
for _definition in ("plf = pound_force / foot", "klf = kip / foot", "psf = pound_force / foot ** 2", "ksf = kip / foot ** 2"):
    ureg.define(_definition)
#: Quantity constructor, e.g. ``Q_(12, "in")``.
Q_ = ureg.Quantity

#: Canonical length unit.
LENGTH = ureg.inch
#: Canonical stress unit.
STRESS = ureg.ksi


def require_length(value: object, name: str) -> pint.Quantity:
    """Return `value` as a length in inches; floats are rejected to avoid unit ambiguity."""
    if not isinstance(value, pint.Quantity):
        raise TypeError(
            f"{name} must be a pint Quantity with length units, e.g. Q_(12, 'in'); got {value!r}"
        )
    if not value.check("[length]"):
        raise ValueError(f"{name} must have length dimensions; got {value.units}")
    return value.to(LENGTH)
