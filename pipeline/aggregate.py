"""Diaspora burden + corridor rankings — Phase 4 aggregations.

Produces the data shapes the dashboard's landing page and world map need:
  - per sending country: total volume, total fee burden, weighted-avg TCI,
    stablecoin savings, top 5 destinations by burden;
  - per receiving country: total inflow + weighted-avg cost on the
    incoming side;
  - global ranking tables (top-N expensive corridors, top-N savings
    corridors, cheapest-N corridors).

Outputs `data/outputs/diaspora_burden.json`.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pipeline import config, stablecoin, tci

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _round(x: Any, n: int = 4) -> float | None:
    if x is None:
        return None
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return None
    return round(float(x), n)


def _maybe_int(x: Any) -> int | None:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return int(x)


def _maybe_str(x: Any) -> str | None:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return str(x)


# ---------------------------------------------------------------------------
# Per-corridor burden assembly
# ---------------------------------------------------------------------------


def build_corridor_burden(savings: pd.DataFrame) -> pd.DataFrame:
    """Add fee-burden columns to the per-corridor savings table.

    fee_burden_usd_annual = (TCI_corridor / 100) × annual_corridor_volume_usd
    """
    head = int(config.HEADLINE_SEND_AMOUNT_USD)
    df = savings[savings["send_amount_usd"] == head].copy()
    df = df[df["volume_usd_annual"].notna() & (df["volume_usd_annual"] > 0)]

    df["fee_burden_usd_annual"] = (
        df["tci_pct_mean"].astype(float) / 100.0
        * df["volume_usd_annual"].astype(float)
    )
    df["fee_burden_usd_annual_r4"] = (
        df["tci_pct_mean_r4"].astype(float) / 100.0
        * df["volume_usd_annual"].astype(float)
    )
    return df


# ---------------------------------------------------------------------------
# Sending-country aggregation
# ---------------------------------------------------------------------------


def by_sending_country(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["source_code", "source_name", "source_region"], dropna=False)
        .agg(
            n_corridors=("corridor_id", "nunique"),
            volume_usd=("volume_usd_annual", "sum"),
            fee_burden_usd=("fee_burden_usd_annual", "sum"),
            fee_burden_usd_r4=("fee_burden_usd_annual_r4", "sum"),
            sc_savings_usd=("savings_usd_annual", "sum"),
            sc_savings_usd_r4=("savings_usd_annual_r4", "sum"),
            tci_simple_mean=("tci_pct_mean", "mean"),
            sc_simple_mean=("sc_total_pct", "mean"),
        )
        .reset_index()
    )
    grouped["tci_volume_weighted_pct"] = (
        grouped["fee_burden_usd"] / grouped["volume_usd"] * 100.0
    )
    grouped["sc_savings_pct_volume_weighted"] = (
        grouped["sc_savings_usd"] / grouped["volume_usd"] * 100.0
    )
    grouped["fee_burden_share_global"] = (
        grouped["fee_burden_usd"] / grouped["fee_burden_usd"].sum()
    )
    return grouped.sort_values("fee_burden_usd", ascending=False).reset_index(drop=True)


def top_destinations_per_sender(
    df: pd.DataFrame, top_n: int = 5
) -> pd.DataFrame:
    cols = [
        "source_code",
        "destination_code",
        "destination_name",
        "destination_region",
        "tci_pct_mean",
        "sc_total_pct",
        "savings_pct",
        "volume_usd_annual",
        "fee_burden_usd_annual",
        "savings_usd_annual",
    ]
    sorted_df = df[cols].sort_values(
        ["source_code", "fee_burden_usd_annual"], ascending=[True, False]
    )
    sorted_df["rank"] = sorted_df.groupby("source_code").cumcount() + 1
    return sorted_df[sorted_df["rank"] <= top_n].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Receiving-country aggregation
# ---------------------------------------------------------------------------


def by_receiving_country(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["destination_code", "destination_name", "destination_region"], dropna=False)
        .agg(
            n_corridors=("corridor_id", "nunique"),
            inflow_usd=("volume_usd_annual", "sum"),
            fee_paid_usd=("fee_burden_usd_annual", "sum"),
            sc_savings_usd=("savings_usd_annual", "sum"),
            tci_simple_mean=("tci_pct_mean", "mean"),
        )
        .reset_index()
    )
    grouped["tci_volume_weighted_pct"] = (
        grouped["fee_paid_usd"] / grouped["inflow_usd"] * 100.0
    )
    return grouped.sort_values("inflow_usd", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Global rankings + headline
# ---------------------------------------------------------------------------


def headline_totals(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "send_amount_usd": int(config.HEADLINE_SEND_AMOUNT_USD),
        "n_corridors": int(df["corridor_id"].nunique()),
        "n_senders": int(df["source_code"].nunique()),
        "n_receivers": int(df["destination_code"].nunique()),
        "total_volume_usd": float(df["volume_usd_annual"].sum()),
        "total_fee_burden_usd": float(df["fee_burden_usd_annual"].sum()),
        "total_sc_savings_usd": float(df["savings_usd_annual"].sum()),
        "global_tci_volume_weighted_pct": (
            float(df["fee_burden_usd_annual"].sum())
            / float(df["volume_usd_annual"].sum()) * 100.0
        ),
    }


def ranking_payload(df: pd.DataFrame, n: int = 20) -> dict[str, list[dict[str, Any]]]:
    """Top-N rankings the dashboard renders on the landing page."""
    expensive = df.sort_values("tci_pct_mean", ascending=False).head(n)
    cheapest = df.sort_values("tci_pct_mean", ascending=True).head(n)
    biggest_savings = df.sort_values("savings_usd_annual", ascending=False).head(n)
    biggest_burden = df.sort_values("fee_burden_usd_annual", ascending=False).head(n)
    return {
        "most_expensive": [_corridor_row(r) for _, r in expensive.iterrows()],
        "cheapest": [_corridor_row(r) for _, r in cheapest.iterrows()],
        "biggest_absolute_savings": [_corridor_row(r) for _, r in biggest_savings.iterrows()],
        "biggest_fee_burden": [_corridor_row(r) for _, r in biggest_burden.iterrows()],
    }


def _corridor_row(r: pd.Series) -> dict[str, Any]:
    return {
        "id": _maybe_str(r["corridor_id"]),
        "source_code": _maybe_str(r["source_code"]),
        "source_name": _maybe_str(r.get("source_name")),
        "destination_code": _maybe_str(r["destination_code"]),
        "destination_name": _maybe_str(r.get("destination_name")),
        "tci_pct": _round(r["tci_pct_mean"]),
        "sc_total_pct": _round(r.get("sc_total_pct")),
        "savings_pct": _round(r.get("savings_pct")),
        "volume_usd_annual": _round(r.get("volume_usd_annual"), 0),
        "fee_burden_usd_annual": _round(r.get("fee_burden_usd_annual"), 0),
        "savings_usd_annual": _round(r.get("savings_usd_annual"), 0),
        "n_providers": _maybe_int(r.get("n_providers")),
    }


# ---------------------------------------------------------------------------
# JSON envelope
# ---------------------------------------------------------------------------


def _sender_row(r: pd.Series, top_dests: pd.DataFrame | None = None) -> dict[str, Any]:
    base = {
        "source_code": _maybe_str(r["source_code"]),
        "source_name": _maybe_str(r.get("source_name")),
        "source_region": _maybe_str(r.get("source_region")),
        "n_corridors": _maybe_int(r["n_corridors"]),
        "volume_usd_annual": _round(r["volume_usd"], 0),
        "fee_burden_usd_annual": _round(r["fee_burden_usd"], 0),
        "fee_burden_usd_annual_rolling_4q": _round(r["fee_burden_usd_r4"], 0),
        "sc_savings_usd_annual": _round(r["sc_savings_usd"], 0),
        "tci_volume_weighted_pct": _round(r["tci_volume_weighted_pct"]),
        "tci_simple_mean_pct": _round(r["tci_simple_mean"]),
        "sc_total_simple_mean_pct": _round(r["sc_simple_mean"]),
        "sc_savings_pct_volume_weighted": _round(r["sc_savings_pct_volume_weighted"]),
        "fee_burden_share_global": _round(r["fee_burden_share_global"], 6),
    }
    if top_dests is not None and not top_dests.empty:
        base["top_destinations"] = [
            {
                "destination_code": _maybe_str(d["destination_code"]),
                "destination_name": _maybe_str(d["destination_name"]),
                "tci_pct": _round(d["tci_pct_mean"]),
                "sc_total_pct": _round(d["sc_total_pct"]),
                "savings_pct": _round(d["savings_pct"]),
                "volume_usd_annual": _round(d["volume_usd_annual"], 0),
                "fee_burden_usd_annual": _round(d["fee_burden_usd_annual"], 0),
                "savings_usd_annual": _round(d["savings_usd_annual"], 0),
                "rank": _maybe_int(d.get("rank")),
            }
            for _, d in top_dests.iterrows()
        ]
    return base


def _receiver_row(r: pd.Series) -> dict[str, Any]:
    return {
        "destination_code": _maybe_str(r["destination_code"]),
        "destination_name": _maybe_str(r.get("destination_name")),
        "destination_region": _maybe_str(r.get("destination_region")),
        "n_corridors": _maybe_int(r["n_corridors"]),
        "inflow_usd_annual": _round(r["inflow_usd"], 0),
        "fee_paid_usd_annual": _round(r["fee_paid_usd"], 0),
        "sc_savings_usd_annual": _round(r["sc_savings_usd"], 0),
        "tci_volume_weighted_pct": _round(r["tci_volume_weighted_pct"]),
        "tci_simple_mean_pct": _round(r["tci_simple_mean"]),
    }


def build_payload(savings: pd.DataFrame) -> dict[str, Any]:
    df = build_corridor_burden(savings)
    senders = by_sending_country(df)
    top_dests = top_destinations_per_sender(df, top_n=5)
    receivers = by_receiving_country(df)
    rankings = ranking_payload(df, n=20)
    headline = headline_totals(df)

    sender_rows = []
    for _, r in senders.iterrows():
        td = top_dests[top_dests["source_code"] == r["source_code"]]
        sender_rows.append(_sender_row(r, td))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "headline": headline,
        "senders": sender_rows,
        "receivers": [_receiver_row(r) for _, r in receivers.iterrows()],
        "rankings": rankings,
    }


def write_json(
    payload: dict[str, Any],
    out_path: Path = config.DIASPORA_BURDEN_JSON,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        json.dump(payload, fh, separators=(",", ":"), allow_nan=False)
    size_kb = out_path.stat().st_size / 1024
    logger.info("wrote %s (%.1f KB)", out_path, size_kb)


# ---------------------------------------------------------------------------
# Pretty-print
# ---------------------------------------------------------------------------


def _fmt_b(x: float | None) -> str:
    if x is None or np.isnan(x):
        return "n/a"
    return f"${x / 1e9:>6.2f} B"


def _fmt_m(x: float | None) -> str:
    if x is None or np.isnan(x):
        return "n/a"
    return f"${x / 1e6:>9.1f} M"


def print_summary(payload: dict[str, Any]) -> None:
    h = payload["headline"]
    print()
    print("=" * 90)
    print("PHASE 4 — Diaspora burden aggregation")
    print("=" * 90)
    print(f"  Send-amount bucket             : USD {h['send_amount_usd']}")
    print(f"  Corridors                      : {h['n_corridors']:>10,}  "
          f"(senders {h['n_senders']}, receivers {h['n_receivers']})")
    print(f"  Total annualised volume        : {_fmt_b(h['total_volume_usd'])}")
    print(f"  Total fee burden               : {_fmt_b(h['total_fee_burden_usd'])}")
    print(f"  Total stablecoin savings       : {_fmt_b(h['total_sc_savings_usd'])}")
    print(f"  Volume-weighted global TCI     : {h['global_tci_volume_weighted_pct']:.2f} %")
    print()
    print("  Top 10 sending countries by fee burden:")
    print(f"    {'iso3':<5s} {'sender':<26s} {'corr':>5s} {'volume':>12s} "
          f"{'burden':>14s} {'TCI vw%':>9s} {'SC svg%':>9s}")
    print(f"    {'-' * 5} {'-' * 26} {'-' * 5} {'-' * 12} {'-' * 14} {'-' * 9} {'-' * 9}")
    for s in payload["senders"][:10]:
        nm = (s["source_name"] or s["source_code"])
        nm = nm[:24] + "…" if nm and len(nm) > 25 else nm
        print(f"    {s['source_code']:<5s} {nm:<26s} {s['n_corridors']:>5d} "
              f"{_fmt_b(s['volume_usd_annual']):>12s} {_fmt_m(s['fee_burden_usd_annual']):>14s} "
              f"{s['tci_volume_weighted_pct'] or 0:>8.2f}% "
              f"{s['sc_savings_pct_volume_weighted'] or 0:>8.2f}%")
    print()
    print("  Top 10 receiving countries by inflow:")
    print(f"    {'iso3':<5s} {'receiver':<26s} {'corr':>5s} {'inflow':>12s} "
          f"{'fees paid':>14s} {'TCI vw%':>9s}")
    print(f"    {'-' * 5} {'-' * 26} {'-' * 5} {'-' * 12} {'-' * 14} {'-' * 9}")
    for r in payload["receivers"][:10]:
        nm = (r["destination_name"] or r["destination_code"])
        nm = nm[:24] + "…" if nm and len(nm) > 25 else nm
        print(f"    {r['destination_code']:<5s} {nm:<26s} {r['n_corridors']:>5d} "
              f"{_fmt_b(r['inflow_usd_annual']):>12s} {_fmt_m(r['fee_paid_usd_annual']):>14s} "
              f"{r['tci_volume_weighted_pct'] or 0:>8.2f}%")
    print()
    print("  Top 10 corridors by absolute fee burden:")
    print(f"    {'corridor':<10s} {'send → recv':<48s} {'TCI%':>6s} "
          f"{'volume':>12s} {'burden':>14s}")
    print(f"    {'-' * 10} {'-' * 48} {'-' * 6} {'-' * 12} {'-' * 14}")
    for c in payload["rankings"]["biggest_fee_burden"][:10]:
        label = f"{c['source_name']} → {c['destination_name']}"
        label = label[:46] + "…" if len(label) > 47 else label
        print(f"    {c['id']:<10s} {label:<48s} {c['tci_pct'] or 0:>6.2f} "
              f"{_fmt_b(c['volume_usd_annual']):>12s} {_fmt_m(c['fee_burden_usd_annual']):>14s}")
    print()
    print("=" * 90)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def compute() -> dict[str, Any]:
    """Run the full Phase 4 aggregation pipeline and return the JSON payload."""
    savings, _summary = stablecoin.compute()
    return build_payload(savings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diaspora burden aggregation.")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--write-json", action="store_true",
                        help="Persist to data/outputs/diaspora_burden.json")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    payload = compute()
    print_summary(payload)
    if args.write_json:
        write_json(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
