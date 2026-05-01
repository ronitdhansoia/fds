"use client";

import { motion, useReducedMotion } from "framer-motion";

export interface TCIBarProps {
  fee: number;
  fxMargin: number;
  speedPenalty: number;
  /** SC counterfactual TCI shown beneath as a comparison row. */
  scCost?: number;
  /** Domain max — defaults to 1.2× the actual sum so there's headroom. */
  domain?: number;
}

const COLOR_FEE = "#D97706"; // amber
const COLOR_FX = "#A45905";
const COLOR_SPEED = "#3F3F3F";
const COLOR_SC = "#65A30D"; // moss green

export function TCIBar({ fee, fxMargin, speedPenalty, scCost, domain }: TCIBarProps) {
  const total = fee + fxMargin + speedPenalty;
  const dom = domain ?? Math.max(total, scCost ?? 0) * 1.2;
  const reduce = useReducedMotion();
  const t = reduce ? 0 : 0.7;

  return (
    <div className="w-full">
      {/* Traditional row */}
      <Row
        label="TRADITIONAL"
        sub={`${total.toFixed(2)}%`}
        segments={[
          { value: fee, color: COLOR_FEE, label: "Fee" },
          { value: fxMargin, color: COLOR_FX, label: "FX margin" },
          { value: speedPenalty, color: COLOR_SPEED, label: "Speed" },
        ]}
        domain={dom}
        animDur={t}
      />

      {/* Stablecoin row */}
      {typeof scCost === "number" ? (
        <Row
          label="STABLECOIN"
          sub={`${scCost.toFixed(2)}%`}
          segments={[{ value: scCost, color: COLOR_SC, label: "Stablecoin" }]}
          domain={dom}
          animDur={t}
          delay={0.15}
        />
      ) : null}

      {/* Savings annotation */}
      {typeof scCost === "number" ? (
        <div className="mt-3 flex items-center gap-3">
          <div className="rule flex-1" />
          <div className="font-mono text-overline tracking-[0.18em] text-accent-2">
            ↘ {Math.max(0, total - scCost).toFixed(2)} pp savings
          </div>
        </div>
      ) : null}
    </div>
  );
}

interface Segment {
  value: number;
  color: string;
  label: string;
}

function Row({
  label,
  sub,
  segments,
  domain,
  animDur,
  delay = 0,
}: {
  label: string;
  sub: string;
  segments: Segment[];
  domain: number;
  animDur: number;
  delay?: number;
}) {
  const total = segments.reduce((acc, s) => acc + Math.max(0, s.value), 0);
  return (
    <div className="grid grid-cols-[120px_1fr_max-content] items-center gap-4 py-3 border-b border-border last:border-b-0">
      <div className="overline">{label}</div>
      <div className="relative h-8 w-full">
        <div className="absolute inset-0 rounded-[1px] bg-surface" />
        <div className="absolute inset-0 flex overflow-hidden">
          {segments.map((s, i) => {
            const widthPct = (Math.max(0, s.value) / domain) * 100;
            return (
              <motion.div
                key={i}
                initial={{ width: 0 }}
                animate={{ width: `${widthPct}%` }}
                transition={{
                  duration: animDur,
                  ease: [0.16, 1, 0.3, 1],
                  delay: delay + i * 0.06,
                }}
                style={{ background: s.color, flex: "0 0 auto" }}
                className="relative h-full"
              >
                {/* Inline label inside segment if it has room */}
                {widthPct > 12 ? (
                  <span className="absolute inset-y-0 left-2 flex items-center font-mono text-overline tracking-[0.18em] uppercase text-bg/90 whitespace-nowrap">
                    {s.label} · {s.value.toFixed(2)}
                  </span>
                ) : null}
              </motion.div>
            );
          })}
        </div>
      </div>
      <div className="font-mono text-body-lg tabular-nums text-text">{sub}</div>
    </div>
  );
}
