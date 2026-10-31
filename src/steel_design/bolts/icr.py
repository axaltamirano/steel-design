"""Instantaneous center of rotation (ICR) solver for in-plane eccentrically loaded bolt groups.

Each bolt follows the Crawford-Kulak load-deformation relationship used in the AISC Steel
Construction Manual, Part 7::

    R = Rult (1 - exp(-mu * delta)) ** lam,      mu = 10, lam = 0.55

The group rotates rigidly about the ICR, so the deformation of each bolt is proportional to its
distance from the ICR and its force is perpendicular to the line joining the bolt to the ICR.
The bolt farthest from the ICR reaches ``delta_max``. The ICR location satisfies two equilibrium
conditions: the resultant of the bolt forces is parallel to the load, and it acts through the
load point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

#: Crawford-Kulak exponent coefficient, 1/in.
MU = 10.0
#: Crawford-Kulak shape exponent.
LAMBDA = 0.55
#: Deformation of the bolt farthest from the ICR at ultimate, in. (3/4 in. A325 bearing tests).
DELTA_MAX = 0.34


@dataclass(frozen=True)
class ICRSolution:
    """Raw ICR solution in inches and kips.

    Attributes:
        icr: ICR coordinates ``(x, y)``; ``None`` for a concentric load (ICR at infinity).
        P: Load at the ultimate state of the farthest bolt.
        forces: Bolt force components ``(Fx, Fy)``.
        converged: True if the equilibrium residuals met the tolerance.
        residual: Final normalized residual.
    """

    icr: tuple[float, float] | None
    P: float
    forces: tuple[tuple[float, float], ...]
    converged: bool
    residual: float


def bolt_force(rult: float, delta: float, mu: float = MU, lam: float = LAMBDA) -> float:
    """Force on a bolt at deformation ``delta``: ``Rult (1 - exp(-mu delta)) ** lam``."""
    return rult * (1.0 - math.exp(-mu * delta)) ** lam


def _forces(c, pts, rult, delta_max, mu, lam):
    """Bolt force vectors for ICR ``c``, with the rotation sense of the first trial (+1)."""
    rho = [(x - c[0], y - c[1]) for x, y in pts]
    dist = [math.hypot(*r) for r in rho]
    dmax = max(dist)
    out = []
    for (rx, ry), d, ru in zip(rho, dist, rult):
        if d == 0.0:
            out.append((0.0, 0.0))
            continue
        r = bolt_force(ru, delta_max * d / dmax, mu, lam)
        out.append((-r * ry / d, r * rx / d))
    return out


def _residual(c, pts, rult, u, p, delta_max, mu, lam):
    """Equilibrium residuals ``(g1, g2)`` and the oriented forces for ICR ``c``."""
    f = _forces(c, pts, rult, delta_max, mu, lam)
    fx = sum(a for a, _ in f)
    fy = sum(b for _, b in f)
    if fx * u[0] + fy * u[1] < 0:
        f = [(-a, -b) for a, b in f]
        fx, fy = -fx, -fy
    g1 = fx * u[1] - fy * u[0]  # force component perpendicular to the load
    g2 = sum((x - p[0]) * b - (y - p[1]) * a for (x, y), (a, b) in zip(pts, f))  # moment about p
    return g1, g2, f


def solve_icr(
    points: Sequence[tuple[float, float]],
    rult: Sequence[float],
    load_point: tuple[float, float],
    direction: tuple[float, float],
    delta_max: float = DELTA_MAX,
    mu: float = MU,
    lam: float = LAMBDA,
    tol: float = 1e-10,
    max_iter: int = 200,
) -> ICRSolution:
    """Locate the ICR and the corresponding load for a bolt group.

    Args:
        points: Bolt coordinates in inches.
        rult: Ultimate (design) strength of each bolt in kips.
        load_point: A point on the line of action of the load, in inches.
        direction: Direction in which the load acts, as a vector (normalized here).
        delta_max: Deformation of the farthest bolt, in.
        mu, lam: Load-deformation constants.
        tol: Convergence tolerance on the normalized residuals.
        max_iter: Maximum Newton iterations.

    Returns:
        The :class:`ICRSolution`.
    """
    pts = [tuple(map(float, q)) for q in points]
    n = len(pts)
    length = math.hypot(*direction)
    u = (direction[0] / length, direction[1] / length)
    nrm = (-u[1], u[0])  # unit vector perpendicular to the load
    rsum = sum(rult)
    # Strength-weighted centroid: a concentric load acts through it when bolt strengths differ.
    xc = sum(r * x for r, (x, _) in zip(rult, pts)) / rsum
    yc = sum(r * y for r, (_, y) in zip(rult, pts)) / rsum

    # Eccentricity of the line of action from the (weighted) centroid.
    e = (load_point[0] - xc) * nrm[0] + (load_point[1] - yc) * nrm[1]
    size = max(math.hypot(x - xc, y - yc) for x, y in pts) or 1.0
    if abs(e) < 1e-9 * max(size, 1.0):
        forces = tuple((r * u[0], r * u[1]) for r in rult)
        return ICRSolution(None, rsum, forces, True, 0.0)

    scale_f, scale_m = rsum, rsum * size

    def res(c):
        g1, g2, f = _residual(c, pts, rult, u, load_point, delta_max, mu, lam)
        return g1 / scale_f, g2 / scale_m, f

    ip = sum(r * ((x - xc) ** 2 + (y - yc) ** 2) for r, (x, y) in zip(rult, pts)) / (rsum / n)
    # The elastic ICR lies on the side of the centroid opposite to the load.
    sign = -1.0 if e > 0 else 1.0
    best = None
    guesses = []
    for k in (1.0, 0.5, 0.25, 2.0, 0.1, 4.0):
        dist = k * ip / (n * abs(e))
        guesses.append((xc + sign * dist * nrm[0], yc + sign * dist * nrm[1]))
    for c in guesses:
        try:
            c, r1, r2, f, ok = _newton(res, c, tol, max_iter)
        except (ZeroDivisionError, OverflowError, ValueError):
            continue
        norm = math.hypot(r1, r2)
        if best is None or norm < best[0]:
            best = (norm, c, f, ok)
        if ok:
            break
    if best is None:
        raise RuntimeError("The ICR solver failed to converge")
    norm, c, f, ok = best
    p_load = sum(a * u[0] + b * u[1] for a, b in f)
    return ICRSolution(c, p_load, tuple(f), ok, norm)


def _newton(res, c, tol, max_iter):
    """Damped Newton iteration with a finite-difference Jacobian."""
    g1, g2, f = res(c)
    for _ in range(max_iter):
        norm = math.hypot(g1, g2)
        if norm < tol:
            return c, g1, g2, f, True
        h = 1e-6 * max(1.0, abs(c[0]), abs(c[1]))
        a1, a2, _ = res((c[0] + h, c[1]))
        b1, b2, _ = res((c[0], c[1] + h))
        j11, j21 = (a1 - g1) / h, (a2 - g2) / h
        j12, j22 = (b1 - g1) / h, (b2 - g2) / h
        det = j11 * j22 - j12 * j21
        if det == 0.0:
            break
        dx = (-g1 * j22 + g2 * j12) / det
        dy = (-g2 * j11 + g1 * j21) / det
        step = 1.0
        while step > 1e-8:
            cn = (c[0] + step * dx, c[1] + step * dy)
            n1, n2, fn = res(cn)
            if math.hypot(n1, n2) < norm:
                c, g1, g2, f = cn, n1, n2, fn
                break
            step *= 0.5
        else:
            break
    return c, g1, g2, f, math.hypot(g1, g2) < tol * 1e3


__all__ = ["DELTA_MAX", "ICRSolution", "LAMBDA", "MU", "bolt_force", "solve_icr"]
