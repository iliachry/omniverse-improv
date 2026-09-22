"""Script to render verified Cesium 4D BIM construction phasing showcase video and animated WebP.
Combines 5 verified Cesium Earth globe milestone screenshots with elegant HUD overlays and smooth crossfades.
"""
import os
from PIL import Image, ImageDraw
import numpy as np
import imageio.v2 as imageio
import shutil

ARTIFACTS_DIR = r"C:\Users\iliac\.gemini\antigravity-ide\brain\6b0f3593-6b3b-46ff-aca2-aa1334a7859a"
WORKSPACE_DIR = r"d:\GitLab\omniverse-improv"

MILESTONES = [
    {
        "file": "cesium_4d_m00_foundation.png",
        "month": 0,
        "title": "CESIUM GLOBE — MONTH 0: SUBSTRUCTURE & EXCAVATION",
        "detail": "Ground Foundation Mat & Pad Footings on Athens Terrain",
        "stats": "Built: 1 Prim (1%) | Georeference: 37.9753° N, 23.7361° E"
    },
    {
        "file": "cesium_4d_m02_columns.png",
        "month": 2,
        "title": "CESIUM GLOBE — MONTH 2: GROUND FRAMING & L1 SLAB",
        "detail": "C40 Concrete Columns & Suspended Deck on Earth Coordinates",
        "stats": "Built: 14 Prims (16%) | WGS84 Altitude: 120.0m"
    },
    {
        "file": "cesium_4d_m06_superstructure.png",
        "month": 6,
        "title": "CESIUM GLOBE — MONTH 6: SUPERSTRUCTURE TOPPING OUT",
        "detail": "4-Storey Structural Column Grid & Penthouse Core",
        "stats": "Built: 40 Prims (46%) | Structure Framing Topped Out"
    },
    {
        "file": "cesium_4d_m08_facade.png",
        "month": 8,
        "title": "CESIUM GLOBE — MONTH 8: CURTAIN WALL ENCLOSURE",
        "detail": "Low-E Double Glazed Perimeter Facade & Weatherproofing",
        "stats": "Built: 57 Prims (66%) | Enclosure Weather-Tight"
    },
    {
        "file": "cesium_4d_m12_handover.png",
        "month": 12,
        "title": "CESIUM GLOBE — MONTH 12: MEP FIT-OUT & COMMISSIONING",
        "detail": "Rooftop Chillers, Solar PV Array, Server Racks & Final Handover",
        "stats": "Built: 87 Prims (100%) | Full Facility Commissioned"
    }
]

def draw_hud(img, milestone):
    """Draw a clean, modern HUD banner onto the Cesium image."""
    canvas = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    bx, by, bw, bh = 40, 40, 840, 140
    # Glass badge
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=16, fill=(15, 23, 42, 220), outline=(56, 189, 248, 180), width=2)
    
    month_color = (56, 189, 248, 255) if milestone["month"] < 12 else (52, 211, 153, 255)
    draw.text((bx + 24, by + 18), milestone["title"], fill=month_color)
    draw.text((bx + 24, by + 56), milestone["detail"], fill=(241, 245, 249, 255))
    draw.text((bx + 24, by + 94), milestone["stats"], fill=(148, 163, 184, 255))

    # Badge on right
    tag = "CESIUM 4D" if milestone["month"] < 12 else "COMPLETED"
    tag_w = 120
    draw.rounded_rectangle([bx + bw - tag_w - 20, by + 18, bx + bw - 20, by + 52], radius=8, 
                           fill=(16, 185, 129, 60) if milestone["month"] == 12 else (14, 165, 233, 60), 
                           outline=month_color, width=1)
    draw.text((bx + bw - tag_w - 6, by + 24), tag, fill=month_color)

    res = Image.alpha_composite(canvas, overlay)
    return res.convert("RGB")

def main():
    loaded_frames = []
    target_w, target_h = 1600, 1200

    print("Loading Cesium milestone screenshots and generating HUD overlays...")
    for m in MILESTONES:
        path = os.path.join(ARTIFACTS_DIR, m["file"])
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {path}")
        im = Image.open(path)
        im_hud = draw_hud(im, m)
        im_hud = im_hud.resize((target_w, target_h), Image.Resampling.LANCZOS)
        loaded_frames.append(im_hud)

    HOLD_FRAMES = 24
    FADE_FRAMES = 12
    FINAL_HOLD = 40

    video_frames = []
    webp_frames = []

    for i in range(len(loaded_frames)):
        cur = np.array(loaded_frames[i])
        hold_count = FINAL_HOLD if i == len(loaded_frames) - 1 else HOLD_FRAMES
        
        for _ in range(hold_count):
            video_frames.append(cur)

        if i < len(loaded_frames) - 1:
            nxt = np.array(loaded_frames[i + 1])
            for f in range(FADE_FRAMES):
                alpha = (f + 1) / (FADE_FRAMES + 1)
                blended = ((1.0 - alpha) * cur + alpha * nxt).astype(np.uint8)
                video_frames.append(blended)

    print(f"Total video frames: {len(video_frames)} (~{len(video_frames)/20:.1f}s at 20fps)")
    for f in video_frames[::2]:
        p_img = Image.fromarray(f).resize((800, 600), Image.Resampling.BILINEAR)
        webp_frames.append(p_img)

    out_mp4_artifact = os.path.join(ARTIFACTS_DIR, "bim_cesium_4d_phasing_showcase.mp4")
    out_mp4_workspace = os.path.join(WORKSPACE_DIR, "bim_cesium_4d_phasing_showcase.mp4")

    print(f"Writing MP4: {out_mp4_artifact}...")
    writer = imageio.get_writer(out_mp4_artifact, fps=20, codec='libx264', quality=8)
    for frame in video_frames:
        writer.append_data(frame)
    writer.close()

    shutil.copyfile(out_mp4_artifact, out_mp4_workspace)
    print(f"Copied MP4 to workspace: {out_mp4_workspace}")

    out_webp_artifact = os.path.join(ARTIFACTS_DIR, "bim_cesium_4d_phasing_showcase_animated.webp")
    out_webp_workspace = os.path.join(WORKSPACE_DIR, "bim_cesium_4d_phasing_showcase_animated.webp")

    print(f"Writing animated WebP: {out_webp_artifact}...")
    webp_frames[0].save(
        out_webp_artifact,
        save_all=True,
        append_images=webp_frames[1:],
        duration=100,
        loop=0,
        quality=85
    )
    shutil.copyfile(out_webp_artifact, out_webp_workspace)
    print(f"Copied WebP to workspace: {out_webp_workspace}")
    print("CESIUM 4D SHOWCASE RENDERING COMPLETE!")

if __name__ == "__main__":
    main()
