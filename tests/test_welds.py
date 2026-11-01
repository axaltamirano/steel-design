"""Fillet welds (AISC 360-22 Section J2) and weld groups (elastic and ICR methods)."""

import csv
import math
from pathlib import Path

import pytest

from steel_design import Q_
from steel_design.welds import (
    E60XX,
    E70XX,
    E80XX,
    E110XX,
    FilletWeld,
    WeldGroup,
    WeldLine,
    directional_factor,
    max_fillet_size,
    min_fillet_size,
)
from steel_design.welds.icr import delta_m, delta_u, rult_per_length


def i(x):
    return Q_(x, "in")


def kips(q):
    return q.to("kip").magnitude


# --- electrodes and single welds ---------------------------------------------------------


def test_electrodes():
    assert E70XX.FEXX.m == 70 and E70XX.Fnw().m == pytest.approx(42)
    assert E70XX.C1() == 1.0
    assert E80XX.C1() == pytest.approx(80 / 70)
    assert E60XX.C1() == pytest.approx(0.857, abs=1e-3)
    assert E110XX.C1() == pytest.approx(1.571, abs=1e-3)
    with pytest.raises(TypeError):
        E70XX()


def test_fillet_weld_strength():
    weld = FilletWeld(i(0.25), i(10))
    assert weld.throat.m == pytest.approx(0.17675)
    s = weld.strength()
    assert kips(s.Rn) == pytest.approx(42 * 0.707 * 0.25 * 10)
    assert kips(s.design_strength) == pytest.approx(0.75 * 42 * 0.707 * 0.25 * 10)
    assert s.reference == "Eq. J2-4"


def test_directional_factor():
    assert directional_factor(0) == 1.0
    assert directional_factor(90) == pytest.approx(1.5)
    assert directional_factor(45) == pytest.approx(1 + 0.5 * math.sin(math.radians(45)) ** 1.5)
    plain = FilletWeld(i(0.25), i(10), angle=90)
    boosted = FilletWeld(i(0.25), i(10), angle=90, directional=True)
    assert kips(boosted.strength().Rn) == pytest.approx(1.5 * kips(plain.strength().Rn))


def test_weld_size_limits():
    assert min_fillet_size(i(0.25)).m == 0.125
    assert min_fillet_size(i(0.3)).m == 0.1875
    assert min_fillet_size(i(0.5)).m == 0.1875
    assert min_fillet_size(i(0.75)).m == 0.25
    assert min_fillet_size(i(1.0)).m == 0.3125
    assert max_fillet_size(i(0.1875)).m == 0.1875
    assert max_fillet_size(i(0.5)).m == pytest.approx(0.5 - 1 / 16)
    assert FilletWeld(i(0.25), i(10)).minimum_length().m == 1.0


def test_end_loaded_effective_length():
    w = i(0.25)
    assert FilletWeld(w, i(25)).effective_length.m == 25  # 100 w
    long = FilletWeld(w, i(50))  # 200 w
    assert long.effective_length.m == pytest.approx((1.2 - 0.002 * 200) * 50)
    assert FilletWeld(w, i(100)).effective_length.m == pytest.approx(180 * 0.25)  # over 300 w
    assert FilletWeld(w, i(50), angle=90).effective_length.m == 50  # not end-loaded


def test_input_validation():
    with pytest.raises(TypeError):
        FilletWeld(0.25, i(10))
    with pytest.raises(ValueError):
        FilletWeld(i(0), i(10))


# --- weld element response ---------------------------------------------------------------


def test_weld_element_parameters():
    assert rult_per_length(0, 0.0625, 70) == pytest.approx(0.6 * 70 * 0.707 * 0.0625)
    assert rult_per_length(90, 0.0625, 70) == pytest.approx(1.5 * rult_per_length(0, 0.0625, 70))
    assert delta_u(0, 1.0) == pytest.approx(1.087 * 6**-0.65)
    assert delta_m(90, 1.0) == pytest.approx(0.209 * 92**-0.32)
    assert delta_u(0, 1.0) > delta_m(0, 1.0)


# --- weld group geometry -----------------------------------------------------------------


def test_group_geometry():
    g = WeldGroup.c_shape(i(10), i(4), i(0.25))
    assert g.total_length.m == 18
    xc, yc = g.centroid
    assert xc.m == pytest.approx(2 * 4 * 2 / 18)  # xl of the Manual, x-bar = 16/18
    assert yc.m == pytest.approx(5)
    box = WeldGroup.box(i(4), i(10), i(0.25))
    assert box.total_length.m == 28
    line = WeldGroup.line(i(10), i(0.25))
    assert line.Ip.m == pytest.approx(10**3 / 12)


