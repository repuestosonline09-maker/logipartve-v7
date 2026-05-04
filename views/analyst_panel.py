"""
Panel de Analista - LogiPartVE Pro v7.5
Sistema de cotización SIN IA - Solo cálculos y formularios
Campos configurables desde Panel Admin
"""

import streamlit as st
import streamlit.components.v1 as _components
import json
import time
import traceback
import unicodedata
import os
import datetime
from datetime import timedelta
from database.db_manager import DBManager
from database.config_helpers import ConfigHelpers
from services.auth_manager import AuthManager
from services.quote_numbering import QuoteNumberingService
from database.cliente_manager import (
    init_clientes_table, buscar_clientes, guardar_o_actualizar,
    es_nombre_real, detectar_duplicados
)
try:
    from services.document_generation import PDFQuoteGenerator, PNGQuoteGenerator, clean_text as _clean_text_gen
except ImportError:
    PDFQuoteGenerator = None
    PNGQuoteGenerator = None
    _clean_text_gen = None
try:
    from services.timezone_utils import now_caracas_naive
except ImportError:
    from datetime import timezone
    def now_caracas_naive():
        return datetime.datetime.now(tz=timezone(timedelta(hours=-4))).replace(tzinfo=None)

# Lista de cantidades del 1 al 1000 (fija, no configurable)
CANTIDADES = list(range(1, 1001))

# ==========================================
# FUNCIÓN DE CÁLCULO DE ENVÍO (copiada de v6.2.2)
# ==========================================

def calcular_envio(largo_cm, ancho_cm, alto_cm, peso_kg, origen, tipo_envio, tarifas):
    """
    Calcula el costo de envío basado en dimensiones y peso.
    Retorna: (total, facturable, unidad, peso_volumetrico, es_minimo)
    """
    vol_cm3 = largo_cm * ancho_cm * alto_cm
    peso_vol_kg = vol_cm3 / 5000
    
    # Determinar puerto de salida
    if origen in ["MIAMI", "EEUU"]:
        puerto = "Miami"
    elif origen in ["MADRID", "ESPAÑA"]:
        puerto = "Madrid"
    else:
        puerto = "Miami"  # Default
    
    if puerto == "Miami":
        if tipo_envio == "MARITIMO":
            facturable = vol_cm3 / 28316.8  # Convertir a ft³
            costo_calc = facturable * tarifas.get("mia_m", 12.0)
            unidad = "ft³"
        else:  # Aéreo
            mayor_kg = max(peso_kg, peso_vol_kg)
            facturable = mayor_kg * 2.20462  # Convertir a lb
            costo_calc = facturable * tarifas.get("mia_a", 5.5)
            unidad = "lb"
    else:  # Madrid
        facturable = max(peso_kg, peso_vol_kg)
        costo_calc = facturable * tarifas.get("mad", 8.0)
        unidad = "kg"
    
    # Aplicar mínimo de $25
    es_minimo = False
    if costo_calc < 25.0:
        total = 25.0
        es_minimo = True
    else:
        total = costo_calc
    
    return round(total, 2), round(facturable, 2), unidad, round(peso_vol_kg, 2), es_minimo


# ==========================================
# FUNCIÓN PARA CARGAR CONFIGURACIONES DESDE BD
# ==========================================

# TTL del caché de configuraciones: 5 minutos (300 segundos)
_CONFIG_CACHE_TTL = 300

def cargar_configuraciones():
    """Carga todas las configuraciones desde la base de datos.
    
    OPTIMIZACIÓN: Usa caché en session_state con TTL de 5 minutos para evitar
    17+ llamadas a BD en cada render. El caché se invalida automáticamente cuando
    el admin actualiza configuraciones (usando la clave 'config_cache_ts').
    """
    # ── CACHÉ EN SESSION_STATE ────────────────────────────────────────────────
    # Si ya tenemos config cacheada y no ha expirado, usarla directamente
    _now = time.time()
    _cached = st.session_state.get('_config_cache')
    _cached_ts = st.session_state.get('_config_cache_ts', 0)
    if _cached is not None and (_now - _cached_ts) < _CONFIG_CACHE_TTL:
        return _cached
    # ── CARGAR DESDE BD (solo cuando el caché expiró o no existe) ────────────
    try:
        # Obtener listas desde BD usando ConfigHelpers
        paises_origen = ConfigHelpers.get_paises_origen()
        tipos_envio = ConfigHelpers.get_tipos_envio()
        tiempos_entrega = ConfigHelpers.get_tiempos_entrega()
        garantias = ConfigHelpers.get_garantias()
        
        # Solo agregar "-- Seleccione --" si la lista NO está vacía y NO empieza con él
        if paises_origen and paises_origen[0] != "-- Seleccione --":
            paises_origen = ["-- Seleccione --"] + paises_origen
        if tipos_envio and tipos_envio[0] != "-- Seleccione --":
            tipos_envio = ["-- Seleccione --"] + tipos_envio
        if tiempos_entrega and tiempos_entrega[0] != "-- Seleccione --":
            tiempos_entrega = ["-- Seleccione --"] + tiempos_entrega
        if garantias and garantias[0] != "-- Seleccione --":
            garantias = ["-- Seleccione --"] + garantias
        
        config = {
            "paises_origen": paises_origen,
            "tipos_envio": tipos_envio,
            "tiempos_entrega": tiempos_entrega,
            "garantias": garantias,
            "manejo_options": ConfigHelpers.get_manejo_options(),
            "impuesto_options": ConfigHelpers.get_impuesto_internacional_options(),
            "utilidad_factors": ConfigHelpers.get_utilidad_factors(),
            "tax_percentage": ConfigHelpers.get_tax_percentage(),
            "diferencial": ConfigHelpers.get_diferencial(),
            "iva_venezuela": ConfigHelpers.get_iva_venezuela(),
            "eur_usd_factor": float(DBManager.get_config('eur_usd_factor') or 1.23),
            "terms_conditions": DBManager.get_config('terms_conditions') or 'Términos y condiciones estándar.'
        }
        # Guardar en caché con timestamp
        st.session_state['_config_cache'] = config
        st.session_state['_config_cache_ts'] = _now
        return config
    except Exception as e:
        # Valores por defecto si hay error
        return {
            "paises_origen": ["-- Seleccione --", "EEUU", "MIAMI", "ESPAÑA", "MADRID"],
            "tipos_envio": ["-- Seleccione --", "AEREO", "MARITIMO", "TERRESTRE"],
            "tiempos_entrega": ["-- Seleccione --", "02 A 05 DIAS", "08 A 12 DIAS", "12 A 15 DIAS"],
            "garantias": ["-- Seleccione --", "NO APLICA", "15 DIAS", "30 DIAS", "45 DIAS", "3 MESES", "6 MESES", "1 AÑO"],
            "manejo_options": [0.0, 15.0, 23.0, 25.0],
            "impuesto_options": [0, 25, 30, 35, 40, 45, 50],
            "utilidad_factors": [1.4285, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10, 0],
            "tax_percentage": 7.0,
            "diferencial": 45.0,
            "iva_venezuela": 16.0,
            "terms_conditions": "Términos y condiciones estándar."
        }


# ==========================================
# FUNCIÓN PRINCIPAL DEL PANEL
# ==========================================

