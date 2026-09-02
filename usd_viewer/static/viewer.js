/**
 * OpenUSD 3D Interactive Studio Engine
 * WebGL PBR Renderer, Prim Inspector, Stage Outliner & Live PhysX Simulation.
 */

// State
let stageData = null;
let currentStagePath = "";
let scene, camera, renderer, controls;
let scenePrims = new Map(); // path -> THREE.Mesh
let selectedPrimPath = null;
let highlightBox = null;
let gridHelper = null;
let axesHelper = null;

// Physics Simulation State (Cannon.js)
let physicsWorld = null;
let physicsBodies = new Map(); // path -> CANNON.Body
let initialTransforms = new Map(); // path -> { pos: THREE.Vector3, quat: THREE.Quaternion }
let isSimulating = false;
let physicsTimeStep = 1 / 60;
let gravityMagnitude = 9.81;

// Performance / Stats
let frameCount = 0;
let lastFpsTime = performance.now();
let fps = 60;

// Shading modes: 'pbr', 'wireframe', 'normal'
let currentShadingMode = 'pbr';

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  initThree();
  initEventListeners();
  fetchStageList();
  animate();
});

// -------------------------------------------------------------
// 1. Three.js Engine Setup
// -------------------------------------------------------------
function initThree() {
  const container = document.getElementById("viewport-container");
  const canvas = document.getElementById("webgl-canvas");

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0c0f14);

  camera = new THREE.PerspectiveCamera(
    45,
    container.clientWidth / container.clientHeight,
    1,
    50000
  );
  camera.position.set(200, 250, 450);

  renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: true,
    powerPreference: "high-performance"
  });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;

  controls = new THREE.OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(0, 30, 0);

  // Default Helpers
  gridHelper = new THREE.GridHelper(1000, 50, 0x38bdf8, 0x21262d);
  gridHelper.position.y = 0;
  scene.add(gridHelper);

  axesHelper = new THREE.AxesHelper(50);
  scene.add(axesHelper);

  // Selection Highlight Box Helper
  const boxGeo = new THREE.BoxGeometry(1, 1, 1);
  const boxMat = new THREE.MeshBasicMaterial({
    color: 0x76b900,
    wireframe: true,
    transparent: true,
    opacity: 0.8
  });
  highlightBox = new THREE.Mesh(boxGeo, boxMat);
  highlightBox.visible = false;
  scene.add(highlightBox);

  // Window Resize
  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });
}

// -------------------------------------------------------------
// 2. Stage Fetching & Loading
// -------------------------------------------------------------
async function fetchStageList() {
  try {
    const res = await fetch("/api/stages");
    const stages = await res.json();
    const select = document.getElementById("stage-select");
    select.innerHTML = "";

    if (stages.length === 0) {
      select.innerHTML = `<option value="">No USD stages found</option>`;
      return;
    }

    stages.forEach((stg, idx) => {
      const opt = document.createElement("option");
      opt.value = stg.relPath;
      opt.textContent = `${stg.name} (${stg.relPath})`;
      select.appendChild(opt);
    });

    // Default select physics playground if available
    const physicsStg = stages.find(s => s.name.includes("physics"));
    if (physicsStg) {
      select.value = physicsStg.relPath;
    } else {
      select.value = stages[0].relPath;
    }

    loadStage(select.value);
  } catch (err) {
    console.error("Error fetching USD stages:", err);
  }
}

