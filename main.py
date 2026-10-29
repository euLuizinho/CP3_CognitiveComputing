"""
Ponto de entrada do projeto Muro Humano.

Permite:
- Jogar o jogo interativamente
- Processar fotos para gerar novas fases
- Gerar fases placeholder
- Modo de validação (para o trabalho acadêmico / CP3)
"""

import os
import sys
import argparse
import csv
import time

_PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.stage_creator import process_all_photos, create_placeholder_stages
from src.game import MuroHumanoGame


def main():
    parser = argparse.ArgumentParser(description="Muro Humano - 3D Hole in the Wall")
    parser.add_argument(
        "--build-stages",
        action="store_true",
        help="Processa as fotos na pasta assets/photos e gera as fases em assets/stages",
    )
    parser.add_argument(
        "--gen-placeholders",
        action="store_true",
        help="Gera fases geométricas de teste na pasta assets/stages",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Índice da câmera (padrão: 0)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Executa o modo de validação com registro de métricas em CSV",
    )
    parser.add_argument(
        "--treino",
        "--free-play",
        action="store_true",
        help="Inicia direto no modo treino/livre (vidas infinitas, sem game over)",
    )

    args = parser.parse_args()

    photos_dir = os.path.join(_PROJECT_ROOT, "assets", "photos")
    stages_dir = os.path.join(_PROJECT_ROOT, "assets", "stages")

    os.makedirs(photos_dir, exist_ok=True)
    os.makedirs(stages_dir, exist_ok=True)

    if args.build_stages:
        print("[*] Iniciando processamento de fotos para geração de fases...")
        stages = process_all_photos(photos_dir, stages_dir)
        if not stages:
            print(f"[!] Nenhuma foto encontrada em {photos_dir}.")
            print("    Adicione imagens (.jpg, .png) nessa pasta e execute novamente:")
            print("    python main.py --build-stages")
        else:
            print(f"[OK] {len(stages)} fases geradas com sucesso em {stages_dir}!")
        return

    if args.gen_placeholders:
        print("[*] Gerando fases placeholder de teste...")
        stages = create_placeholder_stages(stages_dir)
        print(f"[OK] {len(stages)} fases geradas com sucesso em {stages_dir}!")
        return

    # Inicia o jogo
    print("[*] Inicializando Muro Humano...")
    game = MuroHumanoGame(stages_dir=stages_dir, free_play=args.treino, enable_validation=args.validate)
    game.run(camera_index=args.camera)


if __name__ == "__main__":
    main()
