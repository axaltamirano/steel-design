import pytest

from steel_design import Q_
from steel_design.materials import A36, A992
from steel_design.sections import Angle, BuiltUpBox, BuiltUpWideFlange, HSSRound, WideFlange
from steel_design.tension import (
    effective_net_area,
    exceeds_recommended_slenderness,
    tension_strength,
)


def test_w14x90_gross_yielding_hand_calc():
    t = WideFlange("W14X90").tension_strength()
    assert t.yielding.Pn.m == pytest.approx(50 * 26.5)
    assert t.yielding.design_strength.m == pytest.approx(0.9 * 50 * 26.5)
    assert t.yielding.allowable_strength.m == pytest.approx(50 * 26.5 / 1.67)
    assert t.yielding.reference == "Eq. D2-1"


def test_rupture_with_net_area_and_shear_lag():
    t = WideFlange("W14X90").tension_strength(An=Q_(22.0, "in**2"), U=0.9)
    assert t.Ae.m == pytest.approx(19.8)
    assert t.rupture.Pn.m == pytest.approx(65 * 19.8)
    assert t.rupture.design_strength.m == pytest.approx(0.75 * 65 * 19.8)
    assert t.rupture.allowable_strength.m == pytest.approx(65 * 19.8 / 2.0)
    assert t.governing_lrfd is t.rupture and t.governing_asd is t.rupture
    assert t.design_strength == t.rupture.design_strength


def test_defaults_are_no_holes_and_full_shear_lag():
    t = WideFlange("W14X90").tension_strength()
    assert t.An == t.Ag and t.U == 1.0 and t.Ae == t.Ag
    # With Ae = Ag, yielding governs LRFD (0.9*50 < 0.75*65 is false: 45 < 48.75)
    assert t.governing_lrfd is t.yielding


def test_material_changes_strength():
    assert WideFlange("W14X90", material=A36).tension_strength().yielding.Pn.m == pytest.approx(36 * 26.5)
    w = WideFlange("W14X90", material=A992)
    assert w.tension_strength().rupture.Pn.m == pytest.approx(65 * 26.5)


def test_unit_conversion_of_areas():
    a = tension_strength(Q_(26.5, "in**2"), Q_(50, "ksi"), Q_(65, "ksi"), An=Q_(26.5 * 144, "in**2") / 144)
    b = tension_strength(Q_(26.5 / 144, "ft**2"), Q_(50, "ksi"), Q_(65, "ksi"))
    assert a.yielding.Pn.m == pytest.approx(b.yielding.Pn.m)


def test_input_validation():
    w = WideFlange("W14X90")
    with pytest.raises(TypeError):
        w.tension_strength(An=22.0)
    with pytest.raises(ValueError):
        w.tension_strength(An=Q_(22, "in"))
    with pytest.raises(ValueError):
        w.tension_strength(An=Q_(30, "in**2"))
    for u in (0, -0.1, 1.01):
        with pytest.raises(ValueError):
            w.tension_strength(U=u)
    with pytest.raises(ValueError):
        effective_net_area(Q_(10, "in**2"), 0)


def test_works_for_every_section_type():
    for s in (
        Angle("L4X4X1/2"),
        HSSRound("HSS6.000X0.250"),
        BuiltUpWideFlange(Q_(24, "in"), Q_(10, "in"), Q_(1, "in"), Q_(0.5, "in")),
        BuiltUpBox(Q_(12, "in"), Q_(10, "in"), Q_(0.5, "in"), Q_(0.5, "in")),
    ):
        t = s.tension_strength()
        assert t.yielding.Pn.m == pytest.approx(s.material.Fy.m * s.A.m)


def test_slenderness_ratio_uses_least_radius():
    w = WideFlange("W14X90")
    assert w.tension_slenderness_ratio(Q_(20, "ft")) == pytest.approx(240 / w.ry.m)
    angle = Angle("L4X4X1/2")
    assert angle.tension_slenderness_ratio(Q_(10, "ft")) == pytest.approx(120 / angle.rz.m)
    box = BuiltUpBox(Q_(12, "in"), Q_(10, "in"), Q_(0.5, "in"), Q_(0.5, "in"))
    assert box.tension_slenderness_ratio(Q_(10, "ft")) == pytest.approx(120 / min(box.rx.m, box.ry.m))
    assert exceeds_recommended_slenderness(Q_(30, "ft"), Q_(1, "in"))
    assert not exceeds_recommended_slenderness(Q_(25, "ft"), Q_(1, "in"))
