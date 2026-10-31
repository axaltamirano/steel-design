# Shapes database

## Data pipeline

The AISC Shapes Database (`reference/aisc-shapes-database-v160-3.xlsx`) is split
into one CSV per shape family by `tools/build_shape_csvs.py`:

```console
$ uv run python tools/build_shape_csvs.py
```

Only US customary columns are kept, with original AISC column names. The `–`
placeholder becomes an empty cell; HSS is split into round and rectangular by the
presence of an outside diameter. The CSVs are written to `src/steel_design/data`.

## Shape classes

Each family is its own class in its own module, subclassing
{class}`~steel_design.sections.database.DatabaseShape`:

```{eval-rst}
==============  ==============  ==============  ==============
``WideFlange``  ``MShape``      ``SShape``      ``HP``
``Channel``     ``MChannel``    ``Angle``       ``DoubleAngle``
``WT``          ``MT``          ``ST``          ``HSSRect``
``HSSRound``    ``Pipe``
==============  ==============  ==============  ==============
```

```python
from steel_design.sections import WideFlange, get_shape
from steel_design.materials import A572Gr50

w = WideFlange("W14X90", material=A572Gr50)
w.Zx, w.bf_2tf, w.h_tw
get_shape("HSS6X6X1/4")            # family found automatically
```

Each class declares every property of its family (name, type and definition with units),
so they appear in the {doc}`API reference <api>` and in IDE completion. A test checks that the
declarations match the CSV columns. Properties use AISC names with `/` replaced by `_` (`h/tw` becomes
`h_tw`), `W` becomes `weight` and `tan(α)` becomes `tan_alpha`. Values
with units are pint quantities; absent values are `None`.
Labels are case-insensitive; `Family.labels()` lists them.
