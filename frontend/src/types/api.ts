// ===== Auth =====
export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: string
  email: string
  username: string
  is_active: boolean
  is_admin: boolean
  created_at: string
}

// ===== Projects =====
export interface Project {
  id: string
  name: string
  description: string
  is_active: boolean
  created_at: string
  owner_id: string
  file_path?: string
}

// ===== System =====
export interface SystemSummary {
  name: string | null
  uuid: string
  description: string | null
  total_components: number
  component_types: Record<string, number>
}

// ===== Components =====
export interface GDMComponent {
  _type: string
  uuid: string
  name: string
  [key: string]: unknown
}

// ===== Network =====
export interface TopologyNode {
  id: string
  [key: string]: string
}

export interface TopologyEdge {
  source: string
  target: string
  [key: string]: string
}

export interface Topology {
  nodes: TopologyNode[]
  edges: TopologyEdge[]
}

// ===== Equipment Categories =====
export type EquipmentCategories = Record<string, string[]>
