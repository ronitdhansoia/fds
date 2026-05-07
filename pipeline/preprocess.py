"""Clean and normalize the World Bank RPW xlsx into a canonical parquet.

Steps:
  1. Read the modern sheet (`Dataset (from Q2 2016)`) — schema sniff against
     CANDIDATE_COLUMNS in pipeline.config so renamed columns survive.
  2. Melt the per-amount columns (cc1 = USD 200, cc2 = USD 500) into long
     form: one row per (period, source, destination, firm, send_amount).
  3. Derive fee_pct = total_cost_pct - fx_margin_pct.
  4. Map RPW `speed actual` -> days_to_arrive, compute speed_penalty,
     and TCI per methodology §5.1.
  5. Normalize firm_type to the regression taxonomy.
  6. Drop rows missing any TCI input; write parquet + a summary print.

Run as a module:
    uv run python -m pipeline.preprocess
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import config

logger = logging.getLogger(__name__)





def _norm_header(value: object) -> str:
    """Normalise a header for fuzzy matching: lowercase, alnum only."""
    return "".join(ch for ch in str(value).lower() if ch.isalnum())

def resolve_columns(headers: list[str]) -> dict[str, str]:
    """Return {canonical_name: source_header} for the columns we found."""
    norm_to_actual = {_norm_header(h): h for h in headers}
    found: dict[str, str] = {}
    for canonical, aliases in config.CANDIDATE_COLUMNS.items():
        for alias in aliases:
            key = _norm_header(alias)
            if key in norm_to_actual:
                found[canonical] = norm_to_actual[key]
                break
    return found

REQUIRED_CANONICAL: tuple[str, ...] = (
    "period",
    "source_code",
    "destination_code",
    "firm",
    "firm_type_raw",
    "transfer_speed_raw",
    "fx_margin_cc1",
    "total_cost_pct_cc1",
    "denomination_cc1",
)





def read_rpw_workbook(path: Path) -> pd.DataFrame:
    """Read the modern RPW data sheet, falling back across candidate sheets."""
    xl = pd.ExcelFile(path, engine="openpyxl")
    logger.info("workbook sheets: %s", xl.sheet_names)
    target: str | None = None
    for candidate in config.RPW_CANDIDATE_SHEETS:
        if candidate in xl.sheet_names:
            target = candidate
            break
    if target is None:
        raise RuntimeError(
            f"no known data sheet found in {path}; saw {xl.sheet_names}. "
            "Add the new sheet name to RPW_CANDIDATE_SHEETS in pipeline/config.py."
        )
    logger.info("reading sheet %r (this is the slow step, ~30s for the full panel)", target)
    raw = pd.read_excel(xl, sheet_name=target, dtype=object)
    raw = raw.dropna(axis=1, how="all")
    raw = raw.dropna(axis=0, how="all")
    logger.info("raw frame: %d rows x %d cols", len(raw), raw.shape[1])
    return raw

def read_country_info(path: Path) -> pd.DataFrame:
    """RPW ships a Countries sheet with clean region/income — use it to fix
    the ".." sentinels that pollute source_region / destination_region in the
    main panel.
    """
    df = pd.read_excel(path, sheet_name="Countries", header=1, engine="openpyxl")
    df = df.rename(
        columns={
            "ISO 3166-1 alpha-3 country code": "code",
            "Country name": "name",
            "Region": "region",
            "Income Group": "income",
            "Lending category": "lending",
            "G8/G20": "g8g20",
        }
    )
    df = df[["code", "name", "region", "income"]].copy()
    df["code"] = df["code"].astype(str).str.upper().str.strip()
    for c in ("name", "region", "income"):
        df[c] = (
            df[c]
            .astype(str)
            .str.strip()
            .replace({"..": None, "": None, "nan": None, "None": None})
        )
    df = df[df["code"].str.len() == 3]
    logger.info("country info: %d rows", len(df))
    return df





_NUMERIC_NULLS = {"", "..", "...", "n/a", "na", "nan", "none", "-"}

def to_number(series: pd.Series) -> pd.Series:
    """Coerce a column to float, treating common RPW null sentinels as NaN."""
    s = series.astype(object)
    cleaned = s.where(
        ~s.astype(str).str.strip().str.lower().isin(_NUMERIC_NULLS),
        other=np.nan,
    )
    return pd.to_numeric(cleaned, errors="coerce")

def parse_period(period: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Parse RPW period strings like '2024_3Q' into (year, quarter, period_dt)."""
    s = period.astype(str).str.strip()
    parts = s.str.extract(r"(?P<year>\d{4})\D+(?P<q>\d)", expand=True)
    year = pd.to_numeric(parts["year"], errors="coerce").astype("Int64")
    quarter = pd.to_numeric(parts["q"], errors="coerce").astype("Int64")

    month = ((quarter - 1) * 3 + 1).astype("Int64")
    period_dt = pd.to_datetime(
        {
            "year": year.astype("float").fillna(1970),
            "month": month.astype("float").fillna(1),
            "day": 1,
        },
        errors="coerce",
    )
    period_dt = period_dt.where(year.notna() & quarter.notna())
    return year, quarter, period_dt

