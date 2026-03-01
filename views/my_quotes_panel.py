"""
Módulo: Mis Cotizaciones
Flujo:
  1. Al entrar: solo se ven los filtros — pantalla limpia
  2. El analista escribe → aparece dropdown con coincidencias
  3. Al seleccionar una cotización del dropdown → aparece botón VER
  4. Al hacer clic en VER → aparece vista de solo lectura + Acciones
  5. Botón CERRAR limpia TODO (incluyendo el buscador) y vuelve al estado inicial
"""

import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime, timedelta
from database.db_manager import DBManager
from services.auth_manager import AuthManager


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
ESTADO_MAP = {
    'draft':    '📝 Borrador',
    'sent':     '📤 Enviada',
    'approved': '✅ Aprobada',
    'rejected': '❌ Rechazada',
}

PERIOD_DAYS = {
    "Últimos 7 días": 7,
    "Últimos 30 días": 30,
    "Últimos 3 meses": 90,
    "Último año": 365,
}

# Opción vacía del dropdown
_PLACEHOLDER = "— Selecciona una cotización —"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def _limpiar_todo():
    """Limpia todos los estados de Mis Cotizaciones incluyendo el buscador."""
    for k in ['mq_ver_id', 'mq_delete_id',
              'cuadro_costos_quote_id', 'cuadro_costos_png_path']:
        st.session_state.pop(k, None)
    # Incrementar el contador de reset para que todos los widgets se recreen
    st.session_state['mq_reset_counter'] = (
        st.session_state.get('mq_reset_counter', 0) + 1
    )


