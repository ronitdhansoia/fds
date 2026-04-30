"""Serialize corridor-level TCI tables to JSON for the Next.js dashboard.

Outputs (all in `data/outputs/`):
  - corridors.json: per-corridor headline + per-amount details + history +
    latest-quarter provider breakdown.
  - meta.json: generation timestamp, dataset version, key constants.

After Phase 3 the stablecoin counterfactual is merged into the same
corridors.json (this module exposes `update_with_stablecoin()` for that).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pipeline import config, stablecoin, tci

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON-safety helpers
# ---------------------------------------------------------------------------


def _round(x: float, n: int = 4) -> float | None:
    """Round to n decimals, mapping NaN/inf -> None for clean JSON."""
    if x is None:
        return None
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return None
    if isinstance(x, (np.floating, np.integer)):
        x = float(x)
    return round(float(x), n)


def _maybe_int(x: Any) -> int | None:
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    return int(x)


def _maybe_str(x: Any) -> str | None:
    if x is None:
        return None
    if isinstance(x, float) and np.isnan(x):
        return None
    return str(x)


def _period_label(year: Any, quarter: Any) -> str | None:
    y, q = _maybe_int(year), _maybe_int(quarter)
    if y is None or q is None:
        return None
    return f"{y}_{q}Q"


# ---------------------------------------------------------------------------
# Per-amount payload
# ---------------------------------------------------------------------------


def _component_dict(row: pd.Series, suffix: str = "_mean") -> dict[str, float | None]:
    return {
        "fee_pct": _round(row.get(f"fee_pct{suffix}")),
        "fx_margin_pct": _round(row.get(f"fx_margin_pct{suffix}")),
        "speed_penalty_pct": _round(row.get(f"speed_penalty_pct{suffix}")),
        "tci_pct": _round(row.get(f"tci_pct{suffix}")),
    }


def _current_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "period": _period_label(row.get("year"), row.get("quarter")),
        **_component_dict(row, suffix="_mean"),
        "tci_median_pct": _round(row.get("tci_median_pct")),
        "tci_min_pct": _round(row.get("tci_min_pct")),
        "tci_max_pct": _round(row.get("tci_max_pct")),
        "total_cost_pct": _round(row.get("total_cost_pct_mean")),
        "days_to_arrive_mean": _round(row.get("days_to_arrive_mean"), 2),
        "n_providers": _maybe_int(row.get("n_providers")),
        "n_observations": _maybe_int(row.get("n_observations")),
    }


def _rolling_payload(row: pd.Series) -> dict[str, float | None]:
    return {
        "fee_pct": _round(row.get("fee_pct_mean_r4")),
        "fx_margin_pct": _round(row.get("fx_margin_pct_mean_r4")),
        "speed_penalty_pct": _round(row.get("speed_penalty_pct_mean_r4")),
        "tci_pct": _round(row.get("tci_pct_mean_r4")),
    }


def _history_payload(history: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in history.itertuples(index=False):
        out.append(
            {
                "period": _period_label(getattr(row, "year"), getattr(row, "quarter")),
                "fee_pct": _round(row.fee_pct_mean),
                "fx_margin_pct": _round(row.fx_margin_pct_mean),
                "speed_penalty_pct": _round(row.speed_penalty_pct_mean),
                "tci_pct": _round(row.tci_pct_mean),
                "n_providers": _maybe_int(row.n_providers),
            }
        )
    return out


def _provider_payload(providers: pd.DataFrame) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in providers.itertuples(index=False):
        out.append(
            {
                "firm": _maybe_str(row.firm),
                "firm_type": _maybe_str(row.firm_type),
                "fee_pct": _round(row.fee_pct),
                "fx_margin_pct": _round(row.fx_margin_pct),
                "speed_penalty_pct": _round(row.speed_penalty_pct),
                "tci_pct": _round(row.tci_pct),
                "total_cost_pct": _round(row.total_cost_pct),
                "days_to_arrive": _round(row.days_to_arrive, 1),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Corridor-level builder
# ---------------------------------------------------------------------------


def _corridor_identity(row: pd.Series) -> dict[str, Any]:
    return {
        "id": _maybe_str(row.get("corridor_id")),
        "source_code": _maybe_str(row.get("source_code")),
        "source_name": _maybe_str(row.get("source_name")),
        "source_region": _maybe_str(row.get("source_region")),
        "destination_code": _maybe_str(row.get("destination_code")),
        "destination_name": _maybe_str(row.get("destination_name")),
        "destination_region": _maybe_str(row.get("destination_region")),
    }


def _stablecoin_payload(row: pd.Series) -> dict[str, Any]:
    return {
        "onramp_pct": _round(row.get("sc_onramp_pct"), 2),
        "offramp_pct": _round(row.get("sc_offramp_pct"), 2),
        "gas_pct": _round(row.get("sc_gas_pct")),
        "fx_spread_pct": _round(row.get("sc_fx_spread_pct"), 2),
        "total_pct": _round(row.get("sc_total_pct")),
        "savings_pct": _round(row.get("savings_pct")),
        "savings_pct_rolling_4q": _round(row.get("savings_pct_r4")),
        "volume_year": _maybe_int(row.get("volume_year")),
        "volume_usd_annual": _round(row.get("volume_usd_annual"), 0),
        "savings_usd_annual": _round(row.get("savings_usd_annual"), 0),
        "savings_usd_annual_rolling_4q": _round(row.get("savings_usd_annual_r4"), 0),
    }


def build_corridor_payloads(
    panel: pd.DataFrame,
    providers: pd.DataFrame,
    savings: pd.DataFrame | None = None,
) -> list[dict[str, Any]]:
    """One JSON object per corridor with per-amount metrics, history, providers,
    and (when supplied) the stablecoin counterfactual."""
    rolled = tci.rolling_4q_tci(panel)
    snapshot_idx = rolled.groupby(
        ["corridor_id", "send_amount_bucket_usd"], dropna=False
    )["period_dt"].idxmax()
    snap_full = rolled.loc[snapshot_idx].reset_index(drop=True)
    # quick lookup via dict: (corridor_id, amount) -> row Series
    snap_by_key: dict[tuple[str, int], pd.Series] = {
        (str(r["corridor_id"]), int(r["send_amount_bucket_usd"])): r
        for _, r in snap_full.iterrows()
    }

    sc_by_key: dict[tuple[str, int], pd.Series] = {}
    if savings is not None and not savings.empty:
        for _, r in savings.iterrows():
            sc_by_key[(str(r["corridor_id"]), int(r["send_amount_usd"]))] = r

    # group full quarterly history per (corridor × amount)
    history_groups = rolled.groupby(["corridor_id", "send_amount_bucket_usd"], dropna=False)
    provider_groups = providers.groupby(["corridor_id", "send_amount_bucket_usd"], dropna=False)

    corridor_ids = sorted(panel["corridor_id"].unique())
    out: list[dict[str, Any]] = []
    head_amount = int(config.HEADLINE_SEND_AMOUNT_USD)
    sec_amount = int(config.SECONDARY_SEND_AMOUNT_USD)

    for cid in corridor_ids:
        ident_row = snap_by_key.get((cid, head_amount))
        if ident_row is None:
            ident_row = snap_by_key.get((cid, sec_amount))
        if ident_row is None:
            continue
        ident = _corridor_identity(ident_row)

        amounts: dict[str, dict[str, Any]] = {}
        for amount in (head_amount, sec_amount):
            key = (cid, amount)
            row = snap_by_key.get(key)
            if row is None:
                continue
            try:
                hist = history_groups.get_group(key).sort_values("period_dt")
            except KeyError:
                hist = pd.DataFrame()
            try:
                provs = provider_groups.get_group(key).sort_values("tci_pct")
            except KeyError:
                provs = pd.DataFrame()
            amount_payload: dict[str, Any] = {
                "current": _current_payload(row),
                "rolling_4q": _rolling_payload(row),
                "history": _history_payload(hist),
                "providers": _provider_payload(provs),
            }
            sc_row = sc_by_key.get((cid, amount))
            if sc_row is not None:
                amount_payload["stablecoin"] = _stablecoin_payload(sc_row)
            amounts[str(amount)] = amount_payload

        if not amounts:
            continue
        out.append({**ident, "amounts": amounts})

    out.sort(key=lambda c: c["id"])
    return out


# ---------------------------------------------------------------------------
# Meta + envelope
# ---------------------------------------------------------------------------


def build_meta(
    df: pd.DataFrame, savings_summary: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Run-level metadata pinned to the loaded panel."""
    first = df.loc[df["period_dt"].idxmin()]
    last = df.loc[df["period_dt"].idxmax()]
    meta: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "panel_first_period": _period_label(first["year"], first["quarter"]),
        "panel_last_period": _period_label(last["year"], last["quarter"]),
        "n_quarters": int(df["period_dt"].nunique()),
        "n_corridors": int(df["corridor_id"].nunique()),
        "n_providers": int(df["firm"].nunique()),
        "n_rows": int(len(df)),
        "send_amounts_usd": [
            int(config.HEADLINE_SEND_AMOUNT_USD),
            int(config.SECONDARY_SEND_AMOUNT_USD),
        ],
        "headline_send_amount_usd": int(config.HEADLINE_SEND_AMOUNT_USD),
        "kappa_pct_per_day": config.TCI_KAPPA_PCT_PER_DAY,
        "weighting": "uniform",
        "weighting_note": (
            "Provider-level market shares are not exposed in the public "
            "Remittance Prices Worldwide release (verified 2026-04-30). "
            "Corridor-level TCI is the unweighted mean across providers; "
            "median is reported alongside as a robustness check."
        ),
        "stablecoin_assumptions": {
            "gas_usd": config.STABLECOIN_GAS_USD,
            "onramp_pct": {
                "default": config.ONRAMP_DEFAULT_PCT,
                "developed": config.ONRAMP_DEVELOPED_PCT,
                "low_banked": config.ONRAMP_LOW_BANKED_PCT,
                "developed_iso3": sorted(config.DEVELOPED_SENDERS_ISO3),
                "low_banked_iso3": sorted(config.LOW_BANKED_SENDERS_ISO3),
            },
            "offramp_pct": {
                "default": config.OFFRAMP_DEFAULT_PCT,
                "top_p2p": config.OFFRAMP_TOP_P2P_PCT,
                "thin_liquidity": config.OFFRAMP_THIN_LIQUIDITY_PCT,
                "top_p2p_iso3": sorted(config.TOP_P2P_RECEIVERS_ISO3),
                "thin_liquidity_iso3": sorted(config.THIN_LIQUIDITY_RECEIVERS_ISO3),
            },
            "fx_spread_pct": {
                "deep": config.FX_SPREAD_DEEP_PCT,
                "default": config.FX_SPREAD_DEFAULT_PCT,
                "deep_iso3": sorted(config.DEEP_STABLECOIN_RECEIVERS_ISO3),
            },
            "note": (
                "Conservative defaults. Reviewers will probe these — every "
                "value is exposed in /methodology and the per-corridor "
                "stablecoin block lists the actual percent applied."
            ),
        },
        "data_sources": {
            "rpw": {
                "name": "World Bank — Remittance Prices Worldwide (RPW)",
                "url": "https://remittanceprices.worldbank.org/",
                "release_file": config.RPW_PRIMARY_URL,
                "retrieval_date": "2026-04-30",
                "scope_note": (
                    "Modern sheet only ('Dataset (from Q2 2016)'). The legacy "
                    "pre-2016 sheet ships an incompatible schema and is "
                    "excluded from the headline analysis."
                ),
            },
            "bilateral_remittance_matrix": {
                "name": "World Bank / KNOMAD — Bilateral Remittance Estimates",
                "indicator": "WB_KNOMAD_BRE",
                "endpoint": config.BRM_API_URL,
                "year": config.BRM_LATEST_YEAR,
                "retrieval_date": "2026-04-30",
                "unit": "USD millions",
                "scope_note": (
                    "Latest year available is 2021. We pair each RPW corridor "
                    "with its 2021 BRM estimate to compute annual savings. "
                    "Corridors absent from BRM contribute to percentage savings "
                    "only and are excluded from USD totals."
                ),
            },
        },
    }
    if savings_summary:
        meta["global_savings"] = savings_summary
    return meta


