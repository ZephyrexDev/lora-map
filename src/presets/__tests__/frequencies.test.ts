import { describe, it, expect } from "vitest";
import { FREQUENCY_PRESETS } from "../frequencies";

describe("FREQUENCY_PRESETS", () => {
  it("has 5 entries", () => {
    expect(FREQUENCY_PRESETS).toHaveLength(5);
  });

  it("all entries have required fields", () => {
    for (const preset of FREQUENCY_PRESETS) {
      expect(typeof preset.region).toBe("string");
      expect(typeof preset.code).toBe("string");
      expect(typeof preset.frequency_mhz).toBe("number");
      // max_power_dbm can be number or null
      expect(["number", "object"].includes(typeof preset.max_power_dbm)).toBe(true);
    }
  });

  it('Canada has code "CA" and 907 MHz', () => {
    const canada = FREQUENCY_PRESETS.find((f) => f.region === "Canada");
    expect(canada).toBeDefined();
    if (!canada) throw new Error("expected canada preset");
    expect(canada.code).toBe("CA");
    expect(canada.frequency_mhz).toBe(907);
  });

  it("EU max power is 14 dBm", () => {
    const eu = FREQUENCY_PRESETS.find((f) => f.code === "EU");
    expect(eu).toBeDefined();
    if (!eu) throw new Error("expected EU preset");
    expect(eu.max_power_dbm).toBe(14);
  });
});
