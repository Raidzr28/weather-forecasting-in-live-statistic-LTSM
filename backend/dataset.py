"""Feature engineering, windowing and scaling shared by training & inference."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

ENGINEERED_COLS = ["hour_sin", "hour_cos", "doy_sin", "doy_cos"]
FEATURE_COLS = config.HOURLY_VARS + ENGINEERED_COLS


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    hour = df.index.hour + df.index.minute / 60.0
    doy = df.index.dayofyear
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    return df


class Scaler:
    """Simple per-column standardization, saved/loaded as plain dict so it
    has no pickle/version-compat baggage."""

    def __init__(self, mean: dict[str, float], std: dict[str, float]):
        self.mean = mean
        self.std = std

    @classmethod
    def fit(cls, df: pd.DataFrame, cols: list[str]) -> "Scaler":
        mean = {c: float(df[c].mean()) for c in cols}
        std = {c: float(df[c].std() or 1.0) for c in cols}
        return cls(mean, std)

    def transform(self, df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        out = df.copy()
        for c in cols:
            out[c] = (out[c] - self.mean[c]) / self.std[c]
        return out

    def inverse(self, values: np.ndarray, cols: list[str]) -> np.ndarray:
        # values shape (..., len(cols))
        mean = np.array([self.mean[c] for c in cols])
        std = np.array([self.std[c] for c in cols])
        return values * std + mean

    def to_dict(self) -> dict:
        return {"mean": self.mean, "std": self.std}

    @classmethod
    def from_dict(cls, d: dict) -> "Scaler":
        return cls(d["mean"], d["std"])


def make_windows(
    df: pd.DataFrame,
    seq_len: int = config.SEQ_LEN,
    horizon: int = config.HORIZON,
    stride: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Slide a fixed window over the (already scaled) hourly frame to build
    supervised (X, y) pairs: X = past seq_len hours of all features,
    y = next horizon hours of the target columns."""
    feat = df[FEATURE_COLS].to_numpy(dtype=np.float32)
    targ = df[config.TARGET_COLS].to_numpy(dtype=np.float32)

    n = len(df)
    last_start = n - seq_len - horizon
    starts = range(0, last_start + 1, stride)

    X = np.stack([feat[s : s + seq_len] for s in starts])
    y = np.stack([targ[s + seq_len : s + seq_len + horizon] for s in starts])
    return X, y
