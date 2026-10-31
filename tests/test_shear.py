import math

import pytest

from steel_design import Q_
from steel_design.materials import A36, A992
from steel_design.resistance_factors import ResistanceFactors
from steel_design.sections import (
    HP,
    MT,
    ST,
    WT,
    Angle,
    BuiltUpBox,
    BuiltUpWideFlange,
    Channel,
    DoubleAngle,
    HSSRect,
    HSSRound,
    MChannel,
    MShape,
    Pipe,
    SShape,
    WideFlange,
)
from steel_design.shear import cv1, cv2, kv_stiffened, plate_shear, round_hss_shear

E = 29000.0
FY = 50.0


def inch(x):
    return Q_(x, "in")


def kips(q):
    return q.to("kip").magnitude


# --- coefficients ---------------------------------------------------------------------


def test_kv_unstiffened_and_stiffened():
    assert kv_stiffened(None) == 5.34
    assert kv_stiffened(4.0) == 5.34
    assert kv_stiffened(2.0) == pytest.approx(5.34 + 4 / 4)
    assert kv_stiffened(1.0) == pytest.approx(9.34)
    with pytest.raises(ValueError):
        kv_stiffened(0.0)


def test_cv1_regions():
    kv = 5.34
    limit = 1.10 * math.sqrt(kv * E / FY)
    assert cv1(A992, limit - 1, kv) == 1.0
    assert cv1(A992, 2 * limit, kv) == pytest.approx(0.5)


def test_cv2_three_regions():
    kv = 5.34
    root = math.sqrt(kv * E / FY)
    assert cv2(A992, 1.0 * root, kv) == 1.0
    assert cv2(A992, 1.2 * root, kv) == pytest.approx(1.10 / 1.2)
    assert cv2(A992, 1.37 * root, kv) == pytest.approx(1.10 / 1.37)
    assert cv2(A992, 2.0 * root, kv) == pytest.approx(1.51 / 4.0)


def test_cv2_continuous_at_region_boundaries():
    root = math.sqrt(1.2 * E / FY)
    assert cv2(A992, 1.37 * root + 1e-9, 1.2) == pytest.approx(cv2(A992, 1.37 * root - 1e-9, 1.2), rel=3e-3)  # 1.51 in G2-11 rounds 1.10 x 1.37


# --- G2: rolled I-shapes --------------------------------------------------------------


def test_rolled_w_uses_g2_1a_with_phi_1():
    w = WideFlange("W14X90")
    s = w.shear_strength("x")
    assert s.reference.endswith("G2.1(a)")
    assert s.phi == ResistanceFactors.SHEAR_ROLLED_I == 1.0
    assert kips(s.Vn) == pytest.approx(0.6 * FY * 14.0 * 0.44)
    assert kips(w.get_phiVnx()) == pytest.approx(0.6 * FY * 14.0 * 0.44)
    assert kips(w.get_Vnx()) == pytest.approx(0.6 * FY * 14.0 * 0.44)


def test_rolled_w_beyond_g2_1a_limit_uses_phi_0_9():
    w = WideFlange("W12X14")  # h/tw = 54.3 > 2.24 sqrt(E/Fy) = 53.9
    s = w.shear_strength("x")
    assert s.phi == ResistanceFactors.SHEAR == 0.9
    assert s.reference.endswith("G2.1(b)")
    assert kips(s.Vn) == pytest.approx(0.6 * FY * 11.9 * 0.2)
    assert kips(w.get_phiVnx()) == pytest.approx(0.9 * 0.6 * FY * 11.9 * 0.2)


def test_rolled_w_in_a36_has_a_higher_g2_1a_limit():
    w = WideFlange("W12X14", A36)
    assert w.shear_strength("x").phi == 1.0
    assert kips(w.get_Vnx()) == pytest.approx(0.6 * 36 * 11.9 * 0.2)


@pytest.mark.parametrize("cls,label", [(MShape, "M12X10"), (SShape, "S12X35"), (HP, "HP14X73")])
def test_other_rolled_i_shapes(cls, label):
    s = cls(label)
    r = s.shear_strength("x")
    Fy = float(s.material.Fy.to("ksi").m)
    h = s.h_tw * float(s.tw.m)
    c1 = cv1(s.material, s.h_tw, 5.34)
    phi = 1.0 if s.h_tw <= 2.24 * math.sqrt(E / Fy) else 0.9
    assert r.phi == phi
    if phi == 1.0:
        c1 = 1.0
    assert kips(r.Vn) == pytest.approx(0.6 * Fy * float(s.d.m) * float(s.tw.m) * c1)
    assert h > 0


