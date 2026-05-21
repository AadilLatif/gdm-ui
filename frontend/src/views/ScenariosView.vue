<template>
  <div class="page-scenarios">
    <div class="scenario-container">
      <div class="scenario-map-wrap">
        <div id="scenarioMap" ref="scenarioMapContainer"></div>
        <div class="scenario-map-toolbar">
          <button class="map-tool-btn" title="Fit to bounds" @click="fitBounds">
            <i class="ri-fullscreen-line"></i>
          </button>
          <button class="map-tool-btn" :class="{ active: showLabels }" title="Toggle labels" @click="toggleLabels">
            <i class="ri-price-tag-3-line"></i>
          </button>
          <div class="map-legend">
            <span class="legend-item"><span class="legend-dot" style="background:#555a6e"></span>Base</span>
            <span class="legend-item"><span class="legend-dot" style="background:#4ade80"></span>Added</span>
            <span class="legend-item"><span class="legend-dot" style="background:#f87171"></span>Deleted</span>
            <span class="legend-item"><span class="legend-dot" style="background:#fbbf24"></span>Edited</span>
          </div>
        </div>

        <!-- Empty state -->
        <div v-if="!timelineLoaded" class="scenario-empty-state">
          <i class="ri-time-line"></i>
          <h3>No scenario loaded</h3>
          <p>Upload a tracked changes zip file to visualize network evolution.</p>
          <button class="btn btn-outline" @click="triggerUpload">
            <i class="ri-upload-2-line"></i> Upload Scenario Zip
          </button>
          <input ref="fileInput" type="file" accept=".zip" hidden @change="handleUpload" />
        </div>
      </div>

      <!-- Scenario selector toolbar (top) -->
      <div v-if="scenarioFiles.length > 0 || timelineLoaded" class="scenario-selector-bar">
        <div class="selector-group">
          <label class="selector-label">File</label>
          <select class="form-select compact" v-model="selectedFile" @change="onFileChange">
            <option value="">— Select —</option>
            <option v-for="f in scenarioFiles" :key="f.filename" :value="f.filename">{{ f.filename }}</option>
          </select>
        </div>
        <div class="selector-group">
          <label class="selector-label">Scenario</label>
          <select class="form-select compact" v-model="selectedScenario" @change="loadTimeline">
            <option value="">— Select —</option>
            <option v-for="s in currentScenarioNames" :key="s" :value="s">{{ s }}</option>
          </select>
        </div>
        <button class="btn btn-outline btn-sm" @click="triggerUpload" title="Upload another scenario">
          <i class="ri-upload-2-line"></i>
        </button>
        <input ref="fileInput" type="file" accept=".zip" hidden @change="handleUpload" />
      </div>

      <!-- Timeline bar -->
      <div v-if="timelineLoaded" class="timeline-bar">
        <div class="timeline-controls">
          <button class="timeline-btn" @click="prevStep"><i class="ri-skip-back-mini-fill"></i></button>
          <button class="timeline-btn" :class="{ active: playing }" @click="togglePlay">
            <i :class="playing ? 'ri-pause-fill' : 'ri-play-fill'"></i>
          </button>
          <button class="timeline-btn" @click="nextStep"><i class="ri-skip-forward-mini-fill"></i></button>
        </div>
        <div class="timeline-slider-wrap">
          <input
            type="range"
            class="timeline-slider"
            :min="0"
            :max="steps.length"
            :value="currentStep"
            @input="currentStep = Number(($event.target as HTMLInputElement).value)"
          />
          <div class="timeline-ticks">
            <span
              v-for="(step, i) in [{name:'Base'},...steps]"
              :key="i"
              class="timeline-tick"
              :class="{ active: i <= currentStep }"
            >{{ i === 0 ? 'Base' : formatDate(steps[i-1].timestamp) }}</span>
          </div>
        </div>
        <div class="timeline-info">
          <span class="timeline-date">{{ currentStepLabel }}</span>
          <span class="timeline-scenario">{{ selectedScenario }}</span>
        </div>
        <div class="timeline-stats">
          <span class="stat-badge stat-add"><i class="ri-add-line"></i> {{ cumulativeAdded }}</span>
          <span class="stat-badge stat-del"><i class="ri-subtract-line"></i> {{ cumulativeDeleted }}</span>
          <span class="stat-badge stat-edit"><i class="ri-edit-line"></i> {{ cumulativeEdited }}</span>
        </div>
      </div>

      <!-- Change log panel -->
      <div v-if="timelineLoaded" class="scenario-side-panel">
        <div class="panel-section">
          <div class="panel-header">
            <h3>Change Log</h3>
            <span class="panel-hint">{{ filteredChangeLog.length }} / {{ changeLogItems.length }}</span>
          </div>
          <div class="panel-search">
            <i class="ri-search-line"></i>
            <input
              v-model="changeLogSearch"
              type="text"
              class="panel-search-input"
              placeholder="Filter changes…"
            />
          </div>
          <div class="change-log-list">
            <div
              v-for="(item, i) in filteredChangeLog"
              :key="i"
              :class="['change-log-item', item.kind]"
            >
              <div class="change-icon">
                <i :class="item.icon"></i>
              </div>
              <div class="change-detail">
                <span class="change-name">{{ item.name }}</span>
                <span class="change-type">{{ item.label }} · {{ item.type }} · {{ item.date }}</span>
              </div>
            </div>
            <div v-if="filteredChangeLog.length === 0 && changeLogItems.length > 0" class="change-log-empty">
              No matches
            </div>
            <div v-if="changeLogItems.length === 0" class="change-log-empty">
              No changes at base state
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import L from 'leaflet'
import { scenariosApi, networkApi, systemApi } from '../api/client'
import type { ScenarioFile, ScenarioTimeline, ScenarioTimelineStep } from '../api/client'
import type { GDMComponent } from '../types/api'
import { COMPONENT_ICONS } from '../types/schemas'
import { useToast } from '../composables/useToast'

