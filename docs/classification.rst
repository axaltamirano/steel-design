Section classification
======================

:mod:`steel_design.classification` implements AISC 360-22 Section B4 (Tables B4.1a
and B4.1b).

.. code-block:: python

   from steel_design.classification import classify_compression, classify_flexure

   r = classify_flexure(w, axis="x")
   r["flange"].classification, r["web"].ratio, r.governing

``classify_compression`` returns *nonslender* or *slender* per element.
``classify_flexure`` returns *compact*, *noncompact* or *slender*. Results are a
:class:`~steel_design.classification.SectionClassification`; each element carries
its ratio, limits, result and Table B4 case reference.

Supported shapes: rolled I (W, M, S, HP), channels, tees, single and double angles,
rectangular and round HSS, pipe, built-up I and built-up box.

Options
-------

* ``compression_flange="top"|"bottom"``: singly symmetric built-up I-shapes in
  major-axis flexure.
* ``continuous_contact`` (``DoubleAngle`` constructor): ``False`` uses Case 3 (0.45),
  ``True`` uses Case 1 (0.56).

Notable cases
-------------

* Built-up box: flange flexure Case 21 (1.12/1.49), compression Case 8 (1.49).
* Minor-axis flange of I-shapes and channels: Case 13.
* Singly symmetric web: Case 16, ``kc`` limited to 0.35-0.76 and ``FL`` per Table B4.1b.

Assumptions and limitations
---------------------------

* Limits use the section material's ``Fy``.
* Case 16 takes ``My`` as ``Fy`` times the smaller elastic modulus and ``Mp = Fy Zx``
  without the 1.6 ``Fy Sx`` cap; ``λp`` is set to ``λr`` when ``hp <= 0``.
* Double angles in flexure reuse single-angle Case 12.
* Tee flexure about the y-axis checks the flange only.
