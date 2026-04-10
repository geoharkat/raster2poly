raster2poly |version|
=====================

.. image:: https://img.shields.io/pypi/v/raster2poly.svg
   :target: https://pypi.org/project/raster2poly/
.. image:: https://img.shields.io/pypi/pyversions/raster2poly.svg
.. image:: https://readthedocs.org/projects/raster2poly/badge/
   :target: https://raster2poly.readthedocs.io

**Classify rasters and vectorise the result to clean, dissolved polygons
— in three lines of code.**

.. code-block:: python

   from raster2poly import RasterClassifier

   clf = RasterClassifier("satellite.tif")
   gdf = clf.unsupervised(n_clusters=6)
   clf.save(gdf, "classes.gpkg")

----

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   introduction
   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   methods
   cookbook

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog


Indices
-------

* :ref:`genindex`
* :ref:`modindex`
