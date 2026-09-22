"""Script to render verified 4D BIM construction phasing showcase video and animated WebP.
Combines 5 verified milestone screenshots with elegant HUD overlays and smooth crossfades.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import imageio.v2 as imageio

ARTIFACTS_DIR = r"C:\Users\iliac\.gemini\antigravity-ide\brain\6b0f3593-6b3b-46ff-aca2-aa1334a7859a"
WORKSPACE_DIR = r"d:\GitLab\omniverse-improv"

MILESTONES = [
    {
        "file": "verified_4d_m00_foundation_1790057034239.png",
        "month": 0,
        "title": "MONTH 0: SUBSTRUCTURE & EXCAVATION",
        "detail": "Foundation Mat & Reinforced Concrete Slab on Grade",
        "stats": "Built: 1 Prim (1%) | Status: Groundwork Complete"
    },
    {
        "file": "verified_4d_m02_ground_columns_1790057087457.png",
        "month": 2,
        "title": "MONTH 2: GROUND FLOOR FRAMING & L1 SLAB",
        "detail": "Cast Concrete Columns (C1-C12) & First Floor Suspended Deck",
        "stats": "Built: 14 Prims (16%) | Status: Structural Core Active"
    },
    {
        "file": "verified_4d_m06_superstructure_1790057135865.png",
        "month": 6,
        "title": "MONTH 6: SUPERSTRUCTURE TOPPED OUT",
        "detail": "4-Storey Structural Column Grid, L2-L4 Slabs & Rooftop Penthouse",
        "stats": "Built: 40 Prims (46%) | Status: Framing Topped Out"
    },
    {
        "file": "verified_4d_m08_curtain_wall_1790057181777.png",
        "month": 8,
        "title": "MONTH 8: BUILDING ENVELOPE & FACADE",
        "detail": "Low-E Double Glazed Curtain Wall & Weatherproofing Enclosure",
        "stats": "Built: 65 Prims (75%) | Status: Weather-Tight Enclosure"
    },
    {
        "file": "verified_4d_m12_handover_1790057231580.png",
        "month": 12,
        "title": "MONTH 12: MEP FIT-OUT & COMMISSIONING",
        "detail": "Rooftop Chillers, Solar PV Array, Server Racks & Final Handover",
        "stats": "Built: 87 Prims (100%) | Status: Practical Completion & Handover"
    }
]

def draw_hud(img, milestone):
    """Draw a clean, modern HUD banner onto the image."""
    canvas = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = canvas.size

    # Banner dimensions at top-left
    bx, by, bw, bh = 40, 40, 780, 140
    # Background glass pill
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=16, fill=(15, 23, 42, 220), outline=(56, 189, 248, 180), width=2)
    
    # Header bar
    month_color = (56, 189, 248, 255) if milestone["month"] < 12 else (52, 211, 153, 255)
    draw.text((bx + 24, by + 18), milestone["title"], fill=month_color)
    draw.text((bx + 24, by + 56), milestone["detail"], fill=(241, 245, 249, 255))
    draw.text((bx + 24, by + 94), milestone["stats"], fill=(148, 163, 184, 255))

    # Badge on right of HUD
    tag = "HANDOVER" if milestone["month"] == 12 else f"M{milestone['month']} / 12"
    tag_w = 110
    draw.rounded_rectangle([bx + bw - tag_w - 20, by + 18, bx + bw - 20, by + 52], radius=8, 
                           fill=(16, 185, 129, 60) if milestone["month"] == 12 else (14, 165, 233, 60), 
                           outline=month_color, width=1)
    draw.text((bx + bw - tag_w - 6, by + 24), tag, fill=month_color)

    # Composite
    res = Image.alpha_composite(canvas, overlay)
    return res.convert("RGB")

def main():
    loaded_frames = []
    target_w, target_h = 1600, 1200 # Multiple of 16 for video encoder

    print("Loading milestone screenshots and generating HUD overlays...")
    for m in MILESTONES:
        path = os.path.join(ARTIFACTS_DIR, m["file"])
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {path}")
        im = Image.open(path)
        im_hud = draw_hud(im, m)
        im_hud = im_hud.resize((target_w, target_h), Image.Resampling.LANCZOS)
        loaded_frames.append(im_hud)

    # Build sequence of frames with holds and crossfades
    HOLD_FRAMES = 24  # 1.2s hold at 20fps
    FADE_FRAMES = 12  # 0.6s crossfade
    FINAL_HOLD = 40   # 2.0s hold on month 12

    video_frames = []
    webp_frames = []

    for i in range(len(loaded_frames)):
        cur = np.array(loaded_frames[i])
        hold_count = FINAL_HOLD if i == len(loaded_frames) - 1 else HOLD_FRAMES
        
        # Hold
        for _ in range(hold_count):
            video_frames.append(cur)

        # Crossfade to next
        if i < len(loaded_frames) - 1:
            nxt = np.array(loaded_frames[i + 1])
            for f in range(FADE_FRAMES):
                alpha = (f + 1) / (FADE_FRAMES + 1)
                blended = ((1.0 - alpha) * cur + alpha * nxt).astype(np.uint8)
                video_frames.append(blended)

    # Create optimized frames for WebP (downscale to 800x600, sample every 2nd frame)
    print(f"Total video frames: {len(video_frames)} (~{len(video_frames)/20:.1f}s at 20fps)")
    for f in video_frames[::2]:
        p_img = Image.fromarray(f).resize((800, 600), Image.Resampling.BILINEAR)
        webp_frames.append(p_img)

    # 1. Save MP4 to artifacts dir and workspace root
    out_mp4_artifact = os.path.join(ARTIFACTS_DIR, "bim_4d_phasing_showcase.mp4")
    out_mp4_workspace = os.path.join(WORKSPACE_DIR, "bim_4d_phasing_showcase.mp4")

    print(f"Writing MP4 video: {out_mp4_artifact}...")
    writer = imageio.get_writer(out_mp4_artifact, fps=20, codec='libx264', quality=8)
    for frame in video_frames:
        writer.append_data(frame)
    writer.close()

    # Copy to workspace
    import shutil
    shutil.copyfile(out_mp4_artifact, out_mp4_workspace)
    print(f"Copied MP4 to workspace: {out_mp4_workspace}")

    # 2. Save WebP animated to artifacts dir and workspace root
    out_webp_artifact = os.path.join(ARTIFACTS_DIR, "bim_4d_phasing_showcase_animated.webp")
    out_webp_workspace = os.path.join(WORKSPACE_DIR, "bim_4d_phasing_showcase_animated.webp")

    print(f"Writing animated WebP: {out_webp_artifact}...")
    webp_frames[0].save(
        out_webp_artifact,
        save_all=True,
        append_images=webp_frames[1:],
        duration=100, # 10fps = 100ms per frame
        loop=0,
        quality=85
    )
    shutil.copyfile(out_webp_artifact, out_webp_workspace)
    print(f"Copied WebP to workspace: {out_webp_workspace}")
    print("ALL 4D VIDEO RENDERS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
