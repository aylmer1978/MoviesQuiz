import re
import unicodedata
from openpyxl import load_workbook

base = r"G:\Mi unidad\ICEC\ICEC 2026\Proyectos"
proyectos_path = base + r"\Proyectos_ICEC_2026.xlsx"
lecturas_path = base + r"\Lecturas2026.xlsx"

def norm(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

wb1 = load_workbook(proyectos_path, read_only=True, data_only=True)
ws1 = wb1["Proyectos"]
titulo_to_codigo = {}
for row in ws1.iter_rows(min_row=2, values_only=True):
    codigo, titulo, modalitat = row
    titulo_to_codigo[norm(titulo)] = codigo

# manual overrides for known title variants in Lecturas2026 that don't auto-match
manual = {
    "desenllaç": "TEC07326000043",
    "un concert a la casa blanca": "TEC073_26_000028",
    "la companyia": "TEC073_26_000097",
}
for k, v in manual.items():
    titulo_to_codigo[norm(k)] = v

print("Cargando Lecturas2026.xlsx en modo escritura (puede tardar)...")
wb2 = load_workbook(lecturas_path, data_only=False)
ws2 = wb2["PROYECTOS"]

header = [c.value for c in ws2[1]]
idx_expedient = header.index("EXPEDIENT") + 1
idx_titol = header.index("TÍTOL DEL PROJECTE") + 1

matched = 0
unmatched = []
max_row = ws2.max_row
for r in range(2, max_row + 1):
    titulo = ws2.cell(row=r, column=idx_titol).value
    if titulo is None:
        continue
    key = norm(titulo)
    codigo = titulo_to_codigo.get(key)
    if codigo:
        ws2.cell(row=r, column=idx_expedient).value = codigo
        matched += 1
    else:
        unmatched.append((r, titulo))

print("Filas actualizadas:", matched)
print("Sin match:", unmatched)

wb2.save(lecturas_path)
print("Guardado.")
