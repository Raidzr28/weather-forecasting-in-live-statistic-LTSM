"""Client for BMKG's public "prakiraan cuaca" (weather forecast) API.

Docs / source: https://data.bmkg.go.id/prakiraan-cuaca/
No API key required. Rate limit: 60 req/min/IP.
"""
from __future__ import annotations

import httpx

from . import config


class BmkgError(RuntimeError):
    pass


async def fetch_forecast(adm4_code: str) -> dict:
    """Fetch BMKG's official forecast for a kelurahan-level adm4 code.

    Returns a dict with:
      - location: {lat, lon, desa, kecamatan, kotkab, provinsi, timezone}
      - forecast: flat list of 3-hourly entries (datetime, t, hu, tp,
        weather_desc, weather_desc_en, ws, wd, cloud_cover, image)
    """
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(config.BMKG_FORECAST_URL, params={"adm4": adm4_code})
    if resp.status_code != 200:
        raise BmkgError(f"BMKG API returned HTTP {resp.status_code} for adm4={adm4_code}")
    payload = resp.json()

    lokasi = payload.get("lokasi") or {}
    if "lat" not in lokasi or "lon" not in lokasi:
        raise BmkgError(f"BMKG API returned no location data for adm4={adm4_code}")

    entries = []
    for block in payload.get("data", []):
        for slot in block.get("cuaca", []):
            # BMKG nests each day as its own list of 3-hourly slots
            if isinstance(slot, list):
                entries.extend(slot)
            else:
                entries.append(slot)

    entries.sort(key=lambda e: e.get("local_datetime", e.get("datetime", "")))

    return {
        "location": {
            "lat": float(lokasi["lat"]),
            "lon": float(lokasi["lon"]),
            "desa": lokasi.get("desa"),
            "kecamatan": lokasi.get("kecamatan"),
            "kotkab": lokasi.get("kotkab"),
            "provinsi": lokasi.get("provinsi"),
            "timezone": lokasi.get("timezone", "Asia/Jakarta"),
        },
        "forecast": [
            {
                "datetime": e.get("local_datetime"),
                "temperature_c": e.get("t"),
                "humidity_pct": e.get("hu"),
                "precipitation_mm": e.get("tp"),
                "cloud_cover_pct": e.get("tcc"),
                "weather_desc": e.get("weather_desc"),
                "weather_desc_en": e.get("weather_desc_en"),
                "wind_speed_kmh": e.get("ws"),
                "wind_dir": e.get("wd"),
                "icon": e.get("image"),
            }
            for e in entries
        ],
    }
