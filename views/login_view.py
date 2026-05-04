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
    
    # Verificar si hay un token de reset en la URL
    import streamlit as st
    query_params = st.query_params
    reset_token = query_params.get('reset_token', None)
    
    if reset_token:
        show_reset_password(reset_token)
        return
    
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
            margin: 0 auto 0.8rem auto;
            display: block;
        }
        .login-title {
            color: #1f77b4;
            font-size: 1.5rem;
            font-weight: 600;
        }
        /* Responsive móvil */
        @media (max-width: 768px) {
            .login-header {
                margin-bottom: 0.5rem;
                margin-top: 0.5rem;
            }
            .login-logo {
                max-width: 60px;
                margin: 0 auto 0.3rem auto;
            }
            .login-title {
                font-size: 0.9rem;
                margin-bottom: 0.3rem;
                line-height: 1.2;
            }
            /* Reducir espaciado de inputs en móvil */
            .stTextInput, .stButton {
                margin-bottom: 0.5rem !important;
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
                <div class="login-title">Cotizador Global de Repuestos v7.5</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="login-header">
                <div class="login-title">Cotizador Global de Repuestos v7.5</div>
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
        
        # Enlace de recuperación de contraseña
        st.markdown("""<div style='text-align: center; margin-top: 1rem;'>
            <a href='#' style='color: #1f77b4; text-decoration: none; font-size: 0.9rem;'>¿Olvidaste tu contraseña?</a>
        </div>""", unsafe_allow_html=True)
        
        # Verificar si se hizo clic en recuperar contraseña
        if st.session_state.get('show_password_recovery', False):
            show_password_recovery()
        else:
            if st.button("¿Olvidaste tu contraseña?", use_container_width=True, type="secondary"):
                st.session_state['show_password_recovery'] = True
                st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: #6c757d; font-size: 0.9rem;">
            LogiPartVE Pro v7.5 © 2026 - Todos los derechos reservados
        </div>
    """, unsafe_allow_html=True)


def show_password_recovery():
    """
    Muestra el formulario de recuperación de contraseña.
    """
    st.markdown("### 🔑 Recuperar Contraseña")
    st.markdown("Ingresa tu email y te enviaremos un enlace para restablecer tu contraseña.")
    st.info("⏱️ **Importante:** El enlace de recuperación expira en **1 hora**. Solo puedes solicitar un nuevo enlace cada **5 minutos**.")
    
    # Mostrar mensajes previos si existen
    if 'recovery_message' in st.session_state:
        msg = st.session_state['recovery_message']
        if msg['type'] == 'success':
            st.success(msg['text'])
            st.info("📧 Revisa tu bandeja de entrada (y carpeta de spam) y sigue las instrucciones.")
        else:
            st.error(msg['text'])
        # Limpiar mensaje después de mostrarlo
        del st.session_state['recovery_message']
    
    with st.form("recovery_form"):
        email = st.text_input("Email", placeholder="Ingresa tu email registrado")
        submit = st.form_submit_button("Enviar enlace de recuperación", use_container_width=True)
        
        if submit:
            if not email:
                st.session_state['recovery_message'] = {
                    'type': 'error',
                    'text': '⚠️ Por favor ingresa tu email'
                }
                st.rerun()
            else:
                # Importar aquí para evitar dependencias circulares
                from services.password_recovery import PasswordRecoveryService
                
                with st.spinner('Enviando email de recuperación...'):
                    result = PasswordRecoveryService.send_recovery_email(email)
                
                if result["success"]:
                    st.session_state['recovery_message'] = {
                        'type': 'success',
                        'text': f"✅ {result['message']}. El enlace expira en 1 hora."
                    }
                else:
                    st.session_state['recovery_message'] = {
                        'type': 'error',
                        'text': f"❌ {result['message']}"
                    }
                st.rerun()
    
    # Botón para volver al login
    if st.button("← Volver al login", use_container_width=True):
        st.session_state['show_password_recovery'] = False
        if 'recovery_message' in st.session_state:
            del st.session_state['recovery_message']
        st.rerun()


def show_reset_password(token: str):
    """
    Muestra el formulario para establecer una nueva contraseña usando un token.
    """
    st.markdown("### 🔑 Restablecer Contraseña")
    
    # Verificar token
    from services.password_recovery import PasswordRecoveryService
    token_verification = PasswordRecoveryService.verify_token(token)
    
    if not token_verification['valid']:
        st.error(f"❌ {token_verification['message']}")
        if st.button("← Volver al login", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        return
    
    st.success("✅ Token válido. Ingresa tu nueva contraseña.")
    
    # Inicializar estado de reseteo exitoso
    if 'password_reset_success' not in st.session_state:
        st.session_state.password_reset_success = False
    
    # Si el reseteo fue exitoso, mostrar mensaje y botón de redirección
    if st.session_state.password_reset_success:
        st.success("✅ Contraseña restablecida exitosamente")
        st.info("Ahora puedes iniciar sesión con tu nueva contraseña.")
        if st.button("Ir al login", use_container_width=True, type="primary"):
            st.session_state.password_reset_success = False
            st.query_params.clear()
            st.rerun()
    else:
        # Mostrar formulario de reseteo
        with st.form("reset_password_form"):
            new_password = st.text_input("Nueva Contraseña", type="password", placeholder="Mínimo 6 caracteres")
            confirm_password = st.text_input("Confirmar Contraseña", type="password", placeholder="Repite la contraseña")
            submit = st.form_submit_button("Restablecer Contraseña", use_container_width=True)
            
            if submit:
                if not new_password or not confirm_password:
                    st.error("⚠️ Por favor completa ambos campos")
                elif len(new_password) < 6:
                    st.error("⚠️ La contraseña debe tener al menos 6 caracteres")
                elif new_password != confirm_password:
                    st.error("⚠️ Las contraseñas no coinciden")
                else:
                    result = PasswordRecoveryService.reset_password(token, new_password)
                    if result["success"]:
                        st.session_state.password_reset_success = True
                        st.rerun()
                    else:
                        st.error(f"❌ {result['message']}")
        
        # Botón para volver al login (fuera del formulario)
        if st.button("← Volver al login", use_container_width=True):
            st.query_params.clear()
            st.rerun()