async function loadStage(stagePath) {
  currentStagePath = stagePath;
  const select = document.getElementById("stage-select");
  if (select && select.value !== stagePath) {
    select.value = stagePath;
  }

  // Stop simulation if running
  stopPhysicsSimulation();

  try {
    const res = await fetch(`/api/stage?path=${encodeURIComponent(stagePath)}`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    stageData = await res.json();

    buildScene(stageData);
    buildOutlinerTree(stageData.hierarchy);
    setupCameraOptions(stageData.cameras);
    updateBadges(stageData.metadata);

    // Setup Physics if stage contains rigid bodies
    if (stageData.metadata.rigidBodyCount > 0) {
      document.getElementById("physics-toolbar").classList.remove("hidden");
      setupPhysicsWorld(stageData);
    } else {
      document.getElementById("physics-toolbar").classList.add("hidden");
    }

    // Auto-frame camera
    frameScene();
  } catch (err) {
    console.error("Failed to load stage:", err);
  }
}

// Expose globally
window.loadStage = loadStage;

// -------------------------------------------------------------
// 3. 3D Scene Builder from USD JSON
// -------------------------------------------------------------
function buildScene(data) {
  // Clear previous meshes & lights (except helpers)
  scenePrims.forEach(mesh => scene.remove(mesh));
  scenePrims.clear();
  initialTransforms.clear();

  // Remove existing non-helper lights
  const toRemove = [];
  scene.traverse(child => {
    if (child.isLight) toRemove.push(child);
  });
  toRemove.forEach(light => scene.remove(light));

  // 1. Build Lights
  buildLights(data.lights);

  // 2. Build Materials Library
  const materialsMap = buildMaterials(data.materials);

  // 3. Build Prims
  data.prims.forEach(prim => {
    const mesh = createMeshForPrim(prim, materialsMap);
    if (mesh) {
      mesh.userData = prim;
      scenePrims.set(prim.path, mesh);
      scene.add(mesh);

      // Save initial rest transform for physics reset
      initialTransforms.set(prim.path, {
        pos: mesh.position.clone(),
        quat: mesh.quaternion.clone(),
        scale: mesh.scale.clone()
      });
    }
  });

  // Apply current shading mode
  applyShadingMode(currentShadingMode);
}

function buildLights(usdLights) {
  let hasDome = false;
  let hasDistant = false;

  usdLights.forEach(l => {
    const color = new THREE.Color(l.color[0], l.color[1], l.color[2]);
    const intensity = Math.min(l.intensity / 800, 3.5); // Normalize USD Lux intensity

    if (l.type === "DomeLight") {
      hasDome = true;
      const hemi = new THREE.HemisphereLight(color, 0x111625, intensity * 0.9);
      scene.add(hemi);
    } else if (l.type === "DistantLight") {
      hasDistant = true;
      const dirLight = new THREE.DirectionalLight(color, intensity);
      if (l.position) {
        dirLight.position.set(l.position[0], l.position[1], l.position[2]);
      } else {
        dirLight.position.set(150, 300, 150);
      }
      dirLight.castShadow = true;
      dirLight.shadow.mapSize.width = 2048;
      dirLight.shadow.mapSize.height = 2048;
      dirLight.shadow.camera.near = 10;
      dirLight.shadow.camera.far = 2000;
      const d = 400;
      dirLight.shadow.camera.left = -d;
      dirLight.shadow.camera.right = d;
      dirLight.shadow.camera.top = d;
      dirLight.shadow.camera.bottom = -d;
      dirLight.shadow.bias = -0.0005;
      scene.add(dirLight);
    } else if (l.type === "SphereLight") {
      const pLight = new THREE.PointLight(color, intensity * 2, 500);
      if (l.position) pLight.position.set(l.position[0], l.position[1], l.position[2]);
      scene.add(pLight);
    }
  });

  // Fallback default studio lights if none in USD
  if (!hasDome) {
    scene.add(new THREE.AmbientLight(0xdde5f4, 0.6));
  }
  if (!hasDistant) {
    const key = new THREE.DirectionalLight(0xfff5e6, 1.2);
    key.position.set(200, 400, 200);
    key.castShadow = true;
    scene.add(key);
  }
}

function buildMaterials(usdMaterials) {
  const map = new Map();

  for (const [path, mat] of Object.entries(usdMaterials)) {
    const diffuse = new THREE.Color(mat.diffuseColor[0], mat.diffuseColor[1], mat.diffuseColor[2]);
    const emissive = new THREE.Color(mat.emissiveColor[0], mat.emissiveColor[1], mat.emissiveColor[2]);
    const hasEmissive = mat.emissiveColor[0] > 0.05 || mat.emissiveColor[1] > 0.05 || mat.emissiveColor[2] > 0.05;

    const threeMat = new THREE.MeshPhysicalMaterial({
      color: diffuse,
      roughness: Math.max(0.04, mat.roughness),
      metalness: mat.metallic,
      emissive: emissive,
      emissiveIntensity: hasEmissive ? 2.5 : 0.0,
      transparent: mat.opacity < 0.99,
      opacity: mat.opacity,
      ior: mat.ior || 1.5,
      clearcoat: mat.metallic > 0.5 ? 0.3 : 0.0,
      clearcoatRoughness: 0.1,
    });

    threeMat.userData = mat;
    map.set(path, threeMat);
  }

  return map;
}

function createMeshForPrim(prim, materialsMap) {
  let geometry = null;
  const props = prim.geomProps || {};

  switch (prim.type) {
    case "Cube": {
      const size = props.size || 1.0;
      geometry = new THREE.BoxGeometry(size, size, size);
      break;
    }
    case "Sphere": {
      const radius = props.radius || 1.0;
      geometry = new THREE.SphereGeometry(radius, 32, 24);
      break;
    }
    case "Cylinder": {
      const radius = props.radius || 1.0;
      const height = props.height || 2.0;
      geometry = new THREE.CylinderGeometry(radius, radius, height, 32);
      break;
    }
    case "Capsule": {
      const radius = props.radius || 0.5;
      const height = props.height || 1.0;
      geometry = new THREE.CylinderGeometry(radius, radius, height, 24);
      break;
    }
    case "Plane": {
      const width = props.width || 1000.0;
      const length = props.length || 1000.0;
      geometry = new THREE.PlaneGeometry(width, length);
      geometry.rotateX(-Math.PI / 2); // default USD Y-up plane
      break;
    }
    case "Mesh": {
      if (props.points && props.indices) {
        geometry = new THREE.BufferGeometry();
        const vertices = [];
        props.indices.forEach(idx => {
          const pt = props.points[idx];
          if (pt) vertices.push(pt[0], pt[1], pt[2]);
        });
        geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
        geometry.computeVertexNormals();
      }
      break;
    }
  }

  if (!geometry) return null;

  // Material assignment
  let material = materialsMap.get(prim.materialPath);
  if (!material) {
    material = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      roughness: 0.5,
      metalness: 0.1
    });
  }

  const mesh = new THREE.Mesh(geometry, material);

  // Apply USD Matrix transform
  if (prim.matrix && prim.matrix.length === 16) {
    const mat = new THREE.Matrix4();
    mat.fromArray(prim.matrix);
    mat.decompose(mesh.position, mesh.quaternion, mesh.scale);
  } else {
    mesh.position.set(prim.position[0], prim.position[1], prim.position[2]);
    mesh.scale.set(prim.scale[0], prim.scale[1], prim.scale[2]);
  }

  mesh.castShadow = true;
  mesh.receiveShadow = true;

  return mesh;
}

