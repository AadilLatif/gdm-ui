<template>
  <div class="page-network">
    <div class="network-container">
      <div class="network-map-wrap" @dragover.prevent @drop="onMapDrop">
        <div id="networkMap" ref="mapContainer"></div>
        <div class="map-toolbar">
          <button class="map-tool-btn" title="Fit to bounds" @click="fitBounds">
            <i class="ri-fullscreen-line"></i>
          </button>
          <button
            class="map-tool-btn"
            :class="{ active: showLabels }"
            title="Toggle bus labels"
            @click="showLabels = !showLabels"
          >
            <i class="ri-price-tag-3-line"></i>
          </button>
          <button
            class="map-tool-btn"
            :class="{ active: showIcons }"
            title="Toggle component icons"
            @click="showIcons = !showIcons"
          >
            <i class="ri-plug-line"></i>
          </button>
          <div class="map-legend">
            <span class="legend-item"><span class="legend-dot" style="background:#5b67f5"></span>Bus</span>
            <span class="legend-item"><span class="legend-line" style="background:#6fcf6f"></span>Branch</span>
            <span class="legend-item"><span class="legend-dot" style="background:#f0a030"></span>Transformer</span>
            <span class="legend-item"><span class="legend-dot" style="background:#e54d4d"></span>Switch</span>
          </div>
        </div>
        <div v-if="!hasData" class="map-empty-state">
          <i class="ri-road-map-line"></i>
          <h3>No network loaded</h3>
          <p>Load a GDM system to view the network topology on the map.</p>
        </div>
      </div>

      <!-- Right panel: component palette -->
      <div class="network-panel">
        <div class="panel-section">
          <div class="panel-header">
            <h3>Components</h3>
            <span class="panel-hint">Drag onto map bus</span>
          </div>
          <div class="component-palette">
            <div v-for="(items, cat) in palette" :key="cat" class="palette-category">
              <div class="palette-category-title">{{ cat }}</div>
              <div
                v-for="item in items"
                :key="item.type"
                class="palette-item"
                draggable="true"
                @dragstart="onDragStart($event, item.type)"
              >
                <i :class="item.icon"></i>
                <span>{{ item.label }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div v-if="editModal.show" class="modal-overlay" @click.self="editModal.show = false">
      <div class="modal-card">
        <div class="modal-header">
          <h3>{{ editModal.title }}</h3>
          <button class="btn-icon" @click="editModal.show = false"><i class="ri-close-line"></i></button>
        </div>
        <div class="modal-body">
          <!-- Single bus dropdown -->
          <div v-if="activeCompSchema?.busMode === 'single'" class="form-group">
            <label class="form-label">Bus <span class="required">*</span></label>
            <select class="form-select" :value="editData._bus ?? ''" @change="editData._bus = ($event.target as HTMLSelectElement).value || null">
              <option value="">— Select Bus —</option>
              <option v-for="b in busList" :key="b" :value="b">{{ b }}</option>
            </select>
          </div>
          <!-- Dual bus dropdowns -->
          <div v-if="activeCompSchema?.busMode === 'dual'" class="form-group">
            <label class="form-label">Connected Buses <span class="required">*</span></label>
            <div style="display:flex;gap:8px">
              <select class="form-select" :value="editData._bus1 ?? ''" @change="editData._bus1 = ($event.target as HTMLSelectElement).value || null">
                <option value="">— From Bus —</option>
                <option v-for="b in busList" :key="b" :value="b">{{ b }}</option>
              </select>
              <select class="form-select" :value="editData._bus2 ?? ''" @change="editData._bus2 = ($event.target as HTMLSelectElement).value || null">
                <option value="">— To Bus —</option>
                <option v-for="b in busList" :key="b" :value="b">{{ b }}</option>
              </select>
            </div>
          </div>
          <template v-for="(fieldDef, key) in activeCompSchema?.fields" :key="key">
            <!-- Coordinate display for new bus -->
            <div v-if="editModal.isNew && editModal.compType === 'DistributionBus' && String(key) === 'name' && editData._lat" class="form-group" style="margin-bottom:12px">
              <label class="form-label">Location (from map click)</label>
              <div style="display:flex;gap:8px">
                <input type="number" step="any" class="form-input" placeholder="Latitude" :value="editData._lat" @input="editData._lat = ($event.target as HTMLInputElement).value" />
                <input type="number" step="any" class="form-input" placeholder="Longitude" :value="editData._lng" @input="editData._lng = ($event.target as HTMLInputElement).value" />
              </div>
            </div>
            <!-- Phase select -->
            <div v-if="fieldDef.type === 'phase_select'" class="form-group">
              <label class="form-label">{{ formatKey(String(key)) }} <span v-if="fieldDef.required" class="required">*</span></label>
              <div style="display:flex;gap:6px;flex-wrap:wrap">
                <label v-for="p in ['A','B','C','N','S1','S2']" :key="p" class="phase-chip" :class="{ active: (editData[String(key)] as string[] || []).includes(p) }">
                  <input type="checkbox" :value="p" :checked="(editData[String(key)] as string[] || []).includes(p)" @change="togglePhase(String(key), p)" style="display:none" />
                  {{ p }}
                </label>
              </div>
            </div>
            <!-- Equipment ref (dropdown) -->
            <div v-else-if="fieldDef.type === 'equipment_ref'" class="form-group">
              <label class="form-label">{{ fieldDef.description || formatKey(String(key)) }} <span v-if="fieldDef.required" class="required">*</span></label>
              <select class="form-select" :value="getRefName(editData[String(key)])" @change="editData[String(key)] = ($event.target as HTMLSelectElement).value || null">
                <option value="">— Select {{ formatKey(fieldDef.equipmentType || 'Equipment') }} —</option>
                <option v-for="eq in equipmentOptions[fieldDef.equipmentType || ''] || []" :key="eq.uuid" :value="eq.name">{{ eq.name }}</option>
                <option v-if="!(equipmentOptions[fieldDef.equipmentType || ''] || []).length" value="" disabled>No equipment in warehouse</option>
              </select>
            </div>
            <!-- Enum -->
            <div v-else-if="fieldDef.type === 'enum'" class="form-group">
              <label class="form-label">{{ formatKey(String(key)) }} <span v-if="fieldDef.required" class="required">*</span></label>
              <select class="form-select" :value="editData[String(key)] ?? ''" @change="editData[String(key)] = ($event.target as HTMLSelectElement).value || null">
                <option value="">— Select —</option>
                <option v-for="opt in getEnumOpts(fieldDef.enum)" :key="opt" :value="opt">{{ opt }}</option>
              </select>
            </div>
            <!-- Boolean -->
            <div v-else-if="fieldDef.type === 'boolean'" class="form-group">
              <label class="form-label">{{ formatKey(String(key)) }}</label>
              <select class="form-select" :value="editData[String(key)] === true ? 'true' : editData[String(key)] === false ? 'false' : ''" @change="editData[String(key)] = ($event.target as HTMLSelectElement).value === 'true' ? true : ($event.target as HTMLSelectElement).value === 'false' ? false : null">
                <option value="">— Select —</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </div>
            <!-- Quantity -->
            <div v-else-if="fieldDef.type === 'quantity'" class="form-group">
              <label class="form-label">{{ fieldDef.description || formatKey(String(key)) }} <span v-if="fieldDef.required" class="required">*</span></label>
              <div style="display:flex;gap:8px">
                <input type="number" step="any" class="form-input" :placeholder="fieldDef.description || String(key)" :value="getQtyVal(editData[String(key)])" @input="setQtyVal(String(key), ($event.target as HTMLInputElement).value, fieldDef.unit)" />
                <div style="display:flex;align-items:center;color:#5b67f5;font-size:0.82rem;white-space:nowrap;min-width:40px">{{ getQtyUnit(editData[String(key)]) || fieldDef.unit || '' }}</div>
              </div>
            </div>
            <!-- Integer / Float -->
            <div v-else-if="fieldDef.type === 'integer' || fieldDef.type === 'float'" class="form-group">
              <label class="form-label">{{ fieldDef.description || formatKey(String(key)) }} <span v-if="fieldDef.required" class="required">*</span></label>
              <input type="number" :step="fieldDef.type === 'integer' ? '1' : 'any'" class="form-input" :value="editData[String(key)] ?? ''" @input="editData[String(key)] = ($event.target as HTMLInputElement).value ? Number(($event.target as HTMLInputElement).value) : null" />
            </div>
            <!-- Array float -->
            <div v-else-if="fieldDef.type === 'array_float'" class="form-group">
              <label class="form-label">{{ fieldDef.description || formatKey(String(key)) }}</label>
              <input type="text" class="form-input" placeholder="e.g. 1.0, 1.0, 1.0" :value="Array.isArray(editData[String(key)]) ? (editData[String(key)] as number[]).join(', ') : ''" @input="editData[String(key)] = ($event.target as HTMLInputElement).value.split(',').map((s: string) => parseFloat(s.trim())).filter((n: number) => !isNaN(n))" />
            </div>
            <!-- String (default) -->
            <div v-else class="form-group">
              <label class="form-label">{{ fieldDef.description || formatKey(String(key)) }} <span v-if="fieldDef.required" class="required">*</span></label>
              <input type="text" class="form-input" :placeholder="fieldDef.description || String(key)" :value="editData[String(key)] ?? ''" @input="editData[String(key)] = ($event.target as HTMLInputElement).value || null" />
            </div>
          </template>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="editModal.show = false">Cancel</button>
          <button class="btn btn-primary" @click="saveEdit">Save</button>
        </div>
      </div>
    </div>

    <!-- Delete confirm modal -->
    <div v-if="deleteModal.show" class="modal-overlay" @click.self="deleteModal.show = false">
      <div class="modal-card" style="max-width:400px">
        <div class="modal-header">
          <h3>Delete Component</h3>
          <button class="btn-icon" @click="deleteModal.show = false"><i class="ri-close-line"></i></button>
        </div>
        <div class="modal-body">
          <p style="color:#e1e4ea">Delete <strong>"{{ deleteModal.name }}"</strong> ({{ deleteModal.label }})?</p>
          <p style="color:#6b7084;font-size:0.85rem;margin-top:8px">This action cannot be undone.</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-ghost" @click="deleteModal.show = false">Cancel</button>
          <button class="btn btn-danger" @click="confirmDelete">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { networkApi, systemApi, equipmentApi } from '../api/client'
import type { Topology, GDMComponent } from '../types/api'
import { COMPONENT_ICONS, COMPONENT_SCHEMAS, ENUMS } from '../types/schemas'
import { useToast } from '../composables/useToast'

const { toast } = useToast()
const mapContainer = ref<HTMLElement | null>(null)
const showLabels = ref(false)
const showIcons = ref(true)
const hasData = ref(false)

let map: L.Map | null = null
const layers: L.Layer[] = []
const labelLayers: L.Layer[] = []
const iconLayers: L.Layer[] = []

interface BusLoc {
  lat: number; lng: number; name: string; uuid: string
  phases: string[]; voltageType: string; ratedVoltage: string
}

interface NodeComp {
  name: string; uuid: string; type: string; busName: string
}

let nodeComponents: NodeComp[] = []
let busLookup = new Map<string, BusLoc>()

const COMP_LABELS: Record<string, string> = {
  DistributionBus: 'Distribution Bus',
  DistributionLoad: 'Load',
  DistributionSolar: 'Solar',
  DistributionBattery: 'Battery',
  DistributionCapacitor: 'Capacitor',
  DistributionVoltageSource: 'Voltage Source',
  DistributionTransformer: 'Transformer',
  MatrixImpedanceBranch: 'Impedance Branch',
  MatrixImpedanceFuse: 'Fuse',
  MatrixImpedanceRecloser: 'Recloser',
  MatrixImpedanceSwitch: 'Switch',
}

// ===== Modals =====
const editModal = reactive({
  show: false, title: '',
  uuid: '', compType: '', isNew: false,
})

const editData = reactive<Record<string, unknown>>({})

const activeCompSchema = computed(() => COMPONENT_SCHEMAS[editModal.compType] || null)

const busList = computed(() => {
  const names: string[] = []
  for (const bus of busLookup.values()) names.push(bus.name)
  return names.sort()
})

const equipmentOptions = reactive<Record<string, { uuid: string; name: string }[]>>({})

async function loadEquipmentOptions(compType: string) {
  const schema = COMPONENT_SCHEMAS[compType]
  if (!schema) return
  const eqTypes = new Set<string>()
  for (const fd of Object.values(schema.fields)) {
    if (fd.type === 'equipment_ref' && fd.equipmentType) eqTypes.add(fd.equipmentType)
  }
  const fetches = [...eqTypes].filter(t => !(t in equipmentOptions))
  await Promise.all(fetches.map(async (eqType) => {
    try {
      const { data } = await systemApi.components(eqType)
      equipmentOptions[eqType] = data.map((c: any) => ({ uuid: c.uuid, name: c.name }))
    } catch {
      equipmentOptions[eqType] = []
    }
  }))
}

const deleteModal = reactive({
  show: false, name: '', label: '', uuid: '',
})

const palette = {
  'Loads & DER': [
    { type: 'DistributionLoad', icon: 'pi pi-load', label: 'Load' },
    { type: 'DistributionSolar', icon: 'pi pi-solar', label: 'Solar' },
    { type: 'DistributionBattery', icon: 'pi pi-battery', label: 'Battery' },
    { type: 'DistributionCapacitor', icon: 'pi pi-capacitor', label: 'Capacitor' },
  ],
  Sources: [
    { type: 'DistributionVoltageSource', icon: 'pi pi-vsource', label: 'Voltage Source' },
  ],
  Branches: [
    { type: 'MatrixImpedanceBranch', icon: 'pi pi-impedance', label: 'Impedance Branch' },
    { type: 'SequenceImpedanceBranch', icon: 'pi pi-impedance', label: 'Seq. Branch' },
    { type: 'GeometryBranch', icon: 'pi pi-geometry', label: 'Geometry Branch' },
  ],
  Protection: [
    { type: 'MatrixImpedanceFuse', icon: 'pi pi-fuse', label: 'Fuse' },
    { type: 'MatrixImpedanceRecloser', icon: 'pi pi-recloser', label: 'Recloser' },
    { type: 'MatrixImpedanceSwitch', icon: 'pi pi-switch', label: 'Switch' },
  ],
  Infrastructure: [
    { type: 'DistributionTransformer', icon: 'pi pi-transformer', label: 'Transformer' },
    { type: 'DistributionBus', icon: 'pi pi-bus', label: 'Bus' },
  ],
}

// ===== Map =====
function initMap() {
  if (!mapContainer.value || map) return
  map = L.map(mapContainer.value, {
    center: [36.58, -120.95], zoom: 13,
    zoomControl: false, attributionControl: false,
  })
  L.control.zoom({ position: 'bottomleft' }).addTo(map)
  L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
    maxZoom: 20,
    attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>',
  }).addTo(map)
}

