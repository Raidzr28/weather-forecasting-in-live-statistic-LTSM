"""Indonesian administrative region (kode wilayah) lookup.

BMKG's public API keys weather forecasts off "adm4" codes (kelurahan/desa
level, e.g. "31.71.03.1001"), following the Kepmendagri 100.1.1-6117/2022
numbering scheme. BMKG does not publish a name -> code search endpoint, so
we cache the community-maintained reference table (same numbering scheme)
once, and search it locally. This lets a user look up ANY Indonesian
village/city by name instead of relying on a small hardcoded list.
"""
from __future__ import annotations

import csv
import functools
import httpx

from . import config

_CACHE: dict[str, str] | None = None  # code -> name, loaded lazily


def _ensure_cache_file() -> None:
    if config.WILAYAH_CACHE_FILE.exists():
        return
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(config.WILAYAH_SOURCE_URL)
        resp.raise_for_status()
        config.WILAYAH_CACHE_FILE.write_bytes(resp.content)


def _load() -> dict[str, str]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    _ensure_cache_file()
    table: dict[str, str] = {}
    with open(config.WILAYAH_CACHE_FILE, encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) != 2:
                continue
            code, name = row
            table[code.strip()] = name.strip()
    _CACHE = table
    return table


def _level(code: str) -> int:
    return code.count(".") + 1


@functools.lru_cache(maxsize=4096)
def describe(adm4_code: str) -> dict:
    """Resolve an adm4 code into its full name hierarchy by truncating the
    dotted code at each ancestor level and looking each one up."""
    table = _load()
    parts = adm4_code.split(".")
    if len(parts) != 4:
        raise ValueError(f"'{adm4_code}' is not a 4-level adm code")
    adm1 = parts[0]
    adm2 = f"{parts[0]}.{parts[1]}"
    adm3 = f"{parts[0]}.{parts[1]}.{parts[2]}"
    adm4 = adm4_code
    return {
        "adm4": adm4,
        "desa": table.get(adm4, "?"),
        "kecamatan": table.get(adm3, "?"),
        "kotkab": table.get(adm2, "?"),
        "provinsi": table.get(adm1, "?"),
    }


def _rank(query: str, name: str, kecamatan: str, kotkab: str, provinsi: str) -> int | None:
    """Lower is better; None means no match. Ranks matches on the
    city/regency (kotkab) name highest, since that's what people usually
    type ("Bandung", "Surabaya"), ahead of an incidental village-name
    substring match somewhere else in the country."""
    kotkab_l = kotkab.lower()
    # "Kota X" (the city) is what people usually mean by a bare city name,
    # so it should outrank "Kab. X" (the surrounding regency) of the same name.
    if kotkab_l == f"kota {query}":
        return 0
    if kotkab_l == f"kab. {query}":
        return 1
    if kotkab_l.startswith(query):
        return 2
    if query in kotkab_l:
        return 3
    if name.lower().startswith(query):
        return 4
    if kecamatan.lower().startswith(query):
        return 5
    haystack = f"{name} {kecamatan} {kotkab} {provinsi}".lower()
    if query in haystack:
        return 6
    return None


def search(query: str, limit: int = 20) -> list[dict]:
    """Search villages/kelurahan (adm4-level entries) whose own name OR
    any ancestor (kecamatan/kota-kab/provinsi) name contains the query
    (case-insensitive), so e.g. "surabaya" matches every kelurahan inside
    Kota Surabaya even though "Surabaya" itself is only the adm2 name.
    Results are ranked so the city/regency itself outranks an unrelated
    village elsewhere in Indonesia that merely shares the substring."""
    table = _load()
    q = query.strip().lower()
    if len(q) < 3:
        return []

    scored: list[tuple[int, str]] = []
    for code, name in table.items():
        if _level(code) != 4:
            continue
        parts = code.split(".")
        adm1, adm2, adm3 = parts[0], f"{parts[0]}.{parts[1]}", f"{parts[0]}.{parts[1]}.{parts[2]}"
        kecamatan, kotkab, provinsi = table.get(adm3, ""), table.get(adm2, ""), table.get(adm1, "")
        rank = _rank(q, name, kecamatan, kotkab, provinsi)
        if rank is not None:
            scored.append((rank, code))
            if len(scored) >= 4000:  # bound worst-case scan for very short/common queries
                break

    scored.sort(key=lambda item: item[0])
    return [describe(code) for _, code in scored[:limit]]