// -------------------------------------------------------------
// 4. Live Physics Simulation (Cannon.js integration)
// -------------------------------------------------------------
function setupPhysicsWorld(data) {
  physicsWorld = new CANNON.World();
  physicsWorld.gravity.set(0, -gravityMagnitude * 100, 0); // scale for cm units
  physicsWorld.broadphase = new CANNON.NaiveBroadphase();
  physicsWorld.solver.iterations = 15;
  physicsWorld.defaultContactMaterial.friction = 0.4;
  physicsWorld.defaultContactMaterial.restitution = 0.2;

  physicsBodies.clear();

  data.prims.forEach(prim => {
    const mesh = scenePrims.get(prim.path);
    if (!mesh) return;

    const phys = prim.physics;
    if (!phys.isCollisionEnabled && !phys.isRigidBody) return;

    let shape = null;
    const props = prim.geomProps || {};
    const scale = mesh.scale;

    if (prim.type === "Cube") {
      const size = props.size || 1.0;
      const halfExtents = new CANNON.Vec3(
        (size * scale.x) * 0.5,
        (size * scale.y) * 0.5,
        (size * scale.z) * 0.5
      );
      shape = new CANNON.Box(halfExtents);
    } else if (prim.type === "Sphere") {
      const radius = (props.radius || 1.0) * scale.x;
      shape = new CANNON.Sphere(radius);
    } else if (prim.type === "Plane") {
      shape = new CANNON.Plane();
    } else if (prim.type === "Cylinder") {
      const r = (props.radius || 1.0) * scale.x;
      const h = (props.height || 2.0) * scale.y;
      shape = new CANNON.Cylinder(r, r, h, 16);
    }

    if (!shape) return;

    const mass = phys.isRigidBody ? (phys.mass || 1.0) : 0; // mass 0 = static collider
    const body = new CANNON.Body({ mass: mass, shape: shape });

    if (prim.type === "Plane") {
      // Rotate Cannon plane to match USD ground (Y-Up)
      body.quaternion.setFromAxisAngle(new CANNON.Vec3(1, 0, 0), -Math.PI / 2);
    } else {
      body.position.set(mesh.position.x, mesh.position.y, mesh.position.z);
      body.quaternion.set(mesh.quaternion.x, mesh.quaternion.y, mesh.quaternion.z, mesh.quaternion.w);
    }

    physicsWorld.addBody(body);
    physicsBodies.set(prim.path, body);
  });
}

