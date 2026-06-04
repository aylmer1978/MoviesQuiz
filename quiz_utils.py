"""
Módulo de utilidades compartidas para el quiz de películas.
Contiene funciones comunes entre movieQuiz.py y movieQuiz_gui.py
"""

import random
import re

# --- Utilidades para preguntas de género ---

def split_generos(cadena):
    """Separa la cadena de géneros en tokens limpios. Admite separadores comunes."""
    if not cadena:
        return []
    # separadores típicos: coma, barra vertical, slash, punto y coma
    for sep in ['|', '/', ';']:
        cadena = cadena.replace(sep, ',')
    partes = [p.strip() for p in cadena.split(',')]
    # filtra vacíos y normaliza espacios dobles
    return [p for p in (s.replace('  ', ' ').strip() for s in partes) if p]

_ES_KNOWN = {
    'acción','aventura','aventuras','animación','bélico','biografía','ciencia ficción','comedia',
    'crimen','documental','drama','familia','fantasía','historia','misterio','musical','romance',
    'suspense','terror','thriller','western','noir','deportes'
}
_EN_KNOWN = {
    'action','adventure','animation','war','biography','science fiction','sci-fi','comedy','crime',
    'documentary','drama','family','fantasy','history','mystery','musical','romance','thriller',
    'horror','western','film noir','sports'
}

def idioma_genero(g):
    """
    Heurístico suave para determinar si un género está en español o inglés.
    1) Coincidencia con listas conocidas (casefold).
    2) Si contiene tildes/ñ -> ES.
    3) Si contiene solo ASCII y parece inglés común -> EN.
    4) Por defecto, ES (porque en tus CSV suele predominar ES).
    """
    gl = g.casefold()
    # normalización mínima (quitar puntos finales, etc.)
    gl = gl.strip().strip('.')
    if gl in _ES_KNOWN:
        return 'es'
    if gl in _EN_KNOWN:
        return 'en'
    # tildes o ñ
    if any(ch in gl for ch in 'áéíóúüñ'):
        return 'es'
    # sci-fi variantes
    if 'sci-fi' in gl or 'science' in gl:
        return 'en'
    # palabra "thriller" la consideramos EN si no hay acentos
    if gl == 'thriller':
        return 'en'
    # por defecto: español
    return 'es'

def conjunto_generos_por_idioma(peliculas, campo='Géneros'):
    """Devuelve dos sets: (generos_es, generos_en) extraídos de todas las películas."""
    ges, gen = set(), set()
    for p in peliculas:
        for g in split_generos(p.get(campo, '')):
            if idioma_genero(g) == 'es':
                ges.add(g.strip())
            else:
                gen.add(g.strip())
    return ges, gen

def elegir_distractores_genero(correcta, generos_es, generos_en, k=2):
    """
    Elige k distractores del mismo idioma que la opción correcta.
    
    Args:
        correcta: género correcto
        generos_es: set de géneros en español (precalculado)
        generos_en: set de géneros en inglés (precalculado)
        k: número de distractores a elegir
    
    Returns:
        Lista de k distractores
    """
    idioma = idioma_genero(correcta)
    pool = (generos_es if idioma == 'es' else generos_en).copy()
    
    # eliminar la correcta del pool (comparación flexible por casefold)
    pool = {g for g in pool if g.casefold().strip(' .') != correcta.casefold().strip(' .')}
    
    # si no hay suficientes en el mismo idioma, usamos el otro como respaldo
    if len(pool) < k:
        respaldo = (generos_en if idioma == 'es' else generos_es).copy()
        respaldo = {g for g in respaldo if g.casefold().strip(' .') != correcta.casefold().strip(' .')}
        # combinamos manteniendo prioridad del idioma objetivo
        combinados = list(pool) + list(respaldo)
        combinados = list(dict.fromkeys(combinados))  # dedupe manteniendo orden
        if len(combinados) >= k:
            return random.sample(combinados, k=k)
        else:
            # último recurso: relleno con lo que haya
            return combinados[:k]
    else:
        return random.sample(list(pool), k=k)


# --- Utilidades generales ---

def contar_lineas_csv(ruta_csv):
    """
    Cuenta las líneas de un CSV sin cargarlo completamente.
    Más eficiente que pd.read_csv cuando solo se necesita el conteo.
    """
    try:
        with open(ruta_csv, 'r', encoding='utf-8') as f:
            # Leer primera línea (headers) y contar el resto
            f.readline()  # saltar headers
            return sum(1 for _ in f)
    except Exception:
        return 0

def prefiltrar_valores_unicos(peliculas, campo):
    """
    Pre-filtra valores únicos de un campo en todas las películas.
    Útil para optimizar elegir_opciones_correcta_y_distractores.
    
    Returns:
        set con valores únicos no vacíos del campo especificado
    """
    valores = set()
    for p in peliculas:
        valor = p.get(campo, '').strip()
        if valor:
            valores.add(valor)
    return valores

def elegir_opciones_correcta_y_distractores(correcta, valores_unicos, cantidad=3):
    """
    Versión optimizada que usa un set pre-filtrado de valores únicos.
    
    Args:
        correcta: respuesta correcta
        valores_unicos: set de valores únicos pre-filtrados
        cantidad: número de opciones totales (default 3)
    
    Returns:
        Lista de opciones mezcladas aleatoriamente
    """
    opciones = {correcta}
    candidatos = [v for v in valores_unicos if v.lower() != correcta.lower()]
    
    if len(candidatos) >= cantidad - 1:
        distractores = random.sample(candidatos, k=cantidad - 1)
        opciones.update(distractores)
    else:
        # Si no hay suficientes candidatos, usar todos los disponibles
        opciones.update(candidatos)
    
    return random.sample(list(opciones), k=min(len(opciones), cantidad))




