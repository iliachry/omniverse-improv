/**
 * CesiumJS Live 3D Planetary Earth Globe Engine.
 * Provides keyless WGS84 georeferenced BIM facility rendering,
 * coordinate transformations, and synchronized 4D phasing playback.
 */

import { appState } from "../state.js";
import { selectPrim } from "../core/inspector.js";
import { applyBimFilters } from "../bim/bim_manager.js";

export function initCesiumViewer() {
  if (appState.cesiumViewer || typeof Cesium === "undefined") return;

  // Keyless open configuration
  Cesium.Ion.defaultAccessToken = "";

  try {
    appState.cesiumViewer = new Cesium.Viewer("cesium-container", {
      baseLayer: new Cesium.ImageryLayer(
        new Cesium.OpenStreetMapImageryProvider({
          url: "https://tile.openstreetmap.org/"
        })
      ),
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      infoBox: true,
      selectionIndicator: true,
      timeline: false,
      animation: false,
      navigationHelpButton: false,
      sceneModePicker: false
    });

    // Prim selection in Cesium
    appState.cesiumViewer.screenSpaceEventHandler.setInputAction((movement) => {
      const picked = appState.cesiumViewer.scene.pick(movement.position);
      if (Cesium.defined(picked) && picked.id && picked.id._bimPath) {
        selectPrim(picked.id._bimPath);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  } catch (err) {
    console.error("CesiumJS initialization error:", err);
  }
}

export function switchViewMode(mode) {
  const isCesium = (mode === "cesium");
  appState.isCesiumMode = isCesium;

  const btnThree = document.getElementById("btn-mode-three");
  const btnCesium = document.getElementById("btn-mode-cesium");
  const btnFly = document.getElementById("btn-cesium-flyto");
  const canvas = document.getElementById("webgl-canvas");
  const cesiumContainer = document.getElementById("cesium-container");

  if (btnThree) btnThree.classList.toggle("active", !isCesium);
  if (btnCesium) btnCesium.classList.toggle("active", isCesium);
  if (btnFly) btnFly.classList.toggle("hidden", !isCesium);

  if (isCesium) {
    if (canvas) canvas.style.display = "none";
    if (cesiumContainer) cesiumContainer.classList.remove("hidden");
    initCesiumViewer();
    populateCesiumBimFacility();
    flyCesiumToSite();
    applyBimFilters();
  } else {
    if (canvas) canvas.style.display = "block";
    if (cesiumContainer) cesiumContainer.classList.add("hidden");
    applyBimFilters();
  }
}

export function populateCesiumBimFacility() {
  if (!appState.cesiumViewer || typeof Cesium === "undefined" || !appState.stageData) return;

  appState.cesiumFacilityEntities.forEach(ent => appState.cesiumViewer.entities.remove(ent));
  appState.cesiumFacilityEntities = [];

  const lat = appState.stageData.cesium?.latitude || 37.9753;
  const lon = appState.stageData.cesium?.longitude || 23.7361;
  const alt = appState.stageData.cesium?.height || 120.0;
  const mpu = appState.stageData.metadata?.metersPerUnit || 0.01;

  const centerCartesian = Cesium.Cartesian3.fromDegrees(lon, lat, alt);
  const enuToFixed = Cesium.Transforms.eastNorthUpToFixedFrame(centerCartesian);

  // Pin badge
  const pin = appState.cesiumViewer.entities.add({
    name: "Smart Tech Campus Facility",
    position: Cesium.Cartesian3.fromDegrees(lon, lat, alt + 26.0),
    label: {
      text: `🏛️ BIM Smart Tech Campus\n(${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E)`,
      font: "bold 13px Inter, sans-serif",
      fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 3,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      pixelOffset: new Cesium.Cartesian2(0, -25),
      distanceDisplayCondition: new Cesium.DistanceDisplayCondition(80.0, 100000.0)
    }
  });
  appState.cesiumFacilityEntities.push(pin);

  // Granular BIM Prims
  if (appState.stageData.prims && appState.stageData.prims.length > 0) {
    appState.stageData.prims.forEach(prim => {
      if (prim.type === "Plane" || prim.path.includes("ground") || !prim.position) return;

      const px = prim.position[0] * mpu;
      const py = prim.position[1] * mpu; // USD Y is Up
      const pz = prim.position[2] * mpu;

      const localEnu = new Cesium.Cartesian3(px, pz, py);
      const worldPos = Cesium.Matrix4.multiplyByPoint(enuToFixed, localEnu, new Cesium.Cartesian3());
      const enuMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(worldPos);
      const rotMat3 = Cesium.Matrix4.getMatrix3(enuMatrix, new Cesium.Matrix3());
      const orientation = Cesium.Quaternion.fromRotationMatrix(rotMat3);

      const props = prim.geomProps || {};
      const scale = prim.scale || [1, 1, 1];
      const baseSize = (props.size || 1.0) * mpu;

      const dimX = Math.max(0.08, baseSize * scale[0]);
      const dimY = Math.max(0.08, baseSize * scale[2]);
      const dimZ = Math.max(0.08, baseSize * scale[1]);

      let matColor = Cesium.Color.fromCssColorString("#94a3b8");
      const mat = (appState.stageData.materials && prim.materialPath) ? appState.stageData.materials[prim.materialPath] : null;
      if (mat && mat.diffuseColor) {
        const r = mat.diffuseColor[0];
        const g = mat.diffuseColor[1];
        const b = mat.diffuseColor[2];
        const a = (mat.opacity !== undefined && mat.opacity < 0.99) ? mat.opacity : 1.0;
        matColor = new Cesium.Color(r, g, b, a);
      } else if (prim.bim) {
        if (prim.bim.discipline === "Structural") {
          matColor = Cesium.Color.fromCssColorString("#64748b");
        } else if (prim.bim.discipline === "Architectural") {
          if (prim.name.includes("Glass") || prim.path.includes("Curtain")) {
            matColor = Cesium.Color.fromCssColorString("#2074a6").withAlpha(0.40);
          } else {
            matColor = Cesium.Color.fromCssColorString("#cbd5e1");
          }
        } else if (prim.bim.discipline === "MEP") {
          if (prim.name.includes("Solar") || prim.path.includes("Solar")) {
            matColor = Cesium.Color.fromCssColorString("#0a192f");
          } else if (prim.name.includes("Chiller")) {
            matColor = Cesium.Color.fromCssColorString("#525e75");
          } else {
            matColor = Cesium.Color.fromCssColorString("#c2410c");
          }
        }
      }

      if (prim.type === "Cylinder") {
        const cylRadius = ((props.radius || 0.5) * mpu) * scale[0];
        const cylHeight = ((props.height || 2.0) * mpu) * scale[1];
        const isHorizontal = prim.name.includes("Sprinkler") || prim.name.includes("Water") || prim.path.includes("Pipe");
        let cylOrientation = orientation;
        if (isHorizontal) {
          const rotY90 = Cesium.Quaternion.fromAxisAngle(Cesium.Cartesian3.UNIT_Y, Cesium.Math.PI_OVER_TWO);
          cylOrientation = Cesium.Quaternion.multiply(orientation, rotY90, new Cesium.Quaternion());
        }

        const ent = appState.cesiumViewer.entities.add({
          name: prim.name || prim.path,
          position: worldPos,
          orientation: cylOrientation,
          cylinder: {
            length: Math.max(0.1, cylHeight),
            topRadius: Math.max(0.05, cylRadius),
            bottomRadius: Math.max(0.05, cylRadius),
            material: matColor
          }
        });
        ent._bimPath = prim.path;
        ent._prim = prim;
        ent._origMaterial = matColor;
        appState.cesiumFacilityEntities.push(ent);
      } else {
        const ent = appState.cesiumViewer.entities.add({
          name: prim.name || prim.path,
          position: worldPos,
          orientation: orientation,
          box: {
            dimensions: new Cesium.Cartesian3(dimX, dimY, dimZ),
            material: matColor
          }
        });
        ent._bimPath = prim.path;
        ent._prim = prim;
        ent._origMaterial = matColor;
        appState.cesiumFacilityEntities.push(ent);
      }
    });
  }

  applyBimFilters();
}

export function flyCesiumToSite() {
  if (!appState.cesiumViewer || typeof Cesium === "undefined") return;

  const lat = appState.stageData?.cesium?.latitude || 37.9753;
  const lon = appState.stageData?.cesium?.longitude || 23.7361;
  const alt = appState.stageData?.cesium?.height || 120.0;

  appState.cesiumViewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(lon + 0.00038, lat - 0.00055, alt + 32.0),
    orientation: {
      heading: Cesium.Math.toRadians(-28.0),
      pitch: Cesium.Math.toRadians(-22.0),
      roll: 0.0
    },
    duration: 2.5
  });
}
