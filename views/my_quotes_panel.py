"""
Módulo: Mis Cotizaciones
Flujo:
  1. Al entrar: solo se ven los filtros (texto, estado, período)
  2. El analista escribe → aparece dropdown con coincidencias
  3. Al seleccionar una opción → aparece automáticamente la vista de solo lectura + acciones
  4. Botón CERRAR limpia todo y vuelve al estado inicial
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

    user    = AuthManager.get_current_user()
    user_id = user['user_id']
    role    = user['role']

    st.title("📋 MIS COTIZACIONES")
    st.markdown("---")

    # ── BLOQUE 1: FILTROS ──────────────────────────────────────────────────
    st.subheader("🔍 Filtros y Búsqueda")

    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input(
            "Buscar por número, cliente o teléfono",
            placeholder="Ej: 2026-30022-A, José, 0424...",
            key="mq_search"
        )
    with col2:
        status_filter = st.selectbox(
            "Estado",
            options=["Todas", "Aprobadas", "No Aprobadas"],
            key="mq_status"
        )
    with col3:
        period_filter = st.selectbox(
            "Período",
            options=["Últimos 7 días", "Últimos 30 días",
                     "Últimos 3 meses", "Último año", "Todos"],
            key="mq_period"
        )

    # Si no hay texto, no mostramos nada más
    if not search_term or not search_term.strip():
        st.info("💡 Escribe el número de orden, nombre del cliente o teléfono para buscar.")
        return

    st.markdown("---")

    # ── BLOQUE 2: OBTENER Y FILTRAR COTIZACIONES ───────────────────────────
    quotes = (DBManager.search_quotes(None if role == 'admin' else user_id,
                                      search_term.strip(), limit=100))

    # Filtro de estado
    if status_filter == "Aprobadas":
        quotes = [q for q in quotes if q.get('status') == 'approved']
    elif status_filter == "No Aprobadas":
        quotes = [q for q in quotes if q.get('status') != 'approved']

    # Filtro de período
    period_days = {
        "Últimos 7 días": 7, "Últimos 30 días": 30,
        "Últimos 3 meses": 90, "Último año": 365
    }
    if period_filter in period_days:
        cutoff   = datetime.now() - timedelta(days=period_days[period_filter])
        filtered = []
        for q in quotes:
            try:
                if datetime.fromisoformat(str(q.get('created_at'))) >= cutoff:
                    filtered.append(q)
            except Exception:
                filtered.append(q)
        quotes = filtered

    if not quotes:
        st.warning("⚠️ No se encontraron cotizaciones con los criterios indicados.")
        return

    # ── BLOQUE 3: DROPDOWN DE COINCIDENCIAS ───────────────────────────────
    estado_map = {
        'draft':    '📝 Borrador',
        'sent':     '📤 Enviada',
        'approved': '✅ Aprobada',
        'rejected': '❌ Rechazada',
    }

    def _label(q):
        num = q.get('quote_number', 'N/A')
        cli = q.get('client_name', 'Sin nombre')
        tel = q.get('client_phone', '')
        est = estado_map.get(q.get('status', 'draft'), '')
        return f"{num}  —  {cli}  —  {tel}  {est}"

    # Opción vacía como primer elemento para que el analista elija conscientemente
    opciones = ["— Selecciona una cotización —"] + [_label(q) for q in quotes]
    quote_map = {_label(q): q.get('id') for q in quotes}

    sel_col, cerrar_col = st.columns([5, 1])

    with sel_col:
        selected_label = st.selectbox(
            f"Coincidencias encontradas: {len(quotes)}",
            options=opciones,
            key="mq_selected"
        )

    # Botón CERRAR solo cuando hay una vista activa
    with cerrar_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.get('mq_ver_id'):
            if st.button("✖ CERRAR", use_container_width=True, key="mq_btn_cerrar"):
                for k in ['mq_ver_id', 'cuadro_costos_quote_id',
                          'cuadro_costos_png_path', 'mq_delete_id']:
                    st.session_state.pop(k, None)
                st.rerun()

    # Si el analista seleccionó una cotización real, mostrar vista + acciones
    if selected_label and selected_label != "— Selecciona una cotización —":
        selected_id = quote_map.get(selected_label)
        if selected_id:
            # Actualizar el ID en session_state si cambió la selección
            if st.session_state.get('mq_ver_id') != selected_id:
                st.session_state.mq_ver_id = selected_id
                for k in ['cuadro_costos_quote_id', 'cuadro_costos_png_path', 'mq_delete_id']:
                    st.session_state.pop(k, None)

            # ── BLOQUE 4: VISTA DE SOLO LECTURA ───────────────────────────
            show_quote_readonly(selected_id)

            # ── BLOQUE 5: ACCIONES ─────────────────────────────────────────
            st.markdown("---")
            st.subheader("🔧 Acciones")

            a1, a2, a3, a4, a5 = st.columns(5)

            with a1:
                if st.button("✏️ EDITAR", use_container_width=True,
                             type="secondary", key="mq_btn_editar"):
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
                q = DBManager.get_quote_by_id(selected_id)
                if q and q.get('pdf_path') and os.path.exists(str(q['pdf_path'])):
                    with open(q['pdf_path'], 'rb') as f:
                        st.download_button(
                            label="📄 DESCARGAR PDF",
                            data=f,
                            file_name=f"cotizacion_{q['quote_number']}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="mq_dl_pdf"
                        )
                else:
                    st.button("📄 SIN PDF", disabled=True,
                              use_container_width=True, key="mq_no_pdf")

            with a3:
                q = q if 'q' in dir() else DBManager.get_quote_by_id(selected_id)
                if q and q.get('jpeg_path') and os.path.exists(str(q['jpeg_path'])):
                    with open(q['jpeg_path'], 'rb') as f:
                        st.download_button(
                            label="🖼️ DESCARGAR PNG",
                            data=f,
                            file_name=f"cotizacion_{q['quote_number']}.png",
                            mime="image/png",
                            use_container_width=True,
                            key="mq_dl_png"
                        )
                else:
                    st.button("🖼️ SIN PNG", disabled=True,
                              use_container_width=True, key="mq_no_png")

            with a4:
                if st.button("📊 CUADRO COSTOS", use_container_width=True,
                             type="secondary", key="mq_btn_cuadro"):
                    st.session_state.cuadro_costos_quote_id = selected_id
                    st.session_state.pop('cuadro_costos_png_path', None)
                    st.rerun()

            with a5:
                if st.button("🗑️ ELIMINAR", use_container_width=True,
                             type="secondary", key="mq_btn_eliminar"):
                    st.session_state.mq_delete_id = selected_id
                    st.rerun()

    # ── BLOQUE 6: CUADRO DE COSTOS ─────────────────────────────────────────
    if st.session_state.get('cuadro_costos_quote_id'):
        show_cuadro_costos(st.session_state.cuadro_costos_quote_id)

    # ── BLOQUE 7: CONFIRMAR ELIMINACIÓN ───────────────────────────────────
    if st.session_state.get('mq_delete_id'):
        show_delete_confirmation(st.session_state.mq_delete_id)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ══════════════════════════════════════════════════════════════════════════════

def show_quote_readonly(quote_id: int):
    """Vista de solo lectura: encabezado, datos del cliente e ítems."""

    st.markdown("---")

    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        return

    items = DBManager.get_quote_items(quote_id)

    # Fecha
    created_at = quote.get('created_at')
    try:
        date_display = datetime.fromisoformat(str(created_at)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        date_display = str(created_at) if created_at else "N/A"

    estado_map = {
        'draft':    '📝 Borrador', 'sent':     '📤 Enviada',
        'approved': '✅ Aprobada', 'rejected': '❌ Rechazada',
    }

    # Encabezado
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
        st.text_input("Nombre",   value=quote.get('client_name', ''),
                      disabled=True, key=f"ro_nom_{quote_id}")
    with c2:
        st.text_input("Teléfono", value=quote.get('client_phone', ''),
                      disabled=True, key=f"ro_tel_{quote_id}")
    with c3:
        st.text_input("Vehículo", value=quote.get('client_vehicle', ''),
                      disabled=True, key=f"ro_veh_{quote_id}")

    # Ítems
    n_items = len(items)
    st.markdown(f"🔧 **Ítems ({n_items} repuesto{'s' if n_items != 1 else ''})**")

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
        cantidad  = int(item.get('quantity', 1) or 1)
        costo_fob = float(item.get('unit_cost', 0) or 0)
        fob_total = costo_fob * cantidad
        handling  = float(item.get('international_handling', 0) or 0)
        manejo    = float(item.get('national_handling', 0) or 0)
        envio     = float(item.get('shipping_cost', 0) or 0)
        imp_pct   = float(item.get('tax_percentage', 0) or 0)
        factor_ut = float(item.get('profit_factor', 1.0) or 1.0)

        imp_int   = fob_total * (imp_pct / 100)
        utilidad  = (fob_total + handling + manejo + imp_int) * (factor_ut - 1)
        base_tax  = fob_total + handling + manejo + imp_int + utilidad + envio
        tax_pct   = 7.0
        costo_tax = base_tax * (tax_pct / 100)
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
                png_path     = os.path.join(
                    tmp_dir, f"cuadro_costos_{quote_number.replace('-','_')}.png")
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
        st.write(f"**Total:** ${float(quote.get('total_amount', 0) or 0):,.2f}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ SÍ, ELIMINAR", use_container_width=True,
                         type="primary", key="mq_confirm_del"):
                try:
                    DBManager.delete_quote(quote_id)
                    st.success("✅ Cotización eliminada exitosamente")
                except Exception as e:
                    st.error(f"❌ Error al eliminar: {e}")
                for k in ['mq_delete_id', 'mq_ver_id',
                          'cuadro_costos_quote_id', 'cuadro_costos_png_path']:
                    st.session_state.pop(k, None)
                st.rerun()
        with col2:
            if st.button("❌ CANCELAR", use_container_width=True, key="mq_cancel_del"):
                st.session_state.pop('mq_delete_id', None)
                st.rerun()
    else:
        st.error("❌ Cotización no encontrada")
        if st.button("Cerrar", key="mq_close_del"):
            st.session_state.pop('mq_delete_id', None)
            st.rerun()
