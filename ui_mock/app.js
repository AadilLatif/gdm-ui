/**
 * GDM Studio – UI Mock Application
 * SaaS interface for grid-data-models equipment warehouse
 */

// ===== State =====
const state = {
  system: null,           // loaded GDM system JSON
  equipment: {},          // { EquipmentType: [ {id, data} ] }
  activeCategory: "All",
  editTarget: null,       // { type, index } or null for new
  deleteTarget: null,     // { type, index }
};

let nextId = 1;

// ===== DOM refs =====
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

// ===== Page Navigation =====
$$(".nav-item").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    const page = item.dataset.page;
    $$(".nav-item").forEach((n) => n.classList.remove("active"));
    item.classList.add("active");
    $$(".page").forEach((p) => p.classList.remove("active"));
    $(`#page-${page}`).classList.add("active");
  });
});

// ===== File Upload =====
const uploadZone = $("#uploadZone");
const fileInput = $("#fileInput");
const browseBtn = $("#browseBtn");

browseBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});
uploadZone.addEventListener("click", () => fileInput.click());
uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  if (e.dataTransfer.files.length) loadFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) loadFile(fileInput.files[0]);
});

function loadFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      state.system = data;
      parseEquipment(data);
      showSystemSummary(file.name);
      toast("System loaded successfully", "success");
    } catch (err) {
      toast("Failed to parse JSON: " + err.message, "error");
    }
  };
  reader.readAsText(file);
}

// ===== Parse Equipment from GDM JSON =====
function parseEquipment(data) {
  state.equipment = {};

  // GDM JSON format: { components: [ { uuid, name, __metadata__: { fields: { type } }, ...fields } ] }
  // Quantity fields: { value, units, __metadata__ }
  // References to other components use UUID strings

  const components = data.components || [];
  const knownTypes = new Set(Object.keys(SCHEMAS));

  // Build UUID -> component lookup for resolving references
  const uuidMap = {};
  for (const comp of components) {
    if (comp.uuid) uuidMap[comp.uuid] = comp;
  }

  for (const comp of components) {
    const typeName = comp.__metadata__?.fields?.type;
    if (!typeName || !knownTypes.has(typeName)) continue;

    if (!state.equipment[typeName]) state.equipment[typeName] = [];
    state.equipment[typeName].push({
      id: nextId++,
      uuid: comp.uuid,
      data: flattenComponentData(comp, typeName, uuidMap),
      raw: comp,
    });
  }
}

// Flatten nested pint quantities { value: X, units: "Y", __metadata__: {...} } into display-friendly format
function flattenComponentData(raw, typeName, uuidMap) {
  const schema = SCHEMAS[typeName];
  if (!schema) return raw;

  const result = {};
  for (const [key, fieldDef] of Object.entries(schema.fields)) {
    let val = raw[key];
    if (val === undefined || val === null) {
      result[key] = null;
      continue;
    }

    if (fieldDef.type === "quantity") {
      // GDM format: { value: number, units: string, __metadata__: {...} }
      if (typeof val === "object" && val.value !== undefined) {
        result[key] = { value: val.value, unit: val.units || fieldDef.unit };
      } else {
        result[key] = { value: val, unit: fieldDef.unit };
      }
    } else if (fieldDef.type === "nested_list") {
      if (Array.isArray(val)) {
        result[key] = val.map((item) => {
          // GDM composed_component reference: { __metadata__: { fields: { uuid, serialized_type: "composed_component" } } }
          if (typeof item === "object" && item.__metadata__?.fields?.serialized_type === "composed_component") {
            const refUuid = item.__metadata__.fields.uuid;
            const resolved = uuidMap?.[refUuid];
            if (resolved) return flattenComponentData(resolved, fieldDef.schema, uuidMap);
            return { _ref: refUuid, name: `ref:${refUuid?.substring(0, 8)}…` };
          }
          if (typeof item === "string") {
            // Plain UUID reference
            const resolved = uuidMap?.[item];
            if (resolved) return flattenComponentData(resolved, fieldDef.schema, uuidMap);
            return { _ref: item, name: `ref:${item.substring(0, 8)}…` };
          }
          if (typeof item === "object" && item.uuid) {
            return flattenComponentData(item, fieldDef.schema, uuidMap);
          }
          return flattenComponentData(item, fieldDef.schema, uuidMap);
        });
      } else {
        result[key] = val;
      }
    } else if (fieldDef.type === "matrix") {
      // Matrix may be { value: [[...]], units: "...", __metadata__ }
      if (typeof val === "object" && val.value !== undefined) {
        result[key] = { value: val.value, units: val.units || fieldDef.unit };
      } else {
        result[key] = val;
      }
    } else {
      result[key] = val;
    }
  }
  return result;
}

