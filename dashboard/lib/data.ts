// Strict types matching the JSON shapes produced by pipeline/export.py and
// pipeline/aggregate.py. Edit here when the pipeline schema changes — never
// patch downstream components ad hoc.

import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";

// ---------------------------------------------------------------------------
// corridors.json
// ---------------------------------------------------------------------------

export interface CorridorCurrent {
  period: string | null;
  fee_pct: number | null;
  fx_margin_pct: number | null;
  speed_penalty_pct: number | null;
  tci_pct: number | null;
  tci_median_pct: number | null;
  tci_min_pct: number | null;
  tci_max_pct: number | null;
  total_cost_pct: number | null;
  days_to_arrive_mean: number | null;
  n_providers: number | null;
  n_observations: number | null;
}

export interface CorridorRolling {
  fee_pct: number | null;
  fx_margin_pct: number | null;
  speed_penalty_pct: number | null;
  tci_pct: number | null;
}

export interface CorridorHistoryPoint {
  period: string | null;
  fee_pct: number | null;
  fx_margin_pct: number | null;
  speed_penalty_pct: number | null;
  tci_pct: number | null;
  n_providers: number | null;
}

export interface CorridorProvider {
  firm: string | null;
  firm_type: string | null;
  fee_pct: number | null;
  fx_margin_pct: number | null;
  speed_penalty_pct: number | null;
  tci_pct: number | null;
  total_cost_pct: number | null;
  days_to_arrive: number | null;
}

export interface CorridorStablecoin {
  onramp_pct: number | null;
  offramp_pct: number | null;
  gas_pct: number | null;
  fx_spread_pct: number | null;
  total_pct: number | null;
  savings_pct: number | null;
  savings_pct_rolling_4q: number | null;
  volume_year: number | null;
  volume_usd_annual: number | null;
  savings_usd_annual: number | null;
  savings_usd_annual_rolling_4q: number | null;
}

export interface CorridorAmount {
  current: CorridorCurrent;
  rolling_4q: CorridorRolling;
  history: CorridorHistoryPoint[];
  providers: CorridorProvider[];
  stablecoin?: CorridorStablecoin;
}

export interface Corridor {
  id: string;
  source_code: string;
  source_name: string | null;
  source_region: string | null;
  destination_code: string;
  destination_name: string | null;
  destination_region: string | null;
  amounts: Record<string, CorridorAmount>;
}

export interface MetaDataSource {
  name: string;
  url?: string;
  release_file?: string;
  endpoint?: string;
  retrieval_date: string;
  scope_note?: string;
  year?: number;
  unit?: string;
  indicator?: string;
}

export interface MetaStablecoinAssumptions {
  gas_usd: number;
  onramp_pct: {
    default: number;
    developed: number;
    low_banked: number;
    developed_iso3: string[];
    low_banked_iso3: string[];
  };
  offramp_pct: {
    default: number;
    top_p2p: number;
    thin_liquidity: number;
    top_p2p_iso3: string[];
    thin_liquidity_iso3: string[];
  };
  fx_spread_pct: {
    deep: number;
    default: number;
    deep_iso3: string[];
  };
  note: string;
}

export interface CorridorsMeta {
  generated_at: string;
  panel_first_period: string;
  panel_last_period: string;
  n_quarters: number;
  n_corridors: number;
  n_providers: number;
  n_rows: number;
  send_amounts_usd: number[];
  headline_send_amount_usd: number;
  kappa_pct_per_day: number;
  weighting: string;
  weighting_note: string;
  stablecoin_assumptions: MetaStablecoinAssumptions;
  data_sources: {
    rpw: MetaDataSource;
    bilateral_remittance_matrix: MetaDataSource;
  };
  global_savings?: {
    send_amount_usd: number;
    n_corridors_with_volume: number;
    n_corridors_with_positive_savings: number;
    total_corridor_volume_usd: number;
    total_savings_usd_annual_current: number;
    total_savings_usd_annual_rolling4q: number;
    implied_avg_savings_pct_current: number;
    volume_year: number;
  };
}

export interface CorridorsPayload {
  meta: CorridorsMeta;
  corridors: Corridor[];
}

// ---------------------------------------------------------------------------
// diaspora_burden.json
// ---------------------------------------------------------------------------

export interface SenderTopDestination {
  destination_code: string;
  destination_name: string | null;
  tci_pct: number | null;
  sc_total_pct: number | null;
  savings_pct: number | null;
  volume_usd_annual: number | null;
  fee_burden_usd_annual: number | null;
  savings_usd_annual: number | null;
  rank: number | null;
}

