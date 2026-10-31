import math

import pytest

from steel_design import Q_
from steel_design.classification import ElementClassification, Slenderness
from steel_design.flexure import (
    cb,
    effective_section_modulus,
    round_hss_strength,
)
from steel_design.materials import A36, A992, A572Gr50
from steel_design.resistance_factors import ResistanceFactors
from steel_design.sections import (
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
    MT,
    Pipe,
    SShape,
    ST,
    WideFlange,
    get_shape,
)

E = 29000.0
FY = 50.0


def ft(x):
    return Q_(x, "ft")


def inch(x):
    return Q_(x, "in")


def state(strength, name):
    return next(ls for ls in strength.limit_states if ls.name == name)


def mn(strength, name):
    """Nominal strength of a limit state in kip-in."""
    return state(strength, name).Mn.to("kip*in").m


# --- F1 -----------------------------------------------------------------------------


def test_cb_uniform_moment_and_uniform_load():
    assert cb(1, 1, 1, 1) == pytest.approx(1.0)
    assert cb(1, 0.75, 1, 0.75) == pytest.approx(12.5 / (2.5 + 2.25 + 4 + 2.25))
    assert cb(Q_(100, "kip*ft"), Q_(-75, "kip*ft"), Q_(100, "kip*ft"), 75) == pytest.approx(1.136, abs=1e-3)


def test_cb_requires_a_nonzero_moment():
    with pytest.raises(ValueError):
        cb(0, 0, 0, 0)


# --- F2, F3: W shapes, major axis ---------------------------------------------------


@pytest.fixture(scope="module")
def w21x48():
    return WideFlange("W21X48")


def hand_f2_f3(w, Lb_in, Cb=1.0):
    """Independent F2/F3 calculation for a compact-web W shape, in kip-in."""
    Zx, Sx, ry, rts = w.Zx.m, w.Sx.m, w.ry.m, w.rts.m
    J, ho, lam = w.J.m, w.ho.m, w.bf_2tf
    Mp = FY * Zx
    Lp = 1.76 * ry * math.sqrt(E / FY)
    t = J / (Sx * ho)
    Lr = 1.95 * rts * E / (0.7 * FY) * math.sqrt(t + math.sqrt(t**2 + 6.76 * (0.7 * FY / E) ** 2))
    if Lb_in <= Lp:
        ltb = Mp
    elif Lb_in <= Lr:
        ltb = min(Mp, Cb * (Mp - (Mp - 0.7 * FY * Sx) * (Lb_in - Lp) / (Lr - Lp)))
    else:
        fcr = Cb * math.pi**2 * E / (Lb_in / rts) ** 2 * math.sqrt(1 + 0.078 * t * (Lb_in / rts) ** 2)
        ltb = min(fcr * Sx, Mp)
    lp_f, lr_f = 0.38 * math.sqrt(E / FY), 1.0 * math.sqrt(E / FY)
    flb = Mp if lam <= lp_f else Mp - (Mp - 0.7 * FY * Sx) * (lam - lp_f) / (lr_f - lp_f)
    return Mp, ltb, flb, Lp, Lr


@pytest.mark.parametrize("Lb_ft", [4, 8, 14, 30])
def test_w21x48_matches_hand_calculation(w21x48, Lb_ft):
    s = w21x48.flexure_strength("x", ft(Lb_ft))
    Mp, ltb, flb, Lp, Lr = hand_f2_f3(w21x48, Lb_ft * 12)
    assert w21x48.flexure_slenderness_x["flange"].classification is Slenderness.NONCOMPACT
    assert mn(s, "yielding") == pytest.approx(Mp)
    assert mn(s, "compression flange local buckling") == pytest.approx(flb)
    if Lb_ft * 12 > Lp:
        assert mn(s, "lateral-torsional buckling") == pytest.approx(ltb)
    else:
        assert all(ls.name != "lateral-torsional buckling" for ls in s.limit_states)
    assert s.Lp.to("in").m == pytest.approx(Lp)
    assert s.Lr.to("in").m == pytest.approx(Lr)
    assert s.design_strength.to("kip*in").m == pytest.approx(0.9 * min(Mp, ltb, flb))


def test_w21x48_covers_all_three_ltb_ranges(w21x48):
    _, _, _, Lp, Lr = hand_f2_f3(w21x48, 0)
    refs = {
        lb: state(w21x48.flexure_strength("x", inch(lb)), "lateral-torsional buckling").reference
        for lb in (0.5 * (Lp + Lr), 1.5 * Lr)
    }
    assert list(refs.values()) == ["Eq. F2-2", "Eq. F2-3, F2-4"]


