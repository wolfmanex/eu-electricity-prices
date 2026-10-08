"""energy-charts.info (Fraunhofer ISE) public API. No key required.

GET https://api.energy-charts.info/price?bzn=DE-LU&start=2026-10-07&end=2026-10-08
-> {"unix_seconds": [...], "price": [...], "unit": "EUR / MWh", ...}

``end`` is an inclusive date, so a one-day request returns two days of data.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import requests

from eu_prices.providers.base import HTTP_TIMEOUT, USER_AGENT, ProviderError, clip
from eu_prices.zones import Zone

BASE_URL = "https://api.energy-charts.info/price"


class EnergyChartsProvider:
    name = "energy-charts.info"

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)

    def fetch(self, zone: Zone, start: datetime, end: datetime) -> pd.Series:
        params = {
            "bzn": zone.energy_charts_code,
            "start": start.date().isoformat(),
            "end": (end - timedelta(seconds=1)).date().isoformat(),
        }
        try:
            resp = self.session.get(BASE_URL, params=params, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise ProviderError(f"{self.name}: {zone.code}: {exc}") from exc
        return clip(parse(payload, zone.code), start, end)


def parse(payload: dict, zone_code: str = "") -> pd.Series:
    unit = payload.get("unit", "")
    if unit and unit.replace(" ", "") != "EUR/MWh":
        raise ProviderError(f"energy-charts.info: {zone_code}: unexpected unit {unit!r}")
    seconds = payload.get("unix_seconds") or []
    prices = payload.get("price") or []
    if not seconds or len(seconds) != len(prices):
        raise ProviderError(f"energy-charts.info: {zone_code}: no data")
    index = pd.to_datetime(seconds, unit="s", utc=True)
    series = pd.Series(prices, index=index, dtype="float64", name=zone_code).dropna()
    if series.empty:
        raise ProviderError(f"energy-charts.info: {zone_code}: no data")
    return series
