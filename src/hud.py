"""
hud.py - Módulo de renderização do HUD (Heads-Up Display) em HD 1280x720.

Renderiza elementos de interface modernos:
Score, Vidas, Nível, Dificuldade, FPS, Barra de Encaixe, Miniatura Alvo (Thumbnail),
Tela de Preparação/Encaixe Prévio, Contagem e Game Over.
"""

import cv2
import numpy as np

from src.config import (
    FRAME_W,
    FRAME_H,
    COLOR_WHITE,
    COLOR_RED,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_HEART,
    COLOR_BLACK,
    COLOR_CYAN,
    MAX_LIVES,
)

_FONT = cv2.FONT_HERSHEY_SIMPLEX


def _put_text_centered(frame, text: str, y: int, color, scale: float = 1.0,
                       thickness: int = 2, shadow: bool = True):
    """Desenha texto horizontalmente centralizado na coordenada y."""
    (tw, th), _ = cv2.getTextSize(text, _FONT, scale, thickness)
    x = (frame.shape[1] - tw) // 2

    if shadow:
        cv2.putText(frame, text, (x + 2, y + 2), _FONT, scale,
                    COLOR_BLACK, thickness + 2, cv2.LINE_AA)

    cv2.putText(frame, text, (x, y), _FONT, scale, color,
                thickness, cv2.LINE_AA)


