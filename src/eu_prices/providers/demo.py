"""Deterministic synthetic prices for offline development (EU_PRICES_DEMO=1)."""

from __future__ import annotations

import zlib
from datetime import datetime

import numpy as np
import pandas as pd

from eu_prices.zones import Zone


class DemoProvider:
    name = "demo data"

    def fetch(self, zone: Zone, start: datetime, end: datetime) -> pd.Series:
        idx = pd.date_range(start, end, freq="15min", inclusive="left").tz_convert("UTC")
        rng = np.random.default_rng(zlib.crc32(zone.code.encode()))
        base = rng.uniform(20, 160)
        hour = idx.hour + idx.minute / 60
        # Morning and evening peaks with a midday solar dip.
        shape = 25 * np.sin((hour - 6) / 24 * 2 * np.pi) - 30 * np.exp(-((hour - 12) ** 2) / 6)
        noise = rng.normal(0, 6, len(idx))
        return pd.Series(np.round(base + shape + noise, 2), index=idx, name=zone.code)
