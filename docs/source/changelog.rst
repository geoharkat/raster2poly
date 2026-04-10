Changelog
=========

0.1.0 (2025)
-------------

* Initial release.
* Unsupervised classification: KMeans, MiniBatchKMeans.
* Supervised classification: Random Forest from ROI shapefiles.
* Rule-based classification: per-band DN-range thresholds.
* ``encode_roi()`` — convert string labels to integer IDs.
* ``band_stats()`` — per-band min / max / mean / std.
* ``available_algorithms()`` — formatted algorithm reference.
* Polygon dissolve and min-area filtering.
* Auto-format detection for ``.shp`` / ``.gpkg`` / ``.geojson``.
* Nodata → NaN handling throughout.
* CRS auto-reprojection (vector → raster).
