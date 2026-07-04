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
        background-color: #1E1E1E; padding: 20px; border-radius: 12px; 
        border-bottom: 4px solid #4D148C; border-top: 1px solid #2F2F2F; 
        border-left: 1px solid #2F2F2F; border-right: 1px solid #2F2F2F;
        margin-bottom: 5px; text-align: center; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s ease-in-out, border-color 0.2s;
    }
    .metric-box:hover {
        transform: translateY(-5px); border-bottom: 4px solid #FF6600;
    }
    .metric-title { font-size: 13px; color: #A0A0A0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; display: block; }
    .metric-value { font-size: 32px; font-weight: 900; color: #FFFFFF; display: block; }
    
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

def generar_pdf_reporte(fecha_str, total, tricot, sin_asignar, aplazados, sin_movimiento_absoluto):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(77, 20, 140) # Morado FedEx
    pdf.cell(0, 10, txt="REPORTE OPERATIVO - FEDEX VAPA", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(255, 102, 0) # Naranja FedEx
    pdf.cell(0, 10, txt=f"Monitor de Almacenamiento y Excepciones", ln=True, align='C')
    pdf.ln(5)
    
    # Datos
    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, txt=f"Fecha de Auditoria: {fecha_str}", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt="RESUMEN DE INGRESOS Y ESTADO DE BULTOS", ln=True)
    pdf.set_font("Arial", '', 12)
    
    pdf.cell(140, 10, txt="1. Total de Bultos Procesados (Llegaron Hoy):", border=0)
    pdf.cell(0, 10, txt=str(total), border=0, ln=True, align='R')
    
    pdf.cell(140, 10, txt="2. Total Llegaron Tricot:", border=0)
    pdf.cell(0, 10, txt=str(tricot), border=0, ln=True, align='R')
    
    pdf.cell(140, 10, txt="3. Bultos Sin Asignar (En estacion / Sin Ruta):", border=0)
    pdf.cell(0, 10, txt=str(sin_asignar), border=0, ln=True, align='R')
    
    pdf.cell(140, 10, txt="4. Aplazados (Falta 44 y Aplazar):", border=0)
    pdf.cell(0, 10, txt=str(aplazados), border=0, ln=True, align='R')
    
    pdf.cell(140, 10, txt="5. Sin Movimiento Absoluto (Sin 44 ni 17):", border=0)
    pdf.cell(0, 10, txt=str(sin_movimiento_absoluto), border=0, ln=True, align='R')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 10, txt="Documento generado automaticamente por el Sistema de Monitoreo VAPA.", ln=True, align='C')
    
    # Guardar en un archivo temporal de forma segura
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
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; border-bottom-color:#8D99AE;'><span class='metric-title' style='font-size:11px;'>Total Llegaron Hoy</span><span class='metric-value' style='font-size:20px;'>{total_ingreso}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; border-bottom-color:#FF6600;'><span class='metric-title' style='font-size:11px;'>Tricot</span><span class='metric-value' style='font-size:20px; color:#FF6600;'>{tricot_count}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; border-bottom-color:#4D148C;'><span class='metric-title' style='font-size:11px;'>SOCOFAR</span><span class='metric-value' style='font-size:20px; color:#4D148C;'>{socofar_count}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; border-bottom-color:#4D148C;'><span class='metric-title' style='font-size:11px;'>FASA</span><span class='metric-value' style='font-size:20px; color:#4D148C;'>{fasa_count}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-box' style='padding: 8px; margin-bottom: 5px; border-bottom-color:#4D148C;'><span class='metric-title' style='font-size:11px;'>Miguel Torres</span><span class='metric-value' style='font-size:20px; color:#4D148C;'>{miguel_count}</span></div>", unsafe_allow_html=True)

    with c_chart:
        df_ingreso = pd.DataFrame({
            "Categoría": ["Total", "Tricot", "SOCOFAR", "FASA", "Miguel Torres"],
            "Cantidad": [total_ingreso, tricot_count, socofar_count, fasa_count, miguel_count],
            "Color": ["#8D99AE", "#FF6600", "#4D148C", "#4D148C", "#4D148C"]
        })
        fig_ingreso = px.bar(df_ingreso, x="Categoría", y="Cantidad", text="Cantidad", 
                             color="Categoría", color_discrete_sequence=df_ingreso["Color"].tolist(),
                             template="plotly_dark", title="Distribución de Ingreso Relevante")
        fig_ingreso.update_layout(showlegend=False, height=400, margin=dict(l=0, r=0, t=40, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_ingreso, use_container_width=True)

    st.divider()

    # --- LÓGICA DE FILTROS DE EXCEPCIONES ---
    fecha_hoy = datetime.now().date()
    
    df_50 = df_vapa[df_vapa['STAT 50 Latest'].notna()] if 'STAT 50 Latest' in df_vapa.columns else pd.DataFrame()
    df_53 = df_vapa[df_vapa['STAT 53 All'].notna()] if 'STAT 53 All' in df_vapa.columns else pd.DataFrame()
    
    if 'STAT 44 Date Time Latest' in df_vapa.columns:
        filtro_44 = df_vapa['STAT 44 Date Time Latest'].notna() & (df_vapa['VAN All'].isna() | (df_vapa['VAN All'].astype(str).str.strip() == ""))
        if 'DEX All' in df_vapa.columns:
            filtro_44 = filtro_44 & (~df_vapa['DEX All'].astype(str).str.contains('DEX\\[17\\]', na=False))
        df_44 = df_vapa[filtro_44]
    else:
        df_44 = pd.DataFrame()
        
    df_falta_44 = pd.DataFrame()
    if 'Commit Date' in df_vapa.columns:
        fechas_commit = pd.to_datetime(df_vapa['Commit Date'], errors='coerce').dt.date
        es_commit_hoy = fechas_commit == fecha_hoy
        
        if 'STAT 44 Date Time Latest' in df_vapa.columns:
            fechas_44 = pd.to_datetime(df_vapa['STAT 44 Date Time Latest'], errors='coerce').dt.date
            no_tiene_44_hoy = fechas_44.isna() | (fechas_44 != fecha_hoy)
        else:
            no_tiene_44_hoy = pd.Series(True, index=df_vapa.index)
            
        df_falta_44 = df_vapa[es_commit_hoy & no_tiene_44_hoy]
        
    # NUEVO CÁLCULO PARA EL PDF: Bultos sin movimiento absoluto (Sin 44 ni 17)
    if 'STAT 44 Date Time Latest' in df_bodega.columns:
        bodega_has_44 = df_bodega['STAT 44 Date Time Latest'].notna()
    else:
        bodega_has_44 = pd.Series(False, index=df_bodega.index)
        
    if 'DEX All' in df_bodega.columns:
        bodega_has_17 = df_bodega['DEX All'].astype(str).str.contains('DEX\\[17\\]', na=False)
    else:
        bodega_has_17 = pd.Series(False, index=df_bodega.index)
        
    df_sin_mov_absoluto = df_bodega[~bodega_has_44 & ~bodega_has_17]
    count_sin_mov_absoluto = len(df_sin_mov_absoluto)
    
    m_50, m_53, m_44, m_falta44, sin_mov = len(df_50), len(df_53), len(df_44), len(df_falta_44), len(df_bodega)
    cols_to_check = ['Tracking Number', 'Shipper Company', 'Shipper Name', 'status', 'Status', 'Commit Date', 'SIPS Date Time Loc Latest', 'STAT 50 Latest', 'STAT 53 All', 'DEX All', 'Fecha de Carga']
    cols_to_show = [c for c in cols_to_check if c in df_vapa.columns]
    
    tab1, tab2, tab3 = st.tabs(["📊 Panel Operativo", "📋 Base de Datos", "🚨 Alertas de Riesgo"])
    
    with tab1:
        st.markdown("### Resumen de Excepciones e Inventario")
        
        # --- BOTÓN DE DESCARGA PDF ---
        if HAS_FPDF:
            pdf_bytes = generar_pdf_reporte(
                fecha_str=datetime.now().strftime('%d-%m-%Y %H:%M'),
                total=total_ingreso,
                tricot=tricot_count,
                sin_asignar=sin_mov, # En estación (no ruta)
                aplazados=m_falta44,
                sin_movimiento_absoluto=count_sin_mov_absoluto
            )
            st.download_button(
                label="📄 Descargar Reporte en PDF",
                data=pdf_bytes,
                file_name=f"Reporte_VAPA_{fecha_hoy}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("⚠️ Para activar la descarga del PDF, debes agregar la palabra `fpdf` a tu archivo `requirements.txt` en GitHub.")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
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
            st.markdown(f"<div class='metric-box' style='border-bottom-color:#E63946;'><span class='metric-title'>Falta 44 y Aplazar</span><span class='metric-value' style='color:#E63946;'>{m_falta44}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if m_falta44 > 0: st.dataframe(df_falta_44[cols_to_show].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")
        with col5: 
            st.markdown(f"<div class='metric-box' style='border-bottom-color:#4D148C;'><span class='metric-title'>En Estación</span><span class='metric-value' style='color:#4D148C;'>{sin_mov}</span></div>", unsafe_allow_html=True)
            with st.expander("👁️ Ver"): 
                if sin_mov > 0: st.dataframe(df_bodega[[c for c in cols_to_check if c in df_bodega.columns]].style.apply(color_fedex_cliente, axis=1).hide(axis='index'), use_container_width=True)
                else: st.write("Vacío")

        chart_data = pd.DataFrame({"Categoría": ["STAT 50", "STAT 53", "Solo STAT 44", "Falta 44 (Aplazar)", "En Estación"], "Bultos": [m_50, m_53, m_44, m_falta44, sin_mov], "Color": ["#FF6600", "#FF6600", "#FF6600", "#E63946", "#4D148C"]})
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
