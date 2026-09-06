"""Maps Open-Meteo's WMO weather codes to an Indonesian label + a Font
Awesome icon class, so the frontend never has to hardcode this table."""
from __future__ import annotations

_TABLE = {
    0: ("Cerah", "fa-sun"),
    1: ("Cerah Berawan", "fa-cloud-sun"),
    2: ("Berawan Sebagian", "fa-cloud-sun"),
    3: ("Berawan Tebal", "fa-cloud"),
    45: ("Berkabut", "fa-smog"),
    48: ("Kabut Es", "fa-smog"),
    51: ("Gerimis Ringan", "fa-cloud-rain"),
    53: ("Gerimis Sedang", "fa-cloud-rain"),
    55: ("Gerimis Lebat", "fa-cloud-rain"),
    56: ("Gerimis Beku Ringan", "fa-cloud-rain"),
    57: ("Gerimis Beku Lebat", "fa-cloud-rain"),
    61: ("Hujan Ringan", "fa-cloud-showers-heavy"),
    63: ("Hujan Sedang", "fa-cloud-showers-heavy"),
    65: ("Hujan Lebat", "fa-cloud-showers-heavy"),
    66: ("Hujan Beku Ringan", "fa-cloud-showers-heavy"),
    67: ("Hujan Beku Lebat", "fa-cloud-showers-heavy"),
    71: ("Salju Ringan", "fa-snowflake"),
    73: ("Salju Sedang", "fa-snowflake"),
    75: ("Salju Lebat", "fa-snowflake"),
    77: ("Butiran Salju", "fa-snowflake"),
    80: ("Hujan Lokal Ringan", "fa-cloud-showers-heavy"),
    81: ("Hujan Lokal Sedang", "fa-cloud-showers-heavy"),
    82: ("Hujan Lokal Lebat", "fa-cloud-showers-heavy"),
    85: ("Hujan Salju Ringan", "fa-snowflake"),
    86: ("Hujan Salju Lebat", "fa-snowflake"),
    95: ("Badai Petir", "fa-cloud-bolt"),
    96: ("Badai Petir + Es Ringan", "fa-cloud-bolt"),
    99: ("Badai Petir + Es Lebat", "fa-cloud-bolt"),
}

_DEFAULT = ("Tidak diketahui", "fa-cloud-question")


def describe(code) -> dict:
    label, icon = _TABLE.get(int(code) if code is not None else -1, _DEFAULT)
    return {"code": code, "label": label, "icon": icon}
