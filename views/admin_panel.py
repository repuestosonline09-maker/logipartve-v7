# views/admin_panel.py
# Panel de Administración - Fase 2

import streamlit as st
from database.db_manager import DBManager
from services.auth_manager import AuthManager
from datetime import datetime, timedelta

def show_admin_panel():
    """
    Muestra el panel de administración completo.
    Solo accesible para usuarios con rol 'admin'.
    Diseño responsive para PC, laptops, TV, tablets y móviles.
    """
    
    # Verificar que el usuario sea administrador
    if not AuthManager.is_admin():
        st.error("⛔ Acceso denegado. Esta sección es solo para administradores.")
        return
    
    # CSS responsive para el panel
    st.markdown("""
        <style>
        .admin-section {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }
        .admin-section h3 {
            color: #1f77b4;
            margin-bottom: 1rem;
        }
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
        }
        .stat-label {
            color: #6c757d;
            font-size: 1rem;
            margin-top: 0.5rem;
        }
        
        /* Responsive móvil */
        @media (max-width: 768px) {
            .admin-section {
                padding: 1rem;
            }
            .stat-number {
                font-size: 1.8rem;
            }
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("🔧 Panel de Administración")
    
    # Tabs para organizar las secciones
    tab1, tab2, tab3 = st.tabs([
        "👥 Gestión de Usuarios",
        "⚙️ Configuración del Sistema",
        "📊 Reportes y Estadísticas"
    ])
    
    # TAB 1: GESTIÓN DE USUARIOS
    with tab1:
        show_user_management()
    
    # TAB 2: CONFIGURACIÓN DEL SISTEMA
    with tab2:
        show_system_configuration()
    
    # TAB 3: REPORTES Y ESTADÍSTICAS
    with tab3:
        show_reports_and_stats()


def show_user_management():
    """Módulo de gestión de usuarios."""
    
    st.markdown('<div class="admin-section">', unsafe_allow_html=True)
    st.markdown("### 👥 Gestión de Usuarios")
    
    # Sub-tabs para las operaciones
    subtab1, subtab2, subtab3 = st.tabs([
        "➕ Crear Usuario",
        "✏️ Editar Usuario",
        "📋 Lista de Usuarios"
    ])
    
    # SUBTAB 1: Crear Usuario
    with subtab1:
        st.markdown("#### Crear Nuevo Usuario")
        
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Nombre de Usuario*", placeholder="usuario123")
                new_full_name = st.text_input("Nombre Completo*", placeholder="Juan Pérez")
            
            with col2:
                new_password = st.text_input("Contraseña*", type="password", placeholder="Mínimo 6 caracteres")
                new_role = st.selectbox("Rol*", ["analyst", "admin"], format_func=lambda x: "Analista" if x == "analyst" else "Administrador")
            
            submit_create = st.form_submit_button("✅ Crear Usuario", use_container_width=True)
            
            if submit_create:
                if not new_username or not new_password or not new_full_name:
                    st.error("⚠️ Todos los campos marcados con * son obligatorios")
                elif len(new_password) < 6:
                    st.error("⚠️ La contraseña debe tener al menos 6 caracteres")
                else:
                    success = DBManager.create_user(new_username, new_password, new_full_name, new_role)
                    if success:
                        st.success(f"✅ Usuario '{new_username}' creado exitosamente")
                        DBManager.log_activity(
                            st.session_state.user_id,
                            "create_user",
                            f"Creó usuario: {new_username} ({new_role})"
                        )
                        st.rerun()
                    else:
                        st.error("❌ Error al crear usuario. El nombre de usuario puede estar en uso.")
    
    # SUBTAB 2: Editar Usuario
    with subtab2:
        st.markdown("#### Editar Usuario Existente")
        
        users = DBManager.get_all_users()
        
        if not users:
            st.info("No hay usuarios para editar")
        else:
            # Selector de usuario
            user_options = {f"{u['username']} - {u['full_name']}": u['id'] for u in users}
            selected_user_label = st.selectbox("Seleccionar Usuario", list(user_options.keys()))
            selected_user_id = user_options[selected_user_label]
            
            selected_user = DBManager.get_user_by_id(selected_user_id)
            
            if selected_user:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Editar Información**")
                    with st.form("edit_user_form"):
                        edit_full_name = st.text_input("Nombre Completo", value=selected_user['full_name'])
                        edit_role = st.selectbox(
                            "Rol",
                            ["analyst", "admin"],
                            index=0 if selected_user['role'] == "analyst" else 1,
                            format_func=lambda x: "Analista" if x == "analyst" else "Administrador"
                        )
                        
                        submit_edit = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                        
                        if submit_edit:
                            success = DBManager.update_user(selected_user_id, edit_full_name, edit_role)
                            if success:
                                st.success("✅ Usuario actualizado exitosamente")
                                DBManager.log_activity(
                                    st.session_state.user_id,
                                    "update_user",
                                    f"Actualizó usuario: {selected_user['username']}"
                                )
                                st.rerun()
                            else:
                                st.error("❌ Error al actualizar usuario")
                
                with col2:
                    st.markdown("**Cambiar Contraseña**")
                    with st.form("change_password_form"):
                        new_password = st.text_input("Nueva Contraseña", type="password", placeholder="Mínimo 6 caracteres")
                        confirm_password = st.text_input("Confirmar Contraseña", type="password")
                        
                        submit_password = st.form_submit_button("🔑 Cambiar Contraseña", use_container_width=True)
                        
                        if submit_password:
                            if not new_password or not confirm_password:
                                st.error("⚠️ Complete ambos campos")
                            elif len(new_password) < 6:
                                st.error("⚠️ La contraseña debe tener al menos 6 caracteres")
                            elif new_password != confirm_password:
                                st.error("⚠️ Las contraseñas no coinciden")
                            else:
                                success = DBManager.change_password(selected_user_id, new_password)
                                if success:
                                    st.success("✅ Contraseña actualizada exitosamente")
                                    DBManager.log_activity(
                                        st.session_state.user_id,
                                        "change_password",
                                        f"Cambió contraseña de usuario: {selected_user['username']}"
                                    )
                                else:
                                    st.error("❌ Error al cambiar contraseña")
                
                # Botón de eliminar (solo si no es el admin principal)
                if selected_user['username'] != 'admin':
                    st.markdown("---")
                    st.markdown("**⚠️ Zona de Peligro**")
                    if st.button(f"🗑️ Eliminar Usuario: {selected_user['username']}", type="secondary"):
                        success = DBManager.delete_user(selected_user_id)
                        if success:
                            st.success(f"✅ Usuario '{selected_user['username']}' eliminado")
                            DBManager.log_activity(
                                st.session_state.user_id,
                                "delete_user",
                                f"Eliminó usuario: {selected_user['username']}"
                            )
                            st.rerun()
                        else:
                            st.error("❌ Error al eliminar usuario")
                else:
                    st.info("ℹ️ El usuario administrador principal no puede ser eliminado")
    
    # SUBTAB 3: Lista de Usuarios
    with subtab3:
        st.markdown("#### Lista de Todos los Usuarios")
        
        users = DBManager.get_all_users()
        
        if not users:
            st.info("No hay usuarios registrados")
        else:
            # Crear tabla de usuarios
            for user in users:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 2])
                    
                    with col1:
                        role_icon = "👑" if user['role'] == "admin" else "👤"
                        st.markdown(f"**{role_icon} {user['full_name']}**")
                    
                    with col2:
                        st.text(f"Usuario: {user['username']}")
                    
                    with col3:
                        role_label = "Admin" if user['role'] == "admin" else "Analista"
                        st.text(role_label)
                    
                    with col4:
                        if user['last_login']:
                            last_login = datetime.fromisoformat(user['last_login'])
                            st.text(f"Último acceso: {last_login.strftime('%d/%m/%Y %H:%M')}")
                        else:
                            st.text("Sin accesos")
                    
                    st.markdown("---")
    
    st.markdown('</div>', unsafe_allow_html=True)


def show_system_configuration():
    """Módulo de configuración del sistema."""
    
    st.markdown('<div class="admin-section">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Configuración del Sistema")
    
    # Obtener configuraciones actuales
    config = DBManager.get_all_config()
    
    st.markdown("#### Variables de Cálculo de Precios")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Tasas e Impuestos**")
        
        with st.form("tax_config_form"):
            exchange_diff = st.number_input(
                "Diferencial de Cambio Diario (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(config.get('exchange_differential', {}).get('value', 25)),
                step=0.1,
                help="Porcentaje de diferencial de cambio (Y30)"
            )
            
            american_tax = st.number_input(
                "Impuesto Empresa Americana (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(config.get('american_tax', {}).get('value', 7)),
                step=0.1,
                help="Porcentaje de TAX"
            )
            
            venezuela_iva = st.number_input(
                "IVA Venezuela (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(config.get('venezuela_iva', {}).get('value', 16)),
                step=0.1,
                help="Porcentaje de IVA en Venezuela"
            )
            
            submit_tax = st.form_submit_button("💾 Guardar Tasas e Impuestos", use_container_width=True)
            
            if submit_tax:
                DBManager.update_config('exchange_differential', str(exchange_diff), st.session_state.user_id)
                DBManager.update_config('american_tax', str(american_tax), st.session_state.user_id)
                DBManager.update_config('venezuela_iva', str(venezuela_iva), st.session_state.user_id)
                st.success("✅ Tasas e impuestos actualizados")
                DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó tasas e impuestos")
                st.rerun()
    
    with col2:
        st.markdown("**Costos y Márgenes**")
        
        with st.form("costs_config_form"):
            national_handling = st.number_input(
                "Manejo Nacional (USD)",
                min_value=0.0,
                value=float(config.get('national_handling', {}).get('value', 18)),
                step=0.5,
                help="Costo de manejo nacional en dólares"
            )
            
            profit_factors_str = config.get('profit_factors', {}).get('value', '1.4285,1.35,1.30,1.25,1.20,1.15,1.10')
            profit_factors = st.text_input(
                "Factores de Ganancia",
                value=profit_factors_str,
                help="Separados por comas (ej: 1.4285,1.35,1.30)"
            )
            
            submit_costs = st.form_submit_button("💾 Guardar Costos y Márgenes", use_container_width=True)
            
            if submit_costs:
                DBManager.update_config('national_handling', str(national_handling), st.session_state.user_id)
                DBManager.update_config('profit_factors', profit_factors, st.session_state.user_id)
                st.success("✅ Costos y márgenes actualizados")
                DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó costos y márgenes")
                st.rerun()
    
    st.markdown("---")
    st.markdown("#### Opciones de Garantías")
    
    with st.form("warranties_form"):
        warranties_str = config.get('warranties', {}).get('value', '15 días,30 días,45 días,3 meses,6 meses')
        warranties = st.text_area(
            "Opciones de Garantía (una por línea o separadas por comas)",
            value=warranties_str.replace(',', '\n'),
            height=150,
            help="Cada línea será una opción de garantía disponible"
        )
        
        submit_warranties = st.form_submit_button("💾 Guardar Garantías", use_container_width=True)
        
        if submit_warranties:
            # Convertir a formato de comas
            warranties_clean = ','.join([w.strip() for w in warranties.replace('\n', ',').split(',') if w.strip()])
            DBManager.update_config('warranties', warranties_clean, st.session_state.user_id)
            st.success("✅ Opciones de garantía actualizadas")
            DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó opciones de garantía")
            st.rerun()
    
    st.markdown("---")
    st.markdown("#### Términos y Condiciones")
    
    with st.form("terms_form"):
        terms = st.text_area(
            "Términos y Condiciones de las Cotizaciones",
            value=config.get('terms_conditions', {}).get('value', 'Términos y condiciones estándar'),
            height=200,
            help="Texto que aparecerá en todas las cotizaciones"
        )
        
        submit_terms = st.form_submit_button("💾 Guardar Términos y Condiciones", use_container_width=True)
        
        if submit_terms:
            DBManager.update_config('terms_conditions', terms, st.session_state.user_id)
            st.success("✅ Términos y condiciones actualizados")
            DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó términos y condiciones")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def show_reports_and_stats():
    """Módulo de reportes y estadísticas."""
    
    st.markdown('<div class="admin-section">', unsafe_allow_html=True)
    st.markdown("### 📊 Reportes y Estadísticas")
    
    # Obtener estadísticas
    stats = DBManager.get_quote_stats()
    
    # Tarjetas de estadísticas generales
    st.markdown("#### Estadísticas Generales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{stats['total']}</div>
                <div class="stat-label">Total Cotizaciones</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        draft_count = stats['by_status'].get('draft', 0)
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{draft_count}</div>
                <div class="stat-label">Borradores</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sent_count = stats['by_status'].get('sent', 0)
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{sent_count}</div>
                <div class="stat-label">Enviadas</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        approved_count = stats['by_status'].get('approved', 0)
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{approved_count}</div>
                <div class="stat-label">Aprobadas</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Reportes por período
    st.markdown("#### Reportes por Período")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Fecha Inicio", value=datetime.now() - timedelta(days=30))
    
    with col2:
        end_date = st.date_input("Fecha Fin", value=datetime.now())
    
    if st.button("📈 Generar Reporte", use_container_width=True):
        quotes = DBManager.get_quotes_by_period(start_date.isoformat(), end_date.isoformat())
        
        if not quotes:
            st.info(f"No hay cotizaciones en el período seleccionado ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})")
        else:
            st.success(f"✅ Se encontraron {len(quotes)} cotizaciones en el período")
            
            # Mostrar tabla de cotizaciones
            st.markdown("##### Detalle de Cotizaciones")
            
            for quote in quotes:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 2])
                    
                    with col1:
                        st.markdown(f"**{quote['quote_number']}**")
                    
                    with col2:
                        st.text(f"Cliente: {quote['client_name']}")
                    
                    with col3:
                        status_emoji = {
                            'draft': '📝',
                            'sent': '📤',
                            'approved': '✅',
                            'rejected': '❌'
                        }
                        st.text(f"{status_emoji.get(quote['status'], '❓')} {quote['status']}")
                    
                    with col4:
                        created = datetime.fromisoformat(quote['created_at'])
                        st.text(f"Analista: {quote['full_name']}")
                        st.text(f"Fecha: {created.strftime('%d/%m/%Y')}")
                    
                    st.markdown("---")
    
    st.markdown("---")
    
    # Productividad por analista
    st.markdown("#### Productividad por Analista")
    
    if stats['by_analyst']:
        for analyst_name, count in stats['by_analyst'].items():
            st.markdown(f"**{analyst_name}**: {count} cotizaciones")
    else:
        st.info("No hay datos de productividad disponibles")
    
    st.markdown("---")
    
    # Actividad reciente
    st.markdown("#### Actividad Reciente del Sistema")
    
    activities = DBManager.get_recent_activities(20)
    
    if activities:
        for activity in activities:
            timestamp = datetime.fromisoformat(activity['timestamp'])
            st.text(f"[{timestamp.strftime('%d/%m/%Y %H:%M')}] {activity['full_name']}: {activity['action']}")
            if activity['details']:
                st.caption(f"   └─ {activity['details']}")
    else:
        st.info("No hay actividad reciente")
    
    st.markdown('</div>', unsafe_allow_html=True)
