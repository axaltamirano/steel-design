"""Check an eccentrically loaded C-shaped fillet weld group by the ICR method (LRFD) and plot it.

The plot needs matplotlib, an optional dependency (`uv sync` or `pip install steel-design[plot]`).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from steel_design import Q_
from steel_design.welds import E70XX, E80XX, FilletWeld, WeldGroup, min_fillet_size

Pu = Q_(30, "kip")  # factored vertical load
e = Q_(8, "in")  # distance from the weld group centroid to the line of action

# Single fillet weld: 5/16-in. E70XX, 10 in. long
weld = FilletWeld(Q_(5 / 16, "in"), Q_(10, "in"))
print(f"{weld}: phi Rn = {weld.design_strength():~P.1f}, minimum size for 3/4-in. plate = {min_fillet_size(Q_(0.75, 'in')):~P.4f}")

# C-shaped group: a 10-in. vertical weld with 4-in. welds along the top and bottom
group = WeldGroup.c_shape(height=Q_(10, "in"), flange=Q_(4, "in"), size=Q_(5 / 16, "in"), electrode=E70XX)
xc, yc = group.centroid
print(f"{group}: centroid {xc:~P.2f} from the back, Ip = {group.Ip:~P.1f}")
print(f"Concentric strength: {group.concentric_strength():~P.1f}")

# Elastic vector method and ICR method for a load 8 in. from the centroid
load_point = (xc + e, yc)
print(f"Elastic: phi Pn = {group.elastic_strength(load_point):~P.1f}")
result = group.icr_strength_eccentric(e)
l = Q_(10, "in")
a = (e / l).to("dimensionless").m
print(f"ICR at x = {result.icr[0]:~P.2f}, phi Pn = {result.Pn:~P.1f}, Pu / phi Pn = {group.check(Pu, e):.2f}")
print(f"Manual Table 8-8 coefficient: a = {a:.2f}, C = {group.icr_coefficient(e, length=l):.2f}")

# An inclined load, and a stronger electrode
print(f"At 30 degrees: phi Pn = {group.icr_strength_eccentric(e, angle=30).Pn:~P.1f}")
e80 = WeldGroup.c_shape(Q_(10, "in"), Q_(4, "in"), Q_(5 / 16, "in"), electrode=E80XX)
print(f"E80XX: phi Pn = {e80.icr_strength_eccentric(e).Pn:~P.1f}")

# Plot the group, load line, eccentricity, ICR and weld forces
ax = group.plot(e=e, angle=30)
out = Path(__file__).with_name("06_bracket_weld_group.png")
ax.figure.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved {out.name}")
