"""
Módulo de utilidades compartidas para el quiz de películas.
Contiene funciones comunes y el registro extensible de tipos de pregunta.
"""

import random
import re

# --- Utilidades para géneros ---

def split_generos(cadena):
    """Separa la cadena de géneros en tokens limpios. Admite separadores comunes."""
    if not cadena:
        return []
    for sep in ['|', '/', ';']:
        cadena = cadena.replace(sep, ',')
    partes = [p.strip() for p in cadena.split(',')]
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
    """Heurístico para determinar si un género está en español o inglés."""
    gl = g.casefold().strip().strip('.')
    if gl in _ES_KNOWN:
        return 'es'
    if gl in _EN_KNOWN:
        return 'en'
    if any(ch in gl for ch in 'áéíóúüñ'):
        return 'es'
    if 'sci-fi' in gl or 'science' in gl:
        return 'en'
    if gl == 'thriller':
        return 'en'
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
    """Elige k distractores del mismo idioma que la opción correcta."""
    idioma = idioma_genero(correcta)
    pool = (generos_es if idioma == 'es' else generos_en).copy()
    pool = {g for g in pool if g.casefold().strip(' .') != correcta.casefold().strip(' .')}
    if len(pool) < k:
        respaldo = (generos_en if idioma == 'es' else generos_es).copy()
        respaldo = {g for g in respaldo if g.casefold().strip(' .') != correcta.casefold().strip(' .')}
        combinados = list(pool) + list(respaldo)
        combinados = list(dict.fromkeys(combinados))
        return combinados[:k] if len(combinados) < k else random.sample(combinados, k=k)
    return random.sample(list(pool), k=k)


# --- Utilidades generales ---

def contar_lineas_csv(ruta_csv):
    """Cuenta las líneas de datos de un CSV sin cargarlo completamente."""
    try:
        with open(ruta_csv, 'r', encoding='utf-8') as f:
            f.readline()  # saltar headers
            return sum(1 for _ in f)
    except Exception:
        return 0

def prefiltrar_valores_unicos(peliculas, campo):
    """Devuelve un set con valores únicos no vacíos del campo especificado."""
    return {p.get(campo, '').strip() for p in peliculas if p.get(campo, '').strip()}

def elegir_opciones_correcta_y_distractores(correcta, valores_unicos, cantidad=3):
    """Devuelve una lista mezclada con la respuesta correcta y distractores aleatorios."""
    candidatos = [v for v in valores_unicos if v.lower() != correcta.lower()]
    opciones = {correcta}
    if len(candidatos) >= cantidad - 1:
        opciones.update(random.sample(candidatos, k=cantidad - 1))
    else:
        opciones.update(candidatos)
    return random.sample(list(opciones), k=min(len(opciones), cantidad))


# --- Sistema de tipos de pregunta extensible ---

class TipoPregunta:
    """
    Representa un tipo de pregunta del quiz.

    Para añadir un nuevo tipo, crea una instancia y agrégala a TIPOS_PREGUNTA.
    - campo_requerido: campo del CSV que debe estar relleno para que la pregunta sea válida.
    - generar_fn(pelicula, todas, cache) -> (enunciado, opciones, correcta) | None
    - puede_fn(pelicula, todas) -> bool  (opcional, para condiciones extra)
    """
    def __init__(self, id, campo_requerido, generar_fn, puede_fn=None):
        self.id = id
        self.campo_requerido = campo_requerido
        self._generar_fn = generar_fn
        self._puede_fn = puede_fn

    def puede_generar(self, pelicula, todas):
        if not pelicula.get(self.campo_requerido, '').strip():
            return False
        return self._puede_fn(pelicula, todas) if self._puede_fn else True

    def generar(self, pelicula, todas, cache):
        return self._generar_fn(pelicula, todas, cache)


# Funciones generadoras para cada tipo

def _gen_director(pelicula, todas, cache):
    titulo = pelicula['Título']
    correcta = pelicula['Director(es)'].strip()
    opciones = elegir_opciones_correcta_y_distractores(correcta, cache['valores_unicos']['Director(es)'])
    enunciado = f"🎬 ¿Quién ha dirigido la película de {pelicula.get('Año', '?')}, '{titulo}'?"
    return enunciado, opciones, correcta

def _gen_ano(pelicula, todas, cache):
    titulo = pelicula['Título']
    correcta = pelicula['Año'].strip()
    opciones = elegir_opciones_correcta_y_distractores(correcta, cache['valores_unicos']['Año'])
    enunciado = f"📅 ¿En qué año se estrenó '{titulo}'?"
    return enunciado, opciones, correcta

