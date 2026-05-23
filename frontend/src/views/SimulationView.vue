<template>
  <div class="page">
    <header class="page-header">
      <div class="page-header-row">
        <div>
          <h1>Power Flow Simulations</h1>
          <p class="subtitle">Run power flow analysis on the loaded distribution system model</p>
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
        <code class="start-cmd" style="display:inline-block;background:#1e2130;padding:8px 16px;border-radius:6px;font-family:monospace;font-size:.82rem;color:#7c8aff;margin-top:12px;border:1px solid #2a2d3a">./start.sh --flow</code>
        <br/>
        <button class="btn btn-outline" style="margin-top:16px" @click="simStore.checkHealth()">
          <i class="ri-restart-line"></i> Retry Connection
        </button>
      </div>
    </div>

    <div v-if="!projectStore.activeProject && simStore.isBackendOnline" class="flow-down-overlay">
      <div class="empty-state" style="background:#161922;border:2px solid #2a2d3a;border-radius:16px;padding:60px 20px">
        <i class="ri-database-2-line" style="font-size:3rem;color:#6b7084;margin-bottom:12px"></i>
        <h3>No Model Loaded</h3>
        <p>Load a distribution system model on the <router-link to="/">Load Model</router-link> page first.</p>
      </div>
    </div>

    <div :class="['loader-content', { disabled: simStore.isBackendDown }]" style="max-width:900px" v-if="projectStore.activeProject">
      <section class="sim-section">
        <div class="sim-section-header">
          <h3><i class="ri-database-2-line"></i> Model: {{ projectStore.activeProject.name }}</h3>
        </div>
      </section>

      <section class="sim-section">
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
          <button class="btn btn-outline" :disabled="simStore.running || simStore.isBackendDown" @click="simStore.runCompare(buildConfig(true))">
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
        <div class="powerflow-options-section">
          <div class="powerflow-options-header">
            <div>
              <h4><i class="ri-gear-line"></i> Power Flow Options</h4>
              <p>Control which components participate in the {{ solverLabel(selectedSolver) }} run.</p>
            </div>
          </div>
          <div class="powerflow-options-grid">
            <label
              v-for="field in solverOptionDefinitions[selectedSolver]"
              :key="field.key"
              class="powerflow-option"
            >
              <template v-if="field.type === 'checkbox'">
                <input type="checkbox" v-model="solverOptions[selectedSolver][field.key]" />
                <span>{{ field.label }}</span>
              </template>
              <template v-else>
                <span>{{ field.label }}</span>
                <input
                  type="number"
                  :step="field.step || 0.1"
                  :min="field.min"
                  :max="field.max"
                  v-model.number="solverOptions[selectedSolver][field.key]"
                />
              </template>
            </label>
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
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue'
import { useSimulationStore } from '../stores/simulation'
import { useProjectStore } from '../stores/project'
import { modelsApi } from '../api/client'
import { useToast } from '../composables/useToast'
import type {
  SimulationSolverName,
  SimulationDispatchResponse,
  SimulationCompareResponse,
  SimulationBatchResponse,
  ACSolverConfig,
  DCSolverConfig,
  LinDistFlowConfig,
  SolverConfig,
} from '../types/simulation'

const simStore = useSimulationStore()
const projectStore = useProjectStore()
const { toast } = useToast()

const selectedSolver = ref<SimulationSolverName>('ac-opf')
const quickConfig = ref({ tolerance: 1e-6, max_iter: 300, verbose: false })
type PowerflowOptionSet = Partial<ACSolverConfig & DCSolverConfig & LinDistFlowConfig>

