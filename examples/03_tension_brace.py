"""Check a single-angle tension brace for yielding and rupture (LRFD)."""

from steel_design import Q_
from steel_design.sections import Angle

Tu = Q_(75, "kip")

brace = Angle("L4X4X1/2")  # default material: A36

# Net area: one 3/4-in. bolt hole in the connected leg. The user supplies An and U.
hole = Q_(3 / 4 + 1 / 8, "in")  # bolt diameter plus 1/8 in. (standard hole plus 1/16 in.), Section B4.3
An = brace.A - hole * brace.t
U = 0.8  # shear lag factor (Table D3.1), user-supplied

t = brace.tension_strength(An=An, U=U)
print(f"{brace.name} in {brace.material.name}: Ag = {brace.A:~P}, An = {An:~P.3f}, Ae = {t.Ae:~P.3f}")
for ls in (t.yielding, t.rupture):
    print(f"  {ls.name:<17} {ls.reference}: Pn = {ls.Pn:~P.1f}, phi = {ls.phi}, phi Pn = {ls.phi * ls.Pn:~P.1f}")
print(f"Pu / phi Pn = {(Tu / t.design_strength).to('dimensionless').magnitude:.2f}")

# The shortcuts return the governing limit state
print(f"get_Pnt = {brace.get_Pnt(An=An, U=U):~P.1f}, get_phiPnt = {brace.get_phiPnt(An=An, U=U):~P.1f}")

# Compare with the shear lag factor left at its default of 1.0
print(f"With U = 1.0: phi Pn = {brace.get_phiPnt(An=An):~P.1f}")

# Slenderness of the brace between work points
print(f"L/r_min for 8 ft: {(Q_(8, 'ft') / brace.rz).to('dimensionless').magnitude:.0f}")
