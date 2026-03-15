export interface AntennaPreset {
  name: string;
  gain_dbi: number;
  swr: number;
}

export const ANTENNA_PRESETS: readonly AntennaPreset[] = [
  { name: "Ribbed Spring Helical", gain_dbi: 0, swr: 3.0 },
  { name: "Duck Stubby", gain_dbi: 1, swr: 3.5 },
  { name: "Bingfu Whip", gain_dbi: 2.5, swr: 1.8 },
  { name: "Slinkdsco Omni", gain_dbi: 4, swr: 1.1 },
];

export function mismatchLoss(swr: number): number {
  return -10 * Math.log10(1 - ((swr - 1) / (swr + 1)) ** 2);
}
