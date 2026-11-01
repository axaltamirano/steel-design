"""Instantaneous center of rotation (ICR) solver for in-plane eccentrically loaded weld groups.

Each weld line is discretized into short elements. An element's load-deformation response follows
the Lesik-Kennedy relationship used in the AISC Steel Construction Manual, Part 8, and depends on
the angle ``theta`` between the element force and the weld axis::

    R = Rult [p (1.9 - 0.9 p)] ** 0.3,         p = delta / delta_m
    Rult = 0.6 FEXX (0.707 w) (1 + 0.5 sin(theta) ** 1.5)      (per unit length)
    delta_m = 0.209 (theta + 2) ** -0.32 w
    delta_u = 1.087 (theta + 6) ** -0.65 w          (theta in degrees)

The group rotates rigidly about the ICR; the element with the smallest ``delta_u / distance`` ratio
reaches its ultimate deformation and governs the deformation of the others.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from steel_design.bolts.icr import _newton


@dataclass(frozen=True)
class WeldElement:
    """A short weld element: midpoint, length, unit axis, and weld parameters (inches, ksi)."""

    x: float
    y: float
    length: float
    ax: float
    ay: float
    size: float
    fexx: float


@dataclass(frozen=True)
class WeldICRSolution:
    """Raw ICR solution in inches and kips; ``forces`` are element force vectors (Fx, Fy)."""

    icr: tuple[float, float] | None
    P: float
    forces: tuple[tuple[float, float], ...]
    converged: bool
    residual: float


def rult_per_length(theta_deg: float, size: float, fexx: float) -> float:
    """Ultimate strength per inch of fillet weld loaded at ``theta_deg`` to its axis, kip/in."""
    s = math.sin(math.radians(theta_deg))
    return 0.6 * fexx * 0.707 * size * (1.0 + 0.5 * s**1.5)


def delta_m(theta_deg: float, size: float) -> float:
    """Deformation at maximum strength, in."""
    return 0.209 * (theta_deg + 2.0) ** -0.32 * size


def delta_u(theta_deg: float, size: float) -> float:
    """Deformation at fracture, in."""
    return 1.087 * (theta_deg + 6.0) ** -0.65 * size


def _theta(el: WeldElement, fx: float, fy: float) -> float:
    c = abs(fx * el.ax + fy * el.ay)
    return math.degrees(math.acos(min(1.0, c)))


def _forces(c, elements):
    info = []
    for el in elements:
        rx, ry = el.x - c[0], el.y - c[1]
        r = math.hypot(rx, ry)
        if r == 0.0:
            info.append((el, 0.0, 0.0, 0.0, 0.0))
            continue
        ux, uy = -ry / r, rx / r
        th = _theta(el, ux, uy)
        info.append((el, ux, uy, r, th))
    # Critical element: smallest ultimate deformation per unit distance from the ICR.
    scale = min(delta_u(th, el.size) / r for el, _, _, r, th in info if r > 0.0)
    out = []
    for el, ux, uy, r, th in info:
        if r == 0.0:
            out.append((0.0, 0.0))
            continue
        p = scale * r / delta_m(th, el.size)
        mag = rult_per_length(th, el.size, el.fexx) * el.length * max(p * (1.9 - 0.9 * p), 0.0) ** 0.3
        out.append((mag * ux, mag * uy))
    return out


def solve_weld_icr(
    elements: Sequence[WeldElement],
    load_point: tuple[float, float],
    direction: tuple[float, float],
    centroid: tuple[float, float],
    tol: float = 1e-10,
    max_iter: int = 200,
    _recurse: bool = True,
) -> WeldICRSolution:
    """Locate the ICR and the corresponding load for a weld group.

    Args:
        elements: Discretized weld elements.
        load_point: A point on the line of action of the load, in.
        direction: Direction in which the load acts (normalized here).
        centroid: Weld group centroid, in.
    """
    n = math.hypot(*direction)
    u = (direction[0] / n, direction[1] / n)
    nrm = (-u[1], u[0])
    e = (load_point[0] - centroid[0]) * nrm[0] + (load_point[1] - centroid[1]) * nrm[1]
    ltot = sum(el.length for el in elements)
    size = max(math.hypot(el.x - centroid[0], el.y - centroid[1]) for el in elements) or 1.0
    if abs(e) < 1e-9 * max(size, 1.0) and _recurse:
        return _concentric(elements, u, load_point, centroid, nrm, size)

    fmax = sum(rult_per_length(90.0, el.size, el.fexx) * el.length for el in elements)
    scale_f, scale_m = fmax, fmax * size

    def res(c):
        f = _forces(c, elements)
        fx = sum(a for a, _ in f)
        fy = sum(b for _, b in f)
        if fx * u[0] + fy * u[1] < 0:
            f = [(-a, -b) for a, b in f]
            fx, fy = -fx, -fy
        g1 = fx * u[1] - fy * u[0]
        g2 = sum((el.x - load_point[0]) * b - (el.y - load_point[1]) * a for el, (a, b) in zip(elements, f))
        return g1 / scale_f, g2 / scale_m, f

    sign = -1.0 if e > 0 else 1.0
    best = None
    ip = sum(el.length * ((el.x - centroid[0]) ** 2 + (el.y - centroid[1]) ** 2) for el in elements)
    for k in (1.0, 0.5, 0.25, 0.1, 0.05, 0.02, 2.0, 4.0, 8.0):
        dist = k * ip / (ltot * abs(e))
        c = (centroid[0] + sign * dist * nrm[0], centroid[1] + sign * dist * nrm[1])
        try:
            c, r1, r2, f, ok = _newton(res, c, tol, max_iter)
        except (ZeroDivisionError, OverflowError, ValueError):
            continue
        # The ICR lies on the side of the centroid opposite to the load; other roots are spurious.
        wrong_side = ((c[0] - centroid[0]) * nrm[0] + (c[1] - centroid[1]) * nrm[1]) * sign < 0
        if wrong_side:
            continue
        norm = math.hypot(r1, r2)
        if best is None or norm < best[0]:
            best = (norm, c, f, ok)
        if ok:
            break
    if best is None or not best[3]:
        # Fallback: start Newton from the best points of a coarse polar scan around the centroid.
        scan = []
        for mult in (0.02, 0.05, 0.1, 0.2, 0.4, 0.8, 1.5, 3, 6, 12, 25, 50, 100):
            for k in range(16):
                a = 2 * math.pi * k / 16
                c0 = (centroid[0] + mult * size * math.cos(a), centroid[1] + mult * size * math.sin(a))
                try:
                    r1, r2, _ = res(c0)
                except (ZeroDivisionError, OverflowError, ValueError):
                    continue
                scan.append((math.hypot(r1, r2), c0))
        scan.sort()
        for _, c0 in scan[:12]:
            try:
                c, r1, r2, f, ok = _newton(res, c0, tol, max_iter)
            except (ZeroDivisionError, OverflowError, ValueError):
                continue
            # Asymmetric groups loaded near their center of resistance can have the ICR on the load side.
            norm = math.hypot(r1, r2)
            if best is None or (ok and not best[3]) or (ok == best[3] and norm < best[0]):
                best = (norm, c, f, ok)
            if ok:
                break
    if best is None:
        raise RuntimeError("The weld ICR solver failed to converge")
    norm, c, f, ok = best
    p_load = sum(a * u[0] + b * u[1] for a, b in f)
    return WeldICRSolution(c, p_load, tuple(f), ok, norm)


def _concentric(elements, u, load_point, centroid, nrm, size):
    """Strength under a load through the centroid, the greater of two valid methods.

    * The limit of the ICR solution as the eccentricity approaches zero.
    * The sum of the weld strengths (Section J2.4), with the directional strength increase only
      when all the weld lines are parallel (a linear weld group).
    """
    eps = 1e-3 * size
    try:
        limit = solve_weld_icr(
            elements, (centroid[0] + eps * nrm[0], centroid[1] + eps * nrm[1]), u, centroid, _recurse=False
        )
    except RuntimeError:
        limit = None
    linear = all(abs(a.ax * b.ay - a.ay * b.ax) < 1e-9 for a in elements for b in elements)
    forces = []
    for el in elements:
        th = _theta(el, u[0], u[1]) if linear else 0.0
        r = rult_per_length(th, el.size, el.fexx) * el.length
        forces.append((r * u[0], r * u[1]))
    spec = sum(f[0] * u[0] + f[1] * u[1] for f in forces)
    if limit is not None and limit.converged and limit.P >= spec:
        return WeldICRSolution(None, limit.P, limit.forces, True, 0.0)
    return WeldICRSolution(None, spec, tuple(forces), True, 0.0)


__all__ = ["WeldElement", "WeldICRSolution", "delta_m", "delta_u", "rult_per_length", "solve_weld_icr"]
