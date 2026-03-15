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
    <div class="row g-2 mt-1 mb-2">
      <div class="col-12">
        <label for="client-terrain" class="form-label small mb-1">Terrain Model</label>
        <select
          id="client-terrain"
          v-model="store.clientTerrain"
          class="form-select form-select-sm"
          @change="onSelectionChange"
        >
          <option v-for="ter in enabledTerrain" :key="ter.key" :value="ter.key">
            {{ ter.label }}
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
import { isTiffBuffer } from "../utils.ts";
import { HARDWARE_LABELS, ANTENNA_LABELS, TERRAIN_LABELS } from "../presets/labels.ts";
import { type SimulationRecord } from "../types.ts";

const store = useStore();
const pendingMessage = ref("");

const enabledHardware = computed(() => {
  if (!store.matrixConfig?.hardware) return [];
  return Object.entries(store.matrixConfig.hardware)
    .filter(([, enabled]) => enabled)
    .map(([key]) => ({ key, label: HARDWARE_LABELS[key] || key }));
});

const enabledAntennas = computed(() => {
  if (!store.matrixConfig?.antennas) return [];
  return Object.entries(store.matrixConfig.antennas)
    .filter(([, enabled]) => enabled)
    .map(([key]) => ({ key, label: ANTENNA_LABELS[key] || key }));
});

const enabledTerrain = computed(() => {
  if (!store.matrixConfig?.terrain) return [];
  return Object.entries(store.matrixConfig.terrain)
    .filter(([, enabled]) => enabled)
    .map(([key]) => ({ key, label: TERRAIN_LABELS[key] || key }));
});

onMounted(async () => {
  if (!store.matrixConfig) {
    await store.loadMatrixConfig();
  }
  if (enabledHardware.value.length > 0 && !enabledHardware.value.find((h) => h.key === store.clientHardware)) {
    store.clientHardware = enabledHardware.value[0].key;
  }
  if (enabledAntennas.value.length > 0 && !enabledAntennas.value.find((a) => a.key === store.clientAntenna)) {
    store.clientAntenna = enabledAntennas.value[0].key;
  }
  if (enabledTerrain.value.length > 0 && !enabledTerrain.value.find((t) => t.key === store.clientTerrain)) {
    store.clientTerrain = enabledTerrain.value[0].key;
  }
});

async function onSelectionChange() {
  pendingMessage.value = "";

  const tasks = store.localSites
    .filter((site) => site.taskId)
    .map(async (site) => {
      try {
        const response = await fetch(`/towers/${site.taskId}/simulations?enabled_only=true`);
        if (!response.ok) return;
        const data = await response.json();
        const simulations: SimulationRecord[] = data.simulations ?? [];

        if (store.clientTerrain === "weighted_aggregate") {
          try {
            const aggResponse = await fetch(
              `/towers/${site.taskId}/aggregate?client_hardware=${store.clientHardware}&client_antenna=${store.clientAntenna}`,
            );
            if (aggResponse.ok) {
              const arrayBuffer = await aggResponse.arrayBuffer();
              if (isTiffBuffer(arrayBuffer)) {
                await store.swapSimulationLayerFromBuffer(site.taskId, arrayBuffer);
                return;
              }
            }
            pendingMessage.value = "Aggregate requires all 3 base terrain simulations";
          } catch (err) {
            console.warn("Error fetching aggregate:", err);
            pendingMessage.value = "Aggregate unavailable";
          }
          return;
        }

        const match = simulations.find(
          (sim) =>
            sim.client_hardware === store.clientHardware &&
            sim.client_antenna === store.clientAntenna &&
            sim.terrain_model === store.clientTerrain,
        );

        if (match) {
          if (match.status === "completed") {
            await store.swapSimulationLayer(site.taskId, match.id);
          } else {
            pendingMessage.value = "Simulation pending...";
          }
        } else {
          pendingMessage.value = "No simulation for this combination";
        }
      } catch (err) {
        console.warn("Error fetching simulations for tower:", site.taskId, err);
        pendingMessage.value = "Failed to load simulation data";
      }
    });

  await Promise.all(tasks);
}
</script>
