# Graph Report - weather forecasting in live statistic using API  (2026-09-25)

## Corpus Check
- 18 files · ~7,904 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 161 nodes · 291 edges · 11 communities
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 3 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `40c155ee`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- train.py
- route.py
- app.js
- main.py
- Scaler
- wilayah.py
- renderPlaceRow
- Prakiraan Cuaca Indonesia — BMKG + LSTM
- loadAll
- renderTrip
- drawCharts

## God Nodes (most connected - your core abstractions)
1. `plan_trip()` - 11 edges
2. `Scaler` - 9 edges
3. `predict_region()` - 9 edges
4. `_train_sync()` - 9 edges
5. `WeatherLSTM` - 8 edges
6. `loadAll()` - 8 edges
7. `fetch_forecast()` - 7 edges
8. `region_model_forecast()` - 7 edges
9. `has_trained_model()` - 7 edges
10. `search()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `plan_trip()` --calls--> `fetch_forecast()`  [EXTRACTED]
  backend/route.py → backend/bmkg_client.py
- `_evaluate()` --references--> `Scaler`  [EXTRACTED]
  backend/train.py → backend/dataset.py
- `_train_sync()` --calls--> `make_windows()`  [EXTRACTED]
  backend/train.py → backend/dataset.py
- `predict_region()` --calls--> `fetch_recent()`  [EXTRACTED]
  backend/infer.py → backend/openmeteo_client.py
- `region_model_forecast()` --calls--> `predict_region()`  [EXTRACTED]
  backend/main.py → backend/infer.py

## Import Cycles
- None detected.

## Communities (11 total, 0 thin omitted)

### Community 0 - "train.py"
Cohesion: 0.16
Nodes (19): add_time_features(), Feature engineering, windowing and scaling shared by training & inference., load_meta(), predict_region(), Runs live inference with an already-trained per-region model: pulls the most…, model_status(), LSTM sequence-to-vector model: consumes SEQ_LEN hours of history and predicts…, WeatherLSTM (+11 more)

### Community 1 - "route.py"
Cohesion: 0.11
Nodes (24): fetch_historical(), fetch_recent(), fetch_route_point_forecasts(), nearest_row(), DataFrame, Timestamp, Client for Open-Meteo (no API key required). - Historical archive API: long…, Fetch hourly historical weather for training, ending yesterday (archive data… (+16 more)

### Community 2 - "app.js"
Cohesion: 0.07
Nodes (24): bmkgTable, dashboard, metricsContent, nowContent, regionBreadcrumb, regionInfo, regionTitle, regionTitleText (+16 more)

### Community 3 - "main.py"
Cohesion: 0.15
Nodes (18): BmkgError, fetch_forecast(), RuntimeError, Client for BMKG's public "prakiraan cuaca" (weather forecast) API. Docs /…, Fetch BMKG's official forecast for a kelurahan-level adm4 code. Returns a dict…, index(), plan_route(), Search Indonesian villages/cities by name -> BMKG adm4 codes. (+10 more)

### Community 4 - "Scaler"
Cohesion: 0.20
Nodes (6): make_windows(), DataFrame, ndarray, Simple per-column standardization, saved/loaded as plain dict so it has no…, Slide a fixed window over the (already scaled) hourly frame to build supervised…, Scaler

### Community 5 - "wilayah.py"
Cohesion: 0.29
Nodes (10): describe(), _ensure_cache_file(), _level(), _load(), _rank(), Indonesian administrative region (kode wilayah) lookup. BMKG's public API keys…, Resolve an adm4 code into its full name hierarchy by truncating the dotted code…, Lower is better; None means no match. Ranks matches on the city/regency… (+2 more)

### Community 6 - "renderPlaceRow"
Cohesion: 0.46
Nodes (8): loadList(), placeName(), pushHistory(), renderPlaceRow(), renderPlaces(), selectRegion(), storeList(), toggleSaved()

### Community 7 - "Prakiraan Cuaca Indonesia — BMKG + LSTM"
Cohesion: 0.25
Nodes (7): How it works, Notes & honest limitations, Prakiraan Cuaca Indonesia — BMKG + LSTM, Project layout, Run, Setup, Trip planner ("Rencana Perjalanan" tab)

### Community 8 - "loadAll"
Cohesion: 0.29
Nodes (7): countUp(), hideStatus(), loadAll(), renderBmkgTable(), renderNow(), showLoadingCard(), showStatus()

### Community 9 - "renderTrip"
Cohesion: 0.43
Nodes (7): fmtDateTime(), fmtDuration(), rainColor(), renderTrip(), renderTripMap(), renderTripWaypoints(), tripDivIcon()

### Community 10 - "drawCharts"
Cohesion: 0.40
Nodes (5): drawCharts(), fmtLabel(), fmtStamp(), hourKey(), renderModel()

## Knowledge Gaps
- **29 isolated node(s):** `tabButtons`, `tabIndicator`, `views`, `regionInfo`, `regionTitle` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Scaler` connect `Scaler` to `train.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `plan_trip()` connect `route.py` to `main.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **What connects `tabButtons`, `tabIndicator`, `views` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `route.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Should `app.js` be split into smaller, more focused modules?**
  _Cohesion score 0.07407407407407407 - nodes in this community are weakly interconnected._