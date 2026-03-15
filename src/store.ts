import { defineStore } from "pinia";
import { randanimalSync } from "randanimal";
import L from "leaflet";
import GeoRasterLayer from "georaster-layer-for-leaflet";
import parseGeoraster from "georaster";
import "leaflet-easyprint";
import {
  type Site,
  type SplatParams,
  type MatrixConfig,
  type TowerPath,
  type DeadzoneAnalysis,
  type TowerInfo,
} from "./types.ts";
import { cloneObject } from "./utils.ts";
import { redPinMarker } from "./layers.ts";
import { createOverlapHatchLayer } from "./layers/OverlapHatchLayer.ts";
import { DeadzoneCanvasLayer } from "./deadzoneLayer.ts";

/**
 * Map path loss (dB) and LOS status to a color for polyline rendering.
 * Green = good (low loss, LOS), yellow = marginal, red = poor (high loss or NLOS).
 */
function pathLossColor(pathLossDb: number, hasLos: boolean | null): string {
  if (hasLos === false) return "#e74c3c"; // red for NLOS
  if (pathLossDb < 100) return "#2ecc71";
  if (pathLossDb < 120) return "#f1c40f";
  if (pathLossDb < 140) return "#e67e22";
  return "#e74c3c";
}

// Default tower colors for visual differentiation
const TOWER_COLORS = [
  "#e6194b", // red
  "#3cb44b", // green
  "#4363d8", // blue
  "#f58231", // orange
  "#911eb4", // purple
  "#42d4f4", // cyan
  "#f032e6", // magenta
  "#bfef45", // lime
  "#fabed4", // pink
  "#469990", // teal
  "#dcbeff", // lavender
  "#9a6324", // brown
];