const { toast } = useToast()
const scenarioMapContainer = ref<HTMLElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

// Scenario state
const scenarioFiles = ref<ScenarioFile[]>([])
const selectedFile = ref('')
const selectedScenario = ref('')
const steps = ref<ScenarioTimelineStep[]>([])
const timelineLoaded = ref(false)
const currentStep = ref(0)
const playing = ref(false)
let playInterval: ReturnType<typeof setInterval> | null = null

// Map state
let sMap: L.Map | null = null
const mapLayers: L.Layer[] = []
const showLabels = ref(false)

// Base network state (from main system)
interface BusInfo { name: string; lat: number; lng: number; uuid: string }
const baseBuses = ref<BusInfo[]>([])
interface EdgeInfo { name: string; uuid: string; type: string; bus1: string; bus2: string }
const baseEdges = ref<EdgeInfo[]>([])
interface NodeInfo { name: string; uuid: string; type: string; busName: string }
const baseNodes = ref<NodeInfo[]>([])

const currentScenarioNames = computed(() => {
  const f = scenarioFiles.value.find(sf => sf.filename === selectedFile.value)
  return f?.scenario_names || []
})

const currentStepLabel = computed(() => {
  if (currentStep.value === 0) return 'Base System'
  const step = steps.value[currentStep.value - 1]
  if (!step?.timestamp) return step?.name || ''
  const d = new Date(step.timestamp)
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
})

// Cumulative stats
const cumulativeAdded = computed(() => {
  let n = 0
  for (let i = 0; i < currentStep.value; i++) n += steps.value[i].additions.length
  return n
})
const cumulativeDeleted = computed(() => {
  let n = 0
  for (let i = 0; i < currentStep.value; i++) n += steps.value[i].deletions.length
  return n
})
const cumulativeEdited = computed(() => {
  let n = 0
  for (let i = 0; i < currentStep.value; i++) n += steps.value[i].edits.length
  return n
})

const changeLogSearch = ref('')

interface ChangeLogItem { kind: string; icon: string; name: string; label: string; type: string; date: string }

