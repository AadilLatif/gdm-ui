import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { modelsApi, simulationsApi, jobsApi, healthApi } from '../api/client'
import type {
  SimulationSolverName,
  SimulationDispatchResponse,
  SimulationCompareResponse,
  SimulationBatchResponse,
  ModelListItem,
  SolverConfig,
  JobStatusResponse,
} from '../types/simulation'

export const useSimulationStore = defineStore('simulation', () => {
  // ── State ──
  const models = ref<ModelListItem[]>([])
  const selectedModelId = ref<string | null>(null)
  const result = ref<SimulationDispatchResponse | SimulationCompareResponse | SimulationBatchResponse | null>(null)
  const running = ref(false)
  const queuedJobId = ref<string | null>(null)
  const error = ref<string | null>(null)

  const isBackendOnline = ref(false)
  const isBackendDown = ref(false)
  const healthChecking = ref(false)

  let _pollTimer: ReturnType<typeof setInterval> | null = null
  let _healthTimer: ReturnType<typeof setInterval> | null = null

  // ── Getters ──
  const selectedModel = computed(() =>
    models.value.find((m) => m.model_id === selectedModelId.value) ?? null,
  )

  // ── Actions ──
  async function fetchModels() {
    try {
      const { data } = await modelsApi.list()
      models.value = data
      if (!selectedModelId.value && data.length > 0) {
        selectedModelId.value = data[0].model_id
      }
    } catch {
      // Backend may be down; silently ignore
    }
  }

  function selectModel(id: string) {
    selectedModelId.value = id
    result.value = null
    error.value = null
    queuedJobId.value = null
  }

  async function uploadModel(file: File, name: string) {
    const { data } = await modelsApi.upload(file, name)
    models.value.unshift(data)
    selectedModelId.value = data.model_id
  }

  async function runSimulation(solver: SimulationSolverName, config?: SolverConfig) {
    if (!selectedModelId.value) return
    running.value = true
    error.value = null
    result.value = null
    queuedJobId.value = null

    try {
      const { data } = await simulationsApi.dispatch({
        model_id: selectedModelId.value,
        solver,
        config,
      })

      if (data.execution_mode === 'queued' && data.job_id) {
        queuedJobId.value = data.job_id
        pollJobStatus(data.job_id)
      }

      result.value = data
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      error.value = detail || 'Simulation failed'
    } finally {
      running.value = false
    }
  }

  async function runCompare(config?: SolverConfig) {
    if (!selectedModelId.value) return
    running.value = true
    error.value = null
    result.value = null

    try {
      const { data } = await simulationsApi.compare({
        model_id: selectedModelId.value,
        config,
      })
      result.value = data
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      error.value = detail || 'Comparison failed'
    } finally {
      running.value = false
    }
  }

  async function runBatch(solver: SimulationSolverName, paramGrid: Record<string, unknown[]>, config?: SolverConfig) {
    if (!selectedModelId.value) return
    running.value = true
    error.value = null
    result.value = null

    try {
      const { data } = await simulationsApi.batch({
        model_id: selectedModelId.value,
        solver,
        config,
        parameter_grid: paramGrid,
      })
      result.value = data
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      error.value = detail || 'Batch simulation failed'
    } finally {
      running.value = false
    }
  }

  async function pollJobStatus(jobId: string) {
    if (_pollTimer) clearInterval(_pollTimer)
    _pollTimer = setInterval(async () => {
      try {
        const { data } = await jobsApi.status(jobId)

        // Merge result if job completed
        if (data.status === 'completed' || data.status === 'failed') {
          if (_pollTimer) {
            clearInterval(_pollTimer)
            _pollTimer = null
          }

          if (data.status === 'completed') {
            try {
              const { data: resultData } = await jobsApi.result(jobId)
              result.value = {
                execution_mode: 'queued',
                status: 'SUCCESS',
                model_id: selectedModelId.value || '',
                solver: (result.value as SimulationDispatchResponse)?.solver || 'ac-opf',
                config: (result.value as SimulationDispatchResponse)?.config || {},
                job_id: jobId,
                result: resultData.result_json ?? null,
              }
            } catch {
              // Keep dispatch result as-is
            }
          } else {
            error.value = data.error || 'Job failed'
          }

          queuedJobId.value = null
        }
      } catch {
        // Ignore polling errors
      }
    }, 3000)
  }

  async function checkHealth() {
    healthChecking.value = true
    try {
      const { data } = await healthApi.check()
      isBackendOnline.value = data.status === 'ok'
      isBackendDown.value = !isBackendOnline.value
    } catch {
      isBackendOnline.value = false
      isBackendDown.value = true
    } finally {
      healthChecking.value = false
    }
  }

  function startHealthPolling() {
    checkHealth()
    _healthTimer = setInterval(checkHealth, 15000)
  }

  function stopHealthPolling() {
    if (_healthTimer) {
      clearInterval(_healthTimer)
      _healthTimer = null
    }
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  return {
    // state
    models,
    selectedModelId,
    result,
    running,
    queuedJobId,
    error,
    isBackendOnline,
    isBackendDown,
    healthChecking,
    // getters
    selectedModel,
    // actions
    fetchModels,
    selectModel,
    uploadModel,
    runSimulation,
    runCompare,
    runBatch,
    pollJobStatus,
    checkHealth,
    startHealthPolling,
    stopHealthPolling,
  }
})
