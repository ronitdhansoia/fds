import type { CorridorsMeta } from "@/lib/data";
import { fmtPeriod } from "@/lib/format";

export function Footer({ meta }: { meta: CorridorsMeta }) {
  const generated = new Date(meta.generated_at).toISOString().slice(0, 10);
  return (
    <footer className="mt-32 border-t border-border">
      <div className="mx-auto grid max-w-[1280px] grid-cols-12 gap-6 px-6 py-12 font-mono text-overline tracking-[0.18em] uppercase text-text-3">
        <div className="col-span-12 md:col-span-3">
          <div className="text-text">MigrantMoney</div>
          <div className="mt-2 text-text-3 normal-case tracking-normal">
            BITS Pilani Dubai · Fundamentals of Data Science · 2026
          </div>
        </div>
        <dl className="col-span-12 grid grid-cols-2 gap-x-6 gap-y-2 md:col-span-6 md:grid-cols-3">
          <div>
            <dt>Panel</dt>
            <dd className="mt-1 text-text-2 normal-case tracking-normal">
              {fmtPeriod(meta.panel_first_period)} – {fmtPeriod(meta.panel_last_period)}
            </dd>
          </div>
          <div>
            <dt>Corridors</dt>
            <dd className="mt-1 text-text-2 normal-case tracking-normal">
              {meta.n_corridors}
            </dd>
          </div>
          <div>
            <dt>Build</dt>
            <dd className="mt-1 text-text-2 normal-case tracking-normal">{generated}</dd>
          </div>
        </dl>
        <div className="col-span-12 md:col-span-3 md:text-right">
          <a
            className="text-text-2 hover:text-text transition-colors"
            href="https://remittanceprices.worldbank.org/"
            target="_blank"
            rel="noopener noreferrer"
          >
            Source · World Bank RPW
          </a>
        </div>
      </div>
    </footer>
  );
}
