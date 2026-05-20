/**
 * GDM Studio – Network Map Module
 * GIS map with distribution network overlay, drag-drop component placement,
 * and click-to-inspect/edit/delete on map assets.
 */

// ===== Network State =====
const networkState = {
  map: null,
  busMarkers: {},       // busName -> L.marker
  busLabels: {},        // busName -> L.tooltip/marker
  edgeLines: {},        // edgeName -> L.polyline
  componentMarkers: {}, // compName -> L.marker
  buses: [],            // parsed bus data: { name, uuid, lat, lng, phases, voltageType, ratedVoltage, raw }
  edges: [],            // parsed edge data: { name, uuid, type, bus1, bus2, raw }
  nodeComponents: [],   // parsed single-bus components: { name, uuid, type, busName, raw }
  showLabels: true,
  selectedComponent: null, // { type, name, data }
  dragTarget: null,     // bus name when dragging over a bus marker
};

// ===== Initialize Leaflet Map =====
function initNetworkMap() {
  if (networkState.map) return;

  networkState.map = L.map("networkMap", {
    center: [36.58, -120.95],
    zoom: 13,
    zoomControl: true,
    attributionControl: false,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
  }).addTo(networkState.map);

  // Toolbar buttons
  const fitBtn = document.getElementById("mapFitBtn");
  if (fitBtn) fitBtn.addEventListener("click", fitMapToBounds);

  const labelBtn = document.getElementById("mapToggleLabels");
  if (labelBtn) {
    labelBtn.addEventListener("click", () => {
      networkState.showLabels = !networkState.showLabels;
      labelBtn.classList.toggle("active", networkState.showLabels);
      toggleBusLabels();
    });
    labelBtn.classList.add("active");
  }

  // Detail panel buttons
  const editBtn = document.getElementById("detailEditBtn");
  if (editBtn) editBtn.addEventListener("click", editSelectedComponent);
  const deleteBtn = document.getElementById("detailDeleteBtn");
  if (deleteBtn) deleteBtn.addEventListener("click", deleteSelectedComponent);
  const closeBtn = document.getElementById("detailCloseBtn");
  if (closeBtn) closeBtn.addEventListener("click", closeDetailPanel);

  // Make map a drop target for palette items
  const mapEl = document.getElementById("networkMap");
  mapEl.addEventListener("dragover", (e) => e.preventDefault());
  mapEl.addEventListener("drop", handleMapDrop);
}

// ===== Parse Network Topology from GDM JSON =====
function parseNetworkTopology(data) {
  const components = data.components || [];
  const uuidMap = {};
  for (const comp of components) {
    if (comp.uuid) uuidMap[comp.uuid] = comp;
  }

  // Parse buses
  networkState.buses = [];
  for (const comp of components) {
    const typeName = comp.__metadata__?.fields?.type;
    if (typeName !== "DistributionBus") continue;

    const coordRef = comp.coordinate;
    let lat = null, lng = null;
    if (coordRef?.__metadata__?.fields?.serialized_type === "composed_component") {
      const loc = uuidMap[coordRef.__metadata__.fields.uuid];
      if (loc) {
        lat = loc.x;  // GDM stores lat in x, lng in y
        lng = loc.y;
      }
    } else if (coordRef && typeof coordRef === "object" && coordRef.x !== undefined) {
      lat = coordRef.x;
      lng = coordRef.y;
    }

    // Parse rated_voltage
    let ratedVoltage = null;
    if (comp.rated_voltage) {
      const rv = comp.rated_voltage;
      if (typeof rv === "object" && rv.value !== undefined) {
        ratedVoltage = { value: rv.value, unit: rv.units || "V" };
      }
    }

    networkState.buses.push({
      name: comp.name,
      uuid: comp.uuid,
      lat, lng,
      phases: comp.phases || [],
      voltageType: comp.voltage_type,
      ratedVoltage,
      raw: comp,
    });
  }

  // Parse edge components (branches, transformers, switches)
  const edgeTypes = new Set([
    "DistributionTransformer", "DistributionRegulator",
    "MatrixImpedanceBranch", "SequenceImpedanceBranch", "GeometryBranch",
    "MatrixImpedanceFuse", "MatrixImpedanceRecloser", "MatrixImpedanceSwitch",
  ]);
  networkState.edges = [];
  for (const comp of components) {
    const typeName = comp.__metadata__?.fields?.type;
    if (!edgeTypes.has(typeName)) continue;

    const busRefs = comp.buses || [];
    let bus1 = null, bus2 = null;
    if (busRefs.length >= 2) {
      bus1 = resolveBusName(busRefs[0], uuidMap);
      bus2 = resolveBusName(busRefs[1], uuidMap);
    }

    // Parse length
    let length = null;
    if (comp.length) {
      const l = comp.length;
      if (typeof l === "object" && l.value !== undefined) {
        length = { value: l.value, unit: l.units || "m" };
      }
    }

    // Parse phases
    let phases = comp.phases || [];

    // Parse is_closed for switches
    let isClosed = comp.is_closed;

    networkState.edges.push({
      name: comp.name,
      uuid: comp.uuid,
      type: typeName,
      bus1, bus2,
      phases,
      length,
      isClosed,
      raw: comp,
    });
  }

  // Parse single-bus node components (loads, solar, battery, capacitor, vsource)
  const nodeTypes = new Set([
    "DistributionLoad", "DistributionSolar", "DistributionBattery",
    "DistributionCapacitor", "DistributionVoltageSource",
  ]);
  networkState.nodeComponents = [];
  for (const comp of components) {
    const typeName = comp.__metadata__?.fields?.type;
    if (!nodeTypes.has(typeName)) continue;

    const busRef = comp.bus;
    const busName = resolveBusName(busRef, uuidMap);

    networkState.nodeComponents.push({
      name: comp.name,
      uuid: comp.uuid,
      type: typeName,
      busName,
      phases: comp.phases || [],
      raw: comp,
    });
  }
}