// ===== Data Loading =====
async function loadTopology() {
  try {
    const [topologyRes, busesRes, loadsRes, sourcesRes] = await Promise.all([
      networkApi.topology(),
      systemApi.components('DistributionBus'),
      systemApi.components('DistributionLoad'),
      systemApi.components('DistributionVoltageSource'),
    ])

    nodeComponents = []
    for (const load of loadsRes.data) {
      const busName = typeof load.bus === 'object' ? load.bus?.name : load.bus
      if (busName) nodeComponents.push({ name: load.name, uuid: load.uuid, type: 'DistributionLoad', busName })
    }
    for (const src of sourcesRes.data) {
      const busName = typeof src.bus === 'object' ? src.bus?.name : src.bus
      if (busName) nodeComponents.push({ name: src.name, uuid: src.uuid, type: 'DistributionVoltageSource', busName })
    }

    renderTopology(topologyRes.data, busesRes.data)
    hasData.value = true
  } catch {
    hasData.value = false
  }
}

// ===== Helpers =====
function esc(s: string) {
  const d = document.createElement('div')
  d.textContent = s
  return d.innerHTML
}

// ===== Popup Builders =====
function buildBusPopup(bus: BusLoc, attached: NodeComp[]) {
  const icon = COMPONENT_ICONS.DistributionBus || 'ri-circle-line'
  let html = `
    <div class="popup-header">
      <div class="popup-title"><i class="${icon}" style="color:#5b67f5"></i><span>${esc(bus.name)}</span></div>
      <div class="popup-actions">
        <button class="btn-icon popup-edit-btn" data-uuid="${bus.uuid}" data-type="DistributionBus" title="Edit"><i class="ri-edit-line"></i></button>
        <button class="btn-icon danger popup-delete-btn" data-uuid="${bus.uuid}" data-name="${esc(bus.name)}" data-label="Distribution Bus" title="Delete"><i class="ri-delete-bin-line"></i></button>
      </div>
    </div>
    <div class="popup-body"><div class="field-grid">
      <div class="field-item"><div class="field-label">Type</div><div class="field-value">Distribution Bus</div></div>
      <div class="field-item"><div class="field-label">Voltage Type</div><div class="field-value" style="color:#a8b0ff">${esc(bus.voltageType || '—')}</div></div>
      <div class="field-item"><div class="field-label">Phases</div><div class="field-value">${esc(bus.phases.join(', ') || '—')}</div></div>
      <div class="field-item"><div class="field-label">Rated Voltage</div><div class="field-value">${esc(bus.ratedVoltage || '—')}</div></div>
      <div class="field-item"><div class="field-label">Coordinates</div><div class="field-value">${bus.lat.toFixed(5)}, ${bus.lng.toFixed(5)}</div></div>
    </div></div>`

  if (attached.length > 0) {
    html += `<div class="popup-connected"><div class="field-label">CONNECTED COMPONENTS</div>`
    for (const nc of attached) {
      const ncIcon = COMPONENT_ICONS[nc.type] || 'ri-box-3-line'
      html += `<div class="popup-connected-item"><i class="${ncIcon}"></i>${esc(nc.name)}<span class="popup-comp-type">${COMP_LABELS[nc.type] || nc.type}</span></div>`
    }
    html += `</div>`
  }
  return html
}

