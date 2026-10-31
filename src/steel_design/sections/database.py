"""Load AISC database shapes from the bundled CSV files as pint quantities."""

from __future__ import annotations

import csv
from functools import cache
from importlib import resources

from steel_design.materials.base import SteelMaterial
from steel_design.materials.defaults import default_material_for
from steel_design.sections.base import Section
from steel_design.units import Q_

_RENAMES = {"W": "weight", "tan(α)": "tan_alpha"}

_LENGTH = {
    "d", "ddet", "Ht", "h", "OD", "bf", "bfdet", "B", "b", "ID", "tw", "twdet", "twdet/2", "tf",
    "tfdet", "t", "tnom", "tdes", "kdes", "kdet", "k1", "x", "y", "eo", "xp", "yp", "rx", "ry",
    "rz", "ro", "rts", "ho", "zA", "zB", "zC", "wA", "wB", "wC", "PA", "PA2", "PB", "PC", "PD",
    "T", "WGi", "WGo",
}  # fmt: skip
_UNITS = (
    {n: "in" for n in _LENGTH}
    | {"weight": "lbf/ft", "A": "in**2", "Wno": "in**2"}
    | {n: "in**3" for n in ("Zx", "Sx", "Zy", "Sy", "Sz", "C", "Qf", "Qw",
                            "SwA", "SwB", "SwC", "SzA", "SzB", "SzC")}
    | {n: "in**4" for n in ("Ix", "Iy", "Iz", "Iw", "J", "Sw1", "Sw2", "Sw3")}
    | {"Cw": "in**6"}
)  # fmt: skip
_TEXT = {"EDI_Std_Nomenclature", "AISC_Manual_Label", "T_F"}


def _attr(column: str) -> str:
    """Python attribute name for a database column (``h/tw`` -> ``h_tw``, ``W`` -> ``weight``)."""
    return _RENAMES.get(column, column.replace("/", "_"))


def _parse(column: str, text: str):
    """Convert a CSV cell to None, text, a float, or a pint quantity according to its column."""
    if text == "":
        return None
    if column in _TEXT:
        return text
    value = float(text)
    unit = _UNITS.get(column) or _UNITS.get(_attr(column))
    return Q_(value, unit) if unit else value


class DatabaseShape(Section):
    """Base class for shapes from the AISC Shapes Database v16.0.

    Use a family subclass (`W`, `HSSRect`, ...) or `get_shape()`. Properties use the AISC
    names with `/` replaced by `_` (e.g. `h_tw`, `bf_2tf`, `b_t`), `W` renamed to `weight`
    and `tan(α)` to `tan_alpha`. Properties not applicable to a shape are None.
    """

    family: str

    def __init__(self, label: str, material: type[SteelMaterial] | None = None):
        """Look up a shape in this family.

        Args:
            label: AISC Manual label or EDI name, case-insensitive (e.g. ``"W14X90"``).
            material: Material class; defaults to the family default from
                :func:`steel_design.materials.default_material_for`.

        Raises:
            KeyError: If the label is not in this family.
            TypeError: If called on :class:`DatabaseShape` itself.
        """
        if type(self) is DatabaseShape:
            raise TypeError("Use a family class such as W, or get_shape()")
        try:
            props = _load(self.family)[label.strip().upper()]
        except KeyError:
            raise KeyError(f"{label!r} is not a {self.family} shape in the AISC database") from None
        self._properties = props
        self.name = props["AISC_Manual_Label"]
        self.material = material or default_material_for(self.family)

    def __getattr__(self, item: str):
        props = self.__dict__.get("_properties", {})
        try:
            return props[item]
        except KeyError:
            raise AttributeError(f"{self.name} has no property {item!r}") from None

    @classmethod
    def labels(cls) -> list[str]:
        """AISC Manual labels for this family, in database order."""
        return list_shapes(cls.family)

    @classmethod
    def properties(cls) -> list[str]:
        """Property names available for this family."""
        return list(next(iter(_load(cls.family).values())))

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name} ({self.material.name})>"


@cache
def _load(family: str) -> dict[str, dict]:
    """Load and cache a family CSV, keyed by upper-case Manual label and EDI name."""
    path = resources.files("steel_design") / "data" / f"{family.lower()}.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        out: dict[str, dict] = {}
        for row in reader:
            props = {_attr(c): _parse(c, v) for c, v in row.items()}
            out[props["AISC_Manual_Label"].upper()] = props
            out.setdefault(props["EDI_Std_Nomenclature"].upper(), props)
        return out


def list_shapes(family: str) -> list[str]:
    """AISC Manual labels for a family, in database order."""
    return list(dict.fromkeys(p["AISC_Manual_Label"] for p in _load(family.upper()).values()))
