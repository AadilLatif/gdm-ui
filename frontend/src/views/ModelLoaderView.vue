<template>
  <div class="page">
    <header class="page-header">
      <h1>Load Distribution System</h1>
      <p class="subtitle">Upload a GDM distribution system model (.zip) or select an existing one</p>
    </header>

    <div class="loader-content">
      <!-- Upload Zone -->
      <div
        v-if="!projectStore.activeProject"
        class="upload-zone"
        :class="{ dragover }"
        @click="fileInput?.click()"
        @dragover.prevent="dragover = true"
        @dragleave="dragover = false"
        @drop.prevent="handleDrop"
      >
        <div class="upload-icon"><i class="ri-upload-cloud-2-line"></i></div>
        <h3>Drop a GDM model zip file here</h3>
        <p>or click to browse</p>
        <input ref="fileInput" type="file" accept=".zip" hidden @change="handleFileSelect" />
        <button class="btn btn-outline" @click.stop="fileInput?.click()">Browse Files</button>
        <div class="upload-hint">
          <span>Upload a <code>.zip</code> containing the system JSON and time_series folder</span>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="uploading" style="text-align:center;padding:40px">
        <div class="spinner"></div>
        <p style="color:#6b7084">Uploading and loading model...</p>
      </div>

      <!-- System Summary -->
      <div v-if="projectStore.activeProject && projectStore.summary" class="system-summary">
        <div class="summary-header">
          <h2>{{ projectStore.activeProject.name }}</h2>
          <div class="summary-actions">
            <button class="btn btn-primary" @click="$router.push('/warehouse')">
              <i class="ri-archive-2-line"></i> Open Warehouse
            </button>
          </div>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">{{ projectStore.summary.total_components }}</div>
            <div class="stat-label">Total Components</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ Object.keys(projectStore.summary.component_types).length }}</div>
            <div class="stat-label">Component Types</div>
          </div>
        </div>

        <div class="component-table-wrap">
          <h3>Component Inventory</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>Component Type</th>
                <th>Count</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(count, type) in projectStore.summary.component_types" :key="type">
                <td><span class="type-badge">{{ type }}</span></td>
                <td><span class="count-badge">{{ count }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Existing Projects -->
      <div v-if="projectStore.projects.length > 0" style="margin-top:32px">
        <h3 style="color:#c5c9dd;margin-bottom:12px">Your Models</h3>
        <div class="project-grid">
          <div
            v-for="project in projectStore.projects"
            :key="project.id"
            class="project-card"
            :class="{ active: project.is_active }"
            @click="selectProject(project.id)"
          >
            <div class="project-card-name">{{ project.name }}</div>
            <div class="project-card-desc">{{ project.description || 'No description' }}</div>
            <div class="project-card-actions">
              <button
                v-if="!project.is_active"
                class="btn btn-sm btn-primary"
                @click.stop="selectProject(project.id)"
              >
                Select
              </button>
              <span v-else class="type-badge" style="color:#6fcf6f;background:#1a2e1a">Active</span>
              <button class="btn btn-sm btn-outline" title="Edit name / description" @click.stop="openEdit(project)">
                <i class="ri-pencil-line"></i>
              </button>
              <button class="btn btn-sm btn-outline" title="Make a copy" @click.stop="copyProject(project.id)">
                <i class="ri-file-copy-line"></i>
              </button>
              <button
                v-if="project.is_active"
                class="btn btn-sm btn-outline"
                title="Download as .zip"
                @click.stop="downloadProject"
              >
                <i class="ri-download-2-line"></i>
              </button>
              <button class="btn btn-sm btn-outline btn-danger" @click.stop="deleteProject(project.id)">
                <i class="ri-delete-bin-line"></i>
              </button>
            </div>
            <div class="project-card-meta">
              Created {{ new Date(project.created_at).toLocaleDateString() }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <Teleport to="body">
      <div v-if="editModal" class="modal-overlay" @click.self="editModal = false">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h2>Edit Model</h2>
            <button class="modal-close" @click="editModal = false"><i class="ri-close-line"></i></button>
          </div>
          <div class="modal-body">
            <label class="form-label">Name</label>
            <input v-model="editName" class="form-input" />
            <label class="form-label" style="margin-top:12px">Description</label>
            <textarea v-model="editDesc" class="form-input" rows="3" />
          </div>
          <div class="modal-footer">
            <button class="btn btn-outline" @click="editModal = false">Cancel</button>
            <button class="btn btn-primary" :disabled="!editName.trim()" @click="saveEdit">Save</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useProjectStore } from '../stores/project'
import { projectsApi, systemApi } from '../api/client'
import { useToast } from '../composables/useToast'

const projectStore = useProjectStore()
const { toast } = useToast()

const fileInput = ref<HTMLInputElement | null>(null)
const dragover = ref(false)
const uploading = ref(false)

// Edit modal state
const editModal = ref(false)
const editId = ref('')
const editName = ref('')
const editDesc = ref('')

function openEdit(project: { id: string; name: string; description?: string }) {
  editId.value = project.id
  editName.value = project.name
  editDesc.value = project.description || ''
  editModal.value = true
}

async function saveEdit() {
  try {
    await projectsApi.update(editId.value, { name: editName.value.trim(), description: editDesc.value.trim() })
    await projectStore.fetchProjects()
    editModal.value = false
    toast('Model updated', 'success')
  } catch {
    toast('Failed to update model', 'error')
  }
}

async function handleFile(file: File) {
  if (!file.name.endsWith('.zip')) {
    toast('Please upload a .zip file', 'error')
    return
  }
  uploading.value = true
  try {
    const project = await projectStore.uploadProject(file, file.name.replace('.zip', ''))
    await projectStore.selectProject(project.id)
    toast('Model loaded successfully', 'success')
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast(msg || 'Upload failed', 'error')
  } finally {
    uploading.value = false
  }
}

function handleFileSelect(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (files?.length) handleFile(files[0])
}

function handleDrop(e: DragEvent) {
  dragover.value = false
  const files = e.dataTransfer?.files
  if (files?.length) handleFile(files[0])
}

async function selectProject(id: string) {
  try {
    await projectStore.selectProject(id)
    toast('Model selected', 'success')
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast(msg || 'Failed to select model', 'error')
  }
}

async function deleteProject(id: string) {
  if (!confirm('Delete this model?')) return
  try {
    await projectStore.deleteProject(id)
    toast('Model deleted', 'success')
  } catch {
    toast('Failed to delete model', 'error')
  }
}

async function copyProject(id: string) {
  try {
    await projectsApi.copy(id)
    await projectStore.fetchProjects()
    toast('Model copied', 'success')
  } catch {
    toast('Failed to copy model', 'error')
  }
}

async function downloadProject() {
  try {
    const { data } = await systemApi.download()
    const blob = new Blob([data], { type: 'application/zip' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${projectStore.activeProject?.name || 'model'}.zip`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast('Failed to download model', 'error')
  }
}
</script>