def test_cb_scales_inelastic_ltb_and_is_capped_at_mp(w21x48):
    base = w21x48.flexure_strength("x", ft(12), Cb=1.0)
    raised = w21x48.flexure_strength("x", ft(12), Cb=1.14)
    assert mn(raised, "lateral-torsional buckling") == pytest.approx(
        min(mn(raised, "yielding"), 1.14 * mn(base, "lateral-torsional buckling"))
    )
    assert raised.Cb == 1.14
    far = w21x48.flexure_strength("x", ft(12), Cb=3.0)
    assert mn(far, "lateral-torsional buckling") == pytest.approx(mn(far, "yielding"))


def test_w14x90_known_design_strength():
    # The flange is noncompact for Fy = 50 ksi; at Lb <= Lp the flange local buckling governs.
    w = WideFlange("W14X90")
    assert w.get_phiMnx(ft(8)).m == pytest.approx(573.8, abs=0.2)
    assert w.get_Mnx(ft(8)).m == pytest.approx(573.8 / 0.9, abs=0.2)
    s = w.flexure_strength("x", ft(8))
    assert s.Lp.to("ft").m == pytest.approx(13.07, abs=0.01)
    assert s.Lr.to("ft").m == pytest.approx(42.5, abs=0.1)


def test_design_strength_applies_phi_b():
    w = WideFlange("W18X35")
    s = w.flexure_strength("x", ft(10))
    assert s.governing.phi == ResistanceFactors.FLEXURE == 0.90
    assert w.get_phiMnx(ft(10)).m == pytest.approx(0.9 * w.get_Mnx(ft(10)).m)


# --- F3: slender flange ----------------------------------------------------------------


def test_slender_flange_f3_2_equation():
    # A built-up doubly symmetric I with a slender flange and compact web uses F3-2 with kc.
    s = BuiltUpWideFlange(inch(24), inch(14), inch(0.25), inch(0.5), A992)
    c = s.flexure_slenderness_x
    assert c["flange"].classification is Slenderness.SLENDER
    assert c["web"].classification is Slenderness.COMPACT
    r = s.flexure_strength("x", ft(6))
    kc = min(max(4 / math.sqrt(s.h_tw), 0.35), 0.76)
    assert mn(r, "compression flange local buckling") == pytest.approx(
        0.9 * E * kc * s.Sx.m / c["flange"].ratio ** 2
    )
    assert r.governing.name == "compression flange local buckling"


# --- F2: channels -------------------------------------------------------------------


@pytest.mark.parametrize("cls,label", [(Channel, "C12X30"), (MChannel, "MC12X31")])
def test_channel_f2_uses_c_factor(cls, label):
    ch = cls(label, A36)
    Fy = 36.0
    c = (ch.ho.m / 2) * math.sqrt(ch.Iy.m / ch.Cw.m)
    t = ch.J.m * c / (ch.Sx.m * ch.ho.m)
    Lp = 1.76 * ch.ry.m * math.sqrt(E / Fy)
    Lr = 1.95 * ch.rts.m * E / (0.7 * Fy) * math.sqrt(t + math.sqrt(t**2 + 6.76 * (0.7 * Fy / E) ** 2))
    s = ch.flexure_strength("x", ft(8))
    Mp = Fy * ch.Zx.m
    Lb = 96
    assert Lp < Lb < Lr
    assert mn(s, "yielding") == pytest.approx(Mp)
    assert mn(s, "lateral-torsional buckling") == pytest.approx(
        min(Mp, Mp - (Mp - 0.7 * Fy * ch.Sx.m) * (Lb - Lp) / (Lr - Lp))
    )
    assert s.Lp.to("in").m == pytest.approx(Lp)
    assert s.Lr.to("in").m == pytest.approx(Lr)


def test_channel_with_noncompact_element_is_not_covered():
    ch = Channel("C12X30", A36)
    flexure = type(ch).classify_flexure

    def noncompact(self, axis="x"):
        c = flexure(self, axis)
        flange = c["flange"]
        bad = ElementClassification(
            "flange", flange.ratio, flange.limit_p, flange.limit_r, Slenderness.NONCOMPACT, flange.reference
        )
        return type(c)((bad, c["web"]))

    class Weak(type(ch)):
        classify_flexure = noncompact

    weak = Weak("C12X30", A36)
    with pytest.raises(NotImplementedError, match="F12"):
        weak.flexure_strength("x", ft(8))


# --- F6: minor axis -----------------------------------------------------------------


def test_minor_axis_w_shape_noncompact_flange():
    w = WideFlange("W14X90")
    s = w.flexure_strength("y")
    Mp = min(FY * w.Zy.m, 1.6 * FY * w.Sy.m)
    lam = w.bf_2tf
    lp, lr = 0.38 * math.sqrt(E / FY), math.sqrt(E / FY)
    assert mn(s, "yielding") == pytest.approx(Mp)
    assert lam > lp  # W14X90 has a noncompact flange
    assert mn(s, "flange local buckling") == pytest.approx(Mp - (Mp - 0.7 * FY * w.Sy.m) * (lam - lp) / (lr - lp))
    assert w.get_phiMny().m == pytest.approx(0.9 * s.governing.Mn.m)


