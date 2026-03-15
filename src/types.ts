/**
 * Minimal type for parsed georaster objects from the `georaster` library,
 * which does not ship its own TypeScript definitions.
 */
export interface GeoRaster {
  readonly xmin: number;
  readonly xmax: number;
  readonly ymin: number;
  readonly ymax: number;
  readonly pixelWidth: number;
  readonly pixelHeight: number;
  readonly values: number[][][];
  readonly noDataValue?: number;
  readonly width: number;
  readonly height: number;
  readonly numberOfRasters: number;
  readonly projection: number;
}

/** Mutable — toggled by admin in MatrixConfig UI. */
export interface MatrixConfig {
  hardware: Record<string, boolean>;
  antennas: Record<string, boolean>;
  terrain: Record<string, boolean>;
}

export interface TowerPath {
  readonly id: string;
  readonly tower_a_id: string;
  readonly tower_b_id: string;
  readonly lat_a: number;
  readonly lon_a: number;
  readonly lat_b: number;
  readonly lon_b: number;
  readonly path_loss_db: number | null;
  readonly has_los: boolean | null;
  readonly distance_km: number | null;
  readonly created_at: string;
}

export interface AnalysisBounds {
  readonly north: number;
  readonly south: number;
  readonly east: number;
  readonly west: number;
}

export interface SiteSuggestion {
  readonly lat: number;
  readonly lon: number;
  readonly estimated_coverage_km2: number;
  readonly priority_rank: number;
  readonly reason: string;
}

export interface DeadzoneRegion {
  readonly region_id: number;
  readonly center_lat: number;
  readonly center_lon: number;
  readonly area_km2: number;
  readonly priority_score: number;
  readonly pixel_count: number;
  readonly suggestion: SiteSuggestion | null;
}

export interface DeadzoneAnalysis {
  readonly bounds: AnalysisBounds;
  readonly total_coverage_km2: number;
  readonly total_deadzone_km2: number;
  readonly coverage_fraction: number;
  readonly regions: readonly DeadzoneRegion[];
  readonly suggestions: readonly SiteSuggestion[];
  readonly tower_count: number;
}

export interface TowerInfo {
  readonly raster: GeoRaster;
  readonly color: string;
  readonly index: number;
}

export interface SimProgress {
  readonly total: number;
  readonly completed: number;
  readonly pending: number;
}

/** A single simulation row returned by GET /towers/{id}/simulations. */
export interface SimulationRecord {
  readonly id: string;
  readonly client_hardware: string;
  readonly client_antenna: string;
  readonly terrain_model: string;
  readonly status: string;
}

/** Mutable — raster and visible are updated by store actions. */
export interface Site {
  readonly params: SplatParams;
  readonly taskId: string;
  raster: GeoRaster;
  readonly color: string;
  visible: boolean;
}

/** Mutable — bound to Vue form inputs via v-model. */
export interface SplatParams {
  transmitter: {
    name: string;
    tx_lat: number;
    tx_lon: number;
    tx_power: number;
    tx_freq: number;
    tx_height: number;
    tx_gain: number;
    tx_swr?: number;
    tx_color?: string;
  };
  receiver: {
    rx_sensitivity: number;
    rx_height: number;
    rx_gain: number;
    rx_loss: number;
  };
  environment: {
    radio_climate: string;
    polarization: string;
    clutter_height: number;
    ground_dielectric: number;
    ground_conductivity: number;
    atmosphere_bending: number;
  };
  simulation: {
    situation_fraction: number;
    time_fraction: number;
    simulation_extent: number;
    high_resolution: boolean;
  };
  display: {
    color_scale: string;
    min_dbm: number;
    max_dbm: number;
    overlay_transparency: number;
    overlapMode: "hatch" | "blend";
  };
}
