/**
 * GDM Studio – Scenarios / Timeline Module
 * Visualise tracked changes on a GIS map with a timeline slider.
 * Requires a loaded DistributionSystem (via app.js) + a tracked changes JSON.
 */

// ===== Scenario State =====
const scenarioState = {
  map: null,
  trackedChanges: [],       // parsed list of change objects
  timelineSteps: [],        // sorted unique timestamps (+ "base" at index 0)
  currentStep: 0,           // index into timelineSteps
  playing: false,
  playInterval: null,

  // Cloned from the network parser for independent rendering
  buses: [],
  edges: [],
  nodeComponents: [],

  // Map layers
  busMarkers: {},
  busLabels: {},
  edgeLines: {},
  componentMarkers: {},
  connectionLines: [],      // thin dashed lines from comp to bus
  showLabels: true,

  // Diff tracking: what's changed at each step
  stepDiffs: [],             // [{additions:[], deletions:[], edits:[]}] per step
  // Cumulative state at current step
  addedUUIDs: new Set(),
  deletedUUIDs: new Set(),
  editedUUIDs: new Set(),

  // NEW components defined in additions (with full data for rendering)
  addedComponents: [],       // full objects from tracked changes additions
  addedBuses: [],
  addedEdges: [],
  addedNodeComponents: [],
};

// ===== Initialise Scenario Map =====
function initScenarioMap() {
  if (scenarioState.map) return;

  scenarioState.map = L.map("scenarioMap", {
    center: [36.58, -120.95],
    zoom: 13,
    zoomControl: false,
    attributionControl: false,
  });

  L.control.zoom({ position: "bottomleft" }).addTo(scenarioState.map);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
  }).addTo(scenarioState.map);

  // Toolbar buttons
  const fitBtn = document.getElementById("scenarioFitBtn");
  if (fitBtn) fitBtn.addEventListener("click", scenarioFitBounds);

  const labelBtn = document.getElementById("scenarioToggleLabels");
  if (labelBtn) {
    labelBtn.addEventListener("click", () => {
      scenarioState.showLabels = !scenarioState.showLabels;
      labelBtn.classList.toggle("active", scenarioState.showLabels);
      renderScenarioAtStep(scenarioState.currentStep);
    });
  }

  // File input
  const loadBtn = document.getElementById("scenarioLoadBtn");
  const fileInput = document.getElementById("scenarioFileInput");
  if (loadBtn && fileInput) {
    loadBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
      if (fileInput.files.length) loadTrackedChangesFile(fileInput.files[0]);
    });
  }

  // Timeline controls
  const slider = document.getElementById("timelineSlider");
  if (slider) slider.addEventListener("input", () => {
    scenarioState.currentStep = parseInt(slider.value, 10);
    renderScenarioAtStep(scenarioState.currentStep);
  });

  document.getElementById("timelinePrev")?.addEventListener("click", () => {
    if (scenarioState.currentStep > 0) {
      scenarioState.currentStep--;
      document.getElementById("timelineSlider").value = scenarioState.currentStep;
      renderScenarioAtStep(scenarioState.currentStep);
    }
  });

  document.getElementById("timelineNext")?.addEventListener("click", () => {
    if (scenarioState.currentStep < scenarioState.timelineSteps.length - 1) {
      scenarioState.currentStep++;
      document.getElementById("timelineSlider").value = scenarioState.currentStep;
      renderScenarioAtStep(scenarioState.currentStep);
    }
  });

  document.getElementById("timelinePlay")?.addEventListener("click", togglePlay);
}

// ===== Play / Pause =====
function togglePlay() {
  const btn = document.getElementById("timelinePlay");
  if (scenarioState.playing) {
    clearInterval(scenarioState.playInterval);
    scenarioState.playing = false;
    btn.innerHTML = '<i class="ri-play-fill"></i>';
    btn.classList.remove("active");
  } else {
    scenarioState.playing = true;
    btn.innerHTML = '<i class="ri-pause-fill"></i>';
    btn.classList.add("active");
    scenarioState.playInterval = setInterval(() => {
      if (scenarioState.currentStep < scenarioState.timelineSteps.length - 1) {
        scenarioState.currentStep++;
        document.getElementById("timelineSlider").value = scenarioState.currentStep;
        renderScenarioAtStep(scenarioState.currentStep);
      } else {
        togglePlay(); // stop at end
      }
    }, 1500);
  }
}

