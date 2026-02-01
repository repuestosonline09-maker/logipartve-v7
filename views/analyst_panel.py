"""
Panel de Analista - LogiPartVE Pro v7.0
Sistema de cotización SIN IA - Solo cálculos y formularios
"""

import streamlit as st
from datetime import datetime, timedelta

# ==========================================
# DATOS PARA LISTAS DESPLEGABLES
# ==========================================

PAISES_ORIGEN = [
    "EEUU", "MIAMI", "ESPAÑA", "MADRID", "ALEMANIA", "ARGENTINA", "ARUBA", 
    "AUSTRALIA", "BRASIL", "CANADA", "CHILE", "CHINA", "COLOMBIA", 
    "COREA DEL SUR", "DINAMARCA", "DUBAI", "ESTONIA", "FRANCIA", "GRECIA", 
    "HOLANDA", "HUNGRIA", "INDIA", "INDONESIA", "INGLATERRA", "IRLANDA", 
    "ITALIA", "JAPÓN", "JORDANIA", "LETONIA", "LITUANIA", "MALASIA", 
    "MEXICO", "POLONIA", "PORTUGAL", "PUERTO RICO", "REINO UNIDO", 
    "SINGAPUR", "TAILANDIA", "TAIWAN", "TURQUIA", "UCRANIA", 
    "UNION EUROPEA", "VARIOS", "VENEZUELA"
]

TIPOS_ENVIO = ["AEREO", "MARITIMO", "TERRESTRE"]

TIEMPOS_ENTREGA = [
    "02 A 05 DIAS", "08 A 12 DIAS", "12 A 15 DIAS", 
    "18 A 21 DIAS", "25 A 30 DIAS", "30 A 45 DIAS", "60 DIAS"
]

GARANTIAS = ["15 DIAS", "30 DIAS", "45 DIAS", "3 MESES", "6 MESES"]

MARCAS = ["AFTERMARKET", "GENUINO", "OEM", "REMANUFACTURADO", "USADO"]

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
# FUNCIÓN PRINCIPAL DEL PANEL
# ==========================================

