Flexure
=======

:mod:`steel_design.flexure` implements AISC 360-22 Chapter F. Every section provides
:meth:`~steel_design.sections.base.Section.flexure_strength`.

.. code-block:: python

   from steel_design import Q_
   from steel_design.sections import WideFlange

   w = WideFlange("W14X90")
   f = w.flexure_strength("x", Lb=Q_(8, "ft"), Cb=1.0)

   f.design_strength     # governing phi_b Mn, kip-ft
   f.governing.name      # "lateral-torsional buckling" or "yielding"
   f.Mp, f.Lp, f.Lr      # plastic moment and LTB limits

``Lb`` must be a pint length and is required wherever lateral-torsional buckling can apply.
``Cb`` is user-supplied (default 1.0); :func:`steel_design.flexure.cb` evaluates Eq. F1-1.

Shortcuts
---------

.. code-block:: python

   w.get_Mnx(Q_(8, "ft"))       # nominal strength of the governing limit state
   w.get_phiMnx(Q_(8, "ft"))    # phi_b Mn, phi_b = 0.90
   w.get_Mny()                  # minor axis; get_phiMny also available

Angles also provide ``get_Mnw``, ``get_phiMnw``, ``get_Mnz`` and ``get_phiMnz``.

Sections by shape
-----------------

==========================  ===============================================================
Shape                       Sections
==========================  ===============================================================
W, M, S, HP                 F2/F3 (compact web), F4/F5 (noncompact or slender web); F6 minor
Built-up I                  F2/F3 doubly symmetric, F4/F5 otherwise; ``compression_flange``
Channels                    F2 with ``c`` from F2-8a/b; F6 minor
Rectangular HSS, box        F7 (slender flange effective width)
Round HSS, pipe             F8
WT, MT, ST                  F9, ``stem="tension"`` or ``"compression"``
Double angles               F9 and F10.3, ``web_legs="tension"`` or ``"compression"``
Single angles               F10, ``axis="w"``, ``"z"`` (or ``"x"``, ``"y"`` for equal legs)
==========================  ===============================================================

Single-angle options are ``compression_leg``, ``toe_in_compression``, ``lateral_restraint`` and
``beta_w``. ``Cb`` is limited to 1.5 for angles.

Assumptions and exclusions
--------------------------

* Not included: F11, F12, F13.1 (tension-flange holes) and H2 combined loading.
* Channels with noncompact or slender elements raise ``NotImplementedError`` (F12).
* Tees and double angles in minor-axis bending raise ``NotImplementedError``.
* Round HSS with ``D/t >= 0.45 E/Fy`` raises ``ValueError``.
* Singly symmetric I web slenderness uses ``hc/tw`` (Case 16).
* ``Rpt`` uses the same ``lambda_pw`` and ``lambda_rw`` as ``Rpc``.
* ``beta_w`` for unequal-leg angles is computed numerically; override it with ``beta_w``.
* Boxes with both a slender flange and a slender web are not addressed by the Specification.
