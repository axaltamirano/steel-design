import pytest

from steel_design import Q_
from steel_design.materials import (
    A36,
    A572Gr50,
    A992,
    ALL_MATERIALS,
    SteelMaterial,
    default_material_for,
    get_material,
)
from steel_design.sections import BuiltUpBox, BuiltUpWideFlange, get_shape, list_shapes


def test_material_constants_and_grade_values():
    assert A992.E.to("ksi").m == 29000
    assert (A992.Fy.m, A992.Fu.m) == (50, 65)
    assert (A36.Fy.m, A36.Fu.m) == (36, 58)
    assert all(issubclass(m, SteelMaterial) for m in ALL_MATERIALS)
    assert len({m.name for m in ALL_MATERIALS}) == len(ALL_MATERIALS)


def test_registry_aliases():
    assert get_material("a572 gr. 50") is A572Gr50
    assert get_material("A572Gr50") is A572Gr50
    with pytest.raises(KeyError):
        get_material("A1")


def test_default_materials():
    assert default_material_for("W") is A992
    assert default_material_for("hss_rect").name == "A500 Gr. C (rect)"
    assert default_material_for("PIPE").name == "A53 Gr. B"


def test_database_shape_w14x90():
    s = get_shape("w14x90")
    assert s.material is A992
    assert s.A.to("in**2").m == pytest.approx(26.5)
    assert s.Ix.m == pytest.approx(999)
    assert s.h_tw == pytest.approx(25.9)
    assert s.weight.to("lbf/ft").m == 90
    assert get_shape("W14X90", material=A36).material is A36
    with pytest.raises(KeyError):
        get_shape("W99X999")


def test_database_counts_and_hss_split():
    assert len(list_shapes("W")) == 289
    assert get_shape("HSS8X8X1/2").family == "HSS_RECT"
    assert get_shape("HSS10.000X0.500").family == "HSS_ROUND"
    assert get_shape("L4X4X1/2").tan_alpha is not None


def test_family_classes():
    from steel_design.sections import HSSRect, HSSRound, Angle, SHAPE_CLASSES, WideFlange, WT, DoubleAngle, Pipe

    assert len(SHAPE_CLASSES) == 14
    w = WideFlange("W14X90")
    assert isinstance(w, WideFlange) and isinstance(get_shape("W14X90"), WideFlange)
    assert isinstance(get_shape("HSS8X8X1/2"), HSSRect)
    assert isinstance(get_shape("HSS10.000X0.500"), HSSRound)
    assert w.material is A992 and WT("WT7X45").material is A992
    assert WideFlange("W14X90", material=A36).material is A36
    assert len(WideFlange.labels()) == 289 and "Ix" in WideFlange.properties()
    assert Angle.family == "L" and DoubleAngle.family == "2L" and Pipe.family == "PIPE"
    with pytest.raises(KeyError):
        WideFlange("WT7X45")
    with pytest.raises(TypeError):
        from steel_design.sections import DatabaseShape

        DatabaseShape("W14X90")


def test_built_up_wide_flange_hand_calc():
    s = BuiltUpWideFlange(Q_(20, "in"), Q_(10, "in"), Q_(1, "in"), Q_(0.5, "in"))
    assert s.material is A572Gr50
    assert s.A.m == pytest.approx(29)
    assert s.Ix.m == pytest.approx((10 * 20**3 - 9.5 * 18**3) / 12)
    assert s.Zx.m == pytest.approx(230.5)
    assert s.ho.m == 19
    assert s.Cw.m == pytest.approx(s.Iy.m * 19**2 / 4)


def test_built_up_wide_flange_matches_rolled_shape():
    rolled = get_shape("W14X90")
    bu = BuiltUpWideFlange(rolled.d, rolled.bf, rolled.tf, rolled.tw, material=A992)
    assert bu.Ix.m == pytest.approx(rolled.Ix.m, rel=0.04)  # rolled shapes have fillets
    assert bu.Zx.m == pytest.approx(rolled.Zx.m, rel=0.04)