// ===== Load Tracked Changes JSON =====
function loadTrackedChangesFile(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      if (!Array.isArray(data)) {
        toast("Invalid format – expected an array of tracked changes", "error");
        return;
      }
      processTrackedChanges(data);
    } catch (err) {
      toast("Failed to parse tracked changes JSON: " + err.message, "error");
    }
  };
  reader.readAsText(file);
}

// ===== Process Tracked Changes =====
function processTrackedChanges(changes) {
  if (!state.system) {
    toast("Load a GDM system first before loading tracked changes", "error");
    return;
  }

  scenarioState.trackedChanges = changes;

  // Sort by timestamp
  changes.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  // Build timeline steps: base (null) + each unique timestamp
  const timestamps = ["base"];
  for (const ch of changes) {
    const ts = ch.timestamp;
    if (ts && !timestamps.includes(ts)) timestamps.push(ts);
  }
  scenarioState.timelineSteps = timestamps;

  // Build per-step diffs
  scenarioState.stepDiffs = [{ additions: [], deletions: [], edits: [] }]; // base has no diff
  for (let i = 1; i < timestamps.length; i++) {
    const ts = timestamps[i];
    const matchingChanges = changes.filter(c => c.timestamp === ts);
    const additions = [];
    const deletions = [];
    const edits = [];
    for (const mc of matchingChanges) {
      for (const a of (mc.additions || [])) additions.push(a);
      for (const d of (mc.deletions || [])) deletions.push(d);
      for (const e of (mc.edits || [])) edits.push(e);
    }
    scenarioState.stepDiffs.push({ additions, deletions, edits });
  }

  // Parse base network from the loaded system (re-use network parser)
  parseBaseNetworkForScenario();

  // Collect all "added" components from tracked changes (they carry embedded data)
  scenarioState.addedComponents = [];
  for (const ch of changes) {
    for (const a of (ch.additions || [])) {
      scenarioState.addedComponents.push(a);
    }
  }

  // Classify added components
  classifyAddedComponents();

  // Setup slider
  const slider = document.getElementById("timelineSlider");
  slider.max = timestamps.length - 1;
  slider.value = 0;

  // Build tick marks
  buildTimelineTicks();

  // Show timeline bar + side panel
  document.getElementById("timelineBar").style.display = "flex";
  document.getElementById("scenarioPanel").style.display = "block";

  // Hide empty state
  document.getElementById("scenarioEmptyState")?.classList.add("hidden");

  // Set scenario name
  const scenarioName = changes[0]?.scenario_name || "Unnamed";
  document.getElementById("timelineScenario").textContent = scenarioName;

  // Init map if needed and render base
  initScenarioMap();
  scenarioState.currentStep = 0;
  renderScenarioAtStep(0);

  toast("Tracked changes loaded – " + (timestamps.length - 1) + " time steps", "success");
}

