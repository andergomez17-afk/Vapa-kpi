    import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Control VAPA v3.0", layout="wide")

# --- MOTOR DE PROCESAMIENTO ---
class VapaEngine:
    @staticmethod
    def process_file(file):
        df = pd.read_excel(file)
        df.columns = [str(c).strip() for c in df.columns]
        df['fecha_carga'] = datetime.now().strftime('%Y-%m-%d')
        
        df_vapa = df[df['Dest Loc Cd'].astype(str).str.strip().str.upper() == 'VAPA'].copy()
        
        df_bodega = df_vapa[
            (df_vapa['VAN All'].isna() | (df_vapa['VAN All'].astype(str).str.strip() == "")) & 
            (df_vapa['POD All'].isna() | (df_vapa['POD All'].astype(str).str.strip() == ""))
        ].copy()
        
        return df_vapa, df_bodega

# --- INTERFAZ ---
st.title("📦 Control de Inventario Interno VAPA")
uploaded_file = st.sidebar.file_uploader("Cargar reporte Excel", type=["xlsx"])

if uploaded_file:
    df_vapa, df_bodega = VapaEngine.process_file(uploaded_file)
    
    # Filtro Solo SIP
    if st.sidebar.checkbox("Mostrar solo bultos con estado SIP"):
        df_bodega = df_bodega[df_bodega['status'] == 'SIP']
        
    # Colores por Cliente
    def aplicar_colores(row):
        cliente = str(row.get('Shipper Name', ''))
        style = ''
        if 'Tricot' in cliente: style = 'background-color: orange'
        elif any(c in cliente for c in ['Cruz Verde', 'Intercarry', 'Farmacias Ahumada']): style = 'background-color: blue'
        return [style] * len(row)

    st.subheader("📋 Auditoría de Inventario Físico")
    st.dataframe(df_bodega.style.apply(aplicar_colores, axis=1), use_container_width=True)
