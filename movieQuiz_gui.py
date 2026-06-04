# -*- coding: utf-8 -*-
"""
movieQuiz_gui.py
GUI para el quiz de películas basada en el motor movieQuiz.py.

- No requiere dependencias externas (usa tkinter de la librería estándar).
- Detecta automáticamente los CSV en la carpeta ./csv_quiz (o deja elegir otra carpeta).
- Usa funciones del motor (cargar_peliculas, elegir_opciones_correcta_y_distractores, calcular_dificultad,
  nombre_amigable, cargar_record, guardar_record) si están disponibles.
- Implementa su propio bucle de juego con la misma lógica de tipos de pregunta
  (director, año, peli_por_año, género, sinopsis).
"""

import os
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Optional

# Importamos el motor
try:
    import movieQuiz as engine
except Exception as e:
    engine = None

# ---- Funciones de compatibilidad (fallback) ----

def _cargar_peliculas(ruta_csv: str) -> List[Dict]:
    if engine and hasattr(engine, "cargar_peliculas"):
        return engine.cargar_peliculas(ruta_csv)
    # Fallback mínimo si no existe la función en el motor
    import csv
    with open(ruta_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def _elegir_opciones_correcta_y_distractores(correcta: str, todas: List[Dict], campo: str, cantidad: int = 3) -> List[str]:
    if engine and hasattr(engine, "elegir_opciones_correcta_y_distractores"):
        return engine.elegir_opciones_correcta_y_distractores(correcta, todas, campo, cantidad)
    # Fallback simple
    opciones = {correcta}
    intentos = 0
    import random as _rnd
    while len(opciones) < cantidad and intentos < 200:
        opcion = _rnd.choice(todas).get(campo, "").strip()
        if opcion and opcion.lower() != correcta.lower():
            opciones.add(opcion)
        intentos += 1
    lista = list(opciones)
    _rnd.shuffle(lista)
    return lista

def _calcular_dificultad(num_peliculas: int) -> str:
    if engine and hasattr(engine, "calcular_dificultad"):
        return engine.calcular_dificultad(num_peliculas)
    if num_peliculas <= 50:
        return "🟢 FÁCIL"
    elif num_peliculas <= 120:
        return "🟡 MEDIA"
    elif num_peliculas <= 300:
        return "🔴 DIFÍCIL"
    else:
        return "⚫ EXTREMA"

def _nombre_amigable(nombre_archivo: str) -> str:
    if engine and hasattr(engine, "nombre_amigable"):
        return engine.nombre_amigable(nombre_archivo)
    base = os.path.splitext(nombre_archivo)[0]
    base = base.replace("_quiz", "").replace("-", " ")
    return base.upper()

def _cargar_record(ruta_csv: str):
    if engine and hasattr(engine, "cargar_record"):
        return engine.cargar_record(ruta_csv)
    # Fallback (misma convención que el motor)
    base = os.path.splitext(os.path.basename(ruta_csv))[0]
    record_path = os.path.join("records", f"{base}.record")
    if os.path.exists(record_path):
        with open(record_path, "r", encoding="utf-8") as f:
            nombre, puntos = f.read().strip().split(" - ")
            return nombre, int(puntos)
    return None, 0

def _guardar_record(ruta_csv: str, nombre: str, puntuacion: int):
    if engine and hasattr(engine, "guardar_record"):
        return engine.guardar_record(ruta_csv, nombre, puntuacion)
    # Fallback
    os.makedirs("records", exist_ok=True)
    base = os.path.splitext(os.path.basename(ruta_csv))[0]
    record_path = os.path.join("records", f"{base}.record")
    with open(record_path, "w", encoding="utf-8") as f:
        f.write(f"{nombre} - {puntuacion}")

# ---- Lógica de generación de preguntas (reusa la del motor) ----

TIPOS = ("director", "año", "peli_por_año", "genero", "sinopsis")

def generar_pregunta(pelicula: Dict, todas: List[Dict]):
    posibles_tipos = []
    if pelicula.get('Director(es)', '').strip():
        posibles_tipos.append("director")
    if pelicula.get('Año', '').strip():
        posibles_tipos.append("año")
        posibles_tipos.append("peli_por_año")
    if pelicula.get('Géneros', '').strip():
        posibles_tipos.append("genero")
    if pelicula.get('Sinopsis', '').strip():
        posibles_tipos.append("sinopsis")
    if not posibles_tipos:
        return None

    tipo = random.choice(posibles_tipos)
    titulo = pelicula.get('Título', '').strip()

    if tipo == "director":
        correcta = pelicula['Director(es)'].strip()
        opciones = _elegir_opciones_correcta_y_distractores(correcta, todas, 'Director(es)')
        enunciado = f"🎬 ¿Quién ha dirigido la película de {pelicula.get('Año','?')}, «{titulo}»?"

    elif tipo == "año":
        correcta = pelicula['Año'].strip()
        opciones = _elegir_opciones_correcta_y_distractores(correcta, todas, 'Año')
        enunciado = f"📅 ¿En qué año se estrenó «{titulo}»?"

    elif tipo == "peli_por_año":
        correcta = titulo
        mismo_anio = [p for p in todas if p.get('Año') == pelicula.get('Año') and p.get('Título') != titulo]
        if len(mismo_anio) < 1:
            return None
        otras = [p for p in todas if p.get('Año') != pelicula.get('Año')]
        if len(otras) < 2:
            return None
        distractores = random.sample(otras, k=2)
        opciones = [correcta] + [p['Título'] for p in distractores]
        random.shuffle(opciones)
        enunciado = f"📽 ¿Cuál de estas películas se estrenó en {pelicula.get('Año','?')}?"

    elif tipo == "genero":
        enunciado, opciones, correcta = generar_pregunta_genero_gui(pelicula, todas, campo='Géneros')
        if not opciones:
            return None

    elif tipo == "sinopsis":
        correcta = titulo
        opciones = _elegir_opciones_correcta_y_distractores(correcta, todas, 'Título')
        sinopsis = (pelicula.get('Sinopsis','') or '').strip()
        enunciado = "📝 ¿A qué película pertenece esta sinopsis?\n\n" + f"\"{sinopsis}\""

    else:
        return None

    return {
        "tipo": tipo,
        "enunciado": enunciado,
        "opciones": opciones[:3],
        "correcta": correcta,
    }

# ---- GUI ----

class QuizGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Movie Quiz")
        self.geometry("900x600")
        self.minsize(800, 520)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        # Estado
        self.csv_dir = os.path.join(os.getcwd(), "csv_quiz")
        self.datasets = []  # [{nombre, ruta, num_pelis, dificultad, info_record}]
        self.peliculas = []
        self.usadas = set()
        self.aciertos = 0
        self.errores = 0
        self.max_errores = 3
        self.ruta_csv_actual: Optional[str] = None
        self.pregunta_actual = None

        # Construcción UI
        self._build_header()
        self._build_body()
        self._load_datasets()

    # ---- UI construction ----
    def _build_header(self):
        header = ttk.Frame(self, padding=10)
        header.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(header, text="Carpeta CSV:", font=("Helvetica", 12, "bold")).pack(side=tk.LEFT)
        self.dir_var = tk.StringVar(value=self.csv_dir)
        dir_entry = ttk.Entry(header, textvariable=self.dir_var, width=60)
        dir_entry.pack(side=tk.LEFT, padx=8)
        ttk.Button(header, text="Cambiar...", command=self._select_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(header, text="Recargar", command=self._load_datasets).pack(side=tk.LEFT, padx=4)

    def _build_body(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Pestaña selección de dataset
        self.tab_select = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_select, text="Selección de lista")

        cols = ("Nombre", "Películas", "Dificultad", "Récord")
        self.tree = ttk.Treeview(self.tab_select, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor=tk.CENTER, width=160 if c != "Nombre" else 360)
        self.tree.pack(expand=True, fill=tk.BOTH)

        btns = ttk.Frame(self.tab_select)
        btns.pack(fill=tk.X, pady=8)
        ttk.Button(btns, text="Empezar con la seleccionada", command=self._start_selected).pack(side=tk.RIGHT)

        # Pestaña juego
        self.tab_game = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.tab_game, text="Juego")

        # Marcadores
        score_bar = ttk.Frame(self.tab_game)
        score_bar.pack(fill=tk.X, pady=(0,10))
        self.score_var = tk.StringVar(value="Aciertos: 0 | Errores: 0/3")
        ttk.Label(score_bar, textvariable=self.score_var, font=("Helvetica", 12, "bold")).pack(side=tk.LEFT)
        self.dataset_var = tk.StringVar(value="")
        ttk.Label(score_bar, textvariable=self.dataset_var).pack(side=tk.RIGHT)

        # Enunciado
        self.question_text = tk.Text(self.tab_game, height=8, wrap=tk.WORD, font=("Helvetica", 14))
        self.question_text.pack(expand=False, fill=tk.BOTH)
        self.question_text.configure(state=tk.DISABLED)

        # Opciones
        self.buttons_frame = ttk.Frame(self.tab_game)
        self.buttons_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.option_vars = []
        self.option_buttons = []
        for i in range(3):
            v = tk.StringVar(value=f"Opción {i+1}")
            btn = ttk.Button(self.buttons_frame, textvariable=v, command=lambda idx=i: self._answer(idx))
            btn.pack(fill=tk.X, pady=6, ipady=10)
            self.option_vars.append(v)
            self.option_buttons.append(btn)

        # Barra inferior
        bottom = ttk.Frame(self.tab_game)
        bottom.pack(fill=tk.X, pady=6)
        self.feedback_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.feedback_var, font=("Helvetica", 12)).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Siguiente", command=self._next).pack(side=tk.RIGHT)

    # ---- Dataset management ----
    def _select_dir(self):
        newdir = filedialog.askdirectory(initialdir=self.csv_dir, title="Selecciona carpeta con CSV")
        if newdir:
            self.dir_var.set(newdir)
            self.csv_dir = newdir
            self._load_datasets()

    
    def _load_datasets(self):
        self.tree.delete(*self.tree.get_children())
        folder = self.dir_var.get().strip() or os.path.join(os.getcwd(), "csv_quiz")
        self.csv_dir = folder
        if not os.path.isdir(folder):
            messagebox.showwarning("Carpeta no válida", f"No existe la carpeta:{folder}")
            return
        archivos = [f for f in os.listdir(folder) if f.endswith(".csv")]
        if not archivos:
            messagebox.showinfo("Sin CSV", "No hay archivos CSV en la carpeta seleccionada.")
            return

        self.datasets = []
        for archivo in archivos:
            ruta = os.path.join(folder, archivo)
            try:
                pelis = _cargar_peliculas(ruta)
                num_pelis = len(pelis)
                dificultad = _calcular_dificultad(num_pelis)
                record_nombre, record_puntos = _cargar_record(ruta)
                info_record = f"🥇 {record_puntos} pts ({record_nombre})" if record_puntos and record_nombre else "⛔ Sin récord"
                nombre_legible = _nombre_amigable(archivo)
                self.datasets.append({
                    "nombre": nombre_legible,
                    "ruta": ruta,
                    "num_pelis": num_pelis,
                    "dificultad": dificultad,
                    "info_record": info_record
                })
            except Exception as e:
                self.datasets.append({
                    "nombre": archivo,
                    "ruta": ruta,
                    "num_pelis": 0,
                    "dificultad": "ERR",
                    "info_record": "ERR"
                })

        # 🔹 Ordenar por número de películas (mayor a menor)
        self.datasets.sort(key=lambda d: d["num_pelis"], reverse=True)

        # Insertar en el Treeview en el nuevo orden
        for data in self.datasets:
            self.tree.insert("", tk.END, values=(data["nombre"], data["num_pelis"], data["dificultad"], data["info_record"]))


    def _start_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Selecciona una lista", "Por favor, selecciona una fila de la tabla.")
            return
        idx = self.tree.index(sel[0])
        data = self.datasets[idx]
        self._start_quiz(data["ruta"], data["nombre"])

    # ---- Gameplay ----
    def _start_quiz(self, ruta_csv: str, nombre_dataset: str):
        try:
            self.peliculas = _cargar_peliculas(ruta_csv)
        except Exception as e:
            messagebox.showerror("Error al cargar", f"No se pudo cargar el CSV:\n{ruta_csv}\n\n{e}")
            return

        self.usadas = set()
        self.aciertos = 0
        self.errores = 0
        self.max_errores = 3
        self.ruta_csv_actual = ruta_csv
        self.dataset_var.set(f"Lista: {nombre_dataset}")
        self.notebook.select(self.tab_game)
        self._update_score()
        self._nueva_pregunta()

    def _update_score(self):
        self.score_var.set(f"Aciertos: {self.aciertos} | Errores: {self.errores}/{self.max_errores}")

    def _set_question_text(self, text: str):
        self.question_text.configure(state=tk.NORMAL)
        self.question_text.delete("1.0", tk.END)
        self.question_text.insert(tk.END, text.strip())
        self.question_text.configure(state=tk.DISABLED)

    def _nueva_pregunta(self):
        # Elegimos una película no usada
        disponibles = [p for p in self.peliculas if p.get('Título') not in self.usadas]
        if not disponibles or self.errores >= self.max_errores:
            self._finalizar()
            return

        base = 0
        intento = 0
        pregunta = None
        # Hasta 25 intentos para conseguir una pregunta válida (por si falta info en algunas pelis)
        while intento < 25 and pregunta is None:
            peli = random.choice(disponibles)
            pregunta = generar_pregunta(peli, self.peliculas)
            if pregunta:
                self.usadas.add(peli.get('Título'))
                break
            intento += 1

        if not pregunta:
            self._finalizar()
            return

        self.pregunta_actual = pregunta
        self._set_question_text(pregunta["enunciado"])
        self.feedback_var.set("")
        opciones = pregunta["opciones"]
        for i, btn in enumerate(self.option_buttons):
            self.option_vars[i].set(opciones[i])
            btn.state(["!disabled"])

    def _answer(self, idx: int):
        if not self.pregunta_actual:
            return
        seleccion = self.pregunta_actual["opciones"][idx].strip()
        correcta = self.pregunta_actual["correcta"].strip()
        if seleccion.lower() == correcta.lower():
            self.aciertos += 1
            self.feedback_var.set("✅ ¡Correcto!")
        else:
            self.errores += 1
            self.feedback_var.set(f"❌ Incorrecto. La respuesta correcta era: {correcta}")
        for b in self.option_buttons:
            b.state(["disabled"])
        self._update_score()

    def _next(self):
        if self.errores >= self.max_errores:
            self._finalizar()
            return
        self._nueva_pregunta()

    def _finalizar(self):
        # Mensaje final y récords
        total = self.aciertos
        msg = "💀 Has cometido 3 errores. Fin del juego." if self.errores >= self.max_errores else "🏁 No hay más preguntas disponibles."
        record_nombre, record_puntos = _cargar_record(self.ruta_csv_actual or "")
        nuevo_record = record_puntos is None or total > (record_puntos or 0)

        if nuevo_record:
            detalle = f"{msg}\n\n🎯 Aciertos totales: {total}\n\n🏆 ¡Nuevo récord!"
        else:
            detalle = f"{msg}\n\n🎯 Aciertos totales: {total}\n\nRécord actual: {record_puntos} puntos ({record_nombre})."

        if messagebox.askyesno("Fin de la partida", detalle + "\n\n¿Quieres guardar el resultado?"):
            nombre = self._pedir_nombre()
            if nombre:
                _guardar_record(self.ruta_csv_actual or "", nombre, total)
                messagebox.showinfo("Guardado", "¡Récord guardado!")
        # Vuelve a la pestaña de selección y recarga
        self.notebook.select(self.tab_select)
        self._load_datasets()

    def _pedir_nombre(self) -> Optional[str]:
        dialog = tk.Toplevel(self)
        dialog.title("Guardar récord")
        dialog.grab_set()
        tk.Label(dialog, text="Introduce tu nombre:", font=("Helvetica", 12)).pack(padx=12, pady=(12,6))
        v = tk.StringVar()
        e = ttk.Entry(dialog, textvariable=v, width=32)
        e.pack(padx=12, pady=6)
        e.focus_set()
        out = {"nombre": None}
        def ok():
            out["nombre"] = (v.get() or "").strip()[:40]
            dialog.destroy()
        def cancel():
            dialog.destroy()
        btns = ttk.Frame(dialog)
        btns.pack(pady=10)
        ttk.Button(btns, text="Aceptar", command=ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="Cancelar", command=cancel).pack(side=tk.LEFT, padx=6)
        dialog.wait_window()
        return out["nombre"]

