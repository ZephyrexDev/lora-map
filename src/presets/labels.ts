/** Human-readable labels for matrix config keys, shared between ClientSelector and MatrixConfig. */

export const HARDWARE_LABELS: Readonly<Record<string, string>> = {
  v3: "Heltec V3",
  v4: "Heltec V4",
} as const;

export const ANTENNA_LABELS: Readonly<Record<string, string>> = {
  ribbed_spring_helical: "Ribbed Spring Helical",
  duck_stubby: "Duck Stubby",
  bingfu_whip: "Bingfu Whip",
  slinkdsco_omni: "Slinkdsco Omni",
} as const;

export const TERRAIN_LABELS: Readonly<Record<string, string>> = {
  bare_earth: "Bare Earth (SRTM)",
  dsm: "Digital Surface Model",
  lulc_clutter: "LULC Clutter",
  weighted_aggregate: "Weighted Aggregate",
  worst_case: "Worst Case",
} as const;

export interface LabelOption {
  readonly key: string;
  readonly label: string;
}

/** Convert a labels record to an array of {key, label} options. */
export function labelsToOptions(labels: Readonly<Record<string, string>>): readonly LabelOption[] {
  return Object.entries(labels).map(([key, label]) => ({ key, label }));
}
