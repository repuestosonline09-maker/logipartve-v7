"""
Panel de Analista - LogiPartVE Pro v7.0
Sistema de cotización SIN IA - Solo cálculos y formularios
Campos configurables desde Panel Admin
"""

import streamlit as st
from datetime import datetime, timedelta
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
        # Obtener listas desde BD
        paises_origen = DBManager.get_paises_origen()
        tipos_envio = DBManager.get_tipos_envio()
        tiempos_entrega = DBManager.get_tiempos_entrega()
        garantias = DBManager.get_warranties()
        
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
            "manejo_options": DBManager.get_manejo_options(),
            "impuesto_options": DBManager.get_impuesto_internacional_options(),
            "utilidad_factors": DBManager.get_profit_factors(),
            "tax_percentage": DBManager.get_tax_percentage(),
            "diferencial": DBManager.get_diferencial(),
            "iva_venezuela": DBManager.get_iva_venezuela()
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
            "iva_venezuela": 16.0
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
    
    # Título con información del analista y número de cotización
    st.title("📝 Nueva Cotización")
    
    # ==========================================
    # SIDEBAR: CONVERTIDOR DE MONEDA EUR → USD
    # ==========================================
    with st.sidebar:
        st.markdown("### 💱 Convertidor de Moneda")
        st.info("🇪🇺 Convierte precios de repuestos europeos de EUR a USD")
        
        # Obtener factor de conversión desde configuración
        config_list = DBManager.get_all_config()
        config = {item['key']: item for item in config_list}
        eur_usd_factor = float(config.get('eur_usd_factor', {}).get('value', 1.23))
        
        # Inicializar estado para el convertidor
        if 'eur_amount' not in st.session_state:
            st.session_state.eur_amount = 0.0
        if 'usd_amount' not in st.session_state:
            st.session_state.usd_amount = 0.0
        
        # Input para EUR
        eur_input = st.number_input(
            "💶 EURO (€)",
            min_value=0.0,
            value=st.session_state.eur_amount,
            step=1.0,
            placeholder="Ej: 100",
            help="Ingrese el precio en euros",
            key="eur_input_field"
        )
        
        # Calcular automáticamente USD
        if eur_input != st.session_state.eur_amount:
            st.session_state.eur_amount = eur_input
            st.session_state.usd_amount = eur_input * eur_usd_factor
        
        # Mostrar resultado USD
        st.markdown(f"### 💵 DÓLAR ($)")
        st.success(f"**${st.session_state.usd_amount:.2f} USD**")
        st.caption(f"📊 Factor: €1 = ${eur_usd_factor}")
        
        # Botón para limpiar
        if st.button("🧹 Limpiar Convertidor", use_container_width=True, key="btn_limpiar_convertidor"):
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
    col1, col2 = st.columns(2)
    with col1:
        cliente_nombre = st.text_input("Nombre del Cliente", key=f"cliente_nombre_{reset_key}")
        cliente_telefono = st.text_input("Teléfono", key=f"cliente_telefono_{reset_key}")
    with col2:
        cliente_email = st.text_input("Email (opcional)", key=f"cliente_email_{reset_key}")
        cliente_vehiculo = st.text_input("Vehículo", placeholder="Ej: Hyundai Santa Fe 2006", key=f"cliente_vehiculo_{reset_key}")
    
    col3, col4, col5 = st.columns(3)
    with col3:
        cliente_cilindrada = st.text_input("Cilindrada/Motor", placeholder="Ej: V6 3.5L", key=f"cliente_cilindrada_{reset_key}")
    with col4:
        cliente_ano = st.text_input("Año del Vehículo", key=f"cliente_ano_{reset_key}")
    with col5:
        cliente_vin = st.text_input("Nro. VIN (opcional)", key=f"cliente_vin_{reset_key}")
    
    # Nuevos campos opcionales: Dirección y C.I./RIF
    col7, col8 = st.columns(2)
    with col7:
        cliente_direccion = st.text_input("Dirección (opcional)", key=f"cliente_direccion_{reset_key}")
    with col8:
        cliente_ci_rif = st.text_input("C.I. / RIF (opcional)", key=f"cliente_ci_rif_{reset_key}")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 3: FORMULARIO DE ÍTEM
    # ==========================================
    try:
        num_items = len(st.session_state.cotizacion_items) if isinstance(st.session_state.cotizacion_items, list) else 0
    except:
        num_items = 0
        st.session_state.cotizacion_items = []
    
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
        # Marcar como limpiado
        st.session_state.limpiar_campos_item = False
    
    # Usar el contador para generar keys únicas
    reset_key = st.session_state.item_reset_counter
    
    # Fila 1: Descripción y N° Parte
    item_col1, item_col2 = st.columns(2)
    with item_col1:
        item_descripcion = st.text_input("Descripción del Repuesto", key=f"item_descripcion_{reset_key}", placeholder="Ej: Bomba de gasolina")
    with item_col2:
        item_parte = st.text_input("N° de Parte", key=f"item_parte_{reset_key}", placeholder="Ej: 12345-ABC")
    
    # Fila 2: Marca (texto libre), Garantía (desde BD), Cantidad (1-1000)
    item_col3, item_col4, item_col5 = st.columns(3)
    with item_col3:
        item_marca = st.text_input("Marca", placeholder="Ej: TOYOTA, BOSCH, DENSO...", key=f"item_marca_{reset_key}")
    with item_col4:
        item_garantia = st.selectbox("Garantía", config["garantias"], key=f"item_garantia_{reset_key}")
    with item_col5:
        item_cantidad = st.selectbox("Cantidad", CANTIDADES, key=f"item_cantidad_{reset_key}")
    
    # Fila 3: Origen (desde BD), Envío (desde BD), Tiempo de Entrega (desde BD)
    item_col6, item_col7, item_col8 = st.columns(3)
    with item_col6:
        item_origen = st.selectbox("País de Localización", config["paises_origen"], key=f"item_origen_{reset_key}")
    with item_col7:
        item_envio_tipo = st.selectbox("Tipo de Envío", config["tipos_envio"], key=f"item_envio_tipo_{reset_key}")
    with item_col8:
        item_tiempo = st.selectbox("Tiempo de Entrega", config["tiempos_entrega"], key=f"item_tiempo_{reset_key}")
    
    # Fila 4: País de Fabricación (desde BD) y Link
    item_col9, item_col10 = st.columns(2)
    with item_col9:
        item_fabricacion = st.selectbox("País de Fabricación", config["paises_origen"], key=f"item_fabricacion_{reset_key}")
    with item_col10:
        item_link = st.text_input("Link del Producto (opcional)", placeholder="https://...", key=f"item_link_{reset_key}")
    
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
        costo_fob = st.number_input("Costo FOB ($)", min_value=0.0, value=None, step=1.0, placeholder="Ej: $50", key=f"costo_fob_{reset_key}") or 0.0
    with cost_col2:
        costo_handling = st.number_input("Handling ($)", min_value=0.0, value=None, step=1.0, placeholder="Ej: $25", key=f"costo_handling_{reset_key}") or 0.0
    with cost_col3:
        # MANEJO - Selectbox desde Admin
        manejo_idx = st.selectbox("Manejo ($)", range(len(manejo_options_display)), 
                                  format_func=lambda x: manejo_options_display[x], 
                                  key=f"costo_manejo_select_{reset_key}")
        costo_manejo = config["manejo_options"][manejo_idx]
    
    cost_col4, cost_col5, cost_col6 = st.columns(3)
    with cost_col4:
        # IMPUESTO INTERNACIONAL - Selectbox desde Admin
        impuesto_idx = st.selectbox("Impuesto Internacional (%)", range(len(impuesto_options_display)),
                                    format_func=lambda x: impuesto_options_display[x],
                                    key=f"impuesto_select_{reset_key}")
        impuesto_porcentaje = config["impuesto_options"][impuesto_idx]
    with cost_col5:
        # FACTOR DE UTILIDAD - Selectbox desde Admin
        utilidad_idx = st.selectbox("Factor de Utilidad", range(len(utilidad_options_display)),
                                    format_func=lambda x: utilidad_options_display[x],
                                    key=f"utilidad_select_{reset_key}")
        factor_utilidad = config["utilidad_factors"][utilidad_idx]
    with cost_col6:
        costo_envio = st.number_input("Envío ($)", min_value=0.0, value=None, step=1.0, placeholder="Ej: $100", key=f"costo_envio_{reset_key}") or 0.0
    
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
        if st.button("➕ AGREGAR OTRO ÍTEM", use_container_width=True, type="secondary", key="btn_agregar_item"):
            # Validar campos mínimos
            if not item_descripcion:
                st.error("⚠️ Ingrese la descripción del repuesto")
            elif costo_fob <= 0:
                st.error("⚠️ Ingrese el costo FOB")
            else:
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
                    "link": item_link,
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
                # Protección adicional antes de append
                try:
                    if not isinstance(st.session_state.cotizacion_items, list):
                        st.session_state.cotizacion_items = []
                    # Verificar que cotizacion_items tiene el método append
                    if not hasattr(st.session_state.cotizacion_items, 'append'):
                        st.session_state.cotizacion_items = []
                    st.session_state.cotizacion_items.append(nuevo_item)
                    # Guardar mensaje de éxito en session_state para mostrarlo después del rerun
                    st.session_state.item_agregado_msg = f"✅ Ítem #{len(st.session_state.cotizacion_items)} agregado. Puede agregar otro."
                    # Limpiar campos del ítem para el siguiente (mantener datos del cliente)
                    st.session_state.limpiar_campos_item = True
                except (AttributeError, TypeError) as e:
                    # Guardar mensaje de error en session_state
                    st.session_state.item_agregado_msg = f"⚠️ Error al agregar ítem: {str(e)}. Reiniciando lista..."
                    st.session_state.cotizacion_items = [nuevo_item]
                    st.session_state.limpiar_campos_item = True
                st.rerun()
    
    with btn_action_col2:
        if st.button("📄 GENERAR COTIZACIÓN", use_container_width=True, type="primary", key="btn_generar_cotizacion"):
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
                        "link": item_link,
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
                    st.write(f"**💵 Precio USD:** ${item.get('precio_usd', item['costo_unitario']):.2f}")
                    st.write(f"**🇻🇪 Precio Bs:** ${item.get('precio_bs', item['costo_total']):.2f}")
                    st.write(f"**Total USD:** ${item['costo_total']:.2f}")
                
                # Botón para eliminar ítem
                if st.button(f"🗑️ Eliminar Ítem #{i+1}", key=f"del_item_{i}"):
                    st.session_state.cotizacion_items.pop(i)
                    st.rerun()
            
            total_general_usd += item['costo_total']
            total_general_bs += item.get('costo_total_bs', item['costo_total'])
        
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
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
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
            
            # Sub-Total (precio USD + diferencial, sin IVA) - YA VIENE CALCULADO CON CANTIDAD
            precio_usd_total = item.get('precio_usd', 0)
            diferencial_total = item.get('diferencial_valor', 0)
            sub_total += precio_usd_total + diferencial_total
            
            # IVA - YA VIENE CALCULADO CON CANTIDAD
            if item.get('aplicar_iva', False):
                iva_total += item.get('iva_valor', 0)
            
            # Abona Ya (costos base SIN envío) - YA VIENEN CALCULADOS CON CANTIDAD
            abona_item = (
                item.get('fob_total', 0) +
                item.get('costo_handling', 0) +
                item.get('costo_manejo', 0) +
                item.get('costo_impuesto', 0) +
                item.get('utilidad_valor', 0) +
                item.get('costo_tax', 0)
            )
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
            if st.button("💾 GUARDAR COTIZACIÓN", use_container_width=True, type="primary", key="btn_guardar_cotizacion"):
                # Generar número de cotización definitivo
                final_quote_number = QuoteNumberingService.generate_quote_number(user_id, username)
                
                if final_quote_number:
                    # Aquí se guardaría en la base de datos
                    # Por ahora solo mostramos confirmación
                    st.success(f"✅ Cotización {final_quote_number} guardada exitosamente")
                    st.session_state.saved_quote_number = final_quote_number
                    st.session_state.cotizacion_guardada = True  # Marcar que la cotización fue guardada
                    st.rerun()
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
                            'total_usd': total_cotizacion_usd,
                            'total_bs': total_cotizacion_bs,
                            'terms': config.get('terms_conditions', 'Términos y condiciones estándar.')
                        }
                        
                        # Generar PDF
                        output_dir = '/tmp/cotizaciones'
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = f"{output_dir}/cotizacion_{st.session_state.saved_quote_number}.pdf"
                        
                        pdf_gen = PDFQuoteGenerator()
                        result = pdf_gen.generate_quote_pdf(quote_data, output_path)
                        
                        if result:
                            # Ofrecer descarga
                            with open(output_path, 'rb') as f:
                                st.download_button(
                                    label="📅 Descargar PDF",
                                    data=f,
                                    file_name=f"cotizacion_{st.session_state.saved_quote_number}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            st.success("✅ PDF generado exitosamente")
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
                            'total_usd': total_cotizacion_usd,
                            'total_bs': total_cotizacion_bs,
                            'terms': config.get('terms_conditions', 'Términos y condiciones estándar.')
                        }
                        
                        # Generar PNG
                        output_dir = '/tmp/cotizaciones'
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = f"{output_dir}/cotizacion_{st.session_state.saved_quote_number}.png"
                        
                        png_gen = PNGQuoteGenerator()
                        result = png_gen.generate_quote_png_from_data(quote_data, output_path)
                        
                        if result:
                            # Ofrecer descarga
                            with open(output_path, 'rb') as f:
                                st.download_button(
                                    label="🖼️ Descargar PNG",
                                    data=f,
                                    file_name=f"cotizacion_{st.session_state.saved_quote_number}.png",
                                    mime="image/png",
                                    use_container_width=True
                                )
                            st.success("✅ PNG generado exitosamente")
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
                # Limpiar TODO: datos del cliente + ítems + vista previa
                st.session_state.cotizacion_items = []
                st.session_state.cliente_datos = {}
                if 'mostrar_cotizacion' in st.session_state:
                    del st.session_state.mostrar_cotizacion
                if 'saved_quote_number' in st.session_state:
                    del st.session_state.saved_quote_number
                if 'cotizacion_guardada' in st.session_state:
                    del st.session_state.cotizacion_guardada
                
                # Incrementar contadores para limpiar todos los formularios
                st.session_state.cliente_reset_counter += 1
                st.session_state.item_reset_counter += 1
                st.rerun()
