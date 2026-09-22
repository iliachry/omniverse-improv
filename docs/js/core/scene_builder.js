/**
 * Three.js WebGL 3D Scene Builder & PBR Pipeline.
 */

import { appState } from "../state.js";

export function initThree() {
  const container = document.getElementById("canvas-container");
  const canvas = document.getElementById("webgl-canvas");
  if (!container || !canvas) return;

  appState.scene = new THREE.Scene();
  appState.scene.background = new THREE.Color(0x0f172a); // Deep slate dark mode

  const aspect = container.clientWidth / container.clientHeight;
  appState.camera = new THREE.PerspectiveCamera(45, aspect, 1, 50000);
  appState.camera.position.set(600, 500, 800);

  appState.renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: true,
    powerPreference: "high-performance"
  });
  appState.renderer.setSize(container.clientWidth, container.clientHeight);
  appState.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  appState.renderer.shadowMap.enabled = true;
  appState.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  appState.renderer.toneMapping = THREE.ACESFilmicToneMapping;
  appState.renderer.toneMappingExposure = 1.0;

  appState.controls = new THREE.OrbitControls(appState.camera, appState.renderer.domElement);
  appState.controls.enableDamping = true;
  appState.controls.dampingFactor = 0.05;
  appState.controls.screenSpacePanning = true;
  appState.controls.maxPolarAngle = Math.PI / 2 + 0.05;

  appState.gridHelper = new THREE.GridHelper(4000, 80, 0x38bdf8, 0x1e293b);
  appState.gridHelper.position.y = -0.1;
  appState.scene.add(appState.gridHelper);

  appState.axesHelper = new THREE.AxesHelper(150);
  appState.scene.add(appState.axesHelper);

  window.addEventListener("resize", onWindowResize);
}

export function onWindowResize() {
  const container = document.getElementById("canvas-container");
  if (!container || !appState.renderer || !appState.camera) return;

  appState.camera.aspect = container.clientWidth / container.clientHeight;
  appState.camera.updateProjectionMatrix();
  appState.renderer.setSize(container.clientWidth, container.clientHeight);
}

export function buildScene(data) {
  if (!appState.scene) return;

  // Clear existing prim meshes
  appState.scenePrims.forEach(mesh => appState.scene.remove(mesh));
  appState.scenePrims.clear();
  appState.materialsMap.clear();

  // Clear previous lights
  const toRemove = [];
  appState.scene.traverse(obj => {
    if (obj.isLight && obj !== appState.gridHelper && obj !== appState.axesHelper) {
      toRemove.push(obj);
    }
  });
  toRemove.forEach(obj => appState.scene.remove(obj));

  // Build PBR Materials Map
  if (data.materials) {
    Object.entries(data.materials).forEach(([path, matData]) => {
      appState.materialsMap.set(path, createThreeMaterial(matData));
    });
  }

  // Setup Default Ambient & Sun Light
  const ambient = new THREE.AmbientLight(0xffffff, 0.4);
  appState.scene.add(ambient);

  const dirSun = new THREE.DirectionalLight(0xfffaed, 1.6);
  dirSun.position.set(800, 1400, 600);
  dirSun.castShadow = true;
  dirSun.shadow.mapSize.width = 2048;
  dirSun.shadow.mapSize.height = 2048;
  dirSun.shadow.camera.near = 10;
  dirSun.shadow.camera.far = 6000;
  const d = 1600;
  dirSun.shadow.camera.left = -d;
  dirSun.shadow.camera.right = d;
  dirSun.shadow.camera.top = d;
  dirSun.shadow.camera.bottom = -d;
  dirSun.shadow.bias = -0.0005;
  appState.scene.add(dirSun);
  appState.dirSunLight = dirSun;

  // Build Prims
  if (data.prims && data.prims.length > 0) {
    data.prims.forEach(prim => {
      const mesh = createMeshForPrim(prim, appState.materialsMap);
      if (mesh) {
        mesh.userData = { ...prim, _baseMaterial: mesh.material.clone() };
        appState.scenePrims.set(prim.path, mesh);
        appState.scene.add(mesh);

        // Store initial transform for physics reset
        appState.initialTransforms.set(prim.path, {
          pos: mesh.position.clone(),
          quat: mesh.quaternion.clone()
        });
      }
    });
  }

  frameScene();
}