function resolveBusName(busRef, uuidMap) {
  if (!busRef) return null;
  if (typeof busRef === "string") {
    const resolved = uuidMap[busRef];
    return resolved?.name || busRef;
  }
  if (busRef.__metadata__?.fields?.serialized_type === "composed_component") {
    const resolved = uuidMap[busRef.__metadata__.fields.uuid];
    return resolved?.name || null;
  }
  return busRef.name || null;
}

// ===== Render Network on Map =====
function renderNetwork() {
  if (!networkState.map) return;

  clearMapLayers();

  const busLookup = {};
  for (const bus of networkState.buses) {
    busLookup[bus.name] = bus;
  }

  // Check which buses have specific attached components
  const busAttachments = {};
  for (const nc of networkState.nodeComponents) {
    if (!busAttachments[nc.busName]) busAttachments[nc.busName] = [];
    busAttachments[nc.busName].push(nc);
  }

  // Draw edges first (lines)
  for (const edge of networkState.edges) {
    const b1 = busLookup[edge.bus1];
    const b2 = busLookup[edge.bus2];
    if (!b1 || !b2 || b1.lat == null || b2.lat == null) continue;

    const isSwitch = edge.type.includes("Switch") || edge.type.includes("Fuse") || edge.type.includes("Recloser");
    const isTransformer = edge.type.includes("Transformer") || edge.type.includes("Regulator");

    let color = "#6fcf6f";
    let weight = 3;
    let dashArray = null;

    if (isTransformer) {
      color = "#f0a030";
      weight = 4;
    } else if (isSwitch) {
      color = "#e54d4d";
      weight = 3;
      // Dashed if open
      if (edge.isClosed && Array.isArray(edge.isClosed) && !edge.isClosed.every(v => v)) {
        dashArray = "8, 6";
      }
    }

    const line = L.polyline(
      [[b1.lat, b1.lng], [b2.lat, b2.lng]],
      { color, weight, opacity: 0.8, dashArray }
    ).addTo(networkState.map);

    line.on("click", () => {
      selectNetworkComponent("edge", edge);
    });

    line.bindTooltip(
      `<strong>${escapeHtml(edge.name)}</strong><br>${COMPONENT_SCHEMAS[edge.type]?.label || edge.type}`,
      { sticky: true, className: "bus-label" }
    );

    networkState.edgeLines[edge.name] = line;
  }

  // Draw bus markers
  for (const bus of networkState.buses) {
    if (bus.lat == null || bus.lng == null) continue;

    // Determine bus style based on attachments
    let extraClass = "";
    const attached = busAttachments[bus.name] || [];
    const hasSource = attached.some(c => c.type === "DistributionVoltageSource");
    const hasSolar = attached.some(c => c.type === "DistributionSolar");
    const hasLoad = attached.some(c => c.type === "DistributionLoad");

    if (hasSource) extraClass = " source";
    else if (hasSolar) extraClass = " has-solar";
    else if (hasLoad) extraClass = " has-load";

    const busIcon = L.divIcon({
      className: `bus-marker${extraClass}`,
      iconSize: [14, 14],
    });

    const marker = L.marker([bus.lat, bus.lng], { icon: busIcon }).addTo(networkState.map);

    marker.on("click", () => {
      selectNetworkComponent("bus", bus);
    });

    // Make bus a drop target
    marker.getElement()?.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      marker.getElement().classList.add("drop-target");
      networkState.dragTarget = bus.name;
    });
    marker.getElement()?.addEventListener("dragleave", () => {
      marker.getElement().classList.remove("drop-target");
      networkState.dragTarget = null;
    });
    marker.getElement()?.addEventListener("drop", (e) => {
      e.preventDefault();
      e.stopPropagation();
      marker.getElement().classList.remove("drop-target");
      const compType = e.dataTransfer.getData("text/plain");
      if (compType) {
        handleComponentDrop(compType, bus);
      }
      networkState.dragTarget = null;
    });

    networkState.busMarkers[bus.name] = marker;

    // Label
    if (networkState.showLabels) {
      const label = L.marker([bus.lat, bus.lng], {
        icon: L.divIcon({
          className: "bus-label",
          html: escapeHtml(bus.name),
          iconAnchor: [-10, 6],
        }),
        interactive: false,
      }).addTo(networkState.map);
      networkState.busLabels[bus.name] = label;
    }
  }

  // Draw node component markers offset from buses
  for (const nc of networkState.nodeComponents) {
    const bus = busLookup[nc.busName];
    if (!bus || bus.lat == null) continue;

    const siblings = busAttachments[nc.busName] || [];
    const idx = siblings.indexOf(nc);
    const total = siblings.length;
    // Offset in a fan around the bus
    const angle = (idx / Math.max(total, 1)) * Math.PI * 2 - Math.PI / 2;
    const offsetDist = 0.0004;
    const lat = bus.lat + Math.sin(angle) * offsetDist;
    const lng = bus.lng + Math.cos(angle) * offsetDist;

    let markerClass = "component-marker";
    if (nc.type === "DistributionLoad") markerClass += " load";
    else if (nc.type === "DistributionSolar") markerClass += " solar";
    else if (nc.type === "DistributionBattery") markerClass += " battery";
    else if (nc.type === "DistributionCapacitor") markerClass += " capacitor";
    else if (nc.type === "DistributionVoltageSource") markerClass += " source";

    const iconHtml = `<i class="${COMPONENT_ICONS[nc.type] || "ri-box-3-line"}"></i>`;
    const compIcon = L.divIcon({
      className: markerClass,
      html: iconHtml,
      iconSize: [22, 22],
    });

    const compMarker = L.marker([lat, lng], { icon: compIcon }).addTo(networkState.map);
    compMarker.on("click", () => {
      selectNetworkComponent("node", nc);
    });

    // Draw a thin line from component to its bus
    L.polyline(
      [[bus.lat, bus.lng], [lat, lng]],
      { color: "#3a3e52", weight: 1, opacity: 0.5, dashArray: "3, 3" }
    ).addTo(networkState.map);

    networkState.componentMarkers[nc.name] = compMarker;
  }

  // Hide empty state
  const emptyState = document.getElementById("networkEmptyState");
  if (emptyState && networkState.buses.length > 0) {
    emptyState.classList.add("hidden");
  }

  fitMapToBounds();
}

