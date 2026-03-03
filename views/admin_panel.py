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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👤 Mi Perfil",
        "👥 Gestión de Usuarios",
        "⚙️ Configuración del Sistema",
        "📊 Reportes y Estadísticas",
        "📧 Configuración de Correos"
    ])
    
    # TAB 1: MI PERFIL
    with tab1:
        show_my_profile()
    
    # TAB 2: GESTIÓN DE USUARIOS
    with tab2:
        show_user_management()
    
    # TAB 3: CONFIGURACIÓN DEL SISTEMA
    with tab3:
        show_system_configuration()
    
    # TAB 4: REPORTES Y ESTADÍSTICAS
    with tab4:
        show_reports_and_stats()

    # TAB 5: CONFIGURACIÓN DE CORREOS (FASE 5)
    with tab5:
        show_email_configuration()


def show_my_profile():
    """Módulo para editar el perfil del usuario actual."""
    
    st.markdown('<div class="admin-section">', unsafe_allow_html=True)
    st.markdown("### 👤 Mi Perfil")
    
    # Obtener datos del usuario actual
    current_user = DBManager.get_user_by_id(st.session_state.user_id)
    
    if not current_user:
        st.error("⚠️ No se pudo cargar la información del usuario")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    st.info("📝 Aquí puedes actualizar tu información personal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Información Personal")
        
        with st.form("my_profile_form"):
            new_full_name = st.text_input(
                "Nombre Completo",
                value=current_user['full_name'],
                help="Tu nombre completo que aparecerá en las cotizaciones"
            )
            
            new_email = st.text_input(
                "Email (opcional)",
                value=current_user.get('email', '') or '',
                help="Tu correo electrónico"
            )
            
            st.markdown("**Información de Cuenta:**")
            st.text(f"Usuario: {current_user['username']}")
            st.text(f"Rol: {current_user['role']}")
            
            submit_profile = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
            
            if submit_profile:
                # Validar que el nombre no esté vacío
                if not new_full_name or new_full_name.strip() == "":
                    st.error("❌ El nombre no puede estar vacío")
                else:
                    # Actualizar el usuario
                    success = DBManager.update_user(
                        st.session_state.user_id,
                        new_full_name.strip(),
                        current_user['role'],  # No cambiar el rol
                        new_email.strip() if new_email else None
                    )
                    
                    if success:
                        st.success("✅ Perfil actualizado exitosamente")
                        # Actualizar el nombre en la sesión
                        st.session_state.full_name = new_full_name.strip()
                        DBManager.log_activity(
                            st.session_state.user_id,
                            "update_profile",
                            f"Actualizó su perfil: {new_full_name}"
                        )
                        st.rerun()
                    else:
                        st.error("❌ Error al actualizar el perfil")
    
    with col2:
        st.markdown("#### Cambiar Contraseña")
        
        with st.form("change_password_form"):
            current_password = st.text_input(
                "Contraseña Actual",
                type="password",
                help="Ingresa tu contraseña actual"
            )
            
            new_password = st.text_input(
                "Nueva Contraseña",
                type="password",
                help="Mínimo 6 caracteres"
            )
            
            confirm_password = st.text_input(
                "Confirmar Nueva Contraseña",
                type="password"
            )
            
            submit_password = st.form_submit_button("🔐 Cambiar Contraseña", use_container_width=True)
            
            if submit_password:
                # Validaciones
                if not current_password:
                    st.error("❌ Debes ingresar tu contraseña actual")
                elif not new_password or len(new_password) < 6:
                    st.error("❌ La nueva contraseña debe tener al menos 6 caracteres")
                elif new_password != confirm_password:
                    st.error("❌ Las contraseñas no coinciden")
                else:
                    # Verificar contraseña actual
                    if AuthManager.verify_password(current_user['username'], current_password):
                        # Cambiar contraseña
                        success = DBManager.update_password(st.session_state.user_id, new_password)
                        
                        if success:
                            st.success("✅ Contraseña cambiada exitosamente")
                            DBManager.log_activity(
                                st.session_state.user_id,
                                "change_password",
                                "Cambió su contraseña"
                            )
                        else:
                            st.error("❌ Error al cambiar la contraseña")
                    else:
                        st.error("❌ Contraseña actual incorrecta")
    
    st.markdown('</div>', unsafe_allow_html=True)


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
                new_email = st.text_input("Email", placeholder="usuario@ejemplo.com", help="Email para recuperación de contraseña")
            
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
                    success = DBManager.create_user(new_username, new_password, new_full_name, new_role, new_email if new_email else None)
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
                        edit_username = st.text_input(
                            "Nombre de Usuario (para login)",
                            value=selected_user['username'],
                            help="Este es el nombre que usa para iniciar sesión"
                        )
                        edit_full_name = st.text_input("Nombre Completo", value=selected_user['full_name'])
                        edit_email = st.text_input("Email", value=selected_user.get('email', ''), placeholder="usuario@ejemplo.com")
                        edit_role = st.selectbox(
                            "Rol",
                            ["analyst", "admin"],
                            index=0 if selected_user['role'] == "analyst" else 1,
                            format_func=lambda x: "Analista" if x == "analyst" else "Administrador"
                        )
                        
                        submit_edit = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                        
                        if submit_edit:
                            # Validar que el username no esté vacío
                            if not edit_username or edit_username.strip() == "":
                                st.error("❌ El nombre de usuario no puede estar vacío")
                            else:
                                success = DBManager.update_user(
                                    selected_user_id,
                                    edit_full_name,
                                    edit_role,
                                    edit_email if edit_email else None,
                                    edit_username.strip()
                                )
                                if success:
                                    st.success("✅ Usuario actualizado exitosamente")
                                    DBManager.log_activity(
                                        st.session_state.user_id,
                                        "update_user",
                                        f"Actualizó usuario: {edit_username}"
                                    )
                                    st.rerun()
                                else:
                                    st.error("❌ Error al actualizar usuario. El nombre de usuario puede estar en uso.")
                
                with col2:
                    st.markdown("**Cambiar Contraseña**")
                    with st.form("edit_user_change_password_form"):
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
                                # Limpiar TODOS los cachés antes de cambiar contraseña
                                try:
                                    st.cache_data.clear()
                                    st.cache_resource.clear()
                                except:
                                    pass
                                
                                success = DBManager.change_password(selected_user_id, new_password)
                                if success:
                                    DBManager.log_activity(
                                        st.session_state.user_id,
                                        "change_password",
                                        f"Cambió contraseña de usuario: {selected_user['username']}"
                                    )
                                    
                                    # Verificar si el usuario está cambiando su propia contraseña
                                    if selected_user_id == st.session_state.user_id:
                                        # Limpiar TODAS las variables de sesión relacionadas con autenticación
                                        keys_to_delete = []
                                        for key in st.session_state.keys():
                                            if key in ['authenticated', 'user_id', 'username', 'role', 'user_data']:
                                                keys_to_delete.append(key)
                                        
                                        for key in keys_to_delete:
                                            del st.session_state[key]
                                        
                                        # Mostrar mensaje y forzar recarga completa
                                        st.success("✅ Contraseña actualizada exitosamente. Cerrando sesión...")
                                        st.info("🔑 Por favor inicia sesión nuevamente con tu nueva contraseña.")
                                        st.warning("⚠️ Si la nueva contraseña no funciona inmediatamente, espera 30 segundos y vuelve a intentar.")
                                        import time
                                        time.sleep(3)
                                        
                                        # Forzar logout y recarga
                                        from services.auth_manager import AuthManager
                                        AuthManager.logout()
                                        st.rerun()
                                    else:
                                        # Cambio de contraseña de otro usuario
                                        st.success("✅ Contraseña actualizada exitosamente")
                                        st.info(f"🔑 El usuario '{selected_user['username']}' debe cerrar sesión y volver a entrar con la nueva contraseña.")
                                        st.warning("⚠️ Si el usuario tiene problemas para iniciar sesión, debe esperar 30 segundos y volver a intentar.")
                                else:
                                    st.error("❌ Error al cambiar contraseña. Por favor intenta nuevamente.")
                
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
                            # PostgreSQL devuelve datetime, SQLite devuelve string
                            if isinstance(user['last_login'], str):
                                last_login = datetime.fromisoformat(user['last_login'])
                            else:
                                last_login = user['last_login']
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
    config_list = DBManager.get_all_config()
    # Convertir lista a diccionario para fácil acceso
    config = {item['key']: item for item in config_list}
    
    # ==========================================
    # SECCIÓN 1: CONFIGURACIÓN DE COSTOS PARA ANALISTA
    # ==========================================
    st.markdown("#### 💰 Opciones de Costos para el Analista")
    st.info("💡 Estas opciones aparecerán como selectbox en el formulario del analista")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # MANEJO
        st.markdown("**MANEJO ($)**")
        with st.form("manejo_form"):
            manejo_str = config.get('manejo_options', {}).get('value', '0,15,23,25')
            manejo_options = st.text_area(
                "Opciones de Manejo (separadas por coma)",
                value=manejo_str,
                height=100,
                help="Valores en dólares que el analista puede seleccionar. Ej: 0,15,23,25"
            )
            submit_manejo = st.form_submit_button("💾 Guardar", use_container_width=True)
            if submit_manejo:
                DBManager.set_config('manejo_options', manejo_options, "Opciones de MANEJO en dólares", st.session_state.user_id)
                st.success("✅ Opciones de MANEJO actualizadas")
                DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó opciones de MANEJO")
                st.rerun()
        
        # IMPUESTO INTERNACIONAL
        st.markdown("**IMPUESTO INTERNACIONAL (%)**")
        with st.form("impuesto_int_form"):
            impuesto_str = config.get('impuesto_internacional_options', {}).get('value', '0,25,30,35,40,45,50')
            impuesto_options = st.text_input(
                "Opciones de Impuesto Internacional (separadas por coma)",
                value=impuesto_str,
                help="Porcentajes de impuesto internacional (EEUU a países como China, Corea). Ej: 0,25,30,35,40,45,50"
            )
            submit_impuesto = st.form_submit_button("💾 Guardar", use_container_width=True)
            if submit_impuesto:
                DBManager.set_config('impuesto_internacional_options', impuesto_options, "Opciones de Impuesto Internacional %", st.session_state.user_id)
                st.success("✅ Opciones de Impuesto Internacional actualizadas")
                DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó opciones de Impuesto Internacional")
                st.rerun()
    
    with col2:
        # FACTOR DE UTILIDAD
        st.markdown("**FACTOR DE UTILIDAD**")
        with st.form("utilidad_form"):
            utilidad_str = config.get('profit_factors', {}).get('value', '1.4285,1.35,1.30,1.25,1.20,1.15,1.10,0')
            utilidad_options = st.text_input(
                "Factores de Utilidad (separados por coma)",
                value=utilidad_str,
                help="Factores multiplicadores de utilidad. Ej: 1.4285,1.35,1.30,1.25,1.20,1.15,1.10,0"
            )
            submit_utilidad = st.form_submit_button("💾 Guardar", use_container_width=True)
            if submit_utilidad:
                DBManager.set_config('profit_factors', utilidad_options, "Factores de utilidad disponibles", st.session_state.user_id)
                st.success("✅ Factores de Utilidad actualizados")
                DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó factores de utilidad")
                st.rerun()
        
        # TAX (valor único)
        st.markdown("**TAX % (Valor único - NO seleccionable)**")
        with st.form("tax_form"):
            tax_value = config.get('american_tax', {}).get('value', '7')
            tax_percentage = st.number_input(
                "Porcentaje de TAX",
                min_value=0.0,
                max_value=100.0,
                value=float(tax_value),
                step=0.5,
                help="Este valor se aplica automáticamente. El analista NO lo selecciona."
            )
            submit_tax = st.form_submit_button("💾 Guardar", use_container_width=True)
            if submit_tax:
                DBManager.set_config('american_tax', str(tax_percentage), "TAX de empresa americana - Porcentaje", st.session_state.user_id)
                st.success("✅ TAX actualizado")
                DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó TAX")
                st.rerun()
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 2: DIFERENCIAL Y OTROS
    # ==========================================
    st.markdown("#### 📈 Diferencial y Configuración General")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📊 **DIFERENCIAL BCV vs PARALELO** - Este valor cambia diariamente según la diferencia entre la tasa del Banco Central de Venezuela y la tasa paralela. Se aplica automáticamente a todas las cotizaciones cuando el cliente paga en bolívares.")
        with st.form("diferencial_form"):
            exchange_diff = st.number_input(
                "Diferencial de Cambio Diario (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(config.get('exchange_differential', {}).get('value', 45)),
                step=1.0,
                help="Ej: 25, 30, 45. Este porcentaje se suma al precio USD para obtener el precio en Bs."
            )
            submit_diff = st.form_submit_button("💾 Guardar Diferencial", use_container_width=True)
            if submit_diff:
                DBManager.set_config('exchange_differential', str(int(exchange_diff)), "Diferencial BCV vs Paralelo - Porcentaje diario", st.session_state.user_id)
                st.success(f"✅ Diferencial actualizado a {int(exchange_diff)}%")
                DBManager.log_activity(st.session_state.user_id, "update_config", f"Actualizó diferencial a {int(exchange_diff)}%")
                st.rerun()
    
    with col2:
        with st.form("iva_form"):
            venezuela_iva = st.number_input(
                "IVA Venezuela (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(config.get('venezuela_iva', {}).get('value', 16)),
                step=0.1,
                help="Porcentaje de IVA en Venezuela (si aplica)"
            )
            submit_iva = st.form_submit_button("💾 Guardar IVA", use_container_width=True)
            if submit_iva:
                DBManager.set_config('venezuela_iva', str(venezuela_iva), "IVA Venezuela - Porcentaje", st.session_state.user_id)
                st.success("✅ IVA actualizado")
                DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó IVA")
                st.rerun()
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN: CONVERSIÓN DE MONEDA EUR → USD
    # ==========================================
    st.markdown("#### 💱 Conversión de Moneda EUR → USD")
    st.info("🇪🇺 **Factor de Conversión para Repuestos de Europa** - Este factor incluye la comisión bancaria y gastos de paridad. Se utiliza en el convertidor de moneda de la barra lateral.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("eur_usd_factor_form"):
            eur_usd_factor = st.number_input(
                "Factor de Conversión EUR → USD",
                min_value=1.0,
                max_value=2.0,
                value=float(config.get('eur_usd_factor', {}).get('value', 1.23)),
                step=0.01,
                help="Factor multiplicador para convertir EUR a USD. Incluye comisiones bancarias. Ej: 1.23 significa que €100 = $123"
            )
            submit_eur_usd = st.form_submit_button("💾 Guardar Factor EUR → USD", use_container_width=True)
            if submit_eur_usd:
                DBManager.set_config('eur_usd_factor', str(eur_usd_factor), "Factor de conversión EUR a USD con comisiones bancarias", st.session_state.user_id)
                st.success(f"✅ Factor EUR → USD actualizado a {eur_usd_factor}")
                DBManager.log_activity(st.session_state.user_id, "update_config", f"Actualizó factor EUR → USD a {eur_usd_factor}")
                st.rerun()
    
    with col2:
        # Mostrar ejemplo de conversión
        current_factor = float(config.get('eur_usd_factor', {}).get('value', 1.23))
        st.markdown("**Ejemplo de Conversión:**")
        st.markdown(f"- €100 × {current_factor} = **${100 * current_factor:.2f}**")
        st.markdown(f"- €250 × {current_factor} = **${250 * current_factor:.2f}**")
        st.markdown(f"- €500 × {current_factor} = **${500 * current_factor:.2f}**")
    
    st.markdown("---")
    st.markdown("#### Tarifas de Flete")
    
    # Obtener tarifas actuales
    freight_rates = DBManager.get_all_freight_rates()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Miami Aéreo**")
        miami_air_rate = next((r['rate'] for r in freight_rates if r['origin'] == 'Miami' and r['shipping_type'] == 'Aéreo'), 9.0)
        with st.form("miami_air_form"):
            miami_air = st.number_input(
                "Tarifa ($/lb)",
                min_value=0.0,
                value=float(miami_air_rate),
                step=0.1,
                help="Costo por libra para envío aéreo desde Miami"
            )
            submit_miami_air = st.form_submit_button("💾 Guardar", use_container_width=True)
            if submit_miami_air:
                DBManager.update_freight_rate('Miami', 'Aéreo', miami_air, st.session_state.user_id)
                st.success("✅ Tarifa actualizada")
                DBManager.log_activity(st.session_state.user_id, "update_freight_rate", "Actualizó tarifa Miami Aéreo")
                st.rerun()
    
    with col2:
        st.markdown("**Miami Marítimo**")
        miami_sea_rate = next((r['rate'] for r in freight_rates if r['origin'] == 'Miami' and r['shipping_type'] == 'Marítimo'), 40.0)
        with st.form("miami_sea_form"):
            miami_sea = st.number_input(
                "Tarifa ($/ft³)",
                min_value=0.0,
                value=float(miami_sea_rate),
                step=0.5,
                help="Costo por pie cúbico para envío marítimo desde Miami"
            )
            submit_miami_sea = st.form_submit_button("💾 Guardar", use_container_width=True)
            if submit_miami_sea:
                DBManager.update_freight_rate('Miami', 'Marítimo', miami_sea, st.session_state.user_id)
                st.success("✅ Tarifa actualizada")
                DBManager.log_activity(st.session_state.user_id, "update_freight_rate", "Actualizó tarifa Miami Marítimo")
                st.rerun()
    
    with col3:
        st.markdown("**Madrid Aéreo**")
        madrid_air_rate = next((r['rate'] for r in freight_rates if r['origin'] == 'Madrid' and r['shipping_type'] == 'Aéreo'), 25.0)
        with st.form("madrid_air_form"):
            madrid_air = st.number_input(
                "Tarifa ($/kg)",
                min_value=0.0,
                value=float(madrid_air_rate),
                step=0.5,
                help="Costo por kilogramo para envío aéreo desde Madrid"
            )
            submit_madrid_air = st.form_submit_button("💾 Guardar", use_container_width=True)
            if submit_madrid_air:
                DBManager.update_freight_rate('Madrid', 'Aéreo', madrid_air, st.session_state.user_id)
                st.success("✅ Tarifa actualizada")
                DBManager.log_activity(st.session_state.user_id, "update_freight_rate", "Actualizó tarifa Madrid Aéreo")
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
    
    # ==========================================
    # SECCIÓN: LISTAS DESPLEGABLES DEL FORMULARIO
    # ==========================================
    st.markdown("#### 📝 Listas Desplegables del Formulario")
    st.info("💡 Configure las opciones que aparecerán en los selectbox del formulario del analista")
    
    # Países de Origen/Localización
    with st.expander("🌍 Países de Origen / Localización", expanded=False):
        with st.form("paises_form"):
            paises_str = config.get('paises_origen', {}).get('value', 'EEUU,MIAMI,ESPAÑA,MADRID')
            paises_options = st.text_area(
                "Países (separados por coma)",
                value=paises_str,
                height=200,
                help="Lista de países que aparecerán en 'País de Localización' y 'País de Fabricación'. Puede agregar todos los países que necesite."
            )
            submit_paises = st.form_submit_button("💾 Guardar Países", use_container_width=True)
            if submit_paises:
                DBManager.set_config('paises_origen', paises_options, "Países de origen/localización", st.session_state.user_id)
                st.success("✅ Lista de países actualizada")
                DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó lista de países")
                st.rerun()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Tipos de Envío
        with st.expander("🚚 Tipos de Envío", expanded=False):
            with st.form("tipos_envio_form"):
                tipos_str = config.get('tipos_envio', {}).get('value', 'AEREO,MARITIMO,TERRESTRE')
                tipos_options = st.text_input(
                    "Tipos de Envío (separados por coma)",
                    value=tipos_str,
                    help="Ej: AEREO,MARITIMO,TERRESTRE"
                )
                submit_tipos = st.form_submit_button("💾 Guardar", use_container_width=True)
                if submit_tipos:
                    DBManager.set_config('tipos_envio', tipos_options, "Tipos de envío disponibles", st.session_state.user_id)
                    st.success("✅ Tipos de envío actualizados")
                    DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó tipos de envío")
                    st.rerun()
    
    with col2:
        # Tiempos de Entrega
        with st.expander("⏰ Tiempos de Entrega", expanded=False):
            with st.form("tiempos_form"):
                tiempos_str = config.get('tiempos_entrega', {}).get('value', '02 A 05 DIAS,08 A 12 DIAS,12 A 15 DIAS')
                tiempos_options = st.text_input(
                    "Tiempos de Entrega (separados por coma)",
                    value=tiempos_str,
                    help="Ej: 02 A 05 DIAS,08 A 12 DIAS,12 A 15 DIAS"
                )
                submit_tiempos = st.form_submit_button("💾 Guardar", use_container_width=True)
                if submit_tiempos:
                    DBManager.set_config('tiempos_entrega', tiempos_options, "Tiempos de entrega disponibles", st.session_state.user_id)
                    st.success("✅ Tiempos de entrega actualizados")
                    DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó tiempos de entrega")
                    st.rerun()
    
    st.markdown("---")
    st.markdown("#### 📜 Términos y Condiciones")
    
    with st.form("terms_form"):
        terms = st.text_area(
            "Términos y Condiciones de las Cotizaciones",
            value=config.get('terms_conditions', {}).get('value', 'Términos y condiciones estándar'),
            height=200,
            help="Texto que aparecerá en todas las cotizaciones"
        )
        
        submit_terms = st.form_submit_button("💾 Guardar Términos y Condiciones", use_container_width=True)
        
        if submit_terms:
            DBManager.set_config('terms_conditions', terms, "Términos y condiciones de las cotizaciones", st.session_state.user_id)
            st.success("✅ Términos y condiciones actualizados")
            DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó términos y condiciones")
            st.rerun()
    
    # ==========================================
    # SECCIÓN: CONFIGURACIÓN SMTP (RECUPERACIÓN DE CONTRASEÑA)
    # ==========================================
    st.markdown("---")
    st.markdown("#### 📧 Configuración de Email (SMTP)")
    st.info("💡 Configura el servidor SMTP para enviar emails de recuperación de contraseña")
    
    with st.form("smtp_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            smtp_server = st.text_input(
                "Servidor SMTP",
                value=config.get('smtp_server', {}).get('value', ''),
                placeholder="smtp.gmail.com",
                help="Servidor SMTP de tu proveedor de email"
            )
            
            smtp_port = st.number_input(
                "Puerto SMTP",
                min_value=1,
                max_value=65535,
                value=int(config.get('smtp_port', {}).get('value', '587')),
                help="Puerto del servidor SMTP (587 para TLS, 465 para SSL)"
            )
            
            smtp_username = st.text_input(
                "Usuario SMTP",
                value=config.get('smtp_username', {}).get('value', ''),
                placeholder="tu-email@gmail.com",
                help="Usuario para autenticación SMTP"
            )
        
        with col2:
            smtp_password = st.text_input(
                "Contraseña SMTP",
                value=config.get('smtp_password', {}).get('value', ''),
                type="password",
                help="Contraseña o App Password para autenticación SMTP"
            )
            
            smtp_from_email = st.text_input(
                "Email Remitente",
                value=config.get('smtp_from_email', {}).get('value', ''),
                placeholder="noreply@logipartve.com",
                help="Email que aparecerá como remitente"
            )
            
            smtp_from_name = st.text_input(
                "Nombre Remitente",
                value=config.get('smtp_from_name', {}).get('value', 'LogiPartVE'),
                placeholder="LogiPartVE",
                help="Nombre que aparecerá como remitente"
            )
        
        submit_smtp = st.form_submit_button("💾 Guardar Configuración SMTP", use_container_width=True)
        
        if submit_smtp:
            # Validar que los campos obligatorios no estén vacíos
            if not smtp_server or not smtp_username or not smtp_password or not smtp_from_email:
                st.error("❌ Por favor completa todos los campos obligatorios (Servidor, Usuario, Contraseña, Email Remitente)")
            else:
                # Guardar todas las configuraciones SMTP
                try:
                    success_count = 0
                    errors = []
                    
                    if DBManager.set_config('smtp_server', smtp_server, "Servidor SMTP", st.session_state.user_id):
                        success_count += 1
                    else:
                        errors.append("smtp_server")
                    
                    if DBManager.set_config('smtp_port', str(smtp_port), "Puerto SMTP", st.session_state.user_id):
                        success_count += 1
                    else:
                        errors.append("smtp_port")
                    
                    if DBManager.set_config('smtp_username', smtp_username, "Usuario SMTP", st.session_state.user_id):
                        success_count += 1
                    else:
                        errors.append("smtp_username")
                    
                    if DBManager.set_config('smtp_password', smtp_password, "Contraseña SMTP", st.session_state.user_id):
                        success_count += 1
                    else:
                        errors.append("smtp_password")
                    
                    if DBManager.set_config('smtp_from_email', smtp_from_email, "Email remitente", st.session_state.user_id):
                        success_count += 1
                    else:
                        errors.append("smtp_from_email")
                    
                    if DBManager.set_config('smtp_from_name', smtp_from_name, "Nombre remitente", st.session_state.user_id):
                        success_count += 1
                    else:
                        errors.append("smtp_from_name")
                    
                    if success_count == 6:
                        st.success("✅ Configuración SMTP guardada exitosamente (6/6 campos)")
                        DBManager.log_activity(st.session_state.user_id, "update_config", "Actualizó configuración SMTP")
                        st.rerun()
                    else:
                        st.error(f"❌ Error al guardar configuración SMTP. Guardados: {success_count}/6. Fallaron: {', '.join(errors)}")
                        st.warning("⚠️ Verifica los logs del servidor para más detalles")
                except Exception as e:
                    st.error(f"❌ Error inesperado al guardar configuración SMTP: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    # Ayuda para configurar Gmail
    with st.expander("💡 ¿Cómo configurar Gmail?"):
        st.markdown("""
        **Para usar Gmail como servidor SMTP:**
        
        1. **Servidor SMTP**: `smtp.gmail.com`
        2. **Puerto**: `587`
        3. **Usuario**: Tu email de Gmail completo (ej: `tuusuario@gmail.com`)
        4. **Contraseña**: Debes generar una "Contraseña de aplicación" (App Password)
        
        **Pasos para generar App Password en Gmail:**
        1. Ve a tu cuenta de Google: https://myaccount.google.com/
        2. Seguridad → Verificación en 2 pasos (debes activarla primero)
        3. Contraseñas de aplicaciones
        4. Selecciona "Correo" y "Otro (nombre personalizado)"
        5. Escribe "LogiPartVE" y genera
        6. Copia la contraseña de 16 caracteres y pégala aquí
        
        **Otros proveedores populares:**
        - **Outlook/Hotmail**: `smtp-mail.outlook.com` (Puerto 587)
        - **Yahoo**: `smtp.mail.yahoo.com` (Puerto 587)
        - **SendGrid**: `smtp.sendgrid.net` (Puerto 587)
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)


def show_reports_and_stats():
    """Módulo de reportes y estadísticas globales."""
    
    import pandas as pd
    
    st.markdown('<div class="admin-section">', unsafe_allow_html=True)
    st.markdown("### 📊 Estadísticas Globales")
    
    # Filtro de período
    period_col1, period_col2 = st.columns([3, 1])
    
    with period_col1:
        period_global = st.selectbox(
            "Período de estadísticas",
            options=['all', 'year', 'quarter', 'month'],
            format_func=lambda x: {
                'all': 'Todo el tiempo',
                'year': 'Último año',
                'quarter': 'Últimos 3 meses',
                'month': 'Último mes'
            }.get(x, x),
            key="period_global_stats"
        )
    
    # Obtener estadísticas globales
    stats = DBManager.get_global_statistics(period_global)
    
    # Métricas principales
    st.markdown("#### Resumen Global")
    
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    
    with metric_col1:
        st.metric("📊 Total Cotizaciones", stats['total_quotes'])
    
    with metric_col2:
        st.metric("💰 Monto Total", f"${stats['total_amount']:,.2f}")
    
    with metric_col3:
        st.metric("📈 Tasa de Aprobación", f"{stats['approval_rate']}%")
    
    with metric_col4:
        st.metric("👥 Analistas Activos", stats['active_analysts'])
    
    with metric_col5:
        # Promedio por cotización
        avg_amount = stats['total_amount'] / stats['total_quotes'] if stats['total_quotes'] > 0 else 0
        st.metric("💵 Promedio", f"${avg_amount:,.2f}")
    
    st.markdown("---")
    
    # Gráfico de distribución por estado
    st.subheader("📊 Distribución por Estado")
    
    if stats['quotes_by_status']:
        status_map = {
            'draft': '📝 Borrador',
            'sent': '📤 Enviada',
            'approved': '✅ Aprobada',
            'rejected': '❌ Rechazada'
        }
        
        # Preparar datos para gráfico
        status_data = pd.DataFrame([
            {'Estado': status_map.get(status, status), 'Cantidad': count}
            for status, count in stats['quotes_by_status'].items()
        ])
        
        # Gráfico de barras
        st.bar_chart(status_data.set_index('Estado'))
    else:
        st.info("ℹ️ No hay datos para mostrar")
    
    st.markdown("---")
    
    # Ranking de analistas
    st.subheader("🏆 RANKING DE ANALISTAS")
    
    ranking_col1, ranking_col2, ranking_col3 = st.columns(3)
    
    with ranking_col1:
        st.markdown("##### 📊 Por Número de Cotizaciones")
        ranking_count = DBManager.get_analyst_ranking('quote_count', period_global, limit=10)
        
        if ranking_count:
            for idx, analyst in enumerate(ranking_count, 1):
                medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
                st.markdown(f"{medal} **{analyst['analyst_name']}** - {int(analyst['metric_value'])} cotizaciones")
        else:
            st.info("ℹ️ No hay datos")
    
    with ranking_col2:
        st.markdown("##### 💰 Por Monto Total")
        ranking_amount = DBManager.get_analyst_ranking('total_amount', period_global, limit=10)
        
        if ranking_amount:
            for idx, analyst in enumerate(ranking_amount, 1):
                medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
                st.markdown(f"{medal} **{analyst['analyst_name']}** - ${analyst['metric_value']:,.2f}")
        else:
            st.info("ℹ️ No hay datos")
    
    with ranking_col3:
        st.markdown("##### 📈 Por Tasa de Aprobación")
        ranking_approval = DBManager.get_analyst_ranking('approval_rate', period_global, limit=10)
        
        if ranking_approval:
            for idx, analyst in enumerate(ranking_approval, 1):
                medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else f"{idx}."))
                st.markdown(f"{medal} **{analyst['analyst_name']}** - {analyst['metric_value']:.1f}%")
        else:
            st.info("ℹ️ No hay datos")
    
    st.markdown("---")
    
    # Reportes por período (simplificado)
    st.subheader("📅 Reportes por Período")
    
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
                        # PostgreSQL devuelve datetime, SQLite devuelve string
                        if isinstance(quote['created_at'], str):
                            created = datetime.fromisoformat(quote['created_at'])
                        else:
                            created = quote['created_at']
                        st.text(f"Analista: {quote['full_name']}")
                        st.text(f"Fecha: {created.strftime('%d/%m/%Y')}")
                    
                    st.markdown("---")
    
    st.markdown("---")
    
    # Actividad reciente
    st.markdown("#### Actividad Reciente del Sistema")
    
    activities = DBManager.get_recent_activities(20)
    
    if activities:
        for activity in activities:
            # PostgreSQL devuelve datetime, SQLite devuelve string
            if isinstance(activity['timestamp'], str):
                timestamp = datetime.fromisoformat(activity['timestamp'])
            else:
                timestamp = activity['timestamp']
            st.text(f"[{timestamp.strftime('%d/%m/%Y %H:%M')}] {activity['full_name']}: {activity['action']}")
            if activity['details']:
                st.caption(f"   └─ {activity['details']}")
    else:
        st.info("No hay actividad reciente")
    
    st.markdown('</div>', unsafe_allow_html=True)


# ==================== CONFIGURACIÓN DE CORREOS (FASE 5) ====================

def show_email_configuration():
    """Módulo de configuración de correos para el envío de Órdenes Aprobadas."""

    st.markdown('<div class="admin-section">', unsafe_allow_html=True)
    st.markdown("### 📧 Configuración de Correos — Órdenes Aprobadas")
    st.markdown(
        "Configura los destinatarios y los textos del correo que se envía "
        "cuando un analista aprueba una orden. Los datos de la cotización "
        "(ítems, cliente, links) se generan automáticamente y no son editables aquí."
    )
    st.markdown("---")

    # Cargar configuración actual
    cfg = DBManager.get_all_email_config()

    # ── SECCIÓN 1: Destinatarios ──────────────────────────────────────────
    st.markdown("#### 📬 Destinatarios")

    col_to, col_reply = st.columns(2)
    with col_to:
        to_email = st.text_input(
            "Para (To) — Destinatario principal",
            value=cfg.get('to_email', ''),
            key="ecfg_to_email",
            help="Correo del líder de administración (Luciano)"
        )
    with col_reply:
        reply_to = st.text_input(
            "Reply-To — Las respuestas llegan a",
            value=cfg.get('reply_to', ''),
            key="ecfg_reply_to",
            help="Cuando alguien responde el correo, la respuesta llega aquí"
        )

    cc_emails = st.text_area(
        "Con Copia (CC) — separar correos con coma",
        value=cfg.get('cc_emails', ''),
        key="ecfg_cc_emails",
        height=90,
        help="Todos los correos en copia, separados por coma. Ej: a@gmail.com,b@gmail.com"
    )

    st.markdown("---")

    # ── SECCIÓN 2: Remitente ──────────────────────────────────────────────
    st.markdown("#### ✉️ Remitente")

    col_fn, col_fe = st.columns(2)
    with col_fn:
        from_name = st.text_input(
            "Nombre del remitente",
            value=cfg.get('from_name', 'Ordenes LogiPartVE'),
            key="ecfg_from_name",
            help="Nombre que verán los destinatarios en el campo 'De:'"
        )
    with col_fe:
        from_email = st.text_input(
            "Correo remitente (verificado en Resend)",
            value=cfg.get('from_email', 'ordenes@logipartve.com'),
            key="ecfg_from_email",
            help="Debe estar verificado en el panel de Resend"
        )

    st.markdown("---")

    # ── SECCIÓN 3: Textos editables del cuerpo ───────────────────────────
    st.markdown("#### 📝 Textos del Correo")
    st.caption(
        "Solo puedes editar los textos fijos. Los datos de la cotización "
        "(número, cliente, ítems, links, totales) se insertan automáticamente."
    )

    texto_apertura = st.text_area(
        "Texto de apertura (saludo e introducción)",
        value=cfg.get(
            'texto_apertura',
            'Hola, por favor dar proceso a esta orden aprobada. '
            'A continuación te envio los datos para comprar:'
        ),
        key="ecfg_apertura",
        height=100,
        help="Aparece al inicio del correo, antes de los datos de la cotización"
    )

    texto_cierre = st.text_area(
        "Texto de cierre (despedida)",
        value=cfg.get('texto_cierre', 'Sin más por el momento, queda de ustedes'),
        key="ecfg_cierre",
        height=80,
        help="Aparece al final del correo, antes de la firma del analista"
    )

    cargo_analista = st.text_input(
        "Cargo del analista (aparece en la firma)",
        value=cfg.get('cargo_analista', 'Analista de Ventas'),
        key="ecfg_cargo",
        help="Ej: Analista de Ventas, Ejecutivo de Cotizaciones"
    )

    st.markdown("---")

    # ── BOTÓN GUARDAR ─────────────────────────────────────────────────────
    if st.button("💾 GUARDAR CONFIGURACIÓN DE CORREOS", type="primary",
                 use_container_width=True, key="ecfg_save_btn"):
        errores = []
        if not to_email.strip():
            errores.append("El campo 'Para (To)' no puede estar vacío.")
        if not from_email.strip():
            errores.append("El campo 'Correo remitente' no puede estar vacío.")
        if not reply_to.strip():
            errores.append("El campo 'Reply-To' no puede estar vacío.")

        if errores:
            for e in errores:
                st.error(f"❌ {e}")
        else:
            cambios = {
                'to_email':       to_email.strip(),
                'cc_emails':      cc_emails.strip(),
                'reply_to':       reply_to.strip(),
                'from_name':      from_name.strip(),
                'from_email':     from_email.strip(),
                'texto_apertura': texto_apertura.strip(),
                'texto_cierre':   texto_cierre.strip(),
                'cargo_analista': cargo_analista.strip(),
            }
            ok = all(DBManager.set_email_config(k, v) for k, v in cambios.items())
            if ok:
                st.success("✅ Configuración de correos guardada correctamente.")
                st.rerun()
            else:
                st.error("❌ Error al guardar. Intenta de nuevo.")

    st.markdown("---")

    # ── VISTA PREVIA DEL ASUNTO ───────────────────────────────────────────
    st.markdown("#### 👁️ Vista Previa del Asunto")
    st.info(
        "📧 **Asunto del correo:** Orden de Compra #2026-XXXXX-A\n\n"
        "El número de cotización se inserta automáticamente al enviar."
    )

    st.markdown('</div>', unsafe_allow_html=True)
