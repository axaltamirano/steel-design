"""Tests based on the AISC Design Examples, Chapter F (Design of Members for Flexure).

Source: *AISC Design Examples, Version 16.0* (the companion to the 16th Edition Steel
Construction Manual and AISC 360-22), Chapter F. The PDF is not distributed with this
repository (``reference/`` is git-ignored).

Conventions:

* Each test is named after the example it reproduces, for example
  ``test_example_f1...`` for Example F.1, and its docstring gives the example title.
* Only the LRFD results are checked; the library does not implement ASD.
* Expected values are the numbers printed in the example. The examples round intermediate
  values and some read the Manual tables, so tolerances are small absolute or relative bands
  rather than exact matches. Tests named ``..._table`` or marked as approximate compare against
  tabulated or interpolated values.
* Section properties come from the AISC Shapes Database v16.0 used by the library, not from the
  rounded values printed in the examples.
"""

import pytest

from steel_design import Q_
from steel_design.flexure import cb
from steel_design.sections import WideFlange


def _ft(x):
    return Q_(x, "ft")


def _kipft(q):
    return q.to("kip*ft").magnitude


def test_example_f1_1a_w_shape_continuously_braced_beam_selection():
    """Example F.1-1A, W18X50 continuously braced beam, from Manual Table 3-2."""
    w = WideFlange("W18X50")
    assert _kipft(w.get_phiMnx(Lb=Q_(1, "in"))) == pytest.approx(379, abs=1)
    assert _kipft(w.get_phiMnx(Lb=Q_(1, "in"))) > 266


def test_example_f1_1b_w_shape_continuously_braced_beam_direct():
    """Example F.1-1B, W18X50 continuously braced beam, by direct calculation."""
    w = WideFlange("W18X50")
    r = w.flexure_strength("x", Lb=Q_(1, "in"))
    assert _kipft(r.Mp) == pytest.approx(421, abs=0.5)
    assert _kipft(r.design_strength) == pytest.approx(379, abs=0.5)
    assert w.flexure_slenderness_x.elements[0].classification.value == "compact"
    # Required Ix for 1.00-in. live load deflection limit is 746 in.^4 < 800 in.^4
    assert w.Ix.m == pytest.approx(800)
    assert w.Ix.m > 746


def test_example_f1_2a_w_shape_braced_at_third_points_table():
    """Example F.1-2A, W18X50 braced at the third points, from Manual Table 3-10 (Cb = 1.0)."""
    w = WideFlange("W18X50")
    # Manual Table 3-10, Cb = 1.0, Lb = 11.7 ft: 302 kip-ft
    assert _kipft(w.get_phiMnx(Lb=_ft(35 / 3), Cb=1.0)) == pytest.approx(302, abs=2)


def test_example_f1_2b_w_shape_braced_at_third_points_direct():
    """Example F.1-2B, W18X50 braced at the third points, by direct calculation with Cb from Eq. F1-1."""
    w = WideFlange("W18X50")
    cb_center = cb(1.00, 0.972, 1.00, 0.972)
    assert cb_center == pytest.approx(1.01, abs=0.01)
    assert cb(0.889, 0.306, 0.556, 0.750) == pytest.approx(1.46, abs=0.01)
    r = w.flexure_strength("x", Lb=_ft(35 / 3), Cb=cb_center)
    assert r.Lp.to("ft").m == pytest.approx(5.83, abs=0.02)
    assert r.Lr.to("ft").m == pytest.approx(16.9, abs=0.1)
    assert r.governing.name == "lateral-torsional buckling"
    assert _kipft(r.governing.Mn) == pytest.approx(338, rel=0.01)
    assert _kipft(r.design_strength) == pytest.approx(304, rel=0.01)
    assert _kipft(r.design_strength) > 266


