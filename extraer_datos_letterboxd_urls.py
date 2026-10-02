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
from concurrent.futures import ThreadPoolExecutor, as_completed

import quiz_utils

# Nº de descargas simultáneas. Más alto = más rápido pero más riesgo de bloqueo.
MAX_WORKERS = 2

# Campos del CSV de salida (orden fijo para escritura incremental coherente)
CAMPOS_SALIDA = [
    "Título", "Año", "Sinopsis", "Director(es)", "Duración",
    "Géneros", "Reparto principal", "Nombre original", "Año original", "Enlace"
]

# User-Agent realista para reducir el riesgo de bloqueo
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'),
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}


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


def _limpiar_duracion(texto):
    """Extrae solo la duración en minutos, descartando 'More at IMDb', etc."""
    if not texto:
        return ""
    match = re.search(r'(\d+)\s*mins?', texto)
    return f"{match.group(1)} mins" if match else ""


def _limpiar_año(valor):
    """Devuelve solo los 4 dígitos del año, aunque venga como fecha completa."""
    if not valor:
        return ""
    match = re.search(r'(\d{4})', str(valor))
    return match.group(1) if match else ""


def extraer_datos_letterboxd(url):
    try:
        resp = session.get(url, headers=HEADERS, timeout=30)

        if not resp or not resp.text or resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')
        datos = {}

        h1 = soup.find("h1", class_="headline-1")
        datos["Título"] = h1.text.strip() if h1 else ""

        # Año: 1) JSON-LD, 2) h1, 3) URL
        año = ""
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            try:
                parsed = json.loads(json_ld.string)
                año = _limpiar_año(parsed.get("datePublished", ""))
            except Exception:
                pass
        if not año and h1:
            match = re.search(r'\((\d{4})\)', h1.text)
            if match:
                año = match.group(1)
        if not año:
            año = _limpiar_año(re.search(r'-(\d{4})/?$', url).group(1)) if re.search(r'-(\d{4})/?$', url) else ""

        datos["Año"] = año

        sinopsis = soup.find("meta", {"name": "description"})
        datos["Sinopsis"] = sinopsis["content"].strip() if sinopsis else ""

        # Directores: todos, no solo el primero
        directores = soup.select('a[href*="/director/"]')
        nombres_dir = list(dict.fromkeys(d.text.strip() for d in directores if d.text.strip()))
        datos["Director(es)"] = ", ".join(nombres_dir)

        detalles = soup.select_one(".text-link.text-footer")
        datos["Duración"] = _limpiar_duracion(detalles.text if detalles else "")

        generos = soup.select('.text-sluglist a[href*="/films/genre/"]')
        datos["Géneros"] = ", ".join(g.text.strip() for g in generos) if generos else ""

        reparto = soup.select('a[href*="/actor/"]')[:3]
        datos["Reparto principal"] = ", ".join(a.text.strip() for a in reparto) if reparto else ""

        return datos
    except Exception as e:
        print(f"❌ Error extrayendo datos de {url} - {e}")
        return None

def _clave(nombre, año):
    """Identifica una película por título + año: así los remakes no se confunden."""
    return ((nombre or "").strip(), (año or "").strip())

