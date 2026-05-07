"use client";

import * as Slider from "@radix-ui/react-slider";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useTransform,
  animate,
} from "framer-motion";
import { useEffect, useMemo, useState } from "react";

import { fmtUsdCompact } from "@/lib/format";

export interface SensitivityCorridor {
  id: string;
  tci_pct: number;
  volume_usd_annual: number | null;
}

export interface SensitivityDefaults {

  onramp_pct: number;
  offramp_pct: number;

  gas_usd: number;

  fx_spread_pct: number;

  pipeline_savings_usd: number;
}

interface SensitivitySlidersProps {
  corridors: SensitivityCorridor[];
  defaults: SensitivityDefaults;

  sendAmount: number;
}

const SEND_AMOUNT_DEFAULT = 200;

const PARAM_KEYS = ["onramp", "offramp", "gas", "fx"] as const;
type ParamKey = (typeof PARAM_KEYS)[number];

interface ParamSpec {
  key: ParamKey;
  label: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  decimals: number;
  source: string;
}

const PARAMS: ParamSpec[] = [
  {
    key: "onramp",
    label: "On-ramp cost",
    min: 0,
    max: 5,
    step: 0.1,
    unit: "%",
    decimals: 1,
    source:
      "Default reflects a conservative average across major fintech on-ramps; range covers low-banked to friction-heavy markets.",
  },
  {
    key: "offramp",
    label: "Off-ramp cost",
    min: 0,
    max: 6,
    step: 0.1,
    unit: "%",
    decimals: 1,
    source:
      "Default tracks established stablecoin → cash routes; widen for thin-liquidity or sanctioned receivers.",
  },
  {
    key: "gas",
    label: "Network gas",
    min: 0.1,
    max: 10,
    step: 0.1,
    unit: " USD",
    decimals: 2,
    source:
      "USD per transfer, amortised over the send amount. Default assumes L2 / Solana / Tron USDT settlement.",
  },
  {
    key: "fx",
    label: "Local FX spread",
    min: 0,
    max: 5,
    step: 0.1,
    unit: "%",
    decimals: 1,
    source:
      "Spread between the stablecoin and the receiving country's local currency at off-ramp.",
  },
];

function useUrlSyncedState(defaults: Record<ParamKey, number>) {
  const [state, setState] = useState<Record<ParamKey, number>>(defaults);


  useEffect(() => {
    if (typeof window === "undefined") return;
    const sp = new URLSearchParams(window.location.search);
    const next: Record<ParamKey, number> = { ...defaults };
    let changed = false;
    for (const k of PARAM_KEYS) {
      const v = sp.get(k);
      if (v !== null) {
        const n = Number(v);
        if (Number.isFinite(n)) {
          next[k] = n;
          changed = true;
        }
      }
    }
    if (changed) setState(next);

  }, []);




  useEffect(() => {
    if (typeof window === "undefined") return;
    const id = window.setTimeout(() => {
      const sp = new URLSearchParams(window.location.search);
      let dirty = false;
      for (const k of PARAM_KEYS) {
        const v = state[k];
        const isDefault = Math.abs(v - defaults[k]) < 1e-9;
        const cur = sp.get(k);
        if (isDefault && cur !== null) {
          sp.delete(k);
          dirty = true;
        } else if (!isDefault && cur !== String(v)) {
          sp.set(k, String(v));
          dirty = true;
        }
      }
      if (!dirty) return;
      const qs = sp.toString();
      const next =
        window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash;
      try {
        window.history.replaceState(null, "", next);
      } catch {

      }
    }, 350);
    return () => window.clearTimeout(id);
  }, [state, defaults]);

  return [state, setState] as const;
}

function recompute(
  corridors: SensitivityCorridor[],
  params: Record<ParamKey, number>,
  sendAmount: number,
) {
  const sc = params.onramp + params.offramp + (params.gas / sendAmount) * 100 + params.fx;
  let total = 0;
  let nWithVol = 0;
  let nPositive = 0;
  const savingsPcts: number[] = [];
  for (const c of corridors) {
    if (!c.volume_usd_annual || c.volume_usd_annual <= 0) continue;
    nWithVol += 1;
    const sv = Math.max(0, c.tci_pct - sc);
    if (sv > 0) nPositive += 1;
    total += (sv / 100) * c.volume_usd_annual;
    savingsPcts.push(sv);
  }
  return { total, nWithVol, nPositive, savingsPcts, scCost: sc };
}

