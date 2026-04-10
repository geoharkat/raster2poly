"""
Raster classification and vectorisation engine.

Supports unsupervised (KMeans, MiniBatchKMeans), supervised (Random Forest
from ROI shapefiles or DN-range rules), with memory-efficient reading and
clean polygon output.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.windows import from_bounds
from shapely.geometry import shape as shapely_shape
from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.ensemble import RandomForestClassifier

warnings.filterwarnings("ignore", category=rasterio.errors.NotGeoreferencedWarning)

PathLike = Union[str, Path]


# ═══════════════════════════════════════════════════════════════
#  Internal helpers
# ═══════════════════════════════════════════════════════════════

def _read_all_bands(path: PathLike) -> Tuple[np.ndarray, dict]:
    """
    Read all bands as float32, replacing nodata with NaN.

    Returns
    -------
    pixels : (N, B) float32 — one row per pixel, one column per band.
    meta   : rasterio profile dict.
    """
    with rasterio.open(path) as src:
        data = src.read().astype(np.float32)  # (B, H, W)
        meta = src.profile.copy()
        nd = src.nodata
    if nd is not None:
        data[data == nd] = np.nan
    bands, h, w = data.shape
    pixels = data.reshape(bands, h * w).T  # (N, B)
    return pixels, meta


def _valid_mask(pixels: np.ndarray) -> np.ndarray:
    """True where **all** bands are finite."""
    return np.all(np.isfinite(pixels), axis=1)


def _apply_labels(
    valid_mask: np.ndarray,
    labels: np.ndarray,
    total_pixels: int,
    fill: int = 0,
) -> np.ndarray:
    """Scatter classified labels back into a full-length 1-D array."""
    out = np.full(total_pixels, fill, dtype=np.int32)
    out[valid_mask] = labels
    return out


def _vectorize(
    labels_1d: np.ndarray,
    height: int,
    width: int,
    transform,
    crs,
    *,
    dissolve: bool = True,
    min_area: float = 0.0,
) -> gpd.GeoDataFrame:
    """
    Convert a 1-D classified array to polygons.

    Parameters
    ----------
    dissolve : bool
        Merge adjacent polygons of the same class (recommended).
    min_area : float
        Drop polygons smaller than this (map units²).
    """
    grid = labels_1d.astype(np.int32).reshape(height, width)

    records: list[dict] = []
    for geom_dict, value in shapes(grid, transform=transform):
        if value == 0:
            continue
        records.append({"class_id": int(value), "geometry": shapely_shape(geom_dict)})

    if not records:
        raise ValueError(
            "Vectorisation produced no polygons.  Check classification inputs."
        )

    gdf = gpd.GeoDataFrame(records, crs=crs)

    if dissolve:
        gdf = gdf.dissolve(by="class_id", as_index=False)
        # dissolve may create MultiPolygons; explode to simple Polygons
        gdf = gdf.explode(index_parts=False).reset_index(drop=True)

    if min_area > 0:
        gdf = gdf[gdf.geometry.area >= min_area].reset_index(drop=True)

    return gdf


def _extract_training_pixels(
    raster_path: PathLike,
    roi: gpd.GeoDataFrame,
    class_col: str,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Burn ROI geometries into the raster grid and extract per-pixel
    training samples — much more robust than zonal-mean shortcuts.
    """
    X_list: list[np.ndarray] = []
    y_list: list[int] = []

    with rasterio.open(raster_path) as src:
        for _, row in roi.iterrows():
            geom = row.geometry
            label = int(row[class_col])

            # Window covering this geometry
            try:
                window = from_bounds(*geom.bounds, transform=src.transform)
                window = window.round_offsets().round_lengths()
                if window.width < 1 or window.height < 1:
                    continue
            except Exception:
                continue

            win_transform = src.window_transform(window)
            data = src.read(window=window).astype(np.float32)  # (B, h, w)
            nd = src.nodata
            if nd is not None:
                data[data == nd] = np.nan
            b, h, w = data.shape

            # Rasterise geometry into window
            mask = geometry_mask(
                [geom], out_shape=(h, w), transform=win_transform, invert=True,
            )

            pixels = data[:, mask].T  # (n, B)
            finite = np.all(np.isfinite(pixels), axis=1)
            pixels = pixels[finite]

            if len(pixels) > 0:
                X_list.append(pixels)
                y_list.append(np.full(len(pixels), label, dtype=np.int32))

    if not X_list:
        raise ValueError("No valid training pixels extracted from ROI.")

    return np.vstack(X_list), np.concatenate(y_list)