def test_minor_axis_compact_flange_is_capped_at_1_6_my():
    w = WideFlange("W12X50")
    s = w.flexure_strength("y")
    assert mn(s, "yielding") == pytest.approx(min(FY * w.Zy.m, 1.6 * FY * w.Sy.m))
    assert len(s.limit_states) == 1


def test_minor_axis_slender_flange_uses_f6_4():
    s = BuiltUpWideFlange(inch(24), inch(14), inch(0.25), inch(0.5), A992)
    r = s.flexure_strength("y")
    lam = s.flexure_slenderness_y["flange"].ratio
    assert mn(r, "flange local buckling") == pytest.approx(0.69 * E / lam**2 * s.Sy.m)


def test_channel_minor_axis_uses_full_flange_width_ratio():
    ch = Channel("C12X30", A36)
    s = ch.flexure_strength("y")
    assert s.limit_states[0].name == "yielding"
    assert ch.flexure_slenderness_y["flange"].ratio == pytest.approx(ch.b_t)


# --- F4, F5: built-up I-shapes ------------------------------------------------------


def test_singly_symmetric_i_matches_f4_hand_calculation():
    s = BuiltUpWideFlange(inch(30), inch(12), inch(1), inch(0.375), A992, bf_bottom=inch(8), tf_bottom=inch(0.5))
    for cf in ("top", "bottom"):
        r = s.flexure_strength("x", ft(10), compression_flange=cf)
        sxc, sxt = (s.Sx_top.m, s.Sx_bottom.m) if cf == "top" else (s.Sx_bottom.m, s.Sx_top.m)
        bfc, tfc = (12.0, 1.0) if cf == "top" else (8.0, 0.5)
        hc = s.hc(cf).m
        tw = 0.375
        Myc = FY * sxc
        Mp = min(FY * s.Zx.m, 1.6 * Myc)
        web = s.classify_flexure("x", cf)["web"]
        Iyc = tfc * bfc**3 / 12
        mp_myc = Mp / Myc
        if Iyc / s.Iy.m <= 0.23:
            Rpc = 1.0
        elif web.ratio <= web.limit_p:
            Rpc = mp_myc
        else:
            Rpc = min(mp_myc, mp_myc - (mp_myc - 1) * (web.ratio - web.limit_p) / (web.limit_r - web.limit_p))
        assert mn(r, "compression flange yielding") == pytest.approx(Rpc * Myc)
        aw = hc * tw / (bfc * tfc)
        rt = bfc / math.sqrt(12 * (1 + aw / 6))
        FL = 0.7 * FY if sxt / sxc >= 0.7 else max(FY * sxt / sxc, 0.5 * FY)
        Lp = 1.1 * rt * math.sqrt(E / FY)
        t = s.J.m / (sxc * s.ho.m)
        Lr = 1.95 * rt * E / FL * math.sqrt(t + math.sqrt(t**2 + 6.76 * (FL / E) ** 2))
        Lb = 120.0
        assert r.Lp.to("in").m == pytest.approx(Lp)
        assert r.Lr.to("in").m == pytest.approx(Lr)
        assert Lp < Lb <= Lr
        assert mn(r, "lateral-torsional buckling") == pytest.approx(
            min(Rpc * Myc, Rpc * Myc - (Rpc * Myc - FL * sxc) * (Lb - Lp) / (Lr - Lp))
        )
    top = s.flexure_strength("x", ft(10), compression_flange="top")
    bottom = s.flexure_strength("x", ft(10), compression_flange="bottom")
    assert any(ls.name == "tension flange yielding" for ls in top.limit_states)
    assert all(ls.name != "tension flange yielding" for ls in bottom.limit_states)
    assert bottom.design_strength < top.design_strength


def test_slender_web_f5_hand_calculation():
    s = BuiltUpWideFlange(inch(60), inch(12), inch(1), inch(0.375), A992)
    c = s.flexure_slenderness_x
    assert c["web"].classification is Slenderness.SLENDER
    r = s.flexure_strength("x", ft(10))
    hc, tw = s.h.m, 0.375
    aw = hc * tw / (12 * 1.0)
    rt = 12 / math.sqrt(12 * (1 + aw / 6))
    Rpg = 1 - aw / (1200 + 300 * aw) * (hc / tw - 5.7 * math.sqrt(E / FY))
    Lp = 1.1 * rt * math.sqrt(E / FY)
    Lr = math.pi * rt * math.sqrt(E / (0.7 * FY))
    Lb = 120.0
    assert Lp < Lb < Lr
    assert mn(r, "compression flange yielding") == pytest.approx(Rpg * FY * s.Sx.m)
    fcr = FY - 0.3 * FY * (Lb - Lp) / (Lr - Lp)
    assert mn(r, "lateral-torsional buckling") == pytest.approx(Rpg * fcr * s.Sx.m)
    assert 0 < Rpg < 1


