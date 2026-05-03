#!/usr/bin/env bash
# MigrantMoney project CLI. A small interactive menu that wraps every
# command a grader (or future-you) would want during a demo.
#
# Usage:    ./mm
# Direct:   ./mm <number>           runs that menu item once and exits
# Direct:   ./mm pipeline | dash | summary | corridors | regression | pdf | repo

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# ----- ANSI helpers (Mac Terminal, iTerm, VS Code terminal all support these)
B=$'\033[1m'; D=$'\033[2m'; R=$'\033[0m'
AMB=$'\033[38;5;214m'; CY=$'\033[38;5;110m'; GR=$'\033[38;5;245m'

clear_screen() { printf '\033[2J\033[H'; }

banner() {
  printf "\n  ${B}MigrantMoney${R}  ${D}True Cost Index + stablecoin counterfactual${R}\n"
  printf "  ${GR}BITS Pilani Dubai · Fundamentals of Data Science · 2026${R}\n"
  printf "  ${GR}repo · github.com/ronitdhansoia/fds${R}\n"
  printf "  ${D}─────────────────────────────────────────────────────────────${R}\n"
}

menu() {
  cat <<EOF

  ${CY}PIPELINE${R}
   ${B} 1${R}  Full run                ${D}downloads fresh RPW · ~90 s${R}
   ${B} 2${R}  Cached run              ${D}re-uses data/raw · ~20 s${R}
   ${B} 3${R}  Fast cached run         ${D}skip figures · ~10 s${R}

  ${CY}INSPECT${R}
   ${B} 4${R}  Data summary            ${D}meta.json headline numbers${R}
   ${B} 5${R}  Top-20 most expensive corridors
   ${B} 6${R}  Operator-class regression coefficients
   ${B} 7${R}  Stablecoin savings summary

  ${CY}DASHBOARD${R}
   ${B} 8${R}  Dev server              ${D}pnpm dev → http://localhost:3000${R}
   ${B} 9${R}  Production build        ${D}pnpm build${R}

  ${CY}ARTEFACTS${R}
   ${B}10${R}  Open report PDF
   ${B}11${R}  Open GitHub repo in browser
   ${B}12${R}  Show project tree

   ${B} q${R}  Quit
EOF
}

prompt() {
  printf "\n  ${AMB}choose ▸${R} "
  read -r choice
}

press_to_continue() {
  printf "\n  ${D}press enter to return to menu${R} "
  read -r _
}

# ----- check core deps once
require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf "\n  ${AMB}!${R} ${1} not found on PATH.\n  Install with: ${D}%s${R}\n" "$2"
    return 1
  fi
}

run_pipeline_full()  { uv run python scripts/run_all.py; }
run_pipeline_cached(){ uv run python scripts/run_all.py --skip-download; }
run_pipeline_fast()  { uv run python scripts/run_all.py --skip-download --skip-figures; }

show_summary() {
  python3 - <<'PY'
import json
m = json.load(open('data/outputs/meta.json'))
g = m['global_savings']
print()
print(f"  Panel              {m['panel_first_period']} → {m['panel_last_period']}  ({m['n_quarters']} quarters)")
print(f"  Corridors          {m['n_corridors']:,}")
print(f"  Providers          {m['n_providers']:,}")
print(f"  Rows               {m['n_rows']:,}")
print()
print(f"  Volume in scope    ${g['total_corridor_volume_usd']/1e9:,.1f} B   (KNOMAD {g['volume_year']})")
print(f"  Stablecoin savings ${g['total_savings_usd_annual_current']/1e9:,.2f} B / year")
print(f"  Coverage           {g['n_corridors_with_positive_savings']} of {g['n_corridors_with_volume']} corridors with positive savings")
print(f"  Generated          {m['generated_at']}")
print()
PY
}

show_top20()      { uv run python -m pipeline.tci; }
show_regression() { uv run python -m pipeline.regression; }
show_stablecoin() { uv run python -m pipeline.stablecoin; }

dashboard_dev()   { ( cd "$PROJECT_ROOT/dashboard" && pnpm dev ); }
dashboard_build() { ( cd "$PROJECT_ROOT/dashboard" && pnpm build ); }

open_pdf()    { open report/report.pdf; }
open_github() { open https://github.com/ronitdhansoia/fds; }

show_tree() {
  if command -v tree >/dev/null 2>&1; then
    tree -L 2 -I 'node_modules|.next|.venv|__pycache__|.turbo|.playwright-mcp|raw|processed|*.tsbuildinfo'
  else
    printf "  ${D}tree not installed; falling back to ls${R}\n\n"
    ls -la
    printf "\n  ${D}Hint: brew install tree${R}\n"
  fi
}

dispatch() {
  case "$1" in
    1|pipeline|full)         run_pipeline_full ;;
    2|cached)                run_pipeline_cached ;;
    3|fast)                  run_pipeline_fast ;;
    4|summary|data)          show_summary ;;
    5|corridors|top|top20)   show_top20 ;;
    6|regression|reg)        show_regression ;;
    7|stablecoin|sc)         show_stablecoin ;;
    8|dash|dev)              dashboard_dev ;;
    9|build)                 dashboard_build ;;
    10|pdf|report)           open_pdf ;;
    11|repo|github)          open_github ;;
    12|tree|ls)              show_tree ;;
    q|Q|quit|exit)           exit 0 ;;
    "")                      return 1 ;;
    *) printf "\n  ${AMB}?${R} unknown option: %s\n" "$1"; return 1 ;;
  esac
}

# Direct mode: ./mm 4   (runs once, exits)
if [ $# -gt 0 ]; then
  dispatch "$1"
  exit $?
fi

# Interactive mode
while true; do
  clear_screen
  banner
  menu
  prompt
  if dispatch "$choice"; then
    # Some commands (pnpm dev) block until the user hits ctrl-c. When they
    # do, we want to come back to the menu, not exit. So always pause here.
    [ "$choice" != "8" ] && press_to_continue
  else
    press_to_continue
  fi
done
