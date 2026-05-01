import { Footer } from "@/components/Footer";
import { HeadlineTicker, type TickerItem } from "@/components/HeadlineTicker";
import { HeroNumber } from "@/components/HeroNumber";
import { RankingTable } from "@/components/RankingTable";
import { RevealItem } from "@/components/Reveal";
import { Section } from "@/components/Section";
import { TopBar } from "@/components/TopBar";
import { WorldMap } from "@/components/WorldMap";
import { getCorridors, getDiasporaBurden, getRegression } from "@/lib/data";
import { fmtPct, fmtPeriod, fmtUsdCompact } from "@/lib/format";

export default async function HomePage() {
  const burden = await getDiasporaBurden();
  const { corridors, meta } = await getCorridors();
  const reg = await getRegression();
  const headlineModel = reg.models[String(meta.headline_send_amount_usd)];

  const rankings = burden.rankings;
  const totalBurden = burden.headline.total_fee_burden_usd;
  const totalSavings = burden.headline.total_sc_savings_usd;
  const matchedVolume = burden.headline.total_volume_usd;

  // Build ticker items from the top corridors by absolute fee burden so the
  // strip cycles through high-volume, high-stake corridors.
  const headlineAmount = String(meta.headline_send_amount_usd);
  const corridorById = new Map(corridors.map((c) => [c.id, c]));
  const tickerItems: TickerItem[] = [];
  for (const r of rankings.biggest_fee_burden) {
    if (tickerItems.length >= 12) break;
    const c = corridorById.get(r.id);
    if (!c) continue;
    const sc = c.amounts[headlineAmount]?.stablecoin;
    const region = (c.source_region ?? "GLOBAL").toUpperCase();
    if (typeof r.tci_pct !== "number" || !sc?.savings_usd_annual) continue;
    tickerItems.push({
      region,
      source: (r.source_name ?? r.source_code).toUpperCase(),
      destination: (r.destination_name ?? r.destination_code).toUpperCase(),
      tci_pct: r.tci_pct,
      savings_usd: sc.savings_usd_annual,
    });
  }

  const dataPeriodHuman = fmtPeriod(meta.panel_last_period);

  return (
    <main>
      <TopBar active="home" />

      {/* ----------------------------------------------------------------- */}
      {/* HERO                                                                */}
      {/* ----------------------------------------------------------------- */}
      <section className="relative">
        {/* warm shadow only under the hero — applied once, nothing else */}
        <div className="hero-shadow pointer-events-none absolute inset-x-0 bottom-0 top-1/2 -z-[1]" aria-hidden />

        <div className="mx-auto grid max-w-[1280px] grid-cols-12 gap-6 px-6 pt-32 pb-32">
          <div className="col-span-12 lg:col-span-2">
            <RevealItem order={0}>
              <div className="overline">
                FDS · BITS Pilani Dubai · Data as of {dataPeriodHuman}
              </div>
            </RevealItem>
          </div>
          <div className="col-span-12 lg:col-span-10">
            <RevealItem order={1}>
              <h1 className="font-display text-section md:text-display leading-[1.05] tracking-[-0.025em] text-text balance">
                Migrants paid roughly{" "}
                <span className="text-accent">
                  <HeroNumberInline value={totalBurden} unit="B" />
                </span>{" "}
                last year to move their own money.
              </h1>
            </RevealItem>

            <RevealItem order={2}>
              <p className="mt-10 max-w-[640px] text-body-lg text-text-2 leading-[1.7] pretty">
                Across {burden.headline.n_corridors} cross-border corridors at
                an average send size of{" "}
                <span className="num text-text">${meta.headline_send_amount_usd}</span>,
                the World Bank Remittance Prices Worldwide panel implies a true
                cost of{" "}
                <span className="num text-text">
                  {fmtPct(burden.headline.global_tci_volume_weighted_pct, 2)}
                </span>{" "}
                — fee, FX margin, and a penalty for slow settlement combined.
                If the same flows ran on stablecoin rails, our conservative
                counterfactual saves an additional{" "}
                <span className="num text-accent-2">
                  {fmtUsdCompact(totalSavings)}
                </span>{" "}
                a year.
              </p>
            </RevealItem>

            <RevealItem order={3}>
              <div className="mt-10">
                <HeadlineTicker items={tickerItems} />
              </div>
            </RevealItem>

            <RevealItem order={4}>
              <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-5">
                <Stat
                  label="Corridor volume"
                  value={fmtUsdCompact(matchedVolume)}
                  note={`KNOMAD ${meta.global_savings?.volume_year ?? "—"}`}
                />
                <Stat
                  label="Volume-weighted TCI"
                  value={fmtPct(burden.headline.global_tci_volume_weighted_pct, 2)}
                  note="USD 200, latest quarter"
                />
                <Stat
                  label="Stablecoin savings"
                  value={fmtUsdCompact(totalSavings)}
                  note="conservative defaults"
                  tone="moss"
                />
                <Stat
                  label="Top sender burden"
                  value={fmtUsdCompact(burden.senders[0]?.fee_burden_usd_annual ?? 0)}
                  note={burden.senders[0]?.source_name ?? ""}
                  tone="amber"
                />
              </div>
            </RevealItem>
          </div>
        </div>
      </section>

      <hr className="rule mx-auto max-w-[1280px]" />

      {/* ----------------------------------------------------------------- */}
      {/* WORLD MAP                                                           */}
      {/* ----------------------------------------------------------------- */}
      <Section
        overline="§1 — Where the burden falls"
        title={
          <>
            Senders.
            <br />
            <span className="text-text-3">By annual fee burden.</span>
          </>
        }
        className="mt-32"
      >
        <RevealItem order={5}>
          <WorldMap senders={burden.senders} />
        </RevealItem>
        <p className="mt-6 max-w-[640px] text-body text-text-2 leading-relaxed pretty">
          Choropleth shaded by the total fees migrants in each sending country
          paid to move money in {meta.global_savings?.volume_year ?? "the latest year"}. The
          United States dominates ({fmtUsdCompact(burden.senders[0]?.fee_burden_usd_annual ?? 0)})
          because of sheer volume; Saudi Arabia and the UAE follow because of
          high migrant labour shares. Hover any country with data to see the
          per-corridor breakdown, or click through to the corridor explorer.
        </p>
      </Section>

      {/* ----------------------------------------------------------------- */}
      {/* TWO TABLES SIDE BY SIDE                                             */}
      {/* ----------------------------------------------------------------- */}
      <section className="mx-auto mt-32 grid max-w-[1280px] grid-cols-12 gap-x-6 gap-y-12 px-6">
        <header className="col-span-12 lg:col-span-3">
          <div className="overline">§2 — Rankings</div>
          <h2 className="mt-3 font-display text-subhead leading-[1.2] tracking-[-0.02em] text-text balance lg:sticky lg:top-20">
            The most expensive corridors and the biggest stablecoin savings.
          </h2>
        </header>

        <div className="col-span-12 lg:col-span-9 grid grid-cols-1 gap-x-12 gap-y-12 md:grid-cols-2">
          <div>
            <h3 className="overline mb-4">Most expensive · TCI %</h3>
            <RankingTable
              rows={rankings.most_expensive}
              metric="tci"
              rightHeader="TCI%"
              rightTone="amber"
              rightFormat={(r) => fmtPct(r.tci_pct, 1)}
              limit={10}
            />
          </div>
          <div>
            <h3 className="overline mb-4">Biggest annual savings · USD</h3>
            <RankingTable
              rows={rankings.biggest_absolute_savings}
              metric="savings_usd"
              rightHeader="USD/yr"
              rightTone="moss"
              rightFormat={(r) => fmtUsdCompact(r.savings_usd_annual)}
              limit={10}
            />
          </div>
          <div>
            <h3 className="overline mb-4">Biggest fee burden · USD</h3>
            <RankingTable
              rows={rankings.biggest_fee_burden}
              metric="burden_usd"
              rightHeader="USD/yr"
              rightTone="amber"
              rightFormat={(r) => fmtUsdCompact(r.fee_burden_usd_annual)}
              limit={10}
            />
          </div>
          <div>
            <h3 className="overline mb-4">Cheapest · TCI %</h3>
            <RankingTable
              rows={rankings.cheapest}
              metric="tci"
              rightHeader="TCI%"
              rightTone="neutral"
              rightFormat={(r) => fmtPct(r.tci_pct, 1)}
              limit={10}
            />
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- */}
      {/* REGRESSION CALLOUT                                                  */}
      {/* ----------------------------------------------------------------- */}
      <Section
        overline="§3 — Who charges most"
        title={
          <>
            After controlling for corridor and quarter, banks charge{" "}
            <span className="text-accent">~4.5 pp</span> more.
          </>
        }
        className="mt-32"
      >
        <p className="max-w-[640px] text-body-lg text-text-2 leading-[1.7] pretty">
          A two-way fixed-effects regression with N ={" "}
          <span className="num text-text">
            {headlineModel.fit.n_observations.toLocaleString()}
          </span>{" "}
          provider-quarter observations, absorbing corridor and quarter, with
          cluster-robust standard errors. MTOs are the reference. Mobile money
          comes out cheapest; banks are the most expensive non-niche channel.
        </p>

        <div className="mt-10 border-t border-border">
          {headlineModel.coefficients.map((c) => (
            <div
              key={c.firm_type}
              className="grid grid-cols-[7rem_1fr_5.5rem_3rem] items-baseline gap-4 border-b border-border py-4"
            >
              <span className="font-display text-body-lg text-text">{c.firm_type}</span>
              <ForestRow
                estimate={c.estimate_pct}
                lo={c.ci_low_pct}
                hi={c.ci_high_pct}
              />
              <span
                className={`text-right font-mono text-label tabular-nums ${
                  c.estimate_pct > 0 ? "text-accent" : "text-accent-2"
                }`}
              >
                {c.estimate_pct > 0 ? "+" : ""}
                {c.estimate_pct.toFixed(2)} pp
              </span>
              <span className="text-right font-mono text-overline tracking-[0.18em] uppercase text-text-3">
                {c.significance || "n.s."}
              </span>
            </div>
          ))}
        </div>
        <p className="mt-6 max-w-[640px] text-body text-text-2 leading-relaxed">
          R² within = {headlineModel.fit.rsquared_within.toFixed(3)}. F ={" "}
          {headlineModel.fit.f_statistic.toFixed(0)}. Significance:{" "}
          <span className="font-mono text-text-2">*** p&lt;0.01</span>{" "}
          <span className="font-mono text-text-3">·</span>{" "}
          <span className="font-mono text-text-2">** p&lt;0.05</span>{" "}
          <span className="font-mono text-text-3">·</span>{" "}
          <span className="font-mono text-text-2">* p&lt;0.10</span>.
        </p>
      </Section>

      {/* ----------------------------------------------------------------- */}
      {/* CTA                                                                */}
      {/* ----------------------------------------------------------------- */}
      <section className="mx-auto mt-32 max-w-[1280px] px-6">
        <div className="grid grid-cols-12 gap-6 border-t border-border pt-12">
          <div className="col-span-12 md:col-span-3">
            <div className="overline">Continue</div>
          </div>
          <div className="col-span-12 md:col-span-9">
            <h2 className="font-display text-subhead leading-[1.2] tracking-[-0.02em] text-text balance">
              <a className="hover:text-accent transition-colors" href="/corridor/USA-MEX">
                Look up your corridor →
              </a>
            </h2>
            <p className="mt-4 max-w-[560px] text-body text-text-2 leading-relaxed">
              {meta.n_corridors} corridors, {meta.n_providers} unique providers,{" "}
              {meta.n_quarters} quarters of history. Or read the{" "}
              <a
                href="/methodology"
                className="text-text underline underline-offset-4 hover:text-text-2"
              >
                methodology
              </a>{" "}
              to understand exactly what each percentage means and where it
              comes from.
            </p>
          </div>
        </div>
      </section>

      <Footer meta={meta} />
    </main>
  );
}

