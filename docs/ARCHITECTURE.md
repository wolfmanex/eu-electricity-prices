# Architecture

## Goal

Show current and next-day **day-ahead electricity prices** for every EU bidding
zone in one place, refreshed automatically, with no backend to operate.

"Live" here means the price of the delivery interval that is running right now.
EU wholesale prices are set once a day by the Single Day-Ahead Coupling (SDAC)
auction at 12:00 CET, published ~12:45–13:00 CET for the next day, in
15-minute intervals since 1 October 2025 (some zones still publish hourly).

## Overview

```
                ┌────────────────────────── Streamlit app (streamlit_app.py) ───────────────────────────┐
 Browser ◄────► │  UI: KPIs · Map · Ranking · Today & tomorrow · Data/CSV                                 │
                │        │                                                                                │
                │  st.cache_data (TTL 15 min, keyed by market day + zone set + source)                    │
                │        │                                                                                │
                │  eu_prices.service  ── fetch_prices() ── ThreadPool (8 workers, one task per zone)      │
                │        │                 current_prices() · to_hourly() · daily_stats()                 │
                │        ▼                                                                                │
                │  eu_prices.providers   (PriceProvider protocol, tried in order per zone)                │
                │    1. EntsoeProvider        ── only if ENTSOE_API_TOKEN secret is set                   │
                │    2. EnergyChartsProvider  ── always, no key                                           │
                │   (DemoProvider replaces both when EU_PRICES_DEMO=1, for offline dev)                   │
                └────────┬───────────────────────────────────────────┬────────────────────────────────────┘
                         ▼                                           ▼
          web-api.tp.entsoe.eu/api (XML, A44)          api.energy-charts.info/price (JSON)
```

## Components

| Module | Responsibility |
|---|---|
| `src/eu_prices/zones.py` | Registry of bidding zones: our code, display name, ISO-3 country (for the map), ENTSO-E EIC code, EU flag. Single source of truth for identifiers. |
| `src/eu_prices/providers/base.py` | `PriceProvider` protocol and `ProviderError`. Contract: return a `pd.Series` of EUR/MWh indexed by tz-aware UTC interval-start timestamps, clipped to `[start, end)`. |
| `src/eu_prices/providers/entsoe.py` | ENTSO-E Transparency Platform client and XML parser. Handles namespaces, `Acknowledgement` (no data / errors), curve type A03 (omitted positions repeat the previous price), and mixed resolutions (keeps the finest). |
| `src/eu_prices/providers/energy_charts.py` | energy-charts.info client (Fraunhofer ISE, CC BY 4.0). Drops null prices. |
| `src/eu_prices/service.py` | Provider chain + parallel fetch; returns a long DataFrame `timestamp, zone, price, source` and per-zone errors. Analytics helpers. No Streamlit imports. |
| `streamlit_app.py` | UI only: settings, caching, charts, tables, CSV export. |

## Data flow

1. On each page view the app computes today's market day in `Europe/Brussels`
   and asks for **yesterday 00:00 → day-after-tomorrow 00:00**, so today, the
   trailing 24 h and tomorrow (once published) are always in one dataset.
2. `st.cache_data` keeps that result for 15 minutes per (zone set, market day,
   source). All visitors share it, so upstream load is ~4 requests per zone per hour
   regardless of traffic.
3. For each zone the provider chain is tried in order; the first non-empty
   series wins and its name is recorded in `source`. A zone that fails every
   provider is listed in the Data tab instead of breaking the page.
4. `current_prices()` takes, per zone, the last interval that started at or
   before *now*, which works for 15- and 60-minute zones alike.

## Key decisions

| Decision | Why |
|---|---|
| Streamlit, single process, no database | Fastest route to a shareable MVP; free hosting on Streamlit Community Cloud. Day-ahead data is small (≈40 zones × 288 points). |
| Provider abstraction with fallback | ENTSO-E is the authoritative source but needs a token and has outages; energy-charts.info is keyless, so the app works on day one. |
| UTC internally, convert only for display | Avoids DST bugs; the user picks the display time zone. |
| Native resolution kept, hourly is a view | 15-minute MTU is the market reality; hourly averaging is opt-in for comparison. |
| Pure-Python service layer | Testable without Streamlit, reusable for a future API, alerting job or database loader. |

## Non-functional

- **Freshness:** ≤15 min staleness for "now"; tomorrow appears within 15 min of publication. "Refresh now" clears the cache.
- **Resilience:** per-zone isolation, 20 s HTTP timeout, fallback provider.
- **Secrets:** ENTSO-E token only via Streamlit secrets (`ENTSOE_API_TOKEN`), never committed (`.streamlit/secrets.toml` is git-ignored).
- **Licensing:** energy-charts.info data is CC BY 4.0; ENTSO-E data is free to reuse with attribution. Both are credited in the sidebar.

## Roadmap

1. Persist history (SQLite / DuckDB or Postgres) with a scheduled loader, enabling week/month/year views.
2. Price alerts (email / Telegram) for "cheapest hours tomorrow".
3. Retail price estimate per country (taxes, VAT, grid fees) in c/kWh.
4. Cross-border flows and generation mix from ENTSO-E.
5. Move to FastAPI + a JS front end if traffic or UX needs outgrow Streamlit.
