import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import tempfile

# Intentar importar la librería para PDF
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

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
        max-width: 400px; margin: 60px auto; padding: 35px; 
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
# 2. CAPA DE SEGURIDAD (LOGIN INTEGRADO EN CAJA)
# ==============================================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        with st.form("login_form"):
            st.markdown("""
                <div style='text-align: center; padding-bottom: 15px;'>
                    <h2 style='margin-top: 10px; margin-bottom: 5px; font-size: 42px;'>
                        <span style='color: #4D148C; font-weight: 900;'>FedEx</span> 
                        <span style='color: #FF6600; font-weight: 900;'>VAPA</span>
                    </h2>
                    <p style='color: #A0A0A0; font-size: 14px; margin-bottom: 0px;'>
                        Control de Operaciones e Inventario
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            pwd = st.text_input("Clave de Acceso", type="password", placeholder="Ingresa la credencial...")
            submitted = st.form_submit_button("Iniciar Sesión")
            
            if submitted:
                if pwd == "Vapa2026": 
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Credencial denegada. Verifica tu clave.")
        return False
    return True

if not check_password():
    st.stop()

# ==============================================================================
# 3. CABECERA PRINCIPAL Y MOTOR
# ==============================================================================
col_titulo, col_salir = st.columns([7, 1])
with col_titulo:
    st.markdown("<h1 style='margin-bottom: 0px;'>📦 Monitoreo de Almacén</h1>", unsafe_allow_html=True)
    st.caption("Valparaíso Operations | Monitor de Excepciones y Base de Datos")
with col_salir:
    st.write("") 
    if st.button("🚪 Salir"):
        st.session_state["password_correct"] = False
        st.rerun()

st.divider()

class VapaEngine:
    @staticmethod
    @st.cache_data(show_spinner=False)
    def process_file_data(df):
        hoy = datetime.now()
        df['Fecha de Carga'] = hoy.strftime('%Y-%m-%d')
        
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
        
        return df_vapa, df_bodega

    @staticmethod
    def process_file(file):
        try:
            xls = pd.ExcelFile(file)
            sheet_name = 'BD' if 'BD' in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(xls, sheet_name=sheet_name)
            df.columns = [str(c).strip() for c in df.columns]
            return VapaEngine.process_file_data(df)
        except Exception as e:
            st.error(f"Error crítico al procesar el archivo: {e}")
            return None, None

def color_fedex_cliente(row):
    fila_str = ""
    for val in row.values:
        if pd.notna(val):
            fila_str += str(val).upper() + " "
            
    color = ''
    if 'TRICOT' in fila_str: 
        color = 'background-color: #FF6600; color: white;'
    elif any(c in fila_str for c in ['CRUZ VERDE', 'MAICAO', 'INTERCARRY', 'SOCOFAR', 'AHUMADA', 'FASA', 'MIGUEL TORRES']): 
        color = 'background-color: #4D148C; color: white;'
        
    return [color] * len(row)

def clean_pdf_text(text):
    return str(text).encode('latin-1', 'replace').decode('latin-1')

# ==============================================================================
# 4. GENERADOR DE PDF OPERATIVO AVANZADO
# ==============================================================================
def generar_pdf_avanzado(fecha_str, auditor, total, clientes_ordenados, bultos_estacion, en_ruta, count_falta_44, df_criticos, total_compromiso):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    
    # Encabezado Morado
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
    
    # KPIs sobre compromisos
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, txt="1. INDICADORES DE RENDIMIENTO (SOBRE COMPROMISOS VENCIDOS O DE HOY)", ln=True)
    
    if total_compromiso > 0:
        pct_fallando = round((bultos_estacion / total_compromiso) * 100, 1)
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
    
    pdf.cell(80, 8, txt=f"Fallando Compromiso (En Estacion) ({pct_fallando}%):")
    pdf.set_fill_color(220, 220, 220)
    pdf.rect(90, pdf.get_y() + 2, 100, 4, 'F')
    pdf.set_fill_color(200, 0, 0)
    pdf.rect(90, pdf.get_y() + 2, int(pct_fallando), 4, 'F')
    pdf.ln(12)

    # Resumen Volumétrico
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
            
    add_row("Bultos en la Estacion (Fallando Compromiso)", bultos_estacion, (235, 235, 235), (50, 50, 50))
    add_row("Falta Stat 44 y Aplazar (Fallando sin Escaneo)", count_falta_44, (255, 230, 230), (200, 0, 0))
    
    # Anexo Tabla Roja
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
        pdf.cell(0, 10, txt="ANEXO: BULTOS CRITICOS (FALTA STAT 44 Y APLAZAR)", ln=True)
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

# ==============================================================================
# 5. BARRA LATERAL CON FORMULARIO ESTABLE
# ==============================================================================
st.sidebar.header("📥 Ingreso de Datos")
st.sidebar.markdown("Carga aquí los reportes generados por DREUI.")

if "history" not in st.session_state: 
    st.session_state.history = {}

with st.sidebar.form("upload_form", clear_on_submit=False):
    uploaded_files = st.file_uploader("", type=["xlsx"], accept_multiple_files=True)
    btn_procesar = st.form_submit_button("⚙️ Procesar Archivos")

if btn_procesar and uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state.history:
            with st.spinner(f"Procesando {file.name}..."):
                df_vapa, df_bodega = VapaEngine.process_file(file)
                if df_vapa is not None:
                    st.session_state.history[file.name] = {"vapa": df_vapa, "bodega": df_bodega}
    st.sidebar.success("✅ Archivos procesados exitosamente.")

if st.session_state.history:
    if st.sidebar.button("🗑️ Limpiar Memoria (Reiniciar)"):
        st.session_state.history = {}
        st.rerun()

# ==============================================================================
# 6. DASHBOARD INTERACTIVO
# ==============================================================================
if st.session_state.history:
    available_days = sorted(list(st.session_state.history.keys()))
    selected_day = st.sidebar.selectbox("📅 Seleccionar Historial", available_days)
    
    df_vapa = st.session_state.history[selected_day]["vapa"]
    df_bodega = st.session_state.history[selected_day]["bodega"]
    
    # Inicializar variable para el botón de ver fallos si no existe
    if "ver_fallos_kpi" not in st.session_state:
        st.session_state.ver_fallos_kpi = False
        
    total_ingreso = len(df_vapa)
    
    if 'VAN All' in df_vapa.columns:
        filtro_en_ruta = df_vapa['VAN All'].notna() & (df_vapa['VAN All'].astype(str).str.strip() != "")
        df_en_ruta = df_vapa[filtro_en_ruta]
    else:
        df_en_ruta = pd.DataFrame()
    m_en_ruta = len(df_en_ruta)
    
    bultos_estacion_total = len(df_bodega)
    
    if 'Commit Date' in df_vapa.columns:
        fechas_entrega_vapa = pd.to_datetime(df_vapa['Commit Date'], errors='coerce').dt.date
        filtro_compromiso_vapa = fechas_entrega_vapa.isna() | (fechas_entrega_vapa <= datetime.now().date())
        total_compromiso_hoy = len(df_vapa[filtro_compromiso_vapa])
    else:
        total_compromiso_hoy = len(df_vapa)

    # --- CÁLCULO DE KPIs ---
    if total_compromiso_hoy > 0:
        pct_fallando = round((bultos_estacion_total / total_compromiso_hoy) * 100, 1)
        pct_exito = round(100.0 - pct_fallando, 1)
    else:
        pct_exito, pct_fallando = 0, 0

    cols_to_check = ['Tracking Number', 'Shipper Company', 'Shipper Name', 'Recip City', 'CE Recp Address All', 'status', 'Status', 'Commit Date', 'SIPS Date Time Loc Latest', 'STAT 50 Latest', 'STAT 53 All', 'DEX All', 'Fecha de Carga']
    cols_to_show = [c for c in cols_to_check if c in df_vapa.columns]

    # --- KPIs PRINCIPALES ---
    st.markdown("### 📊 Indicadores de Rendimiento (Compromisos de Hoy)")
    col_kpi1, col_kpi2 = st.columns(2)
    with col_kpi1:
        st.markdown(f"""
            <div style='background-color:#1E1E1E; padding:15px; border-radius:10px; border-left:5px solid #00AA50; margin-bottom: 5px;'>
                <span style='color:#A0A0A0; font-size:12px; text-transform:uppercase;'>Compromisos a Tiempo</span><br>
                <span style='color:#FFFFFF; font-size:28px; font-weight:bold;'>{pct_exito}%</span>
                <div style='background-color:#2F2F2F; border-radius:5px; margin-top:5px; height:8px; width:100%;'>
                    <div style='background-color:#00AA50; border-radius:5px; height:8px; width:{pct_exito}%;'></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.write("") # Espaciador simétrico
    with col_kpi2:
        st.markdown(f"""
            <div style='background-color:#1E1E1E; padding:15px; border-radius:10px; border-left:5px solid #E63946; margin-bottom: 5px;'>
                <span style='color:#A0A0A0; font-size:12px; text-transform:uppercase;'>Fallando Compromiso (En Estación)</span><br>
                <span style='color:#FFFFFF; font-size:28px; font-weight:bold;'>{pct_fallando}%</span>
                <div style='background-color:#2F2F2F; border-radius:5px; margin-top:5px; height:8px; width:100%;'>
                    <div style='background-color:#E63946; border-radius:5px; height:8px; width:{pct_fallando}%;'></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # BOTÓN INTERACTIVO PARA DESPLEGAR DETALLES DEL KPI FALLIDO
        if st.button("🔍 Ver Bultos que Afectan este %", use_container_width=True):
            st.session_state.ver_fallos_kpi = not st.session_state.ver_fallos_kpi

    # DESPLIEGUE DINÁMICO DE BULTOS DETENIDOS SI EL BOTÓN FUE CLICKEADO
    if st.session_state.ver_fallos_kpi:
        st.error("🚨 Carga en Estación que está Provocando el Incumplimiento del KPI:")
        if bultos_estacion_total > 0:
            st.dataframe(df_bodega[cols_to_show].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
        else:
            st.write("No hay registros que afecten el compromiso.")

    st.divider()
    
    st.markdown("### 📥 Volumen Diario y Clientes")

    if not df_vapa.empty:
        filas_unidas = pd.Series("", index=df_vapa.index)
        for col in df_vapa.columns:
            filas_unidas += df_vapa[col].fillna('').astype(str).str.upper() + " "
        
        tricot_count = filas_unidas.str.contains('TRICOT', na=False).sum()
        socofar_count = filas_unidas.str.contains('CRUZ VERDE|MAICAO|INTERCARRY|SOCOFAR', na=False).sum()
        fasa_count = filas_unidas.str.contains('AHUMADA|FASA', na=False).sum()
        miguel_count = filas_unidas.str.contains('MIGUEL TORRES', na=False).sum()
    else:
        tricot_count, socofar_count, fasa_count, miguel_count = 0, 0, 0, 0

    clientes = [
        {"nombre": "Tricot", "cantidad": tricot_count, "color": "#FF6600"},
        {"nombre": "SOCOFAR", "cantidad": socofar_count, "color": "#4D148C"},
        {"nombre": "FASA", "cantidad": fasa_count, "color": "#4D148C"},
        {"nombre": "Miguel Torres", "cantidad": miguel_count, "color": "#4D148C"}
    ]
    clientes_ordenados = sorted(clientes, key=lambda x: x["cantidad"], reverse=True)

    c_chart, c_metrics = st.columns([2, 1])
    
    with c_metrics:
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#8D99AE;'><span class='metric-title' style='font-size:11px;'>1. Total Llegaron Hoy</span><span class='metric-value' style='font-size:20px;'>{total_ingreso}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#06D6A0;'><span class='metric-title' style='font-size:11px;'>2. En Ruta (VAN)</span><span class='metric-value' style='font-size:20px; color:#06D6A0;'>{m_en_ruta}</span></div>", unsafe_allow_html=True)
        
        for cli in clientes_ordenados:
            st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:{cli['color']};'><span class='metric-title' style='font-size:11px;'>{cli['nombre']}</span><span class='metric-value' style='font-size:20px; color:{cli['color']};'>{cli['cantidad']}</span></div>", unsafe_allow_html=True)

    with c_chart:
        cat_names = ["1. Llegaron Hoy", "2. En Ruta"] + [c["nombre"] for c in clientes_ordenados]
        cat_counts = [total_ingreso, m_en_ruta] + [c["cantidad"] for c in clientes_ordenados]
        cat_colors = ["#8D99AE", "#06D6A0"] + [c["color"] for c in clientes_ordenados]
        
        df_ingreso = pd.DataFrame({"Categoría": cat_names, "Cantidad": cat_counts, "Color": cat_colors})
        
        fig_ingreso = px.bar(df_ingreso, x="Categoría", y="Cantidad", text="Cantidad", 
                             color="Categoría", color_discrete_sequence=df_ingreso["Color"].tolist(),
                             template="plotly_dark", title="Distribución de Ingreso Relevante")
        fig_ingreso.update_layout(
            showlegend=False, height=380, margin=dict(l=0, r=0, t=40, b=0), 
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            dragmode=False
        )
        fig_ingreso.update_xaxes(fixedrange=True)
        fig_ingreso.update_yaxes(fixedrange=True)
        st.plotly_chart(fig_ingreso, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    # --- LÓGICA DE FILTRADOS RESTANTES ---
    df_50 = df_vapa[df_vapa['STAT 50 Latest'].notna()] if 'STAT 50 Latest' in df_vapa.columns else pd.DataFrame()
    df_53 = df_vapa[df_vapa['STAT 53 All'].notna()] if 'STAT 53 All' in df_vapa.columns else pd.DataFrame()
    
    if 'STAT 44 Date Time Latest' in df_vapa.columns:
        filtro_44 = df_vapa['STAT 44 Date Time Latest'].notna() & (df_vapa['VAN All'].isna() | (df_vapa['VAN All'].astype(str).str.strip() == ""))
        if 'DEX All' in df_vapa.columns:
            filtro_44 = filtro_44 & (~df_vapa['DEX All'].astype(str).str.contains('DEX\\[17\\]', na=False))
        df_44 = df_vapa[filtro_44]
    else:
        df_44 = pd.DataFrame()
        
    has_stat = pd.Series(False, index=df_bodega.index)
    for stat_col in ['STAT 44 Date Time Latest', 'STAT 50 Latest', 'STAT 53 All', 'STAT 37 Latest', 'STAT 27 Latest']:
        if stat_col in df_bodega.columns:
            has_stat = has_stat | df_bodega[stat_col].notna()
            
    has_dex = pd.Series(False, index=df_bodega.index)
    if 'DEX All' in df_bodega.columns:
        dex_col = df_bodega['DEX All'].astype(str).str.upper()
        has_dex = dex_col.str.contains(r'DEX\[03\]|DEX 03|DEX\[07\]|DEX 07', regex=True, na=False)
        
    df_falta_44 = df_bodega[~has_stat & ~has_dex]
    m_50, m_53, m_44, count_falta_44 = len(df_50), len(df_53), len(df_44), len(df_falta_44)
    
    tab1, tab2, tab3 = st.tabs(["📊 Panel Operativo", "📋 Base de Datos", "🚨 Alertas de Riesgo"])
    
    with tab1:
        st.markdown("### Resumen de Excepciones e Inventario")
        
        if HAS_FPDF:
            with st.container():
                st.markdown("<div style='background-color: #1E1E1E; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #FF6600;'>", unsafe_allow_html=True)
                col_pdf1, col_pdf2 = st.columns([2, 1])
                with col_pdf1:
                    auditor_name = st.text_input("👤 Nombre del Supervisor/Auditor (Opcional):", placeholder="Ej. Anderson Gómez")
                with col_pdf2:
                    st.write("") 
                    st.write("") 
                    fecha_actual_str = datetime.now().strftime('%d-%m-%Y')
                    pdf_bytes = generar_pdf_avanzado(
                        fecha_str=datetime.now().strftime('%d-%m-%Y %H:%M'),
                        auditor=auditor_name,
                        total=total_ingreso,
                        clientes_ordenados=clientes_ordenados,
                        bultos_estacion=bultos_estacion_total, 
                        en_ruta=m_en_ruta,   
                        count_falta_44=count_falta_44,
                        df_criticos=df_falta_44,
                        total_compromiso=total_compromiso_hoy
                    )
                    st.download_button(
                        label="📄 Descargar Reporte PDF",
                        data=pdf_bytes,
                        file_name=f"Reporte_Diario_{fecha_actual_str}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1: 
            st.markdown(f"<div class='metric-box'><span class='metric-title'>STAT 50</span><span class='metric-value' style='color:#FF6600;'>{m_50}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if m_50 > 0: st.dataframe(df_50[cols_to_show].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")
        with col2: 
            st.markdown(f"<div class='metric-box'><span class='metric-title'>STAT 53</span><span class='metric-value' style='color:#FF6600;'>{m_53}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if m_53 > 0: st.dataframe(df_53[cols_to_show].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")
        with col3: 
            st.markdown(f"<div class='metric-box'><span class='metric-title'>Solo STAT 44</span><span class='metric-value' style='color:#FF6600;'>{m_44}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if m_44 > 0: st.dataframe(df_44[cols_to_show].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")
        with col4: 
            st.markdown(f"<div class='metric-box' style='border-bottom-color:#06D6A0;'><span class='metric-title'>En Ruta</span><span class='metric-value' style='color:#06D6A0;'>{m_en_ruta}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if m_en_ruta > 0: st.dataframe(df_en_ruta[cols_to_show].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")
        with col5: 
            st.markdown(f"<div class='metric-box' style='border-bottom-color:#E63946;'><span class='metric-title'>Falta Stat 44 y Aplazar</span><span class='metric-value' style='color:#E63946;'>{count_falta_44}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if count_falta_44 > 0: st.dataframe(df_falta_44[cols_to_show].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")
        with col6: 
            st.markdown(f"<div class='metric-box' style='border-bottom-color:#4D148C;'><span class='metric-title'>Bultos en Estación</span><span class='metric-value' style='color:#4D148C;'>{bultos_estacion_total}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if bultos_estacion_total > 0: st.dataframe(df_bodega[[c for c in cols_to_check if c in df_bodega.columns]].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")

    with tab2:
        st.markdown("### Motor de Búsqueda y Filtrado")
        c_search, c_filter = st.columns([3, 1])
        with c_search: search_query = st.text_input("🔍 Buscar número de Tracking:", placeholder="Ej. 770123...")
        with c_filter: 
            st.write("")
            st.write("")
            filtro_sip = st.toggle("Solo bultos SIP")
        
        display_df = df_bodega[cols_to_show].copy()
        if filtro_sip:
            if 'status' in display_df.columns: display_df = display_df[display_df['status'].astype(str).str.upper() == 'SIP']
            elif 'Status' in display_df.columns: display_df = display_df[display_df['Status'].astype(str).str.upper() == 'SIP']
        if search_query: display_df = display_df[display_df['Tracking Number'].astype(str).str.contains(search_query)]

        st.dataframe(display_df.style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True, height=500)

    with tab3:
        st.markdown("### Control de Envejecimiento (≥ 3 días)")
        tracking_history = {}
        for day_name, data in st.session_state.history.items():
            if 'Tracking Number' in data["bodega"].columns:
                for tracking in data["bodega"]['Tracking Number'].dropna().unique():
                    tracking_history[tracking] = tracking_history.get(tracking, 0) + 1
        alertas_criticas = [{"Tracking Number": k, "Días Detectado en Estación": v, "Riesgo Operativo": "Estancamiento Crítico"} for k, v in tracking_history.items() if v >= 3]
        if alertas_criticas:
            pérdidas_df = pd.DataFrame(alertas_criticas).sort_values(by="Días Detectado en Estación", ascending=False)
            st.error(f"⚠️ Atención: Se han detectado {len(pérdidas_df)} bultos críticos estancados.")
            st.dataframe(pérdidas_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ La operación fluye correctamente. Ningún bulto muestra patrones de estancamiento prolongado.")

else:
    st.info("👋 ¡Hola! Despliega el menú lateral y adjunta el archivo generado por DREUI para empezar.")