# ─────────────────────────────────────────────────────────────────────────────
# ADAPTADOR: BD → PDF/PNG generator
# ─────────────────────────────────────────────────────────────────────────────
def _adaptar_quote_para_generadores(qd: dict) -> dict:
    """
    Convierte el diccionario devuelto por get_quote_full_details()
    (campos en inglés: description, part_number, quantity…)
    al formato que espera PDFQuoteGenerator y PNGQuoteGenerator
    (campos en español: descripcion, parte, cantidad…).

    También recalcula los totales que el PDF necesita.
    """
    try:
        from database.config_helpers import ConfigHelpers
        dif_pct = ConfigHelpers.get_diferencial()
    except Exception:
        dif_pct = 45.0

    items_adaptados = []
    sub_total    = 0.0
    iva_total    = 0.0
    abona_ya     = 0.0
    total_usd    = 0.0
    total_bs     = 0.0

    for item in qd.get('items', []):
        cantidad   = int(item.get('quantity', 1) or 1)
        costo_fob  = float(item.get('unit_cost', 0) or 0)
        fob_total  = costo_fob * cantidad
        handling   = float(item.get('international_handling', 0) or 0)
        manejo     = float(item.get('national_handling', 0) or 0)
        envio      = float(item.get('shipping_cost', 0) or 0)
        imp_pct    = float(item.get('tax_percentage', 0) or 0)
        factor_ut  = float(item.get('profit_factor', 1.0) or 1.0)

        imp_int   = fob_total * (imp_pct / 100)
        # FÓRMULA CORRECTA: Utilidad = (FOB_Total × Factor) − FOB_Total
        # El factor se aplica solo sobre el costo FOB, igual que en analyst_panel
        utilidad  = (fob_total * factor_ut) - fob_total
        base_tax  = fob_total + handling + manejo + imp_int + utilidad + envio
        tax_pct   = 7.0
        costo_tax = base_tax * (tax_pct / 100)

        # Precio USD final (lo que ya está guardado en total_cost)
        precio_usd = float(item.get('total_cost', 0) or 0)
        if precio_usd == 0:
            precio_usd = base_tax + costo_tax

        dif_val   = precio_usd * (dif_pct / 100)
        precio_bs = precio_usd + dif_val

        # Acumuladores para totales
        sub_total += precio_bs
        abona_ya  += precio_usd
        total_usd += precio_usd
        total_bs  += precio_bs

        items_adaptados.append({
            # Campos que usa el PDF generator
            'descripcion':         item.get('description', 'N/A'),
            'parte':               item.get('part_number', ''),
            'marca':               item.get('marca', ''),
            'garantia':            item.get('garantia', ''),
            'cantidad':            cantidad,
            'envio_tipo':          item.get('envio_tipo', ''),
            'origen':              item.get('origen', ''),
            'fabricacion':         item.get('fabricacion', ''),
            'tiempo_entrega':      item.get('tiempo_entrega', ''),
            'precio_bs':           precio_bs,
            'precio_usd':          precio_usd,
            # Campos internos para cálculos
            'costo_fob':           costo_fob,
            'fob_total':           fob_total,
            'costo_handling':      handling,
            'costo_manejo':        manejo,
            'costo_impuesto':      imp_int,
            'impuesto_porcentaje': imp_pct,
            'factor_utilidad':     factor_ut,
            'utilidad_valor':      utilidad,
            'costo_envio':         envio,
            'costo_tax':           costo_tax,
            'tax_porcentaje':      tax_pct,
            'diferencial_valor':   dif_val,
            'diferencial_porcentaje': dif_pct,
            'iva_porcentaje':      16.0,
            'iva_valor':           0.0,
            'aplicar_iva':         False,
            'costo_unitario':      precio_usd,
            'costo_total':         precio_usd,
            'costo_total_bs':      precio_bs,
        })

    total_a_pagar = sub_total + iva_total
    y_en_entrega  = total_a_pagar - abona_ya

    # Fecha en formato que espera el PDF
    try:
        fecha_str = datetime.fromisoformat(
            str(qd.get('created_at', ''))
        ).strftime('%Y-%m-%d')
    except Exception:
        fecha_str = datetime.now().strftime('%Y-%m-%d')

    # Términos y condiciones
    terminos = (
        qd.get('terms_conditions') or
        qd.get('terminos_condiciones') or
        'Términos y condiciones estándar.'
    )

    return {
        'quote_number':        qd.get('quote_number', 'N/A'),
        'numero_cotizacion':   qd.get('quote_number', 'N/A'),
        'analyst_name':        qd.get('analyst_name', ''),
        'asesor_ventas':       qd.get('analyst_name', ''),
        'fecha':               fecha_str,
        'client': {
            'nombre':    qd.get('client_name', ''),
            'telefono':  qd.get('client_phone', ''),
            'email':     qd.get('client_email', ''),
            'ci_rif':    qd.get('client_cedula', ''),
            'direccion': qd.get('client_address', ''),
            'vehiculo':  qd.get('client_vehicle', ''),
            'año':       qd.get('client_year', ''),
            'vin':       qd.get('client_vin', ''),
            'motor':     '',
        },
        'cliente': {
            'nombre':    qd.get('client_name', ''),
            'telefono':  qd.get('client_phone', ''),
            'email':     qd.get('client_email', ''),
            'ci_rif':    qd.get('client_cedula', ''),
            'direccion': qd.get('client_address', ''),
            'vehiculo':  qd.get('client_vehicle', ''),
            'año':       qd.get('client_year', ''),
            'vin':       qd.get('client_vin', ''),
            'motor':     '',
        },
        'items':               items_adaptados,
        'sub_total':           sub_total,
        'iva_total':           iva_total,
        'total_a_pagar':       total_a_pagar,
        'abona_ya':            abona_ya,
        'y_en_entrega':        y_en_entrega,
        'total_usd':           total_usd,
        'total_bs':            total_bs,
        'terminos_condiciones': terminos,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
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

    # ── BLOQUE 1: FILTROS ─────────────────────────────────────────────────
    st.subheader("🔍 Filtros y Búsqueda")

    reset_key = st.session_state.get('mq_reset_counter', 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input(
            "Buscar por número, cliente o teléfono",
            placeholder="Ej: 2026-30022-A, José, 0424...",
            key=f"mq_search_{reset_key}"
        )
    with col2:
        status_filter = st.selectbox(
            "Estado",
            options=["Todas", "Aprobadas", "No Aprobadas"],
            key=f"mq_status_{reset_key}"
        )
    with col3:
        period_filter = st.selectbox(
            "Período",
            options=["Últimos 7 días", "Últimos 30 días",
                     "Últimos 3 meses", "Último año", "Todos"],
            key=f"mq_period_{reset_key}"
        )

    # Sin texto → pantalla limpia
    if not search_term or not search_term.strip():
        st.info("💡 Escribe el número de orden, nombre del cliente o teléfono para buscar.")
        return

    st.markdown("---")

    # ── BLOQUE 2: OBTENER Y FILTRAR COTIZACIONES ──────────────────────────
    quotes = DBManager.search_quotes(
        None if role == 'admin' else user_id,
        search_term.strip(),
        limit=100
    )

    # Filtro de estado
    if status_filter == "Aprobadas":
        quotes = [q for q in quotes if q.get('status') == 'approved']
    elif status_filter == "No Aprobadas":
        quotes = [q for q in quotes if q.get('status') != 'approved']

    # Filtro de período
    if period_filter in PERIOD_DAYS:
        cutoff   = datetime.now() - timedelta(days=PERIOD_DAYS[period_filter])
        filtered = []
        for q in quotes:
            try:
                if datetime.fromisoformat(str(q.get('created_at', ''))) >= cutoff:
                    filtered.append(q)
            except Exception:
                filtered.append(q)
        quotes = filtered

    if not quotes:
        st.warning("⚠️ No se encontraron cotizaciones con los criterios indicados.")
        return

    # ── BLOQUE 3: DROPDOWN DE COINCIDENCIAS ──────────────────────────────
    def _label(q):
        num = q.get('quote_number', 'N/A')
        cli = q.get('client_name', 'Sin nombre')
        tel = q.get('client_phone', '')
        est = ESTADO_MAP.get(q.get('status', 'draft'), '')
        return f"{num}  —  {cli}  —  {tel}  {est}"

    quote_by_label = {_label(q): q for q in quotes}
    opciones       = [_PLACEHOLDER] + list(quote_by_label.keys())

    sel_col, btn_col = st.columns([5, 1])

    with sel_col:
        selected_label = st.selectbox(
            f"Coincidencias encontradas: {len(quotes)}",
            options=opciones,
            index=0,                          # siempre empieza en el placeholder
            key=f"mq_selected_{reset_key}"
        )

    # ¿Hay una cotización real seleccionada?
    cotizacion_activa = (selected_label and selected_label != _PLACEHOLDER)
    selected_quote    = quote_by_label.get(selected_label) if cotizacion_activa else None
    selected_id       = selected_quote.get('id') if selected_quote else None

    # Si el usuario cambió la selección, limpiar la vista anterior
    ver_id_actual = st.session_state.get('mq_ver_id')
    if ver_id_actual and selected_id and ver_id_actual != selected_id:
        for k in ['mq_ver_id', 'cuadro_costos_quote_id',
                  'cuadro_costos_png_path', 'mq_delete_id']:
            st.session_state.pop(k, None)
        ver_id_actual = None

    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)

        if ver_id_actual:
            # Hay vista activa → mostrar CERRAR
            if st.button("✖ CERRAR", use_container_width=True,
                         key=f"mq_btn_cerrar_{reset_key}", type="secondary"):
                _limpiar_todo()
                st.rerun()
        elif cotizacion_activa and selected_id:
            # Hay selección pero no vista → mostrar VER
            if st.button("🔍 VER", use_container_width=True,
                         key=f"mq_btn_ver_{reset_key}", type="primary"):
                for k in ['cuadro_costos_quote_id',
                          'cuadro_costos_png_path', 'mq_delete_id']:
                    st.session_state.pop(k, None)
                st.session_state.mq_ver_id = selected_id
                st.rerun()

    # ── BLOQUE 4: VISTA DE SOLO LECTURA + ACCIONES ────────────────────────
    if st.session_state.get('mq_ver_id'):
        ver_id = st.session_state['mq_ver_id']
        _show_quote_readonly(ver_id)
        st.markdown("---")
        _show_acciones(ver_id)

    # ── BLOQUE 5: CUADRO DE COSTOS ────────────────────────────────────────
    if st.session_state.get('cuadro_costos_quote_id'):
        _show_cuadro_costos(st.session_state['cuadro_costos_quote_id'])

    # ── BLOQUE 6: CONFIRMAR ELIMINACIÓN ──────────────────────────────────
    if st.session_state.get('mq_delete_id'):
        _show_delete_confirmation(st.session_state['mq_delete_id'])


# ─────────────────────────────────────────────────────────────────────────────
# VISTA DE SOLO LECTURA
# ─────────────────────────────────────────────────────────────────────────────
def _show_quote_readonly(quote_id: int):
    """Vista de solo lectura: encabezado, datos del cliente e ítems."""

    st.markdown("---")

    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        return

    items = DBManager.get_quote_items(quote_id)

    # Fecha
    try:
        date_display = datetime.fromisoformat(
            str(quote.get('created_at', ''))
        ).strftime("%d/%m/%Y %H:%M")
    except Exception:
        date_display = str(quote.get('created_at', 'N/A'))

    # Encabezado
    h1, h2, h3 = st.columns(3)
    with h1:
        st.markdown(f"📋 **Cotización:** `{quote.get('quote_number', 'N/A')}`")
    with h2:
        st.markdown(f"📅 **Fecha:** {date_display}")
    with h3:
        st.markdown(f"**Estado:** {ESTADO_MAP.get(quote.get('status', 'draft'), 'Desconocido')}")

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
            try:
                fecha_item = datetime.fromisoformat(
                    str(item.get('created_at') or quote.get('created_at', ''))
                ).strftime("%d/%m/%Y %H:%M")
            except Exception:
                fecha_item = date_display

            cantidad   = int(item.get('quantity', 1) or 1)
            fob_unit   = float(item.get('unit_cost', 0) or 0)
            fob_total  = fob_unit * cantidad
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


# ─────────────────────────────────────────────────────────────────────────────
# ACCIONES
# ─────────────────────────────────────────────────────────────────────────────
def _show_acciones(quote_id: int):
    """Muestra los 5 botones de acción para la cotización seleccionada."""

    st.subheader("🔧 Acciones")

    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        return

    a1, a2, a3, a4, a5 = st.columns(5)

    # ── EDITAR ────────────────────────────────────────────────────────────
    with a1:
        if st.button("✏️ EDITAR", use_container_width=True,
                     type="secondary", key=f"acc_editar_{quote_id}"):
            qd = DBManager.get_quote_full_details(quote_id)
            if qd:
                st.session_state.editing_mode         = True
                st.session_state.editing_quote_id     = quote_id
                st.session_state.editing_quote_number = qd['quote_number']
                st.session_state.editing_quote_data   = qd
                st.success(f"✅ Cotización #{qd['quote_number']} cargada para edición")
                st.info("👉 Vaya a la pestaña 'Panel de Analista' para editar")
            else:
                st.error("❌ Error al cargar cotización")

    # ── DESCARGAR PDF ─────────────────────────────────────────────────────
    with a2:
        pdf_path = str(quote.get('pdf_path') or '')
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                st.download_button(
                    label="📄 DESCARGAR PDF",
                    data=f,
                    file_name=f"cotizacion_{quote['quote_number']}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"acc_pdf_{quote_id}"
                )
        else:
            if st.button("📄 GENERAR PDF", use_container_width=True,
                         type="secondary", key=f"acc_gen_pdf_{quote_id}"):
                _regenerar_pdf(quote_id)

    # ── DESCARGAR PNG ─────────────────────────────────────────────────────
    with a3:
        png_path = str(quote.get('jpeg_path') or '')
        if png_path and os.path.exists(png_path):
            with open(png_path, 'rb') as f:
                st.download_button(
                    label="🖼️ DESCARGAR PNG",
                    data=f,
                    file_name=f"cotizacion_{quote['quote_number']}.png",
                    mime="image/png",
                    use_container_width=True,
                    key=f"acc_png_{quote_id}"
                )
        else:
            if st.button("🖼️ GENERAR PNG", use_container_width=True,
                         type="secondary", key=f"acc_gen_png_{quote_id}"):
                _regenerar_png(quote_id)

    # ── CUADRO DE COSTOS ──────────────────────────────────────────────────
    with a4:
        if st.button("📊 CUADRO COSTOS", use_container_width=True,
                     type="secondary", key=f"acc_cuadro_{quote_id}"):
            st.session_state.cuadro_costos_quote_id = quote_id
            st.session_state.pop('cuadro_costos_png_path', None)
            st.rerun()

    # ── ELIMINAR ──────────────────────────────────────────────────────────
    with a5:
        if st.button("🗑️ ELIMINAR", use_container_width=True,
                     type="secondary", key=f"acc_elim_{quote_id}"):
            st.session_state.mq_delete_id = quote_id
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# REGENERAR PDF
# ─────────────────────────────────────────────────────────────────────────────
def _regenerar_pdf(quote_id: int):
    """Regenera el PDF de una cotización y actualiza la BD."""
    try:
        from services.document_generation.pdf_generator import PDFQuoteGenerator

        qd = DBManager.get_quote_full_details(quote_id)
        if not qd:
            st.error("❌ No se pudo cargar la cotización")
            return

        # Adaptar campos de la BD al formato del generador
        datos = _adaptar_quote_para_generadores(qd)

        quote_number = qd.get('quote_number', str(quote_id))
        output_dir   = os.path.join(tempfile.gettempdir(), 'logipartve_docs')
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, f"cotizacion_{quote_number}.pdf")

        with st.spinner("⏳ Generando PDF..."):
            result = PDFQuoteGenerator.generate(datos, pdf_path)

        if result and os.path.exists(pdf_path):
            conn   = DBManager.get_connection()
            cursor = conn.cursor()
            if DBManager.USE_POSTGRES:
                cursor.execute("UPDATE quotes SET pdf_path = %s WHERE id = %s",
                               (pdf_path, quote_id))
            else:
                cursor.execute("UPDATE quotes SET pdf_path = ? WHERE id = ?",
                               (pdf_path, quote_id))
            conn.commit()
            cursor.close()
            conn.close()
            st.success("✅ PDF generado. Haz clic en DESCARGAR PDF.")
            st.rerun()
        else:
            st.error("❌ Error al generar el PDF")
    except Exception as e:
        import traceback
        st.error(f"❌ Error: {e}")
        st.code(traceback.format_exc())


