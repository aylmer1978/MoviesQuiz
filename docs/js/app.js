/*
 * app.js — Controlador de la interfaz y bucle de juego.
 * Usa generarPregunta()/construirCache() de quiz.js y el objeto `records`.
 */

const MAX_ERRORES = 3;

const estado = {
  catalogo: [],
  quizActual: null,     // entrada del índice
  peliculas: [],
  cache: null,
  disponibles: [],      // pelis aún por preguntar (barajadas)
  usadas: new Set(),
  aciertos: 0,
  errores: 0,
  preguntaActual: null,
};

// --- Utilidades de pantalla ---
function mostrarPantalla(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

// --- Carga del catálogo ---
async function cargarCatalogo() {
  const lista = document.getElementById('quizList');
  lista.innerHTML = '<li class="loading">Cargando listas…</li>';
  try {
    const res = await fetch('data/index.json');
    estado.catalogo = await res.json();
    await renderCatalogo();
  } catch (e) {
    lista.innerHTML = '<li class="loading">No se pudo cargar el catálogo.</li>';
    console.error(e);
  }
}

async function renderCatalogo() {
  const lista = document.getElementById('quizList');
  lista.innerHTML = '';
  for (const quiz of estado.catalogo) {
    const record = await records.get(quiz.id);
    const li = document.createElement('li');
    li.className = 'quiz-card';
    li.innerHTML = `
      <div>
        <div class="qc-name">${quiz.nombre}</div>
        <div class="qc-meta">${quiz.num_peliculas} películas · ${quiz.dificultad}</div>
      </div>
      <div class="qc-record">${record ? `🥇 ${record.puntos} pts<br>${escapar(record.nombre)}` : '⛔ Sin récord'}</div>
    `;
    li.addEventListener('click', () => empezarQuiz(quiz));
    lista.appendChild(li);
  }
}

function escapar(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// --- Inicio de un quiz ---
async function empezarQuiz(quiz) {
  estado.quizActual = quiz;
  const box = document.getElementById('questionBox');
  box.textContent = 'Cargando películas…';
  document.getElementById('options').innerHTML = '';
  mostrarPantalla('screen-game');

  try {
    const res = await fetch(quiz.archivo);
    estado.peliculas = await res.json();
  } catch (e) {
    box.textContent = 'Error al cargar las películas.';
    return;
  }

  estado.cache = construirCache(estado.peliculas);
  estado.disponibles = mezclar(estado.peliculas);
  estado.usadas = new Set();
  estado.aciertos = 0;
  estado.errores = 0;
  estado.preguntaActual = null;

  document.getElementById('datasetName').textContent = quiz.nombre;
  actualizarMarcador();
  siguientePregunta();
}

function actualizarMarcador() {
  document.getElementById('scoreLabel').textContent =
    `Aciertos: ${estado.aciertos} · Errores: ${estado.errores}/${MAX_ERRORES}`;
}

// --- Bucle de preguntas ---
function siguientePregunta() {
  document.getElementById('feedback').textContent = '';
  document.getElementById('feedback').className = 'feedback';
  document.getElementById('btnNext').hidden = true;

  if (estado.errores >= MAX_ERRORES) return finalizar();

  // Buscar una pregunta válida (hasta agotar disponibles)
  let pregunta = null;
  while (estado.disponibles.length && !pregunta) {
    const peli = estado.disponibles.pop();
    if (estado.usadas.has(peli.titulo)) continue;
    pregunta = generarPregunta(peli, estado.peliculas, estado.cache);
    if (pregunta) estado.usadas.add(peli.titulo);
  }

  if (!pregunta) return finalizar();

  estado.preguntaActual = pregunta;
  document.getElementById('questionBox').textContent = pregunta.enunciado;

  const cont = document.getElementById('options');
  cont.innerHTML = '';
  pregunta.opciones.forEach(opcion => {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.textContent = opcion;
    btn.addEventListener('click', () => responder(opcion, btn));
    cont.appendChild(btn);
  });
}

function responder(seleccion, btn) {
  if (!estado.preguntaActual) return;
  const correcta = estado.preguntaActual.correcta;
  const acierto = seleccion.trim().toLowerCase() === correcta.trim().toLowerCase();

  // Deshabilitar y marcar todos los botones
  document.querySelectorAll('.option-btn').forEach(b => {
    b.disabled = true;
    if (b.textContent.trim().toLowerCase() === correcta.trim().toLowerCase()) b.classList.add('correct');
  });
  if (!acierto) btn.classList.add('wrong');

  const feedback = document.getElementById('feedback');
  if (acierto) {
    estado.aciertos++;
    feedback.textContent = '✅ ¡Correcto!';
    feedback.className = 'feedback ok';
  } else {
    estado.errores++;
    feedback.textContent = `❌ Era: ${correcta}`;
    feedback.className = 'feedback err';
  }
  actualizarMarcador();
  document.getElementById('btnNext').hidden = false;
}

// --- Fin de partida ---
async function finalizar() {
  mostrarPantalla('screen-end');
  const total = estado.aciertos;
  document.getElementById('endTitle').textContent =
    estado.errores >= MAX_ERRORES ? '💀 Fin del juego' : '🏁 ¡Lista completada!';
  document.getElementById('endScore').textContent = `Aciertos totales: ${total}`;

  const record = await records.get(estado.quizActual.id);
  const recordDiv = document.getElementById('endRecord');
  const nameEntry = document.getElementById('nameEntry');
  const esNuevoRecord = !record || total > record.puntos;

  if (esNuevoRecord && total > 0) {
    recordDiv.innerHTML = '🏆 <strong>¡Nuevo récord!</strong>';
    nameEntry.hidden = false;
    document.getElementById('nameInput').value = record ? record.nombre : '';
  } else {
    recordDiv.innerHTML = record
      ? `🥇 Récord actual: ${record.puntos} pts (${escapar(record.nombre)})`
      : 'Sin récord todavía.';
    nameEntry.hidden = true;
  }
}

// --- Eventos globales ---
document.getElementById('btnNext').addEventListener('click', siguientePregunta);
document.getElementById('btnBack').addEventListener('click', () => { renderCatalogo(); mostrarPantalla('screen-select'); });
document.getElementById('btnPlayAgain').addEventListener('click', () => { renderCatalogo(); mostrarPantalla('screen-select'); });
document.getElementById('btnSaveRecord').addEventListener('click', async () => {
  const nombre = document.getElementById('nameInput').value;
  await records.save(estado.quizActual.id, nombre, estado.aciertos);
  document.getElementById('nameEntry').hidden = true;
  document.getElementById('endRecord').innerHTML = '✅ ¡Récord guardado!';
});

// Arranque
cargarCatalogo();