const changeLogItems = computed<ChangeLogItem[]>(() => {
  const items: ChangeLogItem[] = []
  for (let i = 0; i < currentStep.value; i++) {
    const step = steps.value[i]
    const date = formatDate(step.timestamp)
    for (const a of step.additions) {
      items.push({ kind: 'addition', icon: 'ri-add-line', name: a.name, label: 'Added', type: a.type, date })
    }
    for (const d of step.deletions) {
      items.push({ kind: 'deletion', icon: 'ri-subtract-line', name: d.name, label: 'Removed', type: d.type, date })
    }
    for (const e of step.edits) {
      items.push({ kind: 'edit', icon: 'ri-edit-line', name: e.component_name, label: 'Edited', type: e.field, date })
    }
  }
  return items.reverse()
})

const filteredChangeLog = computed(() => {
  const q = changeLogSearch.value.trim().toLowerCase()
  if (!q) return changeLogItems.value
  return changeLogItems.value.filter(item =>
    item.name.toLowerCase().includes(q) ||
    item.type.toLowerCase().includes(q) ||
    item.label.toLowerCase().includes(q) ||
    item.kind.toLowerCase().includes(q)
  )
})

function formatDate(ts: string | null): string {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

// ===== File management =====
function triggerUpload() { fileInput.value?.click() }

async function handleUpload(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const { data } = await scenariosApi.upload(file)
    toast(`Loaded ${data.total_changes} tracked changes`, 'success')
    await refreshFiles()
    selectedFile.value = data.filename
    if (data.scenario_names.length === 1) {
      selectedScenario.value = data.scenario_names[0]
      await loadTimeline()
    }
  } catch (err: any) {
    toast(err.response?.data?.detail || 'Upload failed', 'error')
  }
  input.value = ''
}

async function refreshFiles() {
  try {
    const { data } = await scenariosApi.list()
    scenarioFiles.value = data
  } catch { /* no scenarios */ }
}

function onFileChange() {
  selectedScenario.value = ''
  timelineLoaded.value = false
  steps.value = []
  currentStep.value = 0
}

async function loadTimeline() {
  if (!selectedFile.value || !selectedScenario.value) return
  try {
    const { data } = await scenariosApi.timeline(selectedFile.value, selectedScenario.value)
    steps.value = data.steps
    currentStep.value = 0
    timelineLoaded.value = true
    await loadBaseNetwork()
    renderMap()
  } catch (err: any) {
    toast(err.response?.data?.detail || 'Failed to load timeline', 'error')
  }
}

// ===== Base network (from topology + system APIs — matches NetworkView) =====
async function loadBaseNetwork() {
  try {
    const [topoRes, busesRes, loadsRes, sourcesRes, solarRes, batteryRes] = await Promise.all([
      networkApi.topology(),
      systemApi.components('DistributionBus'),
      systemApi.components('DistributionLoad'),
      systemApi.components('DistributionVoltageSource'),
      systemApi.components('DistributionSolar').catch(() => ({ data: [] as GDMComponent[] })),
      systemApi.components('DistributionBattery').catch(() => ({ data: [] as GDMComponent[] })),
    ])

    // Parse buses from system API (has coordinates)
    const buses: BusInfo[] = []
    for (const bus of busesRes.data) {
      const coord = bus.coordinate as { x?: number; y?: number } | undefined
      if (coord?.x != null && coord?.y != null) {
        buses.push({ name: bus.name, lat: coord.y, lng: coord.x, uuid: bus.uuid })
      }
    }
    baseBuses.value = buses

    // Parse edges from topology API
    const parsedEdges: EdgeInfo[] = []
    for (const e of topoRes.data.edges) {
      const typeName = (e.type || '').replace(/<class '.*\.(.*)'>/,'$1')
      parsedEdges.push({
        name: e.name || '',
        uuid: e.uuid || '',
        type: typeName,
        bus1: e.source || '',
        bus2: e.target || '',
      })
    }
    baseEdges.value = parsedEdges

    // Parse node components (loads, sources, solar, battery)
    const nodeComps: NodeInfo[] = []
    const extractBusName = (comp: GDMComponent) => {
      const bus = comp.bus as { name?: string } | string | undefined
      return typeof bus === 'object' ? bus?.name : bus
    }
    for (const load of loadsRes.data) {
      const busName = extractBusName(load)
      if (busName) nodeComps.push({ name: load.name, uuid: load.uuid, type: 'DistributionLoad', busName })
    }
    for (const src of sourcesRes.data) {
      const busName = extractBusName(src)
      if (busName) nodeComps.push({ name: src.name, uuid: src.uuid, type: 'DistributionVoltageSource', busName })
    }
    for (const sol of solarRes.data) {
      const busName = extractBusName(sol)
      if (busName) nodeComps.push({ name: sol.name, uuid: sol.uuid, type: 'DistributionSolar', busName })
    }
    for (const bat of batteryRes.data) {
      const busName = extractBusName(bat)
      if (busName) nodeComps.push({ name: bat.name, uuid: bat.uuid, type: 'DistributionBattery', busName })
    }
    baseNodes.value = nodeComps
  } catch { /* ok */ }
}