def _cargar_titulos_existentes(salida_csv):
    """Devuelve el set de (título, año) de las películas ya presentes en el CSV de salida."""
    existentes = set()
    if not os.path.exists(salida_csv):
        return existentes
    try:
        with open(salida_csv, 'r', encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                nombre = (row.get("Nombre original") or "").strip()
                if nombre:
                    existentes.add(_clave(nombre, row.get("Año original")))
    except Exception:
        pass
    return existentes


def _formatear_tiempo(segundos):
    segundos = int(segundos)
    m, s = divmod(segundos, 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def elegir_csv_desde_directorio(directorio_entrada, directorio_salida):
    archivos = [f for f in os.listdir(directorio_entrada) if f.endswith('.csv')]
    if not archivos:
        print("⚠️ No hay archivos CSV en la carpeta.")
        return None

    # Clasificar cada lista en pendientes (sin importar o a medias) y completadas
    pendientes, completadas = [], []
    for archivo in archivos:
        ruta_csv = os.path.join(directorio_entrada, archivo)
        nombre_base = os.path.splitext(archivo)[0]
        quiz_path = os.path.join(directorio_salida, f"{nombre_base}_quiz.csv")

        # Comparamos película a película (título + año) con lo ya extraído
        with open(ruta_csv, 'r', encoding='utf-8') as f:
            filas = list(csv.DictReader(f))
        existentes = _cargar_titulos_existentes(quiz_path)
        faltan = sum(1 for r in filas if _clave(r['Name'], r['Year']) not in existentes)

        total = len(filas)
        info = {"archivo": archivo, "total": total, "hechas": total - faltan}
        if total > 0 and faltan == 0:
            completadas.append(info)
        else:
            pendientes.append(info)

    # Numeración global continua a través de ambas secciones
    orden = []  # lista de nombres de archivo en el orden mostrado

    def _imprimir_seccion(titulo, items):
        if not items:
            return
        print(f"\n{titulo}")
        for info in items:
            orden.append(info["archivo"])
            n = len(orden)
            if info["hechas"]:
                estado = f"[✓ {info['hechas']}/{info['total']} extraídas]"
            else:
                estado = ""
            print(f"{n}) {info['archivo']} ({info['total']} películas) {estado}")

    _imprimir_seccion("📥 PENDIENTES DE IMPORTAR:", pendientes)
    _imprimir_seccion("✅ YA IMPORTADAS:", completadas)

    while True:
        eleccion = input("\nElige un número: ").strip()
        if eleccion.isdigit() and 1 <= int(eleccion) <= len(orden):
            return orden[int(eleccion) - 1]
        print("❌ Opción no válida. Intenta de nuevo.")


def _descargar_pelicula(row):
    """
    Tarea ejecutada en cada hilo: resuelve la URL y extrae los datos de una película.
    Devuelve el dict de datos listo para escribir, o None si falla.
    No escribe en disco (eso lo hace el hilo principal).
    """
    # Pequeña pausa con jitter para repartir la carga entre hilos
    time.sleep(random.uniform(0.3, 1.2))

    print(f"  → descargando: {row['Name']}")
    url_real = resolver_redireccion(row['URL'])
    if not url_real:
        return None

    datos = extraer_datos_letterboxd(url_real)
    if not datos:
        return None

    datos["Nombre original"] = row['Name']
    datos["Año original"] = row['Year']
    datos["Enlace"] = url_real
    if not datos.get("Año", "").strip():
        datos["Año"] = _limpiar_año(row['Year'])
    return datos


def procesar_csv(nombre_archivo, carpeta_entrada="csv_lists", carpeta_salida="csv_quiz"):
    entrada_csv = os.path.join(carpeta_entrada, nombre_archivo)
    nombre_base = os.path.splitext(nombre_archivo)[0]
    salida_csv = os.path.join(carpeta_salida, f"{nombre_base}_quiz.csv")

    with open(entrada_csv, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    total = len(rows)

    os.makedirs(carpeta_salida, exist_ok=True)

    # Reanudación: saltar las que ya están en el CSV de salida
    existentes = _cargar_titulos_existentes(salida_csv)
    archivo_nuevo = not os.path.exists(salida_csv)
    if existentes:
        print(f"♻️  Reanudando: {len(existentes)} películas ya extraídas se saltarán.")

    pendientes = [r for r in rows if _clave(r['Name'], r['Year']) not in existentes]
    if not pendientes:
        print("✅ Nada que hacer: todas las películas ya estaban extraídas.")
        return

    print(f"🚀 Procesando {len(pendientes)} películas con {MAX_WORKERS} descargas simultáneas...\n")

    nuevas = 0
    fallidas = 0
    completadas = 0
    tiempo_inicio = time.time()

    # Un solo hilo escritor (el principal): seguro sin locks.
    # Los hilos del pool solo descargan; aquí escribimos según van completando.
    with open(salida_csv, 'a', encoding='utf-8', newline='') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=CAMPOS_SALIDA)
        if archivo_nuevo:
            writer.writeheader()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futuros = {executor.submit(_descargar_pelicula, row): row for row in pendientes}

            for futuro in as_completed(futuros):
                row = futuros[futuro]
                completadas += 1

                # ETA según el ritmo real de esta sesión
                ritmo = (time.time() - tiempo_inicio) / completadas
                eta = _formatear_tiempo(ritmo * (len(pendientes) - completadas))

                try:
                    datos = futuro.result()
                except Exception as e:
                    datos = None
                    print(f"❌ Error con {row['Name']}: {e}")

                if datos:
                    writer.writerow(datos)
                    f_out.flush()  # guardado incremental inmediato
                    nuevas += 1
                    estado = "✅"
                else:
                    fallidas += 1
                    estado = "⚠️"

                print(f"[{completadas}/{len(pendientes)}] {estado} {row['Name']} (ETA ~{eta})")

    print(f"\n✅ Terminado: {nuevas} nuevas, {fallidas} fallidas.")
    print(f"📄 Archivo: {salida_csv}")
    if fallidas:
        print("💡 Vuelve a ejecutar para reintentar solo las que faltan.")


if __name__ == "__main__":
    archivo_seleccionado = elegir_csv_desde_directorio("csv_lists", "csv_quiz")
    if archivo_seleccionado:
        procesar_csv(archivo_seleccionado)
