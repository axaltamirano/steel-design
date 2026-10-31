Shear
=====

:mod:`steel_design.shear` implements AISC 360-22 Chapter G. Every section provides
:meth:`~steel_design.sections.base.Section.shear_strength`.

.. code-block:: python

   from steel_design import Q_
   from steel_design.sections import WideFlange

   w = WideFlange("W14X90")
   v = w.shear_strength("x")

   v.design_strength    # phi_v Vn, kip
   v.reference          # "Eq. G2-1, G2.1(a)"
   v.Cv, v.kv           # web shear coefficient and buckling coefficient

``axis`` is the axis of bending the shear accompanies, as in flexure: ``"x"`` is shear parallel
to the web (strong axis) and ``"y"`` is shear parallel to the flanges (minor axis).

Shortcuts
---------

.. code-block:: python

   w.get_Vnx()       # nominal strength Vn, kip
   w.get_phiVnx()    # design strength phi_v Vn, kip
   w.get_Vny()
   w.get_phiVny()

Resistance factors
------------------

``phi_v = 0.90`` (G1). ``phi_v = 1.00`` applies only to rolled W, M, S and HP shapes with
``h/tw <= 2.24 sqrt(E/Fy)`` (G2.1(a)); this depends on the material, so the same shape can
take either factor. Both are in :class:`~steel_design.resistance_factors.ResistanceFactors`.

Sections by shape
-----------------

==========================  ===============================================================
Shape                       Provisions
==========================  ===============================================================
W, M, S, HP                 x: G2.1(a), or G2.1(b) beyond the limit; y: G6, two flanges
Channels                    x: G2.1(b); y: G6, two flanges with ``h/tw = bf/tf``
Built-up I                  x: G2.1(b) and G2.2; y: G6, sum over both flanges
WT, MT, ST                  x: G3 stem (``b = d``); y: G6, the flange
Single angle                G3, for the ``leg`` (``"long"`` or ``"short"``) parallel to the shear
Double angles               G3, two angles; x uses the web legs and y the flange legs
Rectangular HSS, box        G4, two walls, ``kv = 5``
Round HSS, pipe             G5, ``Vn = Fcr Ag / 2``
==========================  ===============================================================

Stiffened webs
--------------

Pass the clear stiffener spacing ``a`` to an I-shape or channel to get ``kv`` from Eq. G2-5.
When ``a/h <= 3`` and the web is slender, tension field action (G2.2, Eq. G2-7 or G2-8) is
used if it exceeds the G2.1 strength; the larger is returned and ``name`` reports which.

.. code-block:: python

   from steel_design.sections import BuiltUpWideFlange

   g = BuiltUpWideFlange(Q_(60, "in"), Q_(12, "in"), Q_(1, "in"), Q_(0.375, "in"))
   g.shear_strength("x", a=Q_(60, "in")).name    # "tension field action"

Round HSS
---------

``Lv``, the distance from maximum to zero shear, enables Eq. G5-2a. Without it only Eq. G5-2b
is used, which is conservative.

Assumptions and exclusions
--------------------------

* Not included: end web panels with tension field action (G2.3), transverse stiffener design
  (G2.4) and web openings (G7).
* Tee stems use the overall depth ``d`` as ``b``, matching the database ``D/t``.
* Rectangular HSS use the flat wall width, outside dimension less ``3t``, as ``h``.
* Built-up I-shapes take ``h`` as the clear distance between flanges (welded). For a bolted
  girder the distance between fastener lines is not modelled.
* Angle and double-angle legs are checked in shear only; Section H3.3 (unsymmetric sections)
  is not addressed.
* Eq. G2-11 uses the Specification's constant 1.51, so ``Cv2`` is very slightly discontinuous
  at ``h/tw = 1.37 sqrt(kv E/Fy)``.
