/**
 * Prim Selection, Property Inspector, Live PBR Material Editor & USDA Exporter.
 */

import { appState } from "../state.js";

export function selectPrim(primPath) {
  appState.selectedPrimPath = primPath;

  // Update Outliner UI highlight
  document.querySelectorAll(".outliner-item").forEach(item => {
    item.classList.toggle("selected", item.dataset.path === primPath);
  });

  // Find mesh in 3D scene
  const mesh = appState.scenePrims.get(primPath);

  // Update 3D Selection Bounding Box
  if (appState.highlightBox) {
    appState.scene.remove(appState.highlightBox);
    appState.highlightBox = null;
  }

  if (mesh) {
    appState.highlightBox = new THREE.BoxHelper(mesh, 0x38bdf8); // Glowing cyan highlight
    appState.scene.add(appState.highlightBox);
  }

  // Update Inspector Panel
  const prim = appState.stageData?.prims?.find(p => p.path === primPath);
  updateInspector(prim, mesh);
}

export function updateInspector(prim, mesh) {
  const panel = document.getElementById("inspector-content");
  if (!panel) return;

  if (!prim) {
    panel.innerHTML = `<div class="inspector-placeholder">Select a prim from the outliner or 3D viewport to inspect its OpenUSD schemas, PBR properties, and physics parameters.</div>`;
    return;
  }

  const psetsHtml = buildBimPsetsHtml(prim.bim);

  panel.innerHTML = `
    <div class="inspector-section">
      <div class="inspector-row">
        <span class="inspector-label">Path:</span>
        <span class="inspector-value text-mono text-cyan">${prim.path}</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Type:</span>
        <span class="inspector-value text-badge">${prim.type}</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Position:</span>
        <span class="inspector-value text-mono">${prim.position ? prim.position.map(n => n.toFixed(1)).join(", ") : "0, 0, 0"}</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Material:</span>
        <span class="inspector-value text-mono">${prim.materialPath || "Default"}</span>
      </div>
    </div>

    <!-- Live PBR Material Editor -->
    ${mesh && mesh.material ? `
    <div class="inspector-group-title">🎨 Live PBR Material Tuning</div>
    <div class="inspector-section">
      <div class="inspector-slider-row">
        <label>Roughness:</label>
        <input type="range" id="inspect-roughness" min="0" max="1" step="0.01" value="${mesh.material.roughness !== undefined ? mesh.material.roughness : 0.5}" />
        <span id="val-roughness" class="slider-val">${mesh.material.roughness !== undefined ? mesh.material.roughness.toFixed(2) : "0.50"}</span>
      </div>
      <div class="inspector-slider-row">
        <label>Metalness:</label>
        <input type="range" id="inspect-metalness" min="0" max="1" step="0.01" value="${mesh.material.metalness !== undefined ? mesh.material.metalness : 0.0}" />
        <span id="val-metalness" class="slider-val">${mesh.material.metalness !== undefined ? mesh.material.metalness.toFixed(2) : "0.00"}</span>
      </div>
      <div class="inspector-slider-row">
        <label>Opacity:</label>
        <input type="range" id="inspect-opacity" min="0.05" max="1" step="0.01" value="${mesh.material.opacity !== undefined ? mesh.material.opacity : 1.0}" />
        <span id="val-opacity" class="slider-val">${mesh.material.opacity !== undefined ? mesh.material.opacity.toFixed(2) : "1.00"}</span>
      </div>
    </div>
    ` : ""}

    <!-- BIM Properties -->
    ${psetsHtml}
  `;

  // Bind live material sliders
  if (mesh && mesh.material) {
    bindMaterialSlider("inspect-roughness", "val-roughness", val => {
      mesh.material.roughness = val;
      if (mesh.userData._baseMaterial) mesh.userData._baseMaterial.roughness = val;
    });
    bindMaterialSlider("inspect-metalness", "val-metalness", val => {
      mesh.material.metalness = val;
      if (mesh.userData._baseMaterial) mesh.userData._baseMaterial.metalness = val;
    });
    bindMaterialSlider("inspect-opacity", "val-opacity", val => {
      mesh.material.transparent = val < 0.99;
      mesh.material.opacity = val;
      if (mesh.userData._baseMaterial) {
        mesh.userData._baseMaterial.transparent = val < 0.99;
        mesh.userData._baseMaterial.opacity = val;
      }
    });
  }
}

function bindMaterialSlider(sliderId, valId, callback) {
  const slider = document.getElementById(sliderId);
  const label = document.getElementById(valId);
  if (!slider || !label) return;

  slider.addEventListener("input", (e) => {
    const v = parseFloat(e.target.value);
    label.textContent = v.toFixed(2);
    callback(v);
  });
}

function buildBimPsetsHtml(bim) {
  if (!bim) return "";

  let psetsRows = "";
  if (bim.psets) {
    Object.entries(bim.psets).forEach(([k, v]) => {
      psetsRows += `
        <div class="inspector-row">
          <span class="inspector-label text-truncate" title="${k}">${k.split(":").pop()}:</span>
          <span class="inspector-value text-mono text-cyan">${v}</span>
        </div>
      `;
    });
  }

  return `
    <div class="inspector-group-title">🏛️ BIM & IFC Classification</div>
    <div class="inspector-section">
      <div class="inspector-row">
        <span class="inspector-label">IFC Class:</span>
        <span class="inspector-value text-badge badge-bim">${bim.ifcClass}</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Discipline:</span>
        <span class="inspector-value">${bim.discipline}</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Storey:</span>
        <span class="inspector-value">${bim.storey}</span>
      </div>
      ${bim.constructionMonth !== undefined ? `
      <div class="inspector-row">
        <span class="inspector-label">4D Phase:</span>
        <span class="inspector-value text-cyan">Month ${bim.constructionMonth} (${bim.phase || "Scheduled"})</span>
      </div>` : ""}
      ${psetsRows}
    </div>
  `;
}

export function exportUsda() {
  if (!appState.stageData) {
    alert("No stage loaded to export.");
    return;
  }

  let usda = `#usda 1.0\n(\n    upAxis = "${appState.stageData.metadata?.upAxis || 'Y'}"\n    metersPerUnit = ${appState.stageData.metadata?.metersPerUnit || 0.01}\n)\n\ndef Xform "World"\n{\n`;

  appState.scenePrims.forEach((mesh, path) => {
    const prim = mesh.userData;
    if (!prim) return;

    const p = mesh.position;
    const r = mesh.rotation;
    const s = mesh.scale;

    usda += `    def ${prim.type || 'Xform'} "${mesh.name || 'Prim'}"\n    {\n`;
    usda += `        double3 xformOp:translate = (${p.x.toFixed(2)}, ${p.y.toFixed(2)}, ${p.z.toFixed(2)})\n`;
    usda += `        float3 xformOp:rotateXYZ = (${THREE.MathUtils.radToDeg(r.x).toFixed(1)}, ${THREE.MathUtils.radToDeg(r.y).toFixed(1)}, ${THREE.MathUtils.radToDeg(r.z).toFixed(1)})\n`;
    usda += `        float3 xformOp:scale = (${s.x.toFixed(2)}, ${s.y.toFixed(2)}, ${s.z.toFixed(2)})\n`;
    usda += `        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]\n`;
    usda += `    }\n`;
  });

  usda += `}\n`;

  const blob = new Blob([usda], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${appState.stageData.filename || 'scene'}_exported.usda`;
  a.click();
  URL.revokeObjectURL(a.href);
}
