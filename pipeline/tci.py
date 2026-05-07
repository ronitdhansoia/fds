"""True Cost Index — per-provider, corridor-level, and time series.

Methodology §5.1:

    TCI(s, d, p, q, A) = fee_pct + fx_margin_pct + speed_penalty
    speed_penalty = κ × max(0, days_to_arrive − 1),  κ = 0.10

Per-provider TCI is computed in pipeline.preprocess. This module:
  - Aggregates to (corridor × period × send-amount) using uniform weighting
    across providers. RPW does not publish provider-level market shares
    in the public release (verified 2026-04-30); aggregation method is
    surfaced on /methodology along with this caveat.
  - Provides corridor summaries: latest quarter, 4-quarter rolling mean,
    and the full quarterly history.

Run as a module to print a top-20 ranking:
    uv run python -m pipeline.tci
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline import config

logger = logging.getLogger(__name__)





def load_clean_panel(path: Path = config.PROCESSED_RPW_PATH) -> pd.DataFrame:
    """Load the parquet produced by pipeline.preprocess."""
    if not path.exists():
        raise FileNotFoundError(
            f"missing {path} — run `uv run python -m pipeline.preprocess` first."
        )
    df = pd.read_parquet(path)
    return df







_TCI_COMPONENT_COLS: tuple[str, ...] = (
    "fee_pct",
    "fx_margin_pct",
    "speed_penalty_pct",
    "tci_pct",
    "total_cost_pct",
    "days_to_arrive",
)

def _agg_by(group_cols: list[str], df: pd.DataFrame) -> pd.DataFrame:
    """Mean of every TCI component, plus n_providers and tci median."""
    aggs: dict[str, tuple[str, str | callable]] = {
        f"{c}_mean": (c, "mean") for c in _TCI_COMPONENT_COLS
    }
    aggs["tci_median_pct"] = ("tci_pct", "median")
    aggs["tci_min_pct"] = ("tci_pct", "min")
    aggs["tci_max_pct"] = ("tci_pct", "max")
    aggs["n_providers"] = ("firm", "nunique")
    aggs["n_observations"] = ("tci_pct", "size")
    return df.groupby(group_cols, dropna=False).agg(**aggs).reset_index()

def corridor_period_tci(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (corridor × period × send_amount) with the headline metrics."""
    cols = [
        "corridor_id",
        "source_code",
        "source_name",
        "source_region",
        "destination_code",
        "destination_name",
        "destination_region",
        "period",
        "period_dt",
        "year",
        "quarter",
        "send_amount_bucket_usd",
    ]
    out = _agg_by(cols, df)
    return out.sort_values(["corridor_id", "send_amount_bucket_usd", "period_dt"]).reset_index(
        drop=True
    )

def rolling_4q_tci(period_panel: pd.DataFrame) -> pd.DataFrame:
    """Add 4-quarter rolling means for the headline metrics."""
    panel = period_panel.copy().sort_values(
        ["corridor_id", "send_amount_bucket_usd", "period_dt"]
    )
    grp = panel.groupby(["corridor_id", "send_amount_bucket_usd"], dropna=False)
    rolling_targets = [f"{c}_mean" for c in _TCI_COMPONENT_COLS]
    for col in rolling_targets:
        panel[f"{col}_r4"] = grp[col].transform(
            lambda s: s.rolling(window=4, min_periods=2).mean()
        )
    return panel





@dataclass(frozen=True)
class HeadlineRanking:
    send_amount_usd: int
    period: pd.Timestamp
    table: pd.DataFrame

def latest_corridor_snapshot(period_panel: pd.DataFrame) -> pd.DataFrame:
    """Latest quarter per (corridor × send_amount), with rolling-4q context."""
    rolled = rolling_4q_tci(period_panel)
    idx = rolled.groupby(
        ["corridor_id", "send_amount_bucket_usd"], dropna=False
    )["period_dt"].idxmax()
    snap = rolled.loc[idx].reset_index(drop=True)
    return snap