def test_slender_web_beyond_lr_uses_elastic_fcr():
    s = BuiltUpWideFlange(inch(60), inch(12), inch(1), inch(0.375), A992)
    r = s.flexure_strength("x", ft(60), Cb=1.0)
    aw = s.h.m * 0.375 / 12
    rt = 12 / math.sqrt(12 * (1 + aw / 6))
    Rpg = 1 - aw / (1200 + 300 * aw) * (s.h.m / 0.375 - 5.7 * math.sqrt(E / FY))
    fcr = min(FY, math.pi**2 * E / (720 / rt) ** 2)
    assert mn(r, "lateral-torsional buckling") == pytest.approx(Rpg * fcr * s.Sx.m)


def test_noncompact_web_doubly_symmetric_uses_f4():
    s = BuiltUpWideFlange(inch(48), inch(16), inch(1), inch(0.4), A992)
    c = s.flexure_slenderness_x
    assert c["web"].classification is Slenderness.NONCOMPACT
    r = s.flexure_strength("x", ft(10))
    myc = FY * s.Sx.m
    lam, lpw, lrw = c["web"].ratio, c["web"].limit_p, c["web"].limit_r
    mp = min(FY * s.Zx.m, 1.6 * myc)
    rpc = mp / myc - (mp / myc - 1) * (lam - lpw) / (lrw - lpw)
    assert state(r, "compression flange yielding").reference == "Eq. F4-1"
    assert mn(r, "compression flange yielding") == pytest.approx(rpc * myc)
    assert all(ls.name != "tension flange yielding" for ls in r.limit_states)


def test_f4_low_compression_flange_inertia_gives_rpc_one():
    s = BuiltUpWideFlange(inch(30), inch(4), inch(1), inch(0.375), A992, bf_bottom=inch(14), tf_bottom=inch(1))
    # Iyc/Iy of the 4 in flange is well below 0.23, so Rpc = 1.0 and the yield strength is Myc.
    r = s.flexure_strength("x", ft(6), compression_flange="top")
    assert mn(r, "compression flange yielding") == pytest.approx(FY * s.Sx_top.m)


def test_built_up_i_doubly_symmetric_compact_matches_f2():
    s = BuiltUpWideFlange(inch(24), inch(10), inch(0.75), inch(0.375), A992)
    assert s.flexure_slenderness_x.governing is Slenderness.COMPACT
    r = s.flexure_strength("x", ft(10))
    assert mn(r, "yielding") == pytest.approx(FY * s.Zx.m)
    assert state(r, "lateral-torsional buckling").reference in ("Eq. F2-2", "Eq. F2-3, F2-4")


def test_singly_symmetric_minor_axis_checks_both_flanges():
    s = BuiltUpWideFlange(inch(30), inch(24), inch(0.5), inch(0.375), A992, bf_bottom=inch(8), tf_bottom=inch(0.5))
    r = s.flexure_strength("y")
    names = [ls.name for ls in r.limit_states]
    assert "flange local buckling (top flange)" in names
    assert "flange local buckling (bottom flange)" not in names


# --- F7: rectangular HSS and box ----------------------------------------------------


def test_hss_rect_noncompact_flange_minor_axis():
    h = HSSRect("HSS8X4X1/4", A992)
    c = h.flexure_slenderness_y
    assert c["flange"].classification is Slenderness.NONCOMPACT
    r = h.flexure_strength("y")
    Mp = FY * h.Zy.m
    flange = c["flange"]
    assert mn(r, "flange local buckling") == pytest.approx(
        Mp - (Mp - FY * h.Sy.m) * (flange.ratio - flange.limit_p) / (flange.limit_r - flange.limit_p)
    )
    assert all(ls.name != "lateral-torsional buckling" for ls in r.limit_states)


def test_hss_rect_ltb_major_axis():
    h = HSSRect("HSS20X4X1/4", A992)
    Mp = FY * h.Zx.m
    root = E * h.ry.m * math.sqrt(h.J.m * h.A.m)
    Lp, Lr = 0.13 * root / Mp, 2 * root / (0.7 * FY * h.Sx.m)
    mid = 0.5 * (Lp + Lr)
    r = h.flexure_strength("x", inch(mid))
    assert mn(r, "lateral-torsional buckling") == pytest.approx(
        min(Mp, Mp - (Mp - 0.7 * FY * h.Sx.m) * (mid - Lp) / (Lr - Lp))
    )
    far = 2 * Lr
    r = h.flexure_strength("x", inch(far))
    assert mn(r, "lateral-torsional buckling") == pytest.approx(min(Mp, 2 * root / far))
    assert r.Lp.to("in").m == pytest.approx(Lp)
    assert r.Lr.to("in").m == pytest.approx(Lr)


