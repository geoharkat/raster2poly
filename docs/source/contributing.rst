Contributing
============

Contributions — bug fixes, new algorithms, docs, tests — are welcome.


Development setup
-----------------

.. code-block:: bash

   git clone https://github.com/geoharkat/raster2poly.git
   cd raster2poly
   pip install -e ".[dev]"
   pytest -v


Coding standards
----------------

* All file paths are function arguments — no hardcoded paths.
* Vector → raster CRS reprojection, never the reverse.
* Nodata → NaN on load, excluded from all computation.
* Type hints on all public function signatures.


Adding a new algorithm
----------------------

1. Add the sklearn model to ``classifier.py`` inside ``unsupervised()``
   (for clustering) or create a new method.
2. Register it in ``available_algorithms()``.
3. Add a test in ``tests/test_classifier.py``.
4. Document it in ``docs/source/methods.rst``.


Running tests
-------------

.. code-block:: bash

   pytest -v


Pull request workflow
---------------------

1. Fork → branch → commit → push → PR against ``main``.
2. Ensure all tests pass.
3. Update docs if adding user-facing features.


Reporting issues
----------------

`GitHub Issues <https://github.com/geoharkat/raster2poly/issues>`__ —
include your Python version, ``raster2poly`` version, full traceback,
and a minimal reproducing example.
