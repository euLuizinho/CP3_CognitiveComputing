"""
Módulo principal do jogo Muro Humano (Hole in the Wall) - Widescreen HD 16:9.

Controla o loop do jogo, estados (Start, Prepare/Calibrate, Countdown, Wall 3D, Result, Game Over),
velocidade dinâmica balanceada por dificuldade e miniatura guia da silhueta.
"""

import time
import cv2
import numpy as np

from src.config import (
    FRAME_W,
    FRAME_H,
    MAX_LIVES,
    OVERLAP_THRESHOLD,
    COUNTDOWN_SECONDS,
    RESULT_DISPLAY_SECONDS,
    PREPARE_SECONDS,
    WALL_THEMES,
    COLOR_GREEN,
    COLOR_RED,
    get_approach_duration,
)
from src.segmenter import PersonSegmenter
from src.stage_creator import load_stages
from src.walls import get_wall_texture, render_3d_wall
from src.hud import (
    draw_hud,
    draw_prepare_screen,
    draw_pose_preview_thumbnail,
    draw_countdown,
    draw_result_flash,
    draw_game_over,
    draw_start_screen,
)
from scripts.generate_12_poses import get_pose_info
from src.validator import ValidationTracker
from src import sounds


class GameState:
    START = "START"
    PREPARE = "PREPARE"
    COUNTDOWN = "COUNTDOWN"
    WALL_APPROACHING = "WALL_APPROACHING"
    RESULT = "RESULT"
    GAME_OVER = "GAME_OVER"


