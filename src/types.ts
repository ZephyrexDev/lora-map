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
    north: number;
    south: number;
    east: number;
    west: number;
}

export interface SiteSuggestion {
    lat: number;
    lon: number;
    estimated_coverage_km2: number;
    priority_rank: number;
    reason: string;
}

export interface DeadzoneRegion {
    region_id: number;
    center_lat: number;
    center_lon: number;
    area_km2: number;
    priority_score: number;
    pixel_count: number;
    suggestion: SiteSuggestion | null;
}

export interface DeadzoneAnalysis {
    bounds: AnalysisBounds;
    total_coverage_km2: number;
    total_deadzone_km2: number;
    coverage_fraction: number;
    regions: DeadzoneRegion[];
    suggestions: SiteSuggestion[];
    tower_count: number;
}

export interface TowerInfo {
    raster: any;
    color: string;
    index: number;
}

export interface SimProgress {
    total: number;
    completed: number;
    pending: number;
}

export interface Site {
    params: SplatParams;
    taskId: string;
    raster: any;
    color: string;
    visible: boolean;
}
export interface SplatParams {
    transmitter: {
        name: string;
        tx_lat: number;
        tx_lon: number;
        tx_power: number;
        tx_freq: number;
        tx_height: number;
        tx_gain: number;
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
        overlapMode: 'hatch' | 'blend';
    };
}