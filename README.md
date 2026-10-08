# ⚡ EU electricity prices

A Streamlit app showing **live day-ahead electricity prices** for every EU bidding
zone: current price per zone, a map of Europe, a ranking, today's and tomorrow's
curves, and CSV download.

Data: [ENTSO-E Transparency Platform](https://transparency.entsoe.eu) (when a token
is configured) with [energy-charts.info](https://energy-charts.info) (Fraunhofer ISE,
CC BY 4.0) as keyless fallback.

## Quick start

```bash
pip install -r requirements-dev.txt
streamlit run streamlit_app.py
```

Set `EU_PRICES_DEMO=1` to run with synthetic data and no network.

## Docs

- [Architecture](docs/ARCHITECTURE.md): components, data flow, decisions, roadmap
- [Design](docs/DESIGN.md): users, layout, views, visual rules, states
- [Deployment](docs/DEPLOYMENT.md): Streamlit Community Cloud, ENTSO-E token, local run

## Layout

```
streamlit_app.py            UI
src/eu_prices/zones.py      bidding-zone registry (codes, EIC, countries)
src/eu_prices/providers/    ENTSO-E, energy-charts.info, demo
src/eu_prices/service.py    fetching with fallback + analytics
tests/                      parser and service tests (pytest)
```
