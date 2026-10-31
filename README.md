# steel-design

Python implementation of AISC 360-22 provisions (US customary units, managed with `pint`).

```python
from steel_design import Q_
from steel_design.sections import get_shape, BuiltUpWideFlange, BuiltUpBox
from steel_design.materials import A992, A572Gr65, get_material

w = get_shape("W14X90")                       # default material from Manual Table 2-4 (A992)
w = get_shape("W14X90", material=A572Gr65)    # or override
pg = BuiltUpWideFlange(Q_(30, "in"), Q_(12, "in"), Q_(1, "in"), Q_(0.375, "in"))
mono = BuiltUpWideFlange(Q_(20, "in"), Q_(10, "in"), Q_(1, "in"), Q_(0.5, "in"),
                         bf_bottom=Q_(6, "in"), tf_bottom=Q_(1, "in"))   # singly symmetric
box = BuiltUpBox(Ht=Q_(12, "in"), B=Q_(10, "in"), tf=Q_(0.5, "in"), tw=Q_(0.5, "in"))
```

- **Materials**: `steel_design/materials/` has one class per grade (`a992.py`, `a572_gr50.py`, ...) on a
  `SteelMaterial` base holding constants (E, G, ...). Defaults per shape family are in `defaults.py`.
- **Shapes**: `steel_design/data/*.csv` are generated from `reference/aisc-shapes-database-v160-3.xlsx`
  (US units only). Regenerate with `uv run python tools/build_shape_csvs.py`.
- **Units**: dimensions must be pint quantities; bare floats are rejected.

Tension (AISC 360-22 Chapter D): `w.tension_strength(An=Q_(22, "in**2"), U=0.9)` returns the yielding
(D2-1) and rupture (D2-2) limit states with LRFD design strengths. `An` defaults to the gross area and the
shear lag factor `U` is always user-supplied (default 1.0).

Compression (AISC 360-22 Chapter E): `w.compression_strength(Lx=Q_(10, "ft"), Ly=None, Kx=1.0, Ky=1.0)` checks
flexural (E3), torsional and flexural-torsional (E4) buckling with the slender-element reduction of E7.
Single angles use `a.compression_strength(L, K, e5="planar")` for the Section E5 effective slenderness.

Flexure (AISC 360-22 Chapter F): `w.flexure_strength("x", Lb=Q_(8, "ft"), Cb=1.0)` returns every applicable limit
state (yielding, LTB, flange/web local buckling); `get_Mnx`/`get_phiMnx`/`get_Mny`/`get_phiMny` give the governing
strength in kip-ft. `Cb` is user-supplied.

The library is LRFD only. All resistance factors live in `steel_design.resistance_factors.ResistanceFactors`.
Each shape has `get_Pnt`/`get_phiPnt` (tension) and `get_Pnc`/`get_phiPnc` (compression) for the nominal and
design strength of the governing limit state, in kips.

Tests: `uv run pytest`

```python
w.flexure_slenderness_x["flange"].classification   # Slenderness.NONCOMPACT (Table B4.1b)
w.flexure_slenderness_y.governing                  # weak-axis flexure
w.compression_slenderness.governing                # Slenderness.NONSLENDER (Table B4.1a)
```

Slenderness is a property of every section; `w.classify_flexure(axis)` and `w.classify_compression()`
are the underlying methods. Each shape class declares its AISC database properties (with units and
definitions) so they appear in the API docs and IDE completion.

Classification covers every shape class: rolled I-shapes (W, M, S, HP), channels, tees, angles
(single and double), rectangular and round HSS, pipe, and built-up I-shapes and boxes. Limits and
case numbers were checked against AISC 360-22 Tables B4.1a and B4.1b.

Notes on classification options:
- Singly symmetric built-up I-shapes: `mono.classify_flexure("x", compression_flange="top" | "bottom")` (or the `flexure_slenderness_x` /
  `flexure_slenderness_x_bottom` properties) selects the
  flange in major-axis compression (Case 11 flange with FL from Sxt/Sxc, Case 16 web).
- Double angles: `DoubleAngle(label, continuous_contact=True)` uses Table B4.1a Case 1 (0.56); the default
  (separators) uses Case 3 (0.45).
