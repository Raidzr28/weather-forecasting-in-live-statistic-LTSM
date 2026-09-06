"""Client for the public OSRM routing demo server (no API key).

Note: router.project-osrm.org is a shared public demo instance meant for
light/evaluation use, not a production SLA - fine for this app's scale.
"""
from __future__ import annotations

import httpx

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


class RouteError(RuntimeError):
    pass


async def get_route(lat1: float, lon1: float, lat2: float, lon2: float) -> dict:
    """Returns {distance_m, duration_s, geometry: [(lat, lon), ...]}."""
    coords = f"{lon1},{lat1};{lon2},{lat2}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{OSRM_URL}/{coords}",
            params={"overview": "full", "geometries": "geojson"},
        )
    if resp.status_code != 200:
        raise RouteError(f"OSRM returned HTTP {resp.status_code}")
    payload = resp.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RouteError(f"OSRM could not find a route: {payload.get('message', payload.get('code'))}")

    route = payload["routes"][0]
    # geometry coords come as [lon, lat] pairs; flip to (lat, lon) for the map
    geometry = [(pt[1], pt[0]) for pt in route["geometry"]["coordinates"]]

    return {
        "distance_m": route["distance"],
        "duration_s": route["duration"],
        "geometry": geometry,
    }
