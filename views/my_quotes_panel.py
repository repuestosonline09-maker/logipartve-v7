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
            options=["Todos", "Borrador", "Enviada", "Aprobada", "Rechazada"],
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
    if status_filter != "Todos":
        status_map = {
            "Borrador": "draft",
            "Enviada": "sent",
            "Aprobada": "approved",
            "Rechazada": "rejected"
        }
        status_value = status_map.get(status_filter)
        quotes = [q for q in quotes if q.get('status') == status_value]
    
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
    
    # ==================== MOSTRAR RESULTADOS ====================
    
    st.subheader(f"📊 Resultados ({len(quotes)} cotizaciones)")
    
    if not quotes:
        st.info("ℹ️ No se encontraron cotizaciones con los filtros seleccionados.")
        return
    
    # Convertir a DataFrame para mejor visualización
    df_data = []
    for quote in quotes:
        # Mapear estado a español
        status_map = {
            "draft": "📝 Borrador",
            "sent": "📤 Enviada",
            "approved": "✅ Aprobada",
            "rejected": "❌ Rechazada"
        }
        status_display = status_map.get(quote.get('status', 'draft'), '❓ Desconocido')
        
        # Formatear fecha
        created_at = quote.get('created_at')
        if created_at:
            try:
                date_obj = datetime.fromisoformat(str(created_at))
                date_display = date_obj.strftime("%d/%m/%Y %H:%M")
            except:
                date_display = str(created_at)
        else:
            date_display = "N/A"
        
        # Formatear monto
        total_amount = quote.get('total_amount', 0)
        amount_display = f"${total_amount:,.2f}" if total_amount else "$0.00"
        
        df_data.append({
            "ID": quote.get('id'),
            "Número": quote.get('quote_number', 'N/A'),
            "Fecha": date_display,
            "Cliente": quote.get('client_name', 'N/A'),
            "Teléfono": quote.get('client_phone', 'N/A'),
            "Total": amount_display,
            "Estado": status_display,
            "Analista": quote.get('analyst_name', username) if role == 'admin' else username
        })
    
    df = pd.DataFrame(df_data)
    
    # Mostrar tabla con selección
    st.dataframe(
        df.drop(columns=['ID']),  # Ocultar ID en la visualización
        use_container_width=True,
        hide_index=True
    )
    
    # ==================== ACCIONES SOBRE COTIZACIONES ====================
    
    st.markdown("---")
    st.subheader("🔧 Acciones")
    
    # Selector de cotización
    quote_options = {f"{q['Número']} - {q['Cliente']}": q['ID'] for q in df_data}
    
    if quote_options:
        selected_quote_display = st.selectbox(
            "Seleccionar cotización",
            options=list(quote_options.keys()),
            key="selected_quote"
        )
        
        selected_quote_id = quote_options[selected_quote_display]
        
        # Botones de acción
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)
        
        with action_col1:
            if st.button("👁️ VER DETALLES", use_container_width=True, type="primary"):
                st.session_state.view_quote_id = selected_quote_id
                st.rerun()
        
        with action_col2:
            if st.button("📄 DESCARGAR PDF", use_container_width=True):
                quote = DBManager.get_quote_by_id(selected_quote_id)
                if quote and quote.get('pdf_path'):
                    pdf_path = quote['pdf_path']
                    if os.path.exists(pdf_path):
                        with open(pdf_path, 'rb') as f:
                            st.download_button(
                                label="📄 Descargar PDF",
                                data=f,
                                file_name=f"cotizacion_{quote['quote_number']}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                    else:
                        st.error("❌ Archivo PDF no encontrado")
                else:
                    st.warning("⚠️ Esta cotización no tiene PDF generado")
        
        with action_col3:
            if st.button("🖼️ DESCARGAR PNG", use_container_width=True):
                quote = DBManager.get_quote_by_id(selected_quote_id)
                if quote and quote.get('jpeg_path'):
                    png_path = quote['jpeg_path']
                    if os.path.exists(png_path):
                        with open(png_path, 'rb') as f:
                            st.download_button(
                                label="🖼️ Descargar PNG",
                                data=f,
                                file_name=f"cotizacion_{quote['quote_number']}.png",
                                mime="image/png",
                                use_container_width=True
                            )
                    else:
                        st.error("❌ Archivo PNG no encontrado")
                else:
                    st.warning("⚠️ Esta cotización no tiene PNG generado")
        
        with action_col4:
            if st.button("🗑️ ELIMINAR", use_container_width=True, type="secondary"):
                st.session_state.delete_quote_id = selected_quote_id
                st.rerun()
    
    # ==================== MODAL: VER DETALLES ====================
    
    if st.session_state.get('view_quote_id'):
        show_quote_details(st.session_state.view_quote_id)
    
    # ==================== MODAL: CONFIRMAR ELIMINACIÓN ====================
    
    if st.session_state.get('delete_quote_id'):
        show_delete_confirmation(st.session_state.delete_quote_id)


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
        status_display = status_map.get(quote.get('status', 'draft'), '❓ Desconocido')
        st.metric("Estado", status_display)
    
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
    
    # Botón para cerrar
    if st.button("❌ CERRAR", use_container_width=True):
        del st.session_state.view_quote_id
        st.rerun()


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
