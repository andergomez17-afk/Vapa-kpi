import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN DE LA INTERFAZ Y ESTILOS
# ==============================================================================
# Nota: st.set_page_config DEBE ser el primer comando de Streamlit
st.set_page_config(
    page_title="Control de Inventario Interno VAPA",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { background-color: #121212; color: #FFFFFF; }
    .sidebar .sidebar-content { background-color: #1E1E1E; }
    div.stButton > button:first-child {
        background-color: #4D148C; color: white; border-radius: 6px; font-weight: bold; width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #FF6600; border-color: #FFFFFF; }
    h1, h2, h3 { color: #FF6600; }
    .metric-box {
        background-color: #1E1E1E; padding: 15px; border-radius: 10px; 
        border-left: 5px solid #4D148C; border: 1px solid #2F2F2F; margin-bottom: 10px;
    }
    .login-box {
        max-width: 400px; margin: 60px auto; padding: 30px; 
        background-color: #1E1E1E; border-radius: 10px; 
        border: 2px solid #FF6600; box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. CAPA DE SEGURIDAD (LOGIN)
# ==============================================================================
def check_password():
    """Valida la contraseña antes de mostrar la aplicación."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        # Pantalla de Login
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #FF6600;'>📦 Acceso Restringido</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #A0A0A0;'>Ingresa la clave de operaciones para continuar.</p>", unsafe_allow_html=True)
        
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión"):
            # AQUÍ PUEDES CAMBIAR TU CONTRASEÑA
            if pwd == "Vapa2026": 
                st.session_state["password_correct"] = True
                st.rerun() # Recarga la página para mostrar el dashboard
            else:
                st.error("❌ Contraseña incorrecta. Inténtalo de nuevo.")
        st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True

# Si la contraseña no es correcta, detenemos la app aquí mismo.
if not check_password():
    st.stop()

# ==============================================================================
# 3. DASHBOARD PRINCIPAL (Si el login es exitoso)
# ==============================================================================
col_titulo, col_salir = st.columns([8, 1])
with col_titulo:
    st.title("📦 Control de Inventario Interno VAPA")
    st.caption("Estación Activa: VAPA - Valparaíso | Control de Excepciones y Envejecimiento de Inventario")
with col_salir:
    st.write("") # Espacio para alinear
    if st.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()

# --- MOTOR DE PROCESAMIENTO LOGÍSTICO ---
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
            st.error(f"Error crítico al procesar el archivo '{file.name}': {e}")
            return None, None

# --- BARRA LATERAL ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b9/FedEx_Express_logo.svg", width=140)
st.sidebar.header("📥 Carga de Reportes")
uploaded_files = st.sidebar.file_uploader("Sube tus archivos diarios (.xlsx)", type=["xlsx"], accept_multiple_files=True)

if "history" not in st.session_state: st.session_state.history = {}

if uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state.history:
            df_vapa, df_bodega = VapaEngine.process_file(file)
            if df_vapa is not None:
                st.session_state.history[file.name] = {"vapa": df_vapa, "bodega": df_bodega}
    st.sidebar.success(f"✅ {len(uploaded_files)} archivo(s) indexado(s) correctamente.")

# --- EJECUCIÓN ---
if st.session_state.history:
    available_days = sorted(list(st.session_state.history.keys()))
    selected_day = st.sidebar.selectbox("📅 Seleccionar Día de Análisis", available_days)
    
    df_vapa = st.session_state.history[selected_day]["vapa"]
    df_bodega = st.session_state.history[selected_day]["bodega"]
    
    m_50 = df_vapa['STAT 50 Latest'].notna().sum() if 'STAT 50 Latest' in df_vapa.columns else 0
    m_53 = df_vapa['STAT 53 All'].notna().sum() if 'STAT 53 All' in df_vapa.columns else 0
    m_17 = df_vapa[df_vapa['DEX All'].astype(str).str.contains('DEX\\[17\\]', na=False)].shape[0] if 'DEX All' in df_vapa.columns else 0
    m_44 = df_vapa[df_vapa['STAT 44 Date Time Latest'].notna() & (df_vapa['VAN All'].isna())].shape[0] if 'STAT 44 Date Time Latest' in df_vapa.columns else 0
    sin_mov = df_bodega.shape[0]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: st.markdown(f"<div class='metric-box' style='border-left-color: #00B4D8;'><strong>STAT 50 (Falta Doc)</strong><br><span style='font-size:26px;font-weight:bold;color:#00B4D8;'>{m_50}</span></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='metric-box' style='border-left-color: #FFB703;'><strong>STAT 53 (Incompleto)</strong><br><span style='font-size:26px;font-weight:bold;color:#FFB703;'>{m_53}</span></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='metric-box' style='border-left-color: #E63946;'><strong>Solo STAT 44 (Afecta KPI)</strong><br><span style='font-size:26px;font-weight:bold;color:#E63946;'>{m_44}</span></div>", unsafe_allow_html=True)
    with col4: st.markdown(f"<div class='metric-box' style='border-left-color: #06D6A0;'><strong>DEX 17 (Justificado)</strong><br><span style='font-size:26px;font-weight:bold;color:#06D6A0;'>{m_17}</span></div>", unsafe_allow_html=True)
    with col5: st.markdown(f"<div class='metric-box' style='border-left-color: #4D148C;'><strong>En Bodega (Inventario)</strong><br><span style='font-size:26px;font-weight:bold;color:#FFFFFF;'>{sin_mov}</span></div>", unsafe_allow_html=True)

    st.subheader("📈 Distribución Operativa por Tipo de Excepción")
    chart_data = pd.DataFrame({"Categoría": ["STAT 50", "STAT 53", "Solo STAT 44", "DEX 17", "Carga en Bodega"], "Bultos": [m_50, m_53, m_44, m_17, sin_mov], "Color": ["#00B4D8", "#FFB703", "#E63946", "#06D6A0", "#4D148C"]})
    fig = px.bar(chart_data, x="Categoría", y="Bultos", text="Bultos", color="Categoría", color_discrete_sequence=chart_data["Color"].tolist(), template="plotly_dark")
    fig.update_layout(showlegend=False, height=320, margin=dict(l=20, r=20, t=20, b=20), yaxis_title="Cantidad de Bultos")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🚨 Reporte Avanzado: Alerta de Envejecimiento e Inventario Crítico")
    tracking_history = {}
    for day_name, data in st.session_state.history.items():
        if 'Tracking Number' in data["bodega"].columns:
            for tracking in data["bodega"]['Tracking Number'].dropna().unique():
                tracking_history[tracking] = tracking_history.get(tracking, 0) + 1
    
    alertas_criticas = [{"Tracking Number": k, "Días Detectado en Bodega": v, "Riesgo Operativo": "🚨 Alto Riesgo / Posible Pérdida"} for k, v in tracking_history.items() if v >= 3]
    if alertas_criticas:
        pérdidas_df = pd.DataFrame(alertas_criticas).sort_values(by="Días Detectado en Bodega", ascending=False)
        st.warning(f"Se han detectado {len(pérdidas_df)} bultos críticos estancados en bodega durante 3 o más días acumulados.")
        st.dataframe(pérdidas_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Excelente: Ningún bulto muestra patrones de estancamiento prolongado (≥ 3 días) en el historial actual.")

    st.subheader("📋 Auditoría de Inventario Físico")
    col_buscar, col_sip = st.columns([3, 1])
    with col_buscar: search_query = st.text_input("🔍 Filtro dinámico (Ingresa número de Tracking):", "")
    with col_sip: 
        st.write("")
        st.write("")
        filtro_sip = st.checkbox("Mostrar solo bultos SIP")
    
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

    st.dataframe(display_df.style.apply(color_fedex_cliente, axis=1), use_container_width=True, hide_index=True)

else:
    st.info("💡 Para comenzar el análisis, arrastra y suelta tus archivos Excel diarios (.xlsx) en el panel izquierdo.")
