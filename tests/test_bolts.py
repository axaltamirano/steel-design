"""Bolts (AISC 360-22 Section J3) and bolt groups (ICR method)."""

import math

import pytest

from steel_design import Q_
from steel_design.bolts import (
    A307,
    A325,
    A490,
    Bolt,
    BoltGroup,
    Group120,
    HoleType,
    Ply,
    SlipClass,
    hole_dimensions,
    min_edge_distance,
)
from steel_design.bolts.icr import bolt_force


def i(x):
    return Q_(x, "in")


def kips(q):
    return q.to("kip").magnitude


# --- single bolts ------------------------------------------------------------------------


def test_aliases_and_materials():
    assert A325 is Group120
    assert A307.Fnt.m == 45 and A325.Fnt.m == 90 and A490.Fnt.m == 113
    assert A325.Tb(0.75).m == 28 and A490.Tb(0.75).m == 35
    with pytest.raises(ValueError):
        A307.Tb(0.75)
    with pytest.raises(TypeError):
        A325()


@pytest.mark.parametrize(
    "material, x, expected",
    [(A325, False, 17.9), (A325, True, 22.5), (A490, False, 22.5), (A490, True, 27.8), (A307, False, 9.0)],
)
def test_single_shear_strength_matches_manual_table_7_1(material, x, expected):
    bolt = Bolt(i(0.75), material, threads_excluded=x)
    assert kips(bolt.get_phiRnv()) == pytest.approx(expected, abs=0.1)


def test_tension_rupture_and_shear_planes():
    bolt = Bolt(i(0.75), A325, shear_planes=2)
    assert bolt.Ab.m == pytest.approx(0.4418, abs=1e-4)
    assert kips(bolt.get_phiRnt()) == pytest.approx(29.8, abs=0.05)
    assert kips(bolt.get_phiRnv()) == pytest.approx(2 * 17.9, abs=0.1)


def test_shear_reductions():
    bolt = Bolt(i(0.75), A325)
    base = kips(bolt.shear_strength().Rn)
    assert kips(bolt.shear_strength(pattern_length=i(40)).Rn) == pytest.approx(0.833 * base)
    a307 = Bolt(i(0.75), A307)
    # grip of 4.5 in. is 0.75 in. over five diameters: 12/16 in. is a 12% reduction
    assert kips(a307.shear_strength(grip_length=i(4.5)).Rn) == pytest.approx(0.88 * kips(a307.shear_strength().Rn))


def test_combined_tension_and_shear():
    bolt = Bolt(i(0.75), A325)
    no_shear = bolt.tension_with_shear(Q_(0, "kip"))
    assert kips(no_shear.Rn) == pytest.approx(kips(bolt.tension_strength().Rn))
    frv = 10 / bolt.Ab.m
    fnt = min(90, 1.3 * 90 - 90 / (0.75 * 54) * frv)
    assert kips(bolt.tension_with_shear(Q_(10, "kip")).Rn) == pytest.approx(fnt * bolt.Ab.m)
    with pytest.raises(ValueError):
        bolt.tension_with_shear(Q_(30, "kip"))


def test_slip_resistance_table_7_3():
    bolt = Bolt(i(0.75), A325)
    assert kips(bolt.slip_resistance(SlipClass.A).design_strength) == pytest.approx(9.49, abs=0.01)
    assert kips(bolt.slip_resistance(SlipClass.B).design_strength) == pytest.approx(15.8, abs=0.05)
    two = bolt.slip_resistance(SlipClass.B, fillers=2)
    assert kips(two.design_strength) == pytest.approx(0.85 * 15.8, abs=0.05)
    oversized = Bolt(i(0.75), A325, hole=HoleType.OVERSIZE).slip_resistance(SlipClass.A)
    assert oversized.phi == 0.85
    assert Bolt(i(0.75), A325, hole=HoleType.LONG_SLOT).slip_resistance().phi == 0.70
    reduced = bolt.slip_resistance(SlipClass.A, Tu=Q_(10, "kip"), n_tension_bolts=1)
    assert reduced.Rn.m == pytest.approx(0.3 * 1.13 * 28 * (1 - 10 / (1.13 * 28)))
    with pytest.raises(ValueError):
        Bolt(i(0.75), A307).slip_resistance()


