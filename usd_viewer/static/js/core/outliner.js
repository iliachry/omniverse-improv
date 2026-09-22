/**
 * OpenUSD Hierarchy Outliner Tree Builder.
 */

import { appState } from "../state.js";
import { selectPrim } from "./inspector.js";

export function populateOutliner(hierarchy) {
  const container = document.getElementById("outliner-tree");
  if (!container || !hierarchy) return;

  container.innerHTML = "";
  renderOutlinerNode(hierarchy, container, 0);
}

export function renderOutlinerNode(node, container, level) {
  const item = document.createElement("div");
  item.className = "outliner-item";
  item.dataset.path = node.path;
  item.style.paddingLeft = `${level * 16 + 10}px`;

  // Prim Type Icon
  const icon = document.createElement("span");
  icon.className = "outliner-icon";
  icon.textContent = getPrimTypeIcon(node.type, node);
  item.appendChild(icon);

  // Prim Name
  const label = document.createElement("span");
  label.className = "outliner-label";
  label.textContent = node.name;
  item.appendChild(label);

  // Indicators (RigidBody, Collider)
  if (node.hasRigidBody) {
    const badge = document.createElement("span");
    badge.className = "outliner-badge badge-physics";
    badge.textContent = "PhysX";
    badge.title = "UsdPhysics.RigidBodyAPI applied";
    item.appendChild(badge);
  }

  // Click selection
  item.addEventListener("click", (e) => {
    e.stopPropagation();
    selectPrim(node.path);
  });

  container.appendChild(item);

  // Recurse children
  if (node.children && node.children.length > 0) {
    node.children.forEach(child => renderOutlinerNode(child, container, level + 1));
  }
}

export function filterOutliner(query) {
  const items = document.querySelectorAll(".outliner-item");
  const q = query.toLowerCase().trim();
  items.forEach(item => {
    const name = item.querySelector(".outliner-label")?.textContent.toLowerCase() || "";
    const path = item.dataset.path.toLowerCase();
    item.style.display = (!q || name.includes(q) || path.includes(q)) ? "flex" : "none";
  });
}

function getPrimTypeIcon(type, node) {
  switch (type) {
    case "Xform": return "📁";
    case "Cube": return "🧊";
    case "Cylinder": return "🥫";
    case "Sphere": return "⚪";
    case "Plane": return "🟩";
    case "Mesh": return "🔺";
    case "DomeLight": return "🌅";
    case "DistantLight": return "☀️";
    case "Camera": return "📷";
    case "Material": return "🎨";
    case "Shader": return "✨";
    default: return "🔹";
  }
}
