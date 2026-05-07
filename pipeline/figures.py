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







PNG_WIDTH = 1600
PNG_HEIGHT = 1000
PNG_SCALE = 2

FONT_SERIF = "Source Serif 4, Newsreader, Georgia, serif"
FONT_SANS = "Inter, Helvetica Neue, Arial, sans-serif"
FONT_MONO = "JetBrains Mono, IBM Plex Mono, ui-monospace, monospace"


COLOR_FEE = config.COLOR_ACCENT_POSITIVE
COLOR_FX = "#9C5409"
COLOR_SPEED = "#3F3F3F"
COLOR_NEG = config.COLOR_ACCENT_NEGATIVE
COLOR_AXIS = config.COLOR_TEXT_MUTED
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





def fig_operator_forest(reg_models: dict[int, regression.RegressionResult], out: Path) -> None:
    head = int(config.HEADLINE_SEND_AMOUNT_USD)
    res = reg_models[head]
    coefs = list(reversed(res.coefficients))

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
    rng_hi = max(hi + [0]) + 6.0
    layout["xaxis"]["range"] = [rng_lo, rng_hi]
    layout["annotations"] = annotations
    fig.update_layout(**layout)
    _save(fig, out)





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


    top10 = sub.head(10)

    fig = go.Figure()


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





def fig_diaspora_burden(senders: list[dict], out: Path) -> None:
    df = pd.DataFrame(senders).sort_values("fee_burden_usd_annual", ascending=False).head(10)
    df = df.iloc[::-1]
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





def render_all(out_dir: Path = config.FIGURES_DIR) -> None:
    config.ensure_dirs()

    df = pd.read_parquet(config.PROCESSED_RPW_PATH)


    panel = tci.corridor_period_tci(df)
    snap = tci.latest_corridor_snapshot(panel)


    savings, _ = stablecoin.compute()


    burden_payload = aggregate.build_payload(savings)
    senders = burden_payload["senders"]
    reg_models = regression.fit_all()


    fig_top20_corridors(snap, out_dir / "fig01_top20_corridors.png")
    fig_world_map(senders, out_dir / "fig02_world_map.png")
    fig_operator_forest(reg_models, out_dir / "fig03_operator_forest.png")
    fig_savings_scatter(savings, out_dir / "fig04_stablecoin_scatter.png")
    fig_diaspora_burden(senders, out_dir / "fig05_diaspora_burden.png")
    fig_block_diagram(out_dir / "fig06_block_diagram.png")
    make_tci_distribution_figure(snap, out_dir / "tci_distribution.png")






def make_tci_distribution_figure(snapshot: pd.DataFrame, out: Path,
                                  send_amount_usd: int = 200,
                                  sdg_target_pct: float = 3.0,
                                  global_mean_pct: float = 5.00) -> None:
    """Histogram of corridor-level mean TCI at the headline send amount.

    Hairlines mark the SDG 10.c target (3%) and the panel volume-weighted
    global mean (5.00%, computed once from diaspora_burden.json and passed
    in so the figure does not have to re-aggregate volume × TCI here).
    """
    sub = snapshot[snapshot["send_amount_bucket_usd"] == send_amount_usd].copy()
    tcis = sub["tci_pct_mean"].astype(float).dropna()



    cap = 30.0
    over = int((tcis > cap).sum())
    binned = tcis.clip(upper=cap)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=binned,
        xbins=dict(start=0, end=cap, size=cap / 30),
        marker=dict(color=COLOR_FEE, line=dict(width=0)),
        hovertemplate="TCI bucket: %{x:.1f}%<br>n corridors: %{y}<extra></extra>",
    ))


    fig.add_shape(
        type="line", x0=sdg_target_pct, x1=sdg_target_pct, y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color=COLOR_AXIS, width=1.2, dash="dash"),
    )
    fig.add_annotation(
        x=sdg_target_pct, y=1, xref="x", yref="paper",
        text=f"SDG 10.c target<br>{sdg_target_pct:.0f}%",
        showarrow=False, xanchor="left", yanchor="top",
        font=dict(family=FONT_MONO, size=11, color=COLOR_AXIS),
        xshift=6, yshift=-6,
    )
    fig.add_shape(
        type="line", x0=global_mean_pct, x1=global_mean_pct, y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color=config.COLOR_TEXT, width=1.2),
    )
    fig.add_annotation(
        x=global_mean_pct, y=1, xref="x", yref="paper",
        text=f"global mean<br>{global_mean_pct:.2f}%",
        showarrow=False, xanchor="left", yanchor="top",
        font=dict(family=FONT_MONO, size=11, color=config.COLOR_TEXT),
        xshift=6, yshift=-46,
    )

    if over > 0:
        fig.add_annotation(
            x=cap, y=0, xref="x", yref="paper",
            text=f"+ {over} corridors above {int(cap)}%",
            showarrow=False, xanchor="right", yanchor="bottom",
            font=dict(family=FONT_MONO, size=11, color=COLOR_AXIS),
            xshift=-6, yshift=18,
        )

    layout = _layout(
        title="Distribution of corridor-level TCI",
        subtitle=(
            f"USD {send_amount_usd}, 2025 Q1, "
            f"corridor mean across providers ({len(tcis)} corridors)"
        ),
        xaxis_title="True Cost Index, % of send amount",
        yaxis_title="Corridors",
        margin_l=100, margin_r=80,
        height=620,
    )
    layout["xaxis"]["range"] = [0, cap]
    layout["bargap"] = 0.05
    fig.update_layout(**layout)
    _save(fig, out)





