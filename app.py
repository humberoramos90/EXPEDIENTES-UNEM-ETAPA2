# -*- coding: utf-8 -*-
"""
Expedientes UNEM - Etapa 2  v2.2
Sistema de Gestión de Expedientes Estudiantiles y Certificaciones de Calificaciones
Universidad Nacional Experimental del Magisterio "Samuel Robinson"

Niveles de usuario:
  - Nivel 1: Admin Principal
  - Nivel 2: Secretaría General
  - Nivel 3: Secretaría Situada

Mejoras v2.2 (sobre v2.1):
 13) APERTURA NACIONAL/ESTADAL/MUNICIPAL/POR PLANTEL: Nivel 1 aperturación jerárquica
 14) ELIMINAR REGISTRO CON AUTORIZACIÓN: Nivel 1-2 eliminan directo; Nivel 3 solicita autorización
 15) REPORTE DE AUTORIZACIONES Y ELIMINACIONES: descargable en Excel

Mejoras v2.1:
  1) AUTO-LETRAS: nota numérica → se escribe en letras automáticamente
  2) APERTURA/CIERRE DE NOTAS: periodos de carga de notas controlados por Admin
  3) BATCH PRINTING: generar certificaciones en lote (ZIP con PDFs individuales)
  4) PNF DUAL VIEW: TSU ve solo trayectos Tercer+; BACHILLER ve todo
  5) PNFA_E SUB-OPCIONES: proviene de PNF previo o de otra institución
  6) PNFA_M PRERREQUISITO: requiere cédula de Especialización registrada
  7) PNFA_D PRERREQUISITOS: requiere cédula de Especialización Y Maestría
  8) VERIFICAR EXPEDIENTE ETAPA 1: consulta read-only a expedientes.db
  9) TITULARIDAD POR GÉNERO: Profesor/Profesora, Doctor/Doctora, etc.
 10) CAMBIO DE CONTRASEÑA: pestaña nueva en Gestión de Usuarios
 11) CASCADA DINÁMICA: Estado→Municipio→Aula y Tipo→Programa se actualizan al cambiar
 12) RESPALDO Y EXPORTACIÓN: descargar base de datos (.db), exportar a Excel (.xlsx),
     restaurar respaldo, y descargar base de Etapa 1
"""

import streamlit as st
import sqlite3
import hashlib
import os
import io
import re
import time
import zipfile
from datetime import datetime, date
import pandas as pd
from io import BytesIO

# --- Librerías para PDF (certificaciones) ---
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm, cm
from reportlab.lib.colors import HexColor, black, white, gray
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader

# --- Librerías para QR y Barcode ---
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter

# --- Librería para firma digital (watermark) ---
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================

DB_FILE = "expedientes_unem.db"
DB_FILE_ETAPA1 = "expedientes.db"
UPLOAD_FOLDER = "uploads_pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
MAX_PDF_SIZE = 5 * 1024 * 1024  # 5MB

# ============================================================
# DATOS DE VENEZUELA - 24 Estados y Municipios
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



# ============================================================
# TIPOS DE PROGRAMA Y PROGRAMAS POR DEFECTO
# ============================================================

TIPOS_PROGRAMA = ["PNF", "PNFA_E", "PNFA_M", "PNFA_D"]

PROGRAMAS_POR_DEFECTO = {
    "PNF": [
        "LICENCIADO EN EDUCACIÓN INICIAL",
        "LICENCIADO EN EDUCACIÓN PRIMARIA",
        "PROFESOR DE BIOLOGÍA",
    ],
    "PNFA_E": [
        "ESPECIALIZACIÓN EN EDUCACIÓN MEDIA",
        "ESPECIALIZACIÓN EN EDUCACIÓN DE JÓVENES Y ADULTOS",
        "ESPECIALIZACIÓN EN DERECHOS DEL NIÑO, NIÑAS Y ADOLESCENTES",
        "ESPECIALIZACIÓN EN SUPERVISIÓN EDUCATIVA",
    ],
    "PNFA_M": [
        "MAESTRÍA EN EDUCACIÓN INICIAL",
        "MAESTRÍA EN EDUCACIÓN PRIMARIA",
        "MAESTRÍA EN DIRECCIÓN Y SUPERVISIÓN EDUCATIVA",
        "MAGISTER EN PEDAGOGÍA CULTURAL E INTERCULTURALIDAD",
        "MAESTRÍA EN EDUCACIÓN FÍSICA",
        "MAESTRÍA EN MATEMÁTICAS",
        "MAESTRÍA EN INGLÉS",
    ],
    "PNFA_D": [
        "DOCTORADO EN EDUCACIÓN (Próximamente)",
    ],
}

# ============================================================
# NIVELES ACADÉMICOS, CALIFICACIONES Y CONFIGURACIÓN
# ============================================================

NIVELES_ACADEMICOS = ["BACHILLER", "TSU"]
NIVELES_PNFA = {"PNFA_E": "ESPECIALISTA", "PNFA_M": "MAESTRO", "PNFA_D": "DOCTOR"}
TIPOS_INGRESO = ["INGRESO", "REINGRESO"]
CALIFICACIONES_ESPECIALES = ["AP", "AC", "RE"]

# ============================================================
# TITULARIDAD POR GÉNERO  (v2.1 NUEVO)
# ============================================================

# Mapeo de titularidad según tipo de programa y sexo
# Sexo en el formulario: "M" o "F"
TITULARIDAD_POR_GENERO = {
    "PNF": {"M": "Profesor", "F": "Profesora"},
    "PNFA_E": {"M": "Especialista", "F": "Especialista"},  # No cambia por género
    "PNFA_M": {"M": "Magíster", "F": "Magíster"},  # No cambia por género
    "PNFA_D": {"M": "Doctor", "F": "Doctora"},
}


def calcular_titularidad(tipo_programa, sexo):
    """Calcula la titularidad según tipo de programa y sexo"""
    mapa = TITULARIDAD_POR_GENERO.get(tipo_programa, {})
    if mapa:
        return mapa.get(sexo, mapa.get("M", ""))
    # Si es PNF pero no está en el mapa específico, usar Profesor/a
    if "PNF" in tipo_programa.upper():
        return "Profesor" if sexo == "M" else "Profesora"
    return ""


# Datos fijos de la certificación
SECRETARIO_NOMBRE = "LENIN ROBERTO ROMERO ROSA"
SECRETARIO_CEDULA = "V-2.956.814"
GACETA_NUM = "41.632"
RESOLUCION_NUM = "0026/002"

# ============================================================
# ROLES
# ============================================================

ROLES = {"NIVEL_1": "Admin Principal", "NIVEL_2": "Secretaría General", "NIVEL_3": "Secretaría Situada"}
ROLES_LIST = list(ROLES.values())



# ============================================================
# PENSUM (CURRÍCULO) POR PROGRAMA PNF
# ============================================================

PENSUM_PNF = {
    "LICENCIADO EN EDUCACIÓN INICIAL": {
        "Introductorio - Primer Semestre": [
            {"uc": "Proyecto Socio Integrador, Práctica Profesional Transformadora I", "creditos": 9},
            {"uc": "Educación Bolivariana y Sociedad", "creditos": 2},
            {"uc": "Uso Social de la Lengua", "creditos": 2},
            {"uc": "Desarrollo y Crecimiento del Niño y la Niña en el Contexto Venezolano", "creditos": 3},
            {"uc": "Formación Socio Crítica I", "creditos": 3},
            {"uc": "Gestión de Riesgos y Protección Civil", "creditos": 3},
        ],
        "Primer Trayecto - Segundo Semestre": [
            {"uc": "Proyecto Socio Integrador, Práctica Profesional Transformadora II", "creditos": 8},
            {"uc": "Pedagogía Transformadora", "creditos": 3},
            {"uc": "Cimientos de la Educación Inicial", "creditos": 3},
            {"uc": "Las TICs en la Educación Bolivariana", "creditos": 3},
            {"uc": "La Actividad Física, el Juego y la Recreación en la Educación Inicial", "creditos": 2},
            {"uc": "Formación Socio Crítica II", "creditos": 3},
            {"uc": "Lenguas Indígenas Electiva I", "creditos": 3},
        ],
        "Segundo Trayecto - Tercer Semestre": [
            {"uc": "Proyecto Socio Integrador, Práctica Profesional Transformadora III", "creditos": 9},
            {"uc": "Matemática y Estadística Aplicada a lo Socio Educativo", "creditos": 3},
            {"uc": "Educación y Territorialidad", "creditos": 3},
            {"uc": "Currículo en el Sistema Educativo Venezolano", "creditos": 3},
            {"uc": "Tradiciones y Costumbres del Pueblo Venezolano", "creditos": 2},
            {"uc": "Formación Socio Crítica III", "creditos": 3},
            {"uc": "Ambiente y Salud Integral", "creditos": 3},
        ],
        "Segundo Trayecto - Cuarto Semestre": [
            {"uc": "Proyecto Socio Integrador, Práctica Profesional Transformadora IV", "creditos": 8},
            {"uc": "Desarrollo Socio Afectivo y la Inteligencia", "creditos": 3},
            {"uc": "Responsabilidad Social Familia Escuela y Comunidad", "creditos": 3},
            {"uc": "Educación Sexual y Reproductiva", "creditos": 3},
            {"uc": "Desempeño Profesional del Docente de Educación Inicial", "creditos": 2},
            {"uc": "Formación Socio Crítica IV", "creditos": 3},
            {"uc": "Alimentación Sana y Alternativa en Educación Inicial. Electiva II", "creditos": 2},
        ],
        "Tercer Trayecto - Quinto Semestre": [
            {"uc": "Proyecto Socio Integrador, Práctica Profesional Transformadora V", "creditos": 9},
            {"uc": "Planificación y Evaluación en Educación Inicial", "creditos": 3},
            {"uc": "Derechos Humanos del Niño y la Niña en el Contexto Educativo Venezolano", "creditos": 3},
            {"uc": "Prevención y Atención a la Salud Integral del Niño y la Niña", "creditos": 3},
            {"uc": "Expresión Musical y Corporal", "creditos": 2},
            {"uc": "Formación Socio Crítica V", "creditos": 3},
            {"uc": "Saberes Ancestrales de los Pueblos Indígenas", "creditos": 2},
        ],
        "Tercer Trayecto - Sexto Semestre": [
            {"uc": "Proyecto Socio Integrador, Práctica Profesional Transformadora VI", "creditos": 8},
            {"uc": "Educación Maternal, la Gestación y el Parto Humanizado", "creditos": 3},
            {"uc": "Desarrollo de la Lengua Oral y Lengua Escrita en Niños de Educación Inicial", "creditos": 3},
            {"uc": "Necesidades Educativas Especiales y Atención a la Diversidad", "creditos": 3},
            {"uc": "Expresión Teatral y Danzas Tradicionales de Venezuela", "creditos": 2},
            {"uc": "Formación Socio Crítica VI", "creditos": 3},
            {"uc": "Creatividad e Innovación en Educación Inicial. Electiva III", "creditos": 2},
        ],
        "Cuarto Trayecto - Séptimo Semestre": [
            {"uc": "Proyecto Socio Integrador, Práctica Profesional Transformadora VII", "creditos": 9},
            {"uc": "Desarrollo de los Procesos Lógico Matemáticos en el Niño de Educación Inicial", "creditos": 3},
            {"uc": "Expresión Plástica del Niño en Educación Inicial", "creditos": 3},
            {"uc": "Promoción de la Lectura para Niños y Niñas de Educación Inicial", "creditos": 2},
            {"uc": "Formación Socio Crítica VII", "creditos": 3},
            {"uc": "Transformación de Materiales y Recursos para la Educación Inicial", "creditos": 3},
        ],
        "Cuarto Trayecto - Octavo Semestre": [
            {"uc": "Proyecto Socio Integrador, Práctica Profesional Transformadora VIII", "creditos": 8},
            {"uc": "Procesos Administrativos en la Educación Inicial en Venezuela", "creditos": 3},
            {"uc": "Medios de Comunicación en Educación Inicial", "creditos": 2},
            {"uc": "Formación Socio Crítica VIII", "creditos": 3},
            {"uc": "Continuidad Afectiva y Articulación Pedagógica en Educación Inicial. Electiva IV", "creditos": 3},
        ],
    },
    "LICENCIADO EN EDUCACIÓN PRIMARIA": {
        "Introductorio - Primer Trimestre": [
            {"uc": "El Docente y su Contexto Educativo. (Autobiografía y Caracterización del Entorno)", "creditos": 7},
            {"uc": "Ciencias de la Educación", "creditos": 2},
            {"uc": "Desarrollo Humano Integral", "creditos": 2},
            {"uc": "Uso Social de la Lengua (Hablar, Escuchar, Leer y Escribir) del Docente", "creditos": 3},
        ],
        "Primer Trayecto - Segundo Trimestre": [
            {"uc": "Técnicas e Instrumentos de Recolección de Datos e Información", "creditos": 7},
            {"uc": "Pensamiento Pedagógico Liberador Nuestroamericano", "creditos": 2},
            {"uc": "Identidad, Arraigo, Soberanía e Independencia", "creditos": 2},
            {"uc": "Legislación Educativa y las Leyes del Poder Popular", "creditos": 3},
        ],
        "Primer Trayecto - Tercer Trimestre": [
            {"uc": "Proyecto I: Diagnóstico Participativo Comunitario. (Del Registro a la Sistematización de Experiencias)", "creditos": 7},
            {"uc": "Pensamiento Pedagógico de Simón Rodríguez", "creditos": 2},
            {"uc": "Geo-Histórico", "creditos": 2},
            {"uc": "Fundamentos Políticos, Filosóficos y Pedagógicos de la Educación Bolivariana", "creditos": 3},
        ],
        "Segundo Trayecto - Cuarto Trimestre": [
            {"uc": "Enfoques y Paradigmas de la Investigación Educativa", "creditos": 7},
            {"uc": "Pedagogía Crítica", "creditos": 2},
            {"uc": "Matemática para la Comprensión del Mundo y la Vida", "creditos": 2},
            {"uc": "Historia de la Educación Primaria en Venezuela", "creditos": 3},
        ],
        "Segundo Trayecto - Quinto Trimestre": [
            {"uc": "Bases Teórico-Metodológicas de la Sistematización y los Relatos Pedagógicos", "creditos": 7},
            {"uc": "Formación del Nuevo Republicano", "creditos": 2},
            {"uc": "Didáctica Crítica e Integradora", "creditos": 3},
            {"uc": "Nueva Subjetividad y Función Social del Docente Bolivariano", "creditos": 4},
        ],
        "Segundo Trayecto - Sexto Trimestre": [
            {"uc": "Proyecto II: Registro y Sistematización de Experiencias como Metódica de Reflexión y Transformación", "creditos": 7},
            {"uc": "Nuevas Lógicas de Organización y Valoración de los Procesos Educativos", "creditos": 2},
            {"uc": "Planificación y Evaluación de los Aprendizajes", "creditos": 3},
            {"uc": "Recursos para el Aprendizaje y la Enseñanza", "creditos": 4},
        ],
        "Tercer Trayecto - Séptimo Trimestre": [
            {"uc": "Bases Teórico-Metodológicas de la IAPT Aplicadas a la Educación", "creditos": 7},
            {"uc": "Docencia y Práctica Reflexiva, Innovadora y Creativa", "creditos": 2},
            {"uc": "La Educación Popular como Alternativa para el Trabajo Sociocomunitario en la Construcción del Aprendizaje", "creditos": 4},
            {"uc": "Integración Social e Inclusión en la Escuela Primaria", "creditos": 3},
        ],
        "Tercer Trayecto - Octavo Trimestre": [
            {"uc": "IAPT en la Praxis Pedagógica", "creditos": 7},
            {"uc": "Relaciones de Poder", "creditos": 2},
            {"uc": "Perspectivas en la Enseñanza y Aprendizaje de la Lectura y la Escritura", "creditos": 4},
            {"uc": "Educación, Trabajo Social Liberador y Espacios Productivos en la Escuela Primaria", "creditos": 3},
        ],
        "Cuarto Trayecto - Noveno Trimestre": [
            {"uc": "Proyecto III: Socialización de la Práctica Pedagógica a Través de la Investigación, Acción Participativa y Transformadora", "creditos": 7},
            {"uc": "Cultura de Convivencia y Paz", "creditos": 2},
            {"uc": "El Arte Como Modo de Vivir, Sentir y Mirar lo Estético", "creditos": 4},
            {"uc": "Educación Intercultural", "creditos": 4},
        ],
        "Cuarto Trayecto - Décimo Trimestre": [
            {"uc": "Ecología de los Saberes", "creditos": 7},
            {"uc": "Educación, Territorialización y Comunalización", "creditos": 2},
            {"uc": "Lenguaje Aplicado en las Ciencias y la Tecnología", "creditos": 4},
            {"uc": "Retos y Desafíos de la Educación Ambiental: Formación Ecosocialista", "creditos": 4},
        ],
        "Cuarto Trayecto - Décimo Primer Trimestre": [
            {"uc": "Comunalización de los Espacios de Formación e Investigación", "creditos": 7},
            {"uc": "Democratización del Saber Científico", "creditos": 2},
            {"uc": "Educación Integral de la Sexualidad en la Educación Primaria", "creditos": 4},
            {"uc": "Orientación Escolar y Familiar", "creditos": 4},
        ],
        "Cuarto Trayecto - Décimo Segundo Trimestre": [
            {"uc": "Proyecto IV: Experiencia de Transformación Comunitaria", "creditos": 7},
            {"uc": "Contexto Jurídico-Político de la Comunalización de la Educación en Venezuela", "creditos": 2},
            {"uc": "Educación Física, Deporte y Recreación", "creditos": 4},
            {"uc": "El Cuerpo, la Emocionalidad, la Afectividad y la Lúdica en los Procesos de Enseñanza y Aprendizaje", "creditos": 4},
        ],
    },
    "PROFESOR DE BIOLOGÍA": {
        "Introductorio - Primer Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora I", "creditos": 7},
            {"uc": "Teoría Social del Aprendizaje", "creditos": 2},
            {"uc": "Pedagogía y Didáctica Crítica en el área de Ciencias Naturales", "creditos": 2},
            {"uc": "Elementos Teórico Prácticos de la Biología I", "creditos": 2},
            {"uc": "Biomatemática", "creditos": 2},
            {"uc": "Laboratorio: Integración de las Ciencias Naturales I", "creditos": 3},
        ],
        "Primer Trayecto - Segundo Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora II", "creditos": 7},
            {"uc": "Planificación Educativa por Proyectos", "creditos": 2},
            {"uc": "Elementos Teórico Prácticos de la Biología II", "creditos": 2},
            {"uc": "Química", "creditos": 2},
            {"uc": "Laboratorio: Integración de las Ciencias Naturales II", "creditos": 3},
        ],
        "Primer Trayecto - Tercer Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora III", "creditos": 7},
            {"uc": "Evaluación y Valoración de los Aprendizajes", "creditos": 2},
            {"uc": "Elementos Teórico Prácticos de la Biología III", "creditos": 2},
            {"uc": "Física", "creditos": 2},
            {"uc": "Laboratorio: Integración de las Ciencias Naturales III", "creditos": 3},
        ],
        "Segundo Trayecto - Cuarto Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora IV", "creditos": 7},
            {"uc": "Uso Crítico de las TIC en el Ámbito Educativo", "creditos": 2},
            {"uc": "Elementos Teórico Prácticos de la Biología IV", "creditos": 2},
            {"uc": "Biología Social y Biodiversidad", "creditos": 2},
            {"uc": "Laboratorio Teórico-Práctico I", "creditos": 3},
        ],
        "Segundo Trayecto - Quinto Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora V", "creditos": 7},
            {"uc": "Necesidades Educativas e Integración", "creditos": 2},
            {"uc": "Elementos Teórico Prácticos de la Biología V", "creditos": 2},
            {"uc": "Cultura Ecológica Social", "creditos": 2},
            {"uc": "Laboratorio Teórico-Práctico II", "creditos": 3},
        ],
        "Segundo Trayecto - Sexto Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora VI", "creditos": 7},
            {"uc": "Educación para la Paz y la Vida", "creditos": 2},
            {"uc": "Elementos Teórico Prácticos de la Biología y sus Aplicaciones", "creditos": 2},
            {"uc": "Laboratorio Teórico-Práctico III", "creditos": 3},
        ],
        "Tercer Trayecto - Séptimo Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora VII", "creditos": 7},
            {"uc": "Seminario: Pensamiento Pedagógico Liberador Nuestroamericano", "creditos": 2},
            {"uc": "Ciencias Naturales para la Transformación Social I", "creditos": 3},
            {"uc": "Laboratorio Integración de los Procesos Didácticos de la Biología I", "creditos": 3},
        ],
        "Tercer Trayecto - Octavo Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora VIII", "creditos": 7},
            {"uc": "Desarrollo de la Ciudadanía Crítica", "creditos": 2},
            {"uc": "Ciencias Naturales para la Transformación Social II", "creditos": 3},
            {"uc": "Laboratorio Integración de los Procesos Didácticos de la Biología II", "creditos": 3},
        ],
        "Cuarto Trayecto - Noveno Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora IX", "creditos": 7},
            {"uc": "Procesos Histórico Políticos de la Educación Nuestroamericana", "creditos": 2},
            {"uc": "Ciencias Naturales para la Transformación Social III", "creditos": 3},
            {"uc": "Laboratorio Integración de los Procesos Didácticos de la Biología III", "creditos": 4},
        ],
        "Cuarto Trayecto - Décimo Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora X", "creditos": 7},
            {"uc": "Taller: Metodología IAPT", "creditos": 2},
            {"uc": "Taller: Procesos Interdisciplinarios en Biología", "creditos": 4},
            {"uc": "Laboratorio: Procesos de Investigación, Creación e Innovación de las Ciencias Naturales I", "creditos": 4},
        ],
        "Cuarto Trayecto - Décimo Primer Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora XI", "creditos": 7},
            {"uc": "Taller: Sistematización IAPT", "creditos": 2},
            {"uc": "Ciencias Naturales para la Transformación Social IV", "creditos": 2},
            {"uc": "Laboratorio: Procesos de Investigación, Creación e Innovación de las Ciencias Naturales II", "creditos": 4},
        ],
        "Cuarto Trayecto - Décimo Segundo Trimestre": [
            {"uc": "Proyecto Práctica Docente Transformadora XII", "creditos": 7},
            {"uc": "Taller: Planificación y Evaluación IAPT", "creditos": 2},
            {"uc": "Laboratorio: Fundamentos de Biología Molecular y Celular en Actividades Socioproductivas", "creditos": 2},
            {"uc": "Laboratorio: Procesos de Investigación, Creación e Innovación de las Ciencias Naturales III", "creditos": 4},
        ],
    },
}



