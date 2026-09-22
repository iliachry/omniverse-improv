/**
 * Centralized Application State Store.
 * Holds reactive states for Three.js, Cesium, Physics, BIM Filters, Clashes, and 4D Phasing.
 */

export const appState = {
  // USD Stage Data & Hierarchy
  stageData: null,
  currentStagePath: "",

  // Three.js Scene Engine
  scene: null,
  camera: null,
  renderer: null,
  controls: null,
  scenePrims: new Map(), // path -> THREE.Mesh
  materialsMap: new Map(), // path -> THREE.MeshPhysicalMaterial
  selectedPrimPath: null,
  highlightBox: null,
  gridHelper: null,
  axesHelper: null,
  dirSunLight: null,

  // Performance / Stats
  frameCount: 0,
  lastFpsTime: performance.now(),
  fps: 60,
  currentShadingMode: "pbr",

  // Physics Simulation (Cannon.js)
  physicsWorld: null,
  physicsBodies: new Map(), // path -> CANNON.Body
  initialTransforms: new Map(), // path -> { pos: THREE.Vector3, quat: THREE.Quaternion }
  isSimulating: false,
  physicsTimeStep: 1 / 60,
  gravityMagnitude: 9.81,

  // Synthetic Data (SDG)
  sdgData: null,
  currentSdgFrameIdx: 0,
  cachedImages: new Map(),

  // BIM & Storey Filters
  activeStoreyFilter: "ALL",
  activeDisciplines: {
    Structural: true,
    Architectural: true,
    MEP: true
  },
  isXRayMode: false,
  solarHour: 12.0,

  // CesiumJS 3D Earth Globe
  cesiumViewer: null,
  isCesiumMode: false,
  cesiumFacilityEntities: [],

  // BIM Clash Detection
  isClashMode: false,
  activeClashes: [],
  activeClashFilter: "ALL",
  selectedClashId: null,
  clashWireframeBox: null,
  clashHighlightMeshes: new Map(),

  // 4D Construction Phasing
  is4DMode: false,
  current4DMonth: 12,
  is4DPlaying: false,
  play4DSpeed: 2,
  is4DGhostUnbuilt: false,
  play4DInterval: null,
};

// Bind to window for debugging and inspector hooks
if (typeof window !== "undefined") {
  window.appState = appState;
}
