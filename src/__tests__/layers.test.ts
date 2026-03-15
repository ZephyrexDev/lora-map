// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import L from "leaflet";
import { redPinMarker, chirpyMarker } from "../layers";

describe("redPinMarker", () => {
  it("has correct icon size", () => {
    expect(redPinMarker.options.iconSize).toEqual([30, 30]);
  });

  it("has correct icon anchor", () => {
    expect(redPinMarker.options.iconAnchor).toEqual([15, 30]);
  });

  it("contains pin emoji in HTML", () => {
    const html = (redPinMarker.options as L.DivIconOptions).html as string;
    expect(html).toContain("📍");
  });
});

describe("chirpyMarker", () => {
  it("has correct icon size", () => {
    expect(chirpyMarker.options.iconSize).toEqual([24, 40]);
  });

  it("has correct icon anchor", () => {
    expect(chirpyMarker.options.iconAnchor).toEqual([12, 40]);
  });

  it("contains SVG in HTML", () => {
    const html = (chirpyMarker.options as L.DivIconOptions).html as string;
    expect(html).toContain("<svg");
    expect(html).toContain("</svg>");
  });

  it("has empty className to avoid default leaflet-div-icon styling", () => {
    expect(chirpyMarker.options.className).toBe("");
  });
});