// ===== Timeline controls =====
function prevStep() { if (currentStep.value > 0) currentStep.value-- }
function nextStep() { if (currentStep.value < steps.value.length) currentStep.value++ }

function togglePlay() {
  playing.value = !playing.value
  if (playing.value) {
    playInterval = setInterval(() => {
      if (currentStep.value < steps.value.length) {
        currentStep.value++
      } else {
        playing.value = false
        if (playInterval) clearInterval(playInterval)
      }
    }, 1500)
  } else {
    if (playInterval) clearInterval(playInterval)
  }
}

function toggleLabels() {
  showLabels.value = !showLabels.value
  renderMap()
}

// ===== Map =====
function initMap() {
  if (!scenarioMapContainer.value || sMap) return
  sMap = L.map(scenarioMapContainer.value, {
    center: [38.64, -122.51],
    zoom: 14,
    zoomControl: false,
    attributionControl: false,
  })
  L.control.zoom({ position: 'bottomleft' }).addTo(sMap)
  L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
    maxZoom: 20,
    attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>',
  }).addTo(sMap)
}

function clearMap() {
  mapLayers.forEach(l => sMap?.removeLayer(l))
  mapLayers.length = 0
}

function fitBounds() {
  if (!sMap || mapLayers.length === 0) return
  const group = L.featureGroup(mapLayers)
  sMap.fitBounds(group.getBounds(), { padding: [40, 40] })
}

