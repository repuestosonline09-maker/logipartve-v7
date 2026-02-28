"""
Panel de Analista - LogiPartVE Pro v7.0
Sistema de cotización SIN IA - Solo cálculos y formularios
Campos configurables desde Panel Admin
"""

import streamlit as st
import json
import datetime
from datetime import timedelta
from database.db_manager import DBManager
from database.config_helpers import ConfigHelpers
from services.auth_manager import AuthManager
from services.quote_numbering import QuoteNumberingService

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

def cargar_configuraciones():
    """Carga todas las configuraciones desde la base de datos"""
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
        return config
    except Exception as e:
        # Valores por defecto si hay error
        return {
            "paises_origen": ["-- Seleccione --", "EEUU", "MIAMI", "ESPAÑA", "MADRID"],
            "tipos_envio": ["-- Seleccione --", "AEREO", "MARITIMO", "TERRESTRE"],
            "tiempos_entrega": ["-- Seleccione --", "02 A 05 DIAS", "08 A 12 DIAS", "12 A 15 DIAS"],
            "garantias": ["-- Seleccione --", "15 DIAS", "30 DIAS", "45 DIAS", "3 MESES", "6 MESES"],
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
    if 'tarifas' not in st.session_state:
        st.session_state.tarifas = {
            "mia_a": 5.5,   # Miami Aéreo $/lb
            "mia_m": 12.0,  # Miami Marítimo $/ft³
            "mad": 8.0      # Madrid Aéreo $/kg
        }
    
    # Obtener información del usuario actual
    current_user = AuthManager.get_current_user()
    user_id = current_user.get('user_id') if current_user else None
    username = current_user.get('username', 'Usuario') if current_user else 'Usuario'
    full_name = current_user.get('full_name', username) if current_user else 'Usuario'
    
    # Obtener vista previa del número de cotización
    if user_id:
        next_quote_number = QuoteNumberingService.get_next_quote_number_preview(user_id, username)
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
        st.info("📝 Modo edición activado. Modifique los datos y haga clic en 'ACTUALIZAR COTIZACIÓN' para guardar los cambios.")
        
        # Botón para cancelar edición
        if st.button("❌ CANCELAR EDICIÓN", type="secondary"):
            # Limpiar modo edición
            st.session_state.editing_mode = False
            st.session_state.editing_quote_id = None
            st.session_state.editing_quote_number = None
            st.session_state.editing_quote_data = None
            st.session_state.cotizacion_items = []
            st.session_state.cliente_datos = {}
            st.success("✅ Edición cancelada")
            st.rerun()
    else:
        st.title("📋 Nueva Cotización")
    
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
        
        # Cargar ítems con TODOS los campos
        items = editing_quote_data.get('items', [])
        st.session_state.cotizacion_items = []
        for item in items:
            st.session_state.cotizacion_items.append({
                'descripcion': item.get('description', ''),
                'parte': item.get('part_number', ''),
                'marca': item.get('marca', ''),
                'garantia': item.get('garantia', ''),
                'cantidad': item.get('quantity', 1),
                'origen': item.get('origen', ''),
                'envio_tipo': item.get('envio_tipo', ''),
                'tiempo_entrega': item.get('tiempo_entrega', ''),
                'fabricacion': item.get('fabricacion', ''),
                'link': item.get('page_url', ''),
                'costo_fob': item.get('unit_cost', 0),
                'costo_handling': item.get('international_handling', 0),
                'costo_manejo': item.get('national_handling', 0),
                'costo_envio': item.get('shipping_cost', 0),
                'impuesto_porcentaje': item.get('tax_percentage', 0),
                'factor_utilidad': item.get('profit_factor', 1.0),
                'costo_unitario': item.get('unit_cost', 0),
                'costo_total': item.get('total_cost', 0),
                'precio_usd': item.get('unit_cost', 0),
                'precio_bs': item.get('total_cost', 0)
            })
        
        # Marcar como cargado
        st.session_state.editing_data_loaded = True
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
            st.rerun()
        
        st.markdown("---")
        st.caption("📋 Copie el monto USD al campo 'Costo FOB ($)' en el formulario")
        st.markdown("---")
    
    # ==========================================
    # SIDEBAR: CALCULADORA DE ENVÍO
    # ==========================================
    with st.sidebar:
        st.markdown("### 📊 Calculadora de Envío")
        st.info("💡 Use esta calculadora para estimar el costo de envío. El resultado es solo una **referencia**.")
        
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
                st.rerun()
        
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
    
    # Formulario de datos del cliente
    st.markdown("### 👤 Datos del Cliente")
    
    # Obtener valores por defecto en modo edición
    default_nombre = st.session_state.cliente_datos.get('nombre', '') if editing_mode else ''
    default_telefono = st.session_state.cliente_datos.get('telefono', '') if editing_mode else ''
    default_email = st.session_state.cliente_datos.get('email', '') if editing_mode else ''
    default_vehiculo = st.session_state.cliente_datos.get('vehiculo', '') if editing_mode else ''
    default_cilindrada = st.session_state.cliente_datos.get('cilindrada', '') if editing_mode else ''
    default_ano = st.session_state.cliente_datos.get('year', '') if editing_mode else ''
    default_vin = st.session_state.cliente_datos.get('vin', '') if editing_mode else ''
    default_direccion = st.session_state.cliente_datos.get('direccion', '') if editing_mode else ''
    default_ci_rif = st.session_state.cliente_datos.get('cedula', '') if editing_mode else ''
    
    col1, col2 = st.columns(2)
    with col1:
        cliente_nombre = st.text_input("Nombre del Cliente", value=default_nombre, key=f"cliente_nombre_{reset_key}")
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
    
    # Nuevos campos opcionales: Dirección y C.I./RIF
    col7, col8 = st.columns(2)
    with col7:
        cliente_direccion = st.text_input("Dirección (opcional)", value=default_direccion, key=f"cliente_direccion_{reset_key}")
    with col8:
        cliente_ci_rif = st.text_input("C.I. / RIF (opcional)", value=default_ci_rif, key=f"cliente_ci_rif_{reset_key}")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 2.5: ÍTEMS EXISTENTES (MODO EDICIÓN)
    # ==========================================
    if editing_mode and isinstance(st.session_state.cotizacion_items, list) and len(st.session_state.cotizacion_items) > 0:
        st.markdown("### 📋 ÍTEMS EXISTENTES")
        st.info("📝 Puede editar cualquier ítem haciendo clic en '✏️ EDITAR' o eliminar con '🗑️ ELIMINAR'")
        
        for i, item in enumerate(st.session_state.cotizacion_items):
            with st.expander(f"📦 Ítem #{i+1}: {item.get('descripcion', 'Sin descripción')}", expanded=False):
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
                    
                    # Mostrar múltiples links si existen
                    link = item.get('link', item.get('page_url', ''))
                    if link:
                        try:
                            # Intentar parsear como JSON array
                            if link.startswith('['):
                                links_array = json.loads(link)
                                if links_array:
                                    st.write(f"• **Links ({len(links_array)}):**")
                                    for idx, l in enumerate(links_array, 1):
                                        st.write(f"  {idx}. [{l[:25]}...]({l})")
                                else:
                                    st.write(f"• **Link:** No disponible")
                            else:
                                # Link único (formato antiguo)
                                st.write(f"• **Link:** [{link[:30]}...]({link})")
                        except:
                            # Si falla el parsing, mostrar como link único
                            st.write(f"• **Link:** [{link[:30]}...]({link})")
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
                
                # Botones de acción
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button(f"✏️ EDITAR", key=f"edit_item_{i}", use_container_width=True):
                        # Cargar ítem en el formulario
                        st.session_state.editing_item_index = i
                        st.session_state.editing_item_data = item
                        st.rerun()
                
                with btn_col2:
                    if st.button(f"🗑️ ELIMINAR", key=f"delete_item_{i}", use_container_width=True, type="secondary"):
                        st.session_state.cotizacion_items.pop(i)
                        st.success(f"✅ Ítem #{i+1} eliminado")
                        st.rerun()
        
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
    
    # DEBUG: Mostrar estado de variables de edición
    # st.write(f"DEBUG - editing_item: {editing_item}")
    # st.write(f"DEBUG - editing_item_index: {editing_item_index}")
    # st.write(f"DEBUG - editing_item_data: {editing_item_data}")
    
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
    
    # Inicializar lista de links en session_state si no existe
    if 'item_links' not in st.session_state:
        # Si estamos editando, cargar links existentes
        if editing_item and default_link:
            # Si el link es un JSON array, parsearlo
            try:
                if default_link.startswith('['):
                    st.session_state.item_links = json.loads(default_link)
                else:
                    st.session_state.item_links = [default_link] if default_link else []
            except:
                st.session_state.item_links = [default_link] if default_link else []
        else:
            st.session_state.item_links = []
    
    # Mostrar links existentes
    links_to_remove = []
    if st.session_state.item_links:
        for idx, link in enumerate(st.session_state.item_links):
            col_link, col_delete = st.columns([5, 1])
            with col_link:
                st.text_input(
                    f"Link #{idx + 1}",
                    value=link,
                    key=f"link_display_{idx}_{reset_key}",
                    on_change=lambda i=idx: st.session_state.item_links.__setitem__(i, st.session_state[f"link_display_{i}_{reset_key}"])
                )
            with col_delete:
                if st.button("❌", key=f"delete_link_{idx}_{reset_key}", help="Eliminar link"):
                    links_to_remove.append(idx)
    
    # Eliminar links marcados
    if links_to_remove:
        for idx in sorted(links_to_remove, reverse=True):
            st.session_state.item_links.pop(idx)
        st.session_state.link_counter += 1
        st.rerun()
    
    # Campo para agregar nuevo link
    new_link_col1, new_link_col2 = st.columns([5, 1])
    with new_link_col1:
        new_link = st.text_input(
            "Nuevo link",
            placeholder="https://...",
            key=f"new_link_input_{reset_key}_{st.session_state.link_counter}"
        )
    with new_link_col2:
        if st.button("➞ Agregar", key=f"add_link_{reset_key}", help="Agregar link"):
            if new_link and new_link.strip():
                st.session_state.item_links.append(new_link.strip())
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
    # SECCIÓN 5: PREGUNTA IVA VENEZUELA
    # ==========================================
    st.markdown("### 🇻🇪 IVA Venezuela")
    st.warning(f"⚠️ **¿APLICAR IVA ({iva_porcentaje}%)?** - El IVA solo se aplica al precio en Bolívares")
    
    iva_col1, iva_col2 = st.columns(2)
    with iva_col1:
        aplicar_iva = st.radio(
            "¿Aplicar IVA a esta cotización?",
            options=["NO", "SÍ"],
            index=0,
            horizontal=True,
            key="aplicar_iva"
        )
    
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
                        # ACTUALIZAR ítem existente
                        st.session_state.cotizacion_items[editing_item_index] = nuevo_item
                        st.session_state.item_agregado_msg = f"✅ Ítem #{editing_item_index + 1} actualizado correctamente."
                        # Limpiar estado de edición
                        if 'editing_item_index' in st.session_state:
                            del st.session_state.editing_item_index
                        if 'editing_item_data' in st.session_state:
                            del st.session_state.editing_item_data
                    else:
                        # AGREGAR nuevo ítem
                        if not hasattr(st.session_state.cotizacion_items, 'append'):
                            st.session_state.cotizacion_items = []
                        st.session_state.cotizacion_items.append(nuevo_item)
                        st.session_state.item_agregado_msg = f"✅ Ítem #{len(st.session_state.cotizacion_items)} agregado. Puede agregar otro."
                    
                    # Limpiar campos del ítem para el siguiente (mantener datos del cliente)
                    st.session_state.limpiar_campos_item = True
                except (AttributeError, TypeError) as e:
                    # Guardar mensaje de error en session_state
                    st.session_state.item_agregado_msg = f"⚠️ Error: {str(e)}. Reiniciando lista..."
                    st.session_state.cotizacion_items = [nuevo_item]
                    st.session_state.limpiar_campos_item = True
                st.rerun()
    
    with btn_action_col2:
        # Cambiar texto del botón según si se está editando la cotización completa
        if editing_mode:
            final_button_text = "💾 GUARDAR CAMBIOS"
            final_button_key = "btn_guardar_cambios"
        else:
            final_button_text = "📄 GENERAR COTIZACIÓN"
            final_button_key = "btn_generar_cotizacion"
        
        if st.button(final_button_text, use_container_width=True, type="primary", key=final_button_key):
            # Validar datos del cliente
            if not cliente_nombre:
                st.error("⚠️ Ingrese el nombre del cliente")
            elif not cliente_vehiculo:
                st.error("⚠️ Ingrese el vehículo")
            elif not item_descripcion and len(st.session_state.cotizacion_items) == 0:
                st.error("⚠️ Agregue al menos un ítem")
            else:
                # Si hay un ítem en el formulario actual, agregarlo
                if item_descripcion and costo_fob > 0:
                    # Obtener links de forma segura - variable independiente
                    _lnks2 = st.session_state.get('item_links', [])
                    if not isinstance(_lnks2, list):
                        _lnks2 = []
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
                    st.session_state.cotizacion_items.append(nuevo_item)
                
                # Guardar datos del cliente (solo campos con datos)
                st.session_state.cliente_datos = {
                    "nombre": cliente_nombre,
                    "telefono": cliente_telefono,
                    "email": cliente_email,
                    "vehiculo": cliente_vehiculo,
                    "cilindrada": cliente_cilindrada,
                    "ano": cliente_ano,
                    "vin": cliente_vin,
                    "direccion": cliente_direccion,
                    "ci_rif": cliente_ci_rif
                }
                
                # Si estamos en modo edición, actualizar en BD
                if editing_mode:
                    editing_quote_id = st.session_state.get('editing_quote_id')
                    if editing_quote_id:
                        # Actualizar cotización completa en BD
                        success = db.update_quote_complete(
                            quote_id=editing_quote_id,
                            cliente_datos=st.session_state.cliente_datos,
                            items=st.session_state.cotizacion_items,
                            username=st.session_state.username
                        )
                        
                        if success:
                            st.success("✅ Cotización actualizada correctamente en la base de datos")
                            # Limpiar estado de edición
                            if 'editing_quote_id' in st.session_state:
                                del st.session_state.editing_quote_id
                            if 'editing_quote_number' in st.session_state:
                                del st.session_state.editing_quote_number
                            # Esperar 2 segundos y redirigir a Mis Cotizaciones
                            import time
                            time.sleep(2)
                            st.session_state.selected_panel = "Mis Cotizaciones"
                            st.rerun()
                        else:
                            st.error("❌ Error al actualizar la cotización en la base de datos")
                else:
                    # Modo creación normal
                    st.session_state.mostrar_cotizacion = True
                    st.rerun()
    
    with btn_action_col3:
        if st.button("🗑️ LIMPIAR TODO", use_container_width=True, key="btn_limpiar_todo"):
            st.session_state.cotizacion_items = []
            st.session_state.cliente_datos = {}
            if 'mostrar_cotizacion' in st.session_state:
                del st.session_state.mostrar_cotizacion
            st.rerun()
    
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
            fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y")
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
        
        # Total a Pagar
        total_a_pagar = sub_total + iva_total
        
        # Y en la Entrega
        y_en_entrega = total_a_pagar - abona_ya
        
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
        
        # Botones de generación
        gen_col1, gen_col2, gen_col3 = st.columns(3)
        with gen_col1:
            # Cambiar botón según modo
            button_label = "🔄 ACTUALIZAR COTIZACIÓN" if editing_mode else "💾 GUARDAR COTIZACIÓN"
            
            if st.button(button_label, use_container_width=True, type="primary", key="btn_guardar_cotizacion"):
                # Validar que haya ítems
                if not items or len(items) == 0:
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
                                'total_amount': total_cotizacion_bs,
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
                                    # Limpiar modo edición
                                    st.session_state.editing_mode = False
                                    st.session_state.editing_quote_id = None
                                    st.session_state.editing_quote_number = None
                                    st.session_state.editing_quote_data = None
                                    st.session_state.editing_data_loaded = False
                                    st.session_state.cotizacion_items = []
                                    st.session_state.cliente_datos = {}
                                    
                                    print(f"✅ DEBUG - Cotización actualizada exitosamente: {editing_quote_number}")
                                    
                                    # Registrar actividad
                                    DBManager.log_activity(
                                        user_id,
                                        'quote_updated',
                                        f'Cotización {editing_quote_number} actualizada con {len(items)} ítems'
                                    )
                                    
                                    st.success(f"✅ ¡Cotización {editing_quote_number} actualizada exitosamente!")
                                    st.info("👉 Vaya a 'Mis Cotizaciones' para ver los cambios o regenerar el PDF")
                                else:
                                    st.error("❌ Error al actualizar ítems de la cotización. Revisa los logs para más detalles.")
                            else:
                                st.error("❌ Error al actualizar cotización en base de datos. Revisa los logs para más detalles.")
                    
                    except Exception as e:
                        st.error(f"❌ Error al actualizar cotización: {str(e)}")
                        print(f"❌ DEBUG - Excepción al actualizar: {str(e)}")
                        import traceback
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
                                    'total_amount': total_cotizacion_bs,
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
                                        DBManager.log_activity(
                                            user_id,
                                            'quote_created',
                                            f'Cotización {final_quote_number} creada con {len(items)} ítems'
                                        )
                                        
                                        st.rerun()
                                    else:
                                        st.error("❌ Error al guardar ítems de la cotización. Revisa los logs para más detalles.")
                                else:
                                    st.error("❌ Error al guardar cotización en base de datos. Revisa los logs para más detalles.")
                        
                        except Exception as e:
                            st.error(f"❌ Error al guardar cotización: {str(e)}")
                            print(f"❌ DEBUG - Excepción al guardar: {str(e)}")
                            import traceback
                            traceback.print_exc()
                    else:
                        st.error("❌ Error al generar número de cotización")
        
        with gen_col2:
            if st.button("📅 GENERAR PDF", use_container_width=True, type="secondary", key="btn_generar_pdf"):
                if st.session_state.get('saved_quote_number'):
                    try:
                        from services.document_generation import PDFQuoteGenerator
                        import os
                        
                        # Preparar datos para PDF
                        cliente = st.session_state.get('cliente_datos', {})
                        quote_data = {
                            'quote_number': st.session_state.saved_quote_number,
                            'analyst_name': st.session_state.full_name,
                            'client': {
                                'nombre': cliente.get('nombre', ''),
                                'telefono': cliente.get('telefono', ''),
                                'email': cliente.get('email', ''),
                                'vehiculo': cliente.get('vehiculo', ''),
                                'motor': cliente.get('cilindrada', ''),
                                'año': cliente.get('ano', ''),
                                'vin': cliente.get('vin', ''),
                                'direccion': cliente.get('direccion', ''),
                                'ci_rif': cliente.get('ci_rif', '')
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
                        now = datetime.datetime.now()
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
            if st.button("🖼️ GENERAR PNG", use_container_width=True, type="secondary", key="btn_generar_png"):
                if st.session_state.get('saved_quote_number'):
                    try:
                        from services.document_generation import PNGQuoteGenerator
                        import os
                        
                        # Preparar datos para PNG
                        cliente = st.session_state.get('cliente_datos', {})
                        quote_data = {
                            'quote_number': st.session_state.saved_quote_number,
                            'analyst_name': st.session_state.full_name,
                            'client': {
                                'nombre': cliente.get('nombre', ''),
                                'telefono': cliente.get('telefono', ''),
                                'email': cliente.get('email', ''),
                                'vehiculo': cliente.get('vehiculo', ''),
                                'motor': cliente.get('cilindrada', ''),
                                'año': cliente.get('ano', ''),
                                'vin': cliente.get('vin', ''),
                                'direccion': cliente.get('direccion', ''),
                                'ci_rif': cliente.get('ci_rif', '')
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
                        now = datetime.datetime.now()
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
                    # Limpiar TODO: datos del cliente + ítems + vista previa
                    st.session_state.cotizacion_items = []
                    st.session_state.cliente_datos = {}
                    if 'mostrar_cotizacion' in st.session_state:
                        del st.session_state.mostrar_cotizacion
                    if 'saved_quote_number' in st.session_state:
                        del st.session_state.saved_quote_number
                    if 'cotizacion_guardada' in st.session_state:
                        del st.session_state.cotizacion_guardada
                    
                    # Limpiar variables de modo edición
                    if 'editing_quote_id' in st.session_state:
                        del st.session_state.editing_quote_id
                    if 'editing_quote_number' in st.session_state:
                        del st.session_state.editing_quote_number
                    if 'editing_item_index' in st.session_state:
                        del st.session_state.editing_item_index
                    if 'editing_item_data' in st.session_state:
                        del st.session_state.editing_item_data
                    
                    # Incrementar contadores para limpiar todos los formularios (con verificación de seguridad)
                    if 'cliente_reset_counter' not in st.session_state:
                        st.session_state.cliente_reset_counter = 0
                    if 'item_reset_counter' not in st.session_state:
                        st.session_state.item_reset_counter = 0
                    
                    st.session_state.cliente_reset_counter += 1
                    st.session_state.item_reset_counter += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al crear nueva cotización: {str(e)}")
                    print(f"ERROR en NUEVA COTIZACIÓN: {str(e)}")  # Log para debugging
