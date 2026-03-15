import presets from "./presets.json";

export interface HardwarePreset {
  name: string;
  max_power_dbm: number;
  chip: string;
  is_custom: boolean;
}

export const HARDWARE_PRESETS: readonly HardwarePreset[] = presets.hardware;
