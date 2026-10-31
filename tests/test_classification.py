import math

import pytest

from steel_design import Q_
from steel_design.classification import Slenderness
from steel_design.materials import A36, A992
from steel_design.sections import (
    Section,
    BuiltUpBox,
    BuiltUpWideFlange,
    HSSRect,
    HSSRound,
    WideFlange,
    get_shape,
)

R50 = math.sqrt(29000 / 50)


def test_w14x90_flexure_hand_calc():
    c = WideFlange("W14X90").classify_flexure()
    assert c["flange"].ratio == pytest.approx(10.2)
    assert c["flange"].limit_p == pytest.approx(0.38 * R50)  # 9.15
    assert c["flange"].limit_r == pytest.approx(R50)
    assert c["flange"].classification is Slenderness.NONCOMPACT
    assert c["web"].classification is Slenderness.COMPACT
    assert c.governing is Slenderness.NONCOMPACT


def test_w14x90_compression_and_material_dependence():
    assert WideFlange("W14X90").classify_compression().governing is Slenderness.NONSLENDER
    # A36: sqrt(E/Fy) is larger, so the flange becomes compact
    assert WideFlange("W14X90", material=A36).classify_flexure()["flange"].classification is Slenderness.COMPACT


def test_known_manual_footnotes_fy50():
    noncompact = {
        l
        for l in WideFlange.labels()
        if WideFlange(l).classify_flexure()["flange"].classification is not Slenderness.COMPACT
    }
    assert {"W14X99", "W14X90", "W12X65", "W21X48", "W6X8.5"} <= noncompact
    assert WideFlange("W21X48").classify_compression().governing is Slenderness.SLENDER


def test_built_up_wide_flange():
    s = BuiltUpWideFlange(Q_(30, "in"), Q_(12, "in"), Q_(1, "in"), Q_(0.375, "in"), material=A992)
    kc = 4 / math.sqrt(s.h_tw)
    assert kc == pytest.approx(0.4629, abs=1e-3)
    comp = s.classify_compression()
    assert comp["flange"].limit_r == pytest.approx(0.64 * math.sqrt(kc) * R50)
    assert comp["web"].classification is Slenderness.SLENDER  # h/tw = 74.7 > 35.9
    flex = s.classify_flexure()
    assert flex["flange"].limit_r == pytest.approx(0.95 * math.sqrt(kc * 580 / 0.7))
    assert flex["web"].classification is Slenderness.COMPACT  # 74.7 < 90.5


def test_kc_is_clamped():
    thick_web = BuiltUpWideFlange(Q_(20, "in"), Q_(12, "in"), Q_(1, "in"), Q_(2, "in"))
    assert thick_web.classify_flexure()["flange"].limit_r > 0  # h/tw = 9 -> kc capped at 0.76


def test_hss_rect_axes():
    s = HSSRect("HSS12X4X1/4", material=A992)
    major = s.classify_flexure("x")
    minor = s.classify_flexure("y")
    assert major["flange"].ratio == pytest.approx(s.b_tdes)
    assert major["web"].ratio == pytest.approx(s.h_tdes)
    assert minor["flange"].ratio == pytest.approx(s.h_tdes)
    assert s.classify_compression()["long wall"].ratio == pytest.approx(s.h_tdes)


def test_built_up_box():
    s = BuiltUpBox(Q_(12, "in"), Q_(10, "in"), Q_(0.5, "in"), Q_(0.5, "in"), material=A992)
    flex = s.classify_flexure()
    assert flex["flange"].ratio == pytest.approx(18)  # clear width 9 in / 0.5 in
    assert flex["flange"].limit_r == pytest.approx(1.49 * R50)  # Case 21, not the HSS 1.40
    assert flex["flange"].reference == "Table B4.1b Case 21"
    assert flex["flange"].classification is Slenderness.COMPACT  # 18 < 1.12*24.08 = 27.0
    assert flex["web"].classification is Slenderness.COMPACT  # 22 < 2.42*24.08 = 58.3
    comp = s.classify_compression()
    assert comp["web"].limit_r == pytest.approx(1.49 * R50)  # Case 8
    assert comp.governing is Slenderness.NONSLENDER  # 22 < 35.9