def main():
    app = QuizGUI()
    app.mainloop()

if __name__ == "__main__":
    main()


# --- Utilidades para preguntas de género (mismo idioma) ---

def _split_generos(cadena):
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

def _idioma_genero(g):
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

def _conjunto_generos_por_idioma(peliculas, campo='Géneros'):
    ges, gen = set(), set()
    for p in peliculas:
        for g in _split_generos(p.get(campo, '')):
            if _idioma_genero(g) == 'es':
                ges.add(g.strip())
            else:
                gen.add(g.strip())
    return ges, gen

def elegir_distractores_genero_gui(correcta, todas, campo='Géneros', k=2):
    idioma = _idioma_genero(correcta)
    ges, gen = _conjunto_generos_por_idioma(todas, campo)
    pool = (ges if idioma == 'es' else gen).copy()
    pool = {g for g in pool if g.casefold().strip(' .') != correcta.casefold().strip(' .')}
    if len(pool) < k:
        respaldo = (gen if idioma == 'es' else ges).copy()
        respaldo = {g for g in respaldo if g.casefold().strip(' .') != correcta.casefold().strip(' .')}
        combinados = list(pool) + list(respaldo)
        # de-duplicar manteniendo orden
        seen=set(); combinados=[x for x in combinados if not (x in seen or seen.add(x))]
        return combinados[:k] if len(combinados) < k else random.sample(combinados, k)
    else:
        return random.sample(list(pool), k)

def generar_pregunta_genero_gui(pelicula, todas, campo='Géneros'):
    titulo = pelicula.get('Título','').strip()
    generos_peli = _split_generos(pelicula.get(campo, ''))
    if not generos_peli:
        return None, None, None
    correcta = random.choice(generos_peli).strip()
    distractores = elegir_distractores_genero_gui(correcta, todas, campo=campo, k=2)
    opciones = [correcta] + distractores
    random.shuffle(opciones)
    enunciado = f"🎭 ¿Cuál es uno de los géneros de «{titulo}»?"
    return enunciado, opciones, correcta