class MuroHumanoGame:
    """Gerenciador do loop e lógica do jogo Muro Humano."""

    def __init__(self, stages_dir: str, free_play: bool = False, enable_validation: bool = False):
        self.stages_dir = stages_dir
        self.stages = load_stages(stages_dir)
        self.free_play = free_play
        self.enable_validation = enable_validation
        self.validator = ValidationTracker() if enable_validation else None
        self.trial_counter = 0

        if not self.stages:
            print("[Aviso] Nenhuma fase encontrada em assets/stages.")

        self.segmenter = PersonSegmenter()
        sounds.ensure_sounds()

        # Estado do jogo
        self.state = GameState.START
        self.score = 0
        self.lives = MAX_LIVES
        self.current_stage_idx = 0
        self.current_duration = get_approach_duration(0)

        # Temporizadores e animação
        self.state_start_time = 0.0
        self.wall_start_time = 0.0
        self.last_countdown_sec = -1
        self.last_result_passed = False
        self.last_outside_percent = 0.0
        self.current_fit_pct = 100.0
        self.aligned_time = 0.0

        # Métricas de desempenho
        self.fps = 30.0
        self.prev_frame_time = time.time()
        self.is_fullscreen = False

    def reload_stages(self):
        """Recarrega as fases do disco."""
        self.stages = load_stages(self.stages_dir)

    def reset_game(self):
        """Reinicia os dados do jogo para um novo início."""
        self.score = 0
        self.lives = MAX_LIVES
        self.current_stage_idx = 0
        self.current_duration = get_approach_duration(0)
        self.state = GameState.PREPARE
        self.state_start_time = time.time()
        self.last_countdown_sec = -1
        self.aligned_time = 0.0

    def run(self, camera_index: int = 0):
        """Executa o loop principal com a webcam em Widescreen HD 16:9."""
        cap = cv2.VideoCapture(camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

        if not cap.isOpened():
            print(f"[Erro] Nao foi possivel abrir a webcam no indice {camera_index}.")
            return

        window_name = "Muro Humano 3D - Widescreen HD"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, FRAME_W, FRAME_H)

        print("\n==========================================")
        print("  MURO HUMANO 3D INICIADO!")
        print("  Controles:")
        print("    [ESPACO] Iniciar jogo / Avancar preparacao")
        print("    [T]      Alternar Modo Treino (Vidas Infinitas)")
        print("    [F]      Alternar Tela Cheia")
        print("    [R]      Reiniciar apos Game Over")
        print("    [Q]      Sair do jogo")
        print("==========================================\n")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Aviso] Quadro da webcam nao recebido.")
                break

            # Espelha horizontalmente e garante proporção 16:9
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (FRAME_W, FRAME_H))

            # Cálculo de FPS
            now = time.time()
            dt = now - self.prev_frame_time
            self.prev_frame_time = now
            if dt > 0:
                current_fps = 1.0 / dt
                self.fps = 0.9 * self.fps + 0.1 * current_fps

            timestamp_ms = int(now * 1000)

            # Atualizar lógica e renderizar frame
            rendered_frame = self._update_and_render(frame, timestamp_ms, now)

            cv2.imshow(window_name, rendered_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            elif key == ord('t'):
                self.free_play = not self.free_play
                mode_name = "TREINO (VIDAS INFINITAS)" if self.free_play else "ARCADE (3 VIDAS)"
                print(f"[*] Modo alterado para: {mode_name}")
            elif key == ord('f'):
                # Alterna Tela Cheia
                self.is_fullscreen = not self.is_fullscreen
                if self.is_fullscreen:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                else:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(window_name, FRAME_W, FRAME_H)
            elif key == ord(' '):
                if self.state == GameState.START:
                    self.reset_game()
                elif self.state == GameState.PREPARE:
                    # Jogador pronto! Avança imediatamente para o countdown
                    self.state = GameState.COUNTDOWN
                    self.state_start_time = now
                    self.last_countdown_sec = -1
            elif key == ord('r') and self.state == GameState.GAME_OVER:
                self.reset_game()

        cap.release()
        cv2.destroyAllWindows()
        self.segmenter.close()

    def _update_and_render(self, frame: np.ndarray, timestamp_ms: int, now: float) -> np.ndarray:
        """Atualiza a lógica de transição de estados e renderiza o quadro."""
        if not self.stages:
            display = frame.copy()
            cv2.putText(display, "Nenhuma fase encontrada!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            return display

        current_stage_mask = self.stages[self.current_stage_idx % len(self.stages)]
        theme = WALL_THEMES[self.current_stage_idx % len(WALL_THEMES)]
        pose_info = get_pose_info(self.current_stage_idx)

        # ── ESTADO 1: TELA INICIAL ──
        if self.state == GameState.START:
            display = frame.copy()
            draw_start_screen(display, free_play=self.free_play)
            draw_hud(display, self.score, self.lives, self.fps,
                     level=self.current_stage_idx + 1, free_play=self.free_play)
            return display

        # ── ESTADO 2: PREPARAÇÃO / ENCAIXE PRÉVIO ──
        elif self.state == GameState.PREPARE:
            # Segmentação em tempo real do jogador
            player_mask = self.segmenter.segment_frame(frame, timestamp_ms)

            # Cálculo de encaixe em tempo real
            person_pixels = np.count_nonzero(player_mask == 255)
            if person_pixels > 500:
                outside_pixels = np.count_nonzero((player_mask == 255) & (current_stage_mask == 0))
                outside_ratio = outside_pixels / float(person_pixels)
                fit_ratio = 1.0 - outside_ratio
            else:
                fit_ratio = 0.0
            self.current_fit_pct = fit_ratio * 100.0

            # Contagem regressiva da fase de preparação
            elapsed = now - self.state_start_time
            remaining_sec = max(0.0, PREPARE_SECONDS - elapsed)

            # Se o jogador estiver bem encaixado por mais de 1.2s, auto-avança
            if self.current_fit_pct >= 70.0:
                self.aligned_time += (1.0 / max(10, self.fps))
            else:
                self.aligned_time = 0.0

            display = frame.copy()
            draw_prepare_screen(display, current_stage_mask, player_mask,
                                self.current_fit_pct, pose_info, remaining_sec)
            draw_hud(display, self.score, self.lives, self.fps,
                     level=self.current_stage_idx + 1,
                     fit_pct=self.current_fit_pct,
                     diff_name=pose_info.get("diff", ""),
                     free_play=self.free_play)

            # Transição para contagem após o tempo de preparação ou se o jogador já se alinhou
            if elapsed >= PREPARE_SECONDS or self.aligned_time >= 1.2:
                self.state = GameState.COUNTDOWN
                self.state_start_time = now
                self.last_countdown_sec = -1

            return display

        # ── ESTADO 3: CONTAGEM REGRESSIVA ──
        elif self.state == GameState.COUNTDOWN:
            elapsed = now - self.state_start_time
            countdown_val = int(COUNTDOWN_SECONDS - elapsed) + 1

            if countdown_val != self.last_countdown_sec:
                self.last_countdown_sec = countdown_val
                if countdown_val > 0:
                    sounds.play_countdown()
                elif countdown_val == 0:
                    sounds.play_go()

            display = frame.copy()
            draw_hud(display, self.score, self.lives, self.fps,
                     level=self.current_stage_idx + 1,
                     diff_name=pose_info.get("diff", ""),
                     free_play=self.free_play)
            draw_countdown(display, max(0, countdown_val))

            if elapsed >= COUNTDOWN_SECONDS:
                self.state = GameState.WALL_APPROACHING
                self.wall_start_time = time.time()
                self.current_duration = get_approach_duration(self.current_stage_idx)

            return display

        # ── ESTADO 4: PAREDE 3D SE APROXIMANDO ──
        elif self.state == GameState.WALL_APPROACHING:
            elapsed = now - self.wall_start_time
            t = min(elapsed / self.current_duration, 1.0)

            # Segmentação em tempo real do jogador
            player_mask = self.segmenter.segment_frame(frame, timestamp_ms)

            # Cálculo de encaixe em tempo real
            person_pixels = np.count_nonzero(player_mask == 255)
            if person_pixels > 500:
                outside_pixels = np.count_nonzero((player_mask == 255) & (current_stage_mask == 0))
                outside_ratio = outside_pixels / float(person_pixels)
                fit_ratio = 1.0 - outside_ratio
            else:
                fit_ratio = 1.0
            self.current_fit_pct = fit_ratio * 100.0
            is_aligned = (1.0 - fit_ratio) <= OVERLAP_THRESHOLD

            # Textura temática da parede
            wall_texture = get_wall_texture(theme, FRAME_W, FRAME_H, time_offset=elapsed)

            # Renderizar a parede em 3D com neon multicamadas
            display, _ = render_3d_wall(
                webcam_frame=frame,
                stage_mask=current_stage_mask,
                t=t,
                wall_texture=wall_texture,
                time_offset=elapsed,
                is_player_aligned=is_aligned,
            )

            # Miniatura da pose alvo no canto superior direito para o jogador ter referência clara
            draw_pose_preview_thumbnail(display, current_stage_mask, pose_info)

            # Barra inferior de tempo até o impacto
            bar_w = int(FRAME_W * (1.0 - t))
            bar_color = COLOR_GREEN if is_aligned else (0, 140, 255)
            cv2.rectangle(display, (0, FRAME_H - 8), (bar_w, FRAME_H), bar_color, -1)

            draw_hud(display, self.score, self.lives, self.fps,
                     level=self.current_stage_idx + 1,
                     fit_pct=self.current_fit_pct,
                     diff_name=pose_info.get("diff", ""),
                     free_play=self.free_play)

            # Momento do impacto!
            if t >= 1.0:
                self._judge_attempt(player_mask, current_stage_mask)
                self.state = GameState.RESULT
                self.state_start_time = now

            return display

        # ── ESTADO 5: RESULTADO DO IMPACTO ──
        elif self.state == GameState.RESULT:
            display = frame.copy()
            draw_result_flash(display, self.last_result_passed, free_play=self.free_play)
            draw_hud(display, self.score, self.lives, self.fps,
                     level=self.current_stage_idx + 1,
                     fit_pct=self.current_fit_pct,
                     diff_name=pose_info.get("diff", ""),
                     free_play=self.free_play)

            msg = f"Corpo fora: {self.last_outside_percent:.1f}% (limite maximo: {OVERLAP_THRESHOLD * 100:.0f}%)"
            cv2.putText(display, msg, (FRAME_W // 2 - 250, FRAME_H // 2 + 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)

            if now - self.state_start_time >= RESULT_DISPLAY_SECONDS:
                if (not self.free_play) and self.lives <= 0:
                    self.state = GameState.GAME_OVER
                    sounds.play_splash()
                    sounds.play_gameover()
                else:
                    self.current_stage_idx += 1
                    # Próxima fase: volta para a fase de preparação da nova pose!
                    self.state = GameState.PREPARE
                    self.state_start_time = now
                    self.aligned_time = 0.0

            return display

        # ── ESTADO 6: GAME OVER ──
        elif self.state == GameState.GAME_OVER:
            display = frame.copy()
            draw_game_over(display, self.score)
            return display

        return frame

    def _judge_attempt(self, player_mask: np.ndarray, stage_mask: np.ndarray):
        """Calcula quanto do corpo ficou fora do buraco e define aprovação."""
        person_pixels = np.count_nonzero(player_mask == 255)

        if person_pixels < 500:
            outside_ratio = 1.0
        else:
            outside_pixels = np.count_nonzero((player_mask == 255) & (stage_mask == 0))
            outside_ratio = outside_pixels / float(person_pixels)

        self.last_outside_percent = outside_ratio * 100.0
        passed = outside_ratio <= OVERLAP_THRESHOLD
        self.last_result_passed = passed

        if passed:
            self.score += 100 * (self.current_stage_idx + 1)
            sounds.play_success()
        else:
            if not self.free_play:
                self.lives -= 1
            sounds.play_fail()

        if self.enable_validation and self.validator is not None:
            self.trial_counter += 1
            self.validator.log_trial(
                trial_id=self.trial_counter,
                stage_idx=self.current_stage_idx,
                outside_pct=self.last_outside_percent,
                game_passed=passed,
                human_passed=passed,
                avg_fps=self.fps,
                notes=f"Modo {'Treino' if self.free_play else 'Arcade'}"
            )
