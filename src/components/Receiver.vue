<template>
  <form novalidate>
    <div class="row g-2">
      <div class="col-12 col-sm-6">
        <label for="rx_sensitivity" class="form-label">Sensitivity (dBm)</label>
        <input
          id="rx_sensitivity"
          v-model.number="receiver.rx_sensitivity"
          type="number"
          class="form-control form-control-sm"
          required
          step="1"
          min="-150"
          max="-30"
        />
        <div class="invalid-feedback">Please enter a valid sensitivity.</div>
      </div>
      <div class="col-12 col-sm-6">
        <label for="rx_height" class="form-label">Height AGL (m)</label>
        <input
          id="rx_height"
          v-model.number="receiver.rx_height"
          type="number"
          class="form-control form-control-sm"
          required
          min="0"
          step="0.1"
        />
        <div class="invalid-feedback">Height must be a positive number.</div>
      </div>
    </div>
    <div class="row g-2 mt-2">
      <div class="col-12 col-sm-6">
        <label for="rx_gain" class="form-label">Antenna Gain (dB)</label>
        <input
          id="rx_gain"
          v-model.number="receiver.rx_gain"
          type="number"
          class="form-control form-control-sm"
          required
          min="0"
          max="30"
          step="0.1"
        />
        <div class="invalid-feedback">Gain must be a positive number.</div>
      </div>
      <div class="col-12 col-sm-6">
        <label for="rx_loss" class="form-label">Cable Loss (dB)</label>
        <input
          id="rx_loss"
          v-model.number="receiver.rx_loss"
          type="number"
          class="form-control form-control-sm"
          required
          min="0"
          max="100"
          step="0.1"
        />
        <div class="invalid-feedback">Loss must be a positive number.</div>
      </div>
    </div>

    <!-- Window Mode -->
    <div class="row g-2 mt-3">
      <div class="col-12">
        <div class="form-check form-switch">
          <input id="window_mode" v-model="receiver.window_mode" class="form-check-input" type="checkbox" />
          <label class="form-check-label" for="window_mode">Window Mode</label>
        </div>
      </div>
    </div>
    <template v-if="receiver.window_mode">
      <div class="row g-2 mt-1">
        <div class="col-12 col-sm-6">
          <label for="window_azimuth" class="form-label">Window Azimuth (&deg;)</label>
          <input
            id="window_azimuth"
            v-model.number="receiver.window_azimuth"
            type="number"
            class="form-control form-control-sm"
            min="0"
            max="359"
            step="1"
          />
        </div>
        <div class="col-12 col-sm-6">
          <label for="window_fov" class="form-label">Field of View (&deg;)</label>
          <input
            id="window_fov"
            v-model.number="receiver.window_fov"
            type="number"
            class="form-control form-control-sm"
            min="1"
            max="360"
            step="1"
          />
        </div>
      </div>
      <div class="row g-2 mt-1">
        <div class="col-12 col-sm-6">
          <label for="glass_type" class="form-label">Glass Type</label>
          <select id="glass_type" v-model="receiver.glass_type" class="form-select form-select-sm">
            <option value="single">Single Pane (2 dB)</option>
            <option value="double">Double Pane (4 dB)</option>
            <option value="triple">Triple Pane (6 dB)</option>
          </select>
        </div>
        <div class="col-12 col-sm-6">
          <label for="structural_material" class="form-label">Wall Material</label>
          <select id="structural_material" v-model="receiver.structural_material" class="form-select form-select-sm">
            <option value="drywall">Drywall (3 dB)</option>
            <option value="brick">Brick (10 dB)</option>
            <option value="metal">Metal (20 dB)</option>
          </select>
        </div>
      </div>
    </template>
  </form>
</template>

<script setup lang="ts">
import { watch } from "vue";
import { useStore } from "../store.ts";
const store = useStore();
const { receiver } = store.splatParams;
watch(
  () => [receiver.window_mode, receiver.window_azimuth, receiver.window_fov],
  () => store.updateFovCone(),
);
</script>
