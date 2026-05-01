import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { CorridorPicker } from "@/components/CorridorPicker";
import { Footer } from "@/components/Footer";
import { HistoryChart } from "@/components/HistoryChart";
import { ProviderList } from "@/components/ProviderList";
import { Section } from "@/components/Section";
import { TCIBar } from "@/components/TCIBar";
import { TopBar } from "@/components/TopBar";
import { getCorridors } from "@/lib/data";
import {
  fmtPct,
  fmtPeriod,
  fmtUsdCompact,
  fmtUsdFull,
} from "@/lib/format";

interface RouteProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ a?: string }>;
}

export async function generateMetadata({ params }: RouteProps): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `${id} corridor`,
    description: `True Cost Index, provider breakdown, and stablecoin counterfactual for the ${id} remittance corridor.`,
  };
}

export async function generateStaticParams() {
  const { corridors } = await getCorridors();
  return corridors.map((c) => ({ id: c.id }));
}

export default async function CorridorPage({ params, searchParams }: RouteProps) {
  const { id } = await params;
  const { a } = await searchParams;
  const amount = a === "500" ? 500 : 200;

  const { corridors, meta } = await getCorridors();
  const corridor = corridors.find((c) => c.id === id);
  if (!corridor) notFound();
  const bucket = corridor.amounts[String(amount)];
  if (!bucket) {
    // fall back to USD 200 if 500 missing
    redirect(`/corridor/${id}`);
  }

  const cur = bucket.current;
  const sc = bucket.stablecoin;
  const cheapest = bucket.providers[0];

  // Picker data — sources alphabetically; per-source destinations alphabetically.
  const sendersOptions = uniqOptions(
    corridors.map((c) => ({ code: c.source_code, name: c.source_name ?? c.source_code })),
  );
  const destinationsBySource: Record<string, { code: string; name: string }[]> = {};
  for (const c of corridors) {
    const arr =
      destinationsBySource[c.source_code] ??
      (destinationsBySource[c.source_code] = []);
    arr.push({ code: c.destination_code, name: c.destination_name ?? c.destination_code });
  }
  for (const k of Object.keys(destinationsBySource)) {
    destinationsBySource[k] = uniqOptions(destinationsBySource[k]);
  }

  return (
    <main>
      <TopBar active="explorer" />

      <CorridorPicker
        senders={sendersOptions}
        destinationsBySource={destinationsBySource}
        current={{
          source: { code: corridor.source_code, name: corridor.source_name ?? corridor.source_code },
          destination: {
            code: corridor.destination_code,
            name: corridor.destination_name ?? corridor.destination_code,
          },
        }}
        amount={amount as 200 | 500}
      />

      {/* ----------------------------------------------------------------- */}
      {/* Headline sentence                                                  */}
      {/* ----------------------------------------------------------------- */}
      <section className="mx-auto max-w-[1280px] px-6 pt-20 pb-16 grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-2">
          <div className="overline">Corridor</div>
          <div className="mt-2 font-mono text-body-lg text-text-2">{corridor.id}</div>
          <div className="mt-1 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
            {fmtPeriod(cur.period)}
          </div>
        </div>
        <div className="col-span-12 lg:col-span-10">
          <h1 className="font-display text-section md:text-display leading-[1.05] tracking-[-0.025em] text-text balance">
            Sending{" "}
            <span className="num text-text">${amount}</span> from{" "}
            <span className="text-text">{corridor.source_name}</span> to{" "}
            <span className="text-text">{corridor.destination_name}</span> costs
            on average{" "}
            <span className="text-accent num">
              {fmtPct(cur.tci_pct, 2)}
            </span>
            {cheapest ? (
              <>
                {" "}— or as little as{" "}
                <span className="text-text num">{fmtPct(cheapest.tci_pct, 2)}</span>{" "}
                via <span className="text-text">{cheapest.firm}</span>
              </>
            ) : null}
            {sc?.total_pct !== undefined ? (
              <>
                . Stablecoin rails would cost{" "}
                <span className="text-accent-2 num">{fmtPct(sc.total_pct, 2)}</span>.
              </>
            ) : (
              "."
            )}
          </h1>
        </div>
      </section>

      <hr className="rule mx-auto max-w-[1280px]" />

      {/* ----------------------------------------------------------------- */}
      {/* Comparison bar                                                     */}
      {/* ----------------------------------------------------------------- */}
      <Section
        overline="§1 — TCI breakdown"
        title="What the cost is made of."
        className="mt-20"
      >
        <TCIBar
          fee={cur.fee_pct ?? 0}
          fxMargin={cur.fx_margin_pct ?? 0}
          speedPenalty={cur.speed_penalty_pct ?? 0}
          scCost={sc?.total_pct ?? undefined}
        />

        {sc ? (
          <dl className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-5">
            <Stat
              k="On-ramp"
              v={fmtPct(sc.onramp_pct, 2)}
              note={`Sender ${corridor.source_code}`}
            />
            <Stat
              k="Off-ramp"
              v={fmtPct(sc.offramp_pct, 2)}
              note={`Receiver ${corridor.destination_code}`}
            />
            <Stat
              k="Network gas"
              v={fmtPct(sc.gas_pct, 2)}
              note={`USD 0.50 over $${amount}`}
            />
            <Stat
              k="Local FX spread"
              v={fmtPct(sc.fx_spread_pct, 2)}
              note={`Receiver ${corridor.destination_code}`}
            />
          </dl>
        ) : null}
      </Section>

      {/* ----------------------------------------------------------------- */}
      {/* Provider list                                                      */}
      {/* ----------------------------------------------------------------- */}
      <Section
        overline="§2 — Providers"
        title={
          <>
            {bucket.providers.length} options.
            <br />
            <span className="text-text-3">Ranked by TCI.</span>
          </>
        }
        className="mt-32"
      >
        <ProviderList providers={bucket.providers} />
      </Section>

      {/* ----------------------------------------------------------------- */}
      {/* History                                                            */}
      {/* ----------------------------------------------------------------- */}
      {bucket.history && bucket.history.length > 1 ? (
        <Section
          overline="§3 — History"
          title="Quarterly TCI since the panel began."
          className="mt-32"
        >
          <HistoryChart history={bucket.history} />
          <div className="mt-3 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
            {fmtPeriod(bucket.history[0].period)} → {fmtPeriod(bucket.history[bucket.history.length - 1].period)}
            {" · "}{bucket.history.length} quarters
          </div>
        </Section>
      ) : null}

      {/* ----------------------------------------------------------------- */}
      {/* Annual diaspora callout                                            */}
      {/* ----------------------------------------------------------------- */}
      {sc?.volume_usd_annual ? (
        <section className="mx-auto max-w-[1280px] px-6 mt-32 grid grid-cols-12 gap-6">
          <div className="col-span-12 lg:col-span-3">
            <div className="overline">§4 — Annual aggregate</div>
            <div className="mt-2 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
              KNOMAD bilateral, {sc.volume_year}
            </div>
          </div>
          <div className="col-span-12 lg:col-span-9">
            <p className="font-display text-section leading-[1.1] tracking-[-0.025em] text-text balance">
              At <span className="num text-text">{fmtUsdFull(sc.volume_usd_annual)}</span>{" "}
              of annual flow, this corridor pays roughly{" "}
              <span className="text-accent num">
                {fmtUsdCompact(((cur.tci_pct ?? 0) / 100) * sc.volume_usd_annual)}
              </span>{" "}
              in fees every year. Stablecoin rails would save{" "}
              <span className="text-accent-2 num">
                {fmtUsdCompact(sc.savings_usd_annual)}
              </span>{" "}
              under our conservative assumptions.
            </p>
            <p className="mt-6 text-body text-text-2 leading-relaxed">
              Volume figure is the {sc.volume_year} World Bank / KNOMAD bilateral
              estimate (latest published). TCI is the unweighted mean across
              providers in the {fmtPeriod(cur.period)} RPW release. Stablecoin
              cost composition is laid out in §1 above and the assumptions live
              on the{" "}
              <a className="text-text underline underline-offset-4 hover:text-text-2" href="/methodology">
                methodology page
              </a>
              .
            </p>
          </div>
        </section>
      ) : null}

      <Footer meta={meta} />
    </main>
  );
}

function uniqOptions(opts: { code: string; name: string }[]): { code: string; name: string }[] {
  const seen = new Map<string, { code: string; name: string }>();
  for (const o of opts) {
    if (!seen.has(o.code)) seen.set(o.code, o);
  }
  return Array.from(seen.values()).sort((a, b) => a.name.localeCompare(b.name));
}

function Stat({ k, v, note }: { k: string; v: string; note?: string }) {
  return (
    <div className="border-l border-border pl-4">
      <div className="overline">{k}</div>
      <div className="mt-2 font-mono text-body-lg tabular-nums text-text">{v}</div>
      {note ? (
        <div className="mt-1 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
          {note}
        </div>
      ) : null}
    </div>
  );
}
