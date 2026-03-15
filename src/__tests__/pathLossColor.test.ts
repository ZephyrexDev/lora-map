import { describe, it, expect } from "vitest";
import { pathLossColor } from "../utils";

describe("pathLossColor", () => {
  it("returns red for NLOS regardless of loss value", () => {
    expect(pathLossColor(50, false)).toBe("#e74c3c");
    expect(pathLossColor(150, false)).toBe("#e74c3c");
  });

  it("returns green for low path loss with LOS", () => {
    expect(pathLossColor(50, true)).toBe("#2ecc71");
    expect(pathLossColor(99, true)).toBe("#2ecc71");
  });

  it("returns yellow for marginal path loss (100-130 dB)", () => {
    expect(pathLossColor(100, true)).toBe("#f1c40f");
    expect(pathLossColor(115, true)).toBe("#f1c40f");
    expect(pathLossColor(130, true)).toBe("#f1c40f");
  });

  it("returns red for high path loss (>130 dB)", () => {
    expect(pathLossColor(131, true)).toBe("#e74c3c");
    expect(pathLossColor(200, true)).toBe("#e74c3c");
  });

  it("returns green for low path loss with null LOS (pending)", () => {
    expect(pathLossColor(50, null)).toBe("#2ecc71");
  });

  it("returns yellow for marginal loss with null LOS", () => {
    expect(pathLossColor(115, null)).toBe("#f1c40f");
  });

  it("returns red for high loss with null LOS", () => {
    expect(pathLossColor(150, null)).toBe("#e74c3c");
  });

  it("boundary at exactly 100 dB is yellow", () => {
    expect(pathLossColor(100, true)).toBe("#f1c40f");
  });

  it("boundary just below 100 dB is green", () => {
    expect(pathLossColor(99.9, true)).toBe("#2ecc71");
  });
});
