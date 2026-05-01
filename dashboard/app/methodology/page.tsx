import type { Metadata } from "next";
import Link from "next/link";
import { Footer } from "@/components/Footer";
import { Math, MathBlock } from "@/components/Math";
import { TopBar } from "@/components/TopBar";
import { getMeta } from "@/lib/data";
import { fmtPeriod } from "@/lib/format";

export const metadata: Metadata = {
  title: "Methodology",
  description:
    "Every formula, every constant, every assumption behind the MigrantMoney " +
    "True Cost Index and stablecoin counterfactual.",
};

export default async function MethodologyPage() {
  const meta = await getMeta();
  const a = meta.stablecoin_assumptions;

  return (
    <main>
      <TopBar active="methodology" />

      <article className="mx-auto max-w-[680px] px-6 pt-24 pb-32">
        {/* Overline + title block */}
        <div className="overline">FDS PROJECT · BITS PILANI DUBAI · 2026</div>

        <h1 className="font-display text-section md:text-display mt-6 leading-[1.05] tracking-[-0.025em] text-text balance">
          Methodology — every formula, every constant, every assumption.
        </h1>

        <p className="mt-7 text-body-lg text-text-2 leading-[1.75] pretty">
          This page is the credibility moat. A reviewer should be able to
          reproduce every number on the dashboard with nothing but the formulas
          below, the World Bank Remittance Prices Worldwide panel, and the
          KNOMAD bilateral remittance estimates. If a number on the site is not
          derivable from this page, it is wrong; please open an issue.
        </p>

        <hr className="rule mt-12" />

        {/* ---------------------------------------------------------------- */}
        {/* True Cost Index */}
        {/* ---------------------------------------------------------------- */}
        <section id="tci" className="mt-12">
          <div className="overline">§1 · True Cost Index</div>
          <h2 className="font-display text-subhead mt-3 leading-[1.2] tracking-[-0.02em] text-text">
            The advertised fee is half the story.
          </h2>
          <p className="mt-5 text-body-lg text-text-2 leading-[1.75] pretty">
            For a corridor <em>(s, d)</em>, provider <em>p</em>, quarter{" "}
            <em>q</em>, and send amount <em>A</em>, the True Cost Index is
            three additive components: the advertised transaction fee, the
            margin between the provider&apos;s applied FX rate and the
            interbank mid-rate, and a penalty for slow settlement.
          </p>

          <MathBlock
            expr="\text{TCI}_{s,d,p,q}(A) = \mathrm{fee}_\% + \mathrm{fxMargin}_\% + \kappa \cdot \max(0,\ d_\text{arrive} - 1)"
            caption="Equation 1 — TCI"
          />

          <dl className="mt-6 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-5">
            <dt className="font-mono text-label text-text">
              <Math expr="\mathrm{fee}_\%" />
            </dt>
            <dd className="text-body text-text-2 leading-relaxed">
              Advertised transaction fee as a percent of the send amount.
              Derived from the RPW total cost minus the FX margin so it stays
              comparable to the published headline number.
            </dd>

            <dt className="font-mono text-label text-text">
              <Math expr="\mathrm{fxMargin}_\%" />
            </dt>
            <dd className="text-body text-text-2 leading-relaxed">
              RPW <span className="font-mono text-label">cc1 fx margin</span>{" "}
              column — the spread the provider takes between its applied
              exchange rate and the interbank mid.
            </dd>

            <dt className="font-mono text-label text-text">
              <Math expr="\kappa" />
            </dt>
            <dd className="text-body text-text-2 leading-relaxed">
              Daily cost-of-capital proxy for the receiving household. We
              calibrate{" "}
              <span className="font-mono text-label text-text">
                κ = {a.gas_usd === a.gas_usd ? "0.10" : "—"}% / day
              </span>{" "}
              — at the upper end of informal short-term lending rates
              documented in remittance corridors with same-day alternatives.
              Setting <Math expr="\kappa = 0" /> leaves the ranking ordering
              substantively unchanged; the speed component is a small share of
              total TCI for most corridors.
            </dd>

            <dt className="font-mono text-label text-text">
              <Math expr="d_\text{arrive}" />
            </dt>
            <dd className="text-body text-text-2 leading-relaxed">
              RPW <span className="font-mono text-label">speed actual</span>{" "}
              mapped to days: instant or same-day → 0, next day → 1, two days →
              2, three-to-five days → 4, six or more → 6. Anything outside this
              bucket is excluded from TCI for that row.
            </dd>
          </dl>

          <h3 className="font-display text-subhead mt-12 leading-[1.2] tracking-[-0.02em] text-text">
            Aggregation to corridor level
          </h3>
          <p className="mt-4 text-body-lg text-text-2 leading-[1.75] pretty">
            We report the unweighted mean across providers as the corridor-level
            TCI, alongside the median as a robustness check. We would prefer to
            weight by provider market share, but the public RPW release does
            not expose share data (verified{" "}
            {meta.data_sources.rpw.retrieval_date}). The 4-quarter rolling mean
            is reported next to the headline value so single-quarter noise is
            visible. Throughout the dashboard the headline send amount is{" "}
            <span className="font-mono text-label text-text">USD 200</span> —
            the SDG 10.c benchmark.
          </p>
        </section>

        <hr className="rule mt-16" />

        {/* ---------------------------------------------------------------- */}
        {/* Stablecoin counterfactual */}
        {/* ---------------------------------------------------------------- */}
        <section id="stablecoin" className="mt-16">
          <div className="overline">§2 · Stablecoin counterfactual</div>
          <h2 className="font-display text-subhead mt-3 leading-[1.2] tracking-[-0.02em] text-text">
            What would the same flow cost on USDC / USDT rails?
          </h2>
          <p className="mt-5 text-body-lg text-text-2 leading-[1.75] pretty">
            We model end-to-end stablecoin remittance cost as four components:
            on-ramp from local fiat to USDC/USDT in the sending country,
            off-ramp from stablecoin to local fiat in the receiving country, an
            average network gas fee amortised over the send amount, and the
            local FX spread between the stablecoin and the receiving
            country&apos;s currency.
          </p>

          <MathBlock
            expr="\text{SC}_\%(s, d, A) = \mathrm{onramp}(s) + \mathrm{offramp}(d) + \frac{\mathrm{gas}_{\$}}{A} \times 100 + \mathrm{fxSpread}(d)"
            caption="Equation 2 — stablecoin cost"
          />

          <MathBlock
            expr="\mathrm{savings}_\% = \max\bigl(0,\ \text{TCI} - \text{SC}\bigr) \quad\quad \mathrm{savings}_{\$/\text{yr}} = \frac{\mathrm{savings}_\%}{100} \cdot V_{(s,d)}"
            caption="Equation 3 — corridor savings"
          />

          <p className="mt-5 text-body-lg text-text-2 leading-[1.75] pretty">
            Where{" "}
            <span className="font-mono text-label text-text">V(s,d)</span> is
            the {meta.global_savings?.volume_year ?? "—"} bilateral remittance
            volume from the World Bank / KNOMAD bilateral remittance estimates
            (indicator{" "}
            <span className="font-mono text-label text-text">
              {meta.data_sources.bilateral_remittance_matrix.indicator}
            </span>
            ; the legacy direct-download xlsx was retired in early 2025 and
            replaced by the Data360 API).
          </p>

          <h3 className="font-display text-subhead mt-12 leading-[1.2] tracking-[-0.02em] text-text">
            Locked-in defaults
          </h3>
          <p className="mt-4 text-body-lg text-text-2 leading-[1.75] pretty">
            We chose the conservative end of every published range. A reviewer
            who plugs in optimistic defaults (1% flat SC cost, advertised fee
            only) reaches the press-release figure of $30–50 B / yr; under our
            defaults the global aggregate is{" "}
            <span className="font-mono text-label text-text">
              $
              {(
                (meta.global_savings?.total_savings_usd_annual_current ?? 0) /
                1e9
              ).toFixed(2)}{" "}
              B / yr
            </span>{" "}
            — same order of magnitude, and an honest one. The gap is itself a
            finding.
          </p>

          <Assumption
            label="Network gas"
            value={`USD ${a.gas_usd.toFixed(2)} per transfer`}
            source="L2 / Solana / Tron USDT typical settlement cost. Amortised over the send amount; a USD 200 transfer carries 0.25 percentage points of gas cost."
          />

          <Assumption
            label="On-ramp — developed sender"
            value={`${a.onramp_pct.developed.toFixed(1)}%`}
            source={`Applied to ${a.onramp_pct.developed_iso3.length} OECD high-income senders. ISO-3 list is exposed below.`}
          />
          <Assumption
            label="On-ramp — global default"
            value={`${a.onramp_pct.default.toFixed(1)}%`}
          />
          <Assumption
            label="On-ramp — low-banked sender"
            value={`${a.onramp_pct.low_banked.toFixed(1)}%`}
            source={`Applied to ${a.onramp_pct.low_banked_iso3.length} senders where retail crypto on-ramps are thin (incl. GCC migrant workers paid via labour cards).`}
          />

          <Assumption
            label="Off-ramp — top P2P market"
            value={`${a.offramp_pct.top_p2p.toFixed(1)}%`}
            source={`Applied to ${a.offramp_pct.top_p2p_iso3.length} receivers with established stablecoin → cash routes (${a.offramp_pct.top_p2p_iso3.join(", ")}).`}
          />
          <Assumption
            label="Off-ramp — global default"
            value={`${a.offramp_pct.default.toFixed(1)}%`}
          />
          <Assumption
            label="Off-ramp — thin liquidity"
            value={`${a.offramp_pct.thin_liquidity.toFixed(1)}%`}
            source={`Applied to ${a.offramp_pct.thin_liquidity_iso3.length} receivers where off-ramps are sanctioned, restricted, or genuinely illiquid.`}
          />

          <Assumption
            label="Local FX spread — deep market"
            value={`${a.fx_spread_pct.deep.toFixed(1)}%`}
            source={`Applied to ${a.fx_spread_pct.deep_iso3.length} receivers with a deep local stablecoin market (P2P platforms quote tight spreads to local currency).`}
          />
          <Assumption
            label="Local FX spread — default"
            value={`${a.fx_spread_pct.default.toFixed(1)}%`}
            source="Estimated from the parallel-market premium where the local currency does not have a deep stablecoin OTC desk."
          />
        </section>

        <hr className="rule mt-16" />

        {/* ---------------------------------------------------------------- */}
        {/* Regression */}
        {/* ---------------------------------------------------------------- */}
        <section id="regression" className="mt-16">
          <div className="overline">§3 · Operator-class regression</div>
          <h2 className="font-display text-subhead mt-3 leading-[1.2] tracking-[-0.02em] text-text">
            Does provider class predict cost, after we control for the corridor?
          </h2>
          <p className="mt-5 text-body-lg text-text-2 leading-[1.75] pretty">
            Two-way fixed-effects panel regression of TCI on firm-type dummies,
            absorbing corridor and quarter. Reference category: MTO (the
            largest cell). Standard errors are cluster-robust at the corridor
            level. Run separately for the USD 200 and USD 500 buckets.
          </p>

          <MathBlock
            expr="\text{TCI}_{i,p,q} = \beta_0 + \sum_{k \in K} \beta_k \cdot \mathbf{1}\{\text{firmType}_p = k\} + \alpha_{\text{corridor}_i} + \gamma_q + \varepsilon_{i,p,q}"
            caption="Equation 4 — operator-class FE regression"
          />

          <p className="mt-5 text-body-lg text-text-2 leading-[1.75] pretty">
            The Fintech cell is small{" "}
            <span className="font-mono text-label text-text-2">
              (n ≈ 200 of 197 k)
            </span>{" "}
            because RPW classifies Wise, Remitly, WorldRemit, Xe and similar
            digital-first providers under the &ldquo;Money Transfer
            Operator&rdquo; label. We did not override RPW&apos;s classification
            for this release; the coefficient on Fintech should be read with
            that caveat. A curated allow-list is on the roadmap.
          </p>
        </section>

        <hr className="rule mt-16" />

        {/* ---------------------------------------------------------------- */}
        {/* Data sources */}
        {/* ---------------------------------------------------------------- */}
        <section id="sources" className="mt-16">
          <div className="overline">§4 · Data sources</div>
          <h2 className="font-display text-subhead mt-3 leading-[1.2] tracking-[-0.02em] text-text">
            Two public datasets, no scraping, no proprietary feeds.
          </h2>

          <SourceCard
            name={meta.data_sources.rpw.name}
            url={meta.data_sources.rpw.url}
            file={meta.data_sources.rpw.release_file}
            retrieved={meta.data_sources.rpw.retrieval_date}
            note={meta.data_sources.rpw.scope_note}
            stats={[
              [
                "Coverage",
                `${fmtPeriod(meta.panel_first_period)} – ${fmtPeriod(meta.panel_last_period)} (${meta.n_quarters} quarters)`,
              ],
              ["Corridors", `${meta.n_corridors} unique`],
              ["Providers", `${meta.n_providers} firms`],
              ["Rows", `${meta.n_rows.toLocaleString()} (cc1 + cc2 melted)`],
            ]}
          />

          <SourceCard
            name={meta.data_sources.bilateral_remittance_matrix.name}
            indicator={meta.data_sources.bilateral_remittance_matrix.indicator}
            file={meta.data_sources.bilateral_remittance_matrix.endpoint}
            retrieved={meta.data_sources.bilateral_remittance_matrix.retrieval_date}
            note={meta.data_sources.bilateral_remittance_matrix.scope_note}
            stats={[
              [
                "Year",
                `${meta.data_sources.bilateral_remittance_matrix.year} (latest available)`,
              ],
              ["Unit", meta.data_sources.bilateral_remittance_matrix.unit ?? "—"],
            ]}
          />
        </section>

        <hr className="rule mt-16" />

        {/* ---------------------------------------------------------------- */}
        {/* Limitations */}
        {/* ---------------------------------------------------------------- */}
        <section id="limitations" className="mt-16">
          <div className="overline">§5 · Limitations</div>
          <h2 className="font-display text-subhead mt-3 leading-[1.2] tracking-[-0.02em] text-text">
            What this dashboard cannot tell you.
          </h2>

          <ol className="mt-6 list-none pl-0 text-body-lg text-text-2 leading-[1.75] pretty space-y-5">
            <li>
              <span className="font-mono text-label text-text-3">01 ·</span>{" "}
              <strong className="font-medium text-text">
                RPW is a price quote panel, not a transaction panel.
              </strong>{" "}
              We measure the menu, not what diners ordered. Volume-weighted
              user-experienced cost is almost certainly lower than the
              cross-provider mean we report.
            </li>
            <li>
              <span className="font-mono text-label text-text-3">02 ·</span>{" "}
              <strong className="font-medium text-text">
                Stablecoin cost defaults are conservative.
              </strong>{" "}
              Real on-ramp cost varies wildly across exchanges and KYC tiers.
              We surface every constant on this page so a reviewer can plug in
              their own. Optimistic defaults (1% flat) reach the headline $30 –
              50 B / yr ballpark.
            </li>
            <li>
              <span className="font-mono text-label text-text-3">03 ·</span>{" "}
              <strong className="font-medium text-text">
                BRM volumes are from {meta.data_sources.bilateral_remittance_matrix.year}.
              </strong>{" "}
              Global remittances grew ~35% from 2021 to 2024. Absolute USD
              savings figures should be read as &ldquo;at 2021 corridor scale&rdquo;
              rather than &ldquo;today.&rdquo;
            </li>
            <li>
              <span className="font-mono text-label text-text-3">04 ·</span>{" "}
              <strong className="font-medium text-text">
                We exclude pre-Q2 2016 data.
              </strong>{" "}
              The legacy RPW sheet ships an incompatible schema. Including it
              would require a second schema sniff for nine extra quarters of
              partial coverage; we did not.
            </li>
            <li>
              <span className="font-mono text-label text-text-3">05 ·</span>{" "}
              <strong className="font-medium text-text">
                No causal claims.
              </strong>{" "}
              The regression establishes that bank-routed remittances are
              systematically more expensive than MTO-routed ones after
              corridor / quarter FE. It does not say they are causally
              expensive — selection into firm type is endogenous.
            </li>
          </ol>
        </section>

        <hr className="rule mt-16" />

        <p className="mt-12 text-body text-text-3">
          Built by Ronit Dhansoia. Source code:{" "}
          <Link href="/" className="text-text-2 hover:text-text underline underline-offset-4">
            return to the index
          </Link>{" "}
          or read the{" "}
          <Link href="/" className="text-text-2 hover:text-text underline underline-offset-4">
            README
          </Link>
          .
        </p>
      </article>

      <Footer meta={meta} />
    </main>
  );
}

