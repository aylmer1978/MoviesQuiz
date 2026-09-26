/*
 * records.js — Capa de almacenamiento de récords.
 *
 * Interfaz asíncrona (devuelve Promesas) a propósito: hoy guardamos en
 * localStorage (síncrono envuelto en Promesa), pero mañana podemos cambiar a
 * un backend online (fetch) SIN tocar el resto de la app, solo sustituyendo
 * la implementación de RecordStore.
 */

// Interfaz esperada:
//   get(quizId)            -> Promise<{nombre, puntos} | null>
//   save(quizId, nombre, puntos) -> Promise<void>

class LocalRecordStore {
  constructor(prefijo = 'moviequiz:record:') {
    this.prefijo = prefijo;
  }

  async get(quizId) {
    try {
      const raw = localStorage.getItem(this.prefijo + quizId);
      if (!raw) return null;
      const obj = JSON.parse(raw);
      if (typeof obj.puntos !== 'number') return null;
      return obj;
    } catch {
      return null;
    }
  }

  async save(quizId, nombre, puntos) {
    const limpio = (nombre || '').trim().slice(0, 40) || 'Anónimo';
    localStorage.setItem(this.prefijo + quizId, JSON.stringify({ nombre: limpio, puntos }));
  }
}

// Récords compartidos en Google Sheets (a través de un script de Google)
class RemoteRecordStore {
  constructor(url) {
    this.url = url;
    this.cache = null;   // Aquí guardamos los récords de todas las listas tras la primera petición
  }

  // Pide los récords de todas las listas (solo la primera vez; luego usa la memoria)
  async cargarTodo() {
    if (!this.cache) {
      try {
        const res = await fetch(this.url);
        this.cache = await res.json();
      } catch (e) {
        console.error('No se pudieron cargar los récords', e);
        return {};   // Sin conexión: seguimos sin récords (y se reintentará la próxima vez)
      }
    }
    return this.cache;
  }

  // Olvida la memoria para que la próxima consulta traiga datos frescos
  refrescar() {
    this.cache = null;
  }

  // Los 5 mejores de una lista: [{nombre, puntos}, ...] (vacío si no hay ninguno)
  async getTop(quizId) {
    const todo = await this.cargarTodo();
    return todo[quizId] || [];
  }

  // El mejor de una lista, o null. Mantiene funcionando el app.js actual.
  async get(quizId) {
    const top = await this.getTop(quizId);
    return top.length ? top[0] : null;
  }

  // Envía un récord nuevo. OJO: sin cabecera 'Content-Type' a propósito,
  // porque los scripts de Google rechazan las peticiones que la llevan.
    // Envía un récord nuevo. OJO: sin cabecera 'Content-Type' a propósito,
  // porque los scripts de Google rechazan las peticiones que la llevan.
  async save(quizId, nombre, puntos) {
    try {
      const res = await fetch(this.url, {
        method: 'POST',
        body: JSON.stringify({ lista: quizId, nombre, puntos }),
      });
      const datos = await res.json();
      return datos.ok;
    } catch (e) {
      console.error('No se pudo guardar el récord', e);
      return false;
    } finally {
      // Pase lo que pase, olvidamos la memoria:
      // la próxima consulta traerá el ranking actualizado desde Google
      this.refrescar();
    }
  }
}

// Implementación activa actualmente:
const records = new RemoteRecordStore('https://script.google.com/macros/s/AKfycbwSNWqBvnaQQddr6CaVtRyuYmWuts3D_D8toJcbGCCf6ZfxaBCPnzC1p7ie2mz_UQa7/exec');
