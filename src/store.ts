import { defineStore } from 'pinia';
// import { useLocalStorage } from '@vueuse/core';
import { randanimalSync } from 'randanimal';
import L from 'leaflet';
import GeoRasterLayer from 'georaster-layer-for-leaflet';
import parseGeoraster from 'georaster';
import 'leaflet-easyprint';
import { type Site, type SplatParams } from './types.ts';
import { cloneObject } from './utils.ts';
import { redPinMarker } from './layers.ts';

const useStore = defineStore('store', {
  state() {
    return {
      map: undefined as undefined | L.Map,
      currentMarker: undefined as undefined | L.Marker,
      localSites: [] as Site[], //useLocalStorage('localSites', ),
      simulationState: 'idle',
      isAdmin: false,
      adminToken: localStorage.getItem('adminToken') || '',
      splatParams: <SplatParams>{
        transmitter: {
          name: randanimalSync(),
          tx_lat: 53.5461,
          tx_lon: -113.4937,
          tx_power: 0.1,
          tx_freq: 907.0,
          tx_height: 2.0,
          tx_gain: 2.0,
          tx_swr: 1.0,
          tx_color: ''
        },
        receiver: {
          rx_sensitivity: -130.0,
          rx_height: 1.0,
          rx_gain: 2.0,
          rx_loss: 2.0
        },
        environment: {
          radio_climate: 'continental_temperate',
          polarization: 'vertical',
          clutter_height: 1.0,
          ground_dielectric: 15.0,
          ground_conductivity: 0.005,
          atmosphere_bending: 301.0
        },
        simulation: {
          situation_fraction: 95.0,
          time_fraction: 95.0,
          simulation_extent: 30.0,
          high_resolution: false
        },
        display: {
          color_scale: 'plasma',
          min_dbm: -130.0,
          max_dbm: -80.0,
          overlay_transparency: 50
        },
      }
    }
  },
  actions: {
    async login(password: string): Promise<boolean> {
      try {
        const response = await fetch('/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password }),
        });
        if (!response.ok) return false;
        const data = await response.json();
        this.adminToken = data.token;
        this.isAdmin = true;
        localStorage.setItem('adminToken', this.adminToken);
        return true;
      } catch {
        return false;
      }
    },
    logout() {
      this.adminToken = '';
      this.isAdmin = false;
      localStorage.removeItem('adminToken');
    },
    async checkAuth(): Promise<void> {
      if (!this.adminToken) return;
      try {
        const response = await fetch('/auth/check', {
          headers: { Authorization: `Bearer ${this.adminToken}` },
        });
        if (response.ok) {
          this.isAdmin = true;
        } else {
          this.adminToken = '';
          this.isAdmin = false;
          localStorage.removeItem('adminToken');
        }
      } catch {
        this.adminToken = '';
        this.isAdmin = false;
        localStorage.removeItem('adminToken');
      }
    },
    setTxCoords(lat: number, lon: number) {
      this.splatParams.transmitter.tx_lat = lat
      this.splatParams.transmitter.tx_lon = lon
    },
    removeSite(index: number) {
      if (!this.map) {
        return
      }
      const site = this.localSites[index];
      if (site && site.layer) {
        this.map.removeLayer(site.layer);
      }
      this.localSites.splice(index, 1);
    },
    redrawSites() {
      if (!this.map) {
        return;
      }

      this.localSites.forEach((site: Site) => {
        if (site.raster && !site.layer) {
          const rasterLayer = new GeoRasterLayer({
            georaster: site.raster,
            noDataValue: 255,
            resolution: 256,
            pixelValuesToColorFn: (values: number[]) => {
              const val = values[0];
              if (val === 255 || val === 0) return null;
              const alpha = Math.round(230 - (val / 254) * 179);
              const hex = site.color || '#4a90d9';
              const r = parseInt(hex.slice(1, 3), 16);
              const g = parseInt(hex.slice(3, 5), 16);
              const b = parseInt(hex.slice(5, 7), 16);
              return `rgba(${r},${g},${b},${alpha / 255})`;
            },
          });
          if (!site.visible) {
            rasterLayer.setOpacity(0);
          }
          rasterLayer.addTo(this.map as L.Map);
          site.layer = rasterLayer;
        }
        if (site.layer) {
          site.layer.bringToFront();
        }
      });
    },
    toggleSiteVisibility(index: number) {
      const site = this.localSites[index];
      if (!site) {
        return;
      }
      site.visible = !site.visible;
      if (site.visible) {
        site.layer?.setOpacity(1);
      } else {
        site.layer?.setOpacity(0);
      }
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

      const cartoLight = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap contributors © CARTO',
      });

      const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
      })

      const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles © Esri — Source: Esri, USGS, NOAA',
      });

      const topoLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data: © OpenStreetMap contributors, SRTM | OpenTopoMap',
      });

      streetLayer.addTo(this.map as L.Map);

      // Base Layers
      const baseLayers = {
        "OSM": streetLayer,
        "Carto Light": cartoLight,
        "Satellite": satelliteLayer,
        "Topo Map": topoLayer
      };

      // EasyPrint control
      (L as any).easyPrint({
        title: "Save",
        position: "bottomleft",
        sizeModes: ["A4Portrait", "A4Landscape"],
        filename: "sites",
        exportOnly: true
      }).addTo(this.map as L.Map);

      L.control.layers(baseLayers, {}, {
        position: "bottomleft",
      }).addTo(this.map as L.Map);

      this.map.on("baselayerchange", () => {
        this.localSites.forEach((site: Site) => {
          site.layer?.bringToFront();
        });
      });
      this.currentMarker = L.marker(position, { icon: redPinMarker }).addTo(this.map as L.Map).bindPopup("Transmitter site"); // Variable to hold the current marker
      this.redrawSites();
      this.loadTowers();
    },
    async loadTowers() {
      try {
        const response = await fetch('/towers');
        if (!response.ok) {
          console.warn('Failed to load towers:', response.statusText);
          return;
        }
        const towers = await response.json();
        for (const tower of towers) {
          // Skip towers already present in localSites (matched by taskId)
          if (this.localSites.some((s: Site) => s.taskId === tower.task_id)) {
            continue;
          }
          const site: Site = {
            params: tower.params ?? {
              transmitter: { name: tower.name ?? 'Unknown', tx_lat: tower.lat ?? 0, tx_lon: tower.lon ?? 0, tx_power: 0, tx_freq: 0, tx_height: 0, tx_gain: 0, tx_swr: 1 },
              receiver: { rx_sensitivity: -130, rx_height: 1, rx_gain: 2, rx_loss: 2 },
              environment: { radio_climate: 'continental_temperate', polarization: 'vertical', clutter_height: 1, ground_dielectric: 15, ground_conductivity: 0.005, atmosphere_bending: 301 },
              simulation: { situation_fraction: 95, time_fraction: 95, simulation_extent: 30, high_resolution: false },
              display: { color_scale: 'plasma', min_dbm: -130, max_dbm: -80, overlay_transparency: 50 },
            },
            taskId: tower.task_id ?? '',
            raster: null,
            layer: undefined,
            visible: true,
            color: tower.color || tower.params?.transmitter?.tx_color || '#4a90d9',
          };
          this.localSites.push(site);
        }
      } catch (err) {
        console.warn('Error loading towers:', err);
      }
    },
    async runSimulation() {
      console.log('Simulation running...')
      try {
        // Collect input values
        const payload = {
          // Transmitter parameters
          lat: this.splatParams.transmitter.tx_lat,
          lon: this.splatParams.transmitter.tx_lon,
          tx_height: this.splatParams.transmitter.tx_height,
          tx_power: 10 * Math.log10(this.splatParams.transmitter.tx_power) + 30,
          tx_gain: this.splatParams.transmitter.tx_gain,
          swr: this.splatParams.transmitter.tx_swr,
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

        console.log("Payload:", payload);
        this.simulationState = 'running';

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
          this.simulationState = 'failed';
          const errorDetails = await predictResponse.text();
          throw new Error(`Failed to start prediction: ${errorDetails}`);
        }

        const predictData = await predictResponse.json();
        const taskId = predictData.task_id;

        console.log(`Prediction started with task ID: ${taskId}`);

        const maxRetries = 300; // 5 minutes at initial 1s intervals
        const maxInterval = 10000; // 10 seconds cap
        let retryCount = 0;
        let currentInterval = 1000; // Start at 1 second

        const pollStatus = async () => {
          if (retryCount >= maxRetries) {
            console.error(`Polling timed out after ${retryCount} retries.`);
            this.simulationState = 'failed';
            return;
          }
          retryCount++;

          const statusResponse = await fetch(
            `/status/${taskId}`,
          );
          if (!statusResponse.ok) {
            throw new Error("Failed to fetch task status.");
          }

          const statusData = await statusResponse.json();
          console.log("Task status:", statusData);

          if (statusData.status === "completed") {
            this.simulationState = 'completed';
            console.log("Simulation completed! Adding result to the map...");

            // Fetch the GeoTIFF data
            const resultResponse = await fetch(
              `/result/${taskId}`,
            );
            if (!resultResponse.ok) {
              throw new Error("Failed to fetch simulation result.");
            }
            else
            {
              const arrayBuffer = await resultResponse.arrayBuffer();
              const geoRaster = await parseGeoraster(arrayBuffer);

              const siteColor = this.splatParams.transmitter.tx_color || '#4a90d9';
              const rasterLayer = new GeoRasterLayer({
                georaster: geoRaster,
                noDataValue: 255,
                resolution: 256,
                pixelValuesToColorFn: (values: number[]) => {
                  const val = values[0];
                  if (val === 255 || val === 0) return null;
                  const alpha = Math.round(230 - (val / 254) * 179);
                  const hex = siteColor;
                  const r = parseInt(hex.slice(1, 3), 16);
                  const g = parseInt(hex.slice(3, 5), 16);
                  const b = parseInt(hex.slice(5, 7), 16);
                  return `rgba(${r},${g},${b},${alpha / 255})`;
                },
              });
              rasterLayer.addTo(this.map as L.Map);
              rasterLayer.bringToFront();

              this.localSites.push({
                params: cloneObject(this.splatParams),
                taskId,
                raster: geoRaster,
                layer: rasterLayer,
                visible: true,
                color: siteColor,
              });
              this.currentMarker!.removeFrom(this.map as L.Map);
              this.splatParams.transmitter.name = await randanimalSync();
            }
          }
          else if (statusData.status === "failed") {
            this.simulationState = 'failed';
          } else {
            setTimeout(pollStatus, currentInterval);
            currentInterval = Math.min(currentInterval * 2, maxInterval); // Exponential backoff, capped at 10s
          }
        };

        pollStatus(); // Start polling
      } catch (error) {
        console.error("Error:", error);
      }
    }
  }
});

export { useStore }
