"""EU day-ahead electricity prices: Streamlit entry point."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from eu_prices.service import (  # noqa: E402
    build_providers,
    current_prices,
    daily_stats,
    fetch_prices,
    to_hourly,
)
from eu_prices.zones import BY_CODE, zones  # noqa: E402

CACHE_TTL = 15 * 60  # seconds; day-ahead prices change once a day, "now" moves every 15 min
DEFAULT_ZONES = ["DE-LU", "FR", "ES", "PL", "SE3"]
TIMEZONES = ["Europe/Brussels", "Europe/Tallinn", "Europe/Lisbon", "UTC"]

# Reference categorical palette (fixed order, validated for adjacent pairs) and a
# one-hue sequential ramp for magnitudes. Light / dark steps.
SERIES = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
}
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
MUTED = {"light": "#52514e", "dark": "#c3c2b7"}

st.set_page_config(page_title="EU Electricity Prices", page_icon="⚡", layout="wide")


# ---------------------------------------------------------------- data access
def entsoe_token() -> str | None:
    try:
        return st.secrets.get("ENTSOE_API_TOKEN") or None
    except Exception:  # no secrets file at all
        return None


@st.cache_data(ttl=CACHE_TTL, show_spinner="Fetching day-ahead prices…")
def load_prices(zone_codes: tuple[str, ...], day: str, use_entsoe: bool):
    """Yesterday 00:00 to the day after tomorrow 00:00 (Brussels), so today, tomorrow
    (once published, ~13:00 CET) and the trailing 24 h are always available."""
    market_tz = ZoneInfo("Europe/Brussels")
    d = datetime.fromisoformat(day).replace(tzinfo=market_tz)
    start, end = d - timedelta(days=1), d + timedelta(days=2)
    providers = build_providers(entsoe_token() if use_entsoe else None)
    result = fetch_prices(list(zone_codes), start, end, providers)
    return result.prices, result.errors, datetime.now(timezone.utc)


# ---------------------------------------------------------------- sidebar
mode = "dark" if getattr(st.context, "theme", None) and st.context.theme.type == "dark" else "light"
series_colors = SERIES[mode]

with st.sidebar:
    st.header("Settings")
    tz_name = st.selectbox("Time zone", TIMEZONES, help="Market days follow Brussels time (CET/CEST).")
    include_non_eu = st.toggle("Include Norway & Switzerland", value=False)
    available = zones(include_non_eu)
    picked = st.multiselect(
        "Zones to compare",
        options=[z.code for z in available],
        default=[c for c in DEFAULT_ZONES if c in BY_CODE],
        format_func=lambda c: f"{c} · {BY_CODE[c].name}",
        max_selections=len(series_colors),
    )
    hourly = st.toggle("Hourly averages", value=False, help="Average 15-minute intervals to hourly.")
    if st.button("Refresh now", use_container_width=True):
        load_prices.clear()

    has_token = bool(entsoe_token())
    st.divider()
    st.caption(
        "**Source:** "
        + ("ENTSO-E Transparency Platform, with energy-charts.info as fallback." if has_token
           else "energy-charts.info (Fraunhofer ISE). Add an ENTSO-E token to use ENTSO-E as the primary source.")
    )
    st.caption("Day-ahead (SDAC) prices in EUR/MWh. 1 EUR/MWh = 0.1 c/kWh, before taxes and grid fees.")

# ---------------------------------------------------------------- load
tz = ZoneInfo(tz_name)
now = datetime.now(timezone.utc)
market_day = now.astimezone(ZoneInfo("Europe/Brussels")).date().isoformat()
all_codes = tuple(z.code for z in available)
prices, errors, fetched_at = load_prices(all_codes, market_day, has_token)

st.title("⚡ EU electricity prices")

if prices.empty:
    st.error("No prices could be loaded right now. Try **Refresh now** in a minute.")
    with st.expander("Details"):
        st.json(errors)
    st.stop()

now_df = current_prices(prices, now)
now_df["name"] = now_df["zone"].map(lambda c: BY_CODE[c].name)
now_df["country"] = now_df["zone"].map(lambda c: BY_CODE[c].country)

interval_start = now_df["interval_start"].max().tz_convert(tz)
st.caption(
    f"Current delivery interval from {interval_start:%a %d %b, %H:%M} ({tz_name}) · "
    f"{len(now_df)} zones · data fetched {fetched_at.astimezone(tz):%H:%M}"
)

# ---------------------------------------------------------------- KPIs
cheap, dear = now_df.iloc[0], now_df.iloc[-1]
k1, k2, k3, k4 = st.columns(4)
k1.metric("Average across zones", f"{now_df['price'].mean():.1f} €/MWh")
k2.metric(f"Cheapest · {cheap['name']}", f"{cheap['price']:.1f} €/MWh")
k3.metric(f"Most expensive · {dear['name']}", f"{dear['price']:.1f} €/MWh")
k4.metric("Spread", f"{dear['price'] - cheap['price']:.1f} €/MWh")

tab_map, tab_rank, tab_series, tab_data = st.tabs(["Map", "Ranking", "Today & tomorrow", "Data"])

# ---------------------------------------------------------------- map
with tab_map:
    by_country = (
        now_df.groupby("country")
        .agg(price=("price", "mean"), zones=("zone", lambda s: ", ".join(s)), n=("zone", "size"))
        .reset_index()
    )
    by_country["label"] = by_country.apply(
        lambda r: f"{r['price']:.1f} €/MWh" + (f" (mean of {r['zones']})" if r["n"] > 1 else ""), axis=1
    )
    fig = px.choropleth(
        by_country,
        locations="country",
        color="price",
        custom_data=["label"],
        color_continuous_scale=SEQUENTIAL,
        scope="europe",
        labels={"price": "€/MWh"},
    )
    fig.update_traces(hovertemplate="%{location}: %{customdata[0]}<extra></extra>", marker_line_width=0.5)
    fig.update_geos(
        projection_type="mercator", lataxis_range=[34, 71], lonaxis_range=[-12, 35],
        showland=True, landcolor="rgba(128,128,128,0.15)", showcountries=True,
        countrycolor="rgba(128,128,128,0.5)", bgcolor="rgba(0,0,0,0)", showframe=False,
    )
    fig.update_layout(height=620, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Countries with several bidding zones (Denmark, Italy, Sweden, Norway) show the mean of their zones; see Ranking for each zone.")

# ---------------------------------------------------------------- ranking
with tab_rank:
    rank = now_df.sort_values("price", ascending=True)
    fig = go.Figure(
        go.Bar(
            x=rank["price"], y=rank["zone"], orientation="h",
            marker=dict(color=series_colors[0], cornerradius=4),
            customdata=rank[["name"]],
            hovertemplate="%{customdata[0]}: %{x:.1f} €/MWh<extra></extra>",
            text=rank["price"].map(lambda v: f"{v:.0f}"), textposition="outside", cliponaxis=False,
        )
    )
    mean = now_df["price"].mean()
    fig.add_vline(x=mean, line_dash="dot", line_color=MUTED[mode],
                  annotation_text=f"average {mean:.0f}", annotation_position="top")
    fig.update_layout(
        height=max(400, 22 * len(rank)), bargap=0.25, margin=dict(l=0, r=40, t=30, b=0),
        xaxis_title="€/MWh, current interval", yaxis_title=None,
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- time series
with tab_series:
    if not picked:
        st.info("Pick one or more zones in the sidebar to compare.")
    else:
        series = prices[prices["zone"].isin(picked)]
        if hourly:
            series = to_hourly(series)
        local_today = now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        window = series[series["timestamp"] >= local_today].copy()
        window["local_time"] = window["timestamp"].dt.tz_convert(tz)
        # Colour follows the zone's position in the user's pick list, not its price rank.
        color_map = {code: series_colors[i] for i, code in enumerate(picked)}
        fig = px.line(
            window, x="local_time", y="price", color="zone", line_shape="hv",
            color_discrete_map=color_map, category_orders={"zone": picked},
            labels={"local_time": "", "price": "€/MWh", "zone": "Zone"},
        )
        fig.update_traces(line_width=2, hovertemplate="%{y:.1f} €/MWh")
        fig.add_vline(x=now.astimezone(tz), line_dash="dot", line_color=MUTED[mode])
        fig.add_annotation(x=now.astimezone(tz), y=1, yref="paper", text="now", showarrow=False,
                           yanchor="bottom", font_color=MUTED[mode])
        fig.update_layout(height=480, hovermode="x unified", margin=dict(l=0, r=0, t=30, b=0),
                          legend=dict(orientation="h", y=-0.12, x=0, title_text=""))
        st.plotly_chart(fig, use_container_width=True)

        tomorrow = (local_today + timedelta(days=1)).date()
        have_tomorrow = (window["local_time"].dt.date == tomorrow).any()
        if not have_tomorrow:
            st.caption("Tomorrow's prices are published after the day-ahead auction, around 13:00 CET.")

        stats = daily_stats(series, tz_name)
        stats = stats[stats["day"] >= local_today.date()]
        st.dataframe(
            stats.rename(columns={"zone": "Zone", "day": "Day", "min": "Min", "mean": "Average", "max": "Max"}),
            hide_index=True, use_container_width=True,
            column_config={c: st.column_config.NumberColumn(format="%.1f €/MWh") for c in ["Min", "Average", "Max"]},
        )

# ---------------------------------------------------------------- data
with tab_data:
    table = now_df[["zone", "name", "price", "interval_start", "source"]].copy()
    table["interval_start"] = table["interval_start"].dt.tz_convert(tz)
    st.dataframe(
        table, hide_index=True, use_container_width=True,
        column_config={
            "zone": "Zone", "name": "Name", "source": "Source",
            "price": st.column_config.NumberColumn("Price now", format="%.2f €/MWh"),
            "interval_start": st.column_config.DatetimeColumn("Interval start", format="DD MMM HH:mm"),
        },
    )
    export = prices.assign(timestamp=prices["timestamp"].dt.tz_convert(tz))
    st.download_button(
        "Download all intervals (CSV)", export.to_csv(index=False).encode(),
        file_name=f"eu-day-ahead-{market_day}.csv", mime="text/csv",
    )
    if errors:
        with st.expander(f"{len(errors)} zone(s) unavailable"):
            for code, msg in errors.items():
                st.write(f"**{code}**: {msg}")
