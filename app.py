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
    "Aragua": ["Alcántara", "Bolívar", "Camatagua", "Girardot", "Iragorry", "Lamas", "Libertador", "Mariño", "Michelena", "Ocumare de la Costa de Oro", "Revenga", "Ribas", "San Casimiro", "San Sebastián", "Santiago Mariño", "Sucre", "Tovar", "Urdaneta", "Zamora"],
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
    "Nueva Esparta": ["Arismendi", "Gómez", "García", "Maneiro", "Marcano", "Mariño", "Península de Macanao", "Tubores", "Villalba", "Díaz", "Antolín del Campo", "Bermúdez"],
    "Portuguesa": ["Agua Blanca", "Araure", "Esteller", "Guanare", "Guanarito", "Monseñor José Vicente de Unda", "Ospino", "Páez", "Papelón", "San Genaro de Boconoíto", "San Rafael de Onoto", "Santa Rosalía", "Sucre", "Turén"],
    "Sucre": ["Andrés Eloy Blanco", "Andrés Bello", "Arismendi", "Benítez", "Bermúdez", "Bolívar", "Cajigal", "Cruz Salmerón Acosta", "Libertador", "Mariño", "Mejía", "Montes", "Ribero", "Sucre", "Valdez"],
    "Táchira": ["Andrés Bello", "Antonio Rómulo Costa", "Ayacucho", "Bolívar", "Cárdenas", "Córdoba", "Fernández Feo", "Francisco de Miranda", "García de Hevia", "Guásimos", "Independencia", "Jáuregui", "José María Vargas", "Junín", "Libertad", "Libertador", "Lobatera", "Michelena", "Panamericano", "Pedro María Ureña", "Delicias", "Samuel Darío Maldonado", "San Cristóbal", "Seboruco", "Simón Rodríguez", "Sucre", "Torbes", "Uribante", "San Judas Tadeo"],
    "Trujillo": ["Andrés Bello", "Boconó", "Bolívar", "Candelaria", "Carache", "Carvajal", "Campo Elías", "Cuicas", "Escuque", "Juan Vicente Campos Elías", "La Ceiba", "Miranda", "Monte Carmelo", "Motatán", "Pampán", "Pampanito", "Rafael Rangel", "San Rafael de Carvajal", "Sucre", "Trujillo", "Urdaneta", "Valera"],
    "La Guaira": ["Vargas"],
    "Yaracuy": ["Arístides Bastidas", "Bolívar", "Bruzual", "Cocorote", "Independencia", "José Antonio Páez", "La Trinidad", "Nirgua", "Peña", "San Felipe", "Sucre", "Urachiche", "Veroes", "Manuel Monge"],
    "Zulia": ["Almirante Padilla", "Baralt", "Cabimas", "Catatumbo", "Colón", "Francisco Javier Pulgar", "Guajira", "Jesús Enrique Lossada", "Jesús María Semprún", "La Cañada de Urdaneta", "Lagunillas", "Machiques de Perijá", "Mara", "Maracaibo", "Miranda", "Rosario de Perijá", "San Francisco", "Santa Rita", "Simón Bolívar", "Sucre", "Valmore Rodríguez"],
}