// ===== Parse base network (clone from network module's parseNetworkTopology) =====
function parseBaseNetworkForScenario() {
  const data = state.system;
  const components = data.components || [];
  const uuidMap = {};
  for (const comp of components) {
    if (comp.uuid) uuidMap[comp.uuid] = comp;
  }

  // Buses
  scenarioState.buses = [];
  for (const comp of components) {
    const typeName = comp.__metadata__?.fields?.type;
    if (typeName !== "DistributionBus") continue;
    const coordRef = comp.coordinate;
    let lat = null, lng = null;
    if (coordRef?.__metadata__?.fields?.serialized_type === "composed_component") {
      const loc = uuidMap[coordRef.__metadata__.fields.uuid];
      if (loc) { lat = loc.x; lng = loc.y; }
    } else if (coordRef && typeof coordRef === "object" && coordRef.x !== undefined) {
      lat = coordRef.x; lng = coordRef.y;
    }
    scenarioState.buses.push({ name: comp.name, uuid: comp.uuid, lat, lng, phases: comp.phases || [] });
  }

  // Edges
  const edgeTypes = new Set([
    "DistributionTransformer", "DistributionRegulator",
    "MatrixImpedanceBranch", "SequenceImpedanceBranch", "GeometryBranch",
    "MatrixImpedanceFuse", "MatrixImpedanceRecloser", "MatrixImpedanceSwitch",
  ]);
  scenarioState.edges = [];
  for (const comp of components) {
    const typeName = comp.__metadata__?.fields?.type;
    if (!edgeTypes.has(typeName)) continue;
    const busRefs = comp.buses || [];
    let bus1 = null, bus2 = null;
    if (busRefs.length >= 2) {
      bus1 = resolveBusName(busRefs[0], uuidMap);
      bus2 = resolveBusName(busRefs[1], uuidMap);
    }
    scenarioState.edges.push({ name: comp.name, uuid: comp.uuid, type: typeName, bus1, bus2, phases: comp.phases || [], isClosed: comp.is_closed });
  }

  // Node components
  const nodeTypes = new Set([
    "DistributionLoad", "DistributionSolar", "DistributionBattery",
    "DistributionCapacitor", "DistributionVoltageSource",
  ]);
  scenarioState.nodeComponents = [];
  for (const comp of components) {
    const typeName = comp.__metadata__?.fields?.type;
    if (!nodeTypes.has(typeName)) continue;
    const busRef = comp.bus;
    const busName = resolveBusName(busRef, uuidMap);
    scenarioState.nodeComponents.push({ name: comp.name, uuid: comp.uuid, type: typeName, busName, phases: comp.phases || [] });
  }
}

// ===== Classify added components from tracked changes =====
function classifyAddedComponents() {
  const edgeTypes = new Set([
    "DistributionTransformer", "DistributionRegulator",
    "MatrixImpedanceBranch", "SequenceImpedanceBranch", "GeometryBranch",
    "MatrixImpedanceFuse", "MatrixImpedanceRecloser", "MatrixImpedanceSwitch",
  ]);
  const nodeTypes = new Set([
    "DistributionLoad", "DistributionSolar", "DistributionBattery",
    "DistributionCapacitor", "DistributionVoltageSource",
  ]);

  scenarioState.addedBuses = [];
  scenarioState.addedEdges = [];
  scenarioState.addedNodeComponents = [];

  for (const a of scenarioState.addedComponents) {
    if (a.type === "DistributionBus") {
      const loc = a.location || {};
      scenarioState.addedBuses.push({
        name: a.name, uuid: a.uuid, lat: loc.x || null, lng: loc.y || null, phases: a.phases || [],
      });
    } else if (edgeTypes.has(a.type)) {
      scenarioState.addedEdges.push({
        name: a.name, uuid: a.uuid, type: a.type, bus1: a.bus1 || null, bus2: a.bus2 || null, phases: a.phases || [],
      });
    } else if (nodeTypes.has(a.type)) {
      scenarioState.addedNodeComponents.push({
        name: a.name, uuid: a.uuid, type: a.type, busName: a.bus || null, phases: a.phases || [],
      });
    }
  }
}

// ===== Build Timeline Ticks =====
function buildTimelineTicks() {
  const container = document.getElementById("timelineTicks");
  container.innerHTML = "";
  for (let i = 0; i < scenarioState.timelineSteps.length; i++) {
    const ts = scenarioState.timelineSteps[i];
    const tick = document.createElement("span");
    tick.className = "timeline-tick";
    if (ts === "base") {
      tick.textContent = "Base";
    } else {
      const d = new Date(ts);
      tick.textContent = d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
    }
    tick.dataset.step = i;
    container.appendChild(tick);
  }
}

