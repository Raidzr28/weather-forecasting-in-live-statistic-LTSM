"""Trains (or retrains) one LSTM per region, on demand.

Design: rather than one global model, each requested adm4 region gets its
own small model trained on that location's own historical series and
cached to disk (models/<code>.pt). This keeps training fast (a couple of
years of hourly data is a small dataset) and lets the model specialize on
local climate patterns instead of averaging over all of Indonesia.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from . import config, dataset, storage
from .model import WeatherLSTM
from .openmeteo_client import fetch_historical

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


async def train_region(adm4_code: str, lat: float, lon: float) -> dict:
    raw = await fetch_historical(lat, lon)
    if len(raw) < config.SEQ_LEN + config.HORIZON + 100:
        raise ValueError("Not enough historical data returned by Open-Meteo for this location")

    # The actual model fitting is CPU-bound and can take tens of seconds;
    # run it in a worker thread so it doesn't freeze the async event loop
    # (and therefore the rest of the app) while it's crunching.
    return await asyncio.to_thread(_train_sync, adm4_code, lat, lon, raw)


def _train_sync(adm4_code: str, lat: float, lon: float, raw) -> dict:
    t0 = time.monotonic()

    df = dataset.add_time_features(raw)
    scale_cols = sorted(set(dataset.FEATURE_COLS) | set(config.TARGET_COLS))
    scaler = dataset.Scaler.fit(df, scale_cols)
    scaled = scaler.transform(df, scale_cols)

    X, y = dataset.make_windows(scaled, stride=config.TRAIN_STRIDE)
    n = len(X)
    n_val = max(int(n * config.VAL_FRACTION), 1)
    n_train = n - n_val

    X_train, y_train = X[:n_train], y[:n_train]
    X_val, y_val = X[n_train:], y[n_train:]

    train_loader = DataLoader(
        TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train)),
        batch_size=config.BATCH_SIZE,
        shuffle=True,
    )

    model = WeatherLSTM(n_features=len(dataset.FEATURE_COLS)).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.LEARNING_RATE)
    loss_fn = nn.MSELoss()

    model.train()
    for _epoch in range(config.EPOCHS):
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, yb)
            loss.backward()
            optimizer.step()

    metrics = _evaluate(model, X_val, y_val, scaler)

    torch.save(model.state_dict(), storage.model_path(adm4_code))
    storage.scaler_path(adm4_code).write_text(json.dumps(scaler.to_dict()))
    meta = {
        "adm4": adm4_code,
        "lat": lat,
        "lon": lon,
        "trained_at": dt.datetime.now().isoformat(timespec="seconds"),
        "train_seconds": round(time.monotonic() - t0, 1),
        "n_train_samples": int(n_train),
        "n_val_samples": int(n_val),
        "seq_len": config.SEQ_LEN,
        "horizon": config.HORIZON,
        "feature_cols": dataset.FEATURE_COLS,
        "target_cols": config.TARGET_COLS,
        "metrics": metrics,
    }
    storage.meta_path(adm4_code).write_text(json.dumps(meta, indent=2))
    return meta


def _evaluate(model: WeatherLSTM, X_val: np.ndarray, y_val: np.ndarray, scaler: dataset.Scaler) -> dict:
    model.eval()
    with torch.no_grad():
        pred = model(torch.from_numpy(X_val).to(DEVICE)).cpu().numpy()

    pred_real = scaler.inverse(pred, config.TARGET_COLS)
    true_real = scaler.inverse(y_val, config.TARGET_COLS)

    metrics = {}
    for i, col in enumerate(config.TARGET_COLS):
        err = pred_real[..., i] - true_real[..., i]
        metrics[f"mae_{col}"] = float(np.mean(np.abs(err)))
        metrics[f"rmse_{col}"] = float(np.sqrt(np.mean(err ** 2)))
    return metrics
