"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/cn";

interface Option {
  code: string;
  name: string;
}

interface CorridorPickerProps {
  current: { source: Option; destination: Option };
  /** Map of source ISO3 -> available destination options (ordered alphabetically). */
  destinationsBySource: Record<string, Option[]>;
  /** All sender ISO3s with at least one corridor. */
  senders: Option[];
  amount: 200 | 500;
}

export function CorridorPicker({
  current,
  destinationsBySource,
  senders,
  amount,
}: CorridorPickerProps) {
  const router = useRouter();
  const [src, setSrc] = useState(current.source.code);
  const [dst, setDst] = useState(current.destination.code);
  const [amt, setAmt] = useState<200 | 500>(amount);

  // Reset destination when source changes if the current destination is no
  // longer reachable from this source.
  useEffect(() => {
    const valid = destinationsBySource[src] ?? [];
    if (!valid.find((d) => d.code === dst)) {
      const next = valid[0];
      if (next) setDst(next.code);
    }
  }, [src, dst, destinationsBySource]);

  // Push a navigation when src/dst/amt actually changes from the URL state.
  useEffect(() => {
    if (src === current.source.code && dst === current.destination.code && amt === amount) return;
    const id = `${src}-${dst}`;
    const url = `/corridor/${id}${amt === 500 ? "?a=500" : ""}`;
    router.push(url);
  }, [src, dst, amt, current.source.code, current.destination.code, amount, router]);

  const dstOptions = useMemo(() => destinationsBySource[src] ?? [], [destinationsBySource, src]);

  return (
    <div className="sticky top-12 z-20 border-y border-border bg-bg">
      {/* Desktop / tablet: single horizontal row */}
      <div className="mx-auto hidden md:flex max-w-[1280px] items-center gap-6 px-6 py-4">
        <Slot label="Send from">
          <Select value={src} onChange={setSrc} options={senders} />
        </Slot>
        <Arrow />
        <Slot label="Send to">
          <Select value={dst} onChange={setDst} options={dstOptions} />
        </Slot>
        <div className="ml-auto flex items-center gap-2 border-l border-border pl-6">
          <span className="overline mr-2">Amount</span>
          <AmountToggle value={amt} onChange={setAmt} />
        </div>
      </div>

      {/* Mobile: stacked rows separated by hairlines so each slot has room */}
      <div className="md:hidden">
        <div className="border-b border-border px-6 py-3">
          <div className="overline mb-1">Send from</div>
          <Select value={src} onChange={setSrc} options={senders} />
        </div>
        <div className="border-b border-border px-6 py-3">
          <div className="overline mb-1">Send to</div>
          <Select value={dst} onChange={setDst} options={dstOptions} />
        </div>
        <div className="flex items-center justify-between px-6 py-3">
          <span className="overline">Amount</span>
          <AmountToggle value={amt} onChange={setAmt} />
        </div>
      </div>
    </div>
  );
}

function Slot({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-3 min-w-0">
      <span className="overline whitespace-nowrap">{label}</span>
      {children}
    </div>
  );
}

function Arrow() {
  return <span className="font-mono text-text-3 text-body-lg select-none">→</span>;
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: Option[];
}) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const ref = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 0);
    else setFilter("");
  }, [open]);

  const current = options.find((o) => o.code === value);
  const list = filter
    ? options.filter(
        (o) =>
          o.name.toLowerCase().includes(filter.toLowerCase()) ||
          o.code.toLowerCase().includes(filter.toLowerCase()),
      )
    : options;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          "flex items-baseline gap-2 border-b border-border-hi pb-1 transition-colors",
          "hover:border-text-2 focus:outline-none",
        )}
      >
        <span className="font-display text-body-lg leading-tight tracking-[-0.01em] text-text">
          {current?.name ?? "–"}
        </span>
        <span className="font-mono text-overline tracking-[0.18em] text-text-3">
          {current?.code ?? "?"}
        </span>
      </button>
      {open ? (
        <div className="absolute left-0 top-[calc(100%+0.5rem)] z-50 max-h-72 w-72 overflow-hidden rounded-[2px] border border-border-hi bg-surface">
          <input
            ref={inputRef}
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Type to filter…"
            className="w-full border-b border-border bg-transparent px-3 py-2 font-mono text-label text-text placeholder:text-text-3 focus:outline-none"
          />
          <div className="max-h-56 overflow-y-auto">
            {list.length === 0 ? (
              <div className="px-3 py-3 font-mono text-label text-text-3">
                no matches
              </div>
            ) : (
              list.map((o) => (
                <button
                  key={o.code}
                  onClick={() => {
                    onChange(o.code);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-baseline justify-between gap-3 border-b border-border px-3 py-2 text-left transition-colors hover:bg-surface-2 last:border-b-0",
                    o.code === value && "bg-surface-2",
                  )}
                >
                  <span className="text-label text-text">{o.name}</span>
                  <span className="font-mono text-overline tracking-[0.18em] text-text-3">
                    {o.code}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AmountToggle({
  value,
  onChange,
}: {
  value: 200 | 500;
  onChange: (v: 200 | 500) => void;
}) {
  return (
    <div className="inline-flex items-center rounded-[2px] border border-border-hi p-[2px]">
      {([200, 500] as const).map((v) => (
        <button
          key={v}
          onClick={() => onChange(v)}
          className={cn(
            "px-3 py-1 font-mono text-label transition-colors",
            value === v
              ? "bg-text text-bg"
              : "text-text-2 hover:text-text",
          )}
        >
          ${v}
        </button>
      ))}
    </div>
  );
}
