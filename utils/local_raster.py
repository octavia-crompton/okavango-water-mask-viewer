"""
Utilities for loading and processing local GeoTIFF water masks.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Optional

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

from config import LOCAL_TIFS_DIR, NO_DATA_VALUE


# ── Discovery ──────────────────────────────────────────────────────────────────

def list_local_tifs(directory: Optional[Path] = None) -> list[Path]:
    """Return sorted list of .tif files in the directory."""
    d = directory or LOCAL_TIFS_DIR
    tifs = sorted(d.glob("*.tif")) + sorted(d.glob("*.tiff"))
    return tifs


def parse_date_from_filename(path: Path) -> Optional[dt.date]:
    """
    Try to extract a date from the filename.
    Supports patterns like:
        water_mask_2023-01-15.tif
        okavango_20230115.tif
        mask_2023_01_15.tif
    """
    stem = path.stem
    # Try YYYY-MM-DD or YYYY_MM_DD
    m = re.search(r"(\d{4})[-_](\d{2})[-_](\d{2})", stem)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # Try YYYYMMDD
    m = re.search(r"(\d{4})(\d{2})(\d{2})", stem)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def build_local_catalog(directory: Optional[Path] = None) -> list[dict]:
    """
    Scan directory and return a list of dicts:
        [{"path": Path, "date": date | None, "label": str}, ...]
    """
    tifs = list_local_tifs(directory)
    catalog = []
    for p in tifs:
        d = parse_date_from_filename(p)
        label = d.isoformat() if d else p.stem
        catalog.append({"path": p, "date": d, "label": label})
    # Sort by date when available
    catalog.sort(key=lambda x: (x["date"] is None, x["date"] or dt.date.min))
    return catalog


# ── Raster reading ─────────────────────────────────────────────────────────────

def read_water_mask(path: Path) -> tuple[np.ndarray, dict]:
    """
    Read a single-band water mask GeoTIFF.

    Returns
    -------
    data : np.ndarray  (H, W) with values 0/1 (uint8)
    meta : dict with keys  bounds, crs, transform, shape, pixel_area_m2
    """
    with rasterio.open(path) as src:
        data = src.read(1)
        bounds = src.bounds
        crs = src.crs
        transform = src.transform
        # Compute pixel area in m² (approximate for projected CRS)
        pixel_area = abs(transform.a * transform.e)
        if crs and crs.is_geographic:
            # Rough approximation at the latitude of the Okavango (~-19.5°)
            lat_rad = np.radians(19.5)
            m_per_deg_lat = 111_132
            m_per_deg_lon = 111_132 * np.cos(lat_rad)
            pixel_area = abs(transform.a * m_per_deg_lon * transform.e * m_per_deg_lat)

    # Mask nodata
    mask = (data == NO_DATA_VALUE)
    data = np.where(mask, 0, data).astype(np.uint8)

    meta = {
        "bounds": bounds,
        "crs": str(crs),
        "transform": transform,
        "shape": data.shape,
        "pixel_area_m2": pixel_area,
    }
    return data, meta


def compute_water_area_km2(data: np.ndarray, pixel_area_m2: float) -> float:
    """Return total water area in km² (count of water pixels × pixel area)."""
    water_pixels = int(np.sum(data == 1))
    return water_pixels * pixel_area_m2 / 1e6


def bounds_to_leaflet(bounds) -> list[list[float]]:
    """Convert rasterio BoundingBox to [[south, west], [north, east]]."""
    return [[bounds.bottom, bounds.left], [bounds.top, bounds.right]]