export function createThreeMaterial(matData) {
  const params = {
    color: new THREE.Color(matData.diffuseColor[0], matData.diffuseColor[1], matData.diffuseColor[2]),
    roughness: matData.roughness !== undefined ? matData.roughness : 0.5,
    metalness: matData.metallic !== undefined ? matData.metallic : 0.0,
  };

  if (matData.emissiveColor && (matData.emissiveColor[0] > 0 || matData.emissiveColor[1] > 0 || matData.emissiveColor[2] > 0)) {
    params.emissive = new THREE.Color(matData.emissiveColor[0], matData.emissiveColor[1], matData.emissiveColor[2]);
    params.emissiveIntensity = 1.0;
  }

  if (matData.opacity !== undefined && matData.opacity < 0.99) {
    params.transparent = true;
    params.opacity = matData.opacity;
    params.transmission = 1.0 - matData.opacity;
    params.ior = matData.ior || 1.5;
  }

  return new THREE.MeshPhysicalMaterial(params);
}

export function createMeshForPrim(prim, matsMap) {
  let geometry;
  const props = prim.geomProps || {};
  const scale = prim.scale || [1, 1, 1];

  switch (prim.type) {
    case "Cube":
      const size = props.size || 100.0;
      geometry = new THREE.BoxGeometry(size * scale[0], size * scale[1], size * scale[2]);
      break;

    case "Cylinder":
      const radius = props.radius || 50.0;
      const height = props.height || 200.0;
      geometry = new THREE.CylinderGeometry(radius * scale[0], radius * scale[0], height * scale[1], 32);
      break;

    case "Sphere":
      const r = props.radius || 50.0;
      geometry = new THREE.SphereGeometry(r * scale[0], 32, 32);
      break;

    case "Plane":
      const w = props.width || 2000.0;
      const l = props.length || 2000.0;
      geometry = new THREE.PlaneGeometry(w * scale[0], l * scale[2]);
      geometry.rotateX(-Math.PI / 2);
      break;

    case "Capsule":
      const cr = props.radius || 20.0;
      const ch = props.height || 60.0;
      geometry = new THREE.CapsuleGeometry(cr * scale[0], ch * scale[1], 16, 32);
      break;

    default:
      geometry = new THREE.BoxGeometry(80, 80, 80);
      break;
  }

  // Material selection
  let material = matsMap.get(prim.materialPath);
  if (!material) {
    material = new THREE.MeshPhysicalMaterial({
      color: 0x94a3b8,
      roughness: 0.6,
      metalness: 0.1
    });
  }

  // Clone material per mesh to prevent cross-prim property mutation
  const meshMat = material.clone();
  const mesh = new THREE.Mesh(geometry, meshMat);
  mesh.userData = { ...prim, _baseMaterial: meshMat.clone() };

  if (prim.position && prim.position.length === 3) {
    mesh.position.set(prim.position[0], prim.position[1], prim.position[2]);
  }
  if (prim.rotation && prim.rotation.length === 3) {
    mesh.rotation.set(
      THREE.MathUtils.degToRad(prim.rotation[0]),
      THREE.MathUtils.degToRad(prim.rotation[1]),
      THREE.MathUtils.degToRad(prim.rotation[2])
    );
  }

  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

export function frameScene() {
  if (appState.scenePrims.size === 0 || !appState.camera || !appState.controls) return;

  const box = new THREE.Box3();
  appState.scenePrims.forEach(mesh => {
    if (mesh.visible) box.expandByObject(mesh);
  });

  if (box.isEmpty()) return;

  const center = new THREE.Vector3();
  box.getCenter(center);
  const size = new THREE.Vector3();
  box.getSize(size);

  const maxDim = Math.max(size.x, size.y, size.z);
  const fov = appState.camera.fov * (Math.PI / 180);
  let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2)) * 1.5;
  cameraZ = Math.max(cameraZ, 200);

  appState.camera.position.set(center.x + cameraZ * 0.7, center.y + cameraZ * 0.5, center.z + cameraZ * 0.7);
  appState.controls.target.copy(center);
  appState.controls.update();
}

export function applyShadingMode(mode) {
  appState.currentShadingMode = mode;
  appState.scenePrims.forEach(mesh => {
    if (mode === "wireframe") {
      mesh.material.wireframe = true;
    } else if (mode === "normal") {
      mesh.material.wireframe = false;
      mesh.material = new THREE.MeshNormalMaterial();
    } else {
      // PBR mode
      mesh.material.wireframe = false;
      if (mesh.userData._baseMaterial) {
        mesh.material = mesh.userData._baseMaterial.clone();
      }
    }
  });
}
