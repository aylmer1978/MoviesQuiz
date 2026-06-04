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

/*
 * Para activar récords online en el futuro, crea una clase con la misma interfaz:
 *
 * class RemoteRecordStore {
 *   constructor(baseUrl) { this.baseUrl = baseUrl; }
 *   async get(quizId) {
 *     const r = await fetch(`${this.baseUrl}/records/${quizId}`);
 *     return r.ok ? r.json() : null;
 *   }
 *   async save(quizId, nombre, puntos) {
 *     await fetch(`${this.baseUrl}/records/${quizId}`, {
 *       method: 'POST',
 *       headers: { 'Content-Type': 'application/json' },
 *       body: JSON.stringify({ nombre, puntos }),
 *     });
 *   }
 * }
 *
 * Y en app.js cambiar:  const records = new RemoteRecordStore('https://...');
 */

// Implementación activa actualmente:
const records = new LocalRecordStore();
