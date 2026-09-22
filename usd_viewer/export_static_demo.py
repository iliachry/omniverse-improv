#!/usr/bin/env python3
"""
Static Demo Builder for GitHub Pages & Web Distribution.
Parses all OpenUSD stages in the workspace and exports a zero-dependency static
distribution into the docs/ directory for instant GitHub Pages hosting.
"""

import json
import os
import shutil
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from usd_parser import parse_usd_stage
from server import find_usd_files

DOCS_DIR = os.path.join(WORKSPACE_DIR, "docs")
STATIC_SRC = os.path.join(CURRENT_DIR, "static")
SDG_SRC = os.path.join(WORKSPACE_DIR, "replicator", "_sdg_output")


def build_static_demo():
    print(f"[*] Building static GitHub Pages web demo at: {DOCS_DIR}")

    if os.path.exists(DOCS_DIR):
        shutil.rmtree(DOCS_DIR)
    os.makedirs(DOCS_DIR, exist_ok=True)

    # 1. Copy static web assets directly (clean, uncorrupted)
    for item in sorted(os.listdir(STATIC_SRC)):
        s = os.path.join(STATIC_SRC, item)
        d = os.path.join(DOCS_DIR, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    # 2. Find and pre-parse all USD stages
    api_dir = os.path.join(DOCS_DIR, "api")
    os.makedirs(api_dir, exist_ok=True)

    usd_files = sorted(find_usd_files(WORKSPACE_DIR), key=lambda x: x["relPath"])
    # Sanitize for static distribution (portable relative paths)
    sanitized_usd_files = []
    for stg in usd_files:
        sanitized_usd_files.append({
            "name": stg["name"],
            "relPath": stg["relPath"],
            "fullPath": stg["relPath"],
            "size": stg["size"]
        })

    with open(os.path.join(api_dir, "stages.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(sanitized_usd_files, f, indent=2)

    stage_cache = {}
    for stg in usd_files:
        full_path = stg["fullPath"]
        rel_path = stg["relPath"]
        try:
            print(f"    - Pre-parsing {stg['name']}...")
            parsed = parse_usd_stage(full_path)
            parsed["stagePath"] = rel_path
            stage_cache[rel_path] = parsed
        except Exception as e:
            print(f"[!] Warning: failed to parse {rel_path}: {e}")

    with open(os.path.join(api_dir, "stage_data.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(stage_cache, f, indent=2)

    # 3. Copy SDG Media & Annotations
    if os.path.exists(SDG_SRC):
        sdg_dest = os.path.join(DOCS_DIR, "sdg_media")
        os.makedirs(sdg_dest, exist_ok=True)
        for item in sorted(os.listdir(SDG_SRC)):
            s = os.path.join(SDG_SRC, item)
            d = os.path.join(sdg_dest, item)
            if not os.path.isdir(s):
                shutil.copy2(s, d)

        # Copy annotations to api/sdg.json
        ann_src = os.path.join(SDG_SRC, "dataset_annotations.json")
        if os.path.exists(ann_src):
            with open(ann_src, "r", encoding="utf-8") as f_in:
                sdg_data = json.load(f_in)
            with open(os.path.join(api_dir, "sdg.json"), "w", encoding="utf-8", newline="\n") as f_out:
                json.dump(sdg_data, f_out, indent=2)

    print(f"[OK] Static GitHub Pages build complete in: {DOCS_DIR}")


if __name__ == "__main__":
    build_static_demo()