const solverOptions = reactive<Record<SimulationSolverName, PowerflowOptionSet>>({
  'ac-opf': {
    include_loads: true,
    include_solar: true,
    include_battery: true,
    include_capacitor: true,
    include_regulator_targets: false,
    include_regulator_limits: false,
    load_scale: 1,
    solar_scale: 1,
    battery_scale: 1,
    capacitor_scale: 1,
    include_neutral: true,
    include_shunt: true,
    convert_geometry_to_matrix: true,
    vm_min_pu: 0.95,
    vm_max_pu: 1.05,
  },
  'dc-opf': {
    include_solar_generators: true,
    include_battery_generators: true,
    include_loads: true,
    include_slack_generator: true,
    include_neutral: true,
    include_shunt: true,
    convert_geometry_to_matrix: true,
    slack_cost_linear: 1,
    theta_min_rad: -1.57,
    theta_max_rad: 1.57,
    theta_penalty: 0,
    maxiter: 300,
  },
  lindistflow: {
    include_loads: true,
    include_solar: true,
    include_battery: true,
    include_capacitor: true,
    load_scale: 1,
    solar_scale: 1,
    battery_scale: 1,
    capacitor_scale: 1,
    include_neutral: true,
    include_open_switches: false,
  },
})

const solverOptionDefinitions: Record<
  SimulationSolverName,
  Array<{
    key: keyof PowerflowOptionSet
    label: string
    type?: 'checkbox' | 'number'
    step?: number
    min?: number
    max?: number
    hint?: string
  }>
> = {
  'ac-opf': [
    { key: 'include_loads', label: 'Include loads', type: 'checkbox' },
    { key: 'include_solar', label: 'Include solar generators', type: 'checkbox' },
    { key: 'include_battery', label: 'Include battery generators', type: 'checkbox' },
    { key: 'include_capacitor', label: 'Include capacitors', type: 'checkbox' },
    { key: 'include_regulator_targets', label: 'Include regulator targets', type: 'checkbox' },
    { key: 'include_regulator_limits', label: 'Include regulator limits', type: 'checkbox' },
    { key: 'include_neutral', label: 'Model neutral conductors', type: 'checkbox' },
    { key: 'include_shunt', label: 'Include shunt elements', type: 'checkbox' },
    { key: 'convert_geometry_to_matrix', label: 'Convert geometry to matrix', type: 'checkbox' },
    { key: 'load_scale', label: 'Load scale', type: 'number', step: 0.1, min: 0, max: 5 },
    { key: 'solar_scale', label: 'Solar scale', type: 'number', step: 0.1, min: 0, max: 5 },
  ],
  'dc-opf': [
    { key: 'include_loads', label: 'Include loads', type: 'checkbox' },
    { key: 'include_solar_generators', label: 'Include solar generators', type: 'checkbox' },
    { key: 'include_battery_generators', label: 'Include battery generators', type: 'checkbox' },
    { key: 'include_slack_generator', label: 'Include slack generator', type: 'checkbox' },
    { key: 'include_neutral', label: 'Model neutral conductors', type: 'checkbox' },
    { key: 'include_shunt', label: 'Include shunt elements', type: 'checkbox' },
    { key: 'convert_geometry_to_matrix', label: 'Convert geometry to matrix', type: 'checkbox' },
  ],
  lindistflow: [
    { key: 'include_loads', label: 'Include loads', type: 'checkbox' },
    { key: 'include_solar', label: 'Include solar generators', type: 'checkbox' },
    { key: 'include_battery', label: 'Include battery generators', type: 'checkbox' },
    { key: 'include_capacitor', label: 'Include capacitors', type: 'checkbox' },
    { key: 'include_neutral', label: 'Model neutral conductors', type: 'checkbox' },
    { key: 'include_open_switches', label: 'Include open switches', type: 'checkbox' },
    { key: 'load_scale', label: 'Load scale', type: 'number', step: 0.1, min: 0, max: 5 },
    { key: 'solar_scale', label: 'Solar scale', type: 'number', step: 0.1, min: 0, max: 5 },
  ],
}

const isDispatchResult = computed(() => simStore.result && 'execution_mode' in simStore.result)
const isCompareResult = computed(() => simStore.result && 'ac' in simStore.result && 'dc' in simStore.result)
const isBatchResult = computed(() => simStore.result && 'queued_jobs' in simStore.result)

