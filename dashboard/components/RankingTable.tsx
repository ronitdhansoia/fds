import Link from "next/link";
import type { RankingCorridor } from "@/lib/data";
import { fmtPct, fmtUsdCompact } from "@/lib/format";

interface RankingTableProps {
  rows: RankingCorridor[];
  metric: "tci" | "savings_pct" | "savings_usd" | "burden_usd";

  rightHeader: string;
  rightFormat: (r: RankingCorridor) => string;
  rightTone?: "amber" | "moss" | "neutral";
  limit?: number;
}

export function RankingTable({
  rows,
  rightHeader,
  rightFormat,
  rightTone = "neutral",
  limit = 10,
  metric,
}: RankingTableProps) {
  const max = Math.max(
    ...rows.map((r) => Number(rightValue(r, metric)) || 0),
    0.01,
  );
  const tone =
    rightTone === "amber"
      ? "text-accent"
      : rightTone === "moss"
      ? "text-accent-2"
      : "text-text";

  return (
    <div className="border-t border-border">
      <div className="grid grid-cols-[1.75rem_1fr_max-content] items-baseline gap-3 border-b border-border py-2 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
        <span>#</span>
        <span>Corridor</span>
        <span className="text-right">{rightHeader}</span>
      </div>
      {rows.slice(0, limit).map((r, i) => {
        const v = Number(rightValue(r, metric)) || 0;
        const widthPct = (Math.abs(v) / max) * 100;
        return (
          <Link
            key={r.id}
            href={`/corridor/${r.id}`}
            className="block border-b border-border py-3 transition-colors hover:bg-surface relative"
          >
            <div className="grid grid-cols-[1.75rem_1fr_max-content] items-baseline gap-3 relative">
              <span className="font-mono text-label text-text-3">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span>
                <span className="font-display text-body-lg text-text leading-tight">
                  {r.source_name}
                </span>
                <span className="mx-2 text-text-3">→</span>
                <span className="font-display text-body-lg text-text leading-tight">
                  {r.destination_name}
                </span>
                <div className="mt-1 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
                  {r.id}
                </div>
              </span>
              <span className={`font-mono text-body-lg tabular-nums ${tone}`}>
                {rightFormat(r)}
              </span>
            </div>
            {}
            <div className="absolute -bottom-px left-0 h-px bg-surface w-full">
              <div
                className={`h-full ${
                  rightTone === "moss" ? "bg-accent-2" : "bg-accent"
                }`}
                style={{ width: `${widthPct}%` }}
              />
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function rightValue(r: RankingCorridor, metric: RankingTableProps["metric"]): number | null {
  switch (metric) {
    case "tci":
      return r.tci_pct;
    case "savings_pct":
      return r.savings_pct;
    case "savings_usd":
      return r.savings_usd_annual;
    case "burden_usd":
      return r.fee_burden_usd_annual;
  }
}

export const fmtters = { fmtPct, fmtUsdCompact };
