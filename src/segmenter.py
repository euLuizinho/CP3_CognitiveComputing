"""
Módulo de segmentação de pessoas usando MediaPipe ImageSegmenter (Tasks API).

Fornece a classe PersonSegmenter que realiza segmentação de pessoas em imagens
estáticas (modo IMAGE) e em quadros de vídeo (modo VIDEO), retornando máscaras
binárias (0 = fundo, 255 = pessoa).
"""

import os
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision

from src.config import MODEL_FILENAME, MODEL_URL, SEGMENTER_THRESHOLD

# Diretório raiz do projeto (um nível acima de src/)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class PersonSegmenter:
    """Wrapper do MediaPipe ImageSegmenter para segmentação de pessoas.

    Cria instâncias lazy do segmentador para os modos IMAGE e VIDEO,
    baixando o modelo automaticamente caso não exista localmente.
    """

    def __init__(self) -> None:
        """Inicializa o segmentador, garantindo que o modelo está disponível."""
        # Garante que o modelo existe no disco
        self.model_path: str = self._ensure_model()

        # Instâncias lazy dos segmentadores (criadas sob demanda)
        self._image_seg: vision.ImageSegmenter | None = None
        self._video_seg: vision.ImageSegmenter | None = None

    # ------------------------------------------------------------------
    # Gerenciamento do modelo
    # ------------------------------------------------------------------

    def _ensure_model(self) -> str:
        """Verifica se o arquivo do modelo existe; baixa se necessário.

        Returns:
            Caminho absoluto para o arquivo do modelo .tflite.
        """
        model_dir = os.path.join(_PROJECT_ROOT, "models")
        model_path = os.path.join(model_dir, MODEL_FILENAME)

        if os.path.isfile(model_path):
            return model_path

        # Cria o diretório de modelos se não existir
        os.makedirs(model_dir, exist_ok=True)

        print(f"[Segmenter] Modelo não encontrado em '{model_path}'.")
        print(f"[Segmenter] Baixando de {MODEL_URL} ...")

        def _progress_hook(block_num: int, block_size: int, total_size: int) -> None:
            """Exibe progresso do download no terminal."""
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(downloaded / total_size * 100, 100.0)
                print(f"\r[Segmenter] Download: {pct:.1f}%", end="", flush=True)
            else:
                print(f"\r[Segmenter] Baixados {downloaded} bytes", end="", flush=True)

        urllib.request.urlretrieve(MODEL_URL, model_path, reporthook=_progress_hook)
        print("\n[Segmenter] Download concluído.")

        return model_path

    # ------------------------------------------------------------------
    # Criação lazy dos segmentadores
    # ------------------------------------------------------------------

    def _get_image_segmenter(self) -> vision.ImageSegmenter:
        """Retorna o segmentador no modo IMAGE, criando-o na primeira chamada."""
        if self._image_seg is None:
            options = vision.ImageSegmenterOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path),
                running_mode=vision.RunningMode.IMAGE,
                output_confidence_masks=True,
            )
            self._image_seg = vision.ImageSegmenter.create_from_options(options)
        return self._image_seg

    def _get_video_segmenter(self) -> vision.ImageSegmenter:
        """Retorna o segmentador no modo VIDEO, criando-o na primeira chamada."""
        if self._video_seg is None:
            options = vision.ImageSegmenterOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path),
                running_mode=vision.RunningMode.VIDEO,
                output_confidence_masks=True,
            )
            self._video_seg = vision.ImageSegmenter.create_from_options(options)
        return self._video_seg

    # ------------------------------------------------------------------
    # Métodos de segmentação
    # ------------------------------------------------------------------

    def segment_image(self, image_path: str) -> np.ndarray:
        """Segmenta uma pessoa em uma imagem estática (modo IMAGE).

        Args:
            image_path: Caminho para o arquivo de imagem.

        Returns:
            Máscara binária uint8 (0 = fundo, 255 = pessoa) com as mesmas
            dimensões (altura, largura) da imagem de entrada.
        """
        # Carrega a imagem em BGR e converte para RGB
        frame_bgr = cv2.imread(image_path)
        if frame_bgr is None:
            raise FileNotFoundError(f"Não foi possível carregar a imagem: {image_path}")

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # Cria o objeto mp.Image a partir do array RGB
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # Executa a segmentação no modo IMAGE
        segmenter = self._get_image_segmenter()
        result = segmenter.segment(mp_image)

        # Extrai a máscara de confiança da pessoa
        # Se houver apenas 1 máscara, ela é a da pessoa (foreground)
        # Se houver múltiplas (fundo e pessoa), a pessoa é o índice 1
        if len(result.confidence_masks) > 1:
            confidence = result.confidence_masks[1].numpy_view()
        else:
            confidence = result.confidence_masks[0].numpy_view()

        if confidence.ndim == 3:
            confidence = confidence[:, :, 0]

        # Converte para máscara binária
        mask = (confidence > SEGMENTER_THRESHOLD).astype(np.uint8) * 255

        # Redimensiona para o tamanho original da imagem, se necessário
        h, w = frame_bgr.shape[:2]
        if mask.shape[0] != h or mask.shape[1] != w:
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

        return mask

    def segment_frame(self, frame_bgr: np.ndarray, timestamp_ms: int) -> np.ndarray:
        """Segmenta uma pessoa em um quadro de vídeo (modo VIDEO).

        Args:
            frame_bgr: Quadro em formato BGR do OpenCV (np.ndarray).
            timestamp_ms: Timestamp monotonicamente crescente em milissegundos.

        Returns:
            Máscara binária uint8 (0 = fundo, 255 = pessoa) com as mesmas
            dimensões (altura, largura) do quadro de entrada.
        """
        # Garante timestamp estritamente crescente para a MediaPipe
        if not hasattr(self, '_last_timestamp_ms'):
            self._last_timestamp_ms = 0
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms

        # Converte BGR para RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # Cria o objeto mp.Image a partir do array RGB
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        # Executa a segmentação no modo VIDEO
        segmenter = self._get_video_segmenter()
        result = segmenter.segment_for_video(mp_image, timestamp_ms)

        # Extrai a máscara de confiança da pessoa
        if len(result.confidence_masks) > 1:
            confidence = result.confidence_masks[1].numpy_view()
        else:
            confidence = result.confidence_masks[0].numpy_view()

        if confidence.ndim == 3:
            confidence = confidence[:, :, 0]

        # Converte para máscara binária
        mask = (confidence > SEGMENTER_THRESHOLD).astype(np.uint8) * 255

        # Redimensiona para o tamanho do quadro original, se necessário
        h, w = frame_bgr.shape[:2]
        if mask.shape[0] != h or mask.shape[1] != w:
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

        return mask

    # ------------------------------------------------------------------
    # Limpeza de recursos
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Fecha os segmentadores e libera os recursos alocados."""
        if self._image_seg is not None:
            self._image_seg.close()
            self._image_seg = None
        if self._video_seg is not None:
            self._video_seg.close()
            self._video_seg = None
