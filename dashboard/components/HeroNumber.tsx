"use client";

import {
  motion,
  useMotionValue,
  useReducedMotion,
  useTransform,
  animate,
} from "framer-motion";
import { useEffect } from "react";
import { heroParts } from "@/lib/format";

interface HeroNumberProps {
  /** Final value, in raw USD. e.g. 24_210_000_000 */
  value: number;
  /** Override the displayed unit (B / M / K). Auto-derived if omitted. */
  unit?: "B" | "M" | "K";
  /** Animation duration ms. */
  duration?: number;
}

export function HeroNumber({ value, unit, duration = 1200 }: HeroNumberProps) {
  const reduce = useReducedMotion();
  const target = unit
    ? unit === "B"
      ? value / 1e9
      : unit === "M"
      ? value / 1e6
      : value / 1e3
    : Number(heroParts(value).lead);
  const finalUnit = unit ?? heroParts(value).unit;

  const mv = useMotionValue(reduce ? target : 0);
  const display = useTransform(mv, (v) => v.toFixed(1));

  useEffect(() => {
    if (reduce) return;
    const ctl = animate(mv, target, {
      duration: duration / 1000,
      ease: [0.16, 1, 0.3, 1], // easeOutExpo-ish
    });
    return () => ctl.stop();
  }, [mv, target, duration, reduce]);

  // Hero numbers use Fraunces with high optical size + tabular figures.
  // Force opsz=144 inline so the number reads as the display variant of the
  // axis even though we may be at a smaller px size on mobile.
  return (
    <span
      className="leading-[0.92] tracking-[-0.04em] inline-block"
      style={{
        fontFamily: "var(--font-fraunces), serif",
        fontVariationSettings: "'opsz' 144, 'SOFT' 100, 'WONK' 0",
        fontVariantNumeric: "tabular-nums lining-nums",
      }}
    >
      <span aria-hidden>
        $<motion.span>{display}</motion.span>
        <span>{finalUnit}</span>
      </span>
      <span className="sr-only">${target.toFixed(1)} {finalUnit}</span>
    </span>
  );
}
