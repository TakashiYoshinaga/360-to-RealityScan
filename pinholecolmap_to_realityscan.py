#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
======================================================================
  COLMAP (LichtFeld Studio) → RealityScan Conversion GUI Tool
======================================================================

Takes a LichtFeld Studio training-data folder (COLMAP sparse model +
images + masks, images already split into pinhole views) as input and
converts it to a RealityScan-compatible format (images + masks + XMP).

Expected input layout:
    <train_data>/
    ├── images/               pinhole images (+ optional detail/ subfolder)
    ├── masks/                mask PNGs matching image stems (optional)
    └── sparse/               COLMAP model (cameras/images, .txt or .bin)
        └── (or sparse/0/)

Output layout (same as spheresfm_to_realityscan.py):
    <output>/
    ├── images/               copied images
    ├── masks/                masks renamed to <image>.mask.png
    └── all/                  images + masks + per-image XMP files

No FFmpeg required (images are already split).

Dependencies:
    pip install numpy
======================================================================
"""

import os
import shutil
import struct
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}

# COLMAP camera models: model_id → (name, num_params)
COLMAP_CAMERA_MODELS = {
    0: ("SIMPLE_PINHOLE", 3),
    1: ("PINHOLE", 4),
    2: ("SIMPLE_RADIAL", 4),
    3: ("RADIAL", 5),
    4: ("OPENCV", 8),
    5: ("OPENCV_FISHEYE", 8),
    6: ("FULL_OPENCV", 12),
    7: ("FOV", 5),
    8: ("SIMPLE_RADIAL_FISHEYE", 4),
    9: ("RADIAL_FISHEYE", 5),
    10: ("THIN_PRISM_FISHEYE", 12),
}


# ─────────────────────────────────────────────
# COLMAP Parsers
# ─────────────────────────────────────────────
def extract_intrinsics(model: str, params: List[float]) -> Tuple[float, float, float, float]:
    """Extract (fx, fy, cx, cy) from COLMAP camera params.

    Distortion coefficients are ignored (poses are used as exact priors).
    """
    if model in ("SIMPLE_PINHOLE", "SIMPLE_RADIAL", "RADIAL",
                 "SIMPLE_RADIAL_FISHEYE", "RADIAL_FISHEYE", "FOV"):
        f, cx, cy = params[0], params[1], params[2]
        return f, f, cx, cy
    if model in ("PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV",
                 "THIN_PRISM_FISHEYE"):
        fx, fy, cx, cy = params[0], params[1], params[2], params[3]
        return fx, fy, cx, cy
    raise ValueError(f"Unsupported COLMAP camera model: {model}")


def read_cameras_txt(path: Path) -> Dict[int, Dict[str, Any]]:
    """Parse COLMAP cameras.txt → {camera_id: {model, width, height, params}}."""
    cameras: Dict[int, Dict[str, Any]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            cam_id = int(parts[0])
            cameras[cam_id] = {
                "model": parts[1],
                "width": int(parts[2]),
                "height": int(parts[3]),
                "params": [float(p) for p in parts[4:]],
            }
    return cameras


def read_cameras_bin(path: Path) -> Dict[int, Dict[str, Any]]:
    """Parse COLMAP cameras.bin → {camera_id: {model, width, height, params}}."""
    cameras: Dict[int, Dict[str, Any]] = {}
    with open(path, "rb") as f:
        num_cameras = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_cameras):
            cam_id, model_id = struct.unpack("<ii", f.read(8))
            width, height = struct.unpack("<QQ", f.read(16))
            if model_id not in COLMAP_CAMERA_MODELS:
                raise ValueError(f"Unknown COLMAP camera model id: {model_id}")
            model_name, num_params = COLMAP_CAMERA_MODELS[model_id]
            params = list(struct.unpack(f"<{num_params}d", f.read(8 * num_params)))
            cameras[cam_id] = {
                "model": model_name,
                "width": int(width),
                "height": int(height),
                "params": params,
            }
    return cameras


def read_images_txt(path: Path) -> List[Dict[str, Any]]:
    """Parse COLMAP images.txt → list of {image_id, qvec, tvec, camera_id, name}.

    Reads line by line (the POINTS2D lines can make this file huge) and
    keeps only the pose lines: non-comment lines alternate
    pose line / points2D line.
    """
    images: List[Dict[str, Any]] = []
    expect_pose = True
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if expect_pose:
                # The POINTS2D line may be empty, but a pose line never is
                if not stripped:
                    continue
                parts = stripped.split()
                images.append({
                    "image_id": int(parts[0]),
                    "qvec": np.array([float(v) for v in parts[1:5]]),  # qw qx qy qz
                    "tvec": np.array([float(v) for v in parts[5:8]]),
                    "camera_id": int(parts[8]),
                    "name": " ".join(parts[9:]),
                })
                expect_pose = False
            else:
                expect_pose = True
    return images


def read_images_bin(path: Path) -> List[Dict[str, Any]]:
    """Parse COLMAP images.bin → list of {image_id, qvec, tvec, camera_id, name}."""
    images: List[Dict[str, Any]] = []
    with open(path, "rb") as f:
        num_images = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_images):
            image_id = struct.unpack("<i", f.read(4))[0]
            qvec = np.array(struct.unpack("<4d", f.read(32)))
            tvec = np.array(struct.unpack("<3d", f.read(24)))
            camera_id = struct.unpack("<i", f.read(4))[0]
            name_bytes = b""
            while True:
                c = f.read(1)
                if c == b"\x00" or not c:
                    break
                name_bytes += c
            num_points2d = struct.unpack("<Q", f.read(8))[0]
            f.seek(24 * num_points2d, os.SEEK_CUR)  # skip (x, y, point3D_id)
            images.append({
                "image_id": image_id,
                "qvec": qvec,
                "tvec": tvec,
                "camera_id": camera_id,
                "name": name_bytes.decode("utf-8", errors="replace"),
            })
    return images


def find_sparse_dir(root: Path) -> Optional[Path]:
    """Locate the COLMAP model folder under root (sparse/, sparse/0/, or root)."""
    for cand in (root / "sparse", root / "sparse" / "0", root):
        if (cand / "cameras.txt").is_file() or (cand / "cameras.bin").is_file():
            return cand
    return None


def load_colmap_model(sparse_dir: Path, log_callback) -> Tuple[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]:
    """Load cameras and images from a COLMAP model folder (.txt preferred)."""
    cameras_txt = sparse_dir / "cameras.txt"
    cameras_bin = sparse_dir / "cameras.bin"
    if cameras_txt.is_file():
        log_callback(f"📄 Loading {cameras_txt.name} (text)")
        cameras = read_cameras_txt(cameras_txt)
    elif cameras_bin.is_file():
        log_callback(f"📄 Loading {cameras_bin.name} (binary)")
        cameras = read_cameras_bin(cameras_bin)
    else:
        raise FileNotFoundError("cameras.txt / cameras.bin not found")

    images_txt = sparse_dir / "images.txt"
    images_bin = sparse_dir / "images.bin"
    if images_txt.is_file():
        log_callback(f"📄 Loading {images_txt.name} (text, poses only)")
        images = read_images_txt(images_txt)
    elif images_bin.is_file():
        log_callback(f"📄 Loading {images_bin.name} (binary, poses only)")
        images = read_images_bin(images_bin)
    else:
        raise FileNotFoundError("images.txt / images.bin not found")

    return cameras, images


# ─────────────────────────────────────────────
# Rotation Utilities
# ─────────────────────────────────────────────
def quat_to_rotmat(qvec: np.ndarray) -> np.ndarray:
    """Convert COLMAP quaternion (qw, qx, qy, qz) to a 3x3 rotation matrix."""
    qw, qx, qy, qz = qvec / np.linalg.norm(qvec)
    return np.array([
        [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qw * qz), 2 * (qx * qz + qw * qy)],
        [2 * (qx * qy + qw * qz), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qw * qx)],
        [2 * (qx * qz - qw * qy), 2 * (qy * qz + qw * qx), 1 - 2 * (qx * qx + qy * qy)],
    ])


# ─────────────────────────────────────────────
# XMP Generation
# ─────────────────────────────────────────────
def build_xmp_content(
    R_wc: np.ndarray,
    C: np.ndarray,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
    width: int,
    height: int,
) -> str:
    """Build RealityScan XMP text for one image.

    R_wc: world-to-camera rotation (COLMAP convention)
    C:    camera center in world coordinates
    Applies the same axis remap as spheresfm_to_realityscan.py:
    columns [X, Z, -Y], position [Cx, Cz, -Cy].
    """
    R_rc = np.zeros((3, 3), dtype=np.float64)
    R_rc[:, 0] = R_wc[:, 0]
    R_rc[:, 1] = R_wc[:, 2]
    R_rc[:, 2] = -R_wc[:, 1]
    rot_str = " ".join(f"{x}" for x in R_rc.flatten())
    pos_str = f"{C[0]} {C[2]} {-C[1]}"

    focal_35mm = 36.0 * fx / width
    aspect = fy / fx
    ppu = (cx - width / 2.0) / width
    ppv = (cy - height / 2.0) / height

    return f"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xcr:Version="3"
       xmlns:xcr="http://www.capturingreality.com/ns/xcr/1.1#"
       xcr:CalibrationPrior="exact"
       xcr:DistortionModel="perspective"
       xcr:FocalLength35mm="{focal_35mm}" xcr:Skew="0" xcr:AspectRatio="{aspect}"
       xcr:PrincipalPointU="{ppu}" xcr:PrincipalPointV="{ppv}"
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


# ─────────────────────────────────────────────
# Main Conversion Process
# ─────────────────────────────────────────────
def execute_conversion(
    input_dir: str,
    output_dir: str,
    log_callback,
    progress_callback,
    done_callback,
    cancel_event: threading.Event = None,
    cancel_cleanup_callback=None,
):
    """Run the conversion in a background thread."""
    try:
        root = Path(input_dir)

        # ── 1. Locate input folders ──
        sparse_dir = find_sparse_dir(root)
        if sparse_dir is None:
            log_callback("⚠️ COLMAP model not found (cameras.txt / cameras.bin).")
            log_callback("   Expected under <input>/sparse/ or <input>/sparse/0/.")
            return
        log_callback(f"📁 COLMAP model : {sparse_dir}")

        images_dir = root / "images"
        if not images_dir.is_dir():
            log_callback(f"⚠️ Image folder not found: {images_dir}")
            return
        log_callback(f"📁 Images folder: {images_dir}")

        masks_dir = root / "masks"
        mask_lookup: Dict[str, Path] = {}
        if masks_dir.is_dir():
            for mf in masks_dir.iterdir():
                if mf.is_file() and mf.suffix.lower() in SUPPORTED_EXTENSIONS:
                    stem = mf.stem
                    if stem.endswith(".mask"):
                        stem = stem[:-5]
                    mask_lookup[stem] = mf
            log_callback(f"📁 Masks folder : {masks_dir} ({len(mask_lookup)} masks)")
        else:
            log_callback("📁 Masks folder : (none)")

        # ── 2. Load COLMAP model ──
        cameras, images = load_colmap_model(sparse_dir, log_callback)
        log_callback(f"  Cameras: {len(cameras)}")
        log_callback(f"  Images : {len(images)}")

        # ── 3. Resolve image files & output names ──
        entries: List[Dict[str, Any]] = []
        used_names: Dict[str, int] = {}
        num_missing = 0
        num_detail = 0

        for img in sorted(images, key=lambda x: x["image_id"]):
            rel_name = img["name"].replace("\\", "/")
            src_path = images_dir / rel_name
            if not src_path.is_file():
                num_missing += 1
                if num_missing <= 5:
                    log_callback(f"  ⚠️ Missing image file, skipped: {rel_name}")
                continue

            if img["camera_id"] not in cameras:
                log_callback(f"  ⚠️ Unknown camera id {img['camera_id']}, skipped: {rel_name}")
                continue

            is_detail = "/" in rel_name
            if is_detail:
                num_detail += 1

            # Flatten subfolder paths (detail/photos/X.jpg → X.jpg)
            out_name = os.path.basename(rel_name)
            if out_name in used_names:
                out_name = f"detail_{out_name}"
            used_names[out_name] = 1

            mask_path = mask_lookup.get(src_path.stem) if not is_detail else None

            entries.append({
                "src": src_path,
                "mask": mask_path,
                "out_name": out_name,
                "camera_id": img["camera_id"],
                "qvec": img["qvec"],
                "tvec": img["tvec"],
            })

        if not entries:
            log_callback("⚠️ No valid images found. Check that sparse/ and images/ match.")
            return

        num_masks = sum(1 for e in entries if e["mask"] is not None)

        log_callback(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log_callback(f"📐 Summary:")
        log_callback(f"   Valid images   : {len(entries)}")
        log_callback(f"   Detail images  : {num_detail}")
        log_callback(f"   Masked images  : {num_masks}")
        if num_missing > 0:
            log_callback(f"   Missing files  : {num_missing}")
        for cam_id in sorted(cameras.keys()):
            cam = cameras[cam_id]
            n_use = sum(1 for e in entries if e["camera_id"] == cam_id)
            if n_use > 0:
                log_callback(
                    f"   Camera {cam_id}: {cam['model']} {cam['width']}x{cam['height']} ({n_use} images)"
                )
        log_callback(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log_callback("")

        # ── 4. Create output directories ──
        out_root = Path(output_dir)
        out_root.mkdir(parents=True, exist_ok=True)
        out_img_dir = out_root / "images"
        out_img_dir.mkdir(parents=True, exist_ok=True)
        out_mask_dir = out_root / "masks"
        if num_masks > 0:
            out_mask_dir.mkdir(parents=True, exist_ok=True)
        combined_dir = out_root / "all"
        combined_dir.mkdir(parents=True, exist_ok=True)

        # ── 5. Copy images/masks and write XMP ──
        total_work = len(entries)
        completed = 0
        log_callback(f"🔄 Converting {total_work} images...")

        for entry in entries:
            if cancel_event is not None and cancel_event.is_set():
                log_callback("")
                log_callback("⚠️ Processing was cancelled.")
                if cancel_cleanup_callback is not None:
                    cancel_cleanup_callback(str(out_root))
                return

            out_name = entry["out_name"]

            # images/
            img_out = out_img_dir / out_name
            shutil.copy2(str(entry["src"]), str(img_out))
            shutil.copy2(str(entry["src"]), str(combined_dir / out_name))

            # masks/ (RealityScan naming: <image filename>.mask.png)
            if entry["mask"] is not None:
                mask_out_name = f"{out_name}.mask.png"
                shutil.copy2(str(entry["mask"]), str(out_mask_dir / mask_out_name))
                shutil.copy2(str(entry["mask"]), str(combined_dir / mask_out_name))

            # XMP (all/ only)
            cam = cameras[entry["camera_id"]]
            fx, fy, cx, cy = extract_intrinsics(cam["model"], cam["params"])
            R_wc = quat_to_rotmat(entry["qvec"])
            C = -R_wc.T @ entry["tvec"]
            xmp_content = build_xmp_content(
                R_wc, C, fx, fy, cx, cy, cam["width"], cam["height"]
            )
            xmp_path = combined_dir / f"{Path(out_name).stem}.xmp"
            with open(xmp_path, "w", encoding="utf-8") as xf:
                xf.write(xmp_content)

            completed += 1
            progress_callback(completed, total_work)

        # ── 6. Completion summary ──
        log_callback("")
        log_callback(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log_callback(f"🎉 Conversion complete!")
        log_callback(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        log_callback(f"  Images  : {len(entries)}")
        log_callback(f"  Masks   : {num_masks}")
        log_callback(f"  XMP     : {len(entries)}")
        log_callback(f"  Output  : {output_dir}")
        log_callback("")
        log_callback("  → Load the 'all' folder into RealityScan.")

    except Exception as e:
        log_callback(f"❌ An error occurred: {e}")
        import traceback
        log_callback(traceback.format_exc())
    finally:
        done_callback()


# ─────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────
class ColmapToRSApp:
    """Tkinter-based GUI application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("COLMAP (LichtFeld Studio) → RealityScan Converter")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        self.input_var: tk.StringVar = None  # type: ignore
        self.output_var: tk.StringVar = None  # type: ignore
        self.run_button: ttk.Button = None  # type: ignore
        self.cancel_button: ttk.Button = None  # type: ignore
        self._cancel_event: threading.Event = None  # type: ignore
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
        # Input train-data folder
        ttk.Label(files_frame, text="Input folder (train data):").grid(
            row=row, column=0, sticky=tk.W, pady=3
        )
        self.input_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.input_var, width=45).grid(
            row=row, column=1, sticky=tk.EW, padx=5
        )
        ttk.Button(files_frame, text="📁", width=3,
                   command=lambda: self._browse_folder(self.input_var, "Select Train Data Folder")
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

        # === Run button + progress bar ===
        action_frame = ttk.Frame(self.root, padding=(10, 5))
        action_frame.pack(fill=tk.X)

        self.run_button = ttk.Button(
            action_frame, text="▶ Start Conversion", command=self._start_conversion
        )
        self.run_button.pack(side=tk.LEFT)

        self.cancel_button = ttk.Button(
            action_frame, text="⏹ Cancel", command=self._cancel_conversion, state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(5, 0))

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

    # ── Folder browse ──
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
            self.cancel_button.config(state=tk.DISABLED)
        self.root.after(0, _finish)

    # ── Cancel callback ──
    def _cancel_conversion(self):
        if self._cancel_event is not None:
            self._cancel_event.set()
            self.cancel_button.config(state=tk.DISABLED)

    # ── Cancel cleanup callback (called from background thread) ──
    def _on_cancel_cleanup(self, out_root_str: str):
        def _ask():
            if messagebox.askyesno(
                "Delete Output?",
                f"Processing was cancelled.\nDelete the contents of the output folder?\n\n{out_root_str}",
            ):
                out_root = Path(out_root_str)
                for sub in ["images", "masks", "all"]:
                    d = out_root / sub
                    if d.exists():
                        shutil.rmtree(str(d))
                self._log("🗑️ Output folder contents deleted.")
        self.root.after(0, _ask)

    # ── Validate & start conversion ──
    def _start_conversion(self):
        input_dir = self.input_var.get().strip()
        output_dir = self.output_var.get().strip()

        if not input_dir:
            messagebox.showwarning("Input Error", "Please specify the input (train data) folder.")
            return
        if not os.path.isdir(input_dir):
            messagebox.showwarning("Input Error", f"Input folder not found:\n{input_dir}")
            return
        if not output_dir:
            messagebox.showwarning("Input Error", "Please specify the output folder.")
            return

        # Clear log & disable button
        self.log_text.delete("1.0", tk.END)
        self.progress_var.set(0)
        self.progress_label.config(text="0 / 0")
        self.run_button.config(state=tk.DISABLED)
        self._cancel_event = threading.Event()
        self.cancel_button.config(state=tk.NORMAL)

        thread = threading.Thread(
            target=execute_conversion,
            args=(
                input_dir,
                output_dir,
                self._log,
                self._update_progress,
                self._on_done,
                self._cancel_event,
                self._on_cancel_cleanup,
            ),
            daemon=True,
        )
        thread.start()


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
def main():
    root = tk.Tk()
    ColmapToRSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
