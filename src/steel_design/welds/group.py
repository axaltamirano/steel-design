"""Fillet weld groups: concentric, elastic-vector and ICR strengths for in-plane loads."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import pint

from steel_design.resistance_factors import ResistanceFactors as phi_
from steel_design.units import Q_, require_length
from steel_design.welds.electrodes import E70XX, Electrode
from steel_design.welds.fillet import THROAT_FACTOR
from steel_design.welds.icr import WeldElement, rult_per_length, solve_weld_icr


@dataclass(frozen=True)
class WeldLine:
    """A straight fillet weld line of uniform leg size.

    Attributes:
        start: ``(x, y)`` of one end, length quantities.
        end: ``(x, y)`` of the other end.
        size: Leg size.
    """

    start: tuple
    end: tuple
    size: pint.Quantity

    @property
    def length(self) -> pint.Quantity:
        """Length of the line."""
        (x1, y1), (x2, y2) = _xy(self.start), _xy(self.end)
        return Q_(math.hypot(x2 - x1, y2 - y1), "in")


@dataclass(frozen=True)
class WeldICRResult:
    """Result of an instantaneous-center-of-rotation analysis of a weld group.

    Attributes:
        icr: ICR location ``(x, y)``; ``None`` when the load is concentric.
        Rn: Nominal strength of the group (kip) in the load direction.
        Pn: Design strength ``phi Rn`` (kip).
        eccentricity: Perpendicular distance from the load line to the group centroid.
        angle: Load angle from the vertical, degrees.
        element_forces: ``(x, y, Fx, Fy)`` for each weld element: midpoint (in.) and force (kip).
        converged: True if equilibrium was satisfied within tolerance.
    """

    icr: tuple[pint.Quantity, pint.Quantity] | None
    Rn: pint.Quantity
    Pn: pint.Quantity
    eccentricity: pint.Quantity
    angle: float
    element_forces: tuple[tuple[float, float, float, float], ...]
    converged: bool

    @property
    def design_strength(self) -> pint.Quantity:
        """Alias of :attr:`Pn`."""
        return self.Pn


def _xy(point) -> tuple[float, float]:
    x, y = point
    return require_length(x, "x").m, require_length(y, "y").m


def _direction(angle_deg: float) -> tuple[float, float]:
    """Load direction for an angle from the vertical: 0 degrees acts downward (-y)."""
    a = math.radians(angle_deg)
    return math.sin(a), -math.cos(a)


class WeldGroup:
    """A group of fillet weld lines in a plane, loaded in that plane.

    Coordinates have x to the right and y up. Loads act in the plane of the group. Strength is the
    weld metal strength of the effective throats, with ``phi = 0.75``; the base metal limit
    states of Section J4 are not included.

    Args:
        lines: The weld lines.
        electrode: Electrode class; E70XX by default.
        n_elements: Number of elements each line is divided into for the ICR analysis.
    """

    def __init__(self, lines: Sequence[WeldLine], electrode: type[Electrode] = E70XX, n_elements: int = 40):
        if not lines:
            raise ValueError("a weld group needs at least one line")
        self.lines = [
            WeldLine(
                (require_length(l.start[0], "x"), require_length(l.start[1], "y")),
                (require_length(l.end[0], "x"), require_length(l.end[1], "y")),
                require_length(l.size, "size"),
            )
            for l in lines
        ]
        for l in self.lines:
            if l.length.m <= 0 or l.size.m <= 0:
                raise ValueError("weld lines need a positive length and size")
        if n_elements < 2:
            raise ValueError("n_elements must be at least 2")
        self.electrode = electrode
        self.n_elements = int(n_elements)

    # -- construction helpers -------------------------------------------------------------
    @classmethod
    def _from_segments(cls, segments, size, electrode, **options) -> "WeldGroup":
        size = require_length(size, "size")
        zero = Q_(0, "in")
        lines = [WeldLine((zero + a, zero + b), (zero + c, zero + d), size) for a, b, c, d in segments]
        return cls(lines, electrode, **options)

    @classmethod
    def line(cls, length, size, electrode=E70XX, vertical: bool = True, **options) -> "WeldGroup":
        """A single weld line, vertical (default) or horizontal, from the origin."""
        L = require_length(length, "length")
        z = Q_(0, "in")
        seg = (z, z, z, L) if vertical else (z, z, L, z)
        return cls._from_segments([seg], size, electrode, **options)

    @classmethod
    def parallel_vertical(cls, length, spacing, size, electrode=E70XX, **options) -> "WeldGroup":
        """Two vertical lines of ``length`` ``spacing`` apart (Manual Table 8-4)."""
        L, s = require_length(length, "length"), require_length(spacing, "spacing")
        z = Q_(0, "in")
        return cls._from_segments([(z, z, z, L), (s, z, s, L)], size, electrode, **options)

    @classmethod
    def parallel_horizontal(cls, length, spacing, size, electrode=E70XX, **options) -> "WeldGroup":
        """Two horizontal lines of ``length`` ``spacing`` apart (Manual Table 8-5)."""
        L, s = require_length(length, "length"), require_length(spacing, "spacing")
        z = Q_(0, "in")
        return cls._from_segments([(z, z, L, z), (z, s, L, s)], size, electrode, **options)

    @classmethod
    def box(cls, width, height, size, electrode=E70XX, **options) -> "WeldGroup":
        """A rectangle of welds all around (Manual Tables 8-6 and 8-7)."""
        w, h = require_length(width, "width"), require_length(height, "height")
        z = Q_(0, "in")
        return cls._from_segments([(z, z, w, z), (w, z, w, h), (w, h, z, h), (z, h, z, z)], size, electrode, **options)

    @classmethod
    def c_shape(cls, height, flange, size, electrode=E70XX, open_side: str = "right", **options) -> "WeldGroup":
        """A vertical back weld of ``height`` with top and bottom flange welds of ``flange`` length.

        ``open_side="right"`` is Manual Table 8-8 (back at the left); ``"left"`` is Table 8-9.
        """
        h, f = require_length(height, "height"), require_length(flange, "flange")
        z = Q_(0, "in")
        if open_side == "right":
            segs = [(z, z, z, h), (z, z, f, z), (z, h, f, h)]
        elif open_side == "left":
            segs = [(f, z, f, h), (z, z, f, z), (z, h, f, h)]
        else:
            raise ValueError("open_side must be 'right' or 'left'")
        return cls._from_segments(segs, size, electrode, **options)

    @classmethod
    def l_shape(
        cls, height, flange, size, electrode=E70XX, flange_at: str = "bottom", open_side: str = "right", **options
    ) -> "WeldGroup":
        """A vertical weld of ``height`` with one flange weld of ``flange`` length.

        ``flange_at`` is ``"bottom"`` or ``"top"``; ``open_side`` is the side the flange extends
        to, ``"right"`` (Manual Tables 8-10 and 8-10a) or ``"left"`` (Tables 8-11 and 8-11a).
        """
        h, f = require_length(height, "height"), require_length(flange, "flange")
        z = Q_(0, "in")
        if flange_at not in ("bottom", "top") or open_side not in ("right", "left"):
            raise ValueError("flange_at is 'bottom' or 'top'; open_side is 'right' or 'left'")
        x0 = z if open_side == "right" else f
        x1 = f if open_side == "right" else z
        y = z if flange_at == "bottom" else h
        return cls._from_segments([(x0, z, x0, h), (x0, y, x1, y)], size, electrode, **options)

    # -- geometry -------------------------------------------------------------------------
    @property
    def total_length(self) -> pint.Quantity:
        """Total length of weld."""
        return sum((l.length for l in self.lines), Q_(0, "in")).to("in")

    def _weights(self) -> list[float]:
        return [l.length.m * l.size.m for l in self.lines]

    @property
    def centroid(self) -> tuple[pint.Quantity, pint.Quantity]:
        """Centroid of the effective throat areas (the weld lines when sizes are equal)."""
        w = self._weights()
        tot = sum(w)
        cx = sum(wi * (_xy(l.start)[0] + _xy(l.end)[0]) / 2 for wi, l in zip(w, self.lines)) / tot
        cy = sum(wi * (_xy(l.start)[1] + _xy(l.end)[1]) / 2 for wi, l in zip(w, self.lines)) / tot
        return Q_(cx, "in"), Q_(cy, "in")

    @property
    def Ip(self) -> pint.Quantity:
        """Polar moment of inertia of the weld lines about the centroid, ``sum L (r^2 + L^2/12)`` (in.^3)."""
        cx, cy = (c.m for c in self.centroid)
        tot = 0.0
        for l in self.lines:
            (x1, y1), (x2, y2) = _xy(l.start), _xy(l.end)
            L = l.length.m
            mx, my = (x1 + x2) / 2 - cx, (y1 + y2) / 2 - cy
            tot += L * (mx * mx + my * my + L * L / 12)
        return Q_(tot, "in**3")

    # -- strength -------------------------------------------------------------------------
    def _capacity_per_length(self, line: WeldLine) -> float:
        """Weld metal strength per unit length (kip/in., no phi) at ``kds = 1``."""
        return self.electrode.Fnw().to("ksi").m * THROAT_FACTOR * line.size.m

    def concentric_strength(self, angle: float = 0.0, directional: bool = False) -> pint.Quantity:
        """Design strength ``phi Rn`` of the group under a load through its centroid.

        Args:
            angle: Load angle from the vertical, degrees.
            directional: Apply the directional strength increase of Eq. J2-5 line by line. Allowed
                for linear weld groups of uniform leg size loaded through the center of gravity.
        """
        ux, uy = _direction(angle)
        total = 0.0
        for l in self.lines:
            (x1, y1), (x2, y2) = _xy(l.start), _xy(l.end)
            L = l.length.m
            cos = abs((x2 - x1) * ux + (y2 - y1) * uy) / L
            theta = math.degrees(math.acos(min(1.0, cos)))
            k = 1.0 + 0.5 * math.sin(math.radians(theta)) ** 1.5 if directional else 1.0
            total += self._capacity_per_length(l) * L * k
        return Q_(phi_.FILLET_WELD * total, "kip")

    def elastic_strength(self, load_point, angle: float = 0.0) -> pint.Quantity:
        """Design strength ``phi Rn`` by the elastic vector method (``kds = 1.0``).

        The load is resisted by a uniform direct shear plus the torsional shear about the
        centroid; the weld point with the largest resultant, relative to its strength, governs.
        """
        px, py = _xy(load_point)
        ux, uy = _direction(angle)
        cx, cy = (c.m for c in self.centroid)
        w = self._weights()
        ip = sum(wi * (((_xy(l.start)[0] + _xy(l.end)[0]) / 2 - cx) ** 2 + ((_xy(l.start)[1] + _xy(l.end)[1]) / 2 - cy) ** 2 + l.length.m ** 2 / 12) for wi, l in zip(w, self.lines))
        wl = sum(wi for wi in w)
        # Per unit leg-size-weighted length: stress-like quantity of the throat area.
        moment = (px - cx) * uy - (py - cy) * ux
        worst = 0.0
        for l in self.lines:
            q = self._capacity_per_length(l)
            for pt in (l.start, l.end):
                x, y = _xy(pt)
                vx = ux / wl * l.size.m + (-(y - cy)) * moment / ip * l.size.m
                vy = uy / wl * l.size.m + (x - cx) * moment / ip * l.size.m
                worst = max(worst, math.hypot(vx, vy) / q)
        return Q_(phi_.FILLET_WELD / worst, "kip")

    def icr_strength(self, load_point, angle: float = 0.0) -> WeldICRResult:
        """Design strength for a load through ``load_point`` by the ICR method.

        The weld elements follow the Lesik-Kennedy load-deformation relationship, with strength
        and ductility depending on the angle between the element force and the weld axis, as in
        Part 8 of the Manual.

        Args:
            load_point: ``(x, y)`` of a point on the line of action, in the group's coordinates.
            angle: Angle of the load from the vertical, degrees; 0 acts downward (-y) and a
                positive angle tilts the load toward +x.
        """
        lp = _xy(load_point)
        u = _direction(angle)
        elements = self._elements()
        cx, cy = (c.m for c in self.centroid)
        sol = solve_weld_icr(elements, lp, u, (cx, cy))
        e = (lp[0] - cx) * -u[1] + (lp[1] - cy) * u[0]
        icr = None if sol.icr is None else (Q_(sol.icr[0], "in"), Q_(sol.icr[1], "in"))
        return WeldICRResult(
            icr=icr,
            Rn=Q_(sol.P, "kip"),
            Pn=Q_(phi_.FILLET_WELD * sol.P, "kip"),
            eccentricity=Q_(abs(e), "in"),
            angle=angle,
            element_forces=tuple((el.x, el.y, fx, fy) for el, (fx, fy) in zip(elements, sol.forces)),
            converged=sol.converged,
        )

    def icr_strength_eccentric(self, e, angle: float = 0.0) -> WeldICRResult:
        """ICR strength for a load whose line of action is ``e`` from the centroid.

        The load acts at the centroid shifted by ``e`` perpendicular to the load direction (toward
        +x for a vertical load).
        """
        e = require_length(e, "e")
        u = _direction(angle)
        xc, yc = self.centroid
        return self.icr_strength((xc + e * -u[1], yc + e * u[0]), angle)

    def icr_coefficient(self, e, angle: float = 0.0, length=None) -> float:
        """Coefficient ``C`` of Manual Part 8, ``Rn = C C1 D l``, for a group of uniform leg size.

        Args:
            e: Eccentricity from the centroid.
            angle: Load angle from the vertical, degrees.
            length: Characteristic length ``l`` of the group (e.g. the weld height for the C and
                L shapes); the longest weld line by default.
        """
        sizes = {round(l.size.m, 9) for l in self.lines}
        if len(sizes) != 1:
            raise ValueError("C is defined only for a uniform weld size")
        l = require_length(length, "length").m if length is not None else max(x.length.m for x in self.lines)
        d = 16 * self.lines[0].size.m
        rn = self.icr_strength_eccentric(e, angle).Rn.m
        return rn / (self.electrode.C1() * d * l)

    def check(self, Pu, e, angle: float = 0.0) -> float:
        """Demand/capacity ratio ``Pu / phi Pn`` for an eccentric load, by the ICR method."""
        capacity = self.icr_strength_eccentric(e, angle).Pn
        return float((Pu / capacity).to("dimensionless").magnitude)

    def plot(self, e=None, angle: float = 0.0, load_point=None, ax=None, show_forces: bool = True):
        """Draw the group with the load line, the eccentricity, the ICR and the element forces.

        Pass either ``e`` or ``load_point``; with neither, only the layout is drawn.
        Requires matplotlib (``pip install steel-design[plot]``). Returns the matplotlib axes.
        """
        from steel_design.welds.plotting import plot_weld_group

        if e is not None and load_point is not None:
            raise ValueError("Give either e or load_point, not both")
        result = None
        if e is not None:
            e = require_length(e, "e")
            u = _direction(angle)
            xc, yc = self.centroid
            load_point = (xc + e * -u[1], yc + e * u[0])
        if load_point is not None:
            result = self.icr_strength(load_point, angle)
        return plot_weld_group(self, result, load_point, angle, ax, show_forces)

    def _elements(self) -> list[WeldElement]:
        fexx = self.electrode.FEXX.to("ksi").m
        out = []
        for l in self.lines:
            (x1, y1), (x2, y2) = _xy(l.start), _xy(l.end)
            L = l.length.m
            ax, ay = (x2 - x1) / L, (y2 - y1) / L
            n = self.n_elements
            for i in range(n):
                t = (i + 0.5) / n
                out.append(WeldElement(x1 + t * (x2 - x1), y1 + t * (y2 - y1), L / n, ax, ay, l.size.m, fexx))
        return out

    def __repr__(self) -> str:
        return f"<WeldGroup {len(self.lines)} lines, {self.total_length.m:g} in. {self.electrode.name}>"


__all__ = ["WeldGroup", "WeldICRResult", "WeldLine"]