def test_polar_moment_of_a_box():
    box = WeldGroup.box(i(4), i(10), i(0.25))
    # Sum of L (r^2 + L^2/12) over the four lines
    expected = 2 * 10 * (2**2 + 10**2 / 12) + 2 * 4 * (5**2 + 4**2 / 12)
    assert box.Ip.m == pytest.approx(expected)


def test_group_validation():
    with pytest.raises(ValueError):
        WeldGroup([])
    with pytest.raises(ValueError):
        WeldGroup([WeldLine((i(0), i(0)), (i(0), i(0)), i(0.25))])
    with pytest.raises(ValueError):
        WeldGroup.c_shape(i(10), i(4), i(0.25), open_side="up")
    with pytest.raises(ValueError):
        WeldGroup.l_shape(i(10), i(4), i(0.25), flange_at="middle")
    with pytest.raises(TypeError):
        WeldGroup.line(10, i(0.25))


# --- concentric and elastic strengths ----------------------------------------------------


def test_concentric_strength():
    g = WeldGroup.parallel_vertical(i(10), i(5), i(0.25))
    assert kips(g.concentric_strength()) == pytest.approx(0.75 * 42 * 0.707 * 0.25 * 20)
    # Transverse load on the same group with the directional increase
    assert kips(g.concentric_strength(angle=90, directional=True)) == pytest.approx(1.5 * kips(g.concentric_strength()))


def test_elastic_strength_single_line():
    # A 10 in. line loaded 5 in. from its centroid: resultant at the ends is sqrt(0.1^2 + 0.3^2) P / in.
    g = WeldGroup.line(i(10), i(1 / 16))
    q = 42 * 0.707 / 16
    expected = 0.75 * q / math.hypot(0.1, 0.3)
    assert kips(g.elastic_strength((i(5), i(5)))) == pytest.approx(expected)


def test_elastic_is_below_icr():
    g = WeldGroup.box(i(4), i(10), i(0.25))
    xc, yc = g.centroid
    for e in (1, 3, 8):
        point = (xc + i(e), yc)
        assert kips(g.elastic_strength(point)) < kips(g.icr_strength(point).Pn)


def test_elastic_concentric_matches_sum():
    g = WeldGroup.parallel_vertical(i(10), i(5), i(0.25))
    xc, yc = g.centroid
    assert kips(g.elastic_strength((xc, yc))) == pytest.approx(kips(g.concentric_strength()))


# --- ICR ---------------------------------------------------------------------------------


def test_icr_result_fields():
    g = WeldGroup.parallel_vertical(i(10), i(5), i(1 / 16))
    r = g.icr_strength_eccentric(i(5))
    assert r.converged and r.icr is not None
    assert r.icr[0].m < g.centroid[0].m  # on the side opposite the load
    assert kips(r.Pn) == pytest.approx(0.75 * kips(r.Rn))
    assert r.design_strength == r.Pn
    # Equilibrium of the element forces
    fx = sum(f[2] for f in r.element_forces)
    fy = sum(f[3] for f in r.element_forces)
    assert fx == pytest.approx(0, abs=1e-6)
    assert fy == pytest.approx(-kips(r.Rn), rel=1e-6)


def test_icr_strength_decreases_with_eccentricity():
    g = WeldGroup.box(i(4), i(10), i(0.25))
    caps = [kips(g.icr_strength_eccentric(i(e)).Pn) for e in (0.5, 1, 2, 4, 8)]
    assert caps == sorted(caps, reverse=True)


def test_icr_scales_with_size_and_electrode():
    base = WeldGroup.c_shape(i(10), i(4), i(1 / 16))
    big = WeldGroup.c_shape(i(10), i(4), i(1 / 4))
    e80 = WeldGroup.c_shape(i(10), i(4), i(1 / 16), electrode=E80XX)
    p0 = kips(base.icr_strength_eccentric(i(5)).Pn)
    # Ultimate strength scales with leg size, but so does deformation capacity: the group is similar
    assert kips(big.icr_strength_eccentric(i(5)).Pn) == pytest.approx(4 * p0, rel=1e-6)
    assert kips(e80.icr_strength_eccentric(i(5)).Pn) == pytest.approx(80 / 70 * p0, rel=1e-6)


def test_icr_coefficient_and_check():
    g = WeldGroup.parallel_vertical(i(10), i(5), i(1 / 16))
    c = g.icr_coefficient(i(1), length=i(10))
    assert c == pytest.approx(3.72, rel=0.01)  # Manual Table 8-4, a = 0.1, k = 0.5 (0 degrees)
    cap = kips(g.icr_strength_eccentric(i(1)).Pn)
    assert g.check(Q_(cap / 2, "kip"), i(1)) == pytest.approx(0.5)
    mixed = WeldGroup([WeldLine((i(0), i(0)), (i(0), i(5)), i(0.25)), WeldLine((i(3), i(0)), (i(3), i(5)), i(0.125))])
    with pytest.raises(ValueError):
        mixed.icr_coefficient(i(1))


