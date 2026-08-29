import os, re
from openpyxl import Workbook

base = r"G:\Mi unidad\ICEC\ICEC 2026\Proyectos"
modalidades = ["Modalitat A", "Modalitat B", "Modalitat C"]

rows = []
for mod in modalidades:
    folder = os.path.join(base, mod)
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".pdf"):
            continue
        name = fn[:-4]
        m = re.match(r"^(TEC[\d_-]*\d)[_\-](.+)$", name)
        if m:
            codigo, titulo = m.group(1), m.group(2)
        else:
            codigo, titulo = name, ""
        rows.append((mod, codigo, titulo))

wb = Workbook()
ws = wb.active
ws.title = "Proyectos"
ws.append(["Codigo", "Título", "Modalitat"])
for mod, codigo, titulo in rows:
    ws.append([codigo, titulo, mod])

out = os.path.join(base, "Proyectos_ICEC_2026.xlsx")
wb.save(out)
print("Guardado:", out, "filas:", len(rows))
for mod, codigo, titulo in rows:
    print(mod, "|", codigo, "|", titulo)