# ============================================================
# BASE DE DATOS
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # --- Migración: verificar que las tablas tengan las columnas correctas ---
    # Si existe una tabla 'usuarios' sin columna 'cedula', eliminarla para recrearla
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
    if c.fetchone():
        c.execute("PRAGMA table_info(usuarios)")
        columnas = [row[1] for row in c.fetchall()]
        if 'cedula' not in columnas:
            c.execute("DROP TABLE usuarios")
            conn.commit()

    # --- Usuarios ---
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        cedula TEXT NOT NULL UNIQUE,
        clave TEXT NOT NULL,
        rol TEXT NOT NULL,
        estado TEXT NOT NULL,
        fecha_creacion TEXT NOT NULL
    )""")

    # Migración: verificar tabla 'estudiantes' tenga columna 'cedula'
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='estudiantes'")
    if c.fetchone():
        c.execute("PRAGMA table_info(estudiantes)")
        columnas = [row[1] for row in c.fetchall()]
        if 'cedula' not in columnas:
            c.execute("DROP TABLE estudiantes")
            conn.commit()

    # --- Almacén (sedes) ---
    c.execute("""CREATE TABLE IF NOT EXISTS almacenes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        estado TEXT NOT NULL,
        municipio TEXT NOT NULL,
        aula_taller TEXT NOT NULL,
        fecha_creacion TEXT NOT NULL
    )""")

    # --- Estudiantes ---
    c.execute("""CREATE TABLE IF NOT EXISTS estudiantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cedula TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        nombres TEXT NOT NULL,
        sexo TEXT NOT NULL,
        fecha_nacimiento TEXT,
        lugar_nacimiento TEXT,
        estado TEXT NOT NULL,
        municipio TEXT NOT NULL,
        aula_taller TEXT NOT NULL,
        tipo_programa TEXT NOT NULL,
        programa TEXT NOT NULL,
        nivel_academico TEXT NOT NULL,
        tipo_ingreso TEXT NOT NULL,
        fecha_registro TEXT NOT NULL,
        registrado_por TEXT,
        titularidad TEXT,
        procedencia_especializacion TEXT,
        cedula_especializacion TEXT,
        cedula_maestria TEXT,
        pdf_path TEXT
    )""")

    # --- Notas ---
    c.execute("""CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        uc TEXT NOT NULL,
        calificacion TEXT NOT NULL,
        calificacion_letras TEXT,
        credito INTEGER NOT NULL,
        semestre TEXT NOT NULL,
        fecha_registro TEXT NOT NULL,
        registrado_por TEXT,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
    )""")

    # --- Certificaciones emitidas ---
    c.execute("""CREATE TABLE IF NOT EXISTS certificaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        tipo_certificacion TEXT NOT NULL,
        nivel_academico TEXT NOT NULL,
        fecha_emision TEXT NOT NULL,
        emitida_por TEXT,
        hash_verificacion TEXT,
        FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id)
    )""")

    # --- Configuración de listas (programas dinámicos) ---
    c.execute("""CREATE TABLE IF NOT EXISTS config_listas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_programa TEXT NOT NULL,
        programa TEXT NOT NULL,
        fecha_creacion TEXT NOT NULL
    )""")

    # --- Apertura/Cierre de notas ---
    c.execute("""CREATE TABLE IF NOT EXISTS aperturas_notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nivel_apertura TEXT NOT NULL DEFAULT 'plantel',
        estado TEXT NOT NULL,
        municipio TEXT NOT NULL,
        aula_taller TEXT NOT NULL,
        tipo_programa TEXT,
        programa TEXT NOT NULL,
        semestre TEXT NOT NULL,
        abierto INTEGER DEFAULT 1,
        fecha_apertura TEXT,
        fecha_cierre TEXT,
        abierto_por TEXT
    )""")

    # --- Solicitudes de autorización (eliminar registro, etc.) ---
    c.execute("""CREATE TABLE IF NOT EXISTS solicitudes_autorizacion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_solicitud TEXT NOT NULL,
        solicitado_por TEXT NOT NULL,
        cedula_solicitante TEXT NOT NULL,
        rol_solicitante TEXT NOT NULL,
        estudiante_id INTEGER,
        estudiante_cedula TEXT,
        motivo TEXT,
        estado TEXT NOT NULL DEFAULT 'Pendiente',
        aprobado_por TEXT,
        fecha_solicitud TEXT NOT NULL,
        fecha_respuesta TEXT
    )""")

    # --- Registro de eliminaciones ---
    c.execute("""CREATE TABLE IF NOT EXISTS eliminaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER,
        estudiante_cedula TEXT,
        estudiante_nombre TEXT,
        eliminado_por TEXT,
        rol_eliminador TEXT,
        motivo TEXT,
        tipo_eliminacion TEXT NOT NULL DEFAULT 'directa',
        solicitud_id INTEGER,
        fecha_eliminacion TEXT NOT NULL
    )""")

    # --- Admin por defecto ---
    clave_admin = hashlib.sha256("admin123".encode()).hexdigest()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT COUNT(*) FROM usuarios WHERE cedula = 'admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO usuarios (nombre, cedula, clave, rol, estado, fecha_creacion) VALUES (?, ?, ?, ?, ?, ?)",
                  ("Administrador", "admin", clave_admin, "Admin Principal", "Activo", ahora))

    # --- Secretario por defecto ---
    clave_sec = hashlib.sha256("lenin123".encode()).hexdigest()
    c.execute("SELECT COUNT(*) FROM usuarios WHERE cedula = 'V-2.956.814'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO usuarios (nombre, cedula, clave, rol, estado, fecha_creacion) VALUES (?, ?, ?, ?, ?, ?)",
                  (SECRETARIO_NOMBRE, "V-2.956.814", clave_sec, "Secretaría General", "Activo", ahora))

    conn.commit()
    conn.close()


def hash_clave(clave):
    return hashlib.sha256(clave.encode()).hexdigest()


def verificar_login(cedula, clave):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, nombre, cedula, rol, estado FROM usuarios WHERE cedula = ? AND clave = ?",
              (cedula, hash_clave(clave)))
    row = c.fetchone()
    conn.close()
    return row


def cambiar_clave_usuario(cedula, clave_actual, clave_nueva):
    """Cambia la contraseña de un usuario. Retorna (True, msg) o (False, msg)"""
    if len(clave_nueva) < 8:
        return False, "La nueva contraseña debe tener al menos 8 caracteres."
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM usuarios WHERE cedula = ? AND clave = ?",
              (cedula, hash_clave(clave_actual)))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "Contraseña actual incorrecta."
    c.execute("UPDATE usuarios SET clave = ? WHERE cedula = ?",
              (hash_clave(clave_nueva), cedula))
    conn.commit()
    conn.close()
    return True, "Contraseña actualizada exitosamente."


def crear_usuario(nombre, cedula, clave, rol, estado):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios (nombre, cedula, clave, rol, estado, fecha_creacion) VALUES (?, ?, ?, ?, ?, ?)",
                  (nombre, cedula, hash_clave(clave), rol, estado, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def obtener_usuarios():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, nombre, cedula, rol, estado, fecha_creacion FROM usuarios ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows


def actualizar_estado_usuario(user_id, nuevo_estado):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET estado = ? WHERE id = ?", (nuevo_estado, user_id))
    conn.commit()
    conn.close()


def obtener_almacenes():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, nombre, estado, municipio, aula_taller FROM almacenes ORDER BY estado, municipio")
    rows = c.fetchall()
    conn.close()
    return rows


def crear_almacen(nombre, estado, municipio, aula_taller):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO almacenes (nombre, estado, municipio, aula_taller, fecha_creacion) VALUES (?, ?, ?, ?, ?)",
                  (nombre, estado, municipio, aula_taller, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def eliminar_almacen(almacen_id):
    """Elimina un almacén/aula taller por su ID"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM almacenes WHERE id = ?", (almacen_id,))
        conn.commit()
        eliminado = c.rowcount > 0
        conn.close()
        return eliminado
    except Exception:
        conn.close()
        return False


def obtener_almacenes_filtro(estado="", municipio="", busqueda=""):
    """Obtiene almacenes filtrados por estado, municipio y/o nombre de aula"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = "SELECT id, nombre, estado, municipio, aula_taller FROM almacenes WHERE 1=1"
    params = []
    if estado:
        query += " AND estado = ?"
        params.append(estado)
    if municipio:
        query += " AND municipio = ?"
        params.append(municipio)
    if busqueda:
        query += " AND (nombre LIKE ? OR aula_taller LIKE ?)"
        params.append(f"%{busqueda}%")
        params.append(f"%{busqueda}%")
    query += " ORDER BY estado, municipio, nombre"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


def obtener_programas(tipo_programa):
    """Obtiene la lista de programas para un tipo, incluyendo los dinámicos de config_listas"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Programas por defecto
    por_defecto = PROGRAMAS_POR_DEFECTO.get(tipo_programa, [])
    # Programas dinámicos
    c.execute("SELECT programa FROM config_listas WHERE tipo_programa = ? ORDER BY programa", (tipo_programa,))
    dinamicos = [row[0] for row in c.fetchall()]
    conn.close()
    # Combinar sin duplicados
    todos = list(por_defecto)
    for p in dinamicos:
        if p not in todos:
            todos.append(p)
    return todos


