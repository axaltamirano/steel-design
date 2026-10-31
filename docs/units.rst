Units
=====

The library is US-customary only. Every dimensional value is a ``pint`` quantity
created from the shared registry in :mod:`steel_design.units`.

.. code-block:: python

   from steel_design import Q_
   Q_(12, "in") + Q_(1, "ft")

Conventions:

* Lengths are inches, stresses are ksi, forces are kips; other compatible units
  convert automatically.
* Dimensionless ratios (``h_tw``, ``b_tf``, ...) are plain floats.
* Constructors that take dimensions (e.g. built-up sections) reject bare numbers
  with ``TypeError`` and non-length quantities with ``ValueError`` via
  :func:`steel_design.units.require_length`.
* The registry adds ``plf``, ``klf``, ``psf`` and ``ksf``.
