"""
generate_12_poses.py – Extração e geração em lote das 12 poses humanas reais em 1280x720 (HD 16:9).

Ordem personalizada por progressão de dificuldade:
1. Vitoria (Fácil)
2. T-Pose Inclinada (Fácil)
3. Super-Herói (Fácil)
4. O Pensador (Fácil)
5. O Grito (Médio)
6. Egípcio (Médio)
7. Disco Fever (Médio)
8. Surfista (Médio)
9. O Diamante (Difícil)
10. Esquiva Matrix (Difícil)
11. Contorcionista (Difícil)
12. Karatê Kid (Difícil - Desafio Final)
"""

import os
import sys

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import cv2
import numpy as np
from src.config import FRAME_W, FRAME_H, DILATION_PX

TARGET_GROUND_Y = 714
STAND_SCALE = 618.0 / 212.0  # Escala para altura anatômica padrão

POSES_INFO = [
    # ── NÍVEL FÁCIL (1 a 4) ──
    {"name": "Vitoria", "diff": "FACIL", "desc": "Bracos abertos em V e postura confiante", "slug": "vitoria", "grid": (0, 0)},
    {"name": "T-Pose Inclinada", "diff": "FACIL", "desc": "Bracos em cruz inclinados lateralmente", "slug": "t_pose_inclinada", "grid": (0, 1)},
    {"name": "Super-Heroi", "diff": "FACIL", "desc": "Maos na cintura e peito aberto", "slug": "super_heroi", "grid": (0, 2)},
    {"name": "O Pensador", "diff": "FACIL", "desc": "Mao apoiada no queixo, tronco ereto", "slug": "o_pensador", "grid": (0, 3)},

    # ── NÍVEL MÉDIO (5 a 8) ──
    {"name": "O Grito", "diff": "MEDIO", "desc": "Maos nas bochechas e pernas em zigue-zague", "slug": "o_grito", "grid": (2, 3)},
    {"name": "Egipcio", "diff": "MEDIO", "desc": "Bracos em angulo reto estilo hieroglifo", "slug": "egipcio", "grid": (1, 2)},
    {"name": "Disco Fever", "diff": "MEDIO", "desc": "Dedo apontando para o alto na diagonal", "slug": "disco_fever", "grid": (2, 0)},
    {"name": "Surfista", "diff": "MEDIO", "desc": "Agachamento atletico aberto", "slug": "surfista", "grid": (1, 3)},

    # ── NÍVEL DIFÍCIL (9 a 12) ──
    {"name": "O Diamante", "diff": "DIFICIL", "desc": "Maos unidas sobre a cabeca e joelhos em plie", "slug": "o_diamante", "grid": (2, 1)},
    {"name": "Esquiva Matrix", "diff": "DIFICIL", "desc": "Tronco esquivado para o lado", "slug": "esquiva_matrix", "grid": (1, 1)},
    {"name": "Contorcionista", "diff": "DIFICIL", "desc": "Braco por cima da cabeca e pernas tortas", "slug": "contorcionista", "grid": (2, 2)},
    {"name": "Karate Kid", "diff": "DIFICIL", "desc": "Equilibrio supremo em uma perna so", "slug": "karate_kid", "grid": (1, 0)},
]


def extract_pose_from_cell(cell_img: np.ndarray) -> np.ndarray:
    """Extrai a silhueta da pessoa de uma célula do grid, descartando o texto e as bordas."""
    bin_cell = (cell_img < 128).astype(np.uint8) * 255

    n, labels, stats, centroids = cv2.connectedComponentsWithStats(bin_cell)
    if n <= 1:
        return np.zeros((100, 100), dtype=np.uint8)

    sorted_indices = np.argsort(stats[1:, 4])[::-1] + 1
    largest_comp = sorted_indices[0]

    body = (labels == largest_comp).astype(np.uint8) * 255
    bx, by, bw, bh = stats[largest_comp, :4]
    return body[by:by + bh, bx:bx + bw]


