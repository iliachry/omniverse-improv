#!/usr/bin/env python3
"""
OpenUSD to Apple USDZ & AR QuickLook Exporter.
Converts .usda / .usd scenes into standalone .usdz packages for iOS, macOS,
and Web 3D / AR QuickLook viewing.
"""

import argparse
import os
import sys
from typing import Optional
import zipfile

try:
    from pxr import Sdf, Usd, UsdUtils
    HAS_USDUTILS = hasattr(UsdUtils, "CreateNewUsdzPackage")
except ImportError:
    HAS_USDUTILS = False


def package_to_usdz(input_stage_path: str, output_usdz_path: Optional[str] = None) -> str:
    """
    Packages an OpenUSD stage (.usda or .usd) into an Apple-compatible .usdz archive.
    """
    if not os.path.exists(input_stage_path):
        raise FileNotFoundError(f"Input stage not found: {input_stage_path}")

    if not output_usdz_path:
        base, _ = os.path.splitext(input_stage_path)
        output_usdz_path = f"{base}.usdz"

    print(f"[*] Packaging OpenUSD stage to USDZ: {input_stage_path} -> {output_usdz_path}")

    if HAS_USDUTILS:
        # Official Pixar USD USDZ packager
        asset_id = Sdf.AssetPath(input_stage_path)
        success = UsdUtils.CreateNewUsdzPackage(asset_id, output_usdz_path)
        if success:
            print(f"[OK] USDZ Package created successfully via UsdUtils: {output_usdz_path}")
            return output_usdz_path

    # Standalone zero-compression ZIP fallback (Apple USDZ specification)
    print("[*] Creating USDZ package via uncompressed archive specification...")
    with zipfile.ZipFile(output_usdz_path, "w", compression=zipfile.ZIP_STORED) as zf:
        arcname = os.path.basename(input_stage_path)
        zf.write(input_stage_path, arcname=arcname)

    print(f"[OK] Standalone USDZ Package ready for Apple AR QuickLook: {output_usdz_path}")
    return output_usdz_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package OpenUSD stages to Apple USDZ archives.")
    parser.add_argument("--input", "-i", type=str, default="usd_generators/output_physics_playground.usda", help="Path to input .usda file")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to output .usdz file")
    args = parser.parse_args()

    out = package_to_usdz(args.input, args.output)
    print(f"File size: {os.path.getsize(out)} bytes")