def test_round_hss_and_pipe():
    s = get_shape("HSS10.000X0.500")
    assert isinstance(s, HSSRound)
    c = s.classify_flexure()["wall"]
    assert c.limit_p == pytest.approx(0.07 * s.material.E.m / s.material.Fy.m)
    assert c.ratio == pytest.approx(s.D_t)
    assert s.classify_compression()["wall"].limit_r == pytest.approx(0.11 * s.material.E.m / s.material.Fy.m)


def test_axis_validation_and_unsupported():
    with pytest.raises(ValueError):
        WideFlange("W14X90").classify_flexure("z")
    with pytest.raises(NotImplementedError):
        Section().classify_compression()


def test_channel_matches_i_shape_limits():
    from steel_design.sections import Channel

    c = Channel("C10X30")
    flex = c.classify_flexure()
    assert flex["flange"].ratio == pytest.approx(6.95)
    assert flex["flange"].limit_p == pytest.approx(0.38 * math.sqrt(29000 / 36))
    assert flex["flange"].classification is Slenderness.COMPACT
    assert c.classify_compression().governing is Slenderness.NONSLENDER
    minor = c.classify_flexure("y")
    assert len(minor.elements) == 1 and minor["flange"].reference == "Table B4.1b Case 13"


def test_tee_wt7x45():
    from steel_design.sections import WT

    t = WT("WT7X45")
    comp = t.classify_compression()
    assert comp["stem"].ratio == pytest.approx(15.9)
    assert comp["stem"].limit_r == pytest.approx(0.75 * R50)  # 18.06
    assert comp["stem"].classification is Slenderness.NONSLENDER
    flex = t.classify_flexure()
    assert flex["stem"].limit_p == pytest.approx(0.84 * R50)  # 20.2
    assert flex["stem"].classification is Slenderness.COMPACT
    assert flex["flange"].classification is Slenderness.NONCOMPACT  # 10.2 vs 9.15


def test_angles():
    from steel_design.sections import Angle, DoubleAngle

    a = Angle("L6X4X1/2", material=A36)
    assert a.classify_compression()["leg"].ratio == pytest.approx(12)
    assert a.classify_compression()["leg"].limit_r == pytest.approx(0.45 * math.sqrt(29000 / 36))  # 12.77
    assert a.classify_compression().governing is Slenderness.NONSLENDER
    f = a.classify_flexure()["leg"]
    assert f.limit_p == pytest.approx(0.54 * math.sqrt(29000 / 36))  # 15.3
    assert f.classification is Slenderness.COMPACT
    thin = Angle("L8X8X1/2", material=A36)  # b/t = 16
    assert thin.classify_flexure()["leg"].classification is Slenderness.NONCOMPACT
    assert thin.classify_compression().governing is Slenderness.SLENDER
    assert DoubleAngle("2L6X4X1/2LLBB").classify_compression()["leg"].ratio == pytest.approx(12)


def test_every_database_shape_classifies():
    from steel_design.sections import SHAPE_CLASSES

    for cls in SHAPE_CLASSES.values():
        for label in cls.labels():
            s = cls(label)
            for axis in "xy":
                assert s.classify_flexure(axis).elements
            assert s.classify_compression().elements


def test_case_references_match_spec_tables():
    w = WideFlange("W14X90")
    assert w.classify_flexure()["flange"].reference == "Table B4.1b Case 10"
    assert w.classify_flexure("y")["flange"].reference == "Table B4.1b Case 13"
    assert w.classify_flexure()["web"].reference == "Table B4.1b Case 15"
    from steel_design.sections import WT, Angle

    assert WT("WT7X45").classify_flexure()["stem"].reference == "Table B4.1b Case 14"
    assert WT("WT7X45").classify_compression()["stem"].reference == "Table B4.1a Case 4"
    assert Angle("L6X4X1/2").classify_flexure()["leg"].reference == "Table B4.1b Case 12"
    assert Angle("L6X4X1/2").classify_compression()["leg"].reference == "Table B4.1a Case 3"