function startPhysicsSimulation() {
  if (!physicsWorld) return;
  isSimulating = true;
  const btn = document.getElementById("btn-play-physics");
  btn.classList.add("playing");
  document.getElementById("play-btn-text").textContent = "Pause";
}

function stopPhysicsSimulation() {
  isSimulating = false;
  const btn = document.getElementById("btn-play-physics");
  if (btn) {
    btn.classList.remove("playing");
    document.getElementById("play-btn-text").textContent = "Simulate";
  }
}

function resetPhysicsSimulation() {
  stopPhysicsSimulation();
  
  // Restore all meshes & Cannon bodies to initial transforms
  initialTransforms.forEach((init, path) => {
    const mesh = scenePrims.get(path);
    if (mesh) {
      mesh.position.copy(init.pos);
      mesh.quaternion.copy(init.quat);
      mesh.scale.copy(init.scale);
    }

    const body = physicsBodies.get(path);
    if (body) {
      body.position.set(init.pos.x, init.pos.y, init.pos.z);
      body.quaternion.set(init.quat.x, init.quat.y, init.quat.z, init.quat.w);
      body.velocity.set(0, 0, 0);
      body.angularVelocity.set(0, 0, 0);
    }
  });

  if (selectedPrimPath) updateHighlightBox(selectedPrimPath);
}

function nudgeTriggerBall() {
  // Find trigger sphere
  physicsBodies.forEach((body, path) => {
    if (path.toLowerCase().includes("ball") || path.toLowerCase().includes("sphere")) {
      body.applyImpulse(new CANNON.Vec3(25, 0, 0), body.position);
      if (!isSimulating) startPhysicsSimulation();
    }
  });
}

// -------------------------------------------------------------
// 5. Stage Outliner Tree Builder
// -------------------------------------------------------------
function buildOutlinerTree(rootNode) {
  const container = document.getElementById("outliner-tree");
  container.innerHTML = "";

  function createNodeElement(node, depth = 0) {
    const div = document.createElement("div");
    div.className = "tree-node-wrapper";

    const row = document.createElement("div");
    row.className = "tree-node";
    row.dataset.path = node.path;

    // Indentation
    for (let i = 0; i < depth; i++) {
      const indent = document.createElement("span");
      indent.className = "tree-indent";
      row.appendChild(indent);
    }

    // Expand/Collapse toggle
    const toggle = document.createElement("span");
    toggle.className = "tree-toggle";
    toggle.textContent = (node.children && node.children.length > 0) ? "▼" : "•";
    row.appendChild(toggle);

    // Prim Icon
    const icon = document.createElement("span");
    icon.className = `tree-icon ${getIconClass(node.type)}`;
    icon.textContent = getIconLabel(node.type);
    row.appendChild(icon);

    // Prim Name
    const name = document.createElement("span");
    name.className = "tree-name";
    name.textContent = node.name;
    row.appendChild(name);

    // RigidBody badge
    if (node.hasRigidBody) {
      const tag = document.createElement("span");
      tag.className = "tree-tag";
      tag.textContent = "PhysX";
      row.appendChild(tag);
    }

    div.appendChild(row);

    // Children
    if (node.children && node.children.length > 0) {
      const childrenContainer = document.createElement("div");
      childrenContainer.className = "tree-children";

      node.children.forEach(child => {
        childrenContainer.appendChild(createNodeElement(child, depth + 1));
      });

      div.appendChild(childrenContainer);

      // Toggle click
      toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        const isHidden = childrenContainer.style.display === "none";
        childrenContainer.style.display = isHidden ? "block" : "none";
        toggle.textContent = isHidden ? "▼" : "▶";
      });
    }

    // Node select click
    row.addEventListener("click", () => {
      selectPrim(node.path);
    });

    return div;
  }

  if (rootNode) {
    container.appendChild(createNodeElement(rootNode));
  }
}

