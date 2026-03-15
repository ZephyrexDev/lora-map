import { describe, it, expect } from "vitest";
import { cloneObject, hexToRgb, dbmToRgba } from "../utils";

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
