"""Filesystem paths for per-region cached models."""
from __future__ import annotations

from . import config


def safe_code(adm4_code: str) -> str:
    return adm4_code.replace(".", "_")


def model_path(adm4_code: str):
    return config.MODELS_DIR / f"{safe_code(adm4_code)}.pt"


def scaler_path(adm4_code: str):
    return config.MODELS_DIR / f"{safe_code(adm4_code)}_scaler.json"


def meta_path(adm4_code: str):
    return config.MODELS_DIR / f"{safe_code(adm4_code)}_meta.json"


def has_trained_model(adm4_code: str) -> bool:
    return model_path(adm4_code).exists() and scaler_path(adm4_code).exists() and meta_path(adm4_code).exists()
