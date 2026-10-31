Getting started
===============

Installation
------------

The project uses `uv <https://docs.astral.sh/uv/>`_ and requires Python 3.13.

.. code-block:: console

   $ uv sync
   $ uv run pytest -q

Quick example
-------------

.. code-block:: python

   from steel_design import Q_
   from steel_design.sections import get_shape

   w = get_shape("W14X90")            # default material: A992
   w.Ix                               # <Quantity(999.0, 'inch ** 4')>
   w.flexure_slenderness_x.governing  # Slenderness.NONCOMPACT (flange)

Building the documentation
--------------------------

.. code-block:: console

   $ uv run make -C docs html

The output is written to ``docs/_build/html``.

Scope
-----

Implemented so far: materials, the shapes database, built-up sections and
Section B4 local-buckling classification, Chapter D tension (D1 to D3) and Chapter E
compression. Limit states for flexure and shear (Chapters F, G) are planned.