function clearMapLayers() {
  Object.values(networkState.busMarkers).forEach(m => m.remove());
  Object.values(networkState.busLabels).forEach(m => m.remove());
  Object.values(networkState.edgeLines).forEach(l => l.remove());
  Object.values(networkState.componentMarkers).forEach(m => m.remove());
  networkState.busMarkers = {};
  networkState.busLabels = {};
  networkState.edgeLines = {};
  networkState.componentMarkers = {};

  // Also remove connection lines (thin dashed)
  networkState.map.eachLayer(layer => {
    if (layer instanceof L.Polyline && !(layer instanceof L.TileLayer)) {
      // Only remove non-edge polylines
      const isEdge = Object.values(networkState.edgeLines).includes(layer);
      if (!isEdge) layer.remove();
    }
  });
}

function fitMapToBounds() {
  if (!networkState.map) return;
  const points = networkState.buses.filter(b => b.lat != null).map(b => [b.lat, b.lng]);
  if (points.length === 0) return;
  const bounds = L.latLngBounds(points);
  networkState.map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
}

function toggleBusLabels() {
  if (networkState.showLabels) {
    for (const bus of networkState.buses) {
      if (bus.lat == null || networkState.busLabels[bus.name]) continue;
      const label = L.marker([bus.lat, bus.lng], {
        icon: L.divIcon({
          className: "bus-label",
          html: escapeHtml(bus.name),
          iconAnchor: [-10, 6],
        }),
        interactive: false,
      }).addTo(networkState.map);
      networkState.busLabels[bus.name] = label;
    }
  } else {
    Object.values(networkState.busLabels).forEach(m => m.remove());
    networkState.busLabels = {};
  }
}