function renderMap() {
  if (!sMap) return
  clearMap()

  // Compute cumulative state
  const addedUUIDs = new Set<string>()
  const deletedUUIDs = new Set<string>()
  const editedUUIDs = new Set<string>()

  for (let i = 0; i < currentStep.value; i++) {
    const step = steps.value[i]
    for (const a of step.additions) addedUUIDs.add(a.uuid)
    for (const d of step.deletions) deletedUUIDs.add(d.uuid)
    for (const e of step.edits) editedUUIDs.add(e.component_uuid)
  }

  // Collect added buses and edges from steps
  const addedBuses: BusInfo[] = []
  const addedEdgesResolved: EdgeInfo[] = []
  const addedNodes: Array<{ name: string; uuid: string; type: string; busName: string }> = []

  for (let i = 0; i < currentStep.value; i++) {
    for (const a of steps.value[i].additions) {
      if (a.type === 'DistributionBus' && a.coordinate) {
        addedBuses.push({ name: a.name, lat: a.coordinate.y, lng: a.coordinate.x, uuid: a.uuid })
      } else if (a.type.includes('Branch') || a.type.includes('Transformer') || a.type.includes('Switch') || a.type.includes('Fuse') || a.type.includes('Recloser')) {
        addedEdgesResolved.push({ name: a.name, uuid: a.uuid, type: a.type, bus1: a.bus1 || '', bus2: a.bus2 || '' })
      } else if (a.bus) {
        addedNodes.push({ name: a.name, uuid: a.uuid, type: a.type, busName: a.bus })
      }
    }
  }

  // Build combined bus lookup
  const busLookup = new Map<string, BusInfo>()
  for (const b of baseBuses.value) busLookup.set(b.name, b)
  for (const b of addedBuses) busLookup.set(b.name, b)

  // Compute bus attachments for ALL node components (base + added)
  const allNodeComps = [
    ...baseNodes.value.map(n => ({ ...n, isBase: true })),
    ...addedNodes.map(n => ({ ...n, isBase: false })),
  ]
  const busAttachments = new Map<string, Array<{ name: string; type: string; uuid: string; isBase: boolean }>>()
  for (const nc of allNodeComps) {
    if (deletedUUIDs.has(nc.uuid)) continue
    const arr = busAttachments.get(nc.busName) || []
    arr.push(nc)
    busAttachments.set(nc.busName, arr)
  }

  // Draw edges
  const allEdges = [...baseEdges.value, ...addedEdgesResolved]
  for (const edge of allEdges) {
    if (deletedUUIDs.has(edge.uuid)) {
      // Deleted edge: faded red dashed
      const b1 = busLookup.get(edge.bus1), b2 = busLookup.get(edge.bus2)
      if (b1 && b2) {
        const line = L.polyline([[b1.lat, b1.lng], [b2.lat, b2.lng]], {
          color: '#f87171', weight: 2, opacity: 0.3, dashArray: '6, 8',
        })
        line.bindTooltip(`<strong>${edge.name}</strong><br><em>Deleted</em>`, { sticky: true })
        line.addTo(sMap)
        mapLayers.push(line)
      }
      continue
    }

    const b1 = busLookup.get(edge.bus1), b2 = busLookup.get(edge.bus2)
    if (!b1 || !b2) continue

    const isAdded = addedUUIDs.has(edge.uuid)
    const isEdited = editedUUIDs.has(edge.uuid)
    const isBase = !isAdded && !isEdited

    let color = '#555a6e'  // grey for base
    let weight = 2
    let opacity = 0.45
    if (isAdded) { color = '#4ade80'; weight = 4; opacity = 0.9 }
    else if (isEdited) { color = '#fbbf24'; weight = 4; opacity = 0.9 }

    const line = L.polyline([[b1.lat, b1.lng], [b2.lat, b2.lng]], { color, weight, opacity })
    let extra = ''
    if (isAdded) extra = '<br><em style="color:#4ade80">+ Added</em>'
    else if (isEdited) extra = '<br><em style="color:#fbbf24">~ Edited</em>'
    line.bindTooltip(`<strong>${edge.name}</strong>${extra}`, { sticky: true })
    line.addTo(sMap)
    mapLayers.push(line)
  }

  // Draw bus markers
  const boundsArr: L.LatLng[] = []
  for (const bus of busLookup.values()) {
    if (deletedUUIDs.has(bus.uuid)) continue
    const isAdded = addedUUIDs.has(bus.uuid)
    const isEdited = editedUUIDs.has(bus.uuid)

    let cls = 'bus-marker'
    if (isAdded) cls += ' scenario-added'
    else if (isEdited) cls += ' scenario-edited'
    else cls += ' scenario-base'

    const icon = L.divIcon({ className: cls, iconSize: [14, 14] })
    const marker = L.marker([bus.lat, bus.lng], { icon })
    let extra = ''
    if (isAdded) extra = '<br><em style="color:#4ade80">+ Added</em>'
    else if (isEdited) extra = '<br><em style="color:#fbbf24">~ Edited</em>'
    marker.bindTooltip(`<strong>${bus.name}</strong>${extra}`, { sticky: true })
    marker.addTo(sMap)
    mapLayers.push(marker)
    boundsArr.push(L.latLng(bus.lat, bus.lng))

    if (showLabels.value) {
      const label = L.marker([bus.lat, bus.lng], {
        icon: L.divIcon({ className: 'bus-label', html: bus.name, iconAnchor: [-10, 6] }),
        interactive: false,
      })
      label.addTo(sMap)
      mapLayers.push(label)
    }
  }

  // Draw ALL node components (base + scenario added)
  for (const nc of allNodeComps) {
    if (deletedUUIDs.has(nc.uuid)) continue
    const bus = busLookup.get(nc.busName)
    if (!bus) continue

    const siblings = busAttachments.get(nc.busName) || []
    const idx = siblings.findIndex(s => s.uuid === nc.uuid)
    const total = siblings.length
    const angle = (idx / Math.max(total, 1)) * Math.PI * 2 - Math.PI / 2
    const offsetDist = 0.0004
    const lat = bus.lat + Math.sin(angle) * offsetDist
    const lng = bus.lng + Math.cos(angle) * offsetDist

    const isAdded = addedUUIDs.has(nc.uuid)
    const isEdited = editedUUIDs.has(nc.uuid)

    let markerCls = 'component-marker'
    if (nc.type === 'DistributionLoad') markerCls += ' load'
    else if (nc.type === 'DistributionSolar') markerCls += ' solar'
    else if (nc.type === 'DistributionBattery') markerCls += ' battery'
    else if (nc.type === 'DistributionCapacitor') markerCls += ' capacitor'
    else if (nc.type === 'DistributionVoltageSource') markerCls += ' source'
    if (isAdded) markerCls += ' scenario-added'
    else if (isEdited) markerCls += ' scenario-edited'
    else markerCls += ' scenario-base'

    const compIcon = L.divIcon({
      className: markerCls,
      html: `<i class="${COMPONENT_ICONS[nc.type] || 'ri-box-3-line'}"></i>`,
      iconSize: [22, 22],
    })
    const compMarker = L.marker([lat, lng], { icon: compIcon })

    let tooltipExtra = ''
    if (isAdded) tooltipExtra = '<br><em style="color:#4ade80">+ Added</em>'
    else if (isEdited) tooltipExtra = '<br><em style="color:#fbbf24">~ Edited</em>'
    compMarker.bindTooltip(`<strong>${nc.name}</strong>${tooltipExtra}`, { sticky: true })
    compMarker.addTo(sMap)
    mapLayers.push(compMarker)

    const connColor = isAdded ? '#4ade80' : '#3a3e52'
    const conn = L.polyline([[bus.lat, bus.lng], [lat, lng]], { color: connColor, weight: 1, opacity: isAdded ? 0.6 : 0.3, dashArray: '3, 3' })
    conn.addTo(sMap)
    mapLayers.push(conn)
  }

  // Fit bounds
  if (boundsArr.length > 0 && currentStep.value === 0) {
    sMap.fitBounds(L.latLngBounds(boundsArr), { padding: [40, 40] })
  }
}