def test_hss_rect_square_has_no_ltb_and_needs_no_lb():
    h = HSSRect("HSS8X8X1/2", A992)
    s = h.flexure_strength("x")
    assert all(ls.name != "lateral-torsional buckling" for ls in s.limit_states)
    assert h.get_phiMnx() > 0


def test_hss_rect_non_square_requires_lb_for_major_axis():
    with pytest.raises(ValueError, match="Lb"):
        HSSRect("HSS8X4X1/4").flexure_strength("x")


def test_box_slender_flange_effective_width_f7_5():
    b = BuiltUpBox(inch(24), inch(12), inch(0.375), inch(0.25), A992)
    c = b.flexure_slenderness_y
    assert c["flange"].classification is Slenderness.SLENDER
    r = b.flexure_strength("y")
    lam, t = c["flange"].ratio, 0.25
    flat = lam * t
    be = 1.92 * t * math.sqrt(E / FY) * (1 - 0.34 / lam * math.sqrt(E / FY))
    assert be < flat
    # Plate-by-plate section about the new centroid; the compression wall is the left plate.
    plates = [  # (area, own inertia about the vertical axis, x of centroid)
        (be * t, 0.0, t / 2),
        (flat * t, 0.0, 12 - t / 2),
        (12 * 0.375, 0.375 * 12**3 / 12, 6.0),
        (12 * 0.375, 0.375 * 12**3 / 12, 6.0),
    ]
    area = sum(a for a, _, _ in plates)
    xbar = sum(a * x for a, _, x in plates) / area
    inertia = sum(i + a * (x - xbar) ** 2 for a, i, x in plates)
    assert mn(r, "flange local buckling") == pytest.approx(FY * inertia / xbar, rel=0.002)
    assert state(r, "flange local buckling").reference == "Eq. F7-3, F7-4"


def test_effective_section_modulus_closed_form_matches_direct_computation():
    # Rectangular tube 12 deep by 8 wide, t = 0.25 (no corner radius), top flange reduced.
    H, B, t = 12.0, 8.0, 0.25
    a_flange, a_webs, a_bot = (B - 2 * t) * t, 2 * H * t, B * t
    top_y = H - t / 2
    area = (B * t) + a_webs + a_bot
    ybar = (B * t * top_y + a_webs * H / 2 + B * t * t / 2) / area
    inertia = (
        B * t**3 / 12 + B * t * (top_y - ybar) ** 2
        + 2 * t * H**3 / 12 + a_webs * (H / 2 - ybar) ** 2
        + B * t**3 / 12 + B * t * (t / 2 - ybar) ** 2
    )
    be = 5.0
    flat = B - 2 * t
    removed = (flat - be) * t
    # direct: remove the ineffective strip and recompute about the new centroid
    parts = [(B * t - removed, top_y), (a_webs, H / 2), (a_bot, t / 2)]
    new_area = sum(a for a, _ in parts)
    new_ybar = sum(a * y for a, y in parts) / new_area
    new_i = (
        (B * t**3 / 12 - 0) + (B * t - removed) * (top_y - new_ybar) ** 2
        + 2 * t * H**3 / 12 + a_webs * (H / 2 - new_ybar) ** 2
        + B * t**3 / 12 + a_bot * (t / 2 - new_ybar) ** 2
    )
    # the first term above uses the full flange's own inertia, which differs negligibly
    expected = new_i / (H - new_ybar)
    got = effective_section_modulus(
        Q_(inertia, "in**4"), Q_(area, "in**2"), inch(H), inch(t), inch(flat), inch(be)
    )
    assert got.to("in**3").m == pytest.approx(expected, rel=0.01)
    assert a_flange > removed


def test_box_slender_web_uses_rpg():
    b = BuiltUpBox(inch(60), inch(16), inch(1), inch(0.25), A992)
    c = b.flexure_slenderness_x
    assert c["web"].classification is Slenderness.SLENDER
    r = b.flexure_strength("x", ft(20))
    hw = c["web"].ratio
    bflat = c["flange"].ratio * 1.0
    aw = 2 * hw * 0.25 * 0.25 / (bflat * 1.0)
    rpg = 1 - aw / (1200 + 300 * aw) * (hw - 5.7 * math.sqrt(E / FY))
    assert mn(r, "web local buckling") == pytest.approx(rpg * FY * b.Sx.m)


# --- F8: round HSS and pipe --------------------------------------------------------


def test_round_hss_compact_noncompact_and_limit():
    compact = HSSRound("HSS10.000X0.250")
    s = compact.flexure_strength()
    assert [ls.name for ls in s.limit_states] == ["yielding"]
    assert mn(s, "yielding") == pytest.approx(compact.material.Fy.m * compact.Zx.m)

    thin = HSSRound("HSS20.000X0.250")
    assert thin.flexure_slenderness_x.governing is Slenderness.NONCOMPACT
    r = thin.flexure_strength("y")
    fy = thin.material.Fy.m
    assert mn(r, "local buckling") == pytest.approx((0.021 * E / thin.D_t + fy) * thin.Sx.m)


