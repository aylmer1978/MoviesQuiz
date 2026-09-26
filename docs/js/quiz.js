/*
 * quiz.js — Lógica de generación de preguntas (portada de quiz_utils.py).
 * Sistema de tipos extensible: para añadir una pregunta, define una función
 * generadora y agrégala a TIPOS_PREGUNTA.
 */

// --- Configuración ---
const NUM_OPCIONES = 4;  // Respuestas por pregunta: la correcta + las falsas

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

// --- Valores únicos ---
function prefiltrarValoresUnicos(peliculas, campo) {
  const s = new Set();
  for (const p of peliculas) {
    const v = (p[campo] || '').trim();
    if (v) s.add(v);
  }
  return [...s];
}

function elegirOpcionesCorrectaYDistractores(correcta, valoresUnicos, cantidad = NUM_OPCIONES) {
  const candidatos = valoresUnicos.filter(v => v.toLowerCase() !== correcta.toLowerCase());
  const opciones = new Set([correcta]);
  for (const d of muestra(candidatos, Math.min(cantidad - 1, candidatos.length))) opciones.add(d);
  return muestra([...opciones], Math.min(opciones.size, cantidad));
}

// --- Años cercanos ---
function elegirAniosCercanos(correcta, margen = 5) {
  const anio = parseInt(correcta, 10);           // Pasamos el año de texto a número
  const anioActual = new Date().getFullYear();   // El año en que estamos
  const falsos = NUM_OPCIONES - 1;               // Cuántos años falsos necesitamos

  // Años candidatos por debajo y por encima del correcto (hasta "margen" de distancia)
  const debajo = [];
  const encima = [];
  for (let d = 1; d <= margen; d++) {
    debajo.push(anio - d);
    if (anio + d <= anioActual) encima.push(anio + d);  // Nunca años futuros
  }

  // Posibles repartos: cuántos años falsos van por debajo (de 0 a "falsos").
  // Solo valen los repartos para los que hay suficientes años a cada lado.
  const repartos = [];
  for (let n = 0; n <= falsos; n++) {
    if (n <= debajo.length && falsos - n <= encima.length) repartos.push(n);
  }

  // Elegimos uno al azar: así la correcta puede caer en cualquier posición
  const nDebajo = elegirAlAzar(repartos);

  const elegidos = [...muestra(debajo, nDebajo), ...muestra(encima, falsos - nDebajo)];
  return elegidos.map(a => String(a));  // Los devolvemos como texto, igual que en los datos
}

// --- Reparto ---
function splitReparto(cadena) {
  // Convierte "Actor A, Actor B, Actor C" en una lista: ["Actor A", "Actor B", "Actor C"]
  return (cadena || '')
    .split(',')                    // Corta el texto por las comas
    .map(nombre => nombre.trim())  // Quita espacios sobrantes de cada nombre
    .filter(nombre => nombre);     // Descarta los huecos vacíos
}

// --- Cache ---
function construirCache(peliculas) {
  return {
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
    puede(peli, todas) {
      // El año tiene que ser un número (en los datos hay algún "nan")
      if (isNaN(parseInt(peli.anio, 10))) return false;
      // Contamos cuántas películas de la lista tienen este mismo título
      const mismoTitulo = todas.filter(p => p.titulo === peli.titulo);
      // Si solo hay una (ella misma), el título no está repetido y se puede preguntar
      return mismoTitulo.length === 1;
    },
    generar(peli, todas, cache) {
      const correcta = peli.anio.trim();
      const distractores = elegirAniosCercanos(correcta);
      const opciones = mezclar([correcta, ...distractores]);
      return { enunciado: `📅 ¿En qué año se estrenó «${peli.titulo}»?`, opciones, correcta };
    },
  },
  {
    id: 'peli_por_anio',
    campo: 'anio',
    puede(peli, todas) {
      const mismo = todas.filter(p => p.anio === peli.anio && p.titulo !== peli.titulo);
      const otras = todas.filter(p => p.anio !== peli.anio && p.titulo !== peli.titulo);
      return mismo.length >= 1 && otras.length >= NUM_OPCIONES - 1;
    },
    generar(peli, todas) {
      // Películas de otros años y con distinto título (así no se cuela un remake)
      const otras = todas.filter(p => p.anio !== peli.anio && p.titulo !== peli.titulo);
      // Títulos sin repetir, para que no salgan dos botones iguales
      const titulosOtras = [...new Set(otras.map(p => p.titulo))];
      const distractores = muestra(titulosOtras, NUM_OPCIONES - 1);
      const opciones = mezclar([peli.titulo, ...distractores]);
      return { enunciado: `📽 ¿Cuál de estas películas se estrenó en ${peli.anio || '?'}?`, opciones, correcta: peli.titulo };
    },
  },
  {
    id: 'sinopsis',
    campo: 'sinopsis',
    puede(peli, todas) {
      // Pasamos título y sinopsis a minúsculas para comparar sin importar mayúsculas
      const titulo = peli.titulo.toLowerCase().trim();
      const sinopsis = (peli.sinopsis || '').toLowerCase();
      // Títulos muy cortos ("It", "Us") darían falsos positivos: no los comprobamos
      if (titulo.length <= 3) return true;
      // Solo se puede preguntar si la sinopsis NO contiene el título
      return !sinopsis.includes(titulo);
    },
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
      return todas.filter(p => (p.director || '').trim() !== director && p.titulo !== peli.titulo).length >= NUM_OPCIONES - 1;
    },
    generar(peli, todas) {
      const director = peli.director.trim();
      // Películas de otros directores y con distinto título (así no se cuela un remake)
      const otras = todas.filter(p => (p.director || '').trim() !== director && p.titulo !== peli.titulo);
      // Títulos sin repetir, para que no salgan dos botones iguales
      const titulosOtras = [...new Set(otras.map(p => p.titulo))];
      const distractores = muestra(titulosOtras, NUM_OPCIONES - 1);
      const opciones = mezclar([peli.titulo, ...distractores]);
      return { enunciado: `🎬 ¿Cuál de estas películas está dirigida por ${director}?`, opciones, correcta: peli.titulo };
    },
  },
  {
    id: 'reparto',
    campo: 'reparto',
    puede(peli, todas) {
      // Solo si la película tiene al menos un actor en los datos
      return splitReparto(peli.reparto).length > 0;
    },
    generar(peli, todas) {
      // Elegimos uno de los actores de la película al azar
      const actor = elegirAlAzar(splitReparto(peli.reparto));

      // Títulos de TODAS las películas de la lista en las que sale ese actor
      const titulosConActor = new Set(
        todas.filter(p => splitReparto(p.reparto).includes(actor)).map(p => p.titulo)
      );

      // Opciones falsas: títulos sin repetir en los que ese actor NO sale
      const titulosOtras = [...new Set(todas.map(p => p.titulo))].filter(t => !titulosConActor.has(t));
      const distractores = muestra(titulosOtras, NUM_OPCIONES - 1);

      const opciones = mezclar([peli.titulo, ...distractores]);
      return { enunciado: `🎭 ¿En qué película sale ${actor}?`, opciones, correcta: peli.titulo };
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
  return { tipo: tipo.id, enunciado: r.enunciado, opciones: r.opciones.slice(0, NUM_OPCIONES), correcta: r.correcta };
}
