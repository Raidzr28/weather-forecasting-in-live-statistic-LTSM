# Prakiraan Cuaca Indonesia — BMKG + LSTM

A local web app that forecasts weather for any Indonesian village/city using
a deep learning model (LSTM, PyTorch) trained on real historical weather
data, shown alongside Indonesia's official BMKG forecast for comparison.

## How it works

1. **Search** any Indonesian kelurahan/kecamatan/city. Region codes (`adm4`)
   are resolved locally from a cached copy of the official
   Kepmendagri administrative code table — no guesswork, covers all of
   Indonesia, not just a handful of hardcoded cities.
2. **Official forecast**: the app calls BMKG's public API
   (`api.bmkg.go.id/publik/prakiraan-cuaca`) for that region's current
   conditions and 3-day official forecast.
3. **Model forecast**: the first time a region is requested, the app:
   - pulls ~1.5 years of real hourly history for that location's exact
     coordinates from Open-Meteo's historical archive,
   - trains a small 2-layer LSTM (72h lookback → 24h forecast of
     temperature and precipitation) on it,
   - caches the trained model to `models/<region>.pt`.

   On every later request it reuses the cached model: it fetches the most
   recent real hourly observations (Open-Meteo forecast API's `past_days`
   window) and runs them through the cached LSTM for a fast live
   prediction. Click **"Latih ulang model"** to retrain on the newest data
   at any time.
4. Reported accuracy (MAE/RMSE for temperature and precipitation) comes
   from a genuine held-out validation split of that region's own history —
   it is not a marketing number, and it will vary by location and by how
   much historical data Open-Meteo has for that spot.

This two-phase design (train once, infer live, retrain on demand) is
deliberate: training a deep network from scratch on every request would be
far too slow for an interactive app; this is the same pattern production
ML forecasting systems use.

### Trip planner ("Rencana Perjalanan" tab)

Pick an origin, a destination, and a departure time; the app:
- gets a real road route (distance + driving duration) from the public
  **OSRM** routing API,
- samples 5 points along that route (start, 25%/50%/75%, destination),
- computes each point's estimated arrival time (departure + elapsed travel
  time), and fetches Open-Meteo's forecast for that point at that specific
  hour (temperature, precipitation, cloud cover, WMO weather code),
- draws the route and weather markers on a Leaflet/OpenStreetMap map.

Waypoint weather uses Open-Meteo's own forecast directly (not the per-region
LSTM) so a trip request stays fast — training 5 separate models per trip
would take minutes. The single-location LSTM forecast is unaffected and
still available from the "Cuaca Lokasi" tab for the two endpoints.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```

Then open **http://127.0.0.1:8000/** in a browser.

Search for a location (e.g. "Kemayoran", "Bandung", "Denpasar", "Surabaya").
The first forecast for a new region takes roughly 45-90 seconds (downloading
~1.5 years of hourly history + training the LSTM); every later request for
that region reuses the cached model and returns in a few seconds.

## Project layout

```
backend/
  main.py            FastAPI app & HTTP endpoints
  wilayah.py          Region name -> BMKG adm4 code search (local cache)
  bmkg_client.py       BMKG official forecast API client
  openmeteo_client.py  Open-Meteo historical + recent-observations client
  dataset.py           Feature engineering, windowing, scaling
  model.py             PyTorch LSTM definition
  train.py             Per-region training pipeline
  infer.py             Loads cached model, runs live prediction
  storage.py           Model file path helpers
  osrm_client.py        OSRM route (distance/duration/geometry) client
  route.py              Trip planner: route + weather-along-the-way
  weather_codes.py       WMO weather code -> label + Font Awesome icon
frontend/
  index.html, style.css, app.js   Dashboard UI (vanilla JS, Chart.js, Leaflet)
data/        cached region-code lookup table (downloaded on first search)
models/      cached trained model per region (.pt + scaler + metrics json)
```

## Notes & honest limitations

- BMKG's public API only exposes forecast data, not deep historical
  archives, so historical *training* data comes from Open-Meteo
  (ERA5-based reanalysis + recent observations) for the exact lat/lon BMKG
  reports for the chosen region. BMKG's own official forecast is still
  shown for direct comparison.
- Model accuracy depends on the location and typically lands in the
  low single-digit °C MAE range for temperature — real, but not
  perfect; see the "Akurasi model" panel for the actual numbers per region.
- This is a local development server (`uvicorn --reload`), not hardened
  for public/production deployment.
- The trip planner uses `router.project-osrm.org`, OSRM's shared public
  demo server — fine for personal/demo use, but not rate-limit-free; a
  heavily used deployment should point `OSRM_URL` at a self-hosted OSRM
  instance instead.
- Route waypoint weather is a snapshot forecast for 5 points along the
  path, not a continuous simulation - real conditions between sampled
  points (and any last-minute forecast changes) can differ.
- The dashboard hero photo is by
  [Spenser Sembrat on Unsplash](https://unsplash.com/photos/ezvHNCfN5zw)
  (aerial view of a town in East Java), loaded from Unsplash's CDN.
