import axios from 'axios'
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  User,
  Project,
  SystemSummary,
  GDMComponent,
  Topology,
  EquipmentCategories,
} from '../types/api'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

// Attach auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 — try refresh
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post<TokenResponse>(
            `${api.defaults.baseURL}/api/auth/refresh`,
            { refresh_token: refreshToken }
          )
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

// ===== Auth =====
export const authApi = {
  register: (data: RegisterRequest) => api.post<User>('/api/auth/register', data),
  login: (data: LoginRequest) => api.post<TokenResponse>('/api/auth/login', data),
  me: () => api.get<User>('/api/auth/me'),
}

// ===== Projects =====
export const projectsApi = {
  list: () => api.get<Project[]>('/api/projects/'),
  get: (id: string) => api.get<Project>(`/api/projects/${id}`),
  upload: (file: File, name?: string, description?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (name) form.append('name', name)
    if (description) form.append('description', description)
    return api.post<Project>('/api/projects/upload', form)
  },
  select: (id: string) => api.post<Project>(`/api/projects/${id}/select`),
  update: (id: string, data: { name?: string; description?: string }) =>
    api.patch<Project>(`/api/projects/${id}`, data),
  delete: (id: string) => api.delete(`/api/projects/${id}`),
  copy: (id: string) => api.post<Project>(`/api/projects/${id}/copy`),
}

// ===== System =====
export const systemApi = {
  summary: () => api.get<SystemSummary>('/api/system/summary'),
  components: (type?: string) =>
    api.get<GDMComponent[]>('/api/system/components', { params: type ? { component_type: type } : {} }),
  component: (uuid: string) => api.get<GDMComponent>(`/api/system/components/${uuid}`),
  export: () => api.get('/api/system/export'),
  download: () => api.get('/api/system/download', { responseType: 'blob' }),
}

// ===== Equipment =====
export const equipmentApi = {
  categories: () => api.get<EquipmentCategories>('/api/equipment/categories'),
  list: (category?: string) =>
    api.get<GDMComponent[]>('/api/equipment/', { params: category ? { category } : {} }),
  get: (uuid: string) => api.get<GDMComponent>(`/api/equipment/${uuid}`),
  add: (type: string, data: Record<string, unknown>) =>
    api.post<GDMComponent>('/api/equipment/', { type, data }),
  update: (uuid: string, data: Record<string, unknown>) =>
    api.patch<GDMComponent>(`/api/equipment/${uuid}`, { data }),
  remove: (uuid: string) => api.delete(`/api/equipment/${uuid}`),
}

// ===== Network =====
export const networkApi = {
  topology: () => api.get<Topology>('/api/network/topology'),
  buses: () => api.get<GDMComponent[]>('/api/network/buses'),
}

// ===== Scenarios =====
export const scenariosApi = {
  list: () => api.get<ScenarioFile[]>('/api/scenarios/'),
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ScenarioFile>('/api/scenarios/upload', form)
  },
  timeline: (filename: string, scenarioName: string) =>
    api.get<ScenarioTimeline>('/api/scenarios/timeline', { params: { filename, scenario_name: scenarioName } }),
  remove: (filename: string) => api.delete(`/api/scenarios/${encodeURIComponent(filename)}`),
}

export interface ScenarioFile {
  filename: string
  scenario_names: string[]
  total_changes: number
}

export interface ScenarioTimelineStep {
  name: string
  timestamp: string | null
  additions: Array<{ uuid: string; name: string; type: string; bus?: string; bus1?: string; bus2?: string; coordinate?: { x: number; y: number } }>
  deletions: Array<{ uuid: string; name: string; type: string }>
  edits: Array<{ component_uuid: string; field: string; value: unknown; component_name: string; component_type: string }>
}

export interface ScenarioTimeline {
  scenario_name: string
  filename: string
  steps: ScenarioTimelineStep[]
}

export default api
