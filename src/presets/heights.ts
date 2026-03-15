export interface HeightPreset {
  readonly label: string;
  readonly height_m: number;
}

export const HEIGHT_PRESETS: readonly HeightPreset[] = [
  { label: "Ground Level", height_m: 1 },
  { label: "First Floor Window", height_m: 3 },
  { label: "Second Floor Window", height_m: 6 },
  { label: "Gutter Line", height_m: 8 },
  { label: "Rooftop", height_m: 10 },
  { label: "Roof Tower", height_m: 15 },
  { label: "Ground Tower", height_m: 30 },
] as const;
