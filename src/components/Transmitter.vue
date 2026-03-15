<template>
  <form novalidate>
    <div class="row g-2">
      <div class="col-12 col-sm-8">
        <label for="name" class="form-label">Site name</label>
        <input
          id="name"
          v-model="transmitter.name"
          class="form-control form-control-sm"
          required
          data-bs-toggle="tooltip"
          title="Site Name"
        />
      </div>
      <div class="col-12 col-sm-4">
        <label for="tx_color" class="form-label">Tower Color</label>
        <div class="d-flex align-items-center gap-1">
          <input
            id="tx_color"
            v-model="transmitter.tx_color"
            type="color"
            class="form-control form-control-sm form-control-color"
            :disabled="transmitter.tx_color === ''"
            title="Tower overlay color"
            style="min-width: 38px"
          />
          <div class="form-check form-check-inline mb-0">
            <input
              id="tx_color_auto"
              class="form-check-input"
              type="checkbox"
              :checked="transmitter.tx_color === ''"
              @change="toggleAutoColor"
            />
            <label class="form-check-label small" for="tx_color_auto">Auto</label>
          </div>
        </div>
      </div>
    </div>
    <div class="row g-2">
      <div class="col-12 col-sm-6">
        <label for="tx_lat" class="form-label">Latitude (degrees)</label>
        <input
          id="tx_lat"
          v-model="transmitter.tx_lat"
          type="number"
          class="form-control form-control-sm"
          required
          min="-90"
          max="90"
          step="0.000001"
          data-bs-toggle="tooltip"
          title="Transmitter latitude in degrees (-90 to 90)."
        />
        <div class="invalid-feedback">Please enter a valid latitude (-90 to 90).</div>
      </div>
      <div class="col-12 col-sm-6">
        <label for="tx_lon" class="form-label">Longitude (degrees)</label>
        <input
          id="tx_lon"
          v-model="transmitter.tx_lon"
          type="number"
          class="form-control form-control-sm"
          required
          min="-180"
          max="180"
          step="0.000001"
          data-bs-toggle="tooltip"
          title="Transmitter longitude in degrees (-180 to 180)."
        />
        <div class="invalid-feedback">Please enter a valid longitude (-180 to 180).</div>
      </div>
    </div>

    <!-- Preset selectors -->
    <div class="row g-2 mt-2">
      <div class="col-12 col-sm-6">
        <label for="hardwarePreset" class="form-label">Hardware</label>
        <select
          id="hardwarePreset"
          v-model="selectedHardware"
          class="form-select form-select-sm"
          @change="onHardwareChange"
        >
          <option :value="-1">Custom</option>
          <option v-for="(hw, idx) in HARDWARE_PRESETS" :key="idx" :value="idx">
            {{ hw.name }}{{ hw.is_custom ? "" : ` (${hw.max_power_dbm} dBm)` }}
          </option>
        </select>
      </div>
      <div class="col-12 col-sm-6">
        <label for="regionPreset" class="form-label">Country / Region</label>
        <select id="regionPreset" v-model="selectedRegion" class="form-select form-select-sm" @change="onRegionChange">
          <option :value="-1">Custom</option>
          <option v-for="(freq, idx) in FREQUENCY_PRESETS" :key="idx" :value="idx">
            {{ freq.region }} ({{ freq.code }}) — {{ freq.frequency_mhz }} MHz
          </option>
        </select>
      </div>
    </div>
    <div class="row g-2 mt-2">
      <div class="col-12 col-sm-6">
        <label for="antennaPreset" class="form-label">Antenna</label>
        <div class="d-flex align-items-center gap-1">
          <select
            id="antennaPreset"
            v-model="selectedAntenna"
            class="form-select form-select-sm flex-grow-1"
            @change="onAntennaChange"
          >
            <option :value="-1">Custom</option>
            <option v-for="(ant, idx) in ANTENNA_PRESETS" :key="idx" :value="idx">
              {{ ant.name }} ({{ ant.gain_dbi }} dBi)
            </option>
          </select>
          <span
            v-if="mismatchLossBadge !== null"
            class="badge bg-warning text-dark flex-shrink-0"
            style="white-space: nowrap; font-size: max(0.75rem, 12px)"
          >
            (-{{ mismatchLossBadge }} dB)
          </span>
        </div>
      </div>
      <div class="col-12 col-sm-6">
        <label for="heightPreset" class="form-label">Height Preset</label>
        <select id="heightPreset" v-model="selectedHeight" class="form-select form-select-sm" @change="onHeightChange">
          <option :value="-1">Custom</option>
          <option v-for="(h, idx) in HEIGHT_PRESETS" :key="idx" :value="idx">{{ h.label }} ({{ h.height_m }} m)</option>
        </select>
      </div>
    </div>

    <!-- Manual fields -->
    <div class="row g-2 mt-2">
      <div class="col-12 col-sm-6">
        <label for="tx_power" class="form-label">Power (W)</label>
        <input
          id="tx_power"
          v-model="transmitter.tx_power"
          type="number"
          class="form-control form-control-sm"
          required
          min="0"
          step="0.1"
          data-bs-toggle="tooltip"
          title="Transmitter power in watts (>0)."
          :disabled="isHardwarePresetActive"
        />
        <div class="invalid-feedback">Power must be a positive number.</div>
      </div>
      <div class="col-12 col-sm-6">
        <label for="frequency" class="form-label">Frequency (MHz)</label>
        <input
          id="tx_freq"
          v-model="transmitter.tx_freq"
          type="number"
          class="form-control form-control-sm"
          required
          min="20"
          max="20000"
          step="0.1"
          data-bs-toggle="tooltip"
          title="Transmitter frequency in MHz (20 to 20,000)."
          :disabled="isRegionPresetActive"
        />
        <div class="invalid-feedback">Frequency must be a positive number.</div>
      </div>
    </div>
    <div class="row g-2 mt-2">
      <div class="col-12 col-sm-6">
        <label for="tx_height" class="form-label">Height AGL (m)</label>
        <input
          id="tx_height"
          v-model="transmitter.tx_height"
          type="number"
          class="form-control form-control-sm"
          required
          min="1.0"
          step="0.1"
          data-bs-toggle="tooltip"
          title="Transmitter height above ground in meters (>= 1.0)."
          :disabled="isHeightPresetActive"
        />
        <div class="invalid-feedback">Height must be a positive number.</div>
      </div>
      <div class="col-12 col-sm-6">
        <label for="tx_gain" class="form-label">Antenna Gain (dB)</label>
        <input
          id="tx_gain"
          v-model="transmitter.tx_gain"
          type="number"
          class="form-control form-control-sm"
          required
          min="0"
          step="0.1"
          :disabled="isAntennaPresetActive"
        />
        <div class="invalid-feedback">Gain must be a positive number.</div>
      </div>
    </div>
    <div class="mt-3 d-flex flex-column flex-sm-row gap-2">
      <button
        id="setWithMap"
        type="button"
        class="btn btn-primary btn-sm"
        data-bs-toggle="popover"
        data-bs-trigger="manual"
        data-bs-placement="auto"
        title="Set Coordinates"
        data-bs-content=""
        content="Click on the map to set the transmitter location."
        @click="setWithMap"
      >
        Set with Map
      </button>
      <button type="button" class="btn btn-secondary btn-sm" @click="centerMapOnTransmitter">
        Center map on transmitter
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import L from "leaflet";
import * as bootstrap from "bootstrap";
import { useStore } from "../store.ts";
import { onMounted, onUnmounted, ref, computed } from "vue";
import { redPinMarker } from "../layers.ts";
import { dbmToWatts } from "../utils.ts";
import { HARDWARE_PRESETS } from "../presets/hardware.ts";
import { FREQUENCY_PRESETS } from "../presets/frequencies.ts";
import { ANTENNA_PRESETS, mismatchLoss } from "../presets/antennas.ts";
import { HEIGHT_PRESETS } from "../presets/heights.ts";

