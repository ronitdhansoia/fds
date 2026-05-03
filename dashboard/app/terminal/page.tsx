import type { Metadata } from "next";

import { Footer } from "@/components/Footer";
import { Terminal } from "@/components/Terminal";
import { TopBar } from "@/components/TopBar";
import { getCorridors, getRegression } from "@/lib/data";

export const metadata: Metadata = {
  title: "Terminal",
  description:
    "Query the MigrantMoney corridor panel from a command line. Eleven " +
    "commands, all reading the same JSON the dashboard does.",
};

export default async function TerminalPage() {
  const [{ corridors, meta }, regression] = await Promise.all([
    getCorridors(),
    getRegression(),
  ]);

  return (
    <main>
      <TopBar active="terminal" />

      <section className="mx-auto max-w-[1280px] px-6 pt-20 pb-10">
        <div className="grid grid-cols-12 gap-x-6 gap-y-6">
          <div className="col-span-12 lg:col-span-7">
            <h1
              className="font-display text-text leading-[0.92] tracking-[-0.04em]"
              style={{
                fontSize: "clamp(48px, 8.4vw, 112px)",
                fontVariationSettings: "'opsz' 144, 'SOFT' 60, 'WONK' 0",
              }}
            >
              MigrantMoney
              <br />
              <span className="text-text-3">Terminal.</span>
            </h1>
          </div>

          <div className="col-span-12 lg:col-span-5 lg:pt-3">
            <p className="text-body-lg text-text-2 leading-[1.6] pretty max-w-[440px]">
              Eleven commands over the same JSON the dashboard reads. Top corridors,
              per-provider TCI, the operator-class regression, the stablecoin
              counterfactual, all from a prompt.
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-2 font-mono text-overline tracking-[0.18em] uppercase">
              <span className="rounded-[2px] border border-border bg-surface px-3 py-1.5 text-text-2">
                ./migrantmoney.sh
              </span>
              <span className="text-text-3">type help to start</span>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1280px] px-6 pb-32">
        <Terminal corridors={corridors} regression={regression} meta={meta} />

        <p className="mt-6 max-w-[680px] text-body text-text-3 leading-[1.7] pretty">
          The terminal runs entirely in the browser. There is no server round
          trip, no rate limit, and no authentication. Every command is a pure
          function over the static JSON in <code className="font-mono text-text-2">/public/data</code>.
          Source code:{" "}
          <a
            href="https://github.com/ronitdhansoia/fds/blob/main/dashboard/components/Terminal.tsx"
            target="_blank"
            rel="noopener noreferrer"
            className="text-text-2 hover:text-text underline underline-offset-4"
          >
            Terminal.tsx
          </a>
          .
        </p>
      </section>

      <Footer meta={meta} />
    </main>
  );
}