def write_corridors_json(
    corridors: list[dict[str, Any]],
    meta: dict[str, Any],
    out_path: Path = config.CORRIDORS_JSON,
) -> None:
    payload = {"meta": meta, "corridors": corridors}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        json.dump(payload, fh, separators=(",", ":"), allow_nan=False)
    size_mb = out_path.stat().st_size / 1_048_576
    logger.info("wrote %s (%.2f MB, %d corridors)", out_path, size_mb, len(corridors))


def write_meta_json(meta: dict[str, Any], out_path: Path = config.META_JSON) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        json.dump(meta, fh, indent=2, allow_nan=False)
    logger.info("wrote %s", out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export corridors.json + meta.json.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    config.ensure_dirs()
    df = tci.load_clean_panel()
    panel = tci.corridor_period_tci(df)
    providers = tci.latest_provider_breakdown(df)

    # Stablecoin counterfactual + bilateral volumes (Phase 3)
    try:
        savings_table, savings_summary = stablecoin.compute()
    except FileNotFoundError as exc:
        logger.warning(
            "stablecoin compute skipped (%s) — corridors.json will not include "
            "stablecoin block. Run `pipeline.ingest --only brm` first.",
            exc,
        )
        savings_table, savings_summary = None, None

    corridors = build_corridor_payloads(panel, providers, savings=savings_table)
    meta = build_meta(df, savings_summary=savings_summary)
    write_corridors_json(corridors, meta)
    write_meta_json(meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
