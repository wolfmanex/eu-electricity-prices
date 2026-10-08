"""ENTSO-E Transparency Platform, day-ahead prices (document type A44).

Needs a free security token: register at https://transparency.entsoe.eu and
request "Restful API access" by email (see docs/DEPLOYMENT.md).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from eu_prices.providers.base import HTTP_TIMEOUT, USER_AGENT, ProviderError, clip
from eu_prices.zones import Zone

BASE_URL = "https://web-api.tp.entsoe.eu/api"
_RESOLUTION = re.compile(r"^PT(\d+)M$")


class EntsoeProvider:
    name = "ENTSO-E"

    def __init__(self, token: str, session: requests.Session | None = None):
        if not token:
            raise ValueError("ENTSO-E token is required")
        self.token = token
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)

    def fetch(self, zone: Zone, start: datetime, end: datetime) -> pd.Series:
        params = {
            "securityToken": self.token,
            "documentType": "A44",
            "in_Domain": zone.eic,
            "out_Domain": zone.eic,
            "periodStart": _fmt(start),
            "periodEnd": _fmt(end),
        }
        try:
            resp = self.session.get(BASE_URL, params=params, timeout=HTTP_TIMEOUT)
        except requests.RequestException as exc:
            raise ProviderError(f"{self.name}: {zone.code}: {exc}") from exc
        if resp.status_code == 401:
            raise ProviderError(f"{self.name}: invalid or missing security token")
        # Errors and "no data" come back as an Acknowledgement document, often with HTTP 200.
        series = parse(resp.text, zone.code)
        return clip(series, start, end)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%d%H%M")


def _strip_ns(root: ET.Element) -> None:
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]


def parse(xml_text: str, zone_code: str = "") -> pd.Series:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ProviderError(f"ENTSO-E: {zone_code}: unreadable response") from exc
    _strip_ns(root)

    if root.tag == "Acknowledgement_MarketDocument":
        reason = root.findtext("Reason/text") or "no data"
        raise ProviderError(f"ENTSO-E: {zone_code}: {reason}")

    # A zone can publish the same delivery period at several resolutions
    # (e.g. hourly and 15-minute during the 2025 MTU change). Keep the finest.
    best: dict[pd.Timestamp, tuple[int, float]] = {}
    for period in root.iter("Period"):
        m = _RESOLUTION.match(period.findtext("resolution") or "")
        if not m:
            continue
        step = int(m.group(1))
        period_start = pd.Timestamp(period.findtext("timeInterval/start"))
        period_end = pd.Timestamp(period.findtext("timeInterval/end"))
        n_slots = int((period_end - period_start) / pd.Timedelta(minutes=step))

        points = {
            int(p.findtext("position")): float(p.findtext("price.amount"))
            for p in period.iter("Point")
        }
        # Curve type A03: a missing position repeats the previous price.
        last = None
        for pos in range(1, n_slots + 1):
            last = points.get(pos, last)
            if last is None:
                continue
            ts = period_start + timedelta(minutes=step * (pos - 1))
            if ts not in best or step < best[ts][0]:
                best[ts] = (step, last)

    if not best:
        raise ProviderError(f"ENTSO-E: {zone_code}: no data")
    index = pd.DatetimeIndex(list(best.keys())).tz_convert("UTC")
    return pd.Series([v for _, v in best.values()], index=index, name=zone_code).sort_index()
