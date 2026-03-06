# Okavango Water Mask Viewer

A Streamlit + leafmap web app for visualizing water masks over the Okavango Delta.

## Features

- **Time series slider** — browse water masks by date
- **Side-by-side comparison** — swipe between two dates using a split map
- **Area statistics** — automatic water area computation (km²) with time series chart
- **Basemap toggle** — switch between satellite, terrain, OSM, and dark basemaps
- **Dual data sources** — load masks from local GeoTIFFs or Google Earth Engine

## Quick Start

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Authenticate with GEE
earthengine authenticate

# 4. Add your water mask TIFs
#    Place files in data/local_tifs/ with dates in the filename:
#    e.g. water_mask_2023-01-15.tif, okavango_20230715.tif

# 5. Run the app
streamlit run app.py
```

## Project Structure

```
Okavango-app/
├── app.py                  # Main Streamlit application
├── config.py               # Configuration (paths, GEE settings, vis params)
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Streamlit theme & server settings
├── data/
│   └── local_tifs/         # Place your GeoTIFF water masks here
└── utils/
    ├── __init__.py
    ├── local_raster.py     # Local TIF loading, area computation
    └── gee_utils.py        # GEE initialization, tile URLs, area stats
```

## Data Format

### Local GeoTIFFs
- Single-band binary masks: `1` = water, `0` = land
- Any CRS (area stats approximate for geographic CRS)
- Filename should contain a date in `YYYY-MM-DD`, `YYYY_MM_DD`, or `YYYYMMDD` format

### Google Earth Engine
- Set `GEE_ASSET_COLLECTION` in `config.py` (or via environment variable) to your ImageCollection path
- Images should have a band named `water` (configurable via `WATER_BAND` in config)
- Images must have `system:time_start` property set

## Configuration

Edit `config.py` to customize:

| Setting | Description | Default |
|---|---|---|
| `DEFAULT_CENTER` | Map center `[lat, lon]` | `[-19.5, 22.9]` (Okavango Delta) |
| `DEFAULT_ZOOM` | Initial zoom level | `9` |
| `GEE_ASSET_COLLECTION` | GEE ImageCollection path | `projects/your-project/assets/...` |
| `WATER_BAND` | Band name in GEE images | `water` |
| `WATER_VIS_PARAMS` | Color ramp for water display | Light→dark blue |
| `NO_DATA_VALUE` | NoData pixel value in TIFs | `255` |

## Deploy to Streamlit Cloud

This project is ready for a quick public deployment on Streamlit Community Cloud. The GEE assets used by default in this repository are public, so no Earth Engine authentication is required for the running app.

Steps:

1. Create a GitHub repository and push this project (make sure you do NOT push your local virtual environment or any secret files):

```bash
git init
git add .
git commit -m "Initial Okavango water mask viewer"
git branch -M main
git remote add origin git@github.com:<your-org-or-username>/okavango-water-mask-viewer.git
git push -u origin main
```

2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app**, choose the repository and branch (`main`), and set the main file to `app.py`.
4. Streamlit will detect `requirements.txt` and install dependencies automatically. Deploy the app.

Notes and tips:

- Because the GEE assets in `config.py` are public, the app can read them without credentials. If you later point `GEE_ASSET_COLLECTION` at private assets, you'll need to configure server-side credentials (see the `utils/gee_utils.py` service-account pattern).  
- The `.streamlit/config.toml` is included to provide a consistent theme and server settings on Streamlit Cloud.  
- If you want a private app on Streamlit Cloud or need to store service-account JSON safely, use Streamlit's Secrets manager (paid plan may be required for team/private apps).

Troubleshooting:

- If the app fails to start, check the Streamlit Cloud logs for missing packages or import errors. You can pin versions in `requirements.txt` if needed.
- If you get blank maps, refresh the browser and check the browser console for CORS or tile loading errors.

