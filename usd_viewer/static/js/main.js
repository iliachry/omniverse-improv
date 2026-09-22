/**
 * Main Application Entrypoint Module.
 * Bootstraps the WebGL viewport, registers event listeners, and coordinates subsystems.
 */

import { appState } from "./state.js";
import { initThree, frameScene, applyShadingMode } from "./core/scene_builder.js";
import { fetchStageList, loadStage } from "./core/stage_loader.js";
import { filterOutliner } from "./core/outliner.js";
import { exportUsda, selectPrim } from "./core/inspector.js";
import { togglePhysics, resetPhysics, nudgeTrigger, stepPhysics } from "./engines/physics_engine.js";
import { switchViewMode, flyCesiumToSite } from "./engines/cesium_engine.js";
import { setStoreyFilter, toggleDiscipline, toggleXRayMode, updateSolarStudy } from "./bim/bim_manager.js";
import { toggleClashMode, filterClashes, exportBcfReport } from "./bim/clash_viewer.js";
import { toggle4DPhasingMode, set4DMonth, toggle4DPlayback } from "./bim/phasing_timeline.js";
import { initSdgDashboard } from "./sdg/sdg_manager.js";

// Export helpers to window for backward-compatible inline onclick / HTML hooks
window.selectPrim = selectPrim;
window.set4DMonth = set4DMonth;
window.toggle4DPlayback = toggle4DPlayback;
window.toggleClashMode = toggleClashMode;
window.switchViewMode = switchViewMode;

document.addEventListener("DOMContentLoaded", () => {
  initThree();
  initEventListeners();
  initRaycasting();
  fetchStageList();
  initSdgDashboard();
  animate();
});

