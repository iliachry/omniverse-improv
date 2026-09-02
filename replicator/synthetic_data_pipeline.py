#!/usr/bin/env python3
"""
Omniverse Replicator: Synthetic Data Generation (SDG) Pipeline.
Demonstrates domain randomization (poses, lights, materials) and multi-modal annotation
(RGB, Depth, 2D/3D Bounding Boxes, Semantic Segmentation) for AI training.

Run inside Omniverse Code/Composer/Isaac Sim via Script Editor or headless kit:
  kit.exe --exec replicator/synthetic_data_pipeline.py
"""

import os
import sys

try:
    import omni.replicator.core as rep
    HAS_REPLICATOR = True
except ImportError:
    rep = None
    HAS_REPLICATOR = False


def setup_synthetic_data_pipeline(
    output_dir: str = "_output_sdg",
    num_frames: int = 20,
    camera_resolution: tuple = (1024, 1024)
):
    """
    Constructs an Omniverse Replicator domain randomization graph and triggers capture.
    
    Args:
        output_dir: Directory where annotated datasets will be stored.
        num_frames: Number of randomized synthetic frames to render.
        camera_resolution: (width, height) for synthetic camera render products.
    """
    if not HAS_REPLICATOR:
        print("[!] Omniverse Replicator (omni.replicator.core) is not detected in current Python environment.")
        print("    This script is designed to run within Omniverse Kit / Isaac Sim runtime.")
        print("    Example: <omniverse_dir>/kit/kit.exe --exec synthetic_data_pipeline.py")
        return

    print(f"[*] Initializing Omniverse Replicator Pipeline -> Output: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    with rep.new_layer():
        # 1. Spawn Multi-Modal Camera
        camera = rep.create.camera(
            position=(0, 150, 250),
            look_at=(0, 20, 0),
            focal_length=35.0
        )
        render_product = rep.create.render_product(camera, camera_resolution)

        # 2. Setup Lighting Rig with Randomizer
        distant_light = rep.create.light(
            light_type="Distant",
            intensity=3000,
            temperature=6500,
            rotation=(-45, 45, 0)
        )
        dome_light = rep.create.light(
            light_type="Dome",
            intensity=500
        )

        # 3. Create Domain Randomization Target Objects
        # Primitive shapes with semantic class annotations
        cubes = rep.create.cube(
            semantics=[("class", "cube")],
            position=(0, 10, 0),
            count=6
        )
        spheres = rep.create.sphere(
            semantics=[("class", "sphere")],
            position=(0, 10, 0),
            count=6
        )
        cylinders = rep.create.cylinder(
            semantics=[("class", "cylinder")],
            position=(0, 10, 0),
            count=4
        )

        # 4. Define Randomization Trigger Graph
        with rep.trigger.on_frame(num_frames=num_frames):
            # Randomize Objects: Position, Rotation, Scale, Color
            with cubes:
                rep.modify.pose(
                    position=rep.distribution.uniform((-80, 5, -80), (80, 40, 80)),
                    rotation=rep.distribution.uniform((0, -180, 0), (0, 180, 0)),
                    scale=rep.distribution.uniform(0.6, 1.4)
                )
                rep.randomizer.color(colors=rep.distribution.uniform((0.1, 0.1, 0.5), (0.9, 0.9, 1.0)))

            with spheres:
                rep.modify.pose(
                    position=rep.distribution.uniform((-80, 5, -80), (80, 40, 80)),
                    scale=rep.distribution.uniform(0.5, 1.2)
                )
                rep.randomizer.color(colors=rep.distribution.uniform((0.5, 0.1, 0.1), (1.0, 0.8, 0.2)))

            with cylinders:
                rep.modify.pose(
                    position=rep.distribution.uniform((-70, 5, -70), (70, 30, 70)),
                    rotation=rep.distribution.uniform((-30, -180, -30), (30, 180, 30)),
                    scale=rep.distribution.uniform(0.7, 1.3)
                )

            # Randomize Lighting (Intensity & Color Temperature)
            with distant_light:
                rep.modify.attribute("intensity", rep.distribution.uniform(2000, 5000))
                rep.modify.attribute("temperature", rep.distribution.uniform(4000, 8500))
                rep.modify.pose(rotation=rep.distribution.uniform((-60, -90, 0), (-30, 90, 0)))

            # Randomize Camera Orbit Path
            with camera:
                rep.modify.pose(
                    position=rep.distribution.uniform((-120, 100, 180), (120, 220, 300)),
                    look_at=(0, 15, 0)
                )

        # 5. Configure Annotator Writers (RGB, BBox 2D/3D, Semantic Segmentation, Depth)
        writer = rep.WriterRegistry.get("BasicWriter")
        writer.initialize(
            output_dir=output_dir,
            rgb=True,
            bounding_box_2d_tight=True,
            bounding_box_3d=True,
            semantic_segmentation=True,
            distance_to_image_plane=True,
            image_output_format="png"
        )
        writer.attach([render_product])

    print(f"[*] Triggering Replicator Orchestrator for {num_frames} frames...")
    rep.orchestrator.run()
    print(f"[OK] Replicator dataset generation complete! Check: {output_dir}")


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_sdg_output")
    setup_synthetic_data_pipeline(output_dir=out_dir, num_frames=10)
