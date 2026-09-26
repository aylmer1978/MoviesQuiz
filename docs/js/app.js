/*
 * app.js — Controlador de la interfaz y bucle de juego.
 * Usa generarPregunta()/construirCache() de quiz.js y el objeto `records`.
 */

const MAX_ERRORES = 3;
const TIEMPO_NORMAL = 10;    // Segundos para responder la mayoría de preguntas
const TIEMPO_SINOPSIS = 20;  // Segundos para las de sinopsis, que hay que leer
const TOP_RECORDS = 3;       // Puestos del ranking (igual que MAX_POR_LISTA en el script de Google)
const MEDALLAS = ['🥇', '🥈', '🥉'];

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
  temporizador: null,   // El setInterval en marcha, para poder pararlo
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
    records.cargarTodo();   // Pedimos los récords a Google en segundo plano, sin esperar
  } catch (e) {
    lista.innerHTML = '<li class="loading">No se pudo cargar el catálogo.</li>';
    console.error(e);
  }
}

function renderCatalogo() {
  const lista = document.getElementById('quizList');
  lista.innerHTML = '';
  for (const quiz of estado.catalogo) {
    const li = document.createElement('li');
    li.className = 'quiz-card';
    li.innerHTML = `
      <div>
        <div class="qc-name">${quiz.nombre}</div>
        <div class="qc-meta">${quiz.num_peliculas} películas · ${quiz.dificultad}</div>
      </div>
    `;
    li.addEventListener('click', () => mostrarLista(quiz));   // Ahora abre la pantalla de la lista
    lista.appendChild(li);
  }
}

