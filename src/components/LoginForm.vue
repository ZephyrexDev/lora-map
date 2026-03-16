<template>
  <div>
    <!-- Login Modal -->
    <div id="loginModal" class="modal fade" tabindex="-1" aria-labelledby="loginModalLabel" aria-hidden="true">
      <div class="modal-dialog modal-sm modal-dialog-centered">
        <div class="modal-content bg-dark text-light">
          <div class="modal-header border-secondary">
            <h5 v-if="!store.isAdmin" id="loginModalLabel" class="modal-title">Admin Login</h5>
            <h5 v-else id="loginModalLabel" class="modal-title">Logged In</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <form v-if="!store.isAdmin" @submit.prevent="() => handleLogin()">
              <div class="mb-3">
                <label for="passwordInput" class="form-label">Password</label>
                <input
                  id="passwordInput"
                  v-model="password"
                  type="password"
                  class="form-control form-control-sm"
                  placeholder="Enter admin password"
                  autocomplete="current-password"
                />
              </div>
              <div v-if="errorMessage" class="alert alert-danger py-1 px-2 mb-3" role="alert">
                {{ errorMessage }}
              </div>
              <button type="submit" class="btn btn-primary w-100" :disabled="loading">
                <span
                  v-if="loading"
                  class="spinner-border spinner-border-sm me-1"
                  role="status"
                  aria-hidden="true"
                ></span>
                Login
              </button>
            </form>
            <div v-else class="text-center">
              <p class="mb-3">You are logged in as admin.</p>
              <button type="button" class="btn btn-outline-danger w-100" @click="() => handleLogout()">Logout</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useStore } from "../store.ts";

const store = useStore();
const password = ref("");
const errorMessage = ref("");
const loading = ref(false);

async function handleLogin() {
  errorMessage.value = "";
  loading.value = true;
  const success = await store.login(password.value);
  loading.value = false;
  if (success) {
    password.value = "";
    // Close the modal
    const modalEl = document.getElementById("loginModal");
    if (modalEl) {
      const bootstrap = await import("bootstrap/dist/js/bootstrap.bundle.min.js");
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.hide();
    }
  } else {
    errorMessage.value = "Invalid password. Please try again.";
  }
}

function handleLogout() {
  store.logout();
}
</script>