def top_n_expensive(
    snapshot: pd.DataFrame, send_amount_usd: int, n: int = 20, min_providers: int = 3
) -> pd.DataFrame:
    """Top-N corridors by mean TCI in the latest quarter, gated on coverage."""
    sub = snapshot[snapshot["send_amount_bucket_usd"] == send_amount_usd]
    sub = sub[sub["n_providers"] >= min_providers]
    return sub.sort_values("tci_pct_mean", ascending=False).head(n).reset_index(drop=True)

def cheapest_corridors(
    snapshot: pd.DataFrame, send_amount_usd: int, n: int = 20, min_providers: int = 3
) -> pd.DataFrame:
    sub = snapshot[snapshot["send_amount_bucket_usd"] == send_amount_usd]
    sub = sub[sub["n_providers"] >= min_providers]
    return sub.sort_values("tci_pct_mean", ascending=True).head(n).reset_index(drop=True)





def _format_corridor_label(row: pd.Series, max_len: int = 46) -> str:
    label = f"{row['source_name']} → {row['destination_name']}"
    return (label[: max_len - 1] + "…") if len(label) > max_len else label

def print_top_n(snapshot: pd.DataFrame, send_amount_usd: int = 200, n: int = 20) -> None:
    period = snapshot["period_dt"].max()
    ts = pd.Timestamp(period)
    print()
    print("=" * 86)
    print(
        f"  Top {n} most expensive corridors — USD {send_amount_usd}, "
        f"latest quarter ({ts.year} Q{((ts.month - 1) // 3) + 1})"
    )
    print("  Ranked by mean TCI across providers (uniform weighting). "
          "Min 3 providers per corridor.")
    print("=" * 86)
    print()
    print(
        f"  {'#':>2} {'corridor':<11s} {'send → recv':<46s} "
        f"{'n':>3s} {'fee%':>6s} {'fx%':>6s} {'spd%':>6s} {'TCI%':>7s}"
    )
    print(f"  {'-' * 2} {'-' * 11} {'-' * 46} {'-' * 3} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 7}")

    table = top_n_expensive(snapshot, send_amount_usd=send_amount_usd, n=n)
    for i, row in enumerate(table.itertuples(index=False), start=1):
        label = _format_corridor_label(pd.Series({"source_name": row.source_name,
                                                  "destination_name": row.destination_name}))
        print(
            f"  {i:>2d} {row.corridor_id:<11s} {label:<46s} "
            f"{int(row.n_providers):>3d} "
            f"{row.fee_pct_mean:>6.2f} {row.fx_margin_pct_mean:>6.2f} "
            f"{row.speed_penalty_pct_mean:>6.2f} {row.tci_pct_mean:>7.2f}"
        )

    print()
    print("  Anti-check — 10 cheapest corridors at the same threshold:")
    cheap = cheapest_corridors(snapshot, send_amount_usd=send_amount_usd, n=10)
    for i, row in enumerate(cheap.itertuples(index=False), start=1):
        label = _format_corridor_label(pd.Series({"source_name": row.source_name,
                                                  "destination_name": row.destination_name}))
        print(
            f"  {i:>2d} {row.corridor_id:<11s} {label:<46s} "
            f"{int(row.n_providers):>3d} "
            f"{row.fee_pct_mean:>6.2f} {row.fx_margin_pct_mean:>6.2f} "
            f"{row.speed_penalty_pct_mean:>6.2f} {row.tci_pct_mean:>7.2f}"
        )
    print()
    print("=" * 86)