function escapar(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// --- Pantalla de lista ---
async function mostrarLista(quiz) {
  estado.quizActual = quiz;

  // Rellenamos los datos de la lista elegida
  document.getElementById('listName').textContent = quiz.nombre;
  document.getElementById('listMeta').textContent = `${quiz.num_peliculas} películas · ${quiz.dificultad}`;
  document.getElementById('listDesc').textContent = quiz.descripcion || '';   // Vacío hasta que haya descripciones

  const rankingDiv = document.getElementById('listRanking');
  rankingDiv.textContent = '⏳ Cargando…';
  mostrarPantalla('screen-list');

  // El ranking llega de Google (normalmente ya estará en memoria)
  const top = await records.getTop(quiz.id);

  // Si mientras esperábamos el jugador ha cambiado de lista, no pintamos nada
  if (estado.quizActual !== quiz) return;
  rankingDiv.innerHTML = htmlRanking(top);
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

// --- Temporizador ---
function iniciarTemporizador(segundos) {
  pararTemporizador();                        // Por si quedaba alguno en marcha
  const total = segundos * 1000;              // Duración en milisegundos
  const fin = Date.now() + total;             // Momento exacto en que se acaba el tiempo
  const barra = document.getElementById('timerBar');
  const texto = document.getElementById('timerText');

  function actualizar() {
    const restante = Math.max(0, fin - Date.now());       // Milisegundos que quedan (nunca negativo)
    barra.style.width = (restante / total) * 100 + '%';   // La barra, en porcentaje
    texto.textContent = Math.ceil(restante / 1000);       // El número, en segundos enteros
    barra.classList.toggle('urgente', restante <= 5000);  // Roja en los últimos 5 segundos

    if (restante === 0) {
      pararTemporizador();
      tiempoAgotado();
    }
  }

  actualizar();                                    // Pintamos el primer estado al instante
  estado.temporizador = setInterval(actualizar, 100);  // Y luego cada 100 ms
}

function pararTemporizador() {
  clearInterval(estado.temporizador);
  estado.temporizador = null;
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
    if (estado.usadas.has(peli.enlace)) continue;
    pregunta = generarPregunta(peli, estado.peliculas, estado.cache);
    if (pregunta) estado.usadas.add(peli.enlace);
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

  // Arrancamos el reloj: más tiempo si es de sinopsis
  const segundos = pregunta.tipo === 'sinopsis' ? TIEMPO_SINOPSIS : TIEMPO_NORMAL;
  iniciarTemporizador(segundos);
}

function responder(seleccion, btn) {
  if (!estado.preguntaActual) return;
    pararTemporizador();
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

function tiempoAgotado() {
  if (!estado.preguntaActual) return;
  const correcta = estado.preguntaActual.correcta;

  // Deshabilitar todos los botones y marcar la respuesta correcta en verde
  document.querySelectorAll('.option-btn').forEach(b => {
    b.disabled = true;
    if (b.textContent.trim().toLowerCase() === correcta.trim().toLowerCase()) b.classList.add('correct');
  });

  // Cuenta como un error
  estado.errores++;
  const feedback = document.getElementById('feedback');
  feedback.textContent = `⏰ ¡Tiempo! Era: ${correcta}`;
  feedback.className = 'feedback err';

  actualizarMarcador();
  document.getElementById('btnNext').hidden = false;
}

// --- Fin de partida ---
function htmlRanking(top) {
  // Convierte [{nombre, puntos}, ...] en una lista HTML con medallas
  if (!top.length) return '<p class="ranking-vacio">Aún no hay récords en esta lista.</p>';
  const medallas = ['🥇', '🥈', '🥉'];
  const filas = top.map((r, i) => `<li>${MEDALLAS[i] || ''} ${escapar(r.nombre)} · ${r.puntos} pts</li>`);
  return `<ol class="ranking">${filas.join('')}</ol>`;
}

async function finalizar() {
  mostrarPantalla('screen-end');
  const total = estado.aciertos;
  document.getElementById('endTitle').textContent =
    estado.errores >= MAX_ERRORES ? '💀 Fin del juego' : '🏁 ¡Lista completada!';
  document.getElementById('endScore').textContent = `Aciertos totales: ${total}`;

  const recordDiv = document.getElementById('endRecord');
  const nameEntry = document.getElementById('nameEntry');
  nameEntry.hidden = true;
  recordDiv.textContent = 'Cargando récords…';

  // Pedimos el ranking fresco: alguien puede haber batido un récord mientras jugabas
  records.refrescar();
  const top = await records.getTop(estado.quizActual.id);

  // Entra en el top si tiene al menos 1 acierto y hay un puesto libre o supera al último
  const hayHueco = top.length < TOP_RECORDS;
  const superaAlUltimo = top.length > 0 && total > top[top.length - 1].puntos;
  const entraEnTop = total > 0 && (hayHueco || superaAlUltimo);

  if (entraEnTop) {
    recordDiv.innerHTML = `🏆 <strong>¡Entras en el top ${TOP_RECORDS}!</strong>` + htmlRanking(top);
    document.getElementById('nameInput').value = '';
    nameEntry.hidden = false;
  } else {
    recordDiv.innerHTML = htmlRanking(top);
  }
}

// --- Eventos globales ---
document.getElementById('btnNext').addEventListener('click', siguientePregunta);
document.getElementById('btnPlay').addEventListener('click', () => empezarQuiz(estado.quizActual));
document.getElementById('btnListBack').addEventListener('click', () => mostrarPantalla('screen-select'));
document.getElementById('btnBack').addEventListener('click', () => {
  // Si ya ha respondido alguna pregunta, pedimos confirmación antes de salir
  if (estado.aciertos + estado.errores > 0) {
    const salir = confirm('¿Seguro que quieres salir? Perderás la partida en curso.');
    if (!salir) return;  // Ha pulsado Cancelar: seguimos jugando
  }
  pararTemporizador();
  renderCatalogo();
  mostrarPantalla('screen-select');
});
document.getElementById('btnPlayAgain').addEventListener('click', () => { renderCatalogo(); mostrarPantalla('screen-select'); });
document.getElementById('btnSaveRecord').addEventListener('click', async () => {
  const btn = document.getElementById('btnSaveRecord');
  const recordDiv = document.getElementById('endRecord');
  const nombre = document.getElementById('nameInput').value;

  btn.disabled = true;                   // Evita guardar dos veces con un doble toque
  recordDiv.textContent = 'Guardando…';

  const ok = await records.save(estado.quizActual.id, nombre, estado.aciertos);
  const top = await records.getTop(estado.quizActual.id);   // Ranking ya actualizado

  document.getElementById('nameEntry').hidden = true;
  recordDiv.innerHTML = (ok ? '✅ ¡Récord guardado!' : '⚠️ No se pudo confirmar el guardado') + htmlRanking(top);
  btn.disabled = false;
});

// Arranque
cargarCatalogo();
