# Dashboard Critique — Round 1
Date: 2026-05-01
Vercel preview: not yet deployed (local prod build at http://localhost:3002)
Round-1 screenshots: `dashboard/critique/screenshots/round-1/{home,methodology,corridor}-{1440,1920,390}.png`

## Method

Captured 9 screenshots (3 routes × 3 viewports). Reviewed each against the
matrix in the critique brief. Grep-audited the codebase for anti-pattern
violations. Read the prod console output for unexpected warnings.

Findings are scored against the spec in `dashboard_prompt.md`. P0 = the
aesthetic breaks; P1 = inconsistency; P2 = real polish.

## Summary

- Pages reviewed: 3
- Total findings: 11
- P0 (must fix): 3
- P1 (should fix): 5
- P2 (polish): 3

---

## Findings

### [P0] Geist Mono kerning ruins inline numerics in prose

**Pages:** all three.
**Locations:**
  - `app/page.tsx` hero paragraph (`5.00%`, `$5.22 B`, `$200`).
  - `app/corridor/[id]/page.tsx` headline sentence (`5.18%`, `1.29%`, `2.75%`).
  - `app/methodology/page.tsx` slider readouts (`vs $2.15 B at default…`).
  - `app/page.tsx` annual aggregate callout (`$2.72 B`, `$1.28 B`, `$52 595 342 546`).

**Evidence:** every inline numeric span (`.num`, `<span className="font-mono…">`)
renders `5.18%` as `5 . 18%` — Geist Mono's monospace cell width pads the
period to a full glyph, leaving a one-em gap on each side. See
`screenshots/round-1/corridor-1440.png` at (442, 158) — the headline reads
"costs on average **5 . 18%** — or as little as **1 . 29%** via". This is
the single most visible irritant on the entire site and looks wrong, not
"editorial." Spec says mono is for **tables, charts, KPIs** — not inline
prose.

**Fix:** introduce a `.num-prose` utility (Geist Sans + tabular figures via
`font-feature-settings: "tnum","ss01","cv11"`). Use it for every inline
numeric in prose contexts (hero paragraph, corridor headline, sliders'
"vs default" line, annual aggregate sentence). Keep `.font-mono` for
table cells, KPIs, overlines, and chart labels where alignment matters.

---

### [P0] `backdrop-blur-sm` is glassmorphism — explicitly banned

**Pages:** all three (top bar) + corridor explorer (sticky picker).
**Locations:**
  - `components/TopBar.tsx:5` — `bg-bg/80 backdrop-blur-sm`.
  - `components/CorridorPicker.tsx:53` — `bg-bg/85 backdrop-blur-sm`.

**Evidence:** spec § anti-patterns lists "Glassmorphism / frosted blur
effects" as auto-reject. `backdrop-blur-sm` blurs whatever scrolls under
the sticky bar, producing the frosted-glass look. Visible faintly when the
amber world map slides under the top bar in `screenshots/round-1/home-1440.png`.

**Fix:** drop `backdrop-blur-sm` and the alpha (`bg-bg/80`) on both
elements. Use solid `bg-bg` and rely on the existing `border-b border-border`
hairline to delimit. The dashboard is dark — there's no contrast story
that requires a blur.

---

### [P0] Corridor explorer top bar overflows on mobile (390 px)

**Page:** /corridor/[id]
**Location:** `components/CorridorPicker.tsx` — single flex row of
SEND FROM / arrow / SEND TO / amount toggle.

**Evidence:** `screenshots/round-1/corridor-390.png` shows the picker
crushed onto one line: "SEND FROM United States USA → SEND TO Mexico" with
the right-side amount toggle (`$200 $500`) clipped off the viewport. The
country names truncate to two lines inside their slots. The page is
unusable on phones — you can't change amount, can't see which country
slot you're in.

**Fix:** make the picker stack vertically below `md` — SEND FROM on its
own row, then SEND TO, then the amount toggle as a third row. Drop the
SEND FROM/SEND TO overlines on mobile (the country name + ISO code is
self-explanatory). Add a top divider so the stacked rows read as a list,
not a wall.

---

### [P1] Hero overline wraps to 3 lines at 1920 px wide

**Page:** /
**Location:** `app/page.tsx` hero, `RevealItem order={0}` —
`<div className="overline">FDS · BITS Pilani Dubai · Data as of 2025 Q1</div>`
inside a `lg:col-span-2` (≈ 213 px) left rail.

**Evidence:** `screenshots/round-1/home-1920.png` (250, 144) — the
overline reads:
```
FDS · BITS PILANI
DUBAI · DATA AS OF
2025 Q1
```
That's three lines for what should be one. The 2-column left rail is too
narrow for the text at 11 px tracking-widest mono. At 1920 the page has
plenty of horizontal room.

**Fix:** widen the left rail in the hero to `lg:col-span-3` (matching the
other left-rail sections), or shorten the overline to "FDS · BITS Pilani
Dubai" and move "Data as of 2025 Q1" to a second tighter line on purpose.
Either way it should not wrap mid-word.

---

### [P1] SensitivitySliders logs a warning on every methodology load

**Page:** /methodology
**Location:** `components/SensitivitySliders.tsx` `useEffect` — first-render
verification compares flat-default to pipeline-precise totals.

**Evidence:** prod console shows
`[SensitivitySliders] flat defaults give $2.15B vs pipeline-precise $5.22B
— gap 58.8%. This is expected: the pipeline uses per-country tiered
defaults, the slider applies a flat scenario.` on every page load. The spec
asked us to *verify* the gap and warn when over 0.1%; we now warn 100% of
the time, which makes the warning meaningless and pollutes the prod
console of every visitor.

**Fix:** demote to `console.debug` (which is suppressed in default browser
log levels) or gate behind `process.env.NODE_ENV === "development"`. The
gap is a documented design decision, not a runtime concern.

---

### [P1] Stale `<select>`-style inner box-shadow on the combobox dropdown

**Page:** /corridor/[id]
**Location:** `components/CorridorPicker.tsx:139` —
`shadow-[0_0_0_1px_rgba(0,0,0,0.6)]`.

**Evidence:** the combobox dropdown ships an inset 1 px black shadow on
top of its `border-border-hi` border. Visually it's a doubled hairline,
which fights the rest of the dashboard where every panel uses a single
hairline border. Spec says "use borders, not shadows, in dark mode."

**Fix:** delete the `shadow-[…]` arbitrary value. Keep the
`border-border-hi`. The dropdown already pops because of the surface fill
and z-index.

---

### [P1] "1.3 B SAVABLE" in the ticker uses a different unit format

**Page:** /
**Location:** `components/HeadlineTicker.tsx` `formatSavings()` produces
`$1.3 B`, `$285 M`, `$249 M`, `$135 M` etc. while the rest of the dashboard
formats compact USD as `$1.28 B`, `$285 M` (one decimal max for B values).

**Evidence:** ticker shows `$1.3 B SAVABLE` but the corridor explorer for
USA-MEX shows the same number as `$1.28 B`. Two formatters of the same
quantity in the same session.

**Fix:** route the ticker's `formatSavings` through
`lib/format.ts::fmtUsdCompact` so all "USD compact" output goes through
one function. Drop the duplicate.

---

### [P1] Headlines mention provider names without linking to them

**Page:** /corridor/[id]
**Location:** `app/corridor/[id]/page.tsx` headline sentence —
"...as little as **1.29%** via **Walmart2World**."

**Evidence:** Walmart2World is plain text. The provider list two screens
below is the source of that fact. A reader who reads the sentence and
wants to find Walmart2World has to scroll, scan, and visually match. The
typography and color carry no affordance that the name is a destination.

**Fix:** make the cheapest-provider name an in-page anchor link to the
provider list (or scroll the row into view + briefly highlight). At minimum
underline-on-hover so the affordance exists.

---

### [P2] Hero number breaks the headline rhythm at 1440

**Page:** /
**Location:** `app/page.tsx` — `text-section md:text-display` headline
with inline `text-hero md:text-hero-lg` hero number.

**Evidence:** the 56 px → 128 px size swap mid-line forces the line height
to 128 px for the entire first line, leaving the surrounding text "Migrants
paid roughly" floating at the baseline of an oversized line. The effect
reads as confident editorial layout to me, but a reviewer might call it a
collision rather than a deliberate juxtaposition.

**Fix (defer):** consider a tighter version where the hero number sits on
its own line below the smaller text, or above it as a heading. Hold for
P2 — current state is defensible and follows the spec's "hero number on
the same baseline" instruction.

---

### [P2] Distribution histogram dominated by zero-savings bin

**Page:** /methodology
**Location:** `components/SensitivitySliders.tsx::SavingsHistogram`.

**Evidence:** at conservative defaults (`?onramp=3.0&offramp=4.0&gas=2.0&fx=3.0`)
192 of 349 corridors have zero savings under the flat scenario, all
binning into the leftmost bar. Visual story collapses to "one tall bar."

**Fix (defer):** either (a) plot only positive-savings corridors and add a
subhead "of N corridors that benefit," or (b) use a sqrt-y-axis. Honest
representation of zeros is fine for now; the coverage line above the chart
already says "X of 349 corridors."

---

### [P2] No view-transition on corridor switch

**Page:** /corridor/[id]
**Location:** `components/CorridorPicker.tsx` — `router.push` on slot
change.

**Evidence:** spec asked for "numbers tween between values" on corridor
switch — we currently do a full Next page navigation. The hero number,
provider list, and history chart blink rather than morph. Felt better to
defer this until React 19.2's `ViewTransition` lands more cleanly in Next
16.

**Fix (defer):** wrap the corridor page body in `<ViewTransition>` once
the API settles, or build a client-side sub-route that shares mounted
chart state and tweens values via framer-motion `animate(motionValue, …)`.
Significant refactor; not worth this round.

---

## Resolution Plan (Phase D order)

1. **Geist Mono prose kerning** (P0) — single CSS class change,
   `app/globals.css` + sweep of inline numeric spans.
2. **Drop `backdrop-blur-sm`** (P0) — two lines.
3. **Mobile picker stack** (P0) — `components/CorridorPicker.tsx` layout.
4. **Hero overline wrap** (P1) — `app/page.tsx` rail width or text trim.
5. **Sensitivity warning gate** (P1) — `console.debug` or NODE_ENV gate.
6. **Drop combobox box-shadow** (P1) — one line.
7. **Ticker uses fmtUsdCompact** (P1) — three-line refactor.
8. **Provider-name in-page link** (P1) — small JSX change.

Do P0s first, rebuild, screenshot, commit each. Then P1s. Stop before P2.

---

## Resolution Summary

- **P0 fixed: 3 / 3**
  1. Geist Mono prose kerning → `.num` re-routed to Geist Sans + tabular
     figures. Commit `1b41a7e`.
  2. `backdrop-blur-sm` glassmorphism on TopBar + CorridorPicker → solid
     `bg-bg` with hairline borders. Commit `0fa24c3`.
  3. Corridor explorer top bar overflowed at 390 px → mobile-stack
     layout (SEND FROM / SEND TO / Amount each on own row, hairline-
     separated). Commit `0fa24c3`.

- **P1 fixed: 5 / 5**
  4. Hero overline wrap on 1920 wide viewports → widened left rail to
     `lg:col-span-3` and split into two deliberate lines. Commit
     `0fa24c3`.
  5. SensitivitySliders log spam in prod console → demoted to
     `console.debug` and gated on `NODE_ENV === 'development'`. Commit
     `0fa24c3`.
  6. Combobox dropdown inset 1 px shadow → removed. Commit `0fa24c3`.
  7. Ticker had its own `formatSavings()` → routed through
     `lib/format.ts::fmtUsdCompact` for consistent compact USD across
     the dashboard. Commit `0fa24c3`.
  8. Cheapest provider mention in headline was plain text → wrapped in
     an in-page anchor to `#providers` with subtle decoration that
     lifts on hover. Commit `0fa24c3`.

- **P2 deferred (3):**
  - Hero number breaking the headline rhythm at 1440 px — defensible
    and matches the "hero number on the same baseline" spec.
  - Distribution histogram dominated by zero-savings bin under
    conservative defaults — coverage line above the chart already
    surfaces the zero count.
  - View transition on corridor switch — defer until React 19.2's
    `ViewTransition` settles in Next 16. Significant refactor.

- **Commits:**
  - `1b41a7e` fix(critique-p0/1): drop Geist Mono from inline prose numerics
  - `0fa24c3` fix(critique-p0/2/3 + p1): glassmorphism, mobile picker, overline wrap, ticker, sensitivity log

- **Final preview URL:** local prod build at `http://localhost:3002`;
  Vercel deploy still requires `vercel login` (interactive auth).

---

## Before / After Highlights

### 1. Inline prose numerics — the single biggest visual fix

**Before** (round-1, corridor 1440):
`screenshots/round-1/corridor-1440.png`

> "Sending **$200** from United States to Mexico costs on average **5 . 18%** — or as little as **1 . 29%** via Walmart2World. Stablecoin rails would cost **2 . 75%**."

The Geist Mono cell width pads every period and percent sign, and the headline reads as glitchy spacing rather than editorial typography.

**After** (final, corridor 1440):
`screenshots/final/corridor-1440.png`

> "Sending **$200** from United States to Mexico costs on average **5.18%** — or as little as **1.29%** via Walmart2World. Stablecoin rails would cost **2.75%**."

Periods sit tight to digits, the sentence reads as a single editorial statement, the colour accents on the percentages now register as emphasis instead of as gap-bridging.

### 2. Mobile corridor explorer — usable instead of broken

**Before** (round-1, corridor 390):
`screenshots/round-1/corridor-390.png`

The top bar crushes "SEND FROM United States USA → SEND TO Mexico" onto a single overflowed row; the amount toggle is clipped off the viewport. Country labels truncate. Page is essentially unusable on a phone.

**After** (fix screenshot, corridor 390):
`screenshots/fixes/p0-3-corridor-mobile-after.png`

Each picker slot stacks vertically, separated by hairlines: SEND FROM / United States · USA, SEND TO / Mexico · MEX, AMOUNT / $200 · $500. Country names render in full. Amount toggle is reachable. The headline sentence below picks up the prose-numeric fix automatically: "5.18%", "1.29%", "2.75%" all clean.

### 3. Hero overline at wide viewports — one ragged sentence becomes two confident lines

**Before** (round-1, home 1920):
`screenshots/round-1/home-1920.png`

The 2-column left rail forced the overline to wrap mid-word:
```
FDS · BITS PILANI
DUBAI · DATA AS OF
2025 Q1
```

**After** (final, home 1440):
`screenshots/final/home-1440.png`

Rail widened to 3 columns, the overline split into two deliberate lines:
```
FDS · BITS PILANI DUBAI
DATA AS OF 2025 Q1
```

The data-period line is in `--text-3` so it reads as a sub-line of the institutional credit, not a separate fact competing with it.

---

## Self-honesty pass — second look

Three things I deliberately left as P2 that a reviewer might still flag:

1. The hero number's vertical positioning — at 1440 px wide it sits *to the right of* "Migrants paid roughly," forcing the rest of "last year to move their own money." onto a second line of equal weight. I argued this is the editorial composition working; a senior designer might disagree and want the hero number on its own line beneath a smaller framing sentence.

2. The KPI quad on the home page still uses Geist Mono ("$5.22 B" rendering as "$5 . 22 B" within the small KPI block). I justified keeping mono there because the four KPIs are vertically aligned and the tabular alignment matters more than the period gap. Borderline.

3. The corridor picker on desktop is still a single horizontal row — I made it stack only below `md`. At 1440 it's fine, but the SEND FROM / SEND TO labels are quite small and the combobox affordance (the underline below the country name) is the only visual signal that this is interactive. A more confident treatment would size up the picker or make the slots feel more like buttons.

If the user critique mentions any of these, address in a Round 2 pass.
