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

This project is ready for a quick public deployment on Streamlit Community Cloud.

### 1. Create a GEE service account (required for headless deployment)

Streamlit Cloud runs without any Google credentials, so you need a service account to authenticate with Earth Engine:

1. Open the [GCP Console → IAM → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts) in the `ee-okavango` project.
2. Click **Create Service Account** → give it a name (e.g. `okavango-streamlit`).
3. Grant it the **Earth Engine Resource Viewer** role (`roles/earthengine.viewer`).
4. Click the service account → **Keys** tab → **Add Key** → **JSON**. Download the JSON file.
5. Register the service account with Earth Engine at [https://signup.earthengine.google.com/#!/service_accounts](https://signup.earthengine.google.com/#!/service_accounts) (needed for EE API access).

### 2. Push to GitHub and deploy on Streamlit Cloud

```bash
git push origin main
```

1. Go to **https://share.streamlit.io** and sign in with GitHub.
2. Click **New app**, choose `okavango-water-mask-viewer` → branch `main` → main file `app.py`.
3. Under **Advanced settings → Secrets**, add the secret:

```toml
gee_service_account_json = '''
{ ... paste the full contents of your JSON key file here ... }
'''
```

4. Click **Deploy**.

### 3. Test locally with the service account (optional)

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your JSON key. The app will use it automatically on your next `streamlit run app.py`.

Notes:
- The `.streamlit/secrets.toml` file is git-ignored — never commit it.  
- If you later make the assets public, the service account is still required because `ee.data.listAssets()` always requires authentication even for public folders.
- The app falls back to `earthengine authenticate` credentials automatically when running locally without a secrets file.

Troubleshooting:
- If the app fails to start, check the Streamlit Cloud logs for missing packages or import errors.
- If you get blank maps, refresh the browser and check the browser console for CORS or tile loading errors.

