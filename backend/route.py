"""Trip planning: road route between two regions (OSRM) + estimated
weather at several points along that route, timed to when the traveller
is actually expected to be there (departure time + elapsed travel time)."""
from __future__ import annotations

import math

import pandas as pd

from . import bmkg_client, openmeteo_client, osrm_client, weather_codes
from .bmkg_client import BmkgError
from .osrm_client import RouteError

MAX_GEOMETRY_POINTS = 400
MIN_WAYPOINTS = 5
MAX_WAYPOINTS = 12
MINUTES_PER_WAYPOINT = 30  # aim for roughly one sampled point every 30 min of travel

# rain-probability bands used to colour the route line on the map
RAIN_BANDS = [
    (20, "#4ade80"),   # < 20% - calm / low chance
    (50, "#fbbf24"),   # 20-50% - moderate chance
    (101, "#f87171"),  # >= 50% - high chance
]


def _downsample(points: list, max_points: int) -> list:
    if len(points) <= max_points:
        return points
    stride = math.ceil(len(points) / max_points)
    sampled = points[::stride]
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return sampled


def _rain_color(pct: float) -> str:
    for threshold, color in RAIN_BANDS:
        if pct < threshold:
            return color
    return RAIN_BANDS[-1][1]


def _waypoint_count(duration_s: float) -> int:
    n = round(duration_s / 60 / MINUTES_PER_WAYPOINT) + 1
    return max(MIN_WAYPOINTS, min(MAX_WAYPOINTS, n))


async def plan_trip(from_adm4: str, to_adm4: str, depart: pd.Timestamp) -> dict:
    try:
        origin = await bmkg_client.fetch_forecast(from_adm4)
        dest = await bmkg_client.fetch_forecast(to_adm4)
    except BmkgError as exc:
        raise ValueError(str(exc)) from exc

    o_loc, d_loc = origin["location"], dest["location"]

    try:
        route = await osrm_client.get_route(o_loc["lat"], o_loc["lon"], d_loc["lat"], d_loc["lon"])
    except RouteError as exc:
        raise ValueError(str(exc)) from exc

    geometry = _downsample(route["geometry"], MAX_GEOMETRY_POINTS)  # [(lat, lon), ...]
    duration_s = route["duration_s"]

    n_waypoints = _waypoint_count(duration_s)
    fractions = [i / (n_waypoints - 1) for i in range(n_waypoints)]
    waypoint_idx = [round(f * (len(geometry) - 1)) for f in fractions]
    waypoint_pts = [geometry[i] for i in waypoint_idx]
    etas = [depart + pd.Timedelta(seconds=f * duration_s) for f in fractions]

    now_jkt = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)
    last_eta = max(etas)
    forecast_days = max(1, math.ceil((last_eta - now_jkt).total_seconds() / 86400) + 1)

    frames = await openmeteo_client.fetch_route_point_forecasts(waypoint_pts, forecast_days)

    waypoints = []
    for i, ((lat, lon), eta, df, frac) in enumerate(zip(waypoint_pts, etas, frames, fractions)):
        if i == 0:
            label = "Berangkat"
        elif i == n_waypoints - 1:
            label = "Tiba"
        else:
            label = f"{round(frac * 100)}% perjalanan"

        row = openmeteo_client.nearest_row(df, eta)
        w = weather_codes.describe(row.get("weather_code"))
        rain_prob = float(row.get("precipitation_probability") or 0)
        waypoints.append(
            {
                "label": label,
                "fraction": frac,
                "lat": lat,
                "lon": lon,
                "eta": eta.isoformat(),
                "temperature_c": round(float(row["temperature_2m"]), 1),
                "precipitation_mm": round(float(row["precipitation"]), 2),
                "rain_probability_pct": round(rain_prob),
                "cloud_cover_pct": round(float(row["cloud_cover"])),
                "weather_label": w["label"],
                "weather_icon": w["icon"],
            }
        )

    # Colour each stretch of the route between two consecutive waypoints by
    # the rain probability at that stretch, so the line itself communicates
    # where along the trip rain is more/less likely.
    segments = []
    for i in range(len(waypoint_idx) - 1):
        start_idx, end_idx = waypoint_idx[i], waypoint_idx[i + 1]
        coords = geometry[start_idx : end_idx + 1]
        if len(coords) < 2:
            coords = geometry[start_idx : start_idx + 2]
        seg_prob = round((waypoints[i]["rain_probability_pct"] + waypoints[i + 1]["rain_probability_pct"]) / 2)
        segments.append({"coords": coords, "rain_probability_pct": seg_prob, "color": _rain_color(seg_prob)})

    return {
        "from": {"adm4": from_adm4, **o_loc},
        "to": {"adm4": to_adm4, **d_loc},
        "depart": depart.isoformat(),
        "distance_km": round(route["distance_m"] / 1000, 1),
        "duration_min": round(duration_s / 60),
        "arrival": etas[-1].isoformat(),
        "geometry": geometry,
        "segments": segments,
        "waypoints": waypoints,
    }