# --- G2: channels and built-up I-shapes -----------------------------------------------


def test_channel_web_uses_g2_1b_with_phi_0_9():
    c = Channel("C12X30")
    s = c.shear_strength("x")
    assert s.phi == 0.9
    assert kips(s.Vn) == pytest.approx(0.6 * 36 * 12.0 * 0.51)
    assert MChannel("MC12X31").shear_strength("x").phi == 0.9


def test_built_up_slender_web_unstiffened():
    d, bf, tf, tw = 60.0, 12.0, 1.0, 0.375
    s = BuiltUpWideFlange(inch(d), inch(bf), inch(tf), inch(tw), A992)
    h = d - 2 * tf
    kv = 5.34
    expected_cv = 1.10 * math.sqrt(kv * E / FY) / (h / tw)
    r = s.shear_strength("x")
    assert r.Cv == pytest.approx(expected_cv)
    assert r.phi == 0.9
    assert kips(r.Vn) == pytest.approx(0.6 * FY * d * tw * expected_cv)


def test_built_up_stiffened_uses_larger_kv_and_tension_field_action():
    d, bf, tf, tw = 60.0, 12.0, 1.0, 0.375
    s = BuiltUpWideFlange(inch(d), inch(bf), inch(tf), inch(tw), A992)
    h = d - 2 * tf
    a = 60.0
    a_h = a / h
    kv = 5.34 + 4 / a_h**2
    Aw = d * tw
    c2 = cv2(A992, h / tw, kv)
    # 2 Aw/(Afc+Aft) = 2(22.5)/24 = 1.875 <= 2.5 and h/bf = 4.83 <= 6: Eq. G2-7
    tfa = 0.6 * FY * Aw * (c2 + (1 - c2) / (1.15 * math.sqrt(1 + a_h**2)))
    r = s.shear_strength("x", a=inch(a))
    assert r.name == "tension field action"
    assert r.reference == "Eq. G2-7, G2.2"
    assert r.kv == pytest.approx(kv)
    assert kips(r.Vn) == pytest.approx(tfa)
    assert kips(r.Vn) > kips(s.shear_strength("x").Vn)


def test_tension_field_action_uses_g2_8_for_narrow_flanges():
    d, bf, tf, tw = 60.0, 8.0, 0.5, 0.375
    s = BuiltUpWideFlange(inch(d), inch(bf), inch(tf), inch(tw), A992)
    h = d - 2 * tf
    a_h = 60.0 / h
    kv = 5.34 + 4 / a_h**2
    c2 = cv2(A992, h / tw, kv)
    tfa = 0.6 * FY * d * tw * (c2 + (1 - c2) / (1.15 * (a_h + math.sqrt(1 + a_h**2))))
    r = s.shear_strength("x", a=inch(60))
    assert r.reference == "Eq. G2-8, G2.2"
    assert kips(r.Vn) == pytest.approx(tfa)


def test_widely_spaced_stiffeners_leave_kv_at_5_34():
    s = BuiltUpWideFlange(inch(60), inch(12), inch(1), inch(0.375), A992)
    r = s.shear_strength("x", a=inch(400))
    assert r.kv == 5.34
    assert r.Vn == s.shear_strength("x").Vn


def test_stocky_web_with_stiffeners_is_not_reduced():
    s = BuiltUpWideFlange(inch(24), inch(10), inch(1), inch(0.5), A992)
    r = s.shear_strength("x", a=inch(24))
    assert r.Cv == 1.0
    assert kips(r.Vn) == pytest.approx(0.6 * FY * 24 * 0.5)


def test_rolled_w_with_stiffeners_stays_with_g2_1a_when_eligible():
    r = WideFlange("W14X90").shear_strength("x", a=inch(30))
    assert r.reference.endswith("G2.1(a)")


# --- G3: tees and angles --------------------------------------------------------------


def test_tee_stem_g3():
    t = WT("WT5X6", A992)
    d, tw = float(t.d.m), float(t.tw.m)
    cv = cv2(A992, d / tw, 1.2)
    s = t.shear_strength("x")
    assert s.kv == 1.2
    assert s.phi == 0.9
    assert kips(s.Vn) == pytest.approx(0.6 * FY * d * tw * cv)
    assert kips(t.get_phiVnx()) == pytest.approx(0.9 * 0.6 * FY * d * tw * cv)