def _mono():
    return BuiltUpWideFlange(
        Q_(20, "in"), Q_(10, "in"), Q_(1, "in"), Q_(0.5, "in"),
        bf_bottom=Q_(6, "in"), tf_bottom=Q_(1, "in"), material=A992,
    )  # fmt: skip


def test_singly_symmetric_properties_hand_calc():
    s = _mono()
    assert not s.is_doubly_symmetric
    assert s.A.m == pytest.approx(25)
    assert s.y_bar.m == pytest.approx(11.52)
    assert s.Ix.m == pytest.approx(1630.5733, rel=1e-6)
    assert s.Sx_top.m == pytest.approx(1630.5733 / 8.48, rel=1e-6)
    assert s.Sx_bottom.m == pytest.approx(1630.5733 / 11.52, rel=1e-6)
    assert s.y_p.m == pytest.approx(14)
    assert s.Zx.m == pytest.approx(184.5)
    assert s.hc("top").m == pytest.approx(14.96)
    assert s.hp("top").m == pytest.approx(10)
    assert s.hc("bottom").m == pytest.approx(21.04)
    assert s.hp("bottom").m == pytest.approx(26)
    with pytest.raises(NotImplementedError):
        s.rts


def test_equal_flanges_reduce_to_doubly_symmetric():
    s = BuiltUpWideFlange(Q_(20, "in"), Q_(10, "in"), Q_(1, "in"), Q_(0.5, "in"))
    assert s.is_doubly_symmetric
    assert s.y_bar.m == pytest.approx(10)
    assert s.y_p.m == pytest.approx(10)
    assert s.Sx_top.m == pytest.approx(s.Sx_bottom.m)


def test_singly_symmetric_flexure_case16_web():
    s = _mono()
    flex = s.classify_flexure()  # top flange in compression
    mp_my = (184.5) / (1630.5733 / 11.52)
    lam_p = (14.96 / 10) * R50 / (0.54 * mp_my - 0.09) ** 2
    web = flex["web"]
    assert web.reference == "Table B4.1b Case 16"
    assert web.ratio == pytest.approx(14.96 / 0.5)
    assert web.limit_p == pytest.approx(lam_p)
    assert web.limit_r == pytest.approx(5.70 * R50)
    assert web.classification is Slenderness.COMPACT
    # FL = 0.7 Fy because Sxt/Sxc = 0.736 >= 0.7
    kc = 4 / math.sqrt(36)
    assert flex["flange"].limit_r == pytest.approx(0.95 * math.sqrt(kc * 580 / 0.7))
    assert flex["flange"].reference == "Table B4.1b Case 11"


def test_singly_symmetric_fl_reduced_when_sxt_over_sxc_small():
    s = BuiltUpWideFlange(
        Q_(30, "in"), Q_(16, "in"), Q_(1.5, "in"), Q_(0.5, "in"),
        bf_bottom=Q_(6, "in"), tf_bottom=Q_(0.5, "in"), material=A992,
    )  # fmt: skip
    ratio = s.Sx_bottom.m / s.Sx_top.m  # tension/compression with the big top flange in compression
    assert ratio < 0.7
    flex = s.classify_flexure(compression_flange="top")
    fl = max(ratio, 0.5)
    kc = 4 / math.sqrt(s.h_tw)
    assert flex["flange"].limit_r == pytest.approx(0.95 * math.sqrt(kc * 580 / fl))
    # flipping the section puts the small flange in compression, where Sxt/Sxc > 1 -> FL = 0.7 Fy
    flipped = s.classify_flexure(compression_flange="bottom")
    assert flipped["flange"].ratio == pytest.approx(s.bf_2tf_bottom)
    assert flipped["flange"].limit_r == pytest.approx(0.95 * math.sqrt(kc * 580 / 0.7))


def test_singly_symmetric_slender_web_uses_fl_07():
    s = BuiltUpWideFlange(
        Q_(60, "in"), Q_(16, "in"), Q_(1.5, "in"), Q_(0.25, "in"),
        bf_bottom=Q_(6, "in"), tf_bottom=Q_(0.5, "in"), material=A992,
    )  # fmt: skip
    # the large top flange pulls the centroid up, so the bottom flange in compression gives a slender hc/tw
    flex = s.classify_flexure(compression_flange="bottom")
    assert flex["web"].classification is Slenderness.SLENDER
    kc = max(4 / math.sqrt(s.h_tw), 0.35)
    assert flex["flange"].limit_r == pytest.approx(0.95 * math.sqrt(kc * 580 / 0.7))