def agregar_programa_lista(tipo_programa, programa):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO config_listas (tipo_programa, programa, fecha_creacion) VALUES (?, ?, ?)",
                  (tipo_programa, programa, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def eliminar_programa_lista(programa_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM config_listas WHERE id = ?", (programa_id,))
    conn.commit()
    conn.close()


def obtener_todos_programas_config():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, tipo_programa, programa FROM config_listas ORDER BY tipo_programa, programa")
    rows = c.fetchall()
    conn.close()
    return rows


# --- Funciones de Estudiantes ---

def registrar_estudiante(datos):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO estudiantes 
            (cedula, apellidos, nombres, sexo, fecha_nacimiento, lugar_nacimiento, 
             estado, municipio, aula_taller, tipo_programa, programa, nivel_academico, 
             tipo_ingreso, fecha_registro, registrado_por, titularidad, 
             procedencia_especializacion, cedula_especializacion, cedula_maestria, pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (datos["cedula"], datos["apellidos"], datos["nombres"], datos["sexo"],
                   datos.get("fecha_nacimiento", ""), datos.get("lugar_nacimiento", ""),
                   datos["estado"], datos["municipio"], datos["aula_taller"],
                   datos["tipo_programa"], datos["programa"], datos["nivel_academico"],
                   datos["tipo_ingreso"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   datos.get("registrado_por", ""), datos.get("titularidad", ""),
                   datos.get("procedencia_especializacion", ""),
                   datos.get("cedula_especializacion", ""),
                   datos.get("cedula_maestria", ""), datos.get("pdf_path", "")))
        conn.commit()
        est_id = c.lastrowid
        conn.close()
        return True, est_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, None


def buscar_estudiante(cedula):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, cedula, apellidos, nombres, sexo, fecha_nacimiento, lugar_nacimiento,
                       estado, municipio, aula_taller, tipo_programa, programa, nivel_academico,
                       tipo_ingreso, fecha_registro, titularidad, procedencia_especializacion,
                       cedula_especializacion, cedula_maestria
                FROM estudiantes WHERE cedula = ?""", (cedula,))
    row = c.fetchone()
    conn.close()
    return row


def obtener_estudiantes_filtro(estado="", municipio="", aula_taller="", programa=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = """SELECT id, cedula, apellidos, nombres, sexo, estado, municipio, aula_taller,
                      tipo_programa, programa, nivel_academico, tipo_ingreso, titularidad
               FROM estudiantes WHERE 1=1"""
    params = []
    if estado:
        query += " AND estado = ?"
        params.append(estado)
    if municipio:
        query += " AND municipio = ?"
        params.append(municipio)
    if aula_taller:
        query += " AND aula_taller = ?"
        params.append(aula_taller)
    if programa:
        query += " AND programa = ?"
        params.append(programa)
    query += " ORDER BY apellidos, nombres"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows


# --- Funciones de Notas ---

def registrar_nota(estudiante_id, uc, calificacion, calificacion_letras, credito, semestre, registrado_por):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Verificar si la nota ya existe
    c.execute("SELECT id FROM notas WHERE estudiante_id = ? AND uc = ? AND semestre = ?",
              (estudiante_id, uc, semestre))
    if c.fetchone():
        # Actualizar nota existente
        c.execute("""UPDATE notas SET calificacion = ?, calificacion_letras = ?, credito = ?, 
                    fecha_registro = ?, registrado_por = ?
                    WHERE estudiante_id = ? AND uc = ? AND semestre = ?""",
                  (calificacion, calificacion_letras, credito,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"), registrado_por,
                   estudiante_id, uc, semestre))
    else:
        c.execute("""INSERT INTO notas (estudiante_id, uc, calificacion, calificacion_letras, credito, semestre, fecha_registro, registrado_por)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (estudiante_id, uc, calificacion, calificacion_letras, credito, semestre,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"), registrado_por))
    conn.commit()
    conn.close()


def obtener_notas_estudiante(estudiante_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, uc, calificacion, calificacion_letras, credito, semestre, fecha_registro 
                FROM notas WHERE estudiante_id = ? ORDER BY semestre""", (estudiante_id,))
    rows = c.fetchall()
    conn.close()
    return rows


# --- Funciones de Apertura/Cierre de Notas ---

def verificar_apertura(estado, municipio, aula_taller, programa, semestre):
    """Verifica si el período está abierto. Chequea en orden: nacional → estadal → municipal → plantel."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 1) Apertura NACIONAL (estado='TODOS')
    c.execute("""SELECT abierto FROM aperturas_notas
                WHERE nivel_apertura = 'nacional' AND estado = 'TODOS'
                AND programa = ? AND semestre = ?""",
              (programa, semestre))
    row = c.fetchone()
    if row is not None:
        conn.close()
        return bool(row[0])

    # 2) Apertura ESTADAL
    c.execute("""SELECT abierto FROM aperturas_notas
                WHERE nivel_apertura = 'estadal' AND estado = ?
                AND municipio = 'TODOS'
                AND programa = ? AND semestre = ?""",
              (estado, programa, semestre))
    row = c.fetchone()
    if row is not None:
        conn.close()
        return bool(row[0])

    # 3) Apertura MUNICIPAL
    c.execute("""SELECT abierto FROM aperturas_notas
                WHERE nivel_apertura = 'municipal' AND estado = ? AND municipio = ?
                AND aula_taller = 'TODOS'
                AND programa = ? AND semestre = ?""",
              (estado, municipio, programa, semestre))
    row = c.fetchone()
    if row is not None:
        conn.close()
        return bool(row[0])

    # 4) Apertura POR PLANTEL
    c.execute("""SELECT abierto FROM aperturas_notas
                WHERE nivel_apertura = 'plantel' AND estado = ? AND municipio = ?
                AND aula_taller = ? AND programa = ? AND semestre = ?""",
              (estado, municipio, aula_taller, programa, semestre))
    row = c.fetchone()
    if row is not None:
        conn.close()
        return bool(row[0])

    conn.close()
    return True  # Si no hay registro de cierre, se asume abierto


def establecer_apertura(nivel_apertura, estado, municipio, aula_taller, tipo_programa, programa, semestre, abierto, usuario):
    """Establece apertura/cierre según nivel: nacional, estadal, municipal, plantel."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Para búsqueda, usamos los valores 'TODOS' según nivel
    estado_val = estado if nivel_apertura in ("estadal", "municipal", "plantel") else "TODOS"
    municipio_val = municipio if nivel_apertura in ("municipal", "plantel") else "TODOS"
    aula_val = aula_taller if nivel_apertura == "plantel" else "TODOS"

    c.execute("""SELECT id FROM aperturas_notas
                WHERE nivel_apertura = ? AND estado = ? AND municipio = ? AND aula_taller = ?
                AND tipo_programa = ? AND programa = ? AND semestre = ?""",
              (nivel_apertura, estado_val, municipio_val, aula_val, tipo_programa, programa, semestre))
    row = c.fetchone()
    if row:
        if abierto:
            c.execute("""UPDATE aperturas_notas SET abierto = 1, fecha_apertura = ?, abierto_por = ?
                        WHERE id = ?""", (ahora, usuario, row[0]))
        else:
            c.execute("""UPDATE aperturas_notas SET abierto = 0, fecha_cierre = ?
                        WHERE id = ?""", (ahora, row[0]))
    else:
        c.execute("""INSERT INTO aperturas_notas (nivel_apertura, estado, municipio, aula_taller, tipo_programa, programa, semestre, abierto, fecha_apertura, abierto_por)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (nivel_apertura, estado_val, municipio_val, aula_val, tipo_programa, programa, semestre, 1 if abierto else 0, ahora, usuario))
    conn.commit()
    conn.close()


# --- Funciones de Certificaciones ---

def registrar_certificacion(estudiante_id, tipo, nivel, emitida_por, hash_ver):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT INTO certificaciones (estudiante_id, tipo_certificacion, nivel_academico, fecha_emision, emitida_por, hash_verificacion)
                VALUES (?, ?, ?, ?, ?, ?)""",
              (estudiante_id, tipo, nivel, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), emitida_por, hash_ver))
    conn.commit()
    conn.close()


def obtener_certificaciones(estudiante_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, tipo_certificacion, nivel_academico, fecha_emision, emitida_por, hash_verificacion
                FROM certificaciones WHERE estudiante_id = ? ORDER BY fecha_emision DESC""", (estudiante_id,))
    rows = c.fetchall()
    conn.close()
    return rows


# --- Funciones de Solicitudes de Autorización ---

def crear_solicitud_autorizacion(tipo_solicitud, solicitado_por, cedula_solicitante, rol_solicitante,
                                  estudiante_id=None, estudiante_cedula=None, motivo=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""INSERT INTO solicitudes_autorizacion
                (tipo_solicitud, solicitado_por, cedula_solicitante, rol_solicitante,
                 estudiante_id, estudiante_cedula, motivo, estado, fecha_solicitud)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente', ?)""",
              (tipo_solicitud, solicitado_por, cedula_solicitante, rol_solicitante,
               estudiante_id, estudiante_cedula, motivo, ahora))
    conn.commit()
    solicitud_id = c.lastrowid
    conn.close()
    return solicitud_id


def obtener_solicitudes_autorizacion(estado_filtro=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if estado_filtro:
        c.execute("""SELECT id, tipo_solicitud, solicitado_por, cedula_solicitante, rol_solicitante,
                           estudiante_id, estudiante_cedula, motivo, estado, aprobado_por,
                           fecha_solicitud, fecha_respuesta
                    FROM solicitudes_autorizacion WHERE estado = ? ORDER BY fecha_solicitud DESC""",
                  (estado_filtro,))
    else:
        c.execute("""SELECT id, tipo_solicitud, solicitado_por, cedula_solicitante, rol_solicitante,
                           estudiante_id, estudiante_cedula, motivo, estado, aprobado_por,
                           fecha_solicitud, fecha_respuesta
                    FROM solicitudes_autorizacion ORDER BY fecha_solicitud DESC""")
    rows = c.fetchall()
    conn.close()
    return rows


def responder_solicitud_autorizacion(solicitud_id, aprobado, aprobado_por):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nuevo_estado = "Aprobada" if aprobado else "Rechazada"
    c.execute("""UPDATE solicitudes_autorizacion SET estado = ?, aprobado_por = ?, fecha_respuesta = ?
                WHERE id = ?""",
              (nuevo_estado, aprobado_por, ahora, solicitud_id))
    conn.commit()
    conn.close()
    return nuevo_estado


# --- Funciones de Eliminación de Registros ---

def eliminar_estudiante(estudiante_id, eliminado_por, rol_eliminador, motivo, tipo_eliminacion="directa", solicitud_id=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Obtener datos del estudiante antes de eliminar
    c.execute("SELECT cedula, apellidos, nombres FROM estudiantes WHERE id = ?", (estudiante_id,))
    est = c.fetchone()
    if not est:
        conn.close()
        return False, "Estudiante no encontrado"
    est_cedula, est_apellidos, est_nombres = est
    est_nombre = f"{est_apellidos} {est_nombres}"
    # Registrar la eliminación
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""INSERT INTO eliminaciones
                (estudiante_id, estudiante_cedula, estudiante_nombre, eliminado_por, rol_eliminador,
                 motivo, tipo_eliminacion, solicitud_id, fecha_eliminacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (estudiante_id, est_cedula, est_nombre, eliminado_por, rol_eliminador,
               motivo, tipo_eliminacion, solicitud_id, ahora))
    # Eliminar notas del estudiante
    c.execute("DELETE FROM notas WHERE estudiante_id = ?", (estudiante_id,))
    # Eliminar certificaciones del estudiante
    c.execute("DELETE FROM certificaciones WHERE estudiante_id = ?", (estudiante_id,))
    # Eliminar estudiante
    c.execute("DELETE FROM estudiantes WHERE id = ?", (estudiante_id,))
    conn.commit()
    conn.close()
    return True, f"Estudiante {est_nombre} ({est_cedula}) eliminado correctamente"


def obtener_eliminaciones():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, estudiante_cedula, estudiante_nombre, eliminado_por, rol_eliminador,
                       motivo, tipo_eliminacion, solicitud_id, fecha_eliminacion
                FROM eliminaciones ORDER BY fecha_eliminacion DESC""")
    rows = c.fetchall()
    conn.close()
    return rows


def obtener_aperturas_notas():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, nivel_apertura, estado, municipio, aula_taller, tipo_programa,
                       programa, semestre, abierto, fecha_apertura, fecha_cierre, abierto_por
                FROM aperturas_notas ORDER BY fecha_apertura DESC""")
    rows = c.fetchall()
    conn.close()
    return rows


# --- Consulta read-only Etapa 1 ---

def consultar_expediente_etapa1(cedula):
    """Consulta read-only a la base de datos de Etapa 1 (expedientes.db)"""
    if not os.path.exists(DB_FILE_ETAPA1):
        return None, "Base de datos de Etapa 1 no encontrada."
    try:
        conn = sqlite3.connect(DB_FILE_ETAPA1)
        c = conn.cursor()
        # Intentar buscar en

        # Intentar buscar en tabla 'expedientes' o 'estudiantes'
        # Primero verificar qué tablas existen
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = [row[0] for row in c.fetchall()]
        
        tabla_dest = None
        if "expedientes" in tablas:
            tabla_dest = "expedientes"
        elif "estudiantes" in tablas:
            tabla_dest = "estudiantes"
        else:
            conn.close()
            return None, f"No se encontró tabla de expedientes en Etapa 1. Tablas: {tablas}"
        
        # Verificar columnas
        c.execute(f"PRAGMA table_info({tabla_dest})")
        columnas = [row[1] for row in c.fetchall()]
        
        # Construir SELECT con las columnas disponibles
        campos_disponibles = []
        for col in ["cedula", "apellidos", "nombres", "sexo", "fecha_nacimiento", 
                     "estado", "municipio", "programa", "tipo_programa", "nivel_academico",
                     "fecha_registro", "aula_taller", "tipo_ingreso"]:
            if col in columnas:
                campos_disponibles.append(col)
        
        if "cedula" not in campos_disponibles:
            conn.close()
            return None, "La tabla no tiene columna 'cedula'."
        
        select_sql = ", ".join(campos_disponibles)
        c.execute(f"SELECT {select_sql} FROM {tabla_dest} WHERE cedula = ?", (cedula,))
        row = c.fetchone()
        conn.close()
        
        if row:
            datos = dict(zip(campos_disponibles, row))
            return datos, None
        else:
            return None, "No se encontró expediente en Etapa 1."
    except Exception as e:
        return None, f"Error al consultar Etapa 1: {str(e)}"



# ============================================================
# CONVERSIÓN NÚMERO A LETRAS
# ============================================================

def numero_a_letras(numero):
    """Convierte un número entero (1-20) a su equivalente en letras"""
    mapa = {
        1: "UNO", 2: "DOS", 3: "TRES", 4: "CUATRO", 5: "CINCO",
        6: "SEIS", 7: "SIETE", 8: "OCHO", 9: "NUEVE", 10: "DIEZ",
        11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE", 15: "QUINCE",
        16: "DIECISÉIS", 17: "DIECISIETE", 18: "DIECIOCHO", 19: "DIECINUEVE",
        20: "VEINTE"
    }
    try:
        n = int(numero)
        return mapa.get(n, str(n))
    except (ValueError, TypeError):
        return str(numero)


def calificacion_a_letras(cal):
    """Convierte calificación (número 1-20 o especial AP/AC/RE) a letras"""
    if cal in CALIFICACIONES_ESPECIALES:
        mapa_especiales = {"AP": "APROBADO", "AC": "ACREDITADO", "RE": "REPROBADO"}
        return mapa_especiales.get(cal, cal)
    try:
        n = int(cal)
        if 1 <= n <= 20:
            return f"({numero_a_letras(n)})"
        return str(cal)
    except (ValueError, TypeError):
        return str(cal)


# ============================================================
# GENERACIÓN DE PDF - CERTIFICACIÓN DE CALIFICACIONES
# ============================================================

def generar_certificacion_pdf(estudiante_data, notas_data, nivel_academico, tipo_cert="completa"):
    """Genera PDF de certificación de calificaciones (2 páginas con barcode, QR, firma)"""
    
    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=letter)
    
    # Dimensiones
    w, h = letter
    margin_left = 1.2 * cm
    margin_right = 1.2 * cm
    margin_top = 1.5 * cm
    margin_bottom = 1.5 * cm
    
    # Colores
    azul_oscuro = HexColor("#1a237e")
    azul_medio = HexColor("#283593")
    rojo_unem = HexColor("#b71c1c")
    gris_claro = HexColor("#eeeeee")
    gris_oscuro = HexColor("#424242")
    
    # ---- PÁGINA 1 ----
    
    # Encabezado institucional
    c.setFillColor(azul_oscuro)
    c.rect(0, h - 3.5*cm, w, 3.5*cm, fill=1, stroke=0)
    
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w/2, h - 1.2*cm, "REPÚBLICA BOLIVARIANA DE VENEZUELA")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(w/2, h - 1.8*cm, "UNIVERSIDAD NACIONAL EXPERIMENTAL DEL MAGISTERIO")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w/2, h - 2.3*cm, '"SAMUEL ROBINSON"')
    c.setFont("Helvetica", 9)
    c.drawCentredString(w/2, h - 2.8*cm, "DIRECCIÓN DE REGISTRO ACADÉMICO")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(w/2, h - 3.2*cm, "CERTIFICACIÓN DE CALIFICACIONES")
    
    # Línea decorativa
    c.setStrokeColor(rojo_unem)
    c.setLineWidth(2)
    c.line(margin_left, h - 3.7*cm, w - margin_right, h - 3.7*cm)
    
    # Datos del estudiante
    y = h - 4.5*cm
    c.setFillColor(gris_oscuro)
    c.setFont("Helvetica-Bold", 10)
    
    titularidad = estudiante_data.get("titularidad", "")
    tipo_prog = estudiante_data.get("tipo_programa", "PNF")
    
    # Construir encabezado del estudiante según nivel
    if tipo_prog.startswith("PNFA"):
        linea_nombre = f"{titularidad}: {estudiante_data['nombres']} {estudiante_data['apellidos']}"
    else:
        if titularidad:
            linea_nombre = f"{titularidad}: {estudiante_data['nombres']} {estudiante_data['apellidos']}"
        else:
            linea_nombre = f"CIUDADANO(A): {estudiante_data['nombres']} {estudiante_data['apellidos']}"
    
    c.drawString(margin_left + 0.3*cm, y, "CÉDULA DE IDENTIDAD:")
    c.setFont("Helvetica", 10)
    c.drawString(margin_left + 5.5*cm, y, estudiante_data["cedula"])
    y -= 0.6*cm
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin_left + 0.3*cm, y, linea_nombre[:80])
    y -= 0.6*cm
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_left + 0.3*cm, y, "PROGRAMA:")
    c.setFont("Helvetica", 9)
    c.drawString(margin_left + 3*cm, y, estudiante_data["programa"])
    y -= 0.5*cm
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_left + 0.3*cm, y, "NIVEL ACADÉMICO:")
    c.setFont("Helvetica", 9)
    c.drawString(margin_left + 5*cm, y, nivel_academico)
    y -= 0.5*cm
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin_left + 0.3*cm, y, "SEDE:")
    c.setFont("Helvetica", 9)
    c.drawString(margin_left + 2*cm, y, f"{estudiante_data['estado']} / {estudiante_data['municipio']} / {estudiante_data['aula_taller']}")
    y -= 0.8*cm
    
    # Tabla de calificaciones
    # Encabezado de tabla
    c.setFillColor(azul_medio)
    c.rect(margin_left, y - 0.5*cm, w - margin_left - margin_right, 0.5*cm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    
    col_positions = [margin_left + 0.2*cm, margin_left + 0.8*cm, w - margin_right - 6*cm,
                     w - margin_right - 3*cm, w - margin_right - 1.5*cm, w - margin_right - 0.5*cm]
    headers = ["#", "ASIGNATURA / UC", "CALIFICACIÓN", "EN LETRAS", "UC", "CRÉDITOS"]
    
    # Simplified 4-column layout
    col_positions = [margin_left + 0.3*cm, margin_left + 1*cm, w - margin_right - 5*cm,
                     w - margin_right - 2.5*cm, w - margin_right - 1*cm]
    headers = ["#", "UNIDAD CURRICULAR", "CALIF.", "LETRAS", "CRÉD."]
    
    for i, header in enumerate(headers):
        c.drawString(col_positions[i], y - 0.35*cm, header)
    y -= 0.6*cm
    
    # Filas de notas
    c.setFont("Helvetica", 7)
    semestre_actual = ""
    fila = 0
    max_filas_pag1 = 20
    notas_pag1 = []
    notas_pag2 = []
    
    for nota in notas_data:
        # nota: (id, uc, calificacion, calificacion_letras, credito, semestre, fecha_registro)
        sem = nota[5]
        if sem != semestre_actual:
            semestre_actual = sem
            notas_pag1.append(("", sem, "", "", "", ""))  # Separador de semestre
        notas_pag1.append(nota)
    
    # Si hay más de max_filas, dividir
    if len(notas_pag1) > max_filas_pag1:
        notas_pag2 = notas_pag1[max_filas_pag1:]
        notas_pag1 = notas_pag1[:max_filas_pag1]
    
    for nota in notas_pag1:
        fila += 1
        if fila > max_filas_pag1:
            break
        
        # Fila alternada
        if fila % 2 == 0:
            c.setFillColor(gris_claro)
            c.rect(margin_left, y - 0.4*cm, w - margin_left - margin_right, 0.4*cm, fill=1, stroke=0)
        
        c.setFillColor(black)
        c.setFont("Helvetica", 7)
        
        # Si es separador de semestre
        if nota[0] == "" and nota[1] != "":
            c.setFont("Helvetica-Bold", 8)
            c.drawString(margin_left + 0.3*cm, y - 0.28*cm, nota[1])
            y -= 0.45*cm
            continue
        
        # Dibujar fila de nota
        c.drawString(col_positions[0], y - 0.28*cm, str(fila))
        # Truncar UC si es muy larga
        uc_text = nota[1][:60] + "..." if len(nota[1]) > 60 else nota[1]
        c.drawString(col_positions[1], y - 0.28*cm, uc_text)
        c.drawString(col_positions[2], y - 0.28*cm, str(nota[2]))
        cal_letras = nota[3] if nota[3] else calificacion_a_letras(nota[2])
        c.drawString(col_positions[3], y - 0.28*cm, cal_letras[:25])
        c.drawString(col_positions[4], y - 0.28*cm, str(nota[4]))
        y -= 0.4*cm
    
    # Pie de página 1 - Datos del secretario
    y_pie = margin_bottom + 3*cm
    c.setFont("Helvetica", 8)
    c.setFillColor(gris_oscuro)
    c.drawString(margin_left + 0.3*cm, y_pie + 2*cm, f"Certificación emitada conforme a Gaceta No. {GACETA_NUM}")
    c.drawString(margin_left + 0.3*cm, y_pie + 1.5*cm, f"Resolución Conjunta No. {RESOLUCION_NUM}")
    
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(w/2, y_pie + 0.5*cm, SECRETARIO_NOMBRE)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w/2, y_pie, f"C.I. {SECRETARIO_CEDULA}")
    c.setFont("Helvetica", 7)
    c.drawCentredString(w/2, y_pie - 0.4*cm, "Secretario General")
    
    # Barcode (Code128) de la cédula
    try:
        barcode_buffer = BytesIO()
        barcode = Code128(estudiante_data["cedula"].replace("-", "").replace(".", ""), writer=ImageWriter())
        barcode.write(barcode_buffer)
        barcode_buffer.seek(0)
        barcode_img = ImageReader(barcode_buffer)
        c.drawImage(barcode_img, margin_left, margin_bottom, width=5*cm, height=1*cm)
    except Exception:
        c.setFont("Helvetica", 7)
        c.drawString(margin_left, margin_bottom + 0.3*cm, f"Cód: {estudiante_data['cedula']}")
    
    # QR con hash de verificación
    hash_ver = hashlib.sha256(f"{estudiante_data['cedula']}|{datetime.now().isoformat()}|{tipo_cert}".encode()).hexdigest()[:16]
    try:
        qr = qrcode.make(hash_ver)
        qr_buffer = BytesIO()
        qr.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        qr_img = ImageReader(qr_buffer)
        c.drawImage(qr_img, w - margin_right - 2*cm, margin_bottom, width=2*cm, height=2*cm)
    except Exception:
        pass
    
    # Número de página
    c.setFont("Helvetica", 7)
    c.drawCentredString(w/2, margin_bottom - 0.5*cm, "Página 1 de 2")
    
    # ---- PÁGINA 2 ----
    c.showPage()
    
    # Encabezado simplificado página 2
    c.setFillColor(azul_oscuro)
    c.rect(0, h - 2*cm, w, 2*cm, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w/2, h - 0.8*cm, "CERTIFICACIÓN DE CALIFICACIONES (Continuación)")
    c.setFont("Helvetica", 8)
    c.drawCentredString(w/2, h - 1.5*cm, f"C.I.: {estudiante_data['cedula']} - {estudiante_data['apellidos']}, {estudiante_data['nombres']}")
    
    y = h - 3*cm
    
    if notas_pag2:
        # Repetir encabezado de tabla
        c.setFillColor(azul_medio)
        c.rect(margin_left, y - 0.5*cm, w - margin_left - margin_right, 0.5*cm, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        for i, header in enumerate(headers):
            c.drawString(col_positions[i], y - 0.35*cm, header)
        y -= 0.6*cm
        
        fila_continua = max_filas_pag1
        for nota in notas_pag2:
            fila_continua += 1
            
            if fila_continua % 2 == 0:
                c.setFillColor(gris_claro)
                c.rect(margin_left, y - 0.4*cm, w - margin_left - margin_right, 0.4*cm, fill=1, stroke=0)
            
            c.setFillColor(black)
            c.setFont("Helvetica", 7)
            
            if nota[0] == "" and nota[1] != "":
                c.setFont("Helvetica-Bold", 8)
                c.drawString(margin_left + 0.3*cm, y - 0.28*cm, nota[1])
                y -= 0.45*cm
                continue
            
            c.drawString(col_positions[0], y - 0.28*cm, str(fila_continua))
            uc_text = nota[1][:60] + "..." if len(nota[1]) > 60 else nota[1]
            c.drawString(col_positions[1], y - 0.28*cm, uc_text)
            c.drawString(col_positions[2], y - 0.28*cm, str(nota[2]))
            cal_letras = nota[3] if nota[3] else calificacion_a_letras(nota[2])
            c.drawString(col_positions[3], y - 0.28*cm, cal_letras[:25])
            c.drawString(col_positions[4], y - 0.28*cm, str(nota[4]))
            y -= 0.4*cm
    else:
        c.setFont("Helvetica", 10)
        c.setFillColor(gris_oscuro)
        c.drawCentredString(w/2, y, "(Continúa en página siguiente si aplica)")
    
    # Resumen de créditos y promedio
    y_resumen = max(y - 1*cm, margin_bottom + 6*cm)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(azul_oscuro)
    c.drawString(margin_left + 0.3*cm, y_resumen, "RESUMEN ACADÉMICO")
    y_resumen -= 0.5*cm
    
    total_creditos = 0
    total_uc = len(notas_data)
    notas_numericas = []
    for nota in notas_data:
        total_creditos += nota[4]  # credito
        try:
            n = int(nota[2])
            notas_numericas.append(n)
        except (ValueError, TypeError):
            pass
    
    promedio = sum(notas_numericas) / len(notas_numericas) if notas_numericas else 0
    
    c.setFont("Helvetica", 9)
    c.setFillColor(black)
    c.drawString(margin_left + 0.3*cm, y_resumen, f"Total Unidades Curriculares: {total_uc}")
    y_resumen -= 0.4*cm
    c.drawString(margin_left + 0.3*cm, y_resumen, f"Total Créditos: {total_creditos}")
    y_resumen -= 0.4*cm
    if promedio > 0:
        c.drawString(margin_left + 0.3*cm, y_resumen, f"Promedio Ponderado: {promedio:.2f}")
    
    # Firma del Secretario (líneas y nombre)
    y_firma = margin_bottom + 4*cm
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(w/2 - 4*cm, y_firma, w/2 + 4*cm, y_firma)
    
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(w/2, y_firma - 0.5*cm, SECRETARIO_NOMBRE)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w/2, y_firma - 1*cm, f"C.I. {SECRETARIO_CEDULA}")
    c.setFont("Helvetica", 7)
    c.drawCentredString(w/2, y_firma - 1.4*cm, "Secretario General")
    c.drawCentredString(w/2, y_firma - 1.8*cm, f"Gaceta No. {GACETA_NUM} / Resolución Conjunta No. {RESOLUCION_NUM}")
    
    # Sello de agua - "DOCUMENTO OFICIAL"
    c.saveState()
    c.setFillColor(HexColor("#e0e0e0"))
    c.setFont("Helvetica-Bold", 40)
    c.translate(w/2, h/2)
    c.rotate(45)
    c.drawCentredString(0, 0, "DOCUMENTO OFICIAL")
    c.restoreState()
    
    # Hash de verificación en la parte inferior
    c.setFont("Helvetica", 6)
    c.setFillColor(gris_oscuro)
    c.drawCentredString(w/2, margin_bottom, f"Hash de Verificación: {hash_ver}")
    c.drawCentredString(w/2, margin_bottom - 0.4*cm, "Página 2 de 2")
    
    c.save()
    buffer.seek(0)
    return buffer, hash_ver