// ===== Select & Inspect Component =====
function selectNetworkComponent(kind, item) {
  const panel = document.getElementById("networkDetailSection");
  const title = document.getElementById("detailTitle");
  const body = document.getElementById("detailBody");
  if (!panel || !title || !body) return;

  panel.style.display = "block";
  networkState.selectedComponent = { kind, item };

  if (kind === "bus") {
    title.innerHTML = `<i class="${COMPONENT_ICONS.DistributionBus}" style="margin-right:6px;color:#5b67f5"></i>${escapeHtml(item.name)}`;

    const phasesStr = (item.phases || []).join(", ");
    const rvDisplay = item.ratedVoltage
      ? `${formatNumber(item.ratedVoltage.value)}<span class="unit">${item.ratedVoltage.unit}</span>`
      : "—";

    // List attached components
    const attached = networkState.nodeComponents.filter(nc => nc.busName === item.name);
    let attachedHtml = "";
    if (attached.length > 0) {
      attachedHtml = `<div style="margin-top:12px"><div class="field-label" style="margin-bottom:8px">CONNECTED COMPONENTS</div>`;
      for (const nc of attached) {
        const icon = COMPONENT_ICONS[nc.type] || "ri-box-3-line";
        attachedHtml += `<div class="field-item" style="margin-bottom:4px;cursor:pointer" data-click-comp="${nc.name}" data-click-kind="node"><i class="${icon}" style="margin-right:6px;color:#7c8aff"></i>${escapeHtml(nc.name)} <span style="color:#6b7084;font-size:0.75rem">(${COMPONENT_SCHEMAS[nc.type]?.label || nc.type})</span></div>`;
      }
      attachedHtml += `</div>`;
    }

    body.innerHTML = `
      <div class="field-grid">
        <div class="field-item"><div class="field-label">Type</div><div class="field-value">Distribution Bus</div></div>
        <div class="field-item"><div class="field-label">Voltage Type</div><div class="field-value" style="color:#a8b0ff">${item.voltageType || "—"}</div></div>
        <div class="field-item"><div class="field-label">Phases</div><div class="field-value">${phasesStr || "—"}</div></div>
        <div class="field-item"><div class="field-label">Rated Voltage</div><div class="field-value">${rvDisplay}</div></div>
        <div class="field-item"><div class="field-label">Latitude</div><div class="field-value">${item.lat != null ? formatNumber(item.lat) : "—"}</div></div>
        <div class="field-item"><div class="field-label">Longitude</div><div class="field-value">${item.lng != null ? formatNumber(item.lng) : "—"}</div></div>
      </div>
      ${attachedHtml}
    `;

    // Click handlers for attached components
    body.querySelectorAll("[data-click-comp]").forEach(el => {
      el.addEventListener("click", () => {
        const nc = networkState.nodeComponents.find(c => c.name === el.dataset.clickComp);
        if (nc) selectNetworkComponent("node", nc);
      });
    });

  } else if (kind === "edge") {
    title.innerHTML = `<i class="${COMPONENT_ICONS[item.type] || "ri-git-branch-line"}" style="margin-right:6px;color:#5b67f5"></i>${escapeHtml(item.name)}`;

    const phasesStr = (item.phases || []).join(", ");
    const lengthDisplay = item.length
      ? `${formatNumber(item.length.value)}<span class="unit">${item.length.unit}</span>`
      : "—";
    const closedStr = item.isClosed
      ? (Array.isArray(item.isClosed) ? item.isClosed.map(v => v ? "Closed" : "Open").join(", ") : String(item.isClosed))
      : "—";

    body.innerHTML = `
      <div class="field-grid">
        <div class="field-item"><div class="field-label">Type</div><div class="field-value">${COMPONENT_SCHEMAS[item.type]?.label || item.type}</div></div>
        <div class="field-item"><div class="field-label">From Bus</div><div class="field-value">${escapeHtml(item.bus1 || "—")}</div></div>
        <div class="field-item"><div class="field-label">To Bus</div><div class="field-value">${escapeHtml(item.bus2 || "—")}</div></div>
        <div class="field-item"><div class="field-label">Phases</div><div class="field-value">${phasesStr || "—"}</div></div>
        <div class="field-item"><div class="field-label">Length</div><div class="field-value">${lengthDisplay}</div></div>
        <div class="field-item"><div class="field-label">Status</div><div class="field-value">${closedStr}</div></div>
      </div>
    `;

  } else if (kind === "node") {
    title.innerHTML = `<i class="${COMPONENT_ICONS[item.type] || "ri-box-3-line"}" style="margin-right:6px;color:#5b67f5"></i>${escapeHtml(item.name)}`;

    const phasesStr = (item.phases || []).join(", ");

    body.innerHTML = `
      <div class="field-grid">
        <div class="field-item"><div class="field-label">Type</div><div class="field-value">${COMPONENT_SCHEMAS[item.type]?.label || item.type}</div></div>
        <div class="field-item"><div class="field-label">Bus</div><div class="field-value">${escapeHtml(item.busName || "—")}</div></div>
        <div class="field-item"><div class="field-label">Phases</div><div class="field-value">${phasesStr || "—"}</div></div>
      </div>
    `;
  }
}

function closeDetailPanel() {
  const panel = document.getElementById("networkDetailSection");
  if (panel) panel.style.display = "none";
  networkState.selectedComponent = null;
}

