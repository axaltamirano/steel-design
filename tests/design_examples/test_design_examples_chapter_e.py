"""Tests based on the AISC Design Examples, Chapter E (Design of Members for Compression).

Source: *AISC Design Examples, Version 16.0* (the companion to the 16th Edition Steel
Construction Manual and AISC 360-22), Chapter E. The PDF is not distributed with this
repository (``reference/`` is git-ignored).

Conventions:

* Each test is named after the example it reproduces, for example
  ``test_example_e1...`` for Example E.1, and its docstring gives the example title.
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
from steel_design.sections import WT, WideFlange


def _ft(x):
    return Q_(x, "ft")


def _kips(q):
    return q.to("kip").magnitude


def test_example_e1a_w_shape_column_with_pinned_ends():
    """Example E.1A, W14X132 column with pinned ends, from Manual Table 4-1a."""
    w = WideFlange("W14X132")
    assert _kips(w.get_phiPnc(_ft(30))) == pytest.approx(893, abs=1)  # Manual Table 4-1a
    assert _kips(w.get_phiPnc(_ft(30))) > 840


def test_example_e1b_w_shape_column_with_intermediate_bracing():
    """Example E.1B, W14X90 column braced at mid-height on the y-axis, from Manual Table 4-1a."""
    w = WideFlange("W14X90")
    r = w.compression_strength(Lx=_ft(30), Ly=_ft(15), Lz=_ft(15))
    assert r.governing.name == "flexural buckling about x-axis"
    # Table 4-1a at the equivalent length of 19 ft gives 903 kips (conservative rounding up)
    assert _kips(r.design_strength) == pytest.approx(903, rel=0.03)
    assert _kips(r.design_strength) > 800


def test_example_e1c_w_shape_column_with_pinned_ends_direct():
    """Example E.1C, W14X132 column with pinned ends, by direct calculation."""
    w = WideFlange("W14X132")
    assert w.compression_slenderness.elements[0].classification.value == "nonslender"
    assert w.rx.m == pytest.approx(6.28)
    assert 30 * 12 / w.ry.m == pytest.approx(95.7, abs=0.1)
    r = w.compression_strength(Lx=_ft(30))
    assert _kips(r.design_strength) == pytest.approx(892, abs=2)


def test_example_e1d_w_shape_column_with_intermediate_bracing_direct():
    """Example E.1D, W14X90 column braced at mid-height on the y-axis, by direct calculation."""
    w = WideFlange("W14X90")
    assert all(e.classification.value == "nonslender" for e in w.compression_slenderness.elements)
    r = w.compression_strength(Lx=_ft(30), Ly=_ft(15), Lz=_ft(15))
    assert 30 * 12 / w.rx.m == pytest.approx(58.6, abs=0.1)
    assert r.governing.Fe.to("ksi").m == pytest.approx(83.3, abs=0.2)
    assert _kips(r.governing.Pn) == pytest.approx(1030, abs=3)
    assert _kips(r.design_strength) == pytest.approx(927, abs=3)


def test_example_e4a_w_shape_available_strength_with_alignment_chart_k():
    """Example E.4A, W14X82 column with effective length factors from alignment charts (K = 1.5 and 1.4)."""
    w = WideFlange("W14X82")
    # Upper segment K = 1.5 and lower segment K = 1.4, y-axis continuously braced.
    # The example conservatively reads Table 4-1a at 9 ft (940 kips), so the direct result is >= that.
    upper = w.compression_strength(Lx=_ft(14), Ly=_ft(1), Kx=1.5)
    lower = w.compression_strength(Lx=_ft(14), Ly=_ft(1), Kx=1.4)
    assert _kips(upper.design_strength) >= 940
    assert _kips(lower.design_strength) >= _kips(upper.design_strength)
    assert _kips(upper.design_strength) > 250
    assert _kips(lower.design_strength) > 600
    assert _kips(upper.design_strength) == pytest.approx(940, rel=0.03)


def test_example_e4b_w_shape_available_strength_with_k_equal_two():
    """Example E.4B, W14X82 column with K = 2.0."""
    w = WideFlange("W14X82")
    r = w.compression_strength(Lx=_ft(14), Ly=_ft(1), Kx=2.0)
    assert _kips(r.design_strength) == pytest.approx(861, abs=2)


def test_example_e7_wt_compression_member_without_slender_elements():
    """Example E.7, WT7X34 compression member without slender elements (flexural-torsional check)."""
    wt = WT("WT7X34")
    assert all(e.classification.value == "nonslender" for e in wt.compression_slenderness.elements)
    r = wt.compression_strength(Lx=_ft(20))
    states = {s.name: s for s in r.limit_states}
    assert states["flexural buckling about x-axis"].Fe.to("ksi").m == pytest.approx(16.2, abs=0.2)
    assert states["flexural-torsional buckling"].Fe.to("ksi").m == pytest.approx(29.5, abs=0.2)
    assert r.governing.name == "flexural buckling about x-axis"
    assert _kips(r.governing.Pn) == pytest.approx(142, abs=1.5)
    assert _kips(r.design_strength) == pytest.approx(128, abs=1.5)  # Manual Table 4-7
