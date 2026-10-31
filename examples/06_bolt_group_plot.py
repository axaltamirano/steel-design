"""Draw an eccentrically loaded bolt group (requires matplotlib: `uv sync` or `pip install steel-design[plot]`)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from steel_design import Q_
from steel_design.bolts import A325, Bolt, BoltGroup

group = BoltGroup.grid(rows=4, cols=2, s_row=Q_(3, "in"), s_col=Q_(3, "in"), bolt=Bolt(Q_(3 / 4, "in"), A325))

ax = group.plot(e=Q_(6, "in"), angle=20)
out = Path(__file__).with_name("06_bolt_group_plot.png")
ax.figure.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved {out.name}")