# === Aulas taller oficiales (Resolucion N 092.11.2025 UNEM) ===
# Estado -> Municipio -> lista de sedes. Se ignora la columna Parroquia.
AULAS_OFICIALES = {
    "Amazonas": {
        "Atabapo": ["ETA Jos\u00e9 Gumilla"],
        "Atures": ["Liceo Santiago Aguerrevere", "ETA Comunidad y Trabajo", "E.B 27 de Junio", "U.E Lino de Clemente", "U.E Jos\u00e9 Mar\u00eda Vargas"],
        "Autana": ["U.E Miguel Antonio Caro"],
        "Manapiare": ["ETA Antonio Jos\u00e9 de Sucre"],
    },
    "Anzo\u00e1tegui": {
        "Aragua": ["L.N. Narciso Fragachan", "Escuela Las Margaritas del Llano"],
        "Sotillo": ["G.E. Antonio Jos\u00e9 Sotillo"],
        "P\u00edritu": ["L.B. Pedro Rolingson Herrera"],
        "Bol\u00edvar": ["U.E. Antonio Mata Medina", "C.E. Eulalia Buroz"],
        "Anaco": ["G.E. Narciso Fragachan"],
        "Bruzual": ["L.N. Dr. Jos\u00e9 Rafael Dominguez", "U.E. Manuel Ezequiel Bruzual"],
        "Cajigal": ["L.B. Tomas Ignacio Potentine"],
        "San Juan de Capistrano": ["E.B. Tomas Ignacio Potentine"],
        "Carvajal": ["E.B.N Carvajal"],
        "Freites": ["E.N. Pedro Mar\u00eda Freites", "E.N. Indigena Cachama"],
        "Guanipa": ["L.B. Guanipa"],
        "Independencia": ["L.B. Julian Temistocles Maza"],
        "Sir Arthur McGregor": ["U.E.N. Augusto D'Aubeterre"],
        "Miranda": ["E.B. Antonio Jos\u00e9 de Sucre"],
        "Monagas": ["G.E Dr. Rafael Velasquez Marquez", "U.E. Dr. Pio Ceballo"],
        "Sim\u00f3n Rodr\u00edguez": ["L.N. Dr. Jos\u00e9 Rafael Revenga"],
    },
    "Apure": {
        "Achaguas": ["E.P El Nazareno"],
        "Biruaca": ["EP Leonardo Agrinzones"],
        "Mu\u00f1oz": ["EPP Jos\u00e9 Antonio Paez", "EEP Bruzual", "EP Juan Vicente Torres del Valle"],
        "P\u00e1ez": ["EPB Aramendi", "L.B. Juan de los Santos Contreras"],
        "Pedro Camejo": ["U.E Juan Bautista Este"],
        "R\u00f3mulo Gallegos": ["E.P. Simon Garcia Rosales"],
        "San Fernando": ["E.B.B. Oswaldo del Nogal", "EPB Cristo Rey", "LB Francisco Lazo Mart\u00ed"],
    },
    "Aragua": {
        "Bol\u00edvar": ["UEE Pdte Medina Angarita"],
        "Camatagua": ["UEN Francisco Linares Alc\u00e1ntara"],
        "Tovar": ["UEN Creacion El Pauji"],
        "Alc\u00e1ntara": ["Centro de Par\u00e1lisis Cerebral Linares Alc\u00e1ntara", "Complejo Educativo Nacional Parmanacay"],
        "Lamas": ["GENB Rafael Brice\u00f1o Ortega"],
        "Ribas": ["UEN Vicente Emilio Sojo"],
        "Revenga": ["EBN Juan Uslar"],
        "Libertador": ["LBN Luis Beltran Prieto Figueroa"],
        "Girardot": ["Madre Maria de San Jos\u00e9", "UENB Felipe Guevara Rojas", "Escuela de Artes Visuales Rafael Monasterios", "UEN Jesus Pacheco Rojas", "UENN General Antonio Guzman Blanco", "IEE San Carlos", "ETIN Joaquin Avellan", "UENB Choroni"],
        "Iragorry": ["IEE Padre Antonio Leyh", "UEN Pedro Jos\u00e9 Muguerza", "UEN El Limon"],
        "Ocumare de la Costa de Oro": ["UEN Luciano D'Eluyar"],
        "San Casimiro": ["U.E.N. San Casimiro"],
        "San Sebasti\u00e1n": ["EBN Andres Rodriguez Ramirez", "EBNB Pedro Aldao"],
        "Santiago Mari\u00f1o": ["UEE Humberto Miguel Anzola", "UEP Instituto Andres Bello", "UEN Jos\u00e9 Rafael Revenga"],
        "Michelena": ["TEL Santos Michelena", "UEE Tiara"],
        "Sucre": ["UEN Luis Alejandro Alvarado", "UEE Cesar Zumeta", "EBE Andres Bello", "PEN Andres Bello", "UEN Meregoto", "Academia Gastronomica Aragua"],
        "Urdaneta": ["UEN Inmaculada Concepci\u00f3n"],
        "Zamora": ["EBN Teresa Carre\u00f1o", "EBN Aristides Rojas", "UEP Madre Enriqueta de Lourdes", "Biblioteca Virtual Villa de Cura"],
    },
    "Barinas": {
        "Alberto Arvelo Torrealba": ["EBB Julian Pino", "EBB Rosa Lucia Venero"],
        "Andrés Eloy Blanco": ["EBE Pedro Briceño Mendez"],
        "Antonio José de Sucre": ["EB Barrio Corozal"],
        "Arismendi": ["EB Francisco Lazo"],
        "Barinas": ["GE Estado Guarico", "EB Juan Andres Varela", "EB 24 de Junio", "UE Simon A Jimenez"],
        "Pedraza": ["EBN Gral Tomás Montilla", "EBN José Francisco Jimenez", "Taller de Labores Don Manolo Romero", "EBNC Antonio Lauro", "UE Curbati", "CEIN Curbati", "LN José Francisco Bermudez"],
        "Obispos": ["Complejo Educativo Manuel Piar", "UEN Manuel Palacios", "Liceo Arturo Uslar Prieti"],
        "Bolívar": ["EB Jose Ramon Traspuesto", "LN Simón Bolívar", "EB Barinitas", "IEE Varyna", "EB Miguel Guerrero"],
        "Cruz Paredes": ["G.E Cruz Paredes"],
        "Rojas": ["UEB Ramon Escobar", "EBE Jose Francisco Bermudez", "Liceo Dr. Manuel Heredia Alas"],
        "Sosa": ["Complejo Educativo Aristobulo Isturiz", "Complejo Educativo Francisco de Miranda", "Liceo Ali Primera Rossell", "EB Fernando Peñalver", "EBNB Agustin Isturiz"],
        "Ezequiel Zamora": ["UE Marquez del Pumar"],
    },
    "Bolívar": {
        "El Callao": ["U.E.N. Luis Morillo", "UEN Nicolas Antonio Farreras"],
        "Cedeño": ["U.E.N. Pijiguao", "UEN Lucia Palacios", "U.E.N. Manuel Salvador Gomez", "UEN Cuyuní", "UEN Creación La Urbana"],
        "Gran Sabana": ["Nicolas Meza", "C.E.I. Wara", "U.E.C. Manacru", "U.E.B. Panpatameru", "U.E.N. Juan de Holquin", "L.N. Wadaka Tepuy", "ETA Kumaracay", "UEN Maurak"],
        "Padre Pedro Chien": ["UEN Federico Chirinos"],
        "Piar": ["UEN Simón Barceló", "UEN Auyantepuy", "U.E.N. Morales Marcano", "UEN Tavera Acosta"],
        "Angostura (antiguo Raúl Leoni)": ["EBN Santiago Izaguirre", "UEN Pueblo Guri", "UEN Arturo Lobo Solis", "UEN Lino Maradey"],
        "Heres": ["U.E.N. Tomas de Heres", "LN Fernando Peñalver", "UEN Merida"],
        "Roscio": ["UEN Dalla Costa"],
        "Sifontes": ["UEN Monseñor Francisco J. Zabaleta", "UEN Aurora Miranda", "L.N. Miguel Antonio Mejias", "UEN Juan XXIII"],
        "Sucre": ["ETA Moitaco", "U.E.N. El Guarrey", "UEE La Esmeralda", "UEN Frank Risquez", "UEN Rio Pao"],
        "Caroní": ["E.T.I. Alfredo Maneiro", "UEN Alta Vista Sur", "Centro de Formacion Luis Beltran Prieto Figueroa", "UEN Manuel Piar"],
    },
    "Carabobo": {
        "Bejuma": ["U.E. Arturo Michelena"],
        "Carlos Arvelo": ["U.E. Carlos Arvelo", "U.E Francisco Jose Cisnero"],
        "Diego Ibarra": ["L.N. 181 Aniversario Batalla de Carabobo"],
        "Guacara": ["U.E. Luis Augusto Machado Cisnero"],
        "Juan José Mora": ["E.T.R. Ambrosio Plaza"],
        "Libertador": ["E.B. Prebistero Crispin Perez", "U.E Juan Ramon Gonzalez Baquero"],
        "Los Guayos": ["U.E. Elisa Guevara de Caceres"],
        "Miranda": ["E.B. Daniel Mendoza"],
        "Montalbán": ["E.B. Antonio Herrera Toro"],
        "Naguanagua": ["EBB. Batalla de Bombona"],
        "Puerto Cabello": ["E.T.R. Miguel Peña"],
        "San Diego": ["LN Hipolito Cisnero"],
        "San Joaquín": ["U.E-Dr Rafael Perez"],
        "Valencia": ["U.E Loma de Funval", "U.E. Vicente Emilio Sojo", "E.T.C. Fermin Toro", "L.N Pedro Gual", "U.E. Alejo Zuloaga", "U.E. Cruz Bermudez"],
    },
    "Cojedes": {
        "Anzoátegui": ["EBE Doctor Luis Beltran Prieto Figueroa"],
        "Pao de San Juan Bautista": ["CEN Ana Remigia Tovar", "EPB Jose Antonio Aponte"],
        "Falcón": ["E.B Jose Antonio Anzoategui", "IEE Cojedes"],
        "Girardot": ["EPB Pablo Alejo", "E.B.E. Francisco Villanueva"],
        "Lima Blanco": ["LB Jose Antonio Caballero Malpica"],
        "Ricaurte": ["EPB Pbro Miguel Palaorico"],
        "Rómulo Gallegos": ["E.P.N.B. Juan Ángel Bravo"],
        "San Carlos": ["EPB Carlos Tovar", "LN Eloy Guillermo González", "EPB Eloy Guillermo Gonzalez", "EPB Carlos Vilorio", "IEE Ana Maria Calles", "EP Coaheri"],
        "Tinaco": ["General en Jefe José Laurencio Silva", "EP Aura de Terán", "EPB Jose Laurencio Silva"],
    },
    "Delta Amacuro": {
        "Casacoima": ["UE El Triunfo", "CEIS Bella Vista"],
        "Pedernales": ["EPB Orocoima"],
        "Tucupita": ["Juan Vidal Marcano", "CEIS Raul Van Prag", "UEB Luisa Caceres", "LB José E. Rodo", "LB. Anibal Rojas Perez", "LB. Nestor Luis Perez", "CEIS Teresa Carreño", "LB. Monseñor Argimiro Garcia", "CEIS Ceferino Rojas Dias", "LB. Dionisio Lopez Orihuela", "CEIS La Florida", "EPB La Florida", "UE Dr Samuel Dario Maldonado", "UE Especial Carlos Pérez"],
    },
    "Distrito Capital": {
        "Libertador": ["U.E Simón Bolivar", "UE Maestro Aristobulo Isturiz", "UE Claudio Feliciano", "U.E Pedro Felipe Ledezma", "UE República del Ecuador", "U.E Gran Colombia", "ETCRD Juan España", "UEN Carlos Delgado Chabauld", "Benito Juarez", "C.E. Miguel Antonio Caro", "UEN Sabaneta"],
    },
    "Falcón": {
        "Acosta": ["EPN Antonia Maria Garcia"],
        "Bolívar": ["CEIS Dimas Segovia"],
        "Buchivacoa": ["EP Carlos Lanz"],
        "Cacique Manaure": ["LN Wister Garcia"],
        "Carirubana": ["LN Max de Leon Calles", "EPN Don Rafael Gonzalez Estaba"],
        "Colina": ["LN Juan Crisostomo Falcon"],
        "Dabajuro": ["EPB Guillermo de Leon"],
        "Democracia": ["EPB Fabio Manuel Chirinos"],
        "Falcón": ["EPN Coto Paul"],
        "Federación": ["Liceo Nacional Federacion"],
        "Los Taques": ["LN Antonio Leleux"],
        "Mauroa": ["EPN Elias David Curiel", "IEE Napoleon Reyes"],
        "Miranda": ["LN Esteban Smith Monzón", "LN Cesar Agusto Agreda", "LN Cecilio Acosta"],
        "Monseñor Iturriza": ["LN Ramon Yanez"],
        "Petit": ["CEIS Sara Amelia Salas", "EP Trapichito"],
        "Píritu": ["EP Jose Sirit"],
        "San Francisco": ["LN Jose Felix Ribas", "UE Dominguez Acosta"],
        "Unión": ["LN Domingo G. Couthino"],
        "Urumaco": ["EPN Jose Encarnacion Lopez"],
        "Zamora": ["CE Ezequiel Zamora"],
        "Silva": ["EPN Felipe Esteves"],
    },
    "Guárico": {
        "Camaguán": ["E.B. Joaquin Crespo"],
        "Chaguaramas": ["G.E. Chaguaramas"],
        "El Socorro": ["E.T.A. Henry Pittier"],
        "Miranda": ["U.E. Dr. Pedro Itriago Chacin"],
        "Monagas": ["U.E. Ramón Buenahora"],
        "Roscio": ["G.E. Republica del Brasil"],
        "Mellado": ["U.E.N. Julian Mellado"],
        "Las Mercedes": ["G.E. Rafael Paredes"],
        "Infante": ["U.E.N. Jose Gil Fourtoul"],
        "Ortiz": ["G.E. Juan German Roscio"],
        "Zaraza": ["G.E. Francisco Salias"],
        "San Gerónimo de Guayabal": ["G.E. Carlos del Pozo"],
        "San José de Guaribe": ["E.B.B Monseñor Crespo"],
        "Santa María de Ipire": ["E.B. Antonio de Armas"],
        "Ribas": ["E.B. Arturo Alvarez Alayon"],
    },
    "La Guaira": {
        "Vargas": ["L.B. Juan Jose Mendoza", "Complejo Educativo Taramas", "LB Guaicaipuro", "C.E.I. Josefa Joaquina Sanchez", "L.B. Caruao", "UEE Dr. Alfredo Machado", "L.B. El Junko", "UENB Magaly Espinoza", "U.E.N. Republica de Panamá", "U.E.N. Guaicamacuto", "L.B. Evelia Avilan de Pimentel", "UED Juan Pablo II", "Complejo Educativo Armando Reveron", "E Taller Laboral Simón Bolívar", "E.E. Eugenio Maria de Hostos", "UEN Naiguata"],
    },
    "Lara": {
        "Andrés Eloy Blanco": ["E.B.N El Volcancito"],
        "Crespo": ["U.E.N. Juan Manuel Alamo"],
        "Iribarren": ["E.T.I.R. Pedro León Torres", "E.T.I Lara", "GE Republica de Costa Rica", "U.E.N Dr Jose Gregorio Hernandez", "L.B. Hernan Valera Saavedra", "U.E Stella Cechini", "Escuela Lara", "U.E Nacional Ayacucho", "E.B. Dima Acosta de Alvarez", "U.E Hermano Juan", "UEE José Atanacio Girardot", "EB Boyuare", "U.E.N Francisco de Miranda", "Liceo Bolivariano Tamaca", "E.B.N Boliv Ciudad de Maturin"],
        "Jiménez": ["Liceo Bolivariano Coronel Mariano Peraza", "E.T.A Jose Ramon Rodriguez Torres", "LB Tomás Liscano"],
        "Morán": ["Liceo Bolivariano Doctor Fernando Garmendia Yepez", "U.E.N. Juan Ceferino Castillo", "Liceo Bolivariano Pablo Gil Garcia"],
        "Palavecino": ["Unidad Educativa Valmore Rodriguez"],
        "Simón Planas": ["Escuela Nacional Ature", "EBN Alcides Lozada Torres"],
        "Urdaneta": ["U.E.N. Andrés Bello", "L.B. Egidio Montesinos", "Jose Angel Rodriguez López", "José Pio Tamayo", "E.P.B Dr Francisco Antonio Carreño"],
    },
    "Mérida": {
        "Andrés Bello": ["Liceo Bolivariano La Azulita"],
        "Antonio Pinto Salinas": ["Escuela Basica Carlos Maria Zerpa"],
        "Alberto Adriani": ["U.E Grupo Tovar", "U.E.B Maria de la Concepcion Palacios", "C.E.N Gabriela del Valle Viloria"],
        "Arzobispo Chacón": ["U.E.B. El Molino II", "U.E.B Maldonado Lopez"],
        "Caracciolo Parra Olmedo": ["E.E. Jose Victor Ramirez", "L.B Vicente Campo Elias"],
        "Julio César Salas": ["E.B P Roberto Picon Lares"],
        "Libertador": ["E.T.S.D Domingo Peña", "Talento Deportivo Mérida", "Complejo Educativo Fray Juan Ramos de Lora"],
        "Miranda": ["Liceo Bolivariano Francisco de Paula Andrade"],
        "Obispo Ramos de Lora": ["L.B. José Jesús Osuna Rodríguez"],
        "Pueblo Llano": ["E.B.B Adela Bastidas"],
        "Rangel": ["Liceo Jose Maria Vargas", "Escuela Carmen Elena Lobo", "Liceo Jose Guerrero"],
        "Sucre": ["UEB Genarina Dugarte Contreras", "Liceo Luis Enrique Marquez Barillas", "U.E.B. Estado Nueva Esparta", "G.E. Estado Portuguesa"],
        "Tovar": ["Liceo Bolivariano Felix Roman Duque"],
        "Santos Marquina": ["Liceo Dr Miguel Otero Silva"],
        "Rivas Dávila": ["E.B Flor de Maldonado", "Escuela Estadal Presbiterio Ezequiel Arellano"],
        "Zea": ["E.B Felix Roman Duque"],
        "Campo Elías": ["U.E. Jose Enrique Arias", "Liceo Augusto Rodriguez", "E.B Doña Edelmira Quintero de Lobo"],
        "Justo Briceño": ["U.E.B. San Cristobal", "Liceo Torondoy"],
        "Tulio Febres Cordero": ["Liceo Jose Manuel Briceño Monzillo", "U.E. Dorlisa Guerra", "E.B. Miguel Maria Candales"],
    },
    "Miranda": {
        "Acevedo": ["EN Roscio"],
        "Andrés Bello": ["ENB San José"],
        "Baruta": ["EN Alejo Fortique"],
        "Brión": ["U.E Carmen Guedes Gopar"],
        "Buroz": ["UEN Almirante Luis Brion"],
        "Carrizal": ["UEN Carlos Gauna"],
        "Cristóbal Rojas": ["UEN Creación Charallave"],
        "El Hatillo": ["UEN Conopoima"],
        "Guaicaipuro": ["U.E.N. Francisco de Miranda"],
        "Independencia": ["UEN Juan Antonio Roman Valecillos", "G.E Ezequiel Zamora"],
        "Los Salias": ["UEN Luis Eduardo Egui Arocha"],
        "Páez": ["UE Francisco Arevalo"],
        "Paz Castillo": ["U.E. Dr. Francisco Espejo"],
        "Pedro Gual": ["UEN Cupira"],
        "Plaza": ["UEE Simon Rodriguez"],
        "Simón Bolívar": ["LN Libertador"],
        "Sucre": ["ETI Leonardo Infante"],
        "Lander": ["L.N Juan Antonio Pérez Bonalde"],
        "Urdaneta": ["CEIB Eulalia Buroz"],
        "Zamora": ["UEN Vicente Emilio Sojo"],
    },
    "Monagas": {
        "Acosta": ["UE Manuel Saturnino Peñalver Gomez", "IEE Hugo Rafael Chavez Frias", "CEI Maria Alejandra Silva Maican", "Preescolar Marta Cumbale"],
        "Aguasay": ["EB José Tadeo Monagas", "Liceo Nacional Jose Tadeo Monagas"],
        "Bolívar": ["CEI Maria Montessori", "Preescolar Pedro Gual", "EPB Pedro Gual"],
        "Caripe": ["EPB Eucebio Caripe", "Grupo Escolar Abraham Lincoln"],
        "Cedeño": ["E.B Luis Felipe Turmero Corvo", "EBC Cacique Jose Miguel Guanaguanay", "EB José Francisco Bermudez"],
        "Ezequiel Zamora": ["CEI Centurion", "GE Centurion"],
        "Libertador": ["Liceo Ramón Pierliussi", "CEI Concepcion Aleman de Nuñez", "CE Luisa Otilia Suárez"],
        "Piar": ["ETAR Aragua de Maturin", "EB Olga Betancourt de Perez", "Liceo Nacional Manuel Hernandez Rocca"],
        "Punceres": ["EPE Leonardo Ruiz Pineda"],
        "Sotillo": ["Escuela Uriapara", "CEI Gran Mariscal de Ayacucho", "Compleo Educativo Juana Ramirez"],
        "Uracoa": ["E.P.B Chaimas"],
        "Maturín": ["Centro de Desarrollo Infantil Cacique Guanaguanay", "EB Alejandro de Humboldt", "EB Vicente Salias", "Escuela Adriana Rengel de Sequera", "Biblioteca REDBIM", "Liceo Rafael María Peña Saavedra", "LN Francisco Isnardi", "JI Alejandro de Humbolt", "Grupo Escolar Republica del Uruguay", "EB Manuel Piar", "PE Manuel Piar", "Liceo Nacional Ildefonso Nuñez Mares", "Complejo Educativo Gran Cacique Alberto Tovar", "UECA Dr Braulio Perez Marcio"],
    },
    "Nueva Esparta": {
        "Antolín del Campo": ["UE Antolin del Campo"],
        "Arismendi": ["UE Luisa Caceres de Arismendi", "LTD Guaiqueries de Margarita"],
        "Díaz": ["ETCSA Gran Mariscal de Ayacucho"],
        "García": ["EP Villa Rosa", "UE Pbro. Manuel Montaner Salazar"],
        "Gómez": ["UE Ricardo Marquez Moreno"],
        "Maneiro": ["UE Jose Juaquin de Olmedo"],
        "Marcano": ["UE Antonio Diaz", "ETI Alejandro Hernandez"],
        "Mariño": ["UE Estado Zulia", "UE Jose Joaquin D'Leon", "Liceo Nueva Esparta", "UE Maneiro"],
        "Península de Macanao": ["EB Dr. Francisco Antonio Garcia", "UE Luis Castro", "EB Monseñor Nicolas Eugenio Navarro", "CEI Maestra Nilda Fernández"],
        "Tubores": ["UE Batalla de los Barales"],
        "Villalba": ["EB Dr. Agustin Rafael Hernandez"],
    },
    "Portuguesa": {
        "Araure": ["Complejo Educativo General Paez", "EB Carlos Alberto Pelayo", "UEN Hilarión Lopez"],
        "Agua Blanca": ["UENB Atapaima"],
        "Esteller": ["Liceo Dr. Pablo Herrera Campins", "Escuela Tecnica Piritu", "Complejo Educativo Omaira de Amaro"],
        "Guanare": ["UEN Dr. Cesar Lizardo"],
        "Guanarito": ["Escuela Tecnica Guanarito"],
        "Monseñor José Vicente de Unda": ["Liceo Ramon Parejo Gomez"],
        "Ospino": ["Grupo Escolar Ciudad de Trujillo", "ETA Ospino", "Escuela Bolivariana Cospes", "Escuela Deomedis Leon"],
        "Páez": ["Liceo José Antonio Paez", "Jose Francisco Bermudez"],
        "San Genaro de Boconoíto": ["Escuela Bolivariana Silverina Linares"],
        "San Rafael de Onoto": ["Escuela Menca de Leoni"],
        "Santa Rosalía": ["Liceo Pedro Noguera"],
        "Sucre": ["Escuela Bolivariana Dr. Jaime Cazorla", "CE Guillermo Gamarra Marrero"],
        "Turén": ["Escuela Leticia de Gratero", "Escuela Bolivariana Ezequiel Zamora", "IEE Turén"],
    },
    "Sucre": {
        "Andrés Eloy Blanco": ["UE Rafael Ramos", "LB Andrés Mata", "LB Luis Beltran Prieto Figueroa"],
        "Arismendi": ["UE Dr Juan Pablo Rojas", "UE Guarataro"],
        "Benítez": ["U.E Pablo María Fuentes", "U.E Robert Serra", "U.E Fernanda Bolaños", "U.E Carta de Jamaica"],
        "Bermúdez": ["LB Simón Rodríguez"],
        "Bolívar": ["U.E Jesus Alberto Marcano Echezuria"],
        "Cajigal": ["UE Dr Juan Manuel Cajigal", "U.E Agueda Maria Venturini de Moran"],
        "Cruz Salmerón Acosta": ["UE Cruz Salmeron Acosta", "C.E Eduin Brito", "U.E Lorenza Isava Guevara", "Liceo Bolivariano Creacion Manicuare", "U.E Juana la Avanzadora", "E.B Jose Felix Rivas"],
        "Libertador": ["L.B Bernardo Bermudez"],
        "Mariño": ["L.B Santiago Mariño"],
        "Mejía": ["ETAR Creacion Paradero", "LB Francisco Pérez Aleman"],
        "Montes": ["UE José Luis Ramos", "CE Diego de Vallenilla", "Unidad Educativa Josefa Camejo", "E.B Monseñor Arias Blanco"],
        "Ribero": ["UE Etanislao Rondon", "Liceo Raimundo Martínez Centeno", "U.E Dr. Elisto Silva"],
        "Sucre": ["UE Francisco Badaracco", "UE República Argentina", "EB Santa Teresa del Jesus", "EB Los Chaimas", "E.B Nueva Esparta", "UE Federal Sucre", "L.B Antonio Jose de Sucre", "UEN Nueva Cordoba", "EN Santa Fe", "Aldea Universitaria Cacique Maraguey", "EB Vega Grande", "E.B. Turimiquire", "E.B Mochima"],
        "Valdez": ["U.E. Alejandro Villanueva", "CEI Enea Lopez"],
    },
    "Táchira": {
        "Andrés Bello": ["Escuela Dr. Villalobos"],
        "Antonio Rómulo Costa": ["Escuela Basica Antonio Guzman Blanco"],
        "Ayacucho": ["E.N. Francisco de Paula Reina"],
        "Bolívar": ["Esc Bol Republica de Cuba"],
        "Cárdenas": ["UE Rafael Alvarez"],
        "Córdoba": ["Esc Bol Francisco Javier Garcia de Hevia"],
        "Fernández Feo": ["U.E.E. Ines Labrador de Lara"],
        "García de Hevia": ["E N. Dr. Antonio Rómulo Costa"],
        "Guásimos": ["L.N. Monseñor Ignacio Camargo Alvarez"],
        "Jáuregui": ["U.E. Jesus Manuel Moreno Jauregui"],
        "José María Vargas": ["U.E. Monseñor Acevedo"],
        "Junín": ["Grupo Escolar Estado Sucre", "Centro de Educacion Inicial La Casona"],
        "Michelena": ["ENB. Pbro. Dr. Jose Amando Perez"],
        "Libertador": ["UEB. General Cipriano Castro"],
        "Lobatera": ["Liceo Nacional Francisco Javier Garcia de Hevia"],
        "Panamericano": ["Liceo Monseñor Rafael Arias Blanco"],
        "Delicias": ["UE Arnoldo Gabaldon"],
        "Samuel Darío Maldonado": ["Liceo Nacional Dr. Juan Pablo Perez Alfonzo"],
        "San Cristóbal": ["EB Asisclo Bustamante"],
        "Simón Rodríguez": ["EN Simon León"],
        "Sucre": ["E.N. Juan Bautista Castro"],
        "Torbes": ["IEE Polita de Lima"],
        "Uribante": ["U.E. Sanchez Carrero"],
    },
    "Trujillo": {
        "Boconó": ["Escuela Hilario Pisani Anselmi"],
        "Bolívar": ["Escuela Marcelino Zambrano"],
        "Candelaria": ["Escuela Andres Bello"],
        "Escuque": ["GE Eduardo Blanco"],
        "Monte Carmelo": ["UE Maria Felicita Cadenas"],
        "Pampán": ["Escuela Geronimo Briceño", "Liceo Antonio Sanchez Pacheco"],
        "Rafael Rangel": ["Liceo Emiro Fuenmayor"],
        "Sucre": ["GE Mercedes Diaz"],
        "Trujillo": ["Escuela Americo Briceño"],
        "Valera": ["EB Eloisa Fonseca"],
    },
    "Yaracuy": {
        "Arístides Bastidas": ["CE Luisa de Morales"],
        "Bolívar": ["Escuela Carmelo Fernandez"],
        "Bruzual": ["EPB Escalona y Caltayu"],
        "Cocorote": ["EBP Tovar y Tovar"],
        "Independencia": ["EPB Independencia"],
        "José Antonio Páez": ["ETA Creación Sabana de Parra"],
        "La Trinidad": ["C.E Jose Antonio Paez"],
        "Manuel Monge": ["EB Tomás Jimenez"],
        "Nirgua": ["CE Francisco J. Uztariz"],
        "Peña": ["CE Laureano Villanueva"],
        "San Felipe": ["ETI Romulo Gallegos"],
        "Sucre": ["EPB José Tomas Gonzalez"],
        "Urachiche": ["UE Federico Quiroz"],
        "Veroes": ["EPB Francisco Herrera Vegas"],
    },
    "Zulia": {
        "Baralt": ["CEI José Antonio Paez"],
        "Lagunillas": ["Grupo Escolar Eleazar López Contreras"],
        "Cabimas": ["ETR Hermagora Chavez"],
        "San Francisco": ["CAIPA San Francisco"],
        "Maracaibo": ["EBNB Cristobal Mendoza", "Gran Coquivacoa", "LN Evelia de Pimentel"],
        "Colón": ["Grupo Escolar Almirante Padilla"],
        "Francisco Javier Pulgar": ["Complejo Educativo Bernardo Villasmil"],
        "Guajira": ["Aldea Tawai"],
        "Jesús Enrique Lossada": ["EBN Cristobal Mendoza"],
        "La Cañada de Urdaneta": ["UE Olegario Hernandez"],
        "Mara": ["IEE El Mojan", "UE Dra Blanca Urquiaga"],
        "Machiques de Perijá": ["CEI Maria Teresa del Toro"],
        "Simón Bolívar": ["Escuela Luis Beltran Prieto Figueroa"],
        "Valmore Rodríguez": ["UEN Virgen del Monte Carmelo"],
        "Jesús María Semprún": ["UEN Maura Guerrero"],
        "Rosario de Perijá": ["G E Ziruma"],
        "Miranda": ["Casa de la Cultural"],
    },
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
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN ADMINISTRACIÓN Y GESTIÓN ESCOLAR",
        "LICENCIADO/A EN EDUCACIÓN, MENCIÓN GESTIÓN Y MANTENIMIENTO DEL AMBIENTE ESCOLAR",
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
        "MAESTRÍA EN PEDAGOGÍA CULTURAL E INTERCULTURALIDAD",
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
        trayecto INTEGER DEFAULT 0,
        UNIQUE(programa, materia)
    )""")

    # Migración: agregar columna 'periodo_orden' a mallas (N° de semestre/trimestre)
    try:
        c.execute("ALTER TABLE mallas ADD COLUMN periodo_orden INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # La columna ya existe

    # Migración: agregar columna 'trayecto' a mallas (N° de trayecto 1-4).
    # El trayecto se usa para el recorrido TSU: al TSU se le reconocen los
    # trayectos 1 y 2, por lo que su carga y su certificación arrancan en el 3.
    try:
        c.execute("ALTER TABLE mallas ADD COLUMN trayecto INTEGER DEFAULT 0")
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

    # Migracion: cargar las aulas taller oficiales de la Resolucion N 092.11.2025.
    # Se ejecuta UNA sola vez (sello de version). Borra las aulas anteriores
    # (incluidas las de relleno) y recarga desde AULAS_OFICIALES; los municipios
    # sin sedes en la Resolucion conservan un aula generica para no romper el
    # registro y para que el administrador pueda editarlas a mano.
    VERSION_AULAS = "aulas_resolucion_2025_v1"
    c.execute("SELECT COUNT(*) FROM listas_editables WHERE tipo_lista='meta' AND categoria_padre='version_aulas' AND valor=?",
              (VERSION_AULAS,))
    if c.fetchone()[0] == 0:
        c.execute("DELETE FROM listas_editables WHERE tipo_lista='aula_taller'")
        for estado, municipios in ESTADOS_MUNICIPIOS.items():
            for municipio in municipios:
                sedes = AULAS_OFICIALES.get(estado, {}).get(municipio)
                if sedes:
                    for sede in sedes:
                        c.execute("INSERT OR IGNORE INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES (?, ?, ?)",
                                  ("aula_taller", f"{estado}|{municipio}", sede))
                else:
                    c.execute("INSERT OR IGNORE INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES (?, ?, ?)",
                              ("aula_taller", f"{estado}|{municipio}", f"Aula {municipio} 01"))
        c.execute("INSERT OR IGNORE INTO listas_editables (tipo_lista, categoria_padre, valor) VALUES (?, ?, ?)",
                  ("meta", "version_aulas", VERSION_AULAS))

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
    VERSION_PROGRAMAS = "mallas_2026_v2"
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

# Mallas de las ESPECIALIZACIONES (PNFA) extraidas del formato oficial 2023.
# 9 unidades curriculares por especializacion, 3 por trayecto (3 U.C. c/u).
_MALLAS_PNFA_ESP = {
    'ESPECIALIZACIÓN EN EDUCACIÓN INICIAL': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio critico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Educación Inicial, Retos y Abordaje Humanizador', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación Acción Participativa y Transformadora 2 (IAPT)', 3),
        (2, 'SEGUNDO TRAYECTO', 'Pedagogía Integradora en la Etapa Maternal de Educación Inicial', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Investigación Transformadora 3', 3),
        (3, 'TERCER TRAYECTO', 'Pedagogía Integradora en la Etapa Preescolar de Educación Inicial', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN PRIMARIA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Investigación para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Arriésgate a Transformar ya', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación para la Transformación de la Práctica', 3),
        (2, 'SEGUNDO TRAYECTO', 'El Poder en el Aula y el poder en la Escuela', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Investigación para la Transformación de la Práctica', 3),
        (3, 'TERCER TRAYECTO', 'Maestros y Maestras que leen y Escriben', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN EN CIENCIAS NATURALES': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Investigar para Transformar', 3),
        (1, 'PRIMER TRAYECTO', 'Educación en Ciencias naturales 1', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar: Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación para la Transformación de la Práctica', 3),
        (2, 'SEGUNDO TRAYECTO', 'Educación en Ciencias Naturales 2.', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Investigación para la Transformación de la Práctica', 3),
        (3, 'TERCER TRAYECTO', 'Educación Socio Comunitaria en el Contexto de las Ciencias, la Tecnología y la Producción', 3),
    ],
    'ESPECIALIZACIÓN EN MATEMÁTICA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio Crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Metodología por Proyectos desde la Educación Matemática', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Transformación de la Práctica Concreta de Aprendizaje y Enseñanza de las Matemáticas en el Contexto Educativo Escolar y Circuital.', 3),
        (2, 'SEGUNDO TRAYECTO', 'Etnicidad, Cultura y Matemáticas en la Vida Cotidiana', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e Investigación sobre la Sistematización Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Mapas y Matemática: Una Vía para la conformación ciudadanía', 3),
    ],
    'ESPECIALIZACIÓN EN LENGUA Y COMUNICACIÓN': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I Enfoque Socio critico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Prácticas Sociales de la Lectura y la Escritura', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Formación e Investigación según el Contexto Problemático y Linea de Investigación', 3),
        (2, 'SEGUNDO TRAYECTO', 'Comunicación: Lenguaje y Poder', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario de Investigación III', 3),
        (3, 'TERCER TRAYECTO', 'Narrativa Oral. Escrita y Audiovisual de Venezuela', 3),
    ],
    'ESPECIALIZACIÓN EN GEOGRAFÍA, HISTORIA Y CIUDADANÍA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I Enfoque Socio critico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Petróleo y Soberanía', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Formación e Investigación según el Contexto Problemático y Linea de Investigación a Partir de la Sistematización de los Colectivos de Investigación', 3),
        (2, 'SEGUNDO TRAYECTO', 'Descolonización del Pensamiento acción estratégica para Fortalecer el tejido Identitario nuestro.', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'SeminarioIII: Investigación para la Transformación de la Práctica III: Propuesta Pedagógica en GHC.', 3),
        (3, 'TERCER TRAYECTO', 'La Unión Nuestra Americana en el siglo XX una Reinterpretación desde la Perspectiva de Miranda, Bolivar', 3),
    ],
    'ESPECIALIZACIÓN EN LENGUA EXTRANJERA: INGLÉS': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio Crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'La Percepción de la Identidad Cultural del hablante Bilingue venezolano', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Formación e Investigación según el Contexto problemático y linea de investigación a partir de la sistematización de los Colectivos de Investigación', 3),
        (2, 'SEGUNDO TRAYECTO', 'La Enseñanza de la Producción Oral y la Comprensión Auditiva', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e Investigación sobre la Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Enseñanza del Inglés en la Sociedad de la Información y el Conocimiento', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN FÍSICA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Investigación para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Cuerpo, Corporeidad y Sociedad', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación para la Transformación de la Práctica', 3),
        (2, 'SEGUNDO TRAYECTO', 'Experiencias pedagógicas en el área de Educación Física Planificación Desarrollo y Evaluación', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'SeminarioIII: Investigación para la Transformación de la Práctica', 3),
        (3, 'TERCER TRAYECTO', 'Adaptaciones pedagógicas para la inclusión y la atención de la diversidad en el área de Educación Física', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN EN AGROECOLOGÍA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario 1: Enfoque Socio-Critico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Educación en Agroecologia', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Transformación Pedagógica de la Práctica Educativa', 3),
        (2, 'SEGUNDO TRAYECTO', 'Pedagogía y Agroecoíogia', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Educación Crítica de los Medios de Comunicación para el Trabajo', 3),
        (3, 'TERCER TRAYECTO', 'Recursos para los Aprendizajes en Agroecologia', 3),
    ],
    'ESPECIALIZACIÓN EN DERECHO DE NIÑOS, NIÑAS Y ADOLESCENTES, CONVIVENCIA SOLIDARIA Y PAZ': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio Critico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Derechos Humanos, Cultura y Paz', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación según el Contexto problemático y Línea de lnvestigación a partir de la Sistematización de los Colectivos', 3),
        (2, 'SEGUNDO TRAYECTO', 'Protección Integral y el rol del Defensor en el Marco de las Defensorias Educativas', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e Investigación sobre la Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Prácticas de los Defensores y Defensoras Educativas en el Contexto Venezolano', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN Y TECNOLOGÍA DE LA INFORMACIÓN Y COMUNICACIÓN': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio critico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'OPTATIVA', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación según el Contexto Problematico y Linea de Investigación a Partir de la Sistematización de los Colectivos', 3),
        (2, 'SEGUNDO TRAYECTO', 'OPTATIVA', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e lnvestigación sobre la Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN Y TRABAJO': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio- Critico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'El Proceso Social del Trabajo.', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Transformación Pedagógica de la Práctica Educativa', 3),
        (2, 'SEGUNDO TRAYECTO', 'Encadenamiento Socio Productivo', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Educación Critica de los Medios de Comunicación para el Trabajo', 3),
        (3, 'TERCER TRAYECTO', 'Proyectos del Desarrollo Socio Productivo', 3),
    ],
    'ESPECIALIZACIÓN EN DIRECCIÓN Y SUPERVISIÓN EDUCATIVA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Investigación según el ámbíto de Acción; Argumentación del discurso Cientifico.', 3),
        (1, 'PRIMER TRAYECTO', 'Enfoque Socio - critico para la Transformación de la Práctica', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Formación e Investigación según Contexto Problematico y Lineas de Investigación de los Colectivos de Investigación y Formación', 3),
        (2, 'SEGUNDO TRAYECTO', 'Transformación Pedagógica de la Práctica Educativa', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Educación Critica de los Medios de Comunicación para el Trabajo Colectivo', 3),
    ],
    'ESPECIALIZACIÓN EN LENGUA EXTRANJERA INGLÉS PARA PRIMARIA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Investigación Acción Participativa y Transformadora', 3),
        (1, 'PRIMER TRAYECTO', 'Aproximación a la Lengua Inglés', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación Acción Participativa y Transformadora', 3),
        (2, 'SEGUNDO TRAYECTO', 'El Lenguaje y su uso Cotidiano', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Investigación Acción Participativa y Transformadora', 3),
        (3, 'TERCER TRAYECTO', 'Recursos para la Enseñanza del Inglés en Primaria', 3),
    ],
    'ESPECIALIZACIÓN EN PEDAGOGÍA CULTURAL E INTERCULTURALIDAD': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Escuela Cultura y Diálogo Intercultural', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación según el Contexto problemático y linea de investigación a partir de la sistematización de los Colectivos', 3),
        (2, 'SEGUNDO TRAYECTO', 'Manifestaciones Culturales y Praxis Intercultural desde Venezuela', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e Investigación sobre la Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Hegemonía Contra hegemonía Cultura e Interculturalidad', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN INDÍGENA': [
        (1, 'PRIMER TRAYECTO', 'La Pedagogía del Amor y su Incidencia en la Comunidad Indígena', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I Cosmovisión Indígena para la Transformación de la Práctica Educativa', 3),
        (1, 'PRIMER TRAYECTO', 'Enfoques y Tendencias de la Educación Indígena en Latinoamérica.', 3),
        (2, 'SEGUNDO TRAYECTO', 'Convivencia Escolar, Cultura Propia en el Contexto Indígena', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II Liderazgo en la Escuela ,el Aula y la Comunidad Indígena', 3),
        (2, 'SEGUNDO TRAYECTO', 'Pedagogía y Didáctica de la Educación Indígena', 3),
        (3, 'TERCER TRAYECTO', 'Seminario: La Comunidad Indígena, Estudiantes Indígenas, la Familia y la Escuela, por la Educación Propia.', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Maestras y Maestros que Conozcan y se Apropian de la Realidad Indígena.', 3),
        (3, 'TERCER TRAYECTO', 'Los Pueblos Indígenas desde sus Saberes Ancestrales: Arte, Gastronomía, Socio Productivo.', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN EN FRONTERAS': [
        (1, 'PRIMER TRAYECTO', 'Colectivos de Resistencia e Insurgencia de la Educación en Fronteras', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Critico y Geohistórico en las Prácticas Socioeducativas de la Frontera', 3),
        (1, 'PRIMER TRAYECTO', 'Comportamiento de la Frontera Viva', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien en Fronteras: Educando para la Paz.', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación Acción: Contexto- Educativo en la Frontera', 3),
        (2, 'SEGUNDO TRAYECTO', 'Geopolitica Internacional: Relaciones Internacionales Tratados y Acuerdos', 3),
        (3, 'TERCER TRAYECTO', 'Visión inter y tras Disciplinar en Fronteras', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Estratégias Transformadoras y Sistematización Pedagógica en el Marco del Saber y Trabajo', 3),
        (3, 'TERCER TRAYECTO', 'Nuevas Súbjetividades en la Educación en Fronteras', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN MEDIA TÉCNICA Y PROFESIONAL': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Sociocritico para la Transformación Pedagógica de laPráctica Educativa', 3),
        (1, 'PRIMER TRAYECTO', 'Contexto Problemático y Desarrollo Sostenible de la Educación Técnica en Venezuela', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Formación e lnvestigación Líneas de Investigación para la Transformación Pedagogíca de la Educación Media Técnica', 3),
        (2, 'SEGUNDO TRAYECTO', 'La Formación Cientifica, Tecnológica y Productiva en Educación Macia Técnica', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e lnvestigación, sobre la Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Economia Sustentable a partir del Desarrollo de los Proyectos Productivos en Educación MediaTécnica', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN DE LA SEXUALIDAD': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio-Crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Optativa: La Educación Sexual: ¿Educación Prohibida?', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar: Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Formación e Investigación según el contexto problematico y Linea de Investigación a partir de la Sistematización de los Colectivos de Investigación y Formación', 3),
        (2, 'SEGUNDO TRAYECTO', 'Optativa: La Pedagogía Sexual una mirada desde y hacia Venezuela', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e Investigación sobre la Sistematización y Socialización del Trabajo de Grado.', 3),
        (3, 'TERCER TRAYECTO', 'Pedagogía de la Educación integral de la Sexualidad: estrategias innovadoras', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN DE JÓVENES, ADULTOS Y ADULTAS': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Enfoques y tendencias de la Educación de Jóvenes, Adultas y Adultos', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar: Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Transformación Pedagógica de la Práctica Educativa', 3),
        (2, 'SEGUNDO TRAYECTO', 'Pedagogía y Didáctica en la Educación de Jóvenes, Adultas y Adultos', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Educación Critica de los Medios de Comunicación para el Trabajo', 3),
        (3, 'TERCER TRAYECTO', 'Las y los Jóvenes y la Población Adulta en los Procesos Socio Productivos.', 3),
    ],
    'ESPECIALIZACIÓN EN EDUCACIÓN ESPECIAL': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I : lnvestigación y Métodos Cualitativos en Educación', 3),
        (1, 'PRIMER TRAYECTO', 'Tendencias Actuales en la Educación Especial', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación y Evaluación Educatíva', 3),
        (2, 'SEGUNDO TRAYECTO', 'Atención Educativa Integral en la Moalidad de Educación Especial', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Proyecto de lnvestigación', 3),
        (3, 'TERCER TRAYECTO', 'La lntegración Social: Reto de la Educación Especial en Venezuela', 3),
    ],
}

_MALLAS_OFICIALES.update(_MALLAS_PNFA_ESP)

# ------------------------------------------------------------
# Mallas de las MAESTRÍAS (PNFA_M), extraídas de las certificaciones
# oficiales de calificaciones de la UNEM. Cada maestría tiene 12 unidades
# curriculares de 3 U.C. c/u (36 créditos), organizadas en 4 trayectos de
# 3 unidades. Cada fila es (trayecto, periodo, unidad_curricular, U.C.).
# ------------------------------------------------------------
_MALLAS_MAESTRIA = {
    'MAESTRÍA EN PEDAGOGÍA CULTURAL E INTERCULTURALIDAD': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio Crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Escuela Cultura y Diálogo Intercultural', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación según el Contexto Problemático y Línea de Investigación a partir de la Sistematización de los Colectivos', 3),
        (2, 'SEGUNDO TRAYECTO', 'Manifestaciones Culturales y Praxis Intercultural desde Venezuela', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e Investigación sobre la Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Hegemonía Contra Hegemonía Cultura e Interculturalidad', 3),
        (4, 'CUARTO TRAYECTO', 'La Interculturalidad como Praxis Pedagógica Cotidiana en Venezuela: El Aporte de los Movimientos Indígenas, Afrodescendientes, El Feminismo, Los Biculturales y las Culturas Populares de Resistencia', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario IV: Seminario de Investigación para la Transformación de la Práctica', 3),
        (4, 'CUARTO TRAYECTO', 'La Interculturalidad como Principio Ético-Político', 3),
    ],
    'MAESTRÍA EN MATEMÁTICA PARA EDUCACIÓN MEDIA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio Crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Metodología por Proyectos desde la Educación Matemática', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Transformación de la Práctica Concreta de Aprendizaje y Enseñanza de las Matemáticas en el Contexto Educativo Escolar y Circuital', 3),
        (2, 'SEGUNDO TRAYECTO', 'Etnicidad, Cultura y Matemáticas en la Vida Cotidiana', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e Investigación sobre la Sistematización Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Mapas y Matemática: Una Vía para la Conformación Ciudadanía', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario de Investigación I', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario de Investigación II', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario de Investigación III', 3),
    ],
    'MAESTRÍA EN DIRECCIÓN Y SUPERVISIÓN EDUCATIVA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Investigación según el Ámbito de Acción; Argumentación del Discurso Científico', 3),
        (1, 'PRIMER TRAYECTO', 'Enfoque Socio-Crítico para la Transformación de la Práctica', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Formación e Investigación según Contexto Problemático y Líneas de Investigación de los Colectivos de Investigación y Formación', 3),
        (2, 'SEGUNDO TRAYECTO', 'Transformación Pedagógica de la Práctica Educativa', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Educación Crítica de los Medios de Comunicación para el Trabajo Colectivo', 3),
        (4, 'CUARTO TRAYECTO', 'Referentes Pedagógicos Éticos, Políticos, Geo Históricos y Socioculturales de los Procesos de Dirección y Supervisión', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario IV: Encuentros y Desencuentros Ontológicos, Axiológicos y Metódicos para la Construcción de Procesos de Investigación Educativa y Escolar', 3),
        (4, 'CUARTO TRAYECTO', 'Estudio Comparativo desde la Reflexión Crítica de los Procesos de Dirección y Supervisión Educativa en Venezuela y el Caribe', 3),
    ],
    'MAESTRÍA EN EDUCACIÓN PRIMARIA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Investigación para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Arriésgate a Transformar ya', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación para la Transformación de la Práctica', 3),
        (2, 'SEGUNDO TRAYECTO', 'El Poder en el Aula y el Poder en la Escuela', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Investigación para la Transformación de la Práctica', 3),
        (3, 'TERCER TRAYECTO', 'Maestros y Maestras que Leen y Escriben', 3),
        (4, 'CUARTO TRAYECTO', 'Responsabilidad Sociohistórica del Profesional de la Docencia', 3),
        (4, 'CUARTO TRAYECTO', 'Perspectivas Ontoepistémicas Complejas-Multidimensionales en la Investigación Educativa', 3),
        (4, 'CUARTO TRAYECTO', 'Escenarios Educativos, Pedagógicos y Didácticos para la Transformación de Educación Primaria', 3),
    ],
    'MAESTRÍA EN EDUCACIÓN FÍSICA PARA EDUCACIÓN MEDIA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Investigación para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Cuerpo, Corporeidad y Sociedad', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación para la Transformación de la Práctica', 3),
        (2, 'SEGUNDO TRAYECTO', 'Experiencias Pedagógicas en el área de Educación Física: Planificación, Desarrollo y Evaluación', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Investigación para la Transformación de la Práctica', 3),
        (3, 'TERCER TRAYECTO', 'Adaptaciones Pedagógicas para la Inclusión y la Atención de la Diversidad en el área de Educación Física', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario de Investigación I', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario de Investigación II', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario de Investigación III', 3),
    ],
    'MAESTRÍA EN INGLÉS PARA EDUCACIÓN MEDIA': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio Crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'La Percepción de la Identidad Cultural del Hablante Bilingüe Venezolano', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Formación e Investigación según el Contexto Problemático y Línea de Investigación a partir de la Sistematización de los Colectivos de Investigación', 3),
        (2, 'SEGUNDO TRAYECTO', 'La Enseñanza de la Producción Oral y la Comprensión Auditiva', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Formación e Investigación sobre la Sistematización y Socialización del Trabajo Especial de Grado', 3),
        (3, 'TERCER TRAYECTO', 'Enseñanza del Inglés en la Sociedad de la Información y el Conocimiento', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario de Reflexión Pedagógica 4', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario de Investigación 4', 3),
        (4, 'CUARTO TRAYECTO', 'Optativa: Culturas Originarias e Identidad Nacional / Sociedad Anglófona del Caribe y Africana', 3),
    ],
    'MAESTRÍA EN EDUCACIÓN INICIAL': [
        (1, 'PRIMER TRAYECTO', 'Pedagogía del Amor, del Ejemplo y de la Curiosidad', 3),
        (1, 'PRIMER TRAYECTO', 'Seminario I: Enfoque Socio Crítico para la Transformación de la Práctica', 3),
        (1, 'PRIMER TRAYECTO', 'Educación Inicial, Retos y Abordaje Humanizador', 3),
        (2, 'SEGUNDO TRAYECTO', 'Clima Escolar Cultura Emancipadora para el Vivir Bien', 3),
        (2, 'SEGUNDO TRAYECTO', 'Seminario II: Investigación Acción Participativa y Transformadora 2', 3),
        (2, 'SEGUNDO TRAYECTO', 'Pedagogía Integradora en la Etapa Maternal de Educación Inicial', 3),
        (3, 'TERCER TRAYECTO', 'Estudiante Escuela Familia y Comunidad', 3),
        (3, 'TERCER TRAYECTO', 'Seminario III: Investigación Transformadora 3', 3),
        (3, 'TERCER TRAYECTO', 'Pedagogía Integradora en la Etapa Preescolar de Educación Inicial', 3),
        (4, 'CUARTO TRAYECTO', 'Familias y Comunidades para Diversas Infancias', 3),
        (4, 'CUARTO TRAYECTO', 'Seminario IV: Investigación Transformadora 4', 3),
        (4, 'CUARTO TRAYECTO', 'Educación y Trabajo', 3),
    ],
}

# Mallas de las LICENCIATURAS (recorrido completo, 4 trayectos) extraídas
# del formato oficial. Cada fila es (trayecto, periodo_orden, periodo, materia, U.C.).
# El estudiante TSU usa ESTA MISMA malla, pero se le reconocen los trayectos
# 1 y 2, por lo que su carga y su certificación arrancan en el TRAYECTO 3.
_MALLAS_BACHILLER = {
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN MATEMÁTICA': [
        (1, 1, 'PRIMER SEMESTRE', 'Planificación y análisis de la práctica Docente. Nivel I.A', 3),
        (1, 1, 'PRIMER SEMESTRE', 'Planificación y análisis de la práctica Docente. Nivel I.B', 3),
        (1, 1, 'PRIMER SEMESTRE', 'Pensamiento Pedagogico liberador nuestroamericano', 3),
        (1, 1, 'PRIMER SEMESTRE', 'Matemática y realidad.', 3),
        (1, 1, 'PRIMER SEMESTRE', 'Cantidad y su didáctica.', 3),
        (1, 1, 'PRIMER SEMESTRE', 'Uso racional de los recursos naturales y preservación del planeta I.', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Planificación y análisis de la Práctica Docente. Nivel II.', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Problematización en IAPT I.', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Formacion Ciudadana a la luz de la Constitucion Bolivariana de Venezuela', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Cambio I y su didáctica.', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Forma y dimensión I y su didáctica.', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Uso racional de los recursos naturales y preservación del planeta II.', 3),
        (2, 3, 'TERCER SEMESTRE', 'Intervención fundamentada de la práctica docente. Nivel I.', 3),
        (2, 3, 'TERCER SEMESTRE', 'Construcción de acciones interventoras en IAPT II.', 3),
        (2, 3, 'TERCER SEMESTRE', 'Ciencia, Tecnología y Sociedad para los Procesos Transformadores.', 3),
        (2, 3, 'TERCER SEMESTRE', 'Cambio II y su didáctica.', 3),
        (2, 3, 'TERCER SEMESTRE', 'Forma y dimensión II y su didáctica.', 3),
        (2, 3, 'TERCER SEMESTRE', 'Producción ecológica de alimentos y soberanía alimentaria I.', 3),
        (2, 4, 'CUARTO SEMESTRE', 'Intervención fundamentada de la práctica docente. Nivel II.', 3),
        (2, 4, 'CUARTO SEMESTRE', 'Construcción de acciones interventoras en IAPT II.', 3),
        (2, 4, 'CUARTO SEMESTRE', 'El materialismo historico dialectico para los procesos transformadores', 3),
        (2, 4, 'CUARTO SEMESTRE', 'Cambio III y su didáctica.', 3),
        (2, 4, 'CUARTO SEMESTRE', 'Trigonometría y su didáctica.', 3),
        (2, 4, 'CUARTO SEMESTRE', 'Producción ecológica de alimentos y soberanía alimentaria II.', 3),
        (3, 5, 'QUINTO SEMESTRE', 'Valoración de la Intervención de la práctica docente. Nivel I.', 3),
        (3, 5, 'QUINTO SEMESTRE', 'Ejecución de acciones interventoras en IAPT III', 3),
        (3, 5, 'QUINTO SEMESTRE', 'Consolidación de la Pedagogía Crítica desde la conciencia de Clase.', 3),
        (3, 5, 'QUINTO SEMESTRE', 'Cambio IV y su didáctica.', 3),
        (3, 5, 'QUINTO SEMESTRE', 'Incertidumbre I y su didáctica', 3),
        (3, 5, 'QUINTO SEMESTRE', 'Producción de bienes de consumo masivo I.', 3),
        (3, 6, 'SEXTO SEMESTRE', 'Consolidación de la práctica docente crítica. Nivel I.', 3),
        (3, 6, 'SEXTO SEMESTRE', 'Valoración de acciones interventoras en IAPT II', 3),
        (3, 6, 'SEXTO SEMESTRE', 'Desarrollo de procesos transformadores fundamentados en la formación en la conciencia pedagógica crítica.', 3),
        (3, 6, 'SEXTO SEMESTRE', 'Geometría y su didáctica, entre la teoría axiomática y el contexto.', 3),
        (3, 6, 'SEXTO SEMESTRE', 'Incertidumbre II y su didáctica', 3),
        (3, 6, 'SEXTO SEMESTRE', 'Producción de bienes de consumo masivo II.', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'Valoración de la Intervención de la práctica docente. Nivel II', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'Ejecución de acciones interventoras en IAPT IV', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'Pedagogía Crítica como eje articulador en la concreción del Plan de Patria.', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'CIRCUITO LÒGICO FUNCIONES BOOLE YAPLICACION (ELECTIVA)', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'CONJETURA,PROBAR COMPROBAR EN MATEMATICA (ELECTIVA)', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'Innovación y emprendimientos I.', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'Consolidación de la práctica docente crítica. Nivel II.', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'Valoración de acciones interventoras en IAPT III', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'El Socialismo Bolivariano y la Educación', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'EVALUACION DE LOS APRENDIZAJES EN MATEMATICA (ELECTIVA)', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'LUDICA ANCESTRAL MATEMATICA (ELECTIVA)', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'Innovación y emprendimientos II.', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN FÍSICA': [
        (1, 1, 'PRIMER TRIMESTRE', 'Proyecto Práctica Docente Transformadora I.', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Teoría Social del Aprendizaje: Pedagogía y Didáctica Critica en Ciencia', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Elementos Teórico Prácticos de la Fisica I.A', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Matematica I', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Laboratorio: Vinculación Teórico Prácticos I.A Integración de las Ciencias Naturales', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Proyecto Práctica Docente Transformadora II', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Planificación Educativa por Proyecto', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Elementos Teórico Prácticos de la Fisica I.B', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'MatematicaII', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Laboratorio: Vinculación Teórico Prácticos I.B Integración de las Ciencias Naturales', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Proyecto Práctica Docente Transformadora III', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Evaluación y Valoración de los Aprendizajes', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Elementos Teórico Prácticos de la Fisica I.C', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Matematica III', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Laboratorio: Vinculación Teórico Prácticos I.C Integración de las Ciencias Naturales', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Proyecto Práctica Docente Transformadora IV', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Uso Crítico De las TIC', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Elementos Teórico Prácticos de la Fisica II.A', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Fisica y Entorno Social', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Laboratorio: Vinculación Teórico Prácticos II.A Integración de las Ciencias Naturales', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Proyecto Práctica Docente Transformadora V', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Necesidades Educativas e Integración de Estudiantes con Discapacidad', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Elementos Teórico Prácticos de la Fisica II.B', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Cultura y Ecologia Social', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Laboratorio: Vinculación Teórico Prácticos II.B Integración de las Ciencias Naturales', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto Práctica Docente Transformadora VI', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Educación para la Paz y para la Vida', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Elementos Teórico Prácticos de la Fisica II. C', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Laboratorio: Vinculación Teórico Prácticos II.C Integración de las Ciencias Naturales', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Proyecto P`ractica Docente Transformadora VII', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Seminario: Pensamiento Pedagógico Liberador Nuestroamericano', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Ciencias Naturales para la Transformación Social I', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Laboratorio Procesos Didácticos de la Física I', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Proyecto Práctica Docente Transformadora VIII', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Desarrollo de la Ciudadania Critica', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Ciencias Naturales para la Transformación Social II', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Laboratorio Procesos Didácticos de la Física II', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Proyecto Práctica Docente Transformadora IX', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Procesos Históricos Políticos de la Educación Venezolana Nuestroamericana en el Siglo XXI', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Ciencias Naturales para la Transformacion Social III', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Laboratorio Procesos Didácticos de la Física III', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Proyecto Práctica Docente Transformadora X', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Taller: Metodología IAPT', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Taller: Procesos Didácticos Interdisciplinarios en Fisica', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Laboratorio: Procesos de Investigación, Creación e Innovación en las Ciencias Naturales I', 3),
        (4, 11, 'DECIMO  PRIMER TRIMESTRE', 'Proyecto Práctica Docente Transformadora XI', 3),
        (4, 11, 'DECIMO  PRIMER TRIMESTRE', 'Taller: Sistematización IAPT', 3),
        (4, 11, 'DECIMO  PRIMER TRIMESTRE', 'Laboratorio: Procesos de Investigación, Creación e Innovacián en las Ciencias Naturales II', 3),
        (4, 12, 'DECIMO  SEGUNDO TRIMESTRE', 'Proyecto P`ractica Docente Transformadora XII', 3),
        (4, 12, 'DECIMO  SEGUNDO TRIMESTRE', 'Taller: Planificación IAPT', 3),
        (4, 12, 'DECIMO  SEGUNDO TRIMESTRE', 'Seminario: Procesos Socioproductivos: Física de Nuestros Dias', 3),
        (4, 12, 'DECIMO  SEGUNDO TRIMESTRE', 'Curso: Principios Físicos aplicados a la Producción', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN QUÍMICA': [
        (1, 1, 'PRIMER TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IA', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Teoría Social del Aprendizaje', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Pedagogía y Didáctica Crítica', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Matemática I', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Laboratorio Vinculación Teórico Práctica IA: Integración de las Ciencias Naturales', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IB', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Planificación Educativa por Proyectos', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Matemática II', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Laboratorio Vinculación Teórico Práctica IB: Integración de las Ciencias Naturales', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IC', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Evaluación y Valoración de los Aprendizajes', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Matemática III', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Laboratorio Vinculación Teórico Práctica IC: Integración de las Ciencias Naturales', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IIA', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Uso crítico de las Tecnologías y la Comunicación', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Elementos Teóricos Prácticos de la Química y su aplicación IIA', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Química y Entorno Social I', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Laboratorio Vinculación Teórico Práctica IIA: Integración de las Ciencias Naturales', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IIB', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Necesidades Educativas Especiales e Integración', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Elementos Teóricos Prácticos de la Química y su aplicación IIB', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Química y Entorno Social II', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Laboratorio Vinculación Teórico Práctica IIB: Integración de las Ciencias Naturales', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IIC', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Educación para la Paz y la Vida', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Elementos Teóricos Prácticos de la Química y su aplicación IIC', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Química y Entorno Social III', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Laboratorio Vinculación Teórico Práctica IIC: Integración de las Ciencias Naturales', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IIIA', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Pensamiento Pedagógico Liberador', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Ciencias Naturales para la Transformación Social I', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Laboratorio Procesos Didácticos de la Química I', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IIIB', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Desarrollo de la Ciudadanía Crítica', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Ciencias Naturales para la Transformación Social II', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Laboratorio Procesos Didácticos de la Química II', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IIIC', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Procesos Histórico Políticos de la Educación Nuestro americana del Siglo XX', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Ciencias Naturales para la Transformación Social III', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Laboratorio Procesos Didácticos de la Química III', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IVA', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Taller Metodología Investigación y Acción Participativa', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Laboratorio Procesos de Investigación, Creación e Innovación en las Ciencias Naturales', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Procesos Didácticos Interdisciplinarios en Química', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IVB', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Ciencias Naturales para la Transformación Social IV', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Planificación y Evaluación de la PD- IAPT', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Proyecto: Práctica Docente Transformadora IVC', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Taller Planificación y Evaluación de la PD-IAPT', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Historia y Principios Químicos aplicados a los procesos productivos|', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Seminario Procesos Socio productivos: Las bases de la vida', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN BIOLOGÍA': [
        (1, 1, 'PRIMER TRIMESTRE', 'Proyecto Práctica Docente Transformadora I.A', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Teoría Social del aprendizaje', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Pedagogía y Didactica Critica en el area de Ciencias Naturales', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Elementos Teórico Prácticos de la Biologia I.A', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Biomatematica', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Laboratorio: Integración de las Ciencias Naturales I.A', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Proyecto Práctica Docente Transformadora I.B', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Planificación Educativa por Proyectos', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Elementos Teórico Prácticos de la Biologia I B', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Quimica', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Laboratorio: Integración de las Ciencias Naturales I.B', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Proyecto Práctica Docente Transformadora I.C', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Evaluación y valoración de los aprendizajes', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Elementos Teórico Prácticos de la Biologia I C', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Fisica', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Laboratorio: Integración de las Ciencias Naturales I.C', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Proyecto Práctica Docente Transformadora II.A', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Uso Crítico de las TIC en el Ámbito Educativo', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Elementos Teórico Prácticos de la Biologia II.A', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Biologia Social y Biodiversidad', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Laboratorio Teorico-Practico II.A', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Proyecto Práctica Docente Transformadora II.B', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Necesidades Educativas e Integración', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Elementos Teórico Prácticos de la Biologia II B', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Cultura Ecologica Social', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Laboratorio Teorico-Práctico II.B', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto Práctica Docente Transformadora II.C', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Educación para la Paz y la Vida', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Elementos Teórico Prácticos de la Biología IIC y sus Aplicaciones', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Laboratorio Teorico-Practico II.C', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Proyecto Práctica Docente Transformadora III.A', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Seminario: Pensamiento Pedagógico Liberador Nuestroamericano', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Ciencias Naturales para la transformacion Social I', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Laboratorio Integracion de los procesos Didacticos de la Biologia IA', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Proyecto Práctica Docente Transformadora III.B', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Desarrollo de la Ciudadania Critica', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Ciencias Naturales para la transformacion Social II', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Laboratorio Integración de los procesos Didácticos de la Biologia I.B', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Proyecto Práctica Docente Transformadora III.C', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Procesos Histórico Políticos de la Educación Nuestroamericana', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Ciencias Naturales para la transformacion Social III', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Laboratorio Integración de los procesos Didácticos de la Biologia I.C', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Proyecto Práctica Docente Transformadora IV.A', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Taller: Metodología IAPT', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Taller: Procesos Interdisciplinarios en Biologia', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Laboratorio: Procesos de Investigación. Creacion e innovación de las Ciencias Naturales I', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Proyecto Práctica Docente Transformadora IV.B', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Taller: Sistematización IAPT', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Ciencias Naturales para la Transformación Social IV', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Laboratorio: Procesos de Investigación. Creacion e innovación de las Ciencias Naturales II', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Proyecto Práctica Docente Transformadora IV.C', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Taller: Planificación y Evaluacion IAPT', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Laboratorio: Fundamentos de Biologìa Molecular y Celular en actividades Socioproductivas', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Laboratorio: Procesos de Investigación. Creación e innovación de las Ciencias Naturales III', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN MEMORIA, TERRITORIO Y CIUDADANÍA': [
        (1, 1, 'PRIMER TRIMESTRE', 'Praxis Pedagogica Social Robinsoniana', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Educación Popular', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'El Espacio Geográfico construido', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Interculturalidad. Raíces Indígenas, Criollas y Afrodescendientes', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'La realidad Socio Educativa Venezolana', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Sistema Educativo Venezolano', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Sentido de Territorialidad:', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Realidad socio productiva de la Comunidad y Comuna', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Saberes del Pueblo y Estado Docente', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Protagonista de la vida escolar', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Organización del Espacio en la Venezuela Agraria', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Experiencias de organización en Venezuela', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Cotidianidad Escolar', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Evaluación y Valoración de Aprendizaje', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Soporte Natural de la Diversidad Territorial Venezolana', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Estudios lugarizados del Territorio', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Familia, Escuela, Comunidad y Diversidad Geohistoríca', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Enseñanza y Aprendizaje', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Fronterización del territorio', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Diáspora y neo diáspora en el Espacio Comunal', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Pedagogia y Praxis Contextualizada', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Escuela, Estado Docente y Poderes fácticos', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Historia Regional y Local', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Praxis Docente sustentada en el dialogo de saberes', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Análisis crítico liberador del contexto social', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Movimientos Emancipadores de Nuestramerica', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Integración Latinoamericana y Caribeña', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Potencialidades Docentes para IAPT', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Capitalismo y Socialismo: implicaciones políticas, socioeconómicas y culturales', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Pensamiento Bolivariano', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Ideario Bolivariano VS Doctrina Monroe', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Estado Docente Postulados Ideologicos', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Amenaza Capitalista para el desarrollo de los pueblos', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Republicanismo y Ciudadania', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Descolonización del pensamiento latinoamericano y caribeño', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Educación y Comunicación', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Democratización de la Propiedad de la Tierra y Seguridad Alimentaria', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'La Naturaleza como mercancía en el modo de producción', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Independencia Nacional, Socialismo, Pedagogía y descolonizacion en el contexto local-regional latinoamericano', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Venezuela y su Geopolítica Internacional', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Petróleo y Soberanía', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Socialismo Bolivariano y Pedagogia Critica', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Dependencia y Cultura de la renta', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Autogestión e Independencia', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN FÍSICA': [
        (1, 1, 'PRIMER TRIMESTRE', 'Proyecto I: Bases Teóricas y Legales del Curriculum del Area de Educacion Fisica en Venezuela', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'El docente venezolano', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Educación Física: Conceptualización y Enfoques', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'El Lenguaje del Cuerpo', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Proyecto II: Teoría y Practica de la planificacion Docente', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Educación Fisica y sus Manifestaciones en el Imaginario Social Comunitario', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Pedagogía de la Educación Física', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Educación Física y Convivencia I', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Proyecto III: Evaluación de los Procesos formativos en Educación Física', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Educación Fisica como medio de Transformación Social', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Educación Física y Convivencia II', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Proyecto IV: Conocimiento de la Escuela', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Educación Física y modelos de desarrollo', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Educación Física y Motricidad Humana', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Cultura, Ritmo y movimiento', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Proyecto V: La Investigacion, fundamento de la practica docente', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Psicologia y pensamiento Socio Critico', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Desarrollo Motor', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Educación Física y Procesos Cognitivos', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto VI: La Educación Fisica en el Territorio: Diagnostico y Potencialidades de la Educación Fisica para la Transformación Social', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Educación Física y participacion colectiva en el territorio', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Rondas, Canciones y Juegos Infantiles en la Educación Física', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Ciudadanía, Legislación y Disciplina', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Proyecto VII: Sistematización de los Procesos Pedagógicos del área de Educación Física', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Ciencia, Tecnología y Sociedad para los Procesos Transformadores', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Educación Física Escolar: Medios Educativos para el desarrollo motor', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Pensamiento y Comunicación', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Desarrollo de la Investigación Acción Participativa I', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Educación Física Escolar: Medios Educativos para la Consolidación de la Motricidad Infantil', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Educación Física y Diversidad', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Desarrollo de la Investigación Acción Participativa II', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Educación Física para la Descolonización', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Atención a la Diversidad desde la Educacion Fisica', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Desarrollo de la Investigación Acción Participativa III', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Cuerpo y Pedagogía para la Transformación Pedagógica en el Territorio', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Educación Física y los Medios para su desarrollo I', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Educación Física y Ambiente', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Desarrollo de la Investigación Acción Participativa IV', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Pensamiento Pedagógico, Bolivariano y Latinoamericano', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Educación Física y los Medios para su desarrollo II', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Prevención y Atención de Emergencia en Ambientes Escolares', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Desarrollo de la Investigación Acción Participativa V', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Venezuela Potencia: Aportes desde la Educación Física', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Educación Física y los Medios para su desarrollo Iii', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN INGLÉS': [
        (1, 1, 'PRIMER TRIMESTRE', 'Observación en la Escuela', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Pensamiento Critico', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Introducción al Inglés', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Produccion Escrita', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Conociendo a la Comuna', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Pedagogia Critica', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Inglés en la Escuela Primaria', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Alfabetización Tecnologica', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Diagnóstico y Sistematización', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Didactica Critica', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Inglés en el Contexto Social', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Desarrollo Tecnologico Educativo', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Metodología de la Investigación', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Planes y Proyectos del Sistema Educativo Venezolano', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Inglés en el Contexto Global', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'identidad comunal', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'investigación Educativa', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Planificación Educativa', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Introducción a la Gramática de Inglés', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Diversidad e Inclusion', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Ética de la Investigación Docente', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Filosofía y Pedagogía para la Transformación', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Producción Oral en Inglés', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Valores, familia y sociedad', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Docente y Contexto Educativo', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Ciudadanía y Legislación', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Inglés', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Salud Integral', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'IAP y la Enseñanza del Ingles I', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Psicología Educativa', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Sintaxis', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Ambiente', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'IAP y la Enseñanza del Ingles II', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Planificación de la Enseñanza del Inglés como Lengua Extranjera I', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Fonetica y Fonologia', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Culturas originarias e Identidad', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Praxis Docente en IAPT I', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Evaluación de la enseñanza del Ingles', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Escritura Académica', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Desarrollo Endogeno del Siglo XXI', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Praxis Docente en IAPT II', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Contexto Social Nuestroameriano', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Inglés Técnico', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Cultura Anglófona', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Praxis Docente en IAPT III', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Lenguaje y Comunicación', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Literatura Anglófona', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Ciencia, Tecnología y Comunicación para los Procesos de Transformación', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN INICIAL': [
        (1, 1, 'PRIMER SEMESTRE', 'PROYECTO SOCIO INTEGRADOR: PRACTICA PROFESIONAL TRANSFORMADORA I', 3),
        (1, 1, 'PRIMER SEMESTRE', 'EDUCACIÓN BOLIVARIANA Y SOCIEDAD', 3),
        (1, 1, 'PRIMER SEMESTRE', 'USO SOCIAL DE LA LENGUA', 3),
        (1, 1, 'PRIMER SEMESTRE', 'DESARROLLO Y CRECIMIENTO DEL NIÑO Y LA NIÑA EN EL CONTEXTO VENEZOLANO', 3),
        (1, 1, 'PRIMER SEMESTRE', 'FORMACIÓN SOCIO CRITICA I', 3),
        (1, 1, 'PRIMER SEMESTRE', 'GESTIÓN DE RIEGOS Y PROTECCION CIVIL', 3),
        (1, 2, 'SEGUNDO SEMESTRE', 'PROYECTO SOCIO INTEGRADOR: PRACTICA PROFESIONAL TRANSFORMADORA II', 3),
        (1, 2, 'SEGUNDO SEMESTRE', 'PEDAGOGIA TRANSFORMADORA', 3),
        (1, 2, 'SEGUNDO SEMESTRE', 'CIMIENTOS DE LA EDUCACION INICIAL', 3),
        (1, 2, 'SEGUNDO SEMESTRE', 'LAS TICs EN LA EDUC BOLIVARIANA', 3),
        (1, 2, 'SEGUNDO SEMESTRE', 'LA ACTIVIDAD FISICA , EL JUEGO Y LA RECREACION EL EDUC INICIAL', 3),
        (1, 2, 'SEGUNDO SEMESTRE', 'FORMACIÓN SOCIO CRITICA II', 3),
        (1, 2, 'SEGUNDO SEMESTRE', 'LENGUAS INDIGENAS (ELECTIVA)', 3),
        (2, 3, 'TERCER SEMESTRE', 'PROYECTO SOCIO INTEGRADOR: PRACTICA PROFESIONAL TRANSFORMADORA III', 3),
        (2, 3, 'TERCER SEMESTRE', 'MATEMATICA Y ESTADISTICA APLICADA A LO SOCIO EDUCATIVO', 3),
        (2, 3, 'TERCER SEMESTRE', 'EDUCACION Y TERRITORIALIDAD', 3),
        (2, 3, 'TERCER SEMESTRE', 'CURRICULO EN EL SISTEMA EDUCATIVO VENEZOLANO', 3),
        (2, 3, 'TERCER SEMESTRE', 'TRADICIONES Y COSTUMBRES DEL PUEBLO VENEZOLANO', 3),
        (2, 3, 'TERCER SEMESTRE', 'FORMACIÓN SOCIO CRITICA III', 3),
        (2, 3, 'TERCER SEMESTRE', 'AMBIENTE Y SALUD INTEGRAL', 3),
        (2, 4, 'CUARTO SEMESTRE', 'PROYECTO SOCIO INTEGRADOR: PRACTICA PROFESIONAL TRANSFORMADORA IV', 3),
        (2, 4, 'CUARTO SEMESTRE', 'DESARROLLO SOCIO AFECTIVO Y LA INTELIGENCIA', 3),
        (2, 4, 'CUARTO SEMESTRE', 'RESPONSABILIDAD SOCIAL FAMILIA ESCUELA Y COMUNIDAD', 3),
        (2, 4, 'CUARTO SEMESTRE', 'EDUCACION SEXUAL Y REPREODUCTIVA', 3),
        (2, 4, 'CUARTO SEMESTRE', 'DESEMPEÑO PROFESIONAL DEL DOCENTE DE EDU INICIAL', 3),
        (2, 4, 'CUARTO SEMESTRE', 'FORMACIÓN SOCIO CRITICA IV', 3),
        (2, 4, 'CUARTO SEMESTRE', 'ALIMENTACIÒN SANA Y ALTERNATIVA EN EDUC INICIAL ELECTIVA', 3),
        (3, 5, 'QUINTO  SEMESTRE', 'PROYECTO SOCIO INTEGRADOR: PRACTICA PROFESIONAL TRANSFORMADORA V', 3),
        (3, 5, 'QUINTO  SEMESTRE', 'PLANIFICACIÓN Y EVALUACION EN EDUCACIÓN INICIAL', 3),
        (3, 5, 'QUINTO  SEMESTRE', 'DERECHOS HUMANOS DEL NIÑO Y LA NIÑA EN EL CONTEXTO EDUCATIVO VENEZOLANO', 3),
        (3, 5, 'QUINTO  SEMESTRE', 'PREVENCION Y ATENCION A LA SALUD INTEGRAL DEL NIÑO Y LA NIÑA', 3),
        (3, 5, 'QUINTO  SEMESTRE', 'EXPRESION MUSICAL Y COORPORAL', 3),
        (3, 5, 'QUINTO  SEMESTRE', 'FORMACIÓN SOCIO CRITICA V', 3),
        (3, 5, 'QUINTO  SEMESTRE', 'SABERES ANCESTRALES DE LOS PUEBLOS INDIGENAS', 3),
        (3, 6, 'SEXTO SEMESTRE', 'PROYECTO SOCIO INTEGRADOR: PRACTICA PROFESIONAL TRANSFORMADORA VI', 3),
        (3, 6, 'SEXTO SEMESTRE', 'EDUCACION MATERNAL, LA GESTACION Y EL PARTO HUMANIZADO', 3),
        (3, 6, 'SEXTO SEMESTRE', 'DESARROLLO DE LA LENGUA ORAL Y LENGUA ESCRITA EN ÑINOS DE EDUC INICIAL', 3),
        (3, 6, 'SEXTO SEMESTRE', 'NECESIDADES EDUCATIVAS ESPECIALES Y ATENCION A LA DIVERSIDAD', 3),
        (3, 6, 'SEXTO SEMESTRE', 'EXPRESION TEATRAL Y DANZAS TRADICIONALES DE VENEZUELA', 3),
        (3, 6, 'SEXTO SEMESTRE', 'FORMACIÓN SOCIO CRITICA VI', 3),
        (3, 6, 'SEXTO SEMESTRE', 'CREATIVIDAD E INNOVACIÒN EN EDU INICIAL ELECTIVA', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'PROYECTO SOCIO INTEGRADOR: PRACTICA PROFESIONAL TRANSFORMADORA VII', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'DESARROLLO DE LOS PROCESOS LOGICO MATEMATICOS EN EL NIÑO DE EDUCACION', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'EXPRESION PLASTICA DEL NIÑO EN EDU INICIAL', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'PROMOCION DE LA LECTURA PARA NIÑOS Y NIÑAS DE EDUCACION INICIAL', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'FORMACIÓN SOCIO CRITICA VII', 3),
        (4, 7, 'SEPTIMO SEMESTRE', 'TRANSFORMACIÓN DE MATERIALES Y RECURSOS PARA LA EDUCACIÓN INICIAL', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'PROYECTO SOCIO INTEGRADOR: PRACTICA PROFESIONAL TRANSFORMADORA VIII', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'PROCESOS ADMINISTRATIVOS EN LA EDUC INICIAL EN VENEZUELA', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'MEDIOS DE COMUNICACIÓN EN DUCACION INICIAL', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'FORMACIÓN SOCIO CRITICA VIII', 3),
        (4, 8, 'OCTAVO SEMESTRE', 'CONTINUIDAD AFECTIVA Y ARTICULACIÓN PEDAGOGICA EN EDUC INICIAL ELECTIVA', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN LENGUA': [
        (1, 1, 'PRIMER TRIMESTRE', 'Ideas pedagogicas venezolanas precursoras en la transformacion educativa', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'La lengua como sistema: lo gramatical, ortografico y semantico', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Lenguajes digitales y la Educacion', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Educacion Bolivariana: constructo historico politico', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Discurso texto y contexto', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Poderes creadores del pueblo y educacion', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Sistema Educativo y su comunalizacion', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Lectura sujeto y mundo', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Lengua de la Diversidad Intercultural Venezolana', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Proyecto: Integración Socioeducativa y Lenguaje I', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Didáctica Crítica y Curriculo', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Producir y comprender textos', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Alternativas institucionales para la promocion de las practicas sociales de la Lengua', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Proyecto: Integración Socioeducativa y Lenguaje II', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Psicologia y Educacion', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Planeacion didactica de la lectura y la escritura', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Lenguaje oral y escrito en otros formatos:LSV y Sistema Braille', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto: Integración Socioeducativa y Lenguaje III', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Educación con Sentido de humanidad estetica y docencia', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Literatura para todos y todas', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'El lenguaje de las Artes', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Proyecto: Aplicación del Proyecto I', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Pensamiento Pedagogico Liberador Nuestroamericano I', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Oralidad literatura y comunidad', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'El lenguaje de la imagen', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Proyecto: Aplicación del Proyecto II', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Pensamiento Pedagogico Liberador Nuestroamericano II', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'La palabra en el liceo', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Venezuela contada escrita y filmada', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Proyecto: Aplicación del Proyecto III', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Lectura y escritura para la liberacion', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Historia de la enseñanza de la lengua en Venezuela', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Pueblos y lenguas indigenas', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Proyecto: Sistematización I', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Estudio critico sobre los sistemas de Poder y Dominacion', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Humanidad y literatura.¿ Para jovenes ?', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Lenguaje y Ciber espacio', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Proyecto: Sistematización II', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Independencia Nacional, derechos educativos y formacion de ciudadania', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Leer, oir, escribir y hablar los medios de comunicación', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Leyendo la ciencia', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Proyecto: Sistematización III', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Derechos de la madre tierra', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Literatura y Arte', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Lenguaje y poder', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN PRIMARIA': [
        (1, 1, 'PRIMER TRIMESTRE', 'El Docente y su Contexto Educativo. (Autobiografía y caracterización del entorno)', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Ciencias de la Educación', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Desarrollo humano integral', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Uso social de la lengua (hablar, escuchar, leer y escribir) del docente', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Técnicas e instrumentos de recolección de datos e información', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Pensamiento pedagógico liberador nuestroamericano', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Identidad,arraigo,soberania e Indepencia', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Legislación Educativa y las Leyes del Poder Popular', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Proyecto I: Diagnóstico Participativo Comunitario. (Del registro a la sistematización de experiencias)', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Pensamiento Pedagógico de Simón Rodríguez', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Geo- Histórico', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Fundamentos políticos, filosóficos y pedagógicos de la Educación Bolivariana', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Enfoques y Paradigmas de la Investigación Educativa', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Pedagogía Crítica', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Matemática para la comprensión del mundo y la Vida', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Historia de la Educación Primaria en Venezuela', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Bases teórico-metodológicas de la Sistematización y los Relatos Pedagógicos', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Formación del Nuevo Republicano', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Didáctica crítica e integradora', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Nueva subjetividad y función social del docente bolivariano', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto II: Registro y Sistematización de experiencias como metódica de reflexión y transformación', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Nuevas lógicas de organización y valoración de los procesos educativos', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Planificación y evaluación de los aprendizajes', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Recursos para el Aprendizaje y la Enseñanza', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Bases teórico- metodológicas de la IAPT aplicadas a la educación', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Docencia y práctica reflexiva, innovadora y creativa', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'La Educación Popular como alternativa para el trabajo sociocomunitario en la construcción del aprendizaje', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Integración social e inclusión en la Escuela Primaria', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'IAPT en la praxis pedagógica', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Relaciones de poder', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Perspectivas en la enseñanza y aprendizaje de la lectura y la escritura', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Educación, trabajo social liberador y espacios productivos en la Escuela Primaria', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Proyecto III: Socialización de la práctica pedagógica a través de la Investigación, Acción Participativa y Transformadora', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Cultura de convivencia y paz', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'El arte como modo de vivir, sentir y mirar lo estético', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Educación Intercultural', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Ecología de los saberes', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Educación , Territorialización y Comunalización', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Lenguaje aplicado en las Ciencias y la Tecnología', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Retos y desafíos de la educación ambiental: Formación ecosocialista', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Comunalización de los espacios de formación e investigación', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Democratización del saber científico', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Educación Integral de la Sexualidad en la Educación Primaria', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Orientación Escolar y Familiar', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Proyecto IV: Experiencia de Transformación Comunitaria', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Contexto jurídico – político de la comunalización de la educación en Venezuela', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Educación Física, Deporte y Recreación', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'El cuerpo, la emocionalidad, la afectividad y la lúdica en los procesos de enseñanza y aprendizaje', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN ADMINISTRACIÓN Y GESTIÓN ESCOLAR': [
        (1, 1, 'PRIMER TRIMESTRE', 'Proyecto Práctica Institucional I.A: Reconociendo mi Contexto Laboral', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Enfoque Socio Critico', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Proceso social del Trabajo', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Lengua, Cultura y Comunicación', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Proyecto Práctica Institucional I . B: Reconociendo mi Contexto Laboral', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Filosofía para la Transformación de la realidad social', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Politicas Publicas Educativas en Venezuela', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Formación Ciudadana', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Proyecto Práctica Institucional I.C: Reconociendo mi Contexto Laboral', 3),
        (1, 3, 'TERCER TRIMESTRE', 'La Descolonización del pensamiento. Una visión crítica del servicio público.', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Bases legales de la Administración Publica', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Informatica Tecnología y Sociedad', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Proyecto Práctica Institucional II:A MI Contexto Laboral y la soberania Productiva', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'La Dirección y el Desarrollo Institucional Bolivariano', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'La Planificación Participativa y Democrática en la Gestión Institucional', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Soberanía e identidad Nacional', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Proyecto Práctica Institucional II:B MI Contexto Laboral y la soberania Productiva', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Educación y Economia Social', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Fundamentos de Administración en el Contexto Educativo', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Calidad Educativa y Gestión Institucional', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto Práctica Institucional II:C MI Contexto Laboral y la soberania Productiva', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Educación en, por y para la Producción', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Administración Escolar', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Seminario I: Transformación de la práctica laboral', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Psicologia para la transformación de la realidad social', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Manejo de Riesgos Socioambientales en el Contexto Laboral', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Idiomas', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Proyecto Práctica Institucional III.B Mi contexto Laboral y la Integracion Sociocomunitaria', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Atención al Ciudadano y Etica del servidor Publico', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'La Actividad Física, Bienestar Personal y Salud Social', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Proyecto Práctica Institucional III.C Mi contexto Laboral y la Integración Sociocomunitaria', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Cultura Institucional', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Servicios Educativos y la Administración Escolar en los niveles y modalidades', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Clima Organizacional: Cultura emancipadora para el Vivir Bien.', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Proyecto Práctica Institucional IV:. A Sistematizando la Practica Laboral Transformadora en la institucion Educativa', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Educación Popular', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Evaluación Institucional', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Cultura y Tradiciones Venezolanas', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Proyecto Práctica Institucional IV. B Sistematizando la Practica Laboral Transformadora en la institucion Educativa', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Trabajo voluntario y Productivo', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Uso de las TIC y la Gestión Escolar', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'La Institución Educativa y la Evaluación del Desempeño', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Proyecto Práctica Institucional IV.C :Sistematizando la Practica Laboral Transformadora en la institucion Educativa', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Comunalización y construcción del Poder Popular', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Gestión Educativa', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Seminario II: Transformación de la Práctica Laboral', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN GESTIÓN Y MANTENIMIENTO DEL AMBIENTE ESCOLAR': [
        (1, 1, 'PRIMER TRIMESTRE', 'Proyecto Práctica Institucional I.A: Reconociendo mi Contexto Laboral', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Enfoque Socio Critico', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Proceso social del Trabajo', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Lengua, Cultura y Comunicación', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Proyecto Práctica Institucional I . B: Reconociendo mi Contexto Laboral', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Filosofía para la Transformación de la realidad social', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Politicas Publicas Educativas en Venezuela', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Formación Ciudadana', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Proyecto Práctica Institucional I.C: Reconociendo mi Contexto Laboral', 3),
        (1, 3, 'TERCER TRIMESTRE', 'La Descolonización del pensamiento. Una visión crítica del servicio público.', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Bases legales de la Administración Publica', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Informatica Tecnología y Sociedad', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Proyecto Práctica Institucional II:A MI Contexto Laboral y la soberania Productiva', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'La Dirección y el Desarrollo Institucional Bolivariano', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'La Planificación Participativa y Democrática en la Gestión Institucional', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Soberanía e identidad Nacional', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Proyecto Práctica Institucional II:B MI Contexto Laboral y la soberania Productiva', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Educación y Economia Social', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Cuidado y Mantenimiento de Infraestructuras Educativas', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Mantenimiento y reparación de mobiliarios y equipos en el contexto laboral', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto Práctica Institucional II:C MI Contexto Laboral y la soberania Productiva', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Educación en, por y para la Producción', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Formación profesional en el contexto laboral I', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Seminario I: Transformación de la práctica laboral', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Psicologia para la transformación de la realidad social', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Manejo de Riesgos Socioambientales en el Contexto Laboral', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Idiomas', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Proyecto Práctica Institucional III.B Mi contexto Laboral y la Integracion Sociocomunitaria', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Atención al Ciudadano y Etica del servidor Publico', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'La Actividad Física, Bienestar Personal y Salud Social', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Proyecto Práctica Institucional III.C Mi contexto Laboral y la Integración Sociocomunitaria', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Cultura Institucional', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Seguridad escolar integral', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Clima Organizacional: Cultura emancipadora para el Vivir Bien.', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Proyecto Práctica Institucional IV:. A Sistematizando la Practica Laboral Transformadora en la institucion Educativa', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Educación Popular', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Evaluación Institucional', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Cultura y Tradiciones Venezolanas', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Proyecto Práctica Institucional IV. B Sistematizando la Practica Laboral Transformadora en la institucion Educativa', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Trabajo voluntario y Productivo', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Ambiente,Salud y Desarrollo Sustentable y Sostenible', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'La Institución Educativa y la Evaluación del Desempeño', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Proyecto Práctica Institucional IV.C :Sistematizando la Practica Laboral Transformadora en la institucion Educativa', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Comunalización y construcción del Poder Popular', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Formación profesional en el contexto laboral II', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Seminario II: Transformación de la Práctica Laboral', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN DE JÓVENES, ADULTOS Y ADULTAS': [
        (1, 1, 'PRIMER TRIMESTRE', 'Proyecto Práctica Docente I.A. El Docente y el Contexto Educativo', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Enfoque Socio Critico', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'El Docente y el Contexto Educativo de la Educación de Jóvenes, Adultos y Adultas', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Lengua, Cultura y Comunicación', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Proyecto Práctica Docente I:B El Docente y el Contexto Educativo', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Pensamiento Robinsoniano y Transformación Pedagogícas de la practica educativa', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Formación Ciudadana', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Proyecto Práctica Docente I.C El Docente y el Contexto Educativo', 3),
        (1, 3, 'TERCER TRIMESTRE', 'La Descolonización del pensamiento .Una vision critica de la Educacion de Jovenes y adultos', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Enfoques y tendencias de la Educación de jovenes de adultas y adultos', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Educación Crítica de los Medios', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Proyecto Práctica Docente II.A Mi Práctica Pedagógica y la Soberanía Productiva', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Dirección y Planificación Educativa en la Educación de Jóvenes, Adultos', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Pedagogía y Didáctica de los Componentes de la Educación', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Soberania e identidad Nacional', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Proyecto Práctica Docente II.B Mi Práctica Pedagógica y Soberania Productiva', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Educación en, por y para la producción', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Los Jóvenes, la Población Adulta y sus Necesidades de Aprendizaje', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Calidad educativa y Gestion Institucional', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Proyecto Práctica Docente II.C Mi Práctica Pedagógica y Soberania Productiva', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Pedagogía Productiva', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Diagnóstico y Caracterización de los Procesos Educativos Grupales', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Seminario I: Transformación de la Práctica Pedagógica', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Proyecto Práctica Docente III.A Mi Práctica Pedagógica y la soberania Productiva', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Psicologia Educativa para la transformacion de la Educacion de jovenes, adultas y adultos', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Educación Popular para la construcción del Poder Popular', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Idiomas', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Proyecto Práctica Docente III.C Mi Práctica Pedagógica y la soberania Productiva', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Sociologia Educativa para la transformación de la Educación de jovenes, adultas y adultos', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'La Actividad Física, Bienestar Personal y Salud Social', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Proyecto Práctica Docente III.C Mi Práctica Pedagógica y la soberania Productiva', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Políticas Públicas en Venezuela', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Clima Escolar: Cultura emancipadora para el vivir bien', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Proyecto Práctica Docente IV. A Mi Práctica Pedagógica y la soberania productiva', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Manejo de los riesgos Socio Ambientales', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'La Educación de Jóvenes, Adultas y Adultos y sus necesidades Educativas Especiales', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Cultura y Tradiciones Venezolanas', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Proyecto Práctica Docente IV:. B Mi Práctica Pedagógica y la soberania productiva', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Trabajo Voluntario y Productivo', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Educación a Distancia, Didáctica y Perspectivas de inclusion', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Medios de Comunicación y las Redes Sociales como agentes del Cambio Social Y Organizativo desde la Educacion', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Proyecto Práctica Docente IV.C Mi Práctica Pedagógica y la soberania productiva', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Seminario II: Transformación de la Práctica Pedagógica', 3),
    ],
    'LICENCIADO/A EN EDUCACIÓN, MENCIÓN EDUCACIÓN ESPECIAL': [
        (1, 1, 'PRIMER TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica Caracterización del Ámbito Socio comunitario I', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Sistema Educativo Venezolano', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Educación Especial', 3),
        (1, 1, 'PRIMER TRIMESTRE', 'Neuroanatomía y Neurofisiología Humana', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica Caracterización del Ámbito Socio comunitario II', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Pedagogía como Ciencia Social', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Desarrollo Humano', 3),
        (1, 2, 'SEGUNDO TRIMESTRE', 'Prevención y Atención Integral Temprana', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica Proyecto: Comunalización de la Educación', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Metodología de La Investigación', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Didáctica para la Discapacidad Cognitiva o Retardo Mental', 3),
        (1, 3, 'TERCER TRIMESTRE', 'Psicología Educativa', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Práctica Docente para La Transformación Pedagógica Instrumentos, Técnicas y Recolección de Datos', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Pedagogía del Amor, el Ejemplo y la Curiosidad', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Estrategias Didácticas para estudiantes con Dificultades de Aprendizaje', 3),
        (2, 4, 'CUARTO TRIMESTRE', 'Educación y Trabajo para La Integración Social', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Práctica Docente para La Transformación Pedagógica Sistematización de la práctica educativa especializada', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Pensamiento Pedagógico Liberador Nuestro Americano', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Caracterización del estudiante con Autismo', 3),
        (2, 5, 'QUINTO TRIMESTRE', 'Inclusión social de estudiantes con necesidades educativas especiales y/o con discapacidad', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica Investigación –Acción', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Planificación y Evaluación en el Sistema Escolar', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Didáctica para la Discapacidad Motora o Impedimentos Físicos', 3),
        (2, 6, 'SEXTO TRIMESTRE', 'Rol de la familia en la atención educativa especializada', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica Registro y análisis de datos', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Escuela, Familia y Comunidad y la inclusión social', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Atención Educativa para Personas Sordas y con Discapacidad Auditiva', 3),
        (3, 7, 'SEPTIMO TRIMESTRE', 'Evaluación en Educación Especial', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica Plan de Acción-Ejecución I', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Idioma o Lengua extranjera', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Atención de Estudiantes con Deficiencias Visuales, o Discapacidad Visual', 3),
        (3, 8, 'OCTAVO TRIMESTRE', 'Planificación en Educación Especial', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Práctica Docente Para la Transformación Pedagógica Plan de Acción-Ejecución II', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Uso de las TIC en Educación Especial', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Atención de estudiantes con Talento o alto desempeño', 3),
        (3, 9, 'NOVENO TRIMESTRE', 'Adaptaciones Curriculares en Educación Especial', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica Sistematización y Socialización de la Práctica Pedagógica a través de la Investigación Acción Participativa y Transformadora', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Creatividad e Innovación', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Procesos Didácticos para la Escritura, Lectura y Matemática', 3),
        (4, 10, 'DECIMO TRIMESTRE', 'Desarrollo y estimulación del lenguaje en la infancia', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica I', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Proceso Social de la Lengua', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Lengua de Señas Venezolana', 3),
        (4, 11, 'DECIMO PRIMER TRIMESTRE', 'Educación integral de la sexualidad', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Práctica Docente para la Transformación Pedagógica II', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'El Docente como Líder Social', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Sistema Braille', 3),
        (4, 12, 'DECIMO SEGUNDO TRIMESTRE', 'Educación Física Adaptada', 3),
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


def _trayecto_desde_periodo(texto, periodo_orden=0):
    """Deduce el TRAYECTO (1-4) a partir del texto del período y/o su orden.
    - Si el texto menciona 'TRAYECTO N', usa ese número.
    - Si es 'SEMESTRE N' o 'N TRIMESTRE' (2 por trayecto), trayecto = ceil(N/2).
    - Si es trimestral (3 por trayecto), no siempre se puede deducir por el
      texto; en ese caso el valor real se guarda al sembrar la malla oficial."""
    up = str(texto or "").upper()
    m = re.search(r"TRAYECTO\s*(\d+)", up)
    if m:
        return int(m.group(1))
    po = int(periodo_orden or 0)
    if po <= 0:
        nums = re.findall(r"\d+", up)
        po = int(nums[-1]) if nums else 0
    if po <= 0:
        return 0
    # Por defecto: régimen semestral (2 períodos por trayecto).
    return (po + 1) // 2


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
# LECTURA OPCIONAL DE LA CÉDULA (OCR) PARA AUTOCOMPLETAR DATOS
# ------------------------------------------------------------
# Esta función es TOTALMENTE OPCIONAL y se degrada con elegancia: si el
# equipo no tiene instalado el motor de reconocimiento de texto (Tesseract)
# o las librerías necesarias, no falla; simplemente avisa y el registro
# manual sigue funcionando igual. El objetivo es SOLO ahorrar tecleo: los
# datos leídos SIEMPRE quedan editables por el usuario antes de guardar.

def _ocr_disponible():
    """Indica si el motor de OCR (pytesseract + Tesseract) está disponible.
    Devuelve (ok, mensaje). Nunca lanza excepción."""
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception:
        return False, ("No están instaladas las librerías de lectura de imagen "
                       "(pytesseract / Pillow). El autocompletado por foto no está "
                       "disponible en este equipo; puede escribir los datos a mano.")
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except Exception:
        return False, ("No se encontró el programa Tesseract OCR en este equipo. "
                       "El autocompletado por foto está desactivado; escriba los "
                       "datos a mano (el registro funciona normalmente).")
    return True, ""


def _cedula_imagen_a_texto(file_bytes, filename):
    """Convierte una imagen o PDF de la cédula en texto usando OCR.
    Devuelve (texto, error). Si es PDF, procesa solo la primera página.
    Nunca lanza excepción: cualquier problema se reporta como texto de error."""
    ok, msg = _ocr_disponible()
    if not ok:
        return "", msg
    try:
        import pytesseract
        from PIL import Image, ImageOps
        from io import BytesIO as _BIO
        nombre = (filename or "").lower()
        imagenes = []
        if nombre.endswith(".pdf"):
            try:
                import fitz  # PyMuPDF: convierte PDF a imagen sin programas externos
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if doc.page_count == 0:
                    return "", "El PDF no tiene páginas legibles."
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap(dpi=200)
                imagenes.append(Image.open(_BIO(pix.tobytes("png"))))
                doc.close()
            except Exception:
                return "", ("No se pudo leer el PDF (falta la librería PyMuPDF). "
                            "Suba una foto (JPG/PNG) de la cédula o escriba a mano.")
        else:
            imagenes.append(Image.open(_BIO(file_bytes)))
        # Preprocesado sencillo: escala de grises para mejorar el reconocimiento.
        texto = ""
        idiomas = "spa" if "spa" in _tesseract_idiomas() else "eng"
        for img in imagenes:
            g = ImageOps.grayscale(img)
            try:
                texto += pytesseract.image_to_string(g, lang=idiomas) + "\n"
            except Exception:
                texto += pytesseract.image_to_string(g) + "\n"
        return texto, ""
    except Exception as e:
        return "", f"No se pudo procesar la imagen: {e}"


def _tesseract_idiomas():
    try:
        import pytesseract
        return set(pytesseract.get_languages(config=""))
    except Exception:
        return set()


def _parsear_datos_cedula(texto):
    """Extrae, del texto OCR de la cédula, los campos que se puedan reconocer.
    Devuelve un dict con las claves que logró leer (todas opcionales):
    cedula_tipo, cedula_num, primer_nombre, segundo_nombre,
    primer_apellido, segundo_apellido. El género NO se deduce (no es fiable).
    """
    out = {}
    if not texto:
        return out
    txt = texto.replace("\r", "")
    # --- Cédula: 'V-12.345.678', 'V 12345678', 'E-1234567', etc. ---
    m = re.search(r"\b([VE])[\-\s.]{0,3}(\d{1,3}(?:[.\s]?\d{3}){1,2})\b", txt.upper())
    if not m:
        # A veces sale solo el número largo (7-9 dígitos con puntos).
        m2 = re.search(r"\b(\d{1,3}(?:[.\s]\d{3}){1,2})\b", txt)
        if m2:
            out["cedula_tipo"] = "V"
            out["cedula_num"] = re.sub(r"\D", "", m2.group(1))
    else:
        out["cedula_tipo"] = m.group(1)
        out["cedula_num"] = re.sub(r"\D", "", m.group(2))
    # --- Nombres y apellidos: se buscan por etiquetas de la cédula ---
    lineas = [l.strip() for l in txt.split("\n")]
    def _valor_tras_etiqueta(claves):
        for i, l in enumerate(lineas):
            lu = l.upper()
            for k in claves:
                if k in lu:
                    # El valor puede venir en la misma línea (tras ':') o en la siguiente.
                    resto = l.split(":", 1)[1] if ":" in l else ""
                    resto = re.sub(r"(?i)" + "|".join(claves), "", resto).strip(" :-")
                    if _es_nombre(resto):
                        return resto
                    for j in range(i + 1, min(i + 3, len(lineas))):
                        if _es_nombre(lineas[j]):
                            return lineas[j].strip()
        return ""
    def _es_nombre(s):
        s = (s or "").strip()
        if len(s) < 2:
            return False
        letras = [c for c in s if c.isalpha()]
        return len(letras) >= 2 and len(letras) >= 0.6 * len(s.replace(" ", ""))
    apellidos = _valor_tras_etiqueta(["APELLIDOS", "APELLIDO"])
    nombres = _valor_tras_etiqueta(["NOMBRES", "NOMBRE"])
    if apellidos:
        partes = apellidos.upper().split()
        out["primer_apellido"] = partes[0] if partes else ""
        out["segundo_apellido"] = partes[1] if len(partes) > 1 else ""
    if nombres:
        partes = nombres.upper().split()
        out["primer_nombre"] = partes[0] if partes else ""
        out["segundo_nombre"] = partes[1] if len(partes) > 1 else ""
    return out


# ------------------------------------------------------------
# MALLAS CURRICULARES (materias con U.C. por programa)
# ------------------------------------------------------------

def obtener_malla(programa, incluir_introductorio=True):
    """Lista de materias del programa, en orden. Cada item es un dict:
    {orden, periodo, materia, creditos, es_introductorio}."""
    conn = get_db()
    c = conn.cursor()
    if incluir_introductorio:
        c.execute("""SELECT orden, periodo, materia, creditos, es_introductorio, periodo_orden, trayecto
                     FROM mallas WHERE programa=? ORDER BY orden, id""", (programa,))
    else:
        c.execute("""SELECT orden, periodo, materia, creditos, es_introductorio, periodo_orden, trayecto
                     FROM mallas WHERE programa=? AND es_introductorio=0 ORDER BY orden, id""", (programa,))
    filas = c.fetchall()
    conn.close()
    return [{"orden": r[0], "periodo": r[1] or "", "materia": r[2],
             "creditos": r[3] or 0, "es_introductorio": int(r[4] or 0),
             "periodo_orden": int(r[5] or 0), "trayecto": int(r[6] or 0)} for r in filas]


def guardar_materia_malla(programa, periodo, materia, creditos, es_introductorio, orden=None):
    """Agrega o actualiza una materia de la malla de un programa."""
    conn = get_db()
    c = conn.cursor()
    if orden is None:
        c.execute("SELECT COALESCE(MAX(orden),0)+1 FROM mallas WHERE programa=?", (programa,))
        orden = c.fetchone()[0]
    try:
        c.execute("""INSERT INTO mallas (programa, orden, periodo, materia, creditos, es_introductorio, periodo_orden, trayecto)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (programa, int(orden), periodo, materia, float(creditos or 0), int(es_introductorio), _orden_desde_periodo(periodo, int(orden)), _trayecto_desde_periodo(periodo, _orden_desde_periodo(periodo, int(orden)))))
        ok = True
    except sqlite3.IntegrityError:
        # Ya existe esa materia en ese programa -> actualizar
        c.execute("""UPDATE mallas SET orden=?, periodo=?, creditos=?, es_introductorio=?, periodo_orden=?, trayecto=?
                     WHERE programa=? AND materia=?""",
                  (int(orden), periodo, float(creditos or 0), int(es_introductorio), _orden_desde_periodo(periodo, int(orden)), _trayecto_desde_periodo(periodo, _orden_desde_periodo(periodo, int(orden))), programa, materia))
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
        c.execute("""INSERT OR IGNORE INTO mallas (programa, orden, periodo, materia, creditos, es_introductorio, periodo_orden, trayecto)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (programa, orden, _per, f.get("materia", ""),
                   float(f.get("creditos", 0) or 0), int(f.get("es_introductorio", 0)), int(_po), _trayecto_desde_periodo(_per, int(_po))))
        orden += 1
    conn.commit()
    conn.close()


def _seed_mallas_oficiales(c):
    """Carga UNA sola vez las mallas oficiales reconocidas de los documentos
    aprobados. Usa un sello de versión y no pisa mallas propias del administrador.

    v4: (1) se eliminan los antiguos programas 'TSU ...' separados y sus mallas
    contaminadas; (2) se recargan LIMPIAS las 14 licenciaturas (recorrido
    completo, 4 trayectos) guardando el TRAYECTO por materia; (3) se completa
    la columna 'trayecto' de las demás mallas oficiales ya sembradas."""
    VERSION = "mallas_oficiales_v5"
    c.execute("SELECT COUNT(*) FROM listas_editables WHERE tipo_lista='meta' AND categoria_padre='mallas_seed' AND valor=?", (VERSION,))
    if c.fetchone()[0] > 0:
        return

    # (1) Elimina los programas 'TSU EN EDUCACIÓN ...' que ya no existen como
    # tipo aparte (el TSU pasó a ser un marcador dentro de cada licenciatura).
    c.execute("DELETE FROM mallas WHERE programa LIKE 'TSU EN EDUCACI%'")

    # (2) Licenciaturas del recorrido completo: se recargan LIMPIAS con trayecto.
    for prog, filas in _MALLAS_BACHILLER.items():
        c.execute("DELETE FROM mallas WHERE programa=?", (prog,))
        orden = 1
        for (tray, po, per, mat, uc) in filas:
            c.execute("""INSERT OR IGNORE INTO mallas (programa, orden, periodo, materia, creditos, es_introductorio, periodo_orden, trayecto)
                         VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
                      (prog, orden, per, mat, float(uc), int(po), int(tray)))
            orden += 1

    # (3) Resto de mallas oficiales (Inicial / Especial / Especializaciones):
    #     se siembran si faltan y se completa la columna 'trayecto'.
    for prog, filas in _MALLAS_OFICIALES.items():
        c.execute("SELECT COUNT(*) FROM mallas WHERE programa=?", (prog,))
        if c.fetchone()[0] == 0:
            orden = 1
            for (po, per, mat, uc) in filas:
                c.execute("""INSERT OR IGNORE INTO mallas (programa, orden, periodo, materia, creditos, es_introductorio, periodo_orden, trayecto)
                             VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
                          (prog, orden, per, mat, float(uc), int(po), _trayecto_desde_periodo(per, int(po))))
                orden += 1
        # Completa 'trayecto' en filas que aún lo tengan en 0.
        c.execute("SELECT id, periodo, periodo_orden FROM mallas WHERE programa=? AND (trayecto IS NULL OR trayecto=0)", (prog,))
        for _id, _per, _po in c.fetchall():
            _tr = _trayecto_desde_periodo(_per, int(_po or 0))
            if _tr:
                c.execute("UPDATE mallas SET trayecto=? WHERE id=?", (int(_tr), _id))

    # (4) Maestrías (PNFA_M): 12 U.C. de 3 créditos en 4 trayectos. Se siembran
    #     si faltan, guardando el trayecto explícito de cada unidad curricular.
    for prog, filas in _MALLAS_MAESTRIA.items():
        c.execute("SELECT COUNT(*) FROM mallas WHERE programa=?", (prog,))
        if c.fetchone()[0] == 0:
            orden = 1
            for (tray, per, mat, uc) in filas:
                c.execute("""INSERT OR IGNORE INTO mallas (programa, orden, periodo, materia, creditos, es_introductorio, periodo_orden, trayecto)
                             VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
                          (prog, orden, per, mat, float(uc), int(tray), int(tray)))
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


