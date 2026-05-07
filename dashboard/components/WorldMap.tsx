"use client";

import { feature } from "topojson-client";
import { geoNaturalEarth1, geoPath, type GeoProjection } from "d3-geo";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { Topology, GeometryCollection } from "topojson-specification";

import { M49_TO_ISO3 } from "@/lib/m49";
import type { SenderRow } from "@/lib/data";
import { fmtPct, fmtUsdCompact } from "@/lib/format";

const RAMP = ["#161616", "#3D2A12", "#7A4F1A", "#B85F0A", "#D97706"] as const;

function bucket(burdenB: number | null): number {
  if (burdenB === null || burdenB <= 0) return 0;
  if (burdenB < 0.05) return 1;
  if (burdenB < 0.5) return 2;
  if (burdenB < 2) return 3;
  return 4;
}

interface WorldMapProps {
  senders: SenderRow[];
  topojsonUrl?: string;

  aspect?: number;
}

interface Datum {
  feature: Feature<Geometry>;
  iso3: string | null;
  burden: number | null;
  burdenB: number | null;
  bucketIdx: number;
  name: string;
  source?: SenderRow;
}

interface Hover {
  datum: Datum;
  x: number;
  y: number;
}

export function WorldMap({
  senders,
  topojsonUrl = "/data/world-110m.json",
  aspect = 1.7,
}: WorldMapProps) {
  const [features, setFeatures] = useState<Feature<Geometry>[] | null>(null);
  const [hover, setHover] = useState<Hover | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(960);


  const senderByIso3 = useMemo(() => {
    const m = new Map<string, SenderRow>();
    for (const s of senders) {
      m.set(s.source_code, s);
    }
    return m;
  }, [senders]);


  useEffect(() => {
    let cancelled = false;
    fetch(topojsonUrl)
      .then((r) => r.json())
      .then((topo: Topology) => {
        if (cancelled) return;
        const obj = topo.objects.countries as GeometryCollection;
        const fc = feature(topo, obj) as unknown as FeatureCollection<Geometry>;
        setFeatures(fc.features);
      });
    return () => {
      cancelled = true;
    };
  }, [topojsonUrl]);


  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setWidth(Math.round(e.contentRect.width));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const height = Math.round(width / aspect);

  const projection: GeoProjection = useMemo(() => {
    return geoNaturalEarth1()
      .scale(width / 6.3)
      .translate([width / 2, height / 2 - height * 0.04]);
  }, [width, height]);

  const pathGen = useMemo(() => geoPath(projection), [projection]);


  const data: Datum[] = useMemo(() => {
    if (!features) return [];
    return features.map((f) => {
      const id = String(f.id ?? "");
      const iso3 = M49_TO_ISO3[id] ?? null;
      const sender = iso3 ? senderByIso3.get(iso3) : undefined;
      const burden = sender?.fee_burden_usd_annual ?? null;
      const burdenB = burden !== null ? burden / 1e9 : null;
      const name =
        (f.properties as { name?: string } | null | undefined)?.name ??
        sender?.source_name ??
        "–";
      return {
        feature: f,
        iso3,
        burden,
        burdenB,
        bucketIdx: bucket(burdenB),
        name,
        source: sender,
      };
    });
  }, [features, senderByIso3]);

  return (
    <div
      ref={containerRef}
      className="relative w-full"
      style={{ aspectRatio: `${aspect}` }}
    >
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height="100%"
        preserveAspectRatio="xMidYMid meet"
        className="cursor-map"
        onMouseLeave={() => setHover(null)}
      >
        {}
        <rect width={width} height={height} fill="var(--color-bg)" />

        {}
        <line
          x1={0}
          y1={height - 1}
          x2={width}
          y2={height - 1}
          stroke="var(--color-border)"
          strokeWidth={1}
        />

        <g>
          {data.map((d, i) => {
            const path = pathGen(d.feature) ?? "";
            if (!path) return null;
            const baseFill =
              d.iso3 && d.bucketIdx > 0
                ? RAMP[d.bucketIdx]
                : d.iso3
                ? "var(--color-surface-2)"
                : "var(--color-surface)";
            const isHover = hover?.datum.feature === d.feature;
            const fill = isHover && d.bucketIdx > 0 ? RAMP[Math.min(d.bucketIdx + 1, 4)] : baseFill;
            const stroke = isHover && d.bucketIdx > 0 ? "var(--color-accent)" : "var(--color-border)";
            return (
              <path
                key={i}
                d={path}
                fill={fill}
                stroke={stroke}
                strokeWidth={isHover ? 1 : 0.4}
                className={d.bucketIdx > 0 ? "cursor-map-active" : ""}
                onMouseMove={(e) => {
                  const rect = (e.currentTarget.ownerSVGElement as SVGSVGElement)
                    .getBoundingClientRect();
                  setHover({
                    datum: d,
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                  });
                }}
                onMouseLeave={() => setHover(null)}
              />
            );
          })}
        </g>
      </svg>

      {}
      <div className="absolute bottom-3 left-0 flex items-center gap-3 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
        <span>Annual fee burden</span>
        <div className="flex h-2 items-center gap-[2px]">
          {RAMP.slice(1).map((c, i) => (
            <span
              key={i}
              className="block h-full w-5"
              style={{ background: c }}
              aria-hidden
            />
          ))}
        </div>
        <span className="font-mono normal-case tracking-normal">
          $0 to $2 B+
        </span>
      </div>

      {}
      {hover ? (
        <Tooltip x={hover.x} y={hover.y} datum={hover.datum} containerWidth={width} />
      ) : null}
    </div>
  );
}

function Tooltip({
  x,
  y,
  datum,
  containerWidth,
}: {
  x: number;
  y: number;
  datum: Datum;
  containerWidth: number;
}) {
  const offset = 16;

  const placeRight = x + 280 < containerWidth;
  const tx = placeRight ? x + offset : x - offset;

  return (
    <div
      className="pointer-events-none absolute z-10 min-w-[220px] -translate-y-full rounded-[2px] border border-border-hi bg-surface-2 px-3 py-2.5 shadow-none"
      style={{
        left: tx,
        top: y - 8,
        transform: placeRight
          ? "translate(0, -100%)"
          : "translate(-100%, -100%)",
      }}
    >
      <div className="font-display text-body-lg leading-tight tracking-[-0.01em] text-text">
        {datum.source?.source_name ?? datum.name}
      </div>
      {datum.source ? (
        <>
          <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
            <Stat label="Fee burden" value={fmtUsdCompact(datum.source.fee_burden_usd_annual)} />
            <Stat label="Volume" value={fmtUsdCompact(datum.source.volume_usd_annual)} />
            <Stat label="Avg TCI" value={fmtPct(datum.source.tci_volume_weighted_pct)} />
            <Stat label="Corridors" value={String(datum.source.n_corridors)} />
          </div>
          <div className="mt-2 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
            ↗ click to drill in
          </div>
        </>
      ) : (
        <div className="mt-1 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
          No corridor data in panel
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="overline text-[0.625rem]">{label}</div>
      <div className="font-mono text-label text-text mt-0.5">{value}</div>
    </div>
  );
}