const store = useStore();
const transmitter = store.splatParams.transmitter;

// Preset selection state (-1 means "Custom")
const selectedHardware = ref(-1);
const selectedRegion = ref(-1);
const selectedAntenna = ref(-1);
const selectedHeight = ref(-1);

const isHardwarePresetActive = computed(() => {
  if (selectedHardware.value < 0) return false;
  const preset = HARDWARE_PRESETS[selectedHardware.value];
  return preset && !preset.is_custom;
});
const isRegionPresetActive = computed(() => selectedRegion.value >= 0);
const isAntennaPresetActive = computed(() => selectedAntenna.value >= 0);
const isHeightPresetActive = computed(() => selectedHeight.value >= 0);

const mismatchLossBadge = computed(() => {
  if (selectedAntenna.value < 0) return null;
  const preset = ANTENNA_PRESETS[selectedAntenna.value];
  if (!preset) return null;
  return mismatchLoss(preset.swr).toFixed(2);
});

function onHardwareChange() {
  if (selectedHardware.value < 0) return;
  const preset = HARDWARE_PRESETS[selectedHardware.value];
  if (!preset || preset.is_custom) return;
  transmitter.tx_power = dbmToWatts(preset.max_power_dbm);
}

function onRegionChange() {
  if (selectedRegion.value < 0) return;
  const preset = FREQUENCY_PRESETS[selectedRegion.value];
  if (!preset) return;
  transmitter.tx_freq = preset.frequency_mhz;
}

