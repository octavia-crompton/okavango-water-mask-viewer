"""
Okavango Water Mask Viewer
==========================
Streamlit + leafmap app for visualizing water masks from Google Earth Engine assets.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st
import leafmap.foliumap as leafmap
import folium
import pandas as pd

from config import (
    DEFAULT_CENTER,
    DEFAULT_ZOOM,
    GEE_ASSET_COLLECTION,
    GEE_IMAGES_SUBFOLDER,
    WATER_VIS_PARAMS,
    WATER_BAND,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Okavango Water Mask Viewer",
    page_icon="💧",
    layout="wide",
)

# ── Session state defaults ─────────────────────────────────────────────────────
if "gee_initialized" not in st.session_state:
    st.session_state.gee_initialized = False


# ── Helper: try GEE init ──────────────────────────────────────────────────────
def try_gee_init():
    if not st.session_state.gee_initialized:
        try:
            from utils.gee_utils import initialize_gee
            st.session_state.gee_initialized = initialize_gee()
        except Exception:
            st.session_state.gee_initialized = False


# ── Water mask class legend ───────────────────────────────────────────────────
# Built from WATER_VIS_PARAMS so the legend can never drift from the map palette.
_WATER_SWATCHES = "".join(
    f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px;">'
    f'<div style="width:44px;height:16px;background:{color};'
    f'border:1px solid #ccc;border-radius:3px;"></div>'
    f'<span style="font-size:0.73rem;color:#666;">{cls}</span></div>'
    for cls, color in enumerate(
        WATER_VIS_PARAMS["palette"], start=WATER_VIS_PARAMS["min"]
    )
)
WATER_LEGEND_HTML = f"""
<div style="margin:4px 0 16px 0;padding:8px 12px;background:#f8f9fa;
            border-radius:6px;border:1px solid #dee2e6;">
  <p style="margin:0 0 6px 0;font-size:0.85rem;font-weight:600;color:#333;">
    AdDSWE class
  </p>
  <div style="display:flex;align-items:flex-end;gap:8px;">{_WATER_SWATCHES}</div>
  <p style="margin:6px 0 0 0;font-size:0.73rem;color:#666;">
    0 = not water (transparent)
  </p>