function getIconClass(type) {
  switch (type) {
    case "Cube": return "icon-cube";
    case "Sphere": return "icon-sphere";
    case "Cylinder": return "icon-cylinder";
    case "Plane": return "icon-plane";
    case "Material": return "icon-material";
    case "DomeLight":
    case "DistantLight":
    case "SphereLight": return "icon-light";
    case "Camera": return "icon-camera";
    default: return "icon-xform";
  }
}

function getIconLabel(type) {
  switch (type) {
    case "Cube": return "BOX";
    case "Sphere": return "SPH";
    case "Cylinder": return "CYL";
    case "Plane": return "PLN";
    case "Material": return "MAT";
    case "DomeLight": return "DOME";
    case "DistantLight": return "SUN";
    case "SphereLight": return "LGT";
    case "Camera": return "CAM";
    default: return "XFM";
  }
}

// -------------------------------------------------------------
// 6. Prim Selection & Inspector Panel
// -------------------------------------------------------------
function selectPrim(path) {
  selectedPrimPath = path;

  // Highlight in Tree
  document.querySelectorAll(".tree-node").forEach(n => {
    n.classList.toggle("selected", n.dataset.path === path);
  });

  // Highlight in 3D Viewport
  updateHighlightBox(path);

  // Update Top Selection Tag
  const tag = document.getElementById("selection-tag");
  if (path) {
    tag.classList.remove("hidden");
    document.getElementById("selection-tag-name").textContent = path;
  } else {
    tag.classList.add("hidden");
  }

  // Populate Inspector
  renderInspector(path);
}

function updateHighlightBox(path) {
  const mesh = scenePrims.get(path);
  if (mesh) {
    highlightBox.visible = true;
    mesh.geometry.computeBoundingBox();
    const bbox = mesh.geometry.boundingBox;
    const size = new THREE.Vector3();
    bbox.getSize(size);
    size.multiply(mesh.scale);

    highlightBox.scale.copy(size.multiplyScalar(1.05));
    highlightBox.position.copy(mesh.position);
    highlightBox.quaternion.copy(mesh.quaternion);
  } else {
    highlightBox.visible = false;
  }
}

