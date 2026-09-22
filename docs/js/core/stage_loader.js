/**
 * OpenUSD Stage Loading & Remote / Static API Client.
 */

import { appState } from "../state.js";
import { buildScene } from "./scene_builder.js";
import { populateOutliner } from "./outliner.js";
import { initBimUI } from "../bim/bim_manager.js";
import { initCesiumViewer, switchViewMode } from "../engines/cesium_engine.js";

export async function fetchStageList() {
  const select = document.getElementById("stage-select");
  if (!select) return;

  try {
    // Dual-mode relative fetch: local Python API or static GitHub Pages export
    let res = await fetch("api/stages.json").catch(() => null);
    if (!res || !res.ok) {
      res = await fetch("/api/stages");
    }
    const stages = await res.json();

    select.innerHTML = "";
    stages.forEach(stg => {
      const opt = document.createElement("option");
      opt.value = stg.relPath || stg.fullPath;
      opt.textContent = `${stg.name} (${formatBytes(stg.size)})`;
      select.appendChild(opt);
    });

    // Check URL search parameters
    const urlParams = new URLSearchParams(window.location.search);
    const stageQuery = urlParams.get("stage");

    if (stageQuery) {
      const match = Array.from(select.options).find(o => o.value.includes(stageQuery) || o.value.endsWith(stageQuery));
      if (match) {
        select.value = match.value;
      }
    }

    if (select.value) {
      loadStage(select.value);
    }
  } catch (err) {
    console.error("Error fetching stages list:", err);
  }
}

export async function loadStage(stagePath) {
  const loading = document.getElementById("loading-overlay");
  const loadingText = document.getElementById("loading-text");
  if (loading) loading.classList.remove("hidden");
  if (loadingText) loadingText.textContent = `Loading ${stagePath}...`;

  appState.currentStagePath = stagePath;

  try {
    let stageData = null;

    // Dual-mode fetch: Try static pre-parsed JSON bundle first, then dynamic API
    let res = await fetch("api/stage_data.json").catch(() => null);
    if (res && res.ok) {
      const cache = await res.json();
      const normPath = stagePath.replace(/\\/g, "/");
      const key = Object.keys(cache).find(k => k.endsWith(normPath) || normPath.endsWith(k) || k.includes(normPath));
      if (key && cache[key]) {
        stageData = cache[key];
      }
    }

    if (!stageData) {
      const apiUrl = `/api/stage?path=${encodeURIComponent(stagePath)}`;
      const dynRes = await fetch(apiUrl);
      if (!dynRes.ok) throw new Error(`HTTP ${dynRes.status}`);
      stageData = await dynRes.json();
    }

    appState.stageData = stageData;

    // Build 3D WebGL scene and outliner tree
    buildScene(stageData);
    populateOutliner(stageData.hierarchy);
    updateStageMetadataUI(stageData);
    initBimUI(stageData);

    // If stage contains Cesium georeference, initialize viewer in background
    if (stageData.cesium) {
      initCesiumViewer();
    }

  } catch (err) {
    console.error("Failed to load stage:", err);
    alert(`Failed to load stage: ${err.message}`);
  } finally {
    if (loading) loading.classList.add("hidden");
  }
}

export function updateStageMetadataUI(data) {
  const m = data.metadata || {};
  const setEl = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setEl("stat-prims", m.primCount || data.prims?.length || 0);
  setEl("stat-mats", m.materialCount || Object.keys(data.materials || {}).length || 0);
  setEl("stat-lights", m.lightCount || data.lights?.length || 0);
  setEl("stat-cameras", m.cameraCount || data.cameras?.length || 0);
  setEl("stat-meters-unit", m.metersPerUnit || 0.01);
  setEl("stat-up-axis", m.upAxis || "Y");

  // Show physics action bar if rigid bodies exist
  const physicsToolbar = document.getElementById("physics-toolbar");
  if (physicsToolbar) {
    physicsToolbar.classList.toggle("hidden", !(m.rigidBodyCount && m.rigidBodyCount > 0));
  }

  // Show BIM toolbar if BIM elements exist
  const bimToolbar = document.getElementById("bim-toolbar");
  if (bimToolbar) {
    const isBim = (m.bimCount && m.bimCount > 0) || (data.bimSummary && data.bimSummary.elementCount > 0);
    bimToolbar.classList.toggle("hidden", !isBim);
  }
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}
