Quick start
===========

Three lines, any method.


Unsupervised
------------

.. code-block:: python

   from raster2poly import RasterClassifier

   clf = RasterClassifier("satellite.tif")
   gdf = clf.unsupervised(n_clusters=6, algorithm="mini_batch_kmeans")
   clf.save(gdf, "clusters.gpkg")


Supervised (ROI shapefile)
--------------------------

.. code-block:: python

   # If your labels are strings, encode them first:
   out_path, mapping = clf.encode_roi("training.shp", label_col="LandCover")
   #  1: Bare soil
   #  2: Forest
   #  3: Water
   #  ...

   gdf = clf.supervised(roi_path=out_path, class_col="class_id")
   clf.save(gdf, "supervised.geojson")


Rule-based (DN ranges)
-----------------------

.. code-block:: python

   # Check band value ranges first
   clf.band_stats()

   rules = {
       1: [(4, 0.15, 1.0), (5, 0.0, 0.10)],  # high band 4, low band 5
       2: [(5, 0.25, 1.0)],                     # high band 5
   }
   gdf = clf.from_dn_ranges(rules)
   clf.save(gdf, "dn_rules.gpkg")
