"""
Configurações globais do jogo Muro Humano.
"""

# ── Resolução Widescreen 16:9 (HD 720p) ──
FRAME_W = 1280
FRAME_H = 720

# ── Dinâmica e Ritmo Balanceado por Dificuldade ──
MAX_LIVES = 3
OVERLAP_THRESHOLD = 0.32          # % máximo do corpo fora do buraco para passar (32%)
DILATION_PX = 18                  # Margem de tolerância anatômica (sem parecer bexiga)
COUNTDOWN_SECONDS = 2.0           # Contagem 2.. 1.. VAI!
RESULT_DISPLAY_SECONDS = 1.0      # Exibição do resultado do impacto
PREPARE_SECONDS = 4.0             # Tempo de preparação/encaixe prévio antes de cada parede

def get_approach_duration(stage_idx: int) -> float:
    """Retorna o tempo de aproximação do muro em segundos conforme a fase/dificuldade."""
    if stage_idx < 4:
        # Nível Fácil (Fases 1 a 4): 4.5s descendo suavemente até 3.9s
        return max(3.8, 4.5 - (stage_idx * 0.2))
    elif stage_idx < 8:
        # Nível Médio (Fases 5 a 8): 3.5s até 3.0s
        return max(2.9, 3.5 - ((stage_idx - 4) * 0.15))
    else:
        # Nível Difícil (Fases 9 a 12): 2.8s até 2.2s
        return max(2.1, 2.8 - ((stage_idx - 8) * 0.18))

# ── Segmentação ──
SEGMENTER_THRESHOLD = 0.5         # Confiança mín. p/ considerar pixel como pessoa
MODEL_FILENAME = "selfie_segmenter.tflite"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"
)

# ── Temas Visuais 3D ──
WALL_THEMES = [
    "cyber_neon",
    "wave",
    "plasma",
    "brick",
    "electric",
    "matrix_green",
]

# ── Cores (BGR) ──
COLOR_GREEN = (0, 255, 100)
COLOR_RED = (0, 0, 255)
COLOR_CYAN = (255, 255, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_YELLOW = (0, 255, 255)
COLOR_HEART = (80, 80, 255)
COLOR_MAGENTA = (255, 0, 200)

# ── Sons ──
BEEP_FREQ_COUNTDOWN = 650
BEEP_FREQ_GO = 1100
BEEP_DURATION_MS = 150
SOUND_ENABLED = True