def test_round_hss_slender_wall_and_out_of_range():
    wall = lambda lam: ElementClassification("wall", lam, 0.07 * E / FY, 0.31 * E / FY, Slenderness.SLENDER, "Case 20")
    lam = 0.4 * E / FY
    s = round_hss_strength(A992, Z=Q_(100, "in**3"), S=Q_(80, "in**3"), wall=wall(lam))
    assert mn(s, "local buckling") == pytest.approx(0.33 * E / lam * 80)
    with pytest.raises(ValueError, match="0.45"):
        round_hss_strength(A992, Z=Q_(100, "in**3"), S=Q_(80, "in**3"), wall=wall(0.5 * E / FY))


def test_pipe_flexure():
    p = Pipe("PIPE6STD")
    s = p.flexure_strength()
    assert mn(s, "yielding") == pytest.approx(p.material.Fy.m * p.Zx.m)
    assert p.get_phiMnx().m == pytest.approx(0.9 * p.get_Mnx().m)


# --- F9: tees -----------------------------------------------------------------------


@pytest.fixture(scope="module")
def wt5x6():
    return WT("WT5X6", A992)


def test_tee_stem_in_tension_hand_calculation(wt5x6):
    t = wt5x6
    My = FY * t.Sx.m
    Mp = min(FY * t.Zx.m, 1.6 * My)
    Lp = 1.76 * t.ry.m * math.sqrt(E / FY)
    Lr = (
        1.95 * (E / FY) * (math.sqrt(t.Iy.m * t.J.m) / t.Sx.m)
        * math.sqrt(2.36 * (FY / E) * (t.d.m * t.Sx.m / t.J.m) + 1)
    )
    Lb = 0.5 * (Lp + Lr)
    r = t.flexure_strength("x", inch(Lb), stem="tension")
    sxc = t.Ix.m / t.y.m
    flange = t.flexure_slenderness_x["flange"]
    assert flange.classification is Slenderness.NONCOMPACT
    assert mn(r, "yielding") == pytest.approx(Mp)
    assert mn(r, "lateral-torsional buckling") == pytest.approx(Mp - (Mp - My) * (Lb - Lp) / (Lr - Lp))
    assert mn(r, "flange local buckling") == pytest.approx(
        min(1.6 * My, Mp - (Mp - 0.7 * FY * sxc) * (flange.ratio - flange.limit_p) / (flange.limit_r - flange.limit_p))
    )
    elastic = t.flexure_strength("x", inch(3 * Lr), stem="tension")
    B = 2.3 * (t.d.m / (3 * Lr)) * math.sqrt(t.Iy.m / t.J.m)
    mcr = 1.95 * E / (3 * Lr) * math.sqrt(t.Iy.m * t.J.m) * (B + math.sqrt(1 + B**2))
    assert mn(elastic, "lateral-torsional buckling") == pytest.approx(min(mcr, Mp))


def test_tee_stem_in_compression_hand_calculation(wt5x6):
    t = wt5x6
    My = FY * t.Sx.m
    Lb = 60.0
    r = t.flexure_strength("x", inch(Lb), stem="compression")
    B = -2.3 * (t.d.m / Lb) * math.sqrt(t.Iy.m / t.J.m)
    mcr = 1.95 * E / Lb * math.sqrt(t.Iy.m * t.J.m) * (B + math.sqrt(1 + B**2))
    assert mn(r, "yielding") == pytest.approx(My)
    assert mn(r, "lateral-torsional buckling") == pytest.approx(min(mcr, My))
    lam = t.flexure_slenderness_x["stem"].ratio
    assert 0.84 * math.sqrt(E / FY) < lam <= 1.52 * math.sqrt(E / FY)
    fcr = (1.43 - 0.515 * lam * math.sqrt(FY / E)) * FY
    assert mn(r, "stem local buckling") == pytest.approx(fcr * t.Sx.m)
    assert all(ls.name != "flange local buckling" for ls in r.limit_states)


def test_tee_stem_compression_is_weaker_than_stem_tension(wt5x6):
    assert wt5x6.get_phiMnx(ft(4), stem="compression") < wt5x6.get_phiMnx(ft(4), stem="tension")


@pytest.mark.parametrize("cls,label", [(WT, "WT6X25"), (MT, "MT4X3.25"), (ST, "ST6X20.4")])
def test_each_tee_family_runs(cls, label):
    t = cls(label)
    assert t.get_phiMnx(ft(5)).m > 0
    assert t.get_phiMnx(ft(5), stem="compression").m > 0


