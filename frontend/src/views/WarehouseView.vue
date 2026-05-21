<template>
  <div class="page">
    <header class="page-header">
      <div class="page-header-row">
        <div>
          <h1>Equipment Warehouse</h1>
          <p class="subtitle">Browse distribution equipment from the active model</p>
        </div>
        <button class="btn btn-primary" @click="openTypePicker">
          <i class="ri-add-line"></i> Add Equipment
        </button>
      </div>
    </header>

    <!-- Category tabs -->
    <div v-if="!loading" class="category-tabs">
      <button
        class="category-tab"
        :class="{ active: activeCategory === 'All' }"
        @click="activeCategory = 'All'"
      >
        All<span class="tab-count">{{ totalCount }}</span>
      </button>
      <button
        v-for="(types, cat) in CATEGORIES"
        :key="cat"
        class="category-tab"
        :class="{ active: activeCategory === cat }"
        @click="activeCategory = cat"
      >
        {{ cat }}<span class="tab-count">{{ categoryCount(types) }}</span>
      </button>
    </div>

    <!-- Search bar -->
    <div v-if="!loading" class="warehouse-search">
      <i class="ri-search-line"></i>
      <input
        v-model="searchQuery"
        type="text"
        class="form-input"
        placeholder="Search by name, type, UUID..."
      />
      <span v-if="searchQuery" class="search-clear" @click="searchQuery = ''">
        <i class="ri-close-line"></i>
      </span>
      <span class="search-count">{{ searchedEquipment.length }} results</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="empty-state">
      <div class="spinner"></div>
      <p>Loading equipment...</p>
    </div>

    <!-- Equipment list -->
    <div v-else-if="pagedEquipment.length > 0" class="equipment-list">
      <div
        v-for="item in pagedEquipment"
        :key="item.uuid"
        class="equipment-card"
        :class="{ expanded: expandedIds.has(item.uuid) }"
      >
        <div class="equipment-card-header" @click="toggleExpand(item.uuid)">
          <div class="card-title-section">
            <div class="card-type-icon">
              <i :class="getIcon(item._type)"></i>
            </div>
            <div>
              <div class="card-title">{{ item.name || item._type }}</div>
              <div class="card-type-label">{{ getLabel(item._type) }}</div>
            </div>
          </div>
          <div style="display:flex;align-items:center;">
            <div class="card-actions" @click.stop>
              <button class="btn-icon" title="Edit" @click="openEditModal(item)">
                <i class="ri-edit-line"></i>
              </button>
              <button class="btn-icon danger" title="Delete" @click="openDeleteModal(item)">
                <i class="ri-delete-bin-line"></i>
              </button>
            </div>
            <i class="ri-arrow-right-s-line card-chevron"></i>
          </div>
        </div>
        <div class="equipment-card-body">
          <div class="field-grid">
            <div v-for="(value, key) in getDisplayFields(item)" :key="key" class="field-item">
              <div class="field-label">{{ formatKey(key as string) }}</div>
              <div class="field-value" v-html="formatValue(value)"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="!loading && searchedEquipment.length > 0" class="pagination">
      <button class="btn btn-sm btn-outline" :disabled="currentPage <= 1" @click="currentPage = 1">
        <i class="ri-skip-back-mini-line"></i>
      </button>
      <button class="btn btn-sm btn-outline" :disabled="currentPage <= 1" @click="currentPage--">
        <i class="ri-arrow-left-s-line"></i>
      </button>
      <span class="pagination-info">Page {{ currentPage }} of {{ totalPages }}</span>
      <button class="btn btn-sm btn-outline" :disabled="currentPage >= totalPages" @click="currentPage++">
        <i class="ri-arrow-right-s-line"></i>
      </button>
      <button class="btn btn-sm btn-outline" :disabled="currentPage >= totalPages" @click="currentPage = totalPages">
        <i class="ri-skip-forward-mini-line"></i>
      </button>
      <select class="form-select page-size-select" :value="pageSize" @change="pageSize = Number(($event.target as HTMLSelectElement).value); currentPage = 1">
        <option :value="25">25 / page</option>
        <option :value="50">50 / page</option>
        <option :value="100">100 / page</option>
      </select>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading && searchedEquipment.length === 0" class="empty-state">
      <i class="ri-archive-drawer-line"></i>
      <h3>{{ searchQuery ? 'No matching equipment' : 'No equipment loaded' }}</h3>
      <p>{{ searchQuery ? 'Try a different search term.' : 'Load a GDM system first, or add equipment manually.' }}</p>
    </div>

    <!-- ===== Type Picker Modal ===== -->
    <div v-if="showTypePicker" class="modal-overlay active" @click.self="showTypePicker = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Select Equipment Type</h3>
          <button class="modal-close" @click="showTypePicker = false">
            <i class="ri-close-line"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="type-picker-grid">
            <template
              v-for="(types, cat) in CATEGORIES"
              :key="cat"
            >
              <div v-for="eqType in types" :key="eqType" class="type-picker-item" @click="pickType(eqType)">
                <i :class="getIcon(eqType)"></i>
                <span>{{ getLabel(eqType) }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== Edit / Add Modal ===== -->
    <div v-if="showEditModal" class="modal-overlay active" @click.self="showEditModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editIsNew ? 'Add' : 'Edit' }} {{ editSchemaLabel }}</h3>
          <button class="modal-close" @click="showEditModal = false">
            <i class="ri-close-line"></i>
          </button>
        </div>
        <div class="modal-body">
          <template v-for="(fieldDef, key) in editSchema?.fields" :key="key">

            <!-- Nested List (sub-models as nested cards) -->
            <div v-if="fieldDef.type === 'nested_list'" class="form-group">
              <label class="form-label">
                {{ fieldDef.description || formatKey(String(key)) }}
                <span v-if="fieldDef.required" class="required">*</span>
              </label>
              <div v-for="(item, idx) in getNestedItems(String(key))" :key="idx" class="form-nested-section">
                <div class="form-nested-header">
                  <div class="form-nested-title">{{ getNestedSchema(fieldDef.schema)?.label || fieldDef.schema }} #{{ idx + 1 }}</div>
                  <div class="form-nested-actions">
                    <button type="button" class="btn-icon danger" title="Remove" @click="removeNestedItem(String(key), idx)">
                      <i class="ri-delete-bin-line"></i>
                    </button>
                  </div>
                </div>
                <template v-for="(nFieldDef, nKey) in getNestedSchema(fieldDef.schema)?.fields" :key="nKey">
                  <div class="form-group">
                    <label class="form-label">
                      {{ formatKey(String(nKey)) }}
                      <span v-if="nFieldDef.required" class="required">*</span>
                      <span v-if="nFieldDef.description" class="field-desc">{{ nFieldDef.description }}</span>
                    </label>
                    <!-- Nested Enum -->
                    <select
                      v-if="nFieldDef.type === 'enum'"
                      class="form-select"
                      :value="item[String(nKey)] ?? ''"
                      @change="item[String(nKey)] = ($event.target as HTMLSelectElement).value || null"
                    >
                      <option value="">— Select —</option>
                      <option v-for="opt in getEnumOptions(nFieldDef.enum)" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                    <!-- Nested Boolean -->
                    <select
                      v-else-if="nFieldDef.type === 'boolean'"
                      class="form-select"
                      :value="item[String(nKey)] === true ? 'true' : item[String(nKey)] === false ? 'false' : ''"
                      @change="item[String(nKey)] = ($event.target as HTMLSelectElement).value === 'true' ? true : ($event.target as HTMLSelectElement).value === 'false' ? false : null"
                    >
                      <option value="">— Select —</option>
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                    <!-- Nested Quantity -->
                    <div v-else-if="nFieldDef.type === 'quantity'" style="display:flex;gap:8px">
                      <input
                        type="number"
                        step="any"
                        class="form-input"
                        :placeholder="nFieldDef.description || String(nKey)"
                        :value="getQuantityValue(item[String(nKey)])"
                        @input="setNestedQuantityValue(item, String(nKey), ($event.target as HTMLInputElement).value, nFieldDef.unit)"
                      />
                      <div style="display:flex;align-items:center;color:#5b67f5;font-size:0.82rem;white-space:nowrap;min-width:50px">
                        {{ getQuantityUnit(item[String(nKey)]) || nFieldDef.unit || '' }}
                      </div>
                    </div>
                    <!-- Nested Integer / Float -->
                    <input
                      v-else-if="nFieldDef.type === 'integer' || nFieldDef.type === 'float'"
                      type="number"
                      :step="nFieldDef.type === 'integer' ? '1' : 'any'"
                      class="form-input"
                      :placeholder="nFieldDef.description || String(nKey)"
                      :value="item[String(nKey)] ?? ''"
                      @input="item[String(nKey)] = ($event.target as HTMLInputElement).value ? Number(($event.target as HTMLInputElement).value) : null"
                    />
                    <!-- Nested Array float -->
                    <input
                      v-else-if="nFieldDef.type === 'array_float'"
                      type="text"
                      class="form-input"
                      placeholder="e.g. 1.0, 1.0, 1.0"
                      :value="Array.isArray(item[String(nKey)]) ? (item[String(nKey)] as number[]).join(', ') : ''"
                      @input="item[String(nKey)] = ($event.target as HTMLInputElement).value.split(',').map((s: string) => parseFloat(s.trim())).filter((n: number) => !isNaN(n))"
                    />
                    <!-- Nested Matrix / array_json -->
                    <textarea
                      v-else-if="nFieldDef.type === 'matrix' || nFieldDef.type === 'array_json'"
                      class="form-input"
                      :rows="3"
                      style="font-family:monospace"
                      :value="item[String(nKey)] ? JSON.stringify(item[String(nKey)], null, 2) : ''"
                      @change="item[String(nKey)] = safeJsonParse(($event.target as HTMLTextAreaElement).value)"
                    ></textarea>
                    <!-- Nested String (default) -->
                    <input
                      v-else
                      type="text"
                      class="form-input"
                      :placeholder="nFieldDef.description || String(nKey)"
                      :value="item[String(nKey)] ?? ''"
                      @input="item[String(nKey)] = ($event.target as HTMLInputElement).value || null"
                    />
                  </div>
                </template>
              </div>
              <button type="button" class="form-add-btn" @click="addNestedItem(String(key), fieldDef.schema)">
                <i class="ri-add-line"></i> Add {{ getNestedSchema(fieldDef.schema)?.label || fieldDef.schema }}
              </button>
            </div>

            <!-- Scalar fields (non-nested) -->
            <div v-else class="form-group">
            <label class="form-label">
              {{ formatKey(String(key)) }}
              <span v-if="fieldDef.required" class="required">*</span>
              <span v-if="fieldDef.description" class="field-desc">{{ fieldDef.description }}</span>
            </label>

            <!-- Enum -->
            <select
              v-if="fieldDef.type === 'enum'"
              class="form-select"
              :value="editData[key] ?? ''"
              @change="editData[key] = ($event.target as HTMLSelectElement).value || null"
            >
              <option value="">— Select —</option>
              <option v-for="opt in getEnumOptions(fieldDef.enum)" :key="opt" :value="opt">{{ opt }}</option>
            </select>

            <!-- Boolean -->
            <select
              v-else-if="fieldDef.type === 'boolean'"
              class="form-select"
              :value="editData[key] === true ? 'true' : editData[key] === false ? 'false' : ''"
              @change="editData[key] = ($event.target as HTMLSelectElement).value === 'true' ? true : ($event.target as HTMLSelectElement).value === 'false' ? false : null"
            >
              <option value="">— Select —</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>

            <!-- Quantity -->
            <div v-else-if="fieldDef.type === 'quantity'" style="display:flex;gap:8px">
              <input
                type="number"
                step="any"
                class="form-input"
                :placeholder="fieldDef.description || String(key)"
                :value="getQuantityValue(editData[key])"
                @input="setQuantityValue(String(key), ($event.target as HTMLInputElement).value, fieldDef.unit)"
              />
              <div style="display:flex;align-items:center;color:#5b67f5;font-size:0.82rem;white-space:nowrap;min-width:50px">
                {{ getQuantityUnit(editData[key]) || fieldDef.unit || '' }}
              </div>
            </div>

            <!-- Integer / Float -->
            <input
              v-else-if="fieldDef.type === 'integer' || fieldDef.type === 'float'"
              type="number"
              :step="fieldDef.type === 'integer' ? '1' : 'any'"
              class="form-input"
              :placeholder="fieldDef.description || String(key)"
              :value="editData[key] ?? ''"
              @input="editData[key] = ($event.target as HTMLInputElement).value ? Number(($event.target as HTMLInputElement).value) : null"
            />

            <!-- Array float -->
            <input
              v-else-if="fieldDef.type === 'array_float'"
              type="text"
              class="form-input"
              placeholder="e.g. 1.0, 1.0, 1.0"
              :value="Array.isArray(editData[key]) ? (editData[key] as number[]).join(', ') : ''"
              @input="editData[key] = ($event.target as HTMLInputElement).value.split(',').map((s: string) => parseFloat(s.trim())).filter((n: number) => !isNaN(n))"
            />

            <!-- Matrix / array_json -->
            <textarea
              v-else-if="fieldDef.type === 'matrix' || fieldDef.type === 'array_json'"
              class="form-input"
              :rows="4"
              style="font-family:monospace"
              :placeholder="fieldDef.type === 'matrix' ? '[[0.088, 0.031], [0.031, 0.090]]' : '[[0, 1], ...]'"
              :value="editData[key] ? JSON.stringify(editData[key], null, 2) : ''"
              @change="setJsonField(String(key), ($event.target as HTMLTextAreaElement).value)"
            ></textarea>

            <!-- String (default) -->
            <input
              v-else
              type="text"
              class="form-input"
              :placeholder="fieldDef.description || String(key)"
              :value="editData[key] ?? ''"
              @input="editData[key] = ($event.target as HTMLInputElement).value || null"
            />
          </div>
          </template>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showEditModal = false">Cancel</button>
          <button class="btn btn-primary" @click="saveEquipment">
            {{ editIsNew ? 'Add' : 'Save' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ===== Delete Confirmation Modal ===== -->
    <div v-if="showDeleteModal" class="modal-overlay active" @click.self="showDeleteModal = false">
      <div class="modal" style="max-width:420px">
        <div class="modal-header">
          <h3>Delete Equipment</h3>
          <button class="modal-close" @click="showDeleteModal = false">
            <i class="ri-close-line"></i>
          </button>
        </div>
        <div class="modal-body">
          <p>Are you sure you want to delete "<strong>{{ deleteTarget?.name || deleteTarget?._type }}</strong>"?</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showDeleteModal = false">Cancel</button>
          <button class="btn btn-primary" style="background:#e54d4d" @click="confirmDelete">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, reactive } from 'vue'
import { equipmentApi } from '../api/client'
import { CATEGORIES, ICONS, SCHEMAS, ENUMS } from '../types/schemas'
import type { Schema } from '../types/schemas'
import type { GDMComponent } from '../types/api'
import { useToast } from '../composables/useToast'

const { toast } = useToast()

const activeCategory = ref('All')
const equipment = ref<GDMComponent[]>([])
const loading = ref(false)
const expandedIds = ref(new Set<string>())

// Search & pagination
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(25)

// Reset to page 1 when search or category changes
watch([searchQuery, activeCategory], () => { currentPage.value = 1 })

// Modal state
const showTypePicker = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)

const editIsNew = ref(false)
const editType = ref('')
const editUuid = ref('')
const editData = reactive<Record<string, unknown>>({})
const deleteTarget = ref<GDMComponent | null>(null)

const editSchema = computed(() => SCHEMAS[editType.value] || null)
const editSchemaLabel = computed(() => editSchema.value?.label || editType.value)

const totalCount = computed(() => equipment.value.length)

function categoryCount(types: string[]): number {
  return equipment.value.filter((e) => types.includes(e._type)).length
}

const filteredEquipment = computed(() => {
  if (activeCategory.value === 'All') return equipment.value
  const types = CATEGORIES[activeCategory.value] || []
  return equipment.value.filter((e) => types.includes(e._type))
})

const searchedEquipment = computed(() => {
  if (!searchQuery.value.trim()) return filteredEquipment.value
  const q = searchQuery.value.toLowerCase()
  return filteredEquipment.value.filter((e) => {
    const name = (e.name || '').toLowerCase()
    const type = (e._type || '').toLowerCase()
    const uuid = (e.uuid || '').toLowerCase()
    const label = (getLabel(e._type) || '').toLowerCase()
    return name.includes(q) || type.includes(q) || uuid.includes(q) || label.includes(q)
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(searchedEquipment.value.length / pageSize.value)))

const pagedEquipment = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return searchedEquipment.value.slice(start, start + pageSize.value)
})

function toggleExpand(uuid: string) {
  if (expandedIds.value.has(uuid)) {
    expandedIds.value.delete(uuid)
  } else {
    expandedIds.value.add(uuid)
  }
}

function getIcon(type: string): string {
  return ICONS[type] || 'ri-box-3-line'
}

function getLabel(type: string): string {
  return SCHEMAS[type]?.label || type
}

function getDisplayFields(item: GDMComponent): Record<string, unknown> {
  const skip = new Set(['_type', 'uuid', 'name'])
  const result: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(item)) {
    if (skip.has(k) || v === null || v === undefined) continue
    result[k] = v
  }
  return result
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ')
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '<span style="color:#4a4e65">—</span>'
  if (typeof val === 'object' && val !== null && 'value' in (val as Record<string, unknown>)) {
    const q = val as { value: number; units?: string; unit?: string }
    const v = typeof q.value === 'number' ? formatNumber(q.value) : q.value
    const u = q.units || q.unit || ''
    return `${v}<span class="unit">${u}</span>`
  }
  if (typeof val === 'boolean') {
    return val
      ? '<i class="ri-checkbox-circle-fill" style="color:#6fcf6f"></i> Yes'
      : '<i class="ri-close-circle-fill" style="color:#e54d4d"></i> No'
  }
  if (Array.isArray(val)) {
    return val.map((v) => formatNumber(v)).join(', ')
  }
  return String(val)
}

