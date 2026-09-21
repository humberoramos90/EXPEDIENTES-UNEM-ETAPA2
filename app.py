import streamlit as st
import sqlite3
import hashlib
import os
import time
from datetime import datetime
import pandas as pd
from io import BytesIO
import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import json
import re
# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================
st.set_page_config(
    page_title="Expedientes UNEM",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ocultar barra superior, menú nativo, toolbar de desarrollador y footer
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    .stActionButton {display: none !important;}
    div[class*="stAppToolbar"] {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    [data-testid="stHeader"] {background: transparent !important;}
    /* Forzar que el menu lateral SIEMPRE este visible y no se pueda esconder */
    section[data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        transform: none !important;
        margin-left: 0 !important;
        min-width: 240px !important;
        width: 240px !important;
    }
    section[data-testid="stSidebar"][aria-expanded="false"] {
        transform: none !important;
        margin-left: 0 !important;
        width: 240px !important;
        min-width: 240px !important;
    }
    /* Mantener visible la flecha para abrir el menu, por si acaso */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {display: flex !important; visibility: visible !important; opacity: 1 !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

DB_FILE = "expedientes.db"
UPLOAD_FOLDER = "uploads_pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
MAX_PDF_SIZE = 5 * 1024 * 1024  # 5MB

# Correo por defecto (Admin lo configura después)
SMTP_CONFIG_FILE = "smtp_config.json"
EMAIL_TEMPLATES_FILE = "email_templates.json"
# ============================================================
# DATOS DE VENEZUELA
# ============================================================

ESTADOS_MUNICIPIOS = {
    "Amazonas": ["Alto Orinoco", "Atabapo", "Atures", "Autana", "Manapiare", "Maroa", "Río Negro"],
    "Anzoátegui": ["Anaco", "Aragua", "Bolívar", "Bruzual", "Carvajal", "Cajigal", "Freites", "Guanipa", "Guanta", "Independencia", "Libertad", "MacGregor", "Miranda", "Monagas", "Peñalver", "Píritu", "San Juan de Capistrano", "Santa Ana", "Simón Rodríguez", "Sir Arthur McGregor", "Sotillo"],
    "Apure": ["Achaguas", "Biruaca", "Muñoz", "Páez", "Pedro Camejo", "Rómulo Gallegos", "San Fernando"],
    "Aragua": ["Alcántara", "Camatagua", "Girardot", "Iragorry", "Lamas", "Libertador", "Mariño", "Michelena", "Ocumare de la Costa de Oro", "Revenga", "Ribas", "San Casimiro", "San Sebastián", "Santiago Mariño", "Sucre", "Tovar", "Urdaneta", "Zamora"],
    "Barinas": ["Alberto Arvelo Torrealba", "Andrés Eloy Blanco", "Antonio José de Sucre", "Arismendi", "Barinas", "Bolívar", "Cruz Paredes", "Ezequiel Zamora", "Obispos", "Pedraza", "Rojas", "Sosa"],
    "Bolívar": ["Angostura (antiguo Raúl Leoni)", "Caroní", "Cedeño", "El Callao", "Gran Sabana", "Heres", "Piar", "Roscio", "Sifontes", "Sucre", "Padre Pedro Chien"],
    "Carabobo": ["Bejuma", "Carlos Arvelo", "Diego Ibarra", "Guacara", "Juan José Mora", "Libertador", "Los Guayos", "Miranda", "Montalbán", "Naguanagua", "Puerto Cabello", "San Diego", "San Joaquín", "Valencia"],
    "Cojedes": ["Anzoátegui", "Falcón", "Girardot", "Lima Blanco", "Pao de San Juan Bautista", "Ricaurte", "Rómulo Gallegos", "San Carlos", "Tinaco"],
    "Delta Amacuro": ["Antonio Díaz", "Casacoima", "Pedernales", "Tucupita"],
    "Distrito Capital": ["Libertador"],
    "Falcón": ["Acosta", "Bolívar", "Buchivacoa", "Cacique Manaure", "Carirubana", "Colina", "Dabajuro", "Democracia", "Falcón", "Federación", "Jacura", "Los Taques", "Mauroa", "Miranda", "Monseñor Iturriza", "Palmasola", "Petit", "Píritu", "San Francisco", "Silva", "Sucre", "Tocópero", "Unión", "Urumaco", "Zamora"],
    "Guárico": ["Camaguán", "Chaguaramas", "El Socorro", "Infante", "Las Mercedes", "Mellado", "Miranda", "Monagas", "Ortiz", "Ribas", "Roscio", "San Gerónimo de Guayabal", "San José de Guaribe", "Santa María de Ipire", "Zaraza"],
    "Lara": ["Andrés Eloy Blanco", "Crespo", "Iribarren", "Jiménez", "Morán", "Palavecino", "Simón Planas", "Torres", "Urdaneta"],
    "Mérida": ["Alberto Adriani", "Andrés Bello", "Antonio Pinto Salinas", "Aricagua", "Arzobispo Chacón", "Campo Elías", "Caracciolo Parra Olmedo", "Cardenal Quintero", "Guaraque", "Julio César Salas", "Justo Briceño", "Libertador", "Miranda", "Obispo Ramos de Lora", "Padre Noguera", "Pueblo Llano", "Rangel", "Rivas Dávila", "Santos Marquina", "Sucre", "Tovar", "Tulio Febres Cordero", "Zea"],
    "Miranda": ["Acevedo", "Andrés Bello", "Baruta", "Brión", "Buroz", "Carrizal", "Chacao", "Cristóbal Rojas", "El Hatillo", "Guaicaipuro", "Independencia", "Lander", "Los Salias", "Páez", "Paz Castillo", "Pedro Gual", "Plaza", "Simón Bolívar", "Sucre", "Urdaneta", "Zamora"],
    "Monagas": ["Acosta", "Aguasay", "Bolívar", "Caripe", "Cedeño", "Ezequiel Zamora", "Libertador", "Maturín", "Piar", "Punceres", "Santa Bárbara", "Sotillo", "Uracoa"],
    "Nueva Esparta": ["Arismendi", "García", "Maneiro", "Marcano", "Mariño", "Península de Macanao", "Tubores", "Villalba", "Díaz", "Antolín del Campo", "Bermúdez"],
    "Portuguesa": ["Agua Blanca", "Araure", "Esteller", "Guanare", "Guanarito", "Monseñor José Vicente de Unda", "Ospino", "Páez", "Papelón", "San Genaro de Boconoíto", "San Rafael de Onoto", "Santa Rosalía", "Sucre", "Turén"],
    "Sucre": ["Andrés Eloy Blanco", "Andrés Bello", "Arismendi", "Benítez", "Bermúdez", "Bolívar", "Cajigal", "Cruz Salmerón Acosta", "Libertador", "Mariño", "Mejía", "Montes", "Ribero", "Sucre", "Valdez"],
    "Táchira": ["Andrés Bello", "Antonio Rómulo Costa", "Ayacucho", "Bolívar", "Cárdenas", "Córdoba", "Fernández Feo", "Francisco de Miranda", "García de Hevia", "Guásimos", "Independencia", "Jáuregui", "José María Vargas", "Junín", "Libertad", "Libertador", "Lobatera", "Michelena", "Panamericano", "Pedro María Ureña", "Delicias", "Samuel Darío Maldonado", "San Cristóbal", "Seboruco", "Simón Rodríguez", "Sucre", "Torbes", "Uribante", "San Judas Tadeo"],
    "Trujillo": ["Andrés Bello", "Boconó", "Bolívar", "Candelaria", "Carache", "Carvajal", "Campo Elías", "Cuicas", "Escuque", "Juan Vicente Campos Elías", "La Ceiba", "Miranda", "Monte Carmelo", "Motatán", "Pampán", "Pampanito", "Rafael Rangel", "San Rafael de Carvajal", "Sucre", "Trujillo", "Urdaneta", "Valera"],
    "La Guaira": ["Vargas"],
    "Yaracuy": ["Arístides Bastidas", "Bolívar", "Bruzual", "Cocorote", "Independencia", "José Antonio Páez", "La Trinidad", "Nirgua", "Peña", "San Felipe", "Sucre", "Urachiche", "Veroes", "Manuel Monge"],
    "Zulia": ["Almirante Padilla", "Baralt", "Cabimas", "Catatumbo", "Colón", "Francisco Javier Pulgar", "Guajira", "Jesús Enrique Lossada", "Jesús María Semprún", "La Cañada de Urdaneta", "Lagunillas", "Machiques de Perijá", "Mara", "Maracaibo", "Miranda", "Rosario de Perijá", "San Francisco", "Santa Rita", "Simón Bolívar", "Sucre", "Valmore Rodríguez"],
}

TIPOS_PROGRAMA_PROGRAMAS = {
    "PNF": [
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN BIOLOGÍA",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN DESARROLLO INSTITUCIONAL",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN FÍSICA",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN DE JÓVENES, ADULTOS Y ADULTAS",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN FÍSICA",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN MEMORIA, TERRITORIO Y CIUDADANÍA",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN INGLÉS",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN LENGUA",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN MATEMÁTICA",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN PRIMARIA",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN INICIAL",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN QUÍMICA",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN ESPECIAL",
        "LICENCIATURA EN EDUCACIÓN INDÍGENA MENCIÓN EDUCACIÓN INICIAL",
        "LICENCIATURA EN EDUCACIÓN INDÍGENA MENCIÓN EDUCACIÓN PRIMARIA",
        "LICENCIATURA EN EDUCACIÓN INDÍGENA MENCIÓN EDUCACIÓN MEDIA",
    ],
    "PNFA_E": [
        "ESPECIALIZACIÓN EN EDUCACIÓN INICIAL",
        "ESPECIALIZACIÓN EN EDUCACIÓN PRIMARIA",
        "ESPECIALIZACIÓN EN EDUCACIÓN EN CIENCIAS NATURALES",
        "ESPECIALIZACIÓN EN MATEMÁTICA",
        "ESPECIALIZACIÓN EN LENGUA Y COMUNICACIÓN",
        "ESPECIALIZACIÓN EN GEOGRAFÍA, HISTORIA Y CIUDADANÍA",
        "ESPECIALIZACIÓN EN LENGUA EXTRANJERA: INGLÉS",
        "ESPECIALIZACIÓN EN EDUCACIÓN FÍSICA",
        "ESPECIALIZACIÓN EN EDUCACIÓN EN AGROECOLOGÍA",
        "ESPECIALIZACIÓN EN PEDAGOGÍA CULTURAL E INTERCULTURALIDAD",
        "ESPECIALIZACIÓN EN DERECHO DE NIÑOS, NIÑAS Y ADOLESCENTES, CONVIVENCIA SOLIDARIA Y PAZ",
        "ESPECIALIZACIÓN EN EDUCACIÓN Y TECNOLOGÍA DE LA INFORMACIÓN Y COMUNICACIÓN",
        "ESPECIALIZACIÓN EN EDUCACIÓN Y TRABAJO",
        "ESPECIALIZACIÓN EN DIRECCIÓN Y SUPERVISIÓN EDUCATIVA",
        "ESPECIALIZACIÓN EN EDUCACIÓN ESPECIAL",
        "ESPECIALIZACIÓN EN LENGUA EXTRANJERA INGLÉS PARA PRIMARIA",
        "ESPECIALIZACIÓN EN EDUCACIÓN MEDIA TÉCNICA Y PROFESIONAL",
        "ESPECIALIZACIÓN EN EDUCACIÓN EN FRONTERAS",
        "ESPECIALIZACIÓN EN EDUCACIÓN INDÍGENA",
        "ESPECIALIZACIÓN EN EDUCACIÓN DE JÓVENES, ADULTOS Y ADULTAS",
        "ESPECIALIZACIÓN EN PROMOCIÓN DE LA LECTURA Y LITERATURA INFANTIL",
        "ESPECIALIZACIÓN EN EDUCACIÓN DE LA SEXUALIDAD",
    ],
    "PNFA_M": [
        "MAESTRÍA EN EDUCACIÓN INICIAL",
        "MAESTRÍA EN EDUCACIÓN PRIMARIA",
        "MAESTRÍA EN CIENCIAS NATURALES PARA EDUCACIÓN MEDIA",
        "MAESTRÍA EN MATEMÁTICA PARA EDUCACIÓN MEDIA",
        "MAESTRÍA EN LENGUA Y COMUNICACIÓN PARA EDUCACIÓN MEDIA",
        "MAESTRÍA EN GEOGRAFÍA, HISTORIA Y CIUDADANÍA PARA EDUCACIÓN MEDIA",
        "MAESTRÍA EN INGLÉS PARA EDUCACIÓN MEDIA",
        "MAESTRÍA EN EDUCACIÓN FÍSICA PARA EDUCACIÓN MEDIA",
        "MAESTRÍA EN DIRECCIÓN Y SUPERVISIÓN EDUCATIVA",
        "MAESTRÍA EN EDUCACIÓN EN FRONTERAS",
        "MAESTRÍA EN EDUCACIÓN INDÍGENA",
    ],
    "PNFA_D": [
        "DOCTOR(A) EN EDUCACIÓN",
    ],
}

TIPOS_EXPEDIENTE = ["INGRESO", "PROSECUCION", "EGRESADO"]

ROLES = ["ADMIN_PRINCIPAL", "ADMIN_AUXILIAR", "ADMIN_REGIONAL"]

# ============================================================
# BASE DE DATOS - Funciones
# ============================================================

def get_db():
    """Obtiene conexión a la base de datos con WAL mode para concurrencia"""
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def init_database():
    """Crea todas las tablas si no existen"""
    conn = get_db()
    c = conn.cursor()

    # Tabla de usuarios
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        clave_hash TEXT NOT NULL,
        rol TEXT NOT NULL,
        nombre TEXT NOT NULL,
        correo TEXT NOT NULL,
        estado TEXT DEFAULT 'ACTIVO',
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Tabla de expedientes (NOMBRES y APELLIDOS separados)
    c.execute("""CREATE TABLE IF NOT EXISTS expedientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estado TEXT NOT NULL,
        municipio TEXT NOT NULL,
        aula_taller TEXT,
        nombres TEXT NOT NULL,
        apellidos TEXT DEFAULT '',
        cedula TEXT UNIQUE NOT NULL,
        correo_titular TEXT,
        tipo_programa TEXT NOT NULL,
        programa TEXT NOT NULL,
        tipo_expediente TEXT NOT NULL,
        periodo_culminacion TEXT DEFAULT '',
        pdf_path TEXT,
        observaciones TEXT,
        registrado_por TEXT,
        fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
        fecha_modificacion TEXT
    )""")

    # Migración: agregar columna 'apellidos' si la BD es anterior a esta versión
    try:
        c.execute("ALTER TABLE expedientes ADD COLUMN apellidos TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Migración: agregar columna 'periodo_culminacion' (para la certificación)
    try:
        c.execute("ALTER TABLE expedientes ADD COLUMN periodo_culminacion TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Migración: agregar columna 'sexo' (para redactar el título según el género)
    try:
        c.execute("ALTER TABLE expedientes ADD COLUMN sexo TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Migración: BACHILLER / TSU (para PNF), período inicial y períodos por año
    for _col, _def in (("tipo_estudiante", "''"), ("periodo_inicio", "''"), ("periodos_por_anio", "2")):
        try:
            c.execute(f"ALTER TABLE expedientes ADD COLUMN {_col} TEXT DEFAULT {_def}")
        except sqlite3.OperationalError:
            pass  # La columna ya existe

    # Migración: ESTADO asignado al usuario (para el Administrador Regional Nivel 3).
    # Guarda a qué estado pertenece esa clave; solo trabajará ese estado.
    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN estado_region TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Tabla de MALLAS CURRICULARES: las materias (asignaturas) de cada programa,
    # en el orden de trayecto/semestre/trimestre, con sus unidades de crédito (U.C.).
    # 'es_introductorio'=1 marca las materias del trayecto/curso introductorio, que
    # SÍ se cargan pero NO salen en la Certificación de Calificaciones.
    c.execute("""CREATE TABLE IF NOT EXISTS mallas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        programa TEXT NOT NULL,
        orden INTEGER NOT NULL DEFAULT 0,
        periodo TEXT DEFAULT '',
        materia TEXT NOT NULL,
        creditos REAL DEFAULT 0,
        es_introductorio INTEGER DEFAULT 0,
        periodo_orden INTEGER DEFAULT 0,
        UNIQUE(programa, materia)
    )""")

    # Migración: agregar columna 'periodo_orden' a mallas (N° de semestre/trimestre)
    try:
        c.execute("ALTER TABLE mallas ADD COLUMN periodo_orden INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Tabla de NOTAS (calificaciones) de cada estudiante por materia.
    # La columna 'periodo' guarda el período tal como viene en el archivo
    # (por ejemplo "2020-I", "2020-II", "2020-III"); si está vacío, el
    # certificado calcula el período con la secuencia de inicio.
    c.execute("""CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cedula TEXT NOT NULL,
        programa TEXT NOT NULL,
        materia TEXT NOT NULL,
        creditos REAL DEFAULT 0,
        nota TEXT DEFAULT '',
        periodo TEXT DEFAULT '',
        UNIQUE(cedula, materia)
    )""")

    # Migración: agregar columna 'periodo' a la tabla notas (para las BD antiguas)
    try:
        c.execute("ALTER TABLE notas ADD COLUMN periodo TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Tabla de solicitudes de modificación (incluye solicitudes de eliminación)
    c.execute("""CREATE TABLE IF NOT EXISTS solicitudes_modificacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expediente_id INTEGER NOT NULL,
        solicitado_por TEXT NOT NULL,
        campo_modificar TEXT NOT NULL,
        valor_actual TEXT,
        valor_nuevo TEXT,
        motivo TEXT,
        estado_solicitud TEXT DEFAULT 'PENDIENTE',
        revisado_por TEXT,
        fecha_solicitud TEXT DEFAULT CURRENT_TIMESTAMP,
        fecha_revision TEXT,
        FOREIGN KEY (expediente_id) REFERENCES expedientes(id)
    )""")

    # Tabla de listas editables (aulas_taller, programas futuros)
    c.execute("""CREATE TABLE IF NOT EXISTS listas_editables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_lista TEXT NOT NULL,
        categoria_padre TEXT NOT NULL,
        valor TEXT NOT NULL,
        UNIQUE(tipo_lista, categoria_padre, valor)
    )""")

    # Tabla de plantillas de correo
    c.execute("""CREATE TABLE IF NOT EXISTS plantillas_correo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_plantilla TEXT UNIQUE NOT NULL,
        asunto TEXT NOT NULL,
        cuerpo TEXT NOT NULL,
        fecha_modificacion TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Crear admin principal por defecto
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("SELECT COUNT(*) FROM usuarios WHERE rol='ADMIN_PRINCIPAL'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO usuarios (usuario, clave_hash, rol, nombre, correo) VALUES (?, ?, ?, ?, ?)",
                  ("admin", admin_hash, "ADMIN_PRINCIPAL", "Administrador Principal", "admin@ulgu.edu.ve"))

    # Cargar aulas taller por defecto si no existen
    c.execute("SELECT COUNT(*) FROM listas_editables WHERE tipo_lista='aula_taller'")
    if c.fetchone()[0] == 0:
        for estado, municipios in ESTADOS_MUNICIPIOS.items():
            for municipio in municipios:
                c.execute("INSERT OR IGNORE INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES (?, ?, ?)",
                          ("aula_taller", f"{estado}|{municipio}", f"Aula {municipio} 01"))

    # Cargar programas por defecto si no existen
    c.execute("SELECT COUNT(*) FROM listas_editables WHERE tipo_lista='programa'")
    if c.fetchone()[0] == 0:
        for tipo, programas in TIPOS_PROGRAMA_PROGRAMAS.items():
            for prog in programas:
                c.execute("INSERT OR IGNORE INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES (?, ?, ?)",
                          ("programa", tipo, prog))

    # Migracion: refrescar la lista de programas a la version oficial de las mallas.
    # Se ejecuta UNA sola vez (marcada con un sello de version) para no borrar
    # programas que el administrador agregue manualmente mas adelante.
    VERSION_PROGRAMAS = "mallas_2026_v1"
    c.execute("SELECT COUNT(*) FROM listas_editables WHERE tipo_lista='meta' AND categoria_padre='version_programas' AND valor=?",
              (VERSION_PROGRAMAS,))
    if c.fetchone()[0] == 0:
        # Borrar los programas antiguos y recargar los oficiales desde las mallas
        c.execute("DELETE FROM listas_editables WHERE tipo_lista='programa'")
        for tipo, programas in TIPOS_PROGRAMA_PROGRAMAS.items():
            for prog in programas:
                c.execute("INSERT OR IGNORE INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES (?, ?, ?)",
                          ("programa", tipo, prog))
        # Dejar el sello para no volver a borrar en el futuro
        c.execute("INSERT OR IGNORE INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES (?, ?, ?)",
                  ("meta", "version_programas", VERSION_PROGRAMAS))

    # Plantilla de correo por defecto
    c.execute("SELECT COUNT(*) FROM plantillas_correo")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO plantillas_correo (nombre_plantilla, asunto, cuerpo) VALUES (?, ?, ?)",
                  ("registro_expediente",
                   "Registro de Expediente - UNEM",
                   "Estimado(a) {nombres} {apellidos},\n\n"
                   "Le informamos que su expediente ha sido registrado exitosamente en el sistema de la UNEM.\n\n"
                   "Detalles del registro:\n"
                   "- Cédula: {cedula}\n"
                   "- Estado: {estado}\n"
                   "- Municipio: {municipio}\n"
                   "- Programa: {programa}\n"
                   "- Tipo de Expediente: {tipo_expediente}\n\n"
                   "Se adjunta el PDF de su expediente digital.\n\n"
                   "Atentamente,\n"
                   "Expedientes UNEM"))

    # Carga inicial (una sola vez) de las mallas oficiales reconocidas
    try:
        _seed_mallas_oficiales(c)
    except Exception:
        pass

    conn.commit()
    conn.close()

# ============================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================

def verificar_credenciales(usuario, clave):
    """Verifica usuario y contraseña"""
    conn = get_db()
    c = conn.cursor()
    clave_hash = hashlib.sha256(clave.encode()).hexdigest()
    c.execute("SELECT usuario, rol, nombre, correo, estado_region FROM usuarios WHERE usuario=? AND clave_hash=? AND estado='ACTIVO'",
              (usuario, clave_hash))
    resultado = c.fetchone()
    conn.close()
    return resultado


def crear_usuario(usuario, clave, rol, nombre, correo, estado_region=""):
    """Crea un nuevo usuario. Para el Administrador Regional (Nivel 3) se guarda
    el 'estado_region': el estado al que pertenece esa clave."""
    try:
        conn = get_db()
        c = conn.cursor()
        clave_hash = hashlib.sha256(clave.encode()).hexdigest()
        c.execute("INSERT INTO usuarios (usuario, clave_hash, rol, nombre, correo, estado_region) VALUES (?, ?, ?, ?, ?, ?)",
                  (usuario, clave_hash, rol, nombre, correo, estado_region or ""))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def obtener_usuarios():
    """Obtiene todos los usuarios"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT usuario, rol, nombre, correo, estado, fecha_creacion, estado_region FROM usuarios ORDER BY fecha_creacion DESC")
    datos = c.fetchall()
    conn.close()
    return datos


def cambiar_estado_usuario(usuario, nuevo_estado):
    """Activa o desactiva un usuario"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE usuarios SET estado=? WHERE usuario=?", (nuevo_estado, usuario))
    conn.commit()
    conn.close()


def cambiar_clave_usuario(usuario, nueva_clave):
    """Cambia la contraseña de un usuario"""
    conn = get_db()
    c = conn.cursor()
    clave_hash = hashlib.sha256(nueva_clave.encode()).hexdigest()
    c.execute("UPDATE usuarios SET clave_hash=? WHERE usuario=?", (clave_hash, usuario))
    conn.commit()
    conn.close()


def contar_admin_principal_activos():
    """Cuenta cuántos Administradores Principales (Nivel 1) activos quedan."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM usuarios WHERE rol='ADMIN_PRINCIPAL' AND estado='ACTIVO'")
    n = c.fetchone()[0]
    conn.close()
    return n


def eliminar_usuario(usuario):
    """Elimina un usuario del sistema de forma permanente."""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM usuarios WHERE usuario=?", (usuario,))
    conn.commit()
    conn.close()
    return True


# ============================================================
# FUNCIONES DE EXPEDIENTES
# ============================================================

def registrar_expediente(datos, pdf_file=None):
    """Registra un nuevo expediente en la base de datos"""
    conn = get_db()
    c = conn.cursor()

    # Verificar cédula duplicada
    c.execute("SELECT id FROM expedientes WHERE cedula=?", (datos["cedula"],))
    if c.fetchone():
        conn.close()
        return False, "Ya existe un expediente con esa cédula"

    # Guardar PDF
    pdf_path = None
    if pdf_file:
        filename = f"{datos['cedula'].replace('-', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        pdf_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(pdf_path, "wb") as f:
            f.write(pdf_file)

    c.execute("""INSERT INTO expedientes 
        (estado, municipio, aula_taller, nombres, apellidos, cedula, correo_titular,
         tipo_programa, programa, tipo_expediente, periodo_culminacion, sexo,
         tipo_estudiante, periodo_inicio, periodos_por_anio,
         pdf_path, observaciones, registrado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (datos["estado"], datos["municipio"], datos.get("aula_taller", ""),
               datos["nombres"], datos.get("apellidos", ""), datos["cedula"], datos.get("correo_titular", ""),
               datos["tipo_programa"], datos["programa"], datos["tipo_expediente"],
               datos.get("periodo_culminacion", ""), datos.get("sexo", ""),
               datos.get("tipo_estudiante", ""), datos.get("periodo_inicio", ""),
               str(datos.get("periodos_por_anio", 2)),
               pdf_path, datos.get("observaciones", ""), datos.get("registrado_por", "")))

    expediente_id = c.lastrowid
    conn.commit()
    conn.close()
    return True, f"Expediente #{expediente_id} registrado exitosamente"


def obtener_expedientes(filtros=None):
    """Obtiene expedientes con filtros opcionales"""
    conn = get_db()
    query = "SELECT id, estado, municipio, aula_taller, nombres, apellidos, cedula, correo_titular, tipo_programa, programa, tipo_expediente, periodo_culminacion, sexo, tipo_estudiante, periodo_inicio, periodos_por_anio, pdf_path, observaciones, registrado_por, fecha_registro FROM expedientes WHERE 1=1"
    params = []

    if filtros:
        if filtros.get("estado"):
            query += " AND estado=?"
            params.append(filtros["estado"])
        if filtros.get("municipio"):
            query += " AND municipio=?"
            params.append(filtros["municipio"])
        if filtros.get("tipo_programa"):
            query += " AND tipo_programa=?"
            params.append(filtros["tipo_programa"])
        if filtros.get("programa"):
            query += " AND programa=?"
            params.append(filtros["programa"])
        if filtros.get("tipo_expediente"):
            query += " AND tipo_expediente=?"
            params.append(filtros["tipo_expediente"])
        if filtros.get("cedula"):
            query += " AND cedula=?"
            params.append(filtros["cedula"])

    query += " ORDER BY fecha_registro DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def obtener_expediente_por_id(exp_id):
    """Obtiene un expediente específico por ID"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM expedientes WHERE id=?", (exp_id,))
    datos = c.fetchone()
    conn.close()
    return datos


def eliminar_expediente(exp_id):
    """Elimina un expediente de forma permanente (registro + PDF físico si existe).
    Lo usan directamente el Nivel 1 y el Nivel 2."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT pdf_path FROM expedientes WHERE id=?", (exp_id,))
    row = c.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        try:
            os.remove(row[0])
        except OSError:
            pass
    c.execute("DELETE FROM expedientes WHERE id=?", (exp_id,))
    conn.commit()
    conn.close()
    return True


def actualizar_expediente(exp_id, campos):
    """Actualiza directamente los campos de un expediente (Nivel 1 y 2).
    'campos' es un diccionario columna->valor."""
    columnas_validas = {
        "estado", "municipio", "aula_taller", "nombres", "apellidos", "cedula",
        "correo_titular", "tipo_programa", "programa", "tipo_expediente",
        "observaciones",
    }
    sets = []
    params = []
    for col, val in campos.items():
        if col in columnas_validas:
            sets.append(f"{col}=?")
            params.append(val)
    if not sets:
        return False
    conn = get_db()
    c = conn.cursor()
    params.append(exp_id)
    c.execute(f"UPDATE expedientes SET {', '.join(sets)}, fecha_modificacion=CURRENT_TIMESTAMP WHERE id=?", params)
    conn.commit()
    conn.close()
    return True


def obtener_estadisticas():
    """Obtiene estadísticas generales"""
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM expedientes")
    total = c.fetchone()[0]

    c.execute("SELECT tipo_expediente, COUNT(*) FROM expedientes GROUP BY tipo_expediente")
    por_tipo_exp = dict(c.fetchall())

    c.execute("SELECT estado, COUNT(*) FROM expedientes GROUP BY estado ORDER BY COUNT(*) DESC")
    por_estado = dict(c.fetchall())

    c.execute("SELECT tipo_programa, COUNT(*) FROM expedientes GROUP BY tipo_programa ORDER BY COUNT(*) DESC")
    por_tipo_prog = dict(c.fetchall())

    c.execute("SELECT programa, COUNT(*) FROM expedientes GROUP BY programa ORDER BY COUNT(*) DESC")
    por_programa = dict(c.fetchall())

    c.execute("SELECT municipio, COUNT(*) FROM expedientes GROUP BY municipio ORDER BY COUNT(*) DESC LIMIT 20")
    por_municipio = dict(c.fetchall())

    conn.close()
    return {
        "total": total,
        "por_tipo_expediente": por_tipo_exp,
        "por_estado": por_estado,
        "por_tipo_programa": por_tipo_prog,
        "por_programa": por_programa,
        "por_municipio": por_municipio,
    }


def generar_estadisticas_pdf(df):
    """Genera un PDF de estadísticas con UNA PÁGINA por cada renglón estadístico
    (una tabla por página: total, por estado, por municipio, por tipo de programa,
    por programa y por tipo de expediente)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    ancho, alto = letter
    c = canvas.Canvas(buffer, pagesize=letter)
    margen = 18 * mm
    fecha_txt = datetime.now().strftime("%d/%m/%Y %H:%M")

    def _pagina(titulo, pares, total_registros):
        """Dibuja una página con un título y una tabla de dos columnas (valor / cantidad)."""
        x0 = margen
        x1 = ancho - margen
        y = alto - margen
        # Encabezado
        c.setFont("Helvetica-Bold", 15)
        c.drawString(x0, y, "Estadísticas de Expedientes — UNEM")
        y -= 7 * mm
        c.setFont("Helvetica", 9)
        c.drawString(x0, y, f"Generado: {fecha_txt}")
        c.drawRightString(x1, y, f"Total de expedientes: {total_registros}")
        y -= 5 * mm
        c.setStrokeColorRGB(0.2, 0.2, 0.2); c.setLineWidth(0.8)
        c.line(x0, y, x1, y)
        y -= 10 * mm
        # Título del renglón
        c.setFont("Helvetica-Bold", 13)
        c.drawString(x0, y, titulo)
        y -= 9 * mm
        # Cabecera de tabla
        col_cant = x1 - 40 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x0, y, "Categoría")
        c.drawRightString(x1, y, "Cantidad")
        y -= 2 * mm
        c.setStrokeColorRGB(0.5, 0.5, 0.5); c.setLineWidth(0.5)
        c.line(x0, y, x1, y)
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        if not pares:
            c.setFont("Helvetica-Oblique", 10)
            c.drawString(x0, y, "(Sin datos)")
            return
        for etiqueta, cantidad in pares:
            if y < margen + 15 * mm:
                c.showPage()
                y = alto - margen
                c.setFont("Helvetica-Bold", 12)
                c.drawString(x0, y, titulo + " (continuación)")
                y -= 9 * mm
                c.setFont("Helvetica", 10)
            etq = str(etiqueta) if etiqueta not in (None, "") else "(sin dato)"
            # recortar etiquetas muy largas
            if len(etq) > 70:
                etq = etq[:67] + "..."
            c.drawString(x0, y, etq)
            c.drawRightString(x1, y, str(cantidad))
            c.setStrokeColorRGB(0.85, 0.85, 0.85); c.setLineWidth(0.3)
            c.line(x0, y - 2 * mm, x1, y - 2 * mm)
            y -= 7 * mm

    total = len(df)

    def _conteo(col):
        if col not in df.columns or df.empty:
            return []
        vc = df[col].fillna("(sin dato)").value_counts()
        return list(vc.items())

    # Una página por renglón estadístico
    _pagina("Resumen general", [
        ("Total de expedientes", total),
        ("Estados distintos", df["estado"].nunique() if not df.empty else 0),
        ("Municipios distintos", df["municipio"].nunique() if not df.empty else 0),
        ("Programas distintos", df["programa"].nunique() if not df.empty else 0),
        ("Tipos de expediente", df["tipo_expediente"].nunique() if not df.empty else 0),
    ], total)
    c.showPage()
    _pagina("Expedientes por Estado", _conteo("estado"), total)
    c.showPage()
    _pagina("Expedientes por Municipio", _conteo("municipio"), total)
    c.showPage()
    _pagina("Expedientes por Tipo de Programa", _conteo("tipo_programa"), total)
    c.showPage()
    _pagina("Expedientes por Programa", _conteo("programa"), total)
    c.showPage()
    _pagina("Expedientes por Tipo de Expediente", _conteo("tipo_expediente"), total)

    c.save()
    buffer.seek(0)
    return buffer

# ============================================================
# FUNCIONES DE SOLICITUDES DE MODIFICACIÓN / ELIMINACIÓN
# ============================================================

CAMPO_ELIMINAR = "ELIMINAR EXPEDIENTE"


def crear_solicitud_modificacion(expediente_id, solicitado_por, campo, valor_actual, valor_nuevo, motivo):
    """Crea una solicitud de modificación pendiente"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO solicitudes_modificacion 
        (expediente_id, solicitado_por, campo_modificar, valor_actual, valor_nuevo, motivo)
        VALUES (?, ?, ?, ?, ?, ?)""",
              (expediente_id, solicitado_por, campo, valor_actual, valor_nuevo, motivo))
    conn.commit()
    conn.close()


def crear_solicitud_eliminacion(expediente_id, solicitado_por, resumen, motivo):
    """Crea una solicitud de ELIMINACIÓN de expediente (la ejecutan Nivel 1 y 2)"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO solicitudes_modificacion 
        (expediente_id, solicitado_por, campo_modificar, valor_actual, valor_nuevo, motivo)
        VALUES (?, ?, ?, ?, ?, ?)""",
              (expediente_id, solicitado_por, CAMPO_ELIMINAR, resumen, "ELIMINAR REGISTRO", motivo))
    conn.commit()
    conn.close()


def obtener_solicitudes(estado_filtro=None):
    """Obtiene solicitudes de modificación / eliminación"""
    conn = get_db()
    query = """SELECT s.id, s.expediente_id, s.solicitado_por, s.campo_modificar, 
               s.valor_actual, s.valor_nuevo, s.motivo, s.estado_solicitud, 
               s.revisado_por, s.fecha_solicitud, s.fecha_revision,
               e.cedula, e.nombres, e.apellidos
        FROM solicitudes_modificacion s
        LEFT JOIN expedientes e ON s.expediente_id = e.id
        WHERE 1=1"""
    params = []
    if estado_filtro:
        query += " AND s.estado_solicitud=?"
        params.append(estado_filtro)
    query += " ORDER BY s.fecha_solicitud DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def aprobar_solicitud(solicitud_id, revisado_por):
    """Aprueba una solicitud y aplica la modificación (o elimina el expediente)"""
    conn = get_db()
    c = conn.cursor()

    # Obtener datos de la solicitud
    c.execute("SELECT expediente_id, campo_modificar, valor_nuevo FROM solicitudes_modificacion WHERE id=? AND estado_solicitud='PENDIENTE'",
              (solicitud_id,))
    solicitud = c.fetchone()
    if not solicitud:
        conn.close()
        return False, "Solicitud no encontrada o ya procesada"

    exp_id, campo, valor_nuevo = solicitud

    if campo == CAMPO_ELIMINAR:
        # Eliminar el PDF físico si existe
        c.execute("SELECT pdf_path FROM expedientes WHERE id=?", (exp_id,))
        row_pdf = c.fetchone()
        if row_pdf and row_pdf[0] and os.path.exists(row_pdf[0]):
            try:
                os.remove(row_pdf[0])
            except OSError:
                pass
        # Eliminar el expediente
        c.execute("DELETE FROM expedientes WHERE id=?", (exp_id,))
        c.execute("UPDATE solicitudes_modificacion SET estado_solicitud='APROBADA', revisado_por=?, fecha_revision=CURRENT_TIMESTAMP WHERE id=?",
                  (revisado_por, solicitud_id))
        conn.commit()
        conn.close()
        return True, "Expediente ELIMINADO exitosamente"

    # Modificación de una NOTA (calificación). El campo viene como
    # "NOTA · <materia>" y el valor_nuevo es la nueva calificación.
    if campo.startswith("NOTA · "):
        materia = campo[len("NOTA · "):].strip()
        c.execute("SELECT cedula FROM expedientes WHERE id=?", (exp_id,))
        row_ced = c.fetchone()
        if row_ced and row_ced[0]:
            ced = row_ced[0]
            nuevo_val = str(valor_nuevo or "").strip().upper()
            if nuevo_val == "":
                c.execute("DELETE FROM notas WHERE cedula=? AND materia=?", (ced, materia))
            else:
                c.execute("SELECT id FROM notas WHERE cedula=? AND materia=?", (ced, materia))
                if c.fetchone():
                    c.execute("UPDATE notas SET nota=? WHERE cedula=? AND materia=?",
                              (nuevo_val, ced, materia))
                else:
                    c.execute("""INSERT INTO notas (cedula, programa, materia, creditos, nota)
                                 SELECT ?, programa, ?, 0, ? FROM expedientes WHERE id=?""",
                              (ced, materia, nuevo_val, exp_id))
        c.execute("UPDATE solicitudes_modificacion SET estado_solicitud='APROBADA', revisado_por=?, fecha_revision=CURRENT_TIMESTAMP WHERE id=?",
                  (revisado_por, solicitud_id))
        conn.commit()
        conn.close()
        return True, "Modificación de calificación aprobada y aplicada"

    # Mapeo de campos (modificación normal)
    campos_db = {
        "Estado": "estado", "Municipio": "municipio", "Aula Taller": "aula_taller",
        "Nombres": "nombres", "Apellidos": "apellidos", "Cédula": "cedula",
        "Correo del Titular": "correo_titular",
        "Tipo de Programa": "tipo_programa", "Programa": "programa",
        "Tipo de Expediente": "tipo_expediente", "Observaciones": "observaciones"
    }

    if campo in campos_db:
        columna = campos_db[campo]
        c.execute(f"UPDATE expedientes SET {columna}=?, fecha_modificacion=CURRENT_TIMESTAMP WHERE id=?",
                  (valor_nuevo, exp_id))

    c.execute("UPDATE solicitudes_modificacion SET estado_solicitud='APROBADA', revisado_por=?, fecha_revision=CURRENT_TIMESTAMP WHERE id=?",
              (revisado_por, solicitud_id))

    conn.commit()
    conn.close()
    return True, "Modificación aprobada y aplicada exitosamente"


def rechazar_solicitud(solicitud_id, revisado_por):
    """Rechaza una solicitud de modificación / eliminación"""
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE solicitudes_modificacion SET estado_solicitud='RECHAZADA', revisado_por=?, fecha_revision=CURRENT_TIMESTAMP WHERE id=?",
              (revisado_por, solicitud_id))
    conn.commit()
    conn.close()


# ============================================================
# FUNCIONES DE LISTAS EDITABLES
# ============================================================

def _aula_key(estado, municipio):
    """Llave con la que se guardan las aulas taller: ancladas a ESTADO + MUNICIPIO.
    Así dos municipios con el mismo nombre en estados distintos no se mezclan."""
    return f"{(estado or '').strip()}|{(municipio or '').strip()}"


def obtener_aulas(estado, municipio):
    """Devuelve las aulas taller de un estado+municipio. Mantiene compatibilidad
    con datos antiguos que se guardaron solo por municipio."""
    aulas = obtener_lista_editable("aula_taller", _aula_key(estado, municipio))
    if not aulas:
        aulas = obtener_lista_editable("aula_taller", municipio)
    return aulas


def obtener_lista_editable(tipo_lista, categoria_padre=None):
    """Obtiene valores de una lista editable"""
    conn = get_db()
    c = conn.cursor()
    if categoria_padre:
        c.execute("SELECT valor FROM listas_editables WHERE tipo_lista=? AND categoria_padre=? ORDER BY valor",
                  (tipo_lista, categoria_padre))
    else:
        c.execute("SELECT DISTINCT categoria_padre FROM listas_editables WHERE tipo_lista=? ORDER BY categoria_padre",
                  (tipo_lista,))
    datos = [row[0] for row in c.fetchall()]
    conn.close()
    return datos


def agregar_valor_lista(tipo_lista, categoria_padre, valor):
    """Agrega un nuevo valor a una lista editable"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES (?, ?, ?)",
                  (tipo_lista, categoria_padre, valor))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def eliminar_valor_lista(tipo_lista, categoria_padre, valor):
    """Elimina un valor de una lista editable"""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM listas_editables WHERE tipo_lista=? AND categoria_padre=? AND valor=?",
              (tipo_lista, categoria_padre, valor))
    conn.commit()
    conn.close()

# ============================================================
# FUNCIONES DE CORREO ELECTRÓNICO
# ============================================================

def cargar_smtp_config():
    """Carga configuración SMTP"""
    if os.path.exists(SMTP_CONFIG_FILE):
        with open(SMTP_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "servidor": "smtp.gmail.com",
        "puerto": 587,
        "correo_remitente": "",
        "clave_app": "",
        "usar_tls": True
    }


def guardar_smtp_config(config):
    """Guarda configuración SMTP"""
    with open(SMTP_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def cargar_plantillas_correo():
    """Carga plantillas de correo desde la base de datos"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT nombre_plantilla, asunto, cuerpo FROM plantillas_correo")
    datos = {row[0]: {"asunto": row[1], "cuerpo": row[2]} for row in c.fetchall()}
    conn.close()
    return datos


def guardar_plantilla_correo(nombre, asunto, cuerpo):
    """Guarda o actualiza una plantilla de correo"""
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO plantillas_correo (nombre_plantilla, asunto, cuerpo, fecha_modificacion) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
              (nombre, asunto, cuerpo))
    conn.commit()
    conn.close()


def enviar_correo_registro(correo_destino, datos_expediente, pdf_path=None):
    """Envía correo de notificación de registro con PDF adjunto"""
    smtp = cargar_smtp_config()
    plantillas = cargar_plantillas_correo()

    if not smtp.get("correo_remitente") or not smtp.get("clave_app"):
        return False, "Configure el correo SMTP primero en Configuración"

    plantilla = plantillas.get("registro_expediente", {
        "asunto": "Registro de Expediente - UNEM",
        "cuerpo": "Su expediente ha sido registrado. Cédula: {cedula}"
    })

    # Reemplazar variables en la plantilla (tolerante a variables faltantes)
    datos_fmt = dict(datos_expediente)
    datos_fmt.setdefault("apellidos", "")
    try:
        asunto = plantilla["asunto"].format(**datos_fmt)
        cuerpo = plantilla["cuerpo"].format(**datos_fmt)
    except KeyError:
        asunto = plantilla["asunto"]
        cuerpo = plantilla["cuerpo"]

    try:
        msg = MIMEMultipart()
        msg["From"] = smtp["correo_remitente"]
        msg["To"] = correo_destino
        msg["Subject"] = asunto
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

        # Adjuntar PDF si existe
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                part = MIMEBase("application", "pdf")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename=Expediente_{datos_expediente.get('cedula', '')}.pdf")
                msg.attach(part)

        server = smtplib.SMTP(smtp["servidor"], smtp["puerto"])
        if smtp.get("usar_tls"):
            server.starttls()
        server.login(smtp["correo_remitente"], smtp["clave_app"])
        server.sendmail(smtp["correo_remitente"], correo_destino, msg.as_string())
        server.quit()
        return True, f"Correo enviado exitosamente a {correo_destino}"
    except Exception as e:
        return False, f"Error enviando correo: {str(e)}"


# ============================================================
# FUNCION: GENERAR ETIQUETA PARA LA CARPETA
# ============================================================

def _dibujar_valor_ajustado(c, x, y, texto, max_ancho, font="Helvetica", size=10, leading_mm=5.0):
    """Dibuja el valor y lo parte en varias lineas si es muy largo. Devuelve la Y final."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.units import mm
    palabras = str(texto).split()
    lineas = []
    linea = ""
    for w in palabras:
        prueba = (linea + " " + w).strip()
        if stringWidth(prueba, font, size) <= max_ancho or not linea:
            linea = prueba
        else:
            lineas.append(linea)
            linea = w
    if linea:
        lineas.append(linea)
    if not lineas:
        lineas = [""]
    c.setFont(font, size)
    for ln in lineas:
        c.drawString(x, y, ln)
        y -= leading_mm * mm
    return y


def generar_etiqueta_pdf(row):
    """Genera una etiqueta PDF con los datos del titular (sin el PDF del expediente),
    con el logo de la UNEM, lista para imprimir y pegar en la parte superior de la carpeta."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    buffer = BytesIO()
    ancho, alto = letter
    c = canvas.Canvas(buffer, pagesize=letter)

    margen = 15 * mm
    x0 = margen
    x1 = ancho - margen
    etq_alto = 150 * mm
    caja_y1 = alto - margen
    caja_y0 = caja_y1 - etq_alto

    # Marco exterior de la etiqueta
    c.setLineWidth(2)
    c.rect(x0, caja_y0, x1 - x0, etq_alto)

    # Logo institucional (si existe un archivo de logo en la app)
    logo_paths = ["logo_unem.png", "logo.png", "logo_unem.jpg", "logo.jpg"]
    logo_file = next((p for p in logo_paths if os.path.exists(p)), None)
    if logo_file:
        try:
            c.drawImage(ImageReader(logo_file), x0 + 8 * mm, caja_y1 - 32 * mm,
                        width=26 * mm, height=26 * mm,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # Encabezado institucional
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(ancho / 2, caja_y1 - 11 * mm, "REPUBLICA BOLIVARIANA DE VENEZUELA")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(ancho / 2, caja_y1 - 18 * mm, "UNEM - Universidad Nacional Experimental del Magisterio")
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(ancho / 2, caja_y1 - 28 * mm, "EXPEDIENTE ESTUDIANTIL")
    c.setLineWidth(1)
    c.line(x0 + 8 * mm, caja_y1 - 33 * mm, x1 - 8 * mm, caja_y1 - 33 * mm)

    # Campos (todos los datos personales, menos el PDF)
    nombre_completo = f"{row.get('nombres', '')} {row.get('apellidos', '')}".strip()
    campos = [
        ("NOMBRES Y APELLIDOS", nombre_completo),
        ("CEDULA DE IDENTIDAD", row.get("cedula", "")),
        ("ESTADO", row.get("estado", "")),
        ("MUNICIPIO", row.get("municipio", "")),
        ("AULA TALLER", row.get("aula_taller", "") or "-"),
        ("TIPO DE PROGRAMA", row.get("tipo_programa", "")),
        ("PROGRAMA", row.get("programa", "")),
        ("TIPO DE EXPEDIENTE", row.get("tipo_expediente", "")),
        ("CORREO ELECTRONICO", row.get("correo_titular", "") or "-"),
        ("FECHA DE REGISTRO", str(row.get("fecha_registro", ""))[:19]),
    ]
    etq_x = x0 + 10 * mm
    val_x = x0 + 58 * mm
    val_ancho = (x1 - 10 * mm) - val_x
    y = caja_y1 - 44 * mm
    for etiqueta, valor in campos:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(etq_x, y, f"{etiqueta}:")
        y_val = _dibujar_valor_ajustado(c, val_x, y, valor, val_ancho, size=10, leading_mm=5.5)
        # avanzar segun cuantas lineas ocupo el valor
        lineas_usadas = max(1, round((y - y_val) / (5.5 * mm)))
        y -= max(8 * mm, lineas_usadas * 5.5 * mm)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# CERTIFICACIÓN / CONSTANCIA EN PDF (escudo + QR + código de barras)
# ============================================================

ESCUDO_PATHS = ["escudo_venezuela.png", "escudo.png", "logo_unem.png", "logo.png"]
# Firma digital (escaneada) del Secretario. Suba una imagen con fondo transparente
# (PNG) a la raiz del repositorio con alguno de estos nombres para que aparezca
# automaticamente sobre la linea de la firma en la certificacion.
FIRMA_PATHS = ["firma_lenin_romero.png", "firma_secretario.png", "firma.png", "firma.jpg"]
SELLO_PATHS = ["sello_secretaria.png", "sello_unem.png", "sello.png"]

_MALLAS_OFICIALES = {
    "LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN INICIAL": [
        (1, "SEMESTRE 1", "PROYECTO SOCIO INTEGRADOR: PRÁCTICA PROFESIONAL TRANSFORMADORA I", 9),
        (1, "SEMESTRE 1", "EDUCACIÓN BOLIVARIANA Y SOCIEDAD", 2),
        (1, "SEMESTRE 1", "USO SOCIAL DE LA LENGUA", 2),
        (1, "SEMESTRE 1", "DESARROLLO Y CRECIMIENTO DEL NIÑO Y LA NIÑA EN EL CONTEXTO VENEZOLANO", 3),
        (1, "SEMESTRE 1", "FORMACIÓN SOCIO CRÍTICA I", 3),
        (1, "SEMESTRE 1", "GESTIÓN DE RIESGOS Y PROTECCIÓN CIVIL", 3),
        (2, "SEMESTRE 2", "PROYECTO SOCIO INTEGRADOR: PRÁCTICA PROFESIONAL TRANSFORMADORA II", 8),
        (2, "SEMESTRE 2", "PEDAGOGÍA TRANSFORMADORA", 3),
        (2, "SEMESTRE 2", "CIMIENTOS DE LA EDUCACIÓN INICIAL", 3),
        (2, "SEMESTRE 2", "LAS TICs EN LA EDUCACIÓN BOLIVARIANA", 3),
        (2, "SEMESTRE 2", "LA ACTIVIDAD FÍSICA, EL JUEGO Y LA RECREACIÓN EN EDUCACIÓN INICIAL", 2),
        (2, "SEMESTRE 2", "FORMACIÓN SOCIO CRÍTICA II", 3),
        (2, "SEMESTRE 2", "LENGUAS INDÍGENAS (ELECTIVA)", 3),
        (3, "SEMESTRE 3", "PROYECTO SOCIO INTEGRADOR: PRÁCTICA PROFESIONAL TRANSFORMADORA III", 9),
        (3, "SEMESTRE 3", "MATEMÁTICA Y ESTADÍSTICA APLICADA A LO SOCIO EDUCATIVO", 3),
        (3, "SEMESTRE 3", "EDUCACIÓN Y TERRITORIALIDAD", 3),
        (3, "SEMESTRE 3", "CURRÍCULO EN EL SISTEMA EDUCATIVO VENEZOLANO", 3),
        (3, "SEMESTRE 3", "TRADICIONES Y COSTUMBRES DEL PUEBLO VENEZOLANO", 2),
        (3, "SEMESTRE 3", "AMBIENTE Y SALUD INTEGRAL", 3),
        (3, "SEMESTRE 3", "FORMACIÓN SOCIO CRÍTICA III", 3),
        (4, "SEMESTRE 4", "PROYECTO SOCIO INTEGRADOR: PRÁCTICA PROFESIONAL TRANSFORMADORA IV", 8),
        (4, "SEMESTRE 4", "DESARROLLO SOCIO AFECTIVO Y LA INTELIGENCIA", 3),
        (4, "SEMESTRE 4", "RESPONSABILIDAD SOCIAL FAMILIA ESCUELA Y COMUNIDAD", 3),
        (4, "SEMESTRE 4", "EDUCACIÓN SEXUAL Y REPRODUCTIVA", 3),
        (4, "SEMESTRE 4", "DESEMPEÑO PROFESIONAL DEL DOCENTE DE EDUCACIÓN INICIAL", 2),
        (4, "SEMESTRE 4", "FORMACIÓN SOCIO CRÍTICA IV", 3),
        (4, "SEMESTRE 4", "ALIMENTACIÓN SANA Y ALTERNATIVA EN EDUCACIÓN INICIAL (ELECTIVA)", 2),
        (5, "SEMESTRE 5", "PROYECTO SOCIO INTEGRADOR: PRÁCTICA PROFESIONAL TRANSFORMADORA V", 9),
        (5, "SEMESTRE 5", "PLANIFICACIÓN Y EVALUACIÓN EN EDUCACIÓN INICIAL", 3),
        (5, "SEMESTRE 5", "DERECHOS HUMANOS DEL NIÑO Y LA NIÑA EN EL CONTEXTO EDUCATIVO VENEZOLANO", 3),
        (5, "SEMESTRE 5", "PREVENCIÓN Y ATENCIÓN A LA SALUD INTEGRAL DEL NIÑO Y LA NIÑA", 3),
        (5, "SEMESTRE 5", "EXPRESIÓN MUSICAL Y CORPORAL", 2),
        (5, "SEMESTRE 5", "FORMACIÓN SOCIO CRÍTICA V", 3),
        (5, "SEMESTRE 5", "SABERES ANCESTRALES DE LOS PUEBLOS INDÍGENAS", 2),
        (6, "SEMESTRE 6", "PROYECTO SOCIO INTEGRADOR: PRÁCTICA PROFESIONAL TRANSFORMADORA VI", 8),
        (6, "SEMESTRE 6", "EDUCACIÓN MATERNAL, LA GESTACIÓN Y EL PARTO HUMANIZADO", 3),
        (6, "SEMESTRE 6", "DESARROLLO DE LA LENGUA ORAL Y LENGUA ESCRITA EN NIÑOS DE EDUCACIÓN INICIAL", 3),
        (6, "SEMESTRE 6", "NECESIDADES EDUCATIVAS ESPECIALES Y ATENCIÓN A LA DIVERSIDAD", 3),
        (6, "SEMESTRE 6", "EXPRESIÓN TEATRAL Y DANZAS TRADICIONALES DE VENEZUELA", 2),
        (6, "SEMESTRE 6", "FORMACIÓN SOCIO CRÍTICA VI", 3),
        (6, "SEMESTRE 6", "CREATIVIDAD E INNOVACIÓN EN EDUCACIÓN INICIAL (ELECTIVA)", 2),
        (7, "SEMESTRE 7", "PROYECTO SOCIO INTEGRADOR: PRÁCTICA PROFESIONAL TRANSFORMADORA VII", 9),
        (7, "SEMESTRE 7", "DESARROLLO DE LOS PROCESOS LÓGICO MATEMÁTICOS EN EL NIÑO DE EDUCACIÓN INICIAL", 3),
        (7, "SEMESTRE 7", "EXPRESIÓN PLÁSTICA DEL NIÑO EN EDUCACIÓN INICIAL", 3),
        (7, "SEMESTRE 7", "PROMOCIÓN DE LA LECTURA PARA NIÑOS Y NIÑAS DE EDUCACIÓN INICIAL", 2),
        (7, "SEMESTRE 7", "FORMACIÓN SOCIO CRÍTICA VII", 3),
        (7, "SEMESTRE 7", "TRANSFORMACIÓN DE MATERIALES Y RECURSOS PARA LA EDUCACIÓN INICIAL", 3),
        (8, "SEMESTRE 8", "PROYECTO SOCIO INTEGRADOR: PRÁCTICA PROFESIONAL TRANSFORMADORA VIII", 8),
        (8, "SEMESTRE 8", "PROCESOS ADMINISTRATIVOS EN LA EDUCACIÓN INICIAL EN VENEZUELA", 3),
        (8, "SEMESTRE 8", "MEDIOS DE COMUNICACIÓN EN EDUCACIÓN INICIAL", 2),
        (8, "SEMESTRE 8", "FORMACIÓN SOCIO CRÍTICA VIII", 3),
        (8, "SEMESTRE 8", "CONTINUIDAD AFECTIVA Y ARTICULACIÓN PEDAGÓGICA EN EDUCACIÓN INICIAL (ELECTIVA)", 3),
        (8, "SEMESTRE 8", "ACTIVIDADES ACADÉMICAS ACREDITABLES", 12),
    ],
    "LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN ESPECIAL": [
        (5, "SEMESTRE 5", "PROYECTO SOCIO INTEGRADOR V", 7),
        (5, "SEMESTRE 5", "FORMACIÓN SOCIO CRÍTICA V", 4),
        (5, "SEMESTRE 5", "EDUCACIÓN INTEGRAL PARA ESCOLARES CON DIFICULTADES DE APRENDIZAJES", 2),
        (5, "SEMESTRE 5", "EDUCACIÓN INTEGRAL PARA LA PERSONA CON AUTISMO", 3),
        (5, "SEMESTRE 5", "EVALUACIÓN PARA LA EDUCACIÓN ESPECIAL", 2),
        (5, "SEMESTRE 5", "ENSEÑANZA Y ADAPTACIONES CURRICULARES PARA LA LECTURA, ESCRITURA Y MATEMÁTICA I", 3),
        (6, "SEMESTRE 6", "PROYECTO SOCIO INTEGRADOR VI", 9),
        (6, "SEMESTRE 6", "FORMACIÓN SOCIO CRÍTICA VI", 4),
        (6, "SEMESTRE 6", "EDUCACIÓN INTEGRAL PARA LAS PERSONAS CON DISCAPACIDAD FÍSICO MOTORA", 3),
        (6, "SEMESTRE 6", "EDUCACIÓN INTEGRAL PARA LA PERSONA CON ALTA POTENCIALIDAD", 2),
        (6, "SEMESTRE 6", "ENSEÑANZA Y ADAPTACIONES CURRICULARES PARA LA LECTURA, ESCRITURA Y MATEMÁTICA II", 3),
        (7, "SEMESTRE 7", "PROYECTO SOCIO INTEGRADOR VII", 9),
        (7, "SEMESTRE 7", "FORMACIÓN SOCIO CRÍTICA VII", 4),
        (7, "SEMESTRE 7", "EDUCACIÓN INTEGRAL PARA LAS PERSONAS CON DISCAPACIDAD SENSORIAL Y COMUNICACIONAL", 3),
        (7, "SEMESTRE 7", "EDUCACIÓN INTEGRAL PARA LAS PERSONAS CON ENFERMEDADES ORGÁNICAS DISCAPACITANTES", 3),
        (7, "SEMESTRE 7", "PREVENCIÓN Y ATENCIÓN INTEGRAL TEMPRANA", 2),
        (8, "SEMESTRE 8", "PROYECTO SOCIO INTEGRADOR VIII", 9),
        (8, "SEMESTRE 8", "FORMACIÓN SOCIO CRÍTICA VIII", 4),
        (8, "SEMESTRE 8", "ORIENTACIÓN PARA LA INTEGRACIÓN LABORAL Y SOCIO COMUNITARIA", 3),
        (8, "SEMESTRE 8", "ESTRATEGIAS PARA LA ORIENTACIÓN EDUCATIVA, FAMILIAR Y COMUNITARIA", 3),
        (8, "SEMESTRE 8", "ADMINISTRACIÓN Y GESTIÓN DE LA EDUCACIÓN ESPECIAL", 3),
        (8, "SEMESTRE 8", "ACTIVIDADES ACADÉMICAS ACREDITABLES II", 6),
    ],
}


_ROMANOS = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

_NUM_PALABRA = {
    0: "CERO", 1: "UNO", 2: "DOS", 3: "TRES", 4: "CUATRO", 5: "CINCO",
    6: "SEIS", 7: "SIETE", 8: "OCHO", 9: "NUEVE", 10: "DIEZ",
    11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE", 15: "QUINCE",
    16: "DIECISÉIS", 17: "DIECISIETE", 18: "DIECIOCHO", 19: "DIECINUEVE", 20: "VEINTE",
}


def _calificacion_texto(nota):
    """Devuelve 'NN PALABRA' para notas numéricas 1-20; deja tal cual textos como
    APROBADO, AC, POR CURSAR."""
    s = str(nota or "").strip()
    if s == "":
        return ""
    try:
        n = int(float(s))
        pal = _NUM_PALABRA.get(n, "")
        return f"{n} {pal}".strip()
    except (ValueError, TypeError):
        su = s.upper()
        # Escribir en palabra completa las calificaciones no numéricas.
        mapa_texto = {
            "AP": "APROBADO",
            "APROBADO": "APROBADO",
            "AC": "APROBADA POR ACREDITACI\u00d3N",
            "APROBADA POR ACREDITACION": "APROBADA POR ACREDITACI\u00d3N",
            "APROBADA POR ACREDITACI\u00d3N": "APROBADA POR ACREDITACI\u00d3N",
        }
        return mapa_texto.get(su, su)


def _orden_desde_periodo(texto, grupo_idx):
    """Extrae el número de semestre/trimestre del texto del período (p.ej.
    'TRAYECTO 3 - SEMESTRE 5' -> 5). Si no hay número, usa el índice de grupo."""
    nums = re.findall(r"\d+", str(texto or ""))
    if nums:
        return int(nums[-1])
    return grupo_idx


def _parse_periodo_inicio(txt):
    """'2020-I' o '2020-1' -> (2020, 1). Devuelve None si no se puede leer."""
    t = str(txt or "").strip().upper().replace(" ", "")
    m = re.match(r"(\d{4})[-/._]?([IVX]+|\d+)$", t)
    if not m:
        m2 = re.match(r"(\d{4})", t)
        if m2:
            return int(m2.group(1)), 1
        return None
    year = int(m.group(1))
    p = m.group(2)
    if p.isdigit():
        idx = int(p)
    else:
        idx = _ROMANOS.index(p) if p in _ROMANOS else 1
    return year, idx


def _secuencia_periodos(inicio_txt, ppa, cantidad):
    """Genera 'cantidad' códigos de período consecutivos desde 'inicio_txt'
    (p.ej. 2020-I), rodando al año siguiente cada 'ppa' períodos."""
    parsed = _parse_periodo_inicio(inicio_txt)
    if not parsed or cantidad <= 0:
        return []
    year, idx = parsed
    ppa = int(ppa) if ppa and int(ppa) >= 1 else 2
    if idx > ppa:
        idx = 1
    out = []
    for _ in range(cantidad):
        rom = _ROMANOS[idx] if idx < len(_ROMANOS) else str(idx)
        out.append(f"{year}-{rom}")
        idx += 1
        if idx > ppa:
            idx = 1
            year += 1
    return out


_MESES_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# Régimen académico por programa (punto 10):
#  - Educación Inicial: SEMESTRAL (2 períodos por año: I y II).
#  - Educación Primaria y Biología: TRIMESTRAL (3 períodos por año: I, II y III).
#  - El resto de los programas: semestral por defecto.
# Devuelve (periodos_por_anio, texto_legible).
def _regimen_programa_info(programa):
    up = (programa or "").upper()
    # Programas TRIMESTRALES (3 períodos por año: I, II y III), según las
    # mallas oficiales enviadas. Educación Inicial y Matemática son SEMESTRALES
    # (2 por año); el resto trimestral. Matemática puede variar según la malla,
    # por eso el formulario permite ajustar los "períodos por año".
    trimestrales = [
        "PRIMARIA", "BIOLOG", "F\u00cdSICA", "FISICA", "QU\u00cdMICA", "QUIMICA",
        "GEOGRAF", "HISTORIA", "CIUDADAN", "GHC",
        "INGL", "LENGUA EXTRANJERA", "LENGUA",
        "GESTI\u00d3N", "GESTION", "INSTITUCIONAL", "DESARROLLO INSTITUCIONAL",
        "J\u00d3VENES", "JOVENES", "ADULTOS", "ADULTAS",
        "ESPECIAL",
    ]
    # Educación Física es trimestral (evitar confundir con "Matemática"):
    if "EDUCACI" in up and "F\u00cdSIC" in up or "EDUCACION FISIC" in up:
        return 3, "Trimestral (3 períodos por año: I, II y III)"
    for kw in trimestrales:
        if kw in up:
            return 3, "Trimestral (3 períodos por año: I, II y III)"
    # Inicial, Matemática y cualquier otro no listado: semestral por defecto.
    return 2, "Semestral (2 períodos por año: I y II)"


def _regimen_programa(programa):
    """Texto legible del régimen del programa (semestral / trimestral)."""
    return _regimen_programa_info(programa)[1]


def _fecha_larga_es(dt=None):
    dt = dt or datetime.now()
    return f"{dt.day} de {_MESES_ES[dt.month]} de {dt.year}"


def titulo_por_genero(programa, sexo):
    """Devuelve el título/grado redactado según el género del titular.
    sexo: 'F'/'FEMENINO' -> forma femenina; cualquier otro valor -> masculino.
    Ej.: 'LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN FÍSICA'
         -> Femenino: 'LICENCIADA EN EDUCACIÓN, MENCIÓN EDUCACIÓN FÍSICA'
         -> Masculino: 'LICENCIADO EN EDUCACIÓN, MENCIÓN EDUCACIÓN FÍSICA'"""
    p = (programa or "").strip()
    up = p.upper()
    fem = str(sexo or "").upper().startswith("F")
    if up.startswith("LICENCIADO/A"):
        base = "LICENCIADA" if fem else "LICENCIADO"
        return base + p[len("LICENCIADO/A"):]
    if up.startswith("LICENCIATURA EN"):
        base = "LICENCIADA EN" if fem else "LICENCIADO EN"
        return base + p[len("LICENCIATURA EN"):]
    if up.startswith("DOCTOR(A)"):
        base = "DOCTORA" if fem else "DOCTOR"
        return base + p[len("DOCTOR(A)"):]
    if up.startswith("ESPECIALIZACIÓN EN"):
        # El título profesional es 'ESPECIALISTA EN ...' (igual en ambos géneros)
        return "ESPECIALISTA EN" + p[len("ESPECIALIZACIÓN EN"):]
    if up.startswith("MAESTRÍA EN"):
        # El grado académico es 'MAGÍSTER EN ...' (igual en ambos géneros)
        return "MAGÍSTER EN" + p[len("MAESTRÍA EN"):]
    return p


# ------------------------------------------------------------
# MALLAS CURRICULARES (materias con U.C. por programa)
# ------------------------------------------------------------

def obtener_malla(programa, incluir_introductorio=True):
    """Lista de materias del programa, en orden. Cada item es un dict:
    {orden, periodo, materia, creditos, es_introductorio}."""
    conn = get_db()
    c = conn.cursor()
    if incluir_introductorio:
        c.execute("""SELECT orden, periodo, materia, creditos, es_introductorio, periodo_orden
                     FROM mallas WHERE programa=? ORDER BY orden, id""", (programa,))
    else:
        c.execute("""SELECT orden, periodo, materia, creditos, es_introductorio, periodo_orden
                     FROM mallas WHERE programa=? AND es_introductorio=0 ORDER BY orden, id""", (programa,))
    filas = c.fetchall()
    conn.close()
    return [{"orden": r[0], "periodo": r[1] or "", "materia": r[2],
             "creditos": r[3] or 0, "es_introductorio": int(r[4] or 0),
             "periodo_orden": int(r[5] or 0)} for r in filas]


def guardar_materia_malla(programa, periodo, materia, creditos, es_introductorio, orden=None):
    """Agrega o actualiza una materia de la malla de un programa."""
    conn = get_db()
    c = conn.cursor()
    if orden is None:
        c.execute("SELECT COALESCE(MAX(orden),0)+1 FROM mallas WHERE programa=?", (programa,))
        orden = c.fetchone()[0]
    try:
        c.execute("""INSERT INTO mallas (programa, orden, periodo, materia, creditos, es_introductorio, periodo_orden)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (programa, int(orden), periodo, materia, float(creditos or 0), int(es_introductorio), _orden_desde_periodo(periodo, int(orden))))
        ok = True
    except sqlite3.IntegrityError:
        # Ya existe esa materia en ese programa -> actualizar
        c.execute("""UPDATE mallas SET orden=?, periodo=?, creditos=?, es_introductorio=?, periodo_orden=?
                     WHERE programa=? AND materia=?""",
                  (int(orden), periodo, float(creditos or 0), int(es_introductorio), _orden_desde_periodo(periodo, int(orden)), programa, materia))
        ok = True
    conn.commit()
    conn.close()
    return ok


def eliminar_materia_malla(programa, materia):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM mallas WHERE programa=? AND materia=?", (programa, materia))
    conn.commit()
    conn.close()


def reemplazar_malla(programa, filas):
    """Reemplaza toda la malla de un programa. filas: lista de dicts con
    periodo, materia, creditos, es_introductorio (en el orden deseado)."""
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM mallas WHERE programa=?", (programa,))
    orden = 1
    _grupo = 0
    _periodo_prev = None
    for f in filas:
        _per = f.get("periodo", "")
        if _per != _periodo_prev:
            _grupo += 1
            _periodo_prev = _per
        _po = _orden_desde_periodo(_per, _grupo)
        c.execute("""INSERT OR IGNORE INTO mallas (programa, orden, periodo, materia, creditos, es_introductorio, periodo_orden)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (programa, orden, _per, f.get("materia", ""),
                   float(f.get("creditos", 0) or 0), int(f.get("es_introductorio", 0)), int(_po)))
        orden += 1
    conn.commit()
    conn.close()


def _seed_mallas_oficiales(c):
    """Carga UNA sola vez las mallas oficiales reconocidas de los documentos
    aprobados (Educación Inicial completa; Educación Especial Trayectos 3-4 / TSU).
    Usa un sello de versión y no pisa mallas que el administrador ya tenga."""
    VERSION = "mallas_oficiales_v1"
    c.execute("SELECT COUNT(*) FROM listas_editables WHERE tipo_lista='meta' AND categoria_padre='mallas_seed' AND valor=?", (VERSION,))
    if c.fetchone()[0] > 0:
        return
    for prog, filas in _MALLAS_OFICIALES.items():
        c.execute("SELECT COUNT(*) FROM mallas WHERE programa=?", (prog,))
        if c.fetchone()[0] > 0:
            continue
        orden = 1
        for (po, per, mat, uc) in filas:
            c.execute("""INSERT OR IGNORE INTO mallas (programa, orden, periodo, materia, creditos, es_introductorio, periodo_orden)
                         VALUES (?, ?, ?, ?, ?, 0, ?)""",
                      (prog, orden, per, mat, float(uc), int(po)))
            orden += 1
    c.execute("INSERT OR IGNORE INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES ('meta','mallas_seed',?)", (VERSION,))


def obtener_programas_con_malla():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT programa FROM mallas ORDER BY programa")
    r = [x[0] for x in c.fetchall()]
    conn.close()
    return r


# ------------------------------------------------------------
# NOTAS (calificaciones por estudiante)
# ------------------------------------------------------------

def obtener_notas(cedula):
    """Devuelve un dict {materia: nota} de las notas cargadas del estudiante."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT materia, nota FROM notas WHERE cedula=?", (cedula,))
    r = {row[0]: row[1] for row in c.fetchall()}
    conn.close()
    return r


def obtener_periodos_notas(cedula):
    """Devuelve un dict {materia: periodo} con el período tal como se cargó
    para cada materia del estudiante (por ejemplo "2020-I"). Si una materia
    no tiene período guardado, no aparece en el dict (el certificado usa
    entonces la secuencia calculada)."""
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT materia, periodo FROM notas WHERE cedula=?", (cedula,))
        r = {row[0]: (row[1] or "").strip() for row in c.fetchall() if (row[1] or "").strip()}
    except sqlite3.OperationalError:
        r = {}  # BD antigua sin la columna 'periodo'
    conn.close()
    return r


def guardar_notas(cedula, programa, notas_por_materia):
    """Guarda/actualiza las notas del estudiante. notas_por_materia: dict
    {materia: (creditos, nota)} o {materia: (creditos, nota, periodo)}.
    Las notas vacías se ignoran."""
    conn = get_db()
    c = conn.cursor()
    for materia, valores in notas_por_materia.items():
        # Aceptar tanto (creditos, nota) como (creditos, nota, periodo)
        if len(valores) >= 3:
            creditos, nota, periodo = valores[0], valores[1], valores[2]
        else:
            creditos, nota = valores[0], valores[1]
            periodo = ""
        nota = str(nota or "").strip()
        periodo = str(periodo or "").strip().upper()
        if nota == "":
            c.execute("DELETE FROM notas WHERE cedula=? AND materia=?", (cedula, materia))
            continue
        c.execute("SELECT id FROM notas WHERE cedula=? AND materia=?", (cedula, materia))
        if c.fetchone():
            c.execute("UPDATE notas SET nota=?, creditos=?, programa=?, periodo=? WHERE cedula=? AND materia=?",
                      (nota, float(creditos or 0), programa, periodo, cedula, materia))
        else:
            c.execute("""INSERT INTO notas (cedula, programa, materia, creditos, nota, periodo)
                         VALUES (?, ?, ?, ?, ?, ?)""",
                      (cedula, programa, materia, float(creditos or 0), nota, periodo))
    conn.commit()
    conn.close()


def generar_certificado_pdf(row):
    """CERTIFICACION DE CALIFICACIONES alineada al MODELO OFICIAL de la UNEM:
    encabezado con escudo y serial, parrafo del Secretario, tabla
    Periodo / Unidad Curricular / U.C. / Calificacion (numero + palabra),
    nota de escala, parrafo especial para TSU, firma y sello reales,
    y representante de la Secretaria del estado."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.graphics.barcode import code128
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics import renderPDF

    def _g(k):
        try:
            v = row.get(k, "")
        except AttributeError:
            v = row[k] if k in row else ""
        return str(v or "").strip()

    ancho, alto = letter
    margen = 18 * mm
    x0, x1 = margen, ancho - margen
    centro = ancho / 2

    nombre_completo = (_g("nombres") + " " + _g("apellidos")).strip()
    cedula = _g("cedula")
    programa = _g("programa")
    estado = _g("estado")
    municipio = _g("municipio")
    sexo = _g("sexo")
    tipo_estudiante = _g("tipo_estudiante").upper()
    es_tsu = "TSU" in tipo_estudiante
    periodo_inicio = _g("periodo_inicio")
    try:
        ppa = int(float(_g("periodos_por_anio") or 2))
    except (ValueError, TypeError):
        ppa = 2
    if ppa < 1:
        ppa = 2
    fecha_emision = _fecha_larga_es()
    titulo_grado = titulo_por_genero(programa, sexo)
    _ced_alnum = "".join(ch for ch in cedula if ch.isalnum())
    serial = str(datetime.now().year) + "-I-" + _ced_alnum

    malla = obtener_malla(programa, incluir_introductorio=False)
    notas = obtener_notas(cedula)
    periodos_notas = obtener_periodos_notas(cedula)

    # ----- TSU: solo se certifican las materias del Trayecto III en adelante.
    # A un TSU se le reconocen los dos primeros trayectos (T1 y T2), así que en
    # la certificación solo aparecen T3 y T4. El primer período de cada trayecto
    # se calcula con la fórmula: inicio del Trayecto III = 2*(períodos por año)+1.
    #   - Semestral (2/año): desde el período 5.
    #   - Trimestral (3/año): desde el período 7.
    #   - Por trayecto (1/año, ej. Pedagogía Cultural): desde el período 3.
    if es_tsu:
        umbral_t3 = 2 * ppa + 1
        malla = [m for m in malla if int(m.get("periodo_orden") or 0) >= umbral_t3]

    pos = []
    for m in malla:
        po = int(m.get("periodo_orden") or 0)
        if po not in pos:
            pos.append(po)
    pos_sorted = sorted(p for p in pos if p > 0)
    codigos = _secuencia_periodos(periodo_inicio, ppa, len(pos_sorted)) if periodo_inicio else []
    po_code = {}
    for i, po in enumerate(pos_sorted):
        po_code[po] = codigos[i] if i < len(codigos) else ""

    escudo = next((p for p in ESCUDO_PATHS if os.path.exists(p)), None)
    firma = next((p for p in FIRMA_PATHS if os.path.exists(p)), None)
    sello = next((p for p in SELLO_PATHS if os.path.exists(p)), None)

    _cod_barras = _ced_alnum or "0"

    class NumberedCanvas(canvas.Canvas):
        """Lienzo que, al final, conoce el TOTAL de paginas y estampa en
        cada hoja (arriba-derecha) el serial + 'Pagina X de Y' y el codigo
        de barras debajo, tal como el modelo aprobado."""
        def __init__(self, *a, **k):
            canvas.Canvas.__init__(self, *a, **k)
            self._guardadas = []
        def showPage(self):
            self._guardadas.append(dict(self.__dict__))
            self._startPage()
        def save(self):
            total = len(self._guardadas)
            for i, estado_pag in enumerate(self._guardadas, start=1):
                self.__dict__.update(estado_pag)
                self._encabezado_derecho(i, total)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)
        def _encabezado_derecho(self, num, total):
            yb = alto - margen
            self.setFont("Helvetica", 7.5)
            self.setFillColorRGB(0, 0, 0)
            # "Pagina X de Y-serial"  (ej: Pagina 2 de 2-2026-I-11145691)
            texto_pag = "P\u00e1gina %d de %d-%s" % (num, total, serial)
            self.drawRightString(x1, yb, texto_pag)
            # Codigo de barras debajo del indicador de pagina
            try:
                bc = code128.Code128(_cod_barras, barHeight=9 * mm, barWidth=0.32 * mm)
                bc.drawOn(self, x1 - bc.width, yb - 12 * mm)
            except Exception:
                pass

    buffer = BytesIO()
    c = NumberedCanvas(buffer, pagesize=letter)

    def _wrap(texto, fuente, tam, ancho_max):
        out, linea = [], ""
        for w in str(texto).split():
            prueba = (linea + " " + w).strip()
            if stringWidth(prueba, fuente, tam) <= ancho_max or not linea:
                linea = prueba
            else:
                out.append(linea); linea = w
        if linea:
            out.append(linea)
        return out

    def _justif(texto, fuente, tam, ancho_max, y, alto_linea, ultima_justif=False):
        """Dibuja 'texto' JUSTIFICADO (bordes parejos a ambos lados) desde x0.
        Devuelve la nueva 'y'. La ultima linea de cada parrafo NO se justifica."""
        lineas = _wrap(texto, fuente, tam, ancho_max)
        c.setFont(fuente, tam)
        for idx, ln in enumerate(lineas):
            es_ultima = (idx == len(lineas) - 1)
            palabras = ln.split()
            if es_ultima or len(palabras) == 1:
                c.drawString(x0, y, ln)
            else:
                ancho_txt = stringWidth(ln, fuente, tam)
                extra = (ancho_max - ancho_txt) / (len(palabras) - 1)
                cx = x0
                for w in palabras:
                    c.drawString(cx, y, w)
                    cx += stringWidth(w, fuente, tam) + stringWidth(" ", fuente, tam) + extra
            y -= alto_linea
        return y

    def _timbre(y):
        # Recuadro "TIMBRE FISCAL" VERTICAL (rectángulo hacia abajo) en la
        # esquina superior IZQUIERDA, según la observación del usuario.
        bw, bh = 16 * mm, 26 * mm
        c.setStrokeColorRGB(0.35, 0.35, 0.35); c.setLineWidth(0.6)
        c.rect(x0, y - bh, bw, bh, fill=0, stroke=1)
        c.setFont("Helvetica", 6)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawCentredString(x0 + bw / 2, y - 5 * mm, "TIMBRE")
        c.drawCentredString(x0 + bw / 2, y - 9 * mm, "FISCAL")
        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0, 0, 0)
        return y - 3 * mm

    def _encabezado(y):
        y = _timbre(y)
        # bajar un poco para no chocar con el bloque superior-derecho (pagina/barras)
        y -= 12 * mm
        if escudo:
            try:
                ew, eh = 21 * mm, 23 * mm
                c.drawImage(ImageReader(escudo), centro - ew / 2, y - eh,
                            width=ew, height=eh, preserveAspectRatio=True, mask="auto")
                # MAS espacio entre el escudo y el texto
                y -= eh + 7 * mm
            except Exception:
                y -= 6 * mm
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(centro, y, "REP\u00daBLICA BOLIVARIANA DE VENEZUELA")
        y -= 4.2 * mm
        c.setFont("Helvetica", 8.5)
        c.drawCentredString(centro, y, "Universidad Nacional Experimental del Magisterio \u201cSamuel Robinson\u201d")
        y -= 3.8 * mm
        c.setFont("Helvetica", 8)
        c.drawCentredString(centro, y, "Secretar\u00eda")
        y -= 3 * mm
        # Linea separadora debajo de "Secretaria" (parte del formato)
        c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.7)
        c.line(x0 + 25 * mm, y, x1 - 25 * mm, y)
        y -= 6 * mm
        c.setFont("Helvetica-Bold", 12.5)
        c.drawCentredString(centro, y, "CERTIFICACI\u00d3N DE CALIFICACIONES")
        y -= 7 * mm
        return y

    # Columnas de la tabla (con lineas divisorias verticales)
    col_per = x0 + 28 * mm          # fin de la columna "Periodo Cursado"
    col_ucv = x1 - 46 * mm          # fin de "Unidad Curricular" / inicio "U.C."
    col_cal = x1 - 34 * mm          # fin de "U.C." / inicio "Calificacion"
    col_uc = col_cal                # borde derecho para los valores de U.C.
    col_calif = x1
    _cols_x = [x0, col_per, col_ucv, col_cal, x1]

    def _vlines(y_top, y_bot):
        c.setStrokeColorRGB(0.45, 0.45, 0.45); c.setLineWidth(0.4)
        for cx in _cols_x:
            c.line(cx, y_top, cx, y_bot)

    def _cab_tabla(y):
        c.setFillColorRGB(0.12, 0.16, 0.5)
        c.rect(x0, y - 6 * mm, x1 - x0, 6 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x0 + 2 * mm, y - 4.2 * mm, "Per\u00edodo Cursado")
        c.drawCentredString((col_per + col_ucv) / 2, y - 4.2 * mm, "Nombre de la Unidad Curricular")
        c.drawCentredString((col_ucv + col_cal) / 2, y - 4.2 * mm, "U.C.")
        c.drawCentredString((col_cal + x1) / 2, y - 4.2 * mm, "Calificaci\u00f3n")
        c.setFillColorRGB(0, 0, 0)
        # borde superior de la cabecera
        c.setStrokeColorRGB(0.45, 0.45, 0.45); c.setLineWidth(0.4)
        c.line(x0, y, x1, y)
        _vlines(y, y - 6 * mm)
        return y - 6 * mm


    y = _encabezado(alto - margen)

    intro = ("Quien suscribe LENIN ROBERTO ROMERO ROSA, titular de la C\u00e9dula de identidad "
             "No. V-2.956.814, secretario de la Universidad Nacional Experimental del "
             "Magisterio \u201cSamuel Robinson\u201d, con asiento principal en la ciudad de Caracas, "
             "Distrito Capital, Venezuela, certifica que en el Expediente Acad\u00e9mico "
             "Estudiantil UNEM correspondiente a " + nombre_completo + ", C\u00e9dula de Identidad "
             "No. " + cedula + ", quien curs\u00f3 estudios en el Programa Nacional de Formaci\u00f3n en "
             "Educaci\u00f3n para optar al T\u00edtulo de " + titulo_grado + ", en el Estado " + estado + ", "
             "municipio " + municipio + ", se encuentra su registro acad\u00e9mico en donde consta "
             "que curs\u00f3 y aprob\u00f3 las Unidades Curriculares que se especifican a continuaci\u00f3n:")
    c.setFont("Helvetica", 9)
    y = _justif(intro, "Helvetica", 9, x1 - x0, y, 4.6 * mm)
    y -= 3 * mm

    y = _cab_tabla(y)
    total_uc = 0.0
    fila_alto = 4.6 * mm
    ancho_mat = (col_ucv - 2 * mm) - (col_per + 2 * mm)
    if not malla:
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(col_per + 2 * mm, y - 4 * mm, "(A\u00fan no hay malla curricular cargada para este programa.)")
        c.setStrokeColorRGB(0.45, 0.45, 0.45); c.setLineWidth(0.4)
        c.line(x0, y - fila_alto, x1, y - fila_alto)
        _vlines(y, y - fila_alto)
        y -= fila_alto
    for m in malla:
        nota_raw = notas.get(m["materia"], "")
        calif = _calificacion_texto(nota_raw) if nota_raw else "POR CURSAR"
        mat_lines = _wrap(m["materia"], "Helvetica", 8, ancho_mat) or [""]
        alto_fila = max(fila_alto, len(mat_lines) * 3.6 * mm + 2 * mm)
        # Reserva mínima: solo hay que garantizar que la fila y la fila TOTAL
        # entren en la página. El bloque de cierre+firma se maneja aparte como
        # una unidad (nunca se dibuja la firma sola). Reservar poco = más filas
        # por página = menos páginas (máximo deseado: 4).
        if y - alto_fila < margen + 18 * mm:
            c.showPage()
            y = _encabezado(alto - margen)
            y = _cab_tabla(y)
        po = int(m.get("periodo_orden") or 0)
        cod = periodos_notas.get(m["materia"], "") or po_code.get(po, "")
        uc = float(m["creditos"] or 0)
        total_uc += uc
        yb = y - 4 * mm
        c.setFont("Helvetica", 7.5)
        c.drawString(x0 + 2 * mm, yb, cod)
        c.setFont("Helvetica", 8)
        for i, ml in enumerate(mat_lines):
            c.drawString(col_per + 2 * mm, yb - i * 3.6 * mm, ml)
        c.drawCentredString((col_ucv + col_cal) / 2, yb, ("%g" % uc if uc else "-"))
        c.setFont("Helvetica", 7)
        c.drawCentredString((col_cal + x1) / 2, yb, calif)
        # bordes de la fila (horizontal inferior + verticales de columnas)
        c.setStrokeColorRGB(0.45, 0.45, 0.45); c.setLineWidth(0.4)
        c.line(x0, y - alto_fila, x1, y - alto_fila)
        _vlines(y, y - alto_fila)
        y -= alto_fila
    # Fila TOTAL UNIDADES DE CRÉDITO: por solicitud del usuario, NO se imprime
    # en la certificación. El total sigue visible en pantalla (Ver Calificaciones).
    # Se conserva el cálculo de total_uc por si se necesita internamente.
    y -= 3 * mm

    if y < margen + 72 * mm:
        c.showPage(); y = _encabezado(alto - margen)
    nota_escala = ("Se expone en la certificaci\u00f3n solamente las unidades curriculares "
                   "cursadas y aprobadas en el periodo respectivo. La escala de calificaci\u00f3n "
                   "es del 1 al 20 con m\u00ednima aprobatoria 12 (doce). Son consideradas tambi\u00e9n "
                   "las calificaciones de AP \u201cAprobado\u201d, AC \u201cAprobada por Acreditaci\u00f3n\u201d.")
    c.setFont("Helvetica", 8)
    for ln in _wrap(nota_escala, "Helvetica", 8, x1 - x0):
        c.drawString(x0, y, ln); y -= 4 * mm
    y -= 2 * mm

    if es_tsu:
        parr_tsu = ("Estas Notas Certificadas pertenecen a un Profesional al cual se le "
                    "reconoci\u00f3 dos trayectos (T1 y T2) y curs\u00f3 y aprob\u00f3 o acredit\u00f3 dos "
                    "trayectos (T3 y T4) de la malla del Plan de Estudios para obtener el "
                    "T\u00edtulo de: " + titulo_grado + " y as\u00ed dar cumplimiento a la resoluci\u00f3n del "
                    "Consejo Directivo No: 083.12.2022.")
        c.setFont("Helvetica", 8)
        for ln in _wrap(parr_tsu, "Helvetica", 8, x1 - x0):
            c.drawString(x0, y, ln); y -= 4 * mm
        y -= 2 * mm

    cierre = ("Certificaci\u00f3n que se expide a petici\u00f3n de la parte interesada a los "
              "efectos y fines consiguientes, en Caracas el " + fecha_emision + ".")
    c.setFont("Helvetica", 8.5)
    for ln in _wrap(cierre, "Helvetica", 8.5, x1 - x0):
        c.drawString(x0, y, ln); y -= 4.4 * mm
    y -= 14 * mm

    if firma:
        try:
            fw, fh = 42 * mm, 17 * mm
            c.drawImage(ImageReader(firma), centro - fw / 2, y, width=fw, height=fh,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    if sello:
        try:
            sw, sh = 24 * mm, 24 * mm
            # Sello AL COSTADO (derecha) de la firma, alineado a su altura y
            # pegado al margen derecho para no obstaculizar el texto ni el
            # nombre centrado del Secretario.
            c.drawImage(ImageReader(sello), x1 - sw, y + 1 * mm, width=sw, height=sh,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.7)
    c.line(centro - 40 * mm, y, centro + 40 * mm, y)
    y -= 4.5 * mm
    c.setFont("Helvetica-Bold", 9.5)
    c.drawCentredString(centro, y, "LENIN ROBERTO ROMERO ROSA")
    y -= 4 * mm
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(centro, y, "SECRETARIO")
    y -= 3.8 * mm
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(centro, y, "Universidad Nacional Experimental del Magisterio \u201cSamuel Robinson\u201d")
    y -= 3.5 * mm
    c.drawCentredString(centro, y, "Seg\u00fan Gaceta No: 41.632   Resoluci\u00f3n Conjunta No. 0026/002")
    y -= 13 * mm

    # El bloque "Representante de la Secretaría del Estado" debe quedar ENCIMA
    # de la nota de pie de página y sin chocar con ella (observación del usuario).
    _piso_representante = margen + 30 * mm
    if y < _piso_representante:
        y = _piso_representante
    c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.6)
    c.line(x0, y, x0 + 70 * mm, y)
    y -= 4 * mm
    c.setFont("Helvetica", 8)
    c.drawString(x0, y, "Representante de la Secretar\u00eda")
    y -= 3.6 * mm
    c.drawString(x0, y, "del Estado " + estado)

    qr_texto = ("UNEM - CERTIFICACION DE CALIFICACIONES\n" +
                "Nombres: " + nombre_completo + "\n" +
                "Titulo: " + titulo_grado + "\n" +
                "Cedula: " + cedula + "\n" +
                "Estado: " + estado + "\n" +
                "Serial: " + serial + "\n" +
                "Emision: " + fecha_emision)
    y_pie = margen + 2 * mm
    qsize = 22 * mm
    # Codigo QR en la esquina inferior DERECHA
    try:
        qrw = QrCodeWidget(qr_texto)
        b = qrw.getBounds()
        d = Drawing(qsize, qsize, transform=[qsize / (b[2] - b[0]), 0, 0, qsize / (b[3] - b[1]), 0, 0])
        d.add(qrw)
        renderPDF.draw(d, c, x1 - qsize, y_pie)
    except Exception:
        pass
    # Nota al pie: solo valido con sello humedo y firma autografa
    nota_pie = ("V\u00e1lido solo con el sello h\u00famedo regional y la firma aut\u00f3grafa del "
                "funcionario autorizado. Cualquier enmienda o tachadura anula el presente documento.")
    c.setFont("Helvetica-Oblique", 6.8)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    yy = y_pie + 16 * mm
    for ln in _wrap(nota_pie, "Helvetica-Oblique", 6.8, x1 - x0 - qsize - 6 * mm):
        c.drawString(x0, yy, ln); yy -= 3.4 * mm
    c.setFillColorRGB(0, 0, 0)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# INICIALIZACIÓN
