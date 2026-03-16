// @vitest-environment jsdom
import "../../__tests__/setup";
import { describe, it, expect, vi } from "vitest";
import { destinationPoint, sectorPoints, createFovCone } from "../WindowFovCone";
import L from "leaflet";

describe("destinationPoint", () => {
  it("bearing 0 (north) increases latitude", () => {
    const start = L.latLng(45, -75);
    const result = destinationPoint(start, 1000, 0);
    expect(result.lat).toBeGreaterThan(45);
    expect(result.lng).toBeCloseTo(-75, 4);
  });

  it("bearing 180 (south) decreases latitude", () => {
    const start = L.latLng(45, -75);
    const result = destinationPoint(start, 1000, 180);
    expect(result.lat).toBeLessThan(45);
    expect(result.lng).toBeCloseTo(-75, 4);
  });

  it("bearing 90 (east) increases longitude", () => {
    const start = L.latLng(45, -75);
    const result = destinationPoint(start, 1000, 90);
    expect(result.lat).toBeCloseTo(45, 4);
    expect(result.lng).toBeGreaterThan(-75);
  });

  it("bearing 270 (west) decreases longitude", () => {
    const start = L.latLng(45, -75);
    const result = destinationPoint(start, 1000, 270);
    expect(result.lat).toBeCloseTo(45, 4);
    expect(result.lng).toBeLessThan(-75);
  });

  it("distance 0 returns the same point", () => {
    const start = L.latLng(45, -75);
    const result = destinationPoint(start, 0, 42);
    expect(result.lat).toBeCloseTo(45, 10);
    expect(result.lng).toBeCloseTo(-75, 10);
  });

  it("1000m displacement is approximately correct", () => {
    const start = L.latLng(0, 0);
    const result = destinationPoint(start, 1000, 0);
    // 1000m north at the equator is ~0.009 degrees latitude
    const expectedDeg = (1000 / 6371000) * (180 / Math.PI);
    expect(result.lat).toBeCloseTo(expectedDeg, 4);
  });
});

describe("sectorPoints", () => {
  it("returns array starting and ending with center", () => {
    const center = L.latLng(45, -75);
    const points = sectorPoints(center, 500, 0, 90, 10);
    expect(points[0]).toBe(center);
    expect(points[points.length - 1]).toBe(center);
  });

  it("returns segments + 3 points (center + segments+1 arc + center)", () => {
    const center = L.latLng(45, -75);
    const segments = 10;
    const points = sectorPoints(center, 500, 0, 90, segments);
    // center + (segments + 1) arc points + center = segments + 3
    expect(points).toHaveLength(segments + 3);
  });

  it("arc points are all different from center", () => {
    const center = L.latLng(45, -75);
    const points = sectorPoints(center, 500, 0, 90, 4);
    // Points 1 through length-2 are arc points (not center)
    for (let i = 1; i < points.length - 1; i++) {
      expect(points[i]).not.toBe(center);
    }
  });

  it("single segment produces 4 points", () => {
    const center = L.latLng(45, -75);
    const points = sectorPoints(center, 500, 0, 90, 1);
    // center + 2 arc endpoints + center
    expect(points).toHaveLength(4);
  });
});

describe("createFovCone", () => {
  it("returns an object with update and remove methods", () => {
    const map = L.map(document.createElement("div"));
    const handle = createFovCone(map, [45, -75], 0, 90, vi.fn());
    expect(typeof handle.update).toBe("function");
    expect(typeof handle.remove).toBe("function");
  });

  it("remove() calls map.removeLayer twice (polygon + handle)", () => {
    const map = L.map(document.createElement("div"));
    const handle = createFovCone(map, [45, -75], 0, 90, vi.fn());
    handle.remove();
    expect(map.removeLayer).toHaveBeenCalledTimes(2);
  });

  it("remove() calls map.off to clean up event listeners", () => {
    const map = L.map(document.createElement("div"));
    const handle = createFovCone(map, [45, -75], 0, 90, vi.fn());
    handle.remove();
    expect(map.off).toHaveBeenCalledWith("mousemove", expect.any(Function));
    expect(map.off).toHaveBeenCalledWith("mouseup", expect.any(Function));
  });

  it("creates polygon and circleMarker via Leaflet", () => {
    const map = L.map(document.createElement("div"));
    createFovCone(map, [45, -75], 0, 90, vi.fn());
    expect(L.polygon).toHaveBeenCalled();
    expect(L.circleMarker).toHaveBeenCalled();
  });
});
