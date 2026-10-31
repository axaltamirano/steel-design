"""Check an HSS column for compression and compare effective lengths (LRFD)."""

from steel_design import Q_
from steel_design.materials import A500GrCRect
from steel_design.sections import HSSRect

Pu = Q_(250, "kip")

col = HSSRect("HSS8X8X3/8", A500GrCRect)
print(f"{col.name} in {col.material.name}: Fy = {col.material.Fy:~P}")
print(f"Compression classification: {col.compression_slenderness.governing.value}")
for el in col.compression_slenderness.elements:
    print(f"  {el.element}: {el.ratio:.1f} (limit {el.limit_r:.1f}) -> {el.classification.value}")

# Pinned-pinned and a sway-frame effective length; Ly and Lz default to Lx
for label, K in (("K = 1.0", 1.0), ("K = 1.5", 1.5)):
    c = col.compression_strength(Lx=Q_(12, "ft"), Kx=K, Ky=K)
    print(f"\n{label}: {c.governing.name}")
    print(f"  Fe = {c.governing.Fe:~P.1f}, phi Pn = {c.design_strength:~P.1f}")
    print(f"  Pu / phi Pn = {(Pu / c.design_strength).to('dimensionless').magnitude:.2f}")
    print(f"  KL/r > 200: {c.exceeds_recommended_slenderness}")

# Shortcut for the governing design strength
print(f"\nget_phiPnc: {col.get_phiPnc(Q_(12, 'ft')):~P.1f}")

# A thin-walled HSS has a slender wall, so the effective area of Section E7 is used
thin = HSSRect("HSS8X8X3/16", A500GrCRect)
r = thin.compression_strength(Lx=Q_(12, "ft"))
print(f"\n{thin.name}: {thin.compression_slenderness.governing.value}, phi Pn = {r.design_strength:~P.1f}")
