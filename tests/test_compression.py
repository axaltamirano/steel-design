import math

import pytest

from steel_design import Q_
from steel_design.compression import (
    OTHER_ELEMENTS,
    effective_width,
    flexural_torsional_buckling_stress,
    nominal_stress,
    round_hss_effective_area,
    single_angle_effective_slenderness,
    slender_element,
)
from steel_design.materials import A36, A992
from steel_design.sections import (
    Angle,
    BuiltUpBox,
    BuiltUpWideFlange,
    Channel,
    DoubleAngle,
    HSSRect,
    HSSRound,
    WideFlange,
    get_shape,
)

E = 29000.0


def fn_stress(fy, fe):
    return 0.658 ** (fy / fe) * fy if fy / fe <= 2.25 else 0.877 * fe


def test_w14x90_flexural_buckling_about_y_hand_calc():
    w = WideFlange("W14X90")
    cs = w.compression_strength(Q_(10, "ft"))
    fb = next(ls for ls in cs.limit_states if ls.name == "flexural buckling about y-axis")
    kl_r = 120 / w.ry.m
    fe = math.pi**2 * E / kl_r**2
    assert fb.Fe.m == pytest.approx(fe)
    assert fb.Fn.m == pytest.approx(fn_stress(50, fe))
    assert fb.Pn.m == pytest.approx(fn_stress(50, fe) * 26.5)
    assert fb.design_strength.m == pytest.approx(0.9 * fn_stress(50, fe) * 26.5)
    assert fb.allowable_strength.m == pytest.approx(fn_stress(50, fe) * 26.5 / 1.67)
    assert cs.design_strength == min(ls.design_strength for ls in cs.limit_states)
    assert not cs.has_slender_elements


def test_torsional_buckling_hand_calc_governs_w14x90_at_10ft():
    w = WideFlange("W14X90")
    tb = next(ls for ls in w.compression_strength(Q_(10, "ft")).limit_states if ls.name == "torsional buckling")
    fe = (math.pi**2 * E * w.Cw.m / 120**2 + 11200 * w.J.m) / (w.Ix.m + w.Iy.m)
    assert tb.Fe.m == pytest.approx(fe)


def test_nominal_stress_branches():
    assert nominal_stress(Q_(50, "ksi"), Q_(100, "ksi")).m == pytest.approx(0.658**0.5 * 50)
    assert nominal_stress(Q_(50, "ksi"), Q_(20, "ksi")).m == pytest.approx(0.877 * 20)


def test_w21x48_slender_web_effective_area():
    w = WideFlange("W21X48")
    cs = w.compression_strength(Q_(10, "ft"))
    assert cs.has_slender_elements
    fb = next(ls for ls in cs.limit_states if ls.name == "flexural buckling about y-axis")
    h, tw = w.h_tw * w.tw.m, w.tw.m
    lam, lam_r = w.h_tw, 1.49 * math.sqrt(E / 50)
    fe = math.pi**2 * E / (120 / w.ry.m) ** 2
    fn = fn_stress(50, fe)
    assert lam > lam_r * math.sqrt(50 / fn)
    fel = (1.31 * lam_r / lam) ** 2 * 50
    k = math.sqrt(fel / fn)
    be = h * (1 - 0.18 * k) * k
    assert fb.Ae.m == pytest.approx(14.1 - (h - be) * tw, rel=1e-3)
    assert fb.Pn.m == pytest.approx(fn * fb.Ae.m)


def test_effective_width_is_full_width_when_nonslender():
    el = slender_element("e", Q_(5, "in"), Q_(0.5, "in"), 1, 20.0, OTHER_ELEMENTS)
    assert effective_width(el, Q_(50, "ksi"), Q_(40, "ksi")).m == pytest.approx(5)


