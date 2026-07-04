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
    .metric-title { font-size: 12px; color: #A0A0A0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; display: block; line-height: 1.2; }
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
    def process_file(file):
        try:
            xls = pd.ExcelFile(file)
            sheet_name = 'BD' if 'BD' in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(xls, sheet_name=sheet_name)
            df.columns = [str(c).strip() for c in df.columns]
            
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

# Generador de PDF Corporativo
def generar_pdf_reporte(fecha_str, total, tricot, sin_asignar, en_ruta, sin_aplazar_44):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado con fondo morado
    pdf.set_fill_color(77, 20, 140)
    pdf.rect(0, 0, 210, 35, 'F')
    
    pdf.set_y(8)
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, txt="REPORTE OPERATIVO - FEDEX VAPA", ln=True, align='C')
    pdf.set_font("Arial", 'I', 12)
    pdf.set_text_color(255, 102, 0)
    pdf.cell(0, 10, txt="Control de Inventario y Despacho", ln=True, align='C')
    
    pdf.set_y(45)
    
    # Fecha de emisión
    pdf.set_font("Arial", 'B', 11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, txt=f"FECHA DE EMISION: {fecha_str}", ln=True)
    pdf.line(10, 55, 200, 55)
    pdf.ln(5)
    
    # Función para crear filas de tabla con colores
    def add_row(label, value, fill_color, text_color):
        pdf.set_fill_color(*fill_color)
        pdf.set_text_color(*text_color)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(145, 12, txt=f"  {label}", border=1, fill=True)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(45, 12, txt=str(value), border=1, fill=True, align='C', ln=True)

    pdf.set_fill_color(220, 220, 220)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(145, 10, txt="  INDICADOR LOGISTICO", border=1, fill=True)
    pdf.cell(45, 10, txt="VOLUMEN", border=1, fill=True, align='C', ln=True)

    # Filas de la tabla
    add_row("1. Total Procesados (Llegaron Hoy a la Estacion)", total, (255, 255, 255), (0, 0, 0))
    add_row("2. Total Ingreso Cliente TRICOT", tricot, (255, 245, 235), (255, 102, 0))
    add_row("3. Bultos en Ruta (Carga Asignada en VAN)", en_ruta, (230, 250, 230), (0, 128, 64))
    add_row("4. Bultos Sin Asignar (En Estacion / Sin Ruta)", sin_asignar, (245, 235, 255), (77, 20, 140))
    add_row("5. Sin aplazar ni STAT 44", sin_aplazar_44, (255, 230, 230), (200, 0, 0))
    
    pdf.ln(25)
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, txt="Documento generado automaticamente por el Monitor de Almacen - FedEx VAPA.", ln=True, align='C')
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()

# ==============================================================================
# 4. BARRA LATERAL
# ==============================================================================
st.sidebar.header("📥 Ingreso de Datos")
st.sidebar.markdown("Carga aquí los reportes generados por DREUI.")
uploaded_files = st.sidebar.file_uploader("", type=["xlsx"], accept_multiple_files=True)

if "history" not in st.session_state: st.session_state.history = {}

if uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state.history:
            with st.spinner(f"Procesando {file.name}..."):
                df_vapa, df_bodega = VapaEngine.process_file(file)
                if df_vapa is not None:
                    st.session_state.history[file.name] = {"vapa": df_vapa, "bodega": df_bodega}
    st.sidebar.success("✅ Archivos procesados.")

