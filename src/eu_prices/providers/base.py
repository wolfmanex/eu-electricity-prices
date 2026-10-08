from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd

from eu_prices.zones import Zone

HTTP_TIMEOUT = 20  # seconds
USER_AGENT = "eu-electricity-prices/0.1 (+https://github.com/wolfmanex/eu-electricity-prices)"


class ProviderError(RuntimeError):
    """A provider could not return prices for a zone."""


class PriceProvider(Protocol):
    name: str

    def fetch(self, zone: Zone, start: datetime, end: datetime) -> pd.Series:
        """Return day-ahead prices in EUR/MWh for ``[start, end)``.

        ``start`` and ``end`` are timezone-aware. The result is indexed by
        tz-aware UTC timestamps marking the start of each delivery interval,
        sorted, without duplicates. Raises ``ProviderError`` on failure.
        """
        ...


def clip(series: pd.Series, start: datetime, end: datetime) -> pd.Series:
    series = series[~series.index.duplicated(keep="first")].sort_index()
    return series[(series.index >= start) & (series.index < end)]