def extreme_corridor_robustness(
    df: pd.DataFrame,
    snapshot: pd.DataFrame,
    send_amount_usd: int = 200,
    top_n: int = 5,
    min_providers: int = 3,
) -> list[dict[str, object]]:
    """For each of the top-N corridors by mean TCI, compute robustness checks.

    Returns one dict per corridor with:
      - mean_tci, median_tci, n_providers
      - mean_excl_max: mean recomputed after dropping the single highest-TCI
        provider (a one-out trim).
      - rank_by_mean, rank_by_median, rank_by_excl_max — index in the top-20
        ranking under each aggregation alternative; corridor_ordering_unchanged
        is True if all three rankings keep the corridor in top 10.

    The point is to demonstrate that the headline ordering is not driven by a
    single high-cost provider in a thin sample.
    """
    head = top_n_expensive(snapshot, send_amount_usd=send_amount_usd,
                           n=top_n, min_providers=min_providers)
    target_ids = head["corridor_id"].tolist()
    if not target_ids:
        return []


    sub = df[df["send_amount_bucket_usd"] == send_amount_usd].copy()
    latest = sub["period_dt"].max()
    rows = sub[sub["period_dt"] == latest]



    def _agg_alts(grp: pd.DataFrame) -> pd.Series:
        n = grp["firm"].nunique()
        if n < min_providers:
            return pd.Series(
                {"mean_tci": np.nan, "median_tci": np.nan,
                 "mean_excl_max": np.nan, "n_providers": n}
            )
        tci = grp["tci_pct"].dropna()
        if len(tci) == 0:
            return pd.Series(
                {"mean_tci": np.nan, "median_tci": np.nan,
                 "mean_excl_max": np.nan, "n_providers": n}
            )
        mx = tci.idxmax()
        excl = tci.drop(mx)
        return pd.Series({
            "mean_tci": float(tci.mean()),
            "median_tci": float(tci.median()),
            "mean_excl_max": float(excl.mean()) if len(excl) else float(tci.mean()),
            "n_providers": int(n),
        })

    alts = (
        rows.groupby(["corridor_id", "source_name", "destination_name"])
        .apply(_agg_alts, include_groups=False)
        .reset_index()
    )
    alts = alts[alts["mean_tci"].notna()].copy()
    alts["rank_by_mean"] = alts["mean_tci"].rank(method="min", ascending=False).astype(int)
    alts["rank_by_median"] = alts["median_tci"].rank(method="min", ascending=False).astype(int)
    alts["rank_by_excl_max"] = alts["mean_excl_max"].rank(method="min", ascending=False).astype(int)

    out: list[dict[str, object]] = []
    for cid in target_ids:
        row = alts[alts["corridor_id"] == cid]
        if row.empty:
            continue
        r = row.iloc[0]
        out.append({
            "corridor_id": str(r["corridor_id"]),
            "source_name": str(r["source_name"]),
            "destination_name": str(r["destination_name"]),
            "n_providers": int(r["n_providers"]),
            "mean_tci_pct": round(float(r["mean_tci"]), 4),
            "median_tci_pct": round(float(r["median_tci"]), 4),
            "mean_excl_max_provider_pct": round(float(r["mean_excl_max"]), 4),
            "rank_by_mean": int(r["rank_by_mean"]),
            "rank_by_median": int(r["rank_by_median"]),
            "rank_by_excl_max": int(r["rank_by_excl_max"]),
            "stays_in_top_10_under_all_three": bool(
                r["rank_by_mean"] <= 10
                and r["rank_by_median"] <= 10
                and r["rank_by_excl_max"] <= 10
            ),
        })
    return out

def latest_provider_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """For each corridor × send_amount, the latest-quarter per-provider rows."""
    cols = [
        "corridor_id",
        "send_amount_bucket_usd",
        "period_dt",
        "period",
        "firm",
        "firm_type",
        "fee_pct",
        "fx_margin_pct",
        "speed_penalty_pct",
        "tci_pct",
        "total_cost_pct",
        "days_to_arrive",
    ]
    sub = df[cols].copy()

    latest = sub.groupby(["corridor_id", "send_amount_bucket_usd"])["period_dt"].transform("max")
    keep = sub["period_dt"] == latest
    return sub[keep].sort_values(
        ["corridor_id", "send_amount_bucket_usd", "tci_pct"]
    ).reset_index(drop=True)





def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute corridor-level TCI rankings.")
    parser.add_argument(
        "--amount",
        type=int,
        choices=[int(config.HEADLINE_SEND_AMOUNT_USD), int(config.SECONDARY_SEND_AMOUNT_USD)],
        default=int(config.HEADLINE_SEND_AMOUNT_USD),
    )
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    df = load_clean_panel()
    panel = corridor_period_tci(df)
    snap = latest_corridor_snapshot(panel)
    print_top_n(snap, send_amount_usd=args.amount, n=args.n)
    return 0

if __name__ == "__main__":
    sys.exit(main())
