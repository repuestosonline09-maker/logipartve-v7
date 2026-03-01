"""
Módulo: Mis Cotizaciones
Permite a los analistas buscar y gestionar sus cotizaciones guardadas.
Flujo: Búsqueda → Dropdown de coincidencias → VER → Vista de solo lectura + Acciones
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.db_manager import DBManager
from services.auth_manager import AuthManager
import os
import tempfile

def render_my_quotes_panel():
    """Renderiza el panel de Mis Cotizaciones."""

    if not AuthManager.is_logged_in():
        st.warning("⚠️ Debe iniciar sesión para acceder a esta sección")
        st.stop()

    user     = AuthManager.get_current_user()
    user_id  = user['user_id']
    role     = user['role']

    st.title("📋 MIS COTIZACIONES")
    st.markdown("---")

    # ==================== BLOQUE 1: FILTROS Y BÚSQUEDA ====================

    st.subheader("🔍 Filtros y Búsqueda")

    col1, col2, col3 = st.columns(3)

    with col1:
        search_term = st.text_input(
            "Buscar por número, cliente o teléfono",
            placeholder="Ej: 2026-30022-A, José, 0424...",
            key="search_quotes"
        )

    with col2:
        status_filter = st.selectbox(
            "Estado",
            options=["Todas", "Aprobadas", "No Aprobadas"],
            key="status_filter"
        )

    with col3:
        period_filter = st.selectbox(
            "Período",
            options=["Últimos 7 días", "Últimos 30 días", "Últimos 3 meses", "Último año", "Todos"],
            key="period_filter"
        )

    st.markdown("---")

    # ==================== BLOQUE 2: OBTENER Y FILTRAR COTIZACIONES ====================

    if search_term:
        quotes = DBManager.search_quotes(None if role == 'admin' else user_id,
                                         search_term, limit=100)
    else:
        quotes = (DBManager.get_all_quotes(limit=100) if role == 'admin'
                  else DBManager.get_quotes_by_analyst(user_id, limit=100))

    # Filtro de estado
    if status_filter == "Aprobadas":
        quotes = [q for q in quotes if q.get('status') == 'approved']
    elif status_filter == "No Aprobadas":
        quotes = [q for q in quotes if q.get('status') != 'approved']

    # Filtro de período
    period_days = {"Últimos 7 días": 7, "Últimos 30 días": 30,
                   "Últimos 3 meses": 90, "Último año": 365}
    if period_filter in period_days:
        cutoff = datetime.now() - timedelta(days=period_days[period_filter])
        filtered = []
        for q in quotes:
            try:
                if datetime.fromisoformat(str(q.get('created_at'))) >= cutoff:
                    filtered.append(q)
            except Exception:
                filtered.append(q)
        quotes = filtered

    if not quotes:
        st.info("ℹ️ No se encontraron cotizaciones con los filtros seleccionados.")
        return

    # ==================== BLOQUE 3: DROPDOWN DE COINCIDENCIAS + BOTÓN VER ====================

    estado_map = {
        'draft':    '📝 Borrador',
        'sent':     '📤 Enviada',
        'approved': '✅ Aprobada',
        'rejected': '❌ Rechazada'
    }

    # Construir opciones para el dropdown
    # Formato: "2026-30042-A — Carlos García — 0416-6851083"
    def _label(q):
        num  = q.get('quote_number', 'N/A')
        cli  = q.get('client_name', 'Sin nombre')
        tel  = q.get('client_phone', '')
        est  = estado_map.get(q.get('status', 'draft'), '')
        return f"{num}  —  {cli}  —  {tel}  {est}"

    quote_map = {_label(q): q.get('id') for q in quotes}

    sel_col, btn_col = st.columns([5, 1])

    with sel_col:
        selected_label = st.selectbox(
            f"Cotizaciones encontradas ({len(quotes)})",
            options=list(quote_map.keys()),
            key="selected_quote_label"
        )

    selected_id = quote_map.get(selected_label)

    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)   # alinear verticalmente
        ver_activo = st.session_state.get('ver_quote_id') == selected_id

        if ver_activo:
            if st.button("✖ CERRAR", use_container_width=True, key="btn_cerrar"):
                for k in ['ver_quote_id', 'cuadro_costos_quote_id',
                          'cuadro_costos_png_path', 'delete_quote_id']:
                    st.session_state.pop(k, None)
                st.rerun()
        else:
            if st.button("🔍 VER", use_container_width=True, type="primary", key="btn_ver"):
                st.session_state.ver_quote_id = selected_id
                for k in ['cuadro_costos_quote_id', 'cuadro_costos_png_path', 'delete_quote_id']:
                    st.session_state.pop(k, None)
                st.rerun()

    # ==================== BLOQUE 4: VISTA DE SOLO LECTURA ====================

    if st.session_state.get('ver_quote_id') == selected_id:
        show_quote_readonly(selected_id)

        # ==================== BLOQUE 5: ACCIONES ====================

        st.markdown("---")
        st.subheader("🔧 Acciones")

        a1, a2, a3, a4, a5 = st.columns(5)

        with a1:
            if st.button("✏️ EDITAR", use_container_width=True, type="secondary",
                         key="btn_editar"):
                qd = DBManager.get_quote_full_details(selected_id)
                if qd:
                    st.session_state.editing_mode         = True
                    st.session_state.editing_quote_id     = selected_id
                    st.session_state.editing_quote_number = qd['quote_number']
                    st.session_state.editing_quote_data   = qd
                    st.success(f"✅ Cotización #{qd['quote_number']} cargada para edición")
                    st.info("👉 Vaya a la pestaña 'Panel de Analista' para editar")
                else:
                    st.error("❌ Error al cargar cotización")

        with a2:
            if st.button("📄 DESCARGAR PDF", use_container_width=True, key="btn_pdf"):
                q = DBManager.get_quote_by_id(selected_id)
                if q and q.get('pdf_path') and os.path.exists(q['pdf_path']):
                    with open(q['pdf_path'], 'rb') as f:
                        st.download_button(
                            label="📄 Descargar PDF",
                            data=f,
                            file_name=f"cotizacion_{q['quote_number']}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.warning("⚠️ Esta cotización no tiene PDF generado")

        with a3:
            if st.button("🖼️ DESCARGAR PNG", use_container_width=True, key="btn_png"):
                q = DBManager.get_quote_by_id(selected_id)
                if q and q.get('jpeg_path') and os.path.exists(q['jpeg_path']):
                    with open(q['jpeg_path'], 'rb') as f:
                        st.download_button(
                            label="🖼️ Descargar PNG",
                            data=f,
                            file_name=f"cotizacion_{q['quote_number']}.png",
                            mime="image/png",
                            use_container_width=True
                        )
                else:
                    st.warning("⚠️ Esta cotización no tiene PNG generado")

        with a4:
            if st.button("📊 CUADRO COSTOS", use_container_width=True, type="secondary",
                         key="btn_cuadro",
                         help="Genera el Cuadro de Costos interno para administración"):
                st.session_state.cuadro_costos_quote_id = selected_id
                st.session_state.pop('cuadro_costos_png_path', None)
                st.rerun()

        with a5:
            if st.button("🗑️ ELIMINAR", use_container_width=True, type="secondary",
                         key="btn_eliminar"):
                st.session_state.delete_quote_id = selected_id
                st.rerun()

    # ==================== BLOQUE 6: CUADRO DE COSTOS ====================

    if st.session_state.get('cuadro_costos_quote_id'):
        show_cuadro_costos(st.session_state.cuadro_costos_quote_id)

    # ==================== BLOQUE 7: CONFIRMAR ELIMINACIÓN ====================

    if st.session_state.get('delete_quote_id'):
        show_delete_confirmation(st.session_state.delete_quote_id)


# ==================== FUNCIONES AUXILIARES ====================

def show_quote_readonly(quote_id: int):
    """Vista de solo lectura: datos del cliente e ítems."""

    st.markdown("---")

    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        return

    items = DBManager.get_quote_items(quote_id)

    # Encabezado
    created_at = quote.get('created_at')
    try:
        date_display = datetime.fromisoformat(str(created_at)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        date_display = str(created_at) if created_at else "N/A"

    estado_map = {'draft': '📝 Borrador', 'sent': '📤 Enviada',
                  'approved': '✅ Aprobada', 'rejected': '❌ Rechazada'}

    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(f"📋 **Cotización:** `{quote.get('quote_number', 'N/A')}`")
    with h2:
        st.markdown(f"📅 **Fecha:** {date_display}")
    with h3:
        st.markdown(f"**Estado:** {estado_map.get(quote.get('status', 'draft'), 'Desconocido')}")

    # Datos del cliente
    st.markdown("👤 **Datos del Cliente**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Nombre",   value=quote.get('client_name', ''),    disabled=True, key=f"ro_nom_{quote_id}")
    with c2:
        st.text_input("Teléfono", value=quote.get('client_phone', ''),   disabled=True, key=f"ro_tel_{quote_id}")
    with c3:
        st.text_input("Vehículo", value=quote.get('client_vehicle', ''), disabled=True, key=f"ro_veh_{quote_id}")

    # Ítems
    st.markdown(f"🔧 **Ítems ({len(items)} repuesto{'s' if len(items) != 1 else ''})**")

    if items:
        try:
            from database.config_helpers import ConfigHelpers
            dif_pct = ConfigHelpers.get_diferencial()
        except Exception:
            dif_pct = 45.0

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
            precio_bs  = precio_usd * (1 + dif_pct / 100)

            rows.append({
                "#":              idx,
                "Fecha/Hora":     fecha_item,
                "Descripción":    item.get('description', 'N/A'),
                "N° Parte":       item.get('part_number', 'N/A'),
                "Cantidad":       cantidad,
                "FOB Total ($)":  f"${fob_total:,.2f}",
                "🇻🇪 Precio Bs":  f"Bs {precio_bs:,.2f}",
                "Precio USD ($)": f"${precio_usd:,.2f}",
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Esta cotización no tiene ítems registrados")


def show_cuadro_costos(quote_id: int):
    """Genera y muestra el Cuadro de Costos interno."""

    st.markdown("---")

    hdr1, hdr2 = st.columns([5, 1])
    with hdr1:
        st.subheader("📊 CUADRO DE COSTOS — USO ADMINISTRATIVO INTERNO")
    with hdr2:
        if st.button("✖ CERRAR", use_container_width=True, key="btn_cerrar_cuadro"):
            st.session_state.pop('cuadro_costos_quote_id', None)
            st.session_state.pop('cuadro_costos_png_path', None)
            st.rerun()

    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        return

    items_raw = DBManager.get_quote_items(quote_id)
    if not items_raw:
        st.warning("⚠️ Esta cotización no tiene ítems registrados")
        return

    try:
        from database.config_helpers import ConfigHelpers
        dif_pct = ConfigHelpers.get_diferencial()
    except Exception:
        dif_pct = 45.0

    items_para_cuadro = []
    for item in items_raw:
        cantidad   = int(item.get('quantity', 1) or 1)
        costo_fob  = float(item.get('unit_cost', 0) or 0)
        fob_total  = costo_fob * cantidad
        handling   = float(item.get('international_handling', 0) or 0)
        manejo     = float(item.get('national_handling', 0) or 0)
        envio      = float(item.get('shipping_cost', 0) or 0)
        imp_pct    = float(item.get('tax_percentage', 0) or 0)
        factor_ut  = float(item.get('profit_factor', 1.0) or 1.0)

        imp_int    = fob_total * (imp_pct / 100)
        utilidad   = (fob_total + handling + manejo + imp_int) * (factor_ut - 1)
        base_tax   = fob_total + handling + manejo + imp_int + utilidad + envio
        tax_pct    = 7.0
        costo_tax  = base_tax * (tax_pct / 100)
        precio_usd = base_tax + costo_tax
        dif_val    = precio_usd * (dif_pct / 100)
        precio_bs  = precio_usd + dif_val

        items_para_cuadro.append({
            'descripcion':            item.get('description', 'Ítem'),
            'parte':                  item.get('part_number', ''),
            'cantidad':               cantidad,
            'costo_fob':              costo_fob,
            'fob_total':              fob_total,
            'costo_handling':         handling,
            'costo_manejo':           manejo,
            'costo_impuesto':         imp_int,
            'impuesto_porcentaje':    imp_pct,
            'factor_utilidad':        factor_ut,
            'utilidad_valor':         utilidad,
            'costo_envio':            envio,
            'costo_tax':              costo_tax,
            'tax_porcentaje':         tax_pct,
            'diferencial_valor':      dif_val,
            'diferencial_porcentaje': dif_pct,
            'precio_usd':             precio_usd,
            'precio_bs':              precio_bs,
            'iva_porcentaje':         16.0,
            'iva_valor':              0.0,
            'aplicar_iva':            False,
        })

    png_path = st.session_state.get('cuadro_costos_png_path')

    if not png_path or not os.path.exists(png_path):
        with st.spinner("⏳ Generando Cuadro de Costos..."):
            try:
                from services.document_generation.cuadro_costos_generator import generar_cuadro_costos_png
                tmp_dir      = tempfile.gettempdir()
                quote_number = quote.get('quote_number', str(quote_id))
                png_path     = os.path.join(tmp_dir,
                                            f"cuadro_costos_{quote_number.replace('-','_')}.png")
                if generar_cuadro_costos_png(quote_data=quote, items=items_para_cuadro,
                                             output_path=png_path):
                    st.session_state.cuadro_costos_png_path = png_path
                    st.success(f"✅ Cuadro generado — {quote_number}")
                else:
                    st.error("❌ Error al generar el Cuadro de Costos")
                    return
            except Exception as e:
                st.error(f"❌ Error: {e}")
                return

    if png_path and os.path.exists(png_path):
        st.markdown("### Vista Previa del Cuadro de Costos")
        st.info("📌 Solo lectura — Para modificar valores, edite la cotización primero.")
        st.image(png_path, use_container_width=True)
        st.markdown("---")

        with open(png_path, 'rb') as f:
            png_bytes = f.read()

        quote_number = quote.get('quote_number', str(quote_id))
        _, dl_col, _ = st.columns([1, 2, 1])
        with dl_col:
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
    """Confirmación de eliminación de cotización."""

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
                st.success("✅ Cotización eliminada exitosamente")
                st.session_state.pop('delete_quote_id', None)
                st.rerun()
        with col2:
            if st.button("❌ CANCELAR", use_container_width=True):
                st.session_state.pop('delete_quote_id', None)
                st.rerun()
    else:
        st.error("❌ Cotización no encontrada")
        if st.button("❌ Cerrar"):
            st.session_state.pop('delete_quote_id', None)
            st.rerun()
