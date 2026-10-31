# Section classification

Every section classifies itself for local buckling per AISC 360-22 Section B4 (Tables
B4.1a and B4.1b) against the Fy of its material. The results are properties of the section:

```python
w.compression_slenderness      # axial compression, Table B4.1a
w.flexure_slenderness_x        # strong-axis flexure, Table B4.1b
w.flexure_slenderness_y        # weak-axis flexure, Table B4.1b

r = w.flexure_slenderness_x
r["flange"].classification, r["web"].ratio, r.governing
```

The properties call {meth}`~steel_design.sections.base.Section.classify_compression` and
{meth}`~steel_design.sections.base.Section.classify_flexure`, which each shape class
implements explicitly, with the Table B4 cases and limits written out in each class. Compression
gives *nonslender* or *slender* per element; flexure gives *compact*, *noncompact* or
*slender*. Results are a {class}`~steel_design.classification.SectionClassification`; each
element carries its ratio, limits, result and Table B4 case reference. Properties are
recomputed on each access, so changing `section.material` changes the result.
{mod}`steel_design.classification` holds the result types and shared helpers.

Supported shapes: rolled I (W, M, S, HP), channels, tees, single and double angles,
rectangular and round HSS, pipe, built-up I and built-up box.

## Options

- `compression_flange="top"|"bottom"`: singly symmetric built-up I-shapes in
  major-axis flexure, via `classify_flexure("x", compression_flange=...)`.
  `flexure_slenderness_x` assumes the top flange; `flexure_slenderness_x_bottom` the bottom.
- `continuous_contact` (`DoubleAngle` constructor): `False` uses Case 3 (0.45),
  `True` uses Case 1 (0.56).

## Notable cases

- Built-up box: flange flexure Case 21 (1.12/1.49), compression Case 8 (1.49).
- Minor-axis flange of I-shapes and channels: Case 13.
- Singly symmetric web: Case 16, `kc` limited to 0.35-0.76 and `FL` per Table B4.1b.

## Assumptions and limitations

- Limits use the section material's `Fy`.
- Case 16 takes `My` as `Fy` times the smaller elastic modulus and `Mp = Fy Zx`
  without the 1.6 `Fy Sx` cap; `λp` is set to `λr` when `hp <= 0`.
- Double angles in flexure reuse single-angle Case 12.
- Tee flexure about the y-axis checks the flange only.