function formatNumber(n: unknown): string {
  if (typeof n !== 'number') return String(n)
  if (Number.isInteger(n)) return String(n)
  if (Math.abs(n) < 0.001) return n.toExponential(4)
  return parseFloat(n.toPrecision(6)).toString()
}

// ===== Enum helpers =====
function getEnumOptions(enumName?: string): string[] {
  return enumName ? ENUMS[enumName] || [] : []
}

// ===== Quantity helpers =====
function getQuantityValue(val: unknown): string {
  if (val && typeof val === 'object' && 'value' in (val as Record<string, unknown>)) {
    return String((val as { value: number }).value ?? '')
  }
  if (typeof val === 'string' && val.includes(' ')) return val.split(' ')[0]
  if (val !== null && val !== undefined) return String(val)
  return ''
}

function getQuantityUnit(val: unknown): string {
  if (val && typeof val === 'object') {
    const obj = val as Record<string, unknown>
    if ('unit' in obj) return String(obj.unit || '')
    if ('units' in obj) return String(obj.units || '')
  }
  if (typeof val === 'string' && val.includes(' ')) return val.split(' ').slice(1).join(' ')
  return ''
}

function setQuantityValue(key: string, rawVal: string, defaultUnit?: string) {
  if (!rawVal) {
    editData[key] = null
    return
  }
  const existing = editData[key] as { value?: number; unit?: string } | null
  editData[key] = { value: parseFloat(rawVal), unit: existing?.unit || defaultUnit || '' }
}