export function SensitivitySliders({
  corridors,
  defaults,
  sendAmount = SEND_AMOUNT_DEFAULT,
}: SensitivitySlidersProps) {
  const defaultRecord: Record<ParamKey, number> = {
    onramp: defaults.onramp_pct,
    offramp: defaults.offramp_pct,
    gas: defaults.gas_usd,
    fx: defaults.fx_spread_pct,
  };
  const [params, setParams] = useUrlSyncedState(defaultRecord);

  const baseline = useMemo(
    () => recompute(corridors, defaultRecord, sendAmount),

    [corridors, sendAmount],
  );
  const live = useMemo(
    () => recompute(corridors, params, sendAmount),
    [corridors, params, sendAmount],
  );





  useEffect(() => {
    const pipelineSavings = defaults.pipeline_savings_usd;
    if (!pipelineSavings) return;
    const gapPct = Math.abs(baseline.total - pipelineSavings) / pipelineSavings;
    if (gapPct > 0.001 && process.env.NODE_ENV === "development") {



      console.debug(
        `[SensitivitySliders] flat defaults give $${(baseline.total / 1e9).toFixed(2)}B vs ` +
          `pipeline-precise $${(pipelineSavings / 1e9).toFixed(2)}B (gap ${(gapPct * 100).toFixed(1)}%).`,
      );
    }
  }, [baseline.total, defaults.pipeline_savings_usd]);

  const reduce = useReducedMotion();
  const headlineMv = useMotionValue(reduce ? live.total : 0);
  const headlineDisplay = useTransform(headlineMv, (v) => (v / 1e9).toFixed(2));

  useEffect(() => {
    const ctl = animate(headlineMv, live.total, {
      duration: reduce ? 0 : 0.2,
      ease: [0.16, 1, 0.3, 1],
    });
    return () => ctl.stop();
  }, [live.total, headlineMv, reduce]);

  const deltaUsd = live.total - baseline.total;
  const deltaPct = baseline.total === 0 ? 0 : (deltaUsd / baseline.total) * 100;

  const onParamChange = (key: ParamKey, v: number) =>
    setParams((p) => ({ ...p, [key]: v }));

  const reset = () => setParams(defaultRecord);

  const coveragePct = live.nWithVol === 0 ? 0 : (live.nPositive / live.nWithVol) * 100;

  return (
    <div className="grid grid-cols-12 gap-x-6 gap-y-10">
      {}
      <div className="col-span-12 md:col-span-5 space-y-9">
        {PARAMS.map((p) => (
          <ParamSlider
            key={p.key}
            spec={p}
            value={params[p.key]}
            onChange={(v) => onParamChange(p.key, v)}
          />
        ))}

        <button
          onClick={reset}
          className="font-mono text-overline tracking-[0.2em] uppercase text-text-2 transition-colors hover:text-text hover:underline underline-offset-4"
        >
          Reset to defaults
        </button>
      </div>

      {}
      <div className="col-span-12 md:col-span-7 md:pl-8 md:border-l md:border-border space-y-10">
        {}
        <div>
          <div className="overline">Global stablecoin savings · per year</div>
          <div className="mt-3 leading-[0.95]">
            <span
              className="font-display text-text"
              style={{
                fontSize: "clamp(40px, 7.4vw, 72px)",
                fontVariationSettings: "'opsz' 144, 'SOFT' 100, 'WONK' 0",
                fontVariantNumeric: "tabular-nums lining-nums",
                letterSpacing: "-0.04em",
              }}
            >
              $<motion.span>{headlineDisplay}</motion.span>B
            </span>
          </div>
          <div className="mt-3 font-mono text-label text-text-3">
            vs ${(baseline.total / 1e9).toFixed(2)} B at default assumptions
            {Math.abs(deltaPct) >= 0.1 ? (
              <>
                {" · "}
                <span className={deltaUsd > 0 ? "text-accent-2" : "text-accent"}>
                  {deltaUsd > 0 ? "+" : ""}
                  {fmtUsdCompact(deltaUsd)} ({deltaPct > 0 ? "+" : ""}
                  {deltaPct.toFixed(1)}%)
                </span>
              </>
            ) : null}
          </div>
          <div className="mt-2 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
            Pipeline-precise · per-country tiering · ${(defaults.pipeline_savings_usd / 1e9).toFixed(2)} B
          </div>
        </div>

        {}
        <div>
          <div className="overline">Live formula · stablecoin cost</div>
          <div className="mt-3 font-mono text-label leading-[1.85] tabular-nums">
            <div className="text-text-3">
              SC% = onramp + offramp + (gas / A) × 100 + fxSpread
            </div>
            <div className="text-text-2">
              <span className="text-text-3">{"     = "}</span>
              <span className="text-text">{params.onramp.toFixed(2)}%</span>
              <span className="text-text-3"> + </span>
              <span className="text-text">{params.offramp.toFixed(2)}%</span>
              <span className="text-text-3"> + </span>
              <span className="text-text">{((params.gas / sendAmount) * 100).toFixed(2)}%</span>
              <span className="text-text-3"> + </span>
              <span className="text-text">{params.fx.toFixed(2)}%</span>
            </div>
            <div>
              <span className="text-text-3">{"     = "}</span>
              <span className="text-accent-2 font-medium">{live.scCost.toFixed(2)}%</span>
              <span className="text-text-3"> ({(live.scCost * sendAmount / 100).toFixed(2)} on USD {sendAmount})</span>
            </div>
          </div>
        </div>

        {}
        <div>
          <div className="overline">Robustness</div>
          <p className="mt-3 font-display text-body-lg text-text leading-snug pretty">
            Stablecoin beats traditional in{" "}
            <span className="font-mono text-text">{live.nPositive}</span> of{" "}
            <span className="font-mono text-text">{live.nWithVol}</span>{" "}
            corridors{" "}
            <span className="font-mono text-text-2">
              ({coveragePct.toFixed(0)}%)
            </span>
            , even at a flat-cost <span className="font-mono text-text-2">{live.scCost.toFixed(2)}%</span> stablecoin assumption.
          </p>
        </div>

        {}
        <div>
          <div className="overline">Distribution of per-corridor savings</div>
          <div className="mt-3">
            <SavingsHistogram values={live.savingsPcts} maxValue={30} bins={30} />
          </div>
        </div>
      </div>
    </div>
  );
}