def test_tee_validation(wt5x6):
    with pytest.raises(NotImplementedError):
        wt5x6.flexure_strength("y", ft(5))
    with pytest.raises(ValueError, match="Lb"):
        wt5x6.flexure_strength("x")
    with pytest.raises(ValueError, match="stem"):
        wt5x6.flexure_strength("x", ft(5), stem="up")


# --- F9, F10.3: double angles -----------------------------------------------------------


def test_double_angle_web_legs_in_tension():
    d = DoubleAngle("2L4X4X1/2", A36)
    fy = 36.0
    My = fy * d.Sx.m
    Mp = min(fy * d.Zx.m, 1.6 * My)
    r = d.flexure_strength("x", ft(2), web_legs="tension")
    assert mn(r, "yielding") == pytest.approx(Mp)
    lam = d.b.m / d.t.m
    lam_p = 0.54 * math.sqrt(E / fy)
    assert lam <= lam_p  # compact flange legs
    assert all("local buckling" not in ls.name for ls in r.limit_states)


def test_double_angle_web_legs_in_compression_uses_f10_ltb():
    d = DoubleAngle("2L4X4X1/2", A36)
    fy = 36.0
    My = fy * d.Sx.m
    Lb = 60.0
    B = -2.3 * (d.d.m / Lb) * math.sqrt(d.Iy.m / d.J.m)
    mcr = 1.95 * E / Lb * math.sqrt(d.Iy.m * d.J.m) * (B + math.sqrt(1 + B**2))
    expected = (1.92 - 1.17 * math.sqrt(My / mcr)) * My if My <= mcr else (0.92 - 0.17 * mcr / My) * mcr
    r = d.flexure_strength("x", inch(Lb), web_legs="compression")
    assert mn(r, "yielding") == pytest.approx(1.5 * My)
    assert mn(r, "lateral-torsional buckling") == pytest.approx(min(expected, 1.5 * My))


def test_double_angle_validation():
    d = DoubleAngle("2L4X4X1/2")
    with pytest.raises(NotImplementedError):
        d.flexure_strength("y", ft(5))
    with pytest.raises(ValueError):
        d.flexure_strength("x", ft(5), web_legs="sideways")
    with pytest.raises(ValueError, match="Lb"):
        d.flexure_strength("x")


# --- F10: single angles -----------------------------------------------------------------


def test_beta_w_matches_the_manual_value():
    assert Angle("L6X4X1/2").beta_w.to("in").m == pytest.approx(3.14, rel=0.02)
    assert Angle("L4X4X1/2").beta_w.m == 0


def test_principal_axis_ltb_hand_calculation():
    a = Angle("L6X4X1/2", A572Gr50)
    Lb = 72.0
    My = FY * min(a.SwA.m, a.SwB.m, a.SwC.m)
    for leg, sign in (("long", -1), ("short", 1)):
        bw = sign * a.beta_w.m
        term = 4.4 * bw * a.rz.m / (Lb * 0.5)
        mcr = 9 * E * a.A.m * a.rz.m * 0.5 * 1.0 / (8 * Lb) * (math.sqrt(1 + term**2) + term)
        expected = (1.92 - 1.17 * math.sqrt(My / mcr)) * My if My <= mcr else (0.92 - 0.17 * mcr / My) * mcr
        r = a.flexure_strength("w", inch(Lb), compression_leg=leg)
        assert mn(r, "yielding") == pytest.approx(1.5 * My)
        assert mn(r, "lateral-torsional buckling") == pytest.approx(min(expected, 1.5 * My))
    assert a.get_Mnw(inch(Lb)) < a.get_Mnw(inch(Lb), compression_leg="short")


def test_principal_axis_beta_w_override():
    a = Angle("L6X4X1/2", A572Gr50)
    low = a.flexure_strength("w", ft(6), beta_w=inch(-4.0))
    high = a.flexure_strength("w", ft(6), beta_w=inch(0.0))
    assert mn(low, "lateral-torsional buckling") < mn(high, "lateral-torsional buckling")


def test_minor_principal_axis_leg_local_buckling():
    a = Angle("L8X4X1/2", A36)
    r = a.flexure_strength("z")
    My = 36.0 * min(a.SzA.m, a.SzB.m, a.SzC.m)
    assert mn(r, "yielding") == pytest.approx(1.5 * My)
    no_toes = a.flexure_strength("z", toe_in_compression=False)
    assert all("local buckling" not in ls.name for ls in no_toes.limit_states)


def test_leg_local_buckling_noncompact_and_slender():
    thin = Angle("L8X4X1/2", A36)
    lam = float(thin.b / thin.t)  # 16
    assert thin.flexure_slenderness_x["leg"].classification is Slenderness.NONCOMPACT
    r = thin.flexure_strength("w", ft(2), compression_leg="long")
    sc = thin.SwC.m
    assert mn(r, "leg local buckling (long leg toe)") == pytest.approx(
        36.0 * sc * (2.43 - 1.72 * lam * math.sqrt(36.0 / E))
    )
    slender = Angle("L8X4X1/2", A992).flexure_strength("w", ft(2), compression_leg="long")
    assert any(ls.name.startswith("leg local buckling") for ls in slender.limit_states)


