import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN DE LA INTERFAZ Y ESTILOS FEDEX PREMIER
# ==============================================================================
st.set_page_config(
    page_title="Control de Inventario Interno VAPA",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS avanzados: Colores FedEx, animaciones Hover y diseño de Pestañas
st.markdown("""
    <style>
    /* Fondo general y texto */
    .main { background-color: #121212; color: #FFFFFF; }
    .sidebar .sidebar-content { background-color: #1A1A1A; border-right: 2px solid #4D148C; }
    
    /* Botones primarios */
    div.stButton > button:first-child {
        background-color: #4D148C; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: 1px solid #4D148C; transition: 0.3s;
    }
    div.stButton > button:first-child:hover { background-color: #FF6600; border-color: #FF6600; color: white; transform: scale(1.02); }
    
    /* Títulos y textos destacados */
    h1 { color: #4D148C; text-shadow: 1px 1px 2px rgba(255,102,0,0.2); }
    h2, h3 { color: #FF6600; }
    
    /* Tarjetas de Métricas Interactivas */
    .metric-box {
        background-color: #1E1E1E; padding: 20px; border-radius: 12px; 
        border-bottom: 4px solid #4D148C; border-top: 1px solid #2F2F2F; 
        border-left: 1px solid #2F2F2F; border-right: 1px solid #2F2F2F;
        margin-bottom: 15px; text-align: center; box-shadow: 0px 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s ease-in-out, border-color 0.2s;
    }
    .metric-box:hover {
        transform: translateY(-5px); border-bottom: 4px solid #FF6600; cursor: pointer;
    }
    .metric-title { font-size: 14px; color: #A0A0A0; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; display: block; }
    .metric-value { font-size: 32px; font-weight: 900; color: #FFFFFF; display: block; }
    
    /* Caja de Login */
    .login-box {
        max-width: 400px; margin: 80px auto; padding: 40px; 
        background-color: #1A1A1A; border-radius: 15px; 
        border-top: 5px solid #4D148C; border-bottom: 5px solid #FF6600;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.8);
    }
    
    /* Estilo de Pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; background-color: #1E1E1E; border-radius: 8px 8px 0px 0px; 
        padding: 10px 20px; border: 1px solid #2F2F2F; border-bottom: none;
    }
    .stTabs [aria-selected="true"] { background-color: #4D148C; color: white !important; border-color: #4D148C; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CAPA DE SEGURIDAD (LOGIN)
# ==============================================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #FF6600;'>📦 Terminal VAPA</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #A0A0A0;'>Control de Operaciones e Inventario</p>", unsafe_allow_html=True)
        
        pwd = st.text_input("Clave de Acceso", type="password", placeholder="Ingresa la credencial...")
        if st.button("Iniciar Sesión"):
            if pwd == "Vapa2026": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Credencial denegada. Verifica tu clave.")
        st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True

if not check_password():
    st.stop()

# ==============================================================================
# 3. CABECERA PRINCIPAL Y MOTOR
# ==============================================================================
col_logo, col_titulo, col_salir = st.columns([1, 7, 1])
with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/commons/b/b9/FedEx_Express_logo.svg", width=100)
with col_titulo:
    st.markdown("<h1 style='margin-bottom: 0px;'>Centro de Control VAPA</h1>", unsafe_allow_html=True)
    st.caption("Valparaíso Operations | Monitor de Excepciones y Auditoría de Piso")
with col_salir:
    st.write("") 
    if st.button("🚪 Salir"):
        st.session_state["password_correct"] = False
        st.rerun()

st.divider() # Línea divisoria elegante

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

# ==============================================================================
# 4. BARRA LATERAL (CARGA DE DATOS)
# ==============================================================================
st.sidebar.header("📥 Ingreso de Datos")
st.sidebar.markdown("Carga aquí los reportes diarios extraídos del sistema.")
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
# 5. DASHBOARD INTERACTIVO (PESTAÑAS)
# ==============================================================================
if st.session_state.history:
    available_days = sorted(list(st.session_state.history.keys()))
    selected_day = st.sidebar.selectbox("📅 Seleccionar Historial", available_days)
    
    df_vapa = st.session_state.history[selected_day]["vapa"]
    df_bodega = st.session_state.history[selected_day]["bodega"]
    
    # Cálculos de Métricas
    m_50 = df_vapa['STAT 50 Latest'].notna().sum() if 'STAT 50 Latest' in df_vapa.columns else 0
    m_53 = df_vapa['STAT 53 All'].notna().sum() if 'STAT 53 All' in df_vapa.columns else 0
    m_17 = df_vapa[df_vapa['DEX All'].astype(str).str.contains('DEX\\[17\\]', na=False)].shape[0] if 'DEX All' in df_vapa.columns else 0
    m_44 = df_vapa[df_vapa['STAT 44 Date Time Latest'].notna() & (df_vapa['VAN All'].isna())].shape[0] if 'STAT 44 Date Time Latest' in df_vapa.columns else 0
    sin_mov = df_bodega.shape[0]
    
    # CREACIÓN DE PESTAÑAS (TABS) PARA MEJOR NAVEGACIÓN
    tab1, tab2, tab3 = st.tabs(["📊 Panel Operativo", "📋 Auditoría de Piso", "🚨 Alertas de Riesgo"])
    
    # --- PESTAÑA 1: PANEL OPERATIVO ---
    with tab1:
        st.markdown("### Resumen de Excepciones e Inventario")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: st.markdown(f"<div class='metric-box'><span class='metric-title'>STAT 50</span><span class='metric-value' style='color:#FF6600;'>{m_50}</span></div>", unsafe_allow_html=True)
        with col2: st.markdown(f"<div class='metric-box'><span class='metric-title'>STAT 53</span><span class='metric-value' style='color:#FF6600;'>{m_53}</span></div>", unsafe_allow_html=True)
        with col3: st.markdown(f"<div class='metric-box'><span class='metric-title'>Solo STAT 44</span><span class='metric-value' style='color:#FF6600;'>{m_44}</span></div>", unsafe_allow_html=True)
        with col4: st.markdown(f"<div class='metric-box'><span class='metric-title'>DEX 17</span><span class='metric-value' style='color:#A0A0A0;'>{m_17}</span></div>", unsafe_allow_html=True)
        with col5: st.markdown(f"<div class='metric-box' style='border-bottom-color:#4D148C;'><span class='metric-title'>En Bodega</span><span class='metric-value' style='color:#4D148C;'>{sin_mov}</span></div>", unsafe_allow_html=True)

        chart_data = pd.DataFrame({"Categoría": ["STAT 50", "STAT 53", "Solo STAT 44", "DEX 17", "Carga en Bodega"], "Bultos": [m_50, m_53, m_44, m_17, sin_mov], "Color": ["#FF6600", "#FF6600", "#FF6600", "#8D99AE", "#4D148C"]})
        fig = px.bar(chart_data, x="Categoría", y="Bultos", text="Bultos", color="Categoría", color_discrete_sequence=chart_data["Color"].tolist(), template="plotly_dark")
        fig.update_layout(showlegend=False, height=350, margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

    # --- PESTAÑA 2: AUDITORÍA DE PISO ---
    with tab2:
        st.markdown("### Motor de Búsqueda y Filtrado")
        
        c_search, c_filter = st.columns([3, 1])
        with c_search: 
            search_query = st.text_input("🔍 Buscar número de Tracking exacto o parcial:", placeholder="Ej. 770123...")
        with c_filter: 
            st.write("")
            st.write("")
            filtro_sip = st.toggle("Solo bultos SIP") # Usamos un toggle (interruptor) más moderno
        
        cols_to_check = ['Tracking Number', 'Shipper Name', 'status', 'Status', 'Commit Date', 'SIPS Date Time Loc Latest', 'STAT 50 Latest', 'STAT 53 All', 'DEX All', 'Fecha de Carga']
        cols_to_show = [c for c in cols_to_check if c in df_bodega.columns]
        display_df = df_bodega[cols_to_show].copy()
        
        if filtro_sip:
            if 'status' in display_df.columns: display_df = display_df[display_df['status'].astype(str).str.upper() == 'SIP']
            elif 'Status' in display_df.columns: display_df = display_df[display_df['Status'].astype(str).str.upper() == 'SIP']
                
        if search_query:
            display_df = display_df[display_df['Tracking Number'].astype(str).str.contains(search_query)]
            
        def color_fedex_cliente(row):
            cliente = str(row.get('Shipper Name', ''))
            color = ''
            if 'Tricot' in cliente: color = 'background-color: #FF6600; color: white;'
            elif any(c in cliente for c in ['Cruz Verde', 'Intercarry', 'Farmacias Ahumada']): color = 'background-color: #4D148C; color: white;'
            return [color] * len(row)

        st.dataframe(display_df.style.apply(color_fedex_cliente, axis=1), use_container_width=True, hide_index=True, height=500)

    # --- PESTAÑA 3: ALERTAS DE ESTANCAMIENTO ---
    with tab3:
        st.markdown("### Control de Envejecimiento (≥ 3 días)")
        tracking_history = {}
        for day_name, data in st.session_state.history.items():
            if 'Tracking Number' in data["bodega"].columns:
                for tracking in data["bodega"]['Tracking Number'].dropna().unique():
                    tracking_history[tracking] = tracking_history.get(tracking, 0) + 1
        
        alertas_criticas = [{"Tracking Number": k, "Días Detectado en Bodega": v, "Riesgo Operativo": "Estancamiento Crítico"} for k, v in tracking_history.items() if v >= 3]
        if alertas_criticas:
            pérdidas_df = pd.DataFrame(alertas_criticas).sort_values(by="Días Detectado en Bodega", ascending=False)
            st.error(f"⚠️ Atención: Se han detectado {len(pérdidas_df)} bultos críticos estancados.")
            st.dataframe(pérdidas_df, use_container_width=True, hide_index=True)
        else:
            st.success("✅ La operación fluye correctamente. Ningún bulto muestra patrones de estancamiento prolongado en los registros cargados.")

else:
    # Pantalla de bienvenida amigable cuando no hay datos
    st.info("👋 ¡Bienvenido al Terminal VAPA! Para comenzar tu turno, carga los archivos Excel de la jornada en el menú lateral.")
            