function renderInspector(path) {
  const container = document.getElementById("inspector-content");
  if (!path) {
    container.innerHTML = `
      <div class="inspector-placeholder">
        <p>Select any Prim in the 3D viewport or Stage Outliner to inspect its OpenUSD properties, materials, and physics schemas.</p>
      </div>`;
    return;
  }

  // Find prim data
  const prim = stageData.prims.find(p => p.path === path);
  const mesh = scenePrims.get(path);

  let html = `
    <div class="inspector-section">
      <div class="section-header">
        <span>USD Prim Info</span>
        <span class="badge badge-accent">${prim ? prim.type : 'Xform'}</span>
      </div>
      <div class="section-body">
        <div class="prop-row">
          <span class="prop-label">Path</span>
          <span class="prop-value" title="${path}">${path}</span>
        </div>
        <div class="prop-row">
          <span class="prop-label">Name</span>
          <span class="prop-value">${path.split('/').pop()}</span>
        </div>
      </div>
    </div>
  `;

  if (mesh) {
    html += `
      <div class="inspector-section">
        <div class="section-header">
          <span>Transform (XformOps)</span>
        </div>
        <div class="section-body">
          <div class="prop-label">Position (Translate)</div>
          <div class="vec3-grid">
            <div class="vec3-item"><span class="vec3-axis axis-x">X</span><span class="vec3-val">${mesh.position.x.toFixed(2)}</span></div>
            <div class="vec3-item"><span class="vec3-axis axis-y">Y</span><span class="vec3-val">${mesh.position.y.toFixed(2)}</span></div>
            <div class="vec3-item"><span class="vec3-axis axis-z">Z</span><span class="vec3-val">${mesh.position.z.toFixed(2)}</span></div>
          </div>

          <div class="prop-label" style="margin-top: 6px;">Scale</div>
          <div class="vec3-grid">
            <div class="vec3-item"><span class="vec3-axis axis-x">X</span><span class="vec3-val">${mesh.scale.x.toFixed(2)}</span></div>
            <div class="vec3-item"><span class="vec3-axis axis-y">Y</span><span class="vec3-val">${mesh.scale.y.toFixed(2)}</span></div>
            <div class="vec3-item"><span class="vec3-axis axis-z">Z</span><span class="vec3-val">${mesh.scale.z.toFixed(2)}</span></div>
          </div>
        </div>
      </div>
    `;
  }

  if (prim && prim.materialPath && stageData.materials[prim.materialPath]) {
    const mat = stageData.materials[prim.materialPath];
    const diffHex = rgbToHex(mat.diffuseColor);
    const emisHex = rgbToHex(mat.emissiveColor);

    html += `
      <div class="inspector-section">
        <div class="section-header">
          <span>Bound Material (UsdShade)</span>
        </div>
        <div class="section-body">
          <div class="prop-row">
            <span class="prop-label">Material</span>
            <span class="prop-value">${mat.name}</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Diffuse Color</span>
            <div class="color-preview-row">
              <div class="color-swatch" style="background: ${diffHex};"></div>
              <span class="prop-value">${diffHex}</span>
            </div>
          </div>
          <div class="prop-row">
            <span class="prop-label">Emissive Color</span>
            <div class="color-preview-row">
              <div class="color-swatch" style="background: ${emisHex};"></div>
              <span class="prop-value">${emisHex}</span>
            </div>
          </div>
          <div class="prop-row">
            <span class="prop-label">Roughness</span>
            <span class="prop-value">${mat.roughness.toFixed(2)}</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Metallic</span>
            <span class="prop-value">${mat.metallic.toFixed(2)}</span>
          </div>
        </div>
      </div>
    `;
  }

  if (prim && prim.physics) {
    const phys = prim.physics;
    html += `
      <div class="inspector-section">
        <div class="section-header">
          <span>UsdPhysics API Schemas</span>
        </div>
        <div class="section-body">
          <div class="schema-badge-list">
            ${phys.isRigidBody ? '<span class="schema-badge">RigidBodyAPI</span>' : ''}
            ${phys.isCollisionEnabled ? '<span class="schema-badge">CollisionAPI</span>' : ''}
            ${phys.mass !== null ? '<span class="schema-badge">MassAPI</span>' : ''}
          </div>
          <div class="prop-row">
            <span class="prop-label">Is Rigid Body</span>
            <span class="prop-value">${phys.isRigidBody ? 'Yes (Dynamic)' : 'No (Static)'}</span>
          </div>
          ${phys.mass !== null ? `<div class="prop-row"><span class="prop-label">Mass</span><span class="prop-value">${phys.mass} kg</span></div>` : ''}
          ${phys.density !== null ? `<div class="prop-row"><span class="prop-label">Density</span><span class="prop-value">${phys.density} kg/m³</span></div>` : ''}
          <div class="prop-row">
            <span class="prop-label">Collider Shape</span>
            <span class="prop-value">${phys.approximation}</span>
          </div>
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
}

function rgbToHex(rgb) {
  const r = Math.round(rgb[0] * 255).toString(16).padStart(2, '0');
  const g = Math.round(rgb[1] * 255).toString(16).padStart(2, '0');
  const b = Math.round(rgb[2] * 255).toString(16).padStart(2, '0');
  return `#${r}${g}${b}`;
}

// -------------------------------------------------------------
// 7. Raycasting & Interaction
// -------------------------------------------------------------
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

function onPointerDown(e) {
  if (e.button !== 0) return; // Left click only
  const canvas = document.getElementById("webgl-canvas");
  const rect = canvas.getBoundingClientRect();
  
  mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  const meshes = Array.from(scenePrims.values());
  const intersects = raycaster.intersectObjects(meshes);

  if (intersects.length > 0) {
    const clickedMesh = intersects[0].object;
    if (clickedMesh.userData && clickedMesh.userData.path) {
      selectPrim(clickedMesh.userData.path);
    }
  }
}

// -------------------------------------------------------------
// 8. UI Controls & Event Listeners
// -------------------------------------------------------------
function initEventListeners() {
  document.getElementById("webgl-canvas").addEventListener("pointerdown", onPointerDown);

  // Stage select
  document.getElementById("stage-select").addEventListener("change", (e) => {
    if (e.target.value) loadStage(e.target.value);
  });

  // Camera selector
  document.getElementById("camera-select").addEventListener("change", (e) => {
    switchCamera(e.target.value);
  });

  // Shading mode
  document.getElementById("render-mode").addEventListener("change", (e) => {
    applyShadingMode(e.target.value);
  });

  // Grid toggle
  const gridBtn = document.getElementById("btn-grid-toggle");
  gridBtn.addEventListener("click", () => {
    gridHelper.visible = !gridHelper.visible;
    axesHelper.visible = gridHelper.visible;
    gridBtn.classList.toggle("active", gridHelper.visible);
  });

  // Frame scene
  document.getElementById("btn-reset-cam").addEventListener("click", frameScene);

  // Search filter in Outliner
  document.getElementById("outliner-search").addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase();
    document.querySelectorAll(".tree-node-wrapper").forEach(el => {
      const text = el.textContent.toLowerCase();
      el.style.display = text.includes(query) ? "block" : "none";
    });
  });

  // Expand / Collapse all
  document.getElementById("btn-expand-all").addEventListener("click", () => {
    document.querySelectorAll(".tree-children").forEach(c => c.style.display = "block");
  });
  document.getElementById("btn-collapse-all").addEventListener("click", () => {
    document.querySelectorAll(".tree-children").forEach(c => c.style.display = "none");
  });

  // Physics simulation buttons
  document.getElementById("btn-play-physics").addEventListener("click", () => {
    if (isSimulating) stopPhysicsSimulation();
    else startPhysicsSimulation();
  });

  document.getElementById("btn-reset-physics").addEventListener("click", resetPhysicsSimulation);
  document.getElementById("btn-nudge-ball").addEventListener("click", nudgeTriggerBall);

  document.getElementById("gravity-select").addEventListener("change", (e) => {
    gravityMagnitude = parseFloat(e.target.value);
    if (physicsWorld) {
      physicsWorld.gravity.set(0, -gravityMagnitude * 100, 0);
    }
  });

  // Hotkeys: Space (Play), F (Frame)
  window.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
    if (e.code === "Space") {
      e.preventDefault();
      if (isSimulating) stopPhysicsSimulation();
      else startPhysicsSimulation();
    } else if (e.code === "KeyF") {
      frameScene();
    }
  });
}