def test_mixed_sizes_run():
    g = WeldGroup([WeldLine((i(0), i(0)), (i(0), i(10)), i(0.25)), WeldLine((i(4), i(0)), (i(4), i(10)), i(0.125))])
    r = g.icr_strength_eccentric(i(3))
    assert r.converged and kips(r.Pn) > 0


def test_concentric_icr_not_below_code_sum():
    g = WeldGroup.box(i(4), i(10), i(0.25))
    xc, yc = g.centroid
    r = g.icr_strength((xc, yc))
    assert r.icr is None
    assert kips(r.Pn) >= kips(g.concentric_strength()) * (1 - 1e-9)


@pytest.mark.parametrize("angle", [0, 20, 45, 75, -30])
def test_icr_converges_over_angles(angle):
    for g in (
        WeldGroup.parallel_horizontal(i(8), i(3), i(0.25)),
        WeldGroup.l_shape(i(10), i(5), i(0.25)),
        WeldGroup.c_shape(i(10), i(5), i(0.25)),
    ):
        xc, yc = g.centroid
        for dx in (0.3, 2, 12):
            assert g.icr_strength((xc + i(dx), yc), angle).converged


# --- verification against Manual Part 8 --------------------------------------------------

# (flange_at, tilt sign, load side) for each table; the Manual's load is on the left for 8-9 and 8-11
_TABLES = {
    "8-4": ("bottom", 1),
    "8-5": ("bottom", 1),
    "8-6": ("bottom", 1),
    "8-7": ("bottom", 1),
    "8-8": ("bottom", 1),
    "8-9": ("bottom", -1),
    "8-10": ("bottom", 1),
    "8-10a": ("top", 1),
    "8-11": ("top", -1),
    "8-11a": ("bottom", -1),
}


def _group(table, k, flange_at):
    l, kl, size = i(10), i(10 * k), i(1 / 16)
    if table == "8-4":
        return WeldGroup.parallel_vertical(l, kl, size)
    if table == "8-5":
        return WeldGroup.parallel_horizontal(l, kl, size)
    if table == "8-6":
        return WeldGroup.box(kl, l, size)
    if table == "8-7":
        return WeldGroup.box(l, kl, size)
    if table in ("8-8", "8-9"):
        return WeldGroup.c_shape(l, kl, size)
    return WeldGroup.l_shape(l, kl, size, flange_at=flange_at)


def _rows():
    path = Path(__file__).parent / "data" / "manual_part8_C.csv"
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    return rows[::3]  # every third sampled value keeps the run short


@pytest.mark.parametrize("row", _rows(), ids=lambda r: f"{r['table']}-{r['angle']}-a{r['a']}-k{r['k']}")
def test_manual_part8_coefficients(row):
    table, angle, a, k, expected = row["table"], float(row["angle"]), float(row["a"]), float(row["k"]), float(row["C"])
    flange_at, side = _TABLES[table]
    g = _group(table, k, flange_at)
    xc, yc = g.centroid
    result = g.icr_strength((xc + i(side * a * 10), yc), side * angle)
    c = kips(result.Rn) / (16 * (1 / 16) * 10)
    assert result.converged
    assert c == pytest.approx(expected, rel=0.02)


def test_manual_part8_hand_values():
    # Table 8-4, 0 degrees, a = 0: two vertical lines loaded concentrically, C = 2 x 1.856
    g = WeldGroup.parallel_vertical(i(10), i(5), i(1 / 16))
    xc, yc = g.centroid
    assert kips(g.icr_strength((xc, yc)).Rn) / 10 == pytest.approx(3.71, rel=0.005)
    # Table 8-4, 15 degrees, a = 0: directional strength increase of a linear group
    assert kips(g.icr_strength((xc, yc), 15).Rn) / 10 == pytest.approx(3.96, rel=0.01)


# --- plotting ----------------------------------------------------------------------------


def test_plot_draws_weld_group():
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    group = WeldGroup.c_shape(i(10), i(4), i(0.25))
    ax = group.plot(e=i(6), angle=20)
    assert len(ax.lines) >= 3
    assert any("ICR" in t.get_text() for t in ax.texts)
    assert group.plot().lines  # layout only
    with pytest.raises(ValueError):
        group.plot(e=i(6), load_point=(i(6), i(0)))