// ===== Render Scenario at a Given Step =====
function renderScenarioAtStep(step) {
  // Compute cumulative state up to this step
  scenarioState.addedUUIDs = new Set();
  scenarioState.deletedUUIDs = new Set();
  scenarioState.editedUUIDs = new Set();

  let totalAdded = 0, totalDeleted = 0, totalEdited = 0;

  for (let i = 1; i <= step; i++) {
    const diff = scenarioState.stepDiffs[i];
    for (const a of diff.additions) {
      scenarioState.addedUUIDs.add(a.uuid);
      totalAdded++;
    }
    for (const d of diff.deletions) {
      scenarioState.deletedUUIDs.add(d.uuid);
      totalDeleted++;
    }
    for (const e of diff.edits) {
      scenarioState.editedUUIDs.add(e.component_uuid);
      totalEdited++;
    }
  }

  // Update stats
  document.getElementById("statAdded").textContent = totalAdded;
  document.getElementById("statDeleted").textContent = totalDeleted;
  document.getElementById("statEdited").textContent = totalEdited;

  // Update date display
  const ts = scenarioState.timelineSteps[step];
  if (ts === "base") {
    document.getElementById("timelineDate").textContent = "Base System";
  } else {
    const d = new Date(ts);
    document.getElementById("timelineDate").textContent = d.toLocaleDateString("en-US", {
      month: "long", day: "numeric", year: "numeric",
    });
  }

  // Update tick highlights
  document.querySelectorAll(".timeline-tick").forEach((el, idx) => {
    el.classList.toggle("active", idx <= step);
  });

  // Render map
  renderScenarioMap();

  // Render change log
  renderChangeLog(step);
}

