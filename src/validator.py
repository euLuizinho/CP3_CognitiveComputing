"""
Módulo de validação empírica do jogo Muro Humano (para o CP3 / relatório acadêmico).

Registra tentativas de teste com pessoas reais:
- Veredito do jogo (Passou / Caiu)
- Porcentagem de corpo fora do buraco
- Veredito do observador humano (Passou / Caiu)
- FPS médio durante a tentativa
- Taxa de concordância geral
"""

import os
import csv
import time
from datetime import datetime

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CSV_PATH = os.path.join(_PROJECT_ROOT, "validacao_tentativas.csv")


class ValidationTracker:
    def __init__(self, csv_path: str = _CSV_PATH):
        self.csv_path = csv_path
        self._init_csv()

    def _init_csv(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "tentativa_id",
                    "data_hora",
                    "fase_id",
                    "porcentagem_fora",
                    "veredito_jogo",
                    "veredito_humano",
                    "concordou",
                    "fps_medio",
                    "observacoes"
                ])

    def log_trial(self, trial_id: int, stage_idx: int, outside_pct: float,
                  game_passed: bool, human_passed: bool, avg_fps: float, notes: str = ""):
        """Registra uma tentativa individual no arquivo CSV."""
        concordou = 1 if (game_passed == human_passed) else 0
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                trial_id,
                now_str,
                stage_idx + 1,
                f"{outside_pct:.2f}",
                "PASSOU" if game_passed else "CAIU",
                "PASSOU" if human_passed else "CAIU",
                concordou,
                f"{avg_fps:.1f}",
                notes
            ])

    def get_summary(self) -> dict:
        """Calcula o resumo das métricas (taxa de concordância e FPS médio)."""
        if not os.path.exists(self.csv_path):
            return {"total": 0, "concordancia_pct": 0.0, "fps_medio": 0.0}

        total = 0
        concordancias = 0
        fps_sum = 0.0

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                concordancias += int(row["concordou"])
                fps_sum += float(row["fps_medio"])

        if total == 0:
            return {"total": 0, "concordancia_pct": 0.0, "fps_medio": 0.0}

        return {
            "total": total,
            "concordancia_pct": (concordancias / total) * 100.0,
            "fps_medio": fps_sum / total,
        }