export interface SenderRow {
  source_code: string;
  source_name: string | null;
  source_region: string | null;
  n_corridors: number;
  volume_usd_annual: number | null;
  fee_burden_usd_annual: number | null;
  fee_burden_usd_annual_rolling_4q: number | null;
  sc_savings_usd_annual: number | null;
  tci_volume_weighted_pct: number | null;
  tci_simple_mean_pct: number | null;
  sc_total_simple_mean_pct: number | null;
  sc_savings_pct_volume_weighted: number | null;
  fee_burden_share_global: number | null;
  top_destinations?: SenderTopDestination[];
}

export interface ReceiverRow {
  destination_code: string;
  destination_name: string | null;
  destination_region: string | null;
  n_corridors: number;
  inflow_usd_annual: number | null;
  fee_paid_usd_annual: number | null;
  sc_savings_usd_annual: number | null;
  tci_volume_weighted_pct: number | null;
  tci_simple_mean_pct: number | null;
}

export interface RankingCorridor {
  id: string;
  source_code: string;
  source_name: string | null;
  destination_code: string;
  destination_name: string | null;
  tci_pct: number | null;
  sc_total_pct: number | null;
  savings_pct: number | null;
  volume_usd_annual: number | null;
  fee_burden_usd_annual: number | null;
  savings_usd_annual: number | null;
  n_providers: number | null;
}

export interface DiasporaBurden {
  generated_at: string;
  headline: {
    send_amount_usd: number;
    n_corridors: number;
    n_senders: number;
    n_receivers: number;
    total_volume_usd: number;
    total_fee_burden_usd: number;
    total_sc_savings_usd: number;
    global_tci_volume_weighted_pct: number;
  };
  senders: SenderRow[];
  receivers: ReceiverRow[];
  rankings: {
    most_expensive: RankingCorridor[];
    cheapest: RankingCorridor[];
    biggest_absolute_savings: RankingCorridor[];
    biggest_fee_burden: RankingCorridor[];
  };
}

// ---------------------------------------------------------------------------
// operator_regression.json
// ---------------------------------------------------------------------------

export interface RegressionCoefficient {
  firm_type: string;
  estimate_pct: number;
  std_error_pct: number;
  t_stat: number;
  p_value: number;
  ci_low_pct: number;
  ci_high_pct: number;
  significance: string;
  n_observations_class: number;
}

export interface RegressionModel {
  send_amount_usd: number;
  specification: {
    model: string;
    dependent: string;
    reference_class: string;
    cluster_var: string;
    treatment_classes: string[];
  };
  fit: {
    n_observations: number;
    n_corridors: number;
    n_quarters: number;
    rsquared: number;
    rsquared_within: number;
    rsquared_between: number;
    rsquared_overall: number;
    f_statistic: number;
    f_pvalue: number;
  };
  firm_type_counts: Record<string, number>;
  coefficients: RegressionCoefficient[];
  notes: string[];
}

export interface RegressionPayload {
  generated_at: string;
  models: Record<string, RegressionModel>;
}

// ---------------------------------------------------------------------------
// Loaders — server-only, read from /public/data at request time. We rely on
// Next's static optimisation: every page that calls these is statically
// rendered at build because nothing depends on the request.
// ---------------------------------------------------------------------------

const DATA_DIR = path.join(process.cwd(), "public", "data");

async function readJson<T>(file: string): Promise<T> {
  const buf = await fs.readFile(path.join(DATA_DIR, file), "utf-8");
  return JSON.parse(buf) as T;
}

let _corridors: Promise<CorridorsPayload> | null = null;
let _burden: Promise<DiasporaBurden> | null = null;
let _regression: Promise<RegressionPayload> | null = null;

export function getCorridors(): Promise<CorridorsPayload> {
  if (!_corridors) _corridors = readJson<CorridorsPayload>("corridors.json");
  return _corridors;
}

export function getDiasporaBurden(): Promise<DiasporaBurden> {
  if (!_burden) _burden = readJson<DiasporaBurden>("diaspora_burden.json");
  return _burden;
}

export function getRegression(): Promise<RegressionPayload> {
  if (!_regression) _regression = readJson<RegressionPayload>("operator_regression.json");
  return _regression;
}

export async function getCorridorById(id: string): Promise<Corridor | null> {
  const { corridors } = await getCorridors();
  return corridors.find((c) => c.id === id) ?? null;
}

export async function getMeta(): Promise<CorridorsMeta> {
  const { meta } = await getCorridors();
  return meta;
}
