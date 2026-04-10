Introduction
============

**raster2poly** turns multi-band rasters into classified polygon layers
in a single function call.  It wraps scikit-learn clustering and
classification behind a GIS-native API — you give it a GeoTIFF, you get
back a GeoDataFrame of dissolved, filtered polygons ready for QGIS or
ArcGIS.


Why this package?
-----------------

Converting a classified raster to usable vector polygons is a common GIS
task, but the standard workflow involves half-a-dozen steps: read bands,
mask nodata, flatten to feature arrays, run a classifier, reshape,
polygonise, dissolve, filter.  **raster2poly** collapses all of that into
a single class with three classification methods and clean output.


Supported methods
-----------------

.. list-table::
   :widths: 25 35 40
   :header-rows: 1

   * - Method
     - API
     - When to use
   * - **KMeans**
     - ``clf.unsupervised(algorithm="kmeans")``
     - Quick exploratory clustering, < 10 M pixels
   * - **MiniBatchKMeans**
     - ``clf.unsupervised(algorithm="mini_batch_kmeans")``
     - Large rasters (> 10 M pixels), lower RAM
   * - **Random Forest**
     - ``clf.supervised(roi_path=...)``
     - You have labelled training ROIs (Points or Polygons)
   * - **DN range rules**
     - ``clf.from_dn_ranges(rules=...)``
     - You know the spectral signature of each class

All methods return a ``GeoDataFrame`` with ``class_id`` and ``geometry``
columns.  Adjacent same-class polygons are dissolved by default, and a
``min_area`` filter removes speckle.


Utility helpers
---------------

``clf.band_stats()``
   Print min / max / mean / std for every band — essential before
   writing DN-range rules.

``clf.available_algorithms()``
   List all supported algorithms with usage examples.

``clf.encode_roi(path, label_col="Age")``
   Convert a text label column (e.g. *Holocene*, *Jurassic*) to
   consecutive integer IDs and save the encoded shapefile — no
   external pandas step required.


Design principles
-----------------

* **No hardcoded paths** — every file path is a function argument.
* **CRS safety** — ROI vectors are always reprojected to the raster CRS,
  never the reverse.
* **Nodata → NaN** — on load, nodata values are replaced with NaN and
  excluded from all computation.
* **Format detection** — ``clf.save()`` infers ``.shp`` / ``.gpkg`` /
  ``.geojson`` from the file extension.
