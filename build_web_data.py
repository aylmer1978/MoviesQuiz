"""
build_web_data.py
Convierte los CSV de csv_quiz/ en JSON listos para la web app estática (web/data/).
Genera un archivo JSON por quiz + un index.json con el catálogo.

Uso:
    python build_web_data.py
"""

import csv
import json
import os

import movieQuiz as engine
import quiz_utils

CARPETA_CSV = "csv_quiz"
CARPETA_SALIDA = os.path.join("docs", "data")

# Mapeo de columnas del CSV (con acentos) a claves JSON simples (ascii, cómodas en JS)
CAMPOS = {
    "Título": "titulo",
    "Año": "anio",
    "Sinopsis": "sinopsis",
    "Director(es)": "director",
    "Duración": "duracion",
    "Géneros": "generos",
    "Reparto principal": "reparto",
    "Enlace": "enlace",
}


def quiz_id(nombre_archivo):
    """ID estable del quiz a partir del nombre de archivo."""
    base = os.path.splitext(nombre_archivo)[0]
    return base.replace("_quiz", "")


def convertir_csv(ruta_csv):
    peliculas = []
    with open(ruta_csv, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            peli = {clave_json: (row.get(col) or "").strip() for col, clave_json in CAMPOS.items()}
            # Solo incluir pelis con al menos título
            if peli["titulo"]:
                peliculas.append(peli)
    return peliculas


def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    archivos = sorted(f for f in os.listdir(CARPETA_CSV) if f.endswith(".csv"))

    indice = []
    for archivo in archivos:
        ruta = os.path.join(CARPETA_CSV, archivo)
        peliculas = convertir_csv(ruta)
        if not peliculas:
            print(f"⏭  {archivo}: sin películas válidas, omitido.")
            continue

        qid = quiz_id(archivo)
        salida = os.path.join(CARPETA_SALIDA, f"{qid}.json")
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(peliculas, f, ensure_ascii=False)

        num = len(peliculas)
        indice.append({
            "id": qid,
            "nombre": engine.nombre_amigable(archivo),
            "num_peliculas": num,
            "dificultad": engine.calcular_dificultad(num),
            "archivo": f"data/{qid}.json",
        })
        print(f"✅ {archivo} → {qid}.json ({num} películas)")

    # Ordenar índice por número de películas
    indice.sort(key=lambda x: x["num_peliculas"])
    with open(os.path.join(CARPETA_SALIDA, "index.json"), "w", encoding="utf-8") as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)

    print(f"\n📦 Generados {len(indice)} quizzes en {CARPETA_SALIDA}")
    print("📄 Índice: docs/data/index.json")


if __name__ == "__main__":
    main()
