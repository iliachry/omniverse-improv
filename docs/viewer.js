/**
 * OpenUSD 3D Interactive Studio & SDG Engine
 * WebGL PBR Renderer, Live Shader Editor, Stage Outliner, USDA Exporter,
 * PhysX Dynamic Simulator, and Synthetic Data (SDG) Visualizer.
 */

// State
let stageData = null;
let currentStagePath = "";
let scene, camera, renderer, controls;
let scenePrims = new Map(); // path -> THREE.Mesh
let materialsMap = new Map(); // path -> THREE.MeshPhysicalMaterial
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

// SDG State
let sdgData = null;
let currentSdgFrameIdx = 0;
let cachedImages = new Map();

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  initThree();
  initEventListeners();
  fetchStageList();
  initSdgDashboard();
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
    let stages = null;
    try {
      const staticRes = await fetch("api/stages.json");
      if (staticRes.ok) stages = await staticRes.json();
    } catch (e) {}

    if (!stages) {
      const res = await fetch("/api/stages");
      stages = await res.json();
    }

    const select = document.getElementById("stage-select");
    select.innerHTML = "";

    if (!stages || stages.length === 0) {
      select.innerHTML = `<option value="">No USD stages found</option>`;
      return;
    }

    stages.forEach((stg) => {
      const opt = document.createElement("option");
      opt.value = stg.relPath;
      opt.textContent = `${stg.name} (${stg.relPath})`;
      select.appendChild(opt);
    });

    const defaultStg = stages.find(s => s.name.includes("robotics")) || stages[0];
    select.value = defaultStg.relPath;
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

  stopPhysicsSimulation();

  try {
    let loadedData = null;
    try {
      const staticRes = await fetch("api/stage_data.json");
      if (staticRes.ok) {
        const allData = await staticRes.json();
        loadedData = allData[stagePath] || Object.values(allData)[0];
      }
    } catch (e) {}

    if (!loadedData) {
      const res = await fetch(`/api/stage?path=${encodeURIComponent(stagePath)}`);
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      loadedData = await res.json();
    }

    stageData = loadedData;
    buildScene(stageData);
    buildOutlinerTree(stageData.hierarchy);
    setupCameraOptions(stageData.cameras);
    updateBadges(stageData.metadata);

    // Setup Physics if stage contains rigid bodies
    if (stageData.metadata && stageData.metadata.rigidBodyCount > 0) {
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

window.loadStage = loadStage;

// -------------------------------------------------------------
// 3. 3D Scene Builder from USD JSON
// -------------------------------------------------------------
function buildScene(data) {
  scenePrims.forEach(mesh => scene.remove(mesh));
  scenePrims.clear();
  initialTransforms.clear();

  const toRemove = [];
  scene.traverse(child => {
    if (child.isLight) toRemove.push(child);
  });
  toRemove.forEach(light => scene.remove(light));

  // 1. Build Lights
  buildLights(data.lights);

  // 2. Build Materials Library
  materialsMap = buildMaterials(data.materials);

  // 3. Build Prims
  data.prims.forEach(prim => {
    const mesh = createMeshForPrim(prim, materialsMap);
    if (mesh) {
      mesh.userData = prim;
      scenePrims.set(prim.path, mesh);
      scene.add(mesh);

      initialTransforms.set(prim.path, {
        pos: mesh.position.clone(),
        quat: mesh.quaternion.clone(),
        scale: mesh.scale.clone()
      });
    }
  });

  applyShadingMode(currentShadingMode);
}

function buildLights(usdLights) {
  let hasDome = false;
  let hasDistant = false;

  usdLights.forEach(l => {
    const color = new THREE.Color(l.color[0], l.color[1], l.color[2]);
    const intensity = Math.min(l.intensity / 800, 3.5);

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
      const d = 400;
      dirLight.shadow.camera.left = -d;
      dirLight.shadow.camera.right = d;
      dirLight.shadow.camera.top = d;
      dirLight.shadow.camera.bottom = -d;
      scene.add(dirLight);
    } else if (l.type === "SphereLight") {
      const pLight = new THREE.PointLight(color, intensity * 2, 500);
      if (l.position) pLight.position.set(l.position[0], l.position[1], l.position[2]);
      scene.add(pLight);
    }
  });

  if (!hasDome) scene.add(new THREE.AmbientLight(0xdde5f4, 0.6));
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

    threeMat.userData = { ...mat };
    map.set(path, threeMat);
  }

  return map;
}

