"""Project-wide constants, file paths, schema, and methodology assumptions.

Single source of truth — never hardcode magic numbers in business logic.
Tracks methodology §4, §5, §6 verbatim. Update here, propagate downstream.
"""
from __future__ import annotations

from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------

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

# Sheet name as exposed by the 2026-04 RPW release. The workbook ships two
# data sheets — pre-Q2-2016 and Q2-2016-onward — with incompatible schemas.
# We use the modern sheet for the headline analysis. Pre-2016 quarters are
# documented but excluded; preprocess.py logs the decision.
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


# ---------------------------------------------------------------------------
# RPW source — World Bank Remittance Prices Worldwide
# ---------------------------------------------------------------------------
# Direct URLs verified 2026-04-30 against
# https://remittanceprices.worldbank.org/data-download. The dataset covers
# 2011 through Q1 2025 (47 MB xlsx, last modified 2026-04-20). Despite the
# filename, this is the most recent quarterly dump exposed by the data
# catalog at the time of retrieval. See pipeline/ingest.py for fetch logic.

RPW_PRIMARY_URL: Final[str] = (
    "https://datacatalogfiles.worldbank.org/ddh-published/0037898/DR0095523/"
    "rpw_dataset_2011_2025_q1.xlsx"
)
RPW_FALLBACK_URL: Final[str] = (
    "https://remittanceprices.worldbank.org/sites/default/files/"
    "rpw_dataset_2011_2025_q1.xlsx"
)

# ---------------------------------------------------------------------------
# Bilateral Remittance Matrix (KNOMAD / World Bank)
# ---------------------------------------------------------------------------
# Source: Data360 API exposing the WB_KNOMAD_BRE indicator. The legacy
# direct-download xlsx (knomad.org/sites/default/files/2022-12/...)  was
# retired in early 2025 and now redirects to a landing page; the API is
# the canonical replacement. Latest year available: 2021 (verified
# 2026-04-30). Schema: REF_AREA = source ISO3, COMP_BREAKDOWN_1 =
# WB_KNOMAD_<dest_iso3>, OBS_VALUE in USD millions.
BRM_API_URL: Final[str] = (
    "https://data360api.worldbank.org/data360/data?"
    "DATABASE_ID=WB_KNOMAD&INDICATOR=WB_KNOMAD_BRE"
)
BRM_LATEST_YEAR: Final[int] = 2021

# Sheet-name fallbacks across releases — preprocess.py picks the first that exists.
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

# ---------------------------------------------------------------------------
# Canonical column schema
# ---------------------------------------------------------------------------
# RPW column names drift across quarterly releases. preprocess.py walks
# CANDIDATE_COLUMNS, picks the first match (case-insensitive, ignoring
# spaces/underscores/dots), and renames to the canonical name. Add aliases
# here when a new release breaks the schema sniff. Do not patch downstream.

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

# Maps the columns that exist as-is in the source workbook. Cross-release
# aliases live in CANDIDATE_COLUMNS below — preprocess.py picks the first
# header that matches (case-insensitive, ignoring spaces/underscores/dots).
# Values whose normalized form ends in "_cc1" / "_cc2" indicate per-amount
# fields that get melted in preprocess.py.
CANDIDATE_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    # Identity
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
    # Service / channel
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
    # Per-amount metrics — first send bucket (cc1, typ. USD 200)
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
    # Per-amount metrics — second send bucket (cc2, typ. USD 500)
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
    # Cross-bucket
    "interbank_fx_rate": (
        "inter_lcu_bank_fx",
        "inter lcu bank fx",
        "interbank_fx",
        "interbank_rate",
    ),
    "transparent": ("transparent",),
    "date": ("date",),
}

# ---------------------------------------------------------------------------
# Send-amount buckets
# ---------------------------------------------------------------------------
# RPW reports prices at fixed send amounts. SDG 10.c benchmark is USD 200.

HEADLINE_SEND_AMOUNT_USD: Final[float] = 200.0
SECONDARY_SEND_AMOUNT_USD: Final[float] = 500.0

# Tolerance for matching RPW sending amounts to the headline buckets when the
# source amount is stored in local currency (matched after USD normalization).
SEND_AMOUNT_TOLERANCE_PCT: Final[float] = 0.10

