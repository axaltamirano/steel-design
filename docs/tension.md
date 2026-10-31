# Tension

{mod}`steel_design.tension` implements AISC 360-22 Chapter D, Sections D1 to D3. Every
section provides {meth}`~steel_design.sections.base.Section.tension_strength`.

```python
from steel_design import Q_
from steel_design.sections import WideFlange

w = WideFlange("W14X90")
t = w.tension_strength(An=Q_(22.0, "in**2"), U=0.9)

t.Ae                      # 19.8 in^2, Ae = An U (Eq. D3-1)
t.yielding.Pn             # 1325 kip, Fy Ag (Eq. D2-1)
t.rupture.design_strength # 965.25 kip, 0.75 Fu Ae (Eq. D2-2)
t.design_strength         # governing design strength, phi_t Pn
t.governing.name          # "tensile rupture"

w.get_Pnt(An=Q_(22.0, "in**2"), U=0.9)     # Pn of the governing limit state, kip
w.get_phiPnt(An=Q_(22.0, "in**2"), U=0.9)  # governing design strength, kip
```

## Limit states

| Limit state    | Nominal | LRFD           |
| -------------- | ------- | -------------- |
| Gross yielding | `Fy Ag` | `phi_t = 0.90` |
| Net rupture    | `Fu Ae` | `phi_t = 0.75` |

The design strength is the lower of the two. Each limit state is a
{class}`~steel_design.tension.TensionLimitState` with `Pn`, `phi`,
`design_strength` and the equation `reference`.

## Inputs

- `An` is the net area per Section B4.3 and defaults to the gross area `A` (no holes). It
  must be a pint area quantity and may not exceed `A`.
- `U` is the shear lag factor of Table D3.1. It is always supplied by the user, defaults to
  1.0 and must satisfy `0 < U <= 1`. For open sections the Specification allows `U` to be
  taken no smaller than the ratio of the connected element area to the gross area; that lower
  bound is not computed by the library.
- Fy and Fu come from the section material.

## Slenderness (D1)

There is no maximum slenderness limit for tension members, but the User Note recommends
`L/r` not exceed 300 (not applicable to rods).
{meth}`~steel_design.sections.base.Section.tension_slenderness_ratio` uses the least of
`rx`, `ry` and `rz` (`rz` exists for single angles), and
{func}`~steel_design.tension.exceeds_recommended_slenderness` checks the limit.

## Not yet included

Built-up member detailing (D4), pin-connected members (D5), eyebars (D6), and block shear
rupture (J4.3).
