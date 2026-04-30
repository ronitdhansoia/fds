"""Stablecoin counterfactual cost model + savings computation.

CLAUDE.md §5.2:
    SC_cost_pct = on_ramp(s) + off_ramp(d) + (gas_usd / A * 100)
                  + local_fx_spread(d)
    savings_pct = max(0, TCI_corridor - SC_cost_pct)
    savings_usd_annual = savings_pct/100 * annual_corridor_volume_usd

Annual corridor volumes come from the World Bank / KNOMAD bilateral
remittance matrix (WB_KNOMAD_BRE), latest year 2021. We deliberately
keep per-component cost defaults conservative — every constant is
defined in pipeline.config and surfaced verbatim on /methodology.

Run as a module to print the global savings ballpark:
    uv run python -m pipeline.stablecoin
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from pipeline import config, tci

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bilateral Remittance Matrix loader
# ---------------------------------------------------------------------------

_DEST_PREFIX = "WB_KNOMAD_"


def load_brm(path: Path = config.RAW_BRM_PATH) -> pd.DataFrame:
    """Flatten the Data360 JSON into (source, dest, year, usd_millions) rows.

    Filters out any aggregate destination codes (the API uses
    `WB_KNOMAD_GRD` etc. as mostly real ISO3s — we keep only 3-char codes).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"missing {path} — run `uv run python -m pipeline.ingest --only brm` first."
        )
    with path.open() as fh:
        envelope = json.load(fh)
    records = envelope["records"]
    rows: list[tuple[str, str, int, float]] = []
    for rec in records:
        src = str(rec.get("REF_AREA") or "").upper().strip()
        dst_raw = str(rec.get("COMP_BREAKDOWN_1") or "")
        if not dst_raw.startswith(_DEST_PREFIX):
            continue
        dst = dst_raw[len(_DEST_PREFIX) :].upper().strip()
        if len(src) != 3 or len(dst) != 3:
            continue
        try:
            year = int(rec.get("TIME_PERIOD"))
            value = float(rec.get("OBS_VALUE"))
        except (TypeError, ValueError):
            continue
        rows.append((src, dst, year, value))

    df = pd.DataFrame(rows, columns=["source_code", "destination_code", "year", "usd_millions"])
    df["corridor_id"] = df["source_code"] + "-" + df["destination_code"]
    df["volume_usd_annual"] = df["usd_millions"] * 1_000_000.0
    logger.info(
        "BRM: %d (corridor, year) rows; latest year=%d; %d unique corridors",
        len(df),
        df["year"].max(),
        df["corridor_id"].nunique(),
    )
    return df


def latest_corridor_volumes(brm: pd.DataFrame) -> pd.DataFrame:
    """One row per corridor with the most recent volume estimate."""
    idx = brm.groupby("corridor_id")["year"].idxmax()
    return (
        brm.loc[idx, ["corridor_id", "source_code", "destination_code", "year", "volume_usd_annual"]]
        .reset_index(drop=True)
        .rename(columns={"year": "volume_year"})
    )


# ---------------------------------------------------------------------------
# Stablecoin cost model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StablecoinBreakdown:
    onramp_pct: float
    offramp_pct: float
    gas_pct: float
    fx_spread_pct: float
    total_pct: float


def stablecoin_cost(
    source_iso3: str, dest_iso3: str, send_amount_usd: float
) -> StablecoinBreakdown:
    """Apply §5.2 to a single corridor × send_amount."""
    onramp = config.onramp_pct_for(source_iso3)
    offramp = config.offramp_pct_for(dest_iso3)
    gas_pct = (config.STABLECOIN_GAS_USD / max(send_amount_usd, 1e-9)) * 100.0
    fx_spread = config.fx_spread_pct_for(dest_iso3)
    total = onramp + offramp + gas_pct + fx_spread
    return StablecoinBreakdown(
        onramp_pct=onramp,
        offramp_pct=offramp,
        gas_pct=gas_pct,
        fx_spread_pct=fx_spread,
        total_pct=total,
    )


def stablecoin_cost_frame(
    corridor_keys: pd.DataFrame, send_amount_usd: float
) -> pd.DataFrame:
    """Vectorised stablecoin cost for a (source, destination) frame."""
    src = corridor_keys["source_code"].astype(str).str.upper()
    dst = corridor_keys["destination_code"].astype(str).str.upper()
    onramp = src.map(lambda c: config.onramp_pct_for(c)).astype(float)
    offramp = dst.map(lambda c: config.offramp_pct_for(c)).astype(float)
    fx_spread = dst.map(lambda c: config.fx_spread_pct_for(c)).astype(float)
    gas_pct = (config.STABLECOIN_GAS_USD / max(send_amount_usd, 1e-9)) * 100.0
    return pd.DataFrame(
        {
            "corridor_id": corridor_keys["corridor_id"].values,
            "send_amount_usd": send_amount_usd,
            "sc_onramp_pct": onramp.values,
            "sc_offramp_pct": offramp.values,
            "sc_gas_pct": gas_pct,
            "sc_fx_spread_pct": fx_spread.values,
            "sc_total_pct": (onramp + offramp + fx_spread + gas_pct).values,
        }
    )


