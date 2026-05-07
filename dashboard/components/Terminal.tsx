"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import type {
  Corridor,
  CorridorAmount,
  CorridorsMeta,
  RegressionPayload,
} from "@/lib/data";

type LineKind = "in" | "out" | "sys" | "err";
type Line = { kind: LineKind; text: string };

const BOOT: Line[] = [
  { kind: "sys", text: "MigrantMoney v1.0.0  ·  remittance true-cost terminal" },
  { kind: "sys", text: 'Type "help" for commands, or "summary" for the headline numbers.' },
  { kind: "sys", text: "" },
];

interface TerminalProps {
  corridors: Corridor[];
  regression: RegressionPayload;
  meta: CorridorsMeta;
}

export function Terminal({ corridors, regression, meta }: TerminalProps) {
  const sendAmount = meta.headline_send_amount_usd;
  const sendKey = String(sendAmount);

  const [lines, setLines] = useState<Line[]>(BOOT);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState<number | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);


  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [lines]);


  const focusInput = useCallback(() => {
    inputRef.current?.focus();
  }, []);
  useEffect(() => {
    focusInput();
  }, [focusInput]);




  const byId = useMemo(() => {
    const m = new Map<string, Corridor>();
    for (const c of corridors) m.set(c.id.toUpperCase(), c);
    return m;
  }, [corridors]);

  const sortedByTci = useMemo(() => {
    return corridors
      .map((c) => ({ c, tci: c.amounts[sendKey]?.current?.tci_pct ?? null }))
      .filter((x): x is { c: Corridor; tci: number } => x.tci !== null)
      .sort((a, b) => b.tci - a.tci);
  }, [corridors, sendKey]);

  const sortedBySavings = useMemo(() => {
    return corridors
      .map((c) => ({
        c,
        sv: c.amounts[sendKey]?.stablecoin?.savings_usd_annual ?? null,
        pct: c.amounts[sendKey]?.stablecoin?.savings_pct ?? null,
      }))
      .filter(
        (x): x is { c: Corridor; sv: number; pct: number } =>
          x.sv !== null && x.sv > 0,
      )
      .sort((a, b) => b.sv - a.sv);
  }, [corridors, sendKey]);





  const lpad = (s: string, n: number) => s + " ".repeat(Math.max(0, n - s.length));
  const rpad = (s: string, n: number) => " ".repeat(Math.max(0, n - s.length)) + s;





  function cmdHelp(): Line[] {
    const COMMANDS: [string, string][] = [
      ["help", "Show this message"],
      ["summary", "Headline panel statistics"],
      ["top [n]", "Top N most expensive corridors (default 10)"],
      ["cheapest [n]", "Top N cheapest corridors (default 10)"],
      ["corridor <id>", "TCI breakdown for one corridor (e.g., USA-MEX)"],
      ["provider <id>", "Provider ranking for a corridor"],
      ["savings [n]", "Top N corridors by stablecoin savings"],
      ["regression", "Operator-class fixed-effects coefficients"],
      ["meta", "Pipeline metadata (sources, retrieval dates)"],
      ["about", "About this project"],
      ["clear", "Clear the buffer"],
    ];
    const out: Line[] = [{ kind: "out", text: "" }];
    for (const [cmd, desc] of COMMANDS) {
      out.push({ kind: "out", text: `  ${lpad(cmd, 18)}${desc}` });
    }
    out.push({ kind: "out", text: "" });
    out.push({ kind: "out", text: "Examples:" });
    out.push({ kind: "out", text: "  $ corridor USA-MEX" });
    out.push({ kind: "out", text: "  $ top 20" });
    out.push({ kind: "out", text: "  $ savings 5" });
    out.push({ kind: "out", text: "" });
    out.push({ kind: "out", text: "↑/↓ recall history.  Send amount: USD " + sendAmount + "." });
    out.push({ kind: "out", text: "" });
    return out;
  }

  function cmdSummary(): Line[] {
    const g = meta.global_savings;
    const out: Line[] = [
      { kind: "out", text: "" },
      { kind: "out", text: `  Panel              ${meta.panel_first_period} → ${meta.panel_last_period}  (${meta.n_quarters} quarters)` },
      { kind: "out", text: `  Corridors          ${meta.n_corridors.toLocaleString()}` },
      { kind: "out", text: `  Providers          ${meta.n_providers.toLocaleString()}` },
      { kind: "out", text: `  Rows               ${meta.n_rows.toLocaleString()}` },
    ];
    if (g) {
      out.push({ kind: "out", text: "" });
      out.push({ kind: "out", text: `  Volume in scope    $${(g.total_corridor_volume_usd / 1e9).toFixed(1)} B   (KNOMAD ${g.volume_year})` });
      out.push({ kind: "out", text: `  SC savings / yr    $${(g.total_savings_usd_annual_current / 1e9).toFixed(2)} B` });
      out.push({ kind: "out", text: `  Coverage           ${g.n_corridors_with_positive_savings} of ${g.n_corridors_with_volume} corridors with positive savings` });
    }
    out.push({ kind: "out", text: `  Generated          ${meta.generated_at}` });
    out.push({ kind: "out", text: "" });
    return out;
  }

  function cmdTop(args: string[], reverse = false): Line[] {
    const n = parseInt(args[0] ?? "10", 10);
    if (!Number.isFinite(n) || n < 1) {
      return [{ kind: "err", text: "usage: top [n]   (n must be a positive integer)" }];
    }
    const pool = reverse ? [...sortedByTci].reverse() : sortedByTci;
    const slice = pool.slice(0, Math.min(n, pool.length));
    const label = reverse ? "cheapest" : "most expensive";
    const out: Line[] = [
      { kind: "out", text: "" },
      { kind: "out", text: `  Top ${slice.length} ${label} corridors (USD ${sendAmount}, latest quarter)` },
      { kind: "out", text: "" },
      {
        kind: "out",
        text:
          "  " +
          rpad("#", 3) +
          "  " +
          lpad("corridor", 12) +
          rpad("tci", 8) +
          "   sender → receiver",
      },
      { kind: "out", text: `  ${"─".repeat(64)}` },
    ];
    slice.forEach((x, i) => {
      const tci = x.tci.toFixed(2) + "%";
      const route = `${x.c.source_name ?? x.c.source_code} → ${x.c.destination_name ?? x.c.destination_code}`;
      out.push({
        kind: "out",
        text:
          "  " +
          rpad(String(i + 1), 3) +
          "  " +
          lpad(x.c.id, 12) +
          rpad(tci, 8) +
          "   " +
          route,
      });
    });
    out.push({ kind: "out", text: "" });
    return out;
  }

  function cmdCorridor(args: string[]): Line[] {
    if (args.length === 0) {
      return [{ kind: "err", text: "usage: corridor <id>   (e.g., corridor USA-MEX)" }];
    }
    const id = args[0].toUpperCase();
    const c = byId.get(id);
    if (!c) return [{ kind: "err", text: `corridor not found: ${id}` }];
    const a: CorridorAmount | undefined = c.amounts[sendKey];
    if (!a) return [{ kind: "err", text: `no data for USD ${sendAmount} on ${id}` }];
    const cur = a.current;
    const sc = a.stablecoin;
    const route = `${c.source_name ?? c.source_code} → ${c.destination_name ?? c.destination_code}`;
    const out: Line[] = [
      { kind: "out", text: "" },
      { kind: "out", text: `  ${id}   ${route}` },
      { kind: "out", text: `  USD ${sendAmount}, latest quarter (${cur.period ?? "n/a"})` },
      { kind: "out", text: "" },
      { kind: "out", text: `    fee                ${pct(cur.fee_pct)}` },
      { kind: "out", text: `    fx margin          ${pct(cur.fx_margin_pct)}` },
      { kind: "out", text: `    speed penalty      ${pct(cur.speed_penalty_pct)}` },
      { kind: "out", text: `    ${"─".repeat(28)}` },
      { kind: "out", text: `    TCI                ${pct(cur.tci_pct)}   median ${pct(cur.tci_median_pct)}` },
      { kind: "out", text: `    days to arrive     ${(cur.days_to_arrive_mean ?? 0).toFixed(1)}` },
      { kind: "out", text: `    providers          ${cur.n_providers ?? "?"}` },
    ];
    if (sc) {
      out.push({ kind: "out", text: "" });
      out.push({ kind: "out", text: `  Stablecoin counterfactual` });
      out.push({ kind: "out", text: `    on-ramp            ${pct(sc.onramp_pct)}` });
      out.push({ kind: "out", text: `    off-ramp           ${pct(sc.offramp_pct)}` });
      out.push({ kind: "out", text: `    gas                ${pct(sc.gas_pct)}` });
      out.push({ kind: "out", text: `    fx spread          ${pct(sc.fx_spread_pct)}` });
      out.push({ kind: "out", text: `    ${"─".repeat(28)}` });
      out.push({ kind: "out", text: `    SC total           ${pct(sc.total_pct)}` });
      out.push({ kind: "out", text: `    savings            ${pct(sc.savings_pct)}` });
      if (sc.savings_usd_annual && sc.volume_usd_annual) {
        const sav = (sc.savings_usd_annual / 1e6).toFixed(1);
        const vol = (sc.volume_usd_annual / 1e9).toFixed(2);
        out.push({ kind: "out", text: `    annual savings     $${sav} M   (corridor volume $${vol} B, ${sc.volume_year})` });
      }
    }
    out.push({ kind: "out", text: "" });
    return out;
  }

  function cmdProvider(args: string[]): Line[] {
    if (args.length === 0) {
      return [{ kind: "err", text: "usage: provider <id>   (e.g., provider USA-MEX)" }];
    }
    const id = args[0].toUpperCase();
    const c = byId.get(id);
    if (!c) return [{ kind: "err", text: `corridor not found: ${id}` }];
    const a = c.amounts[sendKey];
    if (!a) return [{ kind: "err", text: `no data for USD ${sendAmount} on ${id}` }];
    const provs = a.providers ?? [];
    if (provs.length === 0) {
      return [{ kind: "err", text: `no provider data on ${id}` }];
    }
    const out: Line[] = [
      { kind: "out", text: "" },
      { kind: "out", text: `  Providers on ${id} (USD ${sendAmount}), ranked by TCI` },
      { kind: "out", text: "" },
      {
        kind: "out",
        text:
          "  " +
          rpad("#", 3) +
          "  " +
          lpad("firm", 26) +
          lpad("type", 12) +
          rpad("tci", 8),
      },
      { kind: "out", text: `  ${"─".repeat(58)}` },
    ];
    provs.slice(0, 12).forEach((p, i) => {
      out.push({
        kind: "out",
        text:
          "  " +
          rpad(String(i + 1), 3) +
          "  " +
          lpad((p.firm ?? "–").slice(0, 24), 26) +
          lpad((p.firm_type ?? "–").slice(0, 10), 12) +
          rpad((p.tci_pct ?? 0).toFixed(2) + "%", 8),
      });
    });
    if (provs.length > 12) {
      out.push({ kind: "out", text: `  … ${provs.length - 12} more` });
    }
    out.push({ kind: "out", text: "" });
    return out;
  }

  function cmdSavings(args: string[]): Line[] {
    const n = parseInt(args[0] ?? "10", 10);
    if (!Number.isFinite(n) || n < 1) {
      return [{ kind: "err", text: "usage: savings [n]" }];
    }
    const slice = sortedBySavings.slice(0, Math.min(n, sortedBySavings.length));
    const total = sortedBySavings.reduce((s, x) => s + x.sv, 0);
    const out: Line[] = [
      { kind: "out", text: "" },
      { kind: "out", text: `  Top ${slice.length} corridors by stablecoin savings (USD ${sendAmount})` },
      { kind: "out", text: `  Global total: $${(total / 1e9).toFixed(2)} B / yr` },
      { kind: "out", text: "" },
      {
        kind: "out",
        text:
          "  " +
          rpad("#", 3) +
          "  " +
          lpad("corridor", 12) +
          rpad("savings", 12) +
          rpad("savings %", 12) +
          " sender → receiver",
      },
      { kind: "out", text: `  ${"─".repeat(80)}` },
    ];
    slice.forEach((x, i) => {
      const usd = x.sv >= 1e9 ? `$${(x.sv / 1e9).toFixed(2)}B` : `$${(x.sv / 1e6).toFixed(0)}M`;
      const route = `${x.c.source_name ?? x.c.source_code} → ${x.c.destination_name ?? x.c.destination_code}`;
      out.push({
        kind: "out",
        text:
          "  " +
          rpad(String(i + 1), 3) +
          "  " +
          lpad(x.c.id, 12) +
          rpad(usd, 12) +
          rpad(x.pct.toFixed(2) + "%", 12) +
          " " +
          route,
      });
    });
    out.push({ kind: "out", text: "" });
    return out;
  }

  function cmdRegression(): Line[] {
    const model = regression.models[sendKey];
    if (!model) {
      return [{ kind: "err", text: `no regression model for USD ${sendAmount}` }];
    }
    const out: Line[] = [
      { kind: "out", text: "" },
      { kind: "out", text: `  Operator-class two-way FE regression  (USD ${sendAmount})` },
      { kind: "out", text: `  Reference category: ${model.specification.reference_class}` },
      { kind: "out", text: `  Cluster: ${model.specification.cluster_var}` },
      {
        kind: "out",
        text: `  N=${model.fit.n_observations.toLocaleString()}, corridors=${model.fit.n_corridors}, quarters=${model.fit.n_quarters}, R² within=${model.fit.rsquared_within.toFixed(3)}`,
      },
      { kind: "out", text: "" },
      {
        kind: "out",
        text:
          "  " +
          lpad("class", 14) +
          rpad("coef (pp)", 12) +
          rpad("se", 8) +
          rpad("t", 8) +
          rpad("p", 9) +
          "    sig",
      },
      { kind: "out", text: `  ${"─".repeat(64)}` },
    ];
    for (const c of model.coefficients) {
      out.push({
        kind: "out",
        text:
          "  " +
          lpad(c.firm_type, 14) +
          rpad((c.estimate_pct >= 0 ? "+" : "") + c.estimate_pct.toFixed(2), 12) +
          rpad(c.std_error_pct.toFixed(2), 8) +
          rpad(c.t_stat.toFixed(2), 8) +
          rpad(c.p_value < 1e-3 ? "<0.001" : c.p_value.toFixed(3), 9) +
          "    " +
          (c.significance || ""),
      });
    }
    out.push({ kind: "out", text: "" });
    return out;
  }

  function cmdMeta(): Line[] {
    const out: Line[] = [
      { kind: "out", text: "" },
      { kind: "out", text: `  Sources` },
      { kind: "out", text: `    rpw     ${meta.data_sources.rpw.name}` },
      { kind: "out", text: `            retrieved ${meta.data_sources.rpw.retrieval_date}` },
      { kind: "out", text: `    bre     ${meta.data_sources.bilateral_remittance_matrix.name}` },
      {
        kind: "out",
        text: `            indicator ${meta.data_sources.bilateral_remittance_matrix.indicator}, ${meta.data_sources.bilateral_remittance_matrix.year}`,
      },
      { kind: "out", text: "" },
      { kind: "out", text: `  Stablecoin defaults` },
      { kind: "out", text: `    gas              $${meta.stablecoin_assumptions.gas_usd.toFixed(2)}` },
      {
        kind: "out",
        text: `    on-ramp          ${meta.stablecoin_assumptions.onramp_pct.developed.toFixed(1)}% (developed) / ${meta.stablecoin_assumptions.onramp_pct.default.toFixed(1)}% (default) / ${meta.stablecoin_assumptions.onramp_pct.low_banked.toFixed(1)}% (low-banked)`,
      },
      {
        kind: "out",
        text: `    off-ramp         ${meta.stablecoin_assumptions.offramp_pct.top_p2p.toFixed(1)}% (top P2P) / ${meta.stablecoin_assumptions.offramp_pct.default.toFixed(1)}% (default) / ${meta.stablecoin_assumptions.offramp_pct.thin_liquidity.toFixed(1)}% (thin)`,
      },
      {
        kind: "out",
        text: `    fx spread        ${meta.stablecoin_assumptions.fx_spread_pct.deep.toFixed(1)}% (deep) / ${meta.stablecoin_assumptions.fx_spread_pct.default.toFixed(1)}% (default)`,
      },
      { kind: "out", text: `    κ (speed/day)    ${meta.kappa_pct_per_day.toFixed(2)}%` },
      { kind: "out", text: "" },
    ];
    return out;
  }

  function cmdAbout(): Line[] {
    return [
      { kind: "out", text: "" },
      { kind: "out", text: "  MigrantMoney" },
      { kind: "out", text: "  A True Cost Index for cross-border remittances," },
      { kind: "out", text: "  plus a stablecoin counterfactual that estimates" },
      { kind: "out", text: "  per-corridor savings if the same flows ran on" },
      { kind: "out", text: "  USDC / USDT rails." },
      { kind: "out", text: "" },
      { kind: "out", text: "  Built by Ronit Dhansoia." },
      { kind: "out", text: "  BITS Pilani Dubai · Fundamentals of Data Science · 2026." },
      { kind: "out", text: "  Source code: github.com/ronitdhansoia/fds" },
      { kind: "out", text: "" },
    ];
  }




  function run(raw: string): Line[] {
    const parts = raw.trim().split(/\s+/);
    const cmd = (parts[0] ?? "").toLowerCase();
    const args = parts.slice(1);
    switch (cmd) {
      case "help":
      case "?":
        return cmdHelp();
      case "summary":
        return cmdSummary();
      case "top":
        return cmdTop(args);
      case "cheapest":
      case "bottom":
        return cmdTop(args, true);
      case "corridor":
      case "c":
        return cmdCorridor(args);
      case "provider":
      case "p":
        return cmdProvider(args);
      case "savings":
        return cmdSavings(args);
      case "regression":
      case "reg":
        return cmdRegression();
      case "meta":
        return cmdMeta();
      case "about":
        return cmdAbout();
      default:
        return [
          { kind: "err", text: `unknown command: ${cmd}` },
          { kind: "out", text: 'Type "help" for the command list.' },
        ];
    }
  }

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const cmd = input.trim();
    setInput("");
    setHistIdx(null);
    if (!cmd) return;
    setHistory((h) => (h[h.length - 1] === cmd ? h : [...h, cmd]));

    if (cmd.toLowerCase() === "clear") {
      setLines(BOOT);
      return;
    }

    setLines((ls) => [...ls, { kind: "in", text: cmd }, ...run(cmd)]);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowUp") {
      if (history.length === 0) return;
      e.preventDefault();
      const idx = histIdx === null ? history.length - 1 : Math.max(0, histIdx - 1);
      setHistIdx(idx);
      setInput(history[idx]);
    } else if (e.key === "ArrowDown") {
      if (histIdx === null) return;
      e.preventDefault();
      const idx = histIdx + 1;
      if (idx >= history.length) {
        setHistIdx(null);
        setInput("");
      } else {
        setHistIdx(idx);
        setInput(history[idx]);
      }
    } else if (e.key === "l" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      setLines(BOOT);
    }
  }

  return (
    <div
      onClick={focusInput}
      className="rounded-[3px] border border-border bg-bg overflow-hidden"
    >
      {}
      <div className="grid grid-cols-3 items-center border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-1.5 col-start-1">
          <span className="block w-[7px] h-[7px] rounded-full bg-text-3 opacity-50" aria-hidden />
          <span className="block w-[7px] h-[7px] rounded-full bg-text-3 opacity-50" aria-hidden />
          <span className="block w-[7px] h-[7px] rounded-full bg-text-3 opacity-50" aria-hidden />
        </div>
        <div className="font-mono text-overline tracking-[0.18em] uppercase text-text-3 text-center col-start-2">
          migrantmoney
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setLines(BOOT);
            focusInput();
          }}
          aria-label="Reset terminal"
          title="Reset terminal"
          className="justify-self-end text-text-3 hover:text-text-2 transition-colors text-[14px] leading-none"
        >
          ⟳
        </button>
      </div>

      {}
      <div
        ref={bodyRef}
        className="px-6 py-5 h-[540px] overflow-y-auto font-mono text-label leading-[1.7] tabular-nums"
      >
        {lines.map((l, i) => (
          <LineView key={i} line={l} />
        ))}
        <form onSubmit={submit} className="flex items-start gap-2 mt-1">
          <span className="text-accent select-none">$</span>
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            spellCheck={false}
            autoCorrect="off"
            autoCapitalize="off"
            autoComplete="off"
            className="flex-1 bg-transparent outline-none border-0 text-text caret-accent font-mono text-label tabular-nums focus-visible:outline-none focus:outline-none"
            style={{ outline: "none", boxShadow: "none" }}
            aria-label="Terminal input"
          />
        </form>
      </div>
    </div>
  );
}

function LineView({ line }: { line: Line }) {
  if (line.text === "") {
    return <div className="leading-[1.7]">&nbsp;</div>;
  }
  if (line.kind === "in") {
    return (
      <div className="text-text whitespace-pre-wrap">
        <span className="text-accent select-none">$ </span>
        {line.text}
      </div>
    );
  }
  if (line.kind === "err") {
    return <div className="text-accent whitespace-pre-wrap">{line.text}</div>;
  }

  return <div className="text-text-2 whitespace-pre-wrap">{line.text}</div>;
}

function pct(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "    –   ";
  return v.toFixed(2).padStart(6, " ") + "%";
}
