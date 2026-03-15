import L from "leaflet";
import { hexToRgb } from "../utils.ts";
import { type TowerInfo, type GeoRaster } from "../types.ts";

// Pre-defined stripe angles in radians for each tower index
const STRIPE_ANGLES = [
  Math.PI / 4, // 45 degrees
  (3 * Math.PI) / 4, // 135 degrees
  Math.PI / 6, // 30 degrees
  (2 * Math.PI) / 3, // 120 degrees
  Math.PI / 3, // 60 degrees
  (5 * Math.PI) / 6, // 150 degrees
  Math.PI / 12, // 15 degrees
  (11 * Math.PI) / 12, // 165 degrees
];

// Stripe width bounds in pixels
const MIN_STRIPE_WIDTH = 2;
const MAX_STRIPE_WIDTH = 8;
// Stripe spacing (period) in pixels
const STRIPE_PERIOD = 12;

interface OverlapHatchLayerOptions extends L.GridLayerOptions {
  towers: TowerInfo[];
  mode: "hatch" | "blend";
  minDbm: number;
  maxDbm: number;
}

/**
 * Sample a georaster at a given lat/lng.
 * Returns the pixel value (dBm) or null if out of bounds or nodata.
 */
function sampleRaster(raster: GeoRaster, lat: number, lng: number): number | null {
  const { xmin, xmax, ymin, ymax, pixelWidth, pixelHeight, values, noDataValue } = raster;

  if (lng < xmin || lng > xmax || lat < ymin || lat > ymax) {
    return null;
  }

  const col = Math.floor((lng - xmin) / pixelWidth);
  const row = Math.floor((ymax - lat) / pixelHeight);

  const band = values[0]; // first band
  if (!band || row < 0 || row >= band.length) {
    return null;
  }
  const rowData = band[row];
  if (!rowData || col < 0 || col >= rowData.length) {
    return null;
  }

  const val = rowData[col];
  if (val === noDataValue || val === 255 || val === undefined || val === null) {
    return null;
  }

  return val;
}

/**
 * Convert a signal value (dBm) to alpha (0-255).
 * min_dbm -> weakest signal -> most transparent (alpha ~25, ~10%)
 * max_dbm -> strongest signal -> least transparent (alpha ~204, ~80%)
 * Values are clamped to the [min_dbm, max_dbm] range.
 */
function signalToAlpha(value: number, minDbm: number, maxDbm: number): number {
  const clamped = Math.max(minDbm, Math.min(maxDbm, value));
  // Normalize to 0..1 where 0 = weakest, 1 = strongest
  const t = (clamped - minDbm) / (maxDbm - minDbm);
  // Map to alpha: 25 (10%) at t=0 to 204 (80%) at t=1
  return Math.round(25 + t * (204 - 25));
}