function setJsonField(key: string, raw: string) {
  try {
    editData[key] = JSON.parse(raw)
  } catch {
    // keep raw string if invalid json
    editData[key] = raw
  }
}

function safeJsonParse(raw: string): unknown {
  try { return JSON.parse(raw) } catch { return raw }
}

// ===== Nested List Helpers =====
function getNestedSchema(schemaName?: string): Schema | null {
  return schemaName ? SCHEMAS[schemaName] || null : null
}

function getNestedItems(key: string): Record<string, unknown>[] {
  if (!Array.isArray(editData[key])) editData[key] = []
  return editData[key] as Record<string, unknown>[]
}

function addNestedItem(key: string, schemaName?: string) {
  if (!Array.isArray(editData[key])) editData[key] = []
  const items = editData[key] as Record<string, unknown>[]
  const newItem: Record<string, unknown> = {}
  const nestedSchema = schemaName ? SCHEMAS[schemaName] : null
  if (nestedSchema) {
    for (const [fk, fd] of Object.entries(nestedSchema.fields)) {
      newItem[fk] = fd.default ?? null
    }
  }
  items.push(newItem)
}

function removeNestedItem(key: string, idx: number) {
  if (!Array.isArray(editData[key])) return
  ;(editData[key] as Record<string, unknown>[]).splice(idx, 1)
}

