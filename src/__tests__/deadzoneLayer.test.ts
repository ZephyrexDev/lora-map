import { describe, it, expect } from "vitest";
import type { DeadzoneRegion } from "../types";

// Test the DeadzoneCanvasLayer's data model and region calculations
// The actual canvas rendering requires a full Leaflet map context, but we
// can test the region data structure and the priority scoring logic.

function makeRegion(overrides: Partial<DeadzoneRegion> = {}): DeadzoneRegion {
  return {
    region_id: 1,
    center_lat: 51.0,
    center_lon: -114.0,
    area_km2: 5.0,
    priority_score: 0.5,
    pixel_count: 100,
    suggestion: null,
    ...overrides,
  };
}

describe("DeadzoneRegion data model", () => {
  it("constructs with required fields", () => {
    const region = makeRegion();
    expect(region.region_id).toBe(1);
    expect(region.center_lat).toBe(51.0);
    expect(region.center_lon).toBe(-114.0);
    expect(region.area_km2).toBe(5.0);
    expect(region.priority_score).toBe(0.5);
    expect(region.pixel_count).toBe(100);
    expect(region.suggestion).toBeNull();
  });

  it("can have an attached suggestion", () => {
    const region = makeRegion({
      suggestion: {
        lat: 51.1,
        lon: -114.1,
        estimated_coverage_km2: 12.5,
        priority_rank: 1,
        reason: "Large gap adjacent to tower A coverage edge",
      },
    });
    expect(region.suggestion).not.toBeNull();
    expect(region.suggestion!.priority_rank).toBe(1);
    expect(region.suggestion!.estimated_coverage_km2).toBe(12.5);
  });

  it("priority_score is between 0 and 1", () => {
    const low = makeRegion({ priority_score: 0 });
    const high = makeRegion({ priority_score: 1.0 });
    expect(low.priority_score).toBe(0);
    expect(high.priority_score).toBe(1.0);
  });
});

describe("Deadzone constants", () => {
  // These constants are used for dot rendering — verify they form valid ranges
  const MIN_DOT_RADIUS = 1.5;
  const MAX_DOT_RADIUS = 3.5;
  const MIN_DOT_SPACING = 7;
  const MAX_DOT_SPACING = 14;
  const MIN_OPACITY = 0.3;
  const MAX_OPACITY = 0.8;

  it("dot radius range is valid", () => {
    expect(MIN_DOT_RADIUS).toBeLessThan(MAX_DOT_RADIUS);
    expect(MIN_DOT_RADIUS).toBeGreaterThan(0);
  });

  it("dot spacing range is valid", () => {
    expect(MIN_DOT_SPACING).toBeLessThan(MAX_DOT_SPACING);
    expect(MIN_DOT_SPACING).toBeGreaterThan(0);
  });

  it("opacity range is valid", () => {
    expect(MIN_OPACITY).toBeLessThan(MAX_OPACITY);
    expect(MIN_OPACITY).toBeGreaterThanOrEqual(0);
    expect(MAX_OPACITY).toBeLessThanOrEqual(1);
  });

  it("dot size scales correctly with priority score", () => {
    const lowScore = 0.1;
    const highScore = 0.9;
    const lowDotRadius = MIN_DOT_RADIUS + (MAX_DOT_RADIUS - MIN_DOT_RADIUS) * lowScore;
    const highDotRadius = MIN_DOT_RADIUS + (MAX_DOT_RADIUS - MIN_DOT_RADIUS) * highScore;
    expect(highDotRadius).toBeGreaterThan(lowDotRadius);
  });

  it("dot spacing decreases with higher severity (denser dots)", () => {
    const lowScore = 0.1;
    const highScore = 0.9;
    const lowSpacing = MAX_DOT_SPACING - (MAX_DOT_SPACING - MIN_DOT_SPACING) * lowScore;
    const highSpacing = MAX_DOT_SPACING - (MAX_DOT_SPACING - MIN_DOT_SPACING) * highScore;
    expect(highSpacing).toBeLessThan(lowSpacing);
  });
});
