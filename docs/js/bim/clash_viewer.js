/**
 * Automated BIM Clash Detection & BCF Issue Management Suite.
 */

import { appState } from "../state.js";
import { toggle4DPhasingMode } from "./phasing_timeline.js";

export function toggleClashMode(forceState) {
  if (typeof forceState === "boolean") {
    appState.isClashMode = forceState;
  } else {
    appState.isClashMode = !appState.isClashMode;
  }

  const btn = document.getElementById("btn-bim-clash");
  const drawer = document.getElementById("clash-drawer");
  if (btn) btn.classList.toggle("active", appState.isClashMode);
  if (drawer) drawer.classList.toggle("hidden", !appState.isClashMode);

  if (appState.isClashMode) {
    if (appState.is4DMode) toggle4DPhasingMode(false);
    renderClashCards();
    highlightAllClashes();
  } else {
    clearClashHighlights();
  }
}

export function renderClashCards() {
  const container = document.getElementById("clash-list-container");
  if (!container) return;

  appState.activeClashes = appState.stageData?.clashes || [];
  container.innerHTML = "";

  const filtered = appState.activeClashes.filter(c => {
    if (appState.activeClashFilter === "ALL") return true;
    return c.severity === appState.activeClashFilter;
  });

  const summary = document.getElementById("clash-summary-stats");
  if (summary) {
    summary.textContent = `${appState.activeClashes.length} Interferences Found`;
  }

  filtered.forEach(clash => {
    const card = document.createElement("div");
    card.className = `clash-card clash-border-${clash.severity.toLowerCase()}`;
    if (clash.id === appState.selectedClashId) card.classList.add("selected");
    card.dataset.clashId = clash.id;

    card.innerHTML = `
      <div class="clash-card-header">
        <span class="badge-clash-pill badge-${clash.severity.toLowerCase()}">${clash.severity}</span>
        <span class="clash-id">${clash.id}</span>
        <span class="clash-depth">${clash.penetrationDepthCm} cm depth</span>
      </div>
      <div class="clash-card-title">${clash.elementA.name} ⚡ ${clash.elementB.name}</div>
      <div class="clash-card-meta">
        <span>Storey: ${clash.storey}</span>
        <span>Centroid: [${clash.centroid.join(", ")}]</span>
      </div>
      <div class="clash-mitigation-box">
        💡 <strong>Mitigation:</strong> ${clash.mitigation}
      </div>
    `;

    card.addEventListener("click", () => selectClash(clash.id));
    container.appendChild(card);
  });
}

export function filterClashes(severity) {
  appState.activeClashFilter = severity;
  document.querySelectorAll(".clash-filter-pill").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.filter === severity);
  });
  renderClashCards();
}

export function selectClash(clashId) {
  appState.selectedClashId = clashId;
  renderClashCards();

  const clash = appState.activeClashes.find(c => c.id === clashId);
  if (!clash) return;

  // Orbit camera to clash centroid
  if (appState.controls && appState.camera) {
    const [cx, cy, cz] = clash.centroid;
    const target = new THREE.Vector3(cx, cy, cz);

    appState.controls.target.copy(target);
    appState.camera.position.set(cx + 300, cy + 200, cz + 300);
    appState.controls.update();
  }

  // Draw clash bounding box
  if (appState.clashWireframeBox) {
    appState.scene.remove(appState.clashWireframeBox);
    appState.clashWireframeBox = null;
  }

  const [cx, cy, cz] = clash.centroid;
  const depth = Math.max(30, clash.penetrationDepthCm * 2);
  const geom = new THREE.BoxGeometry(depth, depth, depth);
  const mat = new THREE.MeshBasicMaterial({
    color: clash.severity === "CRITICAL" ? 0xef4444 : (clash.severity === "MAJOR" ? 0xf97316 : 0xeab308),
    wireframe: true
  });

  appState.clashWireframeBox = new THREE.Mesh(geom, mat);
  appState.clashWireframeBox.position.set(cx, cy, cz);
  appState.scene.add(appState.clashWireframeBox);
}

function highlightAllClashes() {
  clearClashHighlights();

  // Ghost non-clashing geometry and highlight colliding prims
  const clashPrimPaths = new Set();
  appState.activeClashes.forEach(c => {
    if (c.elementA?.path) clashPrimPaths.add(c.elementA.path);
    if (c.elementB?.path) clashPrimPaths.add(c.elementB.path);
  });

  appState.scenePrims.forEach((mesh, path) => {
    if (clashPrimPaths.has(path)) {
      if (!mesh.userData._origMaterial && mesh.material) {
        mesh.userData._origMaterial = mesh.material.clone();
      }
      mesh.material = new THREE.MeshStandardMaterial({
        color: path.includes("HVAC") || path.includes("Duct") || path.includes("Pipe") ? 0xef4444 : 0xf59e0b,
        emissive: 0xef4444,
        emissiveIntensity: 0.4,
        roughness: 0.3
      });
      appState.clashHighlightMeshes.set(path, mesh);
    } else {
      if (!mesh.userData._origOpacity && mesh.material) {
        mesh.userData._origOpacity = mesh.material.opacity;
        mesh.userData._origTransparent = mesh.material.transparent;
      }
      mesh.material.transparent = true;
      mesh.material.opacity = 0.15;
    }
  });
}

function clearClashHighlights() {
  if (appState.clashWireframeBox) {
    appState.scene.remove(appState.clashWireframeBox);
    appState.clashWireframeBox = null;
  }

  appState.clashHighlightMeshes.forEach((mesh, path) => {
    if (mesh.userData._baseMaterial) {
      mesh.material = mesh.userData._baseMaterial.clone();
    }
  });
  appState.clashHighlightMeshes.clear();

  appState.scenePrims.forEach(mesh => {
    if (mesh.userData._baseMaterial) {
      mesh.material = mesh.userData._baseMaterial.clone();
    }
  });
}

export function exportBcfReport() {
  if (!appState.activeClashes || appState.activeClashes.length === 0) {
    alert("No clashes found to export.");
    return;
  }

  const topics = appState.activeClashes.map(c => ({
    guid: c.id,
    topicType: "Clash",
    topicStatus: c.status || "Open",
    title: c.title,
    priority: c.severity,
    creationDate: new Date().toISOString(),
    creationAuthor: "Omniverse WebGL Spatial Solver",
    description: `Penetration of ${c.penetrationDepthCm} cm detected between ${c.elementA.name} and ${c.elementB.name}.`,
    viewpoint: {
      cameraViewPoint: c.centroid,
      cameraDirection: [0.0, -0.707, -0.707],
      cameraUpVector: [0.0, 1.0, 0.0]
    },
    components: [c.elementA.path, c.elementB.path],
    comments: [
      {
        comment: c.mitigation,
        date: new Date().toISOString(),
        author: "BIM Coordination Suite"
      }
    ]
  }));

  const report = {
    project: {
      name: appState.stageData?.filename || "Smart Tech Campus Facility",
      projectId: "PRJ-OPENUSD-BIM-001"
    },
    version: "BCF-API 2.1 JSON",
    topicCount: topics.length,
    topics: topics
  };

  const blob = new Blob([jsonString(report)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "bim_coordination_report.bcf.json";
  a.click();
  URL.revokeObjectURL(a.href);
}

function jsonString(obj) {
  return JSON.stringify(obj, null, 2);
}