function buildEdgePopup(edge: { source: string; target: string; name?: string; type?: string; is_closed?: string; uuid?: string }) {
  const typeName = edge.type?.replace(/<class '.*\.(.*)'>/,'$1') || 'Branch'
  const icon = COMPONENT_ICONS[typeName] || 'ri-git-branch-line'
  const edgeUuid = edge.uuid || ''
  const edgeName = edge.name || ''
  return `
    <div class="popup-header">
      <div class="popup-title"><i class="${icon}" style="color:#5b67f5"></i><span>${esc(edgeName)}</span></div>
      <div class="popup-actions">
        <button class="btn-icon popup-edit-btn" data-uuid="${edgeUuid}" data-type="${esc(typeName)}" title="Edit"><i class="ri-edit-line"></i></button>
        <button class="btn-icon danger popup-delete-btn" data-uuid="${edgeUuid}" data-name="${esc(edgeName)}" data-label="${COMP_LABELS[typeName] || typeName}" title="Delete"><i class="ri-delete-bin-line"></i></button>
      </div>
    </div>
    <div class="popup-body"><div class="field-grid">
      <div class="field-item"><div class="field-label">Type</div><div class="field-value">${COMP_LABELS[typeName] || typeName}</div></div>
      <div class="field-item"><div class="field-label">From Bus</div><div class="field-value">${esc(edge.source)}</div></div>
      <div class="field-item"><div class="field-label">To Bus</div><div class="field-value">${esc(edge.target)}</div></div>
      <div class="field-item"><div class="field-label">Status</div><div class="field-value">${edge.is_closed === 'True' ? 'Closed' : edge.is_closed === 'False' ? 'Open' : '—'}</div></div>
    </div></div>`
}

