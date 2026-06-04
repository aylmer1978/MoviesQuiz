# -*- coding: utf-8 -*-
"""
movieQuiz_gui.py
GUI para el quiz de películas. Usa el motor movieQuiz.py y quiz_utils para toda la lógica.
"""

import os
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List, Dict, Optional

import movieQuiz as engine
import quiz_utils


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

        self.csv_dir = os.path.join(os.getcwd(), "csv_quiz")
        self.datasets: List[Dict] = []
        self.peliculas: List[Dict] = []
        self.cache: Dict = {}
        self.usadas: set = set()
        self.aciertos = 0
        self.errores = 0
        self.max_errores = 3
        self.ruta_csv_actual: Optional[str] = None
        self.pregunta_actual: Optional[Dict] = None

        self._build_header()
        self._build_body()
        self._load_datasets()

    # ---- Construcción de la UI ----

    def _build_header(self):
        header = ttk.Frame(self, padding=10)
        header.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(header, text="Carpeta CSV:", font=("Helvetica", 12, "bold")).pack(side=tk.LEFT)
        self.dir_var = tk.StringVar(value=self.csv_dir)
        ttk.Entry(header, textvariable=self.dir_var, width=60).pack(side=tk.LEFT, padx=8)
        ttk.Button(header, text="Cambiar...", command=self._select_dir).pack(side=tk.LEFT, padx=4)
        ttk.Button(header, text="Recargar", command=self._load_datasets).pack(side=tk.LEFT, padx=4)

    def _build_body(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Pestaña selección
        self.tab_select = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_select, text="Selección de lista")

        cols = ("Nombre", "Películas", "Dificultad", "Récord")
        self.tree = ttk.Treeview(self.tab_select, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor=tk.CENTER, width=160 if c != "Nombre" else 360)
        self.tree.pack(expand=True, fill=tk.BOTH)
        ttk.Button(self.tab_select, text="Empezar con la seleccionada",
                   command=self._start_selected).pack(side=tk.RIGHT, pady=8)

        # Pestaña juego
        self.tab_game = ttk.Frame(self.notebook, padding=14)
        self.notebook.add(self.tab_game, text="Juego")

        score_bar = ttk.Frame(self.tab_game)
        score_bar.pack(fill=tk.X, pady=(0, 10))
        self.score_var = tk.StringVar(value="Aciertos: 0 | Errores: 0/3")
        ttk.Label(score_bar, textvariable=self.score_var, font=("Helvetica", 12, "bold")).pack(side=tk.LEFT)
        self.dataset_var = tk.StringVar(value="")
        ttk.Label(score_bar, textvariable=self.dataset_var).pack(side=tk.RIGHT)

        self.question_text = tk.Text(self.tab_game, height=8, wrap=tk.WORD, font=("Helvetica", 14))
        self.question_text.pack(expand=False, fill=tk.BOTH)
        self.question_text.configure(state=tk.DISABLED)

        self.buttons_frame = ttk.Frame(self.tab_game)
        self.buttons_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.option_vars = []
        self.option_buttons = []
        for i in range(3):
            v = tk.StringVar(value=f"Opción {i + 1}")
            btn = ttk.Button(self.buttons_frame, textvariable=v, command=lambda idx=i: self._answer(idx))
            btn.pack(fill=tk.X, pady=6, ipady=10)
            self.option_vars.append(v)
            self.option_buttons.append(btn)

        bottom = ttk.Frame(self.tab_game)
        bottom.pack(fill=tk.X, pady=6)
        self.feedback_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.feedback_var, font=("Helvetica", 12)).pack(side=tk.LEFT)
        ttk.Button(bottom, text="Siguiente", command=self._next).pack(side=tk.RIGHT)

    # ---- Gestión de datasets ----

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
            messagebox.showwarning("Carpeta no válida", f"No existe la carpeta: {folder}")
            return
        archivos = [f for f in os.listdir(folder) if f.endswith(".csv")]
        if not archivos:
            messagebox.showinfo("Sin CSV", "No hay archivos CSV en la carpeta seleccionada.")
            return

        self.datasets = []
        for archivo in archivos:
            ruta = os.path.join(folder, archivo)
            try:
                num_pelis = quiz_utils.contar_lineas_csv(ruta)
                dificultad = engine.calcular_dificultad(num_pelis)
                record_nombre, record_puntos = engine.cargar_record(ruta)
                info_record = (f"🥇 {record_puntos} pts ({record_nombre})"
                               if record_puntos and record_nombre else "⛔ Sin récord")
                self.datasets.append({
                    "nombre": engine.nombre_amigable(archivo),
                    "ruta": ruta,
                    "num_pelis": num_pelis,
                    "dificultad": dificultad,
                    "info_record": info_record,
                })
            except Exception:
                self.datasets.append({
                    "nombre": archivo, "ruta": ruta,
                    "num_pelis": 0, "dificultad": "ERR", "info_record": "ERR",
                })

        self.datasets.sort(key=lambda d: d["num_pelis"], reverse=True)
        for data in self.datasets:
            self.tree.insert("", tk.END, values=(
                data["nombre"], data["num_pelis"], data["dificultad"], data["info_record"]
            ))

    def _start_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Selecciona una lista", "Por favor, selecciona una fila de la tabla.")
            return
        data = self.datasets[self.tree.index(sel[0])]
        self._start_quiz(data["ruta"], data["nombre"])

    # ---- Juego ----

    def _start_quiz(self, ruta_csv: str, nombre_dataset: str):
        try:
            self.peliculas = engine.cargar_peliculas(ruta_csv)
        except Exception as e:
            messagebox.showerror("Error al cargar", f"No se pudo cargar el CSV:\n{ruta_csv}\n\n{e}")
            return

        self.cache = quiz_utils.construir_cache(self.peliculas)
        self.usadas = set()
        self.aciertos = 0
        self.errores = 0
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
        disponibles = [p for p in self.peliculas if p.get('Título') not in self.usadas]
        if not disponibles or self.errores >= self.max_errores:
            self._finalizar()
            return

        pregunta = None
        for _ in range(25):
            peli = random.choice(disponibles)
            pregunta = quiz_utils.generar_pregunta(peli, self.peliculas, self.cache)
            if pregunta:
                self.usadas.add(peli.get('Título'))
                break

        if not pregunta:
            self._finalizar()
            return

        self.pregunta_actual = pregunta
        self._set_question_text(pregunta["enunciado"])
        self.feedback_var.set("")
        for i, btn in enumerate(self.option_buttons):
            self.option_vars[i].set(pregunta["opciones"][i])
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
        total = self.aciertos
        msg = ("💀 Has cometido 3 errores. Fin del juego."
               if self.errores >= self.max_errores
               else "🏁 No hay más preguntas disponibles.")
        record_nombre, record_puntos = engine.cargar_record(self.ruta_csv_actual or "")
        nuevo_record = total > (record_puntos or 0)

        if nuevo_record:
            detalle = f"{msg}\n\n🎯 Aciertos totales: {total}\n\n🏆 ¡Nuevo récord!"
        else:
            detalle = f"{msg}\n\n🎯 Aciertos totales: {total}\n\nRécord actual: {record_puntos} puntos ({record_nombre})."

        if messagebox.askyesno("Fin de la partida", detalle + "\n\n¿Quieres guardar el resultado?"):
            nombre = self._pedir_nombre()
            if nombre:
                engine.guardar_record(self.ruta_csv_actual or "", nombre, total)
                messagebox.showinfo("Guardado", "¡Récord guardado!")

        self.notebook.select(self.tab_select)
        self._load_datasets()

    def _pedir_nombre(self) -> Optional[str]:
        dialog = tk.Toplevel(self)
        dialog.title("Guardar récord")
        dialog.grab_set()
        tk.Label(dialog, text="Introduce tu nombre:", font=("Helvetica", 12)).pack(padx=12, pady=(12, 6))
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