def _puede_peli_por_ano(pelicula, todas):
    mismo = [p for p in todas if p.get('Año') == pelicula.get('Año') and p.get('Título') != pelicula.get('Título')]
    otras = [p for p in todas if p.get('Año') != pelicula.get('Año')]
    return len(mismo) >= 1 and len(otras) >= 2

def _gen_peli_por_ano(pelicula, todas, cache):
    titulo = pelicula['Título']
    otras = [p for p in todas if p.get('Año') != pelicula.get('Año')]
    distractores = random.sample(otras, k=2)
    opciones = [titulo] + [p['Título'] for p in distractores]
    random.shuffle(opciones)
    enunciado = f"📽 ¿Cuál de estas películas se estrenó en {pelicula.get('Año', '?')}?"
    return enunciado, opciones, titulo

def _gen_genero(pelicula, todas, cache):
    titulo = pelicula['Título']
    generos_peli = split_generos(pelicula.get('Géneros', ''))
    if not generos_peli:
        return None
    correcta = random.choice(generos_peli).strip()
    distractores = elegir_distractores_genero(correcta, cache['generos_es'], cache['generos_en'], k=2)
    opciones = [correcta] + distractores
    random.shuffle(opciones)
    enunciado = f"🎭 ¿Cuál es uno de los géneros de '{titulo}'?"
    return enunciado, opciones, correcta

def _gen_sinopsis(pelicula, todas, cache):
    titulo = pelicula['Título']
    correcta = titulo
    opciones = elegir_opciones_correcta_y_distractores(correcta, cache['valores_unicos']['Título'])
    sinopsis = pelicula.get('Sinopsis', '').strip()
    enunciado = f"📝 ¿A qué película pertenece esta sinopsis?\n\n\"{sinopsis}\""
    return enunciado, opciones, correcta

def _puede_peli_por_director(pelicula, todas):
    director = pelicula.get('Director(es)', '').strip()
    otras = [p for p in todas if p.get('Director(es)', '').strip() != director]
    return len(otras) >= 2

def _gen_peli_por_director(pelicula, todas, cache):
    titulo = pelicula['Título']
    director = pelicula.get('Director(es)', '').strip()
    otras = [p for p in todas if p.get('Director(es)', '').strip() != director]
    distractores = random.sample(otras, k=2)
    opciones = [titulo] + [p['Título'] for p in distractores]
    random.shuffle(opciones)
    enunciado = f"🎬 ¿Cuál de estas películas está dirigida por {director}?"
    return enunciado, opciones, titulo


TIPOS_PREGUNTA = [
    TipoPregunta('director',          'Director(es)', _gen_director),
    TipoPregunta('año',               'Año',          _gen_ano),
    TipoPregunta('peli_por_año',      'Año',          _gen_peli_por_ano,      _puede_peli_por_ano),
    TipoPregunta('genero',            'Géneros',      _gen_genero),
    TipoPregunta('sinopsis',          'Sinopsis',     _gen_sinopsis),
    TipoPregunta('peli_por_director', 'Director(es)', _gen_peli_por_director, _puede_peli_por_director),
]


def construir_cache(peliculas):
    """Pre-calcula los datos necesarios para generar preguntas eficientemente."""
    generos_es, generos_en = conjunto_generos_por_idioma(peliculas)
    return {
        'generos_es': generos_es,
        'generos_en': generos_en,
        'valores_unicos': {
            'Director(es)': prefiltrar_valores_unicos(peliculas, 'Director(es)'),
            'Año':          prefiltrar_valores_unicos(peliculas, 'Año'),
            'Título':       prefiltrar_valores_unicos(peliculas, 'Título'),
        }
    }


def generar_pregunta(pelicula, todas, cache):
    """
    Genera una pregunta para la película dada usando el registro TIPOS_PREGUNTA.
    Devuelve un dict {tipo, enunciado, opciones, correcta} o None si no es posible.
    """
    posibles = [t for t in TIPOS_PREGUNTA if t.puede_generar(pelicula, todas)]
    if not posibles:
        return None
    tipo = random.choice(posibles)
    resultado = tipo.generar(pelicula, todas, cache)
    if resultado is None:
        return None
    enunciado, opciones, correcta = resultado
    return {'tipo': tipo.id, 'enunciado': enunciado, 'opciones': opciones[:3], 'correcta': correcta}
