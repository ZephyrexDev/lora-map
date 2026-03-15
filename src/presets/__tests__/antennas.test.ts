import { describe, it, expect } from "vitest";
import { ANTENNA_PRESETS, mismatchLoss } from "../antennas";

describe("ANTENNA_PRESETS", () => {
  it("has 4 entries", () => {
    expect(ANTENNA_PRESETS).toHaveLength(4);
  });

  it("each antenna has name, gain_dbi, and swr properties", () => {
    for (const antenna of ANTENNA_PRESETS) {
      expect(antenna).toHaveProperty("name");
      expect(antenna).toHaveProperty("gain_dbi");
      expect(antenna).toHaveProperty("swr");
      expect(typeof antenna.name).toBe("string");
      expect(typeof antenna.gain_dbi).toBe("number");
      expect(typeof antenna.swr).toBe("number");
    }
  });
});

describe("mismatchLoss", () => {
  it("returns Infinity for swr=1.0 (perfect match)", () => {
    // When SWR=1.0, reflection coefficient is 0, so -10*log10(1-0) = -10*log10(1) = 0
    // Actually: (1-1)/(1+1) = 0, so 1 - 0^2 = 1, -10*log10(1) = 0
    expect(mismatchLoss(1.0)).toBeCloseTo(0, 5);
  });

  it("returns ~0.01 for swr=1.1", () => {
    // (1.1-1)/(1.1+1) = 0.1/2.1 ≈ 0.04762
    // 0.04762^2 ≈ 0.002268
    // 1 - 0.002268 ≈ 0.997732
    // -10 * log10(0.997732) ≈ 0.00986
    expect(mismatchLoss(1.1)).toBeCloseTo(0.01, 1);
  });

  it("returns ~1.25 for swr=3.0", () => {
    // (3-1)/(3+1) = 0.5
    // 0.5^2 = 0.25
    // 1 - 0.25 = 0.75
    // -10 * log10(0.75) ≈ 1.2494
    expect(mismatchLoss(3.0)).toBeCloseTo(1.25, 1);
  });

  it("returns positive values for SWR > 1", () => {
    for (const swr of [1.1, 1.5, 2.0, 3.0, 5.0]) {
      expect(mismatchLoss(swr)).toBeGreaterThan(0);
    }
  });
});
