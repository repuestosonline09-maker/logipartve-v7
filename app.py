# app.py
# Aplicación principal LogiPartVE Pro v7.0

import streamlit as st
from pathlib import Path

# Configuración de la página
st.set_page_config(
    page_title="LogiPartVE Pro",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar módulos
from database.db_manager import DBManager
from services.auth_manager import AuthManager
from services.session_manager import SessionManager
import os
import sys
from components.header import show_header
from views.login_view import show_login
from views.admin_panel import show_admin_panel
from views.analyst_panel import render_analyst_panel
from views.diagnostics_view import show_diagnostics

# CSS global responsive
st.markdown("""
    <style>
    /* Estilos generales */
    .main {
        padding: 1rem;
    }
    
    /* Footer */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #f8f9fa;
        text-align: center;
        padding: 0.8rem;
        color: #6c757d;
        font-size: 0.9rem;
        border-top: 1px solid #dee2e6;
        z-index: 999;
    }
    
    /* Ajuste para contenido con footer fijo */
    .block-container {
        padding-bottom: 4rem !important;
    }
    
    /* Responsive móvil */
    @media (max-width: 768px) {
        .main {
            padding: 0.5rem;
        }
        .footer {
            font-size: 0.75rem;
            padding: 0.5rem;
        }
    }
    
    /* Botón scroll to top */
    .scroll-top {
        position: fixed;
        bottom: 60px;
        right: 20px;
        background-color: #1f77b4;
        color: white;
        border: none;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        font-size: 24px;
        cursor: pointer;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        z-index: 1000;
        display: none;
    }
    
    .scroll-top:hover {
        background-color: #155a8a;
    }
    </style>
    
    <script>
    // Scroll to top functionality
    window.onscroll = function() {
        var btn = document.querySelector('.scroll-top');
        if (btn) {
            if (document.body.scrollTop > 300 || document.documentElement.scrollTop > 300) {
                btn.style.display = "block";
            } else {
                btn.style.display = "none";
            }
        }
    };
    
    function scrollToTop() {
        window.scrollTo({top: 0, behavior: 'smooth'});
    }
    </script>
    
    <button class="scroll-top" onclick="scrollToTop()">↑</button>
""", unsafe_allow_html=True)

# Inicializar base de datos
DBManager.init_database()

# Asegurar que existe usuario admin con contraseña conocida
def ensure_admin_user():
    """Verifica y crea/resetea el usuario admin si es necesario."""
    try:
        import bcrypt
        admin_password = "Lamesita.99"
        
        # Verificar si existe el usuario admin
        admin_user = DBManager.get_user_by_username('admin')
        
        if not admin_user:
            # No existe, crear usuario admin
            DBManager.create_user(
                username='admin',
                password=admin_password,
                full_name='Administrador',
                role='admin',
                email=None
            )
            print("✅ Usuario admin creado exitosamente")
        else:
            # Existe, verificar si la contraseña funciona
            if not DBManager.verify_user('admin', admin_password):
                # Contraseña no funciona, resetearla
                DBManager.change_password(admin_user['id'], admin_password)
                print("✅ Contraseña del admin reseteada exitosamente")
    except Exception as e:
        print(f"⚠️  Error al verificar/crear usuario admin: {e}")

ensure_admin_user()

# Inicializar configuraciones por defecto
def ensure_default_config():
    """Verifica y crea configuraciones por defecto si no existen."""
    try:
        from database.init_default_config import initialize_default_config
        initialize_default_config()
    except Exception as e:
        print(f"⚠️  Error al inicializar configuraciones por defecto: {e}")

ensure_default_config()

def main():
    """Función principal de la aplicación."""
    
    # Inicializar gestor de sesión
    SessionManager.init_session()
    
    # Ejecutar migraciones automáticamente (solo una vez)
    if 'migrations_executed' not in st.session_state:
        try:
            # Ejecutar migración de numeración de cotizaciones
            sys.path.insert(0, os.path.dirname(__file__))
            from database.migrations.add_quote_numbering import run_migration
            run_migration()
            
            st.session_state.migrations_executed = True
        except Exception as e:
            # Si falla, continuar (las tablas ya pueden existir)
            print(f"Migración de numeración ya ejecutada o error: {e}")
            st.session_state.migrations_executed = True
    
    # Ejecutar migración de países SOLO UNA VEZ por sesión
    # Esto evita ejecuciones innecesarias que pueden causar pérdida de sesión
    if 'countries_migration_executed' not in st.session_state:
        try:
            print("🔄 Ejecutando actualización de lista de países...")
            from database.migrations.update_countries_list import run_migration as update_countries
            update_countries()
            st.session_state.countries_migration_executed = True
            print("✅ Lista de países actualizada")
        except Exception as e:
            # Marcar como ejecutada incluso si falla para evitar reintentos constantes
            st.session_state.countries_migration_executed = True
            print(f"⚠️  Error al actualizar países (puede ser normal si ya existen): {e}")
    
    # Verificar si el usuario está logueado
    if not AuthManager.is_logged_in():
        # Mostrar pantalla de login
        show_login()
    else:
        # Usuario logueado - mostrar aplicación principal
        show_main_app()
    
    # Footer fijo
    st.markdown("""
        <div class="footer">
            LogiPartVE Pro v7.0 © 2026 - Todos los derechos reservados
        </div>
    """, unsafe_allow_html=True)


def show_main_app():
    """Muestra la aplicación principal después del login."""
    
    # Mantener sesión activa
    SessionManager.check_and_refresh_session()
    
    # Mostrar header
    show_header()
    
    # Sidebar con información del usuario
    with st.sidebar:
        user = AuthManager.get_current_user()
        
        st.markdown("---")
        
        # Información del usuario
        role_icon = "👑" if user['role'] == "admin" else "👤"
        role_label = "Administrador" if user['role'] == "admin" else "Analista"
        
        st.markdown(f"### {role_icon} {user['full_name']}")
        st.caption(f"Rol: {role_label}")
        
        st.markdown("---")
        
        # Menú de navegación
        st.markdown("### 📋 Menú")
        
        menu_options = []
        
        if user['role'] == "admin":
            menu_options = [
                "🏠 Inicio",
                "🔧 Panel de Administración",
                "📝 Crear Cotización",
                "📊 Mis Cotizaciones",
                "🔍 Diagnóstico del Sistema"
            ]
        else:
            menu_options = [
                "🏠 Inicio",
                "📝 Crear Cotización",
                "📊 Mis Cotizaciones"
            ]
        
        selected_menu = st.radio("", menu_options, label_visibility="collapsed")
        
        st.markdown("---")
        
        # Botón de cerrar sesión
        def do_logout():
            AuthManager.logout()
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True, key="btn_cerrar_sesion", on_click=do_logout):
            st.rerun()
    
    # Contenido principal según la opción seleccionada
    if selected_menu == "🏠 Inicio":
        show_home()
    elif selected_menu == "🔧 Panel de Administración":
        show_admin_panel()
    elif selected_menu == "📝 Crear Cotización":
        show_create_quote()
    elif selected_menu == "📊 Mis Cotizaciones":
        show_my_quotes()
    elif selected_menu == "🔍 Diagnóstico del Sistema":
        show_diagnostics()


