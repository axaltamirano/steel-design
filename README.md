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