def test_channel_flexural_torsional_buckling_hand_calc():
    c = Channel("C12X30")
    cs = c.compression_strength(Q_(10, "ft"))
    ftb = next(ls for ls in cs.limit_states if ls.name == "flexural-torsional buckling")
    fex = math.pi**2 * E / (120 / c.rx.m) ** 2
    fez = (math.pi**2 * E * c.Cw.m / 120**2 + 11200 * c.J.m) / (c.A.m * c.ro.m**2)
    h = c.H
    fe = (fex + fez) / (2 * h) * (1 - math.sqrt(1 - 4 * fex * fez * h / (fex + fez) ** 2))
    assert ftb.Fe.m == pytest.approx(fe)


def test_tee_flexural_torsional_omits_warping():
    t = get_shape("WT7X34")
    ftb = next(ls for ls in t.compression_strength(Q_(10, "ft")).limit_states if "torsional" in ls.name)
    fey = math.pi**2 * E / (120 / t.ry.m) ** 2
    fez = 11200 * t.J.m / (t.A.m * t.ro.m**2)
    assert ftb.Fe.m == pytest.approx(
        flexural_torsional_buckling_stress(Q_(fey, "ksi"), Q_(fez, "ksi"), t.H).m
    )


def test_round_hss_slender_wall_effective_area():
    s = HSSRound("HSS20.000X0.250")
    fy = s.material.Fy.m
    d_t = s.OD.m / s.tdes.m
    assert 0.11 * E / fy < d_t < 0.45 * E / fy
    expected = (0.038 * E / fy / d_t + 2 / 3) * s.A.m
    assert s.compression_strength(Q_(10, "ft")).governing_lrfd.Ae.m == pytest.approx(expected)


def test_round_hss_beyond_limit_raises():
    with pytest.raises(ValueError):
        round_hss_effective_area(Q_(10, "in**2"), Q_(150, "in"), Q_(0.25, "in"), Q_(E, "ksi"), Q_(50, "ksi"))


def test_hss_rect_flexural_buckling_nonslender():
    s = HSSRect("HSS8X8X1/2")
    cs = s.compression_strength(Q_(10, "ft"))
    fe = math.pi**2 * E / (120 / s.rx.m) ** 2
    assert cs.governing_lrfd.Pn.m == pytest.approx(fn_stress(46, fe) * s.A.m, rel=0.1)
    assert len(cs.limit_states) == 2


def test_built_up_box_slender_plates_reduced():
    box = BuiltUpBox(Q_(20, "in"), Q_(20, "in"), Q_(0.25, "in"), Q_(0.25, "in"), A992)
    cs = box.compression_strength(Q_(10, "ft"))
    assert cs.has_slender_elements
    ls = cs.governing_lrfd
    b = 19.5
    lam, lam_r = b / 0.25, 1.49 * math.sqrt(E / 50)
    fe = math.pi**2 * E / (120 / box.rx.m) ** 2
    fn = fn_stress(50, fe)
    fel = (1.31 * lam_r / lam) ** 2 * 50
    k = math.sqrt(fel / fn)
    be = b * (1 - 0.18 * k) * k
    assert ls.Ae.m == pytest.approx(box.A.m - 4 * (b - be) * 0.25)


def test_single_angle_e5_planar_equal_leg():
    a = Angle("L4X4X1/2")
    cs = a.compression_strength(Q_(5, "ft"), e5="planar")
    ratio = 72 + 0.75 * 60 / a.rx.m
    assert cs.slenderness_ratio == pytest.approx(ratio)
    fe = math.pi**2 * E / ratio**2
    assert cs.governing_lrfd.Pn.m == pytest.approx(fn_stress(36, fe) * a.A.m)


def test_single_angle_e5_box_truss_unequal_leg_short_leg_connected():
    ratio = single_angle_effective_slenderness(
        Q_(100, "in"), Q_(1.14, "in"), Q_(0.864, "in"), Q_(6, "in"), Q_(4, "in"), "box", "short"
    )
    base = 45 + 100 / 1.14
    assert ratio == pytest.approx(max(base + 6 * (1.5**2 - 1), 0.82 * 100 / 0.864))