# ============================================================
# CARGA MASIVA DESDE EXCEL (para poblaciones sin internet)
# Un operador llena la plantilla en Excel, la envía por correo y aquí se
# importa de una sola vez. Tolerante a fallos: los registros con problema
# se reportan y NO detienen la carga del resto.
# ============================================================

def _cm_norm(v):
    """Normaliza un valor de celda a texto limpio."""
    if v is None:
        return ""
    s = str(v).strip()
    if s.lower() in ("nan", "none", "nat"):
        return ""
    return s


def _cm_cedula(v):
    """Deja la cédula solo con dígitos."""
    s = _cm_norm(v)
    s = s.replace("V-", "").replace("v-", "").replace("V", "").replace(".", "").replace("-", "").replace(" ", "")
    return "".join(ch for ch in s if ch.isdigit())


def _cm_mapas_programas():
    """Devuelve (programa_canonico, programa->tipo) para reconocer nombres."""
    canon = {}
    prog_a_tipo = {}
    for tipo, lst in TIPOS_PROGRAMA_PROGRAMAS.items():
        for nombre in lst:
            canon[nombre.upper().strip()] = nombre
            prog_a_tipo[nombre.upper().strip()] = tipo
    return canon, prog_a_tipo


def generar_plantilla_carga_masiva():
    """Genera el archivo Excel (plantilla) que el operador debe llenar.
    Trae 4 hojas: EXPEDIENTES, NOTAS, LISTAS (valores válidos) e INSTRUCCIONES."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    azul = PatternFill("solid", fgColor="1F4E79")
    gris = PatternFill("solid", fgColor="D9E1F2")
    blanco_bold = Font(color="FFFFFF", bold=True)
    negrita = Font(bold=True)
    borde = Border(*[Side(style="thin", color="BFBFBF")] * 4)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)

    wb = openpyxl.Workbook()

    # ---- Hoja EXPEDIENTES ----
    ws = wb.active
    ws.title = "EXPEDIENTES"
    cols_exp = [
        "ESTADO", "MUNICIPIO", "AULA TALLER", "NOMBRES", "APELLIDOS", "CEDULA",
        "CORREO", "SEXO (M/F)", "TIPO PROGRAMA", "PROGRAMA",
        "TIPO ESTUDIANTE (BACHILLER/TSU)", "TIPO EXPEDIENTE",
        "PERIODO INICIO (ej 2020-I)", "PERIODOS POR ANIO (2/3/4)",
        "PERIODO CULMINACION", "OBSERVACIONES",
    ]
    for j, c in enumerate(cols_exp, start=1):
        cell = ws.cell(row=1, column=j, value=c)
        cell.fill = azul
        cell.font = blanco_bold
        cell.alignment = centro
        cell.border = borde
        ws.column_dimensions[cell.column_letter].width = max(14, min(38, len(c) + 2))
    ejemplo = [
        "Miranda", "Guaicaipuro", "", "MARIA JOSE", "PEREZ GOMEZ", "12345678",
        "correo@ejemplo.com", "F", "PNFA_E",
        "ESPECIALIZACION EN EDUCACION INICIAL", "", "EGRESADO",
        "2023-I", "3", "2023-III", "Fila de ejemplo: puede borrarla",
    ]
    for j, v in enumerate(ejemplo, start=1):
        cell = ws.cell(row=2, column=j, value=v)
        cell.font = Font(italic=True, color="808080")
        cell.border = borde
    ws.freeze_panes = "A2"

    # ---- Hoja NOTAS ----
    ws2 = wb.create_sheet("NOTAS")
    cols_not = ["CEDULA", "PROGRAMA", "MATERIA (UNIDAD CURRICULAR)", "U.C. (creditos)", "CALIFICACION", "PERIODO (ej 2023-I)"]
    for j, c in enumerate(cols_not, start=1):
        cell = ws2.cell(row=1, column=j, value=c)
        cell.fill = azul
        cell.font = blanco_bold
        cell.alignment = centro
        cell.border = borde
        ws2.column_dimensions[cell.column_letter].width = max(14, min(48, len(c) + 2))
    ws2.cell(row=2, column=1, value="12345678").font = Font(italic=True, color="808080")
    ws2.cell(row=2, column=2, value="ESPECIALIZACION EN EDUCACION INICIAL").font = Font(italic=True, color="808080")
    ws2.cell(row=2, column=3, value="PEDAGOGIA DEL AMOR, DEL EJEMPLO Y DE LA CURIOSIDAD").font = Font(italic=True, color="808080")
    ws2.cell(row=2, column=4, value="").font = Font(italic=True, color="808080")
    ws2.cell(row=2, column=5, value="19").font = Font(italic=True, color="808080")
    ws2.cell(row=2, column=6, value="2023-I").font = Font(italic=True, color="808080")
    ws2.freeze_panes = "A2"

    # ---- Hoja LISTAS (valores válidos para copiar/pegar) ----
    ws3 = wb.create_sheet("LISTAS")
    ws3.cell(row=1, column=1, value="TIPOS DE PROGRAMA (copie el codigo tal cual)").font = negrita
    ws3.cell(row=1, column=1).fill = gris
    r = 2
    for tipo in TIPOS_PROGRAMA_PROGRAMAS.keys():
        ws3.cell(row=r, column=1, value=tipo)
        r += 1
    ws3.cell(row=1, column=3, value="PROGRAMAS (nombre exacto)").font = negrita
    ws3.cell(row=1, column=3).fill = gris
    ws3.cell(row=1, column=4, value="TIPO").font = negrita
    ws3.cell(row=1, column=4).fill = gris
    r = 2
    for tipo, lst in TIPOS_PROGRAMA_PROGRAMAS.items():
        for nombre in lst:
            ws3.cell(row=r, column=3, value=nombre)
            ws3.cell(row=r, column=4, value=tipo)
            r += 1
    ws3.cell(row=1, column=6, value="ESTADOS").font = negrita
    ws3.cell(row=1, column=6).fill = gris
    r = 2
    for est in ESTADOS_MUNICIPIOS.keys():
        ws3.cell(row=r, column=6, value=est)
        r += 1
    for col, w in (("A", 16), ("C", 60), ("D", 10), ("F", 22)):
        ws3.column_dimensions[col].width = w

    # ---- Hoja INSTRUCCIONES ----
    ws4 = wb.create_sheet("INSTRUCCIONES")
    pasos = [
        "COMO USAR ESTA PLANTILLA",
        "",
        "1. Llene la hoja EXPEDIENTES: una fila por cada estudiante.",
        "   - CEDULA es obligatoria y no debe repetirse.",
        "   - ESTADO, TIPO PROGRAMA y PROGRAMA deben escribirse como en la hoja LISTAS.",
        "   - Si no sabe el TIPO PROGRAMA, dejelo vacio: el sistema lo deduce del PROGRAMA.",
        "   - SEXO: escriba M o F (para redactar bien el titulo).",
        "   - TIPO ESTUDIANTE: BACHILLER o TSU (solo si aplica).",
        "   - TIPO EXPEDIENTE: INGRESO, PROSECUCION o EGRESADO.",
        "",
        "2. (Opcional) Llene la hoja NOTAS: una fila por cada materia del estudiante.",
        "   - CEDULA debe coincidir con la de la hoja EXPEDIENTES.",
        "   - Si deja U.C. vacio, el sistema toma los creditos de la malla del programa.",
        "   - CALIFICACION: numero de 1 a 20.",
        "",
        "3. Guarde el archivo y enviela al administrador. El la sube en",
        "   'Carga Masiva (Excel)' y el sistema importa todo de una vez.",
        "",
        "NOTA: puede borrar las filas de ejemplo (en gris) antes de enviar.",
    ]
    for i, t in enumerate(pasos, start=1):
        cell = ws4.cell(row=i, column=1, value=t)
        if i == 1:
            cell.font = Font(bold=True, size=14, color="1F4E79")
    ws4.column_dimensions["A"].width = 90

    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()


def procesar_carga_masiva_expedientes(df, usuario):
    """Importa la hoja EXPEDIENTES. Devuelve (ok, fallidos, errores[]).
    Tolerante a fallos: cada fila se procesa aislada."""
    ok = 0
    fallidos = 0
    errores = []
    canon, prog_a_tipo = _cm_mapas_programas()
    estados_map = {k.upper(): k for k in ESTADOS_MUNICIPIOS}

    def col(row, *nombres):
        for n in nombres:
            for c in df.columns:
                if str(c).strip().upper().startswith(n):
                    return row[c]
        return ""

    for idx, row in df.iterrows():
        fila_excel = idx + 2
        try:
            ced = _cm_cedula(col(row, "CEDULA", "C\u00c9DULA"))
            nombres = _cm_norm(col(row, "NOMBRES", "NOMBRE"))
            if not ced and not nombres:
                continue  # fila vacía
            if not ced:
                raise ValueError("Falta la cédula")
            programa_in = _cm_norm(col(row, "PROGRAMA"))
            programa = canon.get(programa_in.upper(), programa_in.upper())
            tipo_in = _cm_norm(col(row, "TIPO PROGRAMA", "TIPO_PROGRAMA")).upper()
            if tipo_in not in TIPOS_PROGRAMA_PROGRAMAS:
                tipo_in = prog_a_tipo.get(programa.upper(), "")
            if not tipo_in:
                raise ValueError("No se pudo determinar el TIPO PROGRAMA (revise el nombre del PROGRAMA)")
            estado_in = _cm_norm(col(row, "ESTADO"))
            estado = estados_map.get(estado_in.upper(), estado_in)
            tipo_est = _cm_norm(col(row, "TIPO ESTUDIANTE")).upper()
            tipo_est = "TSU" if tipo_est.startswith("TSU") else ("BACHILLER" if tipo_est.startswith("BACH") else "")
            ppa_raw = _cm_norm(col(row, "PERIODOS POR"))
            try:
                ppa = int(float(ppa_raw)) if ppa_raw else 2
            except ValueError:
                ppa = 2
            sexo = _cm_norm(col(row, "SEXO")).upper()[:1]
            datos = {
                "estado": estado,
                "municipio": _cm_norm(col(row, "MUNICIPIO")),
                "aula_taller": _cm_norm(col(row, "AULA")),
                "nombres": nombres.upper(),
                "apellidos": _cm_norm(col(row, "APELLIDOS", "APELLIDO")).upper(),
                "cedula": ced,
                "correo_titular": _cm_norm(col(row, "CORREO")),
                "tipo_programa": tipo_in,
                "programa": programa,
                "tipo_expediente": (_cm_norm(col(row, "TIPO EXPEDIENTE")).upper() or "EGRESADO"),
                "periodo_culminacion": _cm_norm(col(row, "PERIODO CULMINACION", "PERIODO CULMINACI")),
                "sexo": sexo,
                "tipo_estudiante": tipo_est,
                "periodo_inicio": _cm_norm(col(row, "PERIODO INICIO")),
                "periodos_por_anio": ppa,
                "observaciones": _cm_norm(col(row, "OBSERVACIONES", "OBSERVACION")),
                "registrado_por": usuario,
            }
            exito, msg = registrar_expediente(datos)
            if exito:
                ok += 1
            else:
                fallidos += 1
                errores.append("Fila %d (%s): %s" % (fila_excel, ced, msg))
        except Exception as e:  # noqa: BLE001 - tolerante a fallos por fila
            fallidos += 1
            errores.append("Fila %d: %s" % (fila_excel, e))
    return ok, fallidos, errores


def procesar_carga_masiva_notas(df):
    """Importa la hoja NOTAS. Devuelve (materias_ok, materias_fallidas, errores[]).
    Agrupa por (cédula, programa) y completa U.C. desde la malla si faltan."""
    ok = 0
    fallidos = 0
    errores = []
    canon, _ = _cm_mapas_programas()

    def col(row, *nombres):
        for n in nombres:
            for c in df.columns:
                if str(c).strip().upper().startswith(n):
                    return row[c]
        return ""

    grupos = {}
    for idx, row in df.iterrows():
        ced = _cm_cedula(col(row, "CEDULA", "C\u00c9DULA"))
        materia = _cm_norm(col(row, "MATERIA", "UNIDAD")).upper()
        if not ced or not materia:
            continue
        prog_in = _cm_norm(col(row, "PROGRAMA"))
        prog = canon.get(prog_in.upper(), prog_in.upper())
        nota = _cm_norm(col(row, "CALIFICACION", "NOTA"))
        uc_raw = _cm_norm(col(row, "U.C", "UC", "CREDITO"))
        try:
            uc = float(uc_raw) if uc_raw else 0.0
        except ValueError:
            uc = 0.0
        periodo = _cm_norm(col(row, "PERIODO"))
        grupos.setdefault((ced, prog), {})[materia] = (uc, nota, periodo)

    for (ced, prog), materias in grupos.items():
        try:
            malla = {}
            if prog:
                for m in obtener_malla(prog, incluir_introductorio=True):
                    malla[m["materia"].upper()] = m["creditos"]
            arregladas = {}
            for mat, (uc, nota, per) in materias.items():
                if (not uc) and mat in malla:
                    uc = malla[mat]
                arregladas[mat] = (uc, nota, per)
            guardar_notas(ced, prog, arregladas)
            ok += len(arregladas)
        except Exception as e:  # noqa: BLE001
            fallidos += len(materias)
            errores.append("C\u00e9dula %s: %s" % (ced, e))
    return ok, fallidos, errores


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

    # ----- TSU: solo se certifican las materias del TRAYECTO 3 en adelante.
    # A un TSU se le reconocen los dos primeros trayectos (T1 y T2), así que su
    # carga y su certificación arrancan en el TRAYECTO 3 (trayectos 3 y 4). El
    # trayecto viene guardado por materia en la malla, así que el filtro es
    # directo y funciona tanto en régimen semestral como trimestral.
    if es_tsu:
        malla = [m for m in malla if int(m.get("trayecto") or 0) >= 3]

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
            "📥 Carga Masiva (Excel)",
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
            "📥 Carga Masiva (Excel)",
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
                   "reg_nombres", "reg_apellidos",
                   "reg_primer_nombre", "reg_segundo_nombre",
                   "reg_primer_apellido", "reg_segundo_apellido",
                   "reg_cedula_tipo", "reg_cedula_num", "reg_correo",
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

    # --------------------------------------------------------
    # OPCIONAL: leer la cédula (foto o PDF) para autocompletar
    # --------------------------------------------------------
    with st.expander("🪪 (Opcional) Autocompletar desde una foto o PDF de la cédula", expanded=False):
        _ocr_ok, _ocr_msg = _ocr_disponible()
        st.caption(
            "Suba una **foto nítida** o un **PDF** de la cédula y el sistema intentará "
            "leer la cédula, los nombres y los apellidos para ahorrarle tecleo. "
            "**Siempre revise y corrija** los datos antes de registrar. La imagen se "
            "procesa solo en este equipo y **no se guarda**. El género no se deduce "
            "automáticamente porque la cédula no lo indica de forma fiable."
        )
        if not _ocr_ok:
            st.info(_ocr_msg)
        else:
            _ced_file = st.file_uploader(
                "🖼️ Imagen o PDF de la cédula",
                type=["jpg", "jpeg", "png", "pdf"],
                key="reg_ocr_file",
                help="Formatos aceptados: JPG, PNG o PDF. Use una imagen bien iluminada y enfocada.",
            )
            if st.button("🔍 Leer cédula y autocompletar", key="reg_ocr_btn", use_container_width=True):
                if not _ced_file:
                    st.warning("Primero suba una imagen o PDF de la cédula.")
                else:
                    _bytes = _ced_file.getvalue()
                    if len(_bytes) > 8 * 1024 * 1024:
                        st.warning("El archivo es muy grande (máximo 8 MB). Use una foto más liviana.")
                    else:
                        with st.spinner("Leyendo la cédula..."):
                            _texto, _err = _cedula_imagen_a_texto(_bytes, _ced_file.name)
                        if _err:
                            st.warning(_err)
                        else:
                            _datos = _parsear_datos_cedula(_texto)
                            if _datos.get("cedula_tipo") in ("V", "E", "P"):
                                st.session_state.reg_cedula_tipo = _datos["cedula_tipo"]
                            if _datos.get("cedula_num"):
                                st.session_state.reg_cedula_num = _datos["cedula_num"]
                            for _campo, _key in (("primer_nombre", "reg_primer_nombre"),
                                                 ("segundo_nombre", "reg_segundo_nombre"),
                                                 ("primer_apellido", "reg_primer_apellido"),
                                                 ("segundo_apellido", "reg_segundo_apellido")):
                                if _datos.get(_campo):
                                    st.session_state[_key] = _datos[_campo]
                            _leidos = [k for k in ("cedula_num", "primer_nombre", "primer_apellido") if _datos.get(k)]
                            if _leidos:
                                st.success(
                                    "Datos leídos y colocados en el formulario de abajo. "
                                    "**Revíselos y corrija lo que haga falta** antes de registrar."
                                )
                            else:
                                st.warning(
                                    "No se pudo reconocer automáticamente los datos. "
                                    "Escríbalos a mano en el formulario. "
                                    "(Sugerencia: use una foto más nítida y bien iluminada.)"
                                )
                            with st.expander("Ver texto leído (para copiar manualmente)", expanded=not _leidos):
                                st.text(_texto.strip() or "(sin texto reconocible)")

    st.markdown("---")
    st.markdown("#### 👤 Datos del Titular")

    with st.form("form_registro", clear_on_submit=False):
        col_c, col_d = st.columns(2)

        with col_c:
            # Nombres y apellidos separados en dos campos cada uno.
            # El primero es OBLIGATORIO; el segundo es OPCIONAL.
            pn_col, sn_col = st.columns(2)
            with pn_col:
                primer_nombre = st.text_input("👤 PRIMER NOMBRE *", placeholder="Ej: María", key="reg_primer_nombre")
            with sn_col:
                segundo_nombre = st.text_input("👤 SEGUNDO NOMBRE", placeholder="Opcional. Ej: José", key="reg_segundo_nombre")
            pa_col, sa_col = st.columns(2)
            with pa_col:
                primer_apellido = st.text_input("👤 PRIMER APELLIDO *", placeholder="Ej: Pérez", key="reg_primer_apellido")
            with sa_col:
                segundo_apellido = st.text_input("👤 SEGUNDO APELLIDO", placeholder="Opcional. Ej: González", key="reg_segundo_apellido")
            # Se arma el nombre y el apellido completos (para cédula/certificado).
            nombres = " ".join(x for x in (primer_nombre.strip(), segundo_nombre.strip()) if x)
            apellidos = " ".join(x for x in (primer_apellido.strip(), segundo_apellido.strip()) if x)
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
            if not primer_nombre.strip(): errores.append("PRIMER NOMBRE")
            if not primer_apellido.strip(): errores.append("PRIMER APELLIDO")
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

elif menu == "📥 Carga Masiva (Excel)":
    mostrar_header("📥 Carga Masiva desde Excel",
                   "Importe muchos expedientes y sus notas de una sola vez, sin conexión a internet")

    if rol not in ("ADMIN_PRINCIPAL", "ADMIN_AUXILIAR"):
        st.error("🚫 Su nivel de usuario no está autorizado para esta sección.")
        st.stop()

    st.info("💡 Úselo para poblaciones sin internet: descargue la plantilla, envíela para "
            "que la llenen, y cuando le devuelvan el archivo lleno, súbalo aquí. "
            "El sistema carga todo de una vez y le avisa si alguna fila tuvo problemas "
            "(las demás se cargan igual).")

    st.subheader("1️⃣ Descargar la plantilla en blanco")
    st.caption("Tiene hojas para EXPEDIENTES y NOTAS, más una hoja LISTAS con los "
               "nombres exactos de programas y estados, y una hoja de INSTRUCCIONES.")
    try:
        plantilla_bytes = generar_plantilla_carga_masiva()
        st.download_button(
            "⬇️ Descargar plantilla de carga masiva (Excel)",
            data=plantilla_bytes,
            file_name="PLANTILLA_CARGA_MASIVA_UNEM.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo generar la plantilla: {e}")

    st.markdown("---")
    st.subheader("2️⃣ Subir el archivo lleno e importar")
    archivo = st.file_uploader("Seleccione el archivo Excel lleno", type=["xlsx", "xlsm"], key="cm_file")

    imp_exp = st.checkbox("Importar EXPEDIENTES", value=True, key="cm_imp_exp")
    imp_not = st.checkbox("Importar NOTAS", value=True, key="cm_imp_not")

    if archivo is not None:
        try:
            hojas = pd.read_excel(archivo, sheet_name=None, dtype=str, engine="openpyxl")
        except Exception as e:  # noqa: BLE001
            hojas = None
            st.error(f"No se pudo leer el archivo: {e}")

        if hojas is not None:
            def _buscar_hoja(claves):
                for nombre in hojas.keys():
                    up = str(nombre).strip().upper()
                    if any(k in up for k in claves):
                        return hojas[nombre]
                return None

            df_exp = _buscar_hoja(["EXPEDIENTE"])
            df_not = _buscar_hoja(["NOTA", "CALIFICAC"])

            col_prev1, col_prev2 = st.columns(2)
            with col_prev1:
                if df_exp is not None:
                    st.caption(f"Hoja EXPEDIENTES detectada: {len(df_exp)} fila(s).")
                    st.dataframe(df_exp.head(8), use_container_width=True, height=220)
                else:
                    st.warning("No se encontró la hoja EXPEDIENTES.")
            with col_prev2:
                if df_not is not None:
                    st.caption(f"Hoja NOTAS detectada: {len(df_not)} fila(s).")
                    st.dataframe(df_not.head(8), use_container_width=True, height=220)
                else:
                    st.caption("No se encontró hoja NOTAS (es opcional).")

            if st.button("🚀 Importar ahora", type="primary", use_container_width=True, key="cm_importar"):
                resumen = []
                if imp_exp and df_exp is not None:
                    with st.spinner("Importando expedientes..."):
                        ok, fail, errs = procesar_carga_masiva_expedientes(df_exp, st.session_state.usuario)
                    resumen.append(("Expedientes", ok, fail, errs))
                if imp_not and df_not is not None:
                    with st.spinner("Importando notas..."):
                        okn, failn, errsn = procesar_carga_masiva_notas(df_not)
                    resumen.append(("Notas (materias)", okn, failn, errsn))

                if not resumen:
                    st.warning("No había nada que importar (revise las casillas y las hojas del archivo).")
                else:
                    for etiqueta, ok, fail, errs in resumen:
                        if fail == 0:
                            st.success(f"✅ {etiqueta}: {ok} cargado(s) correctamente.")
                        else:
                            st.warning(f"⚠️ {etiqueta}: {ok} cargado(s), {fail} con problema(s).")
                        if errs:
                            with st.expander(f"Ver detalle de problemas en {etiqueta} ({len(errs)})"):
                                for m in errs[:200]:
                                    st.write("• " + str(m))
                                if len(errs) > 200:
                                    st.caption(f"... y {len(errs) - 200} más.")
                    st.info("Puede revisar los expedientes cargados en 'Consultar Expedientes'.")

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
            # Recorrido TSU: se le reconocen los trayectos 1 y 2, por lo que la
            # carga de calificaciones arranca en el TRAYECTO 3 (no se cargan T1-T2).
            _tipo_est_e = str(row_e.get("tipo_estudiante", "") or "").upper()
            if "TSU" in _tipo_est_e:
                malla_e = [m for m in malla_e if int(m.get("trayecto") or 0) >= 3]
                st.info("🎓 Estudiante **TSU**: se le reconocen los trayectos 1 y 2. "
                        "La carga inicia en el **Trayecto 3**.")
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
            # Recorrido TSU: solo se muestran los trayectos 3 y 4.
            _tipo_est_ev = str(row_ev.get("tipo_estudiante", "") or "").upper()
            if "TSU" in _tipo_est_ev:
                malla_ev = [m for m in malla_ev if int(m.get("trayecto") or 0) >= 3]
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