def test_singly_symmetric_minor_axis_and_compression():
    s = _mono()
    minor = s.classify_flexure("y")
    assert set(e.element for e in minor.elements) == {"top flange", "bottom flange"}
    assert minor["top flange"].ratio == pytest.approx(5.0)
    assert minor["bottom flange"].ratio == pytest.approx(3.0)
    assert minor["top flange"].reference == "Table B4.1b Case 13"
    comp = s.classify_compression()
    assert comp["web"].reference == "Table B4.1a Case 8"
    assert comp["top flange"].limit_r == pytest.approx(0.64 * math.sqrt(4 / math.sqrt(36)) * R50)
    with pytest.raises(ValueError):
        s.classify_flexure(compression_flange="left")


def test_double_angle_continuous_contact_flag():
    from steel_design.sections import DoubleAngle

    sep = DoubleAngle("2L6X4X1/2LLBB", material=A36)
    cont = DoubleAngle("2L6X4X1/2LLBB", material=A36, continuous_contact=True)
    r36 = math.sqrt(29000 / 36)
    assert sep.classify_compression()["leg"].limit_r == pytest.approx(0.45 * r36)
    assert sep.classify_compression()["leg"].reference == "Table B4.1a Case 3"
    assert cont.classify_compression()["leg"].limit_r == pytest.approx(0.56 * r36)
    assert cont.classify_compression()["leg"].reference == "Table B4.1a Case 1"
    # b/t = 14.2: slender with separators (limit 12.8), nonslender in continuous contact (limit 15.9)
    sep14 = DoubleAngle("2L8X6X9/16LLBB", material=A36)
    cont14 = DoubleAngle("2L8X6X9/16LLBB", material=A36, continuous_contact=True)
    assert sep14.classify_compression().governing is Slenderness.SLENDER
    assert cont14.classify_compression().governing is Slenderness.NONSLENDER
    assert get_shape("2L6X4X1/2LLBB", continuous_contact=True).continuous_contact is True
    assert get_shape("2L6X4X1/2LLBB").continuous_contact is False


def test_slenderness_properties_match_methods():
    w = WideFlange("W14X90")
    assert w.compression_slenderness == w.classify_compression()
    assert w.flexure_slenderness_x == w.classify_flexure("x")
    assert w.flexure_slenderness_y == w.classify_flexure("y")
    assert w.flexure_slenderness_x["flange"].classification is Slenderness.NONCOMPACT
    assert w.flexure_slenderness_y.governing is Slenderness.NONCOMPACT


def test_slenderness_properties_on_every_section_type():
    from steel_design.sections import SHAPE_CLASSES

    for cls in SHAPE_CLASSES.values():
        s = cls(cls.labels()[0])
        assert s.compression_slenderness.elements
        assert s.flexure_slenderness_x.elements
        assert s.flexure_slenderness_y.elements
    box = BuiltUpBox(Q_(12, "in"), Q_(10, "in"), Q_(0.5, "in"), Q_(0.5, "in"))
    assert box.flexure_slenderness_x.elements and box.compression_slenderness.elements


def test_singly_symmetric_bottom_compression_property():
    s = BuiltUpWideFlange(
        Q_(24, "in"), Q_(10, "in"), Q_(1, "in"), Q_(0.5, "in"), bf_bottom=Q_(14, "in"), tf_bottom=Q_(1.25, "in")
    )
    assert s.flexure_slenderness_x == s.classify_flexure("x", compression_flange="top")
    assert s.flexure_slenderness_x_bottom == s.classify_flexure("x", compression_flange="bottom")


def test_changing_material_changes_slenderness():
    w = WideFlange("W14X90")
    assert w.flexure_slenderness_x["flange"].classification is Slenderness.NONCOMPACT
    w.material = A36
    assert w.flexure_slenderness_x["flange"].classification is Slenderness.COMPACT
