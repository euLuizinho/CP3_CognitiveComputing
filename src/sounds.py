"""
Módulo de efeitos sonoros para o jogo Muro Humano.

Gera arquivos WAV simples sinteticamente via wave/struct e toca
sons de forma assíncrona no Windows via winsound.
"""

import os
import wave
import struct
import math
import random
import threading

try:
    import winsound
except ImportError:
    winsound = None

from src.config import (
    SOUND_ENABLED,
    BEEP_FREQ_COUNTDOWN,
    BEEP_FREQ_GO,
    BEEP_DURATION_MS,
)

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SOUNDS_DIR = os.path.join(_PROJECT_ROOT, "assets", "sounds")
_INITIALIZED = False


def _generate_wav(filepath: str, tones: list[tuple[float, int]], volume: float = 0.5, sample_rate: int = 44100):
    """
    Gera um arquivo WAV com uma sequência de tons senoidais ou ruído.
    
    Args:
        filepath: Caminho do arquivo a ser salvo.
        tones: Lista de tuplas (frequência_hz, duração_ms). Se freq == 0, gera ruído branco (ex: splash).
        volume: Volume de 0.0 a 1.0.
        sample_rate: Taxa de amostragem.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    all_samples = []

    for freq, duration_ms in tones:
        num_samples = int(sample_rate * (duration_ms / 1000.0))
        for i in range(num_samples):
            if freq == 0:
                # Ruído branco (ex: splash na água)
                val = (random.random() * 2.0 - 1.0) * volume
            else:
                val = math.sin(2.0 * math.pi * freq * (i / sample_rate)) * volume
            
            # Fade out nos últimos 100 samples para evitar estalos
            if i > num_samples - 100:
                fade = (num_samples - i) / 100.0
                val *= fade
            
            sample_int = int(max(min(val, 1.0), -1.0) * 32767)
            all_samples.append(sample_int)

    with wave.open(filepath, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        packed_data = struct.pack(f"<{len(all_samples)}h", *all_samples)
        wav_file.writeframes(packed_data)


def ensure_sounds():
    """Gera todos os arquivos de som necessários caso não existam."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True

    try:
        os.makedirs(_SOUNDS_DIR, exist_ok=True)

        sounds_def = {
            "countdown.wav": [(BEEP_FREQ_COUNTDOWN, BEEP_DURATION_MS)],
            "go.wav": [(BEEP_FREQ_GO, 300)],
            "success.wav": [(800, 120), (1200, 180)],
            "fail.wav": [(400, 150), (200, 250)],
            "splash.wav": [(0, 600)],  # Ruído de água
            "gameover.wav": [(600, 180), (450, 200), (300, 350)],
        }

        for filename, tones in sounds_def.items():
            path = os.path.join(_SOUNDS_DIR, filename)
            if not os.path.exists(path):
                _generate_wav(path, tones)
    except Exception as e:
        print(f"[Aviso] Não foi possível gerar sons: {e}")


def play_sound(name: str):
    """Toca um efeito sonoro assincronamente pelo nome (sem extensão)."""
    if not SOUND_ENABLED or winsound is None:
        return

    try:
        ensure_sounds()
        path = os.path.join(_SOUNDS_DIR, f"{name}.wav")
        if os.path.exists(path):
            threading.Thread(
                target=winsound.PlaySound,
                args=(path, winsound.SND_FILENAME),
                daemon=True,
            ).start()
    except Exception:
        pass


def play_countdown():
    play_sound("countdown")


def play_go():
    play_sound("go")


def play_success():
    play_sound("success")


def play_fail():
    play_sound("fail")


def play_splash():
    play_sound("splash")


def play_gameover():
    play_sound("gameover")