def test_bearing_and_tearout():
    bolt = Bolt(i(0.75), A325)
    ply = Ply(i(0.5), Q_(65, "ksi"), i(1.0))
    r = bolt.bearing_tearout_strength(ply)
    assert r.name == "tearout"
    assert kips(r.Rn) == pytest.approx(1.2 * 1.0 * 0.5 * 65)
    assert kips(r.design_strength) == pytest.approx(0.75 * 39)
    far = Ply(i(0.5), Q_(65, "ksi"), i(3.0))
    r = bolt.bearing_tearout_strength(far, deformation_considered=False)
    assert r.name == "bearing" and kips(r.Rn) == pytest.approx(3.0 * 0.75 * 0.5 * 65)
    slot = bolt.bearing_tearout_strength(far, long_slot_perpendicular=True)
    assert kips(slot.Rn) == pytest.approx(2.0 * 0.75 * 0.5 * 65)


def test_effective_strength_is_lesser_of_shear_and_bearing():
    bolt = Bolt(i(0.75), A325)
    thin = Ply(i(0.25), Q_(58, "ksi"), i(0.75))
    assert bolt.effective_strength(thin).name in {"bearing", "tearout"}
    assert bolt.effective_strength().name == "shear rupture"
    thick = Ply(i(1.0), Q_(65, "ksi"), i(3.0))
    assert bolt.effective_strength([thin, thick]).design_strength == bolt.effective_strength(thin).design_strength


def test_hole_helpers():
    assert hole_dimensions(i(0.75))[0].m == pytest.approx(13 / 16)
    assert hole_dimensions(i(0.75), HoleType.OVERSIZE)[0].m == pytest.approx(15 / 16)
    w, ln = hole_dimensions(i(0.75), HoleType.SHORT_SLOT)
    assert (w.m, ln.m) == (pytest.approx(13 / 16), pytest.approx(1.0))
    assert hole_dimensions(i(0.75), HoleType.LONG_SLOT)[1].m == pytest.approx(1.875)
    assert hole_dimensions(i(1.25))[0].m == pytest.approx(1.3125)
    assert min_edge_distance(i(0.75)).m == 1.0
    assert min_edge_distance(i(1.5)).m == pytest.approx(1.875)
    assert min_edge_distance(i(0.75), HoleType.OVERSIZE).m == pytest.approx(1.0625)


# --- bolt groups ---------------------------------------------------------------------------


def test_group_properties():
    group = BoltGroup.grid(3, 2, i(3), i(4), Bolt(i(0.75), A325))
    assert group.n == 6
    assert group.centroid[0].m == pytest.approx(0) and group.centroid[1].m == pytest.approx(0)
    assert group.Ix.m == pytest.approx(2 * (9 + 0 + 9))
    assert group.Iy.m == pytest.approx(6 * 4)
    assert group.Ip.m == pytest.approx(36 + 24)
    assert kips(group.concentric_strength()) == pytest.approx(6 * 17.9, abs=0.5)


def test_group_validation_and_presets():
    bolt = Bolt(i(0.75), A325)
    with pytest.raises(ValueError):
        BoltGroup.grid(0, 2, i(3), i(3), bolt)
    with pytest.raises(ValueError):
        BoltGroup([], bolt)
    with pytest.raises(TypeError):
        BoltGroup([(3, 4)], bolt)
    assert BoltGroup.row(4, i(3), bolt).Iy.m == pytest.approx(2 * (4.5**2 + 1.5**2))
    assert BoltGroup.column(4, i(3), bolt).Ix.m == pytest.approx(2 * (4.5**2 + 1.5**2))
    with pytest.raises(ValueError):
        BoltGroup.grid(2, 2, i(3), i(3), bolt, plies=[None])