def render_analyst_panel():
    """Renderiza el panel de analista para crear cotizaciones"""
    
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
    if 'diferencial' not in st.session_state:
        st.session_state.diferencial = 0.25  # 25%
    
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
    
    # Fila 2: Marca, Garantía, Cantidad
    item_col3, item_col4, item_col5 = st.columns(3)
    with item_col3:
        item_marca = st.selectbox("Marca", MARCAS, key="item_marca")
    with item_col4:
        item_garantia = st.selectbox("Garantía", GARANTIAS, index=3, key="item_garantia")
    with item_col5:
        item_cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1, key="item_cantidad")
    
    # Fila 3: Origen, Envío, Tiempo de Entrega
    item_col6, item_col7, item_col8 = st.columns(3)
    with item_col6:
        item_origen = st.selectbox("País de Localización", PAISES_ORIGEN, key="item_origen")
    with item_col7:
        item_envio_tipo = st.selectbox("Tipo de Envío", TIPOS_ENVIO, key="item_envio_tipo")
    with item_col8:
        item_tiempo = st.selectbox("Tiempo de Entrega", TIEMPOS_ENTREGA, key="item_tiempo")
    
    # Fila 4: País de Fabricación y Link
    item_col9, item_col10 = st.columns(2)
    with item_col9:
        item_fabricacion = st.selectbox("País de Fabricación", PAISES_ORIGEN, key="item_fabricacion")
    with item_col10:
        item_link = st.text_input("Link del Producto (opcional)", placeholder="https://...", key="item_link")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 4: COSTOS (Solo visible para analista)
    # ==========================================
    st.markdown("### 💰 Costos (Interno - No visible al cliente)")
    
    cost_col1, cost_col2, cost_col3 = st.columns(3)
    with cost_col1:
        costo_fob = st.number_input("Costo FOB ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_fob")
    with cost_col2:
        costo_handling = st.number_input("Handling ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_handling")
    with cost_col3:
        costo_manejo = st.number_input("Manejo ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_manejo")
    
    cost_col4, cost_col5, cost_col6 = st.columns(3)
    with cost_col4:
        costo_impuesto = st.number_input("Impuesto ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_impuesto")
    with cost_col5:
        porcentaje_utilidad = st.number_input("Utilidad (%)", min_value=0, value=0, step=1, key="porcentaje_utilidad")
    with cost_col6:
        costo_envio = st.number_input("Envío ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_envio")
    
    cost_col7, cost_col8 = st.columns(2)
    with cost_col7:
        costo_tax = st.number_input("Tax 7% ($)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key="costo_tax")
    with cost_col8:
        # Calcular utilidad automáticamente
        utilidad_calculada = (costo_fob + costo_handling) * (porcentaje_utilidad / 100)
        st.metric("Utilidad Calculada", f"${utilidad_calculada:.2f}")
    
    # Calcular subtotal antes de diferencial
    subtotal_sin_dif = costo_fob + costo_handling + costo_manejo + costo_impuesto + utilidad_calculada + costo_envio + costo_tax
    
    # Calcular diferencial
    diferencial_valor = subtotal_sin_dif * st.session_state.diferencial
    
    # Total final
    total_item = subtotal_sin_dif + diferencial_valor
    
    st.markdown("---")
    
    # Mostrar resumen de cálculos
    st.markdown("### 📊 Resumen del Ítem")
    
    resumen_col1, resumen_col2, resumen_col3 = st.columns(3)
    with resumen_col1:
        st.metric("Subtotal (sin diferencial)", f"${subtotal_sin_dif:.2f}")
    with resumen_col2:
        st.metric(f"Diferencial ({int(st.session_state.diferencial*100)}%)", f"${diferencial_valor:.2f}")
    with resumen_col3:
        st.metric("**COSTO UNITARIO**", f"${total_item:.2f}")
    
    # Costo total (cantidad × unitario)
    costo_total_item = total_item * item_cantidad
    st.success(f"**COSTO TOTAL (Cant. {item_cantidad}): ${costo_total_item:.2f} USD**")
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN 5: BOTONES DE ACCIÓN
    # ==========================================
    
    btn_action_col1, btn_action_col2, btn_action_col3 = st.columns(3)
    
    with btn_action_col1:
        if st.button("➕ AGREGAR OTRO ÍTEM", use_container_width=True, type="secondary"):
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
                    "utilidad_porcentaje": porcentaje_utilidad,
                    "utilidad_valor": utilidad_calculada,
                    "costo_envio": costo_envio,
                    "costo_tax": costo_tax,
                    "diferencial": diferencial_valor,
                    "costo_unitario": total_item,
                    "costo_total": costo_total_item
                }
                st.session_state.items.append(nuevo_item)
                st.success(f"✅ Ítem #{len(st.session_state.items)} agregado. Puede agregar otro.")
                st.rerun()
    
    with btn_action_col2:
        if st.button("📄 GENERAR COTIZACIÓN", use_container_width=True, type="primary"):
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
                        "utilidad_porcentaje": porcentaje_utilidad,
                        "utilidad_valor": utilidad_calculada,
                        "costo_envio": costo_envio,
                        "costo_tax": costo_tax,
                        "diferencial": diferencial_valor,
                        "costo_unitario": total_item,
                        "costo_total": costo_total_item
                    }
                    st.session_state.items.append(nuevo_item)
                
                # Guardar datos del cliente
                st.session_state.cliente_datos = {
                    "nombre": cliente_nombre,
                    "telefono": cliente_telefono,
                    "email": cliente_email,
                    "vehiculo": cliente_vehiculo,
                    "ano": cliente_ano,
                    "vin": cliente_vin
                }
                
                st.session_state.mostrar_cotizacion = True
                st.rerun()
    
    with btn_action_col3:
        if st.button("🗑️ LIMPIAR TODO", use_container_width=True):
            st.session_state.items = []
            st.session_state.cliente_datos = {}
            if 'mostrar_cotizacion' in st.session_state:
                del st.session_state.mostrar_cotizacion
            st.rerun()
    
    # ==========================================
    # SECCIÓN 6: RESUMEN DE ÍTEMS AGREGADOS
    # ==========================================
    if isinstance(st.session_state.items, list) and len(st.session_state.items) > 0:
        st.markdown("---")
        st.markdown("### 📋 Ítems Agregados")
        
        total_general = 0
        for i, item in enumerate(st.session_state.items):
            with st.expander(f"Ítem #{i+1}: {item['descripcion']}", expanded=False):
                st.write(f"**N° Parte:** {item['parte']}")
                st.write(f"**Marca:** {item['marca']} | **Garantía:** {item['garantia']}")
                st.write(f"**Cantidad:** {item['cantidad']} | **Origen:** {item['origen']}")
                st.write(f"**Costo Unitario:** ${item['costo_unitario']:.2f}")
                st.write(f"**Costo Total:** ${item['costo_total']:.2f}")
            total_general += item['costo_total']
        
        st.success(f"**TOTAL GENERAL ({len(st.session_state.items)} ítems): ${total_general:.2f} USD**")
    
    # ==========================================
    # SECCIÓN 7: VISTA PREVIA DE COTIZACIÓN
    # ==========================================
    if st.session_state.get('mostrar_cotizacion', False):
        st.markdown("---")
        st.markdown("## 📄 VISTA PREVIA DE COTIZACIÓN")
        
        # Calcular totales
        total_general = sum(item['costo_total'] for item in st.session_state.items)
        
        # Mostrar datos del cliente
        st.markdown(f"""
        **Cliente:** {st.session_state.cliente_datos.get('nombre', '')}  
        **Teléfono:** {st.session_state.cliente_datos.get('telefono', '')}  
        **Vehículo:** {st.session_state.cliente_datos.get('vehiculo', '')} {st.session_state.cliente_datos.get('ano', '')}  
        **Fecha:** {datetime.now().strftime('%d/%m/%Y')}  
        **Válido hasta:** {(datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')}
        """)
        
        # Tabla de ítems
        st.markdown("### Detalle de Repuestos")
        
        for i, item in enumerate(st.session_state.items):
            st.markdown(f"""
            | Campo | Valor |
            |-------|-------|
            | Descripción | {item['descripcion']} |
            | N° Parte | {item['parte']} |
            | Marca | {item['marca']} |
            | Garantía | {item['garantia']} |
            | Cantidad | {item['cantidad']} |
            | Envío | {item['envio_tipo']} |
            | Origen | {item['origen']} |
            | Tiempo Entrega | {item['tiempo_entrega']} |
            | **Costo Unitario** | **${item['costo_unitario']:.2f}** |
            | **Costo Total** | **${item['costo_total']:.2f}** |
            """)
            st.markdown("---")
        
        # Totales
        st.markdown(f"""
        ### Totales
        | Concepto | Valor |
        |----------|-------|
        | Sub-Total | ${total_general:.2f} |
        | I.V.A. 16% | $0.00 |
        | **Total a Pagar** | **${total_general:.2f}** |
        """)
        
        # Botones de descarga
        st.markdown("### 📥 Descargar Cotización")
        
        download_col1, download_col2 = st.columns(2)
        with download_col1:
            st.info("🔜 Generación de PDF próximamente")
        with download_col2:
            st.info("🔜 Generación de PNG próximamente")
