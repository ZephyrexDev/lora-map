<template>
  <form ref="formRef" novalidate @submit.prevent @input="() => validateForm()">
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
              @change="() => toggleAutoColor()"
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
          v-model.number="transmitter.tx_lat"
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
          v-model.number="transmitter.tx_lon"
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
          @change="() => onHardwareChange()"
        >
          <option value="">Custom</option>
          <option v-for="hw in HARDWARE_PRESETS" :key="hw.name" :value="hw.name">
            {{ hw.name }}{{ hw.is_custom ? "" : ` (${hw.max_power_dbm} dBm)` }}
          </option>
        </select>
      </div>
      <div class="col-12 col-sm-6">
        <label for="regionPreset" class="form-label">Country / Region</label>
        <select
          id="regionPreset"
          v-model="selectedRegion"
          class="form-select form-select-sm"
          @change="() => onRegionChange()"
        >
          <option value="">Custom</option>
          <option v-for="freq in FREQUENCY_PRESETS" :key="freq.code" :value="freq.code">
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
            @change="() => onAntennaChange()"
          >
            <option value="">Custom</option>
            <option v-for="ant in ANTENNA_PRESETS" :key="ant.name" :value="ant.name">
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
        <select
          id="heightPreset"
          v-model="selectedHeight"
          class="form-select form-select-sm"
          @change="() => onHeightChange()"
        >
          <option value="">Custom</option>
          <option v-for="h in HEIGHT_PRESETS" :key="h.label" :value="h.label">
            {{ h.label }} ({{ h.height_m }} m)
          </option>
        </select>
      </div>
    </div>

    <!-- Manual fields -->
    <div class="row g-2 mt-2">
      <div class="col-12 col-sm-6">
        <label for="tx_power" class="form-label">Power (W)</label>
        <input
          id="tx_power"
          v-model.number="transmitter.tx_power"
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
          v-model.number="transmitter.tx_freq"
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
          v-model.number="transmitter.tx_height"
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
          v-model.number="transmitter.tx_gain"
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
        @click="() => setWithMap()"
      >
        Set with Map
      </button>
      <button type="button" class="btn btn-secondary btn-sm" @click="() => centerMapOnTransmitter()">
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
const { transmitter } = store.splatParams;
const formRef = ref<HTMLFormElement | null>(null);

function validateForm() {
  formRef.value?.classList.add("was-validated");
}

// Preset selection state ("" means "Custom")
const selectedHardware = ref("");
const selectedRegion = ref("");
const selectedAntenna = ref("");
const selectedHeight = ref("");

const activeHardwarePreset = computed(() => HARDWARE_PRESETS.find((p) => p.name === selectedHardware.value));
const activeRegionPreset = computed(() => FREQUENCY_PRESETS.find((p) => p.code === selectedRegion.value));
const activeAntennaPreset = computed(() => ANTENNA_PRESETS.find((p) => p.name === selectedAntenna.value));
const activeHeightPreset = computed(() => HEIGHT_PRESETS.find((p) => p.label === selectedHeight.value));

const isHardwarePresetActive = computed(() => {
  const preset = activeHardwarePreset.value;
  return preset !== undefined && !preset.is_custom;
});
const isRegionPresetActive = computed(() => activeRegionPreset.value !== undefined);
const isAntennaPresetActive = computed(() => activeAntennaPreset.value !== undefined);
const isHeightPresetActive = computed(() => activeHeightPreset.value !== undefined);

const mismatchLossBadge = computed(() => {
  const preset = activeAntennaPreset.value;
  if (!preset) return null;
  return mismatchLoss(preset.swr).toFixed(2);
});

function onHardwareChange() {
  const preset = activeHardwarePreset.value;
  if (!preset || preset.is_custom) return;
  transmitter.tx_power = dbmToWatts(preset.max_power_dbm);
}

function onRegionChange() {
  const preset = activeRegionPreset.value;
  if (!preset) return;
  transmitter.tx_freq = preset.frequency_mhz;
}

function onAntennaChange() {
  const preset = activeAntennaPreset.value;
  if (!preset) return;
  transmitter.tx_gain = preset.gain_dbi;
  transmitter.tx_swr = preset.swr;
}

function onHeightChange() {
  const preset = activeHeightPreset.value;
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
  if (!store.map) return;
  if (!isNaN(transmitter.tx_lat) && !isNaN(transmitter.tx_lon)) {
    store.map.setView([transmitter.tx_lat, transmitter.tx_lon], store.map.getZoom());
  }
};
let popover: bootstrap.Popover | null = null;

const mapClickHandler = (e: L.LeafletMouseEvent) => {
  const { lat } = e.latlng;
  let { lng } = e.latlng;
  lng = ((((lng + 180) % 360) + 360) % 360) - 180;

  store.setTxCoords(parseFloat(lat.toFixed(6)), parseFloat(lng.toFixed(6)));

  if (store.currentMarker && store.map) {
    store.map.removeLayer(store.currentMarker as L.Marker);
  }
  if (store.map) {
    store.currentMarker = L.marker([lat, lng], { icon: redPinMarker }).addTo(store.map);
  }
  popover?.hide();
};

const setWithMap = () => {
  if (!store.map) return;
  popover?.show();
  store.map.once("click", mapClickHandler);
};
onMounted(() => {
  const popoverEl = document.getElementById("setWithMap");
  if (popoverEl) {
    popover = new bootstrap.Popover(popoverEl, {
      trigger: "manual",
    });
  }
  // Map is initialized in App.vue onMounted, not here
});

onUnmounted(() => {
  store.map?.off("click", mapClickHandler);
  popover?.dispose();
  popover = null;
});
</script>
