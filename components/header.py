# components/header.py
# Componente de encabezado con logo

import streamlit as st
from pathlib import Path
import base64

def show_header():
    """
    Muestra el encabezado de la aplicación con logo responsive.
    Diseño aprobado - NO MODIFICAR.
    """
    
    logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
    
    # CSS responsive para el header
    st.markdown("""
        <style>
        .app-header {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem 0;
            gap: 1.5rem;
        }
        .app-logo {
            width: 180px;
            height: 180px;
            object-fit: contain;
            aspect-ratio: 1/1;
        }
        .app-title {
            color: #1f77b4;
            font-size: 2rem;
            font-weight: 600;
            margin: 0;
        }
        
        /* Responsive para diferentes dispositivos */
        @media (max-width: 767px) {
            /* Móvil */
            .app-logo {
                width: 140px;
                height: 140px;
            }
            .app-title {
                font-size: 1.3rem;
            }
            .app-header {
                flex-direction: column;
                gap: 1rem;
            }
        }
        
        @media (min-width: 768px) and (max-width: 1024px) {
            /* Tablet */
            .app-logo {
                width: 160px;
                height: 160px;
            }
            .app-title {
                font-size: 1.7rem;
            }
        }
        
        @media (min-width: 2560px) {
            /* TV */
            .app-logo {
                width: 220px;
                height: 220px;
            }
            .app-title {
                font-size: 2.5rem;
            }
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Mostrar header
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        st.markdown(f"""
            <div class="app-header">
                <img src="data:image/png;base64,{img_data}" class="app-logo" alt="LogiPartVE Logo">
                <h1 class="app-title">Cotizador Global de Repuestos v7.0</h1>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="app-header">
                <h1 class="app-title">Cotizador Global de Repuestos v7.0</h1>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