# ============================================================

init_database()

# CSS Institucional
st.markdown("""
<style>
    /* Ocultar la barra/botones propios de Streamlit (incluye "Manage app",
       "Deploy", el menú de la esquina y el pie "Made with Streamlit").
       Solicitud del usuario: quitar "Manage app" en todos los niveles. */
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="manage-app-button"] { display: none !important; }
    .stDeployButton { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    header [data-testid="stToolbar"] { display: none !important; }
    footer { visibility: hidden !important; }
    .main-header {
        background: linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #1565c0 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .main-header h1 { margin:0; font-size:1.6rem; }
    .main-header p { margin:0.2rem 0 0 0; font-size:0.85rem; opacity:0.9; }
    .stat-card {
        background: #f8f9fa;
        border-left: 4px solid #1565c0;
        padding: 0.8rem;
        border-radius: 8px;
        text-align: center;
    }
    .stat-card h2 { margin:0; color:#1565c0; font-size:1.5rem; }
    .stat-card p { margin:0; color:#666; font-size:0.8rem; }
    .stat-green { border-left-color: #4caf50; }
    .stat-green h2 { color: #4caf50; }
    .stat-orange { border-left-color: #ff9800; }
    .stat-orange h2 { color: #ff9800; }
    .stat-red { border-left-color: #f44336; }
    .stat-red h2 { color: #f44336; }
    .success-box {
        background: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 8px;
    }
    .warning-box {
        background: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 8px;
    }
    .logo-area {
        text-align: center;
        padding: 1rem 0;
    }
    .logo-placeholder {
        width: 120px; height: 120px;
        border: 3px dashed #1565c0;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
        color: #1565c0;
        font-size: 0.8rem;
        text-align: center;
        background: #e3f2fd;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# GESTIÓN DE SESIÓN
# ============================================================

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.nombre = None
    st.session_state.correo = None


def cerrar_sesion():
    st.session_state.autenticado = False
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.nombre = None
    st.session_state.correo = None
    st.rerun()


# ============================================================
# LOGIN
# ============================================================

if not st.session_state.autenticado:
    # Logo placeholder
    st.markdown("""
    <div class='logo-area'>
        <div class='logo-placeholder'>
            LOGO<br>INSTITUCIONAL<br>(Agregue aquí)
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='main-header'>
        <h1>📋 Sistema de Registro de Expedientes</h1>
        <p>UNEM — Período 2026-II</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    col_login1, col_login2, col_login3 = st.columns([1,1,1])
    with col_login2:
        st.subheader("🔐 Iniciar Sesión")
        usuario = st.text_input("👤 Usuario", key="login_user")
        clave = st.text_input("🔑 Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if usuario and clave:
                resultado = verificar_credenciales(usuario, clave)
                if resultado:
                    st.session_state.autenticado = True
                    st.session_state.usuario = resultado[0]
                    st.session_state.rol = resultado[1]
                    st.session_state.nombre = resultado[2]
                    st.session_state.correo = resultado[3]
                    # Estado asignado (solo aplica al Administrador Regional / Nivel 3)
                    st.session_state.estado_region = resultado[4] if len(resultado) > 4 else ""
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Ingrese usuario y contraseña")

        st.markdown("---")
        st.caption("🔒 Acceso restringido. Ingrese sus credenciales institucionales.")

    st.stop()


# ============================================================
# SIDEBAR - NAVEGACIÓN SEGÚN ROL
# ============================================================

rol = st.session_state.rol
nombre_usuario = st.session_state.nombre
# Para el Administrador Regional (Nivel 3): el ESTADO asignado se guarda en la
# clave y se carga al iniciar sesión. Solo puede ver y trabajar los registros
# de ese estado.
estado_regional = st.session_state.get("estado_region", "") if rol == "ADMIN_REGIONAL" else None
if rol == "ADMIN_REGIONAL" and not estado_regional:
    # Compatibilidad: claves regionales antiguas que usaban el nombre como estado
    estado_regional = nombre_usuario

with st.sidebar:
    # Logo en sidebar
    st.markdown("""
    <div class='logo-area'>
        <div class='logo-placeholder' style='width:80px;height:80px;font-size:0.6rem;'>
            LOGO
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"### 👤 {nombre_usuario}")

    rol_nombre = {"ADMIN_PRINCIPAL": "🏛️ Administrador Principal",
                   "ADMIN_AUXILIAR": "🛡️ Administrador Auxiliar",
                   "ADMIN_REGIONAL": "📍 Administrador Regional"}
    st.caption(f"**Rol:** {rol_nombre.get(rol, rol)}")

    st.markdown("---")

    # Menú según rol
    if rol == "ADMIN_PRINCIPAL":
        menu = st.radio("📍 Módulos", [
            "🏠 Inicio",
            "📊 Consultar Expedientes",
            "📝 Registrar Expediente",
            "🔍 Buscar Expediente",
            "📝 Registro de Calificaciones",
            "📊 Ver Calificaciones",
            "📄 Generar Documentos",
            "📋 Solicitudes de Modificación",
            "🧮 Mallas Curriculares",
            "📈 Estadísticas",
            "👥 Gestión de Usuarios",
            "⚙️ Configuración de Listas",
            "🏫 Aulas Taller",
            "📧 Configuración de Correo",
            "📥 Respaldo de Datos",
        ], key="nav_principal")
    elif rol == "ADMIN_AUXILIAR":
        menu = st.radio("📍 Módulos", [
            "🏠 Inicio",
            "📊 Consultar Expedientes",
            "📝 Registrar Expediente",
            "🔍 Buscar Expediente",
            "📝 Registro de Calificaciones",
            "📊 Ver Calificaciones",
            "📄 Generar Documentos",
            "📋 Solicitudes de Modificación",
            "🧮 Mallas Curriculares",
            "📈 Estadísticas",
            "👥 Gestión de Usuarios",
            "🏫 Aulas Taller",
            "📧 Configuración de Correo",
            "📥 Respaldo de Datos",
        ], key="nav_auxiliar")
    else:  # ADMIN_REGIONAL
        menu = st.radio("📍 Módulos", [
            "🏠 Inicio",
            "📊 Consultar Expedientes",
            "📝 Registrar Expediente",
            "🔍 Buscar Expediente",
            "📝 Registro de Calificaciones",
            "📊 Ver Calificaciones",
            "📋 Mis Solicitudes",
            "📈 Estadísticas",
        ], key="nav_regional")

    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        cerrar_sesion()


# ============================================================
# HEADER DINÁMICO
# ============================================================

def mostrar_header(titulo, subtitulo=""):
    st.markdown(f"""
    <div class='main-header'>
        <h1>{titulo}</h1>
        <p>{subtitulo}</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# PÁGINA: INICIO
# ============================================================

if menu == "🏠 Inicio":
    mostrar_header("📋 Expedientes UNEM", "UNEM — Período 2026-II")

    stats = obtener_estadisticas()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='stat-card'><h2>{stats['total']:,}</h2><p>Total Registros</p></div>", unsafe_allow_html=True)
    with col2:
        ingresos = stats['por_tipo_expediente'].get('INGRESO', 0)
        st.markdown(f"<div class='stat-card stat-green'><h2>{ingresos:,}</h2><p>Ingresos</p></div>", unsafe_allow_html=True)
    with col3:
        prosecucion = stats['por_tipo_expediente'].get('PROSECUCION', 0)
        st.markdown(f"<div class='stat-card stat-orange'><h2>{prosecucion:,}</h2><p>Prosecución</p></div>", unsafe_allow_html=True)
    with col4:
        egresados = stats['por_tipo_expediente'].get('EGRESADO', 0)
        st.markdown(f"<div class='stat-card stat-red'><h2>{egresados:,}</h2><p>Egresados</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("🏛️ Registros por Estado")
        if stats['por_estado']:
            df_est = pd.DataFrame(list(stats['por_estado'].items()), columns=["Estado", "Cantidad"])
            df_est = df_est.sort_values("Cantidad", ascending=False)
            st.dataframe(df_est, use_container_width=True, hide_index=True)
        else:
            st.info("No hay registros aún.")

    with col_r2:
        st.subheader("📚 Registros por Tipo de Programa")
        if stats['por_tipo_programa']:
            df_tp = pd.DataFrame(list(stats['por_tipo_programa'].items()), columns=["Tipo Programa", "Cantidad"])
            df_tp = df_tp.sort_values("Cantidad", ascending=False)
            st.dataframe(df_tp, use_container_width=True, hide_index=True)
        else:
            st.info("No hay registros aún.")


# ============================================================
# PÁGINA: REGISTRAR EXPEDIENTE
# ============================================================

elif menu == "📝 Registrar Expediente":
    mostrar_header("📝 Registrar Nuevo Expediente", "Complete todos los campos obligatorios")

    def obtener_programas_para_tipo(tipo):
        """Obtiene programas de la BD primero, con fallback al dict estático"""
        programas_db = obtener_lista_editable("programa", tipo)
        if programas_db:
            return programas_db
        return TIPOS_PROGRAMA_PROGRAMAS.get(tipo, [])

    def on_estado_change():
        st.session_state.reg_municipio = None
        st.session_state.reg_aula_taller = None

    def on_tipo_programa_change():
        st.session_state.reg_programa = None

    def on_municipio_change():
        st.session_state.reg_aula_taller = None

    # Limpieza segura tras un registro exitoso: se hace ANTES de crear los widgets
    if st.session_state.get("_limpiar_registro"):
        for _k in ("reg_estado", "reg_municipio", "reg_tipo_programa",
                   "reg_programa", "reg_aula_taller", "reg_tipo_expediente",
                   "reg_nombres", "reg_apellidos", "reg_cedula_tipo", "reg_cedula_num", "reg_correo",
                   "reg_sexo", "reg_tipo_est", "reg_periodo_inicio", "reg_obs"):
            st.session_state.pop(_k, None)
        st.session_state._limpiar_registro = False

    if "reg_estado" not in st.session_state:
        st.session_state.reg_estado = None
    if "reg_municipio" not in st.session_state:
        st.session_state.reg_municipio = None
    if "reg_tipo_programa" not in st.session_state:
        st.session_state.reg_tipo_programa = None
    if "reg_programa" not in st.session_state:
        st.session_state.reg_programa = None
    if "reg_aula_taller" not in st.session_state:
        st.session_state.reg_aula_taller = None
    if "reg_tipo_expediente" not in st.session_state:
        st.session_state.reg_tipo_expediente = None

    st.markdown("#### 📍 Ubicación y Programa")
    col_a, col_b = st.columns(2)

    with col_a:
        if estado_regional:
            # Nivel 3: el estado queda fijo al estado que tiene asignado.
            estados_lista = [estado_regional] if estado_regional in ESTADOS_MUNICIPIOS else ["— Seleccione —"]
        else:
            estados_lista = ["— Seleccione —"] + list(ESTADOS_MUNICIPIOS.keys())
        estado_sel_idx = 0
        if st.session_state.reg_estado and st.session_state.reg_estado in estados_lista:
            estado_sel_idx = estados_lista.index(st.session_state.reg_estado)
        estado = st.selectbox(
            "🏛️ ESTADO *",
            estados_lista,
            index=estado_sel_idx,
            key="reg_estado",
            on_change=on_estado_change,
            disabled=bool(estado_regional),
        )
        estado_real = estado if estado != "— Seleccione —" else None

        if estado_real:
            municipios_disponibles = ["— Seleccione —"] + ESTADOS_MUNICIPIOS.get(estado_real, [])
        else:
            municipios_disponibles = ["— Primero seleccione un estado —"]

        municipio_sel_idx = 0
        if st.session_state.reg_municipio and estado_real:
            muni_list = ESTADOS_MUNICIPIOS.get(estado_real, [])
            if st.session_state.reg_municipio in muni_list:
                municipio_sel_idx = municipios_disponibles.index(st.session_state.reg_municipio)
        municipio = st.selectbox(
            "🏙️ MUNICIPIO *",
            municipios_disponibles,
            index=municipio_sel_idx,
            key="reg_municipio",
            on_change=on_municipio_change
        )
        municipio_real = municipio if municipio not in ["— Seleccione —", "— Primero seleccione un estado —"] else None

        if municipio_real:
            aulas_disponibles = obtener_aulas(estado_real, municipio_real)
            if aulas_disponibles:
                aulas_lista = ["— Seleccione —"] + aulas_disponibles
                aula_sel_idx = 0
                if st.session_state.reg_aula_taller and st.session_state.reg_aula_taller in aulas_disponibles:
                    aula_sel_idx = aulas_lista.index(st.session_state.reg_aula_taller)
                aula_taller = st.selectbox(
                    "🏫 AULA TALLER",
                    aulas_lista,
                    index=aula_sel_idx,
                    key="reg_aula_taller"
                )
                aula_taller_real = aula_taller if aula_taller != "— Seleccione —" else ""
            else:
                aula_taller_real = st.text_input(
                    "🏫 AULA TALLER",
                    placeholder="Ej: Aula 01 (No hay aulas registradas para este municipio)",
                    key="reg_aula_taller_text"
                )
        else:
            aula_taller_real = ""

    with col_b:
        tipos_lista = ["— Seleccione —"] + list(TIPOS_PROGRAMA_PROGRAMAS.keys())
        tipo_sel_idx = 0
        if st.session_state.reg_tipo_programa and st.session_state.reg_tipo_programa in TIPOS_PROGRAMA_PROGRAMAS:
            tipo_sel_idx = tipos_lista.index(st.session_state.reg_tipo_programa)
        tipo_programa = st.selectbox(
            "📚 TIPO DE PROGRAMA *",
            tipos_lista,
            index=tipo_sel_idx,
            key="reg_tipo_programa",
            on_change=on_tipo_programa_change
        )
        tipo_real = tipo_programa if tipo_programa != "— Seleccione —" else None

        if tipo_real:
            programas_disponibles = obtener_programas_para_tipo(tipo_real)
            programas_lista = ["— Seleccione —"] + programas_disponibles
        else:
            programas_lista = ["— Primero seleccione tipo de programa —"]

        prog_sel_idx = 0
        if st.session_state.reg_programa and tipo_real:
            progs = obtener_programas_para_tipo(tipo_real)
            if st.session_state.reg_programa in progs:
                prog_sel_idx = programas_lista.index(st.session_state.reg_programa)
        programa = st.selectbox(
            "🎓 PROGRAMA *",
            programas_lista,
            index=prog_sel_idx,
            key="reg_programa"
        )
        programa_real = programa if programa not in ["— Seleccione —", "— Primero seleccione tipo de programa —"] else None

    tipo_exp_lista = ["— Seleccione —"] + TIPOS_EXPEDIENTE
    tipo_exp_idx = 0
    if st.session_state.reg_tipo_expediente and st.session_state.reg_tipo_expediente in TIPOS_EXPEDIENTE:
        tipo_exp_idx = tipo_exp_lista.index(st.session_state.reg_tipo_expediente)
    tipo_expediente = st.selectbox(
        "📂 TIPO DE EXPEDIENTE *",
        tipo_exp_lista,
        index=tipo_exp_idx,
        key="reg_tipo_expediente"
    )
    tipo_exp_real = tipo_expediente if tipo_expediente != "— Seleccione —" else None

    st.markdown("---")
    st.markdown("#### 👤 Datos del Titular")

    with st.form("form_registro", clear_on_submit=False):
        col_c, col_d = st.columns(2)

        with col_c:
            nombres = st.text_input("👤 NOMBRES *", placeholder="Ej: María José", key="reg_nombres")
            apellidos = st.text_input("👤 APELLIDOS *", placeholder="Ej: Pérez González", key="reg_apellidos")
            cc_tipo, cc_num = st.columns([1, 2])
            with cc_tipo:
                cedula_tipo = st.selectbox("🪪 TIPO", ["V", "E", "P"], key="reg_cedula_tipo",
                                           help="V: venezolano  •  E: extranjero  •  P: pasaporte")
            with cc_num:
                cedula_num = st.text_input("🪪 CÉDULA DE IDENTIDAD *", placeholder="Solo números. Ej: 12345678",
                                           key="reg_cedula_num")

        with col_d:
            correo_titular = st.text_input("📧 CORREO ELECTRÓNICO DEL TITULAR", placeholder="correo@ejemplo.com (opcional)", key="reg_correo")
            sexo_sel = st.selectbox("⚧ SEXO / GÉNERO *", ["— Seleccione —", "FEMENINO", "MASCULINO"],
                                    key="reg_sexo",
                                    help="Se usa para redactar el título (LICENCIADA/LICENCIADO, DOCTORA/DOCTOR, etc.)")
            tipo_estudiante_sel = st.selectbox(
                "🎓 TIPO DE INGRESO *",
                ["— Seleccione —", "BACHILLER (desde el 1er semestre)", "TSU / PNF (se le reconocen T1 y T2)"],
                key="reg_tipo_est",
                help="BACHILLER: inicia en el primer semestre. TSU/PNF: se le reconocen los dos primeros trayectos (T1 y T2) e inicia en el 5.º semestre.")
            periodo_inicio = st.text_input("🗓️ PERÍODO DE INICIO", placeholder="Ej: 2020-I (el sistema continúa la secuencia)",
                                           key="reg_periodo_inicio",
                                           help="Escriba solo el primer período. El sistema genera automáticamente los siguientes (…-II, luego año+1-I).")
            # Régimen sugerido según el programa (punto 10): semestral o trimestral
            _reg_ppa, _reg_lbl = _regimen_programa_info(programa_real) if programa_real else (2, "Semestral (2 períodos por año: I y II)")
            _reg_idx = {2: 0, 3: 1, 4: 2}.get(_reg_ppa, 0)
            if programa_real:
                st.caption(f"Régimen sugerido para este programa: **{_reg_lbl}**")
            periodos_por_anio_sel = st.selectbox("🔁 PERÍODOS POR AÑO", [2, 3, 4], index=_reg_idx,
                                                 help="2 = semestral, 3 = trimestral por trayecto, 4 = trimestral. Se ajusta solo según el programa, pero puede cambiarlo.")
            observaciones = st.text_area("💬 OBSERVACIONES", placeholder="Observaciones adicionales...", height=120, key="reg_obs")

        pdf_file = st.file_uploader("📄 EXPEDIENTE DIGITAL (PDF) - Máximo 5MB (opcional)",
                                    type=["pdf"],
                                    help="Opcional. Si tiene el PDF del expediente, adjúntelo (máximo 5 Megabytes). Puede registrar sin él y cargarlo después.")

        submitted = st.form_submit_button("✅ REGISTRAR EXPEDIENTE", use_container_width=True, type="primary")

        if submitted:
            # Armar la cédula: prefijo (V/E/P) + solo dígitos.
            cedula_num_limpio = "".join(ch for ch in str(cedula_num) if ch.isdigit())
            cedula = f"{cedula_tipo}-{cedula_num_limpio}" if cedula_num_limpio else ""
            errores = []
            if not estado_real: errores.append("ESTADO")
            if not municipio_real: errores.append("MUNICIPIO")
            if not nombres.strip(): errores.append("NOMBRES")
            if not apellidos.strip(): errores.append("APELLIDOS")
            if not cedula_num_limpio: errores.append("CÉDULA (escriba solo números)")
            if not tipo_real: errores.append("TIPO DE PROGRAMA")
            if not programa_real: errores.append("PROGRAMA")
            if not tipo_exp_real: errores.append("TIPO DE EXPEDIENTE")
            if sexo_sel == "— Seleccione —": errores.append("SEXO / GÉNERO")
            # El PDF del expediente es OPCIONAL: se puede registrar sin adjuntarlo.

            if pdf_file and pdf_file.size > MAX_PDF_SIZE:
                st.error(f"❌ El archivo PDF pesa **{pdf_file.size / (1024*1024):.1f}MB**. El máximo permitido es **5MB**.")
                errores.append("PDF excede 5MB")

            if errores:
                st.error(f"⚠️ Campos obligatorios faltantes: **{', '.join(errores)}**")
            else:
                datos = {
                    "estado": estado_real,
                    "municipio": municipio_real,
                    "aula_taller": aula_taller_real,
                    "nombres": nombres.strip().upper(),
                    "apellidos": apellidos.strip().upper(),
                    "cedula": cedula.strip().upper(),
                    "correo_titular": correo_titular.strip().lower(),
                    "tipo_programa": tipo_real,
                    "programa": programa_real,
                    "tipo_expediente": tipo_exp_real,
                    "periodo_culminacion": "",
                    "sexo": ("" if sexo_sel == "— Seleccione —" else sexo_sel),
                    "tipo_estudiante": ("TSU" if tipo_estudiante_sel.startswith("TSU") else ("BACHILLER" if tipo_estudiante_sel.startswith("BACHILLER") else "")),
                    "periodo_inicio": periodo_inicio.strip().upper(),
                    "periodos_por_anio": int(periodos_por_anio_sel),
                    "observaciones": observaciones.strip(),
                    "registrado_por": st.session_state.usuario,
                }

                exito, mensaje = registrar_expediente(datos, pdf_file.read() if pdf_file else None)

                if exito:
                    st.markdown("""
                    <div class='success-box'>
                        <strong>✅ ¡REGISTRO EXITOSO!</strong><br>
                        El expediente ha sido registrado correctamente en el sistema.<br>
                        Se enviará notificación por correo al titular.
                    </div>
                    """, unsafe_allow_html=True)

                    if correo_titular.strip():
                        datos_correo = {k: v for k, v in datos.items()}
                        conn2 = sqlite3.connect(DB_FILE)
                        c2 = conn2.cursor()
                        c2.execute("SELECT pdf_path FROM expedientes WHERE cedula=? ORDER BY id DESC LIMIT 1", (datos['cedula'],))
                        row_pdf = c2.fetchone()
                        conn2.close()
                        pdf_path_real = row_pdf[0] if row_pdf and row_pdf[0] else None
                        correo_ok, correo_msg = enviar_correo_registro(
                            correo_titular.strip(), datos_correo, pdf_path_real
                        )
                        if correo_ok:
                            st.success(f"📧 {correo_msg}")
                        else:
                            st.warning(f"📧 Correo no enviado: {correo_msg}")

                    # Marcamos para limpiar los campos en el próximo dibujado
                    # (nunca reasignar aquí las claves de widgets ya creados)
                    st.session_state._limpiar_registro = True
                    time.sleep(1.2)
                    st.rerun()
                else:
                    st.error(f"❌ Error: {mensaje}")

# ============================================================
# PÁGINA: CONSULTAR EXPEDIENTES
# ============================================================

elif menu == "📊 Consultar Expedientes":
    mostrar_header("📊 Consultar Expedientes", "Filtre y consulte los registros del sistema")

    st.subheader("🔍 Filtros de Búsqueda")

    def on_filtro_estado_change():
        st.session_state.filtro_municipio = []

    def on_filtro_tipo_prog_change():
        st.session_state.filtro_programa = []

    if "filtro_estado" not in st.session_state:
        st.session_state.filtro_estado = []
    if "filtro_municipio" not in st.session_state:
        st.session_state.filtro_municipio = []
    if "filtro_tipo_prog" not in st.session_state:
        st.session_state.filtro_tipo_prog = []
    if "filtro_programa" not in st.session_state:
        st.session_state.filtro_programa = []

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtro_estado = st.multiselect("Estado", list(ESTADOS_MUNICIPIOS.keys()),
                                       key="filtro_estado",
                                       on_change=on_filtro_estado_change)
        municipios_disponibles = []
        for est in filtro_estado:
            municipios_disponibles.extend(ESTADOS_MUNICIPIOS.get(est, []))
        municipios_disponibles = sorted(set(municipios_disponibles))
        filtro_municipio = st.multiselect("Municipio", municipios_disponibles,
                                          key="filtro_municipio")

    with col_f2:
        filtro_tipo_exp = st.multiselect("Tipo Expediente", TIPOS_EXPEDIENTE, key="filtro_tipo_exp")
        filtro_tipo_prog = st.multiselect("Tipo Programa", list(TIPOS_PROGRAMA_PROGRAMAS.keys()),
                                           key="filtro_tipo_prog",
                                           on_change=on_filtro_tipo_prog_change)
        programas_disponibles = []
        for tp in filtro_tipo_prog:
            programas_disponibles.extend(obtener_lista_editable("programa", tp) or TIPOS_PROGRAMA_PROGRAMAS.get(tp, []))
        programas_disponibles = sorted(set(programas_disponibles))
        filtro_programa = st.multiselect("Programa", programas_disponibles,
                                         key="filtro_programa")

    filtros = {}
    if filtro_estado: filtros["estado"] = filtro_estado[0] if len(filtro_estado) == 1 else None
    if filtro_municipio: filtros["municipio"] = filtro_municipio[0] if len(filtro_municipio) == 1 else None
    if filtro_tipo_exp: filtros["tipo_expediente"] = filtro_tipo_exp[0] if len(filtro_tipo_exp) == 1 else None
    if filtro_tipo_prog: filtros["tipo_programa"] = filtro_tipo_prog[0] if len(filtro_tipo_prog) == 1 else None
    if filtro_programa: filtros["programa"] = filtro_programa[0] if len(filtro_programa) == 1 else None

    df = obtener_expedientes(filtros if any(filtros.values()) else None)

    if not df.empty:
        columnas_mostrar = {
            "id": "#", "estado": "ESTADO", "municipio": "MUNICIPIO",
            "aula_taller": "AULA TALLER", "nombres": "NOMBRES", "apellidos": "APELLIDOS",
            "cedula": "CÉDULA", "correo_titular": "CORREO",
            "tipo_programa": "TIPO PROGRAMA", "programa": "PROGRAMA",
            "tipo_expediente": "TIPO EXPEDIENTE",
            "observaciones": "OBSERVACIONES",
            "registrado_por": "REGISTRADO POR",
            "fecha_registro": "FECHA REGISTRO"
        }
        df_show = df.rename(columns=columnas_mostrar)
        cols_visibles = ["#", "ESTADO", "MUNICIPIO", "AULA TALLER", "NOMBRES", "APELLIDOS",
                         "CÉDULA", "CORREO", "TIPO PROGRAMA", "PROGRAMA",
                         "TIPO EXPEDIENTE", "OBSERVACIONES", "REGISTRADO POR", "FECHA REGISTRO"]
        cols_disponibles = [c for c in cols_visibles if c in df_show.columns]
        st.dataframe(df_show[cols_disponibles], use_container_width=True, hide_index=True)
        st.caption(f"Mostrando **{len(df)}** registros")
    else:
        st.info("📋 No se encontraron expedientes con los filtros seleccionados.")

# ============================================================
# PÁGINA: BUSCAR EXPEDIENTE
# ============================================================

elif menu == "🔍 Buscar Expediente":
    mostrar_header("🔍 Buscar Expediente", "Búsqueda rápida por cédula de identidad")

    buscar = st.text_input("🪪 Ingrese la Cédula de Identidad", placeholder="Ej: V-12345678")

    if buscar:
        df = obtener_expedientes({"cedula": buscar.strip().upper()})
        if estado_regional and not df.empty:
            # Nivel 3: solo puede consultar expedientes de su estado asignado.
            df = df[df["estado"].fillna("").str.upper() == estado_regional.upper()]
        if not df.empty:
            st.success("✅ Expediente encontrado")
            for _, row in df.iterrows():
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"🏛️ **Estado:** {row['estado']}")
                    st.info(f"🏙️ **Municipio:** {row['municipio']}")
                    st.info(f"🏫 **Aula Taller:** {row['aula_taller']}")
                    st.info(f"👤 **Nombres:** {row['nombres']}")
                    st.info(f"👤 **Apellidos:** {row.get('apellidos', '')}")
                    st.info(f"🪪 **Cédula:** {row['cedula']}")
                    st.info(f"📧 **Correo:** {row['correo_titular']}")
                with col2:
                    st.info(f"📚 **Tipo Programa:** {row['tipo_programa']}")
                    st.info(f"🎓 **Programa:** {row['programa']}")
                    st.info(f"📂 **Tipo Expediente:** {row['tipo_expediente']}")
                    st.info(f"💬 **Observaciones:** {row['observaciones']}")
                    st.info(f"👤 **Registrado por:** {row['registrado_por']}")
                    st.info(f"📅 **Fecha:** {row['fecha_registro']}")

                col_desc1, col_desc2 = st.columns(2)
                with col_desc1:
                    if row['pdf_path'] and os.path.exists(row['pdf_path']):
                        with open(row['pdf_path'], "rb") as f:
                            st.download_button(
                                label="📄 Descargar PDF del Expediente",
                                data=f.read(),
                                file_name=f"Expediente_{row['cedula']}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                key=f"pdf_{row['id']}"
                            )
                with col_desc2:
                    # Etiqueta para pegar en la carpeta (todos los datos menos el PDF)
                    try:
                        etiqueta_bytes = generar_etiqueta_pdf(row)
                        st.download_button(
                            label="🏷️ Generar Etiqueta para la Carpeta",
                            data=etiqueta_bytes,
                            file_name=f"Etiqueta_{row['cedula']}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary",
                            key=f"etq_{row['id']}"
                        )
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo generar la etiqueta: {e}")

                # Solicitar modificación (solo REGIONAL)
                if rol == "ADMIN_REGIONAL":
                    st.markdown("---")
                    st.subheader("📝 Solicitar Modificación")
                    campo_mod = st.selectbox("Campo a modificar", [
                        "Estado", "Municipio", "Aula Taller", "Nombres", "Apellidos",
                        "Cédula", "Correo del Titular", "Tipo de Programa", "Programa",
                        "Tipo de Expediente", "Observaciones"
                    ], key=f"campo_{row['id']}")
                    valor_nuevo = st.text_input("Nuevo valor", key=f"nuevo_{row['id']}")
                    motivo = st.text_area("Motivo de la modificación", key=f"motivo_{row['id']}")
                    if st.button("📤 Enviar Solicitud de Modificación", key=f"sol_{row['id']}"):
                        if valor_nuevo.strip() and motivo.strip():
                            campos_db_map = {
                                "Estado": "estado", "Municipio": "municipio", "Aula Taller": "aula_taller",
                                "Nombres": "nombres", "Apellidos": "apellidos", "Cédula": "cedula",
                                "Correo del Titular": "correo_titular",
                                "Tipo de Programa": "tipo_programa", "Programa": "programa",
                                "Tipo de Expediente": "tipo_expediente", "Observaciones": "observaciones"
                            }
                            col_name = campos_db_map.get(campo_mod, '')
                            valor_actual = str(row.get(col_name, '')) if col_name else ''
                            crear_solicitud_modificacion(
                                row['id'], st.session_state.usuario,
                                campo_mod, valor_actual,
                                valor_nuevo.strip(), motivo.strip()
                            )
                            st.success("✅ Solicitud enviada. Será revisada por un administrador.")
                        else:
                            st.warning("⚠️ Complete el nuevo valor y el motivo.")

                    # Solicitar ELIMINACIÓN del expediente (solo REGIONAL)
                    st.markdown("---")
                    st.subheader("🗑️ Solicitar Eliminación del Expediente")
                    st.warning("⚠️ La eliminación será revisada y ejecutada por un Administrador (Nivel 1 o 2).")
                    motivo_elim = st.text_area("Motivo de la eliminación", key=f"motivo_elim_{row['id']}")
                    if st.button("🗑️ Enviar Solicitud de Eliminación", key=f"sol_elim_{row['id']}"):
                        if motivo_elim.strip():
                            resumen = f"{row['cedula']} — {row['nombres']} {row.get('apellidos', '')}".strip()
                            crear_solicitud_eliminacion(
                                row['id'], st.session_state.usuario,
                                resumen, motivo_elim.strip()
                            )
                            st.success("✅ Solicitud de eliminación enviada. Será revisada por un administrador.")
                        else:
                            st.warning("⚠️ Indique el motivo de la eliminación.")

                # Edición y eliminación DIRECTA (solo Nivel 1 y Nivel 2)
                if rol in ("ADMIN_PRINCIPAL", "ADMIN_AUXILIAR"):
                    st.markdown("---")
                    with st.expander("✏️ Editar este expediente (cambio directo)"):
                        with st.form(f"form_edit_{row['id']}"):
                            e_nombres = st.text_input("Nombres", value=row.get("nombres", "") or "", key=f"e_nom_{row['id']}")
                            e_apellidos = st.text_input("Apellidos", value=row.get("apellidos", "") or "", key=f"e_ape_{row['id']}")
                            e_cedula = st.text_input("Cédula", value=row.get("cedula", "") or "", key=f"e_ced_{row['id']}")
                            e_correo = st.text_input("Correo del titular", value=row.get("correo_titular", "") or "", key=f"e_cor_{row['id']}")
                            e_aula = st.text_input("Aula taller", value=row.get("aula_taller", "") or "", key=f"e_aula_{row['id']}")
                            e_obs = st.text_area("Observaciones", value=row.get("observaciones", "") or "", key=f"e_obs_{row['id']}")
                            if st.form_submit_button("💾 Guardar cambios", type="primary", use_container_width=True):
                                actualizar_expediente(int(row['id']), {
                                    "nombres": e_nombres.strip().upper(),
                                    "apellidos": e_apellidos.strip().upper(),
                                    "cedula": e_cedula.strip().upper(),
                                    "correo_titular": e_correo.strip().lower(),
                                    "aula_taller": e_aula.strip(),
                                    "observaciones": e_obs.strip(),
                                })
                                st.success("✅ Expediente actualizado.")
                                st.rerun()

                    st.subheader("🗑️ Eliminar este expediente (directo)")
                    st.warning("⚠️ Esta acción borra el expediente y su PDF de forma permanente y NO se puede deshacer.")
                    confirmar_del = st.checkbox("Sí, confirmo que deseo eliminar este expediente.", key=f"conf_del_{row['id']}")
                    if st.button("🗑️ Eliminar Expediente", key=f"del_exp_{row['id']}", type="primary", use_container_width=True):
                        if confirmar_del:
                            eliminar_expediente(int(row['id']))
                            st.success("✅ Expediente eliminado.")
                            st.rerun()
                        else:
                            st.warning("⚠️ Marque primero la casilla de confirmación.")
        else:
            st.warning(f"⚠️ No se encontró expediente con cédula **{buscar}**")

# ============================================================
# PÁGINA: GENERAR DOCUMENTOS (Certificación en PDF)
# ============================================================

elif menu == "📄 Generar Documentos":
    mostrar_header("📄 Generar Documentos", "Certificación de Calificaciones en PDF con escudo, firma, código QR y código de barras")

    # Solo Nivel 1 (Principal) y Nivel 2 (Auxiliar) pueden imprimir/generar documentos.
    # El Nivel 3 (Regional) NO está autorizado.
    if rol not in ("ADMIN_PRINCIPAL", "ADMIN_AUXILIAR"):
        st.error("🚫 Su nivel de usuario no está autorizado para imprimir o generar documentos. "
                 "Esta función es exclusiva del Nivel 1 y Nivel 2.")
        st.stop()

    st.info("Busque por alumno, aula taller, municipio, estado o programa. "
            "Puede generar la certificación de **un alumno**, o generar **por Estado y Programa** "
            "(un solo PDF por cada programa, con todos sus alumnos), para descargarlos uno por uno.")

    st.subheader("🔍 Filtros de búsqueda")
    colg1, colg2 = st.columns(2)
    with colg1:
        gf_texto = st.text_input("👤 Alumno (nombre, apellido o cédula)", key="gen_texto")
        gf_estado = st.multiselect("🏛️ Estado", list(ESTADOS_MUNICIPIOS.keys()), key="gen_estado")
        gf_muni_disp = []
        for est in gf_estado:
            gf_muni_disp.extend(ESTADOS_MUNICIPIOS.get(est, []))
        gf_muni_disp = sorted(set(gf_muni_disp))
        gf_municipio = st.multiselect("🏙️ Municipio", gf_muni_disp, key="gen_municipio")
    with colg2:
        gf_aula = st.text_input("🏫 Aula taller (contiene)", key="gen_aula")
        gf_tipo_prog = st.multiselect("📚 Tipo de programa", list(TIPOS_PROGRAMA_PROGRAMAS.keys()), key="gen_tipo_prog")
        gf_prog_disp = []
        for tp in gf_tipo_prog:
            gf_prog_disp.extend(obtener_lista_editable("programa", tp) or TIPOS_PROGRAMA_PROGRAMAS.get(tp, []))
        gf_prog_disp = sorted(set(gf_prog_disp))
        gf_programa = st.multiselect("🎓 Programa", gf_prog_disp, key="gen_programa")
        gf_tipo_exp = st.multiselect("📂 Tipo de expediente", TIPOS_EXPEDIENTE, key="gen_tipo_exp")

    df_gen = obtener_expedientes(None)

    if not df_gen.empty:
        if gf_texto.strip():
            t = gf_texto.strip().upper()
            df_gen = df_gen[
                df_gen["nombres"].fillna("").str.upper().str.contains(t) |
                df_gen["apellidos"].fillna("").str.upper().str.contains(t) |
                df_gen["cedula"].fillna("").str.upper().str.contains(t)
            ]
        if gf_estado:
            df_gen = df_gen[df_gen["estado"].isin(gf_estado)]
        if gf_municipio:
            df_gen = df_gen[df_gen["municipio"].isin(gf_municipio)]
        if gf_aula.strip():
            df_gen = df_gen[df_gen["aula_taller"].fillna("").str.upper().str.contains(gf_aula.strip().upper())]
        if gf_tipo_prog:
            df_gen = df_gen[df_gen["tipo_programa"].isin(gf_tipo_prog)]
        if gf_programa:
            df_gen = df_gen[df_gen["programa"].isin(gf_programa)]
        if gf_tipo_exp:
            df_gen = df_gen[df_gen["tipo_expediente"].isin(gf_tipo_exp)]

    st.markdown("---")
    if df_gen.empty:
        st.warning("⚠️ No hay expedientes que coincidan con los filtros.")
    else:
        st.success(f"✅ {len(df_gen)} expediente(s) encontrados.")
        cols_prev = [c for c in ["cedula", "nombres", "apellidos", "estado", "municipio",
                                  "aula_taller", "tipo_programa", "programa",
                                  "periodo_culminacion", "tipo_expediente"] if c in df_gen.columns]
        st.dataframe(df_gen[cols_prev], use_container_width=True, hide_index=True)

        st.markdown("#### 📄 Generar la certificación de UN alumno")
        opciones = {
            f"{r['cedula']} — {r['nombres']} {r.get('apellidos','')}".strip(): idx
            for idx, r in df_gen.iterrows()
        }
        sel = st.selectbox("Seleccione el alumno", list(opciones.keys()), key="gen_sel_alumno")
        if sel:
            row_sel = df_gen.loc[opciones[sel]]
            try:
                cert_bytes = generar_certificado_pdf(row_sel)
                st.download_button(
                    label="📄 Descargar Certificación (PDF)",
                    data=cert_bytes,
                    file_name=f"Certificacion_{row_sel['cedula']}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="gen_dl_uno",
                )
            except Exception as e:
                st.error(f"❌ No se pudo generar la certificación: {e}")

        st.markdown("#### 📚 Generar por ESTADO y PROGRAMA (un PDF por programa)")
        st.caption("El sistema agrupa a los alumnos filtrados por **Estado** y **Programa**. "
                   "Por cada programa arma **un solo PDF** con las certificaciones de todos sus "
                   "alumnos, una detrás de otra. Luego aparece un botón de descarga por cada programa.")
        if st.button("📚 Generar los PDF por programa", use_container_width=True, key="gen_por_programa_btn", type="primary"):
            try:
                from pypdf import PdfWriter, PdfReader
                grupos = {}
                # Agrupar por (estado, programa) conservando el orden
                for _, r in df_gen.iterrows():
                    clave = (str(r.get("estado", "") or ""), str(r.get("programa", "") or ""))
                    grupos.setdefault(clave, []).append(r)
                resultados = []
                for (est_g, prog_g), filas in grupos.items():
                    escritor = PdfWriter()
                    n_ok = 0
                    for r in filas:
                        try:
                            pdf_bytes = generar_certificado_pdf(r)
                            lector = PdfReader(BytesIO(pdf_bytes))
                            for pag in lector.pages:
                                escritor.add_page(pag)
                            n_ok += 1
                        except Exception:
                            pass
                    out = BytesIO()
                    escritor.write(out)
                    out.seek(0)
                    resultados.append((est_g, prog_g, n_ok, out.getvalue()))
                st.session_state["gen_pdfs_programa"] = resultados
                st.success(f"✅ Se prepararon {len(resultados)} PDF (uno por programa). "
                           "Descárguelos abajo, uno por uno.")
            except Exception as e:
                st.error(f"❌ No se pudieron generar los PDF por programa: {e}")

        # Mostrar los botones de descarga UNO POR UNO (no ZIP)
        _resultados = st.session_state.get("gen_pdfs_programa", [])
        if _resultados:
            st.markdown("##### ⬇️ Descargas (una por programa)")
            for _i, (est_g, prog_g, n_ok, data) in enumerate(_resultados):
                _est_lbl = est_g or "(sin estado)"
                _prog_lbl = prog_g or "(sin programa)"
                st.markdown(f"**{_est_lbl} — {_prog_lbl}** · {n_ok} alumno(s)")
                _nombre = f"Certificaciones_{_est_lbl}_{_prog_lbl}.pdf".replace("/", "-").replace(" ", "_")
                st.download_button(
                    label=f"⬇️ Descargar PDF — {_prog_lbl}",
                    data=data,
                    file_name=_nombre,
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"gen_dl_prog_{_i}",
                )

# ============================================================
# PÁGINA: MALLAS CURRICULARES
# ============================================================

elif menu == "🧮 Mallas Curriculares":
    mostrar_header("🧮 Mallas Curriculares", "Cargue las materias (asignaturas) de cada programa, con sus Unidades de Crédito")

    if rol not in ("ADMIN_PRINCIPAL", "ADMIN_AUXILIAR"):
        st.error("🚫 Su nivel de usuario no está autorizado para esta sección.")
        st.stop()

    st.info("Elija un programa y cargue sus materias en orden (Trayecto/Semestre/Trimestre). "
            "Las Unidades de Crédito (U.C.) que escriba aquí saldrán automáticamente al costado "
            "de cada materia en el PDF.")

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        tp_malla = st.selectbox("📚 Tipo de programa", list(TIPOS_PROGRAMA_PROGRAMAS.keys()), key="malla_tipo")
    with col_m2:
        progs_m = obtener_lista_editable("programa", tp_malla) or TIPOS_PROGRAMA_PROGRAMAS.get(tp_malla, [])
        prog_malla = st.selectbox("🎓 Programa", progs_m, key="malla_prog")

    st.markdown("---")
    st.subheader(f"📖 Materias de: {prog_malla}")

    malla_actual = obtener_malla(prog_malla, incluir_introductorio=True)
    if malla_actual:
        df_malla = pd.DataFrame([{
            "Período (Trayecto/Semestre)": m["periodo"],
            "Materia": m["materia"],
            "U.C. (créditos)": m["creditos"],
        } for m in malla_actual])
    else:
        df_malla = pd.DataFrame([{
            "Período (Trayecto/Semestre)": "", "Materia": "", "U.C. (créditos)": 0.0
        }])

    st.caption("Edite la tabla directamente. Use el botón ➕ (abajo de la tabla) para agregar filas. "
               "Deje una fila con la materia vacía para eliminarla al guardar.")
    df_editada = st.data_editor(
        df_malla,
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_malla_{prog_malla}",
        column_config={
            "U.C. (créditos)": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%g"),
        },
    )

    if st.button("💾 Guardar malla de este programa", type="primary", use_container_width=True, key="btn_guardar_malla"):
        filas = []
        for _, r in df_editada.iterrows():
            materia = str(r.get("Materia", "") or "").strip().upper()
            if not materia:
                continue
            filas.append({
                "periodo": str(r.get("Período (Trayecto/Semestre)", "") or "").strip().upper(),
                "materia": materia,
                "creditos": r.get("U.C. (créditos)", 0) or 0,
                "es_introductorio": 0,
            })
        if filas:
            reemplazar_malla(prog_malla, filas)
            st.success(f"✅ Malla guardada: {len(filas)} materia(s) para {prog_malla}.")
            st.rerun()
        else:
            st.warning("⚠️ No hay materias válidas para guardar. Escriba al menos una materia.")

    with st.expander("📋 Carga rápida: pegar varias materias de una vez"):
        st.caption("Pegue una materia por línea con este formato (separado por el signo |):  "
                   "**Período | Materia | U.C.**  —  Ejemplo:  TRAYECTO 1 - SEMESTRE 1 | MATEMÁTICA I | 4")
        pegado = st.text_area("Pegue aquí la lista de materias", height=180, key="malla_pegar")
        modo_reemplazar = st.checkbox("Reemplazar toda la malla actual (si no, se agregan a las existentes)", value=True, key="malla_pegar_modo")
        if st.button("📥 Cargar lista pegada", key="btn_pegar_malla"):
            nuevas = []
            for ln in pegado.splitlines():
                if not ln.strip():
                    continue
                partes = [p.strip() for p in ln.split("|")]
                periodo_v = partes[0].upper() if len(partes) >= 1 else ""
                materia_v = partes[1].upper() if len(partes) >= 2 else ""
                try:
                    cred_v = float(partes[2]) if len(partes) >= 3 and partes[2] else 0
                except ValueError:
                    cred_v = 0
                intro_v = 0
                if materia_v:
                    nuevas.append({"periodo": periodo_v, "materia": materia_v,
                                   "creditos": cred_v, "es_introductorio": intro_v})
            if not nuevas:
                st.warning("⚠️ No se detectaron materias válidas en el texto pegado.")
            else:
                if modo_reemplazar:
                    reemplazar_malla(prog_malla, nuevas)
                else:
                    for f in nuevas:
                        guardar_materia_malla(prog_malla, f["periodo"], f["materia"],
                                              f["creditos"], f["es_introductorio"])
                st.success(f"✅ Se cargaron {len(nuevas)} materia(s) en {prog_malla}.")
                st.rerun()

# ============================================================
# PÁGINA: REGISTRO DE CALIFICACIONES
# ============================================================

elif menu == "📝 Registro de Calificaciones":
    mostrar_header("📝 Registro de Calificaciones", "Cargue las calificaciones del estudiante según la malla de su programa")

    # Los tres niveles pueden CARGAR notas. La diferencia está en MODIFICAR:
    #  - Nivel 1 y 2 (Principal / Auxiliar): cargan y modifican libremente.
    #  - Nivel 3 (Regional): carga notas nuevas, pero NO puede cambiar una nota
    #    ya guardada; para eso debe enviar una SOLICITUD DE MODIFICACIÓN con
    #    su motivo, que el Nivel 1 o 2 autoriza y aplica.
    if rol not in ("ADMIN_PRINCIPAL", "ADMIN_AUXILIAR", "ADMIN_REGIONAL"):
        st.error("🚫 Su nivel de usuario no está autorizado para esta sección.")
        st.stop()

    es_regional = (rol == "ADMIN_REGIONAL")

    st.info("Busque el estudiante. Al elegirlo, el sistema muestra **solo** las materias de su "
            "programa, en orden. El **Período** se calcula solo (según el período de inicio del "
            "estudiante); usted solo escribe la **calificación** de cada materia y guarda.")
    if es_regional:
        st.warning("ℹ️ Como Administrador Regional usted puede **cargar** notas nuevas. "
                   "Una nota que ya esté guardada **no** se puede cambiar aquí: use la pestaña "
                   "**Solicitar cambio de una nota** para pedir la corrección con su motivo.")

    df_est = obtener_expedientes(None)
    if estado_regional and not df_est.empty:
        # Nivel 3: solo estudiantes de su estado asignado.
        df_est = df_est[df_est["estado"].fillna("").str.upper() == estado_regional.upper()]
    buscar_est = st.text_input("🔍 Buscar por nombre, apellido o cédula", key="notas_buscar")
    if not df_est.empty and buscar_est.strip():
        t = buscar_est.strip().upper()
        df_est = df_est[
            df_est["nombres"].fillna("").str.upper().str.contains(t) |
            df_est["apellidos"].fillna("").str.upper().str.contains(t) |
            df_est["cedula"].fillna("").str.upper().str.contains(t)
        ]

    if df_est.empty:
        st.warning("⚠️ No hay estudiantes que coincidan.")
    else:
        opciones_e = {
            f"{r['cedula']} — {r['nombres']} {r.get('apellidos','')}".strip(): idx
            for idx, r in df_est.iterrows()
        }
        sel_e = st.selectbox("Seleccione el estudiante", list(opciones_e.keys()), key="notas_sel")
        if sel_e:
            row_e = df_est.loc[opciones_e[sel_e]]
            ced_e = str(row_e["cedula"])
            prog_e = str(row_e["programa"])
            exp_id_e = int(row_e["id"])
            # Régimen del programa (semestral / trimestral) según sus períodos por año
            _reg_txt = _regimen_programa(prog_e)
            st.markdown(f"**Programa:** {prog_e}")
            st.caption(f"Régimen del programa: **{_reg_txt}**")
            malla_e = obtener_malla(prog_e, incluir_introductorio=True)
            if not malla_e:
                st.warning("⚠️ Este programa aún no tiene malla cargada. Cárguela primero en '🧮 Mallas Curriculares'.")
            else:
                notas_e = obtener_notas(ced_e)
                periodos_e = obtener_periodos_notas(ced_e)

                # ----- Período AUTOMÁTICO por materia (no editable).
                # Se calcula con el período de inicio del estudiante y sus
                # períodos por año (2 semestral, 3 trimestral, etc.). Así la
                # columna "Período" muestra el período REAL (ej. 2020-I) y NO la
                # etiqueta "SEMESTRE 1".
                _pi = str(row_e.get("periodo_inicio", "") or "").strip()
                try:
                    _ppa = int(float(str(row_e.get("periodos_por_anio", 2) or 2)))
                except (ValueError, TypeError):
                    _ppa = 2
                if _ppa < 1:
                    _ppa = 2
                _pos = []
                for _m in malla_e:
                    _po = int(_m.get("periodo_orden") or 0)
                    if _po not in _pos:
                        _pos.append(_po)
                _pos_sorted = sorted(p for p in _pos if p > 0)
                _codigos = _secuencia_periodos(_pi, _ppa, len(_pos_sorted)) if _pi else []
                _po_code = {}
                for _i, _po in enumerate(_pos_sorted):
                    _po_code[_po] = _codigos[_i] if _i < len(_codigos) else ""

                def _periodo_auto(m):
                    return _po_code.get(int(m.get("periodo_orden") or 0), "")

                if not _pi:
                    st.warning("⚠️ Este estudiante no tiene registrado el **período de inicio**. "
                               "Edite el expediente y agréguelo para que el período se calcule solo.")

                # -------- Carga manual (editor) --------
                st.markdown("#### ✏️ Carga manual")
                df_notas = pd.DataFrame([{
                    "Materia": m["materia"],
                    "U.C.": m["creditos"],
                    "Semestre": m["periodo"],
                    "Período": _periodo_auto(m),
                    "Calificación": notas_e.get(m["materia"], ""),
                } for m in malla_e])
                st.caption("El **Semestre** y el **Período** se muestran solos. Escriba solo la **Calificación** de cada materia.")
                df_notas_ed = st.data_editor(
                    df_notas,
                    use_container_width=True,
                    hide_index=True,
                    key=f"editor_notas_{ced_e}",
                    disabled=["Materia", "U.C.", "Semestre", "Período"],
                )
                if st.button("💾 Guardar calificaciones", type="primary", use_container_width=True, key="btn_guardar_notas"):
                    notas_dict = {}
                    bloqueadas = []
                    for i, m in enumerate(malla_e):
                        cal = str(df_notas_ed.iloc[i]["Calificación"] or "").strip().upper()
                        # Guardar SIEMPRE el período REAL calculado (nunca la etiqueta "SEMESTRE 1").
                        per = _periodo_auto(m)
                        anterior = str(notas_e.get(m["materia"], "") or "").strip().upper()
                        # Nivel 3: no puede cambiar una nota YA guardada (solo agregar nuevas)
                        if es_regional and anterior != "" and cal != anterior:
                            bloqueadas.append(m["materia"])
                            notas_dict[m["materia"]] = (m["creditos"], anterior, per)
                        else:
                            notas_dict[m["materia"]] = (m["creditos"], cal, per)
                    guardar_notas(ced_e, prog_e, notas_dict)
                    if bloqueadas:
                        st.warning("⚠️ Se guardaron las notas nuevas. Estas materias YA tenían nota y "
                                   "no se modificaron (use 'Solicitar cambio de una nota'): "
                                   + ", ".join(bloqueadas))
                    st.success("✅ Calificaciones guardadas. Ya puede generar la certificación en '📄 Generar Documentos'.")

                # -------- Carga desde archivo Excel (formato SIGUM) --------
                st.markdown("---")
                st.markdown("#### 📂 Cargar desde archivo Excel (SIGUM)")
                st.caption("El archivo debe tener columnas: **PERÍODO**, **U.C.**, **UNIDAD CURRICULAR**, "
                           "**CALIFICACIÓN (NÚMEROS)** y, opcionalmente, CALIFICACIÓN (LETRAS). "
                           "El sistema empareja cada materia del archivo con la materia de la malla por su nombre.")
                xls_notas = st.file_uploader("Archivo de notas (.xlsx)", type=["xlsx"], key=f"xls_notas_{ced_e}")
                if xls_notas is not None:
                    try:
                        df_sig = pd.read_excel(xls_notas)
                        df_sig.columns = [str(x).strip().upper() for x in df_sig.columns]
                        col_per = next((c for c in df_sig.columns if "PER" in c), None)
                        col_mat = next((c for c in df_sig.columns if "CURRICULAR" in c or "MATERIA" in c or "UNIDAD" in c), None)
                        col_cal = next((c for c in df_sig.columns if "NUMER" in c or "NÚMER" in c or c == "CALIFICACION" or c == "CALIFICACIÓN" or "CALIF" in c), None)
                        if not col_mat or not col_cal:
                            st.error("❌ No encuentro las columnas de materia y calificación en el archivo. "
                                     "Revise los títulos de las columnas.")
                        else:
                            # Mapa de materias de la malla (mayúsculas, sin espacios extra) -> materia real
                            malla_map = {re.sub(r"\s+", " ", m["materia"].strip().upper()): m for m in malla_e}
                            notas_dict = {}
                            no_encontradas = []
                            bloqueadas = []
                            for _, fila in df_sig.iterrows():
                                mat_txt = re.sub(r"\s+", " ", str(fila.get(col_mat, "")).strip().upper())
                                if not mat_txt or mat_txt == "NAN":
                                    continue
                                cal_txt = str(fila.get(col_cal, "")).strip().upper()
                                if cal_txt.endswith(".0"):
                                    cal_txt = cal_txt[:-2]
                                per_txt = str(fila.get(col_per, "")).strip().upper() if col_per else ""
                                if per_txt == "NAN":
                                    per_txt = ""
                                m = malla_map.get(mat_txt)
                                if not m:
                                    no_encontradas.append(mat_txt)
                                    continue
                                anterior = str(notas_e.get(m["materia"], "") or "").strip().upper()
                                if es_regional and anterior != "" and cal_txt != anterior:
                                    bloqueadas.append(m["materia"])
                                    continue
                                notas_dict[m["materia"]] = (m["creditos"], cal_txt, per_txt)
                            st.dataframe(pd.DataFrame([
                                {"Materia": k, "Calificación": v[1], "Período": v[2]}
                                for k, v in notas_dict.items()
                            ]), use_container_width=True, hide_index=True)
                            if no_encontradas:
                                st.warning("⚠️ Estas materias del archivo NO coinciden con la malla y se omiten: "
                                           + ", ".join(no_encontradas[:20]) + (" …" if len(no_encontradas) > 20 else ""))
                            if bloqueadas:
                                st.warning("⚠️ Estas materias YA tenían nota y (por ser Nivel 3) no se cambian: "
                                           + ", ".join(bloqueadas))
                            if notas_dict and st.button("💾 Guardar notas del archivo", type="primary",
                                                        use_container_width=True, key=f"btn_xls_{ced_e}"):
                                guardar_notas(ced_e, prog_e, notas_dict)
                                st.success(f"✅ Se guardaron {len(notas_dict)} calificaciones del archivo.")
                    except Exception as e:
                        st.error(f"❌ No pude leer el archivo. Verifique que sea un Excel válido. Detalle: {e}")

                # -------- Nivel 3: solicitar cambio de una nota ya guardada --------
                if es_regional and notas_e:
                    st.markdown("---")
                    st.markdown("#### 📝 Solicitar cambio de una nota")
                    st.caption("Elija la materia, escriba la nota correcta y el motivo. La solicitud queda "
                               "pendiente hasta que un Administrador Principal o Auxiliar la autorice.")
                    with st.form(f"form_sol_nota_{ced_e}"):
                        materias_con_nota = [m["materia"] for m in malla_e if notas_e.get(m["materia"], "")]
                        mat_sol = st.selectbox("Materia", materias_con_nota)
                        nota_actual = notas_e.get(mat_sol, "") if mat_sol else ""
                        st.text_input("Nota actual", value=str(nota_actual), disabled=True)
                        nota_nueva = st.text_input("Nota correcta")
                        motivo_sol = st.text_area("Motivo del cambio")
                        if st.form_submit_button("📨 Enviar solicitud", type="primary", use_container_width=True):
                            if nota_nueva.strip() and motivo_sol.strip():
                                crear_solicitud_modificacion(
                                    exp_id_e, st.session_state.usuario,
                                    f"NOTA · {mat_sol}", str(nota_actual),
                                    nota_nueva.strip().upper(), motivo_sol.strip())
                                st.success("✅ Solicitud enviada. Quedará pendiente de autorización.")
                            else:
                                st.warning("⚠️ Escriba la nota correcta y el motivo.")

# ============================================================
# PÁGINA: VER CALIFICACIONES (solo lectura)
# ============================================================

elif menu == "📊 Ver Calificaciones":
    mostrar_header("📊 Ver Calificaciones", "Consulte las calificaciones ya registradas de un estudiante")

    # Los tres niveles pueden VER. El Nivel 3 (Regional) solo ve estudiantes de
    # su estado asignado.
    if rol not in ("ADMIN_PRINCIPAL", "ADMIN_AUXILIAR", "ADMIN_REGIONAL"):
        st.error("🚫 Su nivel de usuario no está autorizado para esta sección.")
        st.stop()

    st.info("Busque el estudiante para ver sus calificaciones registradas. Esta sección es "
            "**solo de consulta**: no se puede modificar nada aquí.")

    df_estv = obtener_expedientes(None)
    if estado_regional and not df_estv.empty:
        df_estv = df_estv[df_estv["estado"].fillna("").str.upper() == estado_regional.upper()]
    buscar_estv = st.text_input("🔍 Buscar por nombre, apellido o cédula", key="vernotas_buscar")
    if not df_estv.empty and buscar_estv.strip():
        tv = buscar_estv.strip().upper()
        df_estv = df_estv[
            df_estv["nombres"].fillna("").str.upper().str.contains(tv) |
            df_estv["apellidos"].fillna("").str.upper().str.contains(tv) |
            df_estv["cedula"].fillna("").str.upper().str.contains(tv)
        ]

    if df_estv.empty:
        st.warning("⚠️ No hay estudiantes que coincidan.")
    else:
        opciones_ev = {
            f"{r['cedula']} — {r['nombres']} {r.get('apellidos','')}".strip(): idx
            for idx, r in df_estv.iterrows()
        }
        sel_ev = st.selectbox("Seleccione el estudiante", list(opciones_ev.keys()), key="vernotas_sel")
        if sel_ev:
            row_ev = df_estv.loc[opciones_ev[sel_ev]]
            ced_ev = str(row_ev["cedula"])
            prog_ev = str(row_ev["programa"])
            st.markdown(f"**Estudiante:** {row_ev['nombres']} {row_ev.get('apellidos','')}")
            st.markdown(f"**Cédula:** {ced_ev}  •  **Estado:** {row_ev.get('estado','')}")
            st.markdown(f"**Programa:** {prog_ev}")

            malla_ev = obtener_malla(prog_ev, incluir_introductorio=True)
            notas_ev = obtener_notas(ced_ev)
            periodos_ev = obtener_periodos_notas(ced_ev)

            # Período real por materia (mismo cálculo que en Registro)
            _piv = str(row_ev.get("periodo_inicio", "") or "").strip()
            try:
                _ppav = int(float(str(row_ev.get("periodos_por_anio", 2) or 2)))
            except (ValueError, TypeError):
                _ppav = 2
            if _ppav < 1:
                _ppav = 2
            _posv = []
            for _m in malla_ev:
                _pv = int(_m.get("periodo_orden") or 0)
                if _pv not in _posv:
                    _posv.append(_pv)
            _posv_sorted = sorted(p for p in _posv if p > 0)
            _codv = _secuencia_periodos(_piv, _ppav, len(_posv_sorted)) if _piv else []
            _pocv = {}
            for _iv, _pv in enumerate(_posv_sorted):
                _pocv[_pv] = _codv[_iv] if _iv < len(_codv) else ""

            if not malla_ev:
                st.warning("⚠️ Este programa aún no tiene malla cargada.")
            elif not notas_ev:
                st.info("📭 Este estudiante todavía no tiene calificaciones registradas.")
            else:
                filas_v = []
                total_ucv = 0.0
                total_reg = 0
                for m in malla_ev:
                    cal = notas_ev.get(m["materia"], "")
                    per_real = _pocv.get(int(m.get("periodo_orden") or 0), "") or periodos_ev.get(m["materia"], "")
                    if cal:
                        total_ucv += float(m["creditos"] or 0)
                        total_reg += 1
                    filas_v.append({
                        "Semestre": m["periodo"],
                        "Período": per_real,
                        "Unidad Curricular": m["materia"],
                        "U.C.": m["creditos"],
                        "Calificación": cal if cal else "—",
                    })
                st.dataframe(pd.DataFrame(filas_v), use_container_width=True, hide_index=True)
                cvv1, cvv2 = st.columns(2)
                with cvv1:
                    st.metric("Materias con nota", total_reg)
                with cvv2:
                    st.metric("Total U.C. cursadas", "%g" % total_ucv)

# ============================================================
# PÁGINA: SOLICITUDES (Modificación / Eliminación)
# ============================================================

elif menu in ("📋 Solicitudes de Modificación", "📋 Mis Solicitudes"):

    if rol == "ADMIN_REGIONAL":
        mostrar_header("📋 Mis Solicitudes", "Cree y consulte sus solicitudes de modificación o eliminación")

        # ----- Crear una nueva solicitud (Nivel 3) -----
        # El Regional NO modifica ni elimina directamente: envía una solicitud
        # con su motivo, y solo sobre expedientes de SU estado asignado.
        st.subheader("➕ Crear nueva solicitud")
        st.caption("Busque el expediente por cédula. Solo puede solicitar sobre expedientes de su estado.")
        ced_sol = st.text_input("🪪 Cédula del expediente", key="sol_new_ced", placeholder="Ej: V-12345678")
        if ced_sol.strip():
            df_new = obtener_expedientes({"cedula": ced_sol.strip().upper()})
            if estado_regional and not df_new.empty:
                df_new = df_new[df_new["estado"].fillna("").str.upper() == estado_regional.upper()]
            if df_new.empty:
                st.warning("⚠️ No se encontró un expediente de su estado con esa cédula.")
            else:
                rsol = df_new.iloc[0]
                st.info(f"Expediente: **{rsol['nombres']} {rsol.get('apellidos','')}** — {rsol['cedula']} — {rsol.get('programa','')}")
                tipo_sol = st.radio("Tipo de solicitud", ["Modificación", "Eliminación"], horizontal=True, key="sol_new_tipo")
                if tipo_sol == "Modificación":
                    campo_sol = st.selectbox("Campo a modificar", [
                        "Estado", "Municipio", "Aula Taller", "Nombres", "Apellidos",
                        "Cédula", "Correo del Titular", "Tipo de Programa", "Programa",
                        "Tipo de Expediente", "Observaciones"
                    ], key="sol_new_campo")
                    valor_nuevo_sol = st.text_input("Nuevo valor", key="sol_new_valor")
                    motivo_sol = st.text_area("Motivo de la modificación", key="sol_new_motivo")
                    if st.button("📤 Enviar Solicitud de Modificación", key="sol_new_btn_mod", type="primary"):
                        if valor_nuevo_sol.strip() and motivo_sol.strip():
                            campos_db_map = {
                                "Estado": "estado", "Municipio": "municipio", "Aula Taller": "aula_taller",
                                "Nombres": "nombres", "Apellidos": "apellidos", "Cédula": "cedula",
                                "Correo del Titular": "correo_titular",
                                "Tipo de Programa": "tipo_programa", "Programa": "programa",
                                "Tipo de Expediente": "tipo_expediente", "Observaciones": "observaciones"
                            }
                            col_name = campos_db_map.get(campo_sol, "")
                            valor_actual = str(rsol.get(col_name, "")) if col_name else ""
                            crear_solicitud_modificacion(
                                int(rsol["id"]), st.session_state.usuario,
                                campo_sol, valor_actual, valor_nuevo_sol.strip(), motivo_sol.strip()
                            )
                            st.success("✅ Solicitud de modificación enviada. Será revisada por un administrador.")
                        else:
                            st.warning("⚠️ Complete el nuevo valor y el motivo.")
                else:
                    motivo_elim_sol = st.text_area("Motivo de la eliminación", key="sol_new_motivo_elim")
                    if st.button("🗑️ Enviar Solicitud de Eliminación", key="sol_new_btn_elim", type="primary"):
                        if motivo_elim_sol.strip():
                            resumen = f"{rsol['cedula']} — {rsol['nombres']} {rsol.get('apellidos','')}".strip()
                            crear_solicitud_eliminacion(
                                int(rsol["id"]), st.session_state.usuario,
                                resumen, motivo_elim_sol.strip()
                            )
                            st.success("✅ Solicitud de eliminación enviada. Será revisada por un administrador.")
                        else:
                            st.warning("⚠️ Indique el motivo de la eliminación.")

        st.markdown("---")
        st.subheader("📜 Mis solicitudes enviadas")
        df_sol = obtener_solicitudes()
        if not df_sol.empty:
            df_sol = df_sol[df_sol["solicitado_por"] == st.session_state.usuario]
        if df_sol.empty:
            st.info("📭 Usted no ha enviado solicitudes todavía.")
        else:
            for _, s in df_sol.iterrows():
                es_elim = (s["campo_modificar"] == CAMPO_ELIMINAR)
                estado_badge = {"PENDIENTE": "🟡 PENDIENTE",
                                "APROBADA": "🟢 APROBADA",
                                "RECHAZADA": "🔴 RECHAZADA"}.get(s["estado_solicitud"], s["estado_solicitud"])
                titulo_card = "🗑️ Eliminación" if es_elim else f"📝 Modificar: {s['campo_modificar']}"
                with st.expander(f"{titulo_card} — Cédula {s.get('cedula','(eliminado)')} — {estado_badge}"):
                    st.write(f"**Titular:** {s.get('nombres','')} {s.get('apellidos','')}")
                    if es_elim:
                        st.write("**Tipo:** Solicitud de ELIMINACIÓN del expediente")
                    else:
                        st.write(f"**Valor actual:** {s['valor_actual']}")
                        st.write(f"**Valor nuevo:** {s['valor_nuevo']}")
                    st.write(f"**Motivo:** {s['motivo']}")
                    st.write(f"**Fecha solicitud:** {s['fecha_solicitud']}")
                    if s["estado_solicitud"] != "PENDIENTE":
                        st.write(f"**Revisado por:** {s['revisado_por']}")
                        st.write(f"**Fecha revisión:** {s['fecha_revision']}")

    else:
        # ADMIN_PRINCIPAL y ADMIN_AUXILIAR (Nivel 1 y 2): aprueban / ejecutan
        mostrar_header("📋 Solicitudes de Modificación", "Revise, apruebe o rechace las solicitudes")

        tab_pend, tab_hist = st.tabs(["🟡 Pendientes", "📚 Historial"])

        with tab_pend:
            df_pend = obtener_solicitudes("PENDIENTE")
            if df_pend.empty:
                st.info("✅ No hay solicitudes pendientes.")
            else:
                for _, s in df_pend.iterrows():
                    es_elim = (s["campo_modificar"] == CAMPO_ELIMINAR)
                    titulo_card = "🗑️ ELIMINACIÓN de expediente" if es_elim else f"📝 Modificar: {s['campo_modificar']}"
                    with st.expander(f"{titulo_card} — Cédula {s.get('cedula','(?)')} — 🟡 PENDIENTE", expanded=True):
                        st.write(f"**Titular:** {s.get('nombres','')} {s.get('apellidos','')}")
                        st.write(f"**Solicitado por:** {s['solicitado_por']}")
                        if es_elim:
                            st.error("⚠️ Esta solicitud ELIMINARÁ el expediente y su PDF de forma permanente.")
                        else:
                            st.write(f"**Valor actual:** {s['valor_actual']}")
                            st.write(f"**Valor nuevo:** {s['valor_nuevo']}")
                        st.write(f"**Motivo:** {s['motivo']}")
                        st.write(f"**Fecha:** {s['fecha_solicitud']}")

                        col_a, col_r = st.columns(2)
                        with col_a:
                            label_ap = "🗑️ Aprobar y ELIMINAR" if es_elim else "✅ Aprobar"
                            if st.button(label_ap, key=f"ap_{s['id']}", use_container_width=True, type="primary"):
                                ok, msg = aprobar_solicitud(s['id'], st.session_state.usuario)
                                if ok:
                                    st.success(f"✅ {msg}")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")
                        with col_r:
                            if st.button("❌ Rechazar", key=f"re_{s['id']}", use_container_width=True):
                                rechazar_solicitud(s['id'], st.session_state.usuario)
                                st.warning("Solicitud rechazada.")
                                st.rerun()

        with tab_hist:
            df_hist = obtener_solicitudes()
            if not df_hist.empty:
                df_hist = df_hist[df_hist["estado_solicitud"] != "PENDIENTE"]
            if df_hist.empty:
                st.info("📭 No hay solicitudes en el historial.")
            else:
                for _, s in df_hist.iterrows():
                    es_elim = (s["campo_modificar"] == CAMPO_ELIMINAR)
                    estado_badge = {"APROBADA": "🟢 APROBADA", "RECHAZADA": "🔴 RECHAZADA"}.get(s["estado_solicitud"], s["estado_solicitud"])
                    tipo_txt = "🗑️ Eliminación" if es_elim else f"📝 {s['campo_modificar']}"
                    with st.expander(f"{tipo_txt} — Cédula {s.get('cedula','(eliminado)')} — {estado_badge}"):
                        st.write(f"**Titular:** {s.get('nombres','')} {s.get('apellidos','')}")
                        st.write(f"**Solicitado por:** {s['solicitado_por']}")
                        st.write(f"**Motivo:** {s['motivo']}")
                        st.write(f"**Revisado por:** {s['revisado_por']}")
                        st.write(f"**Fecha revisión:** {s['fecha_revision']}")

# ============================================================
# PÁGINA: ESTADÍSTICAS
# ============================================================

elif menu == "📈 Estadísticas":
    mostrar_header("📈 Estadísticas", "Resumen general del sistema")

    df = obtener_expedientes()

    if df.empty:
        st.info("📊 Aún no hay expedientes registrados para mostrar estadísticas.")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📁 Total Expedientes", len(df))
        col2.metric("🏛️ Estados", df["estado"].nunique())
        col3.metric("🎓 Programas", df["programa"].nunique())
        col4.metric("📂 Tipos Expediente", df["tipo_expediente"].nunique())

        st.markdown("---")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("📊 Por Estado")
            st.bar_chart(df["estado"].value_counts())
        with col_g2:
            st.subheader("📊 Por Tipo de Programa")
            st.bar_chart(df["tipo_programa"].value_counts())

        col_g3, col_g4 = st.columns(2)
        with col_g3:
            st.subheader("📊 Por Tipo de Expediente")
            st.bar_chart(df["tipo_expediente"].value_counts())
        with col_g4:
            st.subheader("📊 Top 10 Programas")
            st.bar_chart(df["programa"].value_counts().head(10))

        st.markdown("---")
        st.subheader("📄 Descargar estadísticas en PDF")
        st.caption("Genera un PDF con **una página por cada renglón estadístico** "
                   "(por estado, por municipio, por tipo de programa, por programa y por tipo de expediente).")
        try:
            pdf_stats = generar_estadisticas_pdf(df)
            st.download_button(
                label="📄 Descargar Estadísticas (PDF)",
                data=pdf_stats,
                file_name=f"Estadisticas_UNEM_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"❌ No se pudo generar el PDF de estadísticas: {e}")

# ============================================================
# PÁGINA: GESTIÓN DE USUARIOS
# ============================================================

elif menu == "👥 Gestión de Usuarios":
    mostrar_header("👥 Gestión de Usuarios", "Cree y administre los usuarios del sistema")

    # Blindaje: solo Nivel 1 y Nivel 2 pueden crear/administrar usuarios.
    # El Nivel 3 (Administrador Regional) NO tiene acceso a esta sección.
    if rol not in ("ADMIN_PRINCIPAL", "ADMIN_AUXILIAR"):
        st.error("🚫 No tiene permiso para acceder a la Gestión de Usuarios.")
        st.stop()

    tab_crear, tab_lista = st.tabs(["➕ Crear Usuario", "📋 Lista de Usuarios"])

    with tab_crear:
        # El Rol se elige FUERA del formulario para poder cambiar el campo
        # "Nombre" según el rol: si es Administrador Regional (Nivel 3), su
        # nombre ES el ESTADO que se le asigna (solo trabajará ese estado).
        roles_disponibles = ROLES if rol == "ADMIN_PRINCIPAL" else ["ADMIN_AUXILIAR", "ADMIN_REGIONAL"]
        nuevo_rol = st.selectbox("Rol del nuevo usuario *", roles_disponibles, key="crear_rol")
        es_regional_nuevo = (nuevo_rol == "ADMIN_REGIONAL")
        if es_regional_nuevo:
            st.caption("El Administrador Regional queda ligado a un ESTADO (que se elige abajo). "
                       "Solo podrá ver y trabajar los registros de ese estado.")

        with st.form("form_crear_usuario", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nuevo_usuario = st.text_input("Usuario (para iniciar sesión) *")
                nuevo_nombre = st.text_input("Nombre completo *")
                nuevo_correo = st.text_input("Correo electrónico")
            with col2:
                nueva_clave = st.text_input("Contraseña *", type="password")
                if es_regional_nuevo:
                    nuevo_estado_region = st.selectbox("🏛️ Estado asignado *", list(ESTADOS_MUNICIPIOS.keys()))
                else:
                    nuevo_estado_region = ""

            if st.form_submit_button("➕ Crear Usuario", use_container_width=True, type="primary"):
                if nuevo_usuario.strip() and nueva_clave.strip() and str(nuevo_nombre).strip():
                    if es_regional_nuevo and not str(nuevo_estado_region).strip():
                        st.warning("⚠️ Seleccione el estado que se le asigna al Administrador Regional.")
                    else:
                        ok = crear_usuario(nuevo_usuario.strip(), nueva_clave.strip(),
                                           nuevo_rol, str(nuevo_nombre).strip(), nuevo_correo.strip(),
                                           str(nuevo_estado_region).strip())
                        if ok:
                            st.success(f"✅ Usuario **{nuevo_usuario}** creado exitosamente.")
                        else:
                            st.error("❌ Ese nombre de usuario ya existe. Elija otro.")
                else:
                    st.warning("⚠️ Complete usuario, contraseña y nombre.")

    with tab_lista:
        usuarios = obtener_usuarios()
        if not usuarios:
            st.info("No hay usuarios registrados.")
        else:
            for u in usuarios:
                usr, u_rol, u_nombre, u_correo, u_estado, u_fecha = u[:6]
                u_estado_region = u[6] if len(u) > 6 else ""
                estado_ico = "🟢 Activo" if u_estado == "ACTIVO" else "🔴 Inactivo"
                with st.expander(f"👤 {u_nombre} ({usr}) — {rol_nombre.get(u_rol, u_rol)} — {estado_ico}"):
                    st.write(f"**Usuario:** {usr}")
                    st.write(f"**Rol:** {rol_nombre.get(u_rol, u_rol)}")
                    if u_rol == "ADMIN_REGIONAL" and u_estado_region:
                        st.write(f"**Estado asignado:** {u_estado_region}")
                    st.write(f"**Correo:** {u_correo or '(sin correo)'}")
                    st.write(f"**Creado:** {u_fecha}")

                    col_e, col_p = st.columns(2)
                    with col_e:
                        if u_estado == "ACTIVO":
                            if st.button("🔴 Desactivar", key=f"des_{usr}", use_container_width=True):
                                cambiar_estado_usuario(usr, "INACTIVO")
                                st.rerun()
                        else:
                            if st.button("🟢 Activar", key=f"act_{usr}", use_container_width=True):
                                cambiar_estado_usuario(usr, "ACTIVO")
                                st.rerun()
                    with col_p:
                        nueva_c = st.text_input("Nueva contraseña", type="password", key=f"nc_{usr}")
                        if st.button("🔑 Cambiar Contraseña", key=f"cc_{usr}", use_container_width=True):
                            if nueva_c.strip():
                                cambiar_clave_usuario(usr, nueva_c.strip())
                                st.success("✅ Contraseña actualizada.")
                            else:
                                st.warning("⚠️ Escriba la nueva contraseña.")

                    # ----- Eliminar usuario (con jerarquía) -----
                    # Nivel 1: puede eliminar a cualquiera (menos a sí mismo y sin
                    #          dejar el sistema sin un Nivel 1 activo).
                    # Nivel 2: solo puede eliminar a usuarios de Nivel 3.
                    # Nivel 3: no tiene acceso a esta sección.
                    es_uno_mismo = (usr == st.session_state.usuario)
                    puede_eliminar = False
                    motivo_bloqueo = ""
                    if es_uno_mismo:
                        motivo_bloqueo = "No puede eliminar su propio usuario."
                    elif rol == "ADMIN_PRINCIPAL":
                        if u_rol == "ADMIN_PRINCIPAL" and u_estado == "ACTIVO" and contar_admin_principal_activos() <= 1:
                            motivo_bloqueo = "No se puede eliminar al último Administrador Principal activo."
                        else:
                            puede_eliminar = True
                    elif rol == "ADMIN_AUXILIAR":
                        if u_rol == "ADMIN_REGIONAL":
                            puede_eliminar = True
                        else:
                            motivo_bloqueo = "Un Administrador Auxiliar (Nivel 2) solo puede eliminar Administradores Regionales (Nivel 3)."

                    st.markdown("---")
                    if puede_eliminar:
                        conf_u = st.checkbox("Sí, confirmo eliminar este usuario de forma permanente.", key=f"confu_{usr}")
                        if st.button("🗑️ Eliminar Usuario", key=f"delu_{usr}", use_container_width=True):
                            if conf_u:
                                eliminar_usuario(usr)
                                st.success(f"✅ Usuario **{usr}** eliminado.")
                                st.rerun()
                            else:
                                st.warning("⚠️ Marque primero la casilla de confirmación.")
                    else:
                        st.caption(f"🔒 {motivo_bloqueo}")

# ============================================================
# PÁGINA: CONFIGURACIÓN DE LISTAS
# ============================================================

elif menu == "⚙️ Configuración de Listas":
    mostrar_header("⚙️ Configuración de Listas", "Administre los programas de cada tipo")

    st.info("Aquí puede agregar o quitar programas dentro de cada Tipo de Programa. "
            "Si no agrega ninguno, el sistema usa la lista oficial predeterminada.")

    tipo_sel = st.selectbox("Tipo de Programa", list(TIPOS_PROGRAMA_PROGRAMAS.keys()))

    st.markdown("---")
    st.subheader(f"🎓 Programas de: {tipo_sel}")

    personalizados = obtener_lista_editable("programa", tipo_sel)
    predeterminados = TIPOS_PROGRAMA_PROGRAMAS.get(tipo_sel, [])

    if personalizados:
        st.write("**Programas personalizados (guardados):**")
        for val in personalizados:
            col_v, col_x = st.columns([5, 1])
            col_v.write(f"• {val}")
            if col_x.button("🗑️", key=f"del_prog_{tipo_sel}_{val}"):
                eliminar_valor_lista("programa", tipo_sel, val)
                st.rerun()
    else:
        st.caption("Actualmente se están usando los programas oficiales predeterminados:")
        for val in predeterminados:
            st.write(f"• {val}")

    st.markdown("---")
    nuevo_prog = st.text_input("Agregar nuevo programa")
    if st.button("➕ Agregar Programa", type="primary"):
        if nuevo_prog.strip():
            ok = agregar_valor_lista("programa", tipo_sel, nuevo_prog.strip().upper())
            if ok:
                st.success("✅ Programa agregado.")
                st.rerun()
            else:
                st.error("❌ Ese programa ya existe en la lista.")
        else:
            st.warning("⚠️ Escriba el nombre del programa.")

# ============================================================
# PÁGINA: AULAS TALLER (carga masiva anclada a estado + municipio)
# ============================================================

elif menu == "🏫 Aulas Taller":
    mostrar_header("🏫 Aulas Taller", "Administre y cargue de forma masiva las aulas taller por estado y municipio")

    if rol not in ("ADMIN_PRINCIPAL", "ADMIN_AUXILIAR"):
        st.error("🚫 No tiene permiso para acceder a esta sección.")
        st.stop()

    st.info("Cada aula taller queda ligada a un **estado** y un **municipio**. "
            "Puede agregarlas una por una, o cargar cientos de golpe pegando una lista "
            "o subiendo un archivo Excel.")

    tab_carga, tab_masiva, tab_lista = st.tabs([
        "➕ Agregar una", "📥 Carga masiva", "📋 Ver / Eliminar"])

    # ---- Agregar una sola aula ----
    with tab_carga:
        col_e, col_m = st.columns(2)
        with col_e:
            est_sel_a = st.selectbox("Estado", list(ESTADOS_MUNICIPIOS.keys()), key="aula_add_estado")
        with col_m:
            muni_sel_a = st.selectbox("Municipio", ESTADOS_MUNICIPIOS.get(est_sel_a, []), key="aula_add_muni")
        nueva_aula = st.text_input("Nombre del aula taller", placeholder="Ej: Aula Taller Bolivariana 01", key="aula_add_nom")
        if st.button("➕ Agregar aula", type="primary", key="aula_add_btn"):
            if nueva_aula.strip():
                ok = agregar_valor_lista("aula_taller", _aula_key(est_sel_a, muni_sel_a), nueva_aula.strip())
                if ok:
                    st.success(f"✅ Aula agregada en {est_sel_a} / {muni_sel_a}.")
                    st.rerun()
                else:
                    st.error("❌ Esa aula ya existe en ese municipio.")
            else:
                st.warning("⚠️ Escriba el nombre del aula.")

    # ---- Carga masiva ----
    with tab_masiva:
        st.markdown("**Opción 1: Pegar una lista** (una aula por línea, con este formato):")
        st.code("ESTADO ; MUNICIPIO ; NOMBRE DEL AULA", language="text")
        st.caption("Puede separar con punto y coma (;), coma (,) o tabulación. "
                   "El estado y el municipio deben escribirse igual que en el sistema.")
        texto_masivo = st.text_area("Pegue aquí su lista", height=200, key="aula_masiva_texto",
                                    placeholder="Zulia ; Maracaibo ; Aula Taller 01\nZulia ; Maracaibo ; Aula Taller 02")

        st.markdown("**Opción 2: Subir un Excel** con las columnas: ESTADO, MUNICIPIO, AULA")
        archivo_aulas = st.file_uploader("Subir Excel (.xlsx)", type=["xlsx"], key="aula_masiva_file")

        if st.button("🚀 Procesar carga masiva", type="primary", key="aula_masiva_btn"):
            filas = []  # (estado, municipio, aula)
            # 1) Desde el texto pegado
            if texto_masivo.strip():
                for linea in texto_masivo.splitlines():
                    if not linea.strip():
                        continue
                    partes = re.split(r"[;,\t]", linea)
                    partes = [p.strip() for p in partes if p.strip()]
                    if len(partes) >= 3:
                        filas.append((partes[0], partes[1], partes[2]))
            # 2) Desde el Excel
            if archivo_aulas is not None:
                try:
                    df_aulas = pd.read_excel(archivo_aulas)
                    df_aulas.columns = [str(c).strip().upper() for c in df_aulas.columns]
                    for _, fa in df_aulas.iterrows():
                        e = str(fa.get("ESTADO", "")).strip()
                        m = str(fa.get("MUNICIPIO", "")).strip()
                        a = str(fa.get("AULA", "")).strip()
                        if e and m and a:
                            filas.append((e, m, a))
                except Exception as e:
                    st.error(f"❌ No se pudo leer el Excel: {e}")

            if not filas:
                st.warning("⚠️ No se encontraron filas válidas. Revise el formato.")
            else:
                agregadas = 0
                repetidas = 0
                no_reconocidas = []
                estados_validos = {k.upper(): k for k in ESTADOS_MUNICIPIOS.keys()}
                for e, m, a in filas:
                    e_key = estados_validos.get(e.strip().upper())
                    if not e_key:
                        no_reconocidas.append(f"{e} / {m} / {a}")
                        continue
                    # Validar municipio (comparación flexible por mayúsculas)
                    munis = ESTADOS_MUNICIPIOS.get(e_key, [])
                    m_map = {mm.upper(): mm for mm in munis}
                    m_key = m_map.get(m.strip().upper())
                    if not m_key:
                        no_reconocidas.append(f"{e} / {m} / {a}")
                        continue
                    ok = agregar_valor_lista("aula_taller", _aula_key(e_key, m_key), a.strip())
                    if ok:
                        agregadas += 1
                    else:
                        repetidas += 1
                st.success(f"✅ Se agregaron **{agregadas}** aulas. Repetidas (ya existían): {repetidas}.")
                if no_reconocidas:
                    st.warning(f"⚠️ {len(no_reconocidas)} filas no se cargaron porque el estado o municipio "
                               "no coinciden con los del sistema:")
                    st.text("\n".join(no_reconocidas[:50]))

    # ---- Ver / eliminar ----
    with tab_lista:
        col_e2, col_m2 = st.columns(2)
        with col_e2:
            est_sel_v = st.selectbox("Estado", list(ESTADOS_MUNICIPIOS.keys()), key="aula_ver_estado")
        with col_m2:
            muni_sel_v = st.selectbox("Municipio", ESTADOS_MUNICIPIOS.get(est_sel_v, []), key="aula_ver_muni")
        aulas_v = obtener_aulas(est_sel_v, muni_sel_v)
        if not aulas_v:
            st.info("📋 No hay aulas registradas para ese municipio.")
        else:
            st.caption(f"**{len(aulas_v)}** aulas en {est_sel_v} / {muni_sel_v}:")
            for av in aulas_v:
                col_av, col_del = st.columns([5, 1])
                col_av.write(f"• {av}")
                if col_del.button("🗑️", key=f"del_aula_{est_sel_v}_{muni_sel_v}_{av}"):
                    eliminar_valor_lista("aula_taller", _aula_key(est_sel_v, muni_sel_v), av)
                    # también intenta borrar la versión antigua (solo municipio)
                    eliminar_valor_lista("aula_taller", muni_sel_v, av)
                    st.rerun()

# ============================================================
# PÁGINA: CONFIGURACIÓN DE CORREO
# ============================================================

elif menu == "📧 Configuración de Correo":
    mostrar_header("📧 Configuración de Correo", "Configure el envío de notificaciones por correo")

    tab_smtp, tab_plantilla = st.tabs(["📮 Servidor SMTP", "✉️ Plantilla de Correo"])

    with tab_smtp:
        smtp = cargar_smtp_config()
        st.info("Para Gmail, use una **Contraseña de Aplicación** (no su contraseña normal). "
                "Actíve la verificación en 2 pasos y genere una clave de aplicación.")
        with st.form("form_smtp"):
            servidor = st.text_input("Servidor SMTP", value=smtp.get("servidor", "smtp.gmail.com"))
            puerto = st.number_input("Puerto", value=int(smtp.get("puerto", 587)), step=1)
            correo_remitente = st.text_input("Correo remitente", value=smtp.get("correo_remitente", ""))
            clave_app = st.text_input("Contraseña de aplicación", value=smtp.get("clave_app", ""), type="password")
            usar_tls = st.checkbox("Usar TLS", value=smtp.get("usar_tls", True))
            if st.form_submit_button("💾 Guardar Configuración", use_container_width=True, type="primary"):
                guardar_smtp_config({
                    "servidor": servidor.strip(),
                    "puerto": int(puerto),
                    "correo_remitente": correo_remitente.strip(),
                    "clave_app": clave_app.strip(),
                    "usar_tls": usar_tls
                })
                st.success("✅ Configuración de correo guardada.")

    with tab_plantilla:
        plantillas = cargar_plantillas_correo()
        pl = plantillas.get("registro_expediente", {
            "asunto": "Registro de Expediente - UNEM",
            "cuerpo": ("Estimado(a) {nombres} {apellidos},\n\n"
                       "Su expediente ha sido registrado exitosamente en el sistema UNEM.\n\n"
                       "Cédula: {cedula}\n"
                       "Programa: {programa}\n"
                       "Tipo de expediente: {tipo_expediente}\n\n"
                       "Adjunto encontrará el PDF de su expediente.\n\n"
                       "Saludos cordiales,\nEquipo UNEM")
        })
        st.caption("Puede usar estas variables en el texto: {nombres}, {apellidos}, {cedula}, "
                   "{estado}, {municipio}, {programa}, {tipo_programa}, {tipo_expediente}")
        with st.form("form_plantilla"):
            asunto_pl = st.text_input("Asunto del correo", value=pl["asunto"])
            cuerpo_pl = st.text_area("Cuerpo del correo", value=pl["cuerpo"], height=280)
            if st.form_submit_button("💾 Guardar Plantilla", use_container_width=True, type="primary"):
                guardar_plantilla_correo("registro_expediente", asunto_pl, cuerpo_pl)
                st.success("✅ Plantilla guardada.")

# ============================================================
# PÁGINA: RESPALDO DE DATOS
# ============================================================

elif menu == "📥 Respaldo de Datos":
    mostrar_header("📥 Respaldo de Datos", "Descargue copias de seguridad del sistema")

    df = obtener_expedientes()

    st.subheader("📊 Respaldo en Excel")
    st.caption("Descarga todos los expedientes en un archivo Excel. La primera hoja trae "
               "todos los datos y la segunda hoja (Calificaciones) trae las notas de cada "
               "estudiante con su período/semestre.")

    if df.empty:
        st.info("📋 Aún no hay expedientes para respaldar.")
    else:
        # Excel: una columna por campo, con nombres claros (sin la ruta interna del PDF)
        columnas_excel = {
            "id": "N°",
            "estado": "ESTADO",
            "municipio": "MUNICIPIO",
            "aula_taller": "AULA TALLER",
            "nombres": "NOMBRES",
            "apellidos": "APELLIDOS",
            "cedula": "CÉDULA",
            "correo_titular": "CORREO ELECTRÓNICO",
            "tipo_programa": "TIPO DE PROGRAMA",
            "programa": "PROGRAMA",
            "tipo_expediente": "TIPO DE EXPEDIENTE",
            "observaciones": "OBSERVACIONES",
            "registrado_por": "REGISTRADO POR",
            "fecha_registro": "FECHA DE REGISTRO",
        }
        df_excel = df.drop(columns=["pdf_path"], errors="ignore").rename(columns=columnas_excel)
        orden = [v for v in columnas_excel.values() if v in df_excel.columns]
        df_excel = df_excel[orden]

        buffer_xlsx = BytesIO()
        with pd.ExcelWriter(buffer_xlsx, engine="openpyxl") as writer:
            df_excel.to_excel(writer, index=False, sheet_name="Expedientes")

            # Segunda hoja: CALIFICACIONES (notas por materia, con su período/semestre)
            filas_notas = []
            for _, rr in df.iterrows():
                ced = str(rr.get("cedula", ""))
                notas_rr = obtener_notas(ced)
                periodos_rr = obtener_periodos_notas(ced)
                nombre_completo = f"{rr.get('nombres','')} {rr.get('apellidos','')}".strip()
                for materia_n, nota_n in notas_rr.items():
                    filas_notas.append({
                        "CÉDULA": ced,
                        "NOMBRE": nombre_completo,
                        "PROGRAMA": rr.get("programa", ""),
                        "MATERIA": materia_n,
                        "PERÍODO / SEMESTRE": periodos_rr.get(materia_n, ""),
                        "CALIFICACIÓN": nota_n,
                    })
            if filas_notas:
                df_notas_bk = pd.DataFrame(filas_notas)
            else:
                df_notas_bk = pd.DataFrame(columns=[
                    "CÉDULA", "NOMBRE", "PROGRAMA", "MATERIA", "PERÍODO / SEMESTRE", "CALIFICACIÓN"
                ])
            df_notas_bk.to_excel(writer, index=False, sheet_name="Calificaciones")
        buffer_xlsx.seek(0)

        st.download_button(
            label="📊 Descargar Respaldo en Excel",
            data=buffer_xlsx,
            file_name=f"Respaldo_Expedientes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.markdown("---")

    st.subheader("🗂️ Respaldo de PDFs (todos los expedientes)")
    st.caption("Descarga un único archivo comprimido (ZIP) con todos los PDFs. "
               "Cada PDF se nombra con la cédula del titular.")

    if df.empty:
        st.info("📋 Aún no hay PDFs para respaldar.")
    else:
        pdfs_disponibles = df[df["pdf_path"].notna()]
        total_pdfs = 0
        buffer_zip = BytesIO()
        nombres_usados = {}
        with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for _, row in pdfs_disponibles.iterrows():
                ruta = row["pdf_path"]
                if ruta and os.path.exists(ruta):
                    cedula_limpia = str(row["cedula"]).replace("/", "-").replace("\\", "-").strip()
                    nombre_base = f"{cedula_limpia}.pdf"
                    # Evitar sobrescribir si hubiera cédulas repetidas
                    if nombre_base in nombres_usados:
                        nombres_usados[nombre_base] += 1
                        nombre_base = f"{cedula_limpia}_{nombres_usados[nombre_base]}.pdf"
                    else:
                        nombres_usados[nombre_base] = 1
                    zf.write(ruta, arcname=nombre_base)
                    total_pdfs += 1
        buffer_zip.seek(0)

        if total_pdfs > 0:
            st.success(f"📄 Se prepararon **{total_pdfs}** PDFs para descargar.")
            st.download_button(
                label="🗂️ Descargar Todos los PDFs (ZIP)",
                data=buffer_zip,
                file_name=f"PDFs_Expedientes_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                mime="application/zip",
                use_container_width=True,
            )
        else:
            st.info("📋 No se encontraron archivos PDF guardados en el sistema.")

    st.markdown("---")

    st.subheader("🎓 Respaldo de Certificaciones (todos los expedientes)")
    st.caption("Genera y descarga un único archivo comprimido (ZIP) con las "
               "CERTIFICACIONES de todos los expedientes. Cada certificación se "
               "nombra con la cédula del titular. La preparación puede tardar unos "
               "segundos si hay muchos expedientes.")

    if df.empty:
        st.info("📋 Aún no hay expedientes para generar certificaciones.")
    else:
        if st.button("🎓 Preparar Certificaciones (ZIP)", use_container_width=True, key="btn_prep_certs"):
            total_certs = 0
            errores_certs = 0
            buffer_zip_cert = BytesIO()
            nombres_usados_cert = {}
            with st.spinner("Generando certificaciones, por favor espera..."):
                with zipfile.ZipFile(buffer_zip_cert, "w", zipfile.ZIP_DEFLATED) as zf:
                    for _, row in df.iterrows():
                        try:
                            datos_cert = generar_certificado_pdf(row)
                        except Exception:
                            errores_certs += 1
                            continue
                        cedula_limpia = str(row["cedula"]).replace("/", "-").replace("\\", "-").strip()
                        nombre_base = f"{cedula_limpia}.pdf"
                        # Evitar sobrescribir si hubiera cédulas repetidas
                        if nombre_base in nombres_usados_cert:
                            nombres_usados_cert[nombre_base] += 1
                            nombre_base = f"{cedula_limpia}_{nombres_usados_cert[nombre_base]}.pdf"
                        else:
                            nombres_usados_cert[nombre_base] = 1
                        zf.writestr(nombre_base, datos_cert)
                        total_certs += 1
            buffer_zip_cert.seek(0)

            if total_certs > 0:
                st.success(f"🎓 Se prepararon **{total_certs}** certificaciones para descargar.")
                if errores_certs > 0:
                    st.warning(f"⚠️ {errores_certs} expediente(s) no se pudieron certificar.")
                st.download_button(
                    label="🗂️ Descargar Todas las Certificaciones (ZIP)",
                    data=buffer_zip_cert,
                    file_name=f"Certificaciones_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="dl_certs_zip",
                )
            else:
                st.info("📋 No se pudo generar ninguna certificación.")
