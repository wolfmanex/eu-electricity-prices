import json
from pathlib import Path

import pandas as pd
import pytest

from eu_prices.providers import ProviderError
from eu_prices.providers import energy_charts, entsoe

FIXTURES = Path(__file__).parent / "fixtures"


def test_energy_charts_parse_drops_nulls():
    s = energy_charts.parse(json.loads((FIXTURES / "energy_charts.json").read_text()), "DE-LU")
    assert list(s.values) == [209.71, 201.53, 189.04]
    assert str(s.index.tz) == "UTC"
    assert s.index[0] == pd.Timestamp(1791324000, unit="s", tz="UTC")


def test_energy_charts_rejects_empty_payload():
    with pytest.raises(ProviderError):
        energy_charts.parse({"unix_seconds": [], "price": []}, "XX")


def test_entsoe_parse_fills_a03_gaps_and_prefers_finest_resolution():
    s = entsoe.parse((FIXTURES / "entsoe_a44.xml").read_text(), "DE-LU")
    t0 = pd.Timestamp("2026-10-07T22:00Z")
    expected = {
        t0: 100.5,
        t0 + pd.Timedelta(minutes=15): 90.0,
        t0 + pd.Timedelta(minutes=30): 90.0,  # repeated (A03)
        t0 + pd.Timedelta(minutes=45): -5.25,
        t0 + pd.Timedelta(minutes=60): 70.0,  # only covered by the hourly series
    }
    assert s.to_dict() == expected


def test_entsoe_acknowledgement_raises_with_reason():
    with pytest.raises(ProviderError, match="No matching data"):
        entsoe.parse((FIXTURES / "entsoe_ack.xml").read_text(), "DE-LU")