# ─────────────────────────────────────────────────────────────────────────────
# REGENERAR PNG
# ─────────────────────────────────────────────────────────────────────────────
def _regenerar_png(quote_id: int):
    """Regenera el PNG de una cotización y actualiza la BD."""
    try:
        from services.document_generation.png_generator import PNGQuoteGenerator

        qd = DBManager.get_quote_full_details(quote_id)
        if not qd:
            st.error("❌ No se pudo cargar la cotización")
            return

        # Adaptar campos de la BD al formato del generador
        datos = _adaptar_quote_para_generadores(qd)

        quote_number = qd.get('quote_number', str(quote_id))
        output_dir   = os.path.join(tempfile.gettempdir(), 'logipartve_docs')
        os.makedirs(output_dir, exist_ok=True)
        png_path = os.path.join(output_dir, f"cotizacion_{quote_number}.png")

        with st.spinner("⏳ Generando PNG..."):
            # PNGQuoteGenerator se usa como INSTANCIA (no método estático)
            gen    = PNGQuoteGenerator()
            result = gen.generate_quote_png_from_data(datos, png_path)

        if result and os.path.exists(png_path):
            conn   = DBManager.get_connection()
            cursor = conn.cursor()
            if DBManager.USE_POSTGRES:
                cursor.execute("UPDATE quotes SET jpeg_path = %s WHERE id = %s",
                               (png_path, quote_id))
            else:
                cursor.execute("UPDATE quotes SET jpeg_path = ? WHERE id = ?",
                               (png_path, quote_id))
            conn.commit()
            cursor.close()
            conn.close()
            st.success("✅ PNG generado. Haz clic en DESCARGAR PNG.")
            st.rerun()
        else:
            st.error("❌ Error al generar el PNG")
    except Exception as e:
        import traceback
        st.error(f"❌ Error: {e}")
        st.code(traceback.format_exc())


