"use client";

import type { CorridorHistoryPoint } from "@/lib/data";
import { fmtPct, fmtPeriod } from "@/lib/format";
import { useMemo, useState } from "react";

interface HistoryChartProps {
  history: CorridorHistoryPoint[];
}

// Compact line chart of TCI over quarters with hover dot. No grid, no axis
// lines, no Recharts.
interface DefinedPoint {
  period: string | null;
  tci_pct: number;
}

export function HistoryChart({ history }: HistoryChartProps) {
  const data = useMemo<DefinedPoint[]>(
    () =>
      history
        .filter((p): p is CorridorHistoryPoint & { tci_pct: number } => p.tci_pct !== null)
        .map((p) => ({ period: p.period, tci_pct: p.tci_pct })),
    [history],
  );
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (data.length < 2) {
    return null;
  }

  const W = 880;
  const H = 220;
  const padL = 8;
  const padR = 8;
  const padT = 16;
  const padB = 24;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const min = Math.min(...data.map((d) => d.tci_pct));
  const max = Math.max(...data.map((d) => d.tci_pct));
  const yMin = Math.floor((min - 0.5) * 2) / 2;
  const yMax = Math.ceil((max + 0.5) * 2) / 2;
  const range = Math.max(yMax - yMin, 0.001);

  const stepX = innerW / (data.length - 1);
  const xs = data.map((_, i) => padL + i * stepX);
  const ys = data.map((d) => padT + (1 - (d.tci_pct - yMin) / range) * innerH);

  const linePath = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x} ${ys[i]}`).join(" ");

  const ticksY = [yMin, yMin + range / 2, yMax];

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        preserveAspectRatio="none"
        onMouseLeave={() => setHoverIdx(null)}
      >
        {/* Y axis ticks: text only, no line */}
        {ticksY.map((t) => {
          const y = padT + (1 - (t - yMin) / range) * innerH;
          return (
            <g key={t}>
              <line
                x1={padL}
                x2={W - padR}
                y1={y}
                y2={y}
                stroke="var(--color-border)"
                strokeDasharray="2,4"
              />
              <text
                x={W - padR}
                y={y - 4}
                textAnchor="end"
                fontSize={11}
                fill="var(--color-text-3)"
                fontFamily="var(--font-geist-mono)"
              >
                {t.toFixed(1)}%
              </text>
            </g>
          );
        })}

        {/* Line */}
        <path
          d={linePath}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Endpoint dot */}
        <circle
          cx={xs[xs.length - 1]}
          cy={ys[ys.length - 1]}
          r={3}
          fill="var(--color-accent)"
        />
        {/* Endpoint label */}
        <text
          x={xs[xs.length - 1] - 6}
          y={ys[ys.length - 1] - 8}
          textAnchor="end"
          fontSize={11}
          fill="var(--color-text-2)"
          fontFamily="var(--font-geist-mono)"
        >
          {fmtPct(data[data.length - 1].tci_pct, 2)}
        </text>

        {/* Hover layer */}
        {data.map((_, i) => (
          <rect
            key={i}
            x={xs[i] - stepX / 2}
            y={padT}
            width={stepX}
            height={innerH}
            fill="transparent"
            onMouseEnter={() => setHoverIdx(i)}
          />
        ))}
        {hoverIdx !== null ? (
          <g>
            <line
              x1={xs[hoverIdx]}
              x2={xs[hoverIdx]}
              y1={padT}
              y2={H - padB}
              stroke="var(--color-border-hi)"
              strokeWidth={1}
            />
            <circle
              cx={xs[hoverIdx]}
              cy={ys[hoverIdx]}
              r={4}
              fill="var(--color-accent)"
              stroke="var(--color-bg)"
              strokeWidth={1}
            />
          </g>
        ) : null}
      </svg>
      {hoverIdx !== null ? (
        <div
          className="pointer-events-none absolute -translate-x-1/2 rounded-[2px] border border-border-hi bg-surface-2 px-2 py-1 font-mono text-label text-text"
          style={{
            left: `${(xs[hoverIdx] / W) * 100}%`,
            top: -4,
          }}
        >
          <span className="text-text-3 mr-2">{fmtPeriod(data[hoverIdx].period)}</span>
          {fmtPct(data[hoverIdx].tci_pct, 2)}
        </div>
      ) : null}
    </div>
  );
}
