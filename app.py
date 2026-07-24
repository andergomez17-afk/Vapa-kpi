import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import tempfile
import json
import os
import gc
import re

# Intentar importar la librería para PDF
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

# ==============================================================================
# 0. CONFIGURACIÓN DE LAS BASES DE DATOS LOCALES Y CARPETAS DEL SERVIDOR
# ==============================================================================
DB_FILE = "vapa_db.json"
CIERRES_FILE = "vapa_cierres.json"
UPLOAD_DIR = "vapa_uploads" # <--- CARPETA DEL SERVIDOR PARA EXCEL

COURIERS = {
    "3890427": "Brian Tapia",
    "4619213": "Alex Duran Rodriguez",
    "3635830": "Alexis Morales Concha",
    "6067748": "Bairon Cartagena Aros",
    "4031450": "Brian Soto",
    "4279994": "Carlos Benitez Romero",
    "3635949": "Carlos Gonzalez Castillo",
    "3635847": "Cristian Orellana Maldonado",
    "6042231": "Gonzalo Rojas Valladares",
    "3635697": "Ignacio Azua Rubina",
    "4211394": "Ivar Grau",
    "5485577": "Jonathan Oliva Venegas",
    "4315829": "Williams Aravena Fuentes",
    "3635722": "Andres Bustamante Silva",
    "3635779": "Claudio Gonzalez Alfaro",
    "6067729": "Diego Muñoz Cordova",
    "3635910": "Diego Silvera Saucedo",
    "4152331": "Federico Araneda",
    "4393060": "Jean Olate Aedo",
    "3635956": "Juan Soto Torrealba",
    "4273766": "Matias Del Bel",
    "4285050": "Michael Sepulveda Mateluna",
    "4031455": "Patricia Serrano",
    "3635943": "Quesny Cherenfant",
    "4396439": "Rodrigo Garcia Andrade",
    "3836119": "Salvador Frez Inostroza",
    "945447": "Mario Duarte",
    "5710691": "Adriasola",
    "6723307": "alexon Caicedo",
    "6269974": "Claudio Tapia",
    "6753631": "Daniel Ibañez",
    "5710643": "Enor Caicedo",
    "6568275": "Fabian Perez",
    "6269970": "Jose Caicedo",
    "6269972": "Julio Lobos",
    "6568276": "Raul Ceballos",
    "9836295": "Javier Gana",
    "9711646": "Williams Piña",
    "9601562": "Yeison Gonzalez",
    "9789500": "Jose Gutierrez",
    "9762038": "Carlos Soto",
    "1019905": "Patricio Troncoso",
    "2588350": "Luis pinto"
}