# ─────────────────────────────────────────────────────────────────────────────
# CUADRO DE COSTOS
# ─────────────────────────────────────────────────────────────────────────────
def _show_cuadro_costos(quote_id: int):
    """Genera y muestra el Cuadro de Costos interno."""

    st.markdown("---")

    hdr1, hdr2 = st.columns([5, 1])
    with hdr1:
        st.subheader("📊 CUADRO DE COSTOS — USO ADMINISTRATIVO INTERNO")
    with hdr2:
        if st.button("✖ CERRAR", use_container_width=True,
                     key="btn_cerrar_cuadro", type="secondary"):
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

        imp_int    = fob_total * (imp_pct / 100)
        # FÓRMULA CORRECTA: Utilidad = (FOB_Total × Factor) − FOB_Total
        # El factor se aplica solo sobre el costo FOB, igual que en analyst_panel
        utilidad   = (fob_total * factor_ut) - fob_total
        base_tax   = fob_total + handling + manejo + imp_int + utilidad + envio
        tax_pct    = 7.0
        costo_tax  = base_tax * (tax_pct / 100)
        precio_usd = float(item.get('total_cost', 0) or 0)
        if precio_usd == 0:
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

    if not png_path or not os.path.exists(str(png_path)):
        with st.spinner("⏳ Generando Cuadro de Costos..."):
            try:
                from services.document_generation.cuadro_costos_generator import (
                    generar_cuadro_costos_png)
                tmp_dir      = tempfile.gettempdir()
                quote_number = quote.get('quote_number', str(quote_id))
                png_path     = os.path.join(
                    tmp_dir,
                    f"cuadro_costos_{quote_number.replace('-', '_')}.png"
                )
                if generar_cuadro_costos_png(quote_data=quote,
                                             items=items_para_cuadro,
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
                type="primary",
                key=f"dl_cuadro_{quote_id}"
            )
        st.caption("💡 Descarga el PNG y envíalo al grupo de WhatsApp administrativo.")


# ─────────────────────────────────────────────────────────────────────────────
# CONFIRMAR ELIMINACIÓN
# ─────────────────────────────────────────────────────────────────────────────
def _show_delete_confirmation(quote_id: int):
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
                _limpiar_todo()
                st.rerun()
        with col2:
            if st.button("❌ CANCELAR", use_container_width=True,
                         key="mq_cancel_del"):
                st.session_state.pop('mq_delete_id', None)
                st.rerun()
    else:
        st.error("❌ Cotización no encontrada")
        if st.button("Cerrar", key="mq_close_del"):
            st.session_state.pop('mq_delete_id', None)
            st.rerun()
