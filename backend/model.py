"""LSTM sequence-to-vector model: consumes SEQ_LEN hours of history and
predicts the next HORIZON hours of each target variable in one shot
(multi-horizon regression head, a standard direct-forecasting approach)."""
from __future__ import annotations

import torch
from torch import nn

from . import config


class WeatherLSTM(nn.Module):
    def __init__(
        self,
        n_features: int,
        n_targets: int = len(config.TARGET_COLS),
        horizon: int = config.HORIZON,
        hidden_size: int = config.HIDDEN_SIZE,
        num_layers: int = config.NUM_LAYERS,
        dropout: float = config.DROPOUT,
    ):
        super().__init__()
        self.horizon = horizon
        self.n_targets = n_targets
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, horizon * n_targets),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, n_features)
        out, _ = self.lstm(x)
        last_step = out[:, -1, :]
        y = self.head(last_step)
        return y.view(-1, self.horizon, self.n_targets)
