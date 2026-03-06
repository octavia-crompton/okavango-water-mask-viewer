"""
Utilities for working with Google Earth Engine water mask assets.

Supports assets stored as individual images inside a GEE Folder
(not only ImageCollections). Dates are derived from ``year`` / ``month``
image properties when ``system:time_start`` is absent.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Optional

import ee
import streamlit as st

from config import (
    GEE_ASSET_COLLECTION,
    GEE_IMAGES_SUBFOLDER,
    WATER_BAND,
    WATER_VIS_PARAMS,
)


# ── Initialization ─────────────────────────────────────────────────────────────

def initialize_gee() -> bool:
    """
    Initialize the Earth Engine API.
    Returns True if successful, False otherwise.
    """
    try:
        ee.Initialize()
        return True
    except Exception:
        try:
            ee.Authenticate()
            ee.Initialize()
            return True
        except Exception as exc:
            st.warning(f"Could not initialize GEE: {exc}")
            return False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_date_from_id(asset_id: str) -> Optional[dt.date]:
    """
    Try to extract a YYYY_MM date from the asset ID tail.
    e.g. '.../DSWE_1984_06' → date(1984, 6, 1)
    """
    tail = asset_id.rsplit("/", 1)[-1]
    m = re.search(r"(\d{4})[_-](\d{1,2})$", tail)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), 1)
    return None


def _resolve_image_parent(root: str) -> str:
    """
    If ``GEE_IMAGES_SUBFOLDER`` is set, append it to *root*.
    Otherwise return root unchanged.
    """
    if GEE_IMAGES_SUBFOLDER:
        return f"{root.rstrip('/')}/{GEE_IMAGES_SUBFOLDER}"
    return root


# ── Catalog ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def list_gee_images(_root_id: Optional[str] = None) -> list[dict]:
    """
    List images in a GEE asset folder and return metadata.

    Works with both:
    - Folders / IndexedFolders containing individual images
    - Standard ImageCollections

    Returns
    -------
    list of dicts with keys: id, date, label
    """
    root = _root_id or GEE_ASSET_COLLECTION
    images_parent = _resolve_image_parent(root)

    # First try as a folder (listAssets)
    catalog: list[dict] = []
    try:
        assets = ee.data.listAssets({"parent": images_parent})
        items = assets.get("assets", [])
        for a in items:
            if a["type"] != "IMAGE":
                continue
            aid = a["id"]
            d = _parse_date_from_id(aid)
            # Fallback: try year/month properties via getAsset
            if d is None:
                try:
                    info = ee.data.getAsset(aid)
                    props = info.get("properties", {})
                    y = props.get("year")
                    mo = props.get("month")
                    if y and mo:
                        d = dt.date(int(y), int(mo), 1)
                except Exception:
                    pass
            label = d.strftime("%Y-%m") if d else aid.rsplit("/", 1)[-1]
            catalog.append({"id": aid, "date": d, "label": label})
    except Exception:
        # Fall back to ImageCollection
        col = ee.ImageCollection(images_parent)
        info = col.aggregate_array("system:time_start").getInfo()
        ids = col.aggregate_array("system:id").getInfo()
        for img_id, ts in zip(ids, info):
            d = dt.datetime.utcfromtimestamp(ts / 1000).date()
            catalog.append({"id": img_id, "date": d, "label": d.isoformat()})

    catalog.sort(key=lambda x: (x["date"] is None, x["date"] or dt.date.min))
    return catalog


def get_ee_image(image_id: str) -> ee.Image:
    """Load an ee.Image by its asset ID."""
    return ee.Image(image_id)


# ── Tile URL ───────────────────────────────────────────────────────────────────

def get_ee_tile_url(image: ee.Image, vis_params: Optional[dict] = None) -> str:
    """
    Get a tile URL string for adding to leafmap/folium.

    Parameters
    ----------
    image : ee.Image
    vis_params : dict, optional (defaults to WATER_VIS_PARAMS)

    Returns
    -------
    tile_url : str  (XYZ tile template)
    """
    vp = vis_params or WATER_VIS_PARAMS
    band = image.select(WATER_BAND)
    # Mask zeros so they render as transparent
    band = band.updateMask(band.gt(0))
    map_id = band.getMapId(vp)
    return map_id["tile_fetcher"].url_format


# ── Area statistics ────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def compute_gee_water_area_km2(
    image_id: str,
    region: Optional[ee.Geometry] = None,
    scale: int = 30,
) -> float:
    """
    Compute total water area in km² for a GEE image.

    For DSWE products the convention is:
        0 = not water, 1 = high confidence water, 2 = moderate confidence,
        3 = low confidence, 4 = wetland (partial).
    By default we count pixels with value >= 1 as water.
    If no region is provided, uses the image footprint.
    """
    img = ee.Image(image_id).select(WATER_BAND)

    # Binary: anything >= 1 is water
    water_binary = img.gte(1)

    if region is None:
        region = img.geometry()

    area_image = water_binary.multiply(ee.Image.pixelArea())
    stats = area_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=scale,
        maxPixels=1e12,
    )
    area_m2 = stats.get(WATER_BAND).getInfo()
    return (area_m2 or 0) / 1e6
