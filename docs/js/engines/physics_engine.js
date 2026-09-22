/**
 * Cannon.js Rigid-Body Dynamic Simulation Engine.
 */

import { appState } from "../state.js";

export function initPhysics(stageData) {
  if (typeof CANNON === "undefined") return;

  appState.physicsWorld = new CANNON.World();
  appState.physicsWorld.gravity.set(0, -appState.gravityMagnitude * 100, 0); // Scale cm
  appState.physicsWorld.broadphase = new CANNON.NaiveBroadphase();
  appState.physicsWorld.solver.iterations = 10;

  appState.physicsBodies.clear();

  if (!stageData || !stageData.prims) return;

  stageData.prims.forEach(prim => {
    const mesh = appState.scenePrims.get(prim.path);
    if (!mesh) return;

    const phys = prim.physics || {};
    const props = prim.geomProps || {};
    const scale = prim.scale || [1, 1, 1];

    let shape = null;
    switch (prim.type) {
      case "Cube":
        const s = props.size || 100.0;
        shape = new CANNON.Box(new CANNON.Vec3((s * scale[0]) / 2, (s * scale[1]) / 2, (s * scale[2]) / 2));
        break;
      case "Sphere":
        const r = props.radius || 50.0;
        shape = new CANNON.Sphere(r * scale[0]);
        break;
      case "Cylinder":
        const rad = props.radius || 50.0;
        const h = props.height || 200.0;
        shape = new CANNON.Cylinder(rad * scale[0], rad * scale[0], h * scale[1], 16);
        break;
      case "Plane":
        shape = new CANNON.Plane();
        break;
      default:
        break;
    }

    if (!shape) return;

    const mass = phys.isRigidBody ? (phys.mass || 1.0) : 0;
    const body = new CANNON.Body({ mass: mass });
    body.addShape(shape);

    body.position.set(mesh.position.x, mesh.position.y, mesh.position.z);
    body.quaternion.set(mesh.quaternion.x, mesh.quaternion.y, mesh.quaternion.z, mesh.quaternion.w);

    if (prim.type === "Plane") {
      body.quaternion.setFromAxisAngle(new CANNON.Vec3(1, 0, 0), -Math.PI / 2);
    }

    appState.physicsWorld.addBody(body);
    appState.physicsBodies.set(prim.path, body);
  });
}

export function stepPhysics() {
  if (!appState.isSimulating || !appState.physicsWorld) return;

  appState.physicsWorld.step(appState.physicsTimeStep);

  appState.physicsBodies.forEach((body, path) => {
    const mesh = appState.scenePrims.get(path);
    if (mesh && body.mass > 0) {
      mesh.position.copy(body.position);
      mesh.quaternion.copy(body.quaternion);
    }
  });

  if (appState.highlightBox) {
    appState.highlightBox.update();
  }
}

export function resetPhysics() {
  appState.isSimulating = false;
  updatePhysicsPlayButton(false);

  appState.initialTransforms.forEach((trans, path) => {
    const mesh = appState.scenePrims.get(path);
    const body = appState.physicsBodies.get(path);

    if (mesh) {
      mesh.position.copy(trans.pos);
      mesh.quaternion.copy(trans.quat);
    }

    if (body) {
      body.position.copy(trans.pos);
      body.quaternion.copy(trans.quat);
      body.velocity.set(0, 0, 0);
      body.angularVelocity.set(0, 0, 0);
    }
  });

  if (appState.highlightBox) appState.highlightBox.update();
}

export function togglePhysics(forcePlay) {
  if (typeof forcePlay === "boolean") {
    appState.isSimulating = forcePlay;
  } else {
    appState.isSimulating = !appState.isSimulating;
  }

  if (appState.isSimulating && (!appState.physicsWorld || appState.physicsBodies.size === 0)) {
    initPhysics(appState.stageData);
  }

  updatePhysicsPlayButton(appState.isSimulating);
}

export function nudgeTrigger() {
  if (!appState.physicsWorld) initPhysics(appState.stageData);
  appState.isSimulating = true;
  updatePhysicsPlayButton(true);

  // Apply kick impulse to the first dynamic body (e.g. kinetic sphere)
  for (const [path, body] of appState.physicsBodies.entries()) {
    if (body.mass > 0) {
      body.applyImpulse(new CANNON.Vec3(0, 0, -18000), body.position);
      break;
    }
  }
}

function updatePhysicsPlayButton(isPlaying) {
  const btn = document.getElementById("btn-play-physics");
  const text = document.getElementById("play-btn-text");
  if (!btn || !text) return;

  btn.classList.toggle("active", isPlaying);
  text.textContent = isPlaying ? "Pause" : "Simulate";
}
