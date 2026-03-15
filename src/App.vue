<template>
  <div>
    <nav class="navbar navbar-dark bg-dark fixed-top">
      <div class="container-fluid">
        <a class="navbar-brand text-truncate" href="#">
          <img src="/logo.svg" alt="LoRa Mesh Logo" width="30" height="30" class="d-inline" />
          LoRa Coverage Planner
        </a>
        <div class="d-flex align-items-center flex-shrink-0">
          <button
            class="btn btn-sm me-2"
            :class="store.isAdmin ? 'btn-outline-success' : 'btn-outline-secondary'"
            data-bs-toggle="modal"
            data-bs-target="#loginModal"
            :title="store.isAdmin ? 'Admin (click to manage)' : 'Visitor mode (click to login)'"
          >
            <svg
              v-if="store.isAdmin"
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              fill="currentColor"
              viewBox="0 0 16 16"
            >
              <path
                d="M11 1a2 2 0 0 0-2 2v4a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1V3a5 5 0 0 1 6.15-4.87l-.35.87A4 4 0 0 0 5 3v4h6a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2z"
              />
            </svg>
            <svg
              v-else
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              fill="currentColor"
              viewBox="0 0 16 16"
            >
              <path
                d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2m3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2"
              />
            </svg>
          </button>
          <button
            class="navbar-toggler"
            type="button"
            data-bs-toggle="offcanvas"
            data-bs-target="#offcanvasDarkNavbar"
            aria-controls="offcanvasDarkNavbar"
            aria-label="Toggle navigation"
          >
            <span class="navbar-toggler-icon"></span>
          </button>
        </div>
        <div
          id="offcanvasDarkNavbar"
          class="offcanvas offcanvas-end text-bg-dark show"
          tabindex="-1"
          aria-labelledby="offcanvasDarkNavbarLabel"
          data-bs-backdrop="false"
        >
          <div class="offcanvas-header">
            <h5 id="offcanvasDarkNavbarLabel" class="offcanvas-title">Site Parameters</h5>
            <button
              type="button"
              class="btn-close btn-close-white p-3"
              data-bs-dismiss="offcanvas"
              aria-label="Close"
            ></button>
          </div>
          <div class="offcanvas-body">
            <template v-if="store.isAdmin">
              <ul class="navbar-nav">
                <li class="nav-item dropdown">
                  <a
                    class="nav-link dropdown-toggle"
                    href="#"
                    role="button"
                    data-bs-toggle="dropdown"
                    data-bs-auto-close="outside"
                    aria-expanded="true"
                    >Site / Transmitter</a
                  >
                  <ul class="dropdown-menu dropdown-menu-dark p-3 show">
                    <li>
                      <Transmitter />
                    </li>
                  </ul>
                </li>
                <li class="nav-item dropdown">
                  <a
                    class="nav-link dropdown-toggle"
                    href="#"
                    role="button"
                    data-bs-toggle="dropdown"
                    data-bs-auto-close="outside"
                    aria-expanded="false"
                    >Receiver</a
                  >
                  <ul class="dropdown-menu dropdown-menu-dark p-3">
                    <li>
                      <Receiver />
                    </li>
                  </ul>
                </li>
                <li class="nav-item dropdown">
                  <a
                    class="nav-link dropdown-toggle"
                    href="#"
                    role="button"
                    data-bs-toggle="dropdown"
                    data-bs-auto-close="outside"
                    aria-expanded="false"
                    >Environment</a
                  >
                  <ul class="dropdown-menu dropdown-menu-dark p-3">
                    <li>
                      <Environment />
                    </li>
                  </ul>
                </li>
                <li class="nav-item dropdown">
                  <a
                    class="nav-link dropdown-toggle"
                    href="#"
                    role="button"
                    data-bs-toggle="dropdown"
                    data-bs-auto-close="outside"
                    aria-expanded="false"
                    >Simulation Options</a
                  >
                  <ul class="dropdown-menu dropdown-menu-dark p-3">
                    <li>
                      <Simulation />
                    </li>
                  </ul>
                </li>
                <li class="nav-item dropdown">
                  <a
                    class="nav-link dropdown-toggle"
                    href="#"
                    role="button"
                    data-bs-toggle="dropdown"
                    data-bs-auto-close="outside"
                    aria-expanded="true"
                  >
                    Display
                  </a>
                  <ul class="dropdown-menu dropdown-menu-dark p-3 show">
                    <li>
                      <Display />
                    </li>
                  </ul>
                </li>
                <li class="nav-item dropdown">
                  <a
                    class="nav-link dropdown-toggle"
                    href="#"
                    role="button"
                    data-bs-toggle="dropdown"
                    data-bs-auto-close="outside"
                    aria-expanded="false"
                  >
                    Matrix Config
                  </a>
                  <ul class="dropdown-menu dropdown-menu-dark p-3">
                    <li>
                      <MatrixConfig />
                    </li>
                  </ul>
                </li>
              </ul>
              <div class="mt-3 sticky-bottom bg-dark py-2" style="z-index: 1">
                <div class="d-flex gap-2">
                  <button
                    id="runSimulation"
                    :disabled="store.simulationState === 'running'"
                    type="button"
                    class="btn btn-success btn-sm"
                    @click="store.runSimulation"
                  >
                    <span
                      :class="{ 'd-none': store.simulationState !== 'running' }"
                      class="spinner-border spinner-border-sm"
                      role="status"
                      aria-hidden="true"
                    ></span>
                    <span class="button-text">{{ buttonText() }}</span>
                  </button>
                </div>
                <div
                  v-if="store.simulationState === 'failed' && store.simulationError"
                  class="alert alert-danger py-1 px-2 mt-2 mb-0 small text-break"
                >
                  {{ store.simulationError }}
                </div>
              </div>
              <h6 class="text-light mt-4 mb-2">Client View</h6>
              <ClientSelector />
            </template>
            <div v-else class="mt-3">
              <h6 class="text-light mb-2">Your Setup</h6>
              <ClientSelector />
              <div class="text-center text-secondary mt-3">
                <p class="small mb-0">Log in as admin to edit parameters and run simulations.</p>
              </div>
            </div>
            <h6 class="text-light mt-4 mb-2">Towers</h6>
            <TowerList />
          </div>
        </div>
      </div>
    </nav>
    <div id="map" ref="map"></div>
    <LoginForm />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import "leaflet/dist/leaflet.css";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import Transmitter from "./components/Transmitter.vue";
import Receiver from "./components/Receiver.vue";
import Environment from "./components/Environment.vue";
import Simulation from "./components/Simulation.vue";
import Display from "./components/Display.vue";
import MatrixConfig from "./components/MatrixConfig.vue";
import ClientSelector from "./components/ClientSelector.vue";
import TowerList from "./components/TowerList.vue";
import LoginForm from "./components/LoginForm.vue";

import { useStore } from "./store.ts";
const store = useStore();

onMounted(() => {
  store.checkAuth();
});
const buttonText = () => {
  if ("running" === store.simulationState) {
    return "Running";
  } else if ("failed" === store.simulationState) {
    return "Failed";
  } else {
    return "Run Simulation";
  }
};
</script>

<style>
.leaflet-div-icon {
  background: transparent;
  border: none !important;
}
</style>