def fig_block_diagram(out: Path) -> None:
    """Architecture sketch — boxes-and-arrows of the data flow.

    Drawn directly with Plotly shapes/annotations so it lives in the same
    rendering pipeline as the data figures. Three rows: sources → pipeline
    stages → outputs.
    """
    fig = go.Figure()


    W, H = 1600, 900
    fig.update_layout(
        width=W, height=H,
        paper_bgcolor=config.COLOR_BG,
        plot_bgcolor=config.COLOR_BG,
        xaxis=dict(visible=False, range=[0, 100]),
        yaxis=dict(visible=False, range=[0, 100]),
        margin=dict(l=0, r=0, t=130, b=40),
        title=dict(
            text=(
                f"<span style='font-family:{FONT_SERIF};font-size:30px;color:"
                f"{config.COLOR_TEXT}'>System architecture</span>"
                f"<br><span style='font-family:{FONT_SANS};font-size:14px;color:"
                f"{COLOR_AXIS}'>Data flow from World Bank panels → static JSON → editorial dashboard</span>"
            ),
            x=0.04, xanchor="left", y=0.96, yanchor="top",
        ),
    )

    def box(x, y, w, h, label, sub=None, fill="#161616", border=COLOR_AXIS, label_color=config.COLOR_TEXT, font_size=18):
        fig.add_shape(
            type="rect", x0=x, y0=y, x1=x + w, y1=y + h,
            line=dict(color=border, width=1),
            fillcolor=fill, layer="below",
        )
        cy = y + h * 0.62 if sub else y + h * 0.5
        fig.add_annotation(
            x=x + w/2, y=cy, text=label,
            showarrow=False, xanchor="center", yanchor="middle",
            font=dict(family=FONT_SERIF, size=font_size, color=label_color),
        )
        if sub:
            fig.add_annotation(
                x=x + w/2, y=y + h * 0.30, text=sub,
                showarrow=False, xanchor="center", yanchor="middle",
                font=dict(family=FONT_MONO, size=11, color=COLOR_AXIS),
            )

    def arrow(x0, y0, x1, y1, color=None):
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1,
            arrowcolor=color or COLOR_AXIS, text="",
        )


    box(8, 75, 26, 14, "World Bank RPW", "rpw_dataset_2011_2025_q1.xlsx", fill="#1a1206")
    box(38, 75, 26, 14, "KNOMAD BRE",   "Data360 API · 2021 bilateral",  fill="#1a1206")
    box(68, 75, 24, 14, "WB Country lookup", "M49 + ISO3 + region",      fill="#1a1206")


    box(4,  50, 18, 13, "ingest",      "pipeline/ingest.py")
    box(24, 50, 18, 13, "preprocess",  "schema sniff · cc1/cc2 melt", fill="#211408")
    box(44, 50, 18, 13, "TCI",         "fee + fxMargin + κ·max(0,d-1)", fill="#211408",
        border=COLOR_FEE, label_color=COLOR_FEE)
    box(64, 50, 18, 13, "stablecoin",  "on/off-ramp + gas + fxSpread", fill="#1a2008",
        border="#65A30D", label_color="#65A30D")
    box(84, 50, 14, 13, "regression",  "two-way FE", fill="#211408")

    box(20, 32, 22, 11, "aggregate",   "diaspora burden · rankings", fill="#161616")
    box(50, 32, 22, 11, "export",      "round · null-safe JSON",     fill="#161616")
    box(80, 32, 14, 11, "figures",     "Plotly · 300 DPI",            fill="#161616")


    box(4, 12, 22, 13, "rpw_clean.parquet", "data/processed/", fill="#0d0d0d", font_size=14)
    box(28, 12, 22, 13, "corridors.json",   "5.7 MB · 368 corridors", fill="#0d0d0d", font_size=14)
    box(52, 12, 22, 13, "diaspora_burden.json", "108 KB · senders/receivers", fill="#0d0d0d", font_size=14)
    box(76, 12, 22, 13, "operator_regression.json", "5.9 KB · models", fill="#0d0d0d", font_size=14)


    arrow(21, 75, 13, 63)
    arrow(21, 75, 33, 63)
    arrow(51, 75, 53, 63)
    arrow(51, 75, 73, 63)
    arrow(80, 75, 33, 63)


    for x_start, x_end in [(22, 24), (42, 44), (62, 64), (82, 84)]:
        arrow(x_start, 56.5, x_end, 56.5)


    arrow(33, 50, 33, 25)
    arrow(53, 32, 39, 25)
    arrow(61, 32, 63, 25)
    arrow(91, 32, 87, 25)


    arrow(53, 50, 31, 43)
    arrow(73, 50, 53, 43)
    arrow(73, 50, 61, 43)
    arrow(91, 50, 87, 43)


    box(28, 0, 70, 7, "dashboard/public/data/  ⇒  Next.js · Tailwind v4 · Fraunces · Geist", None,
        fill="#0a0a0a", border=COLOR_FEE, label_color=COLOR_FEE, font_size=14)
    arrow(39, 12, 39, 7)
    arrow(63, 12, 63, 7)
    arrow(87, 12, 87, 7)

    fig.update_layout(showlegend=False)
    _save(fig, out)

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