// ===== Show System Summary =====
function showSystemSummary(filename) {
  uploadZone.style.display = "none";
  const summary = $("#systemSummary");
  summary.style.display = "block";

  $("#summaryTitle").textContent = filename.replace(".json", "");
  $("#systemBadge").style.display = "flex";
  $("#systemName").textContent = filename.replace(".json", "");

  // Stats
  const statsGrid = $("#statsGrid");
  const totalEquip = Object.values(state.equipment).reduce((s, arr) => s + arr.length, 0);
  const typeCount = Object.keys(state.equipment).filter((k) => state.equipment[k].length > 0).length;

  let totalComponents = 0;
  if (state.system.components) {
    totalComponents = state.system.components.length;
  }

  statsGrid.innerHTML = `
    <div class="stat-card"><div class="stat-value">${totalComponents}</div><div class="stat-label">Total Components</div></div>
    <div class="stat-card"><div class="stat-value">${totalEquip}</div><div class="stat-label">Equipment Items</div></div>
    <div class="stat-card"><div class="stat-value">${typeCount}</div><div class="stat-label">Equipment Types</div></div>
  `;

  // Inventory table
  const tbody = $("#inventoryBody");
  tbody.innerHTML = "";
  for (const [type, items] of Object.entries(state.equipment)) {
    if (!items.length) continue;
    const label = SCHEMAS[type]?.label || type;
    const icon = ICONS[type] || "ri-box-3-line";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="type-badge"><i class="${icon}"></i> ${label}</span></td>
      <td><span class="count-badge">${items.length}</span></td>
      <td><button class="btn btn-sm btn-outline" data-view-type="${type}">View</button></td>
    `;
    tbody.appendChild(tr);
  }
  tbody.querySelectorAll("[data-view-type]").forEach((btn) => {
    btn.addEventListener("click", () => {
      goToWarehouse(btn.dataset.viewType);
    });
  });
}

// ===== Warehouse Navigation =====
$("#goToWarehouse").addEventListener("click", () => goToWarehouse());
function goToWarehouse(filterType) {
  $$(".nav-item").forEach((n) => n.classList.remove("active"));
  $$(".nav-item")[1].classList.add("active");
  $$(".page").forEach((p) => p.classList.remove("active"));
  $("#page-warehouse").classList.add("active");
  renderCategoryTabs();
  if (filterType) {
    // find the category for this type
    for (const [cat, types] of Object.entries(CATEGORIES)) {
      if (types.includes(filterType)) {
        state.activeCategory = cat;
        break;
      }
    }
  }
  renderCategoryTabs();
  renderEquipmentList();
}

// ===== Unload =====
$("#unloadBtn").addEventListener("click", () => {
  state.system = null;
  state.equipment = {};
  uploadZone.style.display = "";
  $("#systemSummary").style.display = "none";
  $("#systemBadge").style.display = "none";
  renderEquipmentList();
  toast("System unloaded", "info");
});

// ===== Category Tabs =====
function renderCategoryTabs() {
  const tabs = $("#categoryTabs");
  const allCount = Object.values(state.equipment).reduce((s, a) => s + a.length, 0);

  let html = `<button class="category-tab ${state.activeCategory === "All" ? "active" : ""}" data-cat="All">All<span class="tab-count">${allCount}</span></button>`;

  for (const [cat, types] of Object.entries(CATEGORIES)) {
    const count = types.reduce((s, t) => s + (state.equipment[t]?.length || 0), 0);
    if (count === 0 && !state.system) continue;
    html += `<button class="category-tab ${state.activeCategory === cat ? "active" : ""}" data-cat="${cat}">${cat}<span class="tab-count">${count}</span></button>`;
  }
  tabs.innerHTML = html;

  tabs.querySelectorAll(".category-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      state.activeCategory = tab.dataset.cat;
      renderCategoryTabs();
      renderEquipmentList();
    });
  });
}

// ===== Render Equipment List =====
function renderEquipmentList() {
  const list = $("#equipmentList");

  let typesToShow;
  if (state.activeCategory === "All") {
    typesToShow = Object.keys(state.equipment);
  } else {
    typesToShow = CATEGORIES[state.activeCategory] || [];
  }

  let cards = [];
  for (const type of typesToShow) {
    const items = state.equipment[type] || [];
    for (let i = 0; i < items.length; i++) {
      cards.push({ type, index: i, item: items[i] });
    }
  }

  if (cards.length === 0) {
    list.innerHTML = `<div class="empty-state"><i class="ri-archive-drawer-line"></i><h3>No equipment loaded</h3><p>Load a GDM system first, or add equipment manually.</p></div>`;
    return;
  }

  list.innerHTML = cards.map((c) => renderEquipmentCard(c.type, c.index, c.item)).join("");

  // Toggle expansion
  list.querySelectorAll(".equipment-card-header").forEach((header) => {
    header.addEventListener("click", (e) => {
      if (e.target.closest(".btn-icon")) return;
      header.closest(".equipment-card").classList.toggle("expanded");
    });
  });

  // Edit buttons
  list.querySelectorAll("[data-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const [type, idx] = btn.dataset.edit.split(":");
      openEditModal(type, parseInt(idx));
    });
  });

  // Delete buttons
  list.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const [type, idx] = btn.dataset.delete.split(":");
      openDeleteModal(type, parseInt(idx));
    });
  });
}

function renderEquipmentCard(type, index, item) {
  const schema = SCHEMAS[type];
  if (!schema) return "";
  const icon = ICONS[type] || "ri-box-3-line";
  const name = item.data.name || `${schema.label} #${index + 1}`;

  let bodyHtml = renderFieldGrid(item.data, schema.fields, type);

  return `
    <div class="equipment-card">
      <div class="equipment-card-header">
        <div class="card-title-section">
          <div class="card-type-icon"><i class="${icon}"></i></div>
          <div>
            <div class="card-title">${escapeHtml(String(name))}</div>
            <div class="card-type-label">${schema.label}</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;">
          <div class="card-actions">
            <button class="btn-icon" data-edit="${type}:${index}" title="Edit"><i class="ri-edit-line"></i></button>
            <button class="btn-icon danger" data-delete="${type}:${index}" title="Delete"><i class="ri-delete-bin-line"></i></button>
          </div>
          <i class="ri-arrow-right-s-line card-chevron"></i>
        </div>
      </div>
      <div class="equipment-card-body">${bodyHtml}</div>
    </div>
  `;
}

function renderFieldGrid(data, fields, parentType) {
  let scalarFields = [];
  let nestedSections = [];

  for (const [key, fieldDef] of Object.entries(fields)) {
    if (key === "name") continue; // shown in header
    const val = data[key];

    if (fieldDef.type === "nested_list") {
      nestedSections.push(renderNestedSection(key, val, fieldDef));
    } else if (fieldDef.type === "matrix") {
      scalarFields.push(renderMatrixField(key, val, fieldDef));
    } else {
      scalarFields.push(renderScalarField(key, val, fieldDef));
    }
  }

  let html = "";
  if (scalarFields.length) {
    html += `<div class="field-grid">${scalarFields.join("")}</div>`;
  }
  html += nestedSections.join("");
  return html;
}

function renderScalarField(key, val, fieldDef) {
  let display = "";
  if (val === null || val === undefined) {
    display = '<span style="color:#4a4e65">—</span>';
  } else if (fieldDef.type === "quantity") {
    if (typeof val === "object" && val.value !== undefined) {
      const v = typeof val.value === "number" ? formatNumber(val.value) : val.value;
      display = `${v}<span class="unit">${val.unit || fieldDef.unit || ""}</span>`;
    } else {
      display = String(val);
    }
  } else if (fieldDef.type === "boolean") {
    display = val ? '<i class="ri-checkbox-circle-fill" style="color:#6fcf6f"></i> Yes' : '<i class="ri-close-circle-fill" style="color:#e54d4d"></i> No';
  } else if (fieldDef.type === "enum") {
    display = `<span style="color:#a8b0ff">${val}</span>`;
  } else if (fieldDef.type === "array_float" || fieldDef.type === "array_json") {
    display = Array.isArray(val) ? val.map((v) => formatNumber(v)).join(", ") : String(val);
  } else {
    display = String(val);
  }

  const label = fieldDef.description || key.replace(/_/g, " ");
  return `<div class="field-item"><div class="field-label">${escapeHtml(label)}</div><div class="field-value">${display}</div></div>`;
}

function renderMatrixField(key, val, fieldDef) {
  let display = "";
  if (val && typeof val === "object" && val.value !== undefined) {
    const matrix = val.value;
    if (Array.isArray(matrix)) {
      display = '<table style="font-size:0.78rem;border-collapse:collapse;width:100%">';
      for (const row of matrix) {
        display += "<tr>";
        if (Array.isArray(row)) {
          for (const cell of row) {
            display += `<td style="padding:2px 6px;border:1px solid #2a2d3a;text-align:right;font-family:monospace">${formatNumber(cell)}</td>`;
          }
        } else {
          display += `<td style="padding:2px 6px;font-family:monospace">${formatNumber(row)}</td>`;
        }
        display += "</tr>";
      }
      display += "</table>";
      if (val.units) display += `<div style="color:#5b67f5;font-size:0.72rem;margin-top:4px">${val.units}</div>`;
    } else {
      display = String(val.value);
    }
  } else if (val !== null && val !== undefined) {
    display = String(val);
  } else {
    display = "—";
  }
  const label = fieldDef.description || key;
  return `<div class="field-item" style="grid-column:1/-1"><div class="field-label">${escapeHtml(label)}</div><div class="field-value">${display}</div></div>`;
}

function renderNestedSection(key, val, fieldDef) {
  const nestedSchema = SCHEMAS[fieldDef.schema];
  if (!nestedSchema || !Array.isArray(val) || val.length === 0) {
    return `<div class="nested-section"><div class="nested-section-title"><i class="ri-arrow-right-s-line"></i> ${fieldDef.description || key}</div><div style="color:#4a4e65;font-size:0.82rem;padding:8px 0">No items</div></div>`;
  }

  let html = `<div class="nested-section"><div class="nested-section-title"><i class="ri-arrow-right-s-line"></i> ${fieldDef.description || key} (${val.length})</div>`;

  for (let i = 0; i < val.length; i++) {
    const item = val[i];
    if (item._ref) {
      html += `<div class="nested-card"><div class="nested-card-header"><div class="nested-card-title">Reference: ${item._ref.substring(0, 8)}…</div></div></div>`;
      continue;
    }
    const name = item.name || `${nestedSchema.label} #${i + 1}`;
    const icon = ICONS[fieldDef.schema] || "ri-box-3-line";
    html += `<div class="nested-card"><div class="nested-card-header"><div class="nested-card-title"><i class="${icon}" style="margin-right:6px"></i>${escapeHtml(String(name))}</div></div>`;
    html += renderFieldGrid(item, nestedSchema.fields, fieldDef.schema);
    html += `</div>`;
  }
  html += `</div>`;
  return html;
}

// ===== Modal: Edit/Add Equipment =====
function openEditModal(type, index) {
  const schema = SCHEMAS[type];
  if (!schema) return;

  const isNew = index === -1;
  state.editTarget = { type, index };

  $("#modalTitle").textContent = isNew ? `Add ${schema.label}` : `Edit ${schema.label}`;
  const body = $("#modalBody");
  body.innerHTML = "";

  const data = isNew ? {} : { ...state.equipment[type][index].data };
  body.appendChild(buildForm(schema.fields, data, type));

  openModal("modalOverlay");
}

function buildForm(fields, data, parentType) {
  const frag = document.createDocumentFragment();

  for (const [key, fieldDef] of Object.entries(fields)) {
    if (fieldDef.type === "nested_list") {
      frag.appendChild(buildNestedListField(key, fieldDef, data[key] || []));
    } else if (fieldDef.type === "matrix") {
      frag.appendChild(buildMatrixField(key, fieldDef, data[key]));
    } else {
      frag.appendChild(buildField(key, fieldDef, data[key]));
    }
  }
  return frag;
}

function buildField(key, fieldDef, value) {
  const group = document.createElement("div");
  group.className = "form-group";

  const reqMark = fieldDef.required ? ' <span class="required">*</span>' : "";
  const desc = fieldDef.description ? `<span class="field-desc">${escapeHtml(fieldDef.description)}</span>` : "";
  group.innerHTML = `<label class="form-label">${key.replace(/_/g, " ")}${reqMark}${desc}</label>`;

  if (fieldDef.type === "enum") {
    const options = ENUMS[fieldDef.enum] || [];
    const currentVal = value || fieldDef.default || "";
    let optionsHtml = options.map((o) => `<option value="${o}" ${o === currentVal ? "selected" : ""}>${o}</option>`).join("");
    const sel = document.createElement("select");
    sel.className = "form-select";
    sel.dataset.field = key;
    sel.innerHTML = `<option value="">— Select —</option>${optionsHtml}`;
    if (currentVal) sel.value = currentVal;
    group.appendChild(sel);
  } else if (fieldDef.type === "boolean") {
    const sel = document.createElement("select");
    sel.className = "form-select";
    sel.dataset.field = key;
    sel.innerHTML = `<option value="">— Select —</option><option value="true" ${value === true ? "selected" : ""}>Yes</option><option value="false" ${value === false ? "selected" : ""}>No</option>`;
    group.appendChild(sel);
  } else if (fieldDef.type === "quantity") {
    const row = document.createElement("div");
    row.style.display = "flex";
    row.style.gap = "8px";
    const input = document.createElement("input");
    input.type = "number";
    input.step = "any";
    input.className = "form-input";
    input.dataset.field = key;
    input.dataset.fieldType = "quantity";
    input.placeholder = "Value";
    if (value && typeof value === "object") input.value = value.value ?? "";
    else if (value !== null && value !== undefined) input.value = value;
    row.appendChild(input);

    const unitSpan = document.createElement("div");
    unitSpan.style.cssText = "display:flex;align-items:center;color:#5b67f5;font-size:0.82rem;white-space:nowrap;min-width:50px;";
    unitSpan.textContent = (value && value.unit) || fieldDef.unit || "";
    row.appendChild(unitSpan);
    group.appendChild(row);
  } else if (fieldDef.type === "integer") {
    const input = document.createElement("input");
    input.type = "number";
    input.step = "1";
    input.className = "form-input";
    input.dataset.field = key;
    input.placeholder = fieldDef.description || key;
    if (value !== null && value !== undefined) input.value = value;
    else if (fieldDef.default !== undefined) input.value = fieldDef.default;
    group.appendChild(input);
  } else if (fieldDef.type === "float") {
    const input = document.createElement("input");
    input.type = "number";
    input.step = "any";
    input.className = "form-input";
    input.dataset.field = key;
    input.placeholder = fieldDef.description || key;
    if (value !== null && value !== undefined) input.value = value;
    else if (fieldDef.default !== undefined) input.value = fieldDef.default;
    group.appendChild(input);
  } else if (fieldDef.type === "array_float") {
    const input = document.createElement("input");
    input.type = "text";
    input.className = "form-input";
    input.dataset.field = key;
    input.dataset.fieldType = "array_float";
    input.placeholder = "e.g. 1.0, 1.0, 1.0";
    if (Array.isArray(value)) input.value = value.join(", ");
    group.appendChild(input);
  } else if (fieldDef.type === "array_json") {
    const input = document.createElement("textarea");
    input.className = "form-input";
    input.dataset.field = key;
    input.dataset.fieldType = "array_json";
    input.rows = 2;
    input.placeholder = '[[0, 1], ...]';
    if (value) input.value = JSON.stringify(value);
    group.appendChild(input);
  } else {
    const input = document.createElement("input");
    input.type = "text";
    input.className = "form-input";
    input.dataset.field = key;
    input.placeholder = fieldDef.description || key;
    if (value !== null && value !== undefined) input.value = value;
    else if (fieldDef.default !== undefined) input.value = fieldDef.default;
    group.appendChild(input);
  }

  return group;
}

function buildMatrixField(key, fieldDef, value) {
  const group = document.createElement("div");
  group.className = "form-group";
  const reqMark = fieldDef.required ? ' <span class="required">*</span>' : "";
  group.innerHTML = `<label class="form-label">${key.replace(/_/g, " ")}${reqMark}<span class="field-desc">${fieldDef.description || ""} — Enter as JSON 2D array</span></label>`;

  const textarea = document.createElement("textarea");
  textarea.className = "form-input";
  textarea.dataset.field = key;
  textarea.dataset.fieldType = "matrix";
  textarea.rows = 4;
  textarea.style.fontFamily = "monospace";
  textarea.placeholder = "[[0.088, 0.031], [0.031, 0.090]]";

  if (value && typeof value === "object" && value.value !== undefined) {
    textarea.value = JSON.stringify(value.value, null, 2);
  } else if (value) {
    textarea.value = JSON.stringify(value, null, 2);
  }
  group.appendChild(textarea);
  return group;
}

function buildNestedListField(key, fieldDef, items) {
  const section = document.createElement("div");
  section.className = "form-group";

  const nestedSchema = SCHEMAS[fieldDef.schema];
  if (!nestedSchema) return section;

  section.innerHTML = `<label class="form-label">${fieldDef.description || key} <span class="required">*</span></label>`;

  const container = document.createElement("div");
  container.dataset.nestedField = key;
  container.dataset.nestedSchema = fieldDef.schema;

  if (Array.isArray(items)) {
    items.forEach((item, i) => {
      container.appendChild(buildNestedItem(fieldDef.schema, nestedSchema, item, i));
    });
  }

  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "form-add-btn";
  addBtn.innerHTML = `<i class="ri-add-line"></i> Add ${nestedSchema.label}`;
  addBtn.addEventListener("click", () => {
    const idx = container.querySelectorAll(".form-nested-section").length;
    container.insertBefore(buildNestedItem(fieldDef.schema, nestedSchema, {}, idx), addBtn);
  });

  container.appendChild(addBtn);
  section.appendChild(container);
  return section;
}

function buildNestedItem(schemaKey, nestedSchema, data, index) {
  const div = document.createElement("div");
  div.className = "form-nested-section";
  div.dataset.nestedIndex = index;

  const header = document.createElement("div");
  header.className = "form-nested-header";
  header.innerHTML = `
    <div class="form-nested-title">${nestedSchema.label} #${index + 1}</div>
    <div class="form-nested-actions">
      <button type="button" class="btn-icon danger nested-remove" title="Remove"><i class="ri-delete-bin-line"></i></button>
    </div>
  `;
  div.appendChild(header);

  for (const [key, fieldDef] of Object.entries(nestedSchema.fields)) {
    if (fieldDef.type === "nested_list") {
      // Deep nesting — skip for simplicity in mock
      continue;
    }
    const field = buildField(key, fieldDef, data[key]);
    // Prefix field names to avoid collisions
    field.querySelectorAll("[data-field]").forEach((el) => {
      el.dataset.field = `${schemaKey}[${index}].${el.dataset.field}`;
    });
    div.appendChild(field);
  }

  div.querySelector(".nested-remove").addEventListener("click", () => {
    div.remove();
  });

  return div;
}

// ===== Collect Form Data =====
function collectFormData() {
  const data = {};
  const body = $("#modalBody");

  // Scalar fields
  body.querySelectorAll("[data-field]").forEach((el) => {
    const key = el.dataset.field;
    if (key.includes("[")) return; // nested, handle separately

    let val;
    if (el.dataset.fieldType === "quantity") {
      val = el.value ? { value: parseFloat(el.value), unit: el.nextElementSibling?.textContent || "" } : null;
    } else if (el.dataset.fieldType === "array_float") {
      val = el.value ? el.value.split(",").map((s) => parseFloat(s.trim())).filter((n) => !isNaN(n)) : [];
    } else if (el.dataset.fieldType === "array_json" || el.dataset.fieldType === "matrix") {
      try { val = JSON.parse(el.value); } catch { val = el.value; }
    } else if (el.tagName === "SELECT") {
      if (el.value === "true") val = true;
      else if (el.value === "false") val = false;
      else val = el.value || null;
    } else if (el.type === "number") {
      val = el.value ? (el.step === "1" ? parseInt(el.value) : parseFloat(el.value)) : null;
    } else {
      val = el.value || null;
    }
    data[key] = val;
  });

  // Nested fields
  body.querySelectorAll("[data-nested-field]").forEach((container) => {
    const key = container.dataset.nestedField;
    const schemaKey = container.dataset.nestedSchema;
    const nestedSchema = SCHEMAS[schemaKey];
    if (!nestedSchema) return;

    const items = [];
    container.querySelectorAll(".form-nested-section").forEach((section, idx) => {
      const item = {};
      section.querySelectorAll("[data-field]").forEach((el) => {
        const fieldPath = el.dataset.field;
        // Extract the field name from "SchemaName[idx].fieldName"
        const match = fieldPath.match(/\[\d+\]\.(.+)$/);
        if (!match) return;
        const fieldName = match[1];

        if (el.dataset.fieldType === "quantity") {
          item[fieldName] = el.value ? { value: parseFloat(el.value), unit: el.nextElementSibling?.textContent || "" } : null;
        } else if (el.dataset.fieldType === "array_float") {
          item[fieldName] = el.value ? el.value.split(",").map((s) => parseFloat(s.trim())).filter((n) => !isNaN(n)) : [];
        } else if (el.tagName === "SELECT") {
          if (el.value === "true") item[fieldName] = true;
          else if (el.value === "false") item[fieldName] = false;
          else item[fieldName] = el.value || null;
        } else if (el.type === "number") {
          item[fieldName] = el.value ? parseFloat(el.value) : null;
        } else {
          item[fieldName] = el.value || null;
        }
      });
      items.push(item);
    });
    data[key] = items;
  });

  return data;
}

// ===== Save Equipment =====
$("#modalSave").addEventListener("click", () => {
  const { type, index } = state.editTarget;
  const data = collectFormData();

  if (!data.name) {
    toast("Name is required", "error");
    return;
  }

  if (index === -1) {
    // Add new
    if (!state.equipment[type]) state.equipment[type] = [];
    state.equipment[type].push({ id: nextId++, data, raw: data });
    toast(`${SCHEMAS[type].label} added`, "success");
  } else {
    // Update existing
    state.equipment[type][index].data = data;
    state.equipment[type][index].raw = data;
    toast(`${SCHEMAS[type].label} updated`, "success");
  }

  closeModal("modalOverlay");
  renderCategoryTabs();
  renderEquipmentList();
});

// ===== Delete Equipment =====
function openDeleteModal(type, index) {
  state.deleteTarget = { type, index };
  const item = state.equipment[type][index];
  const name = item.data.name || SCHEMAS[type]?.label || type;
  $("#deleteMessage").textContent = `Are you sure you want to delete "${name}"?`;
  openModal("deleteOverlay");
}

$("#deleteConfirmBtn").addEventListener("click", () => {
  const { type, index } = state.deleteTarget;
  state.equipment[type].splice(index, 1);
  if (state.equipment[type].length === 0) delete state.equipment[type];
  closeModal("deleteOverlay");
  renderCategoryTabs();
  renderEquipmentList();
  toast("Equipment deleted", "success");
});

// ===== Add Equipment (Type Picker) =====
$("#addEquipmentBtn").addEventListener("click", () => {
  const grid = $("#typePickerGrid");
  grid.innerHTML = "";
  for (const [cat, types] of Object.entries(CATEGORIES)) {
    for (const type of types) {
      const schema = SCHEMAS[type];
      if (!schema) continue;
      const icon = ICONS[type] || "ri-box-3-line";
      const div = document.createElement("div");
      div.className = "type-picker-item";
      div.innerHTML = `<i class="${icon}"></i><span>${schema.label}</span>`;
      div.addEventListener("click", () => {
        closeModal("typePickerOverlay");
        openEditModal(type, -1);
      });
      grid.appendChild(div);
    }
  }
  openModal("typePickerOverlay");
});

// ===== Modal Helpers =====
function openModal(id) {
  $(`#${id}`).classList.add("active");
}
function closeModal(id) {
  $(`#${id}`).classList.remove("active");
}

$("#modalClose").addEventListener("click", () => closeModal("modalOverlay"));
$("#modalCancel").addEventListener("click", () => closeModal("modalOverlay"));
$("#typePickerClose").addEventListener("click", () => closeModal("typePickerOverlay"));
$("#deleteClose").addEventListener("click", () => closeModal("deleteOverlay"));
$("#deleteCancelBtn").addEventListener("click", () => closeModal("deleteOverlay"));

// Close modals on backdrop click
["modalOverlay", "typePickerOverlay", "deleteOverlay"].forEach((id) => {
  $(`#${id}`).addEventListener("click", (e) => {
    if (e.target === $(`#${id}`)) closeModal(id);
  });
});

// ===== Toast =====
function toast(message, type = "info") {
  const container = $("#toastContainer");
  const icons = { success: "ri-checkbox-circle-line", error: "ri-error-warning-line", info: "ri-information-line" };
  const div = document.createElement("div");
  div.className = `toast ${type}`;
  div.innerHTML = `<i class="${icons[type]}"></i> ${escapeHtml(message)}`;
  container.appendChild(div);
  setTimeout(() => div.remove(), 3500);
}

// ===== Helpers =====
function formatNumber(n) {
  if (typeof n !== "number") return n;
  if (Number.isInteger(n)) return String(n);
  if (Math.abs(n) < 0.001) return n.toExponential(4);
  return parseFloat(n.toPrecision(6)).toString();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ===== Init =====
renderCategoryTabs();
renderEquipmentList();
