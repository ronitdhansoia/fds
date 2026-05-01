# MigrantMoney

A True Cost Index for cross-border remittances, plus a stablecoin counterfactual that estimates how much migrants could keep if the same flows ran on USDC or USDT rails.

When you wire $200 home, the fee on the receipt is rarely what it actually cost. There is also an FX margin (the gap between the rate you are shown and the interbank mid) and a speed penalty (the cost to whoever is on the receiving end of waiting two or three working days for the money to land). Public reporting from the World Bank treats fee and FX margin as separate columns, and ignores speed entirely. This project rolls the three together into one number per corridor, per provider, per quarter, and then asks: what would the same flow look like if it ran on a stablecoin?

Built as the term project for *Fundamentals of Data Science* at BITS Pilani Dubai (final-year, Spring 2026). Submitted 22 May 2026.

---

## Headline findings

Numbers below are computed from 36 quarters of World Bank Remittance Prices Worldwide (RPW) data, 2016 Q2 through 2025 Q1, on a USD 200 send amount.

- **368 corridors, 694 providers, 391,797 rows** in the panel.
- **USD 484 billion** of corridor volume in scope (WB/KNOMAD 2021 bilateral matrix).
- **USD 5.22 billion per year** is the conservative estimate of recoverable cost on a stablecoin counterfactual. The 4-quarter rolling figure is USD 5.70 billion.
- **200 of 349** corridors with volume data show positive savings under the model. The remaining 149 already run cheap enough that even a generous stablecoin estimate cannot beat them (US to Mexico is the obvious one, where competitive MTOs keep total cost near 4%).
- The most expensive corridors cluster in Sub-Saharan Africa and the small-island Pacific. The cheapest are South Asia and high-volume Latin America.
- The operator-class regression (two-way FE, clustered SE) puts banks 4 to 5 percentage points above MTOs after controlling for corridor and quarter. Mobile-money operators come in below MTOs by about 1.5 points, which fits the reputation but is the first time I have seen it priced against the panel.

The full ranking, the per-corridor breakdown, the regression table, and a sensitivity slider on every constant are in the dashboard. The 16-page report under `report/` is the writeup.

---

## What is in the repo

```
migrantmoney/
  pipeline/      Python: ingest, preprocess, TCI, stablecoin, regression, aggregate, export, figures
  data/
    raw/         RPW xlsx + KNOMAD JSON (gitignored, fetched by the pipeline)
    processed/   cleaned parquet (gitignored)
    outputs/     JSON consumed by the dashboard
  dashboard/     Next.js 16 + Tailwind v4 + d3-geo (static export)
  report/        figures, tables, the writeup (PDF + tex source)
  scripts/
    run_all.py   one command to regenerate every output
  notebooks/
    01_exploration.ipynb   sanity checks, missingness heatmaps, fee distributions
```

Outputs are pre-computed JSON. The dashboard does not run Python at request time, there is no database, and there is no API. The whole thing deploys as a static bundle.

---

## Prerequisites

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/) for dependency management. A plain `pip install -e .` flow works too if you would rather.
- Node 20 or newer with `pnpm`
- A LaTeX setup if you want to rebuild the report PDF. Either `tectonic` or `pdflatex` works. Optional.

---

## Quick start

```bash
# 1. Pipeline dependencies
uv sync

# 2. Regenerate every output from raw RPW
uv run python scripts/run_all.py

# 3. Dashboard
cd dashboard
pnpm install
pnpm dev   # http://localhost:3000
```

`scripts/run_all.py` is the orchestrator. It downloads the RPW workbook if it is not already in `data/raw/`, normalizes the columns, runs all five computation stages, exports JSON, and then renders the static report figures. End to end it takes about 90 seconds on a 2024 MacBook.

The dashboard reads JSON from `dashboard/public/data/`, which is a copy of `data/outputs/`. A small build hook keeps the two in sync; if you regenerate by hand, run `cp -R data/outputs/* dashboard/public/data/` before `pnpm build`.

---

## Methodology

Every formula and every constant is also exposed on the `/methodology` page of the dashboard, which is the canonical reference. The short version follows.

### True Cost Index

For send amount A, corridor (s to d), provider p, quarter q:

```
TCI = fee_pct + fx_margin_pct + speed_penalty
speed_penalty = kappa * max(0, days_to_arrive - 1)
```

`fee_pct` and `fx_margin_pct` come straight from the RPW columns (`fee_pct` is derived as `total_cost_pct - fx_margin_pct`, clipped at zero). `days_to_arrive` is mapped from the RPW `transfer speed actual` field: under one hour and same day round to 0, next day to 1, two days to 2, three to five days to 4. `kappa` defaults to 0.10 (percentage points per day past same-day), calibrated against short-term cost of capital for the receiving household. It is a sensitivity slider on the dashboard, so you can verify the corridor ranking is largely insensitive over the plausible range.

Corridor-level TCI is the unweighted mean across providers, with the median reported alongside as a robustness check. RPW does not publish provider-level market shares in the public release (verified 2026-04-30), so weighting by share would require private data.

### Stablecoin counterfactual

```
SC_cost_pct = on_ramp(s) + off_ramp(d) + (gas_usd / A * 100) + local_fx_spread(d)
savings_pct = max(0, TCI - SC_cost_pct)
savings_usd_annual = savings_pct/100 * 2021_corridor_volume_usd
```

Defaults are deliberately conservative. Every value lives in `pipeline/config.py` and is editable from the dashboard sliders.

