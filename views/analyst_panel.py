"""
Panel de Analista - LogiPartVE Pro v7.0
Sistema de cotización SIN IA - Solo cálculos y formularios
Campos configurables desde Panel Admin
"""

import streamlit as st
from datetime import datetime, timedelta
from database.db_manager import DBManager

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
        config = {
            "paises_origen": ["-- Seleccione --"] + DBManager.get_paises_origen(),
            "tipos_envio": ["-- Seleccione --"] + DBManager.get_tipos_envio(),
            "tiempos_entrega": ["-- Seleccione --"] + DBManager.get_tiempos_entrega(),
            "garantias": ["-- Seleccione --"] + DBManager.get_warranties(),
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
    if 'items' not in st.session_state or not isinstance(st.session_state.items, list):
        st.session_state.items = []
    if 'cliente_datos' not in st.session_state:
        st.session_state.cliente_datos = {}
    if 'tarifas' not in st.session_state:
        st.session_state.tarifas = {
            "mia_a": 5.5,   # Miami Aéreo $/lb
            "mia_m": 12.0,  # Miami Marítimo $/ft³
            "mad": 8.0      # Madrid Aéreo $/kg
        }
    
    st.title("📝 Nueva Cotización")
    
    # ==========================================
    # SECCIÓN 1: DATOS DEL CLIENTE
    # ==========================================
    st.markdown("### 👤 Datos del Cliente")
    
    col1, col2 = st.columns(2)
    with col1:
        cliente_nombre = st.text_input("Nombre del Cliente", key="cliente_nombre")
        cliente_telefono = st.text_input("Teléfono", key="cliente_telefono")
    with col2:
        cliente_email = st.text_input("Email (opcional)", key="cliente_email")
        cliente_vehiculo = st.text_input("Vehículo", placeholder="Ej: Hyundai Santa Fe 2006", key="cliente_vehiculo")
    
    col3, col4 = st.columns(2)
    with col3:
        cliente_ano = st.text_input("Año del Vehículo", key="cliente_ano")
    with col4:
        cliente_vin = st.text_input("Nro. VIN (opcional)", key="cliente_vin")
    
    # Nuevos campos opcionales: Dirección y C.I./RIF
    col5, col6 = st.columns(2)
    with col5:
        cliente_direccion = st.text_input("Dirección (opcional)", key="cliente_direccion")
    with col6:
        cliente_ci_rif = st.text_input("C.I. / RIF (opcional)", key="cliente_ci_rif")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 2: CALCULADORA DE ENVÍO (EXPANDIBLE)
    # ==========================================
    with st.expander("📊 CALCULADORA DE ENVÍO (Herramienta de referencia)", expanded=False):
        st.info("💡 Use esta calculadora para estimar el costo de envío. El resultado es solo una **referencia** - usted decide el valor final.")
        
        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
            calc_origen = st.selectbox("Origen", ["Miami", "Madrid"], key="calc_origen")
        with calc_col2:
            calc_tipo = st.selectbox("Tipo de Envío", ["Aéreo", "Marítimo"], key="calc_tipo")
        
        calc_col3, calc_col4, calc_col5, calc_col6 = st.columns(4)
        with calc_col3:
            calc_largo = st.number_input("Largo (cm)", min_value=0.0, value=0.0, step=0.1, format="%.1f", key="calc_largo")
        with calc_col4:
            calc_ancho = st.number_input("Ancho (cm)", min_value=0.0, value=0.0, step=0.1, format="%.1f", key="calc_ancho")
        with calc_col5:
            calc_alto = st.number_input("Alto (cm)", min_value=0.0, value=0.0, step=0.1, format="%.1f", key="calc_alto")
        with calc_col6:
            calc_peso = st.number_input("Peso (kg)", min_value=0.0, value=0.0, step=0.1, format="%.1f", key="calc_peso")
        
        if st.button("🧮 CALCULAR ENVÍO", use_container_width=True, key="btn_calcular"):
            if calc_largo > 0 and calc_ancho > 0 and calc_alto > 0 and calc_peso > 0:
                origen_calc = "MIAMI" if calc_origen == "Miami" else "MADRID"
                tipo_calc = "AEREO" if calc_tipo == "Aéreo" else "MARITIMO"
                
                total, fact, unidad, pv, es_min = calcular_envio(
                    calc_largo, calc_ancho, calc_alto, calc_peso,
                    origen_calc, tipo_calc, st.session_state.tarifas
                )
                
                st.success(f"**💰 COSTO ESTIMADO: ${total} USD**")
                st.write(f"📦 Base Facturable: {fact} {unidad} | ⚖️ Peso Volumétrico: {pv} kg")
                if es_min:
                    st.warning("⚠️ Tarifa mínima de $25 aplicada.")
            else:
                st.error("⚠️ Complete todos los campos con valores mayores a 0")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 3: FORMULARIO DE ÍTEM
    # ==========================================
    try:
        num_items = len(st.session_state.items) if isinstance(st.session_state.items, list) else 0
    except:
        num_items = 0
        st.session_state.items = []
    
    st.markdown(f"### 📦 Ítem #{num_items + 1}")
    
    # Fila 1: Descripción y N° Parte
    item_col1, item_col2 = st.columns(2)
    with item_col1:
        item_descripcion = st.text_input("Descripción del Repuesto", key="item_descripcion")
    with item_col2:
        item_parte = st.text_input("N° de Parte", key="item_parte")
    
    # Fila 2: Marca (texto libre), Garantía (desde BD), Cantidad (1-1000)
    item_col3, item_col4, item_col5 = st.columns(3)
    with item_col3:
        item_marca = st.text_input("Marca", placeholder="Ej: TOYOTA, BOSCH, DENSO...", key="item_marca")
    with item_col4:
        item_garantia = st.selectbox("Garantía", config["garantias"], key="item_garantia")
    with item_col5:
        item_cantidad = st.selectbox("Cantidad", CANTIDADES, key="item_cantidad")
    
    # Fila 3: Origen (desde BD), Envío (desde BD), Tiempo de Entrega (desde BD)
    item_col6, item_col7, item_col8 = st.columns(3)
    with item_col6:
        item_origen = st.selectbox("País de Localización", config["paises_origen"], key="item_origen")
    with item_col7:
        item_envio_tipo = st.selectbox("Tipo de Envío", config["tipos_envio"], key="item_envio_tipo")
    with item_col8:
        item_tiempo = st.selectbox("Tiempo de Entrega", config["tiempos_entrega"], key="item_tiempo")
    
    # Fila 4: País de Fabricación (desde BD) y Link
    item_col9, item_col10 = st.columns(2)
    with item_col9:
        item_fabricacion = st.selectbox("País de Fabricación", config["paises_origen"], key="item_fabricacion")
    with item_col10:
        item_link = st.text_input("Link del Producto (opcional)", placeholder="https://...", key="item_link")
    
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
        costo_fob = st.number_input("Costo FOB ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_fob")
    with cost_col2:
        costo_handling = st.number_input("Handling ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_handling")
    with cost_col3:
        # MANEJO - Selectbox desde Admin
        manejo_idx = st.selectbox("Manejo ($)", range(len(manejo_options_display)), 
                                  format_func=lambda x: manejo_options_display[x], 
                                  key="costo_manejo_select")
        costo_manejo = config["manejo_options"][manejo_idx]
    
    cost_col4, cost_col5, cost_col6 = st.columns(3)
    with cost_col4:
        # IMPUESTO INTERNACIONAL - Selectbox desde Admin
        impuesto_idx = st.selectbox("Impuesto Internacional (%)", range(len(impuesto_options_display)),
                                    format_func=lambda x: impuesto_options_display[x],
                                    key="impuesto_select")
        impuesto_porcentaje = config["impuesto_options"][impuesto_idx]
    with cost_col5:
        # FACTOR DE UTILIDAD - Selectbox desde Admin
        utilidad_idx = st.selectbox("Factor de Utilidad", range(len(utilidad_options_display)),
                                    format_func=lambda x: utilidad_options_display[x],
                                    key="utilidad_select")
        factor_utilidad = config["utilidad_factors"][utilidad_idx]
    with cost_col6:
        costo_envio = st.number_input("Envío ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_envio")
    
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
    # ==========================================
    st.markdown("### 📊 Cálculos Automáticos")
    
    # 1. IMPUESTO INTERNACIONAL = FOB * %
    costo_impuesto = costo_fob * (impuesto_porcentaje / 100)
    
    # 2. UTILIDAD = (FOB * Factor) - FOB
    # Ejemplo: (84 * 1.4285) - 84 = 35.99
    if factor_utilidad > 0:
        utilidad_calculada = (costo_fob * factor_utilidad) - costo_fob
    else:
        utilidad_calculada = 0
    
    # 3. TAX = (FOB + Handling + Manejo + Utilidad + Envío) * 7%
    # NOTA: El TAX NO incluye el Impuesto Internacional en su base
    base_tax = costo_fob + costo_handling + costo_manejo + utilidad_calculada + costo_envio
    costo_tax = base_tax * (tax_porcentaje / 100)
    
    # 4. PRECIO USD = FOB + Handling + Manejo + Impuesto + Utilidad + Envío + TAX
    # (SIN diferencial - para clientes que pagan en dólares)
    precio_usd = costo_fob + costo_handling + costo_manejo + costo_impuesto + utilidad_calculada + costo_envio + costo_tax
    
    # 5. DIFERENCIAL = PRECIO_USD * %
    diferencial_valor = precio_usd * (diferencial_porcentaje / 100)
    
    # 6. PRECIO Bs = PRECIO_USD + DIFERENCIAL
    # (Para clientes que pagan en bolívares a tasa BCV)
    precio_bs_sin_iva = precio_usd + diferencial_valor
    
    # 7. IVA VENEZUELA (solo si el analista seleccionó SÍ)
    if aplicar_iva == "SÍ":
        iva_valor = precio_bs_sin_iva * (iva_porcentaje / 100)
        precio_bs = precio_bs_sin_iva + iva_valor
    else:
        iva_valor = 0
        precio_bs = precio_bs_sin_iva
    
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
    
    # Costo total (cantidad × unitario)
    costo_total_usd = precio_usd * item_cantidad
    costo_total_bs = precio_bs * item_cantidad
    
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
                    "costo_impuesto": costo_impuesto,
                    "impuesto_porcentaje": impuesto_porcentaje,
                    "factor_utilidad": factor_utilidad,
                    "utilidad_valor": utilidad_calculada,
                    "costo_envio": costo_envio,
                    "costo_tax": costo_tax,
                    "tax_porcentaje": tax_porcentaje,
                    "diferencial": diferencial_valor,
                    "diferencial_porcentaje": diferencial_porcentaje,
                    "aplicar_iva": aplicar_iva == "SÍ",
                    "iva_porcentaje": iva_porcentaje,
                    "iva_valor": iva_valor,
                    "precio_usd": precio_usd,
                    "precio_bs": precio_bs,
                    "costo_unitario": precio_usd,
                    "costo_total": costo_total_usd,
                    "costo_total_bs": costo_total_bs
                }
                st.session_state.items.append(nuevo_item)
                st.success(f"✅ Ítem #{len(st.session_state.items)} agregado. Puede agregar otro.")
                st.rerun()
    
    with btn_action_col2:
        if st.button("📄 GENERAR COTIZACIÓN", use_container_width=True, type="primary", key="btn_generar_cotizacion"):
            # Validar datos del cliente
            if not cliente_nombre:
                st.error("⚠️ Ingrese el nombre del cliente")
            elif not cliente_vehiculo:
                st.error("⚠️ Ingrese el vehículo")
            elif not item_descripcion and len(st.session_state.items) == 0:
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
                        "costo_impuesto": costo_impuesto,
                        "impuesto_porcentaje": impuesto_porcentaje,
                        "factor_utilidad": factor_utilidad,
                        "utilidad_valor": utilidad_calculada,
                        "costo_envio": costo_envio,
                        "costo_tax": costo_tax,
                        "tax_porcentaje": tax_porcentaje,
                        "diferencial": diferencial_valor,
                        "diferencial_porcentaje": diferencial_porcentaje,
                        "aplicar_iva": aplicar_iva == "SÍ",
                        "iva_porcentaje": iva_porcentaje,
                        "iva_valor": iva_valor,
                        "precio_usd": precio_usd,
                        "precio_bs": precio_bs,
                        "costo_unitario": precio_usd,
                        "costo_total": costo_total_usd,
                        "costo_total_bs": costo_total_bs
                    }
                    st.session_state.items.append(nuevo_item)
                
                # Guardar datos del cliente (solo campos con datos)
                st.session_state.cliente_datos = {
                    "nombre": cliente_nombre,
                    "telefono": cliente_telefono,
                    "email": cliente_email,
                    "vehiculo": cliente_vehiculo,
                    "ano": cliente_ano,
                    "vin": cliente_vin,
                    "direccion": cliente_direccion,
                    "ci_rif": cliente_ci_rif
                }
                
                st.session_state.mostrar_cotizacion = True
                st.rerun()
    
    with btn_action_col3:
        if st.button("🗑️ LIMPIAR TODO", use_container_width=True, key="btn_limpiar_todo"):
            st.session_state.items = []
            st.session_state.cliente_datos = {}
            if 'mostrar_cotizacion' in st.session_state:
                del st.session_state.mostrar_cotizacion
            st.rerun()
    
    # ==========================================
    # SECCIÓN 7: RESUMEN DE ÍTEMS AGREGADOS
    # ==========================================
    if isinstance(st.session_state.items, list) and len(st.session_state.items) > 0:
        st.markdown("---")
        st.markdown("### 📋 Ítems Agregados")
        
        total_general_usd = 0
        total_general_bs = 0
        for i, item in enumerate(st.session_state.items):
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
                    st.session_state.items.pop(i)
                    st.rerun()
            
            total_general_usd += item['costo_total']
            total_general_bs += item.get('costo_total_bs', item['costo_total'])
        
        st.markdown("---")
        st.success(f"**💵 TOTAL USD: ${total_general_usd:.2f}** | **🇻🇪 TOTAL Bs: ${total_general_bs:.2f}**")
    
    # ==========================================
    # SECCIÓN 8: VISTA PREVIA DE COTIZACIÓN
    # ==========================================
    if st.session_state.get('mostrar_cotizacion', False) and len(st.session_state.items) > 0:
        st.markdown("---")
        st.markdown("## 📄 Vista Previa de Cotización")
        
        cliente = st.session_state.cliente_datos
        items = st.session_state.items
        
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
        
        # Mostrar totales
        total_col1, total_col2 = st.columns(2)
        with total_col1:
            st.success(f"**💵 TOTAL USD: ${total_cotizacion_usd:.2f}**")
        with total_col2:
            st.success(f"**🇻🇪 TOTAL Bs: ${total_cotizacion_bs:.2f}**")
        
        # Botones de generación
        gen_col1, gen_col2 = st.columns(2)
        with gen_col1:
            if st.button("📥 GENERAR PDF", use_container_width=True, type="primary", key="btn_generar_pdf"):
                st.info("🔧 Generación de PDF en desarrollo...")
        with gen_col2:
            if st.button("🖼️ GENERAR PNG", use_container_width=True, type="secondary", key="btn_generar_png"):
                st.info("🔧 Generación de PNG en desarrollo...")
