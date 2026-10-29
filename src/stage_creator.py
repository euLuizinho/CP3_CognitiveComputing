"""
stage_creator.py – Criação de fases a partir de fotos, silhuetas ou cabine de webcam ao vivo.
"""

import os
import glob
import time
import cv2
import numpy as np

from src.segmenter import PersonSegmenter
from src.config import DILATION_PX, FRAME_W, FRAME_H, COLOR_WHITE, COLOR_YELLOW, COLOR_CYAN, COLOR_GREEN


def create_stage_from_photo(
    segmenter: PersonSegmenter,
    photo_path: str,
    output_path: str,
    dilation_px: int = None,
) -> np.ndarray:
    """Cria uma máscara de fase a partir de uma foto real ou silhueta já desenhada."""
    if dilation_px is None:
        dilation_px = DILATION_PX

    raw_img = cv2.imread(photo_path, cv2.IMREAD_UNCHANGED)
    mask = None

    if raw_img is not None:
        # 1. PNG com canal Alpha (transparência)
        if raw_img.ndim == 3 and raw_img.shape[2] == 4:
            alpha = raw_img[:, :, 3]
            mask = (alpha > 50).astype(np.uint8) * 255

        # 2. Imagem preto e branco
        elif raw_img.ndim == 2 or (raw_img.ndim == 3 and np.all(raw_img[:, :, 0] == raw_img[:, :, 1])):
            gray = raw_img if raw_img.ndim == 2 else raw_img[:, :, 0]
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            corners = [int(binary[0, 0]), int(binary[0, -1]), int(binary[-1, 0]), int(binary[-1, -1])]
            if sum(corners) >= 2 * 255:
                mask = cv2.bitwise_not(binary)
            else:
                mask = binary

    # 3. Foto colorida normal -> MediaPipe AI
    if mask is None:
        mask = segmenter.segment_image(photo_path)

    mask = cv2.resize(mask, (FRAME_W, FRAME_H), interpolation=cv2.INTER_NEAREST)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation_px, dilation_px))
    dilated = cv2.dilate(mask, kernel, iterations=1)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, dilated)
    return dilated


def process_all_photos(photos_dir: str, stages_dir: str) -> list[np.ndarray]:
    """Processa todas as fotos em photos_dir e salva as fases em stages_dir."""
    extensions = ("*.jpg", "*.jpeg", "*.png")
    photo_files = []
    for ext in extensions:
        photo_files.extend(glob.glob(os.path.join(photos_dir, ext)))

    photo_files.sort()
    if not photo_files:
        return []

    os.makedirs(stages_dir, exist_ok=True)
    segmenter = PersonSegmenter()
    masks = []

    print(f"Encontradas {len(photo_files)} fotos em {photos_dir}.")
    for idx, photo_path in enumerate(photo_files, start=1):
        filename = os.path.basename(photo_path)
        out_name = f"stage_{idx:02d}.png"
        out_path = os.path.join(stages_dir, out_name)

        print(f"Processando foto {idx}/{len(photo_files)}: {filename} -> {out_name}...")
        mask = create_stage_from_photo(segmenter, photo_path, out_path)
        masks.append(mask)

    segmenter.close()
    return masks


def load_stages(stages_dir: str) -> list[np.ndarray]:
    """Carrega todas as fases (máscaras PNG) da pasta stages_dir em ordem."""
    stage_files = sorted(glob.glob(os.path.join(stages_dir, "stage_*.png")))
    if not stage_files:
        return []

    masks = []
    for f in stage_files:
        img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            _, binary = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
            if binary.shape[:2] != (FRAME_H, FRAME_W):
                binary = cv2.resize(binary, (FRAME_W, FRAME_H), interpolation=cv2.INTER_NEAREST)
            masks.append(binary)

    return masks


def create_placeholder_stages(stages_dir: str = "assets/stages") -> list[np.ndarray]:
    """Gera o lote das 12 fases anatômicas em assets/stages."""
    from scripts.generate_12_poses import generate_all_12_poses
    os.makedirs(stages_dir, exist_ok=True)
    poses = generate_all_12_poses()
    dilation_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (DILATION_PX, DILATION_PX))
    masks = []
    for idx, (name, mask) in enumerate(poses.items(), start=1):
        dilated = cv2.dilate(mask, dilation_kernel, iterations=1)
        out_path = os.path.join(stages_dir, f"stage_{idx:02d}.png")
        cv2.imwrite(out_path, dilated)
        masks.append(dilated)
    return masks