def normalise_firm_type_series(s: pd.Series) -> pd.Series:
    norm = s.astype(str).map(config.normalise_firm_type)
    mapped = norm.map(config.FIRM_TYPE_ALIASES)

    def _fallback(raw: str) -> str:
        if "moneytransferoperator" in raw:
            return "MTO"
        if "bank" in raw:
            return "Bank"
        if "mobile" in raw:
            return "MobileMoney"
        if "post" in raw:
            return "PostOffice"
        if "fintech" in raw or "digital" in raw or "online" in raw or "nonbank" in raw:
            return "Fintech"
        return "Other"

    fallback = norm.map(_fallback)
    return mapped.fillna(fallback)

def map_speed_to_days(s: pd.Series) -> pd.Series:
    keys = s.astype(str).map(config.normalise_speed)
    return keys.map(config.SPEED_TO_DAYS).astype("float64")






_PER_BUCKET_ROOTS: tuple[tuple[str, str], ...] = (
    ("lcu_amount", "lcu_amount"),
    ("lcu_code", "lcu_code"),
    ("lcu_fee", "lcu_fee"),
    ("applied_fx_rate", "applied_fx"),
    ("fx_margin_pct", "fx_margin"),
    ("total_cost_pct", "total_cost_pct"),
    ("denomination", "denomination"),
)

