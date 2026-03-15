// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { redPinMarker } from "../layers";

describe("redPinMarker", () => {
  it("has correct icon size", () => {
    expect(redPinMarker.options.iconSize).toEqual([30, 30]);
  });

  it("has correct icon anchor", () => {
    expect(redPinMarker.options.iconAnchor).toEqual([15, 30]);
  });

  it("contains pin emoji in HTML", () => {
    const html = (redPinMarker.options).html as string;
    expect(html).toContain("📍");
  });
});