const solverLabels: Record<string, string> = { 'ac-opf': 'AC OPF', 'dc-opf': 'DC OPF', 'lindistflow': 'LinDistFlow', ac: 'AC OPF', dc: 'DC OPF', lindistflow: 'LinDistFlow' }
const solverIcons: Record<string, string> = { 'ac-opf': 'ri-flashlight-line', 'dc-opf': 'ri-battery-charge-line', 'lindistflow': 'ri-flow-chart', ac: 'ri-flashlight-line', dc: 'ri-battery-charge-line', lindistflow: 'ri-flow-chart' }

function solverLabel(s: string): string { return solverLabels[s] || s }
function solverIcon(s: string): string { return solverIcons[s] || 'ri-play-circle-line' }
function solverResultIcon(s: string): string { return solverIcons[s] || 'ri-line-chart-line' }

function buildConfig(includeAllSolvers = false): SolverConfig {
  const base: SolverConfig = {
    tolerance: quickConfig.value.tolerance,
    max_iter: quickConfig.value.max_iter,
    verbose: quickConfig.value.verbose,
  }

  const acOptions = solverOptions['ac-opf'] as ACSolverConfig
  const dcOptions = solverOptions['dc-opf'] as DCSolverConfig
  const lindistOptions = solverOptions.lindistflow as LinDistFlowConfig

  if (includeAllSolvers) {
    base.ac = { ...acOptions }
    base.dc = { ...dcOptions }
    base.lindistflow = { ...lindistOptions }
    return base
  }

  switch (selectedSolver.value) {
    case 'ac-opf':
      base.ac = { ...acOptions }
      break
    case 'dc-opf':
      base.dc = { ...dcOptions }
      break
    case 'lindistflow':
      base.lindistflow = { ...lindistOptions }
      break
  }

  return base
}

async function runSelectedSolver() {
  if (!simStore.selectedModelId) {
    toast('No model synced. Please wait for sync to complete.', 'error')
    return
  }
  await simStore.runSimulation(selectedSolver.value, buildConfig())
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

async function syncProjectModel(project: { id: string; name: string; file_path?: string }) {
  if (!project.file_path) {
    toast('Project has no file path. Re-select it on the Load Model page.', 'error')
    return
  }
  try {
    const { data } = await modelsApi.register(project.name, project.file_path)
    simStore.models.unshift(data)
    simStore.selectModel(data.model_id)
  } catch {
    toast('Failed to sync project with simulation backend', 'error')
  }
}

async function copyResult() {
  try {
    await navigator.clipboard.writeText(JSON.stringify(simStore.result, null, 2))
    toast('Copied to clipboard', 'success')
  } catch { toast('Copy failed', 'error') }
}

async function ensureProjectSynced() {
  await projectStore.fetchProjects()
  const project = projectStore.activeProject
  if (!project) return

  const alreadySynced = simStore.models.find((m) => m.name === project.name)
  if (alreadySynced) {
    simStore.selectModel(alreadySynced.model_id)
    return
  }

  await syncProjectModel(project)
}

onMounted(async () => {
  simStore.startHealthPolling()
  await simStore.fetchModels()
  await ensureProjectSynced()
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

.powerflow-options-section {
  margin-top: 16px;
  padding: 18px;
  background: #1a1c28;
  border: 1px solid #2a2d3a;
  border-radius: 14px;
}
.powerflow-options-header h4 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 6px;
  font-size: 0.95rem;
  color: #f0f2f7;
}
.powerflow-options-header p {
  margin: 0;
  color: #8b8fa3;
  font-size: 0.8rem;
}
.powerflow-options-grid {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.powerflow-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #2e2f48;
  background: #141625;
  font-size: 0.82rem;
}
.powerflow-option input[type='number'] {
  min-width: 70px;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid #2a2d3a;
  background: #0f111c;
  color: #c5c9dd;
}
.powerflow-option input[type='checkbox'] {
  width: 16px;
  height: 16px;
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