def test_mt_and_st_stems():
    for shape in (MT("MT4X3.25"), ST("ST6X20.4")):
        d, tw = float(shape.d.m), float(shape.tw.m)
        Fy = float(shape.material.Fy.m)
        assert kips(shape.get_Vnx()) == pytest.approx(0.6 * Fy * d * tw * cv2(shape.material, d / tw, 1.2))


def test_single_angle_leg():
    a = Angle("L6X4X1/2", A36)
    t = 0.5
    long = a.shear_strength("x")
    short = a.shear_strength("x", leg="short")
    assert kips(long.Vn) == pytest.approx(0.6 * 36 * 6 * t * cv2(A36, 6 / t, 1.2))
    assert kips(short.Vn) == pytest.approx(0.6 * 36 * 4 * t * cv2(A36, 4 / t, 1.2))
    assert long.Vn > short.Vn
    with pytest.raises(ValueError):
        a.shear_strength("x", leg="both")


def test_double_angle_is_twice_one_angle_per_leg():
    d = DoubleAngle("2L4X4X1/2", A36)
    one = Angle("L4X4X1/2", A36).shear_strength("x")
    assert kips(d.shear_strength("x").Vn) == pytest.approx(2 * kips(one.Vn))
    assert kips(d.shear_strength("y").Vn) == pytest.approx(2 * kips(one.Vn))


# --- G4: HSS and box ------------------------------------------------------------------


def test_rect_hss_g4():
    h = HSSRect("HSS8X4X1/4", A36)
    t = float(h.tdes.m)
    Fy = 36.0
    for axis, flat in (("x", float(h.h.m)), ("y", float(h.b.m))):
        r = h.shear_strength(axis)
        cv = cv2(A36, flat / t, 5.0)
        assert r.kv == 5.0
        assert kips(r.Vn) == pytest.approx(0.6 * Fy * 2 * flat * t * cv)
    assert h.shear_strength("x").Vn > h.shear_strength("y").Vn


def test_rect_hss_flat_width_is_outside_dimension_less_three_t():
    h = HSSRect("HSS8X4X1/4")
    assert float(h.h.m) == pytest.approx(8 - 3 * float(h.tdes.m), abs=0.01)


def test_box_g4():
    b = BuiltUpBox(inch(24), inch(12), inch(0.5), inch(0.375), A992)
    hx = 24 - 2 * 0.5
    hy = 12 - 2 * 0.375
    cx = cv2(A992, hx / 0.375, 5.0)
    cy = cv2(A992, hy / 0.5, 5.0)
    assert kips(b.shear_strength("x").Vn) == pytest.approx(0.6 * FY * 2 * hx * 0.375 * cx)
    assert kips(b.shear_strength("y").Vn) == pytest.approx(0.6 * FY * 2 * hy * 0.5 * cy)


# --- G5: round HSS --------------------------------------------------------------------


def test_round_hss_yielding_governs_for_stocky_wall():
    h = HSSRound("HSS10.75X.500", A36)
    r = h.shear_strength("x")
    assert r.name == "shear yielding"
    assert kips(r.Vn) == pytest.approx(0.6 * 36 * float(h.A.m) / 2)


def test_round_hss_buckling_without_lv_uses_g5_2b():
    h = HSSRound("HSS10.75X.188", A992)
    D_t = 10.75 / float(h.tdes.m)
    fcr = min(0.78 * E / D_t**1.5, 0.6 * FY)
    assert kips(h.shear_strength("x").Vn) == pytest.approx(fcr * float(h.A.m) / 2)


def test_round_hss_g5_2a_with_lv():
    kw = dict(D=inch(30), t=inch(0.25), Ag=inch(1) ** 2 * 23.0)
    without = round_hss_shear(A992, "x", **kw)
    short = round_hss_shear(A992, "x", Lv=inch(20), **kw)
    long = round_hss_shear(A992, "x", Lv=inch(5000), **kw)
    D_t = 30 / 0.25
    fcr_a = 1.6 * E / (math.sqrt(20 / 30) * D_t**1.25)
    assert kips(short.Vn) == pytest.approx(min(max(fcr_a, 0.78 * E / D_t**1.5), 0.6 * FY) * 23 / 2)
    assert short.Vn >= without.Vn
    assert long.Vn >= without.Vn


