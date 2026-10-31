Compression
===========

:mod:`steel_design.compression` implements AISC 360-22 Chapter E: flexural buckling (E3),
torsional and flexural-torsional buckling (E4), single angles (E5) and members with slender
elements (E7). Every section provides
:meth:`~steel_design.sections.base.Section.compression_strength`.

.. code-block:: python

   from steel_design import Q_
   from steel_design.sections import WideFlange

   w = WideFlange("W14X90")
   c = w.compression_strength(Lx=Q_(10, "ft"))   # Ly defaults to Lx, Lz to Ly

   c.design_strength          # governing design strength, phi_c Pn, kip
   c.governing.name           # "torsional buckling"
   c.governing.Fe        # elastic buckling stress, Fe
   c.exceeds_recommended_slenderness   # KL/r > 200 (Section E2)

``Lx``, ``Ly`` and ``Lz`` are the unbraced lengths for buckling about x, about y and for twist;
``Kx``, ``Ky`` and ``Kz`` are the effective length factors. Lengths must be pint quantities.

Strength
--------

``Pn = Fn Ae`` with ``phi_c = 0.90`` (LRFD only). ``Fn`` is ``0.658^(Fy/Fe) Fy``
when ``Fy/Fe <= 2.25`` (E3-2) and ``0.877 Fe`` otherwise (E3-3). ``Ae`` is the gross area
for nonslender sections. The strength is the lowest of the buckling modes of the shape.

Shortcuts
---------

.. code-block:: python

   w.get_Pnc(Q_(10, "ft"))      # nominal strength Pn of the governing limit state, kip
   w.get_phiPnc(Q_(10, "ft"))   # governing design strength phi_c Pn, kip

Buckling modes by shape
-----------------------

==========================  ===============================================================
Shape                       Modes
==========================  ===============================================================
W, M, S, HP                 Flexural about x and y; torsional (E4-2)
Built-up I, doubly sym.     Flexural about x and y; torsional (E4-2)
Built-up I, singly sym.     Flexural about x; flexural-torsional (E4-3)
Channels                    Flexural about y; flexural-torsional with Fex (E4-3)
WT, MT, ST, double angles   Flexural about x; flexural-torsional with Fey (E4-3), no Cw
HSS, pipe, built-up box     Flexural about x and y
Single angles               Flexural about the principal axes, or Section E5
==========================  ===============================================================

Slender elements
----------------

When any element is slender in compression (Table B4.1a), each mode uses the effective area
``Ae = Ag - sum[(b - be) t]`` (E7-1), with ``be`` from E7-2 to E7-5 and ``c1``, ``c2`` from
Table E7.1. Round HSS and pipe use E7-6 and E7-7. The reductions are reported on each limit
state as ``reductions``.

Single angles
-------------

.. code-block:: python

   a = Angle("L4X4X1/2")
   a.compression_strength(Q_(5, "ft"))                 # principal-axis flexural buckling
   a.compression_strength(Q_(5, "ft"), e5="planar")    # E5(a), Eqs. E5-1, E5-2
   a.compression_strength(Q_(5, "ft"), e5="box", connected_leg="short")   # E5(b)

``e5`` raises ``ValueError`` if ``bl/bs >= 1.7`` or ``Lc/r > 200``. The other Section E5
requirements (end connection and no transverse loads) are the user's to confirm.
Flexural-torsional buckling is not checked for single angles: it is only required when
``b/t > 0.71 sqrt(E/Fy)``, and such angles are slender, for which Section E7 takes ``Fn``
from E3.

Assumptions and exclusions
--------------------------

* Double angles: ``J`` is twice that of one angle, and ``Cw`` is omitted in ``Fez``.
* Singly symmetric built-up I-shapes: the shear center uses the same flange inertias as ``Cw``
  (``shear_center_offset``, ``ro`` and ``H``).
* Every slender element of a double angle is checked, using the leg widths ``b`` and ``d``.
* Not included: built-up member connector spacing (E6), bracing offset from the shear center
  (E4(d) to (f)) and the unsymmetric cubic (E4-4).
