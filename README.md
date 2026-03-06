# Okavango Water Mask Viewer

An interactive web application for exploring 40 years of surface water dynamics in the Okavango Delta, Botswana. Built with [Streamlit](https://streamlit.io) and [Google Earth Engine](https://earthengine.google.com).

🌊 **[Launch the app →](https://octavia-crompton-okavango-water-mask-viewer.streamlit.app)**

---

## The Okavango Delta

The Okavango Delta is one of the world's largest and most ecologically significant inland deltas, located in northern Botswana. Unlike most river systems, the Okavango River does not flow to the sea — it fans out across the Kalahari Desert, forming a vast mosaic of channels, floodplains, and islands that supports extraordinary biodiversity. The delta is a UNESCO World Heritage Site and a critical water source for wildlife and communities throughout the region.

The extent of the delta's seasonal flooding varies dramatically from year to year, driven by rainfall in the Angolan highlands (the river's headwaters), regional climate variability, and local evapotranspiration. Understanding these long-term changes — and detecting trends against the backdrop of climate change and upstream water use — requires consistent, long-duration records of surface water extent.

---

## The DSWE Algorithm

Surface water extents in this app are derived from the **Dynamic Surface Water Extent (DSWE)** algorithm, developed by the U.S. Geological Survey (USGS). DSWE applies a series of spectral index tests to Landsat imagery to classify each 30-meter pixel into one of five categories:

| Class | Meaning |
|---|---|
| **1** | High-confidence water |
| **2** | Moderate-confidence water |
| **3** | Potential wetland / low-confidence water |
| **4** | Low-confidence water / partial inundation |
| **0** | Not water |

DSWE uses visible, near-infrared, and shortwave infrared bands to distinguish open water from partially vegetated or turbid surfaces, making it well-suited for dynamic floodplain environments like the Okavango where water and vegetation are interspersed. Monthly composites are generated from all available cloud-free Landsat observations (Landsat 4–9) at 30-meter resolution, spanning **1984 to 2025** (368 monthly scenes).

---

## What the App Does

- **Browse water masks by date** — step through 40 years of monthly DSWE maps using a time slider
- **Compare two dates side-by-side** — use the split-map swipe view to visually compare flood extents across years or seasons
- **Track water area over time** — view an automatically computed time series of total water area (km²) across all scenes
- **Switch basemaps** — toggle between satellite imagery, terrain, and street maps for context
- **Upload local GeoTIFFs** — load your own water masks alongside or instead of the GEE data

---

## Data

- **Source:** Landsat 4–9 (USGS), processed via Google Earth Engine
- **Algorithm:** DSWE v4 with vegetated enhancement (Test 6)
- **Resolution:** 30 m
- **Compositing:** Monthly, using all cloud-free observations
- **Coverage:** Okavango Delta, Botswana (~19.5°S, 22.9°E)
- **Time range:** June 1984 – December 2025

---

## Technical Notes

For developer setup, deployment instructions, and configuration details see [TECHNICAL.md](TECHNICAL.md).