</div>
"""


# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("💧 Okavango Water Masks")

view_mode = st.sidebar.radio(
    "View mode",
    ["Single map", "Split comparison"],
    index=0,
)

st.sidebar.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
#  GOOGLE EARTH ENGINE
# ══════════════════════════════════════════════════════════════════════════════
try_gee_init()

if not st.session_state.gee_initialized:
    st.error(
        "GEE could not be initialized. Run `earthengine authenticate` "
        "in your terminal and restart the app."
    )
    st.stop()

from utils.gee_utils import (
    list_gee_images,
    get_ee_image,
    get_ee_tile_url,
    get_diff_tile_url,
    compute_gee_water_area_km2,
)

# Allow overriding the collection ID
col_id = st.sidebar.text_input(
    "GEE ImageCollection ID",
    value=GEE_ASSET_COLLECTION,
)

# The difference raster is a single-map feature; the split view is reserved for
# comparing the two selected dates.
show_diff = (
    st.sidebar.checkbox("Show AdDSWE mean difference (Fig. 4)", value=False)
    if view_mode == "Single map"
    else False
)

try:
    catalog = list_gee_images(col_id)
except Exception as exc:
    st.error(f"Could not list images from `{col_id}`: {exc}")
    st.stop()

if not catalog:
    st.warning(f"No images found in `{col_id}`.")
    st.stop()

labels = [c["label"] for c in catalog]

# ── Single Map view ───────────────────────────────────────────────────────────
if view_mode == "Single map":
    st.header("Water Mask Viewer (GEE)")

    if len(catalog) > 1:
        idx = st.select_slider(
            "Select date",
            options=list(range(len(catalog))),
            format_func=lambda i: labels[i],
            value=0,
        )
    else:
        idx = 0

    entry = catalog[idx]
    img = get_ee_image(entry["id"])

    # Stats
    with st.spinner("Computing water area…"):
        area_km2 = compute_gee_water_area_km2(entry["id"])
    st.metric("Water area", f"{area_km2:,.1f} km²")

    # Map
    m = leafmap.Map(center=DEFAULT_CENTER, zoom=DEFAULT_ZOOM)
    m.add_basemap("OpenStreetMap")

    tile_url = get_ee_tile_url(img)
    m.add_tile_layer(
        url=tile_url,
        name=f"Water mask – {entry['label']}",
        attribution="Google Earth Engine",
    )

    if show_diff:
        with st.spinner("Loading AdDSWE mean difference layer…"):
            diff_tile_url = get_diff_tile_url()
        m.add_tile_layer(
            url=diff_tile_url,
            name="AdDSWE mean difference (Fig. 4)",
            attribution="Google Earth Engine",
        )

    folium.LayerControl().add_to(m)
    m.to_streamlit(height=650)

    st.markdown(WATER_LEGEND_HTML, unsafe_allow_html=True)

    if show_diff:
        st.markdown(
            """
            <div style="margin:4px 0 16px 0;padding:8px 12px;background:#f8f9fa;
                        border-radius:6px;border:1px solid #dee2e6;">
              <p style="margin:0 0 6px 0;font-size:0.85rem;font-weight:600;color:#333;">
                AdDSWE Mean Difference (DSWE units)
              </p>
              <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:0.78rem;min-width:2rem;text-align:right;">−2</span>
                <div style="flex:1;height:16px;border-radius:3px;
                            background:linear-gradient(to right,#d73027,#f46d43,#fdae61,
                            #fee090,#ffffff,#e0f3f8,#abd9e9,#74add1,#4575b4);
                            border:1px solid #ccc;"></div>
                <span style="font-size:0.78rem;min-width:2rem;">+2</span>
              </div>
              <div style="display:flex;justify-content:space-between;
                          padding:2px 2.8rem 0 2.8rem;">
                <span style="font-size:0.73rem;color:#666;">← drier</span>
                <span style="font-size:0.73rem;color:#666;">no change</span>
                <span style="font-size:0.73rem;color:#666;">wetter →</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Split Comparison view ────────────────────────────────────────────────────
else:
    st.header("Split Comparison (GEE)")

    if len(catalog) < 2:
        st.warning("Need at least 2 images for comparison.")
        st.stop()

    c1, c2 = st.columns(2)
    with c1:
        left_idx = st.selectbox("Left image", range(len(catalog)),
                                 format_func=lambda i: labels[i], index=0)
    with c2:
        right_idx = st.selectbox("Right image", range(len(catalog)),
                                  format_func=lambda i: labels[i],
                                  index=min(1, len(catalog) - 1))

    # Stats comparison
    with st.spinner("Computing areas…"):
        area_l = compute_gee_water_area_km2(catalog[left_idx]["id"])
        area_r = compute_gee_water_area_km2(catalog[right_idx]["id"])

    col1, col2, col3 = st.columns(3)
    col1.metric(f"Left – {catalog[left_idx]['label']}", f"{area_l:,.1f} km²")
    col2.metric(f"Right – {catalog[right_idx]['label']}", f"{area_r:,.1f} km²")
    delta = area_r - area_l
    col3.metric("Difference", f"{delta:+,.1f} km²",
                 delta=f"{delta:+,.1f} km²")

    # Side-by-side swipe map: drag the handle to compare the two dates
    img_l = get_ee_image(catalog[left_idx]["id"])
    img_r = get_ee_image(catalog[right_idx]["id"])

    tile_l = get_ee_tile_url(img_l)
    tile_r = get_ee_tile_url(img_r)

    split_m = leafmap.Map(center=DEFAULT_CENTER, zoom=DEFAULT_ZOOM)
    split_m.add_basemap("OpenStreetMap")
    split_m.split_map(
        left_layer=tile_l,
        right_layer=tile_r,
        left_label=catalog[left_idx]["label"],
        right_label=catalog[right_idx]["label"],
    )
    split_m.to_streamlit(height=650)

    st.markdown(WATER_LEGEND_HTML, unsafe_allow_html=True)

# ── Area time series ────────────────────────────────────────────────────────────
if len(catalog) > 1:
    st.markdown("---")
    st.subheader("📊 Water Area Time Series")

    with st.spinner("Computing area for all dates (this may take a moment)…"):
        records = []
        for entry in catalog:
            try:
                a = compute_gee_water_area_km2(entry["id"])
                records.append({"date": entry["date"], "area_km2": a})
            except Exception:
                pass

    if records:
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        st.line_chart(df["area_km2"], use_container_width=True)
