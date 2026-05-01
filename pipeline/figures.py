"""Static figures for the report — Phase 5.

Generates five PNGs at 300 DPI into report/figures/, all on the dark
editorial palette defined in pipeline.config (Bloomberg-Terminal-meets-
premium-fintech, no gradients, no emojis).

Figures:
  1. fig01_top20_corridors.png    — stacked bar of fee | FX margin | speed
                                    penalty for the 20 most expensive corridors
  2. fig02_world_map.png          — choropleth of annual fee burden by sender
  3. fig03_operator_forest.png    — regression forest plot vs MTO reference
  4. fig04_stablecoin_scatter.png — corridor volume × savings rate
  5. fig05_diaspora_burden.png    — top-10 sender bar chart

Run as a module:
    uv run python -m pipeline.figures
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pipeline import aggregate, config, regression, stablecoin, tci

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

# 300 DPI export — Plotly+Kaleido takes pixels, not inches. Render at 2x and
# scale via the `scale` arg so axis fonts stay crisp.
PNG_WIDTH = 1600
PNG_HEIGHT = 1000
PNG_SCALE = 2  # ⇒ effective 3200 × 2000 ≈ 300 DPI for ~10in wide print

FONT_SERIF = "Source Serif 4, Newsreader, Georgia, serif"
FONT_SANS = "Inter, Helvetica Neue, Arial, sans-serif"
FONT_MONO = "JetBrains Mono, IBM Plex Mono, ui-monospace, monospace"

# Component palette: fee = amber, fx = darker amber, speed = neutral grey.
COLOR_FEE = config.COLOR_ACCENT_POSITIVE  # #D97706
COLOR_FX = "#9C5409"  # darker shade of amber
COLOR_SPEED = "#3F3F3F"  # near-neutral grey
COLOR_NEG = config.COLOR_ACCENT_NEGATIVE  # #B91C1C
COLOR_AXIS = config.COLOR_TEXT_MUTED  # #A8A29E
COLOR_GRID = "#1F1F1F"


def _layout(
    title: str,
    subtitle: str | None = None,
    xaxis_title: str | None = None,
    yaxis_title: str | None = None,
    height: int = PNG_HEIGHT,
    margin_l: int = 220,
    margin_r: int = 80,
    margin_t: int = 130,
    margin_b: int = 80,
) -> dict[str, Any]:
    """Shared dark editorial layout. Title in serif, axes in sans, numbers in mono."""
    title_text = (
        f"<span style='font-family:{FONT_SERIF};font-size:30px;color:"
        f"{config.COLOR_TEXT}'>{title}</span>"
    )
    if subtitle:
        title_text += (
            f"<br><span style='font-family:{FONT_SANS};font-size:14px;color:"
            f"{COLOR_AXIS}'>{subtitle}</span>"
        )
    return dict(
        paper_bgcolor=config.COLOR_BG,
        plot_bgcolor=config.COLOR_BG,
        font=dict(family=FONT_SANS, size=13, color=config.COLOR_TEXT),
        title=dict(text=title_text, x=0.04, xanchor="left", y=0.96, yanchor="top"),
        xaxis=dict(
            title=dict(
                text=xaxis_title or "",
                font=dict(family=FONT_SANS, size=13, color=COLOR_AXIS),
                standoff=10,
            ),
            tickfont=dict(family=FONT_MONO, size=12, color=COLOR_AXIS),
            gridcolor=COLOR_GRID,
            zerolinecolor=COLOR_GRID,
            linecolor=COLOR_GRID,
            ticks="outside",
            tickcolor=COLOR_GRID,
        ),
        yaxis=dict(
            title=dict(
                text=yaxis_title or "",
                font=dict(family=FONT_SANS, size=13, color=COLOR_AXIS),
                standoff=10,
            ),
            tickfont=dict(family=FONT_SANS, size=12, color=config.COLOR_TEXT),
            gridcolor=COLOR_GRID,
            zerolinecolor=COLOR_GRID,
            linecolor=COLOR_GRID,
            ticks="outside",
            tickcolor=COLOR_GRID,
        ),
        height=height,
        margin=dict(l=margin_l, r=margin_r, t=margin_t, b=margin_b),
        showlegend=False,
    )


def _save(fig: go.Figure, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(
        out_path,
        width=PNG_WIDTH,
        height=fig.layout.height or PNG_HEIGHT,
        scale=PNG_SCALE,
    )
    logger.info("wrote %s (%.0f KB)", out_path, out_path.stat().st_size / 1024)


# ---------------------------------------------------------------------------
# Fig 1: Top 20 corridors — stacked TCI bar
# ---------------------------------------------------------------------------


def fig_top20_corridors(snapshot: pd.DataFrame, out: Path) -> None:
    head = int(config.HEADLINE_SEND_AMOUNT_USD)
    sub = snapshot[snapshot["send_amount_bucket_usd"] == head].copy()
    sub = sub[sub["n_providers"] >= 3]
    top = sub.sort_values("tci_pct_mean", ascending=False).head(20).iloc[::-1]

    labels = [
        f"{r.source_name} → {r.destination_name}" for r in top.itertuples(index=False)
    ]
    fee = top["fee_pct_mean"].astype(float).values
    fx = top["fx_margin_pct_mean"].astype(float).values
    spd = top["speed_penalty_pct_mean"].astype(float).values

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=fee, name="Fee",
        marker_color=COLOR_FEE, marker_line_width=0,
        orientation="h",
        hovertemplate="<b>%{y}</b><br>Fee: %{x:.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=labels, x=fx, name="FX margin",
        marker_color=COLOR_FX, marker_line_width=0,
        orientation="h",
        hovertemplate="<b>%{y}</b><br>FX margin: %{x:.2f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=labels, x=spd, name="Speed penalty",
        marker_color=COLOR_SPEED, marker_line_width=0,
        orientation="h",
        hovertemplate="<b>%{y}</b><br>Speed penalty: %{x:.2f}%<extra></extra>",
    ))

    # TCI total annotations to the right of each bar
    totals = fee + fx + spd
    annotations = [
        dict(
            x=t + 1.0,
            y=lbl,
            text=f"{t:>5.1f}%",
            showarrow=False,
            xanchor="left",
            font=dict(family=FONT_MONO, size=12, color=config.COLOR_TEXT),
        )
        for lbl, t in zip(labels, totals)
    ]

    layout = _layout(
        title="The 20 most expensive remittance corridors",
        subtitle="True Cost Index — fee + FX margin + speed penalty   |   "
                 "USD 200 send, 2025 Q1, ≥3 providers per corridor",
        xaxis_title="True Cost Index, % of send amount",
        yaxis_title=None,
        margin_l=300,
        margin_r=140,
    )
    layout["barmode"] = "stack"
    layout["showlegend"] = True
    layout["legend"] = dict(
        orientation="h",
        x=0.04, y=-0.08,
        font=dict(family=FONT_SANS, size=12, color=COLOR_AXIS),
        bgcolor="rgba(0,0,0,0)",
    )
    layout["annotations"] = annotations
    layout["xaxis"]["range"] = [0, max(totals) * 1.15]
    fig.update_layout(**layout)
    _save(fig, out)


# ---------------------------------------------------------------------------
# Fig 2: World choropleth — fee burden by sender
# ---------------------------------------------------------------------------


def fig_world_map(senders: list[dict], out: Path) -> None:
    """Annual fee burden by sending country (USD billions)."""
    rows = [
        {
            "iso3": s["source_code"],
            "burden_b": (s["fee_burden_usd_annual"] or 0) / 1e9,
            "name": s["source_name"] or s["source_code"],
            "tci": s.get("tci_volume_weighted_pct"),
            "vol_b": (s["volume_usd_annual"] or 0) / 1e9,
        }
        for s in senders
    ]
    df = pd.DataFrame(rows)
    df = df[df["burden_b"] > 0]

    # Custom amber colorscale on a dark base.
    scale = [
        [0.0, "#1F1F1F"],
        [0.05, "#3D2A12"],
        [0.30, "#7A4F1A"],
        [0.60, "#B85F0A"],
        [1.0, COLOR_FEE],
    ]

    fig = go.Figure(go.Choropleth(
        locations=df["iso3"],
        z=df["burden_b"],
        text=df.apply(
            lambda r: f"<b>{r['name']}</b><br>"
                      f"Fee burden: USD {r['burden_b']:.2f} B/yr<br>"
                      f"Volume: USD {r['vol_b']:.1f} B/yr<br>"
                      f"Weighted TCI: {r['tci']:.2f}%",
            axis=1,
        ),
        hoverinfo="text",
        colorscale=scale,
        zmin=0,
        zmax=max(df["burden_b"].max(), 1.0),
        marker_line_color="#0A0A0A",
        marker_line_width=0.5,
        colorbar=dict(
            title=dict(
                text="USD B / yr",
                font=dict(family=FONT_SANS, size=12, color=COLOR_AXIS),
                side="right",
            ),
            tickfont=dict(family=FONT_MONO, size=11, color=COLOR_AXIS),
            outlinewidth=0,
            thickness=14,
            len=0.6,
            x=0.96,
        ),
    ))

    fig.update_geos(
        projection_type="natural earth",
        showcoastlines=False,
        showland=True,
        landcolor="#111111",
        showocean=True,
        oceancolor=config.COLOR_BG,
        showframe=False,
        bgcolor=config.COLOR_BG,
        showcountries=True,
        countrycolor="#1F1F1F",
        countrywidth=0.5,
    )

    layout = _layout(
        title="Where migrants pay the most",
        subtitle="Annual fee burden by sending country, USD billions   |   "
                 "RPW 2025 Q1 × KNOMAD bilateral volumes 2021",
        height=900,
        margin_l=20, margin_r=20, margin_b=20,
    )
    layout.pop("xaxis", None)
    layout.pop("yaxis", None)
    fig.update_layout(**layout)
    _save(fig, out)


# ---------------------------------------------------------------------------
# Fig 3: Operator-class regression forest plot
# ---------------------------------------------------------------------------


def fig_operator_forest(reg_models: dict[int, regression.RegressionResult], out: Path) -> None:
    head = int(config.HEADLINE_SEND_AMOUNT_USD)
    res = reg_models[head]
    coefs = list(reversed(res.coefficients))  # plot top-to-bottom

    labels = [c.firm_type for c in coefs]
    est = [c.estimate_pct for c in coefs]
    lo = [c.ci_low_pct for c in coefs]
    hi = [c.ci_high_pct for c in coefs]
    sig = [c.significance for c in coefs]
    n = [c.n_observations_class for c in coefs]

    err_minus = [e - l for e, l in zip(est, lo)]
    err_plus = [h - e for e, h in zip(hi, est)]

    point_colors = [
        COLOR_NEG if e > 0 else COLOR_FEE for e in est
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=est,
        y=labels,
        error_x=dict(
            type="data",
            symmetric=False,
            array=err_plus,
            arrayminus=err_minus,
            color=COLOR_AXIS,
            thickness=1.5,
            width=8,
        ),
        mode="markers",
        marker=dict(size=12, color=point_colors, line=dict(width=0)),
        hovertemplate=(
            "<b>%{y}</b><br>β = %{x:+.3f} pp<br>"
            "<extra></extra>"
        ),
    ))

    fig.add_vline(
        x=0,
        line=dict(color=COLOR_AXIS, dash="dot", width=1),
    )

    annotations = []
    for label, e, h, s, ni in zip(labels, est, hi, sig, n):
        annotations.append(dict(
            x=h + 0.5,
            y=label,
            text=f"{e:+.2f} pp {s}   n={ni:,}",
            showarrow=False,
            xanchor="left",
            font=dict(family=FONT_MONO, size=12, color=config.COLOR_TEXT),
        ))

    layout = _layout(
        title="Banks charge more, mobile money charges less",
        subtitle=(
            "Δ TCI vs MTO (reference) — two-way FE (corridor + quarter), "
            "cluster-robust SEs at corridor   |   USD 200, "
            f"N = {res.n_observations:,}"
        ),
        xaxis_title="Coefficient — Δ TCI vs MTO, percentage points  (95% CI)",
        yaxis_title=None,
        margin_l=180,
        margin_r=300,
        height=600,
    )
    rng_lo = min(lo + [0]) - 1.5
    rng_hi = max(hi + [0]) + 6.0  # leave room for annotation on the right
    layout["xaxis"]["range"] = [rng_lo, rng_hi]
    layout["annotations"] = annotations
    fig.update_layout(**layout)
    _save(fig, out)


# ---------------------------------------------------------------------------
# Fig 4: Stablecoin savings scatter
# ---------------------------------------------------------------------------


def fig_savings_scatter(savings: pd.DataFrame, out: Path) -> None:
    head = int(config.HEADLINE_SEND_AMOUNT_USD)
    sub = savings[
        (savings["send_amount_usd"] == head)
        & savings["volume_usd_annual"].notna()
        & (savings["volume_usd_annual"] > 0)
    ].copy()
    sub = sub.sort_values("savings_usd_annual", ascending=False)

    sub["volume_b"] = sub["volume_usd_annual"] / 1e9
    sub["savings_m"] = sub["savings_usd_annual"] / 1e6

    point_size = np.clip(sub["savings_m"].fillna(0) / 8.0, 4, 40)

    # Highlight top 10 with labels
    top10 = sub.head(10)

    fig = go.Figure()

    # Background scatter — every corridor as an unlabeled dot.
    fig.add_trace(go.Scatter(
        x=sub["volume_b"],
        y=sub["savings_pct"],
        mode="markers",
        marker=dict(
            size=point_size,
            color=COLOR_FEE,
            opacity=0.55,
            line=dict(color=config.COLOR_BG, width=0.5),
        ),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Volume: USD %{x:.2f} B/yr<br>"
            "Savings: %{y:.2f}% (~USD %{customdata[1]:.0f} M/yr)"
            "<extra></extra>"
        ),
        customdata=np.column_stack([
            sub["source_name"].astype(str) + " → " + sub["destination_name"].astype(str),
            sub["savings_m"].fillna(0),
        ]),
    ))

    # Foreground trace: top-10 by absolute savings, marker + label above the dot.
    top10_size = np.clip(top10["savings_m"].fillna(0) / 8.0, 8, 50)
    fig.add_trace(go.Scatter(
        x=top10["volume_b"],
        y=top10["savings_pct"],
        mode="markers+text",
        marker=dict(
            size=top10_size,
            color=COLOR_FEE,
            opacity=0.85,
            line=dict(color=config.COLOR_BG, width=1.2),
        ),
        text=top10["corridor_id"].astype(str),
        textposition="top center",
        textfont=dict(family=FONT_MONO, size=14, color=config.COLOR_TEXT),
        cliponaxis=False,
        hoverinfo="skip",
    ))

    layout = _layout(
        title="Stablecoin savings — volume × rate, top corridors labelled",
        subtitle=(
            "Each dot is one corridor. Bubble size ∝ absolute USD savings. "
            "Conservative SC defaults — see /methodology."
        ),
        xaxis_title="Annual corridor volume — USD billions (log)",
        yaxis_title="Savings rate — TCI − stablecoin cost, percentage points",
        margin_l=120,
        margin_r=80,
        height=820,
    )
    layout["xaxis"]["type"] = "log"
    layout["xaxis"]["range"] = [-2.2, 2.1]
    fig.update_layout(**layout)
    _save(fig, out)


# ---------------------------------------------------------------------------
# Fig 5: Diaspora burden — top 10 senders
# ---------------------------------------------------------------------------


def fig_diaspora_burden(senders: list[dict], out: Path) -> None:
    df = pd.DataFrame(senders).sort_values("fee_burden_usd_annual", ascending=False).head(10)
    df = df.iloc[::-1]  # plotly horizontal bars draw bottom-to-top
    burden_b = df["fee_burden_usd_annual"].astype(float) / 1e9
    savings_b = df["sc_savings_usd_annual"].astype(float) / 1e9
    labels = df["source_name"].astype(str).tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels,
        x=burden_b,
        name="Fee burden",
        marker_color=COLOR_FEE,
        marker_line_width=0,
        orientation="h",
        hovertemplate=(
            "<b>%{y}</b><br>Fee burden: USD %{x:.2f} B/yr<extra></extra>"
        ),
    ))
    fig.add_trace(go.Bar(
        y=labels,
        x=savings_b,
        name="of which: SC counterfactual savings",
        marker_color=COLOR_SPEED,
        marker_line_width=0,
        orientation="h",
        hovertemplate=(
            "<b>%{y}</b><br>SC savings: USD %{x:.2f} B/yr<extra></extra>"
        ),
    ))

    # Annotations: use a Unicode "small dollar" + non-breaking spaces to
    # avoid Plotly interpreting plain `$...$` as inline TeX math.
    annotations = []
    for lbl, b, s in zip(labels, burden_b, savings_b):
        annotations.append(dict(
            x=b + 0.15,
            y=lbl,
            text=f"USD {b:>5.2f} B   (SC USD {s:.2f} B)",
            showarrow=False,
            xanchor="left",
            font=dict(family=FONT_MONO, size=12, color=config.COLOR_TEXT),
        ))

    layout = _layout(
        title="The hidden tax — top 10 sending countries by fee burden",
        subtitle="Annual fee burden = volume-weighted TCI × bilateral volume   |   "
                 "USD 200 bucket, RPW 2025 Q1 × KNOMAD 2021",
        xaxis_title="Fee burden — USD billions / year",
        yaxis_title=None,
        margin_l=240,
        margin_r=200,
        height=620,
    )
    layout["barmode"] = "overlay"
    layout["showlegend"] = True
    layout["legend"] = dict(
        orientation="h",
        x=0.04, y=-0.12,
        font=dict(family=FONT_SANS, size=12, color=COLOR_AXIS),
        bgcolor="rgba(0,0,0,0)",
    )
    layout["annotations"] = annotations
    layout["xaxis"]["range"] = [0, max(burden_b) * 1.35]
    fig.update_layout(**layout)
    _save(fig, out)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def render_all(out_dir: Path = config.FIGURES_DIR) -> None:
    config.ensure_dirs()

    df = pd.read_parquet(config.PROCESSED_RPW_PATH)

    # Phase 2 inputs
    panel = tci.corridor_period_tci(df)
    snap = tci.latest_corridor_snapshot(panel)

    # Phase 3 inputs
    savings, _ = stablecoin.compute()

    # Phase 4 inputs
    burden_payload = aggregate.build_payload(savings)
    senders = burden_payload["senders"]
    reg_models = regression.fit_all()

    # Render
    fig_top20_corridors(snap, out_dir / "fig01_top20_corridors.png")
    fig_world_map(senders, out_dir / "fig02_world_map.png")
    fig_operator_forest(reg_models, out_dir / "fig03_operator_forest.png")
    fig_savings_scatter(savings, out_dir / "fig04_stablecoin_scatter.png")
    fig_diaspora_burden(senders, out_dir / "fig05_diaspora_burden.png")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render report figures.")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    render_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