def test_built_up_box_hand_calc():
    s = BuiltUpBox(Q_(12, "in"), Q_(10, "in"), Q_(0.5, "in"), Q_(0.5, "in"))
    assert s.A.m == pytest.approx(21)
    assert s.Ix.m == pytest.approx(441.75)
    assert s.Zx.m == pytest.approx((10 * 144 - 9 * 121) / 4)
    assert s.Cw.m == 0
    ab = 9.5 * 11.5
    assert s.J.m == pytest.approx(4 * ab**2 / (2 * 9.5 / 0.5 + 2 * 11.5 / 0.5))
    assert s.C.m == pytest.approx(2 * ab * 0.5)


def test_units_are_enforced():
    with pytest.raises(TypeError):
        BuiltUpBox(12, 10, 0.5, 0.5)
    with pytest.raises(ValueError):
        BuiltUpWideFlange(Q_(1, "ksi"), Q_(10, "in"), Q_(1, "in"), Q_(0.5, "in"))
    # mixed length units are converted
    s = BuiltUpWideFlange(Q_(1, "ft"), Q_(10, "in"), Q_(0.5, "in"), Q_(0.25, "in"))
    assert s.d.m == 12


def test_declared_properties_match_database_columns():
    import typing

    from steel_design.sections import SHAPE_CLASSES

    for fam, cls in SHAPE_CLASSES.items():
        declared = {k for c in cls.__mro__ for k in typing.get_type_hints(c, include_extras=False) if not k.startswith("_")}
        declared -= {"name", "family", "material"}
        assert declared == set(cls.properties()), (fam, declared ^ set(cls.properties()))


def _box(inset=None):
    i = lambda x: Q_(x, "in")
    return BuiltUpBox(i(12), i(10), i(0.5), i(0.375), inset_web_PL=None if inset is None else i(inset))


def test_box_inset_zero_matches_default():
    flush = _box()
    zero = _box(0)
    for prop in ("A", "Ix", "Iy", "Zx", "Zy", "J", "b"):
        assert getattr(zero, prop) == getattr(flush, prop)
    assert flush.Iy.m == pytest.approx((12 * 10**3 - 11 * 9.25**3) / 12)


def test_box_inset_section_properties():
    box = _box(1)
    h, tw, tf, B, Ht = 11.0, 0.375, 0.5, 10.0, 12.0
    offset = (B - 2 - tw) / 2
    assert box.b.m == pytest.approx(B - 2 - 2 * tw)
    assert box.A.m == pytest.approx(2 * B * tf + 2 * h * tw)
    assert box.Ix.m == pytest.approx(414.0208333)
    assert box.Iy.m == pytest.approx(2 * tf * B**3 / 12 + 2 * (h * tw**3 / 12 + h * tw * offset**2))
    assert box.Zx.m == pytest.approx(80.1875)
    assert box.Zy.m == pytest.approx(tf * B**2 / 2 + tw * h * 2 * offset)
    assert box.Sy.m == pytest.approx(2 * box.Iy.m / B)
    # Bredt closed cell plus four open overhangs
    ab = 2 * offset * (Ht - tf)
    closed = 4 * ab**2 / (2 * 2 * offset / tf + 2 * (Ht - tf) / tw)
    assert box.J.m == pytest.approx(closed + 4 * 1 * tf**3 / 3)
    assert box.Iy < _box().Iy


def test_box_inset_adds_overhang_element():
    box = _box(1)
    overhang = box.compression_slenderness["flange overhang"]
    assert overhang.ratio == pytest.approx(2.0)
    assert [e.name for e in box.slender_elements()][-1] == "flange overhang"
    assert "flange overhang" not in [e.element for e in _box().compression_slenderness.elements]


def test_box_inset_validation_and_flexure():
    with pytest.raises(ValueError):
        _box(-1)
    with pytest.raises(ValueError):
        _box(4.7)
    with pytest.raises(NotImplementedError):
        _box(1).flexure_strength("x", Lb=Q_(10, "ft"))
