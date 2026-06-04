import csv
import random
import os
import quiz_utils

def cargar_peliculas(ruta_csv):
    with open(ruta_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def mostrar_cartel():
    print(r"""
 _____ _  _ ___   _    ___ _____ _____ ___ ___ ___  _____  _____     ___  _   _ ___ ____
|_   _| || | __| | |  | __|_   _|_   _| __| _ \ _ )/ _ \ \/ /   \   / _ \| | | |_ _|_  /
  | | | __ | _|  | |__| _|  | |   | | | _||   / _ \ (_) >  <| |) | | (_) | |_| || | / /
  |_| |_||_|___| |____|___| |_|   |_| |___|_|_\___/\___/_/\_\___/   \__\_\\___/|___/___|

             T H E   L E T T E R B O X D   Q U I Z
""")


def hacer_pregunta(pelicula, todas, cache):
    pregunta = quiz_utils.generar_pregunta(pelicula, todas, cache)
    if not pregunta:
        return None

    print(pregunta['enunciado'])
    for idx, opcion in enumerate(pregunta['opciones'], start=1):
        print(f"{idx}) {opcion}")

    respuesta = input("Elige una opción (1-3): ").strip()
    if respuesta in ["1", "2", "3"]:
        seleccion = pregunta['opciones'][int(respuesta) - 1]
        acierto = seleccion.strip().lower() == pregunta['correcta'].strip().lower()
        if acierto:
            print("✅ ¡Correcto!")
        else:
            print(f"❌ Incorrecto. La respuesta correcta era: {pregunta['correcta']}")
        return acierto
    else:
        print("❌ Respuesta no válida.")
        return False


def cargar_record(ruta_csv):
    base = os.path.splitext(os.path.basename(ruta_csv))[0]
    record_path = os.path.join("records", f"{base}.record")
    if os.path.exists(record_path):
        with open(record_path, "r", encoding="utf-8") as f:
            nombre, puntos = f.read().strip().split(" - ")
            return nombre, int(puntos)
    return None, 0

def guardar_record(ruta_csv, nombre, puntuacion):
    os.makedirs("records", exist_ok=True)
    base = os.path.splitext(os.path.basename(ruta_csv))[0]
    record_path = os.path.join("records", f"{base}.record")
    with open(record_path, "w", encoding="utf-8") as f:
        f.write(f"{nombre} - {puntuacion}")

def calcular_dificultad(num_peliculas):
    if num_peliculas <= 50:
        return "🟢 FÁCIL"
    elif num_peliculas <= 150:
        return "🟡 MEDIA"
    elif num_peliculas <= 300:
        return "🔴 DIFÍCIL"
    else:
        return "⚫ EXTREMA"

def nombre_amigable(nombre_archivo):
    base = os.path.splitext(nombre_archivo)[0]
    base = base.replace("_quiz", "").replace("-", " ")
    return base.upper()

def elegir_csv_desde_directorio(directorio):
    archivos = [f for f in os.listdir(directorio) if f.endswith('.csv')]
    if not archivos:
        print("⚠️ No hay archivos CSV en la carpeta.")
        return None

    datos_quiz = []
    for archivo in archivos:
        ruta = os.path.join(directorio, archivo)
        try:
            num_pelis = quiz_utils.contar_lineas_csv(ruta)
            dificultad = calcular_dificultad(num_pelis)
            record_nombre, record_puntos = cargar_record(ruta)
            info_record = f"🥇 {record_puntos} pts ({record_nombre})" if record_puntos > 0 else "⛔ Sin récord"
            datos_quiz.append({
                "nombre": nombre_amigable(archivo),
                "ruta": ruta,
                "num_pelis": num_pelis,
                "dificultad": dificultad,
                "info_record": info_record
            })
        except Exception:
            datos_quiz.append({
                "nombre": archivo,
                "ruta": ruta,
                "num_pelis": 0,
                "dificultad": "❌ ERROR",
                "info_record": "⚠️ Error al leer el archivo"
            })

    datos_quiz.sort(key=lambda x: x["num_pelis"])

    print("\n📁 Quizzes disponibles:")
    for i, quiz in enumerate(datos_quiz, start=1):
        print(f"{i}) {quiz['nombre']} ({quiz['num_pelis']} pelis) {quiz['dificultad']} | {quiz['info_record']}")

    while True:
        eleccion = input("Elige un número: ").strip()
        if eleccion.isdigit() and 1 <= int(eleccion) <= len(datos_quiz):
            return datos_quiz[int(eleccion) - 1]["ruta"]
        print("❌ Opción no válida. Intenta de nuevo.")

def iniciar_quiz(peliculas, ruta_csv):
    errores = 0
    aciertos = 0
    disponibles = list(peliculas)
    random.shuffle(disponibles)

    print("\n⚙️ Preparando datos...")
    cache = quiz_utils.construir_cache(peliculas)

    record_nombre, record_puntos = cargar_record(ruta_csv)
    if record_puntos > 0:
        print(f"\n🥇 Récord actual: {record_puntos} puntos (por {record_nombre})")
    else:
        print("\n🆕 Aún no hay récord. ¡Podrías ser el primero!")

    while errores < 3 and disponibles:
        peli = disponibles.pop()
        print(f"\n➡️ Aciertos: {aciertos} | Errores: {errores}/3\n" + "-" * 40 + "\n")
        resultado = hacer_pregunta(peli, peliculas, cache)
        if resultado is None:
            continue
        elif resultado:
            aciertos += 1
        else:
            errores += 1

    if errores >= 3:
        print("\n💀 Has cometido 3 errores. Fin del juego.")
    else:
        print("\n🏁 Se han agotado las películas disponibles.")

    print(f"🎯 Aciertos totales: {aciertos}")

    if aciertos > record_puntos:
        print("🏆 ¡Nuevo récord!")
        nombre = input("Introduce tu nombre: ").strip()
        guardar_record(ruta_csv, nombre, aciertos)
    elif record_puntos > 0:
        print(f"🥈 No has superado el récord actual: {record_puntos} puntos (por {record_nombre}).")
        print("💡 ¡Suerte la próxima vez!")

if __name__ == "__main__":
    mostrar_cartel()
    ruta = elegir_csv_desde_directorio("csv_quiz")
    if ruta:
        peliculas = cargar_peliculas(ruta)
        iniciar_quiz(peliculas, ruta)