def build_stage_from_silhouette(cropped_silhouette: np.ndarray) -> np.ndarray:
    """Redimensiona e posiciona a silhueta humana no canvas 1280x720 com pés no chão."""
    bh, bw = cropped_silhouette.shape[:2]

    new_w = int(round(bw * STAND_SCALE))
    new_h = int(round(bh * STAND_SCALE))

    scaled_float = cv2.resize(
        cropped_silhouette.astype(np.float32),
        (new_w, new_h),
        interpolation=cv2.INTER_LANCZOS4
    )

    blurred = cv2.GaussianBlur(scaled_float, (5, 5), 0)
    scaled_bin = (blurred > 120).astype(np.uint8) * 255

    canvas = np.zeros((FRAME_H, FRAME_W), dtype=np.uint8)
    dest_y2 = min(FRAME_H, TARGET_GROUND_Y)
    dest_y1 = max(0, dest_y2 - new_h)
    actual_h = dest_y2 - dest_y1

    dest_x1 = max(0, (FRAME_W // 2) - (new_w // 2))
    dest_x2 = min(FRAME_W, dest_x1 + new_w)
    actual_w = dest_x2 - dest_x1

    canvas[dest_y1:dest_y2, dest_x1:dest_x2] = scaled_bin[:actual_h, :actual_w]
    return canvas


def generate_all_12_poses() -> dict[str, np.ndarray]:
    """Gera todas as 12 poses a partir do spritesheet humano real na ordem customizada."""
    spritesheet_path = os.path.join(_PROJECT_ROOT, "assets", "poses_spritesheet.png")
    if not os.path.exists(spritesheet_path):
        raise FileNotFoundError(f"Spritesheet de poses nao encontrado em {spritesheet_path}")

    sheet = cv2.imread(spritesheet_path, cv2.IMREAD_GRAYSCALE)
    poses = {}

    for idx, info in enumerate(POSES_INFO):
        r, c = info["grid"]
        x1 = c * 256 + 3
        x2 = (c + 1) * 256 - 3
        y1 = r * 255 + 3
        y2 = (r + 1) * 255 - 3

        cell = sheet[y1:y2, x1:x2]
        cropped = extract_pose_from_cell(cell)
        stage_mask = build_stage_from_silhouette(cropped)

        pose_key = f"pose_{idx + 1:02d}_{info['slug']}"
        poses[pose_key] = stage_mask

    return poses


def get_pose_info(idx: int) -> dict:
    """Retorna os metadados da pose para exibição na interface."""
    return POSES_INFO[idx % len(POSES_INFO)]


def main():
    photos_dir = os.path.join(_PROJECT_ROOT, "assets", "photos")
    stages_dir = os.path.join(_PROJECT_ROOT, "assets", "stages")

    os.makedirs(photos_dir, exist_ok=True)
    os.makedirs(stages_dir, exist_ok=True)

    print("[*] Extraindo e gerando as 12 poses na nova ordem de dificuldade...")
    poses = generate_all_12_poses()

    dilation_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (DILATION_PX, DILATION_PX))
    previews = []

    for idx, (name, mask) in enumerate(poses.items(), start=1):
        # 1. Foto visual: silhueta preta em fundo branco puro
        visual_img = cv2.bitwise_not(mask)
        photo_filename = f"{name}.png"
        photo_path = os.path.join(photos_dir, photo_filename)
        cv2.imwrite(photo_path, visual_img)

        # 2. Máscara do jogo: dilatada com DILATION_PX para tolerância do buraco
        game_mask = cv2.dilate(mask, dilation_kernel, iterations=1)
        stage_filename = f"stage_{idx:02d}.png"
        stage_path = os.path.join(stages_dir, stage_filename)
        cv2.imwrite(stage_path, game_mask)

        info = POSES_INFO[idx - 1]
        print(f"  [OK] Fase {idx:02d}: {info['name']} [{info['diff']}] -> {stage_filename}")

        previews.append(cv2.resize(mask, (320, 180)))

    # Atualiza o mosaico visual de todas as poses na nova ordem
    row1 = np.hstack(previews[0:4])
    row2 = np.hstack(previews[4:8])
    row3 = np.hstack(previews[8:12])
    mosaic = np.vstack([row1, row2, row3])
    preview_path = os.path.join(_PROJECT_ROOT, "assets", "preview_todas_poses.png")
    cv2.imwrite(preview_path, mosaic)

    print(f"\n[SUCESSO] 12 fases atualizadas com sucesso na nova ordem em {stages_dir}!")


if __name__ == "__main__":
    main()
