from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import bmkg_client, config, infer, route, storage, train, wilayah
from .bmkg_client import BmkgError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("weather-app")

app = FastAPI(title="Indonesia Live Weather Forecast (BMKG + LSTM)")


@app.get("/api/search")
async def search_region(q: str):
    """Search Indonesian villages/cities by name -> BMKG adm4 codes."""
    return {"results": wilayah.search(q)}


@app.get("/api/region/{adm4}/live")
async def region_live(adm4: str):
    """Official BMKG current forecast for a region (also used to resolve
    lat/lon, which the trained model needs)."""
    try:
        return await bmkg_client.fetch_forecast(adm4)
    except BmkgError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/region/{adm4}/model-status")
async def model_status(adm4: str):
    if not storage.has_trained_model(adm4):
        return {"trained": False}
    return {"trained": True, "meta": infer.load_meta(adm4)}


@app.get("/api/region/{adm4}/forecast")
async def region_model_forecast(adm4: str):
    """Our own LSTM forecast. Trains a model for this region on first
    request (may take up to ~1 minute), then reuses the cached model on
    subsequent calls."""
    try:
        live = await bmkg_client.fetch_forecast(adm4)
    except BmkgError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    lat, lon = live["location"]["lat"], live["location"]["lon"]

    if not storage.has_trained_model(adm4):
        log.info("No cached model for %s, training now...", adm4)
        await train.train_region(adm4, lat, lon)

    try:
        result = await infer.predict_region(adm4, lat, lon)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result["location"] = live["location"]
    return result


@app.post("/api/region/{adm4}/retrain")
async def retrain(adm4: str):
    try:
        live = await bmkg_client.fetch_forecast(adm4)
    except BmkgError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    lat, lon = live["location"]["lat"], live["location"]["lon"]
    meta = await train.train_region(adm4, lat, lon)
    return meta


@app.get("/api/route")
async def plan_route(from_adm4: str, to_adm4: str, depart: Optional[str] = None):
    """Road route + distance between two regions, with estimated weather
    at a few points along the way, timed to the traveller's actual ETA at
    each point (departure time + elapsed travel time)."""
    now_jkt = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)
    if depart:
        try:
            depart_ts = pd.Timestamp(depart)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Format waktu keberangkatan tidak valid") from exc
    else:
        depart_ts = now_jkt
    if depart_ts < now_jkt:
        depart_ts = now_jkt

    try:
        return await route.plan_trip(from_adm4, to_adm4, depart_ts)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# --- static frontend -------------------------------------------------
app.mount("/static", StaticFiles(directory=str(config.FRONTEND_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(config.FRONTEND_DIR / "index.html"))
