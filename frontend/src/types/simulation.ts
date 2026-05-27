export type SimulationSolverName = '"'"'ac-opf'"'"' | '"'"'dc-opf'"'"' | '"'"'lindistflow'"'"'

export interface ACSolverConfig {
  include_loads?: boolean
  include_solar?: boolean
  include_battery?: boolean
  include_capacitor?: boolean
  include_regulator_targets?: boolean
  include_regulator_limits?: boolean
  load_scale?: number
  solar_scale?: number
  battery_scale?: number
  capacitor_scale?: number
  slack_label?: [string, string][] | null
  include_neutral?: boolean
  include_shunt?: boolean
  convert_geometry_to_matrix?: boolean
  vm_min_pu?: number
  vm_max_pu?: number
  voltage_reg_weight?: number
  voltage_target_weight?: number
  mismatch_scale_floor_w?: number
  max_nfev?: number
}

export interface DCSolverConfig {
  include_solar_generators?: boolean
  include_battery_generators?: boolean
  include_loads?: boolean
  include_slack_generator?: boolean
  slack_label?: [string, string][] | null
  slack_cost_linear?: number
  include_neutral?: boolean
  include_shunt?: boolean
  convert_geometry_to_matrix?: boolean
  theta_min_rad?: number
  theta_max_rad?: number
  theta_penalty?: number
  maxiter?: number
}

export interface LinDistFlowConfig {
  include_loads?: boolean
  include_solar?: boolean
  include_battery?: boolean
  include_capacitor?: boolean
  load_scale?: number
  solar_scale?: number
  battery_scale?: number
  capacitor_scale?: number
  include_neutral?: boolean
  include_open_switches?: boolean
}

export interface SolverConfig {
  tolerance?: number
  max_iter?: number
  verbose?: boolean
  ac?: ACSolverConfig
  dc?: DCSolverConfig
  lindistflow?: LinDistFlowConfig
}

export interface SimulationRequest {
  model_id: string
  solver: SimulationSolverName
  config?: SolverConfig
}

export interface SimulationCompareRequest {
  model_id: string
  config?: SolverConfig
}

export interface SimulationBatchRequest {
  model_id: string
  solver: SimulationSolverName
  config?: SolverConfig
  parameter_grid: Record<string, unknown[]>
}

export interface SimulationDispatchResponse {
  execution_mode: '"'"'inline'"'"' | '"'"'queued'"'"'
  status: string
  model_id: string
  solver: SimulationSolverName
  config: SolverConfig
  job_id?: string | null
  result?: Record<string, unknown> | null
  result_path?: string | null
}

export interface SimulationCompareResponse {
  model_id: string
  ac: Record<string, unknown>
  dc: Record<string, unknown>
  lindistflow: Record<string, unknown>
  summary: Record<string, unknown>
}

export interface SimulationBatchResponse {
  model_id: string
  solver: SimulationSolverName
  queued_jobs: number
  job_ids: string[]
  sweep_points: Record<string, unknown>[]
  parameter_grid: Record<string, unknown[]>
}

export interface JobStatusResponse {
  job_id: string
  status: string
  model_version_id: string
  job_type: string
  params: Record<string, unknown>
  status_events: Record<string, unknown>[]
  retry_count: number
  next_retry_at?: string | null
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  error?: string | null
  result_path?: string | null
}

export interface JobResultResponse {
  job_id: string
  result_json?: Record<string, unknown> | null
  result_path?: string | null
}

export interface ModelListItem {
  model_id: string
  name: string
  file_size: number
  created_at: string
}

export interface ModelUploadResponse {
  model_id: string
  name: string
  file_size: number
  created_at: string
}