function onAntennaChange() {
  if (selectedAntenna.value < 0) return;
  const preset = ANTENNA_PRESETS[selectedAntenna.value];
  if (!preset) return;
  transmitter.tx_gain = preset.gain_dbi;
  transmitter.tx_swr = preset.swr;
}

function onHeightChange() {
  if (selectedHeight.value < 0) return;
  const preset = HEIGHT_PRESETS[selectedHeight.value];
  if (!preset) return;
  transmitter.tx_height = preset.height_m;
}

function toggleAutoColor() {
  if (transmitter.tx_color === "") {
    transmitter.tx_color = "#4a90d9";
  } else {
    transmitter.tx_color = "";
  }
}

const centerMapOnTransmitter = () => {
  if (!isNaN(transmitter.tx_lat) && !isNaN(transmitter.tx_lon)) {
    store.map!.setView([transmitter.tx_lat, transmitter.tx_lon], store.map!.getZoom()); // Center map on the coordinates
  } else {
    alert("Please enter valid Latitude and Longitude values.");
  }
};
let popover = new bootstrap.Popover(document.createElement("input"), {
  trigger: "manual",
});

const setWithMap = () => {
  popover.show();
  store.map!.once("click", function (e: L.LeafletMouseEvent) {
    const { lat } = e.latlng;
    let { lng } = e.latlng; // Get clicked location coordinates
    lng = ((((lng + 180) % 360) + 360) % 360) - 180;

    store.setTxCoords(parseFloat(lat.toFixed(6)), parseFloat(lng.toFixed(6)));

    // Remove the existing marker if it exists
    if (store.currentMarker) {
      store.map!.removeLayer(store.currentMarker as L.Marker);
    }
    // Add a new marker at the clicked location
    store.currentMarker = L.marker([lat, lng], { icon: redPinMarker }).addTo(store.map as L.Map);
    popover.hide(); // Hide the popover
  });
};
function onPrefillTransmitter(e: Event) {
  const { lat, lon } = (e as CustomEvent).detail;
  transmitter.tx_lat = lat;
  transmitter.tx_lon = lon;

  // Place a marker at the pre-filled location
  if (store.currentMarker) {
    store.map!.removeLayer(store.currentMarker as L.Marker);
  }
  store.currentMarker = L.marker([lat, lon], { icon: redPinMarker }).addTo(store.map as L.Map);
  store.map!.setView([lat, lon], store.map!.getZoom());
}

onMounted(() => {
  popover = new bootstrap.Popover(document.getElementById("setWithMap") as Element, {
    trigger: "manual",
  });
  store.initMap();
  window.addEventListener("prefill-transmitter", onPrefillTransmitter);
});

onUnmounted(() => {
  window.removeEventListener("prefill-transmitter", onPrefillTransmitter);
});
</script>