function buildCompPopup(nc: NodeComp) {
  const icon = COMPONENT_ICONS[nc.type] || 'ri-box-3-line'
  return `
    <div class="popup-header">
      <div class="popup-title"><i class="${icon}" style="color:#5b67f5"></i><span>${esc(nc.name)}</span></div>
      <div class="popup-actions">
        <button class="btn-icon popup-edit-btn" data-uuid="${nc.uuid}" data-type="${nc.type}" title="Edit"><i class="ri-edit-line"></i></button>
        <button class="btn-icon danger popup-delete-btn" data-uuid="${nc.uuid}" data-name="${esc(nc.name)}" data-label="${COMP_LABELS[nc.type] || nc.type}" title="Delete"><i class="ri-delete-bin-line"></i></button>
      </div>
    </div>
    <div class="popup-body"><div class="field-grid">
      <div class="field-item"><div class="field-label">Type</div><div class="field-value">${COMP_LABELS[nc.type] || nc.type}</div></div>
      <div class="field-item"><div class="field-label">Bus</div><div class="field-value">${esc(nc.busName)}</div></div>
    </div></div>`
}

function bindPopupActions() {
  document.querySelectorAll('.popup-edit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const uuid = (btn as HTMLElement).dataset.uuid!
      const type = (btn as HTMLElement).dataset.type!
      map?.closePopup()
      openEditModal(uuid, type)
    })
  })
  document.querySelectorAll('.popup-delete-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      map?.closePopup()
      deleteModal.uuid = (btn as HTMLElement).dataset.uuid!
      deleteModal.name = (btn as HTMLElement).dataset.name!
      deleteModal.label = (btn as HTMLElement).dataset.label!
      deleteModal.show = true
    })
  })
}

