<template>
  <form novalidate>
    <div class="row g-2">
      <div class="col-12 col-sm-6">
        <label for="min_dbm" class="form-label">Minimum dBm</label>
        <input
          id="min_dbm"
          v-model.number="display.min_dbm"
          type="number"
          class="form-control form-control-sm"
          required
          step="0.1"
        />
        <div class="invalid-feedback">Minimum dBm must be provided (default: -130.0).</div>
      </div>
      <div class="col-12 col-sm-6">
        <label for="max_dbm" class="form-label">Maximum dBm</label>
        <input
          id="max_dbm"
          v-model.number="display.max_dbm"
          type="number"
          class="form-control form-control-sm"
          required
          step="0.1"
        />
        <div class="invalid-feedback">Maximum dBm must be provided (default: -30.0).</div>
      </div>
    </div>
    <div class="row g-2 mt-2">
      <div class="col-12 col-sm-6">
        <label for="color_scale" class="form-label">Color Scale</label>
        <select id="color_scale" v-model="display.color_scale" class="form-select form-select-sm" required>
          <option value="plasma" selected>Plasma</option>
          <option value="CMRmap">CMR map</option>
          <option value="cool">Cool</option>
          <option value="viridis">Viridis</option>
          <option value="turbo">Turbo</option>
          <option value="jet">Jet</option>
        </select>
        <div class="invalid-feedback">Please select a color scale.</div>
      </div>
      <div class="col-12 col-sm-6">
        <label for="overlay_transparency" class="form-label">Transparency (%)</label>
        <input
          id="overlay_transparency"
          v-model.number="display.overlay_transparency"
          type="number"
          class="form-control form-control-sm"
          required
          min="0"
          max="100"
          step="1"
        />
        <div class="invalid-feedback">Transparency must be between 0 and 100 (default: 50).</div>
      </div>
    </div>
    <div class="row g-2 mt-2">
      <div class="col-12">
        <label for="overlap_mode" class="form-label">Overlap Mode</label>
        <select
          id="overlap_mode"
          v-model="display.overlapMode"
          class="form-select form-select-sm"
          @change="() => onOverlapModeChange()"
        >
          <option value="hatch">Hatched</option>
          <option value="blend">Alpha Blend</option>
        </select>
      </div>
    </div>
    <div class="mt-3 text-center">
      <div>
        <img
          :src="`/colormaps/${display.color_scale}.png`"
          alt="Colorbar"
          style="border: 1px solid #ccc; display: block; margin: 0 auto; max-width: 100%; height: auto"
        />
      </div>
      <div class="d-flex justify-content-between mt-1">
        <span class="badge bg-primary">{{ display.min_dbm }} dBm</span>
        <span class="badge bg-primary">{{ display.max_dbm }} dBm</span>
      </div>
    </div>
    <hr class="my-3" />
    <div class="form-check form-switch">
      <input
        id="deadzoneToggle"
        class="form-check-input"
        type="checkbox"
        role="switch"
        :checked="store.showDeadzones"
        :disabled="store.localSites.length < 2"
        @change="() => store.toggleDeadzones()"
      />
      <label class="form-check-label" for="deadzoneToggle"> Show deadzone remediation </label>
    </div>
    <small v-if="store.localSites.length < 2" class="text-muted d-block mt-1">
      Requires at least 2 completed simulations
    </small>
    <div v-if="store.showDeadzones && store.deadzoneAnalysis" class="mt-2">
      <small class="text-muted d-block" style="line-height: 1.6">
        Coverage: {{ (store.deadzoneAnalysis.coverage_fraction * 100).toFixed(1) }}% ({{
          store.deadzoneAnalysis.total_coverage_km2.toFixed(1)
        }}
        km&sup2;)<br class="d-sm-none" />
        &middot; Deadzones: {{ store.deadzoneAnalysis.total_deadzone_km2.toFixed(1) }} km&sup2;<br class="d-sm-none" />
        &middot; {{ store.deadzoneAnalysis.suggestions.length }} suggested sites
      </small>
    </div>
  </form>
</template>

<script setup lang="ts">
import { watch } from "vue";
import { useStore } from "../store.ts";
const store = useStore();
const { display } = store.splatParams;

function onOverlapModeChange() {
  store.updateOverlapLayer();
}

watch(
  () => display.overlay_transparency,
  () => {
    store.updateOverlapLayer();
  },
);
</script>