def test_equal_leg_geometric_axis():
    a = Angle("L4X4X1/2", A572Gr50)
    Lb = 72.0
    My = FY * a.Sx.m
    mcr_a = 0.58 * E * 4**4 * 0.5 / Lb**2 * (math.sqrt(1 + 0.88 * (Lb * 0.5 / 16) ** 2) - 1)
    mcr_b = 0.58 * E * 4**4 * 0.5 / Lb**2 * (math.sqrt(1 + 0.88 * (Lb * 0.5 / 16) ** 2) + 1)

    def ltb(my, mcr):
        return min(1.5 * my, (1.92 - 1.17 * math.sqrt(my / mcr)) * my if my <= mcr else (0.92 - 0.17 * mcr / my) * mcr)

    r = a.flexure_strength("x", inch(Lb), Cb=1.0)
    assert mn(r, "yielding") == pytest.approx(1.5 * My)
    assert mn(r, "lateral-torsional buckling") == pytest.approx(ltb(0.8 * My, mcr_a))
    r = a.flexure_strength("y", inch(Lb), toe_in_compression=False)
    assert mn(r, "lateral-torsional buckling") == pytest.approx(ltb(0.8 * My, mcr_b))
    r = a.flexure_strength("x", inch(Lb), lateral_restraint=True)
    assert mn(r, "lateral-torsional buckling") == pytest.approx(ltb(My, 1.25 * mcr_a))


def test_angle_cb_is_capped_at_1_5():
    a = Angle("L6X4X1/2", A572Gr50)
    assert a.flexure_strength("w", ft(8), Cb=3.0).Cb == 1.5
    assert mn(a.flexure_strength("w", ft(8), Cb=3.0), "lateral-torsional buckling") == pytest.approx(
        mn(a.flexure_strength("w", ft(8), Cb=1.5), "lateral-torsional buckling")
    )


def test_angle_validation():
    a = Angle("L6X4X1/2")
    with pytest.raises(ValueError, match="equal-leg"):
        a.flexure_strength("x", ft(5))
    with pytest.raises(ValueError, match="axis"):
        a.flexure_strength("q", ft(5))
    with pytest.raises(ValueError, match="Lb"):
        a.flexure_strength("w")
    with pytest.raises(ValueError, match="compression_leg"):
        a.flexure_strength("w", ft(5), compression_leg="both")
    assert a.get_phiMnz().m > 0


# --- all families ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "shape",
    [
        WideFlange("W14X90"),
        MShape("M12X10"),
        SShape("S12X35"),
        Channel("C10X20"),
        MChannel("MC10X22"),
        HSSRect("HSS8X6X3/8"),
        HSSRound("HSS10.000X0.250"),
        Pipe("PIPE6STD"),
        WT("WT6X25"),
        BuiltUpWideFlange(inch(24), inch(10), inch(0.75), inch(0.375)),
        BuiltUpBox(inch(24), inch(12), inch(0.5), inch(0.375)),
    ],
    ids=lambda s: s.name,
)
def test_every_family_runs_both_axes(shape):
    x = shape.get_phiMnx(ft(6))
    assert x.to("kip*ft").m > 0
    if not isinstance(shape, WT):
        assert shape.get_phiMny(ft(6)).m > 0
    assert shape.get_Mnx(ft(6)).m == pytest.approx(x.m / 0.9)


@pytest.mark.parametrize("label", ["W14X90", "HSS8X6X3/8", "C10X20", "WT6X25", "L4X4X1/2"])
def test_get_shape_dispatch_supports_flexure(label):
    shape = get_shape(label)
    axis = "w" if label.startswith("L") else "x"
    assert shape.flexure_strength(axis, ft(5)).design_strength.m > 0


# --- input validation -----------------------------------------------------------------


def test_lb_is_required_and_needs_units(w21x48):
    with pytest.raises(ValueError, match="Lb"):
        w21x48.flexure_strength("x")
    with pytest.raises(TypeError):
        w21x48.flexure_strength("x", 120)
    with pytest.raises(ValueError):
        w21x48.flexure_strength("x", ft(-1))
    with pytest.raises(ValueError, match="Cb"):
        w21x48.flexure_strength("x", ft(10), Cb=0)
    with pytest.raises(ValueError):
        w21x48.flexure_strength("z", ft(10))


def test_built_up_i_validation():
    s = BuiltUpWideFlange(inch(24), inch(10), inch(0.75), inch(0.375))
    with pytest.raises(ValueError, match="Lb"):
        s.flexure_strength("x")
    with pytest.raises(ValueError):
        s.flexure_strength("x", ft(5), compression_flange="left")