// ===== Helpers =====
function formatKey(key: string): string {
  return key.replace(/_/g, ' ')
}

function getEnumOpts(enumName?: string): string[] {
  return enumName ? ENUMS[enumName] || [] : []
}

function getQtyVal(val: unknown): string {
  if (val && typeof val === 'object' && 'value' in (val as Record<string, unknown>)) return String((val as { value: number }).value ?? '')
  if (typeof val === 'string' && val.includes(' ')) return val.split(' ')[0]
  if (val !== null && val !== undefined) return String(val)
  return ''
}

function getQtyUnit(val: unknown): string {
  if (val && typeof val === 'object') {
    const obj = val as Record<string, unknown>
    if ('unit' in obj) return String(obj.unit || '')
    if ('units' in obj) return String(obj.units || '')
  }
  if (typeof val === 'string' && val.includes(' ')) return val.split(' ').slice(1).join(' ')
  return ''
}

function setQtyVal(key: string, rawVal: string, defaultUnit?: string) {
  if (!rawVal) { editData[key] = null; return }
  const existing = editData[key] as { value?: number; unit?: string } | null
  editData[key] = { value: parseFloat(rawVal), unit: existing?.unit || defaultUnit || '' }
}

function togglePhase(key: string, phase: string) {
  const arr = (editData[key] as string[]) || []
  const idx = arr.indexOf(phase)
  if (idx >= 0) arr.splice(idx, 1)
  else arr.push(phase)
  editData[key] = [...arr]
}

