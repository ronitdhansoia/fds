"""Operator-class fixed-effects regression (methodology §5.3).

Specification:

    TCI_ipq = β₀ + Σ βₖ · 1{firm_type = k} + α_corridor + γ_quarter + ε_ipq

  - Entity FE: corridor
  - Time FE:   period (quarter)
  - Reference category: MTO (largest class)
  - Cluster SE by corridor (entity).

We fit twice — once for the headline USD 200 panel, once for USD 500 — and
write coefficient tables + a regression payload consumable by the dashboard
(operator_regression.json).

Run as a module:
    uv run python -m pipeline.regression
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
from linearmodels.panel import PanelOLS

from pipeline import config, tci

logger = logging.getLogger(__name__)





REFERENCE_FIRM_TYPE: str = config.REGRESSION_REFERENCE_FIRM_TYPE
ALL_FIRM_TYPES: tuple[str, ...] = config.FIRM_TYPE_CANONICAL
TREATMENT_FIRM_TYPES: tuple[str, ...] = tuple(
    ft for ft in ALL_FIRM_TYPES if ft != REFERENCE_FIRM_TYPE
)

@dataclass
class CoefficientRow:
    firm_type: str
    estimate_pct: float
    std_error_pct: float
    t_stat: float
    p_value: float
    ci_low_pct: float
    ci_high_pct: float
    significance: str
    n_observations_class: int

def _significance_stars(p: float) -> str:
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""





def _prepare_panel(df: pd.DataFrame, send_amount_usd: int) -> pd.DataFrame:
    """Filter to one send-amount bucket and assemble the regression panel.

    PanelOLS needs a (entity, time) MultiIndex. We use corridor_id as the
    entity dimension and the year-quarter timestamp as time. Multiple rows
    per (entity, time) are allowed — that's what gives us the within-cell
    variation across providers.
    """
    sub = df[df["send_amount_bucket_usd"] == send_amount_usd].copy()
    sub = sub.dropna(
        subset=["tci_pct", "firm_type", "corridor_id", "period_dt"]
    )
    sub["firm_type"] = pd.Categorical(
        sub["firm_type"],
        categories=ALL_FIRM_TYPES,
        ordered=False,
    )
    sub = sub[sub["firm_type"].notna()]
    sub = sub.set_index(["corridor_id", "period_dt"]).sort_index()
    return sub

def _design_matrix(
    panel: pd.DataFrame,
) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    """Pull (y, X, weights) from a prepared panel.

    X has one column per non-reference firm type (binary 0/1). The constant
    is absorbed by entity FE so we do NOT add an explicit intercept.
    """
    y = panel["tci_pct"].astype(float)
    x_cols = []
    for ft in TREATMENT_FIRM_TYPES:
        col = f"is_{ft}"
        panel[col] = (panel["firm_type"] == ft).astype(float)
        x_cols.append(col)
    X = panel[x_cols]
    return y, X, None





@dataclass
class RegressionResult:
    send_amount_usd: int
    n_observations: int
    n_corridors: int
    n_quarters: int
    rsquared: float
    rsquared_within: float
    rsquared_between: float
    rsquared_overall: float
    f_statistic: float
    f_pvalue: float
    coefficients: list[CoefficientRow]
    firm_type_counts: dict[str, int]
    reference_class: str
    cluster_var: str
    notes: list[str]

def fit_two_way_fe(
    df: pd.DataFrame, send_amount_usd: int
) -> RegressionResult:
    """Estimate the §5.3 two-way FE regression for one send-amount bucket."""
    panel = _prepare_panel(df, send_amount_usd)
    y, X, _ = _design_matrix(panel)

    logger.info(
        "fitting USD %d: %d obs, %d corridors, %d quarters",
        send_amount_usd,
        len(y),
        panel.index.get_level_values(0).nunique(),
        panel.index.get_level_values(1).nunique(),
    )

    model = PanelOLS(
        dependent=y,
        exog=X,
        entity_effects=True,
        time_effects=True,
        check_rank=False,
        drop_absorbed=True,
    )
    fit = model.fit(cov_type="clustered", cluster_entity=True)

    counts = panel["firm_type"].value_counts().to_dict()

    coefs: list[CoefficientRow] = []
    params = fit.params
    se = fit.std_errors
    tstats = fit.tstats
    pvals = fit.pvalues
    ci = fit.conf_int()
    for ft in TREATMENT_FIRM_TYPES:
        col = f"is_{ft}"
        if col not in params.index:

            continue
        est = float(params[col])
        s = float(se[col])
        t = float(tstats[col])
        p = float(pvals[col])
        lo = float(ci.loc[col, "lower"])
        hi = float(ci.loc[col, "upper"])
        coefs.append(
            CoefficientRow(
                firm_type=ft,
                estimate_pct=est,
                std_error_pct=s,
                t_stat=t,
                p_value=p,
                ci_low_pct=lo,
                ci_high_pct=hi,
                significance=_significance_stars(p),
                n_observations_class=int(counts.get(ft, 0)),
            )
        )

    return RegressionResult(
        send_amount_usd=int(send_amount_usd),
        n_observations=int(fit.nobs),
        n_corridors=int(panel.index.get_level_values(0).nunique()),
        n_quarters=int(panel.index.get_level_values(1).nunique()),
        rsquared=float(fit.rsquared),
        rsquared_within=float(fit.rsquared_within),
        rsquared_between=float(fit.rsquared_between),
        rsquared_overall=float(fit.rsquared_overall),
        f_statistic=float(fit.f_statistic.stat),
        f_pvalue=float(fit.f_statistic.pval),
        coefficients=coefs,
        firm_type_counts={
            str(k): int(v) for k, v in counts.items()
        },
        reference_class=REFERENCE_FIRM_TYPE,
        cluster_var="corridor_id",
        notes=[
            "Specification: TCI_ipq = β0 + Σ βk · 1{firm_type=k} + α_corridor + γ_period + ε.",
            f"Reference class: {REFERENCE_FIRM_TYPE} (largest cell).",
            "Cluster-robust standard errors at the corridor level.",
            "Estimates report TCI percentage-point differences relative to MTOs, "
            "after absorbing corridor and quarter fixed effects.",
        ],
    )





def result_to_payload(res: RegressionResult) -> dict[str, Any]:
    return {
        "send_amount_usd": res.send_amount_usd,
        "specification": {
            "model": "two-way fixed effects (corridor + quarter)",
            "dependent": "tci_pct",
            "reference_class": res.reference_class,
            "cluster_var": res.cluster_var,
            "treatment_classes": list(TREATMENT_FIRM_TYPES),
        },
        "fit": {
            "n_observations": res.n_observations,
            "n_corridors": res.n_corridors,
            "n_quarters": res.n_quarters,
            "rsquared": res.rsquared,
            "rsquared_within": res.rsquared_within,
            "rsquared_between": res.rsquared_between,
            "rsquared_overall": res.rsquared_overall,
            "f_statistic": res.f_statistic,
            "f_pvalue": res.f_pvalue,
        },
        "firm_type_counts": res.firm_type_counts,
        "coefficients": [asdict(c) for c in res.coefficients],
        "notes": res.notes,
    }

def write_regression_json(
    results: dict[int, RegressionResult],
    out_path: Path = config.OPERATOR_REGRESSION_JSON,
) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "models": {str(amt): result_to_payload(res) for amt, res in results.items()},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        json.dump(payload, fh, indent=2, allow_nan=False)
    logger.info("wrote %s", out_path)





def print_summary(results: dict[int, RegressionResult]) -> None:
    print()
    print("=" * 86)
    print("PHASE 4 — Operator-class regression (two-way FE)")
    print("=" * 86)
    for amount, res in results.items():
        print()
        print(f"  USD {amount}  |  N = {res.n_observations:,}   "
              f"corridors = {res.n_corridors}   quarters = {res.n_quarters}")
        print(f"  R²(overall) = {res.rsquared_overall:.3f}   "
              f"R²(within) = {res.rsquared_within:.3f}   "
              f"F = {res.f_statistic:.2f}   p < {max(res.f_pvalue, 1e-300):.2e}")
        print()
        print(f"  Coefficients (Δ TCI vs {REFERENCE_FIRM_TYPE}, percentage points):")
        print(f"    {'firm_type':<14s} {'β':>8s} {'SE':>7s} {'t':>7s} "
              f"{'p':>9s} {'95% CI':>20s}  sig")
        print(f"    {'-' * 14} {'-' * 8} {'-' * 7} {'-' * 7} {'-' * 9} {'-' * 20}  ---")
        for c in res.coefficients:
            ci = f"[{c.ci_low_pct:+5.2f}, {c.ci_high_pct:+5.2f}]"
            print(
                f"    {c.firm_type:<14s} "
                f"{c.estimate_pct:>+8.3f} {c.std_error_pct:>7.3f} "
                f"{c.t_stat:>+7.2f} {c.p_value:>9.3g} {ci:>20s}  "
                f"{c.significance}"
            )
        print()
        print("  Class counts (panel rows):")
        for ft in ALL_FIRM_TYPES:
            n = res.firm_type_counts.get(ft, 0)
            ref = "  (reference)" if ft == REFERENCE_FIRM_TYPE else ""
            print(f"    {ft:<14s} {n:>10,}{ref}")
    print()
    print("  Significance: ***p<0.01, **p<0.05, *p<0.10")
    print("=" * 86)





def fit_all(parquet_path: Path = config.PROCESSED_RPW_PATH) -> dict[int, RegressionResult]:
    df = pd.read_parquet(parquet_path)
    out: dict[int, RegressionResult] = {}
    for amount in (
        int(config.HEADLINE_SEND_AMOUNT_USD),
        int(config.SECONDARY_SEND_AMOUNT_USD),
    ):
        out[amount] = fit_two_way_fe(df, amount)
    return out

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Operator-class regression.")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--write-json", action="store_true",
                        help="Persist regression results to data/outputs/operator_regression.json")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    results = fit_all()
    print_summary(results)
    if args.write_json:
        write_regression_json(results)
    return 0

if __name__ == "__main__":
    sys.exit(main())
