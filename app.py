import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN DE LA INTERFAZ (Estilo Premium Dark FedEx)
# ==============================================================================
st.set_page_config(
    page_title="FedEx VAPA - KPI Dashboard v3.0",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos CSS personalizados para emular un entorno profesional
st.markdown("""
    <style>
    .main { background-color: #121212; color: #FFFFFF; }
    .sidebar .sidebar-content { background-color: #1E1E1E; }
    div.stButton > button:first-child {
        background-color: #FF6600; color: white; border-radius: 6px; font-weight: bold; width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #E05900; border-color: #FF6600; }
    h1, h2, h3 { color: #FF6600; }
    .metric-box {
        background-color: #1E1E1E; padding: 15px; border-radius: 10px; 
        border-left: 5px solid #8D99AE; border: 1px solid #2F2F2F; margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 FedEx VAPA — Sistema Automatizado de Control de KPI")
st.caption("Estación Activa: VAPA - Valparaíso | Control de Excepciones y Envejecimiento de Inventario")

# ==============================================================================
# 2. MOTOR DE PROCESAMIENTO LOGÍSTICO
# ==============================================================================
class VapaEngine:
    @staticmethod
    def process_file(file):
        """Procesa el archivo Excel aplicando las reglas de negocio de la estación VAPA."""
        try:
            xls = pd.ExcelFile(file)
            # Prioriza la pestaña 'BD' si existe, de lo contrario toma la primera disponible
            sheet_name = 'BD' if 'BD' in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            # Limpieza de nombres de columnas
            df.columns = [str(c).strip() for c in df.columns]
            
            # REGLA 1: Filtro Maestro - Solo la estación destino VAPA
            df_vapa = df[df['Dest Loc Cd'].astype(str).str.strip().str.upper() == 'VAPA'].copy()
            
            # REGLA 2: Aislamiento de Carga Física Pura en Bodega (Sin salida a reparto ni entrega)
            df_bodega = df_vapa[
                (df_vapa['VAN All'].isna() | (df_vapa['VAN All'].astype(str).str.strip() == "")) & 
                (df_vapa['POD All'].isna() | (df_vapa['POD All'].astype(str).str.strip() == ""))
            ].copy()
            
            return df_vapa, df_bodega
        except Exception as e:
            st.error(f"Error crítico al procesar el archivo '{file.name}': {e}")
            return None, None

# ==============================================================================
# 3. CONTROLES Y CARGA DE DATOS (BARRA LATERAL)
# ==============================================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b9/FedEx_Express_logo.svg", width=140)
st.sidebar.header("📥 Carga de Reportes")

uploaded_files = st.sidebar.file_uploader(
    "Sube tus archivos diarios de tracking (.xlsx)", 
    type=["xlsx"], 
    accept_multiple_files=True
)

# Inicializar almacenamiento de estado persistente
if "history" not in st.session_state:
    st.session_state.history = {}

# Procesar y almacenar archivos indexados por nombre
if uploaded_files:
    for file in uploaded_files:
        if file.name not in st.session_state.history:
            df_vapa, df_bodega = VapaEngine.process_file(file)
            if df_vapa is not None:
                st.session_state.history[file.name] = {
                    "vapa": df_vapa,
                    "bodega": df_bodega
                }
    st.sidebar.success(f"✅ {len(uploaded_files)} archivo(s) indexado(s) correctamente.")

# ==============================================================================
# 4. DASHBOARD PRINCIPAL (EJECUCIÓN)
# ==============================================================================
if st.session_state.history:
    available_days = sorted(list(st.session_state.history.keys()))
    selected_day = st.sidebar.selectbox("📅 Seleccionar Día de Análisis", available_days)
    
    # Extraer los datos filtrados correspondientes al día seleccionado
    df_vapa = st.session_state.history[selected_day]["vapa"]
    df_bodega = st.session_state.history[selected_day]["bodega"]
    
    # --- PROCESAMIENTO EXTRACCIÓN DE MÉTRICAS ---
    m_50 = df_vapa['STAT 50 Latest'].notna().sum() if 'STAT 50 Latest' in df_vapa.columns else 0
    m_53 = df_vapa['STAT 53 All'].notna().sum() if 'STAT 53 All' in df_vapa.columns else 0
    m_17 = df_vapa[df_vapa['DEX All'].astype(str).str.contains('DEX\\[17\\]', na=False)].shape[0] if 'DEX All' in df_vapa.columns else 0
    m_44 = df_vapa[df_vapa['STAT 44 Date Time Latest'].notna() & (df_vapa['VAN All'].isna())].shape[0] if 'STAT 44 Date Time Latest' in df_vapa.columns else 0
    sin_mov = df_bodega.shape[0]
    
    # --- FILA DE INDICADORES (TARJETAS VISUALES) ---
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"<div class='metric-box' style='border-left-color: #00B4D8;'><strong>STAT 50 (Falta Doc)</strong><br><span style='font-size:26px;font-weight:bold;color:#00B4D8;'>{m_50}</span></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-box' style='border-left-color: #FFB703;'><strong>STAT 53 (Incompleto)</strong><br><span style='font-size:26px;font-weight:bold;color:#FFB703;'>{m_53}</span></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-box' style='border-left-color: #E63946;'><strong>Solo STAT 44 (Afecta KPI)</strong><br><span style='font-size:26px;font-weight:bold;color:#E63946;'>{m_44}</span></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-box' style='border-left-color: #06D6A0;'><strong>DEX 17 (Justificado)</strong><br><span style='font-size:26px;font-weight:bold;color:#06D6A0;'>{m_17}</span></div>", unsafe_allow_html=True)
    with col5:
        st.markdown(f"<div class='metric-box' style='border-left-color: #8D99AE;'><strong>En Bodega (Inventario)</strong><br><span style='font-size:26px;font-weight:bold;color:#FFFFFF;'>{sin_mov}</span></div>", unsafe_allow_html=True)

    # --- GRÁFICA INTERACTIVA ---
    st.subheader("📈 Distribución Operativa por Tipo de Excepción")
    
    chart_data = pd.DataFrame({
        "Categoría": ["STAT 50", "STAT 53", "Solo STAT 44", "DEX 17", "Carga en Bodega"],
        "Bultos": [m_50, m_53, m_44, m_17, sin_mov],
        "Color": ["#00B4D8", "#FFB703", "#E63946", "#06D6A0", "#8D99AE"]
    })
    
    fig = px.bar(
        chart_data, x="Categoría", y="Bultos", text="Bultos",
        color="Categoría", color_discrete_sequence=chart_data["Color"].tolist(),
        template="plotly_dark"
    )
    fig.update_layout(
        showlegend=False, 
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title=None,
        yaxis_title="Cantidad de Bultos"
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- CRUCE HISTÓRICO / ALERTA DE PÉRDIDAS ---
    st.subheader("🚨 Reporte Avanzado: Alerta de Envejecimiento e Inventario Crítico")
    
    # Calcular reincidencias acumuladas sumando la presencia en carga física a lo largo del tiempo cargado
    tracking_history = {}
    for day_name, data in st.session_state.history.items():
        if 'Tracking Number' in data["bodega"].columns:
            for tracking in data["bodega"]['Tracking Number'].dropna().unique():
                tracking_history[tracking] = tracking_history.get(tracking, 0) + 1
    
    # Filtrar aquellos bultos presentes en bodega por 3 o más días
    alertas_criticas = [
        {"Tracking Number": k, "Días Detectado en Bodega": v, "Riesgo Operativo": "🚨 Alto Riesgo / Posible Pérdida"}
        for k, v in tracking_history.items() if v >= 3
    ]
    
    if alertas_criticas:
        pérdidas_df = pd.DataFrame(alertas_criticas).sort_values(by="Días Detectado en Bodega", ascending=False)
        st.warning(f"Se han detectado {len(pérdidas_df)} bultos críticos estancados en bodega durante 3 o más días acumulados.")
        st.dataframe(pérdidas_df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Excelente: Ningún bulto muestra patrones de estancamiento prolongado (≥ 3 días) en el historial actual.")

    # --- PANEL DETALLADO DE BÚSQUEDA ---
    st.subheader("📋 Auditoría de Inventario Físico")
    search_query = st.text_input("🔍 Filtro dinámico (Ingresa número de Tracking):", "")
    
    # Columnas esenciales para la revisión en piso
    cols_to_show = [c for c in ['Tracking Number', 'SIPS Date Time Loc Latest', 'STAT 50 Latest', 'STAT 53 All', 'DEX All'] if c in df_bodega.columns]
    display_df = df_bodega[cols_to_show].copy()
    
    if search_query:
        display_df = display_df[display_df['Tracking Number'].astype(str).str.contains(search_query)]
        
    st.dataframe(display_df, use_container_width=True, hide_index=True)

else:
    # Estado inicial: Pantalla vacía instructiva
    st.info("💡 Para comenzar el análisis, arrastra y suelta tus archivos Excel diarios (.xlsx) en el panel izquierdo. El sistema consolidará automáticamente los indicadores.")