function getRefName(val: unknown): string {
  if (!val) return ''
  if (typeof val === 'string') return val
  if (typeof val === 'object' && val !== null && 'name' in (val as Record<string, unknown>)) return String((val as { name: string }).name)
  return ''
}

// ===== Edit =====
async function openEditModal(uuid: string, type: string) {
  try {
    const { data: comp } = await equipmentApi.get(uuid)
    editModal.compType = type
    editModal.uuid = uuid
    editModal.isNew = false
    editModal.title = `Edit ${COMP_LABELS[type] || type}`
    // Populate editData from component
    Object.keys(editData).forEach((k) => delete editData[k])
    const schema = COMPONENT_SCHEMAS[type]
    if (schema) {
      for (const key of Object.keys(schema.fields)) {
        editData[key] = comp[key] ?? null
      }
      // Populate bus fields based on busMode
      if (schema.busMode === 'single' && comp.bus) {
        editData._bus = typeof comp.bus === 'object' ? comp.bus.name : comp.bus
      } else if (schema.busMode === 'dual' && comp.buses) {
        const buses = comp.buses as Array<string | { name: string }>
        editData._bus1 = typeof buses[0] === 'object' ? buses[0].name : buses[0] ?? null
        editData._bus2 = typeof buses[1] === 'object' ? buses[1].name : buses[1] ?? null
      }
    } else {
      for (const [k, v] of Object.entries(comp)) {
        if (k !== '_type' && k !== 'uuid') editData[k] = v
      }
    }
    await loadEquipmentOptions(type)
    editModal.show = true
  } catch {
    toast('Failed to load component', 'error')
  }
}

async function saveEdit() {
  try {
    const data: Record<string, unknown> = {}
    for (const [key, val] of Object.entries(editData)) {
      if (key.startsWith('_')) continue
      data[key] = val
    }

    // Include bus references
    const schema = COMPONENT_SCHEMAS[editModal.compType]
    if (schema?.busMode === 'single' && editData._bus) {
      data.bus = editData._bus
    } else if (schema?.busMode === 'dual') {
      if (!editData._bus1 || !editData._bus2) {
        toast('Select both buses', 'error'); return
      }
      if (editData._bus1 === editData._bus2) {
        toast('Buses must be different', 'error'); return
      }
      data.buses = [editData._bus1, editData._bus2]
    }

    if (editModal.isNew) {
      if (editModal.compType === 'DistributionBus' && editData._lat) {
        data.coordinate = { x: parseFloat(String(editData._lng)), y: parseFloat(String(editData._lat)) }
      }
      await equipmentApi.add(editModal.compType, data)
      toast(`${COMP_LABELS[editModal.compType] || editModal.compType} added`, 'success')
    } else {
      await equipmentApi.update(editModal.uuid, data)
      toast(`${COMP_LABELS[editModal.compType] || editModal.compType} updated`, 'success')
    }
    editModal.show = false
    await loadTopology()
  } catch (e: any) {
    toast(e.response?.data?.detail || 'Save failed', 'error')
  }
}

// ===== Delete =====
async function confirmDelete() {
  try {
    await equipmentApi.remove(deleteModal.uuid)
    toast(`${deleteModal.label} deleted`, 'success')
    deleteModal.show = false
    await loadTopology()
  } catch (e: any) {
    toast(e.response?.data?.detail || 'Delete failed', 'error')
  }
}

// ===== Drag & Drop =====
function onDragStart(e: DragEvent, compType: string) {
  e.dataTransfer!.setData('text/plain', compType)
  e.dataTransfer!.effectAllowed = 'copy'
}

function onMapDrop(e: DragEvent) {
  e.preventDefault()
  const compType = e.dataTransfer?.getData('text/plain')
  if (!compType || !map) return

  const rect = mapContainer.value!.getBoundingClientRect()
  const latlng = map.containerPointToLatLng(L.point(e.clientX - rect.left, e.clientY - rect.top))

  if (compType === 'DistributionBus') {
    openNewBusModal(latlng.lat, latlng.lng)
    return
  }

  const nearest = findNearestBus(latlng)
  if (nearest) {
    openNewComponentModal(compType, nearest.name)
  } else {
    toast('Drop on a bus to connect this component', 'info')
  }
}

function handleBusDrop(compType: string, busName: string) {
  if (compType === 'DistributionBus') {
    toast('Buses can only be placed on empty map space', 'info')
    return
  }
  openNewComponentModal(compType, busName)
}

