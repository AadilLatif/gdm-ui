<template>
  <div class="page">
    <header class="page-header">
      <div class="page-header-row">
        <div>
          <h1>Power Flow Simulations</h1>
          <p class="subtitle">Run power flow analysis on uploaded distribution system models</p>
        </div>
        <div v-if="simStore.isBackendOnline" style="display:flex;align-items:center;gap:8px">
          <span class="status-indicator online"><i class="ri-checkbox-circle-fill"></i> API Online</span>
        </div>
        <div v-else-if="simStore.isBackendDown" style="display:flex;align-items:center;gap:8px">
          <span class="status-indicator offline"><i class="ri-close-circle-fill"></i> API Offline</span>
        </div>
        <div v-else style="display:flex;align-items:center;gap:8px">
          <span class="status-indicator checking"><div class="spinner" style="width:12px;height:12px;border-width:2px;margin:0"></div> Checking...</span>
        </div>
      </div>
    </header>

    <div v-if="simStore.isBackendDown" class="flow-down-overlay">
      <div class="empty-state" style="background:#161922;border:2px solid #5a2d2d;border-radius:16px;padding:60px 20px">
        <i class="ri-plug-line" style="font-size:3rem;color:#e54d4d;margin-bottom:12px"></i>
        <h3>Flow Backend Not Running</h3>
        <p>Start the FGC Flow API server to run simulations.</p>
        <code class="start-cmd" style="display:inline-block;background:#1e2130;padding:8px 16px;border-radius:6px;font-family:monospace;font-size:.82rem;color:#7c8aff;margin-top:12px;border:1px solid #2a2d3a">uv run uvicorn fgc_flow_api.main:app --reload --port 8000</code>
        <br/>
        <button class="btn btn-outline" style="margin-top:16px" @click="simStore.checkHealth()">
          <i class="ri-restart-line"></i> Retry Connection
        </button>
      </div>
    </div>

    <div :class="['loader-content', { disabled: simStore.isBackendDown }]" style="max-width:900px">
      <section class="sim-section">
        <div class="sim-section-header">
          <h3><i class="ri-database-2-line"></i> Model Selection</h3>
          <button class="btn btn-sm btn-outline" @click="triggerUpload">
            <i class="ri-upload-cloud-2-line"></i> Upload Model
          </button>
          <input ref="fileInput" type="file" accept=".zip" hidden @change="handleUpload" />
        </div>

        <div v-if="uploading" class="sim-status-row">
          <div class="spinner" style="width:20px;height:20px;border-width:3px;margin:0"></div>
          <span style="color:#6b7084">Uploading model...</span>
        </div>

        <div v-if="!uploading && simStore.models.length > 0">
          <div class="project-grid">
            <div
              v-for="model in simStore.models"
              :key="model.model_id"
              :class="['project-card', { active: simStore.selectedModelId === model.model_id }]"
              @click="simStore.selectModel(model.model_id)"
            >
              <div class="project-card-name">{{ model.name }}</div>
              <div class="project-card-desc">{{ formatSize(model.file_size) }}</div>
              <div class="project-card-meta">Created {{ new Date(model.created_at).toLocaleDateString() }}</div>
            </div>
          </div>
        </div>

        <div v-if="!uploading && !simStore.models.length && simStore.isBackendOnline" class="sim-empty">
          <i class="ri-inbox-line"></i>
          <p>No models uploaded yet. Upload a .zip containing a distribution system JSON.</p>
          <button class="btn btn-primary" @click="triggerUpload">
            <i class="ri-upload-cloud-2-line"></i> Upload First Model
          </button>
        </div>
      </section>

      <section v-if="simStore.selectedModelId" class="sim-section">
        <div class="sim-section-header">
          <h3><i class="ri-play-circle-line"></i> Run Simulation</h3>
        </div>

        <div class="category-tabs">
          <button :class="['category-tab', { active: selectedSolver === 'ac-opf' }]" @click="selectedSolver = 'ac-opf'">
            <i class="ri-flashlight-line"></i> AC OPF
          </button>
          <button :class="['category-tab', { active: selectedSolver === 'dc-opf' }]" @click="selectedSolver = 'dc-opf'">
            <i class="ri-battery-charge-line"></i> DC OPF
          </button>
          <button :class="['category-tab', { active: selectedSolver === 'lindistflow' }]" @click="selectedSolver = 'lindistflow'">
            <i class="ri-flow-chart"></i> LinDistFlow
          </button>
        </div>

        <div class="run-actions">
          <button class="btn btn-primary btn-lg" :disabled="simStore.running || simStore.isBackendDown" @click="runSelectedSolver">
            <span v-if="simStore.running" class="spinner" style="width:16px;height:16px;border-width:2px;margin:0"></span>
            <i v-else :class="solverIcon(selectedSolver)"></i>
            {{ simStore.running ? 'Running...' : 'Run ' + solverLabel(selectedSolver) }}
          </button>
          <button class="btn btn-outline" :disabled="simStore.running || simStore.isBackendDown" @click="simStore.runCompare()">
            <i class="ri-scales-3-line"></i> Compare All Solvers
          </button>
        </div>

        <div class="solver-config-summary">
          <div class="config-row">
            <span class="config-label">Tolerance</span>
            <input type="number" class="form-input config-input" step="any" v-model.number="quickConfig.tolerance" />
          </div>
          <div class="config-row">
            <span class="config-label">Max Iterations</span>
            <input type="number" class="form-input config-input" v-model.number="quickConfig.max_iter" />
          </div>
          <div class="config-row">
            <span class="config-label">Verbose</span>
            <select class="form-select config-input" v-model="quickConfig.verbose">
              <option :value="false">No</option>
              <option :value="true">Yes</option>
            </select>
          </div>
        </div>
      </section>

      <section v-if="simStore.queuedJobId" class="sim-section">
        <div class="sim-section-header">
          <h3><i class="ri-timer-line"></i> Job Status</h3>
        </div>
        <div class="sim-status-row">
          <div class="spinner" style="width:20px;height:20px;border-width:3px;margin:0"></div>
          <span>Processing job {{ simStore.queuedJobId }}...</span>
        </div>
        <p class="sim-hint">The simulation has been queued. Polling for results every 3 seconds.</p>
      </section>

      <section v-if="simStore.error" class="sim-section error">
        <div class="sim-section-header">
          <h3 style="color:#e54d4d"><i class="ri-error-warning-line"></i> Simulation Error</h3>
        </div>
        <div class="error-box">
          <pre>{{ simStore.error }}</pre>
        </div>
      </section>

      <section v-if="simStore.result && !simStore.error" class="sim-section results">
        <div class="sim-section-header">
          <h3><i class="ri-bar-chart-2-line"></i> Results</h3>
          <button class="btn btn-sm btn-outline" @click="copyResult">
            <i class="ri-file-copy-line"></i> Copy JSON
          </button>
        </div>

        <div v-if="isDispatchResult" class="result-card">
          <div class="result-meta">
            <span :class="['type-badge', simStore.result.status === 'SUCCESS' ? 'success' : 'pending']">{{ simStore.result.status }}</span>
            <span class="type-badge">{{ simStore.result.solver }}</span>
            <span class="type-badge mode">{{ simStore.result.execution_mode }}</span>
          </div>
          <div v-if="simStore.result.result" class="result-json">
            <pre>{{ JSON.stringify(simStore.result.result, null, 2) }}</pre>
          </div>
          <div v-else-if="simStore.result.job_id" class="result-message">
            <p>Job queued as <code>{{ simStore.result.job_id }}</code>. Result will appear when complete.</p>
          </div>
        </div>

        <div v-if="isCompareResult" class="compare-results">
          <div v-for="solverName in ['ac','dc','lindistflow']" :key="solverName" class="compare-card">
            <div class="compare-card-header">
              <i :class="solverResultIcon(solverName)"></i>
              <span>{{ solverLabel(solverName) }}</span>
            </div>
            <div class="compare-card-body">
              <template v-if="simStore.result[solverName]">
                <div v-for="[key, val] in Object.entries(simStore.result[solverName] || {}).slice(0, 8)" :key="key" class="field-item">
                  <div class="field-label">{{ key }}</div>
                  <div class="field-value">{{ formatValue(val) }}</div>
                </div>
              </template>
              <div v-else class="sim-hint">No data</div>
            </div>
          </div>
          <div v-if="simStore.result.summary" class="compare-summary">
            <div class="compare-card-header">
              <i class="ri-file-chart-line"></i>
              <span>Summary</span>
            </div>
            <div class="compare-card-body">
              <div v-for="[key, val] in Object.entries(simStore.result.summary).slice(0, 8)" :key="key" class="field-item">
                <div class="field-label">{{ key }}</div>
                <div class="field-value">{{ formatValue(val) }}</div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="isBatchResult" class="result-card">
          <div class="result-meta">
            <span class="type-badge">Queued: {{ simStore.result.queued_jobs }}</span>
            <span class="type-badge">{{ simStore.result.solver }}</span>
          </div>
          <div class="result-message">
            <p>{{ simStore.result.queued_jobs }} job(s) submitted.</p>
            <div v-if="simStore.result.job_ids.length > 0">
              <p>Job IDs:</p>
              <div class="job-ids-list">
                <code v-for="id in simStore.result.job_ids" :key="id">{{ id }}</code>
              </div>
            </div>
            <div v-if="simStore.result.sweep_points.length > 0">
              <p>Sweep points:</p>
              <pre>{{ JSON.stringify(simStore.result.sweep_points.slice(0, 10), null, 2) }}</pre>
              <p v-if="simStore.result.sweep_points.length > 10" class="sim-hint">... and {{ simStore.result.sweep_points.length - 10 }} more</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSimulationStore } from '../stores/simulation'
