"""BIM Automated Clash Detection Engine
====================================
Performs spatial intersection (AABB / geometric clearance) analysis between
MEP distribution elements and Structural framing systems in OpenUSD BIM stages.
Outputs BCF 3.0 (BIM Collaboration Format) compatible clash issues.
"""

from __future__ import annotations
import os
import sys
import argparse
import json
from typing import Dict, List, Any

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from core.bim.spatial_clash import (
    AABB,
    compute_prim_aabb,
    detect_bim_clashes,
    export_bcf_report,
)


def run_clash_detection_on_stage(stage_path: str) -> Dict[str, Any]:
    """Runs clash detection directly on a USDA/USD stage via usd_parser."""
    from usd_viewer.usd_parser import parse_usd_stage
    parsed = parse_usd_stage(stage_path)
    clashes = detect_bim_clashes(parsed.get("prims", []))
    return {
        "stageFile": os.path.basename(stage_path),
        "totalClashes": len(clashes),
        "criticalCount": sum(1 for c in clashes if c["severity"] == "CRITICAL"),
        "majorCount": sum(1 for c in clashes if c["severity"] == "MAJOR"),
        "warningCount": sum(1 for c in clashes if c["severity"] == "WARNING"),
        "clashes": clashes
    }


def main():
    parser = argparse.ArgumentParser(description="Automated OpenUSD / BIM Clash Detection Solver")
    parser.add_argument("--stage", default=os.path.join(CURRENT_DIR, "output_bim_cesium.usda"), help="Path to USD stage")
    parser.add_argument("--json", action="store_true", help="Output raw JSON report")
    parser.add_argument("--out", default=None, help="Save report to JSON file")
    args = parser.parse_args()

    print(f"[*] Running Automated BIM Clash Detection on: {args.stage}")
    report = run_clash_detection_on_stage(args.stage)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"\n========================================================")
        print(f" [*] BIM CLASH DETECTION REPORT: {report['totalClashes']} INTERFERENCE(S) FOUND")
        print(f"     Critical: {report['criticalCount']} | Major: {report['majorCount']} | Warning: {report['warningCount']}")
        print(f"========================================================")
        for c in report["clashes"]:
            sev = c["severity"]
            badge = "[CRITICAL]" if sev == "CRITICAL" else ("[MAJOR]" if sev == "MAJOR" else "[WARNING]")
            print(f"\n{badge} [{c['id']}] {c['title']} ({sev})")
            print(f"   Storey: {c['storey']} | Penetration Depth: {c['penetrationDepthCm']} cm")
            print(f"   Centroid (X,Y,Z): {c['centroid']}")
            print(f"   Element A: {c['elementA']['name']} ({c['elementA']['discipline']})")
            print(f"   Element B: {c['elementB']['name']} ({c['elementB']['discipline']})")
            print(f"   Mitigation: {c['mitigation']}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\n[OK] Saved BCF Clash Report to: {args.out}")


if __name__ == "__main__":
    main()
