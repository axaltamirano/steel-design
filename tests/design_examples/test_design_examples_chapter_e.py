"""AISC Design Examples v16.0, Chapter E (compression), LRFD results."""

import pytest

from steel_design import Q_
from steel_design.sections import WT, WideFlange


def _ft(x):
    return Q_(x, "ft")


def _kips(q):
    return q.to("kip").magnitude


def test_example_e1a_w_shape_column_with_pinned_ends():
    w = WideFlange("W14X132")
    assert _kips(w.get_phiPnc(_ft(30))) == pytest.approx(893, abs=1)  # Manual Table 4-1a
    assert _kips(w.get_phiPnc(_ft(30))) > 840


def test_example_e1b_w_shape_column_with_intermediate_bracing():
    w = WideFlange("W14X90")
    r = w.compression_strength(Lx=_ft(30), Ly=_ft(15), Lz=_ft(15))
    assert r.governing.name == "flexural buckling about x-axis"
    # Table 4-1a at the equivalent length of 19 ft gives 903 kips (conservative rounding up)
    assert _kips(r.design_strength) == pytest.approx(903, rel=0.03)
    assert _kips(r.design_strength) > 800


def test_example_e1c_w_shape_column_with_pinned_ends_direct():
    w = WideFlange("W14X132")
    assert w.compression_slenderness.elements[0].classification.value == "nonslender"
    assert w.rx.m == pytest.approx(6.28)
    assert 30 * 12 / w.ry.m == pytest.approx(95.7, abs=0.1)
    r = w.compression_strength(Lx=_ft(30))
    assert _kips(r.design_strength) == pytest.approx(892, abs=2)


def test_example_e1d_w_shape_column_with_intermediate_bracing_direct():
    w = WideFlange("W14X90")
    assert all(e.classification.value == "nonslender" for e in w.compression_slenderness.elements)
    r = w.compression_strength(Lx=_ft(30), Ly=_ft(15), Lz=_ft(15))
    assert 30 * 12 / w.rx.m == pytest.approx(58.6, abs=0.1)
    assert r.governing.Fe.to("ksi").m == pytest.approx(83.3, abs=0.2)
    assert _kips(r.governing.Pn) == pytest.approx(1030, abs=3)
    assert _kips(r.design_strength) == pytest.approx(927, abs=3)


def test_example_e4a_w_shape_available_strength_with_alignment_chart_k():
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
    w = WideFlange("W14X82")
    r = w.compression_strength(Lx=_ft(14), Ly=_ft(1), Kx=2.0)
    assert _kips(r.design_strength) == pytest.approx(861, abs=2)


def test_example_e7_wt_compression_member_without_slender_elements():
    wt = WT("WT7X34")
    assert all(e.classification.value == "nonslender" for e in wt.compression_slenderness.elements)
    r = wt.compression_strength(Lx=_ft(20))
    states = {s.name: s for s in r.limit_states}
    assert states["flexural buckling about x-axis"].Fe.to("ksi").m == pytest.approx(16.2, abs=0.2)
    assert states["flexural-torsional buckling"].Fe.to("ksi").m == pytest.approx(29.5, abs=0.2)
    assert r.governing.name == "flexural buckling about x-axis"
    assert _kips(r.governing.Pn) == pytest.approx(142, abs=1.5)
    assert _kips(r.design_strength) == pytest.approx(128, abs=1.5)  # Manual Table 4-7
