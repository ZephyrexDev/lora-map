import { describe, it, expect } from "vitest";
import {
  cloneObject,
  hexToRgb,
  dbmToRgba,
  wattsToDbm,
  dbmToWatts,
  arrayToRecord,
  isTiffBuffer,
  buildSimulationPayload,
  TOWER_COLORS,
} from "../utils";
import type { SplatParams } from "../types";

// ---------------------------------------------------------------------------
// cloneObject
// ---------------------------------------------------------------------------
describe("cloneObject", () => {
  it("deep clones a nested object", () => {
    const original = { a: 1, b: { c: [2, 3] } };
    const cloned = cloneObject(original);
    expect(cloned).toEqual(original);
    expect(cloned).not.toBe(original);
    expect(cloned.b).not.toBe(original.b);
    expect(cloned.b.c).not.toBe(original.b.c);
  });

  it("clones arrays", () => {
    const original = [1, { x: 2 }, [3]];
    const cloned = cloneObject(original);
    expect(cloned).toEqual(original);
    expect(cloned[1]).not.toBe(original[1]);
  });

  it("handles primitives", () => {
    expect(cloneObject(42)).toBe(42);
    expect(cloneObject("hello")).toBe("hello");
    expect(cloneObject(null)).toBe(null);
    expect(cloneObject(true)).toBe(true);
  });

  it("drops functions (not JSON-serializable)", () => {
    const original = { a: 1, fn: () => 42 };
    const cloned = cloneObject(original);
    expect(cloned.a).toBe(1);
    expect(cloned.fn).toBeUndefined();
  });

  it("converts undefined values to null in arrays", () => {
    const cloned = cloneObject([1, undefined, 3]);
    expect(cloned).toEqual([1, null, 3]);
  });
});

// ---------------------------------------------------------------------------
// hexToRgb
// ---------------------------------------------------------------------------
describe("hexToRgb", () => {
  it.each([
    ["#000000", { r: 0, g: 0, b: 0 }],
    ["#ffffff", { r: 255, g: 255, b: 255 }],
    ["#ff0000", { r: 255, g: 0, b: 0 }],
    ["#00ff00", { r: 0, g: 255, b: 0 }],
    ["#0000ff", { r: 0, g: 0, b: 255 }],
    ["#4a90d9", { r: 74, g: 144, b: 217 }],
  ])("parses %s correctly", (hex, expected) => {
    expect(hexToRgb(hex)).toEqual(expected);
  });
});

// ---------------------------------------------------------------------------
// dbmToRgba
// ---------------------------------------------------------------------------
describe("dbmToRgba", () => {
  const hex = "#ff0000";
  const minDbm = -130;
  const maxDbm = -80;

  it("returns null for NaN", () => {
    expect(dbmToRgba(NaN, hex, minDbm, maxDbm)).toBeNull();
  });

  it("returns null for null", () => {
    expect(dbmToRgba(null, hex, minDbm, maxDbm)).toBeNull();
  });

  it("returns null for undefined", () => {
    expect(dbmToRgba(undefined, hex, minDbm, maxDbm)).toBeNull();
  });

  it("returns rgba string for valid value", () => {
    const result = dbmToRgba(-100, hex, minDbm, maxDbm);
    expect(result).toMatch(/^rgba\(255,0,0,[\d.]+\)$/);
  });

  it("weakest signal (minDbm) gets alpha ≈ 230/255 (nearly opaque)", () => {
    const result = dbmToRgba(-130, hex, minDbm, maxDbm)!;
    const alpha = parseFloat(result.match(/,([\d.]+)\)$/)![1]);
    expect(alpha).toBeCloseTo(230 / 255, 2);
  });

  it("strongest signal (maxDbm) gets alpha ≈ 51/255 (mostly transparent)", () => {
    const result = dbmToRgba(-80, hex, minDbm, maxDbm)!;
    const alpha = parseFloat(result.match(/,([\d.]+)\)$/)![1]);
    expect(alpha).toBeCloseTo(51 / 255, 2);
  });

  it("clamps values below minDbm", () => {
    const atMin = dbmToRgba(-130, hex, minDbm, maxDbm);
    const belowMin = dbmToRgba(-200, hex, minDbm, maxDbm);
    expect(belowMin).toBe(atMin);
  });

  it("clamps values above maxDbm", () => {
    const atMax = dbmToRgba(-80, hex, minDbm, maxDbm);
    const aboveMax = dbmToRgba(-50, hex, minDbm, maxDbm);
    expect(aboveMax).toBe(atMax);
  });

  it("mid-range value has intermediate alpha", () => {
    const result = dbmToRgba(-105, hex, minDbm, maxDbm)!;
    const alpha = parseFloat(result.match(/,([\d.]+)\)$/)![1]);
    expect(alpha).toBeGreaterThan(51 / 255);
    expect(alpha).toBeLessThan(230 / 255);
  });

  it("uses the provided hex color", () => {
    const result = dbmToRgba(-100, "#00ff80", minDbm, maxDbm)!;
    expect(result).toMatch(/^rgba\(0,255,128,/);
  });
});

