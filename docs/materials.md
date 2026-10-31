# Materials

{class}`~steel_design.materials.base.SteelMaterial` holds constants that never
change (`E`, `G`, `nu`, `density`, `alpha`). Each grade is a subclass
defining `name`, `astm`, `Fy` and `Fu`. Materials are used as classes and
never instantiated.

```python
from steel_design.materials import A992, get_material
A992.Fy                    # 50 ksi
get_material("A572 Gr 50") # lookup ignores case and punctuation
```

Grades with strength levels that differ by thickness or group get separate classes.

## Available grades

A992, A36, A572 Gr. 42/50/55/60/65, A588 Gr. 50, A913 Gr. 50/60/65/70,
A500 Gr. B and C (round and rectangular), A53 Gr. B, A529 Gr. 50/55, A1085.

:::{note}
Fy/Fu for A500, A53, A529 and A588 should be verified against Manual Table 2-4.
:::

## Default materials

```{eval-rst}
.. list-table::
   :header-rows: 1

   * - Family
     - Default
   * - W, WT
     - A992
   * - M, S, C, MC, L, 2L, MT, ST
     - A36
   * - HP
     - A572 Gr. 50
   * - HSS (rectangular / round)
     - A500 Gr. C
   * - Pipe
     - A53 Gr. B
   * - Built-up I and box
     - A572 Gr. 50
```

Defaults live in `DEFAULT_MATERIALS` and are returned by
{func}`~steel_design.materials.defaults.default_material_for`.