function createMeshForPrim(prim, matsMap) {
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
      geometry.rotateX(-Math.PI / 2);
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

  let material = matsMap.get(prim.materialPath);
  if (!material) {
    material = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      roughness: 0.5,
      metalness: 0.1
    });
  }

  const mesh = new THREE.Mesh(geometry, material);

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
  physicsWorld.gravity.set(0, -gravityMagnitude * 100, 0);
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

    const mass = phys.isRigidBody ? (phys.mass || 1.0) : 0;
    const body = new CANNON.Body({ mass: mass, shape: shape });

    if (prim.type === "Plane") {
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
  physicsBodies.forEach((body, path) => {
    if (path.toLowerCase().includes("ball") || path.toLowerCase().includes("trigger") || path.toLowerCase().includes("sphere")) {
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

    for (let i = 0; i < depth; i++) {
      const indent = document.createElement("span");
      indent.className = "tree-indent";
      row.appendChild(indent);
    }

    const toggle = document.createElement("span");
    toggle.className = "tree-toggle";
    toggle.textContent = (node.children && node.children.length > 0) ? "▼" : "•";
    row.appendChild(toggle);

    const icon = document.createElement("span");
    icon.className = `tree-icon ${getIconClass(node.type)}`;
    icon.textContent = getIconLabel(node.type);
    row.appendChild(icon);

    const name = document.createElement("span");
    name.className = "tree-name";
    name.textContent = node.name;
    row.appendChild(name);

    if (node.hasRigidBody) {
      const tag = document.createElement("span");
      tag.className = "tree-tag";
      tag.textContent = "PhysX";
      row.appendChild(tag);
    }

    div.appendChild(row);

    if (node.children && node.children.length > 0) {
      const childrenContainer = document.createElement("div");
      childrenContainer.className = "tree-children";

      node.children.forEach(child => {
        childrenContainer.appendChild(createNodeElement(child, depth + 1));
      });

      div.appendChild(childrenContainer);

      toggle.addEventListener("click", (e) => {
        e.stopPropagation();
        const isHidden = childrenContainer.style.display === "none";
        childrenContainer.style.display = isHidden ? "block" : "none";
        toggle.textContent = isHidden ? "▼" : "▶";
      });
    }

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
// 6. Prim Selection, Inspector & Live PBR Material Editor
// -------------------------------------------------------------
function selectPrim(path) {
  selectedPrimPath = path;

  document.querySelectorAll(".tree-node").forEach(n => {
    n.classList.toggle("selected", n.dataset.path === path);
  });

  updateHighlightBox(path);

  const tag = document.getElementById("selection-tag");
  if (path) {
    tag.classList.remove("hidden");
    document.getElementById("selection-tag-name").textContent = path;
  } else {
    tag.classList.add("hidden");
  }

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

  // Live PBR Material Editor
  if (prim && prim.materialPath && stageData.materials[prim.materialPath]) {
    const mat = stageData.materials[prim.materialPath];
    const diffHex = rgbToHex(mat.diffuseColor);
    const emisHex = rgbToHex(mat.emissiveColor);

    html += `
      <div class="inspector-section">
        <div class="section-header">
          <span>Live PBR Material Editor</span>
          <span class="badge" style="color: var(--accent-green);">UsdShade</span>
        </div>
        <div class="section-body">
          <div class="prop-row">
            <span class="prop-label">Shader</span>
            <span class="prop-value">${mat.name}</span>
          </div>

          <div class="prop-row">
            <span class="prop-label">Diffuse Color</span>
            <div class="color-picker-container">
              <input type="color" id="pbr-diffuse-picker" class="color-input-swatch" value="${diffHex}" data-mat="${prim.materialPath}" />
              <span id="pbr-diffuse-hex" class="prop-value">${diffHex}</span>
            </div>
          </div>

          <div class="prop-row">
            <span class="prop-label">Emissive Glow</span>
            <div class="color-picker-container">
              <input type="color" id="pbr-emissive-picker" class="color-input-swatch" value="${emisHex}" data-mat="${prim.materialPath}" />
              <span id="pbr-emissive-hex" class="prop-value">${emisHex}</span>
            </div>
          </div>

          <div class="slider-row">
            <div class="slider-header">
              <span>Roughness</span>
              <span id="pbr-roughness-val" class="prop-value">${mat.roughness.toFixed(2)}</span>
            </div>
            <div class="slider-input-container">
              <input type="range" id="pbr-roughness-slider" min="0" max="100" value="${Math.round(mat.roughness * 100)}" data-mat="${prim.materialPath}" />
            </div>
          </div>

          <div class="slider-row">
            <div class="slider-header">
              <span>Metallic</span>
              <span id="pbr-metallic-val" class="prop-value">${mat.metallic.toFixed(2)}</span>
            </div>
            <div class="slider-input-container">
              <input type="range" id="pbr-metallic-slider" min="0" max="100" value="${Math.round(mat.metallic * 100)}" data-mat="${prim.materialPath}" />
            </div>
          </div>

          <div class="slider-row">
            <div class="slider-header">
              <span>Opacity</span>
              <span id="pbr-opacity-val" class="prop-value">${(mat.opacity || 1.0).toFixed(2)}</span>
            </div>
            <div class="slider-input-container">
              <input type="range" id="pbr-opacity-slider" min="10" max="100" value="${Math.round((mat.opacity || 1.0) * 100)}" data-mat="${prim.materialPath}" />
            </div>
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
  attachLiveMaterialListeners(prim ? prim.materialPath : null);
}

function attachLiveMaterialListeners(materialPath) {
  if (!materialPath || !stageData.materials[materialPath]) return;

  const matData = stageData.materials[materialPath];
  const threeMat = materialsMap.get(materialPath);

  // Diffuse Color Picker
  const diffPicker = document.getElementById("pbr-diffuse-picker");
  if (diffPicker) {
    diffPicker.addEventListener("input", (e) => {
      const hex = e.target.value;
      document.getElementById("pbr-diffuse-hex").textContent = hex;
      const rgb = hexToRgb(hex);
      matData.diffuseColor = rgb;
      if (threeMat) threeMat.color.set(hex);
    });
  }

  // Emissive Color Picker
  const emisPicker = document.getElementById("pbr-emissive-picker");
  if (emisPicker) {
    emisPicker.addEventListener("input", (e) => {
      const hex = e.target.value;
      document.getElementById("pbr-emissive-hex").textContent = hex;
      const rgb = hexToRgb(hex);
      matData.emissiveColor = rgb;
      if (threeMat) {
        threeMat.emissive.set(hex);
        threeMat.emissiveIntensity = (rgb[0] > 0.05 || rgb[1] > 0.05 || rgb[2] > 0.05) ? 2.5 : 0.0;
      }
    });
  }

  // Roughness Slider
  const roughSlider = document.getElementById("pbr-roughness-slider");
  if (roughSlider) {
    roughSlider.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value) / 100.0;
      document.getElementById("pbr-roughness-val").textContent = val.toFixed(2);
      matData.roughness = val;
      if (threeMat) threeMat.roughness = Math.max(0.04, val);
    });
  }

  // Metallic Slider
  const metalSlider = document.getElementById("pbr-metallic-slider");
  if (metalSlider) {
    metalSlider.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value) / 100.0;
      document.getElementById("pbr-metallic-val").textContent = val.toFixed(2);
      matData.metallic = val;
      if (threeMat) threeMat.metalness = val;
    });
  }

  // Opacity Slider
  const opacSlider = document.getElementById("pbr-opacity-slider");
  if (opacSlider) {
    opacSlider.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value) / 100.0;
      document.getElementById("pbr-opacity-val").textContent = val.toFixed(2);
      matData.opacity = val;
      if (threeMat) {
        threeMat.opacity = val;
        threeMat.transparent = val < 0.99;
      }
    });
  }
}

function hexToRgb(hex) {
  const bigint = parseInt(hex.slice(1), 16);
  const r = ((bigint >> 16) & 255) / 255;
  const g = ((bigint >> 8) & 255) / 255;
  const b = (bigint & 255) / 255;
  return [r, g, b];
}

function rgbToHex(rgb) {
  const r = Math.round(rgb[0] * 255).toString(16).padStart(2, '0');
  const g = Math.round(rgb[1] * 255).toString(16).padStart(2, '0');
  const b = Math.round(rgb[2] * 255).toString(16).padStart(2, '0');
  return `#${r}${g}${b}`;
}

// -------------------------------------------------------------
// 7. In-Browser OpenUSD (.usda) ASCII Serializer & Exporter
// -------------------------------------------------------------
function exportCurrentStageToUSDA() {
  if (!stageData) return;

  let usda = `#usda 1.0\n(\n    metersPerUnit = ${stageData.metadata.metersPerUnit || 0.01}\n    upAxis = "${stageData.metadata.upAxis || 'Y'}"\n)\n\n`;

  // Materials Definition
  usda += `def Xform "Materials"\n{\n`;
  for (const [path, mat] of Object.entries(stageData.materials)) {
    const matName = mat.name;
    const diff = mat.diffuseColor;
    const emis = mat.emissiveColor;
    usda += `    def Material "${matName}"\n    {\n`;
    usda += `        token outputs:surface.connect = <${path}/PBRShader.outputs:surface>\n\n`;
    usda += `        def Shader "PBRShader"\n        {\n`;
    usda += `            uniform token info:id = "UsdPreviewSurface"\n`;
    usda += `            color3f inputs:diffuseColor = (${diff[0].toFixed(3)}, ${diff[1].toFixed(3)}, ${diff[2].toFixed(3)})\n`;
    usda += `            color3f inputs:emissiveColor = (${emis[0].toFixed(3)}, ${emis[1].toFixed(3)}, ${emis[2].toFixed(3)})\n`;
    usda += `            float inputs:roughness = ${mat.roughness.toFixed(3)}\n`;
    usda += `            float inputs:metallic = ${mat.metallic.toFixed(3)}\n`;
    usda += `            float inputs:opacity = ${(mat.opacity || 1.0).toFixed(3)}\n`;
    usda += `            float inputs:ior = ${(mat.ior || 1.5).toFixed(3)}\n`;
    usda += `            token outputs:surface\n`;
    usda += `        }\n    }\n\n`;
  }
  usda += `}\n\n`;

  // Prims Definition
  usda += `def Xform "World"\n{\n`;
  stageData.prims.forEach(prim => {
    const mesh = scenePrims.get(prim.path);
    const pos = mesh ? mesh.position : { x: prim.position[0], y: prim.position[1], z: prim.position[2] };
    const scale = mesh ? mesh.scale : { x: prim.scale[0], y: prim.scale[1], z: prim.scale[2] };
    const cleanName = prim.path.split('/').pop();

    usda += `    def ${prim.type} "${cleanName}" (\n`;
    const schemas = [];
    if (prim.physics && prim.physics.isRigidBody) schemas.push('"PhysicsRigidBodyAPI"');
    if (prim.physics && prim.physics.isCollisionEnabled) schemas.push('"PhysicsCollisionAPI"');
    if (prim.materialPath) schemas.push('"MaterialBindingAPI"');
    if (schemas.length > 0) {
      usda += `        prepend apiSchemas = [${schemas.join(', ')}]\n`;
    }
    usda += `    )\n    {\n`;

    if (prim.materialPath) {
      usda += `        rel material:binding = <${prim.materialPath}>\n`;
    }
    if (prim.physics && prim.physics.isCollisionEnabled) {
      usda += `        bool physics:collisionEnabled = 1\n`;
    }
    if (prim.physics && prim.physics.isRigidBody) {
      usda += `        bool physics:rigidBodyEnabled = 1\n`;
    }

    usda += `        double3 xformOp:translate = (${pos.x.toFixed(2)}, ${pos.y.toFixed(2)}, ${pos.z.toFixed(2)})\n`;
    usda += `        float3 xformOp:scale = (${scale.x.toFixed(2)}, ${scale.y.toFixed(2)}, ${scale.z.toFixed(2)})\n`;
    usda += `        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]\n`;
    usda += `    }\n\n`;
  });
  usda += `}\n`;

  // Download Trigger
  const blob = new Blob([usda], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `exported_${stageData.filename || 'scene.usda'}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// -------------------------------------------------------------
// 8. Synthetic Data (SDG) Visualizer Dashboard
// -------------------------------------------------------------
async function initSdgDashboard() {
  const toggleBtn = document.getElementById("btn-toggle-sdg");
  const closeBtn = document.getElementById("btn-close-sdg");
  const drawer = document.getElementById("sdg-drawer");

  toggleBtn.addEventListener("click", async () => {
    drawer.classList.toggle("hidden");
    if (!drawer.classList.contains("hidden") && !sdgData) {
      await loadSdgDataset();
    }
  });

  closeBtn.addEventListener("click", () => {
    drawer.classList.add("hidden");
  });

  document.getElementById("sdg-toggle-bbox").addEventListener("change", renderCurrentSdgFrame);
  document.getElementById("sdg-toggle-seg").addEventListener("change", renderCurrentSdgFrame);
  
  const opacitySlider = document.getElementById("sdg-seg-opacity");
  opacitySlider.addEventListener("input", (e) => {
    document.getElementById("sdg-opacity-val").textContent = `${e.target.value}%`;
    renderCurrentSdgFrame();
  });
}

async function loadSdgDataset() {
  try {
    let res = await fetch("api/sdg.json").catch(() => null);
    if (!res || !res.ok) {
      res = await fetch("/api/sdg");
    }
    sdgData = await res.json();
    const frameList = document.getElementById("sdg-frame-list");
    frameList.innerHTML = "";

    if (!sdgData.frames || sdgData.frames.length === 0) {
      frameList.innerHTML = `<div class="prop-label" style="padding: 10px;">No SDG frames generated yet.<br>Run replicator/generate_synthetic_dataset_standalone.py</div>`;
      return;
    }

    document.getElementById("sdg-frame-count").textContent = sdgData.frames.length;

    sdgData.frames.forEach((frame, idx) => {
      const item = document.createElement("div");
      item.className = `sdg-frame-item ${idx === 0 ? 'active' : ''}`;
      item.innerHTML = `
        <img class="sdg-thumb" src="sdg_media/${frame.rgbImage}" alt="Frame ${idx}" />
        <div class="sdg-frame-info">
          <span class="sdg-frame-name">Frame #${frame.frameIndex.toString().padStart(4, '0')}</span>
          <span class="sdg-frame-count">${frame.objectsCount} Objects Annotated</span>
        </div>
      `;
      item.addEventListener("click", () => {
        document.querySelectorAll(".sdg-frame-item").forEach(el => el.classList.remove("active"));
        item.classList.add("active");
        currentSdgFrameIdx = idx;
        renderCurrentSdgFrame();
      });
      frameList.appendChild(item);
    });

    currentSdgFrameIdx = 0;
    renderCurrentSdgFrame();
  } catch (err) {
    console.error("Failed to load SDG dataset:", err);
  }
}

async function loadImage(url) {
  if (cachedImages.has(url)) return cachedImages.get(url);
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      cachedImages.set(url, img);
      resolve(img);
    };
    img.onerror = reject;
    img.src = url;
  });
}

async function renderCurrentSdgFrame() {
  if (!sdgData || !sdgData.frames || sdgData.frames.length === 0) return;

  const frame = sdgData.frames[currentSdgFrameIdx];
  const canvas = document.getElementById("sdg-canvas");
  const ctx = canvas.getContext("2d");

  const showBbox = document.getElementById("sdg-toggle-bbox").checked;
  const showSeg = document.getElementById("sdg-toggle-seg").checked;
  const segOpacity = parseFloat(document.getElementById("sdg-seg-opacity").value) / 100.0;

  // Load RGB & Seg images
  const rgbImg = await loadImage(`sdg_media/${frame.rgbImage}`);
  const segImg = await loadImage(`sdg_media/${frame.segmentationMask}`);

  canvas.width = rgbImg.width;
  canvas.height = rgbImg.height;

  // 1. Draw RGB Base Frame
  ctx.drawImage(rgbImg, 0, 0);

  // 2. Draw Semantic Segmentation Overlay
  if (showSeg && segImg) {
    ctx.save();
    ctx.globalAlpha = segOpacity;
    ctx.drawImage(segImg, 0, 0);
    ctx.restore();
  }

  // 3. Draw 2D Bounding Boxes & Tags
  if (showBbox && frame.annotations) {
    ctx.lineWidth = 2;
    ctx.font = "bold 12px JetBrains Mono, monospace";

    frame.annotations.forEach(ann => {
      const box = ann.box2d;
      const cls = ann.class;
      const color = cls === "cube" ? "#f87171" : (cls === "sphere" ? "#4ade80" : "#38bdf8");

      ctx.strokeStyle = color;
      ctx.strokeRect(box[0], box[1], box[2] - box[0], box[3] - box[1]);

      // Tag Background
      ctx.fillStyle = "rgba(0,0,0,0.75)";
      ctx.fillRect(box[0], box[1] - 18, 90, 16);

      // Label Text
      ctx.fillStyle = color;
      ctx.fillText(`${cls} #${ann.objectId}`, box[0] + 4, box[1] - 5);
    });
  }

  // Update Meta Info & JSON view
  document.getElementById("sdg-frame-meta").textContent = `Resolution: ${frame.resolution[0]}x${frame.resolution[1]} | Objects: ${frame.objectsCount} | Frame File: ${frame.rgbImage}`;
  document.getElementById("sdg-json-view").textContent = JSON.stringify(frame, null, 2);
}

// -------------------------------------------------------------
// 9. Raycasting, UI Controls & Animation Loop
// -------------------------------------------------------------
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

function onPointerDown(e) {
  if (e.button !== 0) return;
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

function initEventListeners() {
  document.getElementById("webgl-canvas").addEventListener("pointerdown", onPointerDown);

  document.getElementById("stage-select").addEventListener("change", (e) => {
    if (e.target.value) loadStage(e.target.value);
  });

  document.getElementById("camera-select").addEventListener("change", (e) => {
    switchCamera(e.target.value);
  });

  document.getElementById("render-mode").addEventListener("change", (e) => {
    applyShadingMode(e.target.value);
  });

  const gridBtn = document.getElementById("btn-grid-toggle");
  gridBtn.addEventListener("click", () => {
    gridHelper.visible = !gridHelper.visible;
    axesHelper.visible = gridHelper.visible;
    gridBtn.classList.toggle("active", gridHelper.visible);
  });

  document.getElementById("btn-reset-cam").addEventListener("click", frameScene);
  document.getElementById("btn-export-usda").addEventListener("click", exportCurrentStageToUSDA);

  document.getElementById("outliner-search").addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase();
    document.querySelectorAll(".tree-node-wrapper").forEach(el => {
      const text = el.textContent.toLowerCase();
      el.style.display = text.includes(query) ? "block" : "none";
    });
  });

  document.getElementById("btn-expand-all").addEventListener("click", () => {
    document.querySelectorAll(".tree-children").forEach(c => c.style.display = "block");
  });
  document.getElementById("btn-collapse-all").addEventListener("click", () => {
    document.querySelectorAll(".tree-children").forEach(c => c.style.display = "none");
  });

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

function animate() {
  requestAnimationFrame(animate);

  if (isSimulating && physicsWorld) {
    physicsWorld.step(physicsTimeStep);

    physicsBodies.forEach((body, path) => {
      const mesh = scenePrims.get(path);
      if (mesh && body.mass > 0) {
        mesh.position.set(body.position.x, body.position.y, body.position.z);
        mesh.quaternion.set(body.quaternion.x, body.quaternion.y, body.quaternion.z, body.quaternion.w);
      }
    });

    if (selectedPrimPath) updateHighlightBox(selectedPrimPath);
  }

  controls.update();
  renderer.render(scene, camera);

  frameCount++;
  const now = performance.now();
  if (now - lastFpsTime >= 1000) {
    fps = Math.round((frameCount * 1000) / (now - lastFpsTime));
    document.getElementById("badge-fps").textContent = `${fps} FPS`;
    frameCount = 0;
    lastFpsTime = now;
  }
}
