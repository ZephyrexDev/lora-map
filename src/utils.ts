/**
 * Map path loss (dB) and LOS status to a color for polyline rendering.
 * Green = good (low loss, LOS), yellow = marginal, red = poor (high loss or NLOS).
 */
export function pathLossColor(pathLossDb: number, hasLos: boolean | null): string {
  if (hasLos === false) return "#e74c3c"; // red for NLOS
  if (pathLossDb < 100) return "#2ecc71"; // green – good
  if (pathLossDb <= 130) return "#f1c40f"; // yellow – marginal
  return "#e74c3c"; // red – poor
}

/** Default tower colors for visual differentiation (12-color palette). */
export const TOWER_COLORS = [
  "#e6194b", // red
  "#3cb44b", // green
  "#4363d8", // blue
  "#f58231", // orange
  "#911eb4", // purple
  "#42d4f4", // cyan
  "#f032e6", // magenta
  "#bfef45", // lime
  "#fabed4", // pink
  "#469990", // teal
  "#dcbeff", // lavender
  "#9a6324", // brown
] as const;

/** Convert watts to dBm: dBm = 10 * log10(watts) + 30. */
export function wattsToDbm(watts: number): number {
  return 10 * Math.log10(watts) + 30;
}

/** Convert dBm to watts: W = 10^((dBm - 30) / 10). */
export function dbmToWatts(dbm: number): number {
  return parseFloat(Math.pow(10, (dbm - 30) / 10).toFixed(4));
}

/** Convert an array of enabled keys + a list of all possible keys into a boolean record. */
export function arrayToRecord(arr: readonly string[], allKeys: readonly string[]): Record<string, boolean> {
  const result: Record<string, boolean> = {};
  for (const key of allKeys) {
    result[key] = arr.includes(key);
  }
  return result;
}

/** Check if an ArrayBuffer starts with TIFF magic bytes (II or MM). */
export function isTiffBuffer(buffer: ArrayBuffer): boolean {
  if (buffer.byteLength < 2) return false;
  const first = new Uint8Array(buffer.slice(0, 2));
  return first[0] === 0x49 || first[0] === 0x4d; // 'I' (little-endian) or 'M' (big-endian)
}

/**
 * Build the simulation API payload from SplatParams.
 * Converts watts → dBm, km → m, and remaps field names to backend API keys.
 */
export function buildSimulationPayload(params: import("./types").SplatParams): Record<string, unknown> {
  return {
    lat: params.transmitter.tx_lat,
    lon: params.transmitter.tx_lon,
    tx_height: params.transmitter.tx_height,
    tx_power: wattsToDbm(params.transmitter.tx_power),
    tx_gain: params.transmitter.tx_gain,
    frequency_mhz: params.transmitter.tx_freq,
    rx_height: params.receiver.rx_height,
    rx_gain: params.receiver.rx_gain,
    signal_threshold: params.receiver.rx_sensitivity,
    system_loss: params.receiver.rx_loss,
    clutter_height: params.environment.clutter_height,
    ground_dielectric: params.environment.ground_dielectric,
    ground_conductivity: params.environment.ground_conductivity,
    atmosphere_bending: params.environment.atmosphere_bending,
    radio_climate: params.environment.radio_climate,
    polarization: params.environment.polarization,
    radius: params.simulation.simulation_extent * 1000,
    situation_fraction: params.simulation.situation_fraction,
    time_fraction: params.simulation.time_fraction,
    high_resolution: params.simulation.high_resolution,
    colormap: params.display.color_scale,
    min_dbm: params.display.min_dbm,
    max_dbm: params.display.max_dbm,
  };
}

export function cloneObject<T>(item: T): T {
  return JSON.parse(JSON.stringify(item));
}

/**
 * Convert a hex color string (#RRGGBB) to an {r, g, b} object.
 */
export function hexToRgb(hex: string): { r: number; g: number; b: number } {
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  };
}

/**
 * Map a dBm pixel value to an rgba() color string for coverage rendering.
 *
 * - NaN / null / undefined → null (transparent, no coverage)
 * - Values at minDbm (weakest receivable) → 10% transparency (alpha ≈ 230)
 * - Values at maxDbm (strongest) → 80% transparency (alpha ≈ 51)
 * - Linear interpolation between those bounds
 */
export function dbmToRgba(
  value: number | null | undefined,
  hex: string,
  minDbm: number,
  maxDbm: number,
): string | null {
  if (value === undefined || value === null || isNaN(value)) return null;
  const clamped = Math.max(minDbm, Math.min(maxDbm, value));
  const t = (clamped - minDbm) / (maxDbm - minDbm); // 0 = weakest, 1 = strongest
  const alpha = Math.round(230 - t * 179); // 230 (weak) → 51 (strong)
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r},${g},${b},${alpha / 255})`;
}
