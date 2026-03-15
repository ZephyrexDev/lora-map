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
