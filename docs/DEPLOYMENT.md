# Deployment

## Streamlit Community Cloud (free, recommended for the MVP)

1. Sign in at <https://share.streamlit.io> with the GitHub account that owns this repo.
2. **Create app → Deploy a public app from GitHub**.
3. Repository `wolfmanex/eu-electricity-prices`, branch `main`, main file `streamlit_app.py`.
4. *Advanced settings*: Python 3.12. Optionally paste the secret below.
5. Deploy. The app gets a `*.streamlit.app` URL; every push to `main` redeploys.

Private repos work too: Community Cloud asks for access to private repositories the first time.

## ENTSO-E token (optional, makes ENTSO-E the primary source)

1. Register at <https://transparency.entsoe.eu> (top right, *Register*).
2. Email **transparency@entsoe.eu** with subject "Restful API access" and your account email.
3. When granted, generate a token under *My Account Settings → Web API Security Token*.
4. Add it to the app's secrets (Community Cloud: *App settings → Secrets*):

   ```toml
   ENTSOE_API_TOKEN = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
   ```

Without the token, the app uses energy-charts.info only.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
streamlit run streamlit_app.py          # live data
EU_PRICES_DEMO=1 streamlit run streamlit_app.py   # synthetic data, no network
pytest -q
```

## Other hosts

Any container host works: `pip install -r requirements.txt && streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`, with `ENTSOE_API_TOKEN` provided via `.streamlit/secrets.toml`.
