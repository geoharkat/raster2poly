# raster2poly

**Classify rasters and vectorise the result to clean polygons** — in three lines of code.

Supports unsupervised clustering (KMeans), supervised classification
(Random Forest from ROI shapefiles), and rule-based DN thresholds.
Outputs are dissolved, filtered GeoDataFrames ready for GIS.

## Installation

```bash
pip install raster2poly
```

## Quick start

### Unsupervised (KMeans)

```python
from raster2poly import RasterClassifier

clf = RasterClassifier("satellite_image.tif")
gdf = clf.unsupervised(n_clusters=6, algorithm="mini_batch_kmeans")
clf.save(gdf, "classes.gpkg")
```

### Supervised (ROI shapefile)

```python
gdf = clf.supervised("training_rois.shp", class_col="class_id")
clf.save(gdf, "supervised.shp")
```

The ROI file can contain **Points or Polygons** (or both).
For polygons, every pixel inside the geometry is used as a training
sample — far more robust than a single zonal mean.

### Rule-based (DN ranges)

```python
rules = {
    1: [(4, 0.15, 1.0), (5, 0.0, 0.10)],  # high Red, low NIR → built-up
    2: [(5, 0.25, 1.0)],                     # high NIR → vegetation
}
gdf = clf.from_dn_ranges(rules)
```

Band numbers are **1-based**.  A pixel must satisfy *all* conditions
in the list to be assigned that class.

## Key improvements over the original script

| Issue in original | Fix |
|---|---|
| `point_query` returns wrong shape for multi-band | Replaced with per-pixel rasterised extraction |
| Only zonal *mean* used for polygon ROIs | Every pixel inside the polygon is a training sample |
| Hardcoded `'class'` column name | Configurable `class_col` parameter |
| No polygon dissolve — millions of tiny fragments | `dissolve=True` by default, plus `min_area` filter |
| `rasterstats` dependency for simple ops | Replaced with `rasterio.features.geometry_mask` |
| No CRS check on ROI shapefile | Auto-reprojects vector → raster CRS |
| Output always Shapefile | Auto-detects `.shp` / `.gpkg` / `.geojson` |
| No nodata → NaN conversion | Nodata replaced with NaN on load, masked throughout |

## Output format

The returned `GeoDataFrame` has two columns:

- `class_id` (int) — the class label
- `geometry` — dissolved polygons

Save to any format: `.shp`, `.gpkg`, `.geojson`.

## License

MIT
