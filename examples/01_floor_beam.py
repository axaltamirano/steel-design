"""Check a simply supported W-shape floor beam for flexure and shear (LRFD)."""

from steel_design import Q_
from steel_design.flexure import cb
from steel_design.sections import WideFlange

# Required strengths from the load combinations
Mu = Q_(180, "kip*ft")
Vu = Q_(45, "kip")

beam = WideFlange("W18X50")  # default material: A992
Lb = Q_(10, "ft")  # distance between braced points

# Cb from Eq. F1-1 for a moment diagram with the quarter-point moments below
Cb = cb(Mmax=Q_(180, "kip*ft"), MA=Q_(135, "kip*ft"), MB=Q_(180, "kip*ft"), MC=Q_(135, "kip*ft"))

flexure = beam.flexure_strength("x", Lb=Lb, Cb=Cb)
shear = beam.shear_strength("x")

print(f"{beam.name} in {beam.material.name}, Lb = {Lb:~P}, Cb = {Cb:.3f}")
print(f"Flange: {beam.flexure_slenderness_x['flange'].classification.value}, "
      f"web: {beam.flexure_slenderness_x['web'].classification.value}")
print(f"Mp = {flexure.Mp.to('kip*ft'):~P.1f}, Lp = {flexure.Lp.to('ft'):~P.2f}, Lr = {flexure.Lr.to('ft'):~P.2f}")
for ls in flexure.limit_states:
    print(f"  {ls.name:<30} {ls.reference:<12} phi Mn = {ls.design_strength:~P.1f}")
print(f"Governing: {flexure.governing.name}")

ratio_m = (Mu / flexure.design_strength).to("dimensionless").magnitude
ratio_v = (Vu / shear.design_strength).to("dimensionless").magnitude
print(f"Flexure: Mu / phi Mn = {Mu:~P} / {flexure.design_strength:~P.1f} = {ratio_m:.2f}")
print(f"Shear:   Vu / phi Vn = {Vu:~P} / {shear.design_strength:~P.1f} = {ratio_v:.2f}  ({shear.reference})")
print("OK" if max(ratio_m, ratio_v) <= 1.0 else "NG")

# The same beam with the unbraced length varied: the LTB check starts above Lp
print("\nLb (ft)   phi Mn (kip-ft)")
for L in (4, 8, 12, 16, 20, 25):
    print(f"{L:>6}   {beam.get_phiMnx(Q_(L, 'ft'), Cb).to('kip*ft').magnitude:.1f}")