// ===== Edit Selected Component =====
function editSelectedComponent() {
  const sel = networkState.selectedComponent;
  if (!sel) return;

  const compType = sel.kind === "bus" ? "DistributionBus" : sel.item.type;
  const schema = COMPONENT_SCHEMAS[compType];
  if (!schema) {
    toast("No editable schema for this component type", "error");
    return;
  }

  openNetworkEditModal(compType, schema, sel);
}

function openNetworkEditModal(compType, schema, selection) {
  const title = document.getElementById("modalTitle");
  const body = document.getElementById("modalBody");
  title.textContent = `Edit ${schema.label}`;
  body.innerHTML = "";

  // Build the form using component schema fields
  const data = {};
  const rawItem = selection.item;

  // Pre-populate from raw data
  if (selection.kind === "bus") {
    data.name = rawItem.name;
    data.voltage_type = rawItem.voltageType;
    data.phases = rawItem.phases;
    data.rated_voltage = rawItem.ratedVoltage;
  } else if (selection.kind === "node" || selection.kind === "edge") {
    data.name = rawItem.name;
    data.phases = rawItem.phases;
    if (rawItem.length) data.length = rawItem.length;
    if (rawItem.isClosed) data.is_closed = rawItem.isClosed;
    if (rawItem.bus1) data._bus1 = rawItem.bus1;
    if (rawItem.bus2) data._bus2 = rawItem.bus2;
    if (rawItem.busName) data._bus = rawItem.busName;
  }

  const form = buildComponentForm(schema.fields, data, compType);
  body.appendChild(form);

  // Override save handler
  const saveBtn = document.getElementById("modalSave");
  const newSave = saveBtn.cloneNode(true);
  saveBtn.parentNode.replaceChild(newSave, saveBtn);
  newSave.addEventListener("click", () => {
    const formData = collectFormData();
    // Apply changes to the in-memory item
    if (selection.kind === "bus") {
      const bus = networkState.buses.find(b => b.name === rawItem.name);
      if (bus) {
        if (formData.name) bus.name = formData.name;
        if (formData.voltage_type) bus.voltageType = formData.voltage_type;
        if (formData.rated_voltage) bus.ratedVoltage = formData.rated_voltage;
      }
    } else if (selection.kind === "node") {
      const nc = networkState.nodeComponents.find(c => c.name === rawItem.name);
      if (nc && formData.name) nc.name = formData.name;
    } else if (selection.kind === "edge") {
      const edge = networkState.edges.find(e => e.name === rawItem.name);
      if (edge) {
        if (formData.name) edge.name = formData.name;
        if (formData.length) edge.length = formData.length;
      }
    }

    closeModal("modalOverlay");
    renderNetwork();
    toast(`${schema.label} updated`, "success");
  });

  openModal("modalOverlay");
}

// ===== Delete Selected Component =====
function deleteSelectedComponent() {
  const sel = networkState.selectedComponent;
  if (!sel) return;

  const name = sel.kind === "bus" ? sel.item.name : sel.item.name;
  const label = sel.kind === "bus"
    ? "Distribution Bus"
    : (COMPONENT_SCHEMAS[sel.item.type]?.label || sel.item.type);

  document.getElementById("deleteMessage").textContent = `Delete "${name}" (${label})?`;

  const confirmBtn = document.getElementById("deleteConfirmBtn");
  const newConfirm = confirmBtn.cloneNode(true);
  confirmBtn.parentNode.replaceChild(newConfirm, confirmBtn);
  newConfirm.addEventListener("click", () => {
    if (sel.kind === "bus") {
      networkState.buses = networkState.buses.filter(b => b.name !== sel.item.name);
      // Remove attached components
      networkState.nodeComponents = networkState.nodeComponents.filter(nc => nc.busName !== sel.item.name);
      // Remove edges referencing this bus
      networkState.edges = networkState.edges.filter(e => e.bus1 !== sel.item.name && e.bus2 !== sel.item.name);
    } else if (sel.kind === "node") {
      networkState.nodeComponents = networkState.nodeComponents.filter(nc => nc.name !== sel.item.name);
    } else if (sel.kind === "edge") {
      networkState.edges = networkState.edges.filter(e => e.name !== sel.item.name);
    }

    closeModal("deleteOverlay");
    closeDetailPanel();
    renderNetwork();
    toast(`${label} deleted`, "success");
  });

  openModal("deleteOverlay");
}

// ===== Drag & Drop from Palette =====
function setupPaletteDrag() {
  document.querySelectorAll(".palette-item[draggable]").forEach(item => {
    item.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", item.dataset.compType);
      e.dataTransfer.effectAllowed = "copy";
    });
  });
}

