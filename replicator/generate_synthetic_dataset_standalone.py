#!/usr/bin/env python3
"""
Standalone Synthetic Data Generation (SDG) & Domain Randomization Pipeline.
Generates multi-modal AI training datasets (RGB images, 2D Bounding Boxes,
Semantic Segmentation Masks, and JSON metadata) completely offline using
Pillow, NumPy, and OpenUSD without needing Omniverse Kit or a GPU.
"""

import json
import math
import os
import random
from typing import List, Dict, Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def generate_synthetic_frame(
    frame_idx: int,
    output_dir: str,
    width: int = 512,
    height: int = 512,
) -> Dict[str, Any]:
    """Generates a single randomized multi-modal synthetic frame."""
    
    # 1. Background (Simulated Studio Environment)
    bg_color = (
        random.randint(20, 40),
        random.randint(25, 45),
        random.randint(35, 60)
    )
    rgb_img = Image.new("RGB", (width, height), bg_color)
    seg_img = Image.new("RGB", (width, height), (0, 0, 0)) # Background is class 0 (black)
    
    draw_rgb = ImageDraw.Draw(rgb_img)
    draw_seg = ImageDraw.Draw(seg_img)

    # Class color map for segmentation
    class_seg_colors = {
        "cube": (255, 50, 50),       # Red
        "sphere": (50, 255, 50),     # Green
        "cylinder": (50, 150, 255),  # Blue
    }

    # 2. Domain Randomization (Spawn 6-12 randomized shapes)
    num_objects = random.randint(6, 10)
    bounding_boxes_2d = []
    classes = ["cube", "sphere", "cylinder"]

    # Draw a simulated floor horizon
    horizon_y = height // 2 + 50
    draw_rgb.polygon(
        [(0, horizon_y), (width, horizon_y), (width, height), (0, height)],
        fill=(bg_color[0] + 15, bg_color[1] + 15, bg_color[2] + 15)
    )

    for obj_id in range(num_objects):
        cls_name = random.choice(classes)
        seg_color = class_seg_colors[cls_name]
        
        # Random RGB material color
        r = random.randint(70, 240)
        g = random.randint(70, 240)
        b = random.randint(70, 240)
        obj_rgb = (r, g, b)

        # Random size and position
        size_w = random.randint(35, 75)
        size_h = random.randint(35, 75)
        center_x = random.randint(60, width - 60)
        center_y = random.randint(horizon_y - 40, height - 60)

        x0 = center_x - size_w // 2
        y0 = center_y - size_h // 2
        x1 = center_x + size_w // 2
        y1 = center_y + size_h // 2

        # Draw primitive shape
        if cls_name == "cube":
            # 3D isometric cube look
            draw_rgb.rectangle([x0, y0, x1, y1], fill=obj_rgb, outline=(0, 0, 0), width=2)
            draw_seg.rectangle([x0, y0, x1, y1], fill=seg_color)
        elif cls_name == "sphere":
            draw_rgb.ellipse([x0, y0, x1, y1], fill=obj_rgb, outline=(0, 0, 0), width=2)
            # Add highlight
            draw_rgb.ellipse([x0 + 8, y0 + 8, x0 + 18, y0 + 18], fill=(255, 255, 255, 180))
            draw_seg.ellipse([x0, y0, x1, y1], fill=seg_color)
        elif cls_name == "cylinder":
            draw_rgb.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=obj_rgb, outline=(0, 0, 0), width=2)
            draw_seg.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=seg_color)

        bounding_boxes_2d.append({
            "objectId": obj_id,
            "class": cls_name,
            "box2d": [int(x0), int(y0), int(x1), int(y1)],
            "center": [int(center_x), int(center_y)],
            "area": int((x1 - x0) * (y1 - y0))
        })

    # Save RGB Frame
    rgb_path = os.path.join(output_dir, f"rgb_{frame_idx:04d}.png")
    rgb_img.save(rgb_path)

    # Save Segmentation Mask
    seg_path = os.path.join(output_dir, f"segmentation_{frame_idx:04d}.png")
    seg_img.save(seg_path)

    # Save Bounding Box Overlay Visualization
    bbox_img = rgb_img.copy()
    draw_bbox = ImageDraw.Draw(bbox_img)
    for box_info in bounding_boxes_2d:
        box = box_info["box2d"]
        draw_bbox.rectangle(box, outline=(0, 255, 0), width=2)
        draw_bbox.text((box[0], box[1] - 12), f"{box_info['class']} #{box_info['objectId']}", fill=(0, 255, 0))

    bbox_path = os.path.join(output_dir, f"bbox_overlay_{frame_idx:04d}.png")
    bbox_img.save(bbox_path)

    # Metadata record
    meta = {
        "frameIndex": frame_idx,
        "resolution": [width, height],
        "rgbImage": os.path.basename(rgb_path),
        "segmentationMask": os.path.basename(seg_path),
        "bboxOverlay": os.path.basename(bbox_path),
        "objectsCount": len(bounding_boxes_2d),
        "annotations": bounding_boxes_2d
    }

    return meta


def generate_synthetic_dataset(output_dir: str = "_sdg_output", num_frames: int = 10):
    """Generates a complete multi-modal annotated synthetic dataset."""
    print(f"[*] Starting Standalone Synthetic Data Pipeline -> {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    dataset_records = []
    for i in range(num_frames):
        meta = generate_synthetic_frame(i, output_dir)
        dataset_records.append(meta)

    # Save Master Annotations JSON
    json_path = os.path.join(output_dir, "dataset_annotations.json")
    with open(json_path, "w") as f:
        json.dump({
            "datasetName": "Omniverse_Improv_Standalone_SDG",
            "totalFrames": num_frames,
            "classes": ["cube", "sphere", "cylinder"],
            "frames": dataset_records
        }, f, indent=2)

    print(f"[OK] Generated {num_frames} synthetic annotated frames successfully at: {output_dir}")
    print(f"    - RGB Images: rgb_*.png")
    print(f"    - Semantic Masks: segmentation_*.png")
    print(f"    - BBox Overlays: bbox_overlay_*.png")
    print(f"    - JSON Metadata: dataset_annotations.json")
    return output_dir


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_sdg_output")
    generate_synthetic_dataset(output_dir=out, num_frames=5)
