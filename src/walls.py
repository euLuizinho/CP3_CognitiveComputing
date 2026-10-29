"""
walls.py – Motor gráfico 3D da parede, túnel em perspectiva e efeitos visuais HD 16:9.

Renderiza uma estrutura 3D realista da parede (com espessura/extrusão de profundidade,
bordas chanfradas, túnel do buraco suavizado e chão em perspectiva com grid arcade),
além da aceleração dramática ao se aproximar do jogador.
"""

import math
import cv2
import numpy as np

from src.config import (
    FRAME_W,
    FRAME_H,
    COLOR_CYAN,
    COLOR_MAGENTA,
    COLOR_YELLOW,
    COLOR_WHITE,
    COLOR_BLACK,
    COLOR_GREEN,
    COLOR_RED,
)

CX = FRAME_W // 2
CY = FRAME_H // 2


# ──────────────────────────────────────────────────────────────────────────────
# Geradores de Textura Temática da Parede (BGR)
# ──────────────────────────────────────────────────────────────────────────────

def make_cyber_neon_wall(w: int, h: int, time_offset: float = 0.0) -> np.ndarray:
    """Textura estilo Cyberpunk / Synthwave com feixes de luz cruzados."""
    xs = np.linspace(0, 12, w, dtype=np.float32)
    ys = np.linspace(0, 8, h, dtype=np.float32)
    xv, yv = np.meshgrid(xs, ys)
    grid = np.sin(xv + time_offset * 2.0) * np.cos(yv + time_offset * 1.5)
    pattern = np.clip((grid + 1.0) * 127.5, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(pattern, cv2.COLORMAP_MAGMA)


def make_wave_wall(w: int, h: int, time_offset: float = 0.0) -> np.ndarray:
    """Interferência ondulatória colorida e dinâmica."""
    xs = np.linspace(0, 5 * math.pi, w, dtype=np.float32)
    ys = np.linspace(0, 3 * math.pi, h, dtype=np.float32)
    xv, yv = np.meshgrid(xs, ys)
    wave1 = np.sin(xv + time_offset * 3.0) * 127.0
    wave2 = np.cos(yv * 0.8 + time_offset * 2.5) * 127.0
    pattern = np.clip(wave1 + wave2 + 127, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(pattern, cv2.COLORMAP_TURBO)


def make_plasma_wall(w: int, h: int, time_offset: float = 0.0) -> np.ndarray:
    """Efeito de plasma radiante hipnótico."""
    xs = np.linspace(-3, 3, w, dtype=np.float32)
    ys = np.linspace(-1.8, 1.8, h, dtype=np.float32)
    xv, yv = np.meshgrid(xs, ys)
    r = np.sqrt(xv**2 + yv**2)
    plasma = np.sin(r * 5.0 - time_offset * 4.0)
    pattern = np.clip((plasma + 1.0) * 127.5, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(pattern, cv2.COLORMAP_PLASMA)


def make_brick_wall(w: int, h: int, brick_w: int = 70, brick_h: int = 35) -> np.ndarray:
    """Muro de tijolos clássico com relevo e profundidade."""
    wall = np.full((h, w, 3), (45, 45, 60), dtype=np.uint8)
    brick_bgr = (40, 60, 180)
    row = 0
    y = 0
    while y < h:
        offset = (brick_w // 2) if (row % 2 == 1) else 0
        x = -offset
        while x < w:
            x1, y1 = max(x + 2, 0), max(y + 2, 0)
            x2, y2 = min(x + brick_w, w), min(y + brick_h, h)
            if x1 < x2 and y1 < y2:
                cv2.rectangle(wall, (x1, y1), (x2, y2), brick_bgr, -1)
                cv2.line(wall, (x1, y1), (x2, y1), (80, 100, 220), 1)
            x += brick_w
        y += brick_h
        row += 1
    return wall


def make_electric_wall(w: int, h: int, time_offset: float = 0.0) -> np.ndarray:
    """Descarga elétrica azul vibrante."""
    xs = np.linspace(0, 10, w, dtype=np.float32)
    ys = np.linspace(0, 6, h, dtype=np.float32)
    xv, yv = np.meshgrid(xs, ys)
    val = np.sin(xv * 2.0 + np.sin(yv + time_offset * 5.0))
    pattern = np.clip((val + 1.0) * 127.5, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(pattern, cv2.COLORMAP_OCEAN)


def make_matrix_green_wall(w: int, h: int, time_offset: float = 0.0) -> np.ndarray:
    """Chuva digital Matrix tecnológica."""
    xs = np.linspace(0, 16, w, dtype=np.float32)
    ys = np.linspace(0, 9, h, dtype=np.float32)
    xv, yv = np.meshgrid(xs, ys)
    noise = np.sin(xv * 3.0) * np.cos(yv * 0.5 - time_offset * 6.0)
    pattern = np.clip((noise + 1.0) * 127.5, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(pattern, cv2.COLORMAP_VIRIDIS)


def get_wall_texture(theme_name: str, w: int, h: int, time_offset: float = 0.0) -> np.ndarray:
    """Retorna textura conforme o tema."""
    generators = {
        "cyber_neon": make_cyber_neon_wall,
        "wave": make_wave_wall,
        "plasma": make_plasma_wall,
        "brick": lambda w, h, t: make_brick_wall(w, h),
        "electric": make_electric_wall,
        "matrix_green": make_matrix_green_wall,
    }
    gen = generators.get(theme_name, make_cyber_neon_wall)
    return gen(w, h, time_offset)


# ──────────────────────────────────────────────────────────────────────────────
# Ambiente 3D: Túnel / Arena de Perspectiva com Grid Neon HD
# ──────────────────────────────────────────────────────────────────────────────

def render_3d_corridor(base_frame: np.ndarray, time_offset: float, intensity: float = 1.0) -> np.ndarray:
    """Desenha um corredor 3D dinâmico ao redor da webcam com piso arcade e linhas de fuga."""
    out = base_frame.copy()

    line_color = (int(70 * intensity), int(25 * intensity), int(90 * intensity))
    neon_color = (int(190 * intensity), int(70 * intensity), int(255 * intensity))

    # Piso com perspectiva e linhas de fuga
    floor_steps = 8
    for i in range(-6, 7):
        bottom_x = CX + i * 140
        cv2.line(out, (CX, CY + 60), (bottom_x, FRAME_H), line_color, 1, cv2.LINE_AA)

    # Teto com perspectiva
    for i in range(-6, 7):
        top_x = CX + i * 140
        cv2.line(out, (CX, CY - 60), (top_x, 0), line_color, 1, cv2.LINE_AA)

    # Grades horizontais animadas no piso (efeito de velocidade avançando para a câmera)
    speed_shift = (time_offset * 4.5) % 1.0
    for k in range(1, floor_steps):
        frac = ((k + speed_shift) / float(floor_steps)) ** 2.2
        y = int(CY + 60 + (FRAME_H - (CY + 60)) * frac)
        if y < FRAME_H:
            span = int(180 + 900 * frac)
            x1 = max(0, CX - span // 2)
            x2 = min(FRAME_W, CX + span // 2)
            alpha_line = int(min(255, 60 + 195 * frac) * intensity)
            c = tuple(int(c_val * alpha_line / 255.0) for c_val in neon_color)
            cv2.line(out, (x1, y), (x2, y), c, 1, cv2.LINE_AA)

    return out


# ──────────────────────────────────────────────────────────────────────────────
# Renderizador da Parede 3D com Espessura e Buraco Vazado HD
# ──────────────────────────────────────────────────────────────────────────────

def render_3d_wall(
    webcam_frame: np.ndarray,
    stage_mask: np.ndarray,
    t: float,
    wall_texture: np.ndarray,
    time_offset: float = 0.0,
    is_player_aligned: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Renderiza a parede 3D completa com extrusão, profundidade e buraco anti-serrilhado.

    Parâmetros:
        webcam_frame: Imagem da webcam (720x1280x3).
        stage_mask: Máscara binária da fase (720x1280, 255 no buraco).
        t: Progresso da aproximação de 0.0 (distante) a 1.0 (impacto).
        wall_texture: Textura temática da parede.
        time_offset: Tempo para animação das luzes.
        is_player_aligned: True se o jogador estiver atualmente dentro do limite do buraco.

    Retorna:
        (rendered_frame, current_scaled_hole_mask): imagem final e a máscara atual do buraco.
    """
    # Curva acelerada de aproximação 3D
    scale_front = 0.18 + 0.82 * (t ** 2.0)
    depth_factor = 0.86 + 0.09 * t
    scale_back = scale_front * depth_factor

    # Dimensões e posições da face frontal
    fw = max(10, int(FRAME_W * scale_front))
    fh = max(10, int(FRAME_H * scale_front))
    fx1 = (FRAME_W - fw) // 2
    fy1 = (FRAME_H - fh) // 2
    fx2 = fx1 + fw
    fy2 = fy1 + fh

    # Dimensões e posições da face traseira (extrusão 3D)
    bw = max(10, int(FRAME_W * scale_back))
    bh = max(10, int(FRAME_H * scale_back))
    bx1 = (FRAME_W - bw) // 2
    by1 = (FRAME_H - bh) // 2
    bx2 = bx1 + bw
    by2 = by1 + bh

    # 1. Base com o corredor 3D em perspectiva
    intensity = min(1.0, 0.4 + 0.6 * t)
    output = render_3d_corridor(webcam_frame, time_offset, intensity)

    # 2. Desenhar as 4 faces externas de extrusão 3D (espessura do bloco sólido)
    color_top = (110, 50, 130)
    color_bottom = (30, 15, 40)
    color_sides = (60, 30, 80)

    pts_top = np.array([[fx1, fy1], [fx2, fy1], [bx2, by1], [bx1, by1]], dtype=np.int32)
    pts_bottom = np.array([[fx1, fy2], [fx2, fy2], [bx2, by2], [bx1, by2]], dtype=np.int32)
    pts_left = np.array([[fx1, fy1], [bx1, by1], [bx1, by2], [fx1, fy2]], dtype=np.int32)
    pts_right = np.array([[fx2, fy1], [bx2, by1], [bx2, by2], [fx2, fy2]], dtype=np.int32)

    cv2.fillPoly(output, [pts_top], color_top, cv2.LINE_AA)
    cv2.fillPoly(output, [pts_bottom], color_bottom, cv2.LINE_AA)
    cv2.fillPoly(output, [pts_left], color_sides, cv2.LINE_AA)
    cv2.fillPoly(output, [pts_right], color_sides, cv2.LINE_AA)

    edge_color = (255, 120, 255)
    cv2.polylines(output, [pts_top, pts_bottom, pts_left, pts_right], isClosed=True, color=edge_color, thickness=1, lineType=cv2.LINE_AA)

    # 3. Preparar a Face Frontal da Parede com redimensionamento anti-serrilhado
    wall_front = cv2.resize(wall_texture, (fw, fh), interpolation=cv2.INTER_LINEAR)

    # Redimensionamento suave da máscara com INTER_LINEAR + thresholding para evitar pixelização
    scaled_hole_float = cv2.resize(stage_mask.astype(np.float32), (fw, fh), interpolation=cv2.INTER_LINEAR)
    scaled_hole = (scaled_hole_float > 120).astype(np.uint8) * 255

    # Recortar o pedaço correspondente da webcam
    wc_crop = webcam_frame[max(0, fy1):min(FRAME_H, fy2), max(0, fx1):min(FRAME_W, fx2)]
    crop_h, crop_w = wc_crop.shape[:2]

    if crop_h > 0 and crop_w > 0:
        wall_front_crop = wall_front[:crop_h, :crop_w]
        hole_crop = scaled_hole[:crop_h, :crop_w]

        # Borda suave nítida (feathering leve sem efeito balão)
        feather = cv2.GaussianBlur(hole_crop, (5, 5), 0)
        alpha = (feather.astype(np.float32) / 255.0)[:, :, np.newaxis]

        blended = (wc_crop.astype(np.float32) * alpha + wall_front_crop.astype(np.float32) * (1.0 - alpha)).astype(np.uint8)

        # 4. Extrusão 3D na borda interna do buraco (chanfro sombreado)
        inner_shadow_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        eroded_hole = cv2.erode(hole_crop, inner_shadow_kernel, iterations=1)
        inner_rim = cv2.subtract(hole_crop, eroded_hole)
        blended[inner_rim == 255] = (blended[inner_rim == 255] * 0.55).astype(np.uint8)

        output[max(0, fy1):min(FRAME_H, fy2), max(0, fx1):min(FRAME_W, fx2)] = blended

    # 5. Máscara completa na tela
    full_hole_mask = np.zeros((FRAME_H, FRAME_W), dtype=np.uint8)
    if crop_h > 0 and crop_w > 0:
        full_hole_mask[max(0, fy1):min(FRAME_H, fy2), max(0, fx1):min(FRAME_W, fx2)] = scaled_hole[:crop_h, :crop_w]

    # 6. Contorno Neon Multicamadas Ultra-Visível (Verde esmeralda se encaixado, Laranja néon se fora)
    contours, _ = cv2.findContours(full_hole_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    glow_pulse = 0.80 + 0.20 * math.sin(time_offset * 12.0)

    if is_player_aligned:
        neon_glow = (int(40 * glow_pulse), int(255 * glow_pulse), int(90 * glow_pulse))   # Verde esmeralda vivo
        outer_glow = (int(10 * glow_pulse), int(130 * glow_pulse), int(45 * glow_pulse))
    else:
        neon_glow = (int(0 * glow_pulse), int(150 * glow_pulse), int(255 * glow_pulse))   # Laranja alerta vivo
        outer_glow = (int(0 * glow_pulse), int(70 * glow_pulse), int(140 * glow_pulse))

    # Glow exterior largo -> Glow médio vibrante -> Filete interno branco
    cv2.drawContours(output, contours, -1, outer_glow, 8, cv2.LINE_AA)
    cv2.drawContours(output, contours, -1, neon_glow, 4, cv2.LINE_AA)
    cv2.drawContours(output, contours, -1, (255, 255, 255), 1, cv2.LINE_AA)

    # 7. Speed lines no impacto (t > 0.65)
    if t > 0.65:
        speed_factor = (t - 0.65) / 0.35
        num_streaks = int(14 * speed_factor)
        for _ in range(num_streaks):
            angle = np.random.uniform(0, 2 * math.pi)
            dist_inner = np.random.uniform(fw * 0.45, fw * 0.72)
            dist_outer = dist_inner + np.random.uniform(50, 140) * speed_factor
            p1 = (int(CX + dist_inner * math.cos(angle)), int(CY + dist_inner * math.sin(angle)))
            p2 = (int(CX + dist_outer * math.cos(angle)), int(CY + dist_outer * math.sin(angle)))
            cv2.line(output, p1, p2, (255, 255, 200), 2, cv2.LINE_AA)

    return output, full_hole_mask