import { useToast } from '../composables/useToast'
import type { SimulationSolverName, SimulationDispatchResponse, SimulationCompareResponse, SimulationBatchResponse } from '../types/simulation'

const simStore = useSimulationStore()
const { toast } = useToast()

const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const selectedSolver = ref<SimulationSolverName>('ac-opf')

const quickConfig = ref({ tolerance: 1e-6, max_iter: 300, verbose: false })

const isDispatchResult = computed(() => simStore.result && 'execution_mode' in simStore.result)
const isCompareResult = computed(() => simStore.result && 'ac' in simStore.result && 'dc' in simStore.result)
const isBatchResult = computed(() => simStore.result && 'queued_jobs' in simStore.result)

const solverLabels: Record<string, string> = { 'ac-opf': 'AC OPF', 'dc-opf': 'DC OPF', 'lindistflow': 'LinDistFlow', ac: 'AC OPF', dc: 'DC OPF', lindistflow: 'LinDistFlow' }
const solverIcons: Record<string, string> = { 'ac-opf': 'ri-flashlight-line', 'dc-opf': 'ri-battery-charge-line', 'lindistflow': 'ri-flow-chart', ac: 'ri-flashlight-line', dc: 'ri-battery-charge-line', lindistflow: 'ri-flow-chart' }

