# 🌌 Omniverse OpenUSD Starter & 3D Web Studio

[![CI / USD Validation & Unit Tests](https://github.com/iliachry/omniverse-improv/actions/workflows/ci.yml/badge.svg)](https://github.com/iliachry/omniverse-improv/actions/workflows/ci.yml)
[![Deploy 3D Studio to GitHub Pages](https://github.com/iliachry/omniverse-improv/actions/workflows/deploy-pages.yml/badge.svg)](https://github.com/iliachry/omniverse-improv/actions/workflows/deploy-pages.yml)
[![OpenUSD](https://img.shields.io/badge/OpenUSD-24.08+-00599C?logo=nvidia&logoColor=white)](https://openusd.org/)
[![NVIDIA PhysX 5](https://img.shields.io/badge/Physics-PhysX_5-76B900?logo=nvidia&logoColor=white)](https://developer.nvidia.com/physx-sdk)
[![Three.js](https://img.shields.io/badge/WebGL-Three.js_r128-black?logo=three.js)](https://threejs.org/)
[![Python 3.10 | 3.11 | 3.12](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A modern, end-to-end open-source toolkit and starter template for **NVIDIA Omniverse Kit**, **OpenUSD**, **Isaac Sim Robotics**, and **Synthetic Data Generation (SDG)**. Includes a standalone in-browser **WebGL 3D Studio**, **Live PBR Shader Editor**, **PhysX Simulation Engine**, and **Apple USDZ / AR QuickLook Exporter**.

---

## 🌟 Architecture & Features Overview

```mermaid
graph TD
    A[Omniverse OpenUSD Starter] --> B[🖥️ In-Browser WebGL 3D Studio]
    A --> C[🚀 Native Omniverse Kit Extension]
    A --> D[🦾 Isaac Sim 6-DOF Robotics]
    A --> E[👁️ Replicator Synthetic Data SDG]
    A --> F[📦 Standalone USD & USDZ Tools]

    B --> B1[USD Stage Parser & Outliner]
    B --> B2[Live PBR Shader Editor & Color Pickers]
    B --> B3[In-Browser PhysX Dynamic Simulator]
    B --> B4[Export Modified .usda directly from Web]

    C --> C1[omni.ui Custom Dark-Mode Window]
    C --> C2[One-Click Studio Lighting & Ground Colliders]
    C --> C3[Procedural Kinetic Domino & Tower Spawners]
    C --> C4[Real-time Gravity Tweaker]

    D --> D1[6-DOF Industrial Manipulator Kuka/UR style]
    D --> D2[2-Finger Parallel Jaw Gripper]
    D --> D3[UsdPhysics.DriveAPI Joint Controllers]

    E --> E1[Multi-modal Domain Randomization]
    E --> E2[RGB + Depth + 2D/3D BBoxes + Semantic Masks]
    E --> E3[Interactive SDG Annotation Visualizer Web Dashboard]

    F --> F1[Apple USDZ AR QuickLook Packager]
    F --> F2[Automated Pytest Suite 9/9 Passing]
```

---

## 🚀 Key Highlights

### 1. 🌐 Interactive WebGL 3D Studio (`usd_viewer/`)
* **Zero-Install USD Preview**: Converts OpenUSD stages (`.usda`, `.usd`, `.usdc`) into Three.js scene graphs with real-time PBR shaders (diffuse, metallic, roughness, emissive glow, clearcoat, opacity).
* **Live PBR Material Editor**: Live color pickers and roughness/metallic sliders in the browser.
* **💾 In-Browser USDA Exporter**: Modify shader parameters or transforms in 3D and export the updated `.usda` stage file with a single click.
* **⚡ In-Browser PhysX Simulation**: Live rigid-body dynamics (Cannon.js integration) with gravity presets (Earth, Moon, Jupiter, Zero-G) and kinetic kick triggers.

### 2. 🦾 6-DOF Industrial Robotics & Articulations (`robotics/`)
* **6-DOF Kinematic Chain**: Waist yaw ($\pm 180^\circ$), Shoulder pitch ($-60^\circ \to +90^\circ$), Elbow pitch ($-120^\circ \to +120^\circ$), Wrist roll, Wrist pitch, Tool flange yaw.
* **Parallel Jaw Gripper**: Linear prismatic joint drives for open/close gripping actions.
* **Dual Runtime**: Authors standards-compliant `UsdPhysics.ArticulationRootAPI` and `DriveAPI` for both offline USD pipelines and native **Isaac Sim** control loops.

### 3. 👁️ Replicator Synthetic Data (SDG) Visualizer (`replicator/`)
* **Multi-Modal Captures**: RGB images, 2D tight bounding boxes, 3D oriented bounding boxes, and pixel-wise semantic segmentation masks.
* **Interactive Dashboard**: Inspect captured frames side-by-side with toggleable bounding box tags, semantic segmentation mask alpha slider, and ground-truth JSON metadata.

### 4. 🍏 Apple USDZ & AR QuickLook Exporter (`usd_generators/export_usdz.py`)
* Packages `.usda` scenes into standalone Apple-compatible `.usdz` archives for instant preview on iPhones, iPads, and macOS.

### 5. 🛠️ Official Omniverse Kit Extension (`exts/omni.improv.starter/`)
* Modern dockable `omni.ui` studio extension for NVIDIA Kit 110+ with live hot-reloading, stage builders, and physics tweakers.

---

## ⚡ Quickstart Guide

### 1. In-Browser 3D Studio & SDG Dashboard
```bash
# 1. Clone the repository
git clone https://github.com/iliachry/omniverse-improv.git
cd omniverse-improv

# 2. Install lightweight dependencies
pip install -r requirements.txt

# 3. Launch the WebGL 3D Studio & SDG Dashboard
python usd_viewer/server.py
```
Open **`http://localhost:8088`** in any web browser!

---

### 2. Standalone OpenUSD Scene Generators
Generate high-fidelity `.usda` stages without needing Omniverse Kit or a GPU:
```bash
# Generate 6-DOF Industrial Robot Arm + Parallel Gripper
python usd_generators/generate_robotics_arm.py

# Generate Kinetic Domino Run & Physics Playground
python usd_generators/generate_physics_playground.py

# Generate Procedural Sci-Fi Colonnade & Gem Dais
python usd_generators/generate_procedural_scene.py

# Generate Destructible Jenga Block Tower
python usd_generators/generate_block_tower.py

# Generate Standalone Synthetic Computer Vision Dataset
python replicator/generate_synthetic_dataset_standalone.py
```

---

### 3. Apple USDZ AR Export
```bash
python usd_generators/export_usdz.py --input usd_generators/output_physics_playground.usda
```

---

### 4. Launching Native NVIDIA Omniverse Kit Studio (RTX)
For systems with an NVIDIA RTX GPU, run the native desktop editor:
```powershell
.\launch_omniverse_editor.bat
```
Or open a specific stage directly:
```powershell
.\launch_omniverse_usd.bat usd_generators\output_robotics_arm.usda
```

---

## 🧪 Automated Testing

The codebase includes an automated unit test suite with 100% passing tests:

```bash
pytest tests/ -v
```

```text
tests/test_extension_core.py::test_setup_studio_environment PASSED       [ 11%]
tests/test_extension_core.py::test_spawn_block_tower PASSED              [ 22%]
tests/test_extension_core.py::test_spawn_primitive_and_materials PASSED  [ 33%]
tests/test_extension_core.py::test_physics_helper_gravity_tweaker PASSED [ 44%]
tests/test_robotics_and_sdg.py::test_6dof_robotics_articulation_setup PASSED [ 55%]
tests/test_robotics_and_sdg.py::test_usdz_packaging PASSED               [ 66%]
tests/test_usd_generators.py::test_physics_playground_generation PASSED  [ 77%]
tests/test_usd_generators.py::test_procedural_scene_generation PASSED    [ 88%]
tests/test_usd_generators.py::test_usd_parser_serialization PASSED       [100%]
============================== 9 passed in 0.47s ==============================
```

---

## 📁 Project Structure

```text
omniverse-improv/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Automated cross-platform pytest & USD validation
│       └── deploy-pages.yml          # Automated GitHub Pages web demo build
├── apps/
│   └── omni.improv.editor.kit        # Native Omniverse Kit application definition
├── exts/
│   └── omni.improv.starter/          # Official Omniverse Kit Extension
│       ├── config/extension.toml     # Manifest & dependencies
│       └── omni/improv/starter/
│           ├── extension.py          # omni.ext lifecycle hooks
│           ├── ui/main_window.py     # Dockable omni.ui window
│           └── core/stage_builder.py # Stage spawner & PBR material library
├── usd_generators/                   # Standalone OpenUSD Scene Builders
│   ├── generate_robotics_arm.py      # 6-DOF Industrial Robot Arm + Gripper
│   ├── generate_physics_playground.py# Domino chain reaction & ramps
│   ├── generate_procedural_scene.py  # Sci-Fi platform with emissive shaders
│   ├── generate_block_tower.py       # Jenga-style destructible block tower
│   └── export_usdz.py                # Apple USDZ / AR QuickLook packager
├── usd_viewer/                       # In-Browser WebGL 3D Studio & Simulator
│   ├── server.py                     # API server for stages & SDG datasets
│   ├── usd_parser.py                 # OpenUSD stage to JSON parser
│   ├── export_static_demo.py         # Static bundle builder for GitHub Pages
│   └── static/
│       ├── index.html                # 3D Studio & SDG visualizer UI
│       ├── style.css                 # Dark-mode NVIDIA aesthetic theme
│       └── viewer.js                 # Three.js PBR viewer & Cannon.js PhysX engine
├── replicator/                       # Synthetic Data Generation (SDG)
│   ├── generate_synthetic_dataset_standalone.py # Offline multi-modal SDG generator
│   └── synthetic_data_pipeline.py    # Omniverse Replicator domain randomization
├── robotics/
│   └── isaac_sim_sandbox.py          # 6-DOF Articulation & Revolute/Prismatic Drives
├── tests/                            # Automated Pytest Suite
└── docs/                             # Static WebGL 3D Studio build for GitHub Pages
```

---

## 🤝 Contributing

Contributions, feature suggestions, and pull requests are welcome!
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feat/AmazingFeature`).
3. Commit your Changes (`git commit -m 'feat: Add AmazingFeature'`).
4. Ensure all tests pass (`pytest tests/`).
5. Push to the Branch (`git push origin feat/AmazingFeature`).
6. Open a Pull Request.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
