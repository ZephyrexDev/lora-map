import presets from './presets.json';

export interface AntennaPreset {
  name: string;
  gain_dbi: number;
  swr: number;
}

export const ANTENNA_PRESETS: readonly AntennaPreset[] = presets.antennas;

export function mismatchLoss(swr: number): number {
  return -10 * Math.log10(1 - ((swr - 1) / (swr + 1)) ** 2);
}