def test_example_f1_3a_w_shape_braced_at_midspan_table():
    """Example F.1-3A, W18X50 braced at midspan, from Manual Table 3-10 scaled by Cb."""
    w = WideFlange("W18X50")
    # Manual Table 3-10, Cb = 1.0, Lb = 17.5 ft: 222 kip-ft; Cb = 1.30 adjusts to 289 kip-ft
    base = _kipft(w.get_phiMnx(Lb=_ft(17.5), Cb=1.0))
    assert base == pytest.approx(222, abs=2)
    assert 1.30 * base == pytest.approx(289, abs=3)


def test_example_f1_3b_w_shape_braced_at_midspan_direct():
    """Example F.1-3B, W18X50 braced at midspan, by direct calculation (Lb > Lr)."""
    w = WideFlange("W18X50")
    assert cb(1.00, 0.438, 0.750, 0.938) == pytest.approx(1.30, abs=0.01)
    r = w.flexure_strength("x", Lb=_ft(17.5), Cb=1.30)
    assert r.governing.name == "lateral-torsional buckling"
    assert _kipft(r.governing.Mn) == pytest.approx(320, abs=2)
    assert _kipft(r.design_strength) == pytest.approx(288, abs=2)


def test_example_f3a_w_shape_noncompact_flanges_table():
    """Example F.3A, W21X48 with noncompact flanges, from Manual Table 3-2."""
    w = WideFlange("W21X48")
    assert _kipft(w.get_phiMnx(Lb=Q_(1, "in"))) == pytest.approx(398, abs=1)
    assert _kipft(w.get_phiMnx(Lb=Q_(1, "in"))) > 396


def test_example_f3b_w_shape_noncompact_flanges_direct():
    """Example F.3B, W21X48 with noncompact flanges, by direct calculation (Eq. F3-1)."""
    w = WideFlange("W21X48")
    flange = w.flexure_slenderness_x.elements[0]
    assert flange.classification.value == "noncompact"
    assert flange.ratio == pytest.approx(9.47)
    assert flange.limit_p == pytest.approx(9.15, abs=0.01)
    assert flange.limit_r == pytest.approx(24.1, abs=0.05)
    r = w.flexure_strength("x", Lb=Q_(1, "in"))
    assert _kipft(r.Mp) == pytest.approx(446, abs=0.5)
    assert r.governing.name == "compression flange local buckling"
    assert _kipft(r.governing.Mn) == pytest.approx(442, abs=0.5)
    assert _kipft(r.design_strength) == pytest.approx(398, abs=0.5)


def test_example_f4_w_shape_selection_by_moment_of_inertia():
    """Example F.4, W24X55 selected by required moment of inertia, continuously braced."""
    w_u = 1.2 * 0.8 + 1.6 * 2.0
    m_u = w_u * 30**2 / 8
    assert m_u == pytest.approx(468, abs=0.5)
    i_req = 5 * 2.0 / 12 * (30 * 12) ** 4 / (384 * 29000 * 1.00)
    assert i_req == pytest.approx(1260, rel=0.01)
    w = WideFlange("W24X55")
    assert w.Ix.m > 1260
    assert _kipft(w.get_phiMnx(Lb=Q_(1, "in"))) == pytest.approx(503, abs=1)
    assert _kipft(w.get_phiMnx(Lb=Q_(1, "in"))) > m_u


def test_example_f5_i_shaped_member_in_minor_axis_bending():
    """Example F.5, W12X58 in minor-axis bending (Section F6)."""
    m_u = 4.00 * 15**2 / 8
    assert m_u == pytest.approx(113, abs=0.5)
    w = WideFlange("W12X58")
    assert w.Iy.m > 105
    assert w.flexure_slenderness_y.elements[0].classification.value == "compact"
    r = w.flexure_strength("y")
    # Eq. F6-1: Mn = min(Fy Zy, 1.6 Fy Sy) = 1,630 kip-in.
    assert _kipft(r.governing.Mn) == pytest.approx(136, abs=1)
    assert _kipft(r.design_strength) == pytest.approx(122, abs=1)
    assert _kipft(r.design_strength) > m_u
