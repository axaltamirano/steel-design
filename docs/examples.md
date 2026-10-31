# Examples

The `examples/` folder of the repository holds runnable scripts. Run them
from the repository root with `uv run python examples/<script>.py`. Required strengths are
inputs at the top of each script; the library computes capacities.

## Floor beam: flexure and shear

A rolled W-shape with a user-supplied `Cb` from Eq. F1-1, every flexural limit state, and a
sweep of the unbraced length.

```{literalinclude} ../examples/01_floor_beam.py
:language: python
```

## HSS column: compression

B4 classification, the effect of the effective length factor, and a slender-wall HSS using
the effective area of Section E7.

```{literalinclude} ../examples/02_hss_column.py
:language: python
```

## Tension brace: yielding and rupture

A single angle with a user-supplied net area and shear lag factor.

```{literalinclude} ../examples/03_tension_brace.py
:language: python
```

## Plate girder: built-up section

A singly symmetric built-up I-shape: classification for the compression flange, flexure with
F4, and shear with and without transverse stiffeners (tension field action).

```{literalinclude} ../examples/04_plate_girder.py
:language: python
```

## Bracket bolt group: ICR

Single-bolt strengths, bearing and tearout, and the ICR strength of a bolt group for a vertical
and an inclined eccentric load.

```{literalinclude} ../examples/05_bracket_bolt_group.py
:language: python
```
