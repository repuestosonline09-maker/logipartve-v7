# views/login_view.py
# Vista de login - Diseño simple y funcional

import streamlit as st
from services.auth_manager import AuthManager
from pathlib import Path
import base64

def show_login():
    """
    Muestra la pantalla de login.
    Diseño simple y responsive para PC, laptops, TV, tablets y celulares.
    """
    
    # Ruta del logo
    logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
    
    # CSS simple
    st.markdown("""
        <style>
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-logo {
            max-width: 120px;
            margin: 0 auto 1rem auto;
            display: block;
        }
        .login-title {
            color: #1f77b4;
            font-size: 1.5rem;
            font-weight: 600;
        }
        /* Responsive móvil */
        @media (max-width: 768px) {
            .login-logo {
                max-width: 100px;
            }
            .login-title {
                font-size: 1.2rem;
            }
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Logo y título
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        st.markdown(f"""
            <div class="login-header">
                <img src="data:image/png;base64,{img_data}" class="login-logo">
                <div class="login-title">Cotizador Global de Repuestos v7.0</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="login-header">
                <div class="login-title">Cotizador Global de Repuestos v7.0</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Formulario centrado
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Iniciar Sesión")
        
        with st.form("login_form"):
            username = st.text_input("Usuario", placeholder="Ingresa tu usuario")
            password = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña")
            submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("⚠️ Por favor ingresa usuario y contraseña")
                else:
                    result = AuthManager.login(username, password)
                    if result["success"]:
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(f"❌ {result['message']}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #6c757d; font-size: 0.9rem;">
            LogiPartVE Pro v7.0 © 2026 - Todos los derechos reservados
        </div>
    """, unsafe_allow_html=True)