const useStore = defineStore("store", {
  state() {
    return {
      map: undefined as undefined | L.Map,
      currentMarker: undefined as undefined | L.Marker,
      localSites: [] as Site[],
      overlapLayer: undefined as undefined | L.GridLayer,
      simulationState: "idle",
      isAdmin: false,
      adminToken: localStorage.getItem("adminToken") || "",
      clientHardware: "v3" as string,
      clientAntenna: "bingfu_whip" as string,
      towerPaths: [] as TowerPath[],
      towerPathLayers: [] as L.Polyline[],
      showTowerPaths: true,
      showDeadzones: false,
      deadzoneAnalysis: null as DeadzoneAnalysis | null,
      deadzoneLayer: null as DeadzoneCanvasLayer | null,
      suggestionMarkers: [] as L.Marker[],
      matrixConfig: null as MatrixConfig | null,
      splatParams: <SplatParams>{
        transmitter: {
          name: randanimalSync(),
          tx_lat: 51.102167,
          tx_lon: -114.098667,
          tx_power: 0.1,
          tx_freq: 907.0,
          tx_height: 2.0,
          tx_gain: 2.0,
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
          overlapMode: "hatch" as "hatch" | "blend",
        },
      },
    };
  },
  actions: {
    async loadMatrixConfig(): Promise<void> {
      try {
        const response = await fetch("/matrix/config");
        if (response.ok) {
          this.matrixConfig = await response.json();
        }
      } catch (err) {
        console.warn("Error loading matrix config:", err);
      }
    },
    async loadTowerPaths(): Promise<void> {
      try {
        const response = await fetch("/tower-paths");
        if (!response.ok) {
          console.warn("Failed to load tower paths:", response.statusText);
          return;
        }
        const data = await response.json();
        this.towerPaths = data.paths ?? [];
        this.renderTowerPaths();
      } catch (err) {
        console.warn("Error loading tower paths:", err);
      }
    },
    renderTowerPaths(): void {
      if (!this.map) return;

      for (const layer of this.towerPathLayers) {
        this.map.removeLayer(layer);
      }
      this.towerPathLayers = [];

      if (!this.showTowerPaths) return;

      for (const path of this.towerPaths) {
        if (path.path_loss_db === null) continue;

        const color = pathLossColor(path.path_loss_db, path.has_los);
        const polyline = L.polyline(
          [
            [path.lat_a, path.lon_a],
            [path.lat_b, path.lon_b],
          ],
          {
            color,
            weight: 3,
            opacity: 0.8,
            dashArray: path.has_los ? undefined : "8, 6",
          },
        );

        const lossText = path.path_loss_db !== null ? `${path.path_loss_db.toFixed(1)} dB` : "pending";
        const losText = path.has_los === null ? "pending" : path.has_los ? "Yes" : "No";
        const distText = path.distance_km !== null ? `${path.distance_km.toFixed(1)} km` : "pending";
        polyline.bindPopup(`<b>Path Loss:</b> ${lossText}<br><b>LOS:</b> ${losText}<br><b>Distance:</b> ${distText}`);

        polyline.addTo(this.map);
        this.towerPathLayers.push(polyline);
      }
    },
    toggleTowerPaths(): void {
      this.showTowerPaths = !this.showTowerPaths;
      this.renderTowerPaths();
    },
    async fetchDeadzones(): Promise<void> {
      if (this.localSites.length < 2) {
        this._clearDeadzoneOverlay();
        this.deadzoneAnalysis = null;
        return;
      }

      try {
        const response = await fetch("/deadzones");
        if (!response.ok) {
          console.warn("Deadzone analysis unavailable:", response.status);
          return;
        }
        this.deadzoneAnalysis = await response.json();
        if (this.showDeadzones) {
          this._renderDeadzoneOverlay();
        }
      } catch (error) {
        console.error("Failed to fetch deadzone analysis:", error);
      }
    },
    toggleDeadzones(): void {
      this.showDeadzones = !this.showDeadzones;
      if (this.showDeadzones) {
        this.fetchDeadzones();
      } else {
        this._clearDeadzoneOverlay();
      }
    },
    _renderDeadzoneOverlay(): void {
      if (!this.map || !this.deadzoneAnalysis) return;

      this._clearDeadzoneOverlay();

      const layer = new DeadzoneCanvasLayer(this.deadzoneAnalysis.regions);
      layer.addTo(this.map);
      this.deadzoneLayer = layer;

      for (const suggestion of this.deadzoneAnalysis.suggestions) {
        const icon = L.divIcon({
          html: `<div style="
            background: #0d6efd;
            color: white;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
            border: 2px solid white;
            box-shadow: 0 1px 4px rgba(0,0,0,0.4);
          ">${suggestion.priority_rank}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
          className: "",
        });

        const marker = L.marker([suggestion.lat, suggestion.lon], { icon }).addTo(this.map);

        marker.bindPopup(`
          <div style="min-width: 200px">
            <strong>Suggested Site #${suggestion.priority_rank}</strong><br>
            <small>${suggestion.reason}</small><br>
            <hr style="margin: 4px 0">
            <b>Est. coverage:</b> ${suggestion.estimated_coverage_km2.toFixed(1)} km&sup2;<br>
            <b>Location:</b> ${suggestion.lat.toFixed(4)}, ${suggestion.lon.toFixed(4)}<br>
            <button class="btn btn-sm btn-primary mt-2" onclick="
              window.dispatchEvent(new CustomEvent('prefill-transmitter', {
                detail: { lat: ${suggestion.lat}, lon: ${suggestion.lon} }
              }))
            ">Use as transmitter site</button>
          </div>
        `);
        this.suggestionMarkers.push(marker);
      }
    },
    _clearDeadzoneOverlay(): void {
      if (this.deadzoneLayer && this.map) {
        this.map.removeLayer(this.deadzoneLayer as unknown as L.Layer);
        this.deadzoneLayer = null;
      }
      for (const marker of this.suggestionMarkers) {
        if (this.map) {
          this.map.removeLayer(marker);
        }
      }
      this.suggestionMarkers = [];
    },
    async login(password: string): Promise<boolean> {
      try {
        const response = await fetch("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password }),
        });
        if (!response.ok) return false;
        const data = await response.json();
        this.adminToken = data.token;
        this.isAdmin = true;
        localStorage.setItem("adminToken", this.adminToken);
        return true;
      } catch {
        return false;
      }
    },
    logout() {
      this.adminToken = "";
      this.isAdmin = false;
      localStorage.removeItem("adminToken");
    },
    async checkAuth(): Promise<void> {
      if (!this.adminToken) return;
      try {
        const response = await fetch("/auth/check", {
          headers: { Authorization: `Bearer ${this.adminToken}` },
        });
        if (response.ok) {
          this.isAdmin = true;
        } else {
          this.adminToken = "";
          this.isAdmin = false;
          localStorage.removeItem("adminToken");
        }
      } catch {
        this.adminToken = "";
        this.isAdmin = false;
        localStorage.removeItem("adminToken");
      }
    },
    async swapSimulationLayer(towerId: string, simId: string): Promise<void> {
      try {
        const resultResponse = await fetch(`/simulations/${simId}/result`);
        if (!resultResponse.ok) {
          console.warn("Failed to fetch simulation result:", resultResponse.statusText);
          return;
        }
        const arrayBuffer = await resultResponse.arrayBuffer();
        const geoRaster = await parseGeoraster(arrayBuffer);
        const site = this.localSites.find((s: Site) => s.taskId === towerId);
        if (!site) {
          console.warn("No site found for tower:", towerId);
          return;
        }
        site.raster = geoRaster;
        this.redrawSites();
        this.updateOverlapLayer();
      } catch (err) {
        console.warn("Error swapping simulation layer:", err);
      }
    },
    setTxCoords(lat: number, lon: number) {
      this.splatParams.transmitter.tx_lat = lat;
      this.splatParams.transmitter.tx_lon = lon;
    },
    removeSite(index: number) {
      if (!this.map) {
        return;
      }
      this.localSites.splice(index, 1);
      this.map.eachLayer((layer: L.Layer) => {
        if (layer instanceof GeoRasterLayer) {
          this.map!.removeLayer(layer);
        }
      });
      this.redrawSites();
      this.updateOverlapLayer();
      if (this.showDeadzones) {
        this.fetchDeadzones();
      }
    },
    toggleSiteVisibility(index: number) {
      if (index < 0 || index >= this.localSites.length) return;
      this.localSites[index].visible = !this.localSites[index].visible;
      this.redrawSites();
      this.updateOverlapLayer();
    },
    redrawSites() {
      if (!this.map) {
        return;
      }

      // Remove existing GeoRasterLayers
      this.map.eachLayer((layer: L.Layer) => {
        if (layer instanceof GeoRasterLayer) {
          this.map!.removeLayer(layer);
        }
      });

      // Determine if overlap layer is active (will handle rendering)
      const visibleSites = this.localSites.filter((s: Site) => s.visible);
      const overlapActive = visibleSites.length >= 2;

      // Add GeoRasterLayers back to the map
      this.localSites.forEach((site: Site) => {
        if (!site.visible) return;
        const rasterLayer = new GeoRasterLayer({
          georaster: { ...site }.raster,
          opacity: overlapActive ? 0 : 0.7,
          noDataValue: 255,
          resolution: 256,
        });
        rasterLayer.addTo(this.map as L.Map);
        rasterLayer.bringToFront();
      });
    },
    updateOverlapLayer() {
      if (!this.map) return;

      // Remove old overlap layer if it exists
      if (this.overlapLayer) {
        this.map.removeLayer(this.overlapLayer);
        this.overlapLayer = undefined;
      }

      // Collect all visible sites that have raster data
      const visibleSites = this.localSites.filter((s: Site) => s.visible && s.raster);

      // Only create overlap layer when 2+ visible towers
      if (visibleSites.length < 2) {
        // Restore individual layer opacities by redrawing
        this.redrawSites();
        return;
      }

      // Build tower info array
      const towers: TowerInfo[] = visibleSites.map((site: Site, i: number) => ({
        raster: site.raster,
        color: site.color,
        index: i,
      }));

      // Create the overlap layer
      this.overlapLayer = createOverlapHatchLayer({
        towers,
        mode: this.splatParams.display.overlapMode,
        minDbm: this.splatParams.display.min_dbm,
        maxDbm: this.splatParams.display.max_dbm,
        opacity: 1,
      });

      this.overlapLayer.addTo(this.map);
      this.overlapLayer.bringToFront();

      // Ensure individual GeoRasterLayers are hidden (overlap layer handles rendering)
      this.redrawSites();
    },
    initMap() {
      this.map = L.map("map", {
        // center: [51.102167, -114.098667],
        zoom: 10,
        zoomControl: false,
      });
      const position: [number, number] = [this.splatParams.transmitter.tx_lat, this.splatParams.transmitter.tx_lon];
      this.map.setView(position, 10);

      L.control.zoom({ position: "bottomleft" }).addTo(this.map as L.Map);

      const cartoLight = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        attribution: "© OpenStreetMap contributors © CARTO",
      });

      const streetLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
      });

      const satelliteLayer = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          attribution: "Tiles © Esri — Source: Esri, USGS, NOAA",
        },
      );

      const topoLayer = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
        attribution: "Map data: © OpenStreetMap contributors, SRTM | OpenTopoMap",
      });

      streetLayer.addTo(this.map as L.Map);

      // Base Layers
      const baseLayers = {
        OSM: streetLayer,
        "Carto Light": cartoLight,
        Satellite: satelliteLayer,
        "Topo Map": topoLayer,
      };

      // EasyPrint control
      (L as any)
        .easyPrint({
          title: "Save",
          position: "bottomleft",
          sizeModes: ["A4Portrait", "A4Landscape"],
          filename: "sites",
          exportOnly: true,
        })
        .addTo(this.map as L.Map);

      L.control
        .layers(
          baseLayers,
          {},
          {
            position: "bottomleft",
          },
        )
        .addTo(this.map as L.Map);

      this.map.on("baselayerchange", () => {
        this.redrawSites(); // Re-apply the GeoRasterLayer on top
      });
      this.currentMarker = L.marker(position, { icon: redPinMarker })
        .addTo(this.map as L.Map)
        .bindPopup("Transmitter site");
      this.redrawSites();
      this.loadTowerPaths();
    },
    async runSimulation() {
      try {
        // Collect input values
        const payload = {
          // Transmitter parameters
          lat: this.splatParams.transmitter.tx_lat,
          lon: this.splatParams.transmitter.tx_lon,
          tx_height: this.splatParams.transmitter.tx_height,
          tx_power: 10 * Math.log10(this.splatParams.transmitter.tx_power) + 30,
          tx_gain: this.splatParams.transmitter.tx_gain,
          frequency_mhz: this.splatParams.transmitter.tx_freq,

          // Receiver parameters
          rx_height: this.splatParams.receiver.rx_height,
          rx_gain: this.splatParams.receiver.rx_gain,
          signal_threshold: this.splatParams.receiver.rx_sensitivity,
          system_loss: this.splatParams.receiver.rx_loss,

          // Environment parameters
          clutter_height: this.splatParams.environment.clutter_height,
          ground_dielectric: this.splatParams.environment.ground_dielectric,
          ground_conductivity: this.splatParams.environment.ground_conductivity,
          atmosphere_bending: this.splatParams.environment.atmosphere_bending,
          radio_climate: this.splatParams.environment.radio_climate,
          polarization: this.splatParams.environment.polarization,

          // Simulation parameters
          radius: this.splatParams.simulation.simulation_extent * 1000,
          situation_fraction: this.splatParams.simulation.situation_fraction,
          time_fraction: this.splatParams.simulation.time_fraction,
          high_resolution: this.splatParams.simulation.high_resolution,

          // Display parameters
          colormap: this.splatParams.display.color_scale,
          min_dbm: this.splatParams.display.min_dbm,
          max_dbm: this.splatParams.display.max_dbm,
        };

        this.simulationState = "running";

        // Send the request to the backend's /predict endpoint
        const predictResponse = await fetch("/predict", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!predictResponse.ok) {
          this.simulationState = "failed";
          const errorDetails = await predictResponse.text();
          throw new Error(`Failed to start prediction: ${errorDetails}`);
        }

        const predictData = await predictResponse.json();
        const taskId = predictData.task_id;

        // Poll for task status and result
        const pollInterval = 1000; // 1 seconds
        const pollStatus = async () => {
          const statusResponse = await fetch(`/status/${taskId}`);
          if (!statusResponse.ok) {
            throw new Error("Failed to fetch task status.");
          }

          const statusData = await statusResponse.json();

          if (statusData.status === "completed") {
            this.simulationState = "completed";

            // Fetch the GeoTIFF data
            const resultResponse = await fetch(`/result/${taskId}`);
            if (!resultResponse.ok) {
              throw new Error("Failed to fetch simulation result.");
            } else {
              const arrayBuffer = await resultResponse.arrayBuffer();
              const geoRaster = await parseGeoraster(arrayBuffer);
              const colorIndex = this.localSites.length % TOWER_COLORS.length;
              this.localSites.push({
                params: cloneObject(this.splatParams),
                taskId,
                raster: geoRaster,
                color: TOWER_COLORS[colorIndex],
                visible: true,
              });
              this.currentMarker!.removeFrom(this.map as L.Map);
              this.splatParams.transmitter.name = await randanimalSync();
              this.redrawSites();
              this.updateOverlapLayer();
              // Reload tower paths since the new tower may have triggered path computation
              setTimeout(() => this.loadTowerPaths(), 5000);
              if (this.showDeadzones) {
                this.fetchDeadzones();
              }
            }
          } else if (statusData.status === "failed") {
            this.simulationState = "failed";
          } else {
            setTimeout(pollStatus, pollInterval); // Retry after interval
          }
        };

        pollStatus(); // Start polling
      } catch (error) {
        console.error("Error:", error);
      }
    },
  },
});

export { useStore };
