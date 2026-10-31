"""Bolt groups: concentric strength and eccentric in-plane shear by the ICR method."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import pint

from steel_design.bolts.bolt import Bolt, BoltStrength, Ply
from steel_design.bolts.holes import lc_from_edge, lc_from_spacing
from steel_design.bolts.icr import DELTA_MAX, LAMBDA, MU, solve_icr
from steel_design.units import Q_, require_length


@dataclass(frozen=True)
class ICRResult:
    """Result of an instantaneous-center-of-rotation analysis.

    Attributes:
        icr: ICR location ``(x, y)`` as length quantities; ``None`` when the load is concentric.
        Pn: Design strength of the group (kip) in the load direction, ``phi Rn`` of the bolts
            at the ultimate state of the farthest bolt.
        C: Coefficient ``Pn / (phi rn)`` when all bolts have the same strength, else ``None``.
        eccentricity: Perpendicular distance from the load line to the group centroid.
        angle: Load angle from the vertical, degrees.
        bolt_forces: Force on each bolt as ``(Fx, Fy)`` in kip.
        converged: True if equilibrium was satisfied within tolerance.
    """

    icr: tuple[pint.Quantity, pint.Quantity] | None
    Pn: pint.Quantity
    C: float | None
    eccentricity: pint.Quantity
    angle: float
    bolt_forces: tuple[tuple[pint.Quantity, pint.Quantity], ...]
    converged: bool

    @property
    def design_strength(self) -> pint.Quantity:
        """Alias of :attr:`Pn`; bolt strengths already include ``phi``."""
        return self.Pn


def _xy(point, name: str) -> tuple[float, float]:
    x, y = point
    return require_length(x, name).m, require_length(y, name).m


def _direction(angle_deg: float) -> tuple[float, float]:
    """Load direction for an angle from the vertical: 0 degrees acts downward (-y)."""
    a = math.radians(angle_deg)
    return math.sin(a), -math.cos(a)


class BoltGroup:
    """A group of identical bolts at arbitrary positions.

    Coordinates are in a plane with x to the right and y up. Loads act in that plane. The bolt
    strength of each fastener is the lesser of its shear strength and its bearing/tearout
    strength, so strengths can differ bolt to bolt when edge distances differ.
    """

    def __init__(
        self,
        positions: Iterable[tuple[pint.Quantity, pint.Quantity]],
        bolt: Bolt,
        plies: Ply | Sequence[Ply] | Sequence[Sequence[Ply]] | None = None,
        deformation_considered: bool = True,
        pattern_length=None,
        grip_length=None,
    ):
        """Create a group.

        Args:
            positions: Bolt centers as ``(x, y)`` length quantities.
            bolt: The bolt used at every position.
            plies: Bearing/tearout data. ``None`` checks shear only. A single :class:`Ply`, or a
                flat sequence of plies, applies to every bolt. To set bolts individually pass one
                sequence of plies per bolt, e.g. ``[(ply_a,), (ply_b, ply_c), ...]``.
            deformation_considered: Bearing coefficients: True for 2.4/1.2, false for 3.0/1.5.
            pattern_length: Fastener pattern length for the long-connection shear reduction.
            grip_length: Grip length for the A307 shear reduction.

        Raises:
            ValueError: If there are no positions or the per-bolt ``plies`` have the wrong length.
        """
        self.positions = tuple((require_length(x, "x"), require_length(y, "y")) for x, y in positions)
        if not self.positions:
            raise ValueError("A bolt group needs at least one bolt")
        self.bolt = bolt
        self.deformation_considered = deformation_considered
        self.pattern_length = pattern_length
        self.grip_length = grip_length
        self._plies = self._normalize_plies(plies)
        self.edge_distance = None

    def _normalize_plies(self, plies):
        n = len(self.positions)
        if plies is None:
            return [None] * n
        if isinstance(plies, Ply):
            return [(plies,)] * n
        plies = list(plies)
        if all(isinstance(p, Ply) for p in plies):
            return [tuple(plies)] * n
        if len(plies) != n:
            raise ValueError(f"Per-bolt plies need {n} entries; got {len(plies)}")
        return [(p,) if isinstance(p, Ply) else tuple(p) for p in plies]

    @classmethod
    def grid(
        cls,
        rows: int,
        cols: int,
        s_row,
        s_col,
        bolt: Bolt,
        plies=None,
        edge_distance=None,
        **options,
    ) -> "BoltGroup":
        """Uniform grid centered on the origin.

        Args:
            rows: Number of rows (bolts along y in each column).
            cols: Number of columns (bolts along x in each row).
            s_row: Spacing between rows (vertical).
            s_col: Spacing between columns (horizontal).
            bolt: The bolt at every position.
            plies: See :class:`BoltGroup`.
            edge_distance: Optional edge distance to the plate edges, used by
                :meth:`conservative_Lc`.
            **options: Other :class:`BoltGroup` arguments.

        Raises:
            ValueError: If ``rows`` or ``cols`` is below 1.
        """
        if rows < 1 or cols < 1:
            raise ValueError("rows and cols must be at least 1")
        sr, sc = require_length(s_row, "s_row"), require_length(s_col, "s_col")
        pos = [
            ((i - (cols - 1) / 2) * sc, (j - (rows - 1) / 2) * sr)
            for j in range(rows)
            for i in range(cols)
        ]
        group = cls(pos, bolt, plies=plies, **options)
        group.rows, group.cols, group.s_row, group.s_col = rows, cols, sr, sc
        group.edge_distance = None if edge_distance is None else require_length(edge_distance, "edge_distance")
        return group

    @classmethod
    def row(cls, n: int, spacing, bolt: Bolt, **options) -> "BoltGroup":
        """A single horizontal line of ``n`` bolts."""
        return cls.grid(1, n, spacing, spacing, bolt, **options)

    @classmethod
    def column(cls, n: int, spacing, bolt: Bolt, **options) -> "BoltGroup":
        """A single vertical line of ``n`` bolts."""
        return cls.grid(n, 1, spacing, spacing, bolt, **options)

    def conservative_Lc(self, deformation_hole=None):
        """Conservative clear distance for a grid: the lesser of edge and spacing distances.

        Uses the bolt's hole length for both directions. Requires ``edge_distance`` and a grid
        group built by :meth:`grid`.

        Raises:
            ValueError: If the group has no grid geometry or edge distance.
        """
        if self.edge_distance is None or not hasattr(self, "s_row"):
            raise ValueError("conservative_Lc needs a grid group created with edge_distance")
        h = self.bolt.hole_dimensions[1] if deformation_hole is None else require_length(deformation_hole, "hole")
        options = [lc_from_edge(self.edge_distance, h)]
        for count, s in ((self.rows, self.s_row), (self.cols, self.s_col)):
            if count > 1:
                options.append(lc_from_spacing(s, h))
        return min(options)

    @property
    def n(self) -> int:
        """Number of bolts."""
        return len(self.positions)

    @property
    def centroid(self) -> tuple[pint.Quantity, pint.Quantity]:
        """Centroid of the bolt positions."""
        xs = sum(x.m for x, _ in self.positions) / self.n
        ys = sum(y.m for _, y in self.positions) / self.n
        return Q_(xs, "in"), Q_(ys, "in")

    @property
    def Ix(self) -> pint.Quantity:
        """``sum (y - yc)^2`` about the centroid (in^2)."""
        yc = self.centroid[1].m
        return Q_(sum((y.m - yc) ** 2 for _, y in self.positions), "in**2")

    @property
    def Iy(self) -> pint.Quantity:
        """``sum (x - xc)^2`` about the centroid (in^2)."""
        xc = self.centroid[0].m
        return Q_(sum((x.m - xc) ** 2 for x, _ in self.positions), "in**2")

    @property
    def Ip(self) -> pint.Quantity:
        """Polar moment of the bolt group, ``Ix + Iy`` (in^2)."""
        return self.Ix + self.Iy

    def bolt_strengths(self) -> list[BoltStrength]:
        """Governing single-bolt strength at each position (shear versus bearing/tearout)."""
        return [
            self.bolt.effective_strength(
                p, self.deformation_considered, self.pattern_length, self.grip_length
            )
            for p in self._plies
        ]

    def concentric_strength(self) -> pint.Quantity:
        """Design strength under a load through the centroid: the sum of the bolt strengths."""
        return sum((s.design_strength for s in self.bolt_strengths()), Q_(0, "kip")).to("kip")

    def icr_strength(
        self,
        load_point,
        angle: float = 0.0,
        delta_max: float = DELTA_MAX,
        mu: float = MU,
        lam: float = LAMBDA,
    ) -> ICRResult:
        """Design strength for a load through ``load_point`` by the ICR method.

        Args:
            load_point: ``(x, y)`` of a point on the line of action, in the group's coordinates.
            angle: Angle of the load from the vertical in degrees; 0 acts downward (-y) and a
                positive angle tilts the load toward +x.
            delta_max: Ultimate deformation of the farthest bolt, in.
            mu, lam: Constants of the bolt load-deformation curve.

        Returns:
            An :class:`ICRResult`. ``Pn`` is the load in the direction of ``angle`` at which the
            farthest bolt reaches ``delta_max``, using the design strength of each bolt.
        """
        pts = [(x.m, y.m) for x, y in self.positions]
        rult = [s.design_strength.to("kip").m for s in self.bolt_strengths()]
        sol = solve_icr(pts, rult, _xy(load_point, "load_point"), _direction(angle), delta_max, mu, lam)
        u = _direction(angle)
        xc, yc = (c.m for c in self.centroid)
        e = (_xy(load_point, "load_point")[0] - xc) * -u[1] + (_xy(load_point, "load_point")[1] - yc) * u[0]
        uniform = max(rult) - min(rult) < 1e-9 * max(rult)
        icr = None if sol.icr is None else (Q_(sol.icr[0], "in"), Q_(sol.icr[1], "in"))
        return ICRResult(
            icr=icr,
            Pn=Q_(sol.P, "kip"),
            C=sol.P / rult[0] if uniform else None,
            eccentricity=Q_(abs(e), "in"),
            angle=angle,
            bolt_forces=tuple((Q_(fx, "kip"), Q_(fy, "kip")) for fx, fy in sol.forces),
            converged=sol.converged,
        )

    def icr_strength_eccentric(self, e, angle: float = 0.0, **options) -> ICRResult:
        """ICR strength for a load whose line of action is ``e`` from the centroid.

        The load acts at the geometric centroid shifted by ``e`` perpendicular to the load
        direction (toward +x for a vertical load). When bolt strengths differ, the strength-weighted
        centroid is the point of zero eccentricity, so use :meth:`icr_strength` with a load point.
        """
        e = require_length(e, "e")
        u = _direction(angle)
        xc, yc = self.centroid
        point = (xc + e * -u[1], yc + e * u[0])
        return self.icr_strength(point, angle, **options)

    def icr_coefficient(self, e, angle: float = 0.0, **options) -> float:
        """Coefficient ``C`` of Manual Part 7 (``Pn = C phi rn``) for identical bolts.

        Raises:
            ValueError: If the bolts do not all have the same strength.
        """
        result = self.icr_strength_eccentric(e, angle, **options)
        if result.C is None:
            raise ValueError("C is defined only when all bolts have the same strength")
        return result.C

    def check(self, Pu, e, angle: float = 0.0, **options) -> float:
        """Demand/capacity ratio ``Pu / phi Pn`` for an eccentric load.

        Args:
            Pu: Required strength (kip quantity).
            e: Eccentricity of the load line from the group centroid.
            angle: Load angle from the vertical, degrees.
        """
        capacity = self.icr_strength_eccentric(e, angle, **options).Pn
        return float((Pu / capacity).to("dimensionless").magnitude)

    def __repr__(self) -> str:
        return f"<BoltGroup {self.n} x {self.bolt!r}>"


__all__ = ["BoltGroup", "ICRResult"]
