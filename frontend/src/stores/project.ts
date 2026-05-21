import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectsApi, systemApi } from '../api/client'
import type { Project, SystemSummary } from '../types/api'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const activeProject = computed(() => projects.value.find((p) => p.is_active) ?? null)
  const summary = ref<SystemSummary | null>(null)
  const loading = ref(false)

  async function fetchProjects() {
    const { data } = await projectsApi.list()
    projects.value = data
  }

  async function uploadProject(file: File, name?: string, description?: string) {
    const { data } = await projectsApi.upload(file, name, description)
    projects.value.push(data)
    return data
  }

  async function selectProject(id: string) {
    loading.value = true
    try {
      const { data } = await projectsApi.select(id)
      // Update local state
      projects.value.forEach((p) => (p.is_active = p.id === data.id))
      await fetchSummary()
    } finally {
      loading.value = false
    }
  }

  async function deleteProject(id: string) {
    await projectsApi.delete(id)
    projects.value = projects.value.filter((p) => p.id !== id)
    if (summary.value) summary.value = null
  }

  async function fetchSummary() {
    try {
      const { data } = await systemApi.summary()
      summary.value = data
    } catch {
      summary.value = null
    }
  }

  return { projects, activeProject, summary, loading, fetchProjects, uploadProject, selectProject, deleteProject, fetchSummary }
})
