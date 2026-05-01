# MigrantMoney — dashboard

Editorial, dark-themed Next.js 16 dashboard for the True Cost Index +
stablecoin counterfactual. Static — reads pre-computed JSON from
`public/data/`, no runtime backend.

## Run

```bash
pnpm install
pnpm dev          # http://localhost:3000
pnpm build        # production
pnpm start
```

## Refreshing the data

The dashboard reads from
`public/data/{corridors,meta,diaspora_burden,operator_regression}.json`,
produced by `pipeline/export.py`. After a pipeline run:

```bash
cp ../data/outputs/*.json public/data/
```

## Stack

- Next.js 16 (App Router, Turbopack default)
- React 19.2
- Tailwind CSS v4 (theme via `@theme` block in `app/globals.css`, no
  `tailwind.config.ts` file)
- `next/font/google` — Fraunces (display, variable axes), Geist Sans,
  Geist Mono
- `framer-motion` — orchestrated reveal + count-up + comparison-bar grow
- `d3-geo` + `topojson-client` — world map drawn in vanilla SVG (no
  `react-simple-maps`; that 3.x package has a React-19 peer-dep mismatch)
- `katex` — methodology page formulas
- `i18n-iso-countries` — feeds `lib/m49.ts` with the M49 → ISO3 map used
  to join topojson features to corridor data

## Pages

- `/` — landing. Hero count-up + world choropleth + four ranking tables +
  inline regression forest plot.
- `/corridor/[id]` — explorer. Sticky combobox picker, factual headline
  sentence, TCI-vs-stablecoin comparison bar, ranked provider list,
  quarterly history line, annual aggregate callout. Statically generated
  for all 368 corridors.
- `/methodology` — 680 px reading column. Every formula in KaTeX inside a
  hairline-bordered surface, every constant exposed in a definition-list,
  data sources with retrieval dates, limitations enumerated.

## Deploy

```bash
vercel login                        # one-time, interactive
cd dashboard && vercel deploy --prod
```

The repository ships preview-friendly defaults — no env vars required.

## Aesthetic

Locked in `app/globals.css` `@theme`. Background `#0A0A0A`, surface
`#111`, hairlines `#1F1F1F`. Single amber accent `#D97706` for cost,
moss green `#65A30D` for savings. SVG fractalNoise grain at 4% opacity
fixed-positioned across the page. No emoji. No gradients except the one
warm shadow under the landing hero. No box shadows — borders only.

Typography: Fraunces for display + hero numbers (variable opsz=144);
Geist Sans for body; Geist Mono for tabular figures and overlines (with
`font-feature-settings: "tnum", "ss01"`). Inline prose numerics use a
proportional `.num` utility so periods don’t yawn between digits.