const OverlapHatchLayer = L.GridLayer.extend({
  initialize(options: OverlapHatchLayerOptions) {
    L.Util.setOptions(this, options);
    // Pre-parse tower colors
    const opts = this.options as OverlapHatchLayerOptions;
    this._parsedColors = opts.towers.map((t) => {
      const { r, g, b } = hexToRgb(t.color);
      return [r, g, b] as [number, number, number];
    });
  },

  createTile(coords: L.Coords): HTMLCanvasElement {
    const tile = document.createElement("canvas");
    const tileSize = this.getTileSize();
    tile.width = tileSize.x;
    tile.height = tileSize.y;

    const ctx = tile.getContext("2d");
    if (!ctx) return tile;

    const opts = this.options as OverlapHatchLayerOptions;
    const { towers, mode, minDbm, maxDbm } = opts;
    const parsedColors: [number, number, number][] = this._parsedColors;

    if (towers.length === 0) return tile;

    // Get the pixel bounds for this tile
    const nwPoint = coords.scaleBy(tileSize);
    const map = this._map;
    if (!map) return tile;

    const zoom = coords.z;

    // Create ImageData for direct pixel manipulation
    const imageData = ctx.createImageData(tileSize.x, tileSize.y);
    const data = imageData.data;

    // Pre-compute stripe angles for each tower
    const angles = towers.map((_t: TowerInfo, i: number) => STRIPE_ANGLES[i % STRIPE_ANGLES.length]);
    const cosAngles = angles.map((a: number) => Math.cos(a));
    const sinAngles = angles.map((a: number) => Math.sin(a));

    for (let py = 0; py < tileSize.y; py++) {
      for (let px = 0; px < tileSize.x; px++) {
        // Convert pixel to lat/lng
        const point = L.point(nwPoint.x + px, nwPoint.y + py);
        const latlng = map.unproject(point, zoom);
        const lat = latlng.lat;
        const lng = latlng.lng;

        // Sample each tower's raster at this location
        const towerValues: (number | null)[] = [];
        let coverageCount = 0;

        for (let t = 0; t < towers.length; t++) {
          const val = sampleRaster(towers[t].raster, lat, lng);
          towerValues.push(val);
          if (val !== null) {
            coverageCount++;
          }
        }

        if (coverageCount === 0) continue;

        const pixelOffset = (py * tileSize.x + px) * 4;

        if (coverageCount === 1) {
          // Single tower: solid color with signal-based alpha
          for (let t = 0; t < towers.length; t++) {
            if (towerValues[t] !== null) {
              const [r, g, b] = parsedColors[t];
              const alpha = signalToAlpha(towerValues[t]!, minDbm, maxDbm);
              data[pixelOffset] = r;
              data[pixelOffset + 1] = g;
              data[pixelOffset + 2] = b;
              data[pixelOffset + 3] = alpha;
              break;
            }
          }
        } else if (mode === "blend") {
          // Alpha blend mode: average colors weighted by signal strength
          let totalWeight = 0;
          let rSum = 0,
            gSum = 0,
            bSum = 0;
          let maxAlpha = 0;

          for (let t = 0; t < towers.length; t++) {
            if (towerValues[t] !== null) {
              const alpha = signalToAlpha(towerValues[t]!, minDbm, maxDbm);
              const weight = alpha;
              const [r, g, b] = parsedColors[t];
              rSum += r * weight;
              gSum += g * weight;
              bSum += b * weight;
              totalWeight += weight;
              if (alpha > maxAlpha) maxAlpha = alpha;
            }
          }

          if (totalWeight > 0) {
            data[pixelOffset] = Math.round(rSum / totalWeight);
            data[pixelOffset + 1] = Math.round(gSum / totalWeight);
            data[pixelOffset + 2] = Math.round(bSum / totalWeight);
            data[pixelOffset + 3] = Math.min(255, maxAlpha);
          }
        } else {
          // Hatch mode: draw diagonal stripes per tower
          // For this pixel, determine which tower's stripe it falls on
          // Each tower gets a set of stripes at a unique angle

          // Calculate total signal strength for width scaling
          let totalSignal = 0;
          const towerSignals: number[] = [];
          for (let t = 0; t < towers.length; t++) {
            if (towerValues[t] !== null) {
              const sig = towerValues[t]! - minDbm; // normalize to positive
              towerSignals.push(Math.max(0, sig));
              totalSignal += Math.max(0, sig);
            } else {
              towerSignals.push(0);
            }
          }

          // Check each tower's stripe pattern at this pixel
          // The last matching tower "wins" (they layer on top)
          // Instead: combine by checking all and picking the one whose stripe
          // this pixel falls on; if multiple, pick the one with strongest signal
          let bestTower = -1;
          let bestAlpha = 0;

          for (let t = 0; t < towers.length; t++) {
            if (towerValues[t] === null) continue;

            // Calculate stripe width based on relative signal strength
            let stripeWidth: number;
            if (totalSignal > 0) {
              const relativeStrength = towerSignals[t] / totalSignal;
              stripeWidth = MIN_STRIPE_WIDTH + relativeStrength * (MAX_STRIPE_WIDTH - MIN_STRIPE_WIDTH);
            } else {
              stripeWidth = MIN_STRIPE_WIDTH;
            }

            // Project pixel onto the stripe's perpendicular axis
            const cosA = cosAngles[t];
            const sinA = sinAngles[t];
            // Perpendicular distance from origin along the stripe normal
            const proj = px * cosA + py * sinA;

            // Determine if this pixel falls on a stripe
            // Use modular arithmetic: stripe is "on" for stripeWidth pixels,
            // then "off" for (STRIPE_PERIOD - stripeWidth) pixels
            const modPos = ((proj % STRIPE_PERIOD) + STRIPE_PERIOD) % STRIPE_PERIOD;
            if (modPos < stripeWidth) {
              const alpha = signalToAlpha(towerValues[t]!, minDbm, maxDbm);
              if (alpha > bestAlpha || bestTower === -1) {
                bestTower = t;
                bestAlpha = alpha;
              }
            }
          }

          if (bestTower >= 0) {
            const [r, g, b] = parsedColors[bestTower];
            data[pixelOffset] = r;
            data[pixelOffset + 1] = g;
            data[pixelOffset + 2] = b;
            data[pixelOffset + 3] = bestAlpha;
          } else {
            // Pixel doesn't fall on any tower's stripe — fill with the
            // strongest tower's color at reduced alpha as background
            let strongest = -1;
            let strongestVal = -Infinity;
            for (let t = 0; t < towers.length; t++) {
              if (towerValues[t] !== null && towerValues[t]! > strongestVal) {
                strongestVal = towerValues[t]!;
                strongest = t;
              }
            }
            if (strongest >= 0) {
              const [r, g, b] = parsedColors[strongest];
              const alpha = Math.round(signalToAlpha(strongestVal, minDbm, maxDbm) * 0.3);
              data[pixelOffset] = r;
              data[pixelOffset + 1] = g;
              data[pixelOffset + 2] = b;
              data[pixelOffset + 3] = alpha;
            }
          }
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);
    return tile;
  },
});

export function createOverlapHatchLayer(options: OverlapHatchLayerOptions): L.GridLayer {
  return new (OverlapHatchLayer as unknown as new (o: OverlapHatchLayerOptions) => L.GridLayer)(options);
}

export { sampleRaster, signalToAlpha };
export type { OverlapHatchLayerOptions };
