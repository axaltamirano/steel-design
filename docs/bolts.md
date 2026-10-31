# Bolts and bolt groups

The {mod}`steel_design.bolts` package implements AISC 360-22 Section J3 (LRFD) for single bolts
and the instantaneous center of rotation (ICR) method of the Steel Construction Manual, Part 7,
for bolt groups loaded in the plane of the group.

## Materials

Bolt grades are classes with single values, like the steel grades (Tables J3.1 and J3.2).

| Class | Alias | `Fnt` | `Fnv` (N) | `Fnv` (X) |
| ----- | ----- | ----- | --------- | --------- |
| `A307` | | 45 ksi | 27 ksi | 27 ksi |
| `Group120` | `A325` | 90 ksi | 54 ksi | 68 ksi |
| `Group150` | `A490` | 113 ksi | 68 ksi | 84 ksi |

`Group120.Tb(0.75)` returns the Table J3.1 minimum pretension. A307 bolts have none.

## A single bolt

```python
from steel_design import Q_
from steel_design.bolts import A325, Bolt, Ply, SlipClass

bolt = Bolt(Q_(3 / 4, "in"), A325, threads_excluded=False, shear_planes=1)
bolt.get_phiRnv()                         # 17.9 kip, Eq. J3-1
bolt.get_phiRnt()                         # 29.8 kip
bolt.tension_with_shear(Q_(10, "kip"))    # Eqs. J3-2 and J3-3a
bolt.slip_resistance(SlipClass.A)         # Eq. J3-4, 9.49 kip
```

Each limit state returns a `BoltStrength` with `Rn`, `phi`, `reference` and `design_strength`.

Bearing and tearout (Section J3.11) use a `Ply` with the thickness `t`, the material `Fu` and
the clear distance `Lc` from the edge of the hole to the next hole or the edge of the material:

```python
ply = Ply(Q_(0.5, "in"), Q_(58, "ksi"), Lc=Q_(0.85, "in"))
bolt.bearing_tearout_strength(ply)                               # J3-6a and J3-6c
bolt.bearing_tearout_strength(ply, deformation_considered=False)  # J3-6b and J3-6d
bolt.effective_strength([ply])        # lesser of shear and bearing/tearout
```

The helpers in {mod}`steel_design.bolts.holes` give hole dimensions (Table J3.3), minimum edge
distances (Tables J3.4 and J3.5), the minimum spacing and `Lc` from an edge distance or a spacing.

Resistance factors are in {class}`~steel_design.resistance_factors.ResistanceFactors`. The slip
resistance `phi` follows the hole type: 1.00 standard, 0.85 oversize and short slot, 0.70 long slot.

## Bolt groups

```python
from steel_design.bolts import BoltGroup

group = BoltGroup.grid(rows=4, cols=2, s_row=Q_(3, "in"), s_col=Q_(3, "in"), bolt=bolt, plies=ply)
group = BoltGroup.row(4, Q_(3, "in"), bolt)       # one line of bolts
group = BoltGroup([(Q_(0, "in"), Q_(0, "in")), (Q_(3, "in"), Q_(0, "in")), ...], bolt)  # any layout
```

Coordinates have x to the right and y up. A grid is centered on the origin. `centroid`, `Ix`,
`Iy` and `Ip` describe the layout. The strength of each bolt is the lesser of its shear strength
and its bearing/tearout strength (the Section J3.7 User Note), so `plies` may differ per bolt:
pass one sequence of plies per bolt, e.g. `[(ply_a,), (ply_b,), ...]`. A grid built with
`edge_distance` can derive a conservative `Lc` from `conservative_Lc()`.

A load through the centroid has the strength `concentric_strength()`, the sum of the bolt strengths.

## Eccentric loads: the ICR method

```python
result = group.icr_strength_eccentric(Q_(6, "in"))          # vertical load 6 in. from the centroid
result = group.icr_strength(load_point, angle=30)          # any point and any load angle
result.Pn, result.C, result.icr
group.icr_coefficient(Q_(6, "in"))                          # C of Manual Part 7
group.check(Q_(40, "kip"), Q_(6, "in"))                     # Pu / phi Pn
```

The `angle` is measured from the vertical in degrees: 0 acts downward and positive angles tilt
the load toward +x. Each bolt follows the Crawford-Kulak curve

```
R = Rult (1 - exp(-10 delta)) ** 0.55,   delta = 0.34 in. * d / d_max
```

where `d` is the distance from the bolt to the ICR and `Rult` is the design strength of that
bolt, so `Pn` already includes `phi`. The solver finds the ICR by satisfying two equilibrium
conditions: the resultant of the bolt forces is parallel to the load and passes through the load
point. The result lists the ICR, the force on every bolt and `C = Pn / (phi rn)` when all bolts
have equal strength.

Notes:

- The farthest bolt carries `Rult (1 - exp(-3.4)) ** 0.55 = 0.98 Rult`, so the strength is
  slightly below `n phi rn` as the eccentricity approaches zero (the Manual's tables use the
  same curve). A load exactly through the
  centroid is concentric and uses the full `n phi rn`.
- `Lc` is a single value per bolt. The direction of bearing varies with the ICR, so use the
  smallest clear distance a bolt can bear against.
- Only in-plane eccentric shear is implemented. Prying action and eccentric tension are not.

## Verification against the Manual

The test suite compares the library with the 16th Edition Manual, Part 7:

- Tables 7-1 to 7-3 (shear, tension and slip resistance): all values agree with the published
  `phi rn`. The Manual rounds the nominal bolt area to three figures, so shear values for
  bolts of 1-1/8 in. and larger differ by up to about 1%.
- Tables 7-4 and 7-5 (bearing and tearout based on spacing and edge distance): all 169 values
  checked agree, for standard, oversize, short-slot and long-slot holes.
- Tables 7-6 to 7-13 (coefficients `C`): all 20,652 published values were compared. The mean
  difference is zero, and nearly all values agree within the rounding of the table. Where they
  differ, the library is generally lower, by at most about 2%, at small eccentricities with
  steep load angles. A sample of 384 values is in the test suite.

In the tables the angle is measured from the vertical with the load inclined toward the bolt
group, and `ex` is measured horizontally from the centroid to the line of action, so compare
with `group.icr_strength((ex, 0 in.), angle=-theta).C`.
