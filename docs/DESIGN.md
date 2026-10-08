# Design

## Users and questions

| User | Question the app answers first |
|---|---|
| Energy-curious consumer on a dynamic tariff | What does power cost right now, and when is it cheapest tomorrow? |
| Analyst / trader | How do zones compare right now, what is the spread, and what is the curve for today and tomorrow? |
| Journalist / researcher | Where in Europe is power cheapest or most expensive, and can I download the data? |

## Layout

```
┌ Sidebar ─────────────┐ ┌ Main ─────────────────────────────────────────────────────┐
│ Time zone            │ │ ⚡ EU electricity prices                                   │
│ Include NO & CH      │ │ Current interval · zone count · fetched at                │
│ Zones to compare (≤8)│ │ [Average] [Cheapest · zone] [Most expensive · zone] [Spread]│
│ Hourly averages      │ │ Tabs: Map | Ranking | Today & tomorrow | Data             │
│ Refresh now          │ │                                                           │
│ Source + units note  │ │                                                           │
└──────────────────────┘ └───────────────────────────────────────────────────────────┘
```

### Views

1. **KPI row** – four headline numbers for the current interval. Names of the
   cheapest and most expensive zones sit in the label, so nothing relies on colour.
2. **Map** – choropleth of Europe, one-hue sequential blue scale (light = cheap,
   dark = expensive). Countries with several zones (DK, IT, SE, NO) show the mean,
   with the zone list in the tooltip.
3. **Ranking** – horizontal bar chart of every zone, sorted, with value labels and a
   dotted average line. The most precise "who is cheapest now" view.
4. **Today & tomorrow** – step line chart (prices are constant within an interval)
   for up to 8 chosen zones, with a dotted "now" marker, unified hover, and a
   table of min / average / max per day. Tomorrow appears after ~13:00 CET; a note
   says so before then.
5. **Data** – table of current prices with source per zone, CSV download of all
   intervals, and a list of zones that could not be loaded.

## Visual rules

- **Units:** EUR/MWh everywhere (market convention), with a sidebar note that
  1 EUR/MWh = 0.1 c/kWh before taxes and grid fees.
- **Colour:** fixed 8-hue categorical order for zones (blue, orange, aqua, yellow,
  magenta, green, violet, red), validated for colour-vision deficiency on adjacent
  pairs; colour follows the zone's position in the pick list, never its price rank.
  Light and dark variants are chosen from the active Streamlit theme.
  Primary accent blue `#2a78d6`.
- **Marks:** 2 px lines, rounded bar ends, recessive grid, legend under the chart.
- **Time:** all charts in the selected time zone; market day boundaries follow Brussels.
- **Negative prices** are shown as-is (they happen on sunny/windy days); axes are not clipped at zero.

## States

| State | Behaviour |
|---|---|
| Loading | Spinner "Fetching day-ahead prices…" |
| Some zones fail | Page renders; Data tab lists unavailable zones with the reason |
| All zones fail | Error banner with "Refresh now" hint and an expandable error list |
| No zones picked | Info message in the Today & tomorrow tab |
| Tomorrow not yet published | Caption explaining publication time |

## Accessibility

- Every chart has a table equivalent (Ranking ↔ Data tab, time series ↔ daily stats table, CSV).
- Identity is never colour-only: legend plus zone codes on axes and labels.
- Works in Streamlit light and dark themes and on narrow screens (columns stack).
