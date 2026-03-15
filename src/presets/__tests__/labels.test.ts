import { describe, it, expect } from "vitest";
import { HARDWARE_LABELS, ANTENNA_LABELS, TERRAIN_LABELS, labelsToOptions } from "../labels";

describe("HARDWARE_LABELS", () => {
  it("includes Heltec V3 and V4", () => {
    expect(HARDWARE_LABELS.v3).toBe("Heltec V3");
    expect(HARDWARE_LABELS.v4).toBe("Heltec V4");
  });
});

describe("ANTENNA_LABELS", () => {
  it("includes all four antennas", () => {
    expect(Object.keys(ANTENNA_LABELS)).toHaveLength(4);
    expect(ANTENNA_LABELS.bingfu_whip).toBe("Bingfu Whip");
    expect(ANTENNA_LABELS.slinkdsco_omni).toBe("Slinkdsco Omni");
  });
});

describe("TERRAIN_LABELS", () => {
  it("includes all four terrain models", () => {
    expect(Object.keys(TERRAIN_LABELS)).toHaveLength(4);
    expect(TERRAIN_LABELS.bare_earth).toContain("SRTM");
    expect(TERRAIN_LABELS.weighted_aggregate).toContain("Aggregate");
  });
});

describe("labelsToOptions", () => {
  it("converts labels record to array of {key, label} options", () => {
    const result = labelsToOptions({ a: "Alpha", b: "Bravo" });
    expect(result).toEqual([
      { key: "a", label: "Alpha" },
      { key: "b", label: "Bravo" },
    ]);
  });

  it("returns empty array for empty record", () => {
    expect(labelsToOptions({})).toEqual([]);
  });

  it("preserves key order from Object.entries", () => {
    const result = labelsToOptions({ z: "Zulu", a: "Alpha" });
    expect(result[0].key).toBe("z");
    expect(result[1].key).toBe("a");
  });
});
