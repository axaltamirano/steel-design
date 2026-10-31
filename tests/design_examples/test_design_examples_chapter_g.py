"""Tests based on the AISC Design Examples, Chapter G (Design of Members for Shear).

Source: *AISC Design Examples, Version 16.0* (the companion to the 16th Edition Steel
Construction Manual and AISC 360-22), Chapter G. The PDF is not distributed with this
repository (``reference/`` is git-ignored).

Conventions:

* Each test is named after the example it reproduces, for example
  ``test_example_g1...`` for Example G.1, and its docstring gives the example title.
* Only the LRFD results are checked; the library does not implement ASD.
* Expected values are the numbers printed in the example. The examples round intermediate
  values and some read the Manual tables, so tolerances are small absolute or relative bands
  rather than exact matches. Tests named ``..._table`` or marked as approximate compare against
  tabulated or interpolated values.
* Section properties come from the AISC Shapes Database v16.0 used by the library, not from the
  rounded values printed in the examples.
"""

import pytest

from steel_design.materials import A992
from steel_design.sections import Channel, WideFlange


def _kips(q):
    return q.to("kip").magnitude


def test_example_g1a_w_shape_in_major_axis_shear():
    """Example G.1A, W24X62 in major-axis shear, from Manual Table 3-2."""
    w = WideFlange("W24X62")
    vu = 1.2 * 48 + 1.6 * 145
    assert vu == pytest.approx(290, abs=0.5)
    assert _kips(w.get_phiVnx()) == pytest.approx(306, abs=1)  # Manual Table 3-2
    assert _kips(w.get_phiVnx()) > vu


def test_example_g1b_w_shape_in_major_axis_shear_direct():
    """Example G.1B, W24X62 in major-axis shear, by direct calculation (Eq. G2-1)."""
    w = WideFlange("W24X62")
    v = w.shear_strength("x")
    assert v.Cv == 1.0
    assert v.phi == 1.00
    assert (w.d * w.tw).to("in**2").m == pytest.approx(10.2, abs=0.05)
    assert _kips(v.Vn) == pytest.approx(306, abs=1)
    assert _kips(v.design_strength) == pytest.approx(306, abs=1)


def test_example_g2a_channel_in_major_axis_shear():
    """Example G.2A, C15X33.9 channel in major-axis shear, from Manual Table 3-8."""
    # The example uses A992 channels; library default (A36) is overridden accordingly.
    c = Channel("C15X33.9", A992)
    vu = 1.2 * 25 + 1.6 * 75
    assert vu == pytest.approx(150, abs=0.5)
    assert _kips(c.get_phiVnx()) == pytest.approx(162, abs=1)  # Manual Table 3-8
    assert _kips(c.get_phiVnx()) > vu


def test_example_g2b_channel_in_major_axis_shear_direct():
    """Example G.2B, C15X33.9 channel in major-axis shear, by direct calculation."""
    c = Channel("C15X33.9", A992)
    v = c.shear_strength("x")
    assert v.Cv == 1.0
    assert v.phi == 0.90  # G2.1(a) resistance factor of 1.00 does not apply to channels
    assert _kips(v.Vn) == pytest.approx(180, abs=0.5)
    assert _kips(v.design_strength) == pytest.approx(162, abs=0.5)


def test_example_g6_doubly_symmetric_shape_in_minor_axis_shear():
    """Example G.6, W21X48 in minor-axis shear (Eq. G6-1)."""
    w = WideFlange("W21X48")
    vu = 1.2 * 20 + 1.6 * 60
    assert vu == pytest.approx(120, abs=0.5)
    v = w.shear_strength("y")
    assert v.kv == 1.2
    assert v.Cv == 1.0
    assert _kips(v.Vn) == pytest.approx(210, abs=0.5)
    assert _kips(v.design_strength) == pytest.approx(189, abs=0.5)
    assert _kips(v.design_strength) > vu