function setNestedQuantityValue(item: Record<string, unknown>, key: string, rawVal: string, defaultUnit?: string) {
  if (!rawVal) { item[key] = null; return }
  const existing = item[key] as { value?: number; unit?: string } | null
  item[key] = { value: parseFloat(rawVal), unit: existing?.unit || defaultUnit || '' }
}

// ===== Type Picker =====
function openTypePicker() {
  showTypePicker.value = true
}

function pickType(eqType: string) {
  showTypePicker.value = false
  editIsNew.value = true
  editType.value = eqType
  editUuid.value = ''
  // Clear and populate editData with defaults
  Object.keys(editData).forEach((k) => delete editData[k])
  const schema = SCHEMAS[eqType]
  if (schema) {
    for (const [key, fieldDef] of Object.entries(schema.fields)) {
      editData[key] = fieldDef.default ?? null
    }
  }
  showEditModal.value = true
}

// ===== Edit Modal =====
function openEditModal(item: GDMComponent) {
  editIsNew.value = false
  editType.value = item._type
  editUuid.value = item.uuid
  // Populate form with current values
  Object.keys(editData).forEach((k) => delete editData[k])
  const schema = SCHEMAS[item._type]
  if (schema) {
    for (const key of Object.keys(schema.fields)) {
      editData[key] = item[key] ?? null
    }
  } else {
    for (const [k, v] of Object.entries(item)) {
      if (k !== '_type' && k !== 'uuid') editData[k] = v
    }
  }
  showEditModal.value = true
}