# ==============================================================================
# 5. DASHBOARD INTERACTIVO
# ==============================================================================
if st.session_state.history:
    available_days = sorted(list(st.session_state.history.keys()))
    selected_day = st.sidebar.selectbox("📅 Seleccionar Historial", available_days)
    
    df_vapa = st.session_state.history[selected_day]["vapa"]
    df_bodega = st.session_state.history[selected_day]["bodega"]
    
    st.markdown("### 📥 Ingreso Diario y Clientes Clave")
    
    total_ingreso = len(df_vapa)
    
    if not df_vapa.empty:
        # SOLUCIÓN DEFINITIVA: Concatenación segura sumando columnas
        filas_unidas = pd.Series("", index=df_vapa.index)
        for col in df_vapa.columns:
            filas_unidas += df_vapa[col].fillna('').astype(str).str.upper() + " "
        
        tricot_count = filas_unidas.str.contains('TRICOT', na=False).sum()
        socofar_count = filas_unidas.str.contains('CRUZ VERDE|MAICAO|INTERCARRY|SOCOFAR', na=False).sum()
        fasa_count = filas_unidas.str.contains('AHUMADA|FASA', na=False).sum()
        miguel_count = filas_unidas.str.contains('MIGUEL TORRES', na=False).sum()
    else:
        tricot_count, socofar_count, fasa_count, miguel_count = 0, 0, 0, 0

    c_chart, c_metrics = st.columns([2, 1])
    
    with c_metrics:
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#8D99AE;'><span class='metric-title' style='font-size:11px;'>Total Llegaron Hoy</span><span class='metric-value' style='font-size:20px;'>{total_ingreso}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#FF6600;'><span class='metric-title' style='font-size:11px;'>Tricot</span><span class='metric-value' style='font-size:20px; color:#FF6600;'>{tricot_count}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#4D148C;'><span class='metric-title' style='font-size:11px;'>SOCOFAR</span><span class='metric-value' style='font-size:20px; color:#4D148C;'>{socofar_count}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#4D148C;'><span class='metric-title' style='font-size:11px;'>FASA</span><span class='metric-value' style='font-size:20px; color:#4D148C;'>{fasa_count}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; min-height: 0px; border-bottom-color:#4D148C;'><span class='metric-title' style='font-size:11px;'>Miguel Torres</span><span class='metric-value' style='font-size:20px; color:#4D148C;'>{miguel_count}</span></div>", unsafe_allow_html=True)

    with c_chart:
        df_ingreso = pd.DataFrame({
            "Categoría": ["Total", "Tricot", "SOCOFAR", "FASA", "Miguel Torres"],
            "Cantidad": [total_ingreso, tricot_count, socofar_count, fasa_count, miguel_count],
            "Color": ["#8D99AE", "#FF6600", "#4D148C", "#4D148C", "#4D148C"]
        })
        fig_ingreso = px.bar(df_ingreso, x="Categoría", y="Cantidad", text="Cantidad", 
                             color="Categoría", color_discrete_sequence=df_ingreso["Color"].tolist(),
                             template="plotly_dark", title="Distribución de Ingreso Relevante")
        fig_ingreso.update_layout(showlegend=False, height=350, margin=dict(l=0, r=0, t=40, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_ingreso, use_container_width=True)

    st.divider()

    # --- LÓGICA DE EXCEPCIONES Y EN RUTA ---
    df_50 = df_vapa[df_vapa['STAT 50 Latest'].notna()] if 'STAT 50 Latest' in df_vapa.columns else pd.DataFrame()
    df_53 = df_vapa[df_vapa['STAT 53 All'].notna()] if 'STAT 53 All' in df_vapa.columns else pd.DataFrame()
    
    if 'STAT 44 Date Time Latest' in df_vapa.columns:
        filtro_44 = df_vapa['STAT 44 Date Time Latest'].notna() & (df_vapa['VAN All'].isna() | (df_vapa['VAN All'].astype(str).str.strip() == ""))
        if 'DEX All' in df_vapa.columns:
            filtro_44 = filtro_44 & (~df_vapa['DEX All'].astype(str).str.contains('DEX\\[17\\]', na=False))
        df_44 = df_vapa[filtro_44]
    else:
        df_44 = pd.DataFrame()
        
    # En Ruta (Todo lo que tenga un registro en VAN All)
    if 'VAN All' in df_vapa.columns:
        filtro_en_ruta = df_vapa['VAN All'].notna() & (df_vapa['VAN All'].astype(str).str.strip() != "")
        df_en_ruta = df_vapa[filtro_en_ruta]
    else:
        df_en_ruta = pd.DataFrame()
        
    # Sin aplazar ni STAT 44 (Sin movimiento absoluto)
    if 'STAT 44 Date Time Latest' in df_bodega.columns:
        bodega_has_44 = df_bodega['STAT 44 Date Time Latest'].notna()
    else:
        bodega_has_44 = pd.Series(False, index=df_bodega.index)
        
    df_sin_aplazar_44 = df_bodega[~bodega_has_44]
    
    m_50, m_53, m_44, m_en_ruta, count_sin_aplazar_44, sin_mov = len(df_50), len(df_53), len(df_44), len(df_en_ruta), len(df_sin_aplazar_44), len(df_bodega)
    cols_to_check = ['Tracking Number', 'Shipper Company', 'Shipper Name', 'status', 'Status', 'Commit Date', 'SIPS Date Time Loc Latest', 'STAT 50 Latest', 'STAT 53 All', 'DEX All', 'Fecha de Carga']
    cols_to_show = [c for c in cols_to_check if c in df_vapa.columns]
    
    tab1, tab2, tab3 = st.tabs(["📊 Panel Operativo", "📋 Base de Datos", "🚨 Alertas de Riesgo"])
    
    with tab1:
        st.markdown("### Resumen de Excepciones e Inventario")
        
        # --- BOTÓN DE DESCARGA PDF ---
        if HAS_FPDF:
            fecha_actual_str = datetime.now().strftime('%d-%m-%Y')
            pdf_bytes = generar_pdf_reporte(
                fecha_str=datetime.now().strftime('%d-%m-%Y %H:%M'),
                total=total_ingreso,
                tricot=tricot_count,
                sin_asignar=sin_mov, # Lo que está en estación
                en_ruta=m_en_ruta,   
                sin_aplazar_44=count_sin_aplazar_44
            )
            st.download_button(
                label="📄 Descargar Reporte en PDF",
                data=pdf_bytes,
                file_name=f"Reporte_Diario_{fecha_actual_str}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("⚠️ Recuerda agregar 'fpdf' en tu archivo requirements.txt para habilitar la descarga del documento PDF.")
        
        # Dividido en 6 columnas para alojar todas las métricas operativas
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
            st.markdown(f"<div class='metric-box' style='border-bottom-color:#E63946;'><span class='metric-title'>Sin aplazar ni 44</span><span class='metric-value' style='color:#E63946;'>{count_sin_aplazar_44}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if count_sin_aplazar_44 > 0: st.dataframe(df_sin_aplazar_44[cols_to_show].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")
        with col6: 
            st.markdown(f"<div class='metric-box' style='border-bottom-color:#4D148C;'><span class='metric-title'>En Estación</span><span class='metric-value' style='color:#4D148C;'>{sin_mov}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if sin_mov > 0: st.dataframe(df_bodega[[c for c in cols_to_check if c in df_bodega.columns]].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")

        chart_data = pd.DataFrame({"Categoría": ["STAT 50", "STAT 53", "Solo STAT 44", "En Ruta", "Sin aplazar ni STAT 44", "En Estación"], "Bultos": [m_50, m_53, m_44, m_en_ruta, count_sin_aplazar_44, sin_mov], "Color": ["#FF6600", "#FF6600", "#FF6600", "#06D6A0", "#E63946", "#4D148C"]})
        fig = px.bar(chart_data, x="Categoría", y="Bultos", text="Bultos", color="Categoría", color_discrete_sequence=chart_data["Color"].tolist(), template="plotly_dark")
        fig.update_layout(showlegend=False, height=350, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

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