def test_conservative_lc_from_edge_and_spacing():
    bolt = Bolt(i(0.75), A325)
    group = BoltGroup.grid(3, 2, i(3), i(3), bolt, edge_distance=i(1.25))
    assert group.conservative_Lc().m == pytest.approx(1.25 - 13 / 32)
    with pytest.raises(ValueError):
        BoltGroup.grid(3, 2, i(3), i(3), bolt).conservative_Lc()


def test_per_bolt_plies_change_strengths():
    bolt = Bolt(i(0.75), A325)
    tight = Ply(i(0.5), Q_(65, "ksi"), i(0.5))
    easy = Ply(i(0.5), Q_(65, "ksi"), i(3.0))
    base = BoltGroup.grid(2, 1, i(3), i(3), bolt)
    group = BoltGroup(base.positions, bolt, plies=[(tight,), (easy,)])
    s = group.bolt_strengths()
    assert s[0].name == "tearout" and s[1].name == "shear rupture"
    assert kips(group.concentric_strength()) == pytest.approx(0.75 * 1.2 * 0.5 * 0.5 * 65 + 17.9, abs=0.1)
    assert group.icr_strength_eccentric(i(3)).C is None
    with pytest.raises(ValueError):
        group.icr_coefficient(i(3))


# --- ICR method ----------------------------------------------------------------------------


def _bruteforce_vertical_load(columns, rows_y, rult, e):
    """Independent bisection for a symmetric group with a vertical load at eccentricity e."""
    pts = [(x, y) for x in columns for y in rows_y]
    xc = sum(x for x, _ in pts) / len(pts)

    def state(x0):
        rhos = [(x - x0, y) for x, y in pts]
        dmax = max(math.hypot(*r) for r in rhos)
        moment = vertical = 0.0
        for rx, ry in rhos:
            d = math.hypot(rx, ry)
            r = bolt_force(rult, 0.34 * d / dmax)
            moment += r * d
            vertical += r * rx / d
        return moment, vertical

    # Moment about the ICR: P (e + xc - x0) = sum(R d), with P = sum(R rx/d); x0 left of centroid.
    lo, hi = xc - 200, xc - 1e-6
    for _ in range(200):
        mid = (lo + hi) / 2
        m, v = state(mid)
        f = m - v * (e + xc - mid)
        if f > 0:
            hi = mid
        else:
            lo = mid
    m, v = state((lo + hi) / 2)
    return v, (lo + hi) / 2


@pytest.mark.parametrize("e", [2, 4, 8, 16])
def test_icr_matches_independent_solution(e):
    group = BoltGroup.grid(4, 2, i(3), i(3), Bolt(i(0.75), A325))
    rult = kips(group.bolt_strengths()[0].design_strength)
    p, x0 = _bruteforce_vertical_load([-1.5, 1.5], [-4.5, -1.5, 1.5, 4.5], rult, e)
    result = group.icr_strength_eccentric(i(e))
    assert result.converged
    assert kips(result.Pn) == pytest.approx(p, rel=1e-6)
    assert result.icr[0].m == pytest.approx(x0, rel=1e-6)
    assert result.icr[1].m == pytest.approx(0, abs=1e-6)


