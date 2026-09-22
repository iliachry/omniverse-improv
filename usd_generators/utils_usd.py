"""OpenUSD Authoring Utilities.
Common helper functions for creating, structuring, and decorating standalone USD stages.
Works with standalone pxr.Usd (from usd-core package or Omniverse Python environment).
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(CURRENT_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from core.openusd.stage_utils import (
    create_stage,
    setup_physics_scene,
    create_pbr_material,
    bind_material,
    add_dome_light,
    add_distant_light,
    add_ground_plane,
)

__all__ = [
    "create_stage",
    "setup_physics_scene",
    "create_pbr_material",
    "bind_material",
    "add_dome_light",
    "add_distant_light",
    "add_ground_plane",
]
