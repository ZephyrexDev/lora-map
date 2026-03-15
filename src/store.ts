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
  type SimulationRecord,
} from "./types.ts";
import { cloneObject, pathLossColor, TOWER_COLORS, buildSimulationPayload } from "./utils.ts";
import { redPinMarker } from "./layers.ts";
import { createOverlapHatchLayer } from "./layers/OverlapHatchLayer.ts";
import { DeadzoneCanvasLayer } from "./deadzoneLayer.ts";

/** Delay (ms) before reloading tower paths after a simulation completes. */
const PATH_RELOAD_DELAY_MS = 5000;
/** Interval (ms) between simulation status polls. */
const POLL_INTERVAL_MS = 1000;
/** Maximum number of status polls before declaring a timeout (~5 minutes). */
const MAX_POLL_COUNT = 300;
/** Default map zoom level. */
const DEFAULT_ZOOM = 10;

const useStore = defineStore("store", {
  state() {
    return {
      map: undefined as undefined | L.Map,
      currentMarker: undefined as undefined | L.Marker,
      localSites: [] as Site[],
      overlapLayer: undefined as undefined | L.GridLayer,
      simulationState: "idle" as "idle" | "running" | "completed" | "failed",
      simulationError: "" as string,
      isAdmin: false,
      adminToken: localStorage.getItem("adminToken") ?? "",
      clientHardware: "v3" as string,
      clientAntenna: "bingfu_whip" as string,
      clientTerrain: "bare_earth" as string,
      towerPaths: [] as TowerPath[],
      towerPathLayers: [] as L.Polyline[],
      showTowerPaths: true,
      showDeadzones: false,
      deadzoneAnalysis: null as DeadzoneAnalysis | null,
      deadzoneLayer: null as DeadzoneCanvasLayer | null,
      suggestionMarkers: [] as L.Marker[],
      _pathReloadTimer: 0 as number,
      _pollTimer: 0 as number,
      _prefillCoords: null as { lat: number; lon: number } | null,
      matrixConfig: null as MatrixConfig | null,
      splatParams: <SplatParams>{
        transmitter: {
          name: randanimalSync(),
          tx_lat: 53.5461,
          tx_lon: -113.4937,
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
    async loadTowers(): Promise<void> {
      try {
        const response = await fetch("/towers");
        if (!response.ok) return;
        const data = await response.json();
        const towers: { id: string; name: string; color: string | null; params: Record<string, unknown> }[] =
          data.towers ?? [];

        const newTowers = towers.filter((tower) => !this.localSites.find((s: Site) => s.taskId === tower.id));

        const fetchResults = await Promise.allSettled(
          newTowers.map(async (tower) => {
            const simResponse = await fetch(`/towers/${tower.id}/simulations?enabled_only=true`);
            if (!simResponse.ok) return null;
            const simData = await simResponse.json();
            const sims: SimulationRecord[] = simData.simulations ?? [];
            const completedSim =
              sims.find(
                (s) =>
                  s.status === "completed" &&
                  s.client_hardware === this.clientHardware &&
                  s.client_antenna === this.clientAntenna &&
                  s.terrain_model === "bare_earth",
              ) ?? sims.find((s) => s.status === "completed");

            if (!completedSim) return null;

            const resultResponse = await fetch(`/simulations/${completedSim.id}/result`);
            if (!resultResponse.ok) return null;
            const arrayBuffer = await resultResponse.arrayBuffer();
            const geoRaster = await parseGeoraster(arrayBuffer);

            return { tower, geoRaster };
          }),
        );

        for (const result of fetchResults) {
          if (result.status !== "fulfilled" || !result.value) {
            if (result.status === "rejected") {
              console.warn("Error loading simulation for tower:", result.reason);
            }
            continue;
          }
          const { tower, geoRaster } = result.value;
          const { params } = tower;
          if (!params.transmitter || !params.receiver || !params.environment || !params.simulation || !params.display) {
            console.warn("Skipping tower with malformed params:", tower.id);
            continue;
          }
          const colorIndex = this.localSites.length % TOWER_COLORS.length;
          this.localSites.push({
            params: params as SplatParams,
            taskId: tower.id,
            raster: geoRaster,
            color: tower.color ?? TOWER_COLORS[colorIndex],
            visible: true,
          });
        }

        if (this.localSites.length > 0) {
          this.updateOverlapLayer();
        }
      } catch (err) {
        console.warn("Error loading towers:", err);
      }
    },
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

        const lossText = `${path.path_loss_db.toFixed(1)} dB`;
        let losText = "pending";
        if (path.has_los !== null) {
          losText = path.has_los ? "Yes" : "No";
        }
        const distText = path.distance_km !== null ? `${path.distance_km.toFixed(1)} km` : "pending";

        const popupEl = document.createElement("div");
        const addLine = (label: string, value: string) => {
          const b = document.createElement("b");
          b.textContent = `${label}: `;
          popupEl.appendChild(b);
          popupEl.appendChild(document.createTextNode(value));
          popupEl.appendChild(document.createElement("br"));
        };
        addLine("Path Loss", lossText);
        addLine("LOS", losText);
        addLine("Distance", distText);
        polyline.bindPopup(popupEl);

        polyline.addTo(this.map);
        this.towerPathLayers.push(polyline);
      }
    },
    clearTowerPaths(): void {
      if (!this.map) return;
      for (const layer of this.towerPathLayers) {
        this.map.removeLayer(layer);
      }
      this.towerPathLayers = [];
    },
    toggleTowerPaths(): void {
      this.showTowerPaths = !this.showTowerPaths;
      if (this.showTowerPaths) {
        this.renderTowerPaths();
      } else {
        this.clearTowerPaths();
      }
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
        void this.fetchDeadzones();
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
        const iconEl = document.createElement("div");
        iconEl.style.cssText =
          "background:#0d6efd;color:white;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.4)";
        iconEl.textContent = String(suggestion.priority_rank);
        const icon = L.divIcon({
          html: iconEl.outerHTML,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
          className: "",
        });

        const marker = L.marker([suggestion.lat, suggestion.lon], { icon }).addTo(this.map);

        const popupEl = document.createElement("div");
        popupEl.style.maxWidth = "min(200px, 80vw)";

        const title = document.createElement("strong");
        title.textContent = `Suggested Site #${suggestion.priority_rank}`;
        popupEl.appendChild(title);
        popupEl.appendChild(document.createElement("br"));

        const reason = document.createElement("small");
        reason.textContent = suggestion.reason;
        popupEl.appendChild(reason);
        popupEl.appendChild(document.createElement("br"));

        const hr = document.createElement("hr");
        hr.style.margin = "4px 0";
        popupEl.appendChild(hr);

        const coverageLabel = document.createElement("b");
        coverageLabel.textContent = "Est. coverage: ";
        popupEl.appendChild(coverageLabel);
        popupEl.appendChild(document.createTextNode(`${suggestion.estimated_coverage_km2.toFixed(1)} km\u00B2`));
        popupEl.appendChild(document.createElement("br"));

        const locationLabel = document.createElement("b");
        locationLabel.textContent = "Location: ";
        popupEl.appendChild(locationLabel);
        popupEl.appendChild(document.createTextNode(`${suggestion.lat.toFixed(4)}, ${suggestion.lon.toFixed(4)}`));
        popupEl.appendChild(document.createElement("br"));

        const btn = document.createElement("button");
        btn.className = "btn btn-sm btn-primary mt-2 js-prefill-btn";
        btn.textContent = "Use as transmitter site";
        popupEl.appendChild(btn);

        const { lat, lon } = suggestion;
        btn.addEventListener("click", () => {
          this.prefillTransmitter(lat, lon);
        });

        marker.bindPopup(popupEl);

        this.suggestionMarkers.push(marker);
      }
    },
    _clearDeadzoneOverlay(): void {
      if (this.deadzoneLayer && this.map) {
        this.map.removeLayer(this.deadzoneLayer);
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
        await this.swapSimulationLayerFromBuffer(towerId, arrayBuffer);
      } catch (err) {
        console.warn("Error swapping simulation layer:", err);
      }
    },
    async swapSimulationLayerFromBuffer(towerId: string, arrayBuffer: ArrayBuffer): Promise<void> {
      const geoRaster = await parseGeoraster(arrayBuffer);
      const site = this.localSites.find((s: Site) => s.taskId === towerId);
      if (!site) {
        console.warn("No site found for tower:", towerId);
        return;
      }
      site.raster = geoRaster;
      this.updateOverlapLayer();
    },
    setTxCoords(lat: number, lon: number) {
      this.splatParams.transmitter.tx_lat = lat;
      this.splatParams.transmitter.tx_lon = lon;
    },
    prefillTransmitter(lat: number, lon: number) {
      this._prefillCoords = { lat, lon };
    },
    async removeSite(index: number) {
      if (!this.map) return;
      const site = this.localSites[index];

      // Delete from backend if we have admin credentials and a tower ID
      if (this.adminToken && site.taskId) {
        try {
          const response = await fetch(`/towers/${site.taskId}`, {
            method: "DELETE",
            headers: { Authorization: `Bearer ${this.adminToken}` },
          });
          if (!response.ok) {
            console.warn("Failed to delete tower from backend:", response.statusText);
          }
        } catch (err) {
          console.warn("Error deleting tower:", err);
        }
      }

      this.localSites.splice(index, 1);
      const { map } = this;
      map.eachLayer((layer: L.Layer) => {
        if (layer instanceof GeoRasterLayer) {
          map.removeLayer(layer);
        }
      });
      this.updateOverlapLayer();
      if (this.showDeadzones) {
        void this.fetchDeadzones();
      }
      if (this.showTowerPaths) {
        void this.loadTowerPaths();
      }
    },
    toggleSiteVisibility(index: number) {
      if (index < 0 || index >= this.localSites.length) return;
      this.localSites[index].visible = !this.localSites[index].visible;
      this.updateOverlapLayer();
    },
    redrawSites() {
      if (!this.map) {
        return;
      }
      const { map } = this;

      // Remove existing GeoRasterLayers
      map.eachLayer((layer: L.Layer) => {
        if (layer instanceof GeoRasterLayer) {
          map.removeLayer(layer);
        }
      });

      // Determine if overlap layer is active (will handle rendering)
      const visibleSites = this.localSites.filter((s: Site) => s.visible);
      const overlapActive = visibleSites.length >= 2;

      // Add GeoRasterLayers back to the map
      this.localSites.forEach((site: Site) => {
        if (!site.visible) return;
        const userOpacity = 1 - this.splatParams.display.overlay_transparency / 100;
        const rasterLayer = new GeoRasterLayer({
          georaster: site.raster,
          opacity: overlapActive ? 0 : userOpacity,
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
      const visibleSites = this.localSites.filter((s: Site) => s.visible);

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
      const overlapOpacity = 1 - this.splatParams.display.overlay_transparency / 100;
      this.overlapLayer = createOverlapHatchLayer({
        towers,
        mode: this.splatParams.display.overlapMode,
        minDbm: this.splatParams.display.min_dbm,
        maxDbm: this.splatParams.display.max_dbm,
        opacity: overlapOpacity,
      });

      this.overlapLayer.addTo(this.map);
      this.overlapLayer.bringToFront();

      // Ensure individual GeoRasterLayers are hidden (overlap layer handles rendering)
      this.redrawSites();
    },
    initMap() {
      this.map = L.map("map", {
        zoom: DEFAULT_ZOOM,
        zoomControl: false,
      });
      const position: [number, number] = [this.splatParams.transmitter.tx_lat, this.splatParams.transmitter.tx_lon];
      this.map.setView(position, DEFAULT_ZOOM);

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
      L.easyPrint({
        title: "Save",
        position: "bottomleft",
        sizeModes: ["A4Portrait", "A4Landscape"],
        filename: "sites",
        exportOnly: true,
      }).addTo(this.map as L.Map);

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
      void this.loadTowers();
      void this.loadTowerPaths();
    },
    async runSimulation() {
      try {
        const payload = buildSimulationPayload(this.splatParams);

        if (this._pollTimer) {
          clearTimeout(this._pollTimer);
          this._pollTimer = 0;
        }
        this.simulationState = "running";
        this.simulationError = "";

        // Send the request to the backend's /predict endpoint
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (this.adminToken) {
          headers["Authorization"] = `Bearer ${this.adminToken}`;
        }

        const predictResponse = await fetch("/predict", {
          method: "POST",
          headers,
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
        const pollInterval = POLL_INTERVAL_MS;
        const maxPolls = MAX_POLL_COUNT;
        let pollCount = 0;
        const pollStatus = async () => {
          pollCount++;
          if (pollCount > maxPolls) {
            this.simulationState = "failed";
            this.simulationError = "Simulation timed out after 5 minutes";
            return;
          }

          const statusResponse = await fetch(`/status/${taskId}`);
          if (!statusResponse.ok) {
            this.simulationState = "failed";
            this.simulationError = "Failed to fetch task status";
            return;
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
              const userColor = this.splatParams.transmitter.tx_color;
              this.localSites.push({
                params: cloneObject(this.splatParams),
                taskId,
                raster: geoRaster,
                color: userColor && userColor !== "" ? userColor : TOWER_COLORS[colorIndex],
                visible: true,
              });
              this.currentMarker?.removeFrom(this.map as L.Map);
              this.splatParams.transmitter.name = randanimalSync();
              this.updateOverlapLayer();
              // Reload tower paths after backend has time to compute
              this._pathReloadTimer = window.setTimeout(() => this.loadTowerPaths(), PATH_RELOAD_DELAY_MS);
              if (this.showDeadzones) {
                void this.fetchDeadzones();
              }
            }
          } else if (statusData.status === "failed") {
            this.simulationState = "failed";
            const errorMsg = statusData.error ?? "Unknown error";
            console.error("Simulation failed:", errorMsg);
            this.simulationError = errorMsg;
          } else {
            this._pollTimer = window.setTimeout(pollStatus, pollInterval);
          }
        };

        void pollStatus(); // Start polling
      } catch (error) {
        this.simulationState = "failed";
        this.simulationError = error instanceof Error ? error.message : "Unknown error";
        console.error("Simulation error:", error);
      }
    },
  },
});

export { useStore };
