import presets from './presets.json';

export interface FrequencyPreset {
  region: string;
  code: string;
  frequency_mhz: number;
  max_power_dbm: number | null;
}

export const FREQUENCY_PRESETS: readonly FrequencyPreset[] = presets.frequencies;