def show_home():
    """Muestra la pantalla de inicio."""
    
    user = AuthManager.get_current_user()
    
    st.markdown(f"## ¡Bienvenido, {user['full_name']}! 👋")
    
    st.markdown("""
        <div style="background-color: #d4edda; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #28a745;">
            <h3 style="color: #155724; margin-top: 0;">✅ Fase 1 Completa: Sistema de autenticación funcionando correctamente</h3>
            <p style="color: #155724; margin-bottom: 0;">
                El login, header y estructura base están operativos y aprobados.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 📋 Próximas Fases:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            **✅ Fase 2: Panel de Administración (ACTUAL)**
            - ✅ Gestión de usuarios
            - ✅ Configuración del sistema
            - ✅ Reportes básicos
        """)
        
        st.markdown("""
            **🔄 Fase 3: Panel de Analista**
            - Creación de cotizaciones
            - Gestión de items ilimitados
            - Auto-detección de origen
            - Sistema de caché
        """)
    
    with col2:
        st.markdown("""
            **⏳ Fase 4: Motor de Cálculo de Precios**
            - Traducción de fórmulas Excel a Python
            - Variables editables por admin
            - Cálculo dinámico
            - Factores de ganancia
        """)
        
        st.markdown("""
            **⏳ Fase 5: Generador de Documentos**
            - Generación de PDF (email)
            - Generación de JPEG 1080x1920 (WhatsApp/Instagram)
            - Diseño profesional responsive
        """)
    
    st.markdown("---")
    
    # Información del sistema
    with st.expander("ℹ️ Información del Sistema"):
        st.markdown("""
            **LogiPartVE Pro v7.0**
            
            Sistema de cotización profesional para autopartes con:
            - 🔐 Autenticación multi-usuario (admin/analista)
            - 💾 Base de datos SQLite (migrable a PostgreSQL)
            - 📱 Diseño responsive (PC, laptops, TV, tablets, móviles)
            - 📄 Generación dual: PDF + JPEG
            - 🤖 Integración con IA (próximamente)
            - ☁️ Caché inteligente de repuestos
            
            **Tecnologías:**
            - Framework: Streamlit (Python)
            - Base de datos: SQLite → PostgreSQL
            - Autenticación: bcrypt
            - Generación: ReportLab (PDF) + Pillow (JPEG)
        """)


def show_create_quote():
    """Muestra el módulo de creación de cotizaciones (Fase 3)."""
    
    # Renderizar el panel de analista
    render_analyst_panel()


def show_my_quotes():
    """Muestra el módulo de gestión de cotizaciones (Fase 3)."""
    from views.my_quotes_panel import render_my_quotes_panel
    render_my_quotes_panel()


if __name__ == "__main__":
    main()