function findNearestBus(latlng: L.LatLng): BusLoc | null {
  let nearest: BusLoc | null = null
  let minDist = Infinity
  for (const bus of busLookup.values()) {
    const d = latlng.distanceTo(L.latLng(bus.lat, bus.lng))
    if (d < minDist) { minDist = d; nearest = bus }
  }
  return minDist < 500 ? nearest : null
}

function openNewBusModal(lat: number, lng: number) {
  editModal.compType = 'DistributionBus'
  editModal.uuid = ''
  editModal.isNew = true
  editModal.busInfo = ''
  editModal.title = 'Add Distribution Bus'
  Object.keys(editData).forEach((k) => delete editData[k])
  editData.name = `bus_new_${Date.now() % 10000}`
  editData.voltage_type = 'line-to-ground'
  editData.phases = ['A', 'B', 'C']
  editData.rated_voltage = { value: 12470, unit: 'V' }
  editData._lat = String(lat)
  editData._lng = String(lng)
  editModal.show = true
}

function openNewComponentModal(compType: string, busName: string) {
  editModal.compType = compType
  editModal.uuid = ''
  editModal.isNew = true
  editModal.title = `Add ${COMP_LABELS[compType] || compType}`
  Object.keys(editData).forEach((k) => delete editData[k])
  const schema = COMPONENT_SCHEMAS[compType]
  if (schema) {
    for (const [key, fd] of Object.entries(schema.fields)) {
      editData[key] = fd.default ?? null
    }
    // Populate bus fields based on busMode
    if (schema.busMode === 'single') {
      editData._bus = busName
    } else if (schema.busMode === 'dual') {
      editData._bus1 = busName
      editData._bus2 = null
    }
  }
  editData.name = `${compType.replace('Distribution', '').replace('MatrixImpedance', '').toLowerCase()}_${busName}`
  editData.phases = ['A', 'B', 'C']
  loadEquipmentOptions(compType)
  editModal.show = true
}

