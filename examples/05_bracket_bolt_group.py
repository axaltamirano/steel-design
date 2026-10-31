"""Check an eccentrically loaded bracket bolt group by the ICR method (LRFD)."""

from steel_design import Q_
from steel_design.bolts import A325, Bolt, BoltGroup, Ply, SlipClass

Pu = Q_(40, "kip")  # factored vertical load
e = Q_(6, "in")  # distance from the bolt group centroid to the line of action

# Single bolt: 3/4-in. A325-N in a standard hole
bolt = Bolt(Q_(3 / 4, "in"), A325)
print(f"{bolt}: phi Rnv = {bolt.get_phiRnv():~P.1f}, phi Rnt = {bolt.get_phiRnt():~P.1f}")
print(f"Slip resistance, Class A: {bolt.slip_resistance(SlipClass.A).design_strength:~P.2f}")

# Bearing and tearout in a 1/2-in. A36 bracket plate: 1-1/4 in. edge distance, 3 in. spacing
hole = bolt.hole_dimensions[1]
ply = Ply(Q_(0.5, "in"), Q_(58, "ksi"), Q_(1.25, "in") - hole / 2)
print(f"Bearing/tearout: {bolt.bearing_tearout_strength(ply).design_strength:~P.1f}")

# Two columns of four bolts at 3 in. spacing, with the plate data applied to every bolt
group = BoltGroup.grid(rows=4, cols=2, s_row=Q_(3, "in"), s_col=Q_(3, "in"), bolt=bolt, plies=ply)
print(f"Concentric strength: {group.concentric_strength():~P.1f}")

result = group.icr_strength_eccentric(e)
print(f"ICR at x = {result.icr[0]:~P.2f} from the centroid")
print(f"C = {result.C:.2f}, phi Pn = {result.Pn:~P.1f}, Pu / phi Pn = {group.check(Pu, e):.2f}")

# A load inclined 30 degrees from the vertical, and a bolt group of arbitrary geometry
print(f"At 30 degrees: C = {group.icr_coefficient(e, angle=30):.2f}")
odd = BoltGroup([(Q_(x, "in"), Q_(y, "in")) for x, y in [(0, 0), (3, 0), (6, 0), (0, 4), (6, 4)]], bolt)
print(f"Arbitrary group, load at (9, 2) in.: phi Pn = {odd.icr_strength((Q_(9, 'in'), Q_(2, 'in'))).Pn:~P.1f}")
