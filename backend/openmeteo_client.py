"""Client for Open-Meteo (no API key required).

- Historical archive API: long hourly time series used to TRAIN the model.
- Forecast API (with past_days): recent hourly observations used to feed
  the trained model at inference time.
"""
from __future__ import annotations

import datetime as dt

import httpx
import pandas as pd

from . import config


def _to_dataframe(hourly: dict) -> pd.DataFrame:
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df[config.HOURLY_VARS]
    df = df.interpolate(limit_direction="both")
    return df.dropna()


async def fetch_historical(lat: float, lon: float, years: float = config.HISTORY_YEARS) -> pd.DataFrame:
    """Fetch hourly historical weather for training, ending yesterday
    (archive data lags a couple of days behind real time)."""
    end = dt.date.today() - dt.timedelta(days=2)
    start = end - dt.timedelta(days=int(years * 365))
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(config.HOURLY_VARS),
        "timezone": "Asia/Jakarta",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(config.OPEN_METEO_ARCHIVE_URL, params=params)
    resp.raise_for_status()
    payload = resp.json()
    return _to_dataframe(payload["hourly"])


async def fetch_recent(lat: float, lon: float, past_days: int = 5) -> pd.DataFrame:
    """Fetch the most recent hourly observations (for model input) via the
    forecast endpoint's `past_days` window."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(config.HOURLY_VARS),
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": "Asia/Jakarta",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(config.OPEN_METEO_FORECAST_URL, params=params)
    resp.raise_for_status()
    payload = resp.json()
    df = _to_dataframe(payload["hourly"])
    # The API returns naive local ("Asia/Jakarta") timestamps, so compare
    # against wall-clock Jakarta time rather than the host machine's own
    # local time (which may be in a different timezone).
    now_jkt = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None).floor("h")
    return df[df.index <= now_jkt]


ROUTE_VARS = ["temperature_2m", "precipitation", "precipitation_probability", "weather_code", "cloud_cover"]


async def fetch_route_point_forecasts(points: list[tuple[float, float]], forecast_days: int) -> list[pd.DataFrame]:
    """Fetch hourly forecast (temp/precip/weather code/cloud cover) for
    several lat/lon points in a single request - used to sample weather
    along a trip's waypoints without training a model per point."""
    forecast_days = max(1, min(forecast_days, 16))
    params = {
        "latitude": ",".join(str(p[0]) for p in points),
        "longitude": ",".join(str(p[1]) for p in points),
        "hourly": ",".join(ROUTE_VARS),
        "forecast_days": forecast_days,
        "timezone": "Asia/Jakarta",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(config.OPEN_METEO_FORECAST_URL, params=params)
    resp.raise_for_status()
    payload = resp.json()

    locations = payload if isinstance(payload, list) else [payload]
    frames = []
    for loc in locations:
        df = pd.DataFrame(loc["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        df = df.set_index("time").sort_index()
        frames.append(df)
    return frames


def nearest_row(df: pd.DataFrame, target: pd.Timestamp) -> dict:
    idx = df.index.get_indexer([target], method="nearest")[0]
    row = df.iloc[idx]
    return row.to_dict()
