import sys, types
# Stub streamlit para poder importar app.py sin la UI
st = types.ModuleType("streamlit")
def _noop(*a, **k):
    return None
class _Ctx:
    def __enter__(self): return self
    def __exit__(self, *a): return False
def _passthrough(*a, **k): return _Ctx()
for name in ["set_page_config","markdown","title","caption","error","warning",
             "success","info","stop","dataframe","download_button","text_input",
             "number_input","radio","button","form_submit_button","subheader",
             "checkbox","text_area","rerun","cache_data","cache_resource",
             "columns","expander","form","spinner","sidebar","selectbox"]:
    setattr(st, name, _noop)
class _SS(dict):
    def __getattr__(self, k): return self.get(k)
    def __setattr__(self, k, v): self[k] = v
st.session_state = _SS()
st.columns = lambda spec, **k: [_Ctx() for _ in (spec if isinstance(spec,list) else range(spec))]
st.sidebar = _Ctx()
st.stop = lambda *a,**k: (_ for _ in ()).throw(SystemExit)
sys.modules["streamlit"] = st

def _identity_deco(*a, **k):
    # Soporta @st.cache_data y @st.cache_data(...) 
    if len(a) == 1 and callable(a[0]) and not k:
        return a[0]
    def wrap(f): return f
    return wrap
st.cache_data = _identity_deco
st.cache_resource = _identity_deco

import importlib.util
spec = importlib.util.spec_from_file_location("app", "/nfs/106072397/outputs/app.py")
app = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(app)
except SystemExit:
    pass

# init_db explicito
app.init_database()
conn = app.get_db(); c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bitacora'")
print("tabla bitacora existe:", c.fetchone() is not None)
conn.close()

# Probar registrar + guardar_notas con usuario
app.registrar_bitacora("tester", "PRUEBA", "unidad", 1, "detalle de prueba")
app.guardar_notas("V-123", "MAESTRÍA EN EDUCACIÓN INICIAL",
                  {"Materia X": (3, "18", "2024-I")}, usuario="tester")
regs = app.obtener_bitacora(limite=10)
print("filas en bitacora:", len(regs))
for r in regs:
    print("  ", r["usuario"], "|", r["accion"], "|", r["entidad"], r["entidad_id"], "|", r["detalle"])
