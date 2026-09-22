/**
 * Synthetic Data Generation (SDG) Dashboard & Annotation Overlay Manager.
 */

import { appState } from "../state.js";

export function initSdgDashboard() {
  const panel = document.getElementById("sdg-panel");
  if (!panel) return;

  loadSdgData();
}

export async function loadSdgData() {
  try {
    let res = await fetch("api/sdg.json").catch(() => null);
    if (!res || !res.ok) {
      res = await fetch("/api/sdg");
    }
    if (!res.ok) return;

    const data = await res.json();
    appState.sdgData = data;
    renderSdgUI(data);
  } catch (err) {
    console.debug("SDG data not available for this stage:", err);
  }
}

export function renderSdgUI(data) {
  const framesList = document.getElementById("sdg-frames-list");
  if (!framesList || !data || !data.frames) return;

  framesList.innerHTML = "";
  data.frames.forEach((frame, idx) => {
    const thumb = document.createElement("div");
    thumb.className = `sdg-thumb ${idx === appState.currentSdgFrameIdx ? 'active' : ''}`;
    thumb.dataset.idx = idx;

    const img = document.createElement("img");
    img.src = frame.rgb_image || `sdg_media/rgb_${String(idx).padStart(4, "0")}.png`;
    img.alt = `Frame ${idx}`;

    const label = document.createElement("span");
    label.className = "sdg-thumb-label";
    label.textContent = `#${idx + 1}`;

    thumb.appendChild(img);
    thumb.appendChild(label);

    thumb.addEventListener("click", () => displaySdgFrame(idx));
    framesList.appendChild(thumb);
  });

  displaySdgFrame(0);
}

export function displaySdgFrame(idx) {
  if (!appState.sdgData || !appState.sdgData.frames) return;
  appState.currentSdgFrameIdx = idx;

  const frame = appState.sdgData.frames[idx];
  if (!frame) return;

  // Update active thumbnail
  document.querySelectorAll(".sdg-thumb").forEach(t => {
    t.classList.toggle("active", parseInt(t.dataset.idx, 10) === idx);
  });

  const preview = document.getElementById("sdg-preview-image");
  if (preview) {
    preview.src = frame.bbox_overlay || frame.rgb_image || `sdg_media/bbox_overlay_${String(idx).padStart(4, "0")}.png`;
  }

  const meta = document.getElementById("sdg-frame-meta");
  if (meta) {
    meta.innerHTML = `
      <div><strong>Frame:</strong> ${idx + 1} / ${appState.sdgData.frames.length}</div>
      <div><strong>Objects Detected:</strong> ${frame.bounding_boxes ? frame.bounding_boxes.length : 0}</div>
      <div><strong>Resolution:</strong> ${frame.width || 1280} x ${frame.height || 720}</div>
    `;
  }
}
