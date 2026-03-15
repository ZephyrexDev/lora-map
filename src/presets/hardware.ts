export interface HardwarePreset {
  name: string;
  max_power_dbm: number;
  chip: string;
  is_custom: boolean;
}

export const HARDWARE_PRESETS: readonly HardwarePreset[] = [
  { name: "Heltec V3", max_power_dbm: 22, chip: "SX1262", is_custom: false },
  { name: "Heltec V4", max_power_dbm: 22, chip: "SX1262", is_custom: false },
  { name: "Custom", max_power_dbm: 30, chip: "N/A", is_custom: true },
];
