"""End-to-end orchestrator — regenerates every artifact from raw RPW + BRM.

Usage:
    uv run python scripts/run_all.py            # regenerate everything
    uv run python scripts/run_all.py --skip-download   # use cached raw data

Stages run in order:
  1. ingest    — download RPW xlsx + BRM JSON to data/raw/
  2. preprocess — clean parquet to data/processed/
  3. tci       — sanity print of the top-20 corridor TCI ranking
  4. stablecoin — savings model + global aggregate print
  5. aggregate — diaspora burden payload
  6. regression — operator-class two-way FE regression
  7. export     — write corridors.json, meta.json, diaspora_burden.json,
                  operator_regression.json
  8. figures    — render report PNGs to report/figures/
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import (  # noqa: E402  (sys.path tweak)
    aggregate,
    config,
    export,
    figures,
    ingest,
    preprocess,
    regression,
    stablecoin,
    tci,
)

logger = logging.getLogger("run_all")

def _step(label: str) -> None:
    print()
    print("─" * 86)
    print(f"  ▸ {label}")
    print("─" * 86)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MigrantMoney end-to-end pipeline.")
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Re-use the existing files in data/raw/ instead of re-downloading.",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="Skip Plotly+kaleido figure rendering (used by the CI cron, where Chrome is not installed).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    t0 = time.time()
    config.ensure_dirs()


    _step("1/7 ingest — RPW xlsx + Bilateral Remittance Matrix")
    if not args.skip_download:
        ingest.download_rpw()
        ingest.download_bilateral_remittances()
    else:
        logger.info("skip-download set — using cached raw data")


    _step("2/7 preprocess — schema sniff, melt cc1/cc2, derive fee/speed/TCI")
    df = preprocess.preprocess()
    df.to_parquet(config.PROCESSED_RPW_PATH, index=False)
    preprocess.print_summary(df)


    _step("3/7 tci — top-20 corridor ranking")
    panel = tci.corridor_period_tci(df)
    snap = tci.latest_corridor_snapshot(panel)
    tci.print_top_n(snap, send_amount_usd=int(config.HEADLINE_SEND_AMOUNT_USD), n=20)


    _step("4/7 stablecoin — counterfactual cost model + savings")
    savings, _ = stablecoin.compute()
    stablecoin.print_summary(savings)


    _step("5/7 aggregate — diaspora burden + global rankings")
    burden_payload = aggregate.build_payload(savings)
    aggregate.print_summary(burden_payload)


    _step("6/7 regression — operator-class two-way FE")
    reg_results = regression.fit_all()
    regression.print_summary(reg_results)


    _step("7/8 export — write corridors.json + meta.json + burden + regression")
    providers = tci.latest_provider_breakdown(df)
    summary_dict = stablecoin.global_savings_summary(savings)
    corridors = export.build_corridor_payloads(panel, providers, savings=savings)
    meta = export.build_meta(df, savings_summary=summary_dict)
    export.write_corridors_json(corridors, meta)
    export.write_meta_json(meta)
    aggregate.write_json(burden_payload)
    regression.write_regression_json(reg_results)


    if args.skip_figures:
        _step("8/8 figures — skipped (--skip-figures)")
    else:
        _step("8/8 figures — render report PNGs to report/figures/")
        figures.fig_top20_corridors(snap, config.FIGURES_DIR / "fig01_top20_corridors.png")
        figures.fig_world_map(burden_payload["senders"], config.FIGURES_DIR / "fig02_world_map.png")
        figures.fig_operator_forest(reg_results, config.FIGURES_DIR / "fig03_operator_forest.png")
        figures.fig_savings_scatter(savings, config.FIGURES_DIR / "fig04_stablecoin_scatter.png")
        figures.fig_diaspora_burden(burden_payload["senders"], config.FIGURES_DIR / "fig05_diaspora_burden.png")

    elapsed = time.time() - t0
    print()
    print("=" * 86)
    print(f"  Pipeline complete in {elapsed:.1f} s. Outputs in data/outputs/ + report/figures/.")
    print("=" * 86)
    return 0

if __name__ == "__main__":
    sys.exit(main())
