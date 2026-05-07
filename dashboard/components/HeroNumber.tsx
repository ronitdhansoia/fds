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

  value: number;

  unit?: "B" | "M" | "K";

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
      ease: [0.16, 1, 0.3, 1],
    });
    return () => ctl.stop();
  }, [mv, target, duration, reduce]);




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
