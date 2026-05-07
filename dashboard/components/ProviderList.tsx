import type { CorridorProvider } from "@/lib/data";
import { fmtPct } from "@/lib/format";

export function ProviderList({
  providers,
}: {
  providers: CorridorProvider[];
}) {
  if (providers.length === 0) {
    return (
      <div className="font-mono text-label text-text-3">
        No provider data for this corridor in the latest quarter.
      </div>
    );
  }



  const rows = providers.slice(0, 12);
  const max = Math.max(...providers.map((p) => p.tci_pct ?? 0), 1);

  return (
    <div className="border-t border-border">
      <div className="grid grid-cols-[2.5rem_1fr_5rem_5rem_5rem_5rem_8rem] items-baseline gap-4 border-b border-border py-3 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
        <span>#</span>
        <span>Provider</span>
        <span className="text-right">Fee%</span>
        <span className="text-right">FX%</span>
        <span className="text-right">Speed%</span>
        <span className="text-right">TCI%</span>
        <span></span>
      </div>
      {rows.map((p, i) => {
        const tci = p.tci_pct ?? 0;
        const widthPct = (tci / max) * 100;
        return (
          <div
            key={`${p.firm}-${i}`}
            className="grid grid-cols-[2.5rem_1fr_5rem_5rem_5rem_5rem_8rem] items-baseline gap-4 border-b border-border py-3 transition-colors hover:bg-surface"
          >
            <span className="font-mono text-label text-text-3">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span>
              <span className="font-display text-body-lg text-text">
                {p.firm ?? "–"}
              </span>
              <span className="ml-2 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
                {p.firm_type}
              </span>
            </span>
            <span className="text-right font-mono text-label tabular-nums text-text-2">
              {fmtPct(p.fee_pct)}
            </span>
            <span className="text-right font-mono text-label tabular-nums text-text-2">
              {fmtPct(p.fx_margin_pct)}
            </span>
            <span className="text-right font-mono text-label tabular-nums text-text-3">
              {fmtPct(p.speed_penalty_pct, 2)}
            </span>
            <span className="text-right font-mono text-body-lg tabular-nums text-text">
              {fmtPct(tci)}
            </span>
            <span className="relative h-2 self-center bg-surface">
              <span
                className="absolute inset-y-0 left-0 bg-accent"
                style={{ width: `${widthPct}%` }}
              />
            </span>
          </div>
        );
      })}
    </div>
  );
}