async function saveEquipment() {
  if (!editData.name) {
    toast('Name is required', 'error')
    return
  }

  try {
    if (editIsNew.value) {
      const { data: created } = await equipmentApi.add(editType.value, { ...editData })
      equipment.value.push(created)
      toast(`${editSchemaLabel.value} added`, 'success')
    } else {
      const { data: updated } = await equipmentApi.update(editUuid.value, { ...editData })
      const idx = equipment.value.findIndex((e) => e.uuid === editUuid.value)
      if (idx >= 0) equipment.value[idx] = updated
      toast(`${editSchemaLabel.value} updated`, 'success')
    }
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    toast(msg || 'Save failed', 'error')
  }

  showEditModal.value = false
}

// ===== Delete Modal =====
function openDeleteModal(item: GDMComponent) {
  deleteTarget.value = item
  showDeleteModal.value = true
}

async function confirmDelete() {
  if (deleteTarget.value) {
    try {
      await equipmentApi.remove(deleteTarget.value.uuid)
      equipment.value = equipment.value.filter((e) => e.uuid !== deleteTarget.value!.uuid)
      toast('Equipment deleted', 'success')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast(msg || 'Delete failed', 'error')
    }
  }
  showDeleteModal.value = false
  deleteTarget.value = null
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await equipmentApi.list()
    equipment.value = data
  } catch {
    // No active project or model
  } finally {
    loading.value = false
  }
})
</script>
