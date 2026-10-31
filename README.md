# AISC Steel Section Analysis

`steel_design` is a Python implementation of AISC 360-22 provisions for various steel shapes, including pre-defined sections per the Steel Construction Manual as well as custom built-up shapes. Only LRFD is supported, in US customary units.

`steel_design` internally uses the [`pint`](https://pint.readthedocs.io/en/stable/) library throughout to manage units. 

```python

from steel_design import Q_ 
# the `pint` library is used internally to manage units, and is exposed via Q_
# for example, 20-ft would be expressed as Q_(20, "ft")

from steel_design.sections import WideFlange
from steel_design.materials import A992, A572Gr65

w = WideFlange("W14X90") # default material from Manual Table 2-4 (A992)
w = WideFlange("W14X90", material=A572Gr65) # or override

# get properties
print(A992.E) # Quantity(29000, "kip_per_square_inch")
# Return the raw magnitude with the .m property
print(A992.E.m) # 29000
# use the .to() method to convert a value to the requested unit
print(A992.E.to("ksi").m) # 29000

# beam checks
Lb = Q_(20, "ft")
Cb = 1.0 # user-supplied
phiMnx = w.get_phiMnx(Lb, Cb)
phiVnx = w.get_phiVnx()

# column checks
Lbx = Q_(25, "ft")
K = 1

phiPnc = w.get_phiPnc(Lx=Lbx, Kx=K) # Ly defaults to Lx, and Ky defaults to 1
```

## Installation

`steel_design` requires Python 3.13 or newer. The package is not yet published to PyPI, so install it from source (see [Building from source](#building-from-source)).

## Features

### Standard ASTM Shapes
`WideFlange`, `MShape`, `SShape`, `HP`, `Channel`, `MChannel`, `Angle`, `WT`, `MT`, `ST`, `HSSRect`, `HSSRound`, `Pipe`, `DoubleAngle`

Note: square HSS shapes are included as part of `HSSRect`. 

### Custom Built-Up Shapes
```python
from steel_design.sections import BuiltUpWideFlange, BuiltUpBox

# WF plate girder: 30" tall, 16" wide, 1" thick flange, 3/8" thick web
pg = BuiltUpWideFlange(Q_(30,"in"), Q_(16, "in"), Q_(1, "in"), Q_(0.375, "in"))

# Built-up Box 24"x24" with 2" flange plates and 1" web plates
box = BuiltUpBox(Ht=Q_(24,"in"), B=Q_(24, "in"), tf=Q_(2, "in"), tw=Q_(1, "in"))

```

### Tension (Chapter D)

### Compression (Chapter E)

### Flexure (Chapter F)

### Shear (Chapter G)

## Examples

Refer to [Examples](examples/README.md) for implementation examples. 

## Documentation

Full API documentation is available in [docs/](docs/). Build it with Sphinx: `uv run make -C docs html` (output in `docs/_build/html`).

## Testing

Comprehensive unit tests have been implemented with pytest. Run them with `uv run pytest`.

Unit tests include examples from the AISC Design Examples V16.0 reference, with tests named to match the referenced example. 

## Building from source

The project is managed with [uv](https://docs.astral.sh/uv/) and built with the `uv_build` backend.

```console
$ git clone https://github.com/<your-account>/steel-design.git
$ cd steel-design
$ uv sync                  # creates .venv and installs the package with the dev dependencies
$ uv run pytest            # optional: run the test suite
$ uv build                 # writes an sdist and a wheel to dist/
```

Install the built wheel into another environment with `pip install dist/steel_design-0.1.0-py3-none-any.whl`, or use an editable install with `pip install -e .`.

### Regenerating the shape data

The shape properties live in `src/steel_design/data/*.csv`, which are committed. To regenerate them from the AISC Shapes Database, place `aisc-shapes-database-v160-3.xlsx` in `reference/` (this folder is git-ignored) and run:

```console
$ uv run python tools/build_shape_csvs.py
```

## License

Released under the [MIT License](LICENSE).
## Disclaimer
`steel_design` is an open source engineering tool that benefits from the collaboration of contributors. Although efforts have been made to ensure that the relevant engineering theories have been correctly implemented, no warranties are implied on correctness or completeness of results. It remains solely the user's responsibility to confirm and accept the output. Refer to the license for clarification of the conditions of use.
