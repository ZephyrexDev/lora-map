// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { sampleRaster, signalToAlpha } from "../OverlapHatchLayer";
import type { GeoRaster } from "../../types";

function makeRaster(overrides: Partial<GeoRaster> = {}): GeoRaster {
  return {
    xmin: -115,
    xmax: -114,
    ymin: 50,
    ymax: 51,
    pixelWidth: 0.01,
    pixelHeight: 0.01,
    values: [
      [
        // 100 rows x 100 cols, all set to -90 dBm
        ...Array.from({ length: 100 }, () => Array.from({ length: 100 }, () => -90)),
      ],
    ],
    noDataValue: 255,
    width: 100,
    height: 100,
    numberOfRasters: 1,
    projection: 4326,
    ...overrides,
  };
}

describe("sampleRaster", () => {
  it("returns value for a point inside the raster extent", () => {
    const raster = makeRaster();
    const result = sampleRaster(raster, 50.5, -114.5);
    expect(result).toBe(-90);
  });

  it("returns null for a point west of extent", () => {
    const raster = makeRaster();
    expect(sampleRaster(raster, 50.5, -116)).toBeNull();
  });

  it("returns null for a point east of extent", () => {
    const raster = makeRaster();
    expect(sampleRaster(raster, 50.5, -113)).toBeNull();
  });

  it("returns null for a point north of extent", () => {
    const raster = makeRaster();
    expect(sampleRaster(raster, 52, -114.5)).toBeNull();
  });

  it("returns null for a point south of extent", () => {
    const raster = makeRaster();
    expect(sampleRaster(raster, 49, -114.5)).toBeNull();
  });

  it("returns null for nodata value (255)", () => {
    const values = [Array.from({ length: 100 }, () => Array.from({ length: 100 }, () => 255))];
    const raster = makeRaster({ values });
    expect(sampleRaster(raster, 50.5, -114.5)).toBeNull();
  });

  it("returns null for null pixel value", () => {
    const values = [Array.from({ length: 100 }, () => Array.from({ length: 100 }, () => null as unknown as number))];
    const raster = makeRaster({ values });
    expect(sampleRaster(raster, 50.5, -114.5)).toBeNull();
  });

  it("handles edge coordinates at raster boundaries", () => {
    const raster = makeRaster();
    // Top-left corner
    const topLeft = sampleRaster(raster, 51, -115);
    expect(topLeft).toBe(-90);
    // Bottom-right corner (just inside)
    const bottomRight = sampleRaster(raster, 50.005, -114.005);
    expect(bottomRight).toBe(-90);
  });

  it("returns correct value from a raster with varying pixel values", () => {
    const values = [Array.from({ length: 100 }, (_, row) => Array.from({ length: 100 }, (_, col) => row + col))];
    const raster = makeRaster({ values });
    // Compute expected row/col from the sampleRaster formula
    const row = Math.floor((51 - 50.95) / 0.01); // = 5
    const col = Math.floor((-114.7 - -115) / 0.01); // = 30
    const result = sampleRaster(raster, 50.95, -114.7);
    // Allow for floating-point rounding in floor operations
    expect(result).toBe(values[0][row][col]);
  });

  it("returns null when band data is empty", () => {
    const raster = makeRaster({ values: [[]] });
    expect(sampleRaster(raster, 50.5, -114.5)).toBeNull();
  });
});

describe("signalToAlpha", () => {
  const minDbm = -130;
  const maxDbm = -80;

  it("returns 25 for weakest signal (minDbm)", () => {
    expect(signalToAlpha(-130, minDbm, maxDbm)).toBe(25);
  });

  it("returns 204 for strongest signal (maxDbm)", () => {
    expect(signalToAlpha(-80, minDbm, maxDbm)).toBe(204);
  });

  it("clamps below minDbm to alpha 25", () => {
    expect(signalToAlpha(-200, minDbm, maxDbm)).toBe(25);
  });

  it("clamps above maxDbm to alpha 204", () => {
    expect(signalToAlpha(-50, minDbm, maxDbm)).toBe(204);
  });

  it("returns intermediate alpha for mid-range value", () => {
    const alpha = signalToAlpha(-105, minDbm, maxDbm);
    expect(alpha).toBeGreaterThan(25);
    expect(alpha).toBeLessThan(204);
  });

  it("is monotonically increasing with signal strength", () => {
    const alpha1 = signalToAlpha(-120, minDbm, maxDbm);
    const alpha2 = signalToAlpha(-100, minDbm, maxDbm);
    const alpha3 = signalToAlpha(-85, minDbm, maxDbm);
    expect(alpha1).toBeLessThan(alpha2);
    expect(alpha2).toBeLessThan(alpha3);
  });

  it("returns an integer", () => {
    const alpha = signalToAlpha(-105.7, minDbm, maxDbm);
    expect(Number.isInteger(alpha)).toBe(true);
  });

  it("handles equal minDbm and maxDbm by returning NaN (division by zero)", () => {
    // When min == max, t = 0/0 = NaN — callers should avoid this edge case
    const alpha = signalToAlpha(-100, -100, -100);
    expect(alpha).toBeNaN();
  });
});
