/**
 * 4D Construction Phasing & Lifecycle Timeline Simulator.
 */

import { appState } from "../state.js";
import { applyBimFilters } from "./bim_manager.js";
import { toggleClashMode } from "./clash_viewer.js";

export function toggle4DPhasingMode(forceState) {
  if (typeof forceState === "boolean") {
    appState.is4DMode = forceState;
  } else {
    appState.is4DMode = !appState.is4DMode;
  }

  const btn = document.getElementById("btn-bim-4d");
  const dock = document.getElementById("phasing-dock");
  if (btn) btn.classList.toggle("active", appState.is4DMode);
  if (dock) dock.classList.toggle("hidden", !appState.is4DMode);

  if (!appState.is4DMode) {
    if (appState.is4DPlaying) toggle4DPlayback(false);
    restore4DMaterials();
    applyBimFilters();
  } else {
    if (appState.isClashMode) toggleClashMode(false);
    if (appState.current4DMonth >= 12) {
      appState.current4DMonth = 0;
    }
    update4DUI();
    applyBimFilters();
  }
}

export function set4DMonth(month) {
  appState.current4DMonth = Math.max(0, Math.min(12, parseInt(month, 10)));
  update4DUI();
  applyBimFilters();
}

export function toggle4DPlayback(forcePlay) {
  if (typeof forcePlay === "boolean") {
    appState.is4DPlaying = forcePlay;
  } else {
    appState.is4DPlaying = !appState.is4DPlaying;
  }

  const playBtn = document.getElementById("btn-4d-play");
  const playText = document.getElementById("text-4d-play");
  const playIcon = document.getElementById("icon-4d-play");

  if (appState.is4DPlaying) {
    if (playText) playText.textContent = "Pause";
    if (playIcon) playIcon.innerHTML = `<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>`;
    if (playBtn) playBtn.style.background = "rgba(239, 68, 68, 0.4)";

    if (appState.current4DMonth >= 12) {
      set4DMonth(0);
    }

    if (appState.play4DInterval) clearInterval(appState.play4DInterval);
    const intervalMs = Math.round(1600 / appState.play4DSpeed);
    appState.play4DInterval = setInterval(() => {
      if (appState.current4DMonth >= 12) {
        set4DMonth(0);
      } else {
        set4DMonth(appState.current4DMonth + 1);
      }
    }, intervalMs);
  } else {
    if (playText) playText.textContent = "Play";
    if (playIcon) playIcon.innerHTML = `<path d="M8 5v14l11-7z"/>`;
    if (playBtn) playBtn.style.background = "";
    if (appState.play4DInterval) {
      clearInterval(appState.play4DInterval);
      appState.play4DInterval = null;
    }
  }
}

export function update4DUI() {
  const slider = document.getElementById("phasing-slider");
  const fill = document.getElementById("phasing-progress-fill");
  const pillName = document.getElementById("phasing-pill-name");
  const pillDesc = document.getElementById("phasing-pill-desc");
  const statPct = document.getElementById("phasing-stat-pct");
  const statCount = document.getElementById("phasing-stat-count");

  if (slider) slider.value = appState.current4DMonth;

  // Find active milestone
  const phasing = appState.stageData?.constructionPhasing;
  const milestones = phasing?.milestones || [];
  let currentMilestone = null;

  for (let i = milestones.length - 1; i >= 0; i--) {
    if (appState.current4DMonth >= milestones[i].targetMonth) {
      currentMilestone = milestones[i];
      break;
    }
  }
  if (!currentMilestone && milestones.length > 0) {
    currentMilestone = milestones[0];
  }

  const pct = currentMilestone ? currentMilestone.progressPercent : Math.round((appState.current4DMonth / 12) * 100);
  const builtCount = currentMilestone ? currentMilestone.cumulativeCount : 0;
  const totalCount = phasing ? phasing.totalElements : (appState.stageData?.prims?.length || 0);

  if (fill) fill.style.width = `${pct}%`;
  if (statPct) statPct.textContent = `${pct}%`;
  if (statCount) statCount.textContent = `${builtCount} / ${totalCount} Prims`;

  if (pillName) pillName.textContent = currentMilestone ? currentMilestone.name : `Month ${appState.current4DMonth} Phasing`;
  if (pillDesc) pillDesc.textContent = currentMilestone ? currentMilestone.description : "Continuous building erection and service fit-out.";
}

export function restore4DMaterials() {
  appState.scenePrims.forEach(mesh => {
    mesh.userData._isGhosted = false;
    mesh.userData._isUnderConstruction = false;
    if (mesh.userData._baseMaterial) {
      mesh.material = mesh.userData._baseMaterial.clone();
    }
  });
}
