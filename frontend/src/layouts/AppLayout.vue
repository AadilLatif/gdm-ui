<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-logo">
        <i class="ri-flashlight-line"></i>
        <span>GDM Studio</span>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/model" class="nav-item">
          <i class="ri-file-upload-line"></i>
          <span>Load Model</span>
        </router-link>
        <router-link to="/warehouse" class="nav-item">
          <i class="ri-archive-2-line"></i>
          <span>Warehouse</span>
        </router-link>
        <router-link to="/network" class="nav-item">
          <i class="ri-road-map-line"></i>
          <span>Network</span>
        </router-link>
        <router-link to="/scenarios" class="nav-item">
          <i class="ri-time-line"></i>
          <span>Scenarios</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <div v-if="projectStore.activeProject" class="system-badge">
          <i class="ri-checkbox-circle-line"></i>
          <span>{{ projectStore.activeProject.name }}</span>
        </div>
        <div class="user-section">
          <span class="user-name">{{ auth.user?.username }}</span>
          <button class="btn-icon" title="Logout" @click="handleLogout">
            <i class="ri-logout-box-r-line"></i>
          </button>
        </div>
      </div>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useProjectStore } from '../stores/project'

const auth = useAuthStore()
const projectStore = useProjectStore()
const router = useRouter()

onMounted(async () => {
  await projectStore.fetchProjects()
  if (projectStore.activeProject) {
    await projectStore.fetchSummary()
  }
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
