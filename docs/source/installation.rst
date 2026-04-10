Installation
============

From PyPI
---------

.. code-block:: bash

   pip install raster2poly

This installs: ``numpy``, ``rasterio``, ``geopandas``, ``scikit-learn``,
``shapely``.


From source
-----------

.. code-block:: bash

   git clone https://github.com/geoharkat/raster2poly.git
   cd raster2poly
   pip install -e ".[dev]"


System requirements
-------------------

* Python ≥ 3.9
* GDAL libraries (pulled in by ``rasterio``)

On some Linux distributions install the GDAL headers first:

.. code-block:: bash

   # Debian / Ubuntu
   sudo apt install libgdal-dev

   # Fedora
   sudo dnf install gdal-devel


Verify
------

.. code-block:: python

   from raster2poly import RasterClassifier
   print("OK")