def test_single_angle_e5_requirements_enforced():
    with pytest.raises(ValueError):
        Angle("L6X3-1/2X1/2").compression_strength(Q_(5, "ft"), e5="planar")
    with pytest.raises(ValueError):
        Angle("L4X4X1/2").compression_strength(Q_(30, "ft"), e5="planar")


def test_single_angle_principal_axis_buckling_without_e5():
    a = Angle("L6X4X1/2")
    ls = a.compression_strength(Q_(10, "ft")).governing_lrfd
    assert ls.name == "flexural buckling about minor principal axis"
    assert ls.slenderness == pytest.approx(120 / a.rz.m)


def test_double_angle_flexural_torsional_hand_calc():
    d = DoubleAngle("2L6X4X1/2LLBB")
    assert d.J.m == pytest.approx(2 * Angle("L6X4X1/2").J.m)
    ftb = next(ls for ls in d.compression_strength(Q_(10, "ft")).limit_states if "torsional" in ls.name)
    fey = math.pi**2 * E / (120 / d.ry.m) ** 2
    fez = 11200 * d.J.m / (d.A.m * d.ro.m**2)
    assert ftb.Fe.m == pytest.approx(
        flexural_torsional_buckling_stress(Q_(fey, "ksi"), Q_(fez, "ksi"), d.H).m
    )


def test_material_change_lowers_strength():
    a36 = WideFlange("W14X90", A36).compression_strength(Q_(10, "ft")).design_strength
    a992 = WideFlange("W14X90", A992).compression_strength(Q_(10, "ft")).design_strength
    assert a36 < a992


def test_k_factors_and_separate_lengths():
    w = WideFlange("W14X90")
    base = w.compression_strength(Q_(10, "ft"))
    braced = w.compression_strength(Q_(20, "ft"), Ly=Q_(10, "ft"), Lz=Q_(10, "ft"))
    assert braced.limit_states[0].slenderness == pytest.approx(240 / w.rx.m)
    assert w.compression_strength(Q_(10, "ft"), Ky=2.0).design_strength < base.design_strength


def test_slenderness_recommendation_flag():
    assert WideFlange("W14X90").compression_strength(Q_(70, "ft")).exceeds_recommended_slenderness
    assert not WideFlange("W14X90").compression_strength(Q_(10, "ft")).exceeds_recommended_slenderness


def test_input_validation():
    w = WideFlange("W14X90")
    with pytest.raises(TypeError):
        w.compression_strength(120.0)
    with pytest.raises(ValueError):
        w.compression_strength(Q_(0, "ft"))
    with pytest.raises(ValueError):
        w.compression_strength(Q_(10, "ft"), Kx=0)


def test_singly_symmetric_built_up_i_uses_flexural_torsional_buckling():
    s = BuiltUpWideFlange(Q_(24, "in"), Q_(12, "in"), Q_(1, "in"), Q_(0.5, "in"), A992, bf_bottom=Q_(8, "in"), tf_bottom=Q_(0.75, "in"))
    assert 0 < s.H < 1
    cs = s.compression_strength(Q_(15, "ft"))
    assert {ls.name for ls in cs.limit_states} == {"flexural buckling about x-axis", "flexural-torsional buckling"}


def test_doubly_symmetric_built_up_i_matches_torsional_modes():
    s = BuiltUpWideFlange(Q_(20, "in"), Q_(10, "in"), Q_(1, "in"), Q_(0.5, "in"), A992)
    assert s.H == pytest.approx(1.0)
    names = {ls.name for ls in s.compression_strength(Q_(15, "ft")).limit_states}
    assert "torsional buckling" in names


@pytest.mark.parametrize(
    "label",
    ["W14X90", "M10X9", "S12X35", "HP12X53", "C12X30", "MC12X31", "WT7X34", "MT2.5X9.45", "ST6X25",
     "L4X4X1/2", "2L4X4X1/2", "HSS8X8X1/2", "HSS20.000X0.250", "PIPE6STD"],
)
def test_every_family_runs(label):
    cs = get_shape(label).compression_strength(Q_(8, "ft"))
    assert cs.design_strength.m > 0
    assert cs.allowable_strength.m > 0
