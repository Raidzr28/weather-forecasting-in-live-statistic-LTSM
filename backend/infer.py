"""Runs live inference with an already-trained per-region model: pulls the
most recent hours of real observations from Open-Meteo and feeds them
through the cached LSTM to produce the next HORIZON hours forecast."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import torch

from . import config, dataset, storage
from .model import WeatherLSTM
from .openmeteo_client import fetch_recent
from .train import DEVICE


def load_meta(adm4_code: str) -> dict:
    return json.loads(storage.meta_path(adm4_code).read_text())


async def predict_region(adm4_code: str, lat: float, lon: float) -> dict:
    if not storage.has_trained_model(adm4_code):
        raise FileNotFoundError(f"No trained model for {adm4_code} yet")

    meta = load_meta(adm4_code)
    scaler = dataset.Scaler.from_dict(json.loads(storage.scaler_path(adm4_code).read_text()))

    model = WeatherLSTM(n_features=len(dataset.FEATURE_COLS))
    model.load_state_dict(
        torch.load(storage.model_path(adm4_code), map_location=DEVICE, weights_only=True)
    )
    model.to(DEVICE).eval()

    recent = await fetch_recent(lat, lon, past_days=6)
    recent = dataset.add_time_features(recent)
    if len(recent) < config.SEQ_LEN:
        raise ValueError("Not enough recent observations returned by Open-Meteo for inference")

    window = recent.iloc[-config.SEQ_LEN :]
    scale_cols = sorted(set(dataset.FEATURE_COLS) | set(config.TARGET_COLS))
    scaled = scaler.transform(window, scale_cols)
    x = scaled[dataset.FEATURE_COLS].to_numpy(dtype=np.float32)[None, ...]

    with torch.no_grad():
        pred = model(torch.from_numpy(x).to(DEVICE)).cpu().numpy()[0]  # (horizon, n_targets)

    pred_real = scaler.inverse(pred, config.TARGET_COLS)
    pred_real[:, config.TARGET_COLS.index("precipitation")] = np.clip(
        pred_real[:, config.TARGET_COLS.index("precipitation")], 0, None
    )

    last_ts = window.index[-1]
    future_times = pd.date_range(last_ts + pd.Timedelta(hours=1), periods=config.HORIZON, freq="h")

    forecast = []
    for i, ts in enumerate(future_times):
        row = {"datetime": ts.isoformat()}
        for j, col in enumerate(config.TARGET_COLS):
            row[col] = round(float(pred_real[i, j]), 2)
        forecast.append(row)

    return {
        "adm4": adm4_code,
        "generated_at": pd.Timestamp.now().isoformat(),
        "input_last_observed": last_ts.isoformat(),
        "model_trained_at": meta["trained_at"],
        "model_metrics": meta["metrics"],
        "forecast": forecast,
    }