def test_icr_equilibrium_for_inclined_asymmetric_group():
    bolt = Bolt(i(0.875), A490, threads_excluded=True)
    positions = [(i(x), i(y)) for x, y in [(0, 0), (3, 0), (6, 0), (0, 3), (0, 6), (3, 6)]]
    group = BoltGroup(positions, bolt)
    point = (i(9), i(1))
    result = group.icr_strength(point, angle=25)
    assert result.converged
    a = math.radians(25)
    u = (math.sin(a), -math.cos(a))
    fx = sum(f[0].m for f in result.bolt_forces)
    fy = sum(f[1].m for f in result.bolt_forces)
    assert fx == pytest.approx(result.Pn.m * u[0], abs=1e-6)
    assert fy == pytest.approx(result.Pn.m * u[1], abs=1e-6)
    moment = sum(
        (x.m - 9) * f[1].m - (y.m - 1) * f[0].m for (x, y), f in zip(group.positions, result.bolt_forces)
    )
    assert moment == pytest.approx(0, abs=1e-6)
    # The farthest bolt carries Rult (1 - exp(-10 * 0.34)) ** 0.55
    rult = kips(group.bolt_strengths()[0].design_strength)
    assert max(math.hypot(f[0].m, f[1].m) for f in result.bolt_forces) == pytest.approx(bolt_force(rult, 0.34))


def test_concentric_load_gives_sum_of_bolt_strengths():
    group = BoltGroup.grid(3, 2, i(3), i(3), Bolt(i(0.75), A325))
    result = group.icr_strength_eccentric(i(0))
    assert result.icr is None
    assert result.C == pytest.approx(6)
    assert kips(result.Pn) == pytest.approx(kips(group.concentric_strength()))


def test_capacity_falls_as_eccentricity_grows_and_is_bounded():
    group = BoltGroup.grid(4, 2, i(3), i(3), Bolt(i(0.75), A325))
    c = [group.icr_coefficient(i(e)) for e in (0.5, 2, 4, 8, 16)]
    assert all(a > b for a, b in zip(c, c[1:]))
    assert c[0] < group.n
    assert c[-1] < 2.0


def test_single_line_of_bolts_symmetry_and_angle_independence():
    group = BoltGroup.grid(3, 3, i(3), i(3), Bolt(i(0.75), A325))
    c0 = group.icr_coefficient(i(6), 0)
    c90 = group.icr_coefficient(i(6), 90)
    assert c90 == pytest.approx(c0, rel=1e-6)  # the grid is square, so it is the same rotated
    assert group.icr_coefficient(i(-6), 0) == pytest.approx(c0, rel=1e-6)


def test_check_returns_demand_capacity_ratio():
    group = BoltGroup.grid(3, 2, i(3), i(3), Bolt(i(0.75), A325))
    capacity = group.icr_strength_eccentric(i(5)).Pn
    assert group.check(capacity, i(5)) == pytest.approx(1.0)
    assert group.check(0.5 * capacity, i(5)) == pytest.approx(0.5)


def test_icr_with_unequal_bolt_strengths_is_in_equilibrium():
    bolt = Bolt(i(0.75), A325)
    tight = Ply(i(0.5), Q_(65, "ksi"), i(0.5))
    easy = Ply(i(0.5), Q_(65, "ksi"), i(3.0))
    base = BoltGroup.grid(3, 2, i(3), i(3), bolt)
    group = BoltGroup(base.positions, bolt, plies=[(tight,)] * 2 + [(easy,)] * 4)
    result = group.icr_strength((i(6), i(0)), angle=10)
    assert result.converged
    a = math.radians(10)
    assert sum(f[0].m for f in result.bolt_forces) == pytest.approx(result.Pn.m * math.sin(a), abs=1e-6)
    assert sum(f[1].m for f in result.bolt_forces) == pytest.approx(-result.Pn.m * math.cos(a), abs=1e-6)
    # Through the strength-weighted centroid the load is concentric
    rult = [s.design_strength.m for s in group.bolt_strengths()]
    xw = sum(r * x.m for r, (x, _) in zip(rult, group.positions)) / sum(rult)
    yw = sum(r * y.m for r, (_, y) in zip(rult, group.positions)) / sum(rult)
    concentric = group.icr_strength((i(xw), i(yw)), angle=0)
    assert concentric.icr is None
    assert kips(concentric.Pn) == pytest.approx(sum(rult))