def render_analyst_panel():
    """Renderiza el panel de analista para crear cotizaciones"""

    # ==========================================
    # SCROLL AUTOMÁTICO AL TOPE
    # Si se activó el flag (ej: al pulsar NUEVA COTIZACIÓN), inyectar JS de scroll
    # ==========================================
    if st.session_state.pop('scroll_to_top', False):
        _components.html(
            """
            <script>
            (function() {
                var doc = window.parent.document;
                // El contenedor scrollable real de Streamlit es section.stMain
                // Verificado inspeccionando el DOM en produccion
                var el = doc.querySelector('section.stMain');
                if (el) {
                    el.scrollTo({top: 0, behavior: 'smooth'});
                } else {
                    // Fallback: intentar otros selectores conocidos
                    var fallbacks = ['section.main', '.stMain', '[data-testid="stAppViewContainer"]'];
                    for (var i = 0; i < fallbacks.length; i++) {
                        var fb = doc.querySelector(fallbacks[i]);
                        if (fb) { fb.scrollTo({top: 0, behavior: 'smooth'}); break; }
                    }
                }
            })();
            </script>
            """,
            height=0
        )

    # Cargar configuraciones desde BD
    config = cargar_configuraciones()
    
    # Inicializar estado de sesión (verificar tipo también)
    # Protección adicional: asegurarse de que cotizacion_items sea siempre una lista
    if 'cotizacion_items' not in st.session_state:
        st.session_state.cotizacion_items = []
    # Verificar si cotizacion_items es una lista válida, si no, reinicializarla
    elif not isinstance(st.session_state.cotizacion_items, list) or callable(st.session_state.cotizacion_items):
        st.session_state.cotizacion_items = []
    if 'cliente_datos' not in st.session_state:
        st.session_state.cliente_datos = {}
    # Inicializar tabla de clientes (crea si no existe, operación idempotente)
    if 'clientes_table_init' not in st.session_state:
        init_clientes_table()
        st.session_state.clientes_table_init = True
    # Estado para el autocompletado de clientes
    if 'ac_query' not in st.session_state:
        st.session_state.ac_query = ''
    if 'ac_resultados' not in st.session_state:
        st.session_state.ac_resultados = []
    if 'ac_seleccionado' not in st.session_state:
        st.session_state.ac_seleccionado = None
    # Estado para el panel de alerta de cliente existente
    if 'ac_alerta_cliente' not in st.session_state:
        st.session_state.ac_alerta_cliente = None   # dict del cliente encontrado
    if 'ac_alerta_modo' not in st.session_state:
        st.session_state.ac_alerta_modo = None      # None | 'alerta' | 'actualizar'
    if 'ac_alerta_nombre_trigger' not in st.session_state:
        st.session_state.ac_alerta_nombre_trigger = ''  # nombre que disparó la alerta
    # ── PROTECCIÓN ANTI-DUPLICADO ────────────────────────────────────────────
    # Flag que bloquea el botón GUARDAR después del primer clic exitoso.
    # Se resetea solo cuando el analista inicia una NUEVA COTIZACIÓN.
    if 'guardando_en_progreso' not in st.session_state:
        st.session_state.guardando_en_progreso = False
    # ── CACHÉ DE TARIFAS (TTL 5 min) ─────────────────────────────────────────
    # Evita 3 llamadas a BD en cada render. El admin puede forzar recarga
    # desde su panel (invalida '_tarifas_cache_ts' en session_state).
    _tarifas_now = time.time()
    _tarifas_cached_ts = st.session_state.get('_tarifas_cache_ts', 0)
    if 'tarifas' not in st.session_state or (_tarifas_now - _tarifas_cached_ts) >= _CONFIG_CACHE_TTL:
        _mia_a = DBManager.get_freight_rate('Miami', 'Aéreo')
        _mia_m = DBManager.get_freight_rate('Miami', 'Marítimo')
        _mad   = DBManager.get_freight_rate('Madrid', 'Aéreo')
        st.session_state.tarifas = {
            "mia_a": float(_mia_a) if _mia_a is not None else 9.0,   # Miami Aéreo $/lb
            "mia_m": float(_mia_m) if _mia_m is not None else 40.0,  # Miami Marítimo $/ft³
            "mad":   float(_mad)   if _mad   is not None else 25.0,  # Madrid Aéreo $/kg
        }
        st.session_state['_tarifas_cache_ts'] = _tarifas_now
    # ── FIN CACHÉ DE TARIFAS ──────────────────────────────────────────────────
    
    # ==========================================
    # FUNCIONES CALLBACK PARA BOTONES DE ÍTEMS
    # Estas funciones se ejecutan ANTES del re-render cuando se presiona un botón
    # ==========================================
    def _callback_editar_item(idx):
        """Callback para el botón EDITAR de un ítem"""
        items = st.session_state.get('cotizacion_items', [])
        if not isinstance(items, list) or idx >= len(items):
            return
        _item = items[idx]
        st.session_state.editing_item_index = idx
        st.session_state.editing_item_data = dict(_item)
        # Incrementar reset_key para recrear widgets con nuevos valores
        if 'item_reset_counter' not in st.session_state:
            st.session_state.item_reset_counter = 0
        st.session_state.item_reset_counter += 1
        # No limpiar campos
        st.session_state.limpiar_campos_item = False
        # Pre-cargar los links del ítem (normalizar al formato {url, qty})
        _raw_link = _item.get('link', _item.get('page_url', ''))
        def _normalizar_link(lnk):
            """Convierte cualquier formato de link a {url, qty}"""
            if isinstance(lnk, dict):
                return {'url': lnk.get('url', ''), 'qty': int(lnk.get('qty', 1))}
            return {'url': str(lnk), 'qty': 1}
        if _raw_link:
            try:
                if isinstance(_raw_link, list):
                    st.session_state.item_links = [_normalizar_link(l) for l in _raw_link]
                elif str(_raw_link).strip().startswith('['):
                    _parsed = json.loads(_raw_link)
                    if isinstance(_parsed, list):
                        st.session_state.item_links = [_normalizar_link(l) for l in _parsed]
                    else:
                        st.session_state.item_links = [_normalizar_link(_raw_link)]
                else:
                    st.session_state.item_links = [_normalizar_link(_raw_link)]
            except Exception:
                st.session_state.item_links = [_normalizar_link(_raw_link)] if _raw_link else []
        else:
            st.session_state.item_links = []
    
    def _callback_eliminar_item(idx):
        """Callback para el botón ELIMINAR de un ítem"""
        items = st.session_state.get('cotizacion_items', [])
        if isinstance(items, list) and idx < len(items):
            st.session_state.cotizacion_items.pop(idx)
        # Si estábamos editando este ítem, cancelar edición
        if st.session_state.get('editing_item_index') == idx:
            if 'editing_item_index' in st.session_state:
                del st.session_state['editing_item_index']
            if 'editing_item_data' in st.session_state:
                del st.session_state['editing_item_data']
    
    # Obtener información del usuario actual
    current_user = AuthManager.get_current_user()
    user_id = current_user.get('user_id') if current_user else None
    username = current_user.get('username', 'Usuario') if current_user else 'Usuario'
    full_name = current_user.get('full_name', username) if current_user else 'Usuario'
    
    # Obtener vista previa del número de cotización (cacheado en session_state)
    # Se invalida cuando se guarda una cotización nueva (deleted en el bloque de guardado)
    _nqn_cache_key = f'_next_quote_number_cache_{user_id}'
    if user_id:
        if _nqn_cache_key not in st.session_state:
            st.session_state[_nqn_cache_key] = QuoteNumberingService.get_next_quote_number_preview(user_id, username)
        next_quote_number = st.session_state[_nqn_cache_key] or "N/A"
    else:
        next_quote_number = "N/A"
    
    # Detectar modo edición
    editing_mode = st.session_state.get('editing_mode', False)
    editing_quote_id = st.session_state.get('editing_quote_id', None)
    editing_quote_number = st.session_state.get('editing_quote_number', None)
    editing_quote_data = st.session_state.get('editing_quote_data', None)
    
    # Título con información del analista y número de cotización
    if editing_mode and editing_quote_number:
        st.title(f"✏️ Editando Cotización #{editing_quote_number}")
        # ── BANNER LLAMATIVO: imposible de ignorar ──────────────────────────────
        st.markdown(
            f"""
            <div style="
                background-color: #FF6B35;
                border: 3px solid #CC4400;
                border-radius: 8px;
                padding: 16px 20px;
                margin: 8px 0 16px 0;
                text-align: center;
            ">
                <span style="font-size:1.4rem; font-weight:800; color:#FFFFFF;">
                    ⚠️ MODO EDICIÓN ACTIVO — Cotización #{editing_quote_number}
                </span><br>
                <span style="font-size:1.0rem; color:#FFE8D6;">
                    Estás modificando una cotización existente. El botón central dice
                    <strong>GUARDAR CAMBIOS</strong>.
                    Para crear una cotización nueva, primero cancela la edición.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        # Botón para cancelar edición
        if st.button("❌ CANCELAR EDICIÓN", type="secondary"):
            # Limpiar COMPLETAMENTE el modo edición y todos los datos del formulario
            keys_to_clear = [
                'editing_mode', 'editing_quote_id', 'editing_quote_number',
                'editing_quote_data', 'editing_data_loaded',
                'editing_item_index', 'editing_item_data',
                'cotizacion_items', 'cliente_datos',
                'item_links', 'limpiar_campos_item',
                'mostrar_cotizacion', 'cotizacion_guardada',
                'show_save_success', 'saved_quote_number', 'saved_quote_id',
            ]
            for _k in keys_to_clear:
                if _k in st.session_state:
                    del st.session_state[_k]
            # Incrementar contadores de reset para limpiar los widgets del formulario
            st.session_state.cliente_reset_counter = st.session_state.get('cliente_reset_counter', 0) + 1
            st.session_state.item_reset_counter = st.session_state.get('item_reset_counter', 0) + 1
            st.session_state.item_links = []
            st.session_state.cotizacion_items = []
            st.session_state.cliente_datos = {}
            st.rerun()
    else:
        st.title("📋 Nueva Cotización")
    
    # ══════════════════════════════════════════════════════════════════════════
    # AUTO-GUARDADO DE BORRADOR — Recuperación tras cierre inesperado
    # ══════════════════════════════════════════════════════════════════════════
    # Solo mostrar en modo nueva cotización (no edición, no copia) y solo una vez
    if (not editing_mode and not st.session_state.get('copying_mode', False)
            and user_id
            and not st.session_state.get('draft_checked', False)
            and not st.session_state.get('draft_recovered', False)
            and not st.session_state.get('draft_discarded', False)):
        st.session_state.draft_checked = True
        _draft_info = DBManager.load_draft(user_id)
        if _draft_info and _draft_info.get('items_count', 0) > 0:
            st.session_state._pending_draft = _draft_info

    # Mostrar banner de borrador pendiente si existe
    if st.session_state.get('_pending_draft') and not st.session_state.get('draft_recovered', False):
        _d = st.session_state._pending_draft
        _d_items   = _d.get('items_count', 0)
        _d_cliente = _d.get('client_name', '') or 'Sin nombre'
        _d_vehiculo= _d.get('client_vehicle', '') or ''
        _d_fecha   = _d.get('updated_at', '')
        _d_fecha_str = str(_d_fecha)[:16] if _d_fecha else 'fecha desconocida'
        st.markdown(
            f"""
            <div style="background:#FFF3CD;border:2px solid #FFC107;border-radius:8px;
                        padding:14px 18px;margin:8px 0 16px 0;">
                <span style="font-size:1.1rem;font-weight:700;color:#856404;">
                    ⚠️ Tienes un borrador sin terminar — {_d_fecha_str}
                </span><br>
                <span style="color:#533f03;">
                    Cliente: <strong>{_d_cliente}</strong>
                    {'| Vehículo: <strong>' + _d_vehiculo + '</strong>' if _d_vehiculo else ''}
                    | <strong>{_d_items} ítem{'s' if _d_items != 1 else ''}</strong> guardado{'s' if _d_items != 1 else ''}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        _col_rec, _col_des = st.columns(2)
        with _col_rec:
            if st.button("🔄 RECUPERAR BORRADOR", type="primary", use_container_width=True):
                _draft_data = _d.get('draft_data', {})
                # Restaurar datos del cliente
                st.session_state.cliente_datos = _draft_data.get('cliente', {})
                # Restaurar ítems
                st.session_state.cotizacion_items = _draft_data.get('items', [])
                # Limpiar flags
                st.session_state.draft_recovered  = True
                st.session_state._pending_draft    = None
                st.session_state.draft_checked     = False
                # Forzar re-render de widgets con los datos recuperados
                st.session_state.cliente_reset_counter = st.session_state.get('cliente_reset_counter', 0) + 1
                st.rerun()
        with _col_des:
            if st.button("🗑️ DESCARTAR", type="secondary", use_container_width=True):
                DBManager.delete_draft(user_id)
                st.session_state._pending_draft  = None
                st.session_state.draft_discarded = True
                st.session_state.draft_checked   = False
                st.rerun()
    # ══════════════════════════════════════════════════════════════════════════

    # Mostrar mensaje de éxito si se acaba de guardar
    if st.session_state.get('show_save_success', False):
        st.success(f"✅ ¡Cotización {st.session_state.saved_quote_number} guardada exitosamente! Ahora puedes generar el PDF.")
        # Limpiar el flag después de mostrar
        st.session_state.show_save_success = False
    
    # Cargar datos en modo edición (solo la primera vez)
    if editing_mode and editing_quote_data and not st.session_state.get('editing_data_loaded', False):
        # Cargar datos del cliente
        st.session_state.cliente_datos = {
            'nombre': editing_quote_data.get('client_name', ''),
            'telefono': editing_quote_data.get('client_phone', ''),
            'email': editing_quote_data.get('client_email', ''),
            'cedula': editing_quote_data.get('client_cedula', ''),
            'direccion': editing_quote_data.get('client_address', ''),
            'vehiculo': editing_quote_data.get('client_vehicle', ''),
            'cilindrada': editing_quote_data.get('client_cilindrada', ''),
            'year': editing_quote_data.get('client_year', ''),
            'vin': editing_quote_data.get('client_vin', '')
        }
        
        # Cargar ítems con TODOS los campos (incluyendo financieros y de IVA)
        items = editing_quote_data.get('items', [])
        st.session_state.cotizacion_items = []
        for item in items:
            # Reconstruir campos financieros desde los costos guardados en BD
            _costo_fob      = float(item.get('unit_cost', 0) or 0)
            _costo_handling = float(item.get('international_handling', 0) or 0)
            _costo_manejo   = float(item.get('national_handling', 0) or 0)
            _costo_envio    = float(item.get('shipping_cost', 0) or 0)
            _impuesto_pct   = float(item.get('tax_percentage', 0) or 0)
            _factor_util    = float(item.get('profit_factor', 1.0) or 1.0)
            _cantidad       = int(item.get('quantity', 1) or 1)
            _total_cost     = float(item.get('total_cost', 0) or 0)

            # Reconstruir valores derivados que el recalculador de totales necesita
            _fob_total      = _costo_fob * _cantidad
            _costo_impuesto = _fob_total * (_impuesto_pct / 100)
            _utilidad_base  = _fob_total + _costo_handling + _costo_manejo + _costo_impuesto
            _utilidad_valor = _utilidad_base * (_factor_util - 1.0)

            # IVA: recuperar de los campos extendidos si existen en BD
            _aplicar_iva    = bool(item.get('aplicar_iva', False))
            _iva_porcentaje = float(item.get('iva_porcentaje', 16.0) or 16.0)
            _iva_valor      = float(item.get('iva_valor', 0) or 0)
            _precio_bs      = float(item.get('precio_bs', _total_cost) or _total_cost)
            _precio_usd     = float(item.get('precio_usd', _total_cost) or _total_cost)

            st.session_state.cotizacion_items.append({
                'descripcion':          item.get('description', ''),
                'parte':                item.get('part_number', ''),
                'marca':                item.get('marca', ''),
                'garantia':             item.get('garantia', ''),
                'cantidad':             _cantidad,
                'origen':               item.get('origen', ''),
                'envio_tipo':           item.get('envio_tipo', ''),
                'tiempo_entrega':       item.get('tiempo_entrega', ''),
                'fabricacion':          item.get('fabricacion', ''),
                'link':                 item.get('page_url', ''),
                # Costos base
                'costo_fob':            _costo_fob,
                'costo_handling':       _costo_handling,
                'costo_manejo':         _costo_manejo,
                'costo_envio':          _costo_envio,
                'impuesto_porcentaje':  _impuesto_pct,
                'factor_utilidad':      _factor_util,
                # Campos derivados que usa el recalculador de totales
                'fob_total':            _fob_total,
                'costo_impuesto':       _costo_impuesto,
                'utilidad_valor':       _utilidad_valor,
                'diferencial_valor':    float(item.get('diferencial_valor', 0) or 0),
                'diferencial_porcentaje': float(item.get('diferencial_porcentaje', 0) or 0),
                'costo_tax':            float(item.get('costo_tax', 0) or 0),
                # IVA — CAMPOS CRÍTICOS que antes no se cargaban
                'aplicar_iva':          _aplicar_iva,
                'iva_porcentaje':       _iva_porcentaje,
                'iva_valor':            _iva_valor,
                # Precios finales
                'costo_unitario':       _costo_fob,
                'costo_total':          _total_cost,
                'costo_total_bs':       _precio_bs,
                'precio_usd':           _precio_usd,
                'precio_bs':            _precio_bs,
                'precio_usd_total':     _precio_usd,
            })
        
        # Marcar como cargado
        st.session_state.editing_data_loaded = True
        st.rerun()

    # ── MODO COPIA: pre-cargar datos de la orden original (solo la primera vez) ──
    copying_mode = st.session_state.get('copying_mode', False)
    copying_from_number = st.session_state.get('copying_from_number', '')
    copying_quote_data  = st.session_state.get('copying_quote_data', None)

    if copying_mode and copying_quote_data and not st.session_state.get('copying_data_loaded', False):
        # Guardar snapshot de los ítems originales para detectar cambios obligatorios
        st.session_state.copying_original_items_snapshot = [
            {
                'descripcion': it.get('description', ''),
                'parte':       it.get('part_number', ''),
                'marca':       it.get('marca', ''),
                'costo_fob':   float(it.get('unit_cost', 0) or 0),
                'cantidad':    int(it.get('quantity', 1) or 1),
            }
            for it in copying_quote_data.get('items', [])
        ]
        # Pre-cargar datos del cliente
        st.session_state.cliente_datos = {
            'nombre':     copying_quote_data.get('client_name', ''),
            'telefono':   copying_quote_data.get('client_phone', ''),
            'email':      copying_quote_data.get('client_email', ''),
            'cedula':     copying_quote_data.get('client_cedula', ''),
            'direccion':  copying_quote_data.get('client_address', ''),
            'vehiculo':   copying_quote_data.get('client_vehicle', ''),
            'cilindrada': copying_quote_data.get('client_cilindrada', ''),
            'year':       copying_quote_data.get('client_year', ''),
            'vin':        copying_quote_data.get('client_vin', '')
        }
        # Pre-cargar ítems (misma lógica que editing_mode)
        items_copy = copying_quote_data.get('items', [])
        st.session_state.cotizacion_items = []
        for item in items_copy:
            _costo_fob      = float(item.get('unit_cost', 0) or 0)
            _costo_handling = float(item.get('international_handling', 0) or 0)
            _costo_manejo   = float(item.get('national_handling', 0) or 0)
            _costo_envio    = float(item.get('shipping_cost', 0) or 0)
            _impuesto_pct   = float(item.get('tax_percentage', 0) or 0)
            _factor_util    = float(item.get('profit_factor', 1.0) or 1.0)
            _cantidad       = int(item.get('quantity', 1) or 1)
            _total_cost     = float(item.get('total_cost', 0) or 0)
            _fob_total      = _costo_fob * _cantidad
            _costo_impuesto = _fob_total * (_impuesto_pct / 100)
            _utilidad_base  = _fob_total + _costo_handling + _costo_manejo + _costo_impuesto
            _utilidad_valor = _utilidad_base * (_factor_util - 1.0)
            _aplicar_iva    = bool(item.get('aplicar_iva', False))
            _iva_porcentaje = float(item.get('iva_porcentaje', 16.0) or 16.0)
            _iva_valor      = float(item.get('iva_valor', 0) or 0)
            _precio_bs      = float(item.get('precio_bs', _total_cost) or _total_cost)
            _precio_usd     = float(item.get('precio_usd', _total_cost) or _total_cost)
            st.session_state.cotizacion_items.append({
                'descripcion':            item.get('description', ''),
                'parte':                  item.get('part_number', ''),
                'marca':                  item.get('marca', ''),
                'garantia':               item.get('garantia', ''),
                'cantidad':               _cantidad,
                'origen':                 item.get('origen', ''),
                'envio_tipo':             item.get('envio_tipo', ''),
                'tiempo_entrega':         item.get('tiempo_entrega', ''),
                'fabricacion':            item.get('fabricacion', ''),
                'link':                   item.get('page_url', ''),
                'costo_fob':              _costo_fob,
                'costo_handling':         _costo_handling,
                'costo_manejo':           _costo_manejo,
                'costo_envio':            _costo_envio,
                'impuesto_porcentaje':    _impuesto_pct,
                'factor_utilidad':        _factor_util,
                'fob_total':              _fob_total,
                'costo_impuesto':         _costo_impuesto,
                'utilidad_valor':         _utilidad_valor,
                'diferencial_valor':      float(item.get('diferencial_valor', 0) or 0),
                'diferencial_porcentaje': float(item.get('diferencial_porcentaje', 0) or 0),
                'costo_tax':              float(item.get('costo_tax', 0) or 0),
                'aplicar_iva':            _aplicar_iva,
                'iva_porcentaje':         _iva_porcentaje,
                'iva_valor':              _iva_valor,
                'costo_unitario':         _costo_fob,
                'costo_total':            _total_cost,
                'costo_total_bs':         _precio_bs,
                'precio_usd':             _precio_usd,
                'precio_bs':              _precio_bs,
                'precio_usd_total':       _precio_usd,
            })
        st.session_state.copying_data_loaded = True
        # Incrementar reset_key para forzar re-render de los widgets con los datos pre-cargados
        st.session_state.cliente_reset_counter = st.session_state.get('cliente_reset_counter', 0) + 1
        st.rerun()

    # Mostrar banner de modo copia si está activo
    if copying_mode and copying_from_number:
        st.markdown(
            f"""
            <div style="
                background-color: #1A6B3C;
                border: 3px solid #0D4A28;
                border-radius: 8px;
                padding: 16px 20px;
                margin: 8px 0 16px 0;
                text-align: center;
            ">
                <span style="font-size:1.4rem; font-weight:800; color:#FFFFFF;">
                    📋 MODO COPIA — Basada en #{copying_from_number}
                </span><br>
                <span style="font-size:1.0rem; color:#C8F0D8;">
                    Los datos están pre-cargados. <strong>⚠️ Debes modificar al menos un ítem</strong>
                    antes de poder guardar. Esta será una cotización nueva independiente.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("❌ CANCELAR COPIA", type="secondary"):
            keys_copy = [
                'copying_mode', 'copying_from_quote_id', 'copying_from_number',
                'copying_quote_data', 'copying_data_loaded',
                'copying_original_items_snapshot',
                'cotizacion_items', 'cliente_datos',
                'item_links', 'mostrar_cotizacion', 'cotizacion_guardada',
                'show_save_success', 'saved_quote_number', 'saved_quote_id',
            ]
            for _k in keys_copy:
                if _k in st.session_state:
                    del st.session_state[_k]
            st.session_state.cliente_reset_counter = st.session_state.get('cliente_reset_counter', 0) + 1
            st.session_state.item_reset_counter = st.session_state.get('item_reset_counter', 0) + 1
            st.session_state.cotizacion_items = []
            st.session_state.cliente_datos = {}
            st.rerun()

    # ==========================================
    # SIDEBAR: CONVERTIDOR DE MONEDA EUR → USD
    # ==========================================
    with st.sidebar:
        st.markdown("### 💱 Convertidor de Moneda")
        st.info("🇪🇺 Convierte precios de repuestos europeos de EUR a USD")
        
        # Obtener factor de conversión desde config (ya cargado al inicio)
        eur_usd_factor = config.get('eur_usd_factor', 1.23)
        
        # Inicializar contador de reset para el convertidor si no existe
        if 'converter_reset_counter' not in st.session_state:
            st.session_state.converter_reset_counter = 0
        if 'eur_amount' not in st.session_state:
            st.session_state.eur_amount = 0.0
        if 'usd_amount' not in st.session_state:
            st.session_state.usd_amount = 0.0
        
        # Usar el contador para generar key única que cambie al resetear
        converter_key = st.session_state.converter_reset_counter
        
        # Input para EUR
        eur_input = st.number_input(
            "💶 EURO (€)",
            min_value=0.0,
            value=None,
            step=1.0,
            placeholder="Ej: 100",
            help="Ingrese el precio en euros",
            key=f"eur_input_field_{converter_key}"
        )
        
        # Calcular automáticamente USD
        if eur_input is not None and eur_input > 0:
            st.session_state.eur_amount = eur_input
            st.session_state.usd_amount = eur_input * eur_usd_factor
        else:
            st.session_state.eur_amount = 0.0
            st.session_state.usd_amount = 0.0
        
        # Mostrar resultado USD
        st.markdown(f"### 💵 DÓLAR ($)")
        st.success(f"**${st.session_state.usd_amount:.2f} USD**")
        st.caption(f"📊 Factor: €1 = ${eur_usd_factor}")
        
        # Botón para limpiar
        if st.button("🧹 Limpiar Convertidor", use_container_width=True, key="btn_limpiar_convertidor"):
            # Incrementar el contador de reset para forzar la recreación del widget
            st.session_state.converter_reset_counter += 1
            st.session_state.eur_amount = 0.0
            st.session_state.usd_amount = 0.0
            # No necesita st.rerun(): el cambio de key fuerza recreación automática del widget
        
        st.markdown("---")
        st.caption("📋 Copie el monto USD al campo 'Costo FOB ($)' en el formulario")
        st.markdown("---")
    
    # ==========================================
    # SIDEBAR: CALCULADORA DE ENVÍO
    # ==========================================
    with st.sidebar:
        st.markdown("### 📊 Calculadora de Envío")
        st.info("💡 Use esta calculadora para estimar el costo de envío. El resultado es solo una **referencia**.")
        
        # Mostrar tarifas activas (cargadas desde BD)
        _t = st.session_state.tarifas
        st.caption(
            f"📋 Tarifas activas: "
            f"Miami Aéreo **${_t['mia_a']}/lb** | "
            f"Miami Marítimo **${_t['mia_m']}/ft³** | "
            f"Madrid Aéreo **${_t['mad']}/kg**"
        )
        
        # Inicializar contador de reset si no existe
        if 'calc_reset_counter' not in st.session_state:
            st.session_state.calc_reset_counter = 0
        
        # Usar el contador para generar keys únicas que cambien al resetear
        reset_key = st.session_state.calc_reset_counter
        
        calc_origen = st.selectbox("Origen", ["Miami", "Madrid"], key=f"calc_origen_{reset_key}")
        calc_tipo = st.selectbox("Tipo de Envío", ["Aéreo", "Marítimo"], key=f"calc_tipo_{reset_key}")
        
        calc_largo = st.number_input("Largo (cm)", min_value=0.0, value=None, step=1.0, placeholder="Ej: 50", key=f"calc_largo_{reset_key}")
        calc_ancho = st.number_input("Ancho (cm)", min_value=0.0, value=None, step=1.0, placeholder="Ej: 30", key=f"calc_ancho_{reset_key}")
        calc_alto = st.number_input("Alto (cm)", min_value=0.0, value=None, step=1.0, placeholder="Ej: 20", key=f"calc_alto_{reset_key}")
        calc_peso = st.number_input("Peso (kg)", min_value=0.0, value=None, step=1.0, placeholder="Ej: 5", key=f"calc_peso_{reset_key}")
        
        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
            if st.button("🧮 Calcular", use_container_width=True, key="btn_calcular"):
                if calc_largo > 0 and calc_ancho > 0 and calc_alto > 0 and calc_peso > 0:
                    origen_calc = "MIAMI" if calc_origen == "Miami" else "MADRID"
                    tipo_calc = "AEREO" if calc_tipo == "Aéreo" else "MARITIMO"
                    
                    total, fact, unidad, pv, es_min = calcular_envio(
                        calc_largo, calc_ancho, calc_alto, calc_peso,
                        origen_calc, tipo_calc, st.session_state.tarifas
                    )
                    
                    st.session_state.calc_resultado = {
                        'total': total,
                        'facturable': fact,
                        'unidad': unidad,
                        'peso_vol': pv,
                        'es_minimo': es_min
                    }
                else:
                    st.error("⚠️ Complete todos los campos")
        
        with calc_col2:
            if st.button("🧹 Limpiar", use_container_width=True, key="btn_limpiar_calc"):
                # Incrementar el contador de reset para forzar la recreación de todos los widgets
                st.session_state.calc_reset_counter += 1
                # Limpiar resultado
                if 'calc_resultado' in st.session_state:
                    del st.session_state.calc_resultado
                # No necesita st.rerun(): el cambio de key fuerza recreación automática del widget
        
        # Mostrar resultado si existe
        if 'calc_resultado' in st.session_state:
            res = st.session_state.calc_resultado
            st.success(f"**💰 COSTO: ${res['total']} USD**")
            st.caption(f"📦 Facturable: {res['facturable']} {res['unidad']}")
            st.caption(f"⚖️ Peso Vol.: {res['peso_vol']} kg")
            if res['es_minimo']:
                st.warning("⚠️ Tarifa mínima $25")
        
        st.markdown("---")
        st.caption("📌 Copie el monto al campo 'Envío ($)' en el formulario")
    
    # Mostrar información del analista y número de cotización
    info_col1, info_col2 = st.columns([1, 1])
    with info_col1:
        st.info(f"👤 **Analista:** {full_name}")
    with info_col2:
        st.success(f"🔢 **Número de Cotización:** {next_quote_number}")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 1: DATOS DEL CLIENTE
    # ================================    # Inicializar contador de reset para formulario del cliente
    if 'cliente_reset_counter' not in st.session_state:
        st.session_state.cliente_reset_counter = 0
    
    # Generar keys únicas basadas en el contador
    reset_key = st.session_state.cliente_reset_counter
    
    # ── AUTOCOMPLETADO: valores por defecto ──────────────────────────────────
    # En modo edición O copia, cargar desde cliente_datos. En modo normal, vacío.
    _usar_datos_guardados = editing_mode or copying_mode
    default_nombre    = st.session_state.cliente_datos.get('nombre', '')     if _usar_datos_guardados else ''
    default_telefono  = st.session_state.cliente_datos.get('telefono', '')   if _usar_datos_guardados else ''
    default_email     = st.session_state.cliente_datos.get('email', '')      if _usar_datos_guardados else ''
    default_vehiculo  = st.session_state.cliente_datos.get('vehiculo', '')   if _usar_datos_guardados else ''
    default_cilindrada= st.session_state.cliente_datos.get('cilindrada', '') if _usar_datos_guardados else ''
    default_ano       = st.session_state.cliente_datos.get('year', '')       if _usar_datos_guardados else ''
    default_vin       = st.session_state.cliente_datos.get('vin', '')        if _usar_datos_guardados else ''
    default_direccion = st.session_state.cliente_datos.get('direccion', '')  if _usar_datos_guardados else ''
    default_ci_rif    = st.session_state.cliente_datos.get('cedula', '')     if _usar_datos_guardados else ''

    # Si hay un cliente autocompletado pendiente, sobreescribir los defaults
    if st.session_state.get('ac_seleccionado'):
        _ac = st.session_state.ac_seleccionado
        default_nombre    = _ac.get('nombre', default_nombre)
        default_telefono  = _ac.get('telefono', default_telefono)
        default_direccion = _ac.get('direccion', default_direccion)
        default_ci_rif    = _ac.get('ci_rif', default_ci_rif)
        # Incrementar reset_key para forzar re-render de los widgets con nuevos valores
        st.session_state.cliente_reset_counter += 1
        reset_key = st.session_state.cliente_reset_counter
        st.session_state.ac_seleccionado = None
        st.session_state.ac_resultados = []
        st.session_state.ac_query = ''

    # ── CAMPO NOMBRE CON BÚSQUEDA Y ALERTA DE CLIENTE EXISTENTE ─────────────
    col1, col2 = st.columns(2)
    with col1:
        cliente_nombre = st.text_input(
            "Nombre del Cliente",
            value=default_nombre,
            key=f"cliente_nombre_{reset_key}",
            placeholder="Escribe nombre o apellido para buscar..."
        )
        _nombre_actual = cliente_nombre.strip()

        # ── Lógica de búsqueda y alerta ──────────────────────────────────────
        # Solo buscar si el nombre cambió y tiene al menos 3 caracteres
        if len(_nombre_actual) >= 3 and _nombre_actual != st.session_state.get('ac_query', ''):
            st.session_state.ac_query = _nombre_actual
            _encontrados = buscar_clientes(_nombre_actual, limite=8)
            st.session_state.ac_resultados = _encontrados

            # Si hay coincidencias exactas (nombre normalizado igual), disparar alerta
            from database.cliente_manager import normalizar as _norm
            _nombre_norm = _norm(_nombre_actual)
            _coincidencia_exacta = None
            for _c in _encontrados:
                if _norm(_c.get('nombre', '')) == _nombre_norm:
                    _coincidencia_exacta = _c
                    break

            if _coincidencia_exacta and st.session_state.ac_alerta_nombre_trigger != _nombre_actual:
                st.session_state.ac_alerta_cliente = _coincidencia_exacta
                st.session_state.ac_alerta_modo = 'alerta'
                st.session_state.ac_alerta_nombre_trigger = _nombre_actual

        elif len(_nombre_actual) < 3:
            st.session_state.ac_resultados = []
            st.session_state.ac_query = ''
            st.session_state.ac_alerta_modo = None
            st.session_state.ac_alerta_cliente = None
            st.session_state.ac_alerta_nombre_trigger = ''

        # ── Panel de alerta: cliente encontrado en BD ─────────────────────────
        _modo_alerta = st.session_state.get('ac_alerta_modo')
        _cli_alerta  = st.session_state.get('ac_alerta_cliente')

        if _modo_alerta == 'alerta' and _cli_alerta:
            st.markdown(
                """
                <div style='background:#fff8e1;border-left:4px solid #f9a825;
                            padding:12px 16px;border-radius:6px;margin:8px 0;'>
                <b>⚠️ Este cliente ya existe en la base de datos</b>
                </div>
                """,
                unsafe_allow_html=True
            )
            # Tabla con los datos actuales del cliente
            _datos_bd = {
                "Nombre":     _cli_alerta.get('nombre', '—'),
                "Teléfono":   _cli_alerta.get('telefono', '—') or '—',
                "Dirección":  _cli_alerta.get('direccion', '—') or '—',
                "C.I. / RIF": _cli_alerta.get('ci_rif', '—') or '—',
            }
            for _campo, _valor in _datos_bd.items():
                st.markdown(f"**{_campo}:** {_valor}")

            st.markdown("**¿Qué deseas hacer?**")
            _btn_col1, _btn_col2 = st.columns(2)
            with _btn_col1:
                if st.button(
                    "✅ Usar estos datos",
                    key=f"ac_usar_{reset_key}",
                    use_container_width=True,
                    type="primary"
                ):
                    st.session_state.ac_seleccionado = _cli_alerta
                    st.session_state.ac_alerta_modo = None
                    st.session_state.ac_alerta_cliente = None
                    st.session_state.ac_alerta_nombre_trigger = _nombre_actual
                    st.rerun()
            with _btn_col2:
                if st.button(
                    "✏️ Actualizar datos",
                    key=f"ac_actualizar_{reset_key}",
                    use_container_width=True
                ):
                    st.session_state.ac_alerta_modo = 'actualizar'
                    st.rerun()

        elif _modo_alerta == 'actualizar' and _cli_alerta:
            # ── Formulario de edición inline ──────────────────────────────────
            st.markdown(
                """
                <div style='background:#e8f5e9;border-left:4px solid #43a047;
                            padding:12px 16px;border-radius:6px;margin:8px 0;'>
                <b>✏️ Actualizar datos del cliente</b>
                </div>
                """,
                unsafe_allow_html=True
            )
            _edit_tel = st.text_input(
                "Teléfono",
                value=_cli_alerta.get('telefono', ''),
                key=f"ac_edit_tel_{reset_key}"
            )
            _edit_dir = st.text_input(
                "Dirección",
                value=_cli_alerta.get('direccion', ''),
                key=f"ac_edit_dir_{reset_key}"
            )
            _edit_ci = st.text_input(
                "C.I. / RIF",
                value=_cli_alerta.get('ci_rif', ''),
                key=f"ac_edit_ci_{reset_key}"
            )
            _save_col1, _save_col2 = st.columns(2)
            with _save_col1:
                if st.button(
                    "💾 Guardar cambios",
                    key=f"ac_guardar_edit_{reset_key}",
                    use_container_width=True,
                    type="primary"
                ):
                    from database.cliente_manager import actualizar_cliente as _actualizar
                    _actualizar(
                        _cli_alerta['id'],
                        {
                            'nombre':    _cli_alerta.get('nombre', ''),
                            'telefono':  _edit_tel.strip(),
                            'direccion': _edit_dir.strip(),
                            'ci_rif':    _edit_ci.strip(),
                        }
                    )
                    # Actualizar el dict local con los nuevos valores
                    _cli_alerta_actualizado = {
                        'id':        _cli_alerta['id'],
                        'nombre':    _cli_alerta.get('nombre', ''),
                        'telefono':  _edit_tel.strip(),
                        'direccion': _edit_dir.strip(),
                        'ci_rif':    _edit_ci.strip(),
                    }
                    st.session_state.ac_seleccionado = _cli_alerta_actualizado
                    st.session_state.ac_alerta_modo = None
                    st.session_state.ac_alerta_cliente = None
                    st.session_state.ac_alerta_nombre_trigger = _nombre_actual
                    st.success("✅ Datos actualizados correctamente.")
                    st.rerun()
            with _save_col2:
                if st.button(
                    "↩️ Cancelar",
                    key=f"ac_cancelar_edit_{reset_key}",
                    use_container_width=True
                ):
                    st.session_state.ac_alerta_modo = 'alerta'
                    st.rerun()

        else:
            # ── Sin alerta activa: mostrar sugerencias parciales normales ─────
            _resultados_ac = st.session_state.get('ac_resultados', [])
            if _resultados_ac and len(_nombre_actual) >= 3:
                st.caption("💡 Clientes encontrados — selecciona para autocompletar:")
                for _cli in _resultados_ac:
                    _label = f"{_cli['nombre']}"
                    if _cli.get('telefono'):
                        _label += f" | Tel: {_cli['telefono']}"
                    if _cli.get('ci_rif'):
                        _label += f" | C.I.: {_cli['ci_rif']}"
                    if st.button(
                        _label,
                        key=f"ac_btn_{_cli['id']}_{reset_key}",
                        use_container_width=True
                    ):
                        st.session_state.ac_seleccionado = _cli
                        st.rerun()

        # ── Alerta de duplicados (una sola vez por sesión) ────────────────────
        if 'ac_dups_cache' not in st.session_state:
            try:
                st.session_state.ac_dups_cache = detectar_duplicados()
            except Exception:
                st.session_state.ac_dups_cache = []
        if st.session_state.ac_dups_cache:
            _total_dups = sum(len(g) for g in st.session_state.ac_dups_cache)
            _is_admin_here = AuthManager.is_admin()
            # Construir lista de duplicados para mostrar en el aviso
            _dup_lines = []
            for _gi, _grupo in enumerate(st.session_state.ac_dups_cache, 1):
                for _cli in _grupo:
                    _dup_lines.append(
                        f"  • ID {_cli['id']} | **{_cli['nombre']}** "
                        f"| C.I.: {_cli.get('ci_rif') or '—'} "
                        f"| Tel: {_cli.get('telefono') or '—'}"
                    )
            _dup_detail = "\n".join(_dup_lines)
            if _is_admin_here:
                st.warning(
                    f"⚠️ Se detectaron **{_total_dups} registros duplicados** "
                    f"(misma cédula y teléfono):\n\n{_dup_detail}\n\n"
                    f"Elimina el sobrante usando el botón de abajo."
                )
                # Botones de eliminación directa para cada duplicado
                from database.cliente_manager import eliminar_cliente as _elim_cli
                for _gi, _grupo in enumerate(st.session_state.ac_dups_cache, 1):
                    st.caption(f"Grupo {_gi} — selecciona cuál eliminar:")
                    _bcols = st.columns(len(_grupo))
                    for _bi, (_bcol, _cli) in enumerate(zip(_bcols, _grupo)):
                        with _bcol:
                            _del_key = f"dup_del_{_cli['id']}_confirm"
                            if st.session_state.get(_del_key):
                                st.error(f"¿Eliminar **{_cli['nombre']}** (ID {_cli['id']})?")
                            _btn_label = f"🗑️ Eliminar ID {_cli['id']}: {_cli['nombre']}"
                            if not st.session_state.get(_del_key):
                                if st.button(_btn_label, key=f"dup_del_btn_{_cli['id']}", use_container_width=True):
                                    st.session_state[_del_key] = True
                                    st.rerun()
                            else:
                                _cc1, _cc2 = st.columns(2)
                                with _cc1:
                                    if st.button("✅ SÍ, ELIMINAR", key=f"dup_del_ok_{_cli['id']}", use_container_width=True, type="primary"):
                                        _elim_cli(_cli['id'])
                                        del st.session_state['ac_dups_cache']
                                        st.session_state[_del_key] = False
                                        st.success(f"✅ Cliente ID {_cli['id']} eliminado.")
                                        st.rerun()
                                with _cc2:
                                    if st.button("❌ CANCELAR", key=f"dup_del_cancel_{_cli['id']}", use_container_width=True):
                                        st.session_state[_del_key] = False
                                        # No necesita rerun: el flag False ya oculta la confirmación en el próximo render natural
            else:
                st.warning(
                    f"⚠️ Se detectaron **{_total_dups} registros duplicados** en la base de datos "
                    f"(misma cédula y teléfono). El administrador puede eliminarlos desde el panel."
                )

        cliente_telefono = st.text_input("Teléfono", value=default_telefono, key=f"cliente_telefono_{reset_key}")
    with col2:
        cliente_email = st.text_input("Email (opcional)", value=default_email, key=f"cliente_email_{reset_key}")
        cliente_vehiculo = st.text_input("Vehículo", value=default_vehiculo, placeholder="Ej: Hyundai Santa Fe 2006", key=f"cliente_vehiculo_{reset_key}")

    col3, col4, col5 = st.columns(3)
    with col3:
        cliente_cilindrada = st.text_input("Cilindrada/Motor", value=default_cilindrada, placeholder="Ej: V6 3.5L", key=f"cliente_cilindrada_{reset_key}")
    with col4:
        cliente_ano = st.text_input("Año del Vehículo", value=default_ano, key=f"cliente_ano_{reset_key}")
    with col5:
        cliente_vin = st.text_input("Nro. VIN (opcional)", value=default_vin, key=f"cliente_vin_{reset_key}")

    # Dirección y C.I./RIF
    col7, col8 = st.columns(2)
    with col7:
        cliente_direccion = st.text_input("Dirección (opcional)", value=default_direccion, key=f"cliente_direccion_{reset_key}")
    with col8:
        cliente_ci_rif = st.text_input("C.I. / RIF (opcional)", value=default_ci_rif, key=f"cliente_ci_rif_{reset_key}")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 2.5: ÍTEMS EXISTENTES (MODO EDICIÓN y MODO COPIA)
    # ==========================================
    _mostrar_items_existentes = (editing_mode or copying_mode) and isinstance(st.session_state.cotizacion_items, list) and len(st.session_state.cotizacion_items) > 0
    if _mostrar_items_existentes:
        st.markdown("### 📋 ÍTEMS EXISTENTES")
        _msg_items = "📝 Puede editar cualquier ítem haciendo clic en '✏️ EDITAR' o eliminar con '🗑️ ELIMINAR'"
        if copying_mode:
            _msg_items = "📝 Ítems copiados de la cotización original. Edita o elimina los que necesites antes de guardar."
        st.info(_msg_items)
        
        for i, item in enumerate(st.session_state.cotizacion_items):
            # Expandir automáticamente el ítem que se está editando
            item_being_edited = st.session_state.get('editing_item_index', None) == i
            with st.expander(f"📦 Ítem #{i+1}: {item.get('descripcion', 'Sin descripción')}", expanded=item_being_edited):
                # Mostrar TODOS los datos del ítem
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**📝 Datos Básicos:**")
                    st.write(f"• **Descripción:** {item.get('descripcion', 'N/A')}")
                    st.write(f"• **N° Parte:** {item.get('parte', 'N/A')}")
                    st.write(f"• **Marca:** {item.get('marca', 'N/A')}")
                    st.write(f"• **Garantía:** {item.get('garantia', 'N/A')}")
                    st.write(f"• **Cantidad:** {item.get('cantidad', 0)}")
                
                with col2:
                    st.markdown("**🌍 Logística:**")
                    st.write(f"• **Origen:** {item.get('origen', 'N/A')}")
                    st.write(f"• **Envío:** {item.get('envio_tipo', 'N/A')}")
                    st.write(f"• **Tiempo:** {item.get('tiempo_entrega', 'N/A')}")
                    st.write(f"• **Fabricación:** {item.get('fabricacion', 'N/A')}")
                    
                    # Mostrar múltiples links si existen (retrocompatible: str o dict {url, qty})
                    link = item.get('link', item.get('page_url', ''))
                    if link:
                        try:
                            if isinstance(link, str) and link.startswith('['):
                                links_array = json.loads(link)
                            elif isinstance(link, list):
                                links_array = link
                            else:
                                links_array = [link]  # formato antiguo: URL sola
                            if links_array:
                                st.write(f"• **Links ({len(links_array)}):**")
                                for _li, _lobj in enumerate(links_array, 1):
                                    if isinstance(_lobj, dict):
                                        _url = _lobj.get('url', '')
                                        _qty = _lobj.get('qty', 1)
                                        st.write(f"  {_li}. Comprar **{_qty}** → [{_url[:30]}...]({_url})")
                                    else:
                                        st.write(f"  {_li}. [{str(_lobj)[:30]}...]({_lobj})")
                            else:
                                st.write(f"• **Link:** No disponible")
                        except:
                            st.write(f"• **Link:** [{str(link)[:30]}...]({link})")
                    else:
                        st.write(f"• **Link:** No disponible")
                
                with col3:
                    st.markdown("**💰 Costos Internos:**")
                    st.write(f"• **FOB:** ${item.get('costo_fob', 0):.2f}")
                    st.write(f"• **Handling:** ${item.get('costo_handling', 0):.2f}")
                    st.write(f"• **Manejo:** ${item.get('costo_manejo', 0):.2f}")
                    st.write(f"• **Envío:** ${item.get('costo_envio', 0):.2f}")
                    st.write(f"• **Impuesto:** {item.get('impuesto_porcentaje', 0)}%")
                    st.write(f"• **Factor Util.:** {item.get('factor_utilidad', 0)}")
                
                # Mostrar precios finales
                st.markdown("---")
                precio_col1, precio_col2 = st.columns(2)
                with precio_col1:
                    precio_usd = item.get('costo_unitario', item.get('precio_usd', 0))
                    try:
                        precio_usd = float(precio_usd) if precio_usd else 0.0
                    except:
                        precio_usd = 0.0
                    st.metric("💵 Precio Unitario USD", f"${precio_usd:.2f}")
                
                with precio_col2:
                    total_usd = item.get('costo_total', 0)
                    try:
                        total_usd = float(total_usd) if total_usd else 0.0
                    except:
                        total_usd = 0.0
                    st.metric("📊 Total USD", f"${total_usd:.2f}")
                
            # Botones de acción FUERA del expander para que siempre sean visibles
            # Usan callbacks para modificar session_state ANTES del re-render
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                st.button(
                    f"✏️ EDITAR",
                    key=f"edit_item_{i}",
                    use_container_width=True,
                    on_click=_callback_editar_item,
                    args=(i,)
                )
            
            with btn_col2:
                st.button(
                    f"🗑️ ELIMINAR",
                    key=f"delete_item_{i}",
                    use_container_width=True,
                    type="secondary",
                    on_click=_callback_eliminar_item,
                    args=(i,)
                )
        
        st.markdown("---")
    
    # ==========================================
    # SECCIÓN 3: FORMULARIO DE ÍTEM
    # ==========================================
    try:
        num_items = len(st.session_state.cotizacion_items) if isinstance(st.session_state.cotizacion_items, list) else 0
    except:
        num_items = 0
        st.session_state.cotizacion_items = []
    
    # Detectar modo edición de ítem
    editing_item = st.session_state.get('editing_item_index', None) is not None
    editing_item_index = st.session_state.get('editing_item_index', None)
    editing_item_data = st.session_state.get('editing_item_data', {})
    
    
    if editing_item:
        st.markdown(f"### ✏️ Editando Ítem #{editing_item_index + 1}")
        st.warning("📝 Modifique los campos que desee y haga clic en '💾 ACTUALIZAR ÍTEM'")
    else:
        st.markdown(f"### 📦 Ítem #{num_items + 1}")   
    # Mostrar mensaje de éxito/error si existe
    if 'item_agregado_msg' in st.session_state:
        if "✅" in st.session_state.item_agregado_msg:
            st.success(st.session_state.item_agregado_msg)
        else:
            st.error(st.session_state.item_agregado_msg)
        # Limpiar el mensaje después de mostrarlo
        del st.session_state.item_agregado_msg
    
    # Inicializar contador de reset de campos de ítem
    if 'item_reset_counter' not in st.session_state:
        st.session_state.item_reset_counter = 0
    
    # Limpiar campos del ítem si se agregó uno nuevo
    if st.session_state.get('limpiar_campos_item', False):
        # Incrementar contador para forzar recreación de widgets
        st.session_state.item_reset_counter += 1
        # Limpiar lista de links
        st.session_state.item_links = []
        # Marcar como limpiado
        st.session_state.limpiar_campos_item = False
    
    # Usar el contador para generar keys únicas
    reset_key = st.session_state.item_reset_counter
    
    # Obtener valores por defecto si se está editando un ítem
    if editing_item:
        default_descripcion = editing_item_data.get('descripcion', '')
        default_parte = editing_item_data.get('parte', '')
        default_marca = editing_item_data.get('marca', '')
        default_link = editing_item_data.get('link', editing_item_data.get('page_url', ''))
        default_garantia = editing_item_data.get('garantia', config["garantias"][0])
        default_cantidad = editing_item_data.get('cantidad', 1)
        default_origen = editing_item_data.get('origen', config["paises_origen"][0])
        default_envio_tipo = editing_item_data.get('envio_tipo', config["tipos_envio"][0])
        default_tiempo = editing_item_data.get('tiempo_entrega', config["tiempos_entrega"][0])
        default_fabricacion = editing_item_data.get('fabricacion', config["paises_origen"][0])
        default_fob = float(editing_item_data.get('costo_fob', 0))
        default_handling = float(editing_item_data.get('costo_handling', 0))
        default_envio = float(editing_item_data.get('costo_envio', 0))
        default_manejo = editing_item_data.get('costo_manejo', config["manejo_options"][0])
        default_impuesto_pct = editing_item_data.get('impuesto_porcentaje', config["impuesto_options"][0])
        default_utilidad = editing_item_data.get('factor_utilidad', config["utilidad_factors"][0])
    else:
        default_descripcion = ''
        default_parte = ''
        default_marca = ''
        default_link = ''
        default_garantia = None
        default_cantidad = None
        default_origen = None
        default_envio_tipo = None
        default_tiempo = None
        default_fabricacion = None
        default_fob = None
        default_handling = None
        default_envio = None
        default_manejo = None
        default_impuesto_pct = None
        default_utilidad = None
    
    # Fila 1: Descripción y N° Parte
    item_col1, item_col2 = st.columns(2)
    with item_col1:
        item_descripcion = st.text_input("Descripción del Repuesto", value=default_descripcion, key=f"item_descripcion_{reset_key}", placeholder="Ej: Bomba de gasolina")
    with item_col2:
        item_parte = st.text_input("N° de Parte", value=default_parte, key=f"item_parte_{reset_key}", placeholder="Ej: 12345-ABC")
    
    # Fila 2: Marca (texto libre), Garantía (desde BD), Cantidad (1-1000)
    item_col3, item_col4, item_col5 = st.columns(3)
    with item_col3:
        item_marca = st.text_input("Marca", value=default_marca, placeholder="Ej: TOYOTA, BOSCH, DENSO...", key=f"item_marca_{reset_key}")
    with item_col4:
        # Encontrar índice de garantía por defecto
        garantia_index = config["garantias"].index(default_garantia) if default_garantia and default_garantia in config["garantias"] else 0
        item_garantia = st.selectbox("Garantía", config["garantias"], index=garantia_index if editing_item else 0, key=f"item_garantia_{reset_key}")
    with item_col5:
        # Encontrar índice de cantidad por defecto
        cantidad_index = CANTIDADES.index(default_cantidad) if default_cantidad and default_cantidad in CANTIDADES else 0
        item_cantidad = st.selectbox("Cantidad", CANTIDADES, index=cantidad_index if editing_item else 0, key=f"item_cantidad_{reset_key}")
    
    # Fila 3: Origen (desde BD), Envío (desde BD), Tiempo de Entrega (desde BD)
    item_col6, item_col7, item_col8 = st.columns(3)
    with item_col6:
        origen_index = config["paises_origen"].index(default_origen) if default_origen and default_origen in config["paises_origen"] else 0
        item_origen = st.selectbox("País de Localización", config["paises_origen"], index=origen_index if editing_item else 0, key=f"item_origen_{reset_key}")
    with item_col7:
        envio_index = config["tipos_envio"].index(default_envio_tipo) if default_envio_tipo and default_envio_tipo in config["tipos_envio"] else 0
        item_envio_tipo = st.selectbox("Tipo de Envío", config["tipos_envio"], index=envio_index if editing_item else 0, key=f"item_envio_tipo_{reset_key}")
    with item_col8:
        tiempo_index = config["tiempos_entrega"].index(default_tiempo) if default_tiempo and default_tiempo in config["tiempos_entrega"] else 0
        item_tiempo = st.selectbox("Tiempo de Entrega", config["tiempos_entrega"], index=tiempo_index if editing_item else 0, key=f"item_tiempo_{reset_key}")
    
    # Fila 4: País de Fabricación (desde BD) y Link
    item_col9, item_col10 = st.columns(2)
    with item_col9:
        fabricacion_index = config["paises_origen"].index(default_fabricacion) if default_fabricacion and default_fabricacion in config["paises_origen"] else 0
        item_fabricacion = st.selectbox("País de Fabricación", config["paises_origen"], index=fabricacion_index if editing_item else 0, key=f"item_fabricacion_{reset_key}")
    with item_col10:
        st.write("")  # Espacio para alineación
    
    # ==========================================
    # SECCIÓN 3.5: MÚLTIPLES LINKS DEL PRODUCTO
    # ==========================================
    st.markdown("### 🔗 Links del Producto (opcional - uso interno)")
    
    # Inicializar contador de links para forzar limpieza de campo
    if 'link_counter' not in st.session_state:
        st.session_state.link_counter = 0
    
    # Inicializar lista de links en session_state
    # Los links ya fueron cargados por el callback _callback_editar_item
    # Solo inicializar si no existe (para nuevo ítem)
    if 'item_links' not in st.session_state:
        st.session_state.item_links = []
    
    # ── Helpers para extraer url y qty de un link (retrocompatible) ──
    def _link_url(lnk):
        """Extrae la URL de un link (str o dict {url, qty})"""
        if isinstance(lnk, dict):
            return lnk.get('url', '')
        return str(lnk)

    def _link_qty(lnk):
        """Extrae la cantidad de un link (str o dict {url, qty})"""
        if isinstance(lnk, dict):
            return int(lnk.get('qty', 1))
        return 1

    # Mostrar links existentes
    links_to_remove = []
    if st.session_state.item_links:
        for idx, link in enumerate(st.session_state.item_links):
            # Fila 1: etiqueta "Comprar" + selector de cantidad
            lbl_col, qty_col, spacer_col = st.columns([1, 2, 3])
            with lbl_col:
                st.markdown("**Comprar:**")
            with qty_col:
                _current_qty = _link_qty(link)
                _new_qty = st.selectbox(
                    "Cantidad",
                    options=list(range(1, 101)),
                    index=_current_qty - 1,
                    key=f"link_qty_{idx}_{reset_key}",
                    label_visibility="collapsed"
                )
            # Fila 2: campo URL + botón eliminar
            col_link, col_delete = st.columns([5, 1])
            with col_link:
                _current_url = _link_url(link)
                st.text_input(
                    f"Link #{idx + 1}",
                    value=_current_url,
                    key=f"link_display_{idx}_{reset_key}",
                    on_change=lambda i=idx: st.session_state.item_links.__setitem__(
                        i,
                        {
                            'url': st.session_state[f"link_display_{i}_{reset_key}"],
                            'qty': st.session_state.get(f"link_qty_{i}_{reset_key}", 1)
                        }
                    )
                )
            with col_delete:
                if st.button("❌", key=f"delete_link_{idx}_{reset_key}", help="Eliminar link"):
                    links_to_remove.append(idx)
            # Actualizar qty en tiempo real (sin esperar on_change del text_input)
            if isinstance(st.session_state.item_links[idx], dict):
                st.session_state.item_links[idx]['qty'] = _new_qty
            else:
                st.session_state.item_links[idx] = {'url': _link_url(link), 'qty': _new_qty}

    # Eliminar links marcados
    if links_to_remove:
        for idx in sorted(links_to_remove, reverse=True):
            st.session_state.item_links.pop(idx)
        st.session_state.link_counter += 1
        st.rerun()

    # Campo para agregar nuevo link — con selector de cantidad
    st.markdown("**Comprar:**")
    new_qty_col, new_link_col1, new_link_col2 = st.columns([1, 4, 1])
    with new_qty_col:
        new_link_qty = st.selectbox(
            "Cantidad nuevo link",
            options=list(range(1, 101)),
            index=0,
            key=f"new_link_qty_{reset_key}_{st.session_state.link_counter}",
            label_visibility="collapsed"
        )
    with new_link_col1:
        new_link = st.text_input(
            "Nuevo link",
            placeholder="https://...",
            key=f"new_link_input_{reset_key}_{st.session_state.link_counter}"
        )
    with new_link_col2:
        if st.button("➞ Agregar", key=f"add_link_{reset_key}", help="Agregar link"):
            if new_link and new_link.strip():
                st.session_state.item_links.append({'url': new_link.strip(), 'qty': new_link_qty})
                st.session_state.link_counter += 1
                st.rerun()
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 4: COSTOS (Campos configurables desde Admin)
    # ==========================================
    st.markdown("### 💰 Costos (Interno - No visible al cliente)")
    
    # Preparar opciones de MANEJO con formato $
    manejo_options_display = [f"${m:.0f}" if m == int(m) else f"${m:.2f}" for m in config["manejo_options"]]
    
    # Preparar opciones de IMPUESTO INTERNACIONAL con formato %
    impuesto_options_display = [f"{i}%" for i in config["impuesto_options"]]
    
    # Preparar opciones de FACTOR DE UTILIDAD
    utilidad_options_display = [f"{u}" for u in config["utilidad_factors"]]
    
    cost_col1, cost_col2, cost_col3 = st.columns(3)
    with cost_col1:
        costo_fob = st.number_input("Costo FOB ($)", min_value=0.0, value=default_fob, step=1.0, placeholder="Ej: $50", key=f"costo_fob_{reset_key}") or 0.0
    with cost_col2:
        costo_handling = st.number_input("Handling ($)", min_value=0.0, value=default_handling, step=1.0, placeholder="Ej: $25", key=f"costo_handling_{reset_key}") or 0.0
    with cost_col3:
        # MANEJO - Selectbox desde Admin
        manejo_idx_default = config["manejo_options"].index(default_manejo) if default_manejo and default_manejo in config["manejo_options"] else 0
        manejo_idx = st.selectbox("Manejo ($)", range(len(manejo_options_display)), 
                                  index=manejo_idx_default if editing_item else 0,
                                  format_func=lambda x: manejo_options_display[x], 
                                  key=f"costo_manejo_select_{reset_key}")
        costo_manejo = config["manejo_options"][manejo_idx]
    
    cost_col4, cost_col5, cost_col6 = st.columns(3)
    with cost_col4:
        # IMPUESTO INTERNACIONAL - Selectbox desde Admin
        impuesto_idx_default = config["impuesto_options"].index(default_impuesto_pct) if default_impuesto_pct and default_impuesto_pct in config["impuesto_options"] else 0
        impuesto_idx = st.selectbox("Impuesto Internacional (%)", range(len(impuesto_options_display)),
                                    index=impuesto_idx_default if editing_item else 0,
                                    format_func=lambda x: impuesto_options_display[x],
                                    key=f"impuesto_select_{reset_key}")
        impuesto_porcentaje = config["impuesto_options"][impuesto_idx]
    with cost_col5:
        # FACTOR DE UTILIDAD - Selectbox desde Admin
        utilidad_idx_default = config["utilidad_factors"].index(default_utilidad) if default_utilidad and default_utilidad in config["utilidad_factors"] else 0
        utilidad_idx = st.selectbox("Factor de Utilidad", range(len(utilidad_options_display)),
                                    index=utilidad_idx_default if editing_item else 0,
                                    format_func=lambda x: utilidad_options_display[x],
                                    key=f"utilidad_select_{reset_key}")
        factor_utilidad = config["utilidad_factors"][utilidad_idx]
    with cost_col6:
        costo_envio = st.number_input("Envío ($)", min_value=0.0, value=default_envio, step=1.0, placeholder="Ej: $100", key=f"costo_envio_{reset_key}") or 0.0
    
    # TAX - Valor fijo desde Admin (NO seleccionable)
    tax_porcentaje = config["tax_percentage"]
    diferencial_porcentaje = config["diferencial"]
    iva_porcentaje = config["iva_venezuela"]
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 5: IVA VENEZUELA — CONTROL A NIVEL DE COTIZACIÓN COMPLETA
    # El IVA es un atributo de la cotización, NO de cada ítem individual.
    # Al activarlo, TODOS los ítems (existentes y futuros) lo heredan.
    # ==========================================
    st.markdown("### 🇻🇪 IVA Venezuela")
    
    # Inicializar el estado de IVA de la cotización si no existe
    # REGLA: El IVA siempre inicia en NO (False) por defecto.
    # El analista debe activarlo manualmente si la venta está sujeta a IVA.
    if 'cotizacion_aplica_iva' not in st.session_state:
        st.session_state.cotizacion_aplica_iva = False
    
    iva_col1, iva_col2 = st.columns([2, 3])
    with iva_col1:
        _iva_toggle_index = 1 if st.session_state.cotizacion_aplica_iva else 0
        _iva_seleccion = st.radio(
            f"⚠️ ¿Aplicar IVA ({iva_porcentaje}%) a TODA la cotización?",
            options=["NO", "SÍ"],
            index=_iva_toggle_index,
            horizontal=True,
            key=f"iva_cotizacion_radio"
        )
        # Actualizar el estado global de IVA
        st.session_state.cotizacion_aplica_iva = (_iva_seleccion == "SÍ")
        aplicar_iva = _iva_seleccion  # Compatibilidad con el código existente
    with iva_col2:
        if st.session_state.cotizacion_aplica_iva:
            st.success(f"✅ IVA {iva_porcentaje}% activo para TODOS los ítems de esta cotización")
        else:
            st.info("ℹ️ IVA desactivado. Activálo si la venta está sujeta a IVA.")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 6: CÁLCULOS AUTOMÁTICOS
    # FÓRMULAS CORREGIDAS SEGÚN EXCEL DEL USUARIO
    # IMPORTANTE: Se calcula TODO sobre FOB × Cantidad desde el inicio
    # ==========================================
    st.markdown("### 📊 Cálculos Automáticos")
    
    # PASO 1: FOB TOTAL = FOB × Cantidad
    # Según Excel: Z20 = Y20 * S20
    fob_total = costo_fob * item_cantidad
    
    # PASO 2: IMPUESTO INTERNACIONAL = FOB_TOTAL × %
    # Según Excel: AC20 = Z20 * AC16
    costo_impuesto_total = fob_total * (impuesto_porcentaje / 100)
    
    # PASO 3: UTILIDAD = (FOB_TOTAL × Factor) - FOB_TOTAL
    # Según Excel: AD20 = (Z20 * 1.4285) - Z20
    if factor_utilidad > 0:
        utilidad_total = (fob_total * factor_utilidad) - fob_total
    else:
        utilidad_total = 0
    
    # PASO 4: BASE TAX = FOB_TOTAL + Handling + Manejo + Impuesto + Utilidad + Envío
    # Según Excel: AF20 = (Z20 + AA20 + AB20 + AC20 + AD20 + AE20) * 7%
    base_tax_total = fob_total + costo_handling + costo_manejo + costo_impuesto_total + utilidad_total + costo_envio
    costo_tax_total = base_tax_total * (tax_porcentaje / 100)
    
    # PASO 5: PRECIO USD TOTAL (sin diferencial)
    # Según Excel: Z20 + AA20 + AB20 + AC20 + AD20 + AE20 + AF20
    precio_usd_total = fob_total + costo_handling + costo_manejo + costo_impuesto_total + utilidad_total + costo_envio + costo_tax_total
    
    # PASO 6: DIFERENCIAL = PRECIO_USD_TOTAL × % × Factor_Y30
    # Según Excel: AG20 = (Z20 + AA20 + AB20 + AD20 + AE20 + AC20 + AF20) * Y30
    # Nota: Y30 es el factor de diferencial (45% = 0.45)
    diferencial_total = precio_usd_total * (diferencial_porcentaje / 100)
    
    # PASO 7: PRECIO Bs TOTAL (sin IVA) = PRECIO_USD_TOTAL + DIFERENCIAL
    # Según Excel: AH20 = Z20 + AA20 + AB20 + AD20 + AE20 + AG20 + AC20 + AF20
    precio_bs_total_sin_iva = precio_usd_total + diferencial_total
    
    # PASO 8: IVA VENEZUELA (solo si el analista seleccionó SÍ)
    if aplicar_iva == "SÍ":
        iva_total = precio_bs_total_sin_iva * (iva_porcentaje / 100)
        precio_bs_total = precio_bs_total_sin_iva + iva_total
    else:
        iva_total = 0
        precio_bs_total = precio_bs_total_sin_iva
    
    # Calcular valores UNITARIOS para mostrar
    costo_impuesto = costo_impuesto_total / item_cantidad if item_cantidad > 0 else 0
    utilidad_calculada = utilidad_total / item_cantidad if item_cantidad > 0 else 0
    costo_tax = costo_tax_total / item_cantidad if item_cantidad > 0 else 0
    diferencial_valor = diferencial_total / item_cantidad if item_cantidad > 0 else 0
    iva_valor = iva_total / item_cantidad if item_cantidad > 0 else 0
    precio_usd = precio_usd_total / item_cantidad if item_cantidad > 0 else 0
    precio_bs = precio_bs_total / item_cantidad if item_cantidad > 0 else 0
    precio_bs_sin_iva = precio_bs_total_sin_iva / item_cantidad if item_cantidad > 0 else 0
    
    # Mostrar cálculos intermedios
    if aplicar_iva == "SÍ":
        calc_col1, calc_col2, calc_col3, calc_col4, calc_col5 = st.columns(5)
    else:
        calc_col1, calc_col2, calc_col3, calc_col4 = st.columns(4)
    
    with calc_col1:
        st.metric(f"Impuesto Int. ({impuesto_porcentaje}%)", f"${costo_impuesto:.2f}")
    with calc_col2:
        st.metric(f"Utilidad (Factor {factor_utilidad})", f"${utilidad_calculada:.2f}")
    with calc_col3:
        st.metric(f"TAX ({tax_porcentaje}%)", f"${costo_tax:.2f}")
    with calc_col4:
        st.metric(f"Diferencial ({diferencial_porcentaje}%)", f"${diferencial_valor:.2f}")
    
    if aplicar_iva == "SÍ":
        with calc_col5:
            st.metric(f"IVA ({iva_porcentaje}%)", f"${iva_valor:.2f}")
    
    st.markdown("---")
    
    # Mostrar resumen de precios
    st.markdown("### 💵 Resumen del Ítem")
    
    # Precio unitario en USD y Bs
    resumen_col1, resumen_col2 = st.columns(2)
    with resumen_col1:
        st.metric("💵 PRECIO USD (pago en dólares)", f"${precio_usd:.2f}")
    with resumen_col2:
        if aplicar_iva == "SÍ":
            st.metric(f"🇻🇪 PRECIO Bs (con IVA {iva_porcentaje}%)", f"${precio_bs:.2f}")
        else:
            st.metric("🇻🇪 PRECIO Bs (sin IVA)", f"${precio_bs:.2f}")
    
    # Costo total (ya calculado)
    costo_total_usd = precio_usd_total
    costo_total_bs = precio_bs_total
    
    if aplicar_iva == "SÍ":
        st.success(f"**TOTAL USD (Cant. {item_cantidad}): ${costo_total_usd:.2f}** | **TOTAL Bs (con IVA): ${costo_total_bs:.2f}**")
    else:
        st.success(f"**TOTAL USD (Cant. {item_cantidad}): ${costo_total_usd:.2f}** | **TOTAL Bs: ${costo_total_bs:.2f}**")
    
    # Variables para guardar en el ítem (usamos precio_usd como costo_unitario principal)
    total_item = precio_usd
    costo_total_item = costo_total_usd
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 6: BOTONES DE ACCIÓN
    # ==========================================
    
    btn_action_col1, btn_action_col2, btn_action_col3 = st.columns(3)
    
    with btn_action_col1:
        # Cambiar texto del botón según si se está editando un ítem
        if editing_item:
            button_text = "💾 ACTUALIZAR ÍTEM"
            button_key = "btn_actualizar_item"
        else:
            button_text = "➥ AGREGAR OTRO ÍTEM"
            button_key = "btn_agregar_item"
        
        if st.button(button_text, use_container_width=True, type="secondary", key=button_key):
            # Validar campos mínimos
            if not item_descripcion:
                st.error("⚠️ Ingrese la descripción del repuesto")
            elif costo_fob <= 0:
                st.error("⚠️ Ingrese el costo FOB")
            else:
                # Obtener links de forma segura - variable independiente
                _lnks = st.session_state.get('item_links', [])
                if not isinstance(_lnks, list):
                    _lnks = []
                # Auto-capturar link pendiente en el campo de texto (si el usuario no hizo clic en Agregar)
                _pending_link_key = f"new_link_input_{reset_key}_{st.session_state.get('link_counter', 0)}"
                _pending_link = st.session_state.get(_pending_link_key, '').strip()
                if _pending_link and _pending_link != 'https://':
                    # Verificar que no esté ya (comparando por URL)
                    _existing_urls = [_link_url(l) for l in _lnks]
                    if _pending_link not in _existing_urls:
                        _pending_qty_key = f"new_link_qty_{reset_key}_{st.session_state.get('link_counter', 0)}"
                        _pending_qty = st.session_state.get(_pending_qty_key, 1)
                        _lnks = list(_lnks) + [{'url': _pending_link, 'qty': _pending_qty}]
                _lnks_json = json.dumps(_lnks)

                # Guardar ítem actual
                nuevo_item = {
                    "descripcion": item_descripcion,
                    "parte": item_parte,
                    "marca": item_marca,
                    "garantia": item_garantia,
                    "cantidad": item_cantidad,
                    "origen": item_origen,
                    "envio_tipo": item_envio_tipo,
                    "tiempo_entrega": item_tiempo,
                    "fabricacion": item_fabricacion,
                    "link": _lnks_json,
                    "costo_fob": costo_fob,
                    "costo_handling": costo_handling,
                    "costo_manejo": costo_manejo,
                    "costo_impuesto": costo_impuesto_total,
                    "impuesto_porcentaje": impuesto_porcentaje,
                    "factor_utilidad": factor_utilidad,
                    "utilidad_valor": utilidad_total,
                    "costo_envio": costo_envio,
                    "costo_tax": costo_tax_total,
                    "tax_porcentaje": tax_porcentaje,
                    "diferencial_valor": diferencial_total,
                    "diferencial_porcentaje": diferencial_porcentaje,
                    "aplicar_iva": aplicar_iva == "SÍ",
                    "iva_porcentaje": iva_porcentaje,
                    "iva_valor": iva_total,
                    "precio_usd": precio_usd_total,
                    "precio_bs": precio_bs_total,
                    "costo_unitario": precio_usd,
                    "costo_total": costo_total_usd,
                    "costo_total_bs": costo_total_bs,
                    "fob_total": fob_total
                }
                # Protección adicional antes de append o actualizar
                try:
                    if not isinstance(st.session_state.cotizacion_items, list):
                        st.session_state.cotizacion_items = []
                    
                    if editing_item:
                        # ACTUALIZAR ítem existente en session_state
                        st.session_state.cotizacion_items[editing_item_index] = nuevo_item
                        # Limpiar estado de edición
                        if 'editing_item_index' in st.session_state:
                            del st.session_state.editing_item_index
                        if 'editing_item_data' in st.session_state:
                            del st.session_state.editing_item_data
                        
                        # ── GUARDADO AUTOMÁTICO EN BD (modo edición de cotización) ──────────
                        # Si estamos editando una cotización existente, guardar en BD
                        # automáticamente sin necesidad de presionar GUARDAR CAMBIOS.
                        if editing_mode and editing_quote_id:
                            _cliente = st.session_state.get('cliente_datos', {})
                            _items_actualizados = st.session_state.cotizacion_items
                            _ok = DBManager.update_quote_complete(
                                editing_quote_id,
                                _cliente,
                                _items_actualizados,
                                username
                            )
                            if _ok:
                                st.session_state.item_agregado_msg = f"✅ Ítem #{editing_item_index + 1} actualizado y cotización guardada automáticamente."
                            else:
                                st.session_state.item_agregado_msg = f"✅ Ítem #{editing_item_index + 1} actualizado en pantalla. (Guarda manualmente con GUARDAR CAMBIOS)"
                        else:
                            st.session_state.item_agregado_msg = f"✅ Ítem #{editing_item_index + 1} actualizado correctamente."
                    else:
                        # AGREGAR nuevo ítem — máximo 5 por cotización
                        if not hasattr(st.session_state.cotizacion_items, 'append'):
                            st.session_state.cotizacion_items = []
                        if len(st.session_state.cotizacion_items) >= 5:
                            st.session_state.item_agregado_msg = "⛔ Límite alcanzado: máximo 5 ítems por cotización."
                        else:
                            st.session_state.cotizacion_items.append(nuevo_item)
                            st.session_state.item_agregado_msg = f"✅ Ítem #{len(st.session_state.cotizacion_items)} agregado. Puede agregar otro."
                    
                    # Limpiar campos del ítem para el siguiente (mantener datos del cliente)
                    st.session_state.limpiar_campos_item = True

                    # ══ AUTO-GUARDADO DE BORRADOR ════════════════════════════════════
                    # Solo en modo nueva cotización (no edición, no copia)
                    if (not editing_mode and not st.session_state.get('copying_mode', False)
                            and user_id and username):
                        try:
                            _draft_payload = {
                                'cliente': st.session_state.get('cliente_datos', {}),
                                'items':   st.session_state.cotizacion_items,
                            }
                            DBManager.save_draft(user_id, username, _draft_payload)
                            st.session_state._draft_saved_at = time.time()
                        except Exception as _e_draft:
                            pass  # El auto-guardado nunca debe interrumpir el flujo
                    # ══════════════════════════════════════════════════════

                except (AttributeError, TypeError) as e:
                    # Guardar mensaje de error en session_state
                    st.session_state.item_agregado_msg = f"⚠️ Error: {str(e)}. Reiniciando lista..."
                    st.session_state.cotizacion_items = [nuevo_item]
                    st.session_state.limpiar_campos_item = True
                st.rerun()
    
    with btn_action_col2:
        # Cuando el analista está editando un ítem individual (editing_item=True),
        # el botón ACTUALIZAR ÍTEM ya guarda automáticamente en BD.
        # En ese caso, ocultamos GUARDAR CAMBIOS para evitar redundancia y confusión.
        if editing_item:
            # Mostrar un placeholder informativo en lugar del botón
            st.info("💡 Haz clic en **ACTUALIZAR ÍTEM** para guardar los cambios automáticamente.")
        else:
            # Cambiar texto del botón según si se está editando la cotización completa
            if editing_mode:
                final_button_text = "💾 GUARDAR CAMBIOS"
                final_button_key = "btn_guardar_cambios"
            else:
                final_button_text = "📄 GENERAR COTIZACIÓN"
                final_button_key = "btn_generar_cotizacion"
            
            # En modo edición el botón es "secondary" (gris) para diferenciarlo visualmente
            # del flujo normal de crear cotización (rojo/primary)
            final_button_type = "secondary" if editing_mode else "primary"
            if st.button(final_button_text, use_container_width=True, type=final_button_type, key=final_button_key):
                # Validar datos del cliente
                if not cliente_nombre:
                    st.error("⚠️ Ingrese el nombre del cliente")
                elif not cliente_vehiculo:
                    st.error("⚠️ Ingrese el vehículo")
                elif not item_descripcion and len(st.session_state.cotizacion_items) == 0:
                    st.error("⚠️ Agregue al menos un ítem")
                else:
                    # Si hay un ítem en el formulario actual, agregarlo
                    # ── Determinar si el formulario tiene un ítem pendiente ──────────
                    # En modo edición de cotización (editing_mode), si el formulario
                    # tiene datos Y hay exactamente 1 ítem cargado que corresponde al
                    # ítem original, NO se agrega como nuevo — se reemplaza en su posición.
                    _formulario_tiene_item = bool(item_descripcion and costo_fob > 0)
                    _editing_item_idx_activo = st.session_state.get('editing_item_index', None)

                    if _formulario_tiene_item:
                        # Obtener links de forma segura - variable independiente
                        _lnks2 = st.session_state.get('item_links', [])
                        if not isinstance(_lnks2, list):
                            _lnks2 = []
                        # Auto-capturar link pendiente en el campo de texto
                        _pending_link_key2 = f"new_link_input_{reset_key}_{st.session_state.get('link_counter', 0)}"
                        _pending_link2 = st.session_state.get(_pending_link_key2, '').strip()
                        if _pending_link2 and _pending_link2 != 'https://':
                            _existing_urls2 = [_link_url(l) for l in _lnks2]
                            if _pending_link2 not in _existing_urls2:
                                _pending_qty_key2 = f"new_link_qty_{reset_key}_{st.session_state.get('link_counter', 0)}"
                                _pending_qty2 = st.session_state.get(_pending_qty_key2, 1)
                                _lnks2 = list(_lnks2) + [{'url': _pending_link2, 'qty': _pending_qty2}]
                        _lnks2_json = json.dumps(_lnks2)
                        
                        nuevo_item = {
                            "descripcion": item_descripcion,
                            "parte": item_parte,
                            "marca": item_marca,
                            "garantia": item_garantia,
                            "cantidad": item_cantidad,
                            "origen": item_origen,
                            "envio_tipo": item_envio_tipo,
                            "tiempo_entrega": item_tiempo,
                            "fabricacion": item_fabricacion,
                            "link": _lnks2_json,
                            "costo_fob": costo_fob,
                            "costo_handling": costo_handling,
                            "costo_manejo": costo_manejo,
                            "costo_impuesto": costo_impuesto_total,
                            "impuesto_porcentaje": impuesto_porcentaje,
                            "factor_utilidad": factor_utilidad,
                            "utilidad_valor": utilidad_total,
                            "costo_envio": costo_envio,
                            "costo_tax": costo_tax_total,
                            "tax_porcentaje": tax_porcentaje,
                            "diferencial_valor": diferencial_total,
                            "diferencial_porcentaje": diferencial_porcentaje,
                            "aplicar_iva": aplicar_iva == "SÍ",
                            "iva_porcentaje": iva_porcentaje,
                            "iva_valor": iva_total,
                            "precio_usd": precio_usd_total,
                            "precio_bs": precio_bs_total,
                            "costo_unitario": precio_usd,
                            "costo_total": costo_total_usd,
                            "fob_total": fob_total,
                            "costo_total_bs": costo_total_bs
                        }
                        # ── Inserción inteligente: actualizar o agregar según contexto ──
                        if not isinstance(st.session_state.cotizacion_items, list):
                            st.session_state.cotizacion_items = []

                        if _editing_item_idx_activo is not None:
                            # Estaba editando un ítem específico → reemplazarlo en su posición
                            st.session_state.cotizacion_items[_editing_item_idx_activo] = nuevo_item
                            if 'editing_item_index' in st.session_state:
                                del st.session_state['editing_item_index']
                            if 'editing_item_data' in st.session_state:
                                del st.session_state['editing_item_data']
                        elif editing_mode:
                            # Modo edición de cotización completa (no de ítem individual):
                            # El formulario tiene el ítem original cargado.
                            # Si la descripción del formulario coincide con alguno ya en la
                            # lista, reemplazarlo. Si no coincide, es un ítem genuinamente nuevo.
                            _idx_coincide = None
                            for _ci, _existing in enumerate(st.session_state.cotizacion_items):
                                _desc_existing = _existing.get('descripcion', '') or _existing.get('description', '')
                                _parte_existing = _existing.get('parte', '') or _existing.get('part_number', '')
                                if _desc_existing == item_descripcion and _parte_existing == item_parte:
                                    _idx_coincide = _ci
                                    break
                            if _idx_coincide is not None:
                                # Reemplazar el ítem coincidente con los datos actualizados
                                st.session_state.cotizacion_items[_idx_coincide] = nuevo_item
                            else:
                                # Es un ítem genuinamente nuevo — agregarlo
                                st.session_state.cotizacion_items.append(nuevo_item)
                        else:
                            # Modo creación normal → siempre agregar
                            st.session_state.cotizacion_items.append(nuevo_item)

                    # Guardar datos del cliente limpiando caracteres de control
                    def _clean(v):
                        if v is None:
                            return ''
                        return ''.join(
                            ch for ch in str(v)
                            if unicodedata.category(ch) not in ('Cc', 'Cf') and ord(ch) >= 32
                        ).strip()

                    st.session_state.cliente_datos = {
                        "nombre":    _clean(cliente_nombre),
                        "telefono":  _clean(cliente_telefono),
                        "email":     _clean(cliente_email),
                        "vehiculo":  _clean(cliente_vehiculo),
                        "cilindrada":_clean(cliente_cilindrada),
                        "ano":       _clean(cliente_ano),
                        "vin":       _clean(cliente_vin),
                        "direccion": _clean(cliente_direccion),
                        "ci_rif":    _clean(cliente_ci_rif)
                    }

                    # ── GUARDAR / ACTUALIZAR CLIENTE EN BD ────────────────────────
                    # Solo si el nombre es real (letras, no números ni alias)
                    try:
                        _resultado_cliente = guardar_o_actualizar(st.session_state.cliente_datos)
                        if _resultado_cliente['accion'] == 'creado':
                            print(f"✅ Cliente nuevo registrado: {st.session_state.cliente_datos.get('nombre')}")
                        elif _resultado_cliente['accion'] == 'actualizado':
                            print(f"✅ Cliente actualizado: {st.session_state.cliente_datos.get('nombre')}")
                    except Exception as _e_cli:
                        print(f"⚠️ No se pudo guardar cliente en BD: {_e_cli}")
                    # ──────────────────────────────────────────────────────────────

                    # Si estamos en modo edición, actualizar en BD
                    if editing_mode:
                        editing_quote_id = st.session_state.get('editing_quote_id')
                        if editing_quote_id:
                            # Actualizar cotización completa en BD
                            _username_save = username or st.session_state.get('username', 'admin')
                            success = DBManager.update_quote_complete(
                                quote_id=editing_quote_id,
                                cliente_datos=st.session_state.cliente_datos,
                                items=st.session_state.cotizacion_items,
                                username=_username_save
                            )
                            
                            if success:
                                st.success("✅ Cotización actualizada correctamente en la base de datos")
                                # Capturar número e ID ANTES de limpiar el session_state
                                _saved_quote_number = st.session_state.get('editing_quote_number', '')
                                _saved_quote_id     = editing_quote_id
                                # ── LIMPIEZA COMPLETA DE LA PIZARRA ──────────────────────────────
                                # Borrar TODOS los datos residuales del session_state para evitar
                                # que queden en memoria y se conviertan en una cotización nueva
                                # en una sesión posterior (bug de cotización fantasma).
                                _keys_limpiar_edicion = [
                                    'editing_mode', 'editing_quote_id', 'editing_quote_number',
                                    'editing_quote_data', 'editing_data_loaded',
                                    'editing_item_index', 'editing_item_data',
                                    'cotizacion_items', 'cliente_datos',
                                    'item_links', 'limpiar_campos_item',
                                    'mostrar_cotizacion', 'cotizacion_guardada',
                                    'show_save_success', 'saved_quote_number', 'saved_quote_id',
                                    'guardando_en_progreso',
                                ]
                                for _k in _keys_limpiar_edicion:
                                    if _k in st.session_state:
                                        del st.session_state[_k]
                                # Reinicializar listas vacías para evitar errores en el próximo render
                                st.session_state.cotizacion_items = []
                                st.session_state.cliente_datos = {}
                                st.session_state.item_links = []
                                # Incrementar contadores de reset para limpiar los widgets del formulario
                                st.session_state.cliente_reset_counter = st.session_state.get('cliente_reset_counter', 0) + 1
                                st.session_state.item_reset_counter = st.session_state.get('item_reset_counter', 0) + 1
                                # ─────────────────────────────────────────────────────────────────
                                # Redirigir a Mis Cotizaciones con la orden ya expandida
                                # El flag mq_auto_open le dice a Mis Cotizaciones que abra
                                # automáticamente esa orden sin que el usuario tenga que buscarla.
                                st.session_state.mq_auto_open_quote_number = _saved_quote_number
                                st.session_state.mq_auto_open_quote_id     = _saved_quote_id
                                st.session_state.selected_panel = "Mis Cotizaciones"
                                st.rerun()
                            else:
                                st.error("❌ Error al actualizar la cotización en la base de datos")
                    else:
                        # Modo creación normal
                        # Activar la vista previa de cotización en el mismo render
                        st.session_state.mostrar_cotizacion = True
                        # No necesita st.rerun(): el flag se lee más abajo en el mismo render
    
    with btn_action_col3:
        if st.button("🗑️ LIMPIAR TODO", use_container_width=True, key="btn_limpiar_todo"):
            st.session_state.cotizacion_items = []
            st.session_state.cliente_datos = {}
            if 'mostrar_cotizacion' in st.session_state:
                del st.session_state.mostrar_cotizacion
            # Incrementar reset_key para que los widgets del formulario se limpien visualmente
            st.session_state.cliente_reset_counter = st.session_state.get('cliente_reset_counter', 0) + 1
            st.session_state.item_reset_counter = st.session_state.get('item_reset_counter', 0) + 1
            # No necesita st.rerun(): el cambio de key ya fuerza el re-render de los widgets
    
    # ==========================================
    # SECCIÓN 7: RESUMEN DE ÍTEMS AGREGADOS
    # ==========================================
    if isinstance(st.session_state.cotizacion_items, list) and len(st.session_state.cotizacion_items) > 0:
        st.markdown("---")
        st.markdown("### 📋 Ítems Agregados")
        
        total_general_usd = 0
        total_general_bs = 0
        for i, item in enumerate(st.session_state.cotizacion_items):
            with st.expander(f"Ítem #{i+1}: {item['descripcion']}", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**N° Parte:** {item['parte']}")
                    st.write(f"**Marca:** {item['marca']}")
                    st.write(f"**Cantidad:** {item['cantidad']}")
                with col2:
                    st.write(f"**Origen:** {item['origen']}")
                    st.write(f"**Fabricación:** {item['fabricacion']}")
                    st.write(f"**Envío:** {item['envio_tipo']}")
                with col3:
                    # Manejar valores None o strings en precios
                    precio_usd = item.get('precio_usd', item.get('costo_unitario', 0))
                    precio_bs = item.get('precio_bs', item.get('costo_total', 0))
                    total_usd = item.get('costo_total', 0)
                    
                    # Convertir a float si es necesario
                    try:
                        precio_usd = float(precio_usd) if precio_usd else 0.0
                    except (ValueError, TypeError):
                        precio_usd = 0.0
                    
                    try:
                        precio_bs = float(precio_bs) if precio_bs else 0.0
                    except (ValueError, TypeError):
                        precio_bs = 0.0
                    
                    try:
                        total_usd = float(total_usd) if total_usd else 0.0
                    except (ValueError, TypeError):
                        total_usd = 0.0
                    
                    st.write(f"**💵 Precio USD:** ${precio_usd:.2f}")
                    st.write(f"**🇻🇪 Precio Bs:** ${precio_bs:.2f}")
                    st.write(f"**Total USD:** ${total_usd:.2f}")
                
                # Botón para eliminar ítem
                if st.button(f"🗑️ Eliminar Ítem #{i+1}", key=f"del_item_{i}"):
                    st.session_state.cotizacion_items.pop(i)
                    st.rerun()
            
            # Manejar valores None o strings en totales
            try:
                total_general_usd += float(item.get('costo_total', 0)) if item.get('costo_total') else 0.0
            except (ValueError, TypeError):
                total_general_usd += 0.0
            
            try:
                total_bs_item = item.get('costo_total_bs', item.get('costo_total', 0))
                total_general_bs += float(total_bs_item) if total_bs_item else 0.0
            except (ValueError, TypeError):
                total_general_bs += 0.0
        
        st.markdown("---")
        st.success(f"**💵 TOTAL USD: ${total_general_usd:.2f}** | **🇻🇪 TOTAL Bs: ${total_general_bs:.2f}**")
    
    # ==========================================
    # SECCIÓN 8: VISTA PREVIA DE COTIZACIÓN
    # ==========================================
    if st.session_state.get('mostrar_cotizacion', False) and len(st.session_state.cotizacion_items) > 0:
        st.markdown("---")
        st.markdown("## 📄 Vista Previa de Cotización")
        
        # Mostrar información de la cotización
        quote_info_col1, quote_info_col2, quote_info_col3 = st.columns(3)
        with quote_info_col1:
            st.info(f"🔢 **Cotización:** {next_quote_number}")
        with quote_info_col2:
            st.info(f"👤 **Analista:** {full_name}")
        with quote_info_col3:
            fecha_actual = now_caracas_naive().strftime("%d/%m/%Y")
            st.info(f"📅 **Fecha:** {fecha_actual}")
        
        st.markdown("---")
        
        cliente = st.session_state.cliente_datos
        items = st.session_state.cotizacion_items
        
        # Información del cliente (solo mostrar campos con datos)
        cliente_info = []
        if cliente.get('nombre'):
            cliente_info.append(f"**Cliente:** {cliente.get('nombre')}")
        if cliente.get('ci_rif'):
            cliente_info.append(f"**C.I./RIF:** {cliente.get('ci_rif')}")
        if cliente.get('telefono'):
            cliente_info.append(f"**Teléfono:** {cliente.get('telefono')}")
        if cliente.get('email'):
            cliente_info.append(f"**Email:** {cliente.get('email')}")
        if cliente.get('direccion'):
            cliente_info.append(f"**Dirección:** {cliente.get('direccion')}")
        vehiculo_str = cliente.get('vehiculo', '')
        if cliente.get('ano'):
            vehiculo_str += f" {cliente.get('ano')}"
        if vehiculo_str:
            cliente_info.append(f"**Vehículo:** {vehiculo_str}")
        if cliente.get('vin'):
            cliente_info.append(f"**VIN:** {cliente.get('vin')}")
        
        st.markdown("  \n".join(cliente_info))
        
        st.markdown("---")
        
        # Tabla de ítems
        total_cotizacion_usd = 0
        total_cotizacion_bs = 0
        hay_iva = False
        for i, item in enumerate(items):
            st.markdown(f"**Ítem #{i+1}:** {item['descripcion']}")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"N° Parte: {item['parte']}")
                st.write(f"Marca: {item['marca']}")
            with col2:
                st.write(f"Cantidad: {item['cantidad']}")
                st.write(f"Garantía: {item['garantia']}")
            with col3:
                st.write(f"Origen: {item['origen']}")
                st.write(f"Entrega: {item['tiempo_entrega']}")
            with col4:
                st.write(f"**💵 USD: ${item.get('precio_usd', item['costo_unitario']):.2f}**")
                # Mostrar si tiene IVA
                if item.get('aplicar_iva', False):
                    hay_iva = True
                    st.write(f"**🇻🇪 Bs (con IVA): ${item.get('precio_bs', item['costo_total']):.2f}**")
                else:
                    st.write(f"**🇻🇪 Bs: ${item.get('precio_bs', item['costo_total']):.2f}**")
            
            total_cotizacion_usd += item['costo_total']
            total_cotizacion_bs += item.get('costo_total_bs', item['costo_total'])
            st.markdown("---")
        
        # Calcular totales correctos
        # IMPORTANTE: Los valores ya vienen calculados con cantidad desde el ítem
        sub_total = 0
        iva_total = 0
        abona_ya = 0
        total_usd_divisas = 0
        usd_abono = 0
        
        for item in items:
            cantidad = item.get('cantidad', 1)
            
            # Sub-Total = TODOS los costos (FOB + Handling + Manejo + Imp.Int + Utilidad + Envío + TAX + Diferencial)
            # Es decir, el precio completo SIN IVA
            sub_total_item = (
                item.get('fob_total', 0) +
                item.get('costo_handling', 0) +
                item.get('costo_manejo', 0) +
                item.get('costo_impuesto', 0) +
                item.get('utilidad_valor', 0) +
                item.get('costo_envio', 0) +
                item.get('costo_tax', 0) +
                item.get('diferencial_valor', 0)
            )
            sub_total += sub_total_item
            
            # IVA - YA VIENE CALCULADO CON CANTIDAD
            if item.get('aplicar_iva', False):
                iva_total += item.get('iva_valor', 0)
            
            # Abona Ya = (costos base SIN envío ni diferencial) × (1 + diferencial%)
            # Según Excel: P34 = (Z29+AA29+AB29+AC29+AD29+AF29) + (Z30+AA30+AB30+AC30+AD30+AF30)
            # Donde fila 30 = fila 29 × Y30 (factor diferencial)
            costos_base_item = (
                item.get('fob_total', 0) +
                item.get('costo_handling', 0) +
                item.get('costo_manejo', 0) +
                item.get('costo_impuesto', 0) +
                item.get('utilidad_valor', 0) +
                item.get('costo_tax', 0)
            )
            # Multiplicar por (1 + diferencial%) para obtener Abona Ya
            diferencial_factor = item.get('diferencial_porcentaje', 0) / 100
            abona_item = costos_base_item * (1 + diferencial_factor)
            abona_ya += abona_item
            
            # Total USD Divisas (costos base CON envío) - YA VIENEN CALCULADOS CON CANTIDAD
            total_usd_item = (
                item.get('fob_total', 0) +
                item.get('costo_handling', 0) +
                item.get('costo_manejo', 0) +
                item.get('costo_impuesto', 0) +
                item.get('utilidad_valor', 0) +
                item.get('costo_envio', 0) +
                item.get('costo_tax', 0)
            )
            total_usd_divisas += total_usd_item
            
            # USD Abono = costos base SIN envío ni TAX (lo que se cobra por adelantado en USD)
            # USD Entrega = Envío + TAX (lo que se cobra al momento de la entrega en USD)
            usd_abono_item = (
                item.get('fob_total', 0) +
                item.get('costo_handling', 0) +
                item.get('costo_manejo', 0) +
                item.get('costo_impuesto', 0) +
                item.get('utilidad_valor', 0)
            )
            usd_abono += usd_abono_item
        
        # Total a Pagar
        total_a_pagar = sub_total + iva_total
        
        # Y en la Entrega (Bs)
        y_en_entrega = total_a_pagar - abona_ya
        
        # Y en la Entrega USD = Total USD - USD Abono (equivale a Envío + TAX de todos los ítems)
        usd_entrega = total_usd_divisas - usd_abono
        
        # Mostrar totales
        st.markdown("### 📊 Totales de la Cotización")
        
        total_col1, total_col2, total_col3 = st.columns(3)
        with total_col1:
            st.metric("Sub-Total", f"${sub_total:.2f}")
            st.metric("I.V.A. 16%", f"${iva_total:.2f}")
            st.metric("Total a Pagar", f"${total_a_pagar:.2f}")
        with total_col2:
            st.metric("Abona Ya", f"${abona_ya:.2f}")
            st.metric("Y en la Entrega", f"${y_en_entrega:.2f}")
        with total_col3:
            st.info(f"💵 **Total si paga en USD/Divisas:**\n\n${total_usd_divisas:.2f}")
            st.caption("⚠️ Este monto NO aparece en el PDF. Comunícalo al cliente por mensaje aparte.")
            
            # ── BOTONES POP-UP MENSAJE PAGO USD y BCV ────────────────────
            # Solo visibles después de guardar la cotización exitosamente
            if items and len(items) > 0 and st.session_state.get('cotizacion_guardada', False):
                if st.button("📋 Copiar Mensaje Pago USD", use_container_width=True, type="secondary", key="btn_popup_usd"):
                    st.session_state['mostrar_popup_usd'] = not st.session_state.get('mostrar_popup_usd', False)
                    st.session_state['mostrar_popup_bcv'] = False
                if st.button("📋 Copiar Mensaje BCV", use_container_width=True, type="secondary", key="btn_popup_bcv"):
                    st.session_state['mostrar_popup_bcv'] = not st.session_state.get('mostrar_popup_bcv', False)
                    st.session_state['mostrar_popup_usd'] = False
        
        # ── POP-UP MENSAJE PAGO USD ────────────────────────────────────────────────
        if st.session_state.get('mostrar_popup_usd', False) and items and len(items) > 0:
            st.markdown("---")
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                            border: 2px solid #00d4aa;
                            border-radius: 16px;
                            padding: 24px;
                            margin: 8px 0;">
                    <h3 style="color: #00d4aa; text-align: center; margin-bottom: 16px; font-size: 1.1rem;">
                        📲 Mensaje listo para WhatsApp / Instagram
                    </h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Texto del mensaje completo
                mensaje_usd = f"""✨ ¡Optimiza tu compra con nosotros! ✨

💡 ¿Sabías que al realizar tu pago en divisas, puedes acceder a un beneficio especial en el valor total de tus repuestos? Es nuestra forma de recompensar tu confianza y compromiso. 🙌

🔑 Esta opción te brinda la oportunidad de asegurar tus piezas con una ventaja adicional, manteniendo la transparencia y responsabilidad que nos caracterizan.

📋 Si decides aprovechar esta facilidad, tu presupuesto quedaría en:

━━━━━━━━━━━━━━━━━━━━
💵 *Total a Pagar en USD:*  ${total_usd_divisas:.2f}
✅ *Monto a Abonar:*         ${usd_abono:.2f}
🚚 *Y en la Entrega:*        ${usd_entrega:.2f}
━━━━━━━━━━━━━━━━━━━━

💳 *Formas de pago que te ofrecemos:*
Cash | Zelle | Binance | Depósito Bancario Cta Divisas 🤝"""
                
                # Mostrar el mensaje en un text_area para fácil selección manual
                st.text_area(
                    "Mensaje generado:",
                    value=mensaje_usd,
                    height=320,
                    key="textarea_mensaje_usd",
                    help="Selecciona todo el texto y cópialo, o usa el botón de abajo."
                )
                
                # Botón copiar al portapapeles via JavaScript
                # El texto se pasa directamente al JS del iframe (no puede acceder al DOM externo)
                _texto_js = json.dumps(mensaje_usd)  # escapado seguro para JS
                copy_js = (
                    "<script>"
                    f"var _textoUSD = {_texto_js};"
                    "function copiarMensajeUSD() {"
                    "  navigator.clipboard.writeText(_textoUSD).then(function() {"
                    "    var btn = document.getElementById('copy_btn_usd');"
                    "    btn.innerHTML = '&#9989; &iexcl;Copiado!';"
                    "    btn.style.background = '#00d4aa';"
                    "    btn.style.color = '#000';"
                    "    setTimeout(function() {"
                    "      btn.innerHTML = '&#128203; Copiar al Portapapeles';"
                    "      btn.style.background = '#0f3460';"
                    "      btn.style.color = '#fff';"
                    "    }, 2500);"
                    "  }).catch(function() {"
                    "    var btn = document.getElementById('copy_btn_usd');"
                    "    btn.innerHTML = '&#9888; No se pudo copiar. Selecciona el texto manualmente (Ctrl+A, Ctrl+C)';"
                    "  });"
                    "}"
                    "</script>"
                    "<button id='copy_btn_usd' onclick='copiarMensajeUSD()'"
                    " style='width:100%;padding:12px;font-size:1rem;font-weight:bold;"
                    "background:#0f3460;color:white;border:2px solid #00d4aa;"
                    "border-radius:8px;cursor:pointer;margin-top:8px;'>"
                    "&#128203; Copiar al Portapapeles"
                    "</button>"
                )
                st.components.v1.html(copy_js, height=70)
                
                col_cerrar1, col_cerrar2, col_cerrar3 = st.columns([1, 2, 1])
                with col_cerrar2:
                    if st.button("✖ Cerrar", use_container_width=True, key="btn_cerrar_popup_usd"):
                        st.session_state['mostrar_popup_usd'] = False
                        # No necesita st.rerun(): el flag False ya oculta el popup en el próximo render natural
        # ── FIN POP-UP MENSAJE PAGO USD ────────────────────────────────────────────

        # ── POP-UP MENSAJE BCV ─────────────────────────────────────────────────
        if st.session_state.get('mostrar_popup_bcv', False) and items and len(items) > 0:
            st.markdown("---")
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(135deg, #1a2e1a 0%, #163e16 50%, #0f6030 100%);
                            border: 2px solid #00d4aa;
                            border-radius: 16px;
                            padding: 24px;
                            margin: 8px 0;">
                    <h3 style="color: #00d4aa; text-align: center; margin-bottom: 16px; font-size: 1.1rem;">
                        📲 Mensaje listo para WhatsApp / Instagram
                    </h3>
                </div>
                """, unsafe_allow_html=True)

                # Texto fijo del mensaje BCV
                mensaje_bcv = (
                    "✅ En la parte central tiene el detalle de la(s) pieza(s). "
                    "⏱️ Tiempo de entrega y garantía en VZLA.\n\n"
                    "✅ En la parte inferior derecha puede ver el costo total en sus manos a tasa BCV "
                    "💵 y la forma de pago si desea ordenarlo(s).\n\n"
                    "Estaré atento. 👀\n\n"
                    "Muchas Gracias! 😊🙌"
                )

                # Mostrar el mensaje en un text_area para visualización
                st.text_area(
                    "Mensaje generado:",
                    value=mensaje_bcv,
                    height=200,
                    key="textarea_mensaje_bcv",
                    help="Usa el botón de abajo para copiarlo al portapapeles."
                )

                # Botón copiar al portapapeles via JavaScript (texto incrustado en el iframe)
                _texto_bcv_js = json.dumps(mensaje_bcv)
                copy_js_bcv = (
                    "<script>"
                    f"var _textoBCV = {_texto_bcv_js};"
                    "function copiarMensajeBCV() {"
                    "  navigator.clipboard.writeText(_textoBCV).then(function() {"
                    "    var btn = document.getElementById('copy_btn_bcv');"
                    "    btn.innerHTML = '&#9989; &iexcl;Copiado!';"
                    "    btn.style.background = '#00d4aa';"
                    "    btn.style.color = '#000';"
                    "    setTimeout(function() {"
                    "      btn.innerHTML = '&#128203; Copiar al Portapapeles';"
                    "      btn.style.background = '#0f6030';"
                    "      btn.style.color = '#fff';"
                    "    }, 2500);"
                    "  }).catch(function() {"
                    "    var btn = document.getElementById('copy_btn_bcv');"
                    "    btn.innerHTML = '&#9888; No se pudo copiar. Selecciona el texto manualmente (Ctrl+A, Ctrl+C)';"
                    "  });"
                    "}"
                    "</script>"
                    "<button id='copy_btn_bcv' onclick='copiarMensajeBCV()'"
                    " style='width:100%;padding:12px;font-size:1rem;font-weight:bold;"
                    "background:#0f6030;color:white;border:2px solid #00d4aa;"
                    "border-radius:8px;cursor:pointer;margin-top:8px;'>"
                    "&#128203; Copiar al Portapapeles"
                    "</button>"
                )
                st.components.v1.html(copy_js_bcv, height=70)

                col_cerrar_bcv1, col_cerrar_bcv2, col_cerrar_bcv3 = st.columns([1, 2, 1])
                with col_cerrar_bcv2:
                    if st.button("❖ Cerrar", use_container_width=True, key="btn_cerrar_popup_bcv"):
                        st.session_state['mostrar_popup_bcv'] = False
                        # No necesita st.rerun(): el flag False ya oculta el popup en el próximo render natural
        # ── FIN POP-UP MENSAJE BCV ─────────────────────────────────────────────────
        
        # Botones de generación
        gen_col1, gen_col2, gen_col3 = st.columns(3)
        with gen_col1:
            # Cambiar botón según modo
            button_label = "🔄 ACTUALIZAR COTIZACIÓN" if editing_mode else "💾 GUARDAR COTIZACIÓN"

            # ── PROTECCIÓN ANTI-DUPLICADO ───────────────────────────────────────────
            # El botón se deshabilita si:
            # a) Ya se guardó exitosamente (cotizacion_guardada = True)
            # b) Está en proceso de guardado (guardando_en_progreso = True)
            # Esto impide que un doble clic accidental cree cotizaciones duplicadas.
            _ya_guardada = st.session_state.get('cotizacion_guardada', False)
            _guardando   = st.session_state.get('guardando_en_progreso', False)
            _btn_disabled = (_ya_guardada or _guardando) and not editing_mode

            # Determinar si hay copia sin cambios (para bloquear el botón)
            _copying_mode_active = st.session_state.get('copying_mode', False)
            _copy_sin_cambios = False
            if _copying_mode_active:
                _original_snap = st.session_state.get('copying_original_items_snapshot', [])
                _current_items = st.session_state.get('cotizacion_items', [])
                def _items_son_iguales(orig, curr):
                    if len(orig) != len(curr):
                        return False
                    for o, c in zip(orig, curr):
                        if (str(o.get('descripcion','')) != str(c.get('descripcion','')) or
                            str(o.get('parte',''))       != str(c.get('parte',''))       or
                            str(o.get('marca',''))       != str(c.get('marca',''))       or
                            float(o.get('costo_fob',0))  != float(c.get('costo_fob',0))  or
                            int(o.get('cantidad',1))     != int(c.get('cantidad',1))):
                            return False
                    return True
                _copy_sin_cambios = _items_son_iguales(_original_snap, _current_items)

            # Determinar label y estado del botón (UN SOLO render con una sola key)
            if _btn_disabled:
                _guardar_label    = "✅ COTIZACIÓN GUARDADA" if _ya_guardada else "⏳ Guardando..."
                _guardar_disabled = True
            elif _copy_sin_cambios:
                _guardar_label    = "📋 COPIA SIN CAMBIOS — Modifica al menos un ítem"
                _guardar_disabled = True
            else:
                _guardar_label    = button_label
                _guardar_disabled = False

            if _copy_sin_cambios and not _btn_disabled:
                st.warning("⚠️ Esta cotización es idéntica a la original **#" +
                           st.session_state.get('copying_from_number','') +
                           "**. Debes modificar al menos un ítem (descripción, parte, marca, precio o cantidad) antes de poder guardar.")

            _guardar_clicked = st.button(
                _guardar_label,
                use_container_width=True,
                type="primary",
                key="btn_guardar_cotizacion",
                disabled=_guardar_disabled
            )
            if _guardar_clicked and not _guardar_disabled:
                # Activar flag anti-duplicado INMEDIATAMENTE al primer clic
                if not editing_mode:
                    st.session_state.guardando_en_progreso = True
                # Validar que haya ítems
                if not items or len(items) == 0:
                    st.session_state.guardando_en_progreso = False  # Liberar si hay error
                    st.error("❌ Debes agregar al menos un ítem para guardar la cotización")
                elif editing_mode and editing_quote_id:
                    # MODO EDICIÓN: Actualizar cotización existente
                    try:
                        # Preparar datos del cliente
                        cliente = st.session_state.get('cliente_datos', {})
                        
                        # Validar que las variables de totales existan
                        if 'total_cotizacion_bs' not in locals():
                            st.error("❌ Error: No se pudieron calcular los totales. Por favor, recarga la página.")
                        else:
                            print(f"📊 DEBUG - Actualizando cotización {editing_quote_number}")
                            print(f"📊 DEBUG - Total BS: {total_cotizacion_bs}")
                            print(f"📊 DEBUG - Ítems: {len(items)}")
                            
                            # Preparar datos de la cotización para actualizar
                            quote_data = {
                                'client_name': cliente.get('nombre', ''),
                                'client_phone': cliente.get('telefono', ''),
                                'client_email': cliente.get('email', ''),
                                'client_cedula': cliente.get('ci_rif', ''),
                                'client_address': cliente.get('direccion', ''),
                                'client_vehicle': f"{cliente.get('vehiculo', '')} {cliente.get('cilindrada', '')}".strip(),
                                'client_year': cliente.get('ano', ''),
                                'client_vin': cliente.get('vin', ''),
                                'total_amount': total_cotizacion_usd,  # USD real para el Dashboard
                                'sub_total': sub_total,
                                'iva_total': iva_total,
                                'abona_ya': abona_ya,
                                'en_entrega': y_en_entrega,
                                'terms_conditions': config.get('terms_conditions', ''),
                                'pdf_path': '',  # Se actualizará cuando se regenere el PDF
                                'jpeg_path': ''  # Se actualizará cuando se regenere el PNG
                            }
                            
                            print(f"📊 DEBUG - Llamando a DBManager.update_quote()...")
                            # Actualizar cotización en base de datos
                            success = DBManager.update_quote(editing_quote_id, quote_data, user_id)
                            print(f"📊 DEBUG - Resultado update_quote: {success}")
                            
                            if success:
                                print(f"📊 DEBUG - Actualizando {len(items)} ítems...")
                                # Actualizar ítems de la cotización
                                items_actualizados = DBManager.update_quote_items(editing_quote_id, items, user_id)
                                print(f"📊 DEBUG - Resultado update_quote_items: {items_actualizados}")
                                
                                if items_actualizados:
                                    # Capturar número e ID ANTES de limpiar el session_state
                                    _saved_qnum2 = editing_quote_number
                                    _saved_qid2  = editing_quote_id
                                    # Limpiar modo edición
                                    st.session_state.editing_mode = False
                                    st.session_state.editing_quote_id = None
                                    st.session_state.editing_quote_number = None
                                    st.session_state.editing_quote_data = None
                                    st.session_state.editing_data_loaded = False
                                    st.session_state.cotizacion_items = []
                                    st.session_state.cliente_datos = {}
                                    st.session_state.cotizacion_aplica_iva = False  # Resetear IVA a NO
                                    
                                    print(f"✅ DEBUG - Cotización actualizada exitosamente: {_saved_qnum2}")
                                    
                                    # Registrar actividad
                                    DBManager.log_activity(
                                        user_id,
                                        'quote_updated',
                                        f'Cotización {_saved_qnum2} actualizada con {len(items)} ítems'
                                    )
                                    
                                    # Redirigir a Mis Cotizaciones con la orden ya expandida
                                    st.session_state.mq_auto_open_quote_number = _saved_qnum2
                                    st.session_state.mq_auto_open_quote_id     = _saved_qid2
                                    st.session_state.selected_panel = "Mis Cotizaciones"
                                    st.rerun()
                                else:
                                    st.error("❌ Error al actualizar ítems de la cotización. Revisa los logs para más detalles.")
                            else:
                                st.error("❌ Error al actualizar cotización en base de datos. Revisa los logs para más detalles.")
                    
                    except Exception as e:
                        st.error(f"❌ Error al actualizar cotización: {str(e)}")
                        print(f"❌ DEBUG - Excepción al actualizar: {str(e)}")
                        traceback.print_exc()
                else:
                    # MODO NORMAL: Crear nueva cotización
                    # Generar número de cotización definitivo
                    final_quote_number = QuoteNumberingService.generate_quote_number(user_id, username)
                    
                    if final_quote_number:
                        try:
                            # Preparar datos del cliente
                            cliente = st.session_state.get('cliente_datos', {})
                            
                            # Validar que las variables de totales existan
                            if 'total_cotizacion_bs' not in locals():
                                st.error("❌ Error: No se pudieron calcular los totales. Por favor, recarga la página.")
                            else:
                                print(f"📊 DEBUG - Guardando cotización {final_quote_number}")
                                print(f"📊 DEBUG - Total BS: {total_cotizacion_bs}")
                                print(f"📊 DEBUG - Subtotal: {sub_total}")
                                print(f"📊 DEBUG - IVA: {iva_total}")
                                print(f"📊 DEBUG - Ítems: {len(items)}")
                                
                                # Preparar datos de la cotización para guardar
                                quote_data = {
                                    'quote_number': final_quote_number,
                                    'analyst_id': user_id,
                                    'client_name': cliente.get('nombre', ''),
                                    'client_phone': cliente.get('telefono', ''),
                                    'client_email': cliente.get('email', ''),
                                    'client_cedula': cliente.get('ci_rif', ''),
                                    'client_address': cliente.get('direccion', ''),
                                    'client_vehicle': f"{cliente.get('vehiculo', '')} {cliente.get('cilindrada', '')}".strip(),
                                    'client_year': cliente.get('ano', ''),
                                    'client_vin': cliente.get('vin', ''),
                                    'total_amount': total_cotizacion_usd,  # USD real para el Dashboard
                                    'sub_total': sub_total,
                                    'iva_total': iva_total,
                                    'abona_ya': abona_ya,
                                    'en_entrega': y_en_entrega,
                                    'terms_conditions': config.get('terms_conditions', ''),
                                    'status': 'draft',
                                    'pdf_path': '',  # Se actualizará cuando se genere el PDF
                                    'jpeg_path': ''  # Se actualizará cuando se genere el PNG
                                }
                                
                                print(f"📊 DEBUG - Llamando a DBManager.save_quote()...")
                                # Guardar cotización en base de datos
                                quote_id = DBManager.save_quote(quote_data)
                                print(f"📊 DEBUG - Resultado save_quote: {quote_id}")
                                
                                if quote_id:
                                    print(f"📊 DEBUG - Guardando {len(items)} ítems...")
                                    # Guardar ítems de la cotización
                                    items_guardados = DBManager.save_quote_items(quote_id, items)
                                    print(f"📊 DEBUG - Resultado save_quote_items: {items_guardados}")
                                    
                                    if items_guardados:
                                        # Guardar en session_state
                                        st.session_state.saved_quote_number = final_quote_number
                                        st.session_state.saved_quote_id = quote_id
                                        st.session_state.cotizacion_guardada = True
                                        st.session_state.show_save_success = True

                                        print(f"✅ DEBUG - Cotización guardada exitosamente: {final_quote_number} (ID: {quote_id})")

                                        # Registrar actividad
                                        _copy_origin = st.session_state.get('copying_from_number', '')
                                        _activity_detail = (
                                            f'Cotización {final_quote_number} creada como copia de #{_copy_origin} con {len(items)} ítems'
                                            if _copy_origin else
                                            f'Cotización {final_quote_number} creada con {len(items)} ítems'
                                        )
                                        DBManager.log_activity(user_id, 'quote_created', _activity_detail)

                                        # Registrar en auditoría si es una copia
                                        if _copy_origin:
                                            try:
                                                DBManager.log_quote_change(
                                                    quote_id=quote_id,
                                                    changed_by=username,
                                                    change_type='CREADA_COMO_COPIA',
                                                    old_data={'origen': f'Copia de #{_copy_origin}'},
                                                    new_data={'quote_number': final_quote_number, 'items': len(items)}
                                                )
                                            except Exception:
                                                pass

                                        # Limpiar modo copia del session_state
                                        for _ck in [
                                            'copying_mode', 'copying_from_quote_id', 'copying_from_number',
                                            'copying_quote_data', 'copying_data_loaded',
                                            'copying_original_items_snapshot'
                                        ]:
                                            st.session_state.pop(_ck, None)

                                        # ══ ELIMINAR BORRADOR AL GUARDAR EXITOSAMENTE ══
                                        try:
                                            if user_id:
                                                DBManager.delete_draft(user_id)
                                            # Limpiar flags de borrador
                                            for _dk in ['_pending_draft', 'draft_checked',
                                                        'draft_recovered', 'draft_discarded',
                                                        '_draft_saved_at']:
                                                st.session_state.pop(_dk, None)
                                        except Exception:
                                            pass
                                        # Invalidar caché del número de cotización para que el siguiente render muestre el nuevo número
                                        _nqn_cache_key_clear = f'_next_quote_number_cache_{user_id}'
                                        st.session_state.pop(_nqn_cache_key_clear, None)
                                        # ═══════════════════════════════════════════════

                                        st.rerun()
                                    else:
                                        st.session_state.guardando_en_progreso = False  # Liberar para reintento
                                        st.error("❌ Error al guardar ítems de la cotización. Revisa los logs para más detalles.")
                                else:
                                    st.session_state.guardando_en_progreso = False  # Liberar para reintento
                                    st.error("❌ Error al guardar cotización en base de datos. Revisa los logs para más detalles.")
                        
                        except Exception as e:
                            st.session_state.guardando_en_progreso = False  # Liberar para reintento
                            st.error(f"❌ Error al guardar cotización: {str(e)}")
                            print(f"❌ DEBUG - Excepción al guardar: {str(e)}")
                            traceback.print_exc()
                    else:
                        st.session_state.guardando_en_progreso = False  # Liberar para reintento
                        st.error("❌ Error al generar número de cotización")
        
        with gen_col2:
            # Solo mostrar el botón PDF si la cotización ya fue guardada exitosamente en BD
            if st.session_state.get('cotizacion_guardada', False) and st.button("📅 GENERAR PDF", use_container_width=True, type="secondary", key="btn_generar_pdf"):
                if st.session_state.get('saved_quote_number'):
                    try:
                        # PDFQuoteGenerator y clean_text ya importados al inicio del módulo
                        clean_text = _clean_text_gen
                        
                        # Preparar datos para PDF
                        # clean_text elimina caracteres de control y espacios Unicode especiales
                        # (U+00A0, U+2002-U+200A, U+202F, etc.) que WhatsApp/celular insertan
                        # al copiar números de teléfono y que ReportLab muestra como cuadros negros
                        cliente = st.session_state.get('cliente_datos', {})
                        quote_data = {
                            'quote_number': st.session_state.saved_quote_number,
                            'analyst_name': st.session_state.full_name,
                            'client': {
                                'nombre': clean_text(cliente.get('nombre', '')),
                                'telefono': clean_text(cliente.get('telefono', '')),
                                'email': clean_text(cliente.get('email', '')),
                                'vehiculo': clean_text(cliente.get('vehiculo', '')),
                                'motor': clean_text(cliente.get('cilindrada', '')),
                                'año': clean_text(cliente.get('ano', '')),
                                'vin': clean_text(cliente.get('vin', '')),
                                'direccion': clean_text(cliente.get('direccion', '')),
                                'ci_rif': clean_text(cliente.get('ci_rif', ''))
                            },
                            'items': items,
                            'sub_total': sub_total,
                            'iva_total': iva_total,
                            'total_a_pagar': total_a_pagar,
                            'abona_ya': abona_ya,
                            'y_en_entrega': y_en_entrega,
                            'total_usd': total_cotizacion_usd,
                            'total_bs': total_cotizacion_bs,
                            'terminos_condiciones': config.get('terms_conditions', 'Términos y condiciones estándar.')
                        }
                        
                        # Generar PDF en carpeta permanente
                        # Crear estructura de carpetas: /home/ubuntu/cotizaciones_guardadas/YYYY/MM/
                        now = now_caracas_naive()
                        year = now.strftime("%Y")
                        month = now.strftime("%m")
                        
                        output_dir = f'/home/ubuntu/cotizaciones_guardadas/{year}/{month}'
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Ruta completa del archivo PDF
                        pdf_filename = f"cotizacion_{st.session_state.saved_quote_number}.pdf"
                        pdf_path = f"{output_dir}/{pdf_filename}"
                        
                        result = PDFQuoteGenerator.generate(quote_data, pdf_path)
                        
                        if result:
                            # Actualizar ruta del PDF en la base de datos
                            if st.session_state.get('saved_quote_id'):
                                conn = DBManager.get_connection()
                                cursor = conn.cursor()
                                is_postgres = DBManager.USE_POSTGRES
                                
                                if is_postgres:
                                    cursor.execute("""
                                        UPDATE quotes SET pdf_path = %s WHERE id = %s
                                    """, (pdf_path, st.session_state.saved_quote_id))
                                else:
                                    cursor.execute("""
                                        UPDATE quotes SET pdf_path = ? WHERE id = ?
                                    """, (pdf_path, st.session_state.saved_quote_id))
                                
                                conn.commit()
                                cursor.close()
                                conn.close()
                            
                            # Ofrecer descarga
                            with open(pdf_path, 'rb') as f:
                                st.download_button(
                                    label="📅 Descargar PDF",
                                    data=f,
                                    file_name=pdf_filename,
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            st.success(f"✅ PDF generado y guardado en: {pdf_path}")
                        else:
                            st.error("❌ Error al generar PDF")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ Primero debe guardar la cotización")
        
        with gen_col3:
            # Solo mostrar el botón PNG si la cotización ya fue guardada exitosamente en BD
            if st.session_state.get('cotizacion_guardada', False) and st.button("🖼️ GENERAR PNG", use_container_width=True, type="secondary", key="btn_generar_png"):
                if st.session_state.get('saved_quote_number'):
                    try:
                        # PNGQuoteGenerator y clean_text ya importados al inicio del módulo
                        clean_text = _clean_text_gen
                        
                        # Preparar datos para PNG
                        # clean_text elimina caracteres de control y espacios Unicode especiales
                        cliente = st.session_state.get('cliente_datos', {})
                        quote_data = {
                            'quote_number': st.session_state.saved_quote_number,
                            'analyst_name': st.session_state.full_name,
                            'client': {
                                'nombre': clean_text(cliente.get('nombre', '')),
                                'telefono': clean_text(cliente.get('telefono', '')),
                                'email': clean_text(cliente.get('email', '')),
                                'vehiculo': clean_text(cliente.get('vehiculo', '')),
                                'motor': clean_text(cliente.get('cilindrada', '')),
                                'año': clean_text(cliente.get('ano', '')),
                                'vin': clean_text(cliente.get('vin', '')),
                                'direccion': clean_text(cliente.get('direccion', '')),
                                'ci_rif': clean_text(cliente.get('ci_rif', ''))
                            },
                            'items': items,
                            'sub_total': sub_total,
                            'iva_total': iva_total,
                            'total_a_pagar': total_a_pagar,
                            'abona_ya': abona_ya,
                            'y_en_entrega': y_en_entrega,
                            'total_usd': total_cotizacion_usd,
                            'total_bs': total_cotizacion_bs,
                            'terminos_condiciones': config.get('terms_conditions', 'Términos y condiciones estándar.')
                        }
                        
                        # Generar PNG en carpeta permanente
                        # Crear estructura de carpetas: /home/ubuntu/cotizaciones_guardadas/YYYY/MM/
                        now = now_caracas_naive()
                        year = now.strftime("%Y")
                        month = now.strftime("%m")
                        
                        output_dir = f'/home/ubuntu/cotizaciones_guardadas/{year}/{month}'
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Ruta completa del archivo PNG
                        png_filename = f"cotizacion_{st.session_state.saved_quote_number}.png"
                        png_path = f"{output_dir}/{png_filename}"
                        
                        png_gen = PNGQuoteGenerator()
                        result = png_gen.generate_quote_png_from_data(quote_data, png_path)
                        
                        if result:
                            # Actualizar ruta del PNG en la base de datos
                            if st.session_state.get('saved_quote_id'):
                                conn = DBManager.get_connection()
                                cursor = conn.cursor()
                                is_postgres = DBManager.USE_POSTGRES
                                
                                if is_postgres:
                                    cursor.execute("""
                                        UPDATE quotes SET jpeg_path = %s WHERE id = %s
                                    """, (png_path, st.session_state.saved_quote_id))
                                else:
                                    cursor.execute("""
                                        UPDATE quotes SET jpeg_path = ? WHERE id = ?
                                    """, (png_path, st.session_state.saved_quote_id))
                                
                                conn.commit()
                                cursor.close()
                                conn.close()
                            
                            # Ofrecer descarga
                            with open(png_path, 'rb') as f:
                                st.download_button(
                                    label="🖼️ Descargar PNG",
                                    data=f,
                                    file_name=png_filename,
                                    mime="image/png",
                                    use_container_width=True
                                )
                            st.success(f"✅ PNG generado y guardado en: {png_path}")
                        else:
                            st.error("❌ Error al generar PNG")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.warning("⚠️ Primero debe guardar la cotización")
        
        # Botón NUEVA COTIZACIÓN (solo visible si la cotización fue guardada)
        if st.session_state.get('cotizacion_guardada', False):
            st.markdown("---")
            if st.button("🆕 NUEVA COTIZACIÓN", use_container_width=True, type="primary", key="btn_nueva_cotizacion"):
                try:
                    # Limpiar COMPLETAMENTE todos los datos: cliente + ítems + links + vista previa + modo edición
                    _keys_to_clear_nueva = [
                        'cotizacion_items', 'cliente_datos',
                        'mostrar_cotizacion', 'saved_quote_number', 'saved_quote_id',
                        'cotizacion_guardada', 'show_save_success',
                        'editing_mode', 'editing_quote_id', 'editing_quote_number',
                        'editing_quote_data', 'editing_data_loaded',
                        'editing_item_index', 'editing_item_data',
                        'item_links', 'limpiar_campos_item',
                        'cotizacion_aplica_iva',  # Resetear IVA a NO por defecto
                        'guardando_en_progreso',  # Resetear protección anti-duplicado
                    ]
                    for _k in _keys_to_clear_nueva:
                        if _k in st.session_state:
                            del st.session_state[_k]

                    # Resetear listas y dicts base
                    st.session_state.item_links = []
                    st.session_state.cotizacion_items = []
                    st.session_state.cliente_datos = {}

                    # Incrementar contadores para forzar el reset visual de todos los widgets
                    if 'cliente_reset_counter' not in st.session_state:
                        st.session_state.cliente_reset_counter = 0
                    if 'item_reset_counter' not in st.session_state:
                        st.session_state.item_reset_counter = 0
                    st.session_state.cliente_reset_counter += 1
                    st.session_state.item_reset_counter += 1
                    # Activar scroll automático al tope en el siguiente render
                    st.session_state.scroll_to_top = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al crear nueva cotización: {str(e)}")
                    print(f"ERROR en NUEVA COTIZACIÓN: {str(e)}")  # Log para debugging
