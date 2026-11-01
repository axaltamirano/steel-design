"""Plot of a weld group with its load line, eccentricity and instantaneous center of rotation.

Requires matplotlib (``pip install steel-design[plot]``), which is imported only when plotting.
"""

from __future__ import annotations

import math

from steel_design.welds.group import WeldGroup, WeldICRResult, _direction, _xy


def _pyplot():
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(
            "Plotting requires matplotlib: install it with `pip install steel-design[plot]`"
        ) from exc
    return plt


def plot_weld_group(
    group: WeldGroup,
    result: WeldICRResult | None = None,
    load_point=None,
    angle: float = 0.0,
    ax=None,
    show_forces: bool = True,
    title: str | None = None,
):
    """Draw a weld group, the line of action of the load, the eccentricity and the ICR.

    Args:
        group: The weld group.
        result: An ICR result from the same group; supplies the ICR and the element forces.
        load_point: ``(x, y)`` of a point on the load line. Required to draw the load.
        angle: Load angle from the vertical, degrees (0 acts downward).
        ax: Existing matplotlib axes to draw on; a new figure is created when omitted.
        show_forces: Draw the force on every few weld elements (needs ``result``).
        title: Optional title.

    Returns:
        The matplotlib axes.
    """
    plt = _pyplot()

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))

    xc, yc = (c.m for c in group.centroid)
    xs, ys = [], []
    for line in group.lines:
        (x1, y1), (x2, y2) = _xy(line.start), _xy(line.end)
        ax.plot([x1, x2], [y1, y2], color="#1f3a5f", lw=2 + 12 * line.size.m, solid_capstyle="butt", zorder=3)
        xs += [x1, x2]
        ys += [y1, y2]
    size = max(math.hypot(x - xc, y - yc) for x, y in zip(xs, ys)) or 1.0
    ax.plot([xc], [yc], marker="+", ms=14, mew=1.8, color="#c0392b", zorder=4)
    ax.annotate("centroid", (xc, yc), xytext=(6, -14), textcoords="offset points", fontsize=8, color="#c0392b")

    if load_point is not None:
        px, py = _xy(load_point)
        ux, uy = _direction(angle)
        span = max(3.0 * size, abs(px - xc) + abs(py - yc) + 2 * size)
        ax.plot([px - ux * span, px + ux * span * 0.35], [py - uy * span, py + uy * span * 0.35], ls=":", lw=0.8, color="#b03030", zorder=1)
        arrow_len = 1.2 * size
        ax.annotate(
            "",
            xy=(px, py),
            xytext=(px - ux * arrow_len, py - uy * arrow_len),
            arrowprops=dict(arrowstyle="-|>", color="#b03030", lw=2.2, mutation_scale=18),
            zorder=5,
        )
        label = "P" if result is None else f"Pn = {result.Pn.to('kip').m:.1f} kip"
        ax.annotate(label, (px - ux * arrow_len, py - uy * arrow_len), xytext=(6, 6), textcoords="offset points", color="#b03030", fontsize=9, fontweight="bold")

        t = (xc - px) * ux + (yc - py) * uy
        fx, fy = px + t * ux, py + t * uy
        e = math.hypot(fx - xc, fy - yc)
        if e > 1e-9:
            ax.annotate("", xy=(fx, fy), xytext=(xc, yc), arrowprops=dict(arrowstyle="<->", color="#2b7a3d", lw=1.4), zorder=4)
            ax.annotate(f"e = {e:.2f} in.", ((xc + fx) / 2, (yc + fy) / 2), xytext=(0, 7), textcoords="offset points", ha="center", color="#2b7a3d", fontsize=9, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5), zorder=7)
        xs += [px, fx, px - ux * arrow_len]
        ys += [py, fy, py - uy * arrow_len]

    if result is not None and result.icr is not None:
        ix, iy = result.icr[0].m, result.icr[1].m
        if math.hypot(ix - xc, iy - yc) < 6 * size + 20:
            ax.plot([ix], [iy], marker="X", ms=11, color="#d98324", mec="k", zorder=6)
            ax.annotate("ICR", (ix, iy), xytext=(7, 7), textcoords="offset points", fontsize=9, color="#a35a0f", fontweight="bold")
            xs.append(ix)
            ys.append(iy)
        if show_forces:
            forces = result.element_forces
            peak = max(math.hypot(f[2], f[3]) / (group.total_length.m / len(forces)) for f in forces) or 1.0
            scale = 0.3 * size / peak
            step = max(1, group.n_elements // 8)
            per_line = group.n_elements
            for i, (x, y, fx, fy) in enumerate(forces):
                if i % per_line % step != step // 2:
                    continue
                length = group.total_length.m / len(forces)
                ax.annotate(
                    "",
                    xy=(x + fx / length * scale, y + fy / length * scale),
                    xytext=(x, y),
                    arrowprops=dict(arrowstyle="-|>", color="#6a3d9a", lw=1.2, mutation_scale=9),
                    zorder=5,
                )

    pad = max(1.0, 0.25 * size)
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, lw=0.3, alpha=0.5)
    ax.set_xlabel("x (in.)")
    ax.set_ylabel("y (in.)")
    if title is None:
        title = f"Weld group, {group.total_length.m:g} in. of {group.electrode.name}"
        if result is not None:
            title += f", angle {angle:g}°"
    ax.set_title(title, fontsize=10)
    return ax


__all__ = ["plot_weld_group"]
