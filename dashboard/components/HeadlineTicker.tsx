"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

export interface TickerItem {
  /** Region of the source country, uppercased — e.g. "SUB-SAHARAN AFRICA" */
  region: string;
  /** Source country name, uppercased */
  source: string;
  /** Destination country name, uppercased */
  destination: string;
  /** True cost percent for the corridor */
  tci_pct: number;
  /** Annual savings vs stablecoin counterfactual in USD */
  savings_usd: number;
}

interface HeadlineTickerProps {
  items: TickerItem[];
  /** Cycle interval ms. Default 5000. */
  intervalMs?: number;
}

const FADE_MS = 400;

export function HeadlineTicker({ items, intervalMs = 5000 }: HeadlineTickerProps) {
  const reduce = useReducedMotion();
  const [idx, setIdx] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (reduce || paused || items.length <= 1) return;
    const id = setInterval(() => {
      setIdx((i) => (i + 1) % items.length);
    }, intervalMs);
    return () => clearInterval(id);
  }, [reduce, paused, intervalMs, items.length]);

  if (items.length === 0) return null;
  const cur = items[idx];

  return (
    <div
      className="relative h-5 overflow-hidden font-mono text-overline tracking-[0.22em] uppercase select-none"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-live="polite"
      aria-label="Top corridor headlines"
    >
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={idx}
          className="absolute inset-0 flex items-center gap-3 whitespace-nowrap text-text-2"
          initial={reduce ? { opacity: 1 } : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={reduce ? { opacity: 0 } : { opacity: 0 }}
          transition={{ duration: reduce ? 0 : FADE_MS / 1000, ease: [0.16, 1, 0.3, 1] }}
        >
          <span className="text-accent">{cur.region}</span>
          <Sep />
          <span className="text-text-2">
            {cur.source} <span className="text-text-3">→</span> {cur.destination}
          </span>
          <Sep />
          <span className="text-text-2">{cur.tci_pct.toFixed(1)}% true cost</span>
          <Sep />
          <span className="text-accent-2">{formatSavings(cur.savings_usd)} savable</span>
        </motion.span>
      </AnimatePresence>
    </div>
  );
}

function Sep() {
  return <span className="text-text-3" aria-hidden>·</span>;
}

function formatSavings(usd: number): string {
  if (!usd || !Number.isFinite(usd)) return "$0";
  if (usd >= 1e9) return `$${(usd / 1e9).toFixed(usd >= 10e9 ? 0 : 1)} B`;
  if (usd >= 1e6) return `$${(usd / 1e6).toFixed(usd >= 100e6 ? 0 : 1)} M`;
  if (usd >= 1e3) return `$${(usd / 1e3).toFixed(0)} K`;
  return `$${usd.toFixed(0)}`;
}