function solverLabel(s: string): string { return solverLabels[s] || s }
function solverIcon(s: string): string { return solverIcons[s] || 'ri-play-circle-line' }
function solverResultIcon(s: string): string { return solverIcons[s] || 'ri-line-chart-line' }

function buildConfig() {
  return { tolerance: quickConfig.value.tolerance, max_iter: quickConfig.value.max_iter, verbose: quickConfig.value.verbose }
}

async function runSelectedSolver() {
  await simStore.runSimulation(selectedSolver.value, buildConfig())
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

function triggerUpload() { fileInput.value?.click() }

async function handleUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.name.endsWith('.zip')) { toast('Please upload a .zip file', 'error'); return }
  uploading.value = true
  try {
    await simStore.uploadModel(file, file.name.replace('.zip', ''))
    toast('Model uploaded', 'success')
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast(msg || 'Upload failed', 'error')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function copyResult() {
  try {
    await navigator.clipboard.writeText(JSON.stringify(simStore.result, null, 2))
    toast('Copied to clipboard', 'success')
  } catch { toast('Copy failed', 'error') }
}

onMounted(async () => {
  simStore.startHealthPolling()
  await simStore.fetchModels()
})

onUnmounted(() => {
  simStore.stopHealthPolling()
})
</script>

<style scoped>
.sim-section {
  background: #161922;
  border: 1px solid #2a2d3a;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
}
.sim-section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.sim-section-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  color: #f0f2f7;
  margin: 0;
}
.sim-section-header h3 i { color: #5b67f5; }
.sim-section.error { border-color: #5a2a2a; }

.sim-empty {
  text-align: center;
  padding: 40px 20px;
  color: #4a4e65;
}
.sim-empty i { font-size: 2rem; margin-bottom: 8px; display: block; }
.sim-empty p { margin-bottom: 16px; }

.sim-status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
}
.sim-hint { color: #6b7084; font-size: 0.8rem; margin-top: 8px; }

.run-actions { display: flex; gap: 10px; margin: 16px 0; }
.btn-lg { padding: 12px 24px; font-size: 0.95rem; }

.solver-config-summary {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px;
  background: #1e2130;
  border-radius: 10px;
  margin-top: 12px;
}
.config-row { display: flex; align-items: center; gap: 8px; }
.config-label { font-size: 0.78rem; color: #8b8fa3; min-width: 90px; }
.config-input { width: 120px !important; padding: 6px 10px !important; }

.result-meta { display: flex; gap: 6px; margin-bottom: 16px; }
.type-badge.success { color: #6fcf6f; background: #1a2e1a; }
.type-badge.pending { color: #f0a030; background: #2e2010; }
.type-badge.mode { color: #a78bfa; background: #201a2e; }

.error-box {
  background: #1e1a1a;
  border: 1px solid #5a2a2a;
  border-radius: 8px;
  padding: 16px;
}
.error-box pre {
  color: #e54d4d;
  font-family: monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.result-json {
  background: #1e2130;
  border: 1px solid #2a2d3a;
  border-radius: 8px;
  padding: 16px;
  max-height: 500px;
  overflow-y: auto;
}
.result-json pre {
  color: #c5c9dd;
  font-family: monospace;
  font-size: 0.82rem;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.result-message {
  padding: 12px 16px;
  background: #1e2130;
  border-radius: 8px;
  color: #c5c9dd;
  font-size: 0.88rem;
}
.result-message code {
  background: #252940;
  padding: 2px 8px;
  border-radius: 4px;
  color: #a8b0ff;
  font-family: monospace;
  font-size: 0.82rem;
}
.job-ids-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.job-ids-list code { display: block; font-size: 0.75rem; word-break: break-all; }

.compare-results {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.compare-card {
  background: #1e2130;
  border: 1px solid #2a2d3a;
  border-radius: 10px;
  overflow: hidden;
}
.compare-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid #2a2d3a;
  font-weight: 600;
  color: #e1e4ea;
  font-size: 0.85rem;
}
.compare-card-header i { color: #7c8aff; }
.compare-card-body { padding: 10px 14px; }
.compare-card-body .field-item { padding: 4px 0; margin-bottom: 4px; }
.compare-card-body .field-label { font-size: 0.7rem; color: #6b7084; }
.compare-card-body .field-value { font-size: 0.82rem; color: #c5c9dd; }
.compare-summary {
  grid-column: 1 / -1;
  background: #1e2130;
  border: 1px solid #2a2d3a;
  border-radius: 10px;
  overflow: hidden;
}

.disabled { opacity: 0.4; pointer-events: none; }

.flow-down-overlay { max-width: 900px; margin: 0 auto; }

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 8px;
}
.status-indicator.online { background: #1a2e1a; border: 1px solid #2d5a2d; color: #6fcf6f; }
.status-indicator.offline { background: #2e1a1a; border: 1px solid #5a2d2d; color: #e54d4d; }
.status-indicator.checking { background: #1a1a2e; border: 1px solid #2d2d5a; color: #8b8fa3; }

@media (max-width: 768px) {
  .compare-results { grid-template-columns: 1fr; }
  .solver-config-summary { flex-direction: column; }
}
</style>
