Quick start
===========

Installation
------------

.. code-block:: bash

   pip install raster2poly


Unsupervised classification
---------------------------

.. code-block:: python

   from raster2poly import RasterClassifier

   clf = RasterClassifier("satellite.tif")
   gdf = clf.unsupervised(n_clusters=6, algorithm="mini_batch_kmeans")
   clf.save(gdf, "kmeans.gpkg")

``mini_batch_kmeans`` is recommended for rasters larger than ~10 M pixels.


Supervised classification (ROI shapefile)
-----------------------------------------

Prepare a shapefile with a ``class_id`` column (integer labels).
It may contain **Points, Polygons, or both**.

.. code-block:: python

   gdf = clf.supervised("rois.shp", class_col="class_id", n_estimators=200)
   clf.save(gdf, "supervised.shp")

For polygon ROIs, every pixel inside the geometry is used as a training
sample — much more robust than a single zonal mean.


Rule-based classification (DN ranges)
--------------------------------------

.. code-block:: python

   rules = {
       1: [(4, 0.15, 1.0), (5, 0.0, 0.10)],  # high Red AND low NIR
       2: [(5, 0.25, 1.0)],                     # high NIR
   }
   gdf = clf.from_dn_ranges(rules)

Band numbers are **1-based**.  A pixel must satisfy *all* conditions
in its list.


Polygon options
---------------

All methods accept:

``dissolve=True``
   Merge adjacent polygons of the same class (default).

``min_area=0.0``
   Drop polygons smaller than this threshold (in map units²).
   Useful for removing tiny speckle polygons.


Output formats
--------------

.. code-block:: python

   clf.save(gdf, "out.shp")       # Shapefile
   clf.save(gdf, "out.gpkg")      # GeoPackage
   clf.save(gdf, "out.geojson")   # GeoJSON
