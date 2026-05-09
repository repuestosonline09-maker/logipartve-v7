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
    'draft':     '📝 Borrador',
    'sent':      '📤 Enviada',
    'approved':  '✅ Aprobada',
    'rejected':  '❌ Rechazada',
    'cancelled': '⛔ Anulada',
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
        # precio_usd = precio base SIN diferencial, SIN IVA (guardado en total_cost)
        precio_usd = float(item.get('total_cost', 0) or 0)
        if precio_usd == 0:
            precio_usd = base_tax + costo_tax

        # precio_bs = precio CON diferencial, SIN IVA
        # Este es el precio final que ve el cliente en la tabla (igual que columna AH del Excel)
        dif_val   = precio_usd * (dif_pct / 100)
        precio_bs = precio_usd + dif_val

        # Recuperar campos IVA guardados en la BD
        _aplicar_iva  = bool(item.get('aplicar_iva', False))
        _iva_pct      = float(item.get('iva_porcentaje', 16.0) or 16.0)
        # IVA se calcula sobre precio_bs (precio con diferencial, sin IVA)
        # Igual que Excel: P31 = P30 * 16%  donde P30 = suma de AH (con diferencial)
        if _aplicar_iva:
            _iva_val = round(precio_bs * (_iva_pct / 100), 2)
        else:
            _iva_val = 0.0

        # Acumuladores para totales del resumen
        # sub_total = suma de precio_bs (con diferencial, sin IVA) ← igual que P30 del Excel
        sub_total += precio_bs
        if _aplicar_iva:
            iva_total += _iva_val
        # ABONA YA = precio_bs SIN el costo de envío con diferencial
        # Igual que Excel P34: (FOB+Handling+Manejo+Impuesto+Utilidad+Tax) × (1+diferencial)
        # P34 excluye AE (envío) y su diferencial → abona_ya = precio_bs - envio×(1+dif%)
        envio_con_dif = envio * (1 + dif_pct / 100)
        abona_ya  += precio_bs - envio_con_dif
        total_usd += precio_usd
        total_bs  += precio_bs

        items_adaptados.append({
            # Campos que usa el PDF generator
            # precio_bs = precio CON diferencial, SIN IVA ← igual que columna AH/O del Excel
            'descripcion':         item.get('description', 'N/A'),
            'parte':               item.get('part_number', ''),
            'marca':               item.get('marca', ''),
            'garantia':            item.get('garantia', ''),
            'cantidad':            cantidad,
            'envio_tipo':          item.get('envio_tipo', ''),
            'origen':              item.get('origen', ''),
            'fabricacion':         item.get('fabricacion', ''),
            'tiempo_entrega':      item.get('tiempo_entrega', ''),
            'precio_bs':           precio_bs,   # precio con diferencial, sin IVA (columna TOTAL de la tabla)
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
            'iva_porcentaje':      _iva_pct,
            'iva_valor':           _iva_val,
            'aplicar_iva':         _aplicar_iva,
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

    # ── MENSAJE DE ÉXITO PERSISTENTE (se muestra tras eliminar o actualizar) ──────────────
    if st.session_state.get('mq_delete_success_msg'):
        st.success(st.session_state.pop('mq_delete_success_msg'))

    # ── AUTO-APERTURA TRAS EDICIÓN ────────────────────────────────────────────────────
    # Si el analista acaba de guardar una edición, analyst_panel deja los flags
    # mq_auto_open_quote_number y mq_auto_open_quote_id en el session_state.
    # Los consumimos aquí para pre-rellenar el buscador y abrir la orden directamente.
    _auto_qnum = st.session_state.pop('mq_auto_open_quote_number', None)
    _auto_qid  = st.session_state.pop('mq_auto_open_quote_id', None)
    if _auto_qnum and _auto_qid:
        # Pre-cargar el buscador con el número de la orden
        st.session_state[f"mq_search_{st.session_state.get('mq_reset_counter', 0)}"] = _auto_qnum
        # Activar la vista expandida directamente
        st.session_state['mq_ver_id'] = _auto_qid
        st.success(f"✅ Cotización **{_auto_qnum}** actualizada. Aquí están sus acciones:")
    # ───────────────────────────────────────────────────────────────────────────────────

    # ── BLOQUE 1: FILTROS ─────────────────────────────────────────────────
    st.subheader("🔍 Filtros y Búsqueda")

    reset_key = st.session_state.get('mq_reset_counter', 0)

    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input(
            "Buscar por número, cliente, teléfono o email",
            placeholder="Ej: 2026-30022-A, José, 0424..., cliente@gmail.com",
            key=f"mq_search_{reset_key}"
        )
    with col2:
        # El filtro 'Anuladas' solo es visible para el administrador
        _status_options = ["Todas", "Aprobadas", "No Aprobadas"]
        if role == 'admin':
            _status_options.append("Anuladas")
        status_filter = st.selectbox(
            "Estado",
            options=_status_options,
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
    # EXCEPCIÓN: si hay una vista activa por auto-apertura tras edición,
    # no retornar — dejar que el flujo continúe para mostrar la orden.
    if not search_term or not search_term.strip():
        if not st.session_state.get('mq_ver_id'):
            st.info("💡 Escribe el número de orden, nombre del cliente o teléfono para buscar.")
            return

    st.markdown("---")

    # ── BLOQUE 2: OBTENER Y FILTRAR COTIZACIONES ──────────────────────
    # Si no hay search_term pero sí hay mq_ver_id activo (auto-apertura tras edición),
    # saltar la búsqueda y mostrar directamente la vista de la orden.
    if not search_term or not search_term.strip():
        if st.session_state.get('mq_ver_id'):
            ver_id = st.session_state['mq_ver_id']
            _show_quote_readonly(ver_id)
            st.markdown("---")
            if st.button("✖ CERRAR", key="mq_btn_cerrar_auto", type="secondary"):
                _limpiar_todo()
                st.rerun()
            return

    quotes = DBManager.search_quotes(
        None if role == 'admin' else user_id,
        search_term.strip(),
        limit=100
    )

    # Los analistas nunca ven cotizaciones anuladas en sus resultados
    if role != 'admin':
        quotes = [q for q in quotes if q.get('status') != 'cancelled']

    # Filtro de estado
    if status_filter == "Aprobadas":
        quotes = [q for q in quotes if q.get('status') == 'approved']
    elif status_filter == "Anuladas" and role == 'admin':
        quotes = [q for q in quotes if q.get('status') == 'cancelled']
    elif status_filter == "No Aprobadas":
        quotes = [q for q in quotes if q.get('status') not in ('approved', 'cancelled')]

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

        # ── BLOQUE 6: CONFIRMAR ELIMINACIÓN ────────────────────
    if st.session_state.get('mq_delete_id'):
        _show_delete_confirmation(st.session_state['mq_delete_id'])

    # ── BLOQUE 7: FLUJO ORDEN APROBADA (FASE 5) ────────────────────
    if st.session_state.get('mq_aprobar_id'):
        _show_aprobar_orden(st.session_state['mq_aprobar_id'])


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

    # Banner de ANULADA (solo si la cotización está cancelada)
    if quote.get('status') == 'cancelled':
        _motivo = quote.get('cancellation_reason', 'No especificado')
        _nota   = quote.get('cancellation_note', '')
        _fecha_anulacion = ''
        try:
            if quote.get('cancelled_at'):
                from datetime import datetime as _dt
                _fecha_anulacion = _dt.fromisoformat(str(quote['cancelled_at'])).strftime('%d/%m/%Y %H:%M')
        except Exception:
            pass
        _texto_banner = f"⛔ COTIZACIÓN ANULADA &nbsp;&nbsp;|&nbsp;&nbsp; Motivo: {_motivo}"
        if _fecha_anulacion:
            _texto_banner += f" &nbsp;&nbsp;|&nbsp;&nbsp; Fecha: {_fecha_anulacion}"
        if _nota:
            _texto_banner += f"<br><small style='font-weight:400;'>{_nota}</small>"
        st.markdown(
            f"""
            <div style="
                background-color: #8B0000;
                border: 3px solid #5C0000;
                border-radius: 8px;
                padding: 14px 20px;
                margin: 10px 0 16px 0;
                text-align: center;
            ">
                <span style="font-size:1.1rem; font-weight:800; color:#FFFFFF;">
                    {_texto_banner}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

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
    """Muestra los botones de acción para la cotización seleccionada."""

    st.subheader("🔧 Acciones")

    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        return

    estado_actual = quote.get('status', 'draft')
    ya_aprobada   = (estado_actual == 'approved')
    ya_anulada    = (estado_actual == 'cancelled')

    # Si la cotización está anulada, mostrar solo un mensaje informativo y salir
    if ya_anulada:
        st.warning("⛔ Esta cotización está **anulada**. No se pueden realizar acciones sobre ella. Solo el administrador puede reactivarla si fuera necesario.")
        return

    a1, a2, a3, a4, a5, a6, a7 = st.columns(7)

    # ── EDITAR ────────────────────────────────────────────────────────────────────────────────────────
    with a1:
        editar_disabled = ya_aprobada
        if st.button("✏️ EDITAR", use_container_width=True,
                     type="secondary", key=f"acc_editar_{quote_id}",
                     disabled=editar_disabled):
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
        if ya_aprobada:
            st.caption("🔒 Aprobada")

    # ── COPIAR COTIZACIÓN ───────────────────────────────────────────────────────────────────
    with a2:
        if st.button("📋 COPIAR", use_container_width=True,
                     type="secondary", key=f"acc_copiar_{quote_id}"):
            qd_copy = DBManager.get_quote_full_details(quote_id)
            if qd_copy:
                st.session_state.copying_mode          = True
                st.session_state.copying_from_quote_id = quote_id
                st.session_state.copying_from_number   = qd_copy['quote_number']
                st.session_state.copying_quote_data    = qd_copy
                # Limpiar modo edición previo para evitar conflictos
                st.session_state.editing_mode          = False
                st.session_state.pop('editing_quote_id', None)
                st.session_state.pop('editing_quote_number', None)
                st.session_state.pop('editing_quote_data', None)
                st.success(f"✅ Cotización #{qd_copy['quote_number']} lista para copiar")
                st.info("👉 Vaya a 'Panel de Analista' — datos pre-cargados. "
                        "⚠️ Debes modificar al menos un ítem antes de poder guardar.")
            else:
                st.error("❌ Error al cargar la cotización para copiar")

    # ── DESCARGAR PDF ───────────────────────────────────────────────────────────────────────────────
    with a3:
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

    # ── DESCARGAR PNG ───────────────────────────────────────────────────────────────────────────────
    with a4:
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

    # ── CUADRO DE COSTOS ──────────────────────────────────────────────────────────────────────────────────
    with a5:
        if st.button("📊 CUADRO COSTOS", use_container_width=True,
                     type="secondary", key=f"acc_cuadro_{quote_id}"):
            st.session_state.cuadro_costos_quote_id = quote_id
            # SIEMPRE limpiar el PNG en caché para forzar regeneración con datos frescos
            st.session_state.pop('cuadro_costos_png_path', None)
            import tempfile, os as _os2
            _qb = DBManager.get_quote_by_id(quote_id)
            if _qb:
                _qnum = _qb.get('quote_number', str(quote_id))
                _old_png = _os2.path.join(tempfile.gettempdir(),
                    f"cuadro_costos_{_qnum.replace('-', '_')}.png")
                if _os2.path.exists(_old_png):
                    try:
                        _os2.remove(_old_png)
                    except Exception:
                        pass
            st.rerun()

    # ── ORDEN APROBADA (FASE 5) ────────────────────────────────────────────────────────────────────────
    with a6:
        if ya_aprobada:
            st.button("✅ APROBADA", use_container_width=True,
                      type="secondary", key=f"acc_aprobada_dis_{quote_id}",
                      disabled=True)
            st.caption("Ya enviada")
        else:
            if st.button("✅ ORDEN APROBADA", use_container_width=True,
                         type="primary", key=f"acc_aprobada_{quote_id}"):
                st.session_state.mq_aprobar_id = quote_id
                st.rerun()

    # ── ELIMINAR ───────────────────────────────────────────────────────────────────────────────
    with a7:
        if st.button("🗑️ ELIMINAR", use_container_width=True,
                     type="secondary", key=f"acc_elim_{quote_id}",
                     disabled=ya_aprobada):
            st.session_state.mq_delete_id = quote_id
            st.rerun()
        if ya_aprobada:
            st.caption("🔒 Aprobada")

    # ── BOTONES MENSAJES USD y BCV ────────────────────────────────────────────
    st.markdown("---")
    msg_col1, msg_col2 = st.columns(2)
    with msg_col1:
        if st.button("📋 Copiar Mensaje Pago USD", use_container_width=True,
                     type="secondary", key=f"acc_popup_usd_{quote_id}"):
            st.session_state[f'mq_popup_usd_{quote_id}'] = not st.session_state.get(f'mq_popup_usd_{quote_id}', False)
            st.session_state[f'mq_popup_bcv_{quote_id}'] = False
    with msg_col2:
        if st.button("📋 Copiar Mensaje BCV", use_container_width=True,
                     type="secondary", key=f"acc_popup_bcv_{quote_id}"):
            st.session_state[f'mq_popup_bcv_{quote_id}'] = not st.session_state.get(f'mq_popup_bcv_{quote_id}', False)
            st.session_state[f'mq_popup_usd_{quote_id}'] = False

    # ── POP-UP MENSAJE PAGO USD ───────────────────────────────────────────────
    if st.session_state.get(f'mq_popup_usd_{quote_id}', False):
        # Fórmula aprobada:
        # Abono = FOB + Handling + Manejo + Impuesto Internacional + Utilidad
        # Entrega = total_cost - abono  (= Envío + TAX + Diferencial)
        qd_usd = DBManager.get_quote_full_details(quote_id)
        items_usd = qd_usd.get('items', []) if qd_usd else []
        _total_usd = 0.0
        _usd_abono = 0.0
        for _it in items_usd:
            _total_item   = float(_it.get('total_cost', 0) or 0)
            _qty          = float(_it.get('quantity', 1) or 1)
            _unit_cost    = float(_it.get('unit_cost', 0) or 0)
            _handling     = float(_it.get('international_handling', 0) or 0)
            _manejo       = float(_it.get('national_handling', 0) or 0)
            _imp_pct      = float(_it.get('tax_percentage', 0) or 0)
            _factor_util  = float(_it.get('profit_factor', 1.0) or 1.0)

            _fob          = _unit_cost * _qty
            _imp          = _fob * (_imp_pct / 100)
            _util         = _fob * (_factor_util - 1.0)
            # Abono = FOB + Handling + Manejo + Impuesto + Utilidad
            _abono_item   = _fob + _handling + _manejo + _imp + _util

            _total_usd += _total_item
            _usd_abono += max(0.0, _abono_item)
        # Redondeo al múltiplo de 5 hacia arriba (igual que en el formulario de cotización)
        import math as _math_mq
        _total_usd   = _math_mq.ceil(_total_usd / 5) * 5
        _usd_abono   = _math_mq.ceil(_usd_abono / 5) * 5
        _usd_entrega = _total_usd - _usd_abono
        if _usd_entrega < 0:
            _usd_abono   = _total_usd
            _usd_entrega = 0

        with st.container():
            st.markdown("""
            <div style="background: linear-gradient(135deg, #0d1b2a 0%, #1a3a5c 50%, #0a4a7a 100%);
                        border: 2px solid #00b4d8;
                        border-radius: 16px;
                        padding: 24px;
                        margin: 8px 0;">
                <h3 style="color: #00b4d8; text-align: center; margin-bottom: 16px; font-size: 1.1rem;">
                    &#128242; Mensaje listo para WhatsApp / Instagram
                </h3>
            </div>
            """, unsafe_allow_html=True)

            import json as _json_usd_mq
            _mensaje_usd_mq = (
                "\u2728 \u00a1Optimiza tu compra con nosotros! \u2728\n\n"
                "\U0001f4a1 \u00bfSab\u00edas que al realizar tu pago en divisas, puedes acceder a un beneficio especial "
                "en el valor total de tus repuestos? Es nuestra forma de recompensar tu confianza y compromiso. \U0001f64c\n\n"
                "\U0001f511 Esta opci\u00f3n te brinda la oportunidad de asegurar tus piezas con una ventaja adicional, "
                "manteniendo la transparencia y responsabilidad que nos caracterizan.\n\n"
                "\U0001f4cb Si decides aprovechar esta facilidad, tu presupuesto quedar\u00eda en:\n\n"
                "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n"
                f"\U0001f4b5 *Total a Pagar en USD:*  ${_total_usd:.2f}\n"
                f"\u2705 *Monto a Abonar:*         ${_usd_abono:.2f}\n"
                f"\U0001f69a *Y en la Entrega:*        ${_usd_entrega:.2f}\n"
                "\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n\n"
                "\U0001f4b3 *Formas de pago que te ofrecemos:*\n"
                "Cash | Zelle | Binance | Dep\u00f3sito Bancario Cta Divisas \U0001f91d"
            )

            st.text_area(
                "Mensaje generado:",
                value=_mensaje_usd_mq,
                height=320,
                key=f"ta_usd_mq_{quote_id}",
                help="Usa el bot\u00f3n de abajo para copiarlo al portapapeles."
            )

            _texto_usd_mq_js = _json_usd_mq.dumps(_mensaje_usd_mq)
            _copy_js_usd_mq = (
                "<script>"
                f"var _textoUSDMQ = {_texto_usd_mq_js};"
                "function copiarUSDMQ() {"
                "  navigator.clipboard.writeText(_textoUSDMQ).then(function() {"
                "    var btn = document.getElementById('copy_btn_usd_mq');"
                "    btn.innerHTML = '&#9989; &iexcl;Copiado!';"
                "    btn.style.background = '#00b4d8';"
                "    btn.style.color = '#000';"
                "    setTimeout(function() {"
                "      btn.innerHTML = '&#128203; Copiar al Portapapeles';"
                "      btn.style.background = '#0a4a7a';"
                "      btn.style.color = '#fff';"
                "    }, 2500);"
                "  }).catch(function() {"
                "    var btn = document.getElementById('copy_btn_usd_mq');"
                "    btn.innerHTML = '&#9888; No se pudo copiar. Selecciona manualmente (Ctrl+A, Ctrl+C)';"
                "  });"
                "}"
                "</script>"
                "<button id='copy_btn_usd_mq' onclick='copiarUSDMQ()'"
                " style='width:100%;padding:12px;font-size:1rem;font-weight:bold;"
                "background:#0a4a7a;color:white;border:2px solid #00b4d8;"
                "border-radius:8px;cursor:pointer;margin-top:8px;'>"
                "&#128203; Copiar al Portapapeles"
                "</button>"
            )
            import streamlit.components.v1 as _components_mq
            _components_mq.html(_copy_js_usd_mq, height=70)

            _cc1, _cc2, _cc3 = st.columns([1, 2, 1])
            with _cc2:
                if st.button("\u2716 Cerrar", use_container_width=True,
                             key=f"mq_cerrar_usd_{quote_id}"):
                    st.session_state[f'mq_popup_usd_{quote_id}'] = False
                    st.rerun()
    # ── FIN POP-UP MENSAJE PAGO USD ───────────────────────────────────────────

    # ── POP-UP MENSAJE BCV ────────────────────────────────────────────────────
    if st.session_state.get(f'mq_popup_bcv_{quote_id}', False):
        with st.container():
            st.markdown("""
            <div style="background: linear-gradient(135deg, #1a2e1a 0%, #163e16 50%, #0f6030 100%);
                        border: 2px solid #00d4aa;
                        border-radius: 16px;
                        padding: 24px;
                        margin: 8px 0;">
                <h3 style="color: #00d4aa; text-align: center; margin-bottom: 16px; font-size: 1.1rem;">
                    &#128242; Mensaje listo para WhatsApp / Instagram
                </h3>
            </div>
            """, unsafe_allow_html=True)

            import json as _json_bcv_mq
            _mensaje_bcv_mq = (
                "\u2705 En la parte central tiene el detalle de la(s) pieza(s). "
                "\u23f1\ufe0f Tiempo de entrega y garant\u00eda en VZLA.\n\n"
                "\u2705 En la parte inferior derecha puede ver el costo total en sus manos a tasa BCV "
                "\U0001f4b5 y la forma de pago si desea ordenarlo(s).\n\n"
                "Estar\u00e9 atento. \U0001f440\n\n"
                "Muchas Gracias! \U0001f60a\U0001f64c"
            )

            st.text_area(
                "Mensaje generado:",
                value=_mensaje_bcv_mq,
                height=200,
                key=f"ta_bcv_mq_{quote_id}",
                help="Usa el bot\u00f3n de abajo para copiarlo al portapapeles."
            )

            import streamlit.components.v1 as _components_mq
            _texto_bcv_mq_js = _json_bcv_mq.dumps(_mensaje_bcv_mq)
            _copy_js_bcv_mq = (
                "<script>"
                f"var _textoBCVMQ = {_texto_bcv_mq_js};"
                "function copiarBCVMQ() {"
                "  navigator.clipboard.writeText(_textoBCVMQ).then(function() {"
                "    var btn = document.getElementById('copy_btn_bcv_mq');"
                "    btn.innerHTML = '&#9989; &iexcl;Copiado!';"
                "    btn.style.background = '#00d4aa';"
                "    btn.style.color = '#000';"
                "    setTimeout(function() {"
                "      btn.innerHTML = '&#128203; Copiar al Portapapeles';"
                "      btn.style.background = '#0f6030';"
                "      btn.style.color = '#fff';"
                "    }, 2500);"
                "  }).catch(function() {"
                "    var btn = document.getElementById('copy_btn_bcv_mq');"
                "    btn.innerHTML = '&#9888; No se pudo copiar. Selecciona manualmente (Ctrl+A, Ctrl+C)';"
                "  });"
                "}"
                "</script>"
                "<button id='copy_btn_bcv_mq' onclick='copiarBCVMQ()'"
                " style='width:100%;padding:12px;font-size:1rem;font-weight:bold;"
                "background:#0f6030;color:white;border:2px solid #00d4aa;"
                "border-radius:8px;cursor:pointer;margin-top:8px;'>"
                "&#128203; Copiar al Portapapeles"
                "</button>"
            )
            _components_mq.html(_copy_js_bcv_mq, height=70)

            _cb1, _cb2, _cb3 = st.columns([1, 2, 1])
            with _cb2:
                if st.button("\u2716 Cerrar", use_container_width=True,
                             key=f"mq_cerrar_bcv_{quote_id}"):
                    st.session_state[f'mq_popup_bcv_{quote_id}'] = False
                    st.rerun()
    # ── FIN POP-UP MENSAJE BCV ────────────────────────────────────────────────


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
                    resultado = DBManager.delete_quote(quote_id)
                    if resultado:
                        # Guardar mensaje de éxito en session_state para mostrarlo
                        # DESPUÉS del rerun (antes del rerun no se ve)
                        st.session_state['mq_delete_success_msg'] = (
                            f"✅ Cotización #{quote.get('quote_number', quote_id)} "
                            f"eliminada exitosamente."
                        )
                        _limpiar_todo()
                        st.rerun()
                    else:
                        st.error("❌ No se pudo eliminar la cotización. Intente nuevamente.")
                except Exception as e:
                    st.error(f"❌ Error al eliminar: {e}")
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


# ─────────────────────────────────────────────────────────────────────────────
# FLUJO ORDEN APROBADA — FASE 5
# ─────────────────────────────────────────────────────────────────────────────
def _show_aprobar_orden(quote_id: int):
    """
    Flujo completo de aprobación de orden:
    Paso 1 → Confirmación
    Paso 2 → Vista previa del correo
    Paso 3 → Envío + cambio de estado
    """
    import json

    quote = DBManager.get_quote_by_id(quote_id)
    if not quote:
        st.error("❌ Cotización no encontrada")
        st.session_state.pop('mq_aprobar_id', None)
        return

    st.markdown("---")
    paso = st.session_state.get('mq_aprobar_paso', 1)

    # ── PASO 1: VALIDACIÓN DE DATOS OBLIGATORIOS + CONFIRMACIÓN ──────────────
    if paso == 1:
        # ── VALIDAR DATOS OBLIGATORIOS DEL CLIENTE ANTES DE CONTINUAR ──────────
        _campos_obligatorios = [
            ('client_name',    'Nombre del Cliente'),
            ('client_phone',   'Teléfono'),
            ('client_address', 'Dirección'),
            ('client_cedula',  'C.I. / RIF'),
        ]
        _faltantes = [
            label for campo, label in _campos_obligatorios
            if not str(quote.get(campo) or '').strip()
        ]

        if _faltantes:
            # Bloquear: mostrar error con campos faltantes
            _lista_faltantes = ', '.join(f'**{f}**' for f in _faltantes)
            st.error(
                f"❌ **No se puede aprobar la orden.**\n\n"
                f"Faltan los siguientes datos del cliente: {_lista_faltantes}.\n\n"
                f"Por favor, edita la cotización, completa los datos faltantes, "
                f"guarda los cambios y vuelve a intentar aprobar la orden."
            )
            if st.button("← VOLVER", use_container_width=True, key="apr_volver_validacion"):
                st.session_state.pop('mq_aprobar_id', None)
                st.session_state.pop('mq_aprobar_paso', None)
                st.rerun()
        else:
            # Datos completos: mostrar confirmación normal
            st.warning(
                f"⚠️ **¿Desea enviar la Orden de Compra #{quote.get('quote_number')} "
                f"como APROBADA al equipo administrativo?**\n\n"
                "Esta acción enviará un correo con los documentos adjuntos y cambiará "
                "el estado de la cotización a **APROBADA**. Una vez aprobada, "
                "**no podrá editarse ni eliminarse.**"
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("❌ CANCELAR", use_container_width=True,
                             key="apr_cancel_1"):
                    st.session_state.pop('mq_aprobar_id', None)
                    st.session_state.pop('mq_aprobar_paso', None)
                    st.rerun()
            with c2:
                if st.button("➡️ CONTINUAR — VER VISTA PREVIA", use_container_width=True,
                             type="primary", key="apr_continuar_1"):
                    st.session_state.mq_aprobar_paso = 2
                    st.rerun()

    # ── PASO 2: VISTA PREVIA ──────────────────────────────────────────────────
    elif paso == 2:
        cfg  = DBManager.get_all_email_config()
        qd   = DBManager.get_quote_full_details(quote_id)
        items = DBManager.get_quote_items(quote_id)

        st.markdown("### 👁️ Vista Previa del Correo")
        st.info(
            f"**Para:** {cfg.get('to_email', 'N/A')}\n\n"
            f"**Asunto:** Orden de Compra #{quote.get('quote_number', 'N/A')}\n\n"
            f"**Adjuntos:** PNG Cotización + PNG Cuadro de Costos"
        )

        st.markdown("---")
        st.markdown(f"**{cfg.get('texto_apertura', '')}**")
        st.markdown("---")

        # Datos del cliente (solo los que tienen valor)
        st.markdown("**📋 Datos del Cliente:**")
        campos_cliente = [
            ("Nombre",    quote.get('client_name')),
            ("Teléfono",  quote.get('client_phone')),
            ("Vehículo",  quote.get('client_vehicle')),
            ("Año",       quote.get('client_year')),
            ("VIN",       quote.get('client_vin')),
            ("Cédula",    quote.get('client_cedula')),
            ("Dirección", quote.get('client_address')),
        ]
        for label, val in campos_cliente:
            if val and str(val).strip():
                st.write(f"• **{label}:** {val}")

        st.markdown("---")
        st.markdown("**🔧 Ítems:**")
        for idx, item in enumerate(items, 1):
            desc = item.get('description', 'N/A')
            st.markdown(f"**Ítem #{idx}**")
            st.write(f"  • Descripción: {desc}")

            # Links con cantidad de compra (formato requerido)
            try:
                raw_links = item.get('page_url') or item.get('reference_links') or '[]'
                if isinstance(raw_links, str) and raw_links.strip().startswith('['):
                    links = json.loads(raw_links)
                elif isinstance(raw_links, list):
                    links = raw_links
                elif raw_links and str(raw_links).strip():
                    links = [{'url': str(raw_links), 'qty': 1}]
                else:
                    links = []
                for li in links:
                    if isinstance(li, dict):
                        url = li.get('url', '')
                        qty = li.get('qty', 1)
                    else:
                        url = str(li)
                        qty = 1
                    if url:
                        st.write(f"  • Comprar: {qty}")
                        st.write(f"  • Link: {url}")
            except Exception:
                pass

        st.markdown("---")
        st.markdown(f"*{cfg.get('texto_cierre', '')}*")
        st.markdown(
            f"**{st.session_state.get('full_name', st.session_state.get('username', 'Analista'))}**  \n"
            f"*{cfg.get('cargo_analista', 'Analista de Ventas')}*  \n"
            "LogiPartVE Pro"
        )

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("❌ CANCELAR", use_container_width=True,
                         key="apr_cancel_2"):
                st.session_state.pop('mq_aprobar_id', None)
                st.session_state.pop('mq_aprobar_paso', None)
                st.rerun()
        with c2:
            if st.button("📧 ENVIAR APROBACIÓN", use_container_width=True,
                         type="primary", key="apr_enviar"):
                st.session_state.mq_aprobar_paso = 3
                st.rerun()

    # ── PASO 3: ENVÍO ─────────────────────────────────────────────────────────
    elif paso == 3:
        with st.spinner("⏳ Generando documentos y enviando correo..."):
            exito, mensaje = _enviar_orden_aprobada(quote_id)

        if exito:
            st.success(f"✅ {mensaje}")
            st.balloons()
            st.session_state.pop('mq_aprobar_id', None)
            st.session_state.pop('mq_aprobar_paso', None)
            # Refrescar la vista de la cotización
            st.session_state.mq_ver_id = quote_id
            st.rerun()
        else:
            st.error(f"❌ {mensaje}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 INTENTAR DE NUEVO", use_container_width=True,
                             type="primary", key="apr_retry"):
                    st.rerun()
            with c2:
                if st.button("❌ CANCELAR", use_container_width=True,
                             key="apr_cancel_3"):
                    st.session_state.pop('mq_aprobar_id', None)
                    st.session_state.pop('mq_aprobar_paso', None)
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MOTOR DE ENVÍO — FASE 5
# ─────────────────────────────────────────────────────────────────────────────
def _enviar_orden_aprobada(quote_id: int):
    """
    Genera PNG cotización + PNG cuadro de costos, construye el correo
    y lo envía usando Resend. Retorna (True, msg) o (False, msg).
    """
    import json
    import base64

    try:
        from services.email_service import EmailService
        from services.document_generation.png_generator import PNGQuoteGenerator

        cfg   = DBManager.get_all_email_config()
        qd    = DBManager.get_quote_full_details(quote_id)
        quote = DBManager.get_quote_by_id(quote_id)
        items = DBManager.get_quote_items(quote_id)

        if not qd or not quote:
            return False, "No se pudo cargar la cotización desde la base de datos."

        quote_number = quote.get('quote_number', str(quote_id))
        output_dir   = os.path.join(tempfile.gettempdir(), 'logipartve_docs')
        os.makedirs(output_dir, exist_ok=True)

        # ── Generar PNG de la cotización ──────────────────────────────────────
        datos_adaptados = _adaptar_quote_para_generadores(qd)
        png_cot_path    = os.path.join(output_dir, f"cot_{quote_number}.png")
        try:
            gen = PNGQuoteGenerator()
            gen.generate_quote_png_from_data(datos_adaptados, png_cot_path)
            # Actualizar ruta en BD
            _conn = DBManager.get_connection()
            _cur  = _conn.cursor()
            if DBManager.USE_POSTGRES:
                _cur.execute("UPDATE quotes SET jpeg_path = %s WHERE id = %s",
                             (png_cot_path, quote_id))
            else:
                _cur.execute("UPDATE quotes SET jpeg_path = ? WHERE id = ?",
                             (png_cot_path, quote_id))
            _conn.commit()
            _cur.close()
            _conn.close()
        except Exception as e:
            return False, f"Error generando PNG de cotización: {e}"

        # ── Generar PNG del cuadro de costos ─────────────────────────────────
        png_cuadro_path = os.path.join(output_dir, f"cuadro_{quote_number}.png")
        try:
            _generar_png_cuadro_costos_para_email(quote_id, png_cuadro_path)
        except Exception as e:
            return False, f"Error generando PNG del Cuadro de Costos: {e}"

        # ── Construir cuerpo del correo ───────────────────────────────────────
        analista_nombre = st.session_state.get(
            'full_name', st.session_state.get('username', 'Analista'))
        cargo           = cfg.get('cargo_analista', 'Analista de Ventas')
        texto_apertura  = cfg.get('texto_apertura',
            'Hola, por favor dar proceso a esta orden aprobada. '
            'A continuación te envio los datos para comprar:')
        texto_cierre    = cfg.get('texto_cierre',
            'Sin más por el momento, queda de ustedes')

        # Datos del cliente (solo los que tienen valor)
        campos_cliente = [
            ("Nombre",    quote.get('client_name')),
            ("Teléfono",  quote.get('client_phone')),
            ("Vehículo",  quote.get('client_vehicle')),
            ("Año",       quote.get('client_year')),
            ("VIN",       quote.get('client_vin')),
            ("Cédula",    quote.get('client_cedula')),
            ("Dirección", quote.get('client_address')),
        ]
        cliente_html = "".join(
            f"<li><strong>{lbl}:</strong> {val}</li>"
            for lbl, val in campos_cliente
            if val and str(val).strip()
        )

        # Ítems con links (formato requerido: Descripción, Comprar, Link)
        items_html = ""
        for idx, item in enumerate(items, 1):
            desc = item.get('description', 'N/A')
            items_html += f"<p><strong>Ítem #{idx}</strong><br>Descripción: {desc}</p>"
            try:
                raw_links = item.get('page_url') or item.get('reference_links') or '[]'
                if isinstance(raw_links, str) and raw_links.strip().startswith('['):
                    links = json.loads(raw_links)
                elif isinstance(raw_links, list):
                    links = raw_links
                elif raw_links and str(raw_links).strip():
                    links = [{'url': str(raw_links), 'qty': 1}]
                else:
                    links = []
                if links:
                    items_html += "<ul>"
                    for li in links:
                        if isinstance(li, dict):
                            url = li.get('url', '')
                            qty = li.get('qty', 1)
                        else:
                            url = str(li)
                            qty = 1
                        if url:
                            items_html += (
                                f"<li>Comprar: {qty}<br>"
                                f"Link: <a href='{url}'>{url}</a></li>"
                            )
                    items_html += "</ul>"
            except Exception:
                pass

        html_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:700px;margin:auto;">
          <h2 style="color:#1a3c6e;">Orden de Compra #{quote_number}</h2>
          <p>{texto_apertura}</p>
          <hr>
          <h3>📋 Datos del Cliente</h3>
          <ul>{cliente_html}</ul>
          <hr>
          <h3>🔧 Ítems</h3>
          {items_html}
          <hr>
          <p><em>{texto_cierre}</em></p>
          <p><strong>{analista_nombre}</strong><br>
          <em>{cargo}</em><br>
          LogiPartVE Pro</p>
        </div>
        """

        # ── Preparar adjuntos ─────────────────────────────────────────────────
        adjuntos = []
        for path_file, nombre_file in [
            (png_cot_path,    f"cotizacion_{quote_number}.png"),
            (png_cuadro_path, f"cuadro_costos_{quote_number}.png"),
        ]:
            if os.path.exists(path_file):
                with open(path_file, 'rb') as f:
                    adjuntos.append({
                        "filename": nombre_file,
                        "content":  base64.b64encode(f.read()).decode(),
                        "type":     "image/png",
                    })

        # ── Enviar con Resend (sin CC para garantizar entrega) ───────────────
        resultado = EmailService.send_approval_email(
            from_name    = cfg.get('from_name', 'Ordenes LogiPartVE'),
            from_email   = cfg.get('from_email', 'ordenes@logipartve.com'),
            to_email     = cfg.get('to_email', ''),
            cc_list      = [],
            reply_to     = cfg.get('reply_to', ''),
            subject      = f"Orden de Compra #{quote_number}",
            html_body    = html_body,
            attachments  = adjuntos,
        )

        if resultado.get('success'):
            # Cambiar estado a APROBADA
            user_id = st.session_state.get('user_id', 0)
            DBManager.update_quote_status(quote_id, 'approved', user_id)
            return True, (
                f"Orden #{quote_number} enviada exitosamente al equipo. "
                "El estado ha sido cambiado a APROBADA."
            )
        else:
            return False, f"Error al enviar el correo: {resultado.get('error', 'Error desconocido')}"

    except Exception as e:
        return False, f"Error inesperado: {e}"


def _generar_png_cuadro_costos_para_email(quote_id: int, output_path: str):
    """Genera el PNG del cuadro de costos para adjuntar al correo.
    Usa el mismo generador completo que el botón 'Generar PNG' de la app.
    """
    from services.document_generation.cuadro_costos_generator import generar_cuadro_costos_png
    from database.config_helpers import ConfigHelpers

    quote = DBManager.get_quote_by_id(quote_id)
    items_raw = DBManager.get_quote_items(quote_id)
    if not quote or not items_raw:
        raise ValueError("No se encontró la cotización o no tiene ítems")

    try:
        dif_pct = ConfigHelpers.get_diferencial()
    except Exception:
        dif_pct = 45.0

    # Preparar items con el mismo formato que usa el botón Generar PNG
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
        utilidad  = (fob_total * factor_ut) - fob_total
        base_tax  = fob_total + handling + manejo + imp_int + utilidad + envio
        tax_pct   = 7.0
        costo_tax = base_tax * (tax_pct / 100)
        precio_usd = float(item.get('total_cost', 0) or 0)
        if precio_usd == 0:
            precio_usd = base_tax + costo_tax
        dif_val   = precio_usd * (dif_pct / 100)
        precio_bs = precio_usd + dif_val

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

    resultado = generar_cuadro_costos_png(
        quote_data=quote,
        items=items_para_cuadro,
        output_path=output_path
    )
    if not resultado:
        raise ValueError("El generador de Cuadro de Costos retornó False")