def test_pipe_shear():
    p = Pipe("PIPE6STD", A36)
    assert 0 < kips(p.shear_strength("x").Vn) <= 0.6 * 36 * float(p.A.m) / 2 + 1e-9


# --- G6: minor-axis shear -------------------------------------------------------------


def test_w_minor_axis_shear_two_flanges():
    w = WideFlange("W14X90")
    bf, tf = 14.5, 0.71
    cv = cv2(A992, bf / (2 * tf), 1.2)
    r = w.shear_strength("y")
    assert cv == 1.0  # the User Note: Cv2 = 1.0 for all rolled W shapes with Fy <= 70 ksi
    assert r.phi == 0.9
    assert kips(r.Vn) == pytest.approx(2 * 0.6 * FY * bf * tf)
    assert kips(w.get_phiVny()) == pytest.approx(0.9 * 2 * 0.6 * FY * bf * tf)
    assert kips(w.get_Vny()) == pytest.approx(2 * 0.6 * FY * bf * tf)


def test_channel_minor_axis_shear_uses_bf_over_tf():
    c = Channel("C12X30", A36)
    bf, tf = float(c.bf.m), float(c.tf.m)
    cv = cv2(A36, bf / tf, 1.2)
    assert kips(c.shear_strength("y").Vn) == pytest.approx(2 * 0.6 * 36 * bf * tf * cv)


def test_tee_minor_axis_shear_single_flange():
    t = WT("WT5X6", A992)
    bf, tf = float(t.bf.m), float(t.tf.m)
    cv = cv2(A992, bf / (2 * tf), 1.2)
    assert kips(t.shear_strength("y").Vn) == pytest.approx(0.6 * FY * bf * tf * cv)


def test_built_up_minor_axis_sums_both_flanges():
    s = BuiltUpWideFlange(inch(30), inch(12), inch(1), inch(0.375), A992, bf_bottom=inch(8), tf_bottom=inch(0.5))
    top = 0.6 * FY * 12 * 1 * cv2(A992, 12 / 2, 1.2)
    bottom = 0.6 * FY * 8 * 0.5 * cv2(A992, 8 / 1, 1.2)
    assert kips(s.shear_strength("y").Vn) == pytest.approx(top + bottom)


# --- plate_shear helper, interface ----------------------------------------------------


def test_plate_shear_slender_element_is_reduced():
    r = plate_shear(A992, "x", length=inch(60), thickness=inch(0.25), kv=5.0, reference="test")
    assert r.name == "shear buckling"
    assert r.Cv == pytest.approx(cv2(A992, 240, 5.0))
    assert kips(r.Vn) == pytest.approx(0.6 * FY * 60 * 0.25 * r.Cv)


def test_design_strength_uses_phi_from_the_resistance_factors():
    r = WideFlange("W12X14").shear_strength("x")
    assert r.design_strength == r.Vn * ResistanceFactors.SHEAR


@pytest.mark.parametrize(
    "shape",
    [
        WideFlange("W14X90"), MShape("M12X10"), SShape("S12X35"), HP("HP14X73"), Channel("C10X20"), MChannel("MC10X22"),
        WT("WT5X6"), MT("MT4X3.25"), ST("ST6X20.4"), DoubleAngle("2L4X4X1/2"), Angle("L4X4X1/2"),
        HSSRect("HSS8X6X3/8"), HSSRound("HSS10.75X.250"), Pipe("PIPE6STD"),
        BuiltUpWideFlange(inch(30), inch(12), inch(1), inch(0.5)), BuiltUpBox(inch(24), inch(12), inch(0.5), inch(0.375)),
    ],
    ids=lambda s: s.name if hasattr(s, "name") else str(s),
)
def test_every_family_provides_both_directions(shape):
    for axis in ("x", "y"):
        r = shape.shear_strength(axis)
        assert kips(r.Vn) > 0
        assert r.design_strength.units == Q_(1, "kip").units
    assert shape.get_phiVnx() <= shape.get_Vnx()
    assert shape.get_phiVny() <= shape.get_Vny() * 1.0001


def test_invalid_axis_and_dimensions():
    w = WideFlange("W14X90")
    with pytest.raises(ValueError):
        w.shear_strength("z")
    with pytest.raises(ValueError):
        plate_shear(A992, "x", length=inch(-1), thickness=inch(0.5), kv=5.0, reference="t")
    with pytest.raises(ValueError):
        round_hss_shear(A992, "x", D=inch(10), t=inch(0), Ag=inch(1) ** 2)