# Crear carpeta de subidas si no existe
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_cierres():
    if os.path.exists(CIERRES_FILE):
        try:
            with open(CIERRES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cierres(data):
    with open(CIERRES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==============================================================================
# 1. CONFIGURACIÓN DE LA INTERFAZ Y ESTILOS FEDEX PREMIER
# ==============================================================================
st.set_page_config(
    page_title="Control de Inventario Interno VAPA",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #121212; color: #FFFFFF; }
    .sidebar .sidebar-content { background-color: #1A1A1A; border-right: 2px solid #4D148C; }
    
    div.stButton > button:first-child {
        background-color: #4D148C; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: 1px solid #4D148C; transition: 0.3s;
    }
    div.stButton > button:first-child:hover { background-color: #FF6600; border-color: #FF6600; color: white; transform: scale(1.02); }
    
    h1 { color: #4D148C; text-shadow: 1px 1px 2px rgba(255,102,0,0.2); }
    h2, h3 { color: #FF6600; }
    
    .metric-box {
        background-color: #1E1E1E; padding: 15px; border-radius: 12px; 
        border-bottom: 4px solid #4D148C; border-top: 1px solid #2F2F2F; 
        border-left: 1px solid #2F2F2F; border-right: 1px solid #2F2F2F;
        margin-bottom: 5px; text-align: center; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s ease-in-out, border-color 0.2s;
        min-height: 110px;
    }
    .metric-box:hover {
        transform: translateY(-5px); border-bottom: 4px solid #FF6600;
    }
    .metric-title { font-size: 11px; color: #A0A0A0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; display: block; line-height: 1.2; }
    .metric-value { font-size: 28px; font-weight: 900; color: #FFFFFF; display: block; }
    
    [data-testid="stForm"] {
        padding: 35px; 
        background-color: #1A1A1A; border-radius: 15px; 
        border: none;
        border-top: 5px solid #4D148C; border-bottom: 5px solid #FF6600;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.8);
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; background-color: #1E1E1E; border-radius: 8px 8px 0px 0px; 
        padding: 10px 20px; border: 1px solid #2F2F2F; border-bottom: none;
    }
    .stTabs [aria-selected="true"] { background-color: #4D148C; color: white !important; border-color: #4D148C; }
    div[data-testid="stExpander"] { background-color: #1A1A1A; border: 1px solid #2F2F2F; border-radius: 8px; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CAPA DE CIBERSEGURIDAD AVANZADA (HASH SHA-256 Y ANTI-BRUTE FORCE)
# ==============================================================================
import hashlib
import time
import base64
import os
import json

USERS_FILE = "vapa_users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        default_users = {
            "user": {
                "nombre": "Operador",
                "apellido": "Vapa",
                "role": "operador",
                "hash": hashlib.sha256("Vapa2026".encode('utf-8')).hexdigest()
            },
            "Admin": {
                "nombre": "Admin",
                "apellido": "Local",
                "role": "admin",
                "hash": hashlib.sha256("AdminVapa2026".encode('utf-8')).hexdigest()
            },
            "SAdmin": {
                "nombre": "Super",
                "apellido": "Admin",
                "role": "sadmin",
                "hash": hashlib.sha256("An804223".encode('utf-8')).hexdigest()
            }
        }
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f)
        return default_users
    
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users_dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users_dict, f)

def check_password():
    # 1. Control Anti Fuerza-Bruta
    if "failed_attempts" not in st.session_state:
        st.session_state["failed_attempts"] = 0
    if "lockout_time" not in st.session_state:
        st.session_state["lockout_time"] = 0

    if st.session_state["lockout_time"] > time.time():
        faltan = int(st.session_state["lockout_time"] - time.time())
        st.error(f"🚨 ACCESO BLOQUEADO por seguridad (Múltiples intentos fallidos). Intenta de nuevo en {faltan} segundos.")
        return False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
        st.session_state["role"] = None
        st.session_state["current_user"] = None

    if not st.session_state["password_correct"]:
        c_log1, c_log2, c_log3 = st.columns([1, 1.2, 1])
        with c_log2:
            with st.form("login_form"):
                st.markdown("""
                    <div style='text-align: center; padding-bottom: 15px;'>
                        <h2 style='margin-top: 10px; margin-bottom: 5px; font-size: 42px;'>
                            <span style='color: #4D148C; font-weight: 900;'>FedEx</span> 
                            <span style='color: #FF6600; font-weight: 900;'>VAPA</span>
                        </h2>
                        <p style='color: #A0A0A0; font-size: 14px; margin-bottom: 0px;'>
                            Control Operativo - Acceso Encriptado
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                username = st.text_input("Usuario (ID)", placeholder="Ej. Admin")
                pwd = st.text_input("Contraseña", type="password", placeholder="Tu clave secreta...")
                submitted = st.form_submit_button("Iniciar Sesión")
                
                if submitted:
                    users = load_users()
                    user_id = username.strip()
                    
                    if user_id in users:
                        input_hash = hashlib.sha256(pwd.encode('utf-8')).hexdigest()
                        if input_hash == users[user_id]["hash"]:
                            st.session_state["password_correct"] = True
                            st.session_state["role"] = users[user_id]["role"]
                            st.session_state["current_user"] = users[user_id]
                            st.session_state["failed_attempts"] = 0
                            st.rerun()
                        else:
                            st.session_state["failed_attempts"] += 1
                    else:
                        st.session_state["failed_attempts"] += 1
                    
                    if not st.session_state.get("password_correct", False):
                        if st.session_state["failed_attempts"] >= 5:
                            st.session_state["lockout_time"] = time.time() + 180 # Bloqueo de 3 minutos
                            st.error("🚨 Límite de intentos superado. Bloqueo de seguridad activado.")
                            st.rerun()
                        else:
                            intentos_restantes = 5 - st.session_state["failed_attempts"]
                            st.error(f"❌ Credenciales incorrectas. Intentos restantes: {intentos_restantes}")
            
            # Espaciado extra si es necesario para empujar el form
            st.markdown("<br>", unsafe_allow_html=True)
        return False
    return True

if not check_password():
    st.stop()

# ==============================================================================
# INICIALIZACIÓN DE MEMORIA Y BASE DE DATOS
# ==============================================================================
if "justificaciones_admin" not in st.session_state:
    st.session_state["justificaciones_admin"] = load_db()

if "cierres_admin" not in st.session_state:
    st.session_state["cierres_admin"] = load_cierres()

if "history" not in st.session_state: 
    st.session_state["history"] = {}

# ==============================================================================
# 3. CABECERA PRINCIPAL Y MOTOR ANTI-COLAPSO DE RAM
# ==============================================================================
col_titulo, col_salir = st.columns([7, 1])
with col_titulo:
    st.markdown("<h1 style='margin-bottom: 0px;'>📦 Monitoreo de Almacén</h1>", unsafe_allow_html=True)
    if st.session_state.get("role") == "sadmin":
        st.caption(f"🟣 Conectado como: **SUPERADMIN** | {st.session_state['current_user']['nombre']} {st.session_state['current_user']['apellido']}")
    elif st.session_state.get("role") == "admin":
        st.caption(f"🟢 Conectado como: **ADMINISTRADOR** | {st.session_state['current_user']['nombre']} {st.session_state['current_user']['apellido']}")
    else:
        st.caption(f"🔵 Conectado como: **OPERADOR** | {st.session_state['current_user']['nombre']} {st.session_state['current_user']['apellido']}")

with col_salir:
    st.write("") 
    if st.button("🚪 Salir"):
        st.session_state["password_correct"] = False
        st.session_state["role"] = None
        st.rerun()

st.divider()

def extraer_chofer(row):
    has_van = pd.notna(row.get('VAN All')) and str(row.get('VAN All')).strip() != ""
    has_pod = pd.notna(row.get('POD All')) and str(row.get('POD All')).strip() != ""
    has_44 = pd.notna(row.get('STAT 44 Date Time Latest')) and str(row.get('STAT 44 Date Time Latest')).strip() != ""
    has_17 = pd.notna(row.get('DEX All')) and '17' in str(row.get('DEX All'))

    if not has_van and not has_pod and (has_44 or has_17):
        return "En Estación"

    texto = str(row.get('VAN All', '')) + " " + str(row.get('POD All', '')) + " " + str(row.get('DEX All', ''))
    coincidencias = re.findall(r'(\d{6,7})', texto)
    for c in coincidencias:
        if c in COURIERS:
            return COURIERS[c]
    return "No Identificado"

class VapaEngine:
    @staticmethod
    def process_file_data(df):
        hoy = datetime.now()
        df['Fecha de Carga'] = hoy.strftime('%Y-%m-%d')
        
        if 'Tracking Number' in df.columns:
            df['Tracking Number'] = df['Tracking Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        df_vapa = df[df['Dest Loc Cd'].astype(str).str.strip().str.upper() == 'VAPA'].copy()
        
        df_bodega = df_vapa[
            (df_vapa['VAN All'].isna() | (df_vapa['VAN All'].astype(str).str.strip() == "")) & 
            (df_vapa['POD All'].isna() | (df_vapa['POD All'].astype(str).str.strip() == ""))
        ].copy()

        if 'Commit Date' in df_bodega.columns:
            fechas_entrega = pd.to_datetime(df_bodega['Commit Date'], errors='coerce').dt.date
            fecha_actual = hoy.date()
            filtro_fecha = fechas_entrega.isna() | (fechas_entrega <= fecha_actual)
            df_bodega = df_bodega[filtro_fecha]
            
        dict_admin = st.session_state.get("justificaciones_admin", {})
        if 'Tracking Number' in df_vapa.columns:
            df_vapa['Acción Admin'] = df_vapa['Tracking Number'].map(lambda x: dict_admin.get(x, {}).get('estado', 'N/A'))
            df_vapa['Ruta Asignada'] = df_vapa['Tracking Number'].map(lambda x: dict_admin.get(x, {}).get('ruta', ''))
            # Asignamos Chofer basado en el texto del escaneo
            df_vapa['Chofer Asignado'] = df_vapa.apply(extraer_chofer, axis=1)
        
        if 'Tracking Number' in df_bodega.columns:
            df_bodega['Acción Admin'] = df_bodega['Tracking Number'].map(lambda x: dict_admin.get(x, {}).get('estado', 'N/A'))
            df_bodega['Ruta Asignada'] = df_bodega['Tracking Number'].map(lambda x: dict_admin.get(x, {}).get('ruta', ''))
            df_bodega['Chofer Asignado'] = df_bodega.apply(extraer_chofer, axis=1)
        
        return df_vapa, df_bodega

# CACHÉ DE LECTURA FÍSICA PARA ACELERAR CARGA Y PROTEGER MEMORIA
@st.cache_data(show_spinner=False)
def load_file_from_disk(filepath):
    try:
        xls = pd.ExcelFile(filepath)
        sheet_name = 'BD' if 'BD' in xls.sheet_names else xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df.columns = [str(c).strip() for c in df.columns]
        return VapaEngine.process_file_data(df)
    except Exception as e:
        return None, None

# AUTO-CARGAR ARCHIVOS DEL SERVIDOR (Carpeta vapa_uploads) AL INICIAR
for filename in os.listdir(UPLOAD_DIR):
    if filename.endswith((".xlsx", ".csv")) and filename not in st.session_state["history"]:
        filepath = os.path.join(UPLOAD_DIR, filename)
        df_v, df_b = load_file_from_disk(filepath)
        if df_v is not None:
            st.session_state["history"][filename] = {"vapa": df_v, "bodega": df_b}

def color_fedex_cliente(row):
    fila_str = ""
    for val in row.values:
        if pd.notna(val):
            fila_str += str(val).upper() + " "
            
    color = ''
    if 'TRICOT' in fila_str: 
        color = 'background-color: #FF6600; color: white;'
    elif any(c in fila_str for c in ['CRUZ VERDE', 'MAICAO', 'INTERCARRY', 'SOCOFAR', 'AHUMADA', 'FASA']): 
        color = 'background-color: #4D148C; color: white;'
        
    return [color] * len(row)

def clean_pdf_text(text):
    return str(text).encode('latin-1', 'replace').decode('latin-1')

# ==============================================================================
# 4. GENERADOR DE PDF 
# ==============================================================================
@st.cache_data(show_spinner=False)
def generar_pdf_avanzado(fecha_str, auditor, total, clientes_ordenados, corregir_total, en_ruta, df_criticos, total_compromiso, m_sin_sip=0, m_44_estacion=0, m_pod_sin_van=0):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    pdf.set_fill_color(77, 20, 140) 
    pdf.rect(0, 0, 210, 35, 'F')
    
    pdf.set_y(8)
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, txt="REPORTE DE OPERACIONES", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.set_text_color(255, 102, 0) 
    pdf.cell(0, 10, txt="Terminal VAPA - Auditoria de Despacho", ln=True, align='C')
    
    pdf.set_y(40)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(50, 50, 50)
    
    if auditor and auditor.strip() != "":
        pdf.cell(100, 8, txt=f"FECHA DE EMISION: {fecha_str}")
        pdf.cell(90, 8, txt=clean_pdf_text(f"SUPERVISOR: {auditor.strip()}"), align='R', ln=True)
    else:
        pdf.cell(0, 8, txt=f"FECHA DE EMISION: {fecha_str}", ln=True)
        
    pdf.line(10, 50, 200, 50)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, txt="1. INDICADORES DE RENDIMIENTO (SOBRE COMPROMISOS VENCIDOS O DE HOY)", ln=True)
    
    if total_compromiso > 0:
        pct_fallando = round((corregir_total / total_compromiso) * 100, 1)
        pct_exito = round(100.0 - pct_fallando, 1)
    else:
        pct_exito, pct_fallando = 0, 0
        
    pdf.set_font("Arial", '', 10)
    pdf.cell(80, 8, txt=f"Compromisos a Tiempo ({pct_exito}%):")
    pdf.set_fill_color(220, 220, 220)
    pdf.rect(90, pdf.get_y() + 2, 100, 4, 'F')
    pdf.set_fill_color(0, 170, 80)
    pdf.rect(90, pdf.get_y() + 2, int(pct_exito), 4, 'F')
    pdf.ln(8)
    
    pdf.cell(80, 8, txt=f"Fallando Compromiso (Corregir Stat 44) ({pct_fallando}%):")
    pdf.set_fill_color(220, 220, 220)
    pdf.rect(90, pdf.get_y() + 2, 100, 4, 'F')
    pdf.set_fill_color(200, 0, 0)
    pdf.rect(90, pdf.get_y() + 2, int(pct_fallando), 4, 'F')
    pdf.ln(12)

    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, txt="2. RESUMEN VOLUMETRICO DE BULTOS", ln=True)
    
    def add_row(label, value, fill_color, text_color):
        pdf.set_fill_color(*fill_color)
        pdf.set_text_color(*text_color)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(145, 10, txt=f"  {label}", border=1, fill=True)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(45, 10, txt=str(value), border=1, fill=True, align='C', ln=True)

    pdf.set_fill_color(220, 220, 220)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(145, 8, txt="  ESTADO LOGISTICO", border=1, fill=True)
    pdf.cell(45, 8, txt="CANTIDAD", border=1, fill=True, align='C', ln=True)

    add_row("Total Procesados (Llegaron Hoy a la Estacion)", total, (255, 255, 255), (0, 0, 0))
    add_row("Bultos en Ruta (Carga Asignada en VAN)", en_ruta, (230, 250, 230), (0, 128, 64))
    
    for cli in clientes_ordenados:
        if cli['nombre'] == 'Tricot':
            add_row(f"Ingreso Cliente {cli['nombre']}", cli['cantidad'], (255, 245, 235), (255, 102, 0))
        else:
            add_row(f"Ingreso Cliente {cli['nombre']}", cli['cantidad'], (245, 235, 255), (77, 20, 140))
            
    # Nuevas estadísticas de Fallas
    add_row("Fallas: Salió a Ruta SIN SIP", m_sin_sip, (255, 200, 200), (255, 0, 0))
    add_row("Fallas: Tiene POD pero faltó VAN", m_pod_sin_van, (255, 215, 200), (220, 60, 0))
    add_row("Fallas: Solo STAT 44 en Estación (Hoy)", m_44_estacion, (255, 215, 200), (220, 60, 0))
    add_row("Corregir Stat 44 y Aplazar (Fallando Compromiso)", corregir_total, (255, 230, 230), (200, 0, 0))
    
    def imprimir_cabecera_tabla_roja():
        pdf.set_fill_color(200, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(35, 8, txt="Tracking", border=1, fill=True)
        pdf.cell(45, 8, txt="Cliente", border=1, fill=True)
        pdf.cell(30, 8, txt="Comuna", border=1, fill=True)
        pdf.cell(65, 8, txt="Direccion", border=1, fill=True)
        pdf.cell(15, 8, txt="Status", border=1, fill=True, ln=True)

    if not df_criticos.empty:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(200, 0, 0) 
        pdf.cell(0, 10, txt="ANEXO: BULTOS CRITICOS (CORREGIR STAT 44 Y APLAZAR)", ln=True)
        pdf.ln(4)
        
        imprimir_cabecera_tabla_roja()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 8)
        
        for _, row in df_criticos.iterrows():
            if pdf.get_y() > 275:
                pdf.add_page()
                imprimir_cabecera_tabla_roja()
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 8)

            trk = clean_pdf_text(row.get('Tracking Number', 'N/A'))[:15]
            shp = clean_pdf_text(row.get('Shipper Company', row.get('Shipper Name', 'N/A')))[:25]
            comuna = clean_pdf_text(row.get('Recip City', 'N/A'))[:15]
            direccion = clean_pdf_text(row.get('CE Recp Address All', 'N/A'))[:35]
            stat = clean_pdf_text(row.get('Status', row.get('status', 'N/A')))[:6]
            
            pdf.cell(35, 6, txt=trk, border=1)
            pdf.cell(45, 6, txt=shp, border=1)
            pdf.cell(30, 6, txt=comuna, border=1)
            pdf.cell(65, 6, txt=direccion, border=1)
            pdf.cell(15, 6, txt=stat, border=1, ln=True)

    pdf.set_y(282)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, txt=f"Documento de uso operativo interno VAPA", align='C')
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

def generar_pdf_falla(df_falla, titulo_pdf, sort_by_chofer=False):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_fill_color(77, 20, 140) 
    pdf.rect(0, 0, 210, 25, 'F')
    
    pdf.set_y(8)
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, txt=titulo_pdf, ln=True, align='C')
    
    pdf.set_y(35)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(0, 0, 0)
    fecha_str = datetime.now().strftime('%d-%m-%Y %H:%M')
    pdf.cell(0, 8, txt=f"FECHA DE EMISION: {fecha_str}", ln=True)
    pdf.cell(0, 8, txt=f"TOTAL BULTOS: {len(df_falla)}", ln=True)
    pdf.ln(5)
    
    def imprimir_cabecera():
        pdf.set_fill_color(255, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(30, 8, txt="Tracking", border=1, fill=True)
        pdf.cell(40, 8, txt="Chofer", border=1, fill=True)
        pdf.cell(45, 8, txt="Cliente", border=1, fill=True)
        pdf.cell(20, 8, txt="Estado", border=1, fill=True)
        pdf.cell(55, 8, txt="Direccion", border=1, fill=True, ln=True)
    
    imprimir_cabecera()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 7)
    
    df_imprimir = df_falla.copy()
    if sort_by_chofer and 'Chofer Asignado' in df_imprimir.columns:
        df_imprimir = df_imprimir.sort_values(by='Chofer Asignado')
        
    for _, row in df_imprimir.iterrows():
        trk = clean_pdf_text(row.get('Tracking Number', 'N/A'))[:15]
        chofer = clean_pdf_text(row.get('Chofer Asignado', 'Desconocido'))[:20]
        shp = clean_pdf_text(row.get('Shipper Company', row.get('Shipper Name', 'N/A')))[:25]
        estado = clean_pdf_text(row.get('Status', row.get('status', 'N/A')))[:10]
        direccion = clean_pdf_text(row.get('CE Recp Address All', 'N/A'))[:35]
        
        pdf.cell(30, 6, txt=trk, border=1)
        pdf.cell(40, 6, txt=chofer, border=1)
        pdf.cell(45, 6, txt=shp, border=1)
        pdf.cell(20, 6, txt=estado, border=1)
        pdf.cell(55, 6, txt=direccion, border=1, ln=True)
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

# ==============================================================================
# 5. BARRA LATERAL (CON PROTECCIÓN DE FINES DE SEMANA)
# ==============================================================================
st.sidebar.header("📥 Ingreso de Datos")

st.sidebar.markdown(f"**👤 Sesión actual:** {'Administrador' if st.session_state.get('role') == 'admin' else 'Operador'}")
if st.sidebar.button("Cerrar Sesión", use_container_width=True):
    st.session_state["password_correct"] = False
    st.session_state["role"] = None
    st.rerun()

if st.session_state.get("role") in ["admin", "sadmin"]:
    with st.sidebar.expander("⚙️ Ajustes"):
        st.markdown("<span style='font-size:12px; color:#A0A0A0;'>Usa este botón para borrar todos los Excel del servidor y empezar un mes nuevo.</span>", unsafe_allow_html=True)
        if st.button("🧹 Borrar Historial del Servidor", use_container_width=True, type="primary"):
            for filename in os.listdir(UPLOAD_DIR):
                os.remove(os.path.join(UPLOAD_DIR, filename))
            st.session_state["history"] = {}
            st.session_state["justificaciones_admin"] = {}
            save_db({}) 
            st.rerun()

    st.sidebar.markdown("Carga aquí los reportes generados por DREUI. Se guardarán en el servidor.")
    
    if datetime.now().weekday() >= 5: # 5 = Sábado, 6 = Domingo
        st.sidebar.error("🚫 Carga deshabilitada: Sábados y Domingos no son días laborales.")
    else:
        uploaded_files = st.sidebar.file_uploader("Subir Archivos DREUI", type=["xlsx", "csv"], accept_multiple_files=True)
        if st.sidebar.button("⚙️ Guardar y Procesar en Servidor", use_container_width=True):
            if uploaded_files:
                for file in uploaded_files:
                    file_path = os.path.join(UPLOAD_DIR, file.name)
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                st.sidebar.success("✅ Archivos subidos y guardados en el servidor local. Reiniciando para cargar...")
                st.rerun() 
            else:
                st.sidebar.warning("Agrega un archivo primero.")
else:
    st.sidebar.info("📂 Estás operando en modo lectura. Los reportes DREUI han sido cargados por el Administrador desde el servidor central.")

# ==============================================================================
# 6. MÓDULO DE HISTORIAL GERENCIAL
# ==============================================================================
def mostrar_historial_kpi():
    st.markdown("### 📅 Historial y Rendimiento de la Estación")
    st.markdown("Visualiza el comportamiento del almacén y los porcentajes de éxito en distintos periodos de tiempo.")
    
    historial_cierres = st.session_state.get("cierres_admin", {})
    
    if historial_cierres:
        df_hist = pd.DataFrame.from_dict(historial_cierres, orient='index')
        
        df_hist['Porcentaje de Éxito'] = df_hist['Porcentaje de Éxito'].astype(str).str.replace('%', '').astype(float)
        df_hist['Fecha Real'] = pd.to_datetime(df_hist['Fecha de Registro'])
        
        df_hist_laboral = df_hist[df_hist['Fecha Real'].dt.weekday < 5].copy()
        
        if df_hist_laboral.empty:
            st.warning("No hay registros de cierres en días laborales para mostrar.")
            return

        df_hist_laboral['Semana'] = df_hist_laboral['Fecha Real'].dt.strftime('%G-Semana %V')
        df_hist_laboral['Mes'] = df_hist_laboral['Fecha Real'].dt.strftime('%Y-%m')
        df_hist_laboral['Fecha Visual'] = df_hist_laboral['Fecha Real'].dt.strftime('%Y-%m-%d')
        
        tab_diario, tab_semanal, tab_mensual = st.tabs(["📆 Resumen Diario", "🗓️ Resumen Semanal", "📊 Resumen Mensual"])
        
        with tab_diario:
            df_hist_sorted = df_hist_laboral.sort_values(by="Fecha Real")
            
            fig_d = px.bar(df_hist_sorted, x="Fecha Visual", y="Porcentaje de Éxito", text="Porcentaje de Éxito",
                           title="Evolución Diaria del KPI (%)", template="plotly_dark", color_discrete_sequence=["#00AA50"])
            fig_d.update_traces(textposition='outside', texttemplate='%{text}%')
            fig_d.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', dragmode=False)
            fig_d.update_xaxes(fixedrange=True)
            fig_d.update_yaxes(fixedrange=True, range=[0, 115]) 
            st.plotly_chart(fig_d, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("#### Archivo Estático por Día (Clic para expandir)")
            
            for date_str, row in df_hist_laboral.sort_values(by="Fecha Real", ascending=False).iterrows():
                with st.expander(f"📦 {row['Fecha Visual']} - KPI Final: {row['Porcentaje de Éxito']}% (Cerrado por: {row.get('Auditor Responsable', 'Admin')})"):
                    html_str = f'''
                    <div style="display:flex; gap:10px; justify-content:space-between; margin-bottom:10px;">
                        <div class='metric-box' style='flex:1; border-bottom-color:#8D99AE; min-height:80px; padding:10px;'>
                            <span class='metric-title' style='font-size:10px;'>Total Procesados</span>
                            <span class='metric-value' style='font-size:22px;'>{row.get("Total Procesados", 0)}</span>
                        </div>
                        <div class='metric-box' style='flex:1; border-bottom-color:#06D6A0; min-height:80px; padding:10px;'>
                            <span class='metric-title' style='font-size:10px;'>En Ruta</span>
                            <span class='metric-value' style='font-size:22px; color:#06D6A0;'>{row.get("Bultos en Ruta", 0)}</span>
                        </div>
                        <div class='metric-box' style='flex:1; border-bottom-color:#00AA50; min-height:80px; padding:10px;'>
                            <span class='metric-title' style='font-size:10px;'>Compromisos (Meta)</span>
                            <span class='metric-value' style='font-size:22px; color:#00AA50;'>{row.get("Total Compromisos", 0)}</span>
                        </div>
                        <div class='metric-box' style='flex:1; border-bottom-color:#E63946; min-height:80px; padding:10px;'>
                            <span class='metric-title' style='font-size:10px;'>Fallando (Stat 44)</span>
                            <span class='metric-value' style='font-size:22px; color:#E63946;'>{row.get("Fallando Compromiso", 0)}</span>
                        </div>
                        <div class='metric-box' style='flex:1; border-bottom-color:#FF2B2B; min-height:80px; padding:10px;'>
                            <span class='metric-title' style='font-size:10px;'>Salió SIN SIP</span>
                            <span class='metric-value' style='font-size:22px; color:#FF2B2B;'>{row.get("Salió SIN SIP", 0)}</span>
                        </div>
                    </div>
                    '''
                    st.markdown(html_str, unsafe_allow_html=True)
        
        with tab_semanal:
            df_sem = df_hist_laboral.groupby('Semana').agg({
                'Total Compromisos': 'sum',
                'Fallando Compromiso': 'sum'
            }).reset_index()
            
            df_sem['KPI Semanal (%)'] = np.where(df_sem['Total Compromisos'] > 0, 
                                        round(100 - (df_sem['Fallando Compromiso'] / df_sem['Total Compromisos'] * 100), 1), 0)
            
            fig_s = px.bar(df_sem, x='Semana', y='KPI Semanal (%)', text='KPI Semanal (%)',
                           title="Rendimiento Promedio de Estación por Semana", template="plotly_dark", color_discrete_sequence=["#4D148C"])
            fig_s.update_traces(textposition='outside', texttemplate='%{text}%')
            fig_s.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', dragmode=False)
            fig_s.update_xaxes(fixedrange=True)
            fig_s.update_yaxes(fixedrange=True, range=[0, 115])
            st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})
            
        with tab_mensual:
            df_mes = df_hist_laboral.groupby('Mes').agg({
                'Total Compromisos': 'sum',
                'Fallando Compromiso': 'sum'
            }).reset_index()
            
            df_mes['KPI Mensual (%)'] = np.where(df_mes['Total Compromisos'] > 0, 
                                        round(100 - (df_mes['Fallando Compromiso'] / df_mes['Total Compromisos'] * 100), 1), 0)
            
            fig_m = px.bar(df_mes, x='Mes', y='KPI Mensual (%)', text='KPI Mensual (%)',
                           title="Rendimiento Promedio de Estación por Mes", template="plotly_dark", color_discrete_sequence=["#FF6600"])
            fig_m.update_traces(textposition='outside', texttemplate='%{text}%')
            fig_m.update_layout(height=380, margin=dict(l=0, r=0, t=40, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', dragmode=False)
            fig_m.update_xaxes(fixedrange=True)
            fig_m.update_yaxes(fixedrange=True, range=[0, 115])
            st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False})

    else:
        st.info("Aún no se han registrado cierres de día en la base de datos histórica.")

# ==============================================================================
# 7. DASHBOARD INTERACTIVO PRINCIPAL
# ==============================================================================
if st.session_state["history"]:
    available_days = sorted(list(st.session_state["history"].keys()))
    selected_day = st.sidebar.selectbox("📅 Seleccionar Reporte de Servidor", available_days)
    
    df_vapa = st.session_state["history"][selected_day]["vapa"].copy()
    df_bodega = st.session_state["history"][selected_day]["bodega"].copy()
    
    just_dict = st.session_state.get("justificaciones_admin", {})
    
    if 'Tracking Number' in df_vapa.columns:
        clean_trk_vapa = df_vapa['Tracking Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_vapa['Acción Admin'] = clean_trk_vapa.map(lambda x: just_dict.get(x, {}).get('estado', ''))
        df_vapa['Ruta Asignada'] = clean_trk_vapa.map(lambda x: just_dict.get(x, {}).get('ruta', ''))
        if 'Chofer Asignado' not in df_vapa.columns:
            df_vapa['Chofer Asignado'] = df_vapa.apply(extraer_chofer, axis=1)
    
    if 'Tracking Number' in df_bodega.columns:
        clean_trk_bodega = df_bodega['Tracking Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        df_bodega['Acción Admin'] = clean_trk_bodega.map(lambda x: just_dict.get(x, {}).get('estado', ''))
        df_bodega['Ruta Asignada'] = clean_trk_bodega.map(lambda x: just_dict.get(x, {}).get('ruta', ''))
        if 'Chofer Asignado' not in df_bodega.columns:
            df_bodega['Chofer Asignado'] = df_bodega.apply(extraer_chofer, axis=1)
    
    if "ver_fallos_kpi" not in st.session_state:
        st.session_state.ver_fallos_kpi = False
        
    total_ingreso = len(df_vapa)
    
    if 'VAN All' in df_vapa.columns:
        filtro_en_ruta = df_vapa['VAN All'].notna() & (df_vapa['VAN All'].astype(str).str.strip() != "")
        df_en_ruta = df_vapa[filtro_en_ruta]
    else:
        df_en_ruta = pd.DataFrame()
    m_en_ruta = len(df_en_ruta)
    
    # -------------------------------------------------------------------------
    # IDENTIFICACIÓN DE FALLAS DE PROCESO Y BÚSQUEDA DE FECHAS
    # -------------------------------------------------------------------------
    def check_col(df, col_name, substr=None):
        if col_name not in df.columns: return pd.Series(False, index=df.index)
        if substr: return df[col_name].astype(str).str.contains(substr, regex=True, na=False)
        return df[col_name].notna() & (df[col_name].astype(str).str.strip() != "")

    has_sip = pd.Series(False, index=df_vapa.index)
    if 'SIPS Date Time Loc Latest' in df_vapa.columns:
        has_sip = has_sip | df_vapa['SIPS Date Time Loc Latest'].notna()
    elif 'SIP All' in df_vapa.columns:
        has_sip = has_sip | df_vapa['SIP All'].notna()
        
    has_van = check_col(df_vapa, 'VAN All')
    has_pod = check_col(df_vapa, 'POD All')
    
    # Validación de Fecha para STAT 44 hoy: "dia mes año pegado" ej. 22072026
    fecha_hoy_pegada = datetime.now().strftime("%d%m%Y")
    has_44 = check_col(df_vapa, 'STAT 44 Date Time Latest')
    has_44_hoy = has_44 & df_vapa['STAT 44 Date Time Latest'].astype(str).str.contains(fecha_hoy_pegada, regex=False, na=False)

    # Regla 1: SIN SIP (Salió a ruta o está en estación con 44)
    falla_sin_sip = (~has_sip) & (has_van | has_pod | has_44_hoy)
    df_sin_sip_temp = df_vapa[falla_sin_sip].copy()
    
    def estado_sin_sip_format(row):
        v = pd.notna(row.get('VAN All')) and str(row.get('VAN All')).strip() != ""
        p = pd.notna(row.get('POD All')) and str(row.get('POD All')).strip() != ""
        if p: return "Tiene POD"
        if v: return "Solo VAN"
        return "En Bodega"

    if not df_sin_sip_temp.empty: 
        df_sin_sip_temp['Motivo de Falla'] = 'Falta SIP'
        df_sin_sip_temp['Status'] = df_sin_sip_temp.apply(estado_sin_sip_format, axis=1)
        # Ignorar si se escaneó internamente sin chofer (ej. punto de venta, of. interna)
        df_sin_sip = df_sin_sip_temp[df_sin_sip_temp['Chofer Asignado'] != 'No Identificado'].copy()
    else:
        df_sin_sip = df_sin_sip_temp
    
    m_sin_sip = len(df_sin_sip)

    # Regla 2: POD sin VAN
    falla_pod_sin_van = has_pod & ~has_van
    df_pod_sin_van_temp = df_vapa[falla_pod_sin_van].copy()
    
    # Exclusión definitiva: Solo aquellos con un Chofer Identificado
    if not df_pod_sin_van_temp.empty:
        es_identificado = df_pod_sin_van_temp['Chofer Asignado'] != 'No Identificado'
        df_pod_sin_van = df_pod_sin_van_temp[es_identificado].copy()
    else:
        df_pod_sin_van = df_pod_sin_van_temp

    if not df_pod_sin_van.empty: df_pod_sin_van['Motivo de Falla'] = 'Tiene POD sin VAN'
    m_pod_sin_van = len(df_pod_sin_van)

    # Regla 3: Solo STAT 44 aplicado HOY y en estación (Sin Van/Pod)
    filtro_44_estacion = has_44_hoy & ~(has_van | has_pod)
    df_44_estacion = df_vapa[filtro_44_estacion].copy()
    if not df_44_estacion.empty: df_44_estacion['Motivo de Falla'] = 'Solo STAT 44 en Estación (Hoy)'
    m_44_estacion = len(df_44_estacion)

    # -------------------------------------------------------------------------
    # EXCLUSIÓN DE DEX 16 Y LÓGICA DE JUSTIFICACIONES ADMIN
    # -------------------------------------------------------------------------
    has_stat_bodega = pd.Series(False, index=df_bodega.index)
    for stat_col in ['STAT 44 Date Time Latest', 'STAT 50 Latest', 'STAT 53 All', 'STAT 37 Latest', 'STAT 27 Latest']:
        if stat_col in df_bodega.columns:
            has_stat_bodega = has_stat_bodega | df_bodega[stat_col].notna()

    has_dex_excl = pd.Series(False, index=df_bodega.index)
    if 'DEX All' in df_bodega.columns:
        dex_col = df_bodega['DEX All'].astype(str).str.upper()
        has_dex_excl = dex_col.str.contains(r'DEX\[03\]|DEX 03|DEX\[07\]|DEX 07|DEX\[16\]|DEX 16', regex=True, na=False)
        
    justificados_validos = [str(trk).strip() for trk, data in just_dict.items() if data.get('estado') in ["Sin Van", "POD", "Aplazada"]]
    is_justified_admin = pd.Series(False, index=df_bodega.index)
    if 'Tracking Number' in df_bodega.columns:
        is_justified_admin = clean_trk_bodega.isin(justificados_validos)

    df_corregir = df_bodega[~has_stat_bodega & ~has_dex_excl & ~is_justified_admin]
    corregir_44_aplazar_total = len(df_corregir)
    
    if 'Commit Date' in df_vapa.columns:
        fechas_entrega_vapa = pd.to_datetime(df_vapa['Commit Date'], errors='coerce').dt.date
        filtro_compromiso_vapa = fechas_entrega_vapa.isna() | (fechas_entrega_vapa <= datetime.now().date())
        df_compromiso = df_vapa[filtro_compromiso_vapa]
    else:
        df_compromiso = df_vapa.copy()

    if 'DEX All' in df_compromiso.columns:
        has_dex_16_tot = df_compromiso['DEX All'].astype(str).str.upper().str.contains(r'DEX\[16\]|DEX 16', regex=True, na=False)
        df_compromiso = df_compromiso[~has_dex_16_tot]

    if 'Tracking Number' in df_compromiso.columns:
        clean_trk_comp = df_compromiso['Tracking Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        is_justified_tot = clean_trk_comp.isin(justificados_validos)
        df_compromiso = df_compromiso[~is_justified_tot]

    total_compromiso_hoy = len(df_compromiso)

    # --- CÁLCULO DE KPIs ---
    if total_compromiso_hoy > 0:
        pct_fallando = round((corregir_44_aplazar_total / total_compromiso_hoy) * 100, 1)
        pct_exito = round(100.0 - pct_fallando, 1)
    else:
        pct_exito, pct_fallando = 0, 0

    cols_to_check = ['Tracking Number', 'Chofer Asignado', 'Shipper Company', 'Shipper Name', 'Recip City', 'CE Recp Address All', 'status', 'Status', 'Acción Admin', 'Ruta Asignada', 'Commit Date', 'SIPS Date Time Loc Latest', 'STAT 50 Latest', 'STAT 53 All', 'DEX All', 'Fecha de Carga']
    cols_to_show = list(dict.fromkeys(cols_to_check))

    # --- KPIs PRINCIPALES ---
    st.markdown("### 📊 Indicadores de Rendimiento (Compromisos de Hoy)")
    col_kpi1, col_kpi2 = st.columns(2)
    with col_kpi1:
        st.markdown(f"""
            <div style='background-color:#1E1E1E; padding:15px; border-radius:10px; border-left:5px solid #00AA50; margin-bottom: 5px;'>
                <span style='color:#A0A0A0; font-size:12px; text-transform:uppercase;'>Compromisos a Tiempo / Justificados</span><br>
                <span style='color:#FFFFFF; font-size:28px; font-weight:bold;'>{pct_exito}%</span>
                <div style='background-color:#2F2F2F; border-radius:5px; margin-top:5px; height:8px; width:100%;'>
                    <div style='background-color:#00AA50; border-radius:5px; height:8px; width:{pct_exito}%;'></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.write("") 
    with col_kpi2:
        st.markdown(f"""
            <div style='background-color:#1E1E1E; padding:15px; border-radius:10px; border-left:5px solid #E63946; margin-bottom: 5px;'>
                <span style='color:#A0A0A0; font-size:12px; text-transform:uppercase;'>Fallando Compromiso (Corregir Stat 44)</span><br>
                <span style='color:#FFFFFF; font-size:28px; font-weight:bold;'>{pct_fallando}%</span>
                <div style='background-color:#2F2F2F; border-radius:5px; margin-top:5px; height:8px; width:100%;'>
                    <div style='background-color:#E63946; border-radius:5px; height:8px; width:{pct_fallando}%;'></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔍 Ver Bultos que Afectan este %", use_container_width=True):
            st.session_state.ver_fallos_kpi = not st.session_state.ver_fallos_kpi

    if st.session_state.ver_fallos_kpi:
        st.markdown("""
            <div style='background-color:#4D148C; padding:10px; border-radius:5px; color:white; font-weight:bold; margin-bottom:10px; text-align:center;'>
                🚨 DETALLE DE BULTOS PARA CORREGIR (ACCIÓN INMEDIATA)
            </div>
        """, unsafe_allow_html=True)
        
        if corregir_44_aplazar_total > 0:
            cols_validas_fallos = [c for c in cols_to_show if c in df_corregir.columns]
            st.dataframe(
                df_corregir[cols_validas_fallos].style.apply(color_fedex_cliente, axis=1), 
                use_container_width=True, 
                hide_index=True, 
                height=350
            )
        else:
            st.success("🎉 ¡Excelente! No hay registros pendientes que afecten el compromiso.")

    st.divider()
    
    st.markdown("### 📥 Volumen Diario y Clientes")

    if not df_vapa.empty:
        filas_unidas = pd.Series("", index=df_vapa.index)
        for col in df_vapa.columns:
            filas_unidas += df_vapa[col].fillna('').astype(str).str.upper() + " "
        
        tricot_count = filas_unidas.str.contains('TRICOT', na=False).sum()
        socofar_count = filas_unidas.str.contains('CRUZ VERDE|MAICAO|INTERCARRY|SOCOFAR', na=False).sum()
        fasa_count = filas_unidas.str.contains('AHUMADA|FASA', na=False).sum()
    else:
        tricot_count, socofar_count, fasa_count = 0, 0, 0

    clientes = [
        {"nombre": "Tricot", "cantidad": tricot_count, "color": "#FF6600"},
        {"nombre": "SOCOFAR", "cantidad": socofar_count, "color": "#4D148C"},
        {"nombre": "FASA", "cantidad": fasa_count, "color": "#4D148C"}
    ]
    clientes_ordenados = sorted(clientes, key=lambda x: x["cantidad"], reverse=True)

    c_chart, c_metrics = st.columns([2, 1])
    
    with c_metrics:
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#8D99AE;'><span class='metric-title' style='font-size:11px;'>1. Total Llegaron Hoy</span><span class='metric-value' style='font-size:20px;'>{total_ingreso}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#06D6A0;'><span class='metric-title' style='font-size:11px;'>2. En Ruta (VAN)</span><span class='metric-value' style='font-size:20px; color:#06D6A0;'>{m_en_ruta}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#FF2B2B;'><span class='metric-title' style='font-size:11px;'>🚨 Salió a Ruta SIN SIP</span><span class='metric-value' style='font-size:20px; color:#FF2B2B;'>{m_sin_sip}</span></div>", unsafe_allow_html=True)
        
        for cli in clientes_ordenados:
            st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:{cli['color']};'><span class='metric-title' style='font-size:11px;'>{cli['nombre']}</span><span class='metric-value' style='font-size:20px; color:{cli['color']};'>{cli['cantidad']}</span></div>", unsafe_allow_html=True)

    with c_chart:
        cat_names = ["1. Llegaron Hoy", "2. En Ruta", "🚨 Ruta SIN SIP"] + [c["nombre"] for c in clientes_ordenados]
        cat_counts = [total_ingreso, m_en_ruta, m_sin_sip] + [c["cantidad"] for c in clientes_ordenados]
        cat_colors = ["#8D99AE", "#06D6A0", "#FF2B2B"] + [c["color"] for c in clientes_ordenados]
        
        df_ingreso = pd.DataFrame({"Categoría": cat_names, "Cantidad": cat_counts, "Color": cat_colors})
        
        fig_ingreso = px.bar(df_ingreso, x="Categoría", y="Cantidad", text="Cantidad", 
                             color="Categoría", color_discrete_sequence=df_ingreso["Color"].tolist(),
                             template="plotly_dark", title="Distribución de Ingreso Relevante")
        fig_ingreso.update_layout(
            showlegend=False, height=380, margin=dict(l=0, r=0, t=40, b=0), 
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            dragmode=False
        )
        fig_ingreso.update_xaxes(fixedrange=True, categoryorder='total descending')
        fig_ingreso.update_yaxes(fixedrange=True)
        st.plotly_chart(fig_ingreso, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    df_50 = df_vapa[df_vapa['STAT 50 Latest'].notna()] if 'STAT 50 Latest' in df_vapa.columns else pd.DataFrame()
    df_53 = df_vapa[df_vapa['STAT 53 All'].notna()] if 'STAT 53 All' in df_vapa.columns else pd.DataFrame()
    
    m_50, m_53 = len(df_50), len(df_53)
    
    metricas_operativas = [
        {"nombre": "STAT 50", "cantidad": m_50, "df": df_50, "color": "#FF6600"},
        {"nombre": "STAT 53", "cantidad": m_53, "df": df_53, "color": "#FF6600"},
        {"nombre": "En Ruta", "cantidad": m_en_ruta, "df": df_en_ruta, "color": "#06D6A0"},
        {"nombre": "Falla: Salió a Ruta SIN SIP", "cantidad": m_sin_sip, "df": df_sin_sip, "color": "#FF2B2B"},
        {"nombre": "Falla: Tiene POD pero faltó VAN", "cantidad": m_pod_sin_van, "df": df_pod_sin_van, "color": "#D35400"},
        {"nombre": "Falla: Solo STAT 44 en Estación (Hoy)", "cantidad": m_44_estacion, "df": df_44_estacion, "color": "#D35400"},
        {"nombre": "Corregir Stat 44 y Aplazar", "cantidad": corregir_44_aplazar_total, "df": df_corregir, "color": "#E63946"}
    ]
    
    metricas_ordenadas = sorted(metricas_operativas, key=lambda x: x["cantidad"], reverse=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Panel Operativo", "📋 Base de Datos", "🚨 Alertas de Riesgo", "🛠️ Gestión Admin", "📅 Historial KPI", "👥 Gestión de Usuarios"])
    
    with tab1:
        st.markdown("### Resumen de Excepciones e Inventario")
        
        if HAS_FPDF:
            with st.container():
                st.markdown("<div style='background-color: #1E1E1E; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #FF6600;'>", unsafe_allow_html=True)
                col_pdf1, col_pdf2, col_pdf3, col_pdf4 = st.columns([1, 1, 1, 1])
                with col_pdf1:
                    auditor_name = st.text_input("👤 Nombre del Supervisor/Auditor:", placeholder="Ej. Juan Pérez")
                with col_pdf2:
                    st.write("") 
                    st.write("") 
                    fecha_actual_str = datetime.now().strftime('%d-%m-%Y')
                    pdf_bytes_gral = generar_pdf_avanzado(
                        fecha_str=datetime.now().strftime('%d-%m-%Y %H:%M'),
                        auditor=auditor_name,
                        total=total_ingreso,
                        clientes_ordenados=clientes_ordenados,
                        corregir_total=corregir_44_aplazar_total, 
                        en_ruta=m_en_ruta,   
                        df_criticos=df_corregir,
                        total_compromiso=total_compromiso_hoy,
                        m_sin_sip=m_sin_sip,
                        m_44_estacion=m_44_estacion,
                        m_pod_sin_van=m_pod_sin_van
                    )
                    st.download_button(
                        label="📄 Descargar Reporte General",
                        data=pdf_bytes_gral,
                        file_name=f"Reporte_Diario_{fecha_actual_str}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                with col_pdf3:
                    st.write("")
                    st.write("")
                    if m_sin_sip > 0:
                        pdf_bytes_sinsip = generar_pdf_falla(df_sin_sip, "REPORTE DE BULTOS SIN SIP", sort_by_chofer=False)
                        st.download_button(
                            label="🚨 Descargar Bultos SIN SIP",
                            data=pdf_bytes_sinsip,
                            file_name=f"Falla_SIN_SIP_{fecha_actual_str}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                    else:
                        st.button("✅ No hay Fallas SIP", disabled=True, use_container_width=True)
                with col_pdf4:
                    st.write("")
                    st.write("")
                    if m_pod_sin_van > 0:
                        pdf_bytes_pod_sv = generar_pdf_falla(df_pod_sin_van, "REPORTE DE BULTOS CON POD SIN VAN", sort_by_chofer=True)
                        st.download_button(
                            label="📥 Descargar POD Sin VAN",
                            data=pdf_bytes_pod_sv,
                            file_name=f"Falla_POD_SIN_VAN_{fecha_actual_str}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                    else:
                        st.button("✅ No hay POD sin VAN", disabled=True, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Mostrar métricas ordenadas
        cols_por_fila = 4
        for i in range(0, len(metricas_ordenadas), cols_por_fila):
            cols = st.columns(cols_por_fila)
            for j in range(cols_por_fila):
                if i + j < len(metricas_ordenadas):
                    m = metricas_ordenadas[i + j]
                    with cols[j]:
                        st.markdown(f"<div class='metric-box' style='border-bottom-color:{m['color']};'><span class='metric-title'>{m['nombre']}</span><span class='metric-value' style='color:{m['color']};'>{m['cantidad']}</span></div>", unsafe_allow_html=True)
                        with st.expander("👁️ Ver"): 
                            if m['cantidad'] > 0: 
                                cols_validas = [c for c in cols_to_show if c in m['df'].columns]
                                if "Motivo de Falla" in m['df'].columns:
                                    cols_validas.insert(0, "Motivo de Falla")
                                st.dataframe(m['df'][cols_validas].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                            else: 
                                st.write("Vacío")

        chart_data = pd.DataFrame({
            "Categoría": [m["nombre"] for m in metricas_ordenadas],
            "Bultos": [m["cantidad"] for m in metricas_ordenadas],
            "Color": [m["color"] for m in metricas_ordenadas]
        })
        
        fig = px.bar(chart_data, x="Categoría", y="Bultos", text="Bultos", color="Categoría", color_discrete_sequence=chart_data["Color"].tolist(), template="plotly_dark")
        fig.update_layout(
            showlegend=False, height=350, margin=dict(l=0, r=0, t=30, b=0), 
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            dragmode=False
        )
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with tab2:
        st.markdown("### Motor de Búsqueda y Filtrado")
        c_search, c_filter = st.columns([3, 1])
        with c_search: search_query = st.text_input("🔍 Buscar número de Tracking:", placeholder="Ej. 770123...")
        with c_filter: 
            st.write("")
            st.write("")
            filtro_sip = st.toggle("Solo bultos SIP")
        
        display_df = df_bodega.copy()
        if filtro_sip:
            if 'status' in display_df.columns: display_df = display_df[display_df['status'].astype(str).str.upper() == 'SIP']
            elif 'Status' in display_df.columns: display_df = display_df[display_df['Status'].astype(str).str.upper() == 'SIP']
        if search_query: display_df = display_df[display_df['Tracking Number'].astype(str).str.contains(search_query)]

        cols_validas_busqueda = [c for c in cols_to_show if c in display_df.columns]
        st.dataframe(display_df[cols_validas_busqueda].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True, height=500)

    with tab3:
        st.markdown("### Control de Envejecimiento (≥ 3 días)")
        st.markdown("Aquí se muestran los bultos que fallan compromiso sin justificación, o aquellos marcados explícitamente como **'Sin Movimiento'** que se han repetido por 3 días en los archivos del servidor.")
        
        tracking_counts = {}
        tracking_info = {}

        for day_name, data in st.session_state["history"].items():
            df_b = data["bodega"]
            if 'Tracking Number' in df_b.columns:
                for _, row in df_b.iterrows():
                    trk = str(row['Tracking Number']).replace('.0', '').strip()
                    estado_admin = just_dict.get(trk, {}).get('estado', '')
                    
                    if estado_admin in ["Sin Van", "POD", "Aplazada"]:
                        continue
                        
                    tracking_counts[trk] = tracking_counts.get(trk, 0) + 1
                    tracking_info[trk] = {
                        "Tracking Number": trk,
                        "Cliente": str(row.get('Shipper Company', row.get('Shipper Name', 'N/A'))),
                        "Estado": "Falta de Gestión" if not estado_admin else estado_admin
                    }
                    
        alertas_criticas = []
        for trk, count in tracking_counts.items():
            if count >= 3:
                info = tracking_info[trk]
                info["Días Detectado"] = count
                info["Riesgo Operativo"] = "Estancamiento Crítico 🚨"
                alertas_criticas.append(info)

        if alertas_criticas:
            df_alertas = pd.DataFrame(alertas_criticas).sort_values(by="Días Detectado", ascending=False)
            st.error(f"⚠️ Atención: Se han detectado {len(df_alertas)} bultos críticos estancados.")
            st.dataframe(df_alertas, use_container_width=True, hide_index=True)
        else:
            st.success("✅ La operación fluye correctamente. Ningún bulto muestra patrones de estancamiento prolongado.")

    with tab4:
        st.markdown("### 🛠️ Control de Justificaciones Masivas y Reportes")
        
        if st.session_state["justificaciones_admin"]:
            datos_csv = []
            for k, v in st.session_state["justificaciones_admin"].items():
                datos_csv.append({
                    "Tracking": k,
                    "Cliente": v.get("cliente", "No registrado"),
                    "Dirección": v.get("direccion", "No registrado"),
                    "Justificación": v.get("estado", ""),
                    "Ruta Asignada": v.get("ruta", "")
                })
            
            df_informe = pd.DataFrame(datos_csv)
            csv_informe = df_informe.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="📥 Descargar Informe de Justificaciones (CSV)",
                data=csv_informe,
                file_name=f"Informe_Justificaciones_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
        st.divider()

        if st.session_state.get("role") not in ["admin", "sadmin"]:
            st.error("🔒 ACCESO DENEGADO. Solo el equipo de Administración puede modificar el status de la carga estancada y cerrar el día.")
            st.info("Para acceder, debe cerrar sesión e ingresar con la credencial de Administrador.")
        else:
            st.markdown("#### Panel de Justificación Rápida")
            st.markdown("Edita directamente sobre la tabla (puedes arrastrar celdas hacia abajo para copiar y pegar rápido como en Excel).")
            
            todos_justificados = [str(k).strip() for k in st.session_state["justificaciones_admin"].keys()]
            is_any_justified = clean_trk_bodega.isin(todos_justificados)
            
            df_fallando_base = df_bodega[~has_stat_bodega & ~has_dex_excl & ~is_any_justified].dropna(subset=['Tracking Number']).copy()
            
            if df_fallando_base.empty:
                st.success("🎉 ¡Excelente! No hay bultos pendientes de justificación en la base actual.")
            else:
                df_editor = df_fallando_base.copy()
                df_editor['Tracking Number'] = df_editor['Tracking Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                df_editor['Cliente'] = df_editor.get('Shipper Company', df_editor.get('Shipper Name', 'Desc.'))
                df_editor['Dirección'] = df_editor.get('CE Recp Address All', 'Desc.')
                
                # --- LÓGICA MULTIPIEZA ---
                df_editor['Alerta Multipieza'] = ""
                if 'Master Tracking Number' in df_bodega.columns and 'Piece Cnt' in df_bodega.columns:
                    bodega_masters = df_bodega.dropna(subset=['Master Tracking Number'])
                    def check_condicion(col):
                        if col in bodega_masters.columns:
                            return bodega_masters[col].astype(str).str.strip().replace('nan', '') != ""
                        return pd.Series(False, index=bodega_masters.index)
                        
                    has_v_bodega = check_condicion('VAN All')
                    has_p_bodega = check_condicion('POD All')
                    has_37 = check_condicion('STAT 37 Latest')
                    has_50 = check_condicion('STAT 50 Latest')
                    
                    bodega_masters_clean = bodega_masters.copy()
                    bodega_masters_clean['Master Tracking Number'] = bodega_masters_clean['Master Tracking Number'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    
                    bodega_movimiento = bodega_masters_clean[has_v_bodega | has_p_bodega].copy()
                    if not bodega_movimiento.empty:
                        def get_mov(row):
                            v = str(row.get('VAN All', '')).strip().replace('nan', '')
                            p = str(row.get('POD All', '')).strip().replace('nan', '')
                            if p != "": return "POD"
                            if v != "": return "VAN"
                            return "movimiento"
                        bodega_movimiento['Tipo Mov'] = bodega_movimiento.apply(get_mov, axis=1)
                        dict_movimiento = bodega_movimiento.groupby('Master Tracking Number').first()[['Chofer Asignado', 'Tracking Number', 'Tipo Mov']].to_dict(orient='index')
                    else:
                        dict_movimiento = {}
                    
                    set_37 = set(bodega_masters_clean[has_37]['Master Tracking Number'])
                    set_50 = set(bodega_masters_clean[has_50]['Master Tracking Number'])
                    
                    def evaluar_multipieza(row):
                        master = str(row.get('Master Tracking Number', '')).replace('.0', '').strip()
                        pcs = row.get('Piece Cnt', 1)
                        try:
                            pcs = int(float(pcs))
                        except:
                            pcs = 1
                            
                        if pcs > 1 and master and master != 'nan' and master != '':
                            if master in dict_movimiento:
                                chofer = dict_movimiento[master].get('Chofer Asignado', 'No Identificado')
                                trk = dict_movimiento[master].get('Tracking Number', '')
                                mov = dict_movimiento[master].get('Tipo Mov', 'movimiento')
                                if chofer == "No Identificado":
                                    return f"⚠️ Pieza {trk} con {mov}"
                                else:
                                    return f"⚠️ Pieza {trk} con {mov} ({chofer})"
                            elif master in set_37:
                                return "⚠️ Otra pieza tiene STAT 37"
                            elif master in set_50:
                                return "⚠️ Otra pieza tiene STAT 50"
                            else:
                                return "❌ Multipieza entera estancada"
                        return ""
                    
                    df_editor['Alerta Multipieza'] = df_editor.apply(evaluar_multipieza, axis=1)
                # -------------------------
                
                columnas_mostrar = ['Tracking Number', 'Cliente', 'Dirección']
                if 'Alerta Multipieza' in df_editor.columns:
                    columnas_mostrar.append('Alerta Multipieza')
                    
                df_editor = df_editor[columnas_mostrar].drop_duplicates(subset=['Tracking Number'])
                df_editor['Categoría Operativa'] = None
                df_editor['Ruta (3 dig)'] = ""
                
                with st.form("editor_form"):
                    edited_df = st.data_editor(
                        df_editor,
                        column_config={
                            "Categoría Operativa": st.column_config.SelectboxColumn(
                                "Categoría Operativa",
                                help="Selecciona el motivo",
                                width="medium",
                                options=["Sin movimiento", "Sin Van", "POD", "Aplazada"],
                                required=False,
                            ),
                            "Ruta (3 dig)": st.column_config.TextColumn(
                                "Ruta (3 dig)",
                                help="Aplica para Sin Van o POD",
                                max_chars=3,
                            ),
                            "Tracking Number": st.column_config.TextColumn(disabled=True),
                            "Cliente": st.column_config.TextColumn(disabled=True),
                            "Dirección": st.column_config.TextColumn(disabled=True),
                            "Alerta Multipieza": st.column_config.TextColumn(disabled=True),
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=550,
                        key="admin_data_editor"
                    )
                
                    if st.form_submit_button("💾 Guardar Justificaciones Editadas", type="primary", use_container_width=True):
                        cambios = edited_df.dropna(subset=["Categoría Operativa"])
                        cambios = cambios[cambios["Categoría Operativa"].astype(str).str.strip() != ""]
                        
                        errores_ruta = 0
                        guardados = 0
                        
                        # Almacenamos qué decisión se tomó para cada dirección
                        reglas_por_direccion = {}
                        
                        for _, row in cambios.iterrows():
                            motivo = row["Categoría Operativa"]
                            ruta = str(row.get("Ruta (3 dig)", "")).strip()
                            direccion = row["Dirección"]
                            
                            if motivo in ["Sin Van", "POD"] and len(ruta) != 3:
                                errores_ruta += 1
                                continue
                                
                            reglas_por_direccion[direccion] = {"motivo": motivo, "ruta": ruta}
                        
                        # Aplicamos masivamente a todas las filas que compartan esa dirección en la base de pendientes
                        for _, row in df_editor.iterrows():
                            dir_actual = row["Dirección"]
                            if dir_actual in reglas_por_direccion:
                                regla = reglas_por_direccion[dir_actual]
                                st.session_state["justificaciones_admin"][row["Tracking Number"]] = {
                                    "estado": regla["motivo"], 
                                    "ruta": regla["ruta"],
                                    "cliente": row["Cliente"],
                                    "direccion": dir_actual
                                }
                                guardados += 1
                                
                        if guardados > 0:
                            save_justificaciones(st.session_state["justificaciones_admin"])
                            st.success(f"✅ Se guardaron {guardados} justificaciones (se autocompletó masivamente por dirección).")
                        
                        if errores_ruta > 0:
                            st.warning(f"⚠️ {errores_ruta} guías no se procesaron porque exigían un número de Ruta de exactamente 3 dígitos.")
                        
                        st.rerun()

            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("#### 🗃️ Historial Activo de Carga Justificada")
            
            if st.session_state.get("justificaciones_admin"):
                datos_just = []
                for k, v in st.session_state["justificaciones_admin"].items():
                    estado = v.get("estado", "")
                    impacto = "❌ Sigue en Fallo" if estado == "Sin movimiento" else "✅ Perdonado del KPI"
                    datos_just.append({
                        "Tracking": k, 
                        "Cliente": v.get("cliente", "N/A"),
                        "Categoría": estado, 
                        "Ruta": v.get("ruta", ""), 
                        "KPI": impacto
                    })
                    
                st.dataframe(pd.DataFrame(datos_just), use_container_width=True, hide_index=True)
            else:
                st.info("Aún no se han registrado justificaciones en la Base de Datos.")

            st.divider()
            
            # --- BOTÓN DE CIERRE DE DÍA CON FIRMA DE AUDITOR ---
            st.markdown("#### 🏁 Cierre Operativo Diario")
            st.markdown("Al presionar este botón, se congelará la métrica actual y quedará guardada permanentemente en el historial del almacén.")
            
            col_fecha, col_firma, col_btn = st.columns([1, 1.5, 1])
            with col_fecha:
                fecha_seleccionada = st.date_input("📅 Fecha del Reporte:")
            with col_firma:
                firma_auditor = st.text_input("✍️ Nombre y Apellido:", placeholder="Ej. Juan Pérez")
                
            with col_btn:
                st.write("") 
                st.write("")
                if st.button("🔒 CERRAR DÍA", type="primary", use_container_width=True):
                    if fecha_seleccionada.weekday() >= 5: # 5 es Sábado, 6 es Domingo
                        st.error("🚫 No se pueden realizar cierres operativos los fines de semana (Sábados/Domingos).")
                    elif firma_auditor.strip() == "":
                        st.warning("⚠️ Debes ingresar tu Nombre y Apellido para firmar el cierre.")
                    else:
                        dia_str = fecha_seleccionada.strftime("%Y-%m-%d")
                        firma_completa = firma_auditor.strip().title()
                        
                        cierre_data = {
                            "Fecha de Registro": f"{dia_str} 23:59:59", 
                            "Total Procesados": total_ingreso,
                            "Bultos en Ruta": m_en_ruta,
                            "Salió SIN SIP": m_sin_sip,
                            "Total Compromisos": total_compromiso_hoy,
                            "Fallando Compromiso": corregir_44_aplazar_total,
                            "Porcentaje de Éxito": pct_exito, 
                            "Auditor Responsable": firma_completa
                        }
                        
                        st.session_state["cierres_admin"][dia_str] = cierre_data
                        save_cierres(st.session_state["cierres_admin"])
                        st.success(f"¡Día cerrado con éxito! El KPI de {pct_exito}% quedó registrado a nombre de {firma_completa} para el {dia_str}.")

    with tab5:
        mostrar_historial_kpi()

    with tab6:
        if st.session_state.get("role") != "sadmin":
            st.error("🔒 ACCESO DENEGADO. Solo el Super Administrador puede gestionar los perfiles de usuario.")
        else:
            st.markdown("### 👥 Administración de Usuarios")
            st.markdown("Crea o elimina credenciales de acceso para tu equipo.")
            
            c_u1, c_u2 = st.columns([1, 1.5])
            
            with c_u1:
                with st.form("new_user_form"):
                    st.subheader("Crear Nuevo Usuario")
                    nu_id = st.text_input("Usuario (ID de Acceso)*")
                    nu_nombre = st.text_input("Nombre*")
                    nu_apellido = st.text_input("Apellido*")
                    nu_pwd = st.text_input("Contraseña*", type="password")
                    nu_role = st.selectbox("Tipo de Perfil*", ["operador", "admin"])
                    
                    if st.form_submit_button("➕ Registrar Usuario", type="primary"):
                        if nu_id and nu_nombre and nu_apellido and nu_pwd:
                            users_db = load_users()
                            if nu_id.strip() in users_db:
                                st.error(f"El ID de usuario '{nu_id}' ya existe.")
                            else:
                                users_db[nu_id.strip()] = {
                                    "nombre": nu_nombre.strip(),
                                    "apellido": nu_apellido.strip(),
                                    "role": nu_role,
                                    "hash": hashlib.sha256(nu_pwd.encode('utf-8')).hexdigest()
                                }
                                save_users(users_db)
                                st.success(f"Usuario {nu_id} creado correctamente.")
                                st.rerun()
                        else:
                            st.warning("Completa todos los campos obligatorios (*).")
            
            with c_u2:
                st.subheader("Usuarios Activos")
                users_db = load_users()
                
                lista_usuarios = []
                for uid, udata in users_db.items():
                    lista_usuarios.append({
                        "ID Acceso": uid,
                        "Nombre": f"{udata.get('nombre','')} {udata.get('apellido','')}",
                        "Perfil": udata.get('role','').upper()
                    })
                
                st.dataframe(pd.DataFrame(lista_usuarios), use_container_width=True, hide_index=True)
                
                with st.expander("🗑️ Eliminar un Usuario"):
                    del_id = st.text_input("Escribe el ID del usuario a eliminar (No puedes eliminar a SAdmin)")
                    if st.button("Eliminar Usuario", type="primary"):
                        if del_id == "SAdmin":
                            st.error("No se puede eliminar la cuenta principal de SuperAdmin.")
                        elif del_id in users_db:
                            del users_db[del_id]
                            save_users(users_db)
                            st.success(f"Usuario {del_id} eliminado.")
                            st.rerun()
                        else:
                            st.error("El usuario no existe.")

else:
    st.info("👋 ¡Hola! Despliega el menú lateral y espera a que el servidor auto-cargue los reportes, o inicia sesión como Administrador para subir uno nuevo.")
    
    st.divider()
    st.markdown("### 📅 Acceso Rápido a Estadísticas")
    st.markdown("No necesitas cargar un archivo DREUI para consultar los rendimientos y cierres pasados.")
    
    if st.button("📊 Mostrar / Ocultar Historial de Cierres", type="primary", use_container_width=True):
        st.session_state["ver_solo_historial"] = not st.session_state.get("ver_solo_historial", False)
        
    if st.session_state.get("ver_solo_historial", False):
        st.write("")
        with st.container():
            st.markdown("<div style='background-color: #1A1A1A; padding: 20px; border-radius: 10px; border: 1px solid #2F2F2F;'>", unsafe_allow_html=True)
            mostrar_historial_kpi()
            st.markdown("</div>", unsafe_allow_html=True)