def melt_amount_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Stack the cc1 (USD 200) and cc2 (USD 500) columns into long form."""
    id_cols = [
        c
        for c in df.columns
        if not (c.endswith("_cc1") or c.endswith("_cc2"))
    ]
    frames: list[pd.DataFrame] = []
    for bucket in ("cc1", "cc2"):
        sub = df[id_cols].copy()
        for canonical, root in _PER_BUCKET_ROOTS:
            src_col = f"{root}_{bucket}"
            if src_col in df.columns:
                sub[canonical] = df[src_col]
        sub["amount_bucket"] = bucket
        frames.append(sub)
    out = pd.concat(frames, ignore_index=True)
    return out





def preprocess(raw_path: Path = config.RAW_RPW_PATH) -> pd.DataFrame:
    config.ensure_dirs()
    raw = read_rpw_workbook(raw_path)
    countries = read_country_info(raw_path)
    headers = list(raw.columns)
    resolved = resolve_columns(headers)
    logger.info("resolved %d/%d candidate columns", len(resolved), len(config.CANDIDATE_COLUMNS))

    missing = [c for c in REQUIRED_CANONICAL if c not in resolved]
    if missing:
        raise RuntimeError(
            f"required columns missing after schema sniff: {missing}. "
            "Add aliases to CANDIDATE_COLUMNS in pipeline/config.py."
        )


    df = raw[list(resolved.values())].copy()
    df.columns = list(resolved.keys())


    year, quarter, period_dt = parse_period(df["period"])
    df["year"] = year
    df["quarter"] = quarter
    df["period_dt"] = period_dt


    df["source_code"] = df["source_code"].astype(str).str.upper().str.strip()
    df["destination_code"] = df["destination_code"].astype(str).str.upper().str.strip()
    df["corridor_id"] = df["source_code"] + "-" + df["destination_code"]
    df["firm"] = df["firm"].astype(str).str.strip()
    df["firm_type"] = normalise_firm_type_series(df["firm_type_raw"])



    src_info = countries.rename(
        columns={"name": "source_name_clean", "region": "source_region_clean", "income": "source_income_clean"}
    )
    dst_info = countries.rename(
        columns={"name": "destination_name_clean", "region": "destination_region_clean", "income": "destination_income_clean"}
    )
    df = df.merge(src_info, left_on="source_code", right_on="code", how="left").drop(columns=["code"])
    df = df.merge(dst_info, left_on="destination_code", right_on="code", how="left").drop(columns=["code"])

    for stem in ("source", "destination"):
        for field in ("name", "region", "income"):
            raw_col, clean_col = f"{stem}_{field}", f"{stem}_{field}_clean"
            if raw_col in df.columns and clean_col in df.columns:


                fallback = df[raw_col].astype(str).str.strip().replace(
                    {"..": None, "": None, "nan": None, "None": None}
                )
                df[raw_col] = df[clean_col].fillna(fallback)
                df = df.drop(columns=[clean_col])


    code_col = {"source": "source_code", "destination": "destination_code"}
    for stem in ("source", "destination"):
        col = f"{stem}_region"
        if col in df.columns:
            backfill = df[code_col[stem]].map(config.REGION_BACKFILL)
            df[col] = df[col].fillna(backfill)


    df["days_to_arrive"] = map_speed_to_days(df["transfer_speed_raw"])
    df["speed_penalty_pct"] = config.TCI_KAPPA_PCT_PER_DAY * np.maximum(
        0.0, df["days_to_arrive"] - 1.0
    )


    for col in (
        "lcu_amount_cc1",
        "lcu_fee_cc1",
        "applied_fx_cc1",
        "fx_margin_cc1",
        "total_cost_pct_cc1",
        "denomination_cc1",
        "lcu_amount_cc2",
        "lcu_fee_cc2",
        "applied_fx_cc2",
        "fx_margin_cc2",
        "total_cost_pct_cc2",
        "denomination_cc2",
        "interbank_fx_rate",
    ):
        if col in df.columns:
            df[col] = to_number(df[col])


    long = melt_amount_buckets(df)


    long = long.rename(columns={"denomination": "send_amount_usd"})
    long["send_amount_usd"] = pd.to_numeric(long["send_amount_usd"], errors="coerce")


    pre_drop = len(long)
    long = long[
        long["fx_margin_pct"].notna()
        & long["total_cost_pct"].notna()
        & long["send_amount_usd"].notna()
        & long["speed_penalty_pct"].notna()
        & long["source_code"].str.len().eq(3)
        & long["destination_code"].str.len().eq(3)
    ].copy()
    logger.info("dropped %d rows missing required TCI inputs", pre_drop - len(long))


    long["fee_pct"] = (long["total_cost_pct"] - long["fx_margin_pct"]).clip(lower=0.0)


    long["tci_pct"] = long["fee_pct"] + long["fx_margin_pct"] + long["speed_penalty_pct"]


    head, sec = config.HEADLINE_SEND_AMOUNT_USD, config.SECONDARY_SEND_AMOUNT_USD
    bucket = pd.Series(np.nan, index=long.index, dtype="float64")
    bucket = bucket.mask(
        (long["send_amount_usd"] - head).abs() <= head * config.SEND_AMOUNT_TOLERANCE_PCT,
        head,
    )
    bucket = bucket.mask(
        (long["send_amount_usd"] - sec).abs() <= sec * config.SEND_AMOUNT_TOLERANCE_PCT,
        sec,
    )
    long["send_amount_bucket_usd"] = bucket
    keep = long["send_amount_bucket_usd"].notna()
    logger.info("dropped %d rows outside USD 200 / 500 buckets", int((~keep).sum()))
    long = long[keep].copy()
    long["send_amount_bucket_usd"] = long["send_amount_bucket_usd"].astype("int64")


    pre_clip = len(long)
    long = long[
        (long["fee_pct"].between(0, 100, inclusive="both"))
        & (long["fx_margin_pct"].between(-50, 100, inclusive="both"))
        & (long["total_cost_pct"].between(0, 100, inclusive="both"))
    ].copy()
    logger.info("clipped %d implausible-cost rows", pre_clip - len(long))


    drop_cols = [
        "firm_type_raw",
        "transfer_speed_raw",
        "amount_bucket",
        "lcu_amount",
        "lcu_fee",
        "applied_fx_rate",
    ]
    long = long.drop(columns=[c for c in drop_cols if c in long.columns])


    long["year"] = long["year"].astype("Int64")
    long["quarter"] = long["quarter"].astype("Int64")
    if "date" in long.columns:
        long["date"] = pd.to_datetime(long["date"], errors="coerce")


    for col in ("transparent", "lcu_code", "payment_instrument", "access_point",
                "pickup_method", "pickup_location", "source_region", "source_income",
                "destination_region", "destination_income", "source_name",
                "destination_name", "firm", "firm_type", "corridor_id", "period"):
        if col in long.columns:
            long[col] = long[col].astype(str).where(long[col].notna(), other=None)

    long = long.reset_index(drop=True)
    return long





def _format_money(x: float | int) -> str:
    return f"{x:>14,}"

def print_summary(df: pd.DataFrame) -> None:
    head = config.HEADLINE_SEND_AMOUNT_USD
    head_df = df[df["send_amount_bucket_usd"] == int(head)]

    print()
    print("=" * 78)
    print("PHASE 1 — RPW preprocessing summary")
    print("=" * 78)
    print(f"  Total rows ingested            : {len(df):>10,}")
    print(f"     of which USD {int(head)} bucket     : {len(head_df):>10,}")
    print(
        f"     of which USD {int(config.SECONDARY_SEND_AMOUNT_USD)} bucket     "
        f": {(df['send_amount_bucket_usd'] == int(config.SECONDARY_SEND_AMOUNT_USD)).sum():>10,}"
    )

    if df["period_dt"].notna().any():
        rows_first = df.loc[df["period_dt"].idxmin()]
        rows_last = df.loc[df["period_dt"].idxmax()]
        print(
            f"  Date range covered             : {int(rows_first['year'])} "
            f"Q{int(rows_first['quarter'])}  →  "
            f"{int(rows_last['year'])} Q{int(rows_last['quarter'])}"
        )
        print(f"  Unique quarters                : {df['period_dt'].nunique():>10,}")

    print(f"  Unique corridors               : {df['corridor_id'].nunique():>10,}")
    print(f"  Unique sending countries       : {df['source_code'].nunique():>10,}")
    print(f"  Unique receiving countries     : {df['destination_code'].nunique():>10,}")
    print(f"  Unique providers (firms)       : {df['firm'].nunique():>10,}")
    print()
    print("  Firm-type distribution (rows, USD 200 only):")
    counts = head_df["firm_type"].value_counts()
    for ft, cnt in counts.items():
        print(f"    {ft:<14s} {cnt:>10,}")
    print()



    if not head_df.empty:
        latest = head_df["period_dt"].max()
        recent = head_df[head_df["period_dt"] == latest]
        agg = (
            recent.groupby("corridor_id")
            .agg(
                source=("source_name", "first"),
                dest=("destination_name", "first"),
                providers=("firm", "nunique"),
                tci_mean=("tci_pct", "mean"),
                total_cost_mean=("total_cost_pct", "mean"),
                fee_mean=("fee_pct", "mean"),
                fx_mean=("fx_margin_pct", "mean"),
            )
            .sort_values("total_cost_mean", ascending=False)
            .head(10)
        )
        ts = pd.Timestamp(latest)
        print(
            f"  Top 10 most expensive corridors — USD 200, latest quarter "
            f"({ts.year} Q{((ts.month - 1) // 3) + 1}, mean across providers, raw total cost):"
        )
        print()
        print(
            f"  {'corridor':<11s} {'send → recv':<48s} "
            f"{'n':>3s} {'tot%':>7s} {'fee%':>6s} {'fx%':>6s} {'tci%':>6s}"
        )
        print(f"  {'-' * 11} {'-' * 48} {'-' * 3} {'-' * 7} {'-' * 6} {'-' * 6} {'-' * 6}")
        for cid, row in agg.iterrows():
            label = f"{row['source']} → {row['dest']}"
            label = (label[:46] + "…") if len(label) > 47 else label
            print(
                f"  {cid:<11s} {label:<48s} "
                f"{int(row['providers']):>3d} {row['total_cost_mean']:>7.2f} "
                f"{row['fee_mean']:>6.2f} {row['fx_mean']:>6.2f} {row['tci_mean']:>6.2f}"
            )
    print()
    print(f"  Wrote {config.PROCESSED_RPW_PATH}")
    print("=" * 78)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean and normalize the RPW xlsx.")
    parser.add_argument(
        "--raw",
        type=Path,
        default=config.RAW_RPW_PATH,
        help="Path to raw RPW xlsx",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=config.PROCESSED_RPW_PATH,
        help="Path to write the cleaned parquet",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    df = preprocess(raw_path=args.raw)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    logger.info("wrote %s (%.1f MB, %d rows)", args.out, args.out.stat().st_size / 1_048_576, len(df))
    print_summary(df)
    return 0

if __name__ == "__main__":
    sys.exit(main())
