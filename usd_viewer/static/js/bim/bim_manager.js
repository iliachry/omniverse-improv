/**
 * BIM Storey Isolation, Multi-Discipline Filtering & Solar Simulation.
 */

import { appState } from "../state.js";

export function initBimUI(stageData) {
  if (!stageData) return;

  const summary = stageData.bimSummary;
  const isBim = Boolean(summary && summary.elementCount > 0);

  const bimToolbar = document.getElementById("bim-toolbar");
  if (bimToolbar) bimToolbar.classList.toggle("hidden", !isBim);

  if (!isBim) return;

  // Update coords badge
  const coordsBadge = document.getElementById("bim-coords-badge");
  if (coordsBadge && stageData.cesium) {
    coordsBadge.textContent = `Lat: ${stageData.cesium.latitude.toFixed(4)}° N | Lon: ${stageData.cesium.longitude.toFixed(4)}° E | ${stageData.cesium.height}m WGS84`;
  }

  // Update clash count badge
  const clashBadge = document.getElementById("clash-badge-count");
  if (clashBadge) {
    const count = summary.clashCount || stageData.clashes?.length || 0;
    clashBadge.textContent = count;
    clashBadge.classList.toggle("hidden", count === 0);
  }
}

export function applyBimFilters() {
  // 1. Three.js Viewport Filtering
  appState.scenePrims.forEach((mesh, path) => {
    const prim = mesh.userData;
    if (!prim) return;

    if (prim.bim) {
      const matchStorey = (appState.activeStoreyFilter === "ALL") || (prim.bim.storey === appState.activeStoreyFilter);
      const matchDisc = appState.activeDisciplines[prim.bim.discipline] !== false;
      let visible = matchStorey && matchDisc;

      if (appState.is4DMode && prim.bim.constructionMonth !== undefined) {
        if (prim.bim.constructionMonth > appState.current4DMonth) {
          if (appState.is4DGhostUnbuilt) {
            visible = matchStorey && matchDisc;
            if (!mesh.userData._isGhosted) {
              mesh.userData._isGhosted = true;
              mesh.material = new THREE.MeshBasicMaterial({
                color: 0x38bdf8,
                wireframe: true,
                transparent: true,
                opacity: 0.12
              });
            }
          } else {
            visible = false;
          }
        } else {
          // Constructed by active month
          if (mesh.userData._isGhosted) {
            mesh.userData._isGhosted = false;
            if (mesh.userData._baseMaterial) {
              mesh.material = mesh.userData._baseMaterial.clone();
            }
          }

          // Active month erection highlight
          if (prim.bim.constructionMonth === appState.current4DMonth && appState.is4DMode && appState.current4DMonth > 0) {
            if (mesh.material && mesh.material.emissive) {
              mesh.material.emissive.setHex(0xf59e0b);
              mesh.material.emissiveIntensity = 0.5;
            }
          } else if (mesh.material && mesh.material.emissive && mesh.userData._baseMaterial) {
            mesh.material.emissive.copy(mesh.userData._baseMaterial.emissive);
            mesh.material.emissiveIntensity = mesh.userData._baseMaterial.emissiveIntensity || 0.0;
          }
        }
      } else {
        if (mesh.userData._isGhosted) {
          mesh.userData._isGhosted = false;
          if (mesh.userData._baseMaterial) {
            mesh.material = mesh.userData._baseMaterial.clone();
          }
        }
      }

      mesh.visible = visible;

      // X-Ray Transparency for walls and slabs
      if (visible && appState.isXRayMode && (prim.bim.ifcClass.includes("Wall") || prim.bim.ifcClass.includes("Slab"))) {
        if (mesh.material) {
          mesh.material.transparent = true;
          mesh.material.opacity = 0.2;
          mesh.material.needsUpdate = true;
        }
      }
    }
  });

  // 2. Cesium Earth Globe Filtering
  if (appState.cesiumFacilityEntities && appState.cesiumFacilityEntities.length > 0) {
    appState.cesiumFacilityEntities.forEach(ent => {
      const prim = ent._prim;
      if (!prim || !prim.bim) return;
      const matchStorey = (appState.activeStoreyFilter === "ALL") || (prim.bim.storey === appState.activeStoreyFilter);
      const matchDisc = appState.activeDisciplines[prim.bim.discipline] !== false;
      let show = matchStorey && matchDisc;

      if (appState.is4DMode && prim.bim.constructionMonth !== undefined) {
        if (prim.bim.constructionMonth > appState.current4DMonth) {
          if (appState.is4DGhostUnbuilt && typeof Cesium !== "undefined") {
            show = matchStorey && matchDisc;
            const ghostColor = Cesium.Color.fromCssColorString("#38bdf8").withAlpha(0.12);
            if (ent.box) ent.box.material = ghostColor;
            if (ent.cylinder) ent.cylinder.material = ghostColor;
          } else {
            show = false;
          }
        } else {
          if (prim.bim.constructionMonth === appState.current4DMonth && appState.is4DMode && appState.current4DMonth > 0 && typeof Cesium !== "undefined") {
            const activeColor = Cesium.Color.fromCssColorString("#f59e0b");
            if (ent.box) ent.box.material = activeColor;
            if (ent.cylinder) ent.cylinder.material = activeColor;
          } else if (ent._origMaterial) {
            if (ent.box) ent.box.material = ent._origMaterial;
            if (ent.cylinder) ent.cylinder.material = ent._origMaterial;
          }
        }
      } else {
        if (ent._origMaterial) {
          if (ent.box) ent.box.material = ent._origMaterial;
          if (ent.cylinder) ent.cylinder.material = ent._origMaterial;
        }
      }
      ent.show = show;
    });
  }
}

export function setStoreyFilter(storey) {
  appState.activeStoreyFilter = storey;
  document.querySelectorAll("#bim-storey-chips .bim-chip").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.storey === storey);
  });
  applyBimFilters();
}

export function toggleDiscipline(discipline, isChecked) {
  appState.activeDisciplines[discipline] = isChecked;
  applyBimFilters();
}

export function toggleXRayMode() {
  appState.isXRayMode = !appState.isXRayMode;
  const btn = document.getElementById("btn-bim-xray");
  if (btn) btn.classList.toggle("active", appState.isXRayMode);

  if (!appState.isXRayMode) {
    appState.scenePrims.forEach(mesh => {
      if (mesh.userData._baseMaterial) {
        mesh.material = mesh.userData._baseMaterial.clone();
      }
    });
  }
  applyBimFilters();
}

export function updateSolarStudy(hour) {
  appState.solarHour = hour;
  const readout = document.getElementById("bim-solar-readout");
  if (readout) {
    const h = Math.floor(hour);
    const m = Math.round((hour - h) * 60);
    const timeStr = `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
    const altDeg = Math.sin(((hour - 6.0) / 12.0) * Math.PI) * 62.0;
    readout.textContent = `${timeStr} (${altDeg.toFixed(0)}°)`;
  }

  if (appState.dirSunLight) {
    const progress = (hour - 6.0) / 12.0;
    const phi = progress * Math.PI;
    const r = 1800;
    const x = Math.cos(phi) * r;
    const y = Math.max(100, Math.sin(phi) * r);
    const z = 400;

    appState.dirSunLight.position.set(x, y, z);
    appState.dirSunLight.intensity = Math.max(0.1, Math.sin(phi) * 2.0);
  }
}
