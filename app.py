"""
Okavango Water Mask Viewer
==========================
Streamlit + leafmap app for visualizing water masks from local GeoTIFFs
and Google Earth Engine assets.

Run with:
    streamlit run app.py
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
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
from utils.local_raster import (
    build_local_catalog,
    read_water_mask,
    compute_water_area_km2,
    bounds_to_leaflet,
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


# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("💧 Okavango Water Masks")

data_source = st.sidebar.radio(
    "Data source",
    ["Google Earth Engine", "Local GeoTIFFs"],
    index=0,
)

view_mode = st.sidebar.radio(
    "View mode",
    ["Single map", "Split comparison"],
    index=0,
)

# Basemap selector
BASEMAPS = {
    "OpenStreetMap": "OpenStreetMap",
    "Satellite (Esri)": "Esri_WorldImagery",
    "Terrain": "Esri_WorldTerrain",
    "CartoDB Dark": "CartoDB_DarkMatter",
    "CartoDB Positron": "CartoDB_Positron",
}
basemap_name = st.sidebar.selectbox("Basemap", list(BASEMAPS.keys()), index=1)
basemap = BASEMAPS[basemap_name]

st.sidebar.markdown("---")
st.sidebar.markdown(
    "📂 Place local TIFs in `data/local_tifs/`  \n"
    "Filenames should contain a date (e.g. `water_mask_2023-01-15.tif`)"
)

# ══════════════════════════════════════════════════════════════════════════════
#  LOCAL GEOTIFF MODE
# ══════════════════════════════════════════════════════════════════════════════
if data_source == "Local GeoTIFFs":
    catalog = build_local_catalog()

    # -- Allow upload as alternative ------------------------------------------
    uploaded = st.sidebar.file_uploader(
        "Or upload GeoTIFF(s)",
        type=["tif", "tiff"],
        accept_multiple_files=True,
    )
    if uploaded:
        import tempfile, shutil

        tmp_dir = Path(tempfile.mkdtemp())
        for f in uploaded:
            (tmp_dir / f.name).write_bytes(f.read())
        catalog = build_local_catalog(tmp_dir)

    if not catalog:
        st.warning(
            "No GeoTIFF files found. Place `.tif` files in `data/local_tifs/` "
            "or upload them using the sidebar."
        )
        st.stop()

    labels = [c["label"] for c in catalog]

    # ── Single Map view ──────────────────────────────────────────────────────
    if view_mode == "Single map":
        st.header("Water Mask Viewer")

        if len(catalog) > 1:
            idx = st.select_slider(
                "Select date / layer",
                options=list(range(len(catalog))),
                format_func=lambda i: labels[i],
                value=0,
            )
        else:
            idx = 0

        entry = catalog[idx]
        data, meta = read_water_mask(entry["path"])

        # -- Stats --
        area_km2 = compute_water_area_km2(data, meta["pixel_area_m2"])
        total_pixels = data.size
        water_pixels = int(np.sum(data == 1))

        col1, col2, col3 = st.columns(3)
        col1.metric("Water area", f"{area_km2:,.1f} km²")
        col2.metric("Water pixels", f"{water_pixels:,}")
        col3.metric("Coverage", f"{100 * water_pixels / total_pixels:.1f}%")

        # -- Map --
        m = leafmap.Map(center=DEFAULT_CENTER, zoom=DEFAULT_ZOOM)
        m.add_basemap(basemap)

        # Overlay water mask as image
        bounds = bounds_to_leaflet(meta["bounds"])

        # Create RGBA overlay: blue where water, transparent elsewhere
        rgba = np.zeros((*data.shape, 4), dtype=np.uint8)
        rgba[data == 1] = [8, 81, 156, 180]  # #08519c with alpha

        import io
        from PIL import Image as PILImage

        img = PILImage.fromarray(rgba, "RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        import base64

        img_b64 = base64.b64encode(buf.read()).decode()
        img_url = f"data:image/png;base64,{img_b64}"

        folium.raster_layers.ImageOverlay(
            image=img_url,
            bounds=bounds,
            opacity=0.7,
            name=f"Water mask – {entry['label']}",
        ).add_to(m)

        folium.LayerControl().add_to(m)
        m.to_streamlit(height=650)

    # ── Split Comparison view ────────────────────────────────────────────────
    else:
        st.header("Split Comparison")

        if len(catalog) < 2:
            st.warning("Need at least 2 layers for comparison.")
            st.stop()

        c1, c2 = st.columns(2)
        with c1:
            left_idx = st.selectbox("Left layer", range(len(catalog)),
                                     format_func=lambda i: labels[i], index=0)
        with c2:
            right_idx = st.selectbox("Right layer", range(len(catalog)),
                                      format_func=lambda i: labels[i],
                                      index=min(1, len(catalog) - 1))

        # Read both masks
        data_l, meta_l = read_water_mask(catalog[left_idx]["path"])
        data_r, meta_r = read_water_mask(catalog[right_idx]["path"])

        # Stats comparison
        area_l = compute_water_area_km2(data_l, meta_l["pixel_area_m2"])
        area_r = compute_water_area_km2(data_r, meta_r["pixel_area_m2"])

        col1, col2, col3 = st.columns(3)
        col1.metric(f"Left – {catalog[left_idx]['label']}", f"{area_l:,.1f} km²")
        col2.metric(f"Right – {catalog[right_idx]['label']}", f"{area_r:,.1f} km²")
        delta = area_r - area_l
        col3.metric("Difference", f"{delta:+,.1f} km²",
                     delta=f"{delta:+,.1f} km²")

        # Build overlay helper
        def make_overlay_url(data_arr):
            rgba = np.zeros((*data_arr.shape, 4), dtype=np.uint8)
            rgba[data_arr == 1] = [8, 81, 156, 180]
            import io, base64
            from PIL import Image as PILImage
            img = PILImage.fromarray(rgba, "RGBA")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"

        m = leafmap.Map(center=DEFAULT_CENTER, zoom=DEFAULT_ZOOM)
        m.add_basemap(basemap)

        # Add left layer
        bounds_l = bounds_to_leaflet(meta_l["bounds"])
        left_overlay = folium.raster_layers.ImageOverlay(
            image=make_overlay_url(data_l),
            bounds=bounds_l,
            opacity=0.7,
            name=f"Left – {catalog[left_idx]['label']}",
        )
        left_overlay.add_to(m)

        # Add right layer
        bounds_r = bounds_to_leaflet(meta_r["bounds"])
        right_overlay = folium.raster_layers.ImageOverlay(
            image=make_overlay_url(data_r),
            bounds=bounds_r,
            opacity=0.7,
            name=f"Right – {catalog[right_idx]['label']}",
        )
        right_overlay.add_to(m)

        folium.LayerControl().add_to(m)

        # Use leafmap's split_map for side-by-side
        st.markdown("**Toggle layers on/off using the layer control (top-right)**")
        m.to_streamlit(height=650)

        # Also show a dedicated split map
        st.subheader("Side-by-side swipe view")
        split_m = leafmap.Map(center=DEFAULT_CENTER, zoom=DEFAULT_ZOOM)
        split_m.split_map(
            left_layer=basemap,
            right_layer=basemap,
        )
        # Add overlays to each side by using separate feature groups
        left_fg = folium.FeatureGroup(name="Left water mask")
        folium.raster_layers.ImageOverlay(
            image=make_overlay_url(data_l),
            bounds=bounds_l,
            opacity=0.7,
        ).add_to(left_fg)
        left_fg.add_to(split_m)

        right_fg = folium.FeatureGroup(name="Right water mask")
        folium.raster_layers.ImageOverlay(
            image=make_overlay_url(data_r),
            bounds=bounds_r,
            opacity=0.7,
        ).add_to(right_fg)
        right_fg.add_to(split_m)

        split_m.to_streamlit(height=650)

    # ── Area time series chart (if multiple dates) ───────────────────────────
    if len(catalog) > 1 and any(c["date"] for c in catalog):
        st.markdown("---")
        st.subheader("📊 Water Area Time Series")

        with st.spinner("Computing area statistics for all dates..."):
            records = []
            for entry in catalog:
                if entry["date"] is None:
                    continue
                d, m_ = read_water_mask(entry["path"])
                a = compute_water_area_km2(d, m_["pixel_area_m2"])
                records.append({"date": entry["date"], "area_km2": a})

            if records:
                df = pd.DataFrame(records)
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date").sort_index()
                st.line_chart(df["area_km2"], use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  GOOGLE EARTH ENGINE MODE
# ══════════════════════════════════════════════════════════════════════════════
elif data_source == "Google Earth Engine":
    try_gee_init()

    if not st.session_state.gee_initialized:
        st.error(
            "GEE could not be initialized. Run `earthengine authenticate` "
            "in your terminal and restart the app."
        )
        st.stop()

    import ee
    from utils.gee_utils import (
        list_gee_images,
        get_ee_image,
        get_ee_tile_url,
        compute_gee_water_area_km2,
    )

    # Allow overriding the collection ID
    col_id = st.sidebar.text_input(
        "GEE ImageCollection ID",
        value=GEE_ASSET_COLLECTION,
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

    # ── Single Map view ──────────────────────────────────────────────────────
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
        m.add_basemap(basemap)

        tile_url = get_ee_tile_url(img)
        m.add_tile_layer(
            url=tile_url,
            name=f"Water mask – {entry['label']}",
            attribution="Google Earth Engine",
        )

        folium.LayerControl().add_to(m)
        m.to_streamlit(height=650)

    # ── Split Comparison view ────────────────────────────────────────────────
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

        # Split map with GEE tile layers
        img_l = get_ee_image(catalog[left_idx]["id"])
        img_r = get_ee_image(catalog[right_idx]["id"])

        tile_l = get_ee_tile_url(img_l)
        tile_r = get_ee_tile_url(img_r)

        m = leafmap.Map(center=DEFAULT_CENTER, zoom=DEFAULT_ZOOM)
        m.add_basemap(basemap)
        m.add_tile_layer(url=tile_l, name=f"Left – {catalog[left_idx]['label']}",
                          attribution="GEE")
        m.add_tile_layer(url=tile_r, name=f"Right – {catalog[right_idx]['label']}",
                          attribution="GEE")

        folium.LayerControl().add_to(m)
        m.to_streamlit(height=650)

        # Dedicated split view
        st.subheader("Side-by-side swipe view")
        split_m = leafmap.Map(center=DEFAULT_CENTER, zoom=DEFAULT_ZOOM)
        split_m.split_map(left_layer=tile_l, right_layer=tile_r)
        split_m.to_streamlit(height=650)

    # ── Area time series ─────────────────────────────────────────────────────
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