function handleMapDrop(e) {
  e.preventDefault();
  const compType = e.dataTransfer.getData("text/plain");
  if (!compType) return;

  // If no bus target was detected (dropped on map background)
  if (compType === "DistributionBus") {
    // Create a new bus at this location
    const latlng = networkState.map.containerPointToLatLng(L.point(e.offsetX, e.offsetY));
    openNewBusModal(latlng.lat, latlng.lng);
    return;
  }

  // For dual-bus components dropped on map (not on a specific bus), prompt for bus selection
  const schema = COMPONENT_SCHEMAS[compType];
  if (!schema) return;

  if (schema.busMode === "dual") {
    openNewDualBusComponentModal(compType);
  } else {
    // Single-bus component needs a target bus
    toast("Drop on a bus node to connect this component", "info");
  }
}

function handleComponentDrop(compType, targetBus) {
  const schema = COMPONENT_SCHEMAS[compType];
  if (!schema) return;

  if (compType === "DistributionBus") {
    // Can't drop a bus on a bus
    toast("Buses can only be placed on empty map space", "info");
    return;
  }

  if (schema.busMode === "dual") {
    openNewDualBusComponentModal(compType, targetBus.name);
  } else {
    openNewSingleBusComponentModal(compType, targetBus.name);
  }
}

// ===== New Component Modals =====
function openNewBusModal(lat, lng) {
  const schema = COMPONENT_SCHEMAS.DistributionBus;
  const title = document.getElementById("modalTitle");
  const body = document.getElementById("modalBody");
  title.textContent = "Add Distribution Bus";
  body.innerHTML = "";

  const data = { name: `bus_${networkState.buses.length + 1}` };
  const form = buildComponentForm(schema.fields, data, "DistributionBus");
  body.appendChild(form);

  // Add coordinate display
  const coordDiv = document.createElement("div");
  coordDiv.className = "form-group";
  coordDiv.innerHTML = `<label class="form-label">Location</label><div style="display:flex;gap:8px"><div class="field-item" style="flex:1"><div class="field-label">Latitude</div><div class="field-value">${formatNumber(lat)}</div></div><div class="field-item" style="flex:1"><div class="field-label">Longitude</div><div class="field-value">${formatNumber(lng)}</div></div></div>`;
  body.appendChild(coordDiv);

  const saveBtn = document.getElementById("modalSave");
  const newSave = saveBtn.cloneNode(true);
  saveBtn.parentNode.replaceChild(newSave, saveBtn);
  newSave.addEventListener("click", () => {
    const formData = collectFormData();
    if (!formData.name) { toast("Name is required", "error"); return; }

    networkState.buses.push({
      name: formData.name,
      uuid: crypto.randomUUID(),
      lat, lng,
      phases: formData.phases || [],
      voltageType: formData.voltage_type,
      ratedVoltage: formData.rated_voltage,
      raw: formData,
    });

    closeModal("modalOverlay");
    renderNetwork();
    toast("Bus added", "success");
  });

  openModal("modalOverlay");
}

function openNewSingleBusComponentModal(compType, busName) {
  const schema = COMPONENT_SCHEMAS[compType];
  if (!schema) return;

  const title = document.getElementById("modalTitle");
  const body = document.getElementById("modalBody");
  title.textContent = `Add ${schema.label}`;
  body.innerHTML = "";

  // Show target bus
  const busInfo = document.createElement("div");
  busInfo.className = "form-group";
  busInfo.innerHTML = `<label class="form-label">Connected Bus</label><div class="field-item"><div class="field-value" style="color:#5b67f5"><i class="ri-circle-line" style="margin-right:6px"></i>${escapeHtml(busName)}</div></div>`;
  body.appendChild(busInfo);

  const data = { name: `${compType.replace("Distribution", "").toLowerCase()}_${busName}` };
  const form = buildComponentForm(schema.fields, data, compType);
  body.appendChild(form);

  const saveBtn = document.getElementById("modalSave");
  const newSave = saveBtn.cloneNode(true);
  saveBtn.parentNode.replaceChild(newSave, saveBtn);
  newSave.addEventListener("click", () => {
    const formData = collectFormData();
    if (!formData.name) { toast("Name is required", "error"); return; }

    networkState.nodeComponents.push({
      name: formData.name,
      uuid: crypto.randomUUID(),
      type: compType,
      busName,
      phases: formData.phases || [],
      raw: formData,
    });

    closeModal("modalOverlay");
    renderNetwork();
    toast(`${schema.label} added to ${busName}`, "success");
  });

  openModal("modalOverlay");
}

