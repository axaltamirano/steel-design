# Built-up sections

Built-up shapes are computed from plate dimensions. Fillets and welds are ignored.

## Wide flange (I-shape)

{class}`~steel_design.sections.built_up_wide_flange.BuiltUpWideFlange` supports
doubly and singly symmetric sections. Bottom flange dimensions default to the top
flange.

```python
from steel_design import Q_
from steel_design.sections import BuiltUpWideFlange

g = BuiltUpWideFlange(d=Q_(24, "in"), bf=Q_(10, "in"), tf=Q_(1, "in"), tw=Q_(0.5, "in"),
                      bf_bottom=Q_(14, "in"), tf_bottom=Q_(1.25, "in"))
g.Sx_top, g.Sx_bottom, g.Zx, g.hc("top"), g.hp("top")
```

Singly symmetric sections provide elastic and plastic neutral axes, `Sx_top` and
`Sx_bottom`, `Zx`, `hc` and `hp`, and `Cw`. `rts` is only available for
doubly symmetric sections.

## Rectangular box

{class}`~steel_design.sections.built_up_box.BuiltUpBox` is a doubly symmetric box of
four plates (outside depth `Ht` and width `B`, flange thickness `tf`, web
thickness `tw`). `J` uses Bredt's formula and `Cw` is zero.

The optional `inset_web_PL` argument moves each web plate inward from the flange edge by
that distance, so each flange plate overhangs the web. The area, `Iy`, `Zy`, `J`, the clear
flange width `b` and the compression slenderness (a `"flange overhang"` element) reflect the
inset; `Ix` and `Zx` are unchanged. Flexural strength is not available for inset webs and
raises `NotImplementedError`.

```python
box = BuiltUpBox(Q_(12, "in"), Q_(10, "in"), Q_(0.5, "in"), Q_(0.375, "in"),
                 inset_web_PL=Q_(1, "in"))
```
