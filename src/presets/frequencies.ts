export interface FrequencyPreset {
  region: string;
  code: string;
  frequency_mhz: number;
  max_power_dbm: number | null;
}

export const FREQUENCY_PRESETS: readonly FrequencyPreset[] = [
  {
    region: "Canada",
    code: "CA",
    frequency_mhz: 907,
    max_power_dbm: 30,
  },
  {
    region: "United States",
    code: "US",
    frequency_mhz: 915,
    max_power_dbm: 30,
  },
  {
    region: "European Union",
    code: "EU",
    frequency_mhz: 868,
    max_power_dbm: 14,
  },
  {
    region: "Australia",
    code: "AU",
    frequency_mhz: 915,
    max_power_dbm: 30,
  },
  {
    region: "Japan",
    code: "JP",
    frequency_mhz: 920,
    max_power_dbm: 13,
  },
] as const;