function openNewDualBusComponentModal(compType, preselectedBus) {
  const schema = COMPONENT_SCHEMAS[compType];
  if (!schema) return;

  const title = document.getElementById("modalTitle");
  const body = document.getElementById("modalBody");
  title.textContent = `Add ${schema.label}`;
  body.innerHTML = "";

  // Bus selectors
  const busNames = networkState.buses.map(b => b.name);
  const busGroup = document.createElement("div");
  busGroup.className = "form-group";
  busGroup.innerHTML = `<label class="form-label">Connected Buses <span class="required">*</span></label>`;
  const busRow = document.createElement("div");
  busRow.style.cssText = "display:flex;gap:8px";

  const bus1Select = document.createElement("select");
  bus1Select.className = "form-select";
  bus1Select.dataset.field = "_bus1";
  bus1Select.innerHTML = `<option value="">— From Bus —</option>` + busNames.map(n => `<option value="${escapeHtml(n)}" ${n === preselectedBus ? "selected" : ""}>${escapeHtml(n)}</option>`).join("");
  busRow.appendChild(bus1Select);

  const bus2Select = document.createElement("select");
  bus2Select.className = "form-select";
  bus2Select.dataset.field = "_bus2";
  bus2Select.innerHTML = `<option value="">— To Bus —</option>` + busNames.map(n => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join("");
  busRow.appendChild(bus2Select);

  busGroup.appendChild(busRow);
  body.appendChild(busGroup);

  const data = { name: `${compType.replace("Distribution", "").replace("MatrixImpedance", "").replace("SequenceImpedance", "").replace("Geometry", "").toLowerCase()}_new` };
  const form = buildComponentForm(schema.fields, data, compType);
  body.appendChild(form);

  const saveBtn = document.getElementById("modalSave");
  const newSave = saveBtn.cloneNode(true);
  saveBtn.parentNode.replaceChild(newSave, saveBtn);
  newSave.addEventListener("click", () => {
    const formData = collectFormData();
    if (!formData.name) { toast("Name is required", "error"); return; }
    const b1 = bus1Select.value;
    const b2 = bus2Select.value;
    if (!b1 || !b2) { toast("Select both buses", "error"); return; }
    if (b1 === b2) { toast("Buses must be different", "error"); return; }

    networkState.edges.push({
      name: formData.name,
      uuid: crypto.randomUUID(),
      type: compType,
      bus1: b1,
      bus2: b2,
      phases: formData.phases || [],
      length: formData.length || null,
      isClosed: formData.is_closed || null,
      raw: formData,
    });

    closeModal("modalOverlay");
    renderNetwork();
    toast(`${schema.label} added`, "success");
  });

  openModal("modalOverlay");
}

// ===== Build Component Form =====
function buildComponentForm(fields, data, compType) {
  const frag = document.createDocumentFragment();

  for (const [key, fieldDef] of Object.entries(fields)) {
    if (fieldDef.type === "phase_select") {
      frag.appendChild(buildPhaseSelectField(key, fieldDef, data[key]));
    } else if (fieldDef.type === "equipment_ref") {
      frag.appendChild(buildEquipmentRefField(key, fieldDef, data[key]));
    } else if (fieldDef.type === "array_bool") {
      frag.appendChild(buildArrayBoolField(key, fieldDef, data[key]));
    } else if (fieldDef.type === "winding_phases") {
      frag.appendChild(buildWindingPhasesField(key, fieldDef, data[key]));
    } else {
      // Delegate to existing buildField from app.js
      frag.appendChild(buildField(key, fieldDef, data[key]));
    }
  }

  return frag;
}

function buildPhaseSelectField(key, fieldDef, value) {
  const group = document.createElement("div");
  group.className = "form-group";
  const reqMark = fieldDef.required ? ' <span class="required">*</span>' : "";
  group.innerHTML = `<label class="form-label">${key.replace(/_/g, " ")}${reqMark}<span class="field-desc">${fieldDef.description || ""}</span></label>`;

  const container = document.createElement("div");
  container.style.cssText = "display:flex;gap:6px;flex-wrap:wrap";
  container.dataset.field = key;
  container.dataset.fieldType = "phase_select";

  const allPhases = ["A", "B", "C", "N", "S1", "S2"];
  const selectedPhases = Array.isArray(value) ? value : [];

  for (const phase of allPhases) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-sm " + (selectedPhases.includes(phase) ? "btn-primary" : "btn-outline");
    btn.textContent = phase;
    btn.dataset.phase = phase;
    btn.addEventListener("click", () => {
      btn.classList.toggle("btn-primary");
      btn.classList.toggle("btn-outline");
    });
    container.appendChild(btn);
  }

  group.appendChild(container);
  return group;
}

function buildEquipmentRefField(key, fieldDef, value) {
  const group = document.createElement("div");
  group.className = "form-group";
  const reqMark = fieldDef.required ? ' <span class="required">*</span>' : "";
  group.innerHTML = `<label class="form-label">${key.replace(/_/g, " ")}${reqMark}<span class="field-desc">${fieldDef.description || ""}</span></label>`;

  const select = document.createElement("select");
  select.className = "form-select";
  select.dataset.field = key;
  select.dataset.fieldType = "equipment_ref";

  // Get available equipment from warehouse state
  const equipType = fieldDef.equipmentType;
  const items = state.equipment[equipType] || [];
  const schema = SCHEMAS[equipType];
  const label = schema?.label || equipType;

  select.innerHTML = `<option value="">— Select ${label} —</option>`;
  for (const item of items) {
    const name = item.data.name || item.uuid || `${label} #${item.id}`;
    select.innerHTML += `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`;
  }

  if (items.length === 0) {
    select.innerHTML += `<option value="" disabled>No ${label} in warehouse</option>`;
  }

  group.appendChild(select);
  return group;
}

