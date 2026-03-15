<template>
  <div>
    <div class="row g-2">
      <div class="col-12 col-sm-6">
        <label for="client-hardware" class="form-label small mb-1">Your Hardware</label>
        <select
          id="client-hardware"
          v-model="store.clientHardware"
          class="form-select form-select-sm"
          @change="onSelectionChange"
        >
          <option v-for="hw in enabledHardware" :key="hw.key" :value="hw.key">
            {{ hw.label }}
          </option>
        </select>
      </div>
      <div class="col-12 col-sm-6">
        <label for="client-antenna" class="form-label small mb-1">Your Antenna</label>
        <select
          id="client-antenna"
          v-model="store.clientAntenna"
          class="form-select form-select-sm"
          @change="onSelectionChange"
        >
          <option v-for="ant in enabledAntennas" :key="ant.key" :value="ant.key">
            {{ ant.label }}
          </option>
        </select>
      </div>
    </div>
    <p v-if="pendingMessage" class="text-warning small mt-1 mb-0">{{ pendingMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useStore } from "../store.ts";

const store = useStore();
const pendingMessage = ref("");

const hardwareLabels: Record<string, string> = {
  v3: "Heltec V3",
  v4: "Heltec V4",
};

const antennaLabels: Record<string, string> = {
  ribbed_spring_helical: "Ribbed Spring Helical",
  duck_stubby: "Duck Stubby",
  bingfu_whip: "Bingfu Whip",
  slinkdsco_omni: "Slinkdsco Omni",
};

const enabledHardware = computed(() => {
  if (!store.matrixConfig?.hardware) return [];
  return Object.entries(store.matrixConfig.hardware)
    .filter(([, enabled]) => enabled)
    .map(([key]) => ({ key, label: hardwareLabels[key] || key }));
});

const enabledAntennas = computed(() => {
  if (!store.matrixConfig?.antennas) return [];
  return Object.entries(store.matrixConfig.antennas)
    .filter(([, enabled]) => enabled)
    .map(([key]) => ({ key, label: antennaLabels[key] || key }));
});

onMounted(async () => {
  if (!store.matrixConfig) {
    await store.loadMatrixConfig();
  }
  // Ensure selected values are still valid after config loads
  if (enabledHardware.value.length > 0 && !enabledHardware.value.find((h) => h.key === store.clientHardware)) {
    store.clientHardware = enabledHardware.value[0].key;
  }
  if (enabledAntennas.value.length > 0 && !enabledAntennas.value.find((a) => a.key === store.clientAntenna)) {
    store.clientAntenna = enabledAntennas.value[0].key;
  }
});

async function onSelectionChange() {
  pendingMessage.value = "";

  // For each visible tower, try to load the matching simulation
  for (const site of store.localSites) {
    if (!site.taskId) continue;
    try {
      const response = await fetch(`/towers/${site.taskId}/simulations?enabled_only=true`);
      if (!response.ok) continue;
      const simulations = await response.json();

      // Find the simulation matching current hardware + antenna + bare_earth terrain
      const match = simulations.find(
        (sim: any) =>
          sim.hardware === store.clientHardware && sim.antenna === store.clientAntenna && sim.terrain === "bare_earth",
      );

      if (match) {
        if (match.status === "completed") {
          await store.swapSimulationLayer(site.taskId, match.sim_id);
        } else {
          pendingMessage.value = "Simulation pending...";
        }
      } else {
        pendingMessage.value = "Simulation pending...";
      }
    } catch (err) {
      console.warn("Error fetching simulations for tower:", site.taskId, err);
    }
  }
}
</script>