def draw_hud(frame, score: int, lives: int, fps: float, level: int = 1,
             fit_pct: float = 100.0, diff_name: str = "", free_play: bool = False):
    """Desenha todos os elementos do HUD sobre o frame."""
    h, w = frame.shape[:2]

    # Barra superior semi-transparente para leitura nítida
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 52), (15, 10, 25), -1)
    cv2.addWeighted(overlay, 0.50, frame, 0.50, 0, frame)

    # 1. Score (canto superior esquerdo)
    cv2.putText(frame, f"SCORE: {score}", (25, 36), _FONT, 0.8, COLOR_BLACK, 4, cv2.LINE_AA)
    cv2.putText(frame, f"SCORE: {score}", (25, 36), _FONT, 0.8, COLOR_WHITE, 2, cv2.LINE_AA)

    # 2. Nível e Dificuldade (centro superior)
    lvl_str = f"FASE {level}"
    if diff_name:
        lvl_str += f" - {diff_name}"
    (tw, _), _ = cv2.getTextSize(lvl_str, _FONT, 0.85, 2)
    cv2.putText(frame, lvl_str, (w // 2 - tw // 2 + 2, 38), _FONT, 0.85, COLOR_BLACK, 4, cv2.LINE_AA)
    diff_color = COLOR_GREEN if "FACIL" in diff_name else (COLOR_YELLOW if "MEDIO" in diff_name else (80, 100, 255))
    cv2.putText(frame, lvl_str, (w // 2 - tw // 2, 36), _FONT, 0.85, diff_color, 2, cv2.LINE_AA)

    # 3. FPS (canto superior direito)
    fps_str = f"{fps:.0f} FPS"
    cv2.putText(frame, fps_str, (w - 125, 36), _FONT, 0.65, COLOR_BLACK, 3, cv2.LINE_AA)
    cv2.putText(frame, fps_str, (w - 125, 36), _FONT, 0.65, (200, 200, 200), 1, cv2.LINE_AA)

    # 4. Vidas ou Modo Treino (canto inferior esquerdo)
    if free_play:
        # Modo Treino / Livre (sem limite de vidas)
        cv2.putText(frame, "MODO TREINO (VIDAS INFINITAS)", (25, h - 30), _FONT, 0.65, COLOR_BLACK, 3, cv2.LINE_AA)
        cv2.putText(frame, "MODO TREINO (VIDAS INFINITAS)", (25, h - 30), _FONT, 0.65, COLOR_GREEN, 2, cv2.LINE_AA)
    else:
        for i in range(MAX_LIVES):
            cx = 35 + i * 38
            cy = h - 35
            if i < lives:
                cv2.circle(frame, (cx, cy), 13, COLOR_BLACK, 3, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 12, (60, 60, 255), -1, cv2.LINE_AA)
            else:
                cv2.circle(frame, (cx, cy), 13, (60, 60, 60), 2, cv2.LINE_AA)

    # 5. Medidor de Encaixe em Tempo Real (canto inferior direito)
    meter_w = 220
    meter_h = 16
    mx = w - meter_w - 30
    my = h - 45
    cv2.rectangle(frame, (mx, my), (mx + meter_w, my + meter_h), (25, 25, 25), -1)
    fill_w = int(meter_w * min(1.0, max(0.0, fit_pct / 100.0)))
    bar_color = COLOR_GREEN if fit_pct >= 68.0 else (0, 140, 255)
    cv2.rectangle(frame, (mx, my), (mx + fill_w, my + meter_h), bar_color, -1)
    cv2.rectangle(frame, (mx, my), (mx + meter_w, my + meter_h), COLOR_WHITE, 1)

    meter_text = f"ENCAIXE: {fit_pct:.0f}%"
    cv2.putText(frame, meter_text, (mx, my - 8), _FONT, 0.5, COLOR_WHITE, 1, cv2.LINE_AA)


def draw_prepare_screen(frame, stage_mask: np.ndarray, player_mask: np.ndarray,
                        fit_pct: float, pose_info: dict, remaining_sec: float):
    """Tela de preparação e encaixe prévio: projeta a silhueta alvo na webcam para o jogador se alinhar."""
    h, w = frame.shape[:2]

    # 1. Overlay da silhueta alvo em ciano suave
    overlay = frame.copy()
    hole_color = np.zeros_like(frame)
    hole_color[stage_mask == 255] = (220, 180, 20)  # Ciano/dourado brilhante
    cv2.addWeighted(hole_color, 0.32, overlay, 1.0, 0, overlay)

    # Contorno neon duplo da silhueta alvo
    target_contours, _ = cv2.findContours(stage_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, target_contours, -1, (255, 220, 0), 4, cv2.LINE_AA)
    cv2.drawContours(overlay, target_contours, -1, (255, 255, 255), 1, cv2.LINE_AA)

    # 2. Contorno do jogador em tempo real (verde se encaixado, laranja/vermelho se fora)
    if player_mask is not None:
        player_contours, _ = cv2.findContours(player_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        player_color = COLOR_GREEN if fit_pct >= 68.0 else (0, 140, 255)
        cv2.drawContours(overlay, player_contours, -1, player_color, 2, cv2.LINE_AA)

    frame[:] = overlay

    # 3. Linha guia do chão com indicador de pés
    ground_y = 716
    cv2.line(frame, (100, ground_y), (w - 100, ground_y), (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "CHAO / POSICAO DOS PES", (w // 2 - 110, ground_y - 8),
                _FONT, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

    # 4. Banner superior com informações da pose
    top_bar = frame.copy()
    cv2.rectangle(top_bar, (w // 2 - 380, 60), (w // 2 + 380, 140), (15, 10, 25), -1)
    cv2.addWeighted(top_bar, 0.75, frame, 0.25, 0, frame)
    cv2.rectangle(frame, (w // 2 - 380, 60), (w // 2 + 380, 140), COLOR_CYAN, 1)

    pose_name = pose_info.get("name", "Pose")
    pose_diff = pose_info.get("diff", "")
    pose_desc = pose_info.get("desc", "")

    title_text = f"PREPARE-SE: {pose_name} ({pose_diff})"
    _put_text_centered(frame, title_text, 92, COLOR_YELLOW, scale=0.85, thickness=2)
    _put_text_centered(frame, pose_desc, 124, COLOR_WHITE, scale=0.65, thickness=1)

    # 5. Banner inferior com contagem e dica de avanço
    bot_bar = frame.copy()
    cv2.rectangle(bot_bar, (w // 2 - 320, h - 105), (w // 2 + 320, h - 60), (15, 10, 25), -1)
    cv2.addWeighted(bot_bar, 0.75, frame, 0.25, 0, frame)

    if fit_pct >= 68.0:
        msg = f"MUITO BEM! O MURO VEM EM {remaining_sec:.1f}s (ou [ESPACO])"
        _put_text_centered(frame, msg, h - 75, COLOR_GREEN, scale=0.75, thickness=2)
    else:
        msg = f"Encaixe o corpo na silhueta! Inicia em {remaining_sec:.1f}s [ESPACO]"
        _put_text_centered(frame, msg, h - 75, COLOR_WHITE, scale=0.70, thickness=2)


def draw_pose_preview_thumbnail(frame, stage_mask: np.ndarray, pose_info: dict, width: int = 150):
    """Exibe no canto superior direito uma miniatura nítida da pose alvo durante a aproximação."""
    h, w = frame.shape[:2]
    aspect = FRAME_H / FRAME_W
    thumb_h = int(width * aspect)
    thumb_w = width

    x1 = w - thumb_w - 20
    y1 = 60
    x2 = x1 + thumb_w
    y2 = y1 + thumb_h

    # Fundo escuro com borda neon
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (20, 15, 30), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
    cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_CYAN, 1, cv2.LINE_AA)

    # Redimensiona a máscara para a miniatura
    thumb_mask = cv2.resize(stage_mask, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)

    # Pinta a silhueta em ciano brilhante sobre o fundo escuro
    thumb_roi = frame[y1:y2, x1:x2]
    thumb_roi[thumb_mask == 255] = (220, 200, 30)

    # Rótulo da miniatura
    cv2.putText(frame, "ALVO", (x1 + 6, y1 + 16), _FONT, 0.45, COLOR_CYAN, 1, cv2.LINE_AA)
    p_name = pose_info.get("name", "")
    if p_name:
        cv2.putText(frame, p_name[:14], (x1 + 6, y2 - 6), _FONT, 0.38, COLOR_WHITE, 1, cv2.LINE_AA)


def draw_countdown(frame, number: int):
    """Desenha contagem regressiva 2-1-VAI na tela."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

    if number > 0:
        txt = str(number)
        _put_text_centered(frame, txt, FRAME_H // 2 + 50, COLOR_YELLOW, scale=5.0, thickness=10)
    else:
        _put_text_centered(frame, "VAI!", FRAME_H // 2 + 50, COLOR_GREEN, scale=4.5, thickness=9)


def draw_result_flash(frame, passed: bool, free_play: bool = False):
    """Desenha flash de aprovação ou falha."""
    border_color = COLOR_GREEN if passed else COLOR_RED
    cv2.rectangle(frame, (0, 0), (FRAME_W - 1, FRAME_H - 1), border_color, 16)

    overlay = frame.copy()
    cv2.rectangle(overlay, (FRAME_W // 2 - 320, FRAME_H // 2 - 80), (FRAME_W // 2 + 320, FRAME_H // 2 + 80), (10, 10, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    if passed:
        _put_text_centered(frame, "ENCAIXOU PERFEITO!", FRAME_H // 2 - 10, COLOR_GREEN, scale=1.6, thickness=4)
        _put_text_centered(frame, "+ PONTOS!", FRAME_H // 2 + 45, COLOR_YELLOW, scale=1.1, thickness=2)
    else:
        _put_text_centered(frame, "BATEU NA PAREDE!", FRAME_H // 2 - 10, COLOR_RED, scale=1.6, thickness=4)
        sub_text = "MODO TREINO: SEGUE O JOGO!" if free_play else "-1 VIDA"
        sub_color = COLOR_YELLOW if free_play else (100, 100, 255)
        _put_text_centered(frame, sub_text, FRAME_H // 2 + 45, sub_color, scale=1.1, thickness=2)


def draw_game_over(frame, final_score: int):
    """Tela de Game Over com estética arcade."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (10, 5, 20), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    _put_text_centered(frame, "CAIU NA AGUA!", FRAME_H // 2 - 90, COLOR_RED, scale=2.8, thickness=6)
    _put_text_centered(frame, "GAME OVER", FRAME_H // 2 - 20, (180, 180, 255), scale=1.3, thickness=3)
    _put_text_centered(frame, f"Pontuacao Final: {final_score}", FRAME_H // 2 + 50, COLOR_YELLOW, scale=1.4, thickness=3)

    _put_text_centered(frame, "Pressione [R] para Recomecar", FRAME_H // 2 + 130, COLOR_WHITE, scale=0.9, thickness=2)
    _put_text_centered(frame, "Pressione [Q] para Sair", FRAME_H // 2 + 175, (180, 180, 180), scale=0.75, thickness=2)


def draw_start_screen(frame, free_play: bool = False):
    """Tela inicial com instruções e atalhos."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (FRAME_W, FRAME_H), (10, 5, 20), -1)
    cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

    _put_text_centered(frame, "MURO HUMANO 3D", FRAME_H // 2 - 120, COLOR_CYAN, scale=2.4, thickness=5)
    _put_text_centered(frame, "Encaixe seu corpo no buraco da parede antes do impacto!", FRAME_H // 2 - 50, COLOR_WHITE, scale=0.85, thickness=2)

    _put_text_centered(frame, "Pressione [ESPACO] para Jogar", FRAME_H // 2 + 25, COLOR_YELLOW, scale=1.3, thickness=3)

    mode_label = "[T] Modo de Jogo: [TREINO - VIDAS INFINITAS]" if free_play else "[T] Modo de Jogo: [ARCADE - 3 VIDAS]"
    mode_color = COLOR_GREEN if free_play else (100, 150, 255)
    _put_text_centered(frame, mode_label, FRAME_H // 2 + 80, mode_color, scale=0.85, thickness=2)

    _put_text_centered(frame, "[F] Alternar Tela Cheia  |  [Q] Sair", FRAME_H // 2 + 130, (220, 220, 220), scale=0.75, thickness=2)