function buildArrayBoolField(key, fieldDef, value) {
  const group = document.createElement("div");
  group.className = "form-group";
  const reqMark = fieldDef.required ? ' <span class="required">*</span>' : "";
  group.innerHTML = `<label class="form-label">${key.replace(/_/g, " ")}${reqMark}<span class="field-desc">${fieldDef.description || ""}</span></label>`;

  const container = document.createElement("div");
  container.style.cssText = "display:flex;gap:6px";
  container.dataset.field = key;
  container.dataset.fieldType = "array_bool";

  const phases = ["A", "B", "C"];
  const vals = Array.isArray(value) ? value : [true, true, true];

  for (let i = 0; i < phases.length; i++) {
    const btn = document.createElement("button");
    btn.type = "button";
    const isOn = vals[i] !== false;
    btn.className = `btn btn-sm ${isOn ? "btn-primary" : "btn-outline"}`;
    btn.textContent = `${phases[i]}: ${isOn ? "Closed" : "Open"}`;
    btn.dataset.boolIdx = i;
    btn.addEventListener("click", () => {
      const on = btn.classList.contains("btn-primary");
      btn.classList.toggle("btn-primary", !on);
      btn.classList.toggle("btn-outline", on);
      btn.textContent = `${phases[i]}: ${!on ? "Closed" : "Open"}`;
    });
    container.appendChild(btn);
  }

  group.appendChild(container);
  return group;
}

function buildWindingPhasesField(key, fieldDef, value) {
  const group = document.createElement("div");
  group.className = "form-group";
  group.innerHTML = `<label class="form-label">winding phases <span class="required">*</span><span class="field-desc">Phases per winding (comma-separated per winding, semicolon between windings)</span></label>`;

  const input = document.createElement("input");
  input.type = "text";
  input.className = "form-input";
  input.dataset.field = key;
  input.dataset.fieldType = "winding_phases";
  input.placeholder = "e.g. A,B,C ; A,B,C";
  if (Array.isArray(value)) {
    input.value = value.map(w => Array.isArray(w) ? w.join(",") : w).join(" ; ");
  }
  group.appendChild(input);
  return group;
}

// Extend collectFormData to handle new field types
const originalCollectFormData = collectFormData;
collectFormData = function() {
  const data = originalCollectFormData();

  // Handle phase_select fields
  document.querySelectorAll("#modalBody [data-field-type='phase_select']").forEach(container => {
    const key = container.dataset.field;
    const phases = [];
    container.querySelectorAll(".btn-primary").forEach(btn => {
      if (btn.dataset.phase) phases.push(btn.dataset.phase);
    });
    data[key] = phases;
  });

  // Handle array_bool fields
  document.querySelectorAll("#modalBody [data-field-type='array_bool']").forEach(container => {
    const key = container.dataset.field;
    const vals = [];
    container.querySelectorAll("[data-bool-idx]").forEach(btn => {
      vals.push(btn.classList.contains("btn-primary"));
    });
    data[key] = vals;
  });

  // Handle winding_phases
  document.querySelectorAll("#modalBody [data-field-type='winding_phases']").forEach(el => {
    const key = el.dataset.field;
    if (el.value) {
      data[key] = el.value.split(";").map(w => w.trim().split(",").map(p => p.trim()));
    }
  });

  return data;
};

// ===== Hook into system load =====
const originalLoadFile = loadFile;
loadFile = function(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      state.system = data;
      parseEquipment(data);
      showSystemSummary(file.name);

      // Parse and render network
      parseNetworkTopology(data);
      if (networkState.map) {
        renderNetwork();
      }

      toast("System loaded successfully", "success");
    } catch (err) {
      toast("Failed to parse JSON: " + err.message, "error");
    }
  };
  reader.readAsText(file);
};

// ===== Hook into unload =====
const origUnloadHandler = document.getElementById("unloadBtn").onclick;
document.getElementById("unloadBtn").addEventListener("click", () => {
  networkState.buses = [];
  networkState.edges = [];
  networkState.nodeComponents = [];
  if (networkState.map) {
    clearMapLayers();
    const emptyState = document.getElementById("networkEmptyState");
    if (emptyState) emptyState.classList.remove("hidden");
  }
  closeDetailPanel();
});

// ===== Hook into page navigation =====
const origNavHandler = $$(".nav-item");
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    if (item.dataset.page === "network") {
      setTimeout(() => {
        initNetworkMap();
        if (networkState.buses.length > 0) {
          renderNetwork();
        }
        networkState.map?.invalidateSize();
      }, 100);
    }
  });
});

// ===== Init palette drag =====
setupPaletteDrag();
