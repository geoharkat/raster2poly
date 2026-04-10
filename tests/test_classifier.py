"""Tests for raster2poly."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from raster2poly import RasterClassifier


@pytest.fixture
def sample_raster(tmp_path):
    """Create a small 3-band test raster with two distinct clusters."""
    h, w, bands = 50, 50, 3
    data = np.zeros((bands, h, w), dtype=np.float32)
    # Cluster A: top-left quadrant
    data[:, :25, :25] = np.array([0.8, 0.1, 0.1])[:, None, None]
    # Cluster B: bottom-right quadrant
    data[:, 25:, 25:] = np.array([0.1, 0.1, 0.8])[:, None, None]
    # Add some noise
    rng = np.random.default_rng(42)
    data += rng.normal(0, 0.02, data.shape).astype(np.float32)
    data = np.clip(data, 0, 1)

    path = tmp_path / "test.tif"
    transform = from_bounds(0, 0, 50, 50, w, h)
    with rasterio.open(
        path, "w", driver="GTiff", height=h, width=w,
        count=bands, dtype="float32", crs="EPSG:32632",
        transform=transform, nodata=0,
    ) as dst:
        dst.write(data)
    return path


def test_load(sample_raster):
    clf = RasterClassifier(sample_raster)
    assert clf.bands == 3
    assert clf.height == 50
    assert clf.width == 50


def test_unsupervised_kmeans(sample_raster):
    clf = RasterClassifier(sample_raster)
    gdf = clf.unsupervised(n_clusters=3, algorithm="kmeans")
    assert len(gdf) > 0
    assert "class_id" in gdf.columns
    assert gdf.crs is not None


def test_unsupervised_minibatch(sample_raster):
    clf = RasterClassifier(sample_raster)
    gdf = clf.unsupervised(n_clusters=2, algorithm="mini_batch_kmeans")
    assert len(gdf) >= 2


def test_dn_ranges(sample_raster):
    clf = RasterClassifier(sample_raster)
    rules = {
        1: [(1, 0.5, 1.0)],   # high band 1 → cluster A
        2: [(3, 0.5, 1.0)],   # high band 3 → cluster B
    }
    gdf = clf.from_dn_ranges(rules)
    assert set(gdf["class_id"].unique()) == {1, 2}


def test_save_gpkg(sample_raster, tmp_path):
    clf = RasterClassifier(sample_raster)
    gdf = clf.unsupervised(n_clusters=2)
    out = tmp_path / "out.gpkg"
    clf.save(gdf, out)
    assert out.exists()


def test_min_area_filter(sample_raster):
    clf = RasterClassifier(sample_raster)
    gdf_all = clf.unsupervised(n_clusters=3, min_area=0)
    gdf_big = clf.unsupervised(n_clusters=3, min_area=100)
    assert len(gdf_big) <= len(gdf_all)


def test_invalid_algorithm(sample_raster):
    clf = RasterClassifier(sample_raster)
    with pytest.raises(ValueError, match="Unknown algorithm"):
        clf.unsupervised(n_clusters=2, algorithm="isodata")
