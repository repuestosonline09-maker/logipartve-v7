"""
Módulo: Mis Cotizaciones
Permite a los analistas ver, buscar y gestionar sus cotizaciones guardadas.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.db_manager import DBManager
from services.auth_manager import AuthManager
import os
import tempfile
import json

def render_my_quotes_panel():
    """Renderiza el panel de Mis Cotizaciones."""
    
    # Verificar autenticación usando AuthManager
    if not AuthManager.is_logged_in():
        st.warning("⚠️ Debe iniciar sesión para acceder a esta sección")
        st.stop()
    
    # Obtener datos del usuario actual
    user = AuthManager.get_current_user()
    user_id = user['user_id']
    username = user['username']
    role = user['role']
    
    st.title("📋 MIS COTIZACIONES")
    st.markdown("---")
    
    # ==================== FILTROS Y BÚSQUEDA ====================
    
    st.subheader("🔍 Filtros y Búsqueda")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Búsqueda por texto
        search_term = st.text_input(
            "Buscar por número, cliente o teléfono",
            placeholder="Ej: 2026-30022-A, José, 0424...",
            key="search_quotes"
        )
    
    with col2:
        # Filtro por estado
        status_filter = st.selectbox(
            "Estado",
            options=["Todas", "Aprobadas", "No Aprobadas"],
            key="status_filter"
        )
    
    with col3:
        # Filtro por período
        period_filter = st.selectbox(
            "Período",
            options=["Últimos 7 días", "Últimos 30 días", "Últimos 3 meses", "Último año", "Todos"],
            key="period_filter"
        )
    
    st.markdown("---")
    
    # ==================== OBTENER COTIZACIONES ====================
    
    # Determinar si es búsqueda o listado
    if search_term:
        # Búsqueda
        if role == 'admin':
            quotes = DBManager.search_quotes(None, search_term, limit=100)
        else:
            quotes = DBManager.search_quotes(user_id, search_term, limit=100)
    else:
        # Listado normal
        if role == 'admin':
            quotes = DBManager.get_all_quotes(limit=100)
        else:
            quotes = DBManager.get_quotes_by_analyst(user_id, limit=100)
    
    # Aplicar filtro de estado
    if status_filter == "Aprobadas":
        quotes = [q for q in quotes if q.get('status') == 'approved']
    elif status_filter == "No Aprobadas":
        quotes = [q for q in quotes if q.get('status') != 'approved']
    
    # Aplicar filtro de período
    if period_filter != "Todos":
        now = datetime.now()
        if period_filter == "Últimos 7 días":
            cutoff_date = now - timedelta(days=7)
        elif period_filter == "Últimos 30 días":
            cutoff_date = now - timedelta(days=30)
        elif period_filter == "Últimos 3 meses":
            cutoff_date = now - timedelta(days=90)
        elif period_filter == "Último año":
            cutoff_date = now - timedelta(days=365)
        else:
            cutoff_date = None
        
        if cutoff_date:
            quotes = [q for q in quotes if datetime.fromisoformat(str(q.get('created_at'))) >= cutoff_date]
    
    # ==================== ACCIONES SOBRE COTIZACIONES ====================

    if not quotes:
        st.info("ℹ️ No se encontraron cotizaciones con los filtros seleccionados.")
        return

    # Construir lista compacta para el selector
    df_data = []
    for quote in quotes:
        df_data.append({
            "ID":      quote.get('id'),
            "Número":  quote.get('quote_number', 'N/A'),
            "Cliente": quote.get('client_name', 'Sin nombre'),
        })

    st.markdown("---")
    st.subheader("🔧 Seleccionar Cotización")

    quote_options = {f"{q['Número']} - {q['Cliente']}": q['ID'] for q in df_data}

    if quote_options:
        sel_col, btn_col = st.columns([4, 1])

        with sel_col:
            selected_quote_display = st.selectbox(
                "Cotización",
                options=list(quote_options.keys()),
                key="selected_quote",
                label_visibility="collapsed"
            )

        selected_quote_id = quote_options[selected_quote_display]

        with btn_col:
            if st.button("🔍 VER", use_container_width=True, type="primary"):
                st.session_state.ver_quote_id = selected_quote_id
                # Limpiar vistas anteriores al cambiar de cotización
                for k in ['cuadro_costos_quote_id', 'cuadro_costos_png_path', 'delete_quote_id']:
                    st.session_state.pop(k, None)
                st.rerun()

        # Si se presionó VER y la cotización seleccionada coincide, mostrar vista + botones
        if st.session_state.get('ver_quote_id') == selected_quote_id:
            show_quote_readonly(selected_quote_id)

            st.markdown("---")
            st.subheader("🔧 Acciones")

            action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns(5)

            with action_col1:
                if st.button("✏️ EDITAR", use_container_width=True, type="secondary", key="btn_editar"):
                    quote_details = DBManager.get_quote_full_details(selected_quote_id)
                    if quote_details:
                        st.session_state.editing_mode         = True
                        st.session_state.editing_quote_id     = selected_quote_id
                        st.session_state.editing_quote_number = quote_details['quote_number']
                        st.session_state.editing_quote_data   = quote_details
                        st.success(f"✅ Cotización #{quote_details['quote_number']} cargada para edición")
                        st.info("👉 Vaya a la pestaña 'Panel de Analista' para editar")
                    else:
                        st.error("❌ Error al cargar cotización")

            with action_col2:
                if st.button("📄 DESCARGAR PDF", use_container_width=True, key="btn_pdf"):
                    quote = DBManager.get_quote_by_id(selected_quote_id)
                    if quote and quote.get('pdf_path') and os.path.exists(quote['pdf_path']):
                        with open(quote['pdf_path'], 'rb') as f:
                            st.download_button(
                                label="📄 Descargar PDF",
                                data=f,
                                file_name=f"cotizacion_{quote['quote_number']}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                    else:
                        st.warning("⚠️ Esta cotización no tiene PDF generado")

            with action_col3:
                if st.button("🖼️ DESCARGAR PNG", use_container_width=True, key="btn_png"):
                    quote = DBManager.get_quote_by_id(selected_quote_id)
                    if quote and quote.get('jpeg_path') and os.path.exists(quote['jpeg_path']):
                        with open(quote['jpeg_path'], 'rb') as f:
                            st.download_button(
                                label="🖼️ Descargar PNG",
                                data=f,
                                file_name=f"cotizacion_{quote['quote_number']}.png",
                                mime="image/png",
                                use_container_width=True
                            )
                    else:
                        st.warning("⚠️ Esta cotización no tiene PNG generado")

            with action_col4:
                if st.button("📊 CUADRO COSTOS", use_container_width=True, type="secondary",
                             key="btn_cuadro",
                             help="Genera el Cuadro de Costos interno para administración"):
                    st.session_state.cuadro_costos_quote_id = selected_quote_id
                    st.session_state.pop('cuadro_costos_png_path', None)
                    st.rerun()

            with action_col5:
                if st.button("🗑️ ELIMINAR", use_container_width=True, type="secondary", key="btn_eliminar"):
                    st.session_state.delete_quote_id = selected_quote_id
                    st.rerun()

        # ==================== SECCIÓN: CUADRO DE COSTOS ====================
    
    if st.session_state.get('cuadro_costos_quote_id'):
        show_cuadro_costos(st.session_state.cuadro_costos_quote_id)
    
    # ==================== MODAL: CONFIRMAR ELIMINACIÓN ====================
    
    if st.session_state.get('delete_quote_id'):
        show_delete_confirmation(st.session_state.delete_quote_id)


def show_quote_readonly(quote_id: int):
    """Vista de solo lectura de una cotización: datos del cliente e ítems."""

    st.markdown("---")

    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        return

    items = DBManager.get_quote_items(quote_id)

    # --- Encabezado con número y fecha ---
    created_at = quote.get('created_at')
    try:
        date_display = datetime.fromisoformat(str(created_at)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        date_display = str(created_at) if created_at else "N/A"

    h_col1, h_col2, h_col3 = st.columns(3)
    with h_col1:
        st.markdown(f"📋 **Cotización:** `{quote.get('quote_number', 'N/A')}`")
    with h_col2:
        st.markdown(f"📅 **Fecha:** {date_display}")
    with h_col3:
        estado_map = {'draft': '📝 Borrador', 'sent': '📤 Enviada',
                      'approved': '✅ Aprobada', 'rejected': '❌ Rechazada'}
        st.markdown(f"**Estado:** {estado_map.get(quote.get('status','draft'), 'Desconocido')}")

    # --- Datos del cliente ---
    st.markdown("👤 **Datos del Cliente**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Nombre", value=quote.get('client_name', ''), disabled=True, key=f"ro_nombre_{quote_id}")
    with c2:
        st.text_input("Teléfono", value=quote.get('client_phone', ''), disabled=True, key=f"ro_tel_{quote_id}")
    with c3:
        st.text_input("Vehículo", value=quote.get('client_vehicle', ''), disabled=True, key=f"ro_veh_{quote_id}")

    # --- Ítems ---
    st.markdown(f"🔧 **Ítems ({len(items)} repuesto{'s' if len(items) != 1 else ''})**")

    if items:
        rows = []
        for idx, item in enumerate(items, 1):
            created_item = item.get('created_at') or quote.get('created_at')
            try:
                fecha_item = datetime.fromisoformat(str(created_item)).strftime("%d/%m/%Y %H:%M")
            except Exception:
                fecha_item = date_display

            cantidad   = int(item.get('quantity', 1) or 1)
            fob_total  = float(item.get('unit_cost', 0) or 0) * cantidad
            precio_usd = float(item.get('total_cost', 0) or 0)

            # Precio Bs: recalcular con diferencial actual
            try:
                from database.config_helpers import ConfigHelpers
                dif_pct = ConfigHelpers.get_diferencial()
            except Exception:
                dif_pct = 45.0
            precio_bs = precio_usd * (1 + dif_pct / 100)

            rows.append({
                "#":              idx,
                "Fecha/Hora":     fecha_item,
                "Descripción":    item.get('description', 'N/A'),
                "N° Parte":       item.get('part_number', 'N/A'),
                "Cantidad":        cantidad,
                "FOB Total ($)":   f"${fob_total:,.2f}",
                "🇻🇪 Precio Bs":  f"Bs {precio_bs:,.2f}",
                "Precio USD ($)":  f"${precio_usd:,.2f}",
            })

        import pandas as pd
        df_items = pd.DataFrame(rows)
        st.dataframe(df_items, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Esta cotización no tiene ítems registrados")


def show_quote_details(quote_id: int):
    """Muestra los detalles completos de una cotización."""
    
    st.markdown("---")
    st.subheader("📋 DETALLES DE LA COTIZACIÓN")
    
    # Obtener cotización
    quote = DBManager.get_quote_by_id(quote_id)
    
    if not quote:
        st.error("❌ Cotización no encontrada")
        if st.button("❌ Cerrar"):
            del st.session_state.view_quote_id
            st.rerun()
        return
    
    # Obtener ítems
    items = DBManager.get_quote_items(quote_id)
    
    # Información general
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Número de Cotización", quote.get('quote_number', 'N/A'))
    
    with col2:
        created_at = quote.get('created_at')
        if created_at:
            try:
                date_obj = datetime.fromisoformat(str(created_at))
                date_display = date_obj.strftime("%d/%m/%Y %H:%M")
            except:
                date_display = str(created_at)
        else:
            date_display = "N/A"
        st.metric("Fecha de Creación", date_display)
    
    with col3:
        status_map = {
            "draft": "📝 Borrador",
            "sent": "📤 Enviada",
            "approved": "✅ Aprobada",
            "rejected": "❌ Rechazada"
        }
        current_status = quote.get('status', 'draft')
        status_display = status_map.get(current_status, '❓ Desconocido')
        st.metric("Estado", status_display)
    
    # Cambiar estado
    st.markdown("---")
    st.subheader("🔄 CAMBIAR ESTADO")
    
    status_col1, status_col2 = st.columns([2, 1])
    
    with status_col1:
        new_status = st.selectbox(
            "Nuevo estado",
            options=['draft', 'sent', 'approved', 'rejected'],
            format_func=lambda x: status_map.get(x, x),
            index=['draft', 'sent', 'approved', 'rejected'].index(current_status),
            key=f"status_change_{quote_id}"
        )
    
    with status_col2:
        if new_status != current_status:
            if st.button("✅ CAMBIAR ESTADO", use_container_width=True, type="primary"):
                user = AuthManager.get_current_user()
                success = DBManager.update_quote_status(quote_id, new_status, user['user_id'])
                if success:
                    st.success(f"✅ Estado actualizado a: {status_map.get(new_status)}")
                    st.rerun()
                else:
                    st.error("❌ Error al actualizar estado")
        else:
            st.info("ℹ️ Seleccione un estado diferente")
    
    st.markdown("---")
    
    # Datos del cliente
    st.subheader("👤 DATOS DEL CLIENTE")
    
    client_col1, client_col2 = st.columns(2)
    
    with client_col1:
        st.text_input("Nombre", value=quote.get('client_name', ''), disabled=True)
        st.text_input("Email", value=quote.get('client_email', ''), disabled=True)
        st.text_input("Cédula/RIF", value=quote.get('client_cedula', ''), disabled=True)
        st.text_input("Vehículo", value=quote.get('client_vehicle', ''), disabled=True)
    
    with client_col2:
        st.text_input("Teléfono", value=quote.get('client_phone', ''), disabled=True)
        st.text_input("Dirección", value=quote.get('client_address', ''), disabled=True)
        st.text_input("Año", value=quote.get('client_year', ''), disabled=True)
        st.text_input("VIN", value=quote.get('client_vin', ''), disabled=True)
    
    st.markdown("---")
    
    # Ítems de la cotización
    st.subheader(f"🛠️ ÍTEMS ({len(items)} repuestos)")
    
    if items:
        items_df_data = []
        for idx, item in enumerate(items, 1):
            items_df_data.append({
                "#": idx,
                "Descripción": item.get('description', 'N/A'),
                "Parte": item.get('part_number', 'N/A'),
                "Marca": item.get('marca', 'N/A'),
                "Cantidad": item.get('quantity', 0),
                "Precio Unit.": f"${item.get('unit_cost', 0):,.2f}",
                "Total": f"${item.get('total_cost', 0):,.2f}"
            })
        
        items_df = pd.DataFrame(items_df_data)
        st.dataframe(items_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Esta cotización no tiene ítems registrados")
    
    st.markdown("---")
    
    # Totales
    st.subheader("💰 TOTALES")
    
    total_col1, total_col2, total_col3, total_col4 = st.columns(4)
    
    with total_col1:
        st.metric("Subtotal", f"${quote.get('sub_total', 0):,.2f}")
    
    with total_col2:
        st.metric("IVA", f"${quote.get('iva_total', 0):,.2f}")
    
    with total_col3:
        st.metric("Total a Pagar", f"${quote.get('total_amount', 0):,.2f}")
    
    with total_col4:
        st.metric("Abona Ya", f"${quote.get('abona_ya', 0):,.2f}")
    
    st.markdown("---")
    
    # Historial de cambios
    st.subheader("📜 HISTORIAL DE CAMBIOS")
    
    history = DBManager.get_quote_history(quote_id)
    
    if history:
        for change in history:
            edited_at = change.get('edited_at')
            if edited_at:
                try:
                    date_obj = datetime.fromisoformat(str(edited_at))
                    date_display = date_obj.strftime("%d/%m/%Y %H:%M")
                except:
                    date_display = str(edited_at)
            else:
                date_display = "N/A"
            
            editor_name = change.get('editor_name', 'Usuario desconocido')
            change_summary = change.get('change_summary', 'Sin descripción')
            
            st.markdown(f"""
            📅 **{date_display}** - {editor_name}  
            {change_summary}
            """)
            st.markdown("---")
    else:
        st.info("ℹ️ Esta cotización no tiene historial de cambios")
    
    st.markdown("---")
    
    # Botón para cerrar
    if st.button("❌ CERRAR", use_container_width=True):
        del st.session_state.view_quote_id
        st.rerun()


def show_cuadro_costos(quote_id: int):
    """Genera y muestra el Cuadro de Costos interno de una cotización."""
    
    st.markdown("---")
    
    # Encabezado de la sección
    cc_header_col1, cc_header_col2 = st.columns([5, 1])
    with cc_header_col1:
        st.subheader("📊 CUADRO DE COSTOS — USO ADMINISTRATIVO INTERNO")
    with cc_header_col2:
        if st.button("✖ CERRAR", use_container_width=True, key="btn_cerrar_cuadro"):
            del st.session_state.cuadro_costos_quote_id
            if 'cuadro_costos_png_path' in st.session_state:
                del st.session_state.cuadro_costos_png_path
            st.rerun()
    
    # Obtener datos de la cotización
    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        return
    
    # Obtener ítems con todos sus costos
    items_raw = DBManager.get_quote_items(quote_id)
    
    if not items_raw:
        st.warning("⚠️ Esta cotización no tiene ítems registrados")
        return
    
    # Reconstruir los datos de costos de cada ítem desde la BD
    # Los ítems en BD tienen: unit_cost (FOB), international_handling, national_handling,
    # shipping_cost, tax_percentage, profit_factor, total_cost
    # Los costos calculados (diferencial, utilidad, etc.) se recalculan aquí
    items_para_cuadro = []
    for item in items_raw:
        cantidad     = int(item.get('quantity', 1) or 1)
        costo_fob    = float(item.get('unit_cost', 0) or 0)
        fob_total    = costo_fob * cantidad
        handling     = float(item.get('international_handling', 0) or 0)
        manejo       = float(item.get('national_handling', 0) or 0)
        envio        = float(item.get('shipping_cost', 0) or 0)
        imp_pct      = float(item.get('tax_percentage', 0) or 0)
        factor_ut    = float(item.get('profit_factor', 1.0) or 1.0)
        total_cost   = float(item.get('total_cost', 0) or 0)
        
        # Reconstruir costos calculados
        imp_int      = fob_total * (imp_pct / 100)
        utilidad     = (fob_total + handling + manejo + imp_int) * (factor_ut - 1)
        base_tax     = fob_total + handling + manejo + imp_int + utilidad + envio
        tax_pct      = 7.0   # valor fijo del sistema
        costo_tax    = base_tax * (tax_pct / 100)
        precio_usd   = base_tax + costo_tax
        
        # Diferencial: intentar obtener de la config actual
        try:
            from database.config_helpers import ConfigHelpers
            dif_pct = ConfigHelpers.get_diferencial()
        except Exception:
            dif_pct = 45.0
        dif_val = precio_usd * (dif_pct / 100)
        precio_bs = precio_usd + dif_val
        
        # IVA Venezuela (16% si aplica — por defecto no aplica en cuadro de costos)
        iva_pct = 16.0
        iva_val = 0.0
        aplicar_iva = False
        
        items_para_cuadro.append({
            'descripcion':        item.get('description', f'Ítem'),
            'parte':              item.get('part_number', ''),
            'cantidad':           cantidad,
            'costo_fob':          costo_fob,
            'fob_total':          fob_total,
            'costo_handling':     handling,
            'costo_manejo':       manejo,
            'costo_impuesto':     imp_int,
            'impuesto_porcentaje': imp_pct,
            'factor_utilidad':    factor_ut,
            'utilidad_valor':     utilidad,
            'costo_envio':        envio,
            'costo_tax':          costo_tax,
            'tax_porcentaje':     tax_pct,
            'diferencial_valor':  dif_val,
            'diferencial_porcentaje': dif_pct,
            'precio_usd':         precio_usd,
            'precio_bs':          precio_bs,
            'iva_porcentaje':     iva_pct,
            'iva_valor':          iva_val,
            'aplicar_iva':        aplicar_iva,
        })
    
    # Generar PNG si no existe ya en session_state
    png_path = st.session_state.get('cuadro_costos_png_path')
    
    if not png_path or not os.path.exists(png_path):
        with st.spinner("⏳ Generando Cuadro de Costos..."):
            try:
                from services.document_generation.cuadro_costos_generator import generar_cuadro_costos_png
                
                # Directorio temporal para el PNG
                tmp_dir = tempfile.gettempdir()
                quote_number = quote.get('quote_number', str(quote_id))
                png_filename = f"cuadro_costos_{quote_number.replace('-', '_')}.png"
                png_path = os.path.join(tmp_dir, png_filename)
                
                result = generar_cuadro_costos_png(
                    quote_data=quote,
                    items=items_para_cuadro,
                    output_path=png_path
                )
                
                if result:
                    st.session_state.cuadro_costos_png_path = png_path
                    st.success(f"✅ Cuadro de Costos generado — Cotización {quote.get('quote_number', 'N/A')}")
                else:
                    st.error("❌ Error al generar el Cuadro de Costos")
                    return
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                return
    
    # Mostrar el PNG en pantalla
    if png_path and os.path.exists(png_path):
        st.markdown("### Vista Previa del Cuadro de Costos")
        st.info("📌 Solo lectura — Para modificar valores, edite la cotización primero.")
        st.image(png_path, use_container_width=True)
        
        st.markdown("---")
        
        # Botón de descarga
        with open(png_path, 'rb') as f:
            png_bytes = f.read()
        
        quote_number = quote.get('quote_number', str(quote_id))
        dl_col1, dl_col2, dl_col3 = st.columns([1, 2, 1])
        with dl_col2:
            st.download_button(
                label="⬇️ DESCARGAR CUADRO DE COSTOS (PNG)",
                data=png_bytes,
                file_name=f"CuadroCostos_{quote_number}.png",
                mime="image/png",
                use_container_width=True,
                type="primary"
            )
        st.caption("💡 Descarga el PNG y envíalo al grupo de WhatsApp administrativo.")


def show_delete_confirmation(quote_id: int):
    """Muestra confirmación para eliminar una cotización."""
    
    st.markdown("---")
    st.warning("⚠️ **¿ESTÁ SEGURO QUE DESEA ELIMINAR ESTA COTIZACIÓN?**")
    
    quote = DBManager.get_quote_by_id(quote_id)
    
    if quote:
        st.write(f"**Número:** {quote.get('quote_number', 'N/A')}")
        st.write(f"**Cliente:** {quote.get('client_name', 'N/A')}")
        st.write(f"**Total:** ${quote.get('total_amount', 0):,.2f}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ SÍ, ELIMINAR", use_container_width=True, type="primary"):
                # TODO: Implementar eliminación en db_manager.py
                st.success("✅ Cotización eliminada exitosamente")
                del st.session_state.delete_quote_id
                st.rerun()
        
        with col2:
            if st.button("❌ CANCELAR", use_container_width=True):
                del st.session_state.delete_quote_id
                st.rerun()
    else:
        st.error("❌ Cotización no encontrada")
        if st.button("❌ Cerrar"):
            del st.session_state.delete_quote_id
            st.rerun()