// ---------------------------------------------------------------------------
// TOWER_COLORS
// ---------------------------------------------------------------------------
describe("TOWER_COLORS", () => {
  it("has exactly 12 colors", () => {
    expect(TOWER_COLORS).toHaveLength(12);
  });

  it("all values are valid hex color strings", () => {
    for (const color of TOWER_COLORS) {
      expect(color).toMatch(/^#[0-9a-f]{6}$/);
    }
  });

  it("has no duplicate colors", () => {
    const unique = new Set(TOWER_COLORS);
    expect(unique.size).toBe(TOWER_COLORS.length);
  });
});

// ---------------------------------------------------------------------------
// wattsToDbm
// ---------------------------------------------------------------------------
describe("wattsToDbm", () => {
  it.each([
    [0.001, 0], // 1 mW = 0 dBm
    [0.01, 10], // 10 mW = 10 dBm
    [0.1, 20], // 100 mW = 20 dBm
    [1, 30], // 1 W = 30 dBm
    [10, 40], // 10 W = 40 dBm
  ])("converts %f W to %d dBm", (watts, expectedDbm) => {
    expect(wattsToDbm(watts)).toBeCloseTo(expectedDbm, 5);
  });

  it("returns -Infinity for 0 watts", () => {
    expect(wattsToDbm(0)).toBe(-Infinity);
  });

  it("returns a finite number for very small power", () => {
    const result = wattsToDbm(0.0001); // 10*log10(0.0001)+30 = -40+30 = -10
    expect(Number.isFinite(result)).toBe(true);
    expect(result).toBeCloseTo(-10, 5);
  });
});

// ---------------------------------------------------------------------------
// dbmToWatts
// ---------------------------------------------------------------------------
describe("dbmToWatts", () => {
  it.each([
    [0, 0.001], // 0 dBm = 1 mW
    [10, 0.01], // 10 dBm = 10 mW
    [20, 0.1], // 20 dBm = 100 mW
    [30, 1], // 30 dBm = 1 W
    [22, 0.1585], // 22 dBm = 158.5 mW (Heltec V3/V4 max)
  ])("converts %d dBm to %f W", (dbm, expectedWatts) => {
    expect(dbmToWatts(dbm)).toBeCloseTo(expectedWatts, 4);
  });

  it("is the inverse of wattsToDbm", () => {
    const watts = 0.158;
    const dbm = wattsToDbm(watts);
    expect(dbmToWatts(dbm)).toBeCloseTo(watts, 3);
  });

  it("round-trips through wattsToDbm for standard values", () => {
    for (const watts of [0.001, 0.01, 0.1, 1, 10]) {
      expect(dbmToWatts(wattsToDbm(watts))).toBeCloseTo(watts, 3);
    }
  });
});

// ---------------------------------------------------------------------------
// arrayToRecord
// ---------------------------------------------------------------------------
describe("arrayToRecord", () => {
  it("maps enabled keys to true, others to false", () => {
    const result = arrayToRecord(["v3", "v4"], ["v3", "v4", "custom"]);
    expect(result).toEqual({ v3: true, v4: true, custom: false });
  });

  it("returns all false for empty array", () => {
    const result = arrayToRecord([], ["a", "b", "c"]);
    expect(result).toEqual({ a: false, b: false, c: false });
  });

  it("returns all true when all keys are enabled", () => {
    const result = arrayToRecord(["a", "b"], ["a", "b"]);
    expect(result).toEqual({ a: true, b: true });
  });

  it("ignores arr values not in allKeys", () => {
    const result = arrayToRecord(["a", "x"], ["a", "b"]);
    expect(result).toEqual({ a: true, b: false });
    expect(result).not.toHaveProperty("x");
  });

  it("returns empty record for empty allKeys", () => {
    expect(arrayToRecord(["a"], [])).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// isTiffBuffer
// ---------------------------------------------------------------------------
describe("isTiffBuffer", () => {
  it("returns true for little-endian TIFF (II = 0x49 0x49)", () => {
    const buf = new Uint8Array([0x49, 0x49, 0x2a, 0x00]).buffer;
    expect(isTiffBuffer(buf)).toBe(true);
  });

  it("returns true for big-endian TIFF (MM = 0x4d 0x4d)", () => {
    const buf = new Uint8Array([0x4d, 0x4d, 0x00, 0x2a]).buffer;
    expect(isTiffBuffer(buf)).toBe(true);
  });

  it("returns false for JSON response ({)", () => {
    const buf = new TextEncoder().encode('{"error":"missing"}').buffer;
    expect(isTiffBuffer(buf)).toBe(false);
  });

  it("returns false for empty buffer", () => {
    expect(isTiffBuffer(new ArrayBuffer(0))).toBe(false);
  });

  it("returns false for single byte buffer", () => {
    expect(isTiffBuffer(new Uint8Array([0x49]).buffer)).toBe(false);
  });

  it("returns false for PNG magic bytes", () => {
    const buf = new Uint8Array([0x89, 0x50, 0x4e, 0x47]).buffer;
    expect(isTiffBuffer(buf)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// buildSimulationPayload
// ---------------------------------------------------------------------------
describe("buildSimulationPayload", () => {
  function makeParams(): SplatParams {
    return {
      transmitter: {
        name: "test-tower",
        tx_lat: 51.102,
        tx_lon: -114.099,
        tx_power: 0.1, // 100 mW = 20 dBm
        tx_freq: 907.0,
        tx_height: 10.0,
        tx_gain: 2.5,
      },
      receiver: {
        rx_sensitivity: -130.0,
        rx_height: 1.5,
        rx_gain: 2.0,
        rx_loss: 1.5,
      },
      environment: {
        radio_climate: "continental_temperate",
        polarization: "vertical",
        clutter_height: 1.0,
        ground_dielectric: 15.0,
        ground_conductivity: 0.005,
        atmosphere_bending: 301.0,
      },
      simulation: {
        situation_fraction: 95.0,
        time_fraction: 95.0,
        simulation_extent: 30.0, // 30 km
        high_resolution: false,
      },
      display: {
        color_scale: "plasma",
        min_dbm: -130.0,
        max_dbm: -80.0,
        overlay_transparency: 50,
        overlapMode: "hatch",
      },
    };
  }

  it("converts watts to dBm for tx_power", () => {
    const payload = buildSimulationPayload(makeParams());
    // 0.1 W = 20 dBm
    expect(payload.tx_power).toBeCloseTo(20, 5);
  });

  it("converts km to m for radius", () => {
    const payload = buildSimulationPayload(makeParams());
    expect(payload.radius).toBe(30000); // 30 km * 1000
  });

  it("maps rx_sensitivity to signal_threshold", () => {
    const payload = buildSimulationPayload(makeParams());
    expect(payload.signal_threshold).toBe(-130.0);
  });

  it("maps rx_loss to system_loss", () => {
    const payload = buildSimulationPayload(makeParams());
    expect(payload.system_loss).toBe(1.5);
  });

  it("maps tx_freq to frequency_mhz", () => {
    const payload = buildSimulationPayload(makeParams());
    expect(payload.frequency_mhz).toBe(907.0);
  });

  it("maps color_scale to colormap", () => {
    const payload = buildSimulationPayload(makeParams());
    expect(payload.colormap).toBe("plasma");
  });

  it("includes all required API keys", () => {
    const payload = buildSimulationPayload(makeParams());
    const requiredKeys = [
      "lat",
      "lon",
      "tx_height",
      "tx_power",
      "tx_gain",
      "frequency_mhz",
      "rx_height",
      "rx_gain",
      "signal_threshold",
      "system_loss",
      "clutter_height",
      "ground_dielectric",
      "ground_conductivity",
      "atmosphere_bending",
      "radio_climate",
      "polarization",
      "radius",
      "situation_fraction",
      "time_fraction",
      "high_resolution",
      "colormap",
      "min_dbm",
      "max_dbm",
    ];
    for (const key of requiredKeys) {
      expect(payload).toHaveProperty(key);
    }
  });

  it("does not include frontend-only fields", () => {
    const payload = buildSimulationPayload(makeParams());
    expect(payload).not.toHaveProperty("name");
    expect(payload).not.toHaveProperty("overlay_transparency");
    expect(payload).not.toHaveProperty("overlapMode");
    expect(payload).not.toHaveProperty("simulation_extent");
    expect(payload).not.toHaveProperty("tx_freq");
    expect(payload).not.toHaveProperty("rx_sensitivity");
    expect(payload).not.toHaveProperty("rx_loss");
    expect(payload).not.toHaveProperty("color_scale");
  });

  it("all numeric values are numbers, not strings", () => {
    const payload = buildSimulationPayload(makeParams());
    for (const [key, value] of Object.entries(payload)) {
      if (key === "radio_climate" || key === "polarization" || key === "colormap") continue;
      if (key === "high_resolution") {
        expect(typeof value).toBe("boolean");
      } else {
        expect(typeof value).toBe("number");
      }
    }
  });

  it("preserves passthrough values unchanged", () => {
    const params = makeParams();
    const payload = buildSimulationPayload(params);
    expect(payload.lat).toBe(51.102);
    expect(payload.lon).toBe(-114.099);
    expect(payload.tx_height).toBe(10.0);
    expect(payload.tx_gain).toBe(2.5);
    expect(payload.rx_height).toBe(1.5);
    expect(payload.rx_gain).toBe(2.0);
    expect(payload.radio_climate).toBe("continental_temperate");
    expect(payload.polarization).toBe("vertical");
  });
});
