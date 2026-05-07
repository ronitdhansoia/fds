#!/usr/bin/env bash

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT" || exit 1

COLS=$(tput cols 2>/dev/null || echo 88)
[ "$COLS" -lt 80 ] && COLS=80
[ "$COLS" -gt 96 ] && COLS=96

E=$'\033'
RST="$E[0m"
B="$E[1m"; D="$E[2m"
AMB="$E[38;5;214m"     # accent
T1="$E[38;5;252m"      # primary text
T2="$E[38;5;245m"      # secondary
T3="$E[38;5;240m"      # tertiary / dividers
HI="$E[38;5;255m"      # bright white
GRN="$E[38;5;107m"     # success
RED="$E[38;5;167m"     # warning
HIDE="$E[?25l"
SHOW="$E[?25h"
CLR="$E[2J$E[H"

_strip() { printf '%s' "$1" | sed -E "s/$E\\[[0-9;]*m//g"; }

hr() {
  printf '%s' "$T3"
  printf '%*s' "$COLS" "" | tr ' ' '─'
  printf '%s\n' "$RST"
}

center() {
  local s="$1" raw
  raw=$(_strip "$s")
  local pad=$(( (COLS - ${#raw}) / 2 ))
  [ "$pad" -lt 0 ] && pad=0
  printf '%*s%s\n' "$pad" "" "$s"
}

box_top()   { printf '%s╭' "$T3"; printf '%*s' "$((COLS - 2))" "" | tr ' ' '─'; printf '╮%s\n' "$RST"; }
box_bot()   { printf '%s╰' "$T3"; printf '%*s' "$((COLS - 2))" "" | tr ' ' '─'; printf '╯%s\n' "$RST"; }
box_mid()   { printf '%s├' "$T3"; printf '%*s' "$((COLS - 2))" "" | tr ' ' '─'; printf '┤%s\n' "$RST"; }

box_line() {
  local text="$1" raw pad
  raw=$(_strip "$text")
  pad=$(( COLS - ${#raw} - 6 ))
  [ "$pad" -lt 0 ] && pad=0
  printf '%s│%s  %s%*s  %s│%s\n' "$T3" "$RST" "$text" "$pad" "" "$T3" "$RST"
}

box_empty() {
  printf '%s│%*s│%s\n' "$T3" "$((COLS - 2))" "" "$RST"
}

META_AVAILABLE=false
META_CORRIDORS="?"
META_PROVIDERS="?"
META_QUARTERS="?"
META_ROWS="?"
META_SAVINGS_B="?"
META_VOLUME_B="?"
META_PERIOD_TO="?"
META_GENERATED="?"

read_meta() {
  [ -f data/outputs/meta.json ] || return 0
  local data
  data=$(python3 - <<'PY' 2>/dev/null
import json, sys
try:
    m = json.load(open('data/outputs/meta.json'))
    g = m.get('global_savings', {}) or {}
    print(m.get('n_corridors', '?'))
    print(m.get('n_providers', '?'))
    print(m.get('n_quarters', '?'))
    print(m.get('n_rows', '?'))
    print(f"{(g.get('total_savings_usd_annual_current') or 0)/1e9:.2f}")
    print(f"{(g.get('total_corridor_volume_usd') or 0)/1e9:.0f}")
    print((m.get('panel_last_period') or '').replace('_', ' '))
    print((m.get('generated_at') or '')[:10])
except Exception:
    sys.exit(1)
PY
  )
  if [ -n "$data" ]; then
    META_AVAILABLE=true
    META_CORRIDORS=$(printf '%s' "$data" | sed -n 1p)
    META_PROVIDERS=$(printf '%s' "$data" | sed -n 2p)
    META_QUARTERS=$(printf '%s' "$data" | sed -n 3p)
    META_ROWS=$(printf '%s' "$data" | sed -n 4p)
    META_SAVINGS_B=$(printf '%s' "$data" | sed -n 5p)
    META_VOLUME_B=$(printf '%s' "$data" | sed -n 6p)
    META_PERIOD_TO=$(printf '%s' "$data" | sed -n 7p)
    META_GENERATED=$(printf '%s' "$data" | sed -n 8p)
  fi
}

_thousands() {
  printf '%s' "$1" | python3 -c 'import sys; v=sys.stdin.read().strip()
try: print(f"{int(v):,}")
except ValueError: print(v)'
}

git_state() {
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
      printf '%sgit clean%s' "$GRN" "$RST"
    else
      printf '%sgit dirty%s' "$RED" "$RST"
    fi
  else
    printf '%sno git%s' "$T3" "$RST"
  fi
}

data_state() {
  if [ "$META_AVAILABLE" = true ]; then
    printf '%sdata %s · panel %s%s' "$T2" "$META_GENERATED" "$META_PERIOD_TO" "$RST"
  else
    printf '%sdata not generated%s' "$RED" "$RST"
  fi
}

boot() {
  printf '%s%s' "$HIDE" "$CLR"
  printf '\n\n\n\n'

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
  sleep 0.16

  center "${T2}True Cost Index  ·  Stablecoin counterfactual${RST}"
  printf '\n'
  center "${T3}BITS Pilani Dubai  ·  Fundamentals of Data Science  ·  2026${RST}"
  printf '\n\n'
  sleep 0.30

  if [ "$META_AVAILABLE" = true ]; then
    local stats_w=58
    local stats_pad=$(( (COLS - stats_w) / 2 ))
    [ "$stats_pad" -lt 0 ] && stats_pad=0
    local rule
    rule=$(printf '%*s' "$stats_w" "" | tr ' ' '╌')

    printf '%*s%s%s%s\n\n' "$stats_pad" "" "$T3" "$rule" "$RST"

    _emit_stat() {
      local val="$1" label="$2"
      printf '%*s' "$stats_pad" ""
      printf '%s%-12s%s  %s%s%s\n' "$HI$B" "$val" "$RST" "$T3" "$label" "$RST"
      sleep 0.13
    }

    _emit_stat "$(_thousands "$META_CORRIDORS")"  "country corridors in the panel"
    _emit_stat "$(_thousands "$META_PROVIDERS")"  "providers across MTOs, banks, mobile money"
    _emit_stat "$META_QUARTERS"                   "quarters of history (latest $META_PERIOD_TO)"
    _emit_stat "\$$META_SAVINGS_B B/yr"           "recoverable on stablecoin rails"
    printf '\n'
    printf '%*s%s%s%s\n' "$stats_pad" "" "$T3" "$rule" "$RST"
  fi

  printf '\n\n'
  sleep 0.40
  printf '%s' "$SHOW"
}

draw_menu() {
  printf '%s' "$CLR"
  printf '\n'

  local now
  now=$(date '+%H:%M  ·  %a %d %b')

  local title_left="${B}${HI}MigrantMoney${RST}"
  local title_right="${T3}v1.0  ·  ${now}${RST}"
  local left_raw="MigrantMoney"
  local right_raw
  right_raw=$(_strip "$title_right")
  local gap=$(( COLS - ${#left_raw} - ${#right_raw} - 6 ))
  [ "$gap" -lt 0 ] && gap=0

  local status_left="$(data_state)"
  local status_right="$(git_state)"
  local sl_raw sr_raw
  sl_raw=$(_strip "$status_left")
  sr_raw=$(_strip "$status_right")
  local status_gap=$(( COLS - ${#sl_raw} - ${#sr_raw} - 6 ))
  [ "$status_gap" -lt 0 ] && status_gap=0

  box_top
  box_empty
  printf '%s│%s  %s%*s%s  %s│%s\n' "$T3" "$RST" "$title_left" "$gap" "" "$title_right" "$T3" "$RST"
  box_line "${T2}True Cost Index  ·  Stablecoin counterfactual${RST}"
  printf '%s│%s  %s%*s%s  %s│%s\n' "$T3" "$RST" "$status_left" "$status_gap" "" "$status_right" "$T3" "$RST"
  box_empty
  box_mid
  box_empty

  draw_section "PIPELINE" \
    "01" "full run"                "downloads RPW  ·  ~90s" \
    "02" "cached run"              "re-use data/raw  ·  ~20s" \
    "03" "fast cached run"         "skip figures  ·  ~10s"
  box_empty

  draw_section "INSPECT" \
    "04" "data summary"            "panel headline + top 5" \
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
  box_empty
  local foot_left="${T2}↵ run${RST}  ${T3}·${RST}  ${T2}q quit${RST}"
  local foot_right="${T3}github.com/ronitdhansoia/fds${RST}"
  local fl_visible=15
  local fr_raw
  fr_raw=$(_strip "$foot_right")
  local foot_gap=$(( COLS - fl_visible - ${#fr_raw} - 6 ))
  [ "$foot_gap" -lt 0 ] && foot_gap=0
  printf '%s│%s  %s%*s%s  %s│%s\n' "$T3" "$RST" "$foot_left" "$foot_gap" "" "$foot_right" "$T3" "$RST"
  box_empty
  box_bot
  printf '\n'
}

draw_section() {
  local title="$1"; shift
  box_line "${T3}${title}${RST}"
  while [ "$#" -ge 3 ]; do
    local num="$1" label="$2" sub="$3"; shift 3
    if [ -z "$sub" ]; then
      box_line "    ${AMB}${num}${RST}   ${T1}${label}${RST}"
    else
      local left_visible="    ${num}   ${label}"
      local gap=$(( COLS - ${#left_visible} - ${#sub} - 6 ))
      [ "$gap" -lt 0 ] && gap=0
      printf '%s│%s  ' "$T3" "$RST"
      printf '    %s%s%s   %s%s%s' "$AMB" "$num" "$RST" "$T1" "$label" "$RST"
      printf '%*s' "$gap" ""
      printf '%s%s%s' "$T3" "$sub" "$RST"
      printf '  %s│%s\n' "$T3" "$RST"
    fi
  done
}

launching() {
  local label="$1"
  printf '%s' "$CLR"
  printf '\n\n'
  local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
  local k
  for k in 0 1 2 3 4 5 6 7; do
    local f="${frames[$((k % 10))]}"
    printf '\r  %s%s%s  %s%s%s%s' "$AMB" "$f" "$RST" "$T2" "launching " "$RST" "$T1$label$RST"
    sleep 0.04
  done
  printf '\r%*s\r' 60 ''
}

header() {
  printf '%s' "$CLR"
  printf '\n  %s▸%s %s%s%s\n\n' "$AMB" "$RST" "$T2" "$1" "$RST"
  hr
  printf '\n'
}

require() {
  command -v "$1" >/dev/null 2>&1 && return 0
  printf '\n  %s!%s %s not on PATH.\n  %sinstall with:%s %s\n\n' \
    "$RED" "$RST" "$1" "$T3" "$RST" "$2"
  return 1
}

run_pipeline_full() {
  header "pipeline · full run"
  require uv "https://docs.astral.sh/uv/" || return 1
  uv run python scripts/run_all.py
}
run_pipeline_cached() {
  header "pipeline · cached"
  require uv "https://docs.astral.sh/uv/" || return 1
  uv run python scripts/run_all.py --skip-download
}
run_pipeline_fast() {
  header "pipeline · fast cached"
  require uv "https://docs.astral.sh/uv/" || return 1
  uv run python scripts/run_all.py --skip-download --skip-figures
}

show_summary() {
  if [ "$META_AVAILABLE" != true ]; then
    header "data summary"
    printf '  %s!%s data not generated yet. Run option %s01%s first.\n\n' \
      "$RED" "$RST" "$AMB" "$RST"
    return 0
  fi
  header "data summary"
  python3 - <<PY "$T1" "$T2" "$T3" "$AMB" "$HI" "$B" "$GRN" "$RST" "$COLS"
import json, sys
T1, T2, T3, AMB, HI, B, GRN, RST = sys.argv[1:9]
COLS = int(sys.argv[9])

m = json.load(open('data/outputs/meta.json'))
g = m['global_savings']

INNER = COLS - 6
LBL_W = 12

def kv(label, value, sub=''):
    label_s = f"{T3}{label:<{LBL_W}}{RST}"
    value_s = f"{HI}{B}{value}{RST}"
    sub_s = f"  {T3}{sub}{RST}" if sub else ''
    print(f"  {label_s}  {value_s}{sub_s}")

def hairline():
    print(f"  {T3}{'─' * (INNER + 2)}{RST}")

print()
kv("PANEL",     f"{m['panel_first_period']} → {m['panel_last_period']}", f"{m['n_quarters']} quarters")
kv("CORRIDORS", f"{m['n_corridors']:,}",  "country pair × send amount")
kv("PROVIDERS", f"{m['n_providers']:,}",  "banks · MTOs · mobile money · fintechs")
kv("ROWS",      f"{m['n_rows']:,}",       "after schema sniff and clean")
print()
hairline()
print()
kv("VOLUME",    f"\${g['total_corridor_volume_usd']/1e9:,.0f} B",       f"in scope · KNOMAD {g['volume_year']}")
kv("SAVINGS",   f"\${g['total_savings_usd_annual_current']/1e9:,.2f} B", "per year · stablecoin counterfactual")
kv("COVERAGE",  f"{g['n_corridors_with_positive_savings']} / {g['n_corridors_with_volume']}", "corridors with positive savings")
print()
hairline()
print()

try:
    payload = json.load(open('data/outputs/corridors.json'))
    corridors = payload.get('corridors', [])
    amount = str(m.get('headline_send_amount_usd', 200))

    rows = []
    for c in corridors:
        bucket = c.get('amounts', {}).get(amount, {}) or {}
        cur = bucket.get('current', {}) or {}
        tci = cur.get('tci_pct')
        if tci is None:
            continue
        src = (c.get('source_name') or c.get('source_code') or '?')[:14]
        dst = (c.get('destination_name') or c.get('destination_code') or '?')[:14]
        rows.append((tci, c.get('id'), src, dst))
    rows.sort(reverse=True, key=lambda x: x[0])
    top5 = rows[:5]

    print(f"  {T3}TOP 5 MOST EXPENSIVE  ·  USD {amount}{RST}")
    print()
    if top5:
        max_tci = top5[0][0] * 1.05
        BAR = 24
        for tci, cid, src, dst in top5:
            n = round(BAR * tci / max_tci)
            bar = ('█' * n) + ('░' * (BAR - n))
            route = f"{src} → {dst}"
            label = f"{route:<32}"
            tci_s = f"{tci:5.1f}%"
            print(f"  {T2}{label}{RST}  {AMB}{bar}{RST}  {HI}{tci_s}{RST}")
    print()
except Exception:
    pass
PY
}

show_top20()      { header "top 20 most expensive corridors"; require uv "https://docs.astral.sh/uv/" || return 1; uv run python -m pipeline.tci; }
show_regression() { header "operator-class regression"; require uv "https://docs.astral.sh/uv/" || return 1; uv run python -m pipeline.regression; }
show_stablecoin() { header "stablecoin savings"; require uv "https://docs.astral.sh/uv/" || return 1; uv run python -m pipeline.stablecoin; }

dashboard_dev() {
  header "dashboard · dev server"
  require pnpm "https://pnpm.io/installation" || return 1
  printf '   %surl%s    %shttp://localhost:3000%s\n' "$T3" "$RST" "$AMB" "$RST"
  printf '   %sstop%s   %sCtrl+C%s\n\n' "$T3" "$RST" "$T2" "$RST"
  ( cd "$PROJECT_ROOT/dashboard" && pnpm dev )
}
dashboard_build() {
  header "dashboard · production build"
  require pnpm "https://pnpm.io/installation" || return 1
  ( cd "$PROJECT_ROOT/dashboard" && pnpm build )
}

open_pdf() {
  header "open report PDF"
  if [ ! -f report/report.pdf ]; then
    printf '  %s!%s report/report.pdf not found.\n' "$RED" "$RST"
    return 1
  fi
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

prompt() {
  printf "  %s▸%s " "$AMB" "$RST"
  read -r choice
}

press_enter() {
  printf "\n  %s↵ press enter to return  %s·%s  %sq quit%s " \
    "$T3" "$T3" "$RST" "$T3" "$RST"
  read -r ack
  case "$ack" in
    q|Q|quit|exit) printf '%s' "$SHOW"; exit 0 ;;
  esac
}

normalize() {
  local n="$1"
  case "$n" in
    0[1-9]) printf '%s' "${n#0}" ;;
    *)      printf '%s' "$n" ;;
  esac
}

label_for() {
  case "$(normalize "$1")" in
    1)  echo "pipeline · full run" ;;
    2)  echo "pipeline · cached" ;;
    3)  echo "pipeline · fast cached" ;;
    4|summary|data) echo "data summary" ;;
    5|top|corridors|top20) echo "top 20 corridors" ;;
    6|reg|regression) echo "operator-class regression" ;;
    7|sc|stablecoin) echo "stablecoin savings" ;;
    8|dev|dash|dashboard) echo "dashboard dev server" ;;
    9|build) echo "dashboard production build" ;;
    10|pdf|report) echo "open report PDF" ;;
    11|repo|github|gh) echo "open GitHub repo" ;;
    12|tree|ls) echo "project tree" ;;
    *) echo "" ;;
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
    h|help|\?)
      printf '\n  %scommands:%s\n' "$T3" "$RST"
      printf '    01-12  menu items\n'
      printf '    summary, top, regression, stablecoin\n'
      printf '    dev, build, pdf, github, tree\n'
      printf '    q  quit\n\n'
      ;;
    *) printf "\n  %s!%s unknown: %s\n" "$RED" "$RST" "$1"; return 1 ;;
  esac
}

read_meta
if [ $# -gt 0 ]; then
  dispatch "$1"
  exit $?
fi

trap 'printf "%s" "$SHOW"; exit 0' INT TERM

boot
while true; do
  draw_menu
  prompt

  if [ -z "$choice" ]; then
    continue
  fi

  case "$(normalize "$choice")" in
    q|Q|quit|exit) printf '%s' "$SHOW"; exit 0 ;;
  esac

  lbl=$(label_for "$choice")
  if [ -n "$lbl" ]; then
    launching "$lbl"
  fi

  if dispatch "$choice"; then
    if [ "$(normalize "$choice")" != "8" ]; then
      press_enter
    fi
  else
    press_enter
  fi
done
