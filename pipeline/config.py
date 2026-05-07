"""Project-wide constants, file paths, schema, and methodology assumptions.

Single source of truth — never hardcode magic numbers in business logic.
Tracks methodology §4, §5, §6 verbatim. Update here, propagate downstream.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final





PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
RAW_DIR: Final[Path] = DATA_DIR / "raw"
PROCESSED_DIR: Final[Path] = DATA_DIR / "processed"
OUTPUTS_DIR: Final[Path] = DATA_DIR / "outputs"

REPORT_DIR: Final[Path] = PROJECT_ROOT / "report"
FIGURES_DIR: Final[Path] = REPORT_DIR / "figures"
TABLES_DIR: Final[Path] = REPORT_DIR / "tables"

DASHBOARD_PUBLIC_DATA_DIR: Final[Path] = PROJECT_ROOT / "dashboard" / "public" / "data"

RAW_RPW_PATH: Final[Path] = RAW_DIR / "rpw_latest.xlsx"
RAW_BRM_PATH: Final[Path] = RAW_DIR / "bilateral_remittances_2021.json"
PROCESSED_RPW_PATH: Final[Path] = PROCESSED_DIR / "rpw_clean.parquet"
PROCESSED_BRM_PATH: Final[Path] = PROCESSED_DIR / "bilateral_remittances.parquet"





RPW_DATA_SHEET_MODERN: Final[str] = "Dataset (from Q2 2016)"
RPW_DATA_SHEET_LEGACY: Final[str] = "Dataset (up to Q1 2016)"

CORRIDORS_JSON: Final[Path] = OUTPUTS_DIR / "corridors.json"
OPERATOR_REGRESSION_JSON: Final[Path] = OUTPUTS_DIR / "operator_regression.json"
DIASPORA_BURDEN_JSON: Final[Path] = OUTPUTS_DIR / "diaspora_burden.json"
META_JSON: Final[Path] = OUTPUTS_DIR / "meta.json"

def ensure_dirs() -> None:
    """Create every directory the pipeline writes to."""
    for d in (RAW_DIR, PROCESSED_DIR, OUTPUTS_DIR, FIGURES_DIR, TABLES_DIR):
        d.mkdir(parents=True, exist_ok=True)










RPW_PRIMARY_URL: Final[str] = (
    "https://datacatalogfiles.worldbank.org/ddh-published/0037898/DR0095523/"
    "rpw_dataset_2011_2025_q1.xlsx"
)
RPW_FALLBACK_URL: Final[str] = (
    "https://remittanceprices.worldbank.org/sites/default/files/"
    "rpw_dataset_2011_2025_q1.xlsx"
)










BRM_API_URL: Final[str] = (
    "https://data360api.worldbank.org/data360/data?"
    "DATABASE_ID=WB_KNOMAD&INDICATOR=WB_KNOMAD_BRE"
)
BRM_LATEST_YEAR: Final[int] = 2021


RPW_CANDIDATE_SHEETS: Final[tuple[str, ...]] = (
    RPW_DATA_SHEET_MODERN,
    "Dataset",
    "RPW",
    "RPW_data",
    "Data",
    "data",
    "RemittancePrices",
    "Sheet1",
)









CANONICAL_COLUMNS: Final[tuple[str, ...]] = (
    "period",
    "source_code",
    "source_name",
    "source_region",
    "source_income",
    "destination_code",
    "destination_name",
    "destination_region",
    "destination_income",
    "firm",
    "firm_type_raw",
    "firm_type",
    "payment_instrument",
    "access_point",
    "pickup_method",
    "transfer_speed_raw",
    "days_to_arrive",
    "send_amount_usd",
    "lcu_amount",
    "lcu_fee",
    "fx_margin_pct",
    "total_cost_pct",
    "fee_pct",
    "speed_penalty_pct",
    "tci_pct",
    "lcu_code",
    "applied_fx_rate",
    "interbank_fx_rate",
    "transparent",
    "date",
    "quarter",
    "year",
)






CANDIDATE_COLUMNS: Final[dict[str, tuple[str, ...]]] = {

    "period": ("period", "quarter", "yearquarter", "year_quarter", "time"),
    "source_code": ("source_code", "sourcecode", "sending_country_code", "iso_send"),
    "source_name": ("source_name", "sending_country", "country_send", "from"),
    "source_region": ("source_region", "sending_region"),
    "source_income": ("source_income", "sending_income"),
    "destination_code": (
        "destination_code",
        "destinationcode",
        "receiving_country_code",
        "iso_recv",
    ),
    "destination_name": ("destination_name", "receiving_country", "country_receive", "to"),
    "destination_region": ("destination_region", "receiving_region"),
    "destination_income": ("destination_income", "receiving_income"),
    "firm": ("firm", "rsp_name", "operator", "provider_name", "rsp"),
    "firm_type_raw": (
        "firm_type",
        "firm_type_actual",
        "rsp_type",
        "operator_type",
        "provider_type",
    ),

    "payment_instrument": ("payment_instrument", "payment instrument", "paymentinstrument"),
    "access_point": ("access_point", "access point", "accesspoint"),
    "pickup_method": (
        "pickup_method",
        "pickup method",
        "pickupmethod",
        "receiving_method",
        "disbursement_method",
        "delivery_method",
    ),
    "pickup_location": ("pickup_location", "pickup location", "pickuplocation"),
    "transfer_speed_raw": (
        "speed_actual",
        "speed actual",
        "speedactual",
        "transfer_speed",
        "transfer_speed_actual",
        "delivery_speed",
    ),

    "lcu_amount_cc1": ("cc1_lcu_amount", "cc1 lcu amount", "ccone_lcu_amount"),
    "denomination_cc1": ("cc1_denomination_amount", "cc1 denomination amount"),
    "lcu_code_cc1": ("cc1_lcu_code", "cc1 lcu code"),
    "lcu_fee_cc1": ("cc1_lcu_fee", "cc1 lcu fee"),
    "applied_fx_cc1": ("cc1_lcu_fx_rate", "cc1 lcu fx rate"),
    "fx_margin_cc1": ("cc1_fx_margin", "cc1 fx margin", "cc1_margin"),
    "total_cost_pct_cc1": (
        "cc1_total_cost_%",
        "cc1 total cost %",
        "cc1_total_cost_pct",
        "cc1_total_cost",
    ),

    "lcu_amount_cc2": ("cc2_lcu_amount", "cc2 lcu amount"),
    "denomination_cc2": ("cc2_denomination_amount", "cc2 denomination amount"),
    "lcu_code_cc2": ("cc2_lcu_code", "cc2 lcu code"),
    "lcu_fee_cc2": ("cc2_lcu_fee", "cc2 lcu fee"),
    "applied_fx_cc2": ("cc2_lcu_fx_rate", "cc2 lcu fx rate"),
    "fx_margin_cc2": ("cc2_fx_margin", "cc2 fx margin", "cc2_margin"),
    "total_cost_pct_cc2": (
        "cc2_total_cost_%",
        "cc2 total cost %",
        "cc2_total_cost_pct",
        "cc2_total_cost",
    ),

    "interbank_fx_rate": (
        "inter_lcu_bank_fx",
        "inter lcu bank fx",
        "interbank_fx",
        "interbank_rate",
    ),
    "transparent": ("transparent",),
    "date": ("date",),
}






HEADLINE_SEND_AMOUNT_USD: Final[float] = 200.0
SECONDARY_SEND_AMOUNT_USD: Final[float] = 500.0



SEND_AMOUNT_TOLERANCE_PCT: Final[float] = 0.10









TCI_KAPPA_PCT_PER_DAY: Final[float] = 0.10




SPEED_TO_DAYS: Final[dict[str, float]] = {

    "lessthanonehour": 0.0,
    "lessthananhour": 0.0,
    "lessthan1hour": 0.0,
    "withinonehour": 0.0,
    "within1hour": 0.0,
    "withinanhour": 0.0,
    "instant": 0.0,
    "realtime": 0.0,
    "sameday": 0.0,
    "samedayhours": 0.0,

    "nextday": 1.0,
    "nextbusinessday": 1.0,
    "1businessday": 1.0,
    "1day": 1.0,
    "oneday": 1.0,

    "twodays": 2.0,
    "2days": 2.0,
    "2businessdays": 2.0,
    "13days": 2.0,
    "1to3days": 2.0,
    "onethreedays": 2.0,

    "threedays": 3.0,
    "3days": 3.0,
    "3businessdays": 3.0,

    "35days": 4.0,
    "3to5days": 4.0,
    "threetofivedays": 4.0,
    "3to5businessdays": 4.0,
    "fourdays": 4.0,
    "4days": 4.0,

    "fivedays": 5.0,
    "5days": 5.0,

    "morethan5days": 6.0,
    "morethanfivedays": 6.0,
    "over5days": 6.0,
    "6daysormore": 6.0,
    "sixdaysormore": 6.0,
    "morethan6days": 6.0,
    "6plusdays": 6.0,
}

def normalise_speed(value: str | None) -> str:
    """Lowercased, alnum-only key used to look up SPEED_TO_DAYS."""
    if value is None:
        return ""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())







STABLECOIN_GAS_USD: Final[float] = 0.50


ONRAMP_DEFAULT_PCT: Final[float] = 1.5
ONRAMP_DEVELOPED_PCT: Final[float] = 1.0
ONRAMP_LOW_BANKED_PCT: Final[float] = 2.5


OFFRAMP_DEFAULT_PCT: Final[float] = 2.5
OFFRAMP_TOP_P2P_PCT: Final[float] = 1.0
OFFRAMP_THIN_LIQUIDITY_PCT: Final[float] = 4.0


FX_SPREAD_DEEP_PCT: Final[float] = 0.5
FX_SPREAD_DEFAULT_PCT: Final[float] = 1.5


DEVELOPED_SENDERS_ISO3: Final[frozenset[str]] = frozenset(
    {
        "USA",
        "GBR",
        "DEU",
        "FRA",
        "ITA",
        "ESP",
        "NLD",
        "BEL",
        "AUT",
        "PRT",
        "IRL",
        "FIN",
        "SWE",
        "DNK",
        "NOR",
        "POL",
        "CZE",
        "GRC",
        "LUX",
        "CHE",
        "CAN",
        "AUS",
        "NZL",
        "JPN",
        "KOR",
        "SGP",
        "HKG",
        "ISL",
        "MLT",
        "CYP",
        "EST",
        "LVA",
        "LTU",
        "SVK",
        "SVN",
        "HRV",
        "HUN",
        "BGR",
        "ROU",
    }
)

LOW_BANKED_SENDERS_ISO3: Final[frozenset[str]] = frozenset(
    {"RUS", "ZAF", "SAU", "KWT", "QAT", "OMN", "BHR", "ARE"}
)

TOP_P2P_RECEIVERS_ISO3: Final[frozenset[str]] = frozenset({"NGA", "PHL", "IND", "MEX"})



THIN_LIQUIDITY_RECEIVERS_ISO3: Final[frozenset[str]] = frozenset(
    {"CUB", "MMR", "AFG", "PRK", "SDN", "SYR", "YEM", "ZWE", "VEN", "ETH"}
)



DEEP_STABLECOIN_RECEIVERS_ISO3: Final[frozenset[str]] = frozenset(
    {"NGA", "PHL", "IND", "MEX", "BRA", "ARG", "TUR", "VNM", "IDN", "KEN", "GHA", "COL"}
)

def onramp_pct_for(iso3: str) -> float:
    """On-ramp cost for a sending country (methodology §5.2)."""
    iso3 = (iso3 or "").upper()
    if iso3 in DEVELOPED_SENDERS_ISO3:
        return ONRAMP_DEVELOPED_PCT
    if iso3 in LOW_BANKED_SENDERS_ISO3:
        return ONRAMP_LOW_BANKED_PCT
    return ONRAMP_DEFAULT_PCT

def offramp_pct_for(iso3: str) -> float:
    """Off-ramp cost for a receiving country (methodology §5.2)."""
    iso3 = (iso3 or "").upper()
    if iso3 in TOP_P2P_RECEIVERS_ISO3:
        return OFFRAMP_TOP_P2P_PCT
    if iso3 in THIN_LIQUIDITY_RECEIVERS_ISO3:
        return OFFRAMP_THIN_LIQUIDITY_PCT
    return OFFRAMP_DEFAULT_PCT

def fx_spread_pct_for(iso3: str) -> float:
    """Local FX spread between stablecoin and local currency (methodology §5.2)."""
    iso3 = (iso3 or "").upper()
    if iso3 in DEEP_STABLECOIN_RECEIVERS_ISO3:
        return FX_SPREAD_DEEP_PCT
    return FX_SPREAD_DEFAULT_PCT







FIRM_TYPE_CANONICAL: Final[tuple[str, ...]] = (
    "MTO",
    "Bank",
    "MobileMoney",
    "PostOffice",
    "Fintech",
    "Other",
)




FIRM_TYPE_ALIASES: Final[dict[str, str]] = {

    "mto": "MTO",
    "moneytransferoperator": "MTO",
    "moneytransferoperatorpostoffice": "MTO",
    "moneytransferoperatorbuildingsociety": "MTO",
    "remittancecompany": "MTO",

    "bank": "Bank",
    "bankpostoffice": "Bank",
    "bankmoneytransferoperator": "Bank",
    "commercialbank": "Bank",
    "savingsbank": "Bank",
    "creditunion": "Bank",

    "mobilemoney": "MobileMoney",
    "mobileoperator": "MobileMoney",
    "mno": "MobileMoney",

    "postoffice": "PostOffice",
    "postal": "PostOffice",

    "fintech": "Fintech",
    "nonbankfi": "Fintech",
    "nonbankfinancialinstitution": "Fintech",
    "digital": "Fintech",
    "digitalonly": "Fintech",
    "online": "Fintech",
    "neobank": "Fintech",

    "other": "Other",
    "na": "Other",
    "": "Other",
}

def normalise_firm_type(value: str | None) -> str:
    """Lowercased, alnum-only key used to look up FIRM_TYPE_ALIASES."""
    if value is None:
        return ""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())

REGRESSION_REFERENCE_FIRM_TYPE: Final[str] = "MTO"










REGION_BACKFILL: Final[dict[str, str]] = {

    "USA": "Northern America",
    "CAN": "Northern America",

    "DEU": "Western Europe",
    "FRA": "Western Europe",
    "NLD": "Western Europe",
    "BEL": "Western Europe",
    "AUT": "Western Europe",
    "LUX": "Western Europe",
    "CHE": "Western Europe",

    "GBR": "Northern Europe",
    "IRL": "Northern Europe",
    "SWE": "Northern Europe",
    "DNK": "Northern Europe",
    "FIN": "Northern Europe",
    "NOR": "Northern Europe",
    "ISL": "Northern Europe",
    "EST": "Northern Europe",
    "LVA": "Northern Europe",
    "LTU": "Northern Europe",

    "ITA": "Southern Europe",
    "ESP": "Southern Europe",
    "PRT": "Southern Europe",
    "GRC": "Southern Europe",
    "MLT": "Southern Europe",
    "CYP": "Southern Europe",
    "HRV": "Southern Europe",
    "SVN": "Southern Europe",

    "POL": "Eastern Europe",
    "CZE": "Eastern Europe",
    "SVK": "Eastern Europe",
    "HUN": "Eastern Europe",
    "BGR": "Eastern Europe",
    "ROU": "Eastern Europe",

    "AUS": "Oceania",
    "NZL": "Oceania",

    "JPN": "Eastern Asia",
    "KOR": "Eastern Asia",
    "HKG": "Eastern Asia",

    "SGP": "South-Eastern Asia",

    "ARE": "Western Asia",
    "SAU": "Western Asia",
    "KWT": "Western Asia",
    "QAT": "Western Asia",
    "OMN": "Western Asia",
    "BHR": "Western Asia",
    "ISR": "Western Asia",
}







COLOR_BG: Final[str] = "#0A0A0A"
COLOR_SURFACE: Final[str] = "#111111"
COLOR_BORDER: Final[str] = "#1F1F1F"
COLOR_TEXT: Final[str] = "#F5F5F4"
COLOR_TEXT_MUTED: Final[str] = "#A8A29E"
COLOR_ACCENT_POSITIVE: Final[str] = "#D97706"
COLOR_ACCENT_NEGATIVE: Final[str] = "#B91C1C"