function ParamSlider({
  spec,
  value,
  onChange,
}: {
  spec: ParamSpec;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <label className="text-label text-text-2 select-none" style={{ letterSpacing: "-0.011em" }}>
          {spec.label}
        </label>
        <div className="font-mono text-label text-text tabular-nums">
          {value.toFixed(spec.decimals)}
          {spec.unit}
        </div>
      </div>

      <Slider.Root
        className="relative flex h-5 w-full items-center mt-2 select-none touch-none"
        value={[value]}
        min={spec.min}
        max={spec.max}
        step={spec.step}
        onValueChange={(v) => onChange(v[0])}
        aria-label={spec.label}
      >
        <Slider.Track className="relative grow h-[2px] bg-border">
          <Slider.Range className="absolute h-full bg-accent" />
        </Slider.Track>
        <Slider.Thumb
          className="block h-4 w-4 rounded-full bg-text transition-[height,width,transform] hover:h-5 hover:w-5 active:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          aria-label={spec.label}
        />
      </Slider.Root>

      <p className="mt-2 font-mono text-overline tracking-[0.16em] uppercase text-text-3">
        {spec.source}
      </p>
    </div>
  );
}

function SavingsHistogram({
  values,
  maxValue,
  bins,
}: {
  values: number[];
  maxValue: number;
  bins: number;
}) {
  const reduce = useReducedMotion();
  const counts = useMemo(() => {
    const out = new Array<number>(bins).fill(0);
    for (const v of values) {
      const clipped = Math.max(0, Math.min(maxValue, v));
      const idx = Math.min(bins - 1, Math.floor((clipped / maxValue) * bins));
      out[idx] += 1;
    }
    return out;
  }, [values, maxValue, bins]);

  const median = useMemo(() => {
    if (values.length === 0) return 0;
    const sorted = [...values].sort((a, b) => a - b);
    const mid = sorted.length >>> 1;
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }, [values]);

  const maxCount = Math.max(1, ...counts);
  const W = 600;
  const H = 110;
  const gap = 2;
  const barW = (W - gap * (bins - 1)) / bins;

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto"
        preserveAspectRatio="none"
      >
        {counts.map((c, i) => {
          const h = (c / maxCount) * (H - 12);
          const x = i * (barW + gap);
          const y = H - h;
          return (
            <motion.rect
              key={i}
              x={x}
              width={barW}
              fill="var(--color-accent-2)"
              initial={false}
              animate={{ y, height: h }}
              transition={{ duration: reduce ? 0 : 0.15, ease: [0.16, 1, 0.3, 1] }}
            />
          );
        })}
        {}
        {values.length > 0 ? (
          <line
            x1={(median / maxValue) * W}
            x2={(median / maxValue) * W}
            y1={0}
            y2={H}
            stroke="var(--color-text-2)"
            strokeWidth={1}
          />
        ) : null}
      </svg>
      <div className="mt-2 flex items-baseline justify-between font-mono text-overline tracking-[0.16em] uppercase text-text-3">
        <span>0%</span>
        <span>
          Median {median.toFixed(2)}%{" "}
          <span className="text-text-3">·</span>{" "}
          {values.length} corridors
        </span>
        <span>{maxValue}%+</span>
      </div>
    </div>
  );
}
