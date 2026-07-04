import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ==============================================================================
# 1. CONFIGURACIÓN DE LA INTERFAZ
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
    .sidebar .sidebar-content { background-color: #1E1E1E; }
    div.stButton > button:first-child {
        background-color: #FF6600; color: white; border-radius: 6px; font-weight: bold; width: 100%;
    }
    h1, h2, h3 { color: #FF6600; }
    .metric-box {
        background-color: #1E1E1E; padding: 15px; border-radius: 10px; 
        border-left: 5px solid #8D99AE; border: 1px solid #2F2F2F; margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Control de Inventario Interno VAPA")
st.caption("Estación Activa: VAPA - Valparaíso | Control de Excepciones y Envejecimiento de Inventario")

# ==============================================================================
# 2. MOTOR DE PROCESAMIENTO (MODIFICADO: Fecha agregada)
# ==============================================================================
class VapaEngine:
    @staticmethod
    def process_file(file):
        try:
            xls = pd.ExcelFile(file)
            sheet_name = 'BD' if 'BD' in xls.sheet_names else xls.sheet_names[0]
            df = pd.read_excel(xls, sheet_name=sheet_name)
            df.columns = [str(c).strip() for c in df.columns]
            
            # AGREGADO: Fecha de carga
            df['fecha_carga'] = datetime.now().strftime('%Y-%m-%d')
            
            df_vapa = df[df['Dest Loc Cd'].astype(str).str.strip().str.upper() == 'VAPA'].copy()
            df_bodega = df_vapa[
                (df_vapa['VAN All'].isna() | (df_vapa['VAN All'].astype(str).str.strip() == "")) & 
                (df_vapa['POD All'].isna() | (df_vapa['POD All'].astype(str).str.strip() == ""))
            ].copy()
            return df_vapa, df_bodega
        except Exception as e:
            st.error(f"Error procesando '{file.name}': {e}")
            return None, None

# ==============================================================================
# 3. CARGA Y LÓGICA DE COLORES
# ==============================================================================
def aplicar_estilo(df_estilo):
    """Aplica colores según cliente en Shipper Name"""
    def resaltar(row):
        cliente = str(row.get('Shipper Name', ''))
        estilo = ''
        if 'Tricot' in cliente: estilo = 'background-color: orange; color: black'
        elif any(c in cliente for c in ['Cruz Verde', 'Intercarry', 'Farmacias Ahumada']): estilo = 'background-color: blue; color: white'
        return [estilo] * len(row)
    return df_estilo.style.apply(resaltar, axis=1)

# ... (El resto de tu lógica de carga de archivos y estados permanece igual) ...
# (Mantén aquí tu bloque de inicialización de st.session_state.history)

# ==============================================================================
# 4. DASHBOARD PRINCIPAL (MODIFICADO: Filtro SIP y Tabla con Colores)
# ==============================================================================
if st.session_state.history:
    # ... (Tus métricas originales aquí) ...

    # --- PANEL DETALLADO DE BÚSQUEDA (MODIFICADO) ---
    st.subheader("📋 Auditoría de Inventario Físico")
    
    # MODIFICACIÓN: Filtro Solo SIP
    solo_sip = st.checkbox("Filtrar: Solo bultos con estado SIP")
    if solo_sip and 'status' in df_bodega.columns:
        df_bodega = df_bodega[df_bodega['status'] == 'SIP']
        
    search_query = st.text_input("🔍 Filtro dinámico (Tracking):", "")
    
    if search_query:
        df_bodega = df_bodega[df_bodega['Tracking Number'].astype(str).str.contains(search_query)]
        
    # Aplicar colores a la tabla final
    st.dataframe(aplicar_estilo(df_bodega), use_container_width=True, hide_index=True)
    
