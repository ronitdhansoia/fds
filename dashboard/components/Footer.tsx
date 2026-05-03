import type { CorridorsMeta } from "@/lib/data";
import { fmtPeriod } from "@/lib/format";

export function Footer({ meta }: { meta: CorridorsMeta }) {
  const dataPeriod = fmtPeriod(meta.panel_last_period);

  return (
    <footer className="mt-32 border-t border-border">
      <div className="mx-auto flex max-w-[1280px] flex-wrap items-center gap-x-3 gap-y-2 px-6 py-10 font-mono text-overline tracking-[0.22em] uppercase text-text-3">
        <span>
          Data <span className="text-text-2">·</span>{" "}
          <span className="text-text-2">{dataPeriod}</span>
        </span>
        <Sep />
        <a
          href="https://remittanceprices.worldbank.org/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-text-2 hover:text-text transition-colors"
        >
          World Bank RPW ↗
        </a>
        <Sep />
        <a
          href="https://datacatalog.worldbank.org/dataset/remittance-prices-worldwide"
          target="_blank"
          rel="noopener noreferrer"
          className="text-text-3 hover:text-text-2 transition-colors"
        >
          Catalog
        </a>
        <span className="ml-auto text-text-3">
          BITS Pilani Dubai · Fundamentals of Data Science · 2026
        </span>
      </div>
    </footer>
  );
}

function Sep() {
  return <span className="text-text-3" aria-hidden>·</span>;
}
