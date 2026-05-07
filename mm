#!/usr/bin/env bash
# MigrantMoney CLI · pure-bash TUI for live demos.
#
#   ./mm              interactive menu
#   ./mm <n>          run item n directly and exit (e.g. ./mm 4)
#   ./mm <name>       same, by alias (e.g. ./mm summary)
#
# Zero external deps. Tuned for macOS Terminal.app and iTerm2.

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT" || exit 1

# ─────────────────────────────────────────────────────────────────────────
#  Geometry
# ─────────────────────────────────────────────────────────────────────────
COLS=$(tput cols 2>/dev/null || echo 88)
[ "$COLS" -lt 80 ] && COLS=80
[ "$COLS" -gt 96 ] && COLS=96

# ─────────────────────────────────────────────────────────────────────────
#  Palette  ·  amber accent over greyscale, mirrors the dashboard
# ─────────────────────────────────────────────────────────────────────────
E=$'\033'
RST="$E[0m"
B="$E[1m"; D="$E[2m"
AMB="$E[38;5;214m"     # accent
T1="$E[38;5;252m"      # primary text
T2="$E[38;5;245m"      # secondary
T3="$E[38;5;240m"      # tertiary  / dividers
HI="$E[38;5;255m"      # bright white
GRN="$E[38;5;107m"
HIDE="$E[?25l"
SHOW="$E[?25h"
CLR="$E[2J$E[H"

# ─────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────

# Strip ANSI escape codes for visible-width measurement.
_strip() { printf '%s' "$1" | sed -E "s/$E\\[[0-9;]*m//g"; }

# Print a horizontal line of `─` filling COLS.
hr() {
  printf '%s' "$T3"
  printf '%*s' "$COLS" "" | tr ' ' '─'
  printf '%s\n' "$RST"
}