# ═══════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════

class RasterClassifier:
    """
    Classify a raster and vectorise the result to polygons.

    Parameters
    ----------
    raster_path : path-like
        Multi-band GeoTIFF (or any GDAL-readable raster).

    Examples
    --------
    >>> clf = RasterClassifier("image.tif")
    >>> gdf = clf.unsupervised(n_clusters=6)
    >>> gdf.to_file("classes.shp")
    """

    def __init__(self, raster_path: PathLike) -> None:
        self.raster_path = Path(raster_path)
        if not self.raster_path.is_file():
            raise FileNotFoundError(self.raster_path)

        self._pixels, self._meta = _read_all_bands(self.raster_path)
        self._valid = _valid_mask(self._pixels)
        self._valid_pixels = self._pixels[self._valid]

        bands = self._meta["count"]
        self.height: int = self._meta["height"]
        self.width: int = self._meta["width"]
        self.bands: int = bands
        self.crs = self._meta.get("crs") or "EPSG:4326"
        self.transform = self._meta["transform"]

        n_valid = int(self._valid.sum())
        n_total = self.height * self.width
        print(
            f"Loaded {self.raster_path.name}: "
            f"{self.width}×{self.height} px, {bands} bands, "
            f"{n_valid}/{n_total} valid pixels ({n_valid/n_total*100:.1f}%)"
        )

    # ── Unsupervised ──

    def unsupervised(
        self,
        n_clusters: int = 5,
        *,
        algorithm: str = "kmeans",
        dissolve: bool = True,
        min_area: float = 0.0,
    ) -> gpd.GeoDataFrame:
        """
        K-Means or MiniBatchKMeans clustering.

        Parameters
        ----------
        n_clusters : int
            Number of classes.
        algorithm : ``"kmeans"`` | ``"mini_batch_kmeans"``
            MiniBatchKMeans is recommended for rasters > 10 M pixels.
        dissolve : bool
            Merge adjacent same-class polygons.
        min_area : float
            Drop polygons smaller than this (map units²).

        Returns
        -------
        GeoDataFrame with ``class_id`` and ``geometry`` columns.
        """
        if algorithm == "kmeans":
            model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        elif algorithm == "mini_batch_kmeans":
            model = MiniBatchKMeans(
                n_clusters=n_clusters, batch_size=10_000, random_state=42,
            )
        else:
            raise ValueError(
                f"Unknown algorithm {algorithm!r}. "
                "Choose 'kmeans' or 'mini_batch_kmeans'."
            )

        print(f"Running {algorithm} with {n_clusters} clusters …")
        labels = model.fit_predict(self._valid_pixels) + 1  # 0 = nodata

        labels_1d = _apply_labels(self._valid, labels, len(self._pixels))
        return _vectorize(
            labels_1d, self.height, self.width,
            self.transform, self.crs,
            dissolve=dissolve, min_area=min_area,
        )

    # ── Supervised (ROI shapefile) ──

    def supervised(
        self,
        roi_path: PathLike,
        *,
        class_col: str = "class_id",
        n_estimators: int = 100,
        dissolve: bool = True,
        min_area: float = 0.0,
    ) -> gpd.GeoDataFrame:
        """
        Random Forest classification trained from an ROI shapefile.

        The ROI file may contain **Points or Polygons** (or both).  For
        polygons every pixel inside the geometry is used as a training
        sample — far more robust than a single zonal mean.

        Parameters
        ----------
        roi_path : path-like
            Shapefile / GeoPackage with training geometries.
        class_col : str
            Column holding integer class labels (default ``"class_id"``).
        n_estimators : int
            Number of Random Forest trees.

        Returns
        -------
        Classified GeoDataFrame.
        """
        roi = gpd.read_file(roi_path)
        if class_col not in roi.columns:
            raise KeyError(
                f"Column {class_col!r} not found in {roi_path}.  "
                f"Available: {list(roi.columns)}"
            )

        # Reproject vector → raster CRS (never the other way)
        if self._meta.get("crs") and roi.crs != self._meta["crs"]:
            roi = roi.to_crs(self._meta["crs"])

        X_train, y_train = _extract_training_pixels(
            self.raster_path, roi, class_col,
        )
        n_classes = len(np.unique(y_train))
        print(
            f"Training Random Forest ({n_estimators} trees) on "
            f"{len(X_train)} pixels, {n_classes} classes …"
        )

        clf = RandomForestClassifier(
            n_estimators=n_estimators, random_state=42, n_jobs=-1,
        )
        clf.fit(X_train, y_train)

        self._last_model = clf  # keep for feature_importances_, etc.

        print("Classifying full raster …")
        labels = clf.predict(self._valid_pixels)
        labels_1d = _apply_labels(self._valid, labels, len(self._pixels))
        return _vectorize(
            labels_1d, self.height, self.width,
            self.transform, self.crs,
            dissolve=dissolve, min_area=min_area,
        )

    # ── Supervised (DN range rules) ──

    def from_dn_ranges(
        self,
        rules: Dict[int, List[Tuple[int, float, float]]],
        *,
        dissolve: bool = True,
        min_area: float = 0.0,
    ) -> gpd.GeoDataFrame:
        """
        Rule-based classification from digital-number thresholds.

        Parameters
        ----------
        rules : dict
            ``{class_id: [(band, min_dn, max_dn), …], …}``
            Band numbers are **1-based**.  A pixel must satisfy *all*
            conditions in the list to be assigned that class.

        Example
        -------
        >>> rules = {
        ...     1: [(4, 0.15, 1.0), (5, 0.0, 0.10)],  # high Red, low NIR
        ...     2: [(5, 0.25, 1.0)],                     # high NIR
        ... }
        >>> gdf = clf.from_dn_ranges(rules)
        """
        labels = np.zeros(len(self._valid_pixels), dtype=np.int32)

        for class_id, conditions in rules.items():
            mask = np.ones(len(self._valid_pixels), dtype=bool)
            for band_1based, lo, hi in conditions:
                col = self._valid_pixels[:, band_1based - 1]
                mask &= (col >= lo) & (col <= hi)
            labels[mask] = class_id

        labels_1d = _apply_labels(self._valid, labels, len(self._pixels))
        return _vectorize(
            labels_1d, self.height, self.width,
            self.transform, self.crs,
            dissolve=dissolve, min_area=min_area,
        )

    # ── Convenience ──

    @staticmethod
    def available_algorithms() -> None:
        """
        Print all supported classification algorithms.

        Example
        -------
        >>> RasterClassifier.available_algorithms()
        """
        info = {
            "Unsupervised  (no training data required)": {
                "kmeans": (
                    "K-Means clustering — best for small / medium rasters.  "
                    "Use via: clf.unsupervised(n_clusters=N, algorithm='kmeans')"
                ),
                "mini_batch_kmeans": (
                    "MiniBatch K-Means — memory-efficient, recommended for "
                    "rasters > 10 M pixels.  "
                    "Use via: clf.unsupervised(n_clusters=N, algorithm='mini_batch_kmeans')"
                ),
            },
            "Supervised  (requires labelled data)": {
                "random_forest  →  .supervised()": (
                    "Random Forest trained on pixel samples burned from ROI "
                    "geometries (Points or Polygons).  "
                    "Use via: clf.supervised(roi_path=..., class_col=...)"
                ),
                "dn_ranges  →  .from_dn_ranges()": (
                    "Rule-based thresholding — classify pixels by per-band "
                    "digital-number ranges; no training data needed.  "
                    "Use via: clf.from_dn_ranges({class_id: [(band, lo, hi), ...]})"
                ),
            },
        }
        print("\n── Available Classification Algorithms ──")
        for category, algorithms in info.items():
            print(f"\n  [{category}]")
            for name, desc in algorithms.items():
                # Wrap description at 70 chars for readability
                import textwrap
                wrapped = textwrap.wrap(desc, width=70)
                print(f"    • {name}")
                for line in wrapped:
                    print(f"        {line}")
        print()

    def band_stats(self) -> None:
        """
        Print min / max / mean / std for every band directly from the raster.

        Example
        -------
        >>> clf.band_stats()
        """
        print(f"\n── Band statistics: {self.raster_path.name} ──")
        with rasterio.open(self.raster_path) as src:
            for i in range(1, src.count + 1):
                band = src.read(i).astype(np.float32)
                nd = src.nodata
                if nd is not None:
                    band = np.where(band == nd, np.nan, band)
                finite = band[np.isfinite(band)]
                if finite.size == 0:
                    print(f"  Band {i}: all nodata / non-finite — skipped")
                    continue
                print(
                    f"  Band {i}: "
                    f"min={finite.min():.4f}  "
                    f"max={finite.max():.4f}  "
                    f"mean={finite.mean():.4f}  "
                    f"std={finite.std():.4f}"
                )
        print()

    def encode_roi(
        self,
        roi_path: PathLike,
        label_col: str,
        *,
        output_path: Optional[PathLike] = None,
        id_col: str = "class_id",
    ) -> Tuple[Path, Dict[str, int]]:
        """
        Encode a string / categorical label column to consecutive integer IDs
        and save the result — no extra scripts required.

        Parameters
        ----------
        roi_path : path-like
            Input shapefile / GeoPackage with a text label column.
        label_col : str
            Column that holds the string class names (e.g. ``"Age"``).
        output_path : path-like, optional
            Destination file.  Defaults to ``<stem>_encoded<suffix>``
            next to the input file.
        id_col : str
            Name of the new integer-ID column added to the output
            (default ``"class_id"``).

        Returns
        -------
        output_path : Path
            Path of the saved encoded file.
        mapping : dict
            ``{label_name: integer_id}`` — labels are sorted alphabetically
            and numbered from 1 (0 is reserved for nodata).

        Example
        -------
        >>> out, mapping = clf.encode_roi("ages2.shp", label_col="Age")
        >>> print(mapping)   # {'Holocene': 1, 'Jurassic': 2, ...}
        >>> gdf_rf = clf.supervised(roi_path=out, class_col="class_id")
        """
        roi_path = Path(roi_path)

        if output_path is None:
            output_path = roi_path.with_name(
                roi_path.stem + "_encoded" + roi_path.suffix
            )
        output_path = Path(output_path)

        gdf = gpd.read_file(roi_path)

        if label_col not in gdf.columns:
            raise KeyError(
                f"Column {label_col!r} not found in {roi_path}.  "
                f"Available: {list(gdf.columns)}"
            )

        # Sort for deterministic IDs across runs
        unique_labels = sorted(gdf[label_col].dropna().unique(), key=str)
        mapping: Dict[str, int] = {
            name: idx + 1 for idx, name in enumerate(unique_labels)
        }
        gdf[id_col] = gdf[label_col].map(mapping).astype("Int32")

        driver_map = {
            ".shp":     "ESRI Shapefile",
            ".gpkg":    "GPKG",
            ".geojson": "GeoJSON",
            ".json":    "GeoJSON",
        }
        driver = driver_map.get(output_path.suffix.lower(), "ESRI Shapefile")
        gdf.to_file(output_path, driver=driver)

        print(f"Encoded {label_col!r} → {id_col!r}  ({len(mapping)} classes):")
        for name, idx in mapping.items():
            print(f"  {idx:>3}: {name}")
        print(f"Saved encoded ROI → {output_path}\n")

        return output_path, mapping

    def save(
        self,
        gdf: gpd.GeoDataFrame,
        path: PathLike,
        driver: Optional[str] = None,
    ) -> None:
        """
        Write classified polygons to disk.

        Format is inferred from extension (``.shp``, ``.gpkg``,
        ``.geojson``).
        """
        path = Path(path)
        if driver is None:
            driver = {
                ".shp": "ESRI Shapefile",
                ".gpkg": "GPKG",
                ".geojson": "GeoJSON",
                ".json": "GeoJSON",
            }.get(path.suffix.lower(), "ESRI Shapefile")
        gdf.to_file(path, driver=driver)
        print(f"Saved {len(gdf)} polygons → {path}")