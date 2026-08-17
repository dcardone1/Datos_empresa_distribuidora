"""
run_all.py
===========
Corre todo el pipeline de generación en el orden correcto. Podés ejecutar
este script solo, o correr cada 0X_*.py por separado si querés inspeccionar
resultados intermedios paso a paso (es lo recomendable la primera vez que
lo revises, para entender qué hace cada etapa).

Uso:
    python3 run_all.py
"""

import os
import subprocess
import sys
import time

import config as cfg

SCRIPTS = [
    "01_generar_catalogos.py",
    "02_generar_flota_clientes.py",
    "03_generar_pedidos.py",
    "04_generar_viajes.py",
    "05_generar_combustible_mantenimiento.py",
]


def main():
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    inicio_total = time.time()

    for script in SCRIPTS:
        print(f"\n{'=' * 70}\n>>> Ejecutando {script}\n{'=' * 70}")
        inicio = time.time()
        resultado = subprocess.run([sys.executable, script])
        if resultado.returncode != 0:
            print(f"\n❌ {script} terminó con error (código {resultado.returncode}). Se detiene el pipeline.")
            sys.exit(1)
        print(f"--- {script} terminado en {time.time() - inicio:.1f}s ---")

    print(f"\n{'=' * 70}")
    print(f"Pipeline completo en {time.time() - inicio_total:.1f}s. "
          f"Archivos CSV disponibles en ./{cfg.OUTPUT_DIR}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