function initEventListeners() {
  // Stage selector
  const stageSelect = document.getElementById("stage-select");
  if (stageSelect) {
    stageSelect.addEventListener("change", (e) => loadStage(e.target.value));
  }

  // Camera Framing & Reset
  document.getElementById("btn-frame-all")?.addEventListener("click", frameScene);
  document.getElementById("btn-reset-cam")?.addEventListener("click", () => {
    appState.camera.position.set(600, 500, 800);
    appState.controls.target.set(0, 0, 0);
    appState.controls.update();
  });

  // Shading Modes
  document.querySelectorAll(".shading-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".shading-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      applyShadingMode(btn.dataset.mode);
    });
  });

  // Grid & Axes Toggles
  document.getElementById("toggle-grid")?.addEventListener("change", (e) => {
    if (appState.gridHelper) appState.gridHelper.visible = e.target.checked;
  });
  document.getElementById("toggle-axes")?.addEventListener("change", (e) => {
    if (appState.axesHelper) appState.axesHelper.visible = e.target.checked;
  });

  // Outliner Search
  document.getElementById("outliner-search")?.addEventListener("input", (e) => {
    filterOutliner(e.target.value);
  });

  // Export USDA
  document.getElementById("btn-export-usda")?.addEventListener("click", exportUsda);

  // Physics Controls
  document.getElementById("btn-play-physics")?.addEventListener("click", () => togglePhysics());
  document.getElementById("btn-reset-physics")?.addEventListener("click", resetPhysics);
  document.getElementById("btn-nudge-ball")?.addEventListener("click", nudgeTrigger);
  document.getElementById("gravity-select")?.addEventListener("change", (e) => {
    appState.gravityMagnitude = parseFloat(e.target.value);
    if (appState.physicsWorld) {
      appState.physicsWorld.gravity.set(0, -appState.gravityMagnitude * 100, 0);
    }
  });

  // View Mode Switcher (Studio vs Cesium)
  document.getElementById("btn-mode-three")?.addEventListener("click", () => switchViewMode("three"));
  document.getElementById("btn-mode-cesium")?.addEventListener("click", () => switchViewMode("cesium"));
  document.getElementById("btn-cesium-flyto")?.addEventListener("click", flyCesiumToSite);

  // BIM Controls
  document.querySelectorAll("#bim-storey-chips .bim-chip").forEach(btn => {
    btn.addEventListener("click", () => setStoreyFilter(btn.dataset.storey));
  });

  document.getElementById("bim-toggle-struct")?.addEventListener("change", (e) => toggleDiscipline("Structural", e.target.checked));
  document.getElementById("bim-toggle-arch")?.addEventListener("change", (e) => toggleDiscipline("Architectural", e.target.checked));
  document.getElementById("bim-toggle-mep")?.addEventListener("change", (e) => toggleDiscipline("MEP", e.target.checked));
  document.getElementById("btn-bim-xray")?.addEventListener("click", toggleXRayMode);

  // Solar Study Slider
  document.getElementById("bim-solar-slider")?.addEventListener("input", (e) => {
    updateSolarStudy(parseFloat(e.target.value));
  });

  // Clash Detection Controls
  document.getElementById("btn-bim-clash")?.addEventListener("click", () => toggleClashMode());
  document.getElementById("btn-close-clash")?.addEventListener("click", () => toggleClashMode(false));
  document.querySelectorAll(".clash-filter-pill").forEach(btn => {
    btn.addEventListener("click", () => filterClashes(btn.dataset.filter));
  });
  document.getElementById("btn-export-bcf")?.addEventListener("click", exportBcfReport);

  // 4D Phasing Controls
  document.getElementById("btn-bim-4d")?.addEventListener("click", () => toggle4DPhasingMode());
  document.getElementById("btn-close-4d")?.addEventListener("click", () => toggle4DPhasingMode(false));
  document.getElementById("btn-4d-play")?.addEventListener("click", () => toggle4DPlayback());
  document.getElementById("phasing-slider")?.addEventListener("input", (e) => set4DMonth(e.target.value));
  document.getElementById("select-4d-speed")?.addEventListener("change", (e) => {
    appState.play4DSpeed = parseFloat(e.target.value);
    if (appState.is4DPlaying) {
      toggle4DPlayback(false);
      toggle4DPlayback(true);
    }
  });
  document.getElementById("check-4d-ghost")?.addEventListener("change", (e) => {
    appState.is4DGhostUnbuilt = e.target.checked;
    import("./bim/bim_manager.js").then(m => m.applyBimFilters());
  });

  // Keyboard Shortcuts
  window.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;

    if (e.code === "Space") {
      e.preventDefault();
      if (appState.is4DMode) {
        toggle4DPlayback();
      } else {
        togglePhysics();
      }
    } else if (e.code === "KeyF") {
      frameScene();
    }
  });
}

function initRaycasting() {
  const canvas = document.getElementById("webgl-canvas");
  if (!canvas) return;

  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  canvas.addEventListener("pointerdown", (e) => {
    // Only select on primary left click
    if (e.button !== 0) return;

    const rect = canvas.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, appState.camera);
    const visibleMeshes = Array.from(appState.scenePrims.values()).filter(m => m.visible);
    const intersects = raycaster.intersectObjects(visibleMeshes, false);

    if (intersects.length > 0) {
      const hit = intersects[0].object;
      if (hit.userData && hit.userData.path) {
        selectPrim(hit.userData.path);
      }
    }
  });
}

function animate() {
  requestAnimationFrame(animate);

  // Measure FPS
  appState.frameCount++;
  const now = performance.now();
  if (now - appState.lastFpsTime >= 1000) {
    appState.fps = Math.round((appState.frameCount * 1000) / (now - appState.lastFpsTime));
    appState.frameCount = 0;
    appState.lastFpsTime = now;
    const fpsEl = document.getElementById("stat-fps");
    if (fpsEl) fpsEl.textContent = appState.fps;
  }

  // Update Controls & Physics
  if (appState.controls) appState.controls.update();
  stepPhysics();

  // Render WebGL Viewport
  if (!appState.isCesiumMode && appState.renderer && appState.scene && appState.camera) {
    appState.renderer.render(appState.scene, appState.camera);
  }
}
