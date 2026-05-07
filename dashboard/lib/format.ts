

const THIN = " ";

const intFmt = new Intl.NumberFormat("en-US");

export function fmtInt(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return intFmt.format(Math.round(n)).replace(/,/g, THIN);
}

export function fmtPct(
  n: number | null | undefined,
  decimals = 2,
  withSign = false,
): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  const sign = withSign && n > 0 ? "+" : "";
  return `${sign}${n.toFixed(decimals)}%`;
}

export function fmtPp(n: number | null | undefined, decimals = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(decimals)} pp`;
}

export function fmtUsdCompact(
  n: number | null | undefined,
  unit?: "B" | "M" | "K",
): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  const abs = Math.abs(n);
  let u: "B" | "M" | "K" | "" = "";
  let v = n;
  if (unit) {
    u = unit;
    v = unit === "B" ? n / 1e9 : unit === "M" ? n / 1e6 : n / 1e3;
  } else if (abs >= 1e9) {
    u = "B";
    v = n / 1e9;
  } else if (abs >= 1e6) {
    u = "M";
    v = n / 1e6;
  } else if (abs >= 1e3) {
    u = "K";
    v = n / 1e3;
  }
  const decimals = Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2;
  return `$${v.toFixed(decimals)}${u ? `${THIN}${u}` : ""}`;
}

export function fmtUsdFull(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return `$${intFmt.format(Math.round(n)).replace(/,/g, THIN)}`;
}

export function heroParts(n: number): { lead: string; unit: "B" | "M" | "K" } {
  const abs = Math.abs(n);
  if (abs >= 1e9) return { lead: (n / 1e9).toFixed(1), unit: "B" };
  if (abs >= 1e6) return { lead: (n / 1e6).toFixed(1), unit: "M" };
  return { lead: (n / 1e3).toFixed(0), unit: "K" };
}

export function fmtPeriod(period: string | null | undefined): string {
  if (!period) return "–";
  const m = period.match(/^(\d{4})[_\s]*(\d)Q?$/);
  if (!m) return period;
  return `${m[1]} Q${m[2]}`;
}

export function corridorLabel(
  source: string | null | undefined,
  destination: string | null | undefined,
): string {
  return `${source ?? "?"} → ${destination ?? "?"}`;
}
