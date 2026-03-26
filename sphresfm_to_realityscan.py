#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
======================================================================
  SphReSfM → RealityScan Conversion GUI Tool
======================================================================

Takes NeRF output (transforms.json + PLY) together with 360° images
and mask images as input, and converts them to a RealityScan-compatible
format (images + XMP) with flexible split settings
(FOV, Overlap, Pitch, Aspect Ratio).

Image cropping uses the FFmpeg v360 filter.

Dependencies:
    pip install numpy
    FFmpeg (conda install -c conda-forge ffmpeg -y)
======================================================================
"""

import math
import os
import shutil
import struct
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import concurrent.futures

import numpy as np


# ─────────────────────────────────────────────
# PLY Parser (ASCII + Binary support)
# ─────────────────────────────────────────────
def read_ply(filepath: str) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Read a PLY file and return vertex coordinates and color data.

    Supports ASCII, binary_little_endian, and binary_big_endian formats.

    Returns:
        points: (N, 3) float64 array (x, y, z)
        colors: (N, 3) uint8 array (r, g, b) or None
    """
    properties: List[Tuple[str, str]] = []  # (type, name)
    vertex_count = 0
    ply_format = "ascii"

    with open(filepath, "rb") as f:
        # ── Parse header (read in binary mode, decode as text) ──
        while True:
            line = f.readline()
            if not line:
                break
            line_str = line.decode("utf-8", errors="replace").strip()
            if line_str == "end_header":
                break
            if line_str.startswith("format"):
                parts = line_str.split()
                if len(parts) >= 2:
                    ply_format = parts[1]  # ascii, binary_little_endian, binary_big_endian
            elif line_str.startswith("element vertex"):
                vertex_count = int(line_str.split()[-1])
            elif line_str.startswith("property"):
                parts = line_str.split()
                if len(parts) >= 3:
                    properties.append((parts[1], parts[2]))  # (type, name)

        if vertex_count == 0:
            return np.empty((0, 3)), None

        # Identify indices from property names
        prop_names = [p[1] for p in properties]
        try:
            idx_x = prop_names.index("x")
            idx_y = prop_names.index("y")
            idx_z = prop_names.index("z")
        except ValueError:
            raise ValueError("PLY file does not contain x, y, z properties")

        has_color = "red" in prop_names and "green" in prop_names and "blue" in prop_names
        if has_color:
            idx_r = prop_names.index("red")
            idx_g = prop_names.index("green")
            idx_b = prop_names.index("blue")

        points = np.empty((vertex_count, 3), dtype=np.float64)
        colors = np.empty((vertex_count, 3), dtype=np.uint8) if has_color else None

        if ply_format == "ascii":
            # ── Read ASCII data ──
            for i in range(vertex_count):
                line = f.readline()
                if not line:
                    points = points[:i]
                    if colors is not None:
                        colors = colors[:i]
                    break
                parts = line.decode("utf-8", errors="replace").split()
                try:
                    points[i, 0] = float(parts[idx_x])
                    points[i, 1] = float(parts[idx_y])
                    points[i, 2] = float(parts[idx_z])
                    if has_color and colors is not None:
                        colors[i, 0] = max(0, min(255, int(float(parts[idx_r]))))
                        colors[i, 1] = max(0, min(255, int(float(parts[idx_g]))))
                        colors[i, 2] = max(0, min(255, int(float(parts[idx_b]))))
                except (ValueError, IndexError):
                    continue
        else:
            # ── Read binary data ──
            byte_order = "<" if ply_format == "binary_little_endian" else ">"

            # PLY type → struct format char & size
            type_map = {
                "float": ("f", 4), "float32": ("f", 4),
                "double": ("d", 8), "float64": ("d", 8),
                "char": ("b", 1), "int8": ("b", 1),
                "uchar": ("B", 1), "uint8": ("B", 1),
                "short": ("h", 2), "int16": ("h", 2),
                "ushort": ("H", 2), "uint16": ("H", 2),
                "int": ("i", 4), "int32": ("i", 4),
                "uint": ("I", 4), "uint32": ("I", 4),
            }

            # Build format string for each property
            fmt_chars = []
            for prop_type, prop_name in properties:
                if prop_type in type_map:
                    fc, sz = type_map[prop_type]
                    fmt_chars.append(fc)
                else:
                    raise ValueError(f"Unsupported PLY property type: {prop_type}")

            vertex_fmt = byte_order + "".join(fmt_chars)
            vertex_size = struct.calcsize(vertex_fmt)

            for i in range(vertex_count):
                data = f.read(vertex_size)
                if len(data) < vertex_size:
                    points = points[:i]
                    if colors is not None:
                        colors = colors[:i]
                    break
                values = struct.unpack(vertex_fmt, data)
                points[i, 0] = float(values[idx_x])
                points[i, 1] = float(values[idx_y])
                points[i, 2] = float(values[idx_z])
                if has_color and colors is not None:
                    colors[i, 0] = max(0, min(255, int(values[idx_r])))
                    colors[i, 1] = max(0, min(255, int(values[idx_g])))
                    colors[i, 2] = max(0, min(255, int(values[idx_b])))

    return points, colors




# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
DEFAULT_FOV = 90
DEFAULT_OVERLAP = 0.3
DEFAULT_PITCHES = "0"
DEFAULT_WIDTH = 960
DEFAULT_ASPECT = "1:1"


# ─────────────────────────────────────────────
# FFmpeg Check
# ─────────────────────────────────────────────
def check_ffmpeg() -> bool:
    """Check whether FFmpeg is available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


# ─────────────────────────────────────────────
# Calculation Utilities
# ─────────────────────────────────────────────
def compute_yaw_interval(fov: float, overlap: float) -> float:
    """Calculate the horizontal rotation step (degrees)."""
    return fov * (1.0 - overlap)


def derive_vertical_fov(h_fov: float, aspect: float) -> float:
    """Derive vertical FOV (degrees) from horizontal FOV and aspect ratio."""
    h_rad = math.radians(h_fov)
    v_rad = 2.0 * math.atan(math.tan(h_rad / 2.0) / aspect)
    return math.degrees(v_rad)


def fov_to_focal_pixel(output_width: int, h_fov: float) -> float:
    """Calculate focal length in pixels."""
    h_rad = math.radians(h_fov)
    return output_width / (2.0 * math.tan(h_rad / 2.0))


def vfov_to_focal_pixel(output_height: int, v_fov: float) -> float:
    """Calculate vertical focal length in pixels."""
    v_rad = math.radians(v_fov)
    return output_height / (2.0 * math.tan(v_rad / 2.0))


def fov_to_focal_equiv(h_fov: float) -> float:
    """Calculate 35mm-equivalent focal length (mm)."""
    h_rad = math.radians(h_fov)
    return 36.0 / (2.0 * math.tan(h_rad / 2.0))


# ─────────────────────────────────────────────
# NeRF JSON Parser
# ─────────────────────────────────────────────
def parse_nerf_json(json_path: Path) -> Dict[str, Any]:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ─────────────────────────────────────────────
# Rotation Matrix / Quaternion
# ─────────────────────────────────────────────
def build_view_rotation(yaw_deg: float, pitch_deg: float) -> np.ndarray:
    """Build a rotation matrix for the given yaw/pitch angles.

    yaw:   rotation around the Y-axis (degrees)
    pitch: rotation around the X-axis (degrees)
    """
    yaw = np.radians(yaw_deg)
    cos_y = np.cos(yaw)
    sin_y = np.sin(yaw)
    R_yaw = np.array([
        [cos_y, 0, sin_y],
        [0, 1, 0],
        [-sin_y, 0, cos_y],
    ])

    pitch = np.radians(pitch_deg)
    cos_p = np.cos(pitch)
    sin_p = np.sin(pitch)
    R_pitch = np.array([
        [1, 0, 0],
        [0, cos_p, -sin_p],
        [0, sin_p, cos_p],
    ])

    return R_yaw @ R_pitch


def rotmat_to_quat(R: np.ndarray) -> np.ndarray:
    """Convert 3x3 rotation matrix to normalized quaternion (x, y, z, w)."""
    trace = np.trace(R)
    if trace > 0:
        S = 0.5 / np.sqrt(trace + 1.0)
        w = 0.25 / S
        x = (R[2, 1] - R[1, 2]) * S
        y = (R[0, 2] - R[2, 0]) * S
        z = (R[1, 0] - R[0, 1]) * S
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        S = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        w = (R[2, 1] - R[1, 2]) / S
        x = 0.25 * S
        y = (R[0, 1] + R[1, 0]) / S
        z = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        w = (R[0, 2] - R[2, 0]) / S
        x = (R[0, 1] + R[1, 0]) / S
        y = 0.25 * S
        z = (R[1, 2] + R[2, 1]) / S
    else:
        S = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        w = (R[1, 0] - R[0, 1]) / S
        x = (R[0, 2] + R[2, 0]) / S
        y = (R[1, 2] + R[2, 1]) / S
        z = 0.25 * S

    q = np.array([x, y, z, w])
    return q / np.linalg.norm(q)


# ─────────────────────────────────────────────
# Image Cropping via FFmpeg
# ─────────────────────────────────────────────
def extract_perspective_view(
    input_path: str,
    out_root: str,
    yaw_deg: float,
    pitch_deg: float,
    h_fov: float,
    v_fov: float,
    output_width: int,
    output_height: int,
    flip_vertical: bool = False,
) -> subprocess.CompletedProcess:
    """Convert equirectangular → flat using the FFmpeg v360 filter."""
    # FFmpeg v360 accepts yaw in the range -180 to 180
    ff_yaw = yaw_deg if yaw_deg <= 180.0 else yaw_deg - 360.0

    # pitch sign: positive is upward in FFmpeg v360
    ff_pitch = pitch_deg

    filter_chain = []
    if flip_vertical:
        filter_chain.append("vflip")

    filter_chain.append(
        f"v360=input=e:output=flat"
        f":yaw={ff_yaw}"
        f":pitch={ff_pitch}"
        f":h_fov={h_fov}"
        f":v_fov={v_fov:.2f}"
        f":w={output_width}"
        f":h={output_height}"
    )

    video_filter = ",".join(filter_chain)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vf", video_filter,
        "-q:v", "2",
        out_root,
    ]

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )


# ─────────────────────────────────────────────
# Main Conversion Process
# ─────────────────────────────────────────────
def execute_conversion(
    json_path: str,
    assume_opengl: bool,
    images_dir: str,
    output_dir: str,
    ply_path: Optional[str],
    masks_dir: Optional[str],
    h_fov: float,
    overlap: float,
    pitches: List[float],
    output_width: int,
    aspect_ratio: float,
    rotate_cams_y180: bool,
    skip_crop: bool,
    log_callback,
    progress_callback,
    done_callback,
):
    """Run the conversion in a background thread."""
    try:
        # ── 1. Collect input images ──
        input_dir = Path(images_dir)
        src_images = []
        for ext in SUPPORTED_EXTENSIONS:
            src_images.extend(input_dir.glob(f"*{ext}"))
        src_images.sort()
        src_image_lookup = {img.stem: img for img in src_images}
        src_image_lookup.update({img.name: img for img in src_images})

        if not src_images:
            log_callback("⚠️ No image files were found.")
            done_callback()
            return

        mask_lookup: Dict[str, Path] = {}
        num_masks = 0
        if masks_dir:
            masks_path = Path(masks_dir)
            if masks_path.is_dir():
                mask_files = []
                for ext in SUPPORTED_EXTENSIONS:
                    mask_files.extend(masks_path.glob(f"*{ext}"))
                # Match mask files by stem name
                for mf in mask_files:
                    # "frame_001.mask.png" → stem = "frame_001.mask"
                    # "frame_001.png" → stem = "frame_001"
                    stem = mf.stem
                    if stem.endswith(".mask"):
                        stem = stem[:-5]
                    mask_lookup[stem] = mf
                    mask_lookup[mf.name] = mf
                num_masks = len(mask_files)

        # ── 3. Parse NeRF JSON ──
        log_callback(f"📄 Loading NeRF JSON: {json_path}")
        nerf_data = parse_nerf_json(Path(json_path))
        frames = nerf_data.get("frames", [])
        log_callback(f"  Frames: {len(frames)}")

        # ── 4. Calculate split angles ──
        output_height = int(output_width / aspect_ratio)
        v_fov = derive_vertical_fov(h_fov, aspect_ratio)
        yaw_interval = compute_yaw_interval(h_fov, overlap)

        yaw_angles: List[float] = []
        yaw = 0.0
        while yaw < 360.0:
            yaw_angles.append(round(yaw, 2))
            yaw += yaw_interval

        log_callback(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log_callback(f"📐 Settings:")
        log_callback(f"   Horizontal FOV  : {h_fov}°")
        log_callback(f"   Vertical FOV    : {v_fov:.1f}°")
        log_callback(f"   Overlap Rate    : {overlap}")
        log_callback(f"   Yaw Step        : {yaw_interval:.1f}°")
        log_callback(f"   Yaw Count       : {len(yaw_angles)}")
        log_callback(f"   Pitch Values    : {pitches}")
        log_callback(f"   Output Size     : {output_width} × {output_height}")
        log_callback(f"   Input Images    : {len(src_images)}")
        log_callback(f"   Mask Images     : {num_masks}")
        log_callback(f"   Skip Splitting  : {'ON' if skip_crop else 'OFF'}")
        log_callback(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log_callback("")

        # ── 5. Create output directories ──
        out_root = Path(output_dir)
        out_root.mkdir(parents=True, exist_ok=True)
        combined_dir = out_root / "all"
        combined_dir.mkdir(parents=True, exist_ok=True)
        split_img_dir = out_root / "images"
        split_img_dir.mkdir(parents=True, exist_ok=True)
        split_mask_dir = None
        if mask_lookup:
            split_mask_dir = out_root / "masks"
            split_mask_dir.mkdir(parents=True, exist_ok=True)

        # ── 6. Collect camera information ──
        camera_entries: List[Dict[str, Any]] = []
        num_skipped = 0

        for frame_idx, frame in enumerate(frames):
            fpath = frame.get("file_path", "")
            if not fpath:
                num_skipped += 1
                continue
                
            img_path = None
            base_name_f = os.path.basename(fpath)
            
            if base_name_f in src_image_lookup:
                img_path = src_image_lookup[base_name_f]
            else:
                # Try matching without extension
                stem_f = Path(base_name_f).stem
                if stem_f in src_image_lookup:
                    img_path = src_image_lookup[stem_f]
            
            if img_path is None:
                p = Path(json_path).parent / fpath
                if p.exists() and p.is_file():
                    img_path = p
                else:
                    for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                        if p.with_suffix(ext).exists():
                            img_path = p.with_suffix(ext)
                            break
            
            if img_path is None or not img_path.exists():
                num_skipped += 1
                continue
                
            transform = np.array(frame["transform_matrix"], dtype=np.float64)
            R_cam = transform[:3, :3]
            t_cam = transform[:3, 3]
            
            if assume_opengl:
                flip_yz = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=np.float64)
                R_cam = R_cam @ flip_yz
                
            base_name = img_path.stem
            
            mask_path = None
            if mask_lookup:
                if base_name in mask_lookup:
                    mask_path = mask_lookup[base_name]

            camera_entries.append({
                "label": base_name,
                "base_name": base_name,
                "src_image": img_path,
                "mask_image": mask_path,
                "R_cam": R_cam,
                "t_cam": t_cam,
            })

        if not camera_entries:
            log_callback("⚠️ No valid cameras found. Please check that the JSON and image folder match.")
            done_callback()
            return

        log_callback(f"📷 Valid cameras: {len(camera_entries)}")
        if num_skipped > 0:
            log_callback(f"   Skipped: {num_skipped}")
        log_callback("")

        # ── 7. COLMAP camera intrinsics ──
        fx = fov_to_focal_pixel(output_width, h_fov)
        fy = vfov_to_focal_pixel(output_height, v_fov)
        cx = output_width / 2.0
        cy = output_height / 2.0
        cam_id = 1
        colmap_cameras = {
            cam_id: {
                "width": output_width,
                "height": output_height,
                "model": "PINHOLE",
                "params": [fx, fy, cx, cy],
            }
        }

        # ── 8. Image cropping + extrinsic parameters ──
        total_views = len(camera_entries) * len(yaw_angles) * len(pitches)
        if mask_lookup:
            total_work = total_views * 2  # images + masks
        else:
            total_work = total_views
        log_callback(f"🔄 Starting crop: {total_views} images (cameras {len(camera_entries)} × yaw {len(yaw_angles)} × pitch {len(pitches)})")
        log_callback("")

        colmap_images: Dict[int, Dict[str, Any]] = {}
        img_id = 1
        completed = 0
        split_errors = 0

        split_tasks = []

        for cam_entry in camera_entries:
            base_name = cam_entry["base_name"]
            src_image = str(cam_entry["src_image"])
            mask_image = str(cam_entry["mask_image"]) if cam_entry["mask_image"] else None
            R_cam = cam_entry["R_cam"]
            t_cam = cam_entry["t_cam"]

            for pitch in pitches:
                for yaw in yaw_angles:
                    # Output filename
                    out_name = f"{base_name}_y{yaw:06.1f}_p{pitch:+.0f}.jpg"
                    out_path = str(split_img_dir / out_name)

                    if not skip_crop:
                        # Add FFmpeg task to list
                        split_tasks.append((
                            src_image, out_path,
                            yaw, pitch,
                            h_fov, v_fov,
                            output_width, output_height,
                            out_name
                        ))

                        # Crop mask image
                        if mask_image and split_mask_dir:
                            mask_out_name = f"{base_name}_y{yaw:06.1f}_p{pitch:+.0f}.jpg.mask.png"
                            mask_out_path = str(split_mask_dir / mask_out_name)

                            split_tasks.append((
                                mask_image, mask_out_path,
                                yaw, pitch,
                                h_fov, v_fov,
                                output_width, output_height,
                                mask_out_name
                            ))
                    else:
                        # Advance progress even when splitting is skipped
                        completed += 1
                        progress_callback(completed, total_work)
                        if mask_image and split_mask_dir:
                            completed += 1
                            progress_callback(completed, total_work)

                    # ── Calculate extrinsic parameters ──
                    R_view = build_view_rotation(yaw, pitch)
                    R_world = R_cam @ R_view

                    if rotate_cams_y180:
                        R_y180 = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, -1]], dtype=np.float64)
                        t_cam_mod = R_y180 @ t_cam
                        R_world_mod = R_y180 @ R_world
                    else:
                        t_cam_mod = t_cam
                        R_world_mod = R_world

                    R_inv = R_world_mod.T
                    t_inv = -R_inv @ t_cam_mod

                    q = rotmat_to_quat(R_inv)

                    colmap_images[img_id] = {
                        "quat": q,  # [x, y, z, w]
                        "tvec": t_inv,
                        "cam_id": cam_id,
                        "name": out_name,
                        "world_pos": t_cam_mod.copy(),          # position in world coordinates
                        "R_world": R_world_mod.copy(),  # camera orientation rotation matrix in world coordinates
                    }
                    img_id += 1

        if not skip_crop and split_tasks:
            max_workers = max(1, (os.cpu_count() or 4))
            log_callback(f"⚡ Starting parallel processing with ThreadPoolExecutor (max workers: {max_workers})")
            
            def run_split_task(args):
                src, out_p, y, p, hf, vf, ow, oh, oname = args
                res = extract_perspective_view(src, out_p, y, p, hf, vf, ow, oh)
                return (res, oname)

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(run_split_task, args): args for args in split_tasks}
                for future in concurrent.futures.as_completed(futures):
                    res, oname = future.result()
                    completed += 1
                    progress_callback(completed, total_work)
                    if res.returncode != 0:
                        split_errors += 1
                        if split_errors <= 5:
                            log_callback(f"  ❌ Failed: {oname}")
                            err_lines = res.stderr.strip().splitlines()
                            err_msg = "\n     ".join(err_lines[-3:]) if err_lines else "Unknown error"
                            log_callback(f"     {err_msg}")

        if skip_crop:
            log_callback("")
            log_callback("⚠️ Image splitting was skipped.")
        if split_errors > 0:
            log_callback(f"⚠️ Crop errors: {split_errors}")

        # ── 9. Copy files to all/ folder ──
        log_callback("")
        log_callback("📂 Copying files to all/ folder...")
        # images/ → all/
        if split_img_dir.exists():
            for f in split_img_dir.iterdir():
                if f.is_file():
                    shutil.copy2(str(f), str(combined_dir / f.name))
        # masks/ → all/
        if split_mask_dir and split_mask_dir.exists():
            for f in split_mask_dir.iterdir():
                if f.is_file():
                    shutil.copy2(str(f), str(combined_dir / f.name))

        # ── 10. Output COLMAP cameras.txt ──
        cameras_txt = out_root / "cameras.txt"
        with open(cameras_txt, "w", encoding="utf-8") as f:
            f.write("# Camera list with one line of data per camera:\n")
            f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
            f.write(f"# Number of cameras: {len(colmap_cameras)}\n")
            for cam_id, cam_data in colmap_cameras.items():
                params_str = " ".join(str(p) for p in cam_data["params"])
                f.write(
                    f"{cam_id} {cam_data['model']} {cam_data['width']} {cam_data['height']} {params_str}\n"
                )

        # ── 11. Output COLMAP images.txt ──
        images_txt = out_root / "images.txt"
        with open(images_txt, "w", encoding="utf-8") as f:
            f.write("# Image list with two lines of data per image:\n")
            f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
            f.write("# POINTS2D[] as (X, Y, POINT3D_ID)\n")
            f.write(f"# Number of images: {len(colmap_images)}\n")
            for img_id in sorted(colmap_images.keys()):
                img_data = colmap_images[img_id]
                q = img_data["quat"]
                t = img_data["tvec"]
                f.write(
                    f"{img_id} {q[3]} {q[0]} {q[1]} {q[2]} {t[0]} {t[1]} {t[2]} {img_data['cam_id']} {img_data['name']}\n"
                )
                f.write(" \n")  # COLMAP format requires a second line

        # ── 12. Output RealityCapture XMP files (to all/ folder) ──
        focal_equiv = fov_to_focal_equiv(h_fov)
        for img_id in sorted(colmap_images.keys()):
            img_data = colmap_images[img_id]
            base_name = Path(img_data["name"]).stem
            xmp_filepath = combined_dir / f"{base_name}.xmp"
            
            # C = world_pos
            # R = R_world.T  (World-to-Camera)
            C = img_data["world_pos"]
            R = img_data["R_world"].T

            # RealityCapture XMP Rotation (Row-major)
            # Rebuild by mapping column vectors of R as [X, Z, -Y]
            R_rc = np.zeros((3, 3), dtype=np.float64)
            R_rc[:, 0] = R[:, 0]
            R_rc[:, 1] = R[:, 2]
            R_rc[:, 2] = -R[:, 1]
            
            rot_str = " ".join(f"{x}" for x in R_rc.flatten())

            # Position: [C_x, C_z, -C_y]
            pos_str = f"{C[0]} {C[2]} {-C[1]}"

            xmp_content = f"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xcr:Version="3"
       xmlns:xcr="http://www.capturingreality.com/ns/xcr/1.1#"
       xcr:CalibrationPrior="exact"
       xcr:DistortionModel="perspective"
       xcr:FocalLength35mm="{focal_equiv}" xcr:Skew="0" xcr:AspectRatio="1"
       xcr:PrincipalPointU="0" xcr:PrincipalPointV="0"
       xcr:PosePrior="exact"
       xcr:Coordinates="absolute"
       xcr:InMeshing="1" xcr:InTexturing="1">
      <xcr:Rotation>{rot_str}</xcr:Rotation>
      <xcr:Position>{pos_str}</xcr:Position>
	  <xcr:DistortionCoeficients>0 0 0 0 0 0</xcr:DistortionCoeficients>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
"""
            with open(xmp_filepath, "w", encoding="utf-8") as xmp_file:
                xmp_file.write(xmp_content)

        # ── 13. Convert PLY → points3D.txt ──
        point_cloud_entries = []
        if ply_path and Path(ply_path).exists():
            log_callback(f"📦 Processing point cloud: {ply_path}")
            points3d, colors = read_ply(ply_path)
            log_callback(f"  Vertices loaded: {len(points3d)}")

            for idx, point in enumerate(points3d, start=1):
                x, y, z = point
                if colors is not None:
                    r = int(colors[idx - 1, 0])
                    g = int(colors[idx - 1, 1])
                    b = int(colors[idx - 1, 2])
                else:
                    r = g = b = 128
                point_cloud_entries.append((idx, x, y, z, r, g, b, 0.0, ""))

            points3d_txt = out_root / "points3D.txt"
            with open(points3d_txt, "w", encoding="utf-8") as f:
                f.write("# 3D point list with one line of data per point:\n")
                f.write("# POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
                f.write(f"# Number of points: {len(point_cloud_entries)}\n")
                batch_size = 10000
                point_lines = []
                for pid, x, y, z, r, g, b, err, track in point_cloud_entries:
                    point_lines.append(f"{pid} {x:.6f} {y:.6f} {z:.6f} {r} {g} {b} {err} {track}\n")
                    if len(point_lines) >= batch_size:
                        f.write("".join(point_lines))
                        point_lines.clear()
                if point_lines:
                    f.write("".join(point_lines))
            log_callback(f"  points3D.txt written")

        # ── 14. Completion summary ──
        focal_pixel = fov_to_focal_pixel(output_width, h_fov)
        focal_equiv = fov_to_focal_equiv(h_fov)

        log_callback("")
        log_callback(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log_callback(f"🎉 Conversion complete!")
        log_callback(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log_callback(f"  Cropped images : {len(colmap_images)}")
        log_callback(f"  COLMAP cameras : {len(colmap_cameras)}")
        log_callback(f"  Points3D       : {len(point_cloud_entries)}")
        log_callback(f"  Skipped        : {num_skipped}")
        log_callback(f"  Output dir     : {output_dir}")
        log_callback("")
        log_callback(f"╔══════════════════════════════════════════╗")
        log_callback(f"║  📷 Focal Length Info                       ║")
        log_callback(f"╠══════════════════════════════════════════╣")
        log_callback(f"║  ■ Focal length (35mm) : {focal_equiv:<7.2f} mm     ║")
        log_callback(f"║  ■ Focal Length (px)   : {focal_pixel:<7.2f} px     ║")
        log_callback(f"║  ■ fx={fx:.2f}  fy={fy:.2f}              ")
        log_callback(f"║  ■ cx={cx:.2f}  cy={cy:.2f}              ")
        log_callback(f"╚══════════════════════════════════════════╝")

    except Exception as e:
        log_callback(f"❌ An error occurred: {e}")
        import traceback
        log_callback(traceback.format_exc())
    finally:
        done_callback()


# ─────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────
class SphReSfMToRSApp:
    """Tkinter-based GUI application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SphReSfM → RealityScan Converter")
        self.root.geometry("750x850")
        self.root.resizable(True, True)

        # Pre-declare attributes
        self.json_path: tk.StringVar = None  # type: ignore
        self.ply_var: tk.StringVar = None  # type: ignore
        self.images_var: tk.StringVar = None  # type: ignore
        self.masks_var: tk.StringVar = None  # type: ignore
        self.output_var: tk.StringVar = None  # type: ignore
        self.fov_var: tk.StringVar = None  # type: ignore
        self.overlap_var: tk.StringVar = None  # type: ignore
        self.pitch_var: tk.StringVar = None  # type: ignore
        self.width_var: tk.StringVar = None  # type: ignore
        self.aspect_var: tk.StringVar = None  # type: ignore
        self.skip_crop_var: tk.BooleanVar = None  # type: ignore
        self.run_button: ttk.Button = None  # type: ignore
        self.progress_var: tk.DoubleVar = None  # type: ignore
        self.progress_bar: ttk.Progressbar = None  # type: ignore
        self.progress_label: ttk.Label = None  # type: ignore
        self.log_text: tk.Text = None  # type: ignore

        self._build_ui()

    def _build_ui(self):
        # === Input/Output files frame ===
        files_frame = ttk.LabelFrame(self.root, text="📁 Input / Output", padding=10)
        files_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        row = 0
        # transforms.json
        ttk.Label(files_frame, text="transforms.json:").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.json_path = tk.StringVar(value="")
        ttk.Entry(files_frame, textvariable=self.json_path, width=45).grid(
            row=row, column=1, sticky=tk.EW, padx=5
        )
        ttk.Button(files_frame, text="📄", width=3,
                   command=lambda: self._browse_json()).grid(row=row, column=2, sticky=tk.E)

        # PLY
        row += 1
        ttk.Label(files_frame, text="PLY file (optional):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.ply_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.ply_var, width=45).grid(
            row=row, column=1, sticky=tk.EW, padx=5
        )
        ttk.Button(files_frame, text="📄", width=3,
                   command=lambda: self._browse_file(
                       self.ply_var, "Select PLY file",
                       [("PLY files", "*.ply"), ("All files", "*.*")]
                   )).grid(row=row, column=2, sticky=tk.E)

        # Input images folder
        row += 1
        ttk.Label(files_frame, text="Input folder (Equirectangular):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.images_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.images_var, width=45).grid(
            row=row, column=1, sticky=tk.EW, padx=5
        )
        ttk.Button(files_frame, text="📁", width=3,
                   command=lambda: self._browse_folder(self.images_var, "Select Input Image Folder")
                   ).grid(row=row, column=2, sticky=tk.E)

        # Mask images folder
        row += 1
        ttk.Label(files_frame, text="Mask folder (Equirectangular, optional):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.masks_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.masks_var, width=45).grid(
            row=row, column=1, sticky=tk.EW, padx=5
        )
        ttk.Button(files_frame, text="📁", width=3,
                   command=lambda: self._browse_folder(self.masks_var, "Select Mask Image Folder")
                   ).grid(row=row, column=2, sticky=tk.E)

        # Output folder
        row += 1
        ttk.Label(files_frame, text="Output folder:").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.output_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.output_var, width=45).grid(
            row=row, column=1, sticky=tk.EW, padx=5
        )
        ttk.Button(files_frame, text="📁", width=3,
                   command=lambda: self._browse_folder(self.output_var, "Select Output Folder")
                   ).grid(row=row, column=2, sticky=tk.E)

        files_frame.columnconfigure(1, weight=1)

        # === Split settings frame ===
        settings_frame = ttk.LabelFrame(self.root, text="⚙️ Split Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)

        row = 0
        # FOV
        ttk.Label(settings_frame, text="Horizontal FOV (°):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.fov_var = tk.StringVar(value=str(DEFAULT_FOV))
        ttk.Entry(settings_frame, textvariable=self.fov_var, width=10).grid(
            row=row, column=1, sticky=tk.W, padx=5
        )

        # Overlap
        row += 1
        ttk.Label(settings_frame, text="Overlap Rate (0–1):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.overlap_var = tk.StringVar(value=str(DEFAULT_OVERLAP))
        ttk.Entry(settings_frame, textvariable=self.overlap_var, width=10).grid(
            row=row, column=1, sticky=tk.W, padx=5
        )

        # Pitch
        row += 1
        ttk.Label(settings_frame, text="Pitch Angles (comma-separated, e.g. -45,0,45):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.pitch_var = tk.StringVar(value=DEFAULT_PITCHES)
        ttk.Entry(settings_frame, textvariable=self.pitch_var, width=30).grid(
            row=row, column=1, sticky=tk.W, padx=5
        )

        # Aspect ratio
        row += 1
        ttk.Label(settings_frame, text="Aspect Ratio (W:H):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.aspect_var = tk.StringVar(value=DEFAULT_ASPECT)
        ttk.Entry(settings_frame, textvariable=self.aspect_var, width=15).grid(
            row=row, column=1, sticky=tk.W, padx=5
        )

        # Output width
        row += 1
        ttk.Label(settings_frame, text="Output Width (px):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.width_var = tk.StringVar(value=str(DEFAULT_WIDTH))
        ttk.Entry(settings_frame, textvariable=self.width_var, width=10).grid(
            row=row, column=1, sticky=tk.W, padx=5
        )

        # Checkboxes
        frame_flags = ttk.Frame(settings_frame)
        frame_flags.grid(row=row+1, column=0, columnspan=2, sticky=tk.W, pady=3)

        self.skip_crop_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame_flags, text="Skip Image Splitting",
            variable=self.skip_crop_var
        ).pack(side=tk.LEFT, padx=5)

        settings_frame.columnconfigure(1, weight=1)

        # === Run button + progress bar ===
        action_frame = ttk.Frame(self.root, padding=(10, 5))
        action_frame.pack(fill=tk.X)

        self.run_button = ttk.Button(
            action_frame, text="▶ Start Conversion", command=self._start_conversion
        )
        self.run_button.pack(side=tk.LEFT)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            action_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        self.progress_label = ttk.Label(action_frame, text="0 / 0")
        self.progress_label.pack(side=tk.LEFT, padx=(5, 0))

        # === Log area ===
        log_frame = ttk.LabelFrame(self.root, text="📋 Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    # ── File/folder browse ──
    def _browse_file(self, var: tk.StringVar, title: str, filetypes: list):
        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if path:
            var.set(path)
            
    def _browse_json(self):
        filepath = filedialog.askopenfilename(
            title="Select transforms.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            self.json_path.set(filepath)

    def _browse_folder(self, var: tk.StringVar, title: str):
        path = filedialog.askdirectory(title=title)
        if path:
            var.set(path)

    # ── Log output ──
    def _log(self, message: str):
        def _append():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.root.after(0, _append)

    # ── Progress update ──
    def _update_progress(self, current: int, total: int):
        def _update():
            pct = (current / total * 100) if total > 0 else 0
            self.progress_var.set(pct)
            self.progress_label.config(text=f"{current} / {total}")
        self.root.after(0, _update)

    # ── Done callback ──
    def _on_done(self):
        def _finish():
            self.run_button.config(state=tk.NORMAL)
        self.root.after(0, _finish)

    # ── Validate & start conversion ──
    def _start_conversion(self):
        # Required input validation
        json_path = self.json_path.get().strip()
        images_dir = self.images_var.get().strip()
        output_dir = self.output_var.get().strip()

        if not json_path:
            messagebox.showwarning("Input Error", "Please specify transforms.json.")
            return
        if not os.path.isfile(json_path):
            messagebox.showwarning("Input Error", f"JSON file not found:\n{json_path}")
            return
        if not images_dir:
            messagebox.showwarning("Input Error", "Please specify the input image folder.")
            return
        if not os.path.isdir(images_dir):
            messagebox.showwarning("Input Error", f"Image folder not found:\n{images_dir}")
            return
        if not output_dir:
            messagebox.showwarning("Input Error", "Please specify the output folder.")
            return

        # Optional input validation
        ply_path = self.ply_var.get().strip() or None
        if ply_path and not os.path.isfile(ply_path):
            messagebox.showwarning("Input Error", f"PLY file not found:\n{ply_path}")
            return

        masks_dir = self.masks_var.get().strip() or None
        if masks_dir and not os.path.isdir(masks_dir):
            messagebox.showwarning("Input Error", f"Mask folder not found:\n{masks_dir}")
            return

        # Parameter validation
        try:
            h_fov = float(self.fov_var.get())
            if not (10 <= h_fov <= 180):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "FOV must be a number between 10 and 180.")
            return

        try:
            overlap = float(self.overlap_var.get())
            if not (0 <= overlap < 1):
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Overlap Rate must be a number between 0 and 1 (exclusive).")
            return

        try:
            pitches = [float(x.strip()) for x in self.pitch_var.get().split(",")]
        except ValueError:
            messagebox.showwarning("Input Error", "Pitch Angles must be comma-separated numbers.")
            return

        try:
            aspect_str = self.aspect_var.get().strip()
            if ":" not in aspect_str:
                raise ValueError
            w_str, h_str = aspect_str.split(":", 1)
            aspect_w = float(w_str)
            aspect_h = float(h_str)
            if aspect_w <= 0 or aspect_h <= 0:
                raise ValueError
            aspect_ratio = aspect_w / aspect_h
        except ValueError:
            messagebox.showwarning("Input Error", "Enter the aspect ratio in the format '16:9'.")
            return

        try:
            out_width = int(self.width_var.get())
            if out_width < 100:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Output width must be an integer of 100 or more.")
            return

        # Clear log & disable button
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)
        self.progress_label.config(text="0 / 0")
        self.run_button.config(state=tk.DISABLED)

        # Run conversion in background thread
        thread = threading.Thread(
            target=execute_conversion,
            args=(
                json_path,
                True,               # assume_opengl: always True
                images_dir,
                output_dir,
                ply_path,
                masks_dir,
                h_fov,
                overlap,
                pitches,
                out_width,
                aspect_ratio,
                True,               # rotate_cams_y180: always True
                self.skip_crop_var.get(),
                self._log,
                self._update_progress,
                self._on_done,
            ),
            daemon=True,
        )
        thread.start()


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
def main():
    # Check FFmpeg availability
    if not check_ffmpeg():
        err_root = tk.Tk()
        err_root.withdraw()
        messagebox.showerror(
            "FFmpeg not found",
            "FFmpeg is not installed or not in your PATH.\n\n"
            "How to fix:\n"
            "1. Open Anaconda Navigator\n"
            "2. Select Environments → panorama_env\n"
            "3. Change the package list dropdown from 'Installed' to 'Not installed'\n"
            "4. Type 'ffmpeg' in the search box\n"
            "5. Check ffmpeg and click 'Apply'\n\n"
            "See SETUP_GUIDE.md for details.",
        )
        err_root.destroy()
        sys.exit(1)

    root = tk.Tk()
    SphReSfMToRSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