// ===== Render the scenario map =====
function renderScenarioMap() {
  clearScenarioLayers();

  const allBuses = [...scenarioState.buses];
  const allEdges = [...scenarioState.edges];
  const allNodes = [...scenarioState.nodeComponents];

  // Add "added" items that exist at current step
  for (const b of scenarioState.addedBuses) {
    if (scenarioState.addedUUIDs.has(b.uuid)) allBuses.push(b);
  }
  for (const e of scenarioState.addedEdges) {
    if (scenarioState.addedUUIDs.has(e.uuid)) allEdges.push(e);
  }
  for (const n of scenarioState.addedNodeComponents) {
    if (scenarioState.addedUUIDs.has(n.uuid)) allNodes.push(n);
  }

  const busLookup = {};
  for (const bus of allBuses) busLookup[bus.name] = bus;

  // Compute bus attachments
  const busAttachments = {};
  for (const nc of allNodes) {
    if (scenarioState.deletedUUIDs.has(nc.uuid)) continue;
    if (!busAttachments[nc.busName]) busAttachments[nc.busName] = [];
    busAttachments[nc.busName].push(nc);
  }

  // Draw edges
  for (const edge of allEdges) {
    if (scenarioState.deletedUUIDs.has(edge.uuid)) {
      // Draw deleted edge as faded red dashed
      const b1 = busLookup[edge.bus1], b2 = busLookup[edge.bus2];
      if (b1 && b2 && b1.lat != null && b2.lat != null) {
        const line = L.polyline(
          [[b1.lat, b1.lng], [b2.lat, b2.lng]],
          { color: "#f87171", weight: 2, opacity: 0.3, dashArray: "6, 8" }
        ).addTo(scenarioState.map);
        line.bindTooltip(`<strong>${escapeHtml(edge.name)}</strong><br><em>Deleted</em>`, { sticky: true, className: "bus-label" });
        scenarioState.edgeLines[edge.name] = line;
      }
      continue;
    }

    const b1 = busLookup[edge.bus1], b2 = busLookup[edge.bus2];
    if (!b1 || !b2 || b1.lat == null || b2.lat == null) continue;

    const isAdded = scenarioState.addedUUIDs.has(edge.uuid);
    const isEdited = scenarioState.editedUUIDs.has(edge.uuid);
    const isSwitch = edge.type.includes("Switch") || edge.type.includes("Fuse") || edge.type.includes("Recloser");
    const isTransformer = edge.type.includes("Transformer") || edge.type.includes("Regulator");

    let color = "#6fcf6f";
    let weight = 3;
    if (isTransformer) { color = "#f0a030"; weight = 4; }
    else if (isSwitch) { color = "#e54d4d"; weight = 3; }
    if (isAdded) { color = "#4ade80"; weight = 4; }
    else if (isEdited) { color = "#fbbf24"; weight = 4; }

    const line = L.polyline(
      [[b1.lat, b1.lng], [b2.lat, b2.lng]],
      { color, weight, opacity: 0.85 }
    ).addTo(scenarioState.map);

    let tooltipExtra = "";
    if (isAdded) tooltipExtra = "<br><em style='color:#4ade80'>+ Added</em>";
    else if (isEdited) tooltipExtra = "<br><em style='color:#fbbf24'>~ Edited</em>";
    line.bindTooltip(`<strong>${escapeHtml(edge.name)}</strong>${tooltipExtra}`, { sticky: true, className: "bus-label" });

    scenarioState.edgeLines[edge.name] = line;
  }

  // Draw bus markers
  for (const bus of allBuses) {
    if (bus.lat == null || bus.lng == null) continue;
    if (scenarioState.deletedUUIDs.has(bus.uuid)) continue;

    const isAdded = scenarioState.addedUUIDs.has(bus.uuid);
    const isEdited = scenarioState.editedUUIDs.has(bus.uuid);
    const attached = busAttachments[bus.name] || [];
    const hasSource = attached.some(c => c.type === "DistributionVoltageSource");
    const hasSolar = attached.some(c => c.type === "DistributionSolar");
    const hasLoad = attached.some(c => c.type === "DistributionLoad");

    let extraClass = "";
    if (hasSource) extraClass = " source";
    else if (hasSolar) extraClass = " has-solar";
    else if (hasLoad) extraClass = " has-load";

    const busIcon = L.divIcon({
      className: `bus-marker${extraClass}${isAdded ? " scenario-marker-added" : ""}${isEdited ? " scenario-marker-edited" : ""}`,
      iconSize: [14, 14],
    });

    const marker = L.marker([bus.lat, bus.lng], { icon: busIcon }).addTo(scenarioState.map);

    let tooltipExtra = "";
    if (isAdded) tooltipExtra = "<br><em style='color:#4ade80'>+ Added</em>";
    else if (isEdited) tooltipExtra = "<br><em style='color:#fbbf24'>~ Edited</em>";
    marker.bindTooltip(`<strong>${escapeHtml(bus.name)}</strong>${tooltipExtra}`, { sticky: true, className: "bus-label" });

    scenarioState.busMarkers[bus.name] = marker;

    // Label
    if (scenarioState.showLabels) {
      const label = L.marker([bus.lat, bus.lng], {
        icon: L.divIcon({
          className: "bus-label",
          html: escapeHtml(bus.name),
          iconAnchor: [-10, 6],
        }),
        interactive: false,
      }).addTo(scenarioState.map);
      scenarioState.busLabels[bus.name] = label;
    }
  }

  // Draw node components
  for (const nc of allNodes) {
    if (scenarioState.deletedUUIDs.has(nc.uuid)) continue;

    const bus = busLookup[nc.busName];
    if (!bus || bus.lat == null) continue;

    const siblings = (busAttachments[nc.busName] || []).filter(c => !scenarioState.deletedUUIDs.has(c.uuid));
    const idx = siblings.indexOf(nc);
    const total = siblings.length;
    const angle = (idx / Math.max(total, 1)) * Math.PI * 2 - Math.PI / 2;
    const offsetDist = 0.0004;
    const lat = bus.lat + Math.sin(angle) * offsetDist;
    const lng = bus.lng + Math.cos(angle) * offsetDist;

    const isAdded = scenarioState.addedUUIDs.has(nc.uuid);
    const isEdited = scenarioState.editedUUIDs.has(nc.uuid);

    let markerClass = "component-marker";
    if (nc.type === "DistributionLoad") markerClass += " load";
    else if (nc.type === "DistributionSolar") markerClass += " solar";
    else if (nc.type === "DistributionBattery") markerClass += " battery";
    else if (nc.type === "DistributionCapacitor") markerClass += " capacitor";
    else if (nc.type === "DistributionVoltageSource") markerClass += " source";

    if (isAdded) markerClass += " scenario-marker-added";
    else if (isEdited) markerClass += " scenario-marker-edited";

    const iconHtml = `<i class="${COMPONENT_ICONS[nc.type] || "ri-box-3-line"}"></i>`;
    const compIcon = L.divIcon({ className: markerClass, html: iconHtml, iconSize: [22, 22] });
    const compMarker = L.marker([lat, lng], { icon: compIcon }).addTo(scenarioState.map);

    let tooltipExtra = "";
    if (isAdded) tooltipExtra = "<br><em style='color:#4ade80'>+ Added</em>";
    else if (isEdited) tooltipExtra = "<br><em style='color:#fbbf24'>~ Edited</em>";
    compMarker.bindTooltip(`<strong>${escapeHtml(nc.name)}</strong>${tooltipExtra}`, { sticky: true, className: "bus-label" });

    // Connection line
    const connLine = L.polyline(
      [[bus.lat, bus.lng], [lat, lng]],
      { color: isAdded ? "#4ade80" : "#3a3e52", weight: 1, opacity: isAdded ? 0.6 : 0.5, dashArray: "3, 3" }
    ).addTo(scenarioState.map);
    scenarioState.connectionLines.push(connLine);

    scenarioState.componentMarkers[nc.name] = compMarker;
  }
}