# Center a string in COLS columns.
center() {
  local s="$1" raw
  raw=$(_strip "$s")
  local pad=$(( (COLS - ${#raw}) / 2 ))
  [ "$pad" -lt 0 ] && pad=0
  printf '%*s%s\n' "$pad" "" "$s"
}

# Box drawing.
box_top()   { printf '%s╭' "$T3"; printf '%*s' "$((COLS - 2))" "" | tr ' ' '─'; printf '╮%s\n' "$RST"; }
box_bot()   { printf '%s╰' "$T3"; printf '%*s' "$((COLS - 2))" "" | tr ' ' '─'; printf '╯%s\n' "$RST"; }
box_mid()   { printf '%s├' "$T3"; printf '%*s' "$((COLS - 2))" "" | tr ' ' '─'; printf '┤%s\n' "$RST"; }

# Print a line inside the box. Layout: `│  <text><padding>  │`
# Visible width = 1 + 2 + len(text) + pad + 2 + 1 = 6 + len + pad = COLS
box_line() {
  local text="$1" raw pad
  raw=$(_strip "$text")
  pad=$(( COLS - ${#raw} - 6 ))
  [ "$pad" -lt 0 ] && pad=0
  printf '%s│%s  %s%*s  %s│%s\n' "$T3" "$RST" "$text" "$pad" "" "$T3" "$RST"
}

# Empty box line.
box_empty() {
  printf '%s│%*s│%s\n' "$T3" "$((COLS - 2))" "" "$RST"
}

# ─────────────────────────────────────────────────────────────────────────
#  Boot animation  ·  ~1.5 s total
# ─────────────────────────────────────────────────────────────────────────
boot() {
  printf '%s%s' "$HIDE" "$CLR"
  printf '\n\n\n\n\n'

  # Type the project name letter-by-letter, centered.
  local name="MIGRANTMONEY"
  local pad=$(( (COLS - ${#name}) / 2 ))
  printf '%*s' "$pad" ""
  local i ch
  for (( i=0; i<${#name}; i++ )); do
    ch="${name:$i:1}"
    printf '%s%s%s' "$B$HI" "$ch" "$RST"
    sleep 0.022
  done
  printf '\n\n'
  sleep 0.18

  # Tagline fades in (no real fade, but the delay creates rhythm).
  center "${T2}True Cost Index  ·  Stablecoin counterfactual${RST}"
  printf '\n'
  center "${T3}BITS Pilani Dubai  ·  Fundamentals of Data Science  ·  2026${RST}"
  printf '\n\n\n'
  sleep 0.45

  printf '%s' "$SHOW"
}

# ─────────────────────────────────────────────────────────────────────────
#  Main menu
# ─────────────────────────────────────────────────────────────────────────
draw_menu() {
  printf '%s' "$CLR"
  printf '\n'

  local now
  now=$(date '+%H:%M  ·  %a %d %b')

  # Right-justified meta on the title line.
  local title_left="${B}${HI}MigrantMoney${RST}"
  local title_right="${T3}v1.0  ·  ${now}${RST}"
  local left_raw="MigrantMoney"
  local right_raw
  right_raw=$(_strip "$title_right")
  local gap=$(( COLS - ${#left_raw} - ${#right_raw} - 6 ))
  [ "$gap" -lt 0 ] && gap=0

  box_top
  box_empty
  printf '%s│%s  %s%*s%s  %s│%s\n' "$T3" "$RST" "$title_left" "$gap" "" "$title_right" "$T3" "$RST"
  box_line "${T2}True Cost Index  ·  Stablecoin counterfactual${RST}"
  box_empty
  box_mid
  box_empty

  draw_section "PIPELINE" \
    "01" "full run"                "downloads RPW  ·  ~90s" \
    "02" "cached run"              "re-use data/raw  ·  ~20s" \
    "03" "fast cached run"         "skip figures  ·  ~10s"
  box_empty

  draw_section "INSPECT" \
    "04" "data summary"            "panel headline" \
    "05" "top 20 most expensive corridors" "" \
    "06" "operator-class regression"       "" \
    "07" "stablecoin savings"      ""
  box_empty

  draw_section "DASHBOARD" \
    "08" "dev server"              "localhost:3000" \
    "09" "production build"        ""
  box_empty

  draw_section "ARTEFACTS" \
    "10" "open report PDF"         "" \
    "11" "open GitHub repo"        "" \
    "12" "project tree"            ""
  box_empty

  box_mid
  local foot_left="${T2}↵ run${RST}  ${T3}·${RST}  ${T2}q quit${RST}"
  local foot_right="${T3}github.com/ronitdhansoia/fds${RST}"
  local fl_raw="↵ run  ·  q quit"
  local fr_raw
  fr_raw=$(_strip "$foot_right")
  # ↵ may render as 1 column in most terms.
  local fl_visible=15
  local foot_gap=$(( COLS - fl_visible - ${#fr_raw} - 6 ))
  [ "$foot_gap" -lt 0 ] && foot_gap=0
  box_empty
  printf '%s│%s  %s%*s%s  %s│%s\n' "$T3" "$RST" "$foot_left" "$foot_gap" "" "$foot_right" "$T3" "$RST"
  box_empty
  box_bot
  printf '\n'
}

# Render one menu section: title, then triplets of (num, label, sub).
draw_section() {
  local title="$1"; shift
  box_line "${T3}${title}${RST}"
  while [ "$#" -ge 3 ]; do
    local num="$1" label="$2" sub="$3"; shift 3
    # left = "    NN   label"  ·  right = "sub"
    # NN highlighted amber, label normal, sub T3 right-aligned.
    local left_visible="    ${num}   ${label}"
    local right_visible="$sub"
    local gap=$(( COLS - ${#left_visible} - ${#right_visible} - 6 ))
    [ "$gap" -lt 0 ] && gap=0
    if [ -z "$sub" ]; then
      box_line "    ${AMB}${num}${RST}   ${T1}${label}${RST}"
    else
      printf '%s│%s  ' "$T3" "$RST"
      printf '    %s%s%s   %s%s%s' "$AMB" "$num" "$RST" "$T1" "$label" "$RST"
      printf '%*s' "$gap" ""
      printf '%s%s%s' "$T3" "$sub" "$RST"
      printf '  %s│%s\n' "$T3" "$RST"
    fi
  done
}

# ─────────────────────────────────────────────────────────────────────────
#  Command handlers
# ─────────────────────────────────────────────────────────────────────────

# Print a standard "running" header before the actual output.
header() {
  printf '%s' "$CLR"
  printf '\n  %s▸%s %s%s%s\n\n' "$AMB" "$RST" "$T2" "$1" "$RST"
  hr
  printf '\n'
}

run_pipeline_full()   { header "pipeline · full run";        uv run python scripts/run_all.py; }
run_pipeline_cached() { header "pipeline · cached";          uv run python scripts/run_all.py --skip-download; }
run_pipeline_fast()   { header "pipeline · fast cached";     uv run python scripts/run_all.py --skip-download --skip-figures; }

show_summary() {
  header "data summary"
  python3 - <<PY "$T1" "$T2" "$T3" "$AMB" "$HI" "$B" "$RST" "$COLS"
import json, sys

T1, T2, T3, AMB, HI, B, RST = sys.argv[1:8]
COLS = int(sys.argv[8])

m = json.load(open('data/outputs/meta.json'))
g = m['global_savings']

def line(label, value, sub=''):
    label_s = f"{T3}{label:<14}{RST}"
    value_s = f"{HI}{B}{value}{RST}"
    sub_s = f"  {T3}{sub}{RST}" if sub else ''
    print(f"   {label_s}  {value_s}{sub_s}")

def rule():
    print(f"   {T3}{'─' * (COLS - 6)}{RST}")

print()
line("PANEL",     f"{m['panel_first_period']} → {m['panel_last_period']}", f"{m['n_quarters']} quarters")
line("CORRIDORS", f"{m['n_corridors']:,}",  "country pair × send amount")
line("PROVIDERS", f"{m['n_providers']:,}",  "banks · MTOs · mobile money · fintechs")
line("ROWS",      f"{m['n_rows']:,}",       "after schema sniff and clean")
print()
rule()
print()
line("VOLUME",    f"\${g['total_corridor_volume_usd']/1e9:,.0f} B",       f"in scope · KNOMAD {g['volume_year']}")
line("SAVINGS",   f"\${g['total_savings_usd_annual_current']/1e9:,.2f} B", "per year · stablecoin counterfactual")
line("COVERAGE",  f"{g['n_corridors_with_positive_savings']} / {g['n_corridors_with_volume']}", "corridors with positive savings")
print()
PY
}

show_top20()      { header "top 20 most expensive corridors"; uv run python -m pipeline.tci; }
show_regression() { header "operator-class regression"; uv run python -m pipeline.regression; }
show_stablecoin() { header "stablecoin savings"; uv run python -m pipeline.stablecoin; }

dashboard_dev()   {
  header "dashboard · dev server"
  printf '   %surl%s    %shttp://localhost:3000%s\n' "$T3" "$RST" "$AMB" "$RST"
  printf '   %sstop%s   %sCtrl+C%s\n\n' "$T3" "$RST" "$T2" "$RST"
  ( cd "$PROJECT_ROOT/dashboard" && pnpm dev )
}
dashboard_build() { header "dashboard · production build"; ( cd "$PROJECT_ROOT/dashboard" && pnpm build ); }

open_pdf()    {
  header "open report PDF"
  printf '   %s→%s opening %sreport/report.pdf%s\n' "$AMB" "$RST" "$T2" "$RST"
  open report/report.pdf
  sleep 0.3
}
open_github() {
  header "open GitHub repo"
  printf '   %s→%s opening %sgithub.com/ronitdhansoia/fds%s\n' "$AMB" "$RST" "$T2" "$RST"
  open https://github.com/ronitdhansoia/fds
  sleep 0.3
}

show_tree() {
  header "project tree"
  if command -v tree >/dev/null 2>&1; then
    tree -L 2 -I 'node_modules|.next|.venv|__pycache__|.turbo|.playwright-mcp|raw|processed|*.tsbuildinfo'
  else
    printf '   %stree not installed; falling back to ls%s\n\n' "$T3" "$RST"
    ls -la
    printf '\n   %shint%s  brew install tree\n' "$T3" "$RST"
  fi
}

# ─────────────────────────────────────────────────────────────────────────
#  Prompt + dispatch
# ─────────────────────────────────────────────────────────────────────────
prompt() {
  printf "  %s▸%s " "$AMB" "$RST"
  read -r choice
}

press_enter() {
  printf "\n  %s↵ press enter to return%s " "$T3" "$RST"
  read -r _
}

# Strip a single leading zero so 01..09 work like 1..9.
normalize() {
  local n="$1"
  case "$n" in
    0[1-9]) printf '%s' "${n#0}" ;;
    *)      printf '%s' "$n" ;;
  esac
}

dispatch() {
  local n
  n=$(normalize "$1")
  case "$n" in
    1)                            run_pipeline_full ;;
    2)                            run_pipeline_cached ;;
    3)                            run_pipeline_fast ;;
    4|summary|data)               show_summary ;;
    5|top|corridors|top20)        show_top20 ;;
    6|reg|regression)             show_regression ;;
    7|sc|stablecoin)              show_stablecoin ;;
    8|dev|dash|dashboard)         dashboard_dev ;;
    9|build)                      dashboard_build ;;
    10|pdf|report)                open_pdf ;;
    11|repo|github|gh)            open_github ;;
    12|tree|ls)                   show_tree ;;
    q|Q|quit|exit)                printf '%s' "$SHOW"; exit 0 ;;
    "")                           return 1 ;;
    *) printf "\n  %sunknown:%s %s\n" "$AMB" "$RST" "$1"; return 1 ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────
#  Direct mode  ·  ./mm <n|name>  runs once and exits
# ─────────────────────────────────────────────────────────────────────────
if [ $# -gt 0 ]; then
  dispatch "$1"
  exit $?
fi

# ─────────────────────────────────────────────────────────────────────────
#  Interactive mode
# ─────────────────────────────────────────────────────────────────────────
trap 'printf "%s" "$SHOW"; exit 0' INT TERM

boot
while true; do
  draw_menu
  prompt
  if dispatch "$choice"; then
    # Item 8 (dashboard dev server) blocks until Ctrl-C; no need to wait.
    [ "$(normalize "$choice")" != "8" ] && press_enter
  else
    press_enter
  fi
done
