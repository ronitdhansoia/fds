# MigrantMoney

The hidden tax on global remittances. A True Cost Index + stablecoin counterfactual,
delivered as a research dashboard.

Built for BITS Pilani Dubai — Fundamentals of Data Science (final-year, 2026).

## What this is

Two headline outputs computed from the World Bank Remittance Prices Worldwide (RPW)
quarterly panel:

1. **True Cost Index (TCI)** — fee + FX margin + speed penalty per corridor × provider.
2. **Stablecoin counterfactual** — corridor-level savings if the same flows ran on
   USDC/USDT rails.

Static dashboard (Next.js) reads pre-computed JSON. Python pipeline does the math.

## How to run

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+, pnpm.

```bash
# 1. Install Python deps
uv sync

# 2. Regenerate all data outputs from raw RPW
uv run python scripts/run_all.py

# 3. Run the dashboard locally
cd dashboard
pnpm install
pnpm dev
```

## Methodology summary

See [`/methodology`](dashboard/app/methodology/page.tsx) on the deployed dashboard
for the formulas, every constant with its source, and an explicit limitations
section. The full specification lives in [`CLAUDE.md`](CLAUDE.md) §5.

## Layout

```
pipeline/    Python — ingest, clean, TCI, stablecoin, regression, export
data/        raw (gitignored), processed parquet, outputs JSON
dashboard/   Next.js 15 + Tailwind v4 + shadcn/ui
report/      figures, tables, write-up
scripts/     run_all.py orchestrator
```
