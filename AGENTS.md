# 🤖 AI Agent Engineering Guidelines (`AGENTS.md`)

> **Repository:** [iliachry/omniverse-improv](https://github.com/iliachry/omniverse-improv)  
> **Mission:** Production-grade NVIDIA Omniverse Kit, OpenUSD, Isaac Sim Robotics, WebGL 3D Studio, and Synthetic Data (SDG) starter repository.

---

## 🚨 Cardinal Rule: CI/CD Pipelines Must Never Fail

Before completing any task, submitting code, or pushing commits to `main`, every AI agent **MUST** run and pass the full local validation protocol. **No exceptions.**

---

## ✅ Mandatory Pre-Completion Verification Checklist

Run these commands in order. If any step fails, diagnose and fix the issue before declaring work done:

```powershell
# 1. Run the entire automated unit test suite (must pass 100%)
pytest tests/ -v

# 2. Validate all standalone OpenUSD scene generators
python usd_generators/generate_physics_playground.py
python usd_generators/generate_procedural_scene.py
python usd_generators/generate_robotics_arm.py
python usd_generators/generate_block_tower.py

# 3. Validate the Synthetic Data Generation (SDG) pipeline
python replicator/generate_synthetic_dataset_standalone.py

# 4. Validate Apple USDZ packaging pipeline
python usd_generators/export_usdz.py --input usd_generators/output_physics_playground.usda

# 5. Rebuild the static GitHub Pages bundle and validate JavaScript syntax
python usd_viewer/export_static_demo.py
node -c docs/viewer.js
```

---

## 📐 Architecture & Coding Guidelines

### 1. Robust Import Paths & Cross-Platform Execution
* Standalone scripts in `usd_generators/`, `replicator/`, `robotics/`, and `usd_viewer/` are executed both from the root directory (by CI/CD runners) and directly inside their subfolders.
* **Always** bootstrap `sys.path` defensively at the top of standalone scripts:
  ```python
  import os
  import sys

  CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
  WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
  if CURRENT_DIR not in sys.path:
      sys.path.insert(0, CURRENT_DIR)
  if WORKSPACE_DIR not in sys.path:
      sys.path.insert(0, WORKSPACE_DIR)
  ```

### 2. Relative URLs for Web Assets & Dual-Mode Endpoints
* The WebGL 3D Studio runs both locally (`python usd_viewer/server.py`) and as a static build on GitHub Pages / Custom Domains (`https://iliachry.gr/omniverse-improv/`).
* **Never hardcode absolute web paths** (e.g. `/api/...` or `/sdg_media/...`).
* Use dual-mode relative fetching:
  ```javascript
  let res = await fetch("api/stages.json").catch(() => null);
  if (!res || !res.ok) {
    res = await fetch("/api/stages");
  }
  ```

### 3. Omniverse Kit API Guardrails
* **Window Styling**: In `omni.ui`, assign styles to `self._window.frame.style = STYLE` (not `self._window.style`).
* **Window Flags**: Do not pass unsupported bitflags (e.g. `flags=ui.WINDOW_FLAGS_NO_SCROLLBAR`) to `omni.ui.Window` constructor.
* **Dual Runtimes**: Ensure all core logic in `core/` can run headless with `pxr` alone without requiring `omni.usd` / Kit to be present.

### 4. Git Hygiene & Artifact Safety
* Never commit heavy build directories:
  * `kit-app-template/_build/`, `kit-app-template/_repo/`, `.venv/`, `.pytest_cache/`, `_sdg_output/`
* Keep all test artifacts temporary or cleaned up via `pytest` fixtures (`tmp_path`).

---

## 🧪 CI/CD Matrix Reference

The GitHub Actions workflow runs on every push and PR:
* **Operating Systems:** `ubuntu-latest`, `windows-latest`
* **Python Versions:** `3.10`, `3.11`, `3.12`
* **Checks:**
  1. `pip install -r requirements.txt`
  2. Execution of all generator scripts in `usd_generators/`
  3. Execution of `replicator/generate_synthetic_dataset_standalone.py`
  4. Execution of `pytest tests/ -v`
  5. Deployment of `docs/` to GitHub Pages
