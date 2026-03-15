<template>
  <div>
    <ul class="list-group" v-if="store.localSites.length > 0">
      <li
        class="list-group-item list-group-item-dark d-flex justify-content-between align-items-center py-1 px-2"
        v-for="(site, index) in store.localSites"
        :key="site.taskId"
      >
        <span class="text-truncate me-2" :class="{ 'text-muted': !site.visible }">
          <span
            class="d-inline-block rounded-circle me-1"
            :style="{ backgroundColor: site.color || '#4a90d9', width: '10px', height: '10px' }"
          ></span>
          {{ site.params.transmitter.name }}
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
          >&#x1F5D1;&#xFE0F;</button>
        </span>
      </li>
    </ul>
    <p v-else class="text-muted small mb-0">No towers</p>
  </div>
</template>

<script setup lang="ts">
import { useStore } from '../store.ts'

const store = useStore()
</script>
