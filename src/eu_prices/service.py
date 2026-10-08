"""Fetch prices for many zones with provider fallback, plus small analytics helpers.

Pure Python, no Streamlit imports, so it can be tested and reused (e.g. by a
future API or scheduled job).
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from eu_prices.providers import EnergyChartsProvider, EntsoeProvider, PriceProvider, ProviderError
from eu_prices.zones import BY_CODE

COLUMNS = ["timestamp", "zone", "price", "source"]


@dataclass
class FetchResult:
    prices: pd.DataFrame  # long format: timestamp (UTC), zone, price (EUR/MWh), source
    errors: dict[str, str] = field(default_factory=dict)  # zone -> last error message


def build_providers(entsoe_token: str | None) -> list[PriceProvider]:
    """ENTSO-E first when a token is configured, energy-charts.info always as fallback."""
    if os.environ.get("EU_PRICES_DEMO") == "1":
        from eu_prices.providers.demo import DemoProvider

        return [DemoProvider()]
    providers: list[PriceProvider] = []
    if entsoe_token:
        providers.append(EntsoeProvider(entsoe_token))
    providers.append(EnergyChartsProvider())
    return providers


def _fetch_zone(providers: list[PriceProvider], code: str, start: datetime, end: datetime):
    zone = BY_CODE[code]
    last_error = "no provider"
    for provider in providers:
        try:
            series = provider.fetch(zone, start, end)
        except ProviderError as exc:
            last_error = str(exc)
            continue
        if not series.empty:
            return code, series, provider.name, None
        last_error = f"{provider.name}: {code}: no data in range"
    return code, None, None, last_error


def fetch_prices(
    zone_codes: list[str],
    start: datetime,
    end: datetime,
    providers: list[PriceProvider],
    max_workers: int = 8,
) -> FetchResult:
    frames, errors = [], {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        jobs = [pool.submit(_fetch_zone, providers, c, start, end) for c in zone_codes]
        for job in jobs:
            code, series, source, error = job.result()
            if series is None:
                errors[code] = error
                continue
            frames.append(
                pd.DataFrame(
                    {"timestamp": series.index, "zone": code, "price": series.values, "source": source}
                )
            )
    prices = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    return FetchResult(prices=prices, errors=errors)


def current_prices(prices: pd.DataFrame, now: datetime) -> pd.DataFrame:
    """Price of the delivery interval containing ``now`` for each zone.

    Zones settle at different resolutions (15 or 60 minutes), so we take the
    last interval that started at or before ``now``.
    """
    if prices.empty:
        return pd.DataFrame(columns=["zone", "price", "interval_start", "source"])
    started = prices[prices["timestamp"] <= pd.Timestamp(now)]
    latest = started.sort_values("timestamp").groupby("zone").tail(1)
    out = latest.rename(columns={"timestamp": "interval_start"})[
        ["zone", "price", "interval_start", "source"]
    ]
    return out.sort_values("price").reset_index(drop=True)


def to_hourly(prices: pd.DataFrame) -> pd.DataFrame:
    """Average sub-hourly intervals to hourly so zones are comparable."""
    if prices.empty:
        return prices
    hourly = (
        prices.assign(timestamp=prices["timestamp"].dt.floor("h"))
        .groupby(["zone", "timestamp"], as_index=False)
        .agg(price=("price", "mean"), source=("source", "first"))
    )
    return hourly[COLUMNS]


def daily_stats(prices: pd.DataFrame, tz: str) -> pd.DataFrame:
    """Min / mean / max per zone and local calendar day."""
    if prices.empty:
        return pd.DataFrame(columns=["zone", "day", "min", "mean", "max"])
    local_day = prices["timestamp"].dt.tz_convert(tz).dt.date
    return (
        prices.assign(day=local_day)
        .groupby(["zone", "day"])["price"]
        .agg(["min", "mean", "max"])
        .reset_index()
    )
