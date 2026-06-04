import csv
import random
import os
import pandas as pd
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


def generar_pregunta_genero(pelicula, generos_es, generos_en, campo='Géneros'):
    """
    Construye la pregunta de género usando distractores del mismo idioma.
    Devuelve (enunciado, opciones, correcta)
    Optimizado: usa conjuntos de géneros pre-calculados.
    """
    titulo = pelicula['Título']
    # Tomamos un género de la película (si tiene varios, elegimos uno al azar)
    generos_peli = quiz_utils.split_generos(pelicula.get(campo, ''))
    if not generos_peli:
        return None, None, None
    correcta = random.choice(generos_peli).strip()
    distractores = quiz_utils.elegir_distractores_genero(correcta, generos_es, generos_en, k=2)

    opciones = [correcta] + distractores
    random.shuffle(opciones)
    enunciado = f"🎭 ¿Cuál es uno de los géneros de '{titulo}'?"
    return enunciado, opciones, correcta

def elegir_opciones_correcta_y_distractores(correcta, valores_unicos, cantidad=3):
    """
    Versión optimizada que usa un set pre-filtrado de valores únicos.
    """
    return quiz_utils.elegir_opciones_correcta_y_distractores(correcta, valores_unicos, cantidad)

def hacer_pregunta(pelicula, todas, generos_es=None, generos_en=None, valores_unicos=None):
    """
    Genera una pregunta sobre una película.
    
    Args:
        pelicula: dict con datos de la película
        todas: lista de todas las películas
        generos_es: set de géneros en español (pre-calculado, opcional)
        generos_en: set de géneros en inglés (pre-calculado, opcional)
        valores_unicos: dict con sets de valores únicos por campo (pre-calculado, opcional)
    """
    posibles_tipos = []
    if pelicula.get('Director(es)', '').strip():
        posibles_tipos.append("director")
    if pelicula.get('Año', '').strip():
        posibles_tipos.append("año")
        posibles_tipos.append("peli_por_año")
    if pelicula.get('Géneros', '').strip():
        posibles_tipos.append("genero")
    if pelicula.get('Sinopsis', '').strip():
        posibles_tipos.append("sinopsis")

    if not posibles_tipos:
        return None

    tipo_pregunta = random.choice(posibles_tipos)
    titulo = pelicula['Título']

    if tipo_pregunta == "director":
        correcta = pelicula['Director(es)'].strip()
        # Usar cache si está disponible
        if valores_unicos and 'Director(es)' in valores_unicos:
            opciones = elegir_opciones_correcta_y_distractores(correcta, valores_unicos['Director(es)'])
        else:
            opciones = elegir_opciones_correcta_y_distractores(
                correcta, quiz_utils.prefiltrar_valores_unicos(todas, 'Director(es)')
            )
        print(f"🎬 ¿Quién ha dirigido la película de {pelicula['Año']}, '{titulo}'?")

    elif tipo_pregunta == "año":
        correcta = pelicula['Año'].strip()
        # Usar cache si está disponible
        if valores_unicos and 'Año' in valores_unicos:
            opciones = elegir_opciones_correcta_y_distractores(correcta, valores_unicos['Año'])
        else:
            opciones = elegir_opciones_correcta_y_distractores(
                correcta, quiz_utils.prefiltrar_valores_unicos(todas, 'Año')
            )
        print(f"📅 ¿En qué año se estrenó '{titulo}'?")

    elif tipo_pregunta == "peli_por_año":
        correcta = titulo
        mismo_anio = [p for p in todas if p['Año'] == pelicula['Año'] and p['Título'] != titulo]
        if len(mismo_anio) < 1:
            return None
        otras = [p for p in todas if p['Año'] != pelicula['Año']]
        if len(otras) < 2:
            return None
        distractores = random.sample(otras, k=2)
        opciones = [correcta] + [p['Título'] for p in distractores]
        random.shuffle(opciones)
        print(f"📽 ¿Cuál de estas películas se estrenó en {pelicula['Año']}?")

    elif tipo_pregunta == "genero":
        # Usar caches pre-calculados si están disponibles
        if generos_es is None or generos_en is None:
            generos_es, generos_en = quiz_utils.conjunto_generos_por_idioma(todas, campo='Géneros')
        enunciado, opciones, correcta = generar_pregunta_genero(pelicula, generos_es, generos_en, campo='Géneros')
        if not opciones:
            return None
        print(enunciado)

    elif tipo_pregunta == "sinopsis":
        correcta = titulo
        # Usar cache si está disponible
        if valores_unicos and 'Título' in valores_unicos:
            opciones = elegir_opciones_correcta_y_distractores(correcta, valores_unicos['Título'])
        else:
            opciones = elegir_opciones_correcta_y_distractores(
                correcta, quiz_utils.prefiltrar_valores_unicos(todas, 'Título')
            )
        print("📝 ¿A qué película pertenece esta sinopsis?\n")
        print(f"\"{pelicula['Sinopsis'].strip()}\"\n")

    for idx, opcion in enumerate(opciones, start=1):
        print(f"{idx}) {opcion}")

    respuesta = input("Elige una opción (1-3): ").strip()
    if respuesta in ["1", "2", "3"]:
        seleccion = opciones[int(respuesta) - 1]
        acierto = seleccion.strip().lower() == correcta.strip().lower()
        if not acierto:
            print(f"❌ Incorrecto. La respuesta correcta era: {correcta}")
        else:
            print("✅ ¡Correcto!")
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
    base = base.replace("_quiz", "")
    base = base.replace("-", " ")
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
            # Optimización: contar líneas sin cargar todo el CSV
            num_pelis = quiz_utils.contar_lineas_csv(ruta)
            dificultad = calcular_dificultad(num_pelis)

            record_nombre, record_puntos = cargar_record(ruta)
            info_record = f"🥇 {record_puntos} pts ({record_nombre})" if record_puntos > 0 else "⛔ Sin récord"

            nombre_legible = nombre_amigable(archivo)
            datos_quiz.append({
                "nombre": nombre_legible,
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

    # Ordenar por número de películas
    datos_quiz.sort(key=lambda x: x["num_pelis"])

    print("\n📁 Quizzes disponibles:")
    for i, quiz in enumerate(datos_quiz, start=1):
        print(f"{i}) {quiz['nombre']} ({quiz['num_pelis']} pelis) {quiz['dificultad']} | {quiz['info_record']}")

    while True:
        eleccion = input("Elige un número: ").strip()
        if eleccion.isdigit() and 1 <= int(eleccion) <= len(datos_quiz):
            return datos_quiz[int(eleccion) - 1]["ruta"]
        else:
            print("❌ Opción no válida. Intenta de nuevo.")

def iniciar_quiz(peliculas, ruta_csv):
    errores = 0
    aciertos = 0
    
    # Optimización: mantener lista de disponibles en lugar de set + random.choice
    disponibles = list(peliculas)
    random.shuffle(disponibles)  # Mezclar una vez al inicio
    
    # Pre-calcular caches para mejor rendimiento
    print("\n⚙️ Preparando datos...")
    generos_es, generos_en = quiz_utils.conjunto_generos_por_idioma(peliculas, campo='Géneros')
    valores_unicos = {
        'Director(es)': quiz_utils.prefiltrar_valores_unicos(peliculas, 'Director(es)'),
        'Año': quiz_utils.prefiltrar_valores_unicos(peliculas, 'Año'),
        'Título': quiz_utils.prefiltrar_valores_unicos(peliculas, 'Título'),
    }

    record_nombre, record_puntos = cargar_record(ruta_csv)
    if record_puntos > 0:
        print(f"\n🥇 Récord actual: {record_puntos} puntos (por {record_nombre})")
    else:
        print("\n🆕 Aún no hay récord. ¡Podrías ser el primero!")

    # Optimización: selección directa desde lista mezclada
    while errores < 3 and disponibles:
        peli = disponibles.pop()  # O(1) en lugar de O(n) con random.choice + verificación

        print(f"\n➡️ Aciertos: {aciertos} | Errores: {errores}/3\n" + "-" * 40 + "\n")
        resultado = hacer_pregunta(peli, peliculas, generos_es, generos_en, valores_unicos)
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