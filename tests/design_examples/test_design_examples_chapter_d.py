"""AISC Design Examples v16.0, Chapter D (tension), LRFD results.

The library takes the net area and shear lag factor as inputs, so each test derives ``An`` and
``U`` from the example's own formulas (Spec. B4.3b and Table D3.1) and checks the strengths.
"""

import pytest

from steel_design import Q_
from steel_design.materials import A992, A572Gr50
from steel_design.sections import WT, Angle, DoubleAngle, WideFlange
from steel_design.tension import slenderness_ratio

KIP = "kip"


def _in(x):
    return Q_(x, "in")


def _ft(x):
    return Q_(x, "ft")


def _kips(q):
    return q.to(KIP).magnitude


def test_example_d1_w_shape_tension_member():
    pu = 1.2 * 30 + 1.6 * 90
    w = WideFlange("W8X21", A992)
    assert w.A.m == pytest.approx(6.16)

    # Tensile yielding (Manual Table 5-1 gives 277 kips)
    t_gross = w.tension_strength()
    assert _kips(t_gross.yielding.Pn * 0.9) == pytest.approx(277, abs=0.5)

    # Shear lag: larger of Case 2 (two WTs, x = 0.831 in., l = 9 in.), Case 7 (0.85), and bf*tf/Ag
    wt_xbar, length = 0.831, 9.0
    u_case2 = 1 - wt_xbar / length
    u = max(u_case2, 0.85, 2 * 5.27 * 0.400 / 6.16)
    assert u == pytest.approx(0.908, abs=0.001)

    dh = 13 / 16 + 1 / 16  # 3/4-in. bolts, standard holes, plus 1/16 in. (B4.3b)
    an = w.A - 4 * _in(dh) * w.tf
    assert an.m == pytest.approx(4.76, abs=0.005)

    t = w.tension_strength(An=an, U=u)
    assert t.Ae.m == pytest.approx(4.32, abs=0.01)
    assert t.Ae.m / w.A.m == pytest.approx(0.701, abs=0.001)
    assert _kips(t.rupture.Pn) == pytest.approx(281, abs=1)
    assert _kips(t.rupture.Pn * 0.75) == pytest.approx(211, abs=1)
    assert _kips(t.design_strength) == pytest.approx(211, abs=1)
    assert _kips(t.design_strength) > pu

    # Recommended slenderness limit: L/r = 238 < 300
    assert slenderness_ratio(_ft(25), w.ry) == pytest.approx(238, abs=1)
    assert w.get_phiPnt(An=an, U=u) == t.design_strength


def test_example_d2_single_angle_tension_member():
    pu = 1.2 * 20 + 1.6 * 60
    a = Angle("L4X4X1/2", A572Gr50)
    assert a.rz.m == pytest.approx(0.776)

    # Tensile yielding
    t0 = a.tension_strength()
    assert _kips(t0.yielding.Pn) == pytest.approx(188, abs=0.5)
    assert _kips(t0.yielding.Pn * 0.9) == pytest.approx(169, abs=0.5)

    # Shear lag: Case 2 (x = 1.18 in., l = 9 in.) governs over Case 8 (0.80) and the 0.50 minimum
    u = max(1 - a.x.m / 9.0, 0.80, 0.50)
    assert u == pytest.approx(0.869, abs=0.001)

    an = a.A.m - (13 / 16 + 1 / 16) * a.t.m
    assert an == pytest.approx(3.31, abs=0.01)

    t = a.tension_strength(An=an * Q_(1, "in**2"), U=u)
    assert t.Ae.m == pytest.approx(2.88, abs=0.01)
    assert _kips(t.rupture.Pn) == pytest.approx(187, abs=1)
    assert _kips(t.rupture.Pn * 0.75) == pytest.approx(140, abs=1)
    assert _kips(t.design_strength) == pytest.approx(140, abs=1)
    assert _kips(t.design_strength) > pu

    # Recommended maximum length at L/r = 300
    l_max = 300 * a.rz.m / 12
    assert l_max == pytest.approx(19.4, abs=0.05)


def test_example_d3_wt_shape_tension_member():
    pu = 1.2 * 40 + 1.6 * 120
    wt = WT("WT6X20", A992)

    t0 = wt.tension_strength()
    assert _kips(t0.yielding.Pn * 0.9) == pytest.approx(263, abs=0.5)  # Manual Table 5-3

    # Shear lag, Case 4 (welded plate to the flange only): l = 16 in., w = bf = 8.01 in.
    l, w, xbar = 16.0, wt.bf.m, wt.y.m
    u_case4 = (3 * l**2 / (3 * l**2 + w**2)) * (1 - xbar / l)
    u = max(u_case4, wt.bf.m * wt.tf.m / wt.A.m)
    assert u == pytest.approx(0.860, abs=0.001)

    t = wt.tension_strength(U=u)  # no holes: An = Ag
    assert t.Ae.m == pytest.approx(5.02, abs=0.01)
    assert _kips(t.rupture.Pn) == pytest.approx(326, abs=1)
    assert _kips(t.rupture.Pn * 0.75) == pytest.approx(245, abs=1)
    assert _kips(t.design_strength) == pytest.approx(245, abs=1)
    assert _kips(t.design_strength) > pu

    assert slenderness_ratio(_ft(30), wt.rx) == pytest.approx(229, abs=1)


def test_example_d6_double_angle_tension_member():
    pu = 1.2 * 40 + 1.6 * 120
    da = DoubleAngle("2L4X4X1/2X3/8", A572Gr50)  # 3/8-in. separation
    assert da.A.m == pytest.approx(7.50)

    t0 = da.tension_strength()
    assert _kips(t0.yielding.Pn * 0.9) == pytest.approx(338, abs=0.5)  # Manual Table 5-8

    # Shear lag, Case 2 (x = 1.18 in., l = 21 in.) governs over Case 8 (0.80)
    u = max(1 - 1.18 / 21.0, 0.80, 0.50)
    assert u == pytest.approx(0.944, abs=0.001)

    an = da.A.m - 2 * (13 / 16 + 1 / 16) * 0.5
    assert an == pytest.approx(6.63, abs=0.01)

    t = da.tension_strength(An=an * Q_(1, "in**2"), U=u)
    assert t.Ae.m == pytest.approx(6.26, abs=0.01)
    assert _kips(t.rupture.Pn) == pytest.approx(407, abs=1)
    assert _kips(t.rupture.Pn * 0.75) == pytest.approx(305, abs=1)
    assert _kips(t.design_strength) == pytest.approx(305, abs=1)
    assert _kips(t.design_strength) > pu

    assert slenderness_ratio(_ft(25), da.rx) == pytest.approx(248, abs=1)


@pytest.mark.skip(reason="The library has no net-width helper for staggered bolt holes (Spec. B4.3b.4)")
def test_example_d9_plate_with_staggered_bolts():
    """Plate 14 in. x 1/2 in.: An = 5.75 in.^2, Ae = 5.75 in.^2 with U = 1.0."""
