<template>
  <form novalidate>
    <div class="mb-2">
      <label class="form-label fw-bold mb-1">Hardware</label>
      <div>
        <div class="form-check form-check-inline" v-for="hw in hardwareOptions" :key="hw.key">
          <input
            class="form-check-input"
            type="checkbox"
            :id="'hw-' + hw.key"
            :checked="config.hardware[hw.key]"
            @change="toggle('hardware', hw.key)"
          />
          <label class="form-check-label" :for="'hw-' + hw.key">{{ hw.label }}</label>
        </div>
      </div>
    </div>
    <div class="mb-2">
      <label class="form-label fw-bold mb-1">Antennas</label>
      <div>
        <div class="form-check form-check-inline" v-for="ant in antennaOptions" :key="ant.key">
          <input
            class="form-check-input"
            type="checkbox"
            :id="'ant-' + ant.key"
            :checked="config.antennas[ant.key]"
            @change="toggle('antennas', ant.key)"
          />
          <label class="form-check-label" :for="'ant-' + ant.key">{{ ant.label }}</label>
        </div>
      </div>
    </div>
    <div class="mb-1">
      <label class="form-label fw-bold mb-1">Terrain</label>
      <div>
        <div class="form-check form-check-inline" v-for="ter in terrainOptions" :key="ter.key">
          <input
            class="form-check-input"
            type="checkbox"
            :id="'ter-' + ter.key"
            :checked="config.terrain[ter.key]"
            @change="toggle('terrain', ter.key)"
          />
          <label class="form-check-label" :for="'ter-' + ter.key">{{ ter.label }}</label>
        </div>
      </div>
    </div>
    <transition name="fade">
      <span v-if="showSaved" class="badge bg-success ms-1">Saved</span>
    </transition>
  </form>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useStore } from "../store.ts";
import { arrayToRecord } from "../utils.ts";
import { HARDWARE_LABELS, ANTENNA_LABELS, TERRAIN_LABELS, labelsToOptions } from "../presets/labels.ts";
import type { MatrixConfig } from "../types.ts";

const store = useStore();
const showSaved = ref(false);

const hardwareOptions = labelsToOptions(HARDWARE_LABELS);
const antennaOptions = labelsToOptions(ANTENNA_LABELS);
// Exclude weighted_aggregate — it's derived, not a real terrain simulation
const terrainOptions = labelsToOptions(
  Object.fromEntries(Object.entries(TERRAIN_LABELS).filter(([k]) => k !== "weighted_aggregate")),
);

const config = reactive<MatrixConfig>({
  hardware: { v3: true, v4: true },
  antennas: {
    ribbed_spring_helical: true,
    duck_stubby: true,
    bingfu_whip: true,
    slinkdsco_omni: true,
  },
  terrain: { bare_earth: true },
});

onMounted(async () => {
  try {
    const response = await fetch("/matrix/config");
    if (response.ok) {
      const data = await response.json();
      const hwKeys = hardwareOptions.map((o) => o.key);
      const antKeys = antennaOptions.map((o) => o.key);
      const terKeys = terrainOptions.map((o) => o.key);
      if (data.hardware) Object.assign(config.hardware, arrayToRecord(data.hardware, hwKeys));
      if (data.antennas) Object.assign(config.antennas, arrayToRecord(data.antennas, antKeys));
      if (data.terrain) Object.assign(config.terrain, arrayToRecord(data.terrain, terKeys));
      store.matrixConfig = { ...config };
    }
  } catch (err) {
    console.warn("Error loading matrix config:", err);
  }
});

let saveTimeout: ReturnType<typeof setTimeout> | null = null;

async function toggle(section: keyof MatrixConfig, key: string) {
  (config[section] as Record<string, boolean>)[key] = !config[section][key];
  try {
    const response = await fetch("/matrix/config", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${store.adminToken}`,
      },
      body: JSON.stringify({
        hardware: Object.entries(config.hardware)
          .filter(([, v]) => v)
          .map(([k]) => k),
        antennas: Object.entries(config.antennas)
          .filter(([, v]) => v)
          .map(([k]) => k),
        terrain: Object.entries(config.terrain)
          .filter(([, v]) => v)
          .map(([k]) => k),
      }),
    });
    if (response.ok) {
      store.matrixConfig = { ...config };
      showSaved.value = true;
      if (saveTimeout) clearTimeout(saveTimeout);
      saveTimeout = setTimeout(() => {
        showSaved.value = false;
      }, 1500);
    }
  } catch (err) {
    console.warn("Error saving matrix config:", err);
  }
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
