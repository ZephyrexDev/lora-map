import { describe, it, expect } from "vitest";
import type {
  Site,
  SplatParams,
  GeoRaster,
  TowerInfo,
  TowerPath,
  MatrixConfig,
  DeadzoneAnalysis,
  DeadzoneRegion,
  SiteSuggestion,
  AnalysisBounds,
  SimProgress,
} from "../types";

function makeGeoRaster(): GeoRaster {
  return {
    xmin: -115,
    xmax: -114,
    ymin: 50,
    ymax: 51,
    pixelWidth: 0.01,
    pixelHeight: 0.01,
    values: [[[0]]],
    noDataValue: 255,
    width: 100,
    height: 100,
    numberOfRasters: 1,
    projection: 4326,
  };
}

function makeSplatParams(): SplatParams {
  return {
    transmitter: {
      name: "test",
      tx_lat: 51.0,
      tx_lon: -114.0,
      tx_power: 0.1,
      tx_freq: 907.0,
      tx_height: 2.0,
      tx_gain: 2.0,
      tx_swr: 1.5,
      tx_color: "#ff0000",
    },
    receiver: {
      rx_sensitivity: -130.0,
      rx_height: 1.0,
      rx_gain: 2.0,
      rx_loss: 2.0,
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
      simulation_extent: 30.0,
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

describe("GeoRaster interface", () => {
  it("can construct a valid GeoRaster", () => {
    const raster = makeGeoRaster();
    expect(raster.xmin).toBeLessThan(raster.xmax);
    expect(raster.ymin).toBeLessThan(raster.ymax);
    expect(raster.pixelWidth).toBeGreaterThan(0);
    expect(raster.pixelHeight).toBeGreaterThan(0);
    expect(raster.values).toHaveLength(1);
    expect(raster.numberOfRasters).toBe(1);
  });

  it("noDataValue is optional", () => {
    const raster: GeoRaster = {
      ...makeGeoRaster(),
      noDataValue: undefined,
    };
    expect(raster.noDataValue).toBeUndefined();
  });
});

describe("Site interface", () => {
  it("can construct a valid Site object", () => {
    const site: Site = {
      params: makeSplatParams(),
      taskId: "abc-123",
      raster: makeGeoRaster(),
      visible: true,
      color: "#ff0000",
    };

    expect(site.taskId).toBe("abc-123");
    expect(site.visible).toBe(true);
    expect(site.color).toBe("#ff0000");
    expect(site.params.transmitter.tx_swr).toBe(1.5);
    expect(site.params.transmitter.tx_color).toBe("#ff0000");
    expect(site.raster.xmin).toBe(-115);
  });
});

describe("SplatParams interface", () => {
  it("has all five sections", () => {
    const params = makeSplatParams();
    expect(Object.keys(params)).toEqual(
      expect.arrayContaining(["transmitter", "receiver", "environment", "simulation", "display"]),
    );
  });

  it("tx_swr and tx_color are optional", () => {
    const params: SplatParams = {
      ...makeSplatParams(),
      transmitter: {
        name: "basic",
        tx_lat: 0,
        tx_lon: 0,
        tx_power: 0.1,
        tx_freq: 907,
        tx_height: 2,
        tx_gain: 2,
      },
    };
    expect(params.transmitter.tx_swr).toBeUndefined();
    expect(params.transmitter.tx_color).toBeUndefined();
  });

  it("overlapMode accepts only hatch or blend", () => {
    const params = makeSplatParams();
    expect(["hatch", "blend"]).toContain(params.display.overlapMode);
  });
});

describe("TowerInfo interface", () => {
  it("can construct a valid TowerInfo", () => {
    const info: TowerInfo = {
      raster: makeGeoRaster(),
      color: "#e6194b",
      index: 0,
    };
    expect(info.color).toBe("#e6194b");
    expect(info.index).toBe(0);
  });
});

describe("TowerPath interface", () => {
  it("can construct a valid TowerPath", () => {
    const path: TowerPath = {
      id: "path-1",
      tower_a_id: "tower-a",
      tower_b_id: "tower-b",
      lat_a: 51.0,
      lon_a: -114.0,
      lat_b: 51.1,
      lon_b: -114.1,
      path_loss_db: 105.5,
      has_los: true,
      distance_km: 12.3,
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(path.path_loss_db).toBe(105.5);
    expect(path.has_los).toBe(true);
    expect(path.distance_km).toBe(12.3);
  });

  it("handles pending path with null values", () => {
    const path: TowerPath = {
      id: "path-2",
      tower_a_id: "a",
      tower_b_id: "b",
      lat_a: 0,
      lon_a: 0,
      lat_b: 1,
      lon_b: 1,
      path_loss_db: null,
      has_los: null,
      distance_km: null,
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(path.path_loss_db).toBeNull();
    expect(path.has_los).toBeNull();
    expect(path.distance_km).toBeNull();
  });
});

describe("MatrixConfig interface", () => {
  it("can construct a valid MatrixConfig", () => {
    const config: MatrixConfig = {
      hardware: { v3: true, v4: false },
      antennas: { bingfu_whip: true, duck_stubby: true, ribbed_spring_helical: false, slinkdsco_omni: false },
      terrain: { bare_earth: true, dsm: false, lulc_clutter: false },
    };
    expect(config.hardware.v3).toBe(true);
    expect(config.hardware.v4).toBe(false);
    expect(Object.keys(config.antennas).filter((k) => config.antennas[k])).toHaveLength(2);
  });
});

describe("DeadzoneAnalysis interface", () => {
  it("can construct a valid DeadzoneAnalysis", () => {
    const bounds: AnalysisBounds = { north: 52, south: 50, east: -113, west: -115 };
    const suggestion: SiteSuggestion = {
      lat: 51.5,
      lon: -114.5,
      estimated_coverage_km2: 15.0,
      priority_rank: 1,
      reason: "Large gap",
    };
    const region: DeadzoneRegion = {
      region_id: 1,
      center_lat: 51.5,
      center_lon: -114.5,
      area_km2: 20.0,
      priority_score: 0.8,
      pixel_count: 500,
      suggestion,
    };
    const analysis: DeadzoneAnalysis = {
      bounds,
      total_coverage_km2: 100.0,
      total_deadzone_km2: 20.0,
      coverage_fraction: 0.83,
      regions: [region],
      suggestions: [suggestion],
      tower_count: 3,
    };
    expect(analysis.coverage_fraction).toBeCloseTo(0.83);
    expect(analysis.regions).toHaveLength(1);
    expect(analysis.suggestions).toHaveLength(1);
    expect(analysis.tower_count).toBe(3);
  });
});

describe("SimProgress interface", () => {
  it("can construct a valid SimProgress", () => {
    const progress: SimProgress = { total: 8, completed: 5, pending: 3 };
    expect(progress.total).toBe(progress.completed + progress.pending);
  });
});