def generar_certificacion_lote(estudiantes_ids, nivel_academico, tipo_cert="completa"):
    """Genera un ZIP con certificaciones PDF individuales para múltiples estudiantes"""
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for est_id in estudiantes_ids:
            est_data = buscar_estudiante_por_id(est_id)
            if est_data:
                notas = obtener_notas_estudiante(est_id)
                if notas:
                    pdf_buffer, _ = generar_certificacion_pdf(est_data, notas, nivel_academico, tipo_cert)
                    filename = f"Cert_{est_data['cedula'].replace('-','').replace('.','')}_{nivel_academico}.pdf"
                    zf.writestr(filename, pdf_buffer.getvalue())
    zip_buffer.seek(0)
    return zip_buffer


def buscar_estudiante_por_id(est_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT id, cedula, apellidos, nombres, sexo, fecha_nacimiento, lugar_nacimiento,
                       estado, municipio, aula_taller, tipo_programa, programa, nivel_academico,
                       tipo_ingreso, fecha_registro, titularidad
                FROM estudiantes WHERE id = ?""", (est_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "cedula": row[1], "apellidos": row[2], "nombres": row[3],
            "sexo": row[4], "fecha_nacimiento": row[5], "lugar_nacimiento": row[6],
            "estado": row[7], "municipio": row[8], "aula_taller": row[9],
            "tipo_programa": row[10], "programa": row[11], "nivel_academico": row[12],
            "tipo_ingreso": row[13], "fecha_registro": row[14], "titularidad": row[15]
        }
    return None



# ============================================================
# CONFIGURACIÓN DE STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Expedientes UNEM",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Ocultar barra de herramientas de Streamlit (logo gato, compartir, editar, GitHub) ---
hide_streamlit_style = """
<style>
/* Ocultar el menú hamburguesa y la barra de herramientas superior */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
/* Ocultar el footer de Streamlit */
footer {visibility: hidden;}
/* Ocultar boton de deploy/compartir */
.stDeployButton {visibility: hidden;}
/* Eliminar espacio vacio arriba */
.block-container {padding-top: 1rem;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Inicializar DB
init_db()

# Inicializar session_state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.user_rol = None

# ============================================================
# PANTALLA DE LOGIN
# ============================================================

def mostrar_login():
    st.markdown("""
    <div style='text-align: center; padding: 2rem;'>
        <h1 style='color: #1a237e;'>📚 Expedientes UNEM</h1>
        <h3 style='color: #424242;'>Sistema de Gestión de Expedientes Estudiantiles</h3>
        <p style='color: #757575;'>Universidad Nacional Experimental del Magisterio "Samuel Robinson"</p>
        <p style='color: #b71c1c; font-weight: bold;'>ETAPA 2 - Certificaciones de Calificaciones</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            cedula = st.text_input("Cédula de Identidad", placeholder="Ej: V-12.345.678")
            clave = st.text_input("Contraseña", type="password", placeholder="Mínimo 8 caracteres")
            submitted = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submitted:
                if not cedula or not clave:
                    st.error("⚠️ Debe ingresar cédula y contraseña.")
                else:
                    user = verificar_login(cedula, clave)
                    if user:
                        user_id, nombre, ced, rol, estado = user
                        if estado == "Activo":
                            st.session_state.logged_in = True
                            st.session_state.user_info = {"id": user_id, "nombre": nombre, "cedula": ced, "rol": rol}
                            st.session_state.user_rol = rol
                            st.rerun()
                        else:
                            st.error("⚠️ Su cuenta está inactiva. Contacte al administrador.")
                    else:
                        st.error("❌ Cédula o contraseña incorrecta.")
        
        st.info("💡 **Credenciales por defecto:**\n- Admin: `admin` / `admin123`\n- Secretaría: `V-2.956.814` / `lenin123`")


# ============================================================
# SIDEBAR - NAVEGACIÓN
# ============================================================

def mostrar_sidebar():
    rol = st.session_state.user_rol
    
    st.sidebar.markdown(f"### 👤 {st.session_state.user_info['nombre']}")
    st.sidebar.caption(f"📋 {st.session_state.user_info['cedula']} | {rol}")
    
    # Opciones según rol
    paginas = []
    
    # Todos los niveles
    paginas.append("📊 Dashboard")
    paginas.append("📝 Registrar Estudiante")
    paginas.append("🔍 Consultar Expediente")
    paginas.append("📖 Cargar Notas")
    paginas.append("📄 Certificaciones")
    
    # Nivel 2 y 3
    if rol in ["Secretaría General", "Secretaría Situada"]:
        paginas.append("📋 Listado de Estudiantes")
    
    # Solo Nivel 1
    if rol == "Admin Principal":
        paginas.append("👥 Gestión de Usuarios")
        paginas.append("🏫 Gestión de Almacenes")
        paginas.append("⚙️ Configuración de Listas")
        paginas.append("🔓 Apertura/Cierre de Notas")
        paginas.append("🗑️ Eliminar Registro")
        paginas.append("📋 Autorizaciones")
        paginas.append("🔎 Verificar Expediente Etapa 1")
    
    # Nivel 2 y 3
    if rol in ["Secretaría General", "Secretaría Situada"]:
        paginas.append("🗑️ Eliminar Registro")
        paginas.append("📋 Autorizaciones")
    
    # Todos los niveles - Respaldo
    paginas.append("💾 Respaldo y Exportación")
    
    paginas.append("🚪 Cerrar Sesión")
    
    pagina = st.sidebar.radio("Navegación", paginas, label_visibility="collapsed")
    return pagina



# ============================================================
# PÁGINA: DASHBOARD
# ============================================================

def pagina_dashboard():
    st.title("📊 Dashboard - Expedientes UNEM")
    st.markdown("---")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Estadísticas
    c.execute("SELECT COUNT(*) FROM estudiantes")
    total_est = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT estado) FROM estudiantes")
    total_estados = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT programa) FROM estudiantes")
    total_programas = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM certificaciones")
    total_cert = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM usuarios WHERE estado = 'Activo'")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM almacenes")
    total_alm = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM notas")
    total_notas = c.fetchone()[0]
    
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👨‍🎓 Estudiantes", total_est)
    with col2:
        st.metric("🏛️ Estados con Sedes", total_estados)
    with col3:
        st.metric("📚 Programas", total_programas)
    with col4:
        st.metric("📄 Certificaciones Emitidas", total_cert)
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("👥 Usuarios Activos", total_users)
    with col6:
        st.metric("🏫 Almacenes/Sedes", total_alm)
    with col7:
        st.metric("📝 Notas Registradas", total_notas)
    with col8:
        st.metric("🖥️ Etapa", "2")
    
    st.markdown("---")
    st.subheader("📈 Distribución por Programa")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT programa, COUNT(*) as cnt FROM estudiantes GROUP BY programa ORDER BY cnt DESC")
    prog_data = c.fetchall()
    conn.close()
    
    if prog_data:
        df_prog = pd.DataFrame(prog_data, columns=["Programa", "Cantidad"])
        st.dataframe(df_prog, use_container_width=True, hide_index=True)
    else:
        st.info("No hay estudiantes registrados aún.")


# ============================================================
# PÁGINA: REGISTRAR ESTUDIANTE
# ============================================================

def pagina_registrar_estudiante():
    st.title("📝 Registrar Estudiante")
    st.markdown("---")
    
    rol = st.session_state.user_rol
    usuario = st.session_state.user_info["nombre"]
    
    # ---- CAMPOS FUERA DEL FORM (cascada dinámica) ----
    # Los dropdowns que dependen de otros deben estar FUERA del st.form
    # para que se actualicen inmediatamente al cambiar la selección.
    
    st.subheader("📍 Ubicación y Programa")
    
    # --- Cascada Estado → Municipio → Aula Taller ---
    col_estado, col_municipio = st.columns(2)
    
    with col_estado:
        lista_estados = list(ESTADOS_MUNICIPIOS.keys())
        estado_sel = st.selectbox(
            "Estado *",
            options=lista_estados,
            index=lista_estados.index(st.session_state.get("reg_estado", lista_estados[0])) if st.session_state.get("reg_estado") in lista_estados else 0,
            key="reg_estado_widget"
        )
        # Guardar en session_state
        if st.session_state.get("reg_estado") != estado_sel:
            st.session_state["reg_estado"] = estado_sel
            st.session_state["reg_municipio"] = None  # Reset municipio
    
    with col_municipio:
        municipios = ESTADOS_MUNICIPIOS.get(estado_sel, [])
        mun_default = st.session_state.get("reg_municipio")
        mun_index = municipios.index(mun_default) if mun_default in municipios else 0
        municipio_sel = st.selectbox(
            "Municipio *",
            options=municipios,
            index=mun_index,
            key="reg_municipio_widget"
        )
        st.session_state["reg_municipio"] = municipio_sel
    
    # Aula Taller (cargar de almacenes)
    almacenes_lista = obtener_almacenes()
    aulas_disponibles = [f"{a[1]} ({a[2]}/{a[3]}/{a[4]})" for a in almacenes_lista if a[2] == estado_sel and a[3] == municipio_sel]
    if not aulas_disponibles:
        aulas_disponibles = ["No hay aulas disponibles - cree un almacén primero"]
    aula_sel = st.selectbox("Aula Taller *", options=aulas_disponibles, key="reg_aula_widget")
    st.session_state["reg_aula"] = aula_sel
    
    # --- Cascada Tipo de Programa → Programa ---
    col_tipo, col_prog = st.columns(2)
    
    with col_tipo:
        tipo_prog_sel = st.selectbox(
            "Tipo de Programa *",
            options=TIPOS_PROGRAMA,
            key="reg_tipo_programa_widget"
        )
        if st.session_state.get("reg_tipo_programa") != tipo_prog_sel:
            st.session_state["reg_tipo_programa"] = tipo_prog_sel
            st.session_state["reg_programa"] = None  # Reset programa
    
    with col_prog:
        programas = obtener_programas(tipo_prog_sel)
        prog_default = st.session_state.get("reg_programa")
        prog_index = programas.index(prog_default) if prog_default in programas else 0
        programa_sel = st.selectbox(
            "Programa *",
            options=programas,
            index=prog_index,
            key="reg_programa_widget"
        )
        st.session_state["reg_programa"] = programa_sel
    
    st.markdown("---")
    st.subheader("👤 Datos Personales")
    
    # ---- FORMULARIO (campos que no dependen de otros) ----
    with st.form("form_registrar_estudiante"):
        col_ced, col_sexo = st.columns(2)
        with col_ced:
            cedula = st.text_input("Cédula de Identidad *", placeholder="Ej: V-12.345.678")
        with col_sexo:
            sexo = st.selectbox("Sexo *", options=["M", "F"], format_func=lambda x: "Masculino" if x == "M" else "Femenino")
        
        apellidos = st.text_input("Apellidos *", placeholder="Apellidos del estudiante")
        nombres = st.text_input("Nombres *", placeholder="Nombres del estudiante")
        
        col_fnac, col_lnac = st.columns(2)
        with col_fnac:
            fecha_nacimiento = st.date_input("Fecha de Nacimiento", value=None)
        with col_lnac:
            lugar_nacimiento = st.text_input("Lugar de Nacimiento", placeholder="Ciudad, Estado")
        
        col_nivel, col_ingreso = st.columns(2)
        with col_nivel:
            # Nivel académico según tipo de programa
            if tipo_prog_sel == "PNF":
                nivel_opciones = NIVELES_ACADEMICOS  # ["BACHILLER", "TSU"]
            else:
                nivel_opciones = [NIVELES_PNFA.get(tipo_prog_sel, "ESPECIALISTA")]
            nivel_academico = st.selectbox("Nivel Académico *", options=nivel_opciones)
        with col_ingreso:
            tipo_ingreso = st.selectbox("Tipo de Ingreso *", options=TIPOS_INGRESO)
        
        # --- Campos condicionales PNFA ---
        cedula_especializacion = ""
        cedula_maestria = ""
        procedencia = ""
        
        if tipo_prog_sel == "PNFA_E":
            st.markdown("**📋 Requisito PNFA Especialización:**")
            procedencia = st.selectbox(
                "Proviene de PNF previo en UNEM o de otra institución",
                options=["PNF en UNEM", "Otra Institución"]
            )
            cedula_especializacion = st.text_input(
                "Cédula del Programa PNF de Origen (si aplica)",
                placeholder="Cédula del expediente PNF"
            )
        
        elif tipo_prog_sel == "PNFA_M":
            st.markdown("**📋 Requisito PNFA Maestría:** Se requiere Especialización registrada")
            cedula_especializacion = st.text_input(
                "Cédula de Especialización *",
                placeholder="Cédula del expediente de Especialización"
            )
        
        elif tipo_prog_sel == "PNFA_D":
            st.markdown("**📋 Requisito PNFA Doctorado:** Se requieren Especialización Y Maestría registradas")
            cedula_especializacion = st.text_input(
                "Cédula de Especialización *",
                placeholder="Cédula del expediente de Especialización"
            )
            cedula_maestria = st.text_input(
                "Cédula de Maestría *",
                placeholder="Cédula del expediente de Maestría"
            )
        
        # PDF de respaldo (opcional)
        pdf_file = st.file_uploader("📄 Documento PDF de respaldo (opcional, máx 5MB)", type=["pdf"])
        
        submitted = st.form_submit_button("✅ Registrar Estudiante", use_container_width=True)
        
        if submitted:
            # Validaciones
            errores = []
            if not cedula:
                errores.append("Cédula es obligatoria")
            if not apellidos:
                errores.append("Apellidos son obligatorios")
            if not nombres:
                errores.append("Nombres son obligatorios")
            if "No hay aulas" in aula_sel:
                errores.append("Debe existir un almacén/aula para esta ubicación")
            
            # Validar prerrequisitos PNFA
            if tipo_prog_sel == "PNFA_M" and not cedula_especializacion:
                errores.append("Se requiere cédula de Especialización para Maestría")
            if tipo_prog_sel == "PNFA_D":
                if not cedula_especializacion:
                    errores.append("Se requiere cédula de Especialización para Doctorado")
                if not cedula_maestria:
                    errores.append("Se requiere cédula de Maestría para Doctorado")
            
            # Verificar prerrequisitos en BD
            if tipo_prog_sel == "PNFA_M" and cedula_especializacion:
                est_esp = buscar_estudiante(cedula_especializacion)
                if not est_esp:
                    errores.append(f"No se encontró expediente de Especialización con cédula {cedula_especializacion}")
                elif est_esp[10] != "PNFA_E":  # tipo_programa
                    errores.append(f"La cédula {cedula_especializacion} no corresponde a una Especialización")
            
            if tipo_prog_sel == "PNFA_D":
                if cedula_especializacion:
                    est_esp = buscar_estudiante(cedula_especializacion)
                    if not est_esp:
                        errores.append(f"No se encontró expediente de Especialización con cédula {cedula_especializacion}")
                if cedula_maestria:
                    est_maest = buscar_estudiante(cedula_maestria)
                    if not est_maest:
                        errores.append(f"No se encontró expediente de Maestría con cédula {cedula_maestria}")
                    elif est_maest[10] != "PNFA_M":
                        errores.append(f"La cédula {cedula_maestria} no corresponde a una Maestría")
            
            if errores:
                for err in errores:
                    st.error(f"❌ {err}")
            else:
                # Calcular titularidad por género
                titularidad = calcular_titularidad(tipo_prog_sel, sexo)
                
                # Extraer nombre del aula del texto completo
                aula_nombre = aula_sel.split(" (")[0] if " (" in aula_sel else aula_sel
                
                # Procesar PDF si se subió
                pdf_path = ""
                if pdf_file:
                    if pdf_file.size > MAX_PDF_SIZE:
                        st.error("❌ El archivo PDF excede el tamaño máximo de 5MB.")
                        return
                    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', pdf_file.name)
                    pdf_path = os.path.join(UPLOAD_FOLDER, f"{cedula}_{safe_name}")
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_file.getbuffer())
                
                datos = {
                    "cedula": cedula,
                    "apellidos": apellidos.upper(),
                    "nombres": nombres.upper(),
                    "sexo": sexo,
                    "fecha_nacimiento": str(fecha_nacimiento) if fecha_nacimiento else "",
                    "lugar_nacimiento": lugar_nacimiento.upper() if lugar_nacimiento else "",
                    "estado": estado_sel,
                    "municipio": municipio_sel,
                    "aula_taller": aula_nombre,
                    "tipo_programa": tipo_prog_sel,
                    "programa": programa_sel,
                    "nivel_academico": nivel_academico,
                    "tipo_ingreso": tipo_ingreso,
                    "registrado_por": usuario,
                    "titularidad": titularidad,
                    "procedencia_especializacion": procedencia,
                    "cedula_especializacion": cedula_especializacion,
                    "cedula_maestria": cedula_maestria,
                    "pdf_path": pdf_path,
                }
                
                ok, est_id = registrar_estudiante(datos)
                if ok:
                    st.success(f"✅ Estudiante registrado exitosamente. ID: {est_id}")
                    if titularidad:
                        st.info(f"🎓 Titularidad asignada: **{titularidad}** (según sexo: {'Masculino' if sexo == 'M' else 'Femenino'})")
                    # Limpiar session_state de registro
                    for key in ["reg_estado", "reg_municipio", "reg_tipo_programa", "reg_programa"]:
                        st.session_state.pop(key, None)
                else:
                    st.error("❌ Error al registrar. Posible cédula duplicada.")




# ============================================================
# PÁGINA: CONSULTAR EXPEDIENTE
# ============================================================

def pagina_consultar_expediente():
    st.title("🔍 Consultar Expediente")
    st.markdown("---")
    
    cedula_buscar = st.text_input("Ingrese la Cédula del Estudiante", placeholder="Ej: V-12.345.678")
    
    if st.button("🔍 Buscar", type="primary"):
        if not cedula_buscar:
            st.warning("⚠️ Ingrese una cédula para buscar.")
            return
        
        est = buscar_estudiante(cedula_buscar)
        if est:
            est_id = est[0]
            titularidad = est[15] if len(est) > 15 else ""
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(f"📋 Expediente de {est[3]} {est[2]}")
                
                datos_mostrar = [
                    ("Cédula", est[1]),
                    ("Sexo", "Masculino" if est[4] == "M" else "Femenino"),
                    ("Fecha de Nacimiento", est[5]),
                    ("Lugar de Nacimiento", est[6]),
                    ("Estado", est[7]),
                    ("Municipio", est[8]),
                    ("Aula Taller", est[9]),
                    ("Tipo de Programa", est[10]),
                    ("Programa", est[11]),
                    ("Nivel Académico", est[12]),
                    ("Tipo de Ingreso", est[13]),
                    ("Fecha de Registro", est[14]),
                ]
                if titularidad:
                    datos_mostrar.insert(0, ("Titularidad", titularidad))
                
                for label, value in datos_mostrar:
                    if value:
                        st.markdown(f"**{label}:** {value}")
            
            with col2:
                st.subheader("📊 Notas Registradas")
                notas = obtener_notas_estudiante(est_id)
                if notas:
                    df_notas = pd.DataFrame(notas, columns=["ID", "Unidad Curricular", "Calificación", "En Letras", "Créditos", "Semestre", "Fecha"])
                    # Mostrar según nivel
                    tipo_prog = est[10]
                    nivel = est[12]
                    
                    if tipo_prog == "PNF" and nivel == "TSU":
                        # TSU: solo Tercer Trayecto+
                        df_notas = df_notas[df_notas["Semestre"].str.contains("Tercer|Cuarto", na=False)]
                    
                    st.dataframe(df_notas[["Unidad Curricular", "Calificación", "En Letras", "Créditos", "Semestre"]], 
                                use_container_width=True, hide_index=True)
                else:
                    st.info("No hay notas registradas para este estudiante.")
        else:
            st.error("❌ No se encontró expediente con esa cédula.")


# ============================================================
# PÁGINA: CARGAR NOTAS
# ============================================================

def pagina_cargar_notas():
    st.title("📖 Cargar Notas")
    st.markdown("---")
    
    rol = st.session_state.user_rol
    usuario = st.session_state.user_info["nombre"]
    
    # Buscar estudiante
    cedula_buscar = st.text_input("Cédula del Estudiante", placeholder="Ej: V-12.345.678")
    
    if st.button("🔍 Buscar Estudiante"):
        if not cedula_buscar:
            st.warning("⚠️ Ingrese una cédula.")
            return
        
        est = buscar_estudiante(cedula_buscar)
        if est:
            est_id = est[0]
            st.session_state["nota_est_id"] = est_id
            st.session_state["nota_est_info"] = est
            st.success(f"✅ Estudiante encontrado: {est[3]} {est[2]}")
        else:
            st.error("❌ Estudiante no encontrado.")
            return
    
    # Si hay estudiante seleccionado
    if "nota_est_id" in st.session_state:
        est_id = st.session_state["nota_est_id"]
        est_info = st.session_state.get("nota_est_info")
        
        if est_info:
            tipo_prog = est_info[10]
            programa = est_info[11]
            nivel = est_info[12]
            estado_est = est_info[7]
            municipio_est = est_info[8]
            aula_est = est_info[9]
            
            st.subheader(f"📝 Cargando notas para: {est_info[3]} {est_info[2]}")
            st.caption(f"Programa: {programa} | Nivel: {nivel}")
            
            # Verificar si el período está abierto
            # (solo Admin puede cargar notas independientemente)
            
            # Obtener pensum del programa
            pensum = PENSUM_PNF.get(programa, {})
            
            if not pensum:
                st.warning("⚠️ No hay pensum configurado para este programa. Las notas se ingresarán manualmente.")
                semestre_manual = st.text_input("Semestre/Trimestre", placeholder="Ej: Tercer Trayecto - Quinto Semestre")
                uc_manual = st.text_input("Unidad Curricular", placeholder="Nombre de la UC")
                calif_manual = st.text_input("Calificación (1-20 o AP/AC/RE)")
                cred_manual = st.number_input("Créditos", min_value=1, max_value=12, value=3)
                
                if st.button("💾 Guardar Nota Manual"):
                    if uc_manual and calif_manual:
                        cal_letras = calificacion_a_letras(calif_manual)
                        # Verificar apertura
                        abierto = verificar_apertura(estado_est, municipio_est, aula_est, programa, semestre_manual)
                        if abierto or rol == "Admin Principal":
                            registrar_nota(est_id, uc_manual, calif_manual, cal_letras, cred_manual, semestre_manual, usuario)
                            st.success(f"✅ Nota registrada: {uc_manual} = {calif_manual}")
                        else:
                            st.error("❌ El período de notas está cerrado para esta sede/programa/semestre.")
                    else:
                        st.error("❌ Complete todos los campos.")
            else:
                # Mostrar pensum con campos de calificación
                # Filtrar trayectos según nivel
                semestres_disponibles = list(pensum.keys())
                
                if tipo_prog == "PNF" and nivel == "TSU":
                    # TSU: solo Tercer Trayecto+
                    semestres_disponibles = [s for s in semestres_disponibles if "Tercer" in s or "Cuarto" in s]
                
                semestre_sel = st.selectbox("Seleccione Semestre/Trimestre", options=semestres_disponibles)
                
                # Verificar apertura
                abierto = verificar_apertura(estado_est, municipio_est, aula_est, programa, semestre_sel)
                if not abierto and rol != "Admin Principal":
                    st.error("❌ El período de notas está **cerrado** para este semestre/sede/programa.")
                    st.info("Contacte al administrador para solicitar apertura.")
                    return
                elif not abierto:
                    st.warning("⚠️ El período está cerrado, pero como Admin puede cargar notas.")
                
                ucs = pensum.get(semestre_sel, [])
                
                if ucs:
                    st.markdown(f"**Semestre:** {semestre_sel}")
                    
                    # Cargar notas existentes
                    notas_existentes = obtener_notas_estudiante(est_id)
                    notas_dict = {(n[1], n[5]): n[2] for n in notas_existentes}  # (uc, semestre) -> calif
                    
                    with st.form("form_cargar_notas"):
                        notas_nuevas = []
                        for uc_data in ucs:
                            uc_nombre = uc_data["uc"]
                            uc_creditos = uc_data["creditos"]
                            
                            calif_existente = notas_dict.get((uc_nombre, semestre_sel))
                            
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.markdown(f"**{uc_nombre}**")
                            with col2:
                                calif = st.text_input(
                                    f"Calif_{uc_nombre[:20]}",
                                    value=str(calif_existente) if calif_existente else "",
                                    placeholder="1-20 / AP / AC / RE",
                                    key=f"nota_{est_id}_{uc_nombre[:30]}"
                                )
                            with col3:
                                st.caption(f"UC: {uc_creditos}")
                            
                            notas_nuevas.append({"uc": uc_nombre, "calif": calif, "creditos": uc_creditos})
                        
                        submitted = st.form_submit_button("💾 Guardar Todas las Notas")
                        
                        if submitted:
                            guardadas = 0
                            vacias = 0
                            errores_calif = 0
                            for nota_data in notas_nuevas:
                                calif = nota_data["calif"].strip()
                                if not calif:
                                    vacias += 1
                                    continue
                                
                                # Validar calificación
                                if calif in CALIFICACIONES_ESPECIALES:
                                    pass  # Válida
                                else:
                                    try:
                                        n = int(calif)
                                        if not (1 <= n <= 20):
                                            errores_calif += 1
                                            continue
                                    except ValueError:
                                        errores_calif += 1
                                        continue
                                
                                cal_letras = calificacion_a_letras(calif)
                                registrar_nota(
                                    est_id, nota_data["uc"], calif, cal_letras,
                                    nota_data["creditos"], semestre_sel, usuario
                                )
                                guardadas += 1
                            
                            if guardadas > 0:
                                st.success(f"✅ {guardadas} nota(s) guardada(s) exitosamente.")
                            if vacias > 0:
                                st.info(f"ℹ️ {vacias} UC(s) sin calificación (se omitieron).")
                            if errores_calif > 0:
                                st.error(f"❌ {errores_calif} calificación(es) inválida(s). Use 1-20 o AP/AC/RE.")
                else:
                    st.info("No hay UCs definidas para este semestre.")


# ============================================================
# PÁGINA: CERTIFICACIONES
# ============================================================

def pagina_certificaciones():
    st.title("📄 Certificaciones de Calificaciones")
    st.markdown("---")
    
    rol = st.session_state.user_rol
    usuario = st.session_state.user_info["nombre"]
    
    tab1, tab2 = st.tabs(["📄 Certificación Individual", "📦 Certificación en Lote"])
    
    with tab1:
        st.subheader("Generar Certificación Individual")
        
        cedula_buscar = st.text_input("Cédula del Estudiante", placeholder="Ej: V-12.345.678", key="cert_cedula")
        
        if cedula_buscar:
            est = buscar_estudiante(cedula_buscar)
            if est:
                est_id = est[0]
                titularidad = est[15] if len(est) > 15 else ""
                st.info(f"👨‍🎓 **{est[3]} {est[2]}** | C.I.: {est[1]} | {est[11]} | {est[12]}")
                
                notas = obtener_notas_estudiante(est_id)
                if notas:
                    # Seleccionar nivel para la certificación
                    tipo_prog = est[10]
                    if tipo_prog == "PNF":
                        nivel_cert = st.selectbox("Nivel para Certificación", options=NIVELES_ACADEMICOS, key="cert_nivel")
                    else:
                        nivel_cert = NIVELES_PNFA.get(tipo_prog, "")
                        st.info(f"Nivel: {nivel_cert}")
                    
                    tipo_cert = st.selectbox("Tipo de Certificación", 
                                           options=["completa", "parcial"],
                                           format_func=lambda x: "Completa" if x == "completa" else "Parcial")
                    
                    if st.button("📄 Generar Certificación", type="primary", key="btn_cert_individual"):
                        est_data = buscar_estudiante_por_id(est_id)
                        if est_data:
                            # Filtrar notas según nivel
                            if tipo_prog == "PNF" and nivel_cert == "TSU":
                                notas_filtradas = [n for n in notas if "Tercer" in n[5] or "Cuarto" in n[5]]
                            else:
                                notas_filtradas = notas
                            
                            pdf_buffer, hash_ver = generar_certificacion_pdf(est_data, notas_filtradas, nivel_cert, tipo_cert)
                            
                            # Registrar certificación
                            registrar_certificacion(est_id, tipo_cert, nivel_cert, usuario, hash_ver)
                            
                            st.download_button(
                                label="⬇️ Descargar Certificación PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=f"Certificacion_{cedula_buscar.replace('-','').replace('.','')}_{nivel_cert}.pdf",
                                mime="application/pdf"
                            )
                            st.success("✅ Certificación generada exitosamente.")
                else:
                    st.warning("⚠️ No hay notas registradas para este estudiante.")
            else:
                st.error("❌ Estudiante no encontrado.")
    
    with tab2:
        st.subheader("Generar Certificaciones en Lote")
        st.info("💡 Seleccione estudiantes para generar un archivo ZIP con certificaciones individuales.")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            filtro_estado = st.selectbox("Estado", options=[""] + list(ESTADOS_MUNICIPIOS.keys()), key="batch_estado")
        with col2:
            filtro_programa = st.selectbox("Programa", options=[""] + obtener_programas("PNF") + obtener_programas("PNFA_E") + obtener_programas("PNFA_M"), key="batch_prog")
        
        if st.button("🔍 Buscar Estudiantes", key="btn_batch_search"):
            estudiantes = obtener_estudiantes_filtro(
                estado=filtro_estado,
                programa=filtro_programa
            )
            if estudiantes:
                st.session_state["batch_estudiantes"] = estudiantes
            else:
                st.warning("No se encontraron estudiantes con esos filtros.")
        
        if "batch_estudiantes" in st.session_state:
            estudiantes = st.session_state["batch_estudiantes"]
            df_est = pd.DataFrame(estudiantes, columns=["ID", "Cédula", "Apellidos", "Nombres", "Sexo", "Estado", "Municipio", "Aula", "Tipo", "Programa", "Nivel", "Ingreso", "Titularidad"])
            st.dataframe(df_est, use_container_width=True, hide_index=True)
            
            seleccionados = st.multiselect(
                "Seleccione estudiantes (por ID)",
                options=[e[0] for e in estudiantes],
                key="batch_selected"
            )
            
            if seleccionados and st.button("📦 Generar ZIP", type="primary", key="btn_batch_gen"):
                nivel_batch = st.session_state.get("batch_nivel", "BACHILLER")
                zip_buffer = generar_certificacion_lote(seleccionados, nivel_batch)
                st.download_button(
                    label="⬇️ Descargar ZIP con Certificaciones",
                    data=zip_buffer.getvalue(),
                    file_name=f"Certificaciones_Lote_{datetime.now().strftime('%Y%m%d')}.zip",
                    mime="application/zip"
                )
                st.success(f"✅ {len(seleccionados)} certificación(es) generada(s).")




# ============================================================
# PÁGINA: LISTADO DE ESTUDIANTES
# ============================================================

def pagina_listado_estudiantes():
    st.title("📋 Listado de Estudiantes")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_estado = st.selectbox("Filtrar por Estado", options=[""] + list(ESTADOS_MUNICIPIOS.keys()), key="list_estado")
    with col2:
        municipios = ESTADOS_MUNICIPIOS.get(filtro_estado, []) if filtro_estado else []
        filtro_municipio = st.selectbox("Filtrar por Municipio", options=[""] + municipios, key="list_municipio")
    with col3:
        filtro_programa = st.selectbox("Filtrar por Programa", options=[""] + obtener_programas("PNF") + obtener_programas("PNFA_E") + obtener_programas("PNFA_M"), key="list_prog")
    
    if st.button("🔍 Aplicar Filtros", key="btn_list_filter"):
        estudiantes = obtener_estudiantes_filtro(
            estado=filtro_estado,
            municipio=filtro_municipio,
            programa=filtro_programa
        )
        if estudiantes:
            df = pd.DataFrame(estudiantes, columns=["ID", "Cédula", "Apellidos", "Nombres", "Sexo", "Estado", "Municipio", "Aula", "Tipo", "Programa", "Nivel", "Ingreso", "Titularidad"])
            # Formatear sexo
            df["Sexo"] = df["Sexo"].map({"M": "Masculino", "F": "Femenino"}).fillna(df["Sexo"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Exportar a Excel
            buffer_excel = BytesIO()
            with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name="Estudiantes", index=False)
            buffer_excel.seek(0)
            st.download_button(
                label="📊 Exportar a Excel",
                data=buffer_excel.getvalue(),
                file_name=f"Listado_Estudiantes_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No se encontraron estudiantes con esos filtros.")
    
    # Mostrar todos si no hay filtros
    todos = obtener_estudiantes_filtro()
    if todos:
        df_all = pd.DataFrame(todos, columns=["ID", "Cédula", "Apellidos", "Nombres", "Sexo", "Estado", "Municipio", "Aula", "Tipo", "Programa", "Nivel", "Ingreso", "Titularidad"])
        df_all["Sexo"] = df_all["Sexo"].map({"M": "Masculino", "F": "Femenino"}).fillna(df_all["Sexo"])
        st.dataframe(df_all, use_container_width=True, hide_index=True)


# ============================================================
# PÁGINA: GESTIÓN DE USUARIOS
# ============================================================

def pagina_gestion_usuarios():
    st.title("👥 Gestión de Usuarios")
    st.markdown("---")
    
    rol_actual = st.session_state.user_rol
    usuario_actual = st.session_state.user_info["cedula"]
    
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Listado", "➕ Crear Usuario", "🔑 Cambiar Contraseña", "⚙️ Estado"])
    
    # --- Tab 1: Listado ---
    with tab1:
        usuarios = obtener_usuarios()
        if usuarios:
            df = pd.DataFrame(usuarios, columns=["ID", "Nombre", "Cédula", "Rol", "Estado", "Fecha Creación"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No hay usuarios registrados.")
    
    # --- Tab 2: Crear Usuario ---
    with tab2:
        with st.form("form_crear_usuario"):
            nuevo_nombre = st.text_input("Nombre Completo *")
            nueva_cedula = st.text_input("Cédula de Identidad *", placeholder="Ej: V-12.345.678")
            nueva_clave = st.text_input("Contraseña *", type="password", placeholder="Mínimo 8 caracteres")
            nuevo_rol = st.selectbox("Rol *", options=ROLES_LIST)
            nuevo_estado = st.selectbox("Estado *", options=["Activo", "Inactivo"])
            
            submitted = st.form_submit_button("✅ Crear Usuario")
            
            if submitted:
                errores = []
                if not nuevo_nombre:
                    errores.append("Nombre es obligatorio")
                if not nueva_cedula:
                    errores.append("Cédula es obligatoria")
                if not nueva_clave or len(nueva_clave) < 8:
                    errores.append("Contraseña debe tener al menos 8 caracteres")
                
                if errores:
                    for err in errores:
                        st.error(f"❌ {err}")
                else:
                    ok = crear_usuario(nuevo_nombre.upper(), nueva_cedula, nueva_clave, nuevo_rol, nuevo_estado)
                    if ok:
                        st.success(f"✅ Usuario {nuevo_nombre} creado exitosamente.")
                    else:
                        st.error("❌ Error al crear usuario. Posible cédula duplicada.")
    
    # --- Tab 3: Cambiar Contraseña (v2.1 NUEVO) ---
    with tab3:
        st.subheader("🔑 Cambiar Mi Contraseña")
        st.info(f"Usuario: **{st.session_state.user_info['nombre']}** | Cédula: **{usuario_actual}**")
        
        with st.form("form_cambiar_clave"):
            clave_actual = st.text_input("Contraseña Actual *", type="password")
            clave_nueva = st.text_input("Contraseña Nueva *", type="password", placeholder="Mínimo 8 caracteres")
            clave_confirmar = st.text_input("Confirmar Contraseña Nueva *", type="password")
            
            submitted = st.form_submit_button("🔑 Cambiar Contraseña")
            
            if submitted:
                if not clave_actual or not clave_nueva or not clave_confirmar:
                    st.error("❌ Todos los campos son obligatorios.")
                elif clave_nueva != clave_confirmar:
                    st.error("❌ La contraseña nueva y su confirmación no coinciden.")
                elif len(clave_nueva) < 8:
                    st.error("❌ La contraseña nueva debe tener al menos 8 caracteres.")
                else:
                    ok, msg = cambiar_clave_usuario(usuario_actual, clave_actual, clave_nueva)
                    if ok:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")
    
    # --- Tab 4: Cambiar Estado ---
    with tab4:
        if rol_actual == "Admin Principal":
            usuarios = obtener_usuarios()
            if usuarios:
                for u in usuarios:
                    u_id, u_nombre, u_cedula, u_rol, u_estado, u_fecha = u
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{u_nombre}** ({u_cedula}) - {u_rol}")
                    with col2:
                        st.caption(f"Estado: {u_estado}")
                    with col3:
                        nuevo_est = "Inactivo" if u_estado == "Activo" else "Activo"
                        if st.button(f"{'🔴' if u_estado == 'Activo' else '🟢'} {nuevo_est}", key=f"est_{u_id}"):
                            actualizar_estado_usuario(u_id, nuevo_est)
                            st.success(f"✅ Estado de {u_nombre} cambiado a {nuevo_est}.")
                            st.rerun()
        else:
            st.warning("⚠️ Solo el Admin Principal puede cambiar estados de usuario.")


# ============================================================
# PÁGINA: GESTIÓN DE ALMACENES
# ============================================================

def pagina_gestion_almacenes():
    st.title("🏫 Gestión de Almacenes / Aulas Taller")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📋 Listado", "➕ Crear Almacén", "🗑️ Eliminar Almacén"])
    
    with tab1:
        st.subheader("📋 Almacenes / Aulas Taller Registrados")
        
        # Filtros para buscar fácilmente entre 1000+ registros
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_estado = st.selectbox("Filtrar por Estado", options=["Todos"] + list(ESTADOS_MUNICIPIOS.keys()), key="alm_filt_est")
        with col_f2:
            estado_sel = filtro_estado if filtro_estado != "Todos" else ""
            municipios_disponibles = ["Todos"] + ESTADOS_MUNICIPIOS.get(filtro_estado, ["Seleccione"]) if filtro_estado != "Todos" else ["Todos"]
            filtro_municipio = st.selectbox("Filtrar por Municipio", options=municipios_disponibles, key="alm_filt_mun")
        with col_f3:
            filtro_busqueda = st.text_input("🔍 Buscar por nombre o aula", placeholder="Escriba para buscar...", key="alm_filt_bus")
        
        municipio_sel = filtro_municipio if filtro_municipio != "Todos" else ""
        almacenes = obtener_almacenes_filtro(estado_sel, municipio_sel, filtro_busqueda)
        
        if almacenes:
            df = pd.DataFrame(almacenes, columns=["ID", "Nombre", "Estado", "Municipio", "Aula Taller"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"Mostrando {len(almacenes)} almacén(es)")
        else:
            st.info("No se encontraron almacenes con esos filtros.")
    
    with tab2:
        with st.form("form_crear_almacen"):
            nombre_alm = st.text_input("Nombre del Almacén *", placeholder="Ej: Aula Taller Principal")
            estado_alm = st.selectbox("Estado *", options=list(ESTADOS_MUNICIPIOS.keys()), key="alm_crear_est")
            municipio_alm = st.selectbox("Municipio *", options=ESTADOS_MUNICIPIOS.get(estado_alm, ["Seleccione"]), key="alm_crear_mun")
            aula_alm = st.text_input("Aula Taller *", placeholder="Ej: Aula 01")
            
            submitted = st.form_submit_button("✅ Crear Almacén")
            
            if submitted:
                if not nombre_alm or not aula_alm:
                    st.error("❌ Todos los campos son obligatorios.")
                else:
                    ok = crear_almacen(nombre_alm.upper(), estado_alm, municipio_alm, aula_alm.upper())
                    if ok:
                        st.success(f"✅ Almacén '{nombre_alm}' creado exitosamente.")
                    else:
                        st.error("❌ Error al crear almacén.")
    
    with tab3:
        st.subheader("🗑️ Eliminar Almacén / Aula Taller")
        st.warning("⚠️ Al eliminar un almacén, los estudiantes asociados a esa aula quedarán sin asignación. Verifique antes de eliminar.")
        
        # Filtro para buscar el almacén a eliminar
        elim_estado = st.selectbox("Filtrar por Estado", options=["Todos"] + list(ESTADOS_MUNICIPIOS.keys()), key="alm_elim_est")
        elim_estado_sel = elim_estado if elim_estado != "Todos" else ""
        elim_municipios = ["Todos"] + ESTADOS_MUNICIPIOS.get(elim_estado, ["Seleccione"]) if elim_estado != "Todos" else ["Todos"]
        elim_municipio = st.selectbox("Filtrar por Municipio", options=elim_municipios, key="alm_elim_mun")
        elim_busqueda = st.text_input("🔍 Buscar por nombre o aula", placeholder="Escriba para buscar...", key="alm_elim_bus")
        
        elim_municipio_sel = elim_municipio if elim_municipio != "Todos" else ""
        almacenes_elim = obtener_almacenes_filtro(elim_estado_sel, elim_municipio_sel, elim_busqueda)
        
        if almacenes_elim:
            df_elim = pd.DataFrame(almacenes_elim, columns=["ID", "Nombre", "Estado", "Municipio", "Aula Taller"])
            st.dataframe(df_elim, use_container_width=True, hide_index=True)
            st.caption(f"Mostrando {len(almacenes_elim)} almacén(es). Seleccione el ID a eliminar.")
            
            # Selección del ID a eliminar
            almacen_id_elim = st.number_input("ID del almacén a eliminar", min_value=1, step=1, key="alm_elim_id")
            
            # Buscar el almacén seleccionado para mostrar sus datos
            almacen_seleccionado = None
            for a in almacenes_elim:
                if a[0] == almacen_id_elim:
                    almacen_seleccionado = a
                    break
            
            if almacen_seleccionado:
                st.info(f"📌 Va a eliminar: **{almacen_seleccionado[1]}** | Estado: {almacen_seleccionado[2]} | Municipio: {almacen_seleccionado[3]} | Aula: {almacen_seleccionado[4]}")
                
                confirmar_elim = st.checkbox("✅ Confirmo que deseo eliminar este almacén", key="alm_elim_confirm")
                
                if st.button("🗑️ Eliminar Almacén", type="primary", key="btn_elim_almacen"):
                    if confirmar_elim:
                        ok = eliminar_almacen(almacen_id_elim)
                        if ok:
                            st.success(f"✅ Almacén ID {almacen_id_elim} eliminado exitosamente.")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ No se encontró el almacén con ese ID.")
                    else:
                        st.error("❌ Debe marcar la casilla de confirmación antes de eliminar.")
        else:
            st.info("No se encontraron almacenes con esos filtros.")


# ============================================================
# PÁGINA: CONFIGURACIÓN DE LISTAS
# ============================================================

def pagina_config_listas():
    st.title("⚙️ Configuración de Listas")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 Programas Existentes", "➕ Agregar Programa"])
    
    with tab1:
        programas_db = obtener_todos_programas_config()
        if programas_db:
            df = pd.DataFrame(programas_db, columns=["ID", "Tipo", "Programa"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            prog_del = st.number_input("ID del programa a eliminar", min_value=1, step=1, key="del_prog_id")
            if st.button("🗑️ Eliminar Programa"):
                eliminar_programa_lista(prog_del)
                st.success("✅ Programa eliminado.")
                st.rerun()
        else:
            st.info("No hay programas adicionales configurados.")
        
        # Mostrar programas por defecto
        st.subheader("📌 Programas por Defecto (del sistema)")
        for tipo, progs in PROGRAMAS_POR_DEFECTO.items():
            st.markdown(f"**{tipo}:**")
            for p in progs:
                st.markdown(f"  - {p}")
    
    with tab2:
        with st.form("form_agregar_programa"):
            tipo_prog_nuevo = st.selectbox("Tipo de Programa *", options=TIPOS_PROGRAMA)
            programa_nuevo = st.text_input("Nombre del Programa *", placeholder="Ej: PROFESOR DE MATEMÁTICA")
            
            submitted = st.form_submit_button("✅ Agregar Programa")
            
            if submitted:
                if not programa_nuevo:
                    st.error("❌ Ingrese un nombre de programa.")
                else:
                    ok = agregar_programa_lista(tipo_prog_nuevo, programa_nuevo.upper())
                    if ok:
                        st.success(f"✅ Programa '{programa_nuevo}' agregado a {tipo_prog_nuevo}.")
                    else:
                        st.error("❌ Error al agregar programa.")


# ============================================================
# PÁGINA: APERTURA / CIERRE DE NOTAS
# ============================================================

def pagina_apertura_notas():
    st.title("🔓 Apertura / Cierre de Notas")
    st.markdown("---")
    
    rol = st.session_state.user_rol
    usuario = st.session_state.user_info["nombre"]
    
    if rol != "Admin Principal":
        st.warning("⚠️ Solo el Admin Principal (Nivel 1) puede gestionar la apertura/cierre de notas.")
        st.info("💡 Si necesita cargar notas y el período está cerrado, solicite apertura a su superior.")
        return
    
    st.info("💡 Controle cuándo los Secretarios Situados pueden cargar notas. Puede aperturar a nivel **Nacional**, **Estadal**, **Municipal** o **por Plantel**.")
    
    # ---- SECCIÓN 1: APERTURA ----
    st.subheader("📤 Aperturar / Cerrar Período de Notas")
    
    # Selector de nivel de apertura (fuera del form para cascada)
    nivel_opciones = ["Nacional", "Estadal", "Municipal", "Por Plantel"]
    nivel_sel = st.selectbox("🎯 Nivel de Apertura *", options=nivel_opciones, key="ap_nivel")
    
    nivel_map = {"Nacional": "nacional", "Estadal": "estadal", "Municipal": "municipal", "Por Plantel": "plantel"}
    nivel_val = nivel_map[nivel_sel]
    
    # Campos dinámicos según nivel
    if nivel_val == "nacional":
        st.info("🌍 **Apertura Nacional**: Aplica para TODOS los estados, municipios y planteles.")
        ap_estado = "TODOS"
        ap_municipio = "TODOS"
        ap_aula = "TODOS"
    elif nivel_val == "estadal":
        st.info("🏛️ **Apertura Estadal**: Aplica para un estado específico y TODOS sus municipios y planteles.")
        ap_estado = st.selectbox("Estado *", options=list(ESTADOS_MUNICIPIOS.keys()), key="ap_estado_est")
        ap_municipio = "TODOS"
        ap_aula = "TODOS"
    elif nivel_val == "municipal":
        st.info("🏘️ **Apertura Municipal**: Aplica para un municipio específico y TODAS sus aulas.")
        ap_estado = st.selectbox("Estado *", options=list(ESTADOS_MUNICIPIOS.keys()), key="ap_estado_mun")
        municipios = ESTADOS_MUNICIPIOS.get(ap_estado, [])
        ap_municipio = st.selectbox("Municipio *", options=municipios, key="ap_municipio_mun")
        ap_aula = "TODOS"
    else:  # plantel
        st.info("🏫 **Apertura por Plantel**: Aplica para un aula taller específica.")
        col_e, col_m = st.columns(2)
        with col_e:
            ap_estado = st.selectbox("Estado *", options=list(ESTADOS_MUNICIPIOS.keys()), key="ap_estado_pla")
        with col_m:
            municipios = ESTADOS_MUNICIPIOS.get(ap_estado, [])
            ap_municipio = st.selectbox("Municipio *", options=municipios, key="ap_municipio_pla")
        
        # Aulas disponibles
        almacenes = obtener_almacenes()
        aulas_opciones = [f"{a[1]} ({a[4]})" for a in almacenes if a[2] == ap_estado and a[3] == ap_municipio]
        if not aulas_opciones:
            aulas_opciones = ["Sin aulas disponibles"]
        ap_aula_display = st.selectbox("Aula Taller *", options=aulas_opciones, key="ap_aula_pla")
        ap_aula = ap_aula_display.split(" (")[0] if " (" in ap_aula_display else ap_aula_display
    
    # Tipo de Programa y Programa (cascada)
    col_tipo, col_prog = st.columns(2)
    with col_tipo:
        ap_tipo_prog = st.selectbox("Tipo de Programa *", options=TIPOS_PROGRAMA, key="ap_tipo_prog")
    with col_prog:
        programas = obtener_programas(ap_tipo_prog)
        ap_programa = st.selectbox("Programa *", options=programas, key="ap_prog")
    
    ap_semestre = st.text_input("Semestre/Trimestre *", placeholder="Ej: Tercer Trayecto - Quinto Semestre", key="ap_semestre")
    
    accion = st.radio("Acción", options=["Abrir", "Cerrar"], horizontal=True, key="ap_accion")
    
    if st.button("💾 Aplicar Apertura/Cierre", type="primary", key="btn_apertura"):
        if not ap_semestre:
            st.error("❌ El campo Semestre/Trimestre es obligatorio.")
        else:
            abierto = accion == "Abrir"
            establecer_apertura(nivel_val, ap_estado, ap_municipio, ap_aula, ap_tipo_prog, ap_programa, ap_semestre, abierto, usuario)
            estado_texto = "ABIERTO" if abierto else "CERRADO"
            nivel_texto = nivel_sel
            st.success(f"✅ Período de notas {estado_texto} a nivel **{nivel_texto}** para **{ap_programa}** - {ap_semestre}.")
    
    st.markdown("---")
    
    # ---- SECCIÓN 2: ESTADO ACTUAL DE APERTURAS ----
    st.subheader("📋 Estado Actual de Aperturas")
    
    aperturas = obtener_aperturas_notas()
    if aperturas:
        df_ap = pd.DataFrame(aperturas, columns=["ID", "Nivel", "Estado", "Municipio", "Aula", "Tipo Prog.", "Programa", "Semestre", "Abierto", "F. Apertura", "F. Cierre", "Abierto Por"])
        df_ap["Abierto"] = df_ap["Abierto"].map({1: "✅ Sí", 0: "❌ No"})
        df_ap["Nivel"] = df_ap["Nivel"].map({"nacional": "🌍 Nacional", "estadal": "🏛️ Estadal", "municipal": "🏘️ Municipal", "plantel": "🏫 Plantel"})
        st.dataframe(df_ap, use_container_width=True, hide_index=True)
        
        # Exportar a Excel
        buffer_excel = BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            df_ap.to_excel(writer, sheet_name="Aperturas", index=False)
        buffer_excel.seek(0)
        st.download_button(
            label="📊 Descargar Aperturas en Excel",
            data=buffer_excel.getvalue(),
            file_name=f"Aperturas_Notas_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_download_aperturas"
        )
    else:
        st.info("No hay registros de apertura/cierre de notas.")


# ============================================================
# PÁGINA: ELIMINAR REGISTRO
# ============================================================

def pagina_eliminar_registro():
    st.title("🗑️ Eliminar Registro de Estudiante")
    st.markdown("---")
    
    rol = st.session_state.user_rol
    usuario = st.session_state.user_info["usuario"]
    
    if rol == 3:
        st.warning("⚠️ Su nivel (Nivel 3 - Secretaría Situada) no puede eliminar registros directamente.")
        st.info("💡 Debe solicitar autorización. Los usuarios Nivel 1 o Nivel 2 aprobarán o rechazarán su solicitud.")
        
        st.markdown("### 📝 Solicitar Autorización de Eliminación")
        
        cedula_el = st.text_input("Cédula del estudiante a eliminar", placeholder="Ej: V-12.345.678", key="el_ced_n3")
        motivo_el = st.text_area("Motivo de la eliminación *", placeholder="Ej: Registro duplicado, estudiante retirado, error de registro...", key="el_motivo_n3")
        
        if st.button("📨 Enviar Solicitud de Autorización", type="primary", key="btn_sol_elim_n3"):
            if not cedula_el or not motivo_el:
                st.error("❌ Todos los campos son obligatorios.")
            else:
                # Buscar ID del estudiante por cédula
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT id FROM estudiantes WHERE cedula = ?", (cedula_el,))
                est_row = c.fetchone()
                conn.close()
                est_id = est_row[0] if est_row else None
                
                crear_solicitud_autorizacion(
                    tipo_solicitud="eliminacion",
                    solicitado_por=usuario,
                    cedula_solicitante=cedula_el,
                    rol_solicitante=rol,
                    estudiante_id=est_id,
                    estudiante_cedula=cedula_el,
                    motivo=motivo_el
                )
                st.success("✅ Solicitud de autorización enviada exitosamente.")
                st.info("📌 Un usuario Nivel 1 o Nivel 2 revisará su solicitud. Consulte el estado en la página 📋 Autorizaciones.")
    else:
        st.info(f"💡 Su nivel ({'Nivel 1 - Admin Principal' if rol == 1 else 'Nivel 2 - Secretaría General'}) puede eliminar registros directamente.")
        
        st.markdown("### 🔍 Buscar Estudiante a Eliminar")
        
        cedula_el = st.text_input("Cédula del estudiante", placeholder="Ej: V-12.345.678", key="el_ced_n12")
        
        if st.button("🔍 Buscar", key="btn_buscar_elim"):
            if not cedula_el:
                st.error("❌ Ingrese una cédula.")
            else:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("SELECT id, cedula, apellidos, nombres, programa, semestre, estado, municipio, aula_taller FROM estudiantes WHERE cedula = ?", (cedula_el,))
                est = c.fetchone()
                conn.close()
                
                if est:
                    st.session_state["est_encontrado_elim"] = est
                else:
                    st.error("❌ No se encontró ningún estudiante con esa cédula.")
                    st.session_state.pop("est_encontrado_elim", None)
        
        est = st.session_state.get("est_encontrado_elim")
        if est:
            est_id = est[0]
            st.markdown("#### 📋 Datos del Estudiante")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Cédula:** {est[1]}")
                st.markdown(f"**Apellidos:** {est[2]}")
                st.markdown(f"**Nombres:** {est[3]}")
                st.markdown(f"**Programa:** {est[4]}")
            with col2:
                st.markdown(f"**Semestre:** {est[5]}")
                st.markdown(f"**Estado:** {est[6]}")
                st.markdown(f"**Municipio:** {est[7]}")
                st.markdown(f"**Aula:** {est[8]}")
            
            st.markdown("---")
            motivo_el = st.text_area("Motivo de la eliminación *", placeholder="Ej: Registro duplicado, estudiante retirado, error de registro...", key="el_motivo_n12")
            
            confirmar = st.checkbox(f"✅ Confirmo que deseo ELIMINAR el registro de **{est[3]} {est[2]}** (C.I: {est[1]})", key="el_confirm_n12")
            
            if st.button("🗑️ Eliminar Registro", type="primary", key="btn_elim_directo"):
                if not motivo_el:
                    st.error("❌ El motivo es obligatorio.")
                elif not confirmar:
                    st.error("❌ Debe confirmar la eliminación marcando el checkbox.")
                else:
                    exito, msg = eliminar_estudiante(est_id, usuario, rol, motivo_el, tipo_eliminacion="directa")
                    if exito:
                        st.success(f"✅ {msg}")
                        st.session_state.pop("est_encontrado_elim", None)
                    else:
                        st.error(f"❌ {msg}")


# ============================================================
# PÁGINA: AUTORIZACIONES
# ============================================================

def pagina_autorizaciones():
    st.title("📋 Gestión de Autorizaciones")
    st.markdown("---")
    
    rol = st.session_state.user_rol
    usuario = st.session_state.user_info["usuario"]
    
    if rol == 3:
        # NIVEL 3: Solo puede ver sus solicitudes
        st.info("💡 Aquí puede consultar el estado de sus solicitudes de autorización.")
        
        # Obtener todas y filtrar por solicitante
        todas_sol = obtener_solicitudes_autorizacion()
        mis_sol = [s for s in todas_sol if s[2] == usuario]  # columna 2 = solicitado_por
        
        if mis_sol:
            st.markdown("### 📋 Mis Solicitudes")
            # Columnas: id, tipo, solicitado_por, cedula_solicitante, rol_solicitante, est_id, est_cedula, motivo, estado, aprobado_por, f_sol, f_rev
            df_sol = pd.DataFrame(mis_sol, columns=["ID", "Tipo", "Solicitante", "Cédula Solic.", "Rol", "Est.ID", "Cédula Est.", "Motivo", "Estado", "Revisado Por", "Fecha Solicitud", "Fecha Revisión"])
            df_sol["Estado"] = df_sol["Estado"].map({"Pendiente": "⏳ Pendiente", "Aprobada": "✅ Aprobada", "Rechazada": "❌ Rechazada"})
            # Mostrar columnas clave
            df_display = df_sol[["ID", "Cédula Est.", "Motivo", "Tipo", "Estado", "Revisado Por", "Fecha Solicitud", "Fecha Revisión"]]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No ha enviado solicitudes de autorización.")
    else:
        # NIVEL 1 y 2: Pueden aprobar/rechazar solicitudes
        st.info(f"💡 Su nivel ({'Nivel 1 - Admin Principal' if rol == 1 else 'Nivel 2 - Secretaría General'}) le permite aprobar o rechazar solicitudes de autorización.")
        
        tab_pend, tab_todas, tab_elim, tab_reporte = st.tabs(["⏳ Pendientes", "📋 Todas", "🗑️ Eliminaciones", "📊 Reporte Excel"])
        
        # TAB: Pendientes
        with tab_pend:
            st.subheader("⏳ Solicitudes Pendientes")
            pendientes = obtener_solicitudes_autorizacion(estado_filtro="Pendiente")
            
            if pendientes:
                for sol in pendientes:
                    # Columnas: id, tipo, solicitado_por, cedula_solicitante, rol_solicitante, est_id, est_cedula, motivo, estado, aprobado_por, f_sol, f_rev
                    sol_id, tipo_sol, sol_por, ced_sol, rol_sol, est_id, est_ced, motivo, estado_sol, aprob_por, f_sol, f_rev = sol
                    with st.expander(f"Solicitud #{sol_id} - {tipo_sol.title()} - {est_ced} (por {sol_por})", expanded=False):
                        st.markdown(f"**Cédula Estudiante:** {est_ced}")
                        st.markdown(f"**Solicitante:** {sol_por}")
                        st.markdown(f"**Rol Solicitante:** Nivel {rol_sol}")
                        st.markdown(f"**Tipo:** {tipo_sol.title()}")
                        st.markdown(f"**Motivo:** {motivo}")
                        st.markdown(f"**Fecha Solicitud:** {f_sol}")
                        st.markdown(f"**Estado:** ⏳ Pendiente")
                        
                        col_apr, col_rec = st.columns(2)
                        with col_apr:
                            if st.button(f"✅ Aprobar #{sol_id}", key=f"btn_apr_{sol_id}"):
                                responder_solicitud_autorizacion(sol_id, True, usuario)
                                
                                if tipo_sol == "eliminacion" and est_id:
                                    exito, msg = eliminar_estudiante(est_id, sol_por, rol_sol, motivo, tipo_eliminacion="autorizada", solicitud_id=sol_id)
                                    if exito:
                                        st.success(f"✅ Solicitud #{sol_id} aprobada. {msg}")
                                    else:
                                        st.warning(f"⚠️ Solicitud aprobada, pero no se pudo eliminar el registro: {msg}")
                                else:
                                    st.success(f"✅ Solicitud #{sol_id} aprobada exitosamente.")
                                st.rerun()
                        with col_rec:
                            if st.button(f"❌ Rechazar #{sol_id}", key=f"btn_rec_{sol_id}"):
                                responder_solicitud_autorizacion(sol_id, False, usuario)
                                st.success(f"✅ Solicitud #{sol_id} rechazada.")
                                st.rerun()
            else:
                st.info("No hay solicitudes pendientes.")
        
        # TAB: Todas
        with tab_todas:
            st.subheader("📋 Todas las Solicitudes")
            todas = obtener_solicitudes_autorizacion()
            
            if todas:
                df_todas = pd.DataFrame(todas, columns=["ID", "Tipo", "Solicitante", "Cédula Solic.", "Rol", "Est.ID", "Cédula Est.", "Motivo", "Estado", "Revisado Por", "Fecha Solicitud", "Fecha Revisión"])
                df_todas["Estado"] = df_todas["Estado"].map({"Pendiente": "⏳ Pendiente", "Aprobada": "✅ Aprobada", "Rechazada": "❌ Rechazada"})
                df_display = df_todas[["ID", "Cédula Est.", "Solicitante", "Motivo", "Tipo", "Estado", "Revisado Por", "Fecha Solicitud", "Fecha Revisión"]]
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            else:
                st.info("No hay solicitudes registradas.")
        
        # TAB: Eliminaciones
        with tab_elim:
            st.subheader("🗑️ Registro de Eliminaciones")
            eliminaciones = obtener_eliminaciones()
            
            if eliminaciones:
                # Columnas: id, est_cedula, est_nombre, eliminado_por, rol_eliminador, motivo, tipo_eliminacion, solicitud_id, fecha_eliminacion
                df_el = pd.DataFrame(eliminaciones, columns=["ID", "Cédula", "Nombre Completo", "Eliminado Por", "Rol Elim.", "Motivo", "Tipo Elim.", "Solicitud ID", "Fecha Eliminación"])
                st.dataframe(df_el, use_container_width=True, hide_index=True)
            else:
                st.info("No hay registros de eliminaciones.")
        
        # TAB: Reporte Excel
        with tab_reporte:
            st.subheader("📊 Descargar Reporte Completo")
            st.info("💡 Descargue un reporte Excel con todas las autorizaciones y eliminaciones registradas en el sistema.")
            
            todas_sol = obtener_solicitudes_autorizacion()
            todas_elim = obtener_eliminaciones()
            
            buffer_excel = BytesIO()
            with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                # Hoja de Autorizaciones
                cols_aut = ["ID", "Tipo", "Solicitante", "Cédula Solic.", "Rol Solic.", "Est.ID", "Cédula Est.", "Motivo", "Estado", "Aprobado Por", "Fecha Solicitud", "Fecha Revisión"]
                if todas_sol:
                    df_s = pd.DataFrame(todas_sol, columns=cols_aut)
                    df_s["Estado"] = df_s["Estado"].map({"Pendiente": "Pendiente", "Aprobada": "Aprobada", "Rechazada": "Rechazada"})
                    df_s.to_excel(writer, sheet_name="Autorizaciones", index=False)
                else:
                    pd.DataFrame(columns=cols_aut).to_excel(writer, sheet_name="Autorizaciones", index=False)
                
                # Hoja de Eliminaciones
                cols_elim = ["ID", "Cédula", "Nombre Completo", "Eliminado Por", "Rol Elim.", "Motivo", "Tipo Elim.", "Solicitud ID", "Fecha Eliminación"]
                if todas_elim:
                    df_e = pd.DataFrame(todas_elim, columns=cols_elim)
                    df_e.to_excel(writer, sheet_name="Eliminaciones", index=False)
                else:
                    pd.DataFrame(columns=cols_elim).to_excel(writer, sheet_name="Eliminaciones", index=False)
            
            buffer_excel.seek(0)
            st.download_button(
                label="📊 Descargar Reporte de Autorizaciones y Eliminaciones",
                data=buffer_excel.getvalue(),
                file_name=f"Reporte_Autorizaciones_Eliminaciones_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_reporte_aut"
            )


# ============================================================
# PÁGINA: VERIFICAR EXPEDIENTE ETAPA 1
# ============================================================

def pagina_verificar_etapa1():
    st.title("🔎 Verificar Expediente Etapa 1")
    st.markdown("---")
    
    st.info("💡 Consulte expedientes registrados en Etapa 1 (solo lectura). Cruce referencia por cédula.")
    
    cedula_buscar = st.text_input("Cédula a buscar en Etapa 1", placeholder="Ej: V-12.345.678")
    
    if st.button("🔍 Buscar en Etapa 1", key="btn_etapa1"):
        if not cedula_buscar:
            st.warning("⚠️ Ingrese una cédula.")
            return
        
        datos, error = consultar_expediente_etapa1(cedula_buscar)
        
        if datos:
            st.success("✅ Expediente encontrado en Etapa 1:")
            for campo, valor in datos.items():
                st.markdown(f"**{campo}:** {valor}")
        elif error:
            st.error(f"❌ {error}")
        else:
            st.warning("⚠️ No se encontró expediente en Etapa 1.")



# ============================================================
# PÁGINA: RESPALDO Y EXPORTACIÓN
# ============================================================

def pagina_respaldo_exportacion():
    st.title("💾 Respaldo y Exportación")
    st.markdown("---")
    st.info("💡 Desde aquí puede descargar copias de seguridad de la base de datos, exportar registros a Excel, y restaurar respaldos anteriores. Se recomienda hacer un respaldo **diario**.")
    
    rol = st.session_state.user_rol
    
    # ---- SECCIÓN 1: DESCARGAR BASE DE DATOS COMPLETA ----
    st.subheader("📥 Descargar Base de Datos")
    st.markdown("Descargue el archivo completo de la base de datos (`.db`) para respaldarlo en su disco externo u otro lugar seguro.")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("**📂 Etapa 2 — Base actual**")
        if os.path.exists(DB_FILE):
            tamano_db = os.path.getsize(DB_FILE)
            tamano_mb = tamano_db / (1024 * 1024)
            st.caption(f"Archivo: `{DB_FILE}` — Tamaño: {tamano_mb:.2f} MB")
            
            with open(DB_FILE, "rb") as f:
                db_bytes = f.read()
            
            st.download_button(
                label="📥 Descargar Base Etapa 2 (.db)",
                data=db_bytes,
                file_name=f"{DB_FILE}",
                mime="application/octet-stream",
                key="btn_download_db_etapa2"
            )
        else:
            st.warning("⚠️ No se encontró la base de datos de Etapa 2.")
    
    with col_b:
        st.markdown("**📂 Etapa 1 — Base anterior**")
        if os.path.exists(DB_FILE_ETAPA1):
            tamano_db1 = os.path.getsize(DB_FILE_ETAPA1)
            tamano_mb1 = tamano_db1 / (1024 * 1024)
            st.caption(f"Archivo: `{DB_FILE_ETAPA1}` — Tamaño: {tamano_mb1:.2f} MB")
            
            with open(DB_FILE_ETAPA1, "rb") as f:
                db1_bytes = f.read()
            
            st.download_button(
                label="📥 Descargar Base Etapa 1 (.db)",
                data=db1_bytes,
                file_name=f"{DB_FILE_ETAPA1}",
                mime="application/octet-stream",
                key="btn_download_db_etapa1"
            )
        else:
            st.warning("⚠️ No se encontró la base de datos de Etapa 1. Coloque `expedientes.db` en la misma carpeta de la app.")
    
    st.markdown("---")
    
    # ---- SECCIÓN 2: EXPORTAR A EXCEL ----
    st.subheader("📊 Exportar Registros a Excel")
    st.markdown("Exporte todos los registros a archivos Excel (`.xlsx`) para abrirlos en Excel, Google Sheets, etc.")
    
    # Seleccionar qué exportar
    exportar_opciones = st.multiselect(
        "Seleccione qué tablas exportar:",
        ["Estudiantes", "Notas", "Certificaciones", "Usuarios", "Almacenes", "Configuración de Listas"],
        default=["Estudiantes", "Notas", "Certificaciones"],
        key="multi_export"
    )
    
    if st.button("📊 Generar archivo Excel", key="btn_export_excel"):
        if not exportar_opciones:
            st.warning("⚠️ Seleccione al menos una tabla para exportar.")
            return
        
        conn = sqlite3.connect(DB_FILE)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            for tabla in exportar_opciones:
                tabla_map = {
                    "Estudiantes": "estudiantes",
                    "Notas": "notas",
                    "Certificaciones": "certificaciones",
                    "Usuarios": "usuarios",
                    "Almacenes": "almacenes",
                    "Configuración de Listas": "config_listas"
                }
                tabla_sql = tabla_map[tabla]
                
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {tabla_sql}", conn)
                    
                    # Para usuarios, ocultar la columna de claves por seguridad
                    if tabla_sql == "usuarios" and "clave" in df.columns:
                        df = df.drop(columns=["clave"])
                    
                    df.to_excel(writer, sheet_name=tabla, index=False)
                except Exception as e:
                    st.error(f"❌ Error al exportar {tabla}: {e}")
        
        conn.close()
        excel_bytes = output.getvalue()
        
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        nombre_archivo = f"Expedientes_UNEM_Export_{fecha_hoy}.xlsx"
        
        st.success(f"✅ Archivo Excel generado con {len(exportar_opciones)} hoja(s).")
        st.download_button(
            label="📥 Descargar Excel (.xlsx)",
            data=excel_bytes,
            file_name=nombre_archivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_download_excel"
        )
    
    st.markdown("---")
    
    # ---- SECCIÓN 3: RESTAURAR RESPALDO (Solo Admin) ----
    if rol == "Admin Principal":
        st.subheader("📤 Restaurar Respaldo de Base de Datos")
        st.markdown("⚠️ **CUIDADO:** Al restaurar un respaldo, **se reemplazará** la base de datos actual con la versión que suba. Los datos registrados después del respaldo se perderán.")
        
        uploaded_db = st.file_uploader(
            "Subir archivo de respaldo (.db)",
            type=["db"],
            key="upload_restore_db"
        )
        
        if uploaded_db is not None:
            st.warning(f"📁 Archivo recibido: `{uploaded_db.name}` — {uploaded_db.size / 1024:.1f} KB")
            
            confirmar = st.checkbox(
                "☑️ Confirmo que deseo RESTAURAR este respaldo y reemplazar la base actual",
                key="chk_confirm_restore"
            )
            
            if st.button("📤 Restaurar Base de Datos", key="btn_restore_db", disabled=not confirmar):
                try:
                    # Guardar respaldo de la base actual antes de reemplazar
                    backup_nombre = f"{DB_FILE}.previo_a_restaurar_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    if os.path.exists(DB_FILE):
                        import shutil
                        shutil.copy2(DB_FILE, backup_nombre)
                        st.info(f"📋 Se guardó copia de la base actual como: `{backup_nombre}`")
                    
                    # Escribir la nueva base
                    with open(DB_FILE, "wb") as f:
                        f.write(uploaded_db.getbuffer())
                    
                    st.success("✅ ¡Base de datos restaurada exitosamente! Recargue la página para ver los cambios.")
                    st.info("💡 Haga clic en el botón ↻ (Recargar) del navegador o presione F5.")
                except Exception as e:
                    st.error(f"❌ Error al restaurar: {e}")
    
    st.markdown("---")
    
    # ---- SECCIÓN 4: INFORMACIÓN ----
    st.subheader("📋 Información del Sistema")
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    info_tablas = ["estudiantes", "notas", "certificaciones", "usuarios", "almacenes", "config_listas", "aperturas_notas"]
    
    for tabla in info_tablas:
        try:
            c.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = c.fetchone()[0]
            st.markdown(f"- **{tabla}:** {count} registro(s)")
        except:
            pass
    
    conn.close()
    
    # Fecha del último registro
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("SELECT MAX(fecha_registro) FROM estudiantes")
        ultima_fecha = c.fetchone()[0]
        if ultima_fecha:
            st.markdown(f"\n📅 **Último estudiante registrado:** {ultima_fecha}")
    except:
        pass
    conn.close()
    
    st.caption("💡 Recomendación: haga un respaldo diario descargando la base de datos (.db) y guárdela en su disco externo de 1 TB.")



# ============================================================
# MAIN - EJECUCIÓN PRINCIPAL
# ============================================================

if not st.session_state.get("logged_in", False):
    mostrar_login()
else:
    pagina = mostrar_sidebar()
    
    if pagina == "📊 Dashboard":
        pagina_dashboard()
    elif pagina == "📝 Registrar Estudiante":
        pagina_registrar_estudiante()
    elif pagina == "🔍 Consultar Expediente":
        pagina_consultar_expediente()
    elif pagina == "📖 Cargar Notas":
        pagina_cargar_notas()
    elif pagina == "📄 Certificaciones":
        pagina_certificaciones()
    elif pagina == "📋 Listado de Estudiantes":
        pagina_listado_estudiantes()
    elif pagina == "👥 Gestión de Usuarios":
        pagina_gestion_usuarios()
    elif pagina == "🏫 Gestión de Almacenes":
        pagina_gestion_almacenes()
    elif pagina == "⚙️ Configuración de Listas":
        pagina_config_listas()
    elif pagina == "🔓 Apertura/Cierre de Notas":
        pagina_apertura_notas()
    elif pagina == "🗑️ Eliminar Registro":
        pagina_eliminar_registro()
    elif pagina == "📋 Autorizaciones":
        pagina_autorizaciones()
    elif pagina == "🔎 Verificar Expediente Etapa 1":
        pagina_verificar_etapa1()
    elif pagina == "💾 Respaldo y Exportación":
        pagina_respaldo_exportacion()
    elif pagina == "🚪 Cerrar Sesión":
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.user_rol = None
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