function setupCameraOptions(usdCameras) {
  const select = document.getElementById("camera-select");
  select.innerHTML = `<option value="free">Free Orbit Camera</option>`;

  usdCameras.forEach(cam => {
    const opt = document.createElement("option");
    opt.value = cam.path;
    opt.textContent = `${cam.name} (${cam.focalLength}mm)`;
    select.appendChild(opt);
  });

  select.innerHTML += `
    <option value="top">Top View (XZ)</option>
    <option value="front">Front View (XY)</option>
    <option value="side">Side View (YZ)</option>
  `;
}

function switchCamera(val) {
  if (val === "free") return;

  if (val === "top") {
    camera.position.set(0, 500, 0);
    controls.target.set(0, 0, 0);
  } else if (val === "front") {
    camera.position.set(0, 100, 500);
    controls.target.set(0, 50, 0);
  } else if (val === "side") {
    camera.position.set(500, 100, 0);
    controls.target.set(0, 50, 0);
  } else {
    // Preset USD camera
    const usdCam = stageData.cameras.find(c => c.path === val);
    if (usdCam) {
      camera.position.set(usdCam.position[0], usdCam.position[1], usdCam.position[2]);
      controls.target.set(0, 30, 0);
      if (usdCam.fov) camera.fov = usdCam.fov;
      camera.updateProjectionMatrix();
    }
  }
}

