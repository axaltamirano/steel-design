"""Check a built-up singly symmetric plate girder (LRFD)."""

from steel_design import Q_
from steel_design.materials import A572Gr50
from steel_design.sections import BuiltUpWideFlange

Mu = Q_(3200, "kip*ft")
Vu = Q_(260, "kip")

girder = BuiltUpWideFlange(
    d=Q_(60, "in"), bf=Q_(16, "in"), tf=Q_(1.25, "in"), tw=Q_(0.4375, "in"),
    material=A572Gr50, bf_bottom=Q_(12, "in"), tf_bottom=Q_(1.0, "in"),
)
print(f"{girder.name}: A = {girder.A:~P.1f}, Sx(top) = {girder.Sx_top:~P.0f}, Sx(bottom) = {girder.Sx_bottom:~P.0f}")

# Classification depends on which flange is in compression (positive moment: top)
c = girder.classify_flexure("x", compression_flange="top")
for el in c.elements:
    print(f"  {el.element}: {el.ratio:.1f} -> {el.classification.value} ({el.reference})")

Lb = Q_(8, "ft")
f = girder.flexure_strength("x", Lb=Lb, Cb=1.14, compression_flange="top")
print(f"\nFlexure, Lb = {Lb:~P}: governing {f.governing.name} ({f.governing.reference})")
print(f"  phi Mn = {f.design_strength:~P.0f}, Mu / phi Mn = {(Mu / f.design_strength).to('dimensionless').magnitude:.2f}")

# Shear: unstiffened, then with transverse stiffeners every 60 in.
for a in (None, Q_(60, "in"), Q_(45, "in")):
    s = girder.shear_strength("x") if a is None else girder.shear_strength("x", a=a)
    label = "unstiffened" if a is None else f"a = {a:~P}"
    print(f"Shear, {label:<14} {s.name:<20} kv = {s.kv:.2f}  phi Vn = {s.design_strength:~P.0f}"
          f"  Vu / phi Vn = {(Vu / s.design_strength).to('dimensionless').magnitude:.2f}")