| Component | Value | Rationale |
|---|---|---|
| `on_ramp` developed | 1.0% | US, EU, UK on Coinbase, Kraken, Bitstamp |
| `on_ramp` default | 1.5% | Mid-tier exchange or regulated fintech |
| `on_ramp` low-banked | 2.5% | GCC corridors, OTC desks |
| `off_ramp` top P2P | 1.0% | India, Mexico, Nigeria, Philippines |
| `off_ramp` default | 2.5% | Median liquidity |
| `off_ramp` thin liquidity | 4.0% | Sanctioned and FX-restricted markets |
| `gas_usd` | $0.50 | Tron USDT, Solana, or an L2 |
| `fx_spread` deep | 0.5% | Markets with active stablecoin to local pairs |
| `fx_spread` default | 1.5% | Implied parallel-market premium |

Annual corridor volume is the WB/KNOMAD 2021 bilateral remittance estimate, the latest year published. Corridors absent from the matrix contribute to percentage savings only and are excluded from the USD totals.

### Operator-class regression

Two-way fixed-effects panel on per-provider TCI:

```
TCI_ipq = beta_0 + sum_k beta_k * 1{firm_type = k} + alpha_corridor + gamma_quarter + epsilon
```

- Entity FE: corridor (368 levels)
- Time FE: quarter (36 levels)
- Reference category: MTO
- Standard errors clustered by corridor

Implemented with `linearmodels.PanelOLS`. The forest plot in `report/figures/fig03_operator_forest.png` reports each operator class with 95% CI.

---

## Outputs

`data/outputs/` contains:

- **`corridors.json`**: corridor-level TCI (current quarter, 4-quarter rolling, full quarterly history), per-provider list, stablecoin breakdown, savings.
- **`operator_regression.json`**: regression coefficients, standard errors, p-values, sample size, R-squared.
- **`diaspora_burden.json`**: aggregated annual fee burden by sending country, ranked.
- **`extreme_corridor_robustness.json`**: stress test that drops the top and bottom 5% of provider observations per corridor and re-aggregates.
- **`meta.json`**: generation timestamp, panel dates, every stablecoin default, source citations, retrieval dates.

These are the contract between the pipeline and the dashboard. TypeScript schemas are in `dashboard/lib/data.ts`; if you add a column to the JSON, the typecheck will tell you what to update.

---

## The dashboard

Three pages, dark editorial theme:

- **Landing (`/`)**: world map of sending-country annual cost burden, top-10 most expensive corridors, top-10 highest stablecoin savings. The `kappa` and stablecoin defaults are sliders, so the headline numbers re-aggregate live.
- **Corridor explorer (`/corridor/[id]`)**: pick a country pair and an amount; see the TCI breakdown stacked by component, the provider ranking, and the side-by-side stablecoin comparison.
- **Methodology (`/methodology`)**: every formula, every default, every limitation. The point of this page is that anyone skeptical of the savings number can read it and reproduce it.

`pnpm build` produces a fully static export. There is no API and no database, so deploying is one `vercel deploy` away.

---

## Reproducing against a fresher RPW release

1. Drop the new xlsx in `data/raw/rpw_latest.xlsx`. The download URL is documented in `pipeline/ingest.py` with a retrieval date.
2. Run `uv run python scripts/run_all.py`. The schema sniffer in `pipeline/preprocess.py` handles renamed columns; if a column is missing entirely, it logs a warning and continues.
3. Sync the dashboard data: `cp -R data/outputs/* dashboard/public/data/`.
4. `pnpm build` from `dashboard/`.

The bilateral remittance matrix is fetched live from the World Bank Data360 API. It is cached in `data/raw/` after the first call.

---

## Limitations

Read these before quoting any number from the project.

1. **Provider weighting is uniform.** RPW does not publish market shares. A bank that handles 20% of a corridor counts as much as a fintech that handles 0.1%. Median TCI is reported alongside the mean as a sanity check, and both are surfaced on the dashboard.
2. **The speed penalty constant is calibrated, not estimated.** `kappa = 0.10%` per day is defensible (it lines up with short-term cost of capital for low-income households) but it is not measured. The slider exists so you can verify the ranking is robust.
3. **Stablecoin off-ramp costs are floor estimates.** Real-world frictions (KYC delays, P2P trade risk, regulatory ambiguity, banking de-risking) are not in the cost number. The savings figure is best read as an upper bound on what is technically recoverable, not a prediction.
4. **2021 bilateral volumes are the latest the World Bank publishes.** Corridor flows have shifted since (war, sanctions, dollar strength). The headline USD figure is anchored to 2021.
5. **No causal claim.** The regression isolates an operator-class effect after fixed effects, but it does not identify entry, exit, or pricing dynamics. A diff-in-diff on fintech entry would be the natural follow-up study.

---

## Data sources

- World Bank Remittance Prices Worldwide. Quarterly panel, dashboard at <https://remittanceprices.worldbank.org/>. Retrieval date 2026-04-30.
- World Bank / KNOMAD Bilateral Remittance Matrix, 2021 release, indicator `WB_KNOMAD_BRE` via the Data360 API.
- ISO-3 country and M49 region codes from the World Bank country lookup table.

Both datasets are public.

---

## References

The full IEEE-style bibliography lives in `report/report.md` and the rendered PDF. Headline references:

- World Bank, *Remittance Prices Worldwide Quarterly* (Issue 53, March 2025).
- UN, *SDG 10.c.1: Remittance costs as a proportion of the amount remitted*.
- Ratha et al., *Migration and Development Brief 40*, World Bank / KNOMAD (December 2024).
- Auer, Frost, and Pastor, *Stablecoins, BIS Bulletin 87* (2024).
- Aldasoro, Frost, and Whitcomb, *Decline in remittance fees: A blockchain effect?*, BIS Working Paper 1185 (2024).

---

## License

MIT. Use the code freely; cite the World Bank for the underlying RPW panel and KNOMAD for the bilateral matrix.