function applyShadingMode(mode) {
  currentShadingMode = mode;
  scenePrims.forEach(mesh => {
    if (mode === "wireframe") {
      mesh.material.wireframe = true;
    } else if (mode === "normal") {
      mesh.material.wireframe = false;
      mesh.material = new THREE.MeshNormalMaterial();
    } else {
      mesh.material.wireframe = false;
      // Restore PBR
      const prim = mesh.userData;
      if (prim && prim.materialPath && stageData.materials[prim.materialPath]) {
        const mat = stageData.materials[prim.materialPath];
        mesh.material = new THREE.MeshPhysicalMaterial({
          color: new THREE.Color(mat.diffuseColor[0], mat.diffuseColor[1], mat.diffuseColor[2]),
          roughness: mat.roughness,
          metalness: mat.metallic,
          emissive: new THREE.Color(mat.emissiveColor[0], mat.emissiveColor[1], mat.emissiveColor[2]),
          emissiveIntensity: mat.emissiveColor[0] > 0.05 ? 2.5 : 0.0
        });
      }
    }
  });
}

function frameScene() {
  if (selectedPrimPath && scenePrims.has(selectedPrimPath)) {
    const mesh = scenePrims.get(selectedPrimPath);
    controls.target.copy(mesh.position);
    camera.position.set(mesh.position.x + 80, mesh.position.y + 60, mesh.position.z + 120);
  } else {
    // Compute stage bounding box
    const box = new THREE.Box3();
    scenePrims.forEach(mesh => box.expandByObject(mesh));
    const center = new THREE.Vector3();
    box.getCenter(center);
    controls.target.copy(center);
    camera.position.set(center.x + 180, center.y + 220, center.z + 360);
  }
}

function updateBadges(metadata) {
  document.getElementById("badge-axis").textContent = `Up: ${metadata.upAxis}`;
  document.getElementById("badge-units").textContent = `Scale: ${metadata.metersPerUnit === 0.01 ? 'cm' : 'm'}`;
  document.getElementById("badge-prims").textContent = `${metadata.primCount} Prims`;
}

// -------------------------------------------------------------
// 9. Animation & Simulation Loop
// -------------------------------------------------------------
function animate() {
  requestAnimationFrame(animate);

  // Step physics simulation
  if (isSimulating && physicsWorld) {
    physicsWorld.step(physicsTimeStep);

    // Sync mesh transforms from physics bodies
    physicsBodies.forEach((body, path) => {
      const mesh = scenePrims.get(path);
      if (mesh && body.mass > 0) { // only dynamic bodies move
        mesh.position.set(body.position.x, body.position.y, body.position.z);
        mesh.quaternion.set(body.quaternion.x, body.quaternion.y, body.quaternion.z, body.quaternion.w);
      }
    });

    if (selectedPrimPath) updateHighlightBox(selectedPrimPath);
  }

  // Update OrbitControls
  controls.update();

  // Render WebGL frame
  renderer.render(scene, camera);

  // FPS Counter
  frameCount++;
  const now = performance.now();
  if (now - lastFpsTime >= 1000) {
    fps = Math.round((frameCount * 1000) / (now - lastFpsTime));
    document.getElementById("badge-fps").textContent = `${fps} FPS`;
    frameCount = 0;
    lastFpsTime = now;
  }
}