// ===== Clear scenario layers =====
function clearScenarioLayers() {
  Object.values(scenarioState.busMarkers).forEach(m => m.remove());
  Object.values(scenarioState.busLabels).forEach(m => m.remove());
  Object.values(scenarioState.edgeLines).forEach(l => l.remove());
  Object.values(scenarioState.componentMarkers).forEach(m => m.remove());
  scenarioState.connectionLines.forEach(l => l.remove());
  scenarioState.busMarkers = {};
  scenarioState.busLabels = {};
  scenarioState.edgeLines = {};
  scenarioState.componentMarkers = {};
  scenarioState.connectionLines = [];
}

// ===== Fit to bounds =====
function scenarioFitBounds() {
  const points = [];
  for (const bus of scenarioState.buses) {
    if (bus.lat != null) points.push([bus.lat, bus.lng]);
  }
  for (const bus of scenarioState.addedBuses) {
    if (bus.lat != null && scenarioState.addedUUIDs.has(bus.uuid)) points.push([bus.lat, bus.lng]);
  }
  if (points.length > 0) {
    scenarioState.map.fitBounds(L.latLngBounds(points).pad(0.15));
  }
}

// ===== Render Change Log Panel =====
function renderChangeLog(step) {
  const list = document.getElementById("changeLogList");
  const hint = document.getElementById("changeLogHint");
  list.innerHTML = "";

  if (step === 0) {
    hint.textContent = "Base system";
    list.innerHTML = '<div style="padding:12px;color:#6b6f82;font-size:0.8rem;text-align:center;">No changes at base state</div>';
    return;
  }

  // Collect all changes up to current step
  const items = [];
  for (let i = 1; i <= step; i++) {
    const ts = scenarioState.timelineSteps[i];
    const diff = scenarioState.stepDiffs[i];
    const isCurrentStep = i === step;
    for (const a of diff.additions) {
      items.push({ changeType: "addition", name: a.name, type: a.type, timestamp: ts, current: isCurrentStep });
    }
    for (const d of diff.deletions) {
      items.push({ changeType: "deletion", name: d.component_name || d.uuid, type: d.component_type || "", timestamp: ts, current: isCurrentStep });
    }
    for (const e of diff.edits) {
      items.push({ changeType: "edit", name: e.component_name || e.component_uuid, type: e.field, timestamp: ts, current: isCurrentStep });
    }
  }

  hint.textContent = items.length + " change" + (items.length !== 1 ? "s" : "");

  // Render items (most recent first)
  for (const item of items.reverse()) {
    const el = document.createElement("div");
    el.className = `change-log-item ${item.changeType}`;
    if (item.current) el.style.borderColor = "#2a2d3a";

    const iconMap = { addition: "ri-add-line", deletion: "ri-subtract-line", edit: "ri-edit-line" };
    const labelMap = { addition: "Added", deletion: "Removed", edit: "Edited" };
    const d = new Date(item.timestamp);
    const dateStr = d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });

    el.innerHTML = `
      <div class="change-icon"><i class="${iconMap[item.changeType]}"></i></div>
      <div class="change-detail">
        <span class="change-name">${escapeHtml(item.name)}</span>
        <span class="change-type">${labelMap[item.changeType]} · ${escapeHtml(item.type)} · ${dateStr}</span>
      </div>
    `;
    list.appendChild(el);
  }
}

// ===== Hook into page navigation (init map when switching to Scenarios) =====
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
      if (item.dataset.page === "scenarios") {
        setTimeout(() => {
          initScenarioMap();
          if (scenarioState.map) scenarioState.map.invalidateSize();
        }, 100);
      }
    });
  });
});
