from datetime import datetime, timezone

import pandas as pd

from eu_prices.providers import ProviderError
from eu_prices.service import current_prices, daily_stats, fetch_prices, to_hourly

START = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 10, 8, 2, 0, tzinfo=timezone.utc)


class Broken:
    name = "broken"

    def fetch(self, zone, start, end):
        raise ProviderError("down")


class Fixed:
    name = "fixed"

    def __init__(self, freq="15min"):
        self.freq = freq

    def fetch(self, zone, start, end):
        idx = pd.date_range(start, end, freq=self.freq, inclusive="left")
        return pd.Series(range(len(idx)), index=idx, dtype="float64")


def test_falls_back_to_next_provider():
    result = fetch_prices(["FR", "DE-LU"], START, END, [Broken(), Fixed()])
    assert result.errors == {}
    assert set(result.prices["source"]) == {"fixed"}
    assert len(result.prices) == 2 * 8


def test_reports_zone_errors_when_all_providers_fail():
    result = fetch_prices(["FR"], START, END, [Broken()])
    assert result.prices.empty
    assert "down" in result.errors["FR"]


def test_current_price_handles_mixed_resolutions():
    a = fetch_prices(["FR"], START, END, [Fixed("15min")]).prices
    b = fetch_prices(["ES"], START, END, [Fixed("60min")]).prices
    now = datetime(2026, 10, 8, 1, 20, tzinfo=timezone.utc)
    cur = current_prices(pd.concat([a, b]), now).set_index("zone")["price"]
    assert cur["FR"] == 5.0  # 01:15 slot
    assert cur["ES"] == 1.0  # 01:00 slot


def test_hourly_and_daily_stats():
    p = fetch_prices(["FR"], START, END, [Fixed()]).prices
    h = to_hourly(p)
    assert list(h["price"]) == [1.5, 5.5]
    d = daily_stats(p, "Europe/Brussels")
    assert d.iloc[0][["min", "mean", "max"]].tolist() == [0.0, 3.5, 7.0]
