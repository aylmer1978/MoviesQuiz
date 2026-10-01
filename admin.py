"""
admin.py — Panel de control de The Letterboxd Quiz.
Muestra todas las listas con su estado y permite decidir cuáles son públicas.

Uso:
    python3 admin.py
"""

import csv
import os

CARPETA_LISTAS = "csv_lists"
CARPETA_QUIZ = "csv_quiz"
ARCHIVO_PUBLICAS = "listas_publicas.txt"


# --- Listas públicas ---
def leer_publicas():
    """Devuelve el conjunto de ids marcados como públicos (vacío si no hay archivo)."""
    if not os.path.exists(ARCHIVO_PUBLICAS):
        return set()
    with open(ARCHIVO_PUBLICAS, "r", encoding="utf-8") as f:
        return {linea.strip() for linea in f if linea.strip()}


def guardar_publicas(publicas):
    """Escribe los ids públicos en el archivo, uno por línea y en orden alfabético."""
    with open(ARCHIVO_PUBLICAS, "w", encoding="utf-8") as f:
        for qid in sorted(publicas):
            f.write(qid + "\n")


# --- Progreso de extracción ---
def _clave(nombre, año):
    """Identifica una película por título + año (igual que el extractor)."""
    return ((nombre or "").strip(), (año or "").strip())


def progreso(qid):
    """Devuelve (extraídas, total) de una lista, comparando su CSV con el del quiz."""
    with open(os.path.join(CARPETA_LISTAS, f"{qid}.csv"), "r", encoding="utf-8") as f:
        claves_lista = [_clave(r["Name"], r["Year"]) for r in csv.DictReader(f)]

    extraidas = set()
    ruta_quiz = os.path.join(CARPETA_QUIZ, f"{qid}_quiz.csv")
    if os.path.exists(ruta_quiz):
        with open(ruta_quiz, "r", encoding="utf-8") as f:
            extraidas = {_clave(r["Nombre original"], r["Año original"]) for r in csv.DictReader(f)}

    hechas = sum(1 for c in claves_lista if c in extraidas)
    return hechas, len(claves_lista)


# --- Menú ---
def mostrar_listas(ids, publicas):
    print("\n📋 LISTAS")
    for n, qid in enumerate(ids, start=1):
        hechas, total = progreso(qid)
        estado = "✅ pública" if qid in publicas else "🚫 oculta "
        aviso = "" if hechas == total else f"   ⚠️ incompleta ({hechas}/{total})"
        print(f"{n:2}) {estado}   {qid}{aviso}")


def cambiar_visibilidad(qid, publicas):
    # Si es pública, la ocultamos sin más
    if qid in publicas:
        publicas.remove(qid)
        print(f"🚫 {qid} ahora está oculta")
        return

    # Si es oculta, comprobamos antes que se pueda publicar
    hechas, total = progreso(qid)
    if hechas == 0:
        print(f"❌ {qid} no tiene ninguna película extraída: no se puede publicar")
        return
    if hechas < total:
        respuesta = input(f"⚠️ {qid} está incompleta ({hechas}/{total}). ¿Publicarla igualmente? (s/n): ")
        if respuesta.strip().lower() != "s":
            print("Sin cambios.")
            return

    publicas.add(qid)
    print(f"✅ {qid} ahora es pública")


def main():
    # Todas las listas que existen: las de csv_lists, que es donde empieza cada una
    ids = sorted(os.path.splitext(f)[0] for f in os.listdir(CARPETA_LISTAS) if f.endswith(".csv"))
    publicas = leer_publicas()

    while True:
        mostrar_listas(ids, publicas)
        eleccion = input("\nNúmero para mostrar/ocultar una lista, o S para salir: ").strip().lower()

        if eleccion == "s":
            break
        if eleccion.isdigit() and 1 <= int(eleccion) <= len(ids):
            cambiar_visibilidad(ids[int(eleccion) - 1], publicas)
            guardar_publicas(publicas)   # Guardamos en cada cambio, por si cierras de golpe
        else:
            print("❌ Opción no válida")

    print("\n👋 Recuerda: los cambios se aplican al juego cuando generes los datos (python3 build_web_data.py).")


if __name__ == "__main__":
    main()