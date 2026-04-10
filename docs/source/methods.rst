Classification methods
======================

This page explains each method in detail, when to use it, and what the
parameters do.


Unsupervised — ``clf.unsupervised()``
--------------------------------------

Groups pixels into *k* spectral clusters with no training data.

.. code-block:: python

   gdf = clf.unsupervised(
       n_clusters=5,
       algorithm="kmeans",          # or "mini_batch_kmeans"
       dissolve=True,               # merge adjacent same-class polygons
       min_area=50.0,               # drop polygons < 50 m²
   )

**Algorithm choice:**

``"kmeans"``
   Standard Lloyd's algorithm.  Loads all valid pixels into RAM.
   Best for rasters under ~10 M pixels.

``"mini_batch_kmeans"``
   Processes pixels in batches of 10 000.  Convergence is slightly
   noisier but uses far less memory and runs much faster on large
   scenes.

.. tip::

   Call ``RasterClassifier.available_algorithms()`` to see all options
   with inline usage examples.


Supervised — ``clf.supervised()``
----------------------------------

Trains a Random Forest classifier from labelled training geometries.

.. code-block:: python

   gdf = clf.supervised(
       roi_path="training_rois.shp",
       class_col="class_id",        # column with integer labels
       n_estimators=100,             # RF trees
       dissolve=True,
       min_area=25.0,
   )

**ROI requirements:**

* The file may contain **Points, Polygons, or both** (mixed geometry).
* For polygons, *every pixel inside the geometry* is used as a training
  sample — no lossy zonal-mean shortcut.
* The label column must contain **integers**.  If you have string labels,
  use :meth:`~raster2poly.RasterClassifier.encode_roi` first.
* CRS is automatically reprojected to match the raster — never the
  reverse.

**After classification** the fitted model is available at
``clf._last_model``.  Use it to inspect feature importances:

.. code-block:: python

   importances = clf._last_model.feature_importances_


Rule-based — ``clf.from_dn_ranges()``
---------------------------------------

Classify pixels by per-band value thresholds.  No training data and no
statistical model — you define the rules from domain knowledge.

.. code-block:: python

   rules = {
       1: [(4, 0.15, 1.0), (5, 0.0, 0.10)],   # class 1: high B4 AND low B5
       2: [(5, 0.25, 1.0)],                      # class 2: high B5
   }
   gdf = clf.from_dn_ranges(rules)

**Rule format:** ``{class_id: [(band, min, max), …]}``

* Band numbers are **1-based**.
* A pixel must satisfy **all** conditions in the list to be assigned
  that class.
* If multiple rules overlap, the **last matching class wins**.
* Class 0 is reserved for nodata / unclassified.

.. tip::

   Run ``clf.band_stats()`` first to see min / max / mean / std for
   every band, then design rules accordingly.


Utility helpers
---------------

``available_algorithms()``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Print a formatted list of all supported algorithms with usage snippets.
Works as a static method or on an instance:

.. code-block:: python

   RasterClassifier.available_algorithms()
   # — or —
   clf.available_algorithms()


``band_stats()``
^^^^^^^^^^^^^^^^

Print per-band statistics directly from the raster:

.. code-block:: python

   clf.band_stats()
   # Band  1: min=0.8706  max=10.4115  mean=2.1423  std=0.9812
   # Band  2: min=0.4902  max=1.6621   mean=0.9134  std=0.1089
   # ...


``encode_roi()``
^^^^^^^^^^^^^^^^

Convert a string/categorical label column to consecutive integer IDs:

.. code-block:: python

   out_path, mapping = clf.encode_roi(
       "geology.shp",
       label_col="Formation",
   )
   # mapping = {'Alluvium': 1, 'Granite': 2, 'Schist': 3}

   # Feed directly into supervised():
   gdf = clf.supervised(roi_path=out_path, class_col="class_id")

Labels are sorted alphabetically and numbered from 1 (0 is reserved
for nodata).  The encoded file is saved next to the input by default.


Polygon options (all methods)
-----------------------------

``dissolve`` (default ``True``)
   Merge adjacent polygons of the same class into single features,
   then explode MultiPolygons to simple Polygons.

``min_area`` (default ``0.0``)
   Drop polygons smaller than this threshold (in map units²).
   Set to e.g. ``50.0`` to remove 1–2 pixel speckle.


Output formats
--------------

``clf.save()`` auto-detects format from the file extension:

.. code-block:: python

   clf.save(gdf, "out.shp")       # Shapefile
   clf.save(gdf, "out.gpkg")      # GeoPackage (recommended)
   clf.save(gdf, "out.geojson")   # GeoJSON