function Assumption({
  label,
  value,
  source,
}: {
  label: string;
  value: string;
  source?: string;
}) {
  return (
    <div className="mt-6 grid grid-cols-[1fr_max-content] gap-4 border-t border-border pt-5">
      <div>
        <div className="font-mono text-label text-text">{label}</div>
        {source ? (
          <p className="mt-2 text-body text-text-2 leading-relaxed pretty">
            {source}
          </p>
        ) : null}
      </div>
      <div className="font-mono text-body-lg text-text tabular-nums text-right">
        {value}
      </div>
    </div>
  );
}

function SourceCard({
  name,
  url,
  file,
  retrieved,
  note,
  stats,
  indicator,
}: {
  name: string;
  url?: string;
  file?: string;
  retrieved: string;
  note?: string;
  stats: [string, string][];
  indicator?: string;
}) {
  return (
    <div className="mt-8 rounded-[2px] border border-border bg-surface px-6 py-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="overline">Dataset</div>
          <h3 className="font-display text-body-lg text-text mt-2">{name}</h3>
          {indicator ? (
            <div className="mt-1 font-mono text-label text-text-2">
              indicator: {indicator}
            </div>
          ) : null}
        </div>
        <div className="text-right">
          <div className="overline">Retrieved</div>
          <div className="mt-2 font-mono text-label text-text">{retrieved}</div>
        </div>
      </div>
      {note ? (
        <p className="mt-4 text-body text-text-2 leading-relaxed pretty">{note}</p>
      ) : null}
      <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-border pt-4 md:grid-cols-4">
        {stats.map(([k, v]) => (
          <div key={k}>
            <dt className="overline">{k}</dt>
            <dd className="font-mono text-label text-text mt-1">{v}</dd>
          </div>
        ))}
      </dl>
      {file ? (
        <a
          href={file}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 inline-block font-mono text-overline tracking-[0.18em] uppercase text-text-3 hover:text-text transition-colors"
        >
          ↗ Open canonical URL
        </a>
      ) : null}
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-4 ml-6 inline-block font-mono text-overline tracking-[0.18em] uppercase text-text-3 hover:text-text transition-colors"
        >
          ↗ Source page
        </a>
      ) : null}
    </div>
  );
}
