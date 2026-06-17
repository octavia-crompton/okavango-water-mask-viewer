"""
Configuration for the Okavango Water Mask Viewer.
"""
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
LOCAL_TIFS_DIR = PROJECT_ROOT / "data" / "local_tifs"

# ── Map defaults ───────────────────────────────────────────────────────────────
# Center of the Okavango Delta
DEFAULT_CENTER = [-19.5, 22.9]
DEFAULT_ZOOM = 9

# ── GEE ────────────────────────────────────────────────────────────────────────
# GEE asset path containing water mask images
GEE_ASSET_COLLECTION = os.environ.get(
    "GEE_ASSET_COLLECTION",
    "projects/ee-okavango/assets/water_masks/monthly_DSWE_Landsat_30m_v4",
)

# Band name that contains the binary water mask (1 = water, 0 = land)
WATER_BAND = os.environ.get("WATER_BAND", "dswe")

# Sub-folder within the asset root that contains the actual images
GEE_IMAGES_SUBFOLDER = os.environ.get("GEE_IMAGES_SUBFOLDER", "DSWE_Products")

# ── Visualization ──────────────────────────────────────────────────────────────
WATER_VIS_PARAMS = {
    "min": 1,
    "max": 4,
    "palette": [
        "#08519c",  # 1 – high-confidence water
        "#3182bd",  # 2 – moderate-confidence water
        "#9ecae1",  # 3 – low-confidence water
        "#6baed6",  # 4 – wetland / partial water
    ],
}

# Color for the water overlay on local TIFs
WATER_COLOR = "#08519cCC"  # semi-transparent blue
NO_DATA_VALUE = 255

# ── AdDSWE mean difference raster (Figure 4) ──────────────────────────────────
ADDWSE_DIFF_ASSET_ID = (
    "projects/ee-okavango/assets/water_masks/"
    "monthly_DSWE_Landsat_30m_v4/AdDSWE_mean_difference"
)
DIFF_BAND = "difference"
DIFF_VIS_PARAMS = {
    "min": -2,
    "max": 2,
    "palette": [
        "#d73027",  # strongly negative (drier)
        "#f46d43",
        "#fdae61",
        "#fee090",
        "#ffffff",  # 0 – no change
        "#e0f3f8",
        "#abd9e9",
        "#74add1",
        "#4575b4",  # strongly positive (wetter)
    ],
}