# ---------------------------------------------------------------------------
# Combine TCI snapshot + stablecoin + volumes -> savings
# ---------------------------------------------------------------------------


def build_savings_table(
    tci_snapshot: pd.DataFrame, brm: pd.DataFrame
) -> pd.DataFrame:
    """One row per (corridor × send_amount) with TCI, SC cost, savings, volume.

    `tci_snapshot` is the latest-quarter snapshot from
    pipeline.tci.latest_corridor_snapshot.
    """
    out_frames: list[pd.DataFrame] = []
    for amount in (
        int(config.HEADLINE_SEND_AMOUNT_USD),
        int(config.SECONDARY_SEND_AMOUNT_USD),
    ):
        sub = tci_snapshot[tci_snapshot["send_amount_bucket_usd"] == amount].copy()
        if sub.empty:
            continue
        keys = sub[["corridor_id", "source_code", "destination_code"]].drop_duplicates()
        sc = stablecoin_cost_frame(keys, send_amount_usd=float(amount))
        merged = sub.merge(sc, on="corridor_id", how="left")

        merged["savings_pct"] = (
            merged["tci_pct_mean"].astype(float) - merged["sc_total_pct"].astype(float)
        ).clip(lower=0.0)

        # Conservative savings using rolling 4q average (reduces noise).
        merged["savings_pct_r4"] = (
            merged["tci_pct_mean_r4"].astype(float) - merged["sc_total_pct"].astype(float)
        ).clip(lower=0.0)

        # Match volumes (BRM is corridor-level, not amount-specific).
        vol = latest_corridor_volumes(brm)
        merged = merged.merge(
            vol[["corridor_id", "volume_year", "volume_usd_annual"]],
            on="corridor_id",
            how="left",
        )
        merged["savings_usd_annual"] = (
            merged["savings_pct"].astype(float) / 100.0
            * merged["volume_usd_annual"].astype(float)
        )
        merged["savings_usd_annual_r4"] = (
            merged["savings_pct_r4"].astype(float) / 100.0
            * merged["volume_usd_annual"].astype(float)
        )

        # Normalised send-amount column for downstream join.
        merged["send_amount_usd"] = amount
        out_frames.append(merged)

    return pd.concat(out_frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Global aggregates
# ---------------------------------------------------------------------------


def global_savings_summary(savings: pd.DataFrame) -> dict[str, object]:
    """Headline numbers for sanity-checking against published estimates."""
    head = int(config.HEADLINE_SEND_AMOUNT_USD)
    sub = savings[savings["send_amount_usd"] == head].copy()

    has_volume = sub["volume_usd_annual"].notna() & (sub["volume_usd_annual"] > 0)
    sub = sub[has_volume]
    total_volume = float(sub["volume_usd_annual"].sum())
    total_savings = float(sub["savings_usd_annual"].sum())
    total_savings_r4 = float(sub["savings_usd_annual_r4"].sum())
    n_corridors_priced = int(sub["corridor_id"].nunique())
    n_with_savings = int((sub["savings_pct"] > 0).sum())

    return {
        "send_amount_usd": head,
        "n_corridors_with_volume": n_corridors_priced,
        "n_corridors_with_positive_savings": n_with_savings,
        "total_corridor_volume_usd": total_volume,
        "total_savings_usd_annual_current": total_savings,
        "total_savings_usd_annual_rolling4q": total_savings_r4,
        "implied_avg_savings_pct_current": (
            (total_savings / total_volume) * 100.0 if total_volume else 0.0
        ),
        "volume_year": (
            int(sub["volume_year"].dropna().mode().iloc[0])
            if not sub["volume_year"].dropna().empty
            else None
        ),
    }


def by_sending_country_burden(
    savings: pd.DataFrame, top_n: int = 10
) -> pd.DataFrame:
    """Diaspora burden by sending country (preview — full version in aggregate.py)."""
    head = int(config.HEADLINE_SEND_AMOUNT_USD)
    sub = savings[
        (savings["send_amount_usd"] == head)
        & savings["volume_usd_annual"].notna()
    ].copy()
    sub["fee_burden_usd_annual"] = (
        sub["tci_pct_mean"].astype(float) / 100.0
        * sub["volume_usd_annual"].astype(float)
    )
    out = (
        sub.groupby(["source_code", "source_name"], dropna=False)
        .agg(
            corridors=("corridor_id", "nunique"),
            volume_usd=("volume_usd_annual", "sum"),
            burden_usd=("fee_burden_usd_annual", "sum"),
            sc_savings_usd=("savings_usd_annual", "sum"),
        )
        .sort_values("burden_usd", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return out


# ---------------------------------------------------------------------------
# Pretty print
# ---------------------------------------------------------------------------


def _fmt_usd_b(x: float) -> str:
    if x is None or np.isnan(x):
        return "n/a"
    return f"${x / 1e9:>6.2f} B"


def _fmt_usd_m(x: float) -> str:
    if x is None or np.isnan(x):
        return "n/a"
    return f"${x / 1e6:>9.1f} M"


def print_summary(savings: pd.DataFrame) -> None:
    head = int(config.HEADLINE_SEND_AMOUNT_USD)
    summary = global_savings_summary(savings)
    sub = savings[
        (savings["send_amount_usd"] == head)
        & savings["volume_usd_annual"].notna()
    ].copy()

    print()
    print("=" * 86)
    print("PHASE 3 — Stablecoin counterfactual + savings")
    print("=" * 86)
    print(f"  Volume year (BRM)              : {summary['volume_year']}")
    print(
        f"  Corridors priced w/ volume     : {summary['n_corridors_with_volume']:>10,}  "
        f"({summary['n_corridors_with_positive_savings']:,} have positive savings)"
    )
    print(
        f"  Total corridor volume (matched): {_fmt_usd_b(summary['total_corridor_volume_usd'])}"
    )
    print(
        f"  Total savings (current period) : {_fmt_usd_b(summary['total_savings_usd_annual_current'])}"
    )
    print(
        f"  Total savings (rolling 4q TCI) : {_fmt_usd_b(summary['total_savings_usd_annual_rolling4q'])}"
    )
    print(
        f"  Implied weighted savings (cur) : "
        f"{summary['implied_avg_savings_pct_current']:>10.2f} %"
    )
    print()
    print("  Sanity check — published ballpark for global stablecoin")
    print("  remittance savings is ~$30-50 B/yr (CLAUDE.md §7).")
    print()

    print("  Top 10 corridors by absolute savings (USD/year, USD 200 bucket):")
    abs_top = sub.sort_values("savings_usd_annual", ascending=False).head(10)
    print(
        f"    {'corridor':<11s} {'send → recv':<46s} "
        f"{'TCI%':>6s} {'SC%':>6s} {'save%':>6s} {'volume':>12s} {'savings $/yr':>14s}"
    )
    print(f"    {'-' * 11} {'-' * 46} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 12} {'-' * 14}")
    for r in abs_top.itertuples(index=False):
        label = f"{r.source_name} → {r.destination_name}"
        label = (label[:44] + "…") if len(label) > 45 else label
        print(
            f"    {r.corridor_id:<11s} {label:<46s} "
            f"{r.tci_pct_mean:>6.2f} {r.sc_total_pct:>6.2f} {r.savings_pct:>6.2f} "
            f"{_fmt_usd_b(r.volume_usd_annual):>12s} {_fmt_usd_m(r.savings_usd_annual):>14s}"
        )
    print()
    print("  Top 10 sending countries by total fee burden:")
    burden = by_sending_country_burden(savings, top_n=10)
    print(
        f"    {'iso3':<5s} {'sender':<28s} {'corridors':>10s} {'volume':>12s} "
        f"{'burden $/yr':>14s} {'SC savings':>14s}"
    )
    print(f"    {'-' * 5} {'-' * 28} {'-' * 10} {'-' * 12} {'-' * 14} {'-' * 14}")
    for r in burden.itertuples(index=False):
        sender = (r.source_name[:26] + "…") if r.source_name and len(r.source_name) > 27 else (r.source_name or r.source_code)
        print(
            f"    {r.source_code:<5s} {sender:<28s} {int(r.corridors):>10d} "
            f"{_fmt_usd_b(r.volume_usd):>12s} {_fmt_usd_m(r.burden_usd):>14s} "
            f"{_fmt_usd_m(r.sc_savings_usd):>14s}"
        )
    print()
    print("=" * 86)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def compute(
    parquet_path: Path = config.PROCESSED_RPW_PATH,
    brm_path: Path = config.RAW_BRM_PATH,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Return (per-corridor savings table, global summary dict)."""
    df = pd.read_parquet(parquet_path)
    period_panel = tci.corridor_period_tci(df)
    snapshot = tci.latest_corridor_snapshot(period_panel)
    brm = load_brm(brm_path)
    savings = build_savings_table(snapshot, brm)
    summary = global_savings_summary(savings)
    return savings, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute stablecoin savings.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    savings, _summary = compute()
    print_summary(savings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
