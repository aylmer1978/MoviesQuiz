import csv
import requests
from bs4 import BeautifulSoup
import time
import random
import os
import json
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def crear_sesion_reintentos():
    sesion = requests.Session()
    reintentos = Retry(
        total=5,                # hasta 5 intentos por petición
        backoff_factor=1.5,     # espera creciente: 1.5s, 3s, 4.5s...
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adaptador = HTTPAdapter(max_retries=reintentos)
    sesion.mount("http://", adaptador)
    sesion.mount("https://", adaptador)
    return sesion

session = crear_sesion_reintentos()

def resolver_redireccion(url):
    try:
        resp = session.head(url, allow_redirects=True, timeout=10)
        return resp.url
    except Exception as e:
        print(f"❌ No se pudo resolver la URL: {url} - {e}")
        return None

def extraer_datos_letterboxd(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = session.get(url, headers=headers, timeout=30)
        
        # Añadimos esta comprobación para evitar errores con respuestas vacías
        if not resp or not resp.text:
            return None

        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')
        datos = {}

        datos["Título"] = soup.find("h1", class_="headline-1").text.strip() if soup.find("h1", class_="headline-1") else ""

        # Extraer año desde JSON-LD
        año = ""
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            try:
                parsed = json.loads(json_ld.string)
                año = str(parsed.get("datePublished", "")).strip()
            except Exception:
                pass

        # Si falla, buscar en el h1
        if not año:
            h1 = soup.find("h1", class_="headline-1")
            if h1:
                match = re.search(r'\((\d{4})\)', h1.text)
                if match:
                    año = match.group(1)

        # Último intento: buscar en la URL
        if not año:
            match = re.search(r'/(\d{4})/?$', url)
            if match:
                año = match.group(1)

        datos["Año"] = año

        sinopsis = soup.find("meta", {"name": "description"})
        datos["Sinopsis"] = sinopsis["content"].strip() if sinopsis else ""
        director = soup.select_one('a[href*="/director/"]')
        datos["Director(es)"] = director.text.strip() if director else ""
        detalles = soup.select_one(".text-link.text-footer")
        datos["Duración"] = detalles.text.strip() if detalles else ""
        generos = soup.select('.text-sluglist a[href*="/films/genre/"]')
        datos["Géneros"] = ", ".join([g.text.strip() for g in generos]) if generos else ""
        reparto = soup.select('a[href*="/actor/"]')[:3]
        datos["Reparto principal"] = ", ".join([a.text.strip() for a in reparto]) if reparto else ""

        return datos
    except Exception as e:
        print(f"❌ Error extrayendo datos de {url} - {e}")
        return None

def contar_lineas_csv(ruta_csv):
    """Cuenta líneas de un CSV sin cargarlo completamente (más eficiente)."""
    try:
        with open(ruta_csv, 'r', encoding='utf-8') as f:
            f.readline()  # saltar headers
            return sum(1 for _ in f)
    except Exception:
        return 0

def elegir_csv_desde_directorio(directorio_entrada, directorio_salida):
    archivos = [f for f in os.listdir(directorio_entrada) if f.endswith('.csv')]
    if not archivos:
        print("⚠️ No hay archivos CSV en la carpeta.")
        return None

    print("\n📁 Listas disponibles:")
    for i, archivo in enumerate(archivos):
        ruta_csv = os.path.join(directorio_entrada, archivo)
        num_lineas = contar_lineas_csv(ruta_csv)

        nombre_base = os.path.splitext(archivo)[0]
        quiz_path = os.path.join(directorio_salida, f"{nombre_base}_quiz.csv")
        extraido = os.path.exists(quiz_path)
        estado = "[✓ EXTRAÍDO]" if extraido else ""
        print(f"{i+1}) {archivo} ({num_lineas} películas) {estado}")

    while True:
        eleccion = input("Elige un número: ").strip()
        if eleccion.isdigit() and 1 <= int(eleccion) <= len(archivos):
            return archivos[int(eleccion) - 1]
        else:
            print("❌ Opción no válida. Intenta de nuevo.")

def procesar_csv(nombre_archivo, carpeta_entrada="csv_lists", carpeta_salida="csv_quiz"):
    entrada_csv = os.path.join(carpeta_entrada, nombre_archivo)
    nombre_base = os.path.splitext(nombre_archivo)[0]
    salida_csv = os.path.join(carpeta_salida, f"{nombre_base}_quiz.csv")

    # Optimización: usar csv estándar en lugar de pandas (más eficiente para lectura simple)
    resultados = []
    total = 0
    
    # Primero contar total de filas
    with open(entrada_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        total = len(rows)

    for i, row in enumerate(rows, start=1):
        print(f"[{i}/{total}] Procesando: {row['Name']}")
        short_url = row['URL']
        url_real = resolver_redireccion(short_url)

        if not url_real:
            continue

        datos = extraer_datos_letterboxd(url_real)

        if datos:
            datos["Nombre original"] = row['Name']
            datos["Año original"] = row['Year']
            datos["Enlace"] = url_real

            # Si no se pudo extraer el año, usar el del CSV original
            if not datos.get("Año") or not datos["Año"].strip():
                datos["Año"] = str(row['Year']).strip()

            resultados.append(datos)
        else:
            print("⚠️ No se pudo obtener información.")

        time.sleep(random.uniform(1.5, 2.5))

    if not resultados:
        print("❌ No se pudo generar el CSV de salida.")
        return

    # Escribir CSV usando csv estándar (más eficiente que pandas para este caso)
    os.makedirs(carpeta_salida, exist_ok=True)
    
    # Determinar campos (usar los del primer resultado más los campos estándar)
    if resultados:
        campos = list(resultados[0].keys())
        with open(salida_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(resultados)
        print(f"\n✅ Archivo generado: {salida_csv}")

if __name__ == "__main__":
    archivo_seleccionado = elegir_csv_desde_directorio("csv_lists", "csv_quiz")
    if archivo_seleccionado:
        procesar_csv(archivo_seleccionado)