# ---------------------------------------------------------------------------
# 5.1 True Cost Index — speed penalty mapping
# ---------------------------------------------------------------------------
# κ * max(0, days_to_arrive - 1). κ is the daily cost-of-capital proxy for
# the receiving household — calibrated to ~0.10% per day, matching the
# upper end of informal short-term lending rates documented in remittance
# corridors with high-speed alternatives. Document on /methodology.

TCI_KAPPA_PCT_PER_DAY: Final[float] = 0.10

# Map RPW `speed actual` buckets -> days. Lookup keys are the source string
# normalised by `normalise_speed()` (lowercased, all non-alnum stripped).
# Anything outside this map -> NaN -> excluded from TCI for that row.
SPEED_TO_DAYS: Final[dict[str, float]] = {
    # 0 days
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
    # 1 day
    "nextday": 1.0,
    "nextbusinessday": 1.0,
    "1businessday": 1.0,
    "1day": 1.0,
    "oneday": 1.0,
    # 2 days
    "twodays": 2.0,
    "2days": 2.0,
    "2businessdays": 2.0,
    "13days": 2.0,  # "1-3 days" -> midpoint 2
    "1to3days": 2.0,
    "onethreedays": 2.0,
    # 3 days
    "threedays": 3.0,
    "3days": 3.0,
    "3businessdays": 3.0,
    # 4 days (3-5 day bucket)
    "35days": 4.0,
    "3to5days": 4.0,
    "threetofivedays": 4.0,
    "3to5businessdays": 4.0,
    "fourdays": 4.0,
    "4days": 4.0,
    # 5 days
    "fivedays": 5.0,
    "5days": 5.0,
    # 6+ days
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

# ---------------------------------------------------------------------------
# 5.2 Stablecoin counterfactual cost model
# ---------------------------------------------------------------------------
# All values in percent of send amount unless suffixed _USD.
# Sources / justification surfaced verbatim on /methodology.

STABLECOIN_GAS_USD: Final[float] = 0.50  # L2 / Solana / Tron USDT default

# On-ramp tiers — sending side
ONRAMP_DEFAULT_PCT: Final[float] = 1.5
ONRAMP_DEVELOPED_PCT: Final[float] = 1.0  # US, EU members, UK
ONRAMP_LOW_BANKED_PCT: Final[float] = 2.5

# Off-ramp tiers — receiving side
OFFRAMP_DEFAULT_PCT: Final[float] = 2.5
OFFRAMP_TOP_P2P_PCT: Final[float] = 1.0  # NG, PH, IN, MX
OFFRAMP_THIN_LIQUIDITY_PCT: Final[float] = 4.0

# Local FX spread — receiving side
FX_SPREAD_DEEP_PCT: Final[float] = 0.5
FX_SPREAD_DEFAULT_PCT: Final[float] = 1.5

# ISO-3 country sets driving the tier lookups.
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
    {"RUS", "ZAF", "SAU", "KWT", "QAT", "OMN", "BHR", "ARE"}  # GCC + others where on-ramps thin
)

TOP_P2P_RECEIVERS_ISO3: Final[frozenset[str]] = frozenset({"NGA", "PHL", "IND", "MEX"})

# Receiving markets where stablecoin off-ramps are illiquid / heavily restricted.
# Conservative shortlist; expand after sensitivity analysis.
THIN_LIQUIDITY_RECEIVERS_ISO3: Final[frozenset[str]] = frozenset(
    {"CUB", "MMR", "AFG", "PRK", "SDN", "SYR", "YEM", "ZWE", "VEN", "ETH"}
)

# Receiving markets with a deep local stablecoin (USDT/USDC) market — both
# crypto-on-ramp and stablecoin-to-cash routes are routinely available.
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


# ---------------------------------------------------------------------------
# Firm-type taxonomy
# ---------------------------------------------------------------------------
# RPW ships heterogeneous firm_type values across releases. Normalise to a
# small fixed taxonomy so the regression has a clean reference category.

FIRM_TYPE_CANONICAL: Final[tuple[str, ...]] = (
    "MTO",
    "Bank",
    "MobileMoney",
    "PostOffice",
    "Fintech",
    "Other",
)

# Firm-type lookup uses normalise_firm_type() — alnum-only lowercased key.
# Compound types observed in the wild (e.g. "Money Transfer Operator / Post
# Office") are mapped by their primary classification.
FIRM_TYPE_ALIASES: Final[dict[str, str]] = {
    # MTO and MTO hybrids
    "mto": "MTO",
    "moneytransferoperator": "MTO",
    "moneytransferoperatorpostoffice": "MTO",
    "moneytransferoperatorbuildingsociety": "MTO",
    "remittancecompany": "MTO",
    # Bank and bank hybrids
    "bank": "Bank",
    "bankpostoffice": "Bank",
    "bankmoneytransferoperator": "Bank",
    "commercialbank": "Bank",
    "savingsbank": "Bank",
    "creditunion": "Bank",
    # Mobile money / MNO
    "mobilemoney": "MobileMoney",
    "mobileoperator": "MobileMoney",
    "mno": "MobileMoney",
    # Post office
    "postoffice": "PostOffice",
    "postal": "PostOffice",
    # Fintech / digital — Non-Bank FI maps here as the closest fit
    "fintech": "Fintech",
    "nonbankfi": "Fintech",
    "nonbankfinancialinstitution": "Fintech",
    "digital": "Fintech",
    "digitalonly": "Fintech",
    "online": "Fintech",
    "neobank": "Fintech",
    # Other / null
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

# ---------------------------------------------------------------------------
# High-income region backfill
# ---------------------------------------------------------------------------
# The RPW Countries sheet leaves "Region" blank for high-income countries
# (the World Bank reserves the field for developing-region classification).
# We backfill from the UN M49 macro-regions so the dashboard has a region
# label for every sender / receiver. Conservative scope: only countries the
# panel actually contains as senders or in the GCC.

REGION_BACKFILL: Final[dict[str, str]] = {
    # North America
    "USA": "Northern America",
    "CAN": "Northern America",
    # Western Europe
    "DEU": "Western Europe",
    "FRA": "Western Europe",
    "NLD": "Western Europe",
    "BEL": "Western Europe",
    "AUT": "Western Europe",
    "LUX": "Western Europe",
    "CHE": "Western Europe",
    # Northern Europe
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
    # Southern Europe
    "ITA": "Southern Europe",
    "ESP": "Southern Europe",
    "PRT": "Southern Europe",
    "GRC": "Southern Europe",
    "MLT": "Southern Europe",
    "CYP": "Southern Europe",
    "HRV": "Southern Europe",
    "SVN": "Southern Europe",
    # Eastern Europe (high income)
    "POL": "Eastern Europe",
    "CZE": "Eastern Europe",
    "SVK": "Eastern Europe",
    "HUN": "Eastern Europe",
    "BGR": "Eastern Europe",
    "ROU": "Eastern Europe",
    # Oceania
    "AUS": "Oceania",
    "NZL": "Oceania",
    # East Asia
    "JPN": "Eastern Asia",
    "KOR": "Eastern Asia",
    "HKG": "Eastern Asia",
    # Southeast Asia
    "SGP": "South-Eastern Asia",
    # Western Asia (GCC + neighbours)
    "ARE": "Western Asia",
    "SAU": "Western Asia",
    "KWT": "Western Asia",
    "QAT": "Western Asia",
    "OMN": "Western Asia",
    "BHR": "Western Asia",
    "ISR": "Western Asia",
}


# ---------------------------------------------------------------------------
# Aesthetic tokens (mirrored on the dashboard side)
# ---------------------------------------------------------------------------
# Dashboard reads from tailwind.config.ts; this block keeps Python-generated
# figures (Plotly) on-brand. Bloomberg-terminal-meets-editorial.

COLOR_BG: Final[str] = "#0A0A0A"
COLOR_SURFACE: Final[str] = "#111111"
COLOR_BORDER: Final[str] = "#1F1F1F"
COLOR_TEXT: Final[str] = "#F5F5F4"
COLOR_TEXT_MUTED: Final[str] = "#A8A29E"
COLOR_ACCENT_POSITIVE: Final[str] = "#D97706"  # deep amber — savings
COLOR_ACCENT_NEGATIVE: Final[str] = "#B91C1C"  # muted red — cost
