"""Bidding-zone registry.

Each zone carries the identifiers every provider needs, so the rest of the app
only ever deals with our own zone code (``code``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    code: str  # our code
    name: str  # human readable label
    country: str  # ISO 3166-1 alpha-3, used for the map
    eic: str  # ENTSO-E EIC area code
    eu: bool = True  # False for non-EU zones coupled to the EU market
    bzn: str | None = None  # energy-charts.info code when it differs from ``code``

    @property
    def energy_charts_code(self) -> str:
        return self.bzn or self.code


ZONES: tuple[Zone, ...] = (
    Zone("AT", "Austria", "AUT", "10YAT-APG------L"),
    Zone("BE", "Belgium", "BEL", "10YBE----------2"),
    Zone("BG", "Bulgaria", "BGR", "10YCA-BULGARIA-R"),
    Zone("HR", "Croatia", "HRV", "10YHR-HEP------M"),
    Zone("CZ", "Czechia", "CZE", "10YCZ-CEPS-----N"),
    Zone("DK1", "Denmark West", "DNK", "10YDK-1--------W"),
    Zone("DK2", "Denmark East", "DNK", "10YDK-2--------M"),
    Zone("EE", "Estonia", "EST", "10Y1001A1001A39I"),
    Zone("FI", "Finland", "FIN", "10YFI-1--------U"),
    Zone("FR", "France", "FRA", "10YFR-RTE------C"),
    Zone("DE-LU", "Germany / Luxembourg", "DEU", "10Y1001A1001A82H"),
    Zone("GR", "Greece", "GRC", "10YGR-HTSO-----Y"),
    Zone("HU", "Hungary", "HUN", "10YHU-MAVIR----U"),
    Zone("IE", "Ireland (SEM)", "IRL", "10Y1001A1001A59C", bzn="IE(SEM)"),
    Zone("IT-North", "Italy North", "ITA", "10Y1001A1001A73I"),
    Zone("IT-Centre-North", "Italy Centre-North", "ITA", "10Y1001A1001A70O"),
    Zone("IT-Centre-South", "Italy Centre-South", "ITA", "10Y1001A1001A71M"),
    Zone("IT-South", "Italy South", "ITA", "10Y1001A1001A788"),
    Zone("IT-Calabria", "Italy Calabria", "ITA", "10Y1001C--00096J"),
    Zone("IT-Sicily", "Italy Sicily", "ITA", "10Y1001A1001A75E"),
    Zone("IT-Sardinia", "Italy Sardinia", "ITA", "10Y1001A1001A74G"),
    Zone("LV", "Latvia", "LVA", "10YLV-1001A00074"),
    Zone("LT", "Lithuania", "LTU", "10YLT-1001A0008Q"),
    Zone("NL", "Netherlands", "NLD", "10YNL----------L"),
    Zone("PL", "Poland", "POL", "10YPL-AREA-----S"),
    Zone("PT", "Portugal", "PRT", "10YPT-REN------W"),
    Zone("RO", "Romania", "ROU", "10YRO-TEL------P"),
    Zone("SK", "Slovakia", "SVK", "10YSK-SEPS-----K"),
    Zone("SI", "Slovenia", "SVN", "10YSI-ELES-----O"),
    Zone("ES", "Spain", "ESP", "10YES-REE------0"),
    Zone("SE1", "Sweden SE1 (Luleå)", "SWE", "10Y1001A1001A44P"),
    Zone("SE2", "Sweden SE2 (Sundsvall)", "SWE", "10Y1001A1001A45N"),
    Zone("SE3", "Sweden SE3 (Stockholm)", "SWE", "10Y1001A1001A46L"),
    Zone("SE4", "Sweden SE4 (Malmö)", "SWE", "10Y1001A1001A47J"),
    # Coupled non-EU zones, hidden unless the user opts in.
    Zone("NO1", "Norway NO1 (Oslo)", "NOR", "10YNO-1--------2", eu=False),
    Zone("NO2", "Norway NO2 (Kristiansand)", "NOR", "10YNO-2--------T", eu=False),
    Zone("NO3", "Norway NO3 (Trondheim)", "NOR", "10YNO-3--------J", eu=False),
    Zone("NO4", "Norway NO4 (Tromsø)", "NOR", "10YNO-4--------9", eu=False),
    Zone("NO5", "Norway NO5 (Bergen)", "NOR", "10Y1001A1001A48H", eu=False),
    Zone("CH", "Switzerland", "CHE", "10YCH-SWISSGRIDZ", eu=False),
)

BY_CODE: dict[str, Zone] = {z.code: z for z in ZONES}


def zones(include_non_eu: bool = False) -> list[Zone]:
    return [z for z in ZONES if z.eu or include_non_eu]
