# -*- coding: utf-8 -*-
import sys, types, io, os

class _Dummy:
    def __call__(self, *a, **k): return self
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self): return iter([])
    def __getitem__(self, k): return self
    def __setitem__(self, k, v): pass
    def __getattr__(self, n): return self
    def __bool__(self): return False

class _FakeST:
    def __getattr__(self, n): return _Dummy()
    session_state = _Dummy()

fake = _FakeST()
sys.modules["streamlit"] = fake
sys.modules["streamlit.components"] = types.ModuleType("streamlit.components")
sys.modules["streamlit.components.v1"] = _Dummy()

APP = "/nfs/106072397/outputs/app.py"
with io.open(APP, "r", encoding="utf-8") as f:
    src = f.read()
marker = "# ============================================================\n# INICIALIZACI\u00d3N"
head = src[:src.index(marker)]

ns = {"__name__": "appmod"}
exec(compile(head, APP, "exec"), ns)

# usar DB temporal
ns["DB_FILE"] = "/nfs/106072397/temp/test_expedientes.db"
if os.path.exists(ns["DB_FILE"]):
    os.remove(ns["DB_FILE"])

ns["init_database"]()

# comprobar que la malla oficial se sembró
malla_esp = ns["obtener_malla"]("LICENCIADO/A EN EDUCACI\u00d3N, MENCI\u00d3N EDUCACI\u00d3N ESPECIAL", incluir_introductorio=False)
print("Materias Especial:", len(malla_esp))
for m in malla_esp[:3]:
    print("  po", m["periodo_orden"], "|", m["periodo"], "|", m["materia"], "| UC", m["creditos"])
malla_ini = ns["obtener_malla"]("LICENCIADO/A EN EDUCACI\u00d3N, MENCI\u00d3N EDUCACI\u00d3N INICIAL", incluir_introductorio=False)
print("Materias Inicial:", len(malla_ini))

# registrar un estudiante TSU Especial
datos = {
    "estado": "NUEVA ESPARTA", "municipio": "ARISMENDI", "aula_taller": "",
    "nombres": "ANGELY PAOLA", "apellidos": "ROJAS RIVERO", "cedula": "V-19317478",
    "correo_titular": "", "tipo_programa": "PNF",
    "programa": "LICENCIADO/A EN EDUCACI\u00d3N, MENCI\u00d3N EDUCACI\u00d3N ESPECIAL",
    "tipo_expediente": "CERTIFICACI\u00d3N DE CALIFICACIONES",
    "periodo_culminacion": "2024-II", "sexo": "FEMENINO",
    "tipo_estudiante": "TSU", "periodo_inicio": "2023-I", "periodos_por_anio": 2,
    "observaciones": "", "registrado_por": "tester",
}
try:
    ok, msg = ns["registrar_expediente"](datos, None)
    print("registrar:", ok, msg)
except Exception as e:
    print("registrar EXC:", repr(e))

# cargar notas para todas las materias de la malla especial
notas = {}
for i, m in enumerate(malla_esp):
    nota = 18 if (i % 3) else 17
    if "ACREDITABLES" in m["materia"]:
        nota = "APROBADO"
    notas[m["materia"]] = (m["creditos"], nota)
ns["guardar_notas"]("V-19317478", datos["programa"], notas)
print("notas guardadas:", len(ns["obtener_notas"]("V-19317478")))

# construir row como lo hace la app (dict)
row = dict(datos)
pdf = ns["generar_certificado_pdf"](row)
out = "/nfs/106072397/temp/cert_test.pdf"
with open(out, "wb") as f:
    f.write(pdf)
print("PDF bytes:", len(pdf), "->", out)

# secuencia de periodos comprobación
print("secuencia 4:", ns["_secuencia_periodos"]("2023-I", 2, 4))
