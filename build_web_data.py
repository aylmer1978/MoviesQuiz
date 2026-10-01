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
CARPETA_DESCRIPCIONES = "descripciones"
ARCHIVO_PUBLICAS = "listas_publicas.txt"
CARPETA_LISTAS = "csv_lists"

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

def leer_descripcion(qid):
    """Devuelve el texto de descripciones/<id>.txt, o "" si esa lista aún no tiene."""
    ruta = os.path.join(CARPETA_DESCRIPCIONES, f"{qid}.txt")
    if not os.path.exists(ruta):
        return ""
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read().strip()

def leer_publicas():
    """Devuelve el conjunto de ids de las listas marcadas como públicas."""
    with open(ARCHIVO_PUBLICAS, "r", encoding="utf-8") as f:
        return {linea.strip() for linea in f if linea.strip()}

def claves_de_lista(qid):
    """Devuelve el conjunto (título, año) de las películas que hay ahora en la lista, o None si no existe."""
    ruta = os.path.join(CARPETA_LISTAS, f"{qid}.csv")
    if not os.path.exists(ruta):
        return None
    with open(ruta, "r", encoding="utf-8") as f:
        return {((r["Name"] or "").strip(), (r["Year"] or "").strip()) for r in csv.DictReader(f)}

def convertir_csv(ruta_csv, claves=None):
    """Convierte un CSV de quiz en una lista de películas.
    Si se pasan 'claves', solo incluye las películas que siguen en la lista de Letterboxd."""
    peliculas = []
    with open(ruta_csv, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if claves is not None:
                clave = ((row.get("Nombre original") or "").strip(), (row.get("Año original") or "").strip())
                if clave not in claves:
                    continue   # Película que ya no está en la lista: no se publica
            peli = {clave_json: (row.get(col) or "").strip() for col, clave_json in CAMPOS.items()}
            # Solo incluir pelis con al menos título
            if peli["titulo"]:
                peliculas.append(peli)
    return peliculas


def main():
    # Sin el archivo de listas públicas no seguimos: publicaríamos un juego vacío
    if not os.path.exists(ARCHIVO_PUBLICAS):
        print(f"❌ No existe {ARCHIVO_PUBLICAS}. Créalo con los ids de las listas públicas.")
        return
    publicas = leer_publicas()

    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    # Borramos los JSON anteriores: así, si ocultas una lista, desaparece también de la web
    for viejo in os.listdir(CARPETA_SALIDA):
        if viejo.endswith(".json"):
            os.remove(os.path.join(CARPETA_SALIDA, viejo))

    archivos = sorted(f for f in os.listdir(CARPETA_CSV) if f.endswith(".csv"))

    indice = []
    for archivo in archivos:
        qid = quiz_id(archivo)
        if qid not in publicas:
            print(f"🚫 {archivo}: oculta, no se publica")
            continue

        ruta = os.path.join(CARPETA_CSV, archivo)
        peliculas = convertir_csv(ruta, claves_de_lista(qid))
        if not peliculas:
            print(f"⏭  {archivo}: sin películas válidas, omitido.")
            continue

        salida = os.path.join(CARPETA_SALIDA, f"{qid}.json")
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(peliculas, f, ensure_ascii=False)

        num = len(peliculas)
        indice.append({
            "id": qid,
            "nombre": engine.nombre_amigable(archivo),
            "num_peliculas": num,
            "dificultad": engine.calcular_dificultad(num),
            "descripcion": leer_descripcion(qid),
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