function HeroNumberInline({ value, unit }: { value: number; unit?: "B" | "M" | "K" }) {
  return (
    <span className="font-display text-hero md:text-hero-lg leading-[0.92] tracking-[-0.04em] inline-block translate-y-[6px]">
      <HeroNumber value={value} unit={unit} />
    </span>
  );
}

function Stat({
  label,
  value,
  note,
  tone = "neutral",
}: {
  label: string;
  value: string;
  note?: string;
  tone?: "neutral" | "amber" | "moss";
}) {
  const colour =
    tone === "amber"
      ? "text-accent"
      : tone === "moss"
      ? "text-accent-2"
      : "text-text";
  return (
    <div className="border-l border-border pl-4">
      <div className="overline">{label}</div>
      <div className={`mt-2 font-mono text-body-lg tabular-nums ${colour}`}>
        {value}
      </div>
      {note ? (
        <div className="mt-1 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
          {note}
        </div>
      ) : null}
    </div>
  );
}

function ForestRow({
  estimate,
  lo,
  hi,
}: {
  estimate: number;
  lo: number;
  hi: number;
}) {
  const dispMin = -8;
  const dispMax = 12;
  const range = dispMax - dispMin;
  const toPct = (v: number) =>
    ((Math.max(dispMin, Math.min(dispMax, v)) - dispMin) / range) * 100;
  const center = toPct(0);
  const left = toPct(Math.max(lo, dispMin));
  const right = toPct(Math.min(hi, dispMax));
  const dotX = toPct(estimate);
  const tone = estimate > 0 ? "var(--color-accent)" : "var(--color-accent-2)";

  return (
    <div className="relative h-6 self-center">
      <span
        className="absolute top-0 bottom-0 w-px bg-border-hi"
        style={{ left: `${center}%` }}
      />
      <span
        className="absolute top-1/2 h-px bg-text-3"
        style={{ left: `${left}%`, width: `${right - left}%` }}
      />
      <span
        className="absolute top-[8px] h-2 w-px bg-text-3"
        style={{ left: `${left}%` }}
      />
      <span
        className="absolute top-[8px] h-2 w-px bg-text-3"
        style={{ left: `${right}%` }}
      />
      <span
        className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 h-[8px] w-[8px] rounded-full"
        style={{ left: `${dotX}%`, background: tone }}
      />
    </div>
  );
}