watch(currentStep, () => { renderMap() })

onMounted(async () => {
  await nextTick()
  initMap()
  await refreshFiles()
})

onUnmounted(() => {
  if (playInterval) clearInterval(playInterval)
  if (sMap) { sMap.remove(); sMap = null }
})
</script>

<style scoped>
.page-scenarios {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.scenario-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}
.scenario-map-wrap {
  flex: 1;
  position: relative;
  min-height: 0;
}
#scenarioMap {
  width: 100%;
  height: 100%;
}
.scenario-map-toolbar {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 800;
  display: flex;
  gap: 6px;
  align-items: center;
}
.scenario-empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(26, 28, 38, 0.85);
  z-index: 600;
  color: #9ca0b4;
}
.scenario-empty-state i {
  font-size: 3rem;
  margin-bottom: 12px;
  color: #5b67f5;
}
.scenario-empty-state h3 {
  color: #e0e2ed;
  margin: 0 0 6px;
}
.scenario-empty-state p {
  margin: 0 0 16px;
  font-size: 0.85rem;
}

/* Selector bar */
.scenario-selector-bar {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 800;
  display: flex;
  gap: 10px;
  align-items: center;
  background: rgba(26, 28, 38, 0.92);
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #2a2d3a;
}
.selector-group {
  display: flex;
  align-items: center;
  gap: 6px;
}
.selector-label {
  font-size: 0.75rem;
  color: #6b6f82;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.form-select.compact {
  padding: 4px 8px;
  font-size: 0.8rem;
  min-width: 140px;
}
.btn-sm {
  padding: 4px 10px;
  font-size: 0.8rem;
}

