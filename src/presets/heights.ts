import presets from "./presets.json";

export interface HeightPreset {
  label: string;
  height_m: number;
}

export const HEIGHT_PRESETS: readonly HeightPreset[] = presets.heights;
