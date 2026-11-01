# Examples

Run any example from the repository root:

```console
$ uv run python examples/01_floor_beam.py
```

| Script | Demonstrates |
| ------ | ------------ |
| [01_floor_beam.py](01_floor_beam.py) | Flexure (Chapter F) and shear (Chapter G) of a rolled W-shape, with `Cb` and the unbraced length |
| [02_hss_column.py](02_hss_column.py) | Compression (Chapter E) of an HSS column, slenderness classification and effective length |
| [03_tension_brace.py](03_tension_brace.py) | Tension (Chapter D) of a single-angle brace with a net area and shear lag factor |
| [04_plate_girder.py](04_plate_girder.py) | A built-up singly symmetric girder: classification, flexure, and shear with and without stiffeners |
| [05_bracket_bolt_group.py](05_bracket_bolt_group.py) | Bolt strengths (Section J3) and an eccentrically loaded bolt group by the ICR method, with a plot (needs `matplotlib`) |
| [06_bracket_weld_group.py](06_bracket_weld_group.py) | A fillet weld and an eccentrically loaded C-shaped weld group by the elastic and ICR methods (Manual Part 8), with a plot (needs `matplotlib`) |

The library has no demand or load-combination features. The required strengths in each
example are inputs written at the top of the script. Combined forces (Chapter H) are not yet
implemented.
