import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# ==============================================================================
# CONFIGURACIÓN E INYECCIÓN DE ESTILOS
# ==============================================================================
st.set_page_config(page_title="FedEx VAPA - KPI Dashboard v3.0", page_icon="📦", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #121212; color: #FFFFFF; }
    .metric-box { background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #2F2F2F; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Control de Inventario Interno VAPA")

# ==============================================================================
# MOTOR DE PROCESAMIENTO (Con adición de fecha)
# ==============================================================================
class VapaEngine:
    @staticmethod
    def process_file(file):
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        df['fecha_carga'] = datetime.now().strftime('%Y-%m-%d') # MODIFICACIÓN: Fecha automática
        
        df_vapa = df[df['Dest Loc Cd'].astype(str).str.strip().str.upper() == 'VAPA'].copy()
        
        df_bodega = df_vapa[
            (df_vapa['VAN All'].isna() | (df_vapa['VAN All'].astype(str).str.strip() == "")) & 
            (df_vapa['POD All'].isna() | (df_vapa['POD All'].astype(str).str.strip() == ""))
        ].copy()
        return df_vapa, df_bodega

# ==============================================================================
# LÓGICA DE COLORES POR CLIENTE
# ==============================================================================
def aplicar_colores(row):
    cliente = str(row.get('Shipper Name', ''))
    style = ''
    if 'Tricot' in cliente: style = 'background-color: orange; color: black'
    elif any(c in cliente for c in ['Cruz Verde', 'Intercarry', 'Farmacias Ahumada']): style = 'background-color: blue; color: white'
    return [style] * len(row)

# ==============================================================================
# CARGA Y EJECUCIÓN (Manteniendo todos tus filtros originales)
# ==============================================================================
uploaded_file = st.sidebar.file_uploader("Cargar reporte Excel", type=["xlsx"])

if uploaded_file:
    df_vapa, df_bodega = VapaEngine.process_file(uploaded_file)
    
    # MODIFICACIÓN: Filtro Solo SIP
    if st.sidebar.checkbox("Mostrar solo bultos con estado SIP"):
        if 'status' in df_bodega.columns:
            df_bodega = df_bodega[df_bodega['status'] == 'SIP']

    st.subheader("📋 Auditoría de Inventario Físico")
    st.dataframe(df_bodega.style.apply(aplicar_colores, axis=1), use_container_width=True)
else:
    st.info("💡 Por favor, sube un archivo Excel para comenzar.")
