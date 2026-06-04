/*
 * quiz.js — Lógica de generación de preguntas (portada de quiz_utils.py).
 * Sistema de tipos extensible: para añadir una pregunta, define una función
 * generadora y agrégala a TIPOS_PREGUNTA.
 */

// --- Utilidades aleatorias ---
function elegirAlAzar(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function muestra(arr, k) {
  // Devuelve k elementos únicos al azar (Fisher-Yates parcial)
  const copia = arr.slice();
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia.slice(0, k);
}

function mezclar(arr) {
  return muestra(arr, arr.length);
}

// --- Géneros ---
function splitGeneros(cadena) {
  if (!cadena) return [];
  let c = cadena;
  for (const sep of ['|', '/', ';']) c = c.split(sep).join(',');
  return c.split(',').map(s => s.replace(/ {2}/g, ' ').trim()).filter(Boolean);
}

const ES_KNOWN = new Set([
  'acción','aventura','aventuras','animación','bélico','biografía','ciencia ficción','comedia',
  'crimen','documental','drama','familia','fantasía','historia','misterio','musical','romance',
  'suspense','terror','thriller','western','noir','deportes'
]);
const EN_KNOWN = new Set([
  'action','adventure','animation','war','biography','science fiction','sci-fi','comedy','crime',
  'documentary','drama','family','fantasy','history','mystery','musical','romance','thriller',
  'horror','western','film noir','sports'
]);

function idiomaGenero(g) {
  const gl = g.toLowerCase().trim().replace(/\.+$/, '');
  if (ES_KNOWN.has(gl)) return 'es';
  if (EN_KNOWN.has(gl)) return 'en';
  if (/[áéíóúüñ]/.test(gl)) return 'es';
  if (gl.includes('sci-fi') || gl.includes('science')) return 'en';
  if (gl === 'thriller') return 'en';
  return 'es';
}

function conjuntoGenerosPorIdioma(peliculas) {
  const ges = new Set(), gen = new Set();
  for (const p of peliculas) {
    for (const g of splitGeneros(p.generos || '')) {
      (idiomaGenero(g) === 'es' ? ges : gen).add(g.trim());
    }
  }
  return { es: [...ges], en: [...gen] };
}

function norm(s) {
  return s.toLowerCase().trim().replace(/^[ .]+|[ .]+$/g, '');
}

function elegirDistractoresGenero(correcta, generos, k = 2) {
  const idioma = idiomaGenero(correcta);
  let pool = (idioma === 'es' ? generos.es : generos.en).filter(g => norm(g) !== norm(correcta));
  if (pool.length < k) {
    const respaldo = (idioma === 'es' ? generos.en : generos.es).filter(g => norm(g) !== norm(correcta));
    const combinados = [...new Set([...pool, ...respaldo])];
    return combinados.length < k ? combinados.slice(0, k) : muestra(combinados, k);
  }
  return muestra(pool, k);
}

// --- Valores únicos ---
function prefiltrarValoresUnicos(peliculas, campo) {
  const s = new Set();
  for (const p of peliculas) {
    const v = (p[campo] || '').trim();
    if (v) s.add(v);
  }
  return [...s];
}

function elegirOpcionesCorrectaYDistractores(correcta, valoresUnicos, cantidad = 3) {
  const candidatos = valoresUnicos.filter(v => v.toLowerCase() !== correcta.toLowerCase());
  const opciones = new Set([correcta]);
  for (const d of muestra(candidatos, Math.min(cantidad - 1, candidatos.length))) opciones.add(d);
  return muestra([...opciones], Math.min(opciones.size, cantidad));
}

// --- Cache ---
function construirCache(peliculas) {
  return {
    generos: conjuntoGenerosPorIdioma(peliculas),
    valoresUnicos: {
      director: prefiltrarValoresUnicos(peliculas, 'director'),
      anio: prefiltrarValoresUnicos(peliculas, 'anio'),
      titulo: prefiltrarValoresUnicos(peliculas, 'titulo'),
    },
  };
}

// --- Tipos de pregunta ---
// Cada tipo: { id, campo, puede(peli, todas)?, generar(peli, todas, cache) -> {enunciado, opciones, correcta}|null }

const TIPOS_PREGUNTA = [
  {
    id: 'director',
    campo: 'director',
    generar(peli, todas, cache) {
      const correcta = peli.director.trim();
      const opciones = elegirOpcionesCorrectaYDistractores(correcta, cache.valoresUnicos.director);
      return { enunciado: `🎬 ¿Quién ha dirigido la película de ${peli.anio || '?'}, «${peli.titulo}»?`, opciones, correcta };
    },
  },
  {
    id: 'anio',
    campo: 'anio',
    generar(peli, todas, cache) {
      const correcta = peli.anio.trim();
      const opciones = elegirOpcionesCorrectaYDistractores(correcta, cache.valoresUnicos.anio);
      return { enunciado: `📅 ¿En qué año se estrenó «${peli.titulo}»?`, opciones, correcta };
    },
  },
  {
    id: 'peli_por_anio',
    campo: 'anio',
    puede(peli, todas) {
      const mismo = todas.filter(p => p.anio === peli.anio && p.titulo !== peli.titulo);
      const otras = todas.filter(p => p.anio !== peli.anio);
      return mismo.length >= 1 && otras.length >= 2;
    },
    generar(peli, todas) {
      const otras = todas.filter(p => p.anio !== peli.anio);
      const distractores = muestra(otras, 2).map(p => p.titulo);
      const opciones = mezclar([peli.titulo, ...distractores]);
      return { enunciado: `📽 ¿Cuál de estas películas se estrenó en ${peli.anio || '?'}?`, opciones, correcta: peli.titulo };
    },
  },
  {
    id: 'genero',
    campo: 'generos',
    generar(peli, todas, cache) {
      const generosPeli = splitGeneros(peli.generos || '');
      if (!generosPeli.length) return null;
      const correcta = elegirAlAzar(generosPeli).trim();
      const distractores = elegirDistractoresGenero(correcta, cache.generos, 2);
      const opciones = mezclar([correcta, ...distractores]);
      return { enunciado: `🎭 ¿Cuál es uno de los géneros de «${peli.titulo}»?`, opciones, correcta };
    },
  },
  {
    id: 'sinopsis',
    campo: 'sinopsis',
    generar(peli, todas, cache) {
      const correcta = peli.titulo;
      const opciones = elegirOpcionesCorrectaYDistractores(correcta, cache.valoresUnicos.titulo);
      return { enunciado: `📝 ¿A qué película pertenece esta sinopsis?\n\n"${(peli.sinopsis || '').trim()}"`, opciones, correcta };
    },
  },
  {
    id: 'peli_por_director',
    campo: 'director',
    puede(peli, todas) {
      const director = peli.director.trim();
      return todas.filter(p => (p.director || '').trim() !== director).length >= 2;
    },
    generar(peli, todas) {
      const director = peli.director.trim();
      const otras = todas.filter(p => (p.director || '').trim() !== director);
      const distractores = muestra(otras, 2).map(p => p.titulo);
      const opciones = mezclar([peli.titulo, ...distractores]);
      return { enunciado: `🎬 ¿Cuál de estas películas está dirigida por ${director}?`, opciones, correcta: peli.titulo };
    },
  },
];

function puedeGenerar(tipo, peli, todas) {
  if (!(peli[tipo.campo] || '').trim()) return false;
  return tipo.puede ? tipo.puede(peli, todas) : true;
}

function generarPregunta(peli, todas, cache) {
  const posibles = TIPOS_PREGUNTA.filter(t => puedeGenerar(t, peli, todas));
  if (!posibles.length) return null;
  const tipo = elegirAlAzar(posibles);
  const r = tipo.generar(peli, todas, cache);
  if (!r) return null;
  return { tipo: tipo.id, enunciado: r.enunciado, opciones: r.opciones.slice(0, 3), correcta: r.correcta };
}