/* Timeline bar */
.timeline-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #1a1c26;
  border-top: 1px solid #2a2d3a;
}
.timeline-controls {
  display: flex;
  gap: 4px;
}
.timeline-btn {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  border: 1px solid #2a2d3a;
  background: #22242e;
  color: #9ca0b4;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.timeline-btn:hover { background: #2a2d3a; color: #e0e2ed; }
.timeline-btn.active { background: #5b67f5; color: #fff; border-color: #5b67f5; }
.timeline-slider-wrap {
  flex: 1;
  min-width: 0;
}
.timeline-slider {
  width: 100%;
  height: 4px;
  accent-color: #5b67f5;
}
.timeline-ticks {
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: #4a4e65;
  margin-top: 2px;
  overflow: hidden;
}
.timeline-tick {
  white-space: nowrap;
}
.timeline-tick.active {
  color: #5b67f5;
}
.timeline-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 120px;
}
.timeline-date {
  font-size: 0.8rem;
  color: #e0e2ed;
  font-weight: 500;
}
.timeline-scenario {
  font-size: 0.7rem;
  color: #6b6f82;
}
.timeline-stats {
  display: flex;
  gap: 8px;
}
.stat-badge {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 0.75rem;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.stat-add { background: rgba(74, 222, 128, 0.1); color: #4ade80; }
.stat-del { background: rgba(248, 113, 113, 0.1); color: #f87171; }
.stat-edit { background: rgba(251, 191, 36, 0.1); color: #fbbf24; }

/* Side panel */
.scenario-side-panel {
  position: absolute;
  top: 60px;
  right: 12px;
  bottom: 60px;
  width: 280px;
  z-index: 700;
  background: rgba(26, 28, 38, 0.95);
  border-radius: 10px;
  border: 1px solid #2a2d3a;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.panel-section {
  padding: 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.panel-header h3 {
  margin: 0;
  font-size: 0.85rem;
  color: #e0e2ed;
}
.panel-hint {
  font-size: 0.72rem;
  color: #6b6f82;
}
.panel-search {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  background: #22242e;
  border: 1px solid #2a2d3a;
  border-radius: 6px;
  padding: 5px 8px;
}
.panel-search i {
  color: #6b6f82;
  font-size: 0.8rem;
  flex-shrink: 0;
}
.panel-search-input {
  background: transparent;
  border: none;
  outline: none;
  color: #e0e2ed;
  font-size: 0.78rem;
  width: 100%;
}
.panel-search-input::placeholder {
  color: #4a4e65;
}
.change-log-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.change-log-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 8px;
  border-radius: 6px;
  border-left: 3px solid transparent;
  background: #22242e;
}
.change-log-item.addition { border-left-color: #4ade80; }
.change-log-item.deletion { border-left-color: #f87171; }
.change-log-item.edit { border-left-color: #fbbf24; }
.change-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
}
.change-log-item.addition .change-icon { color: #4ade80; }
.change-log-item.deletion .change-icon { color: #f87171; }
.change-log-item.edit .change-icon { color: #fbbf24; }
.change-detail {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.change-name {
  font-size: 0.78rem;
  color: #e0e2ed;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.change-type {
  font-size: 0.68rem;
  color: #6b6f82;
}
.change-log-empty {
  padding: 12px;
  color: #6b6f82;
  font-size: 0.8rem;
  text-align: center;
}

/* Scenario markers */
:deep(.scenario-added) {
  border: 2px solid #4ade80 !important;
  box-shadow: 0 0 6px rgba(74, 222, 128, 0.4);
}
:deep(.scenario-edited) {
  border: 2px solid #fbbf24 !important;
  box-shadow: 0 0 6px rgba(251, 191, 36, 0.4);
}
:deep(.scenario-base.bus-marker) {
  background: #555a6e !important;
  border-color: #555a6e !important;
  opacity: 0.5;
  width: 10px !important;
  height: 10px !important;
}
:deep(.scenario-base.component-marker) {
  background: #3a3e52 !important;
  border-color: #555a6e !important;
  color: #6b6f82 !important;
  opacity: 0.45;
}
</style>