// ===== Render =====
function renderTopology(topology: Topology, buses: GDMComponent[]) {
  if (!map) return
  clearLayers()
  busLookup = new Map<string, BusLoc>()

  for (const bus of buses) {
    const coord = bus.coordinate as { x?: number; y?: number } | undefined
    if (coord?.x != null && coord?.y != null) {
      busLookup.set(bus.name, {
        lat: coord.y, lng: coord.x, name: bus.name, uuid: bus.uuid,
        phases: bus.phases as string[] || [],
        voltageType: bus.voltage_type as string || '',
        ratedVoltage: bus.rated_voltage as string || '',
      })
    }
  }

  const busAttachments = new Map<string, NodeComp[]>()
  for (const nc of nodeComponents) {
    const list = busAttachments.get(nc.busName) || []
    list.push(nc)
    busAttachments.set(nc.busName, list)
  }

  const boundsArr: L.LatLng[] = []

  // Bus markers
  for (const [name, loc] of busLookup) {
    const attached = busAttachments.get(name) || []
    const hasSource = attached.some(c => c.type === 'DistributionVoltageSource')
    const hasSolar = attached.some(c => c.type === 'DistributionSolar')
    const hasLoad = attached.some(c => c.type === 'DistributionLoad')

    let extraClass = ''
    if (hasSource) extraClass = ' source'
    else if (hasSolar) extraClass = ' has-solar'
    else if (hasLoad) extraClass = ' has-load'

    const busIcon = L.divIcon({ className: `bus-marker${extraClass}`, iconSize: [14, 14] })
    const marker = L.marker([loc.lat, loc.lng], { icon: busIcon })
    marker.bindPopup(buildBusPopup(loc, attached), {
      className: 'network-popup', closeButton: false, maxWidth: 360, minWidth: 260,
    })
    marker.on('popupopen', () => setTimeout(bindPopupActions, 50))

    // Make bus a drop target
    marker.on('add', () => {
      const el = marker.getElement()
      if (!el) return
      el.addEventListener('dragover', (ev) => { ev.preventDefault(); el.classList.add('drop-target') })
      el.addEventListener('dragleave', () => el.classList.remove('drop-target'))
      el.addEventListener('drop', (ev) => {
        ev.preventDefault(); ev.stopPropagation()
        el.classList.remove('drop-target')
        const ct = ev.dataTransfer?.getData('text/plain')
        if (ct) handleBusDrop(ct, name)
      })
    })

    marker.addTo(map)
    layers.push(marker)
    boundsArr.push(L.latLng(loc.lat, loc.lng))

    if (showLabels.value) {
      const label = L.marker([loc.lat, loc.lng], {
        icon: L.divIcon({ className: 'bus-label', html: name, iconAnchor: [-10, 6] }),
        interactive: false,
      })
      label.addTo(map)
      labelLayers.push(label)
    }
  }

  // Equipment component markers
  for (const nc of nodeComponents) {
    const bus = busLookup.get(nc.busName)
    if (!bus) continue
    const siblings = busAttachments.get(nc.busName) || []
    const idx = siblings.indexOf(nc)
    const total = siblings.length
    const angle = (idx / Math.max(total, 1)) * Math.PI * 2 - Math.PI / 2
    const offsetDist = 0.0004
    const lat = bus.lat + Math.sin(angle) * offsetDist
    const lng = bus.lng + Math.cos(angle) * offsetDist

    let markerClass = 'component-marker'
    if (nc.type === 'DistributionLoad') markerClass += ' load'
    else if (nc.type === 'DistributionSolar') markerClass += ' solar'
    else if (nc.type === 'DistributionBattery') markerClass += ' battery'
    else if (nc.type === 'DistributionCapacitor') markerClass += ' capacitor'
    else if (nc.type === 'DistributionVoltageSource') markerClass += ' source'

    const compIcon = L.divIcon({
      className: markerClass,
      html: `<i class="${COMPONENT_ICONS[nc.type] || 'ri-box-3-line'}"></i>`,
      iconSize: [22, 22],
    })
    const compMarker = L.marker([lat, lng], { icon: compIcon })
    compMarker.bindPopup(buildCompPopup(nc), {
      className: 'network-popup', closeButton: false, maxWidth: 360, minWidth: 220,
    })
    compMarker.on('popupopen', () => setTimeout(bindPopupActions, 50))

    const connLine = L.polyline([[bus.lat, bus.lng], [lat, lng]], { color: '#3a3e52', weight: 1, opacity: 0.5, dashArray: '3, 3' })

    if (showIcons.value) {
      compMarker.addTo(map)
      connLine.addTo(map)
    }
    layers.push(compMarker)
    iconLayers.push(compMarker)
    layers.push(connLine)
    iconLayers.push(connLine)
  }

  // Edges
  for (const edge of topology.edges) {
    const src = busLookup.get(edge.source)
    const tgt = busLookup.get(edge.target)
    if (!src || !tgt) continue

    const typeName = edge.type?.replace(/<class '.*\.(.*)'>/,'$1') || ''
    const isSwitch = typeName.includes('Switch') || typeName.includes('Fuse') || typeName.includes('Recloser')
    const isTransformer = typeName.includes('Transformer') || typeName.includes('Regulator')

    let color = '#6fcf6f', weight = 3
    let dashArray: string | undefined
    if (isTransformer) { color = '#f0a030'; weight = 4 }
    else if (isSwitch) { color = '#e54d4d' }
    if (isSwitch && edge.is_closed === 'False') dashArray = '8, 6'

    const line = L.polyline([[src.lat, src.lng], [tgt.lat, tgt.lng]], { color, weight, opacity: 0.8, dashArray })
    line.bindPopup(buildEdgePopup(edge), { className: 'network-popup', closeButton: false, maxWidth: 360, minWidth: 260 })
    line.on('popupopen', () => setTimeout(bindPopupActions, 50))
    line.bindTooltip(`<strong>${esc(edge.name || '')}</strong><br>${COMP_LABELS[typeName] || typeName}`, { sticky: true, className: 'bus-label' })
    line.addTo(map)
    layers.push(line)
  }

  if (boundsArr.length > 0) {
    map.invalidateSize()
    map.fitBounds(L.latLngBounds(boundsArr), { padding: [40, 40] })
  }
}

function clearLayers() {
  layers.forEach((l) => map?.removeLayer(l))
  layers.length = 0
  labelLayers.forEach((l) => map?.removeLayer(l))
  labelLayers.length = 0
  iconLayers.length = 0
}

function fitBounds() {
  if (!map || layers.length === 0) return
  const group = L.featureGroup(layers)
  map.fitBounds(group.getBounds(), { padding: [40, 40] })
}

watch(showLabels, () => {
  if (!map) return
  if (showLabels.value) loadTopology()
  else { labelLayers.forEach((l) => map?.removeLayer(l)); labelLayers.length = 0 }
})

watch(showIcons, () => {
  if (!map) return
  if (showIcons.value) {
    iconLayers.forEach((l) => l.addTo(map!))
  } else {
    iconLayers.forEach((l) => map?.removeLayer(l))
  }
})

onMounted(async () => {
  await nextTick()
  initMap()
  map?.invalidateSize()
  await loadTopology()
  map?.invalidateSize()
})

onUnmounted(() => {
  if (map) { map.remove(); map = null }
})
</script>
