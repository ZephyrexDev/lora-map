<template>
  <div>
    <ul v-if="store.localSites.length > 0" class="list-group">
      <li
        v-for="(site, index) in store.localSites"
        :key="site.taskId"
        class="list-group-item list-group-item-dark d-flex justify-content-between align-items-center py-1 px-2"
      >
        <span class="text-truncate me-2" :class="{ 'text-muted': !site.visible }">
          <span
            class="d-inline-block rounded-circle me-1"
            :style="{ backgroundColor: site.color || '#4a90d9', width: '10px', height: '10px' }"
          ></span>
          {{ site.params.transmitter.name }}
          <span
            v-if="store.isAdmin && progress[site.taskId] && progress[site.taskId].pending > 0"
            class="badge bg-warning text-dark ms-1"
            :title="`${progress[site.taskId].completed}/${progress[site.taskId].total} simulations completed`"
          >
            {{ progress[site.taskId].completed }}/{{ progress[site.taskId].total }}
          </span>
        </span>
        <span class="d-flex gap-1 flex-shrink-0">
          <button
            type="button"
            class="btn btn-sm btn-outline-light py-0 px-1"
            :title="site.visible ? 'Hide layer' : 'Show layer'"
            @click="store.toggleSiteVisibility(index)"
          >
            <span v-if="site.visible">&#x1F441;&#xFE0F;</span>
            <span v-else class="text-muted">&#x1F6AB;</span>
          </button>
          <button
            v-if="store.isAdmin"
            type="button"
            class="btn btn-sm btn-outline-danger py-0 px-1"
            title="Delete tower"
            @click="store.removeSite(index)"
          >
            &#x1F5D1;&#xFE0F;
          </button>
        </span>
      </li>
    </ul>
    <p v-else class="text-muted small mb-0">No towers</p>
    <div v-if="store.localSites.length >= 2" class="mt-2">
      <button
        type="button"
        class="btn btn-sm w-100"
        :class="store.showTowerPaths ? 'btn-outline-info' : 'btn-outline-secondary'"
        @click="store.toggleTowerPaths()"
      >
        {{ store.showTowerPaths ? "Hide Mesh Paths" : "Show Mesh Paths" }}
      </button>
      <button
        v-if="store.isAdmin"
        type="button"
        class="btn btn-sm btn-outline-warning w-100 mt-1"
        @click="recomputePaths()"
      >
        Recompute Paths
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from "vue";
import { useStore } from "../store.ts";
import { type SimProgress } from "../types.ts";

const store = useStore();

const progress = ref<Record<string, SimProgress>>({});
let pollTimer: ReturnType<typeof setTimeout> | null = null;

async function fetchProgress() {
  if (!store.isAdmin) return;

  let anyPending = false;

  for (const site of store.localSites) {
    if (!site.taskId) continue;
    try {
      const response = await fetch(`/towers/${site.taskId}/simulations`);
      if (!response.ok) continue;
      const data = await response.json();
      const sims: { status: string }[] = data.simulations ?? [];
      const total = sims.length;
      const completed = sims.filter((s) => s.status === "completed").length;
      const pending = sims.filter((s) => s.status === "pending" || s.status === "processing").length;
      progress.value[site.taskId] = { total, completed, pending };
      if (pending > 0) anyPending = true;
    } catch {
      // ignore fetch errors
    }
  }

  // Poll every 5 seconds while any simulations are pending
  if (anyPending) {
    pollTimer = setTimeout(fetchProgress, 5000);
  } else {
    pollTimer = null;
  }
}

function startPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  fetchProgress();
}

// Watch for admin status or site list changes to start/stop polling
watch(
  () => [store.isAdmin, store.localSites.length],
  () => {
    if (store.isAdmin && store.localSites.length > 0) {
      startPolling();
    }
  },
  { immediate: true },
);

onUnmounted(() => {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
});

async function recomputePaths(): Promise<void> {
  try {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (store.adminToken) {
      headers["Authorization"] = `Bearer ${store.adminToken}`;
    }
    const response = await fetch("/tower-paths", {
      method: "POST",
      headers,
    });
    if (!response.ok) {
      console.warn("Failed to recompute paths:", response.statusText);
      return;
    }
    // Wait a few seconds for background tasks, then reload
    setTimeout(() => store.loadTowerPaths(), 5000);
  } catch (err) {
    console.warn("Error recomputing paths:", err);
  }
}
</script>
