"""
Panel de Analista - LogiPartVE Pro v7.0
Interfaz principal para generar cotizaciones de repuestos
Flujo: Completar ítem → Ver resultado → Agregar otro ítem
"""
import streamlit as st

from services.url_validator import URLValidator
from services.calculation_service import CalculationService
from services.ai_service import AIService
from services.ai_parser import AIParser


def render_analyst_panel():
    """Renderiza el panel de analista para generar cotizaciones"""
    
    st.title("📋 Panel de Analista")
    st.markdown("---")
    
    # Inicializar estado de ítems completados PRIMERO
    if 'completed_items' not in st.session_state:
        st.session_state.completed_items = []
    
    # Inicializar estado del ítem actual
    if 'current_item_analyzed' not in st.session_state:
        st.session_state.current_item_analyzed = False
    
    # Inicializar servicios (con manejo de errores)
    try:
        if 'url_validator' not in st.session_state:
            st.session_state.url_validator = URLValidator()
        if 'calc_service' not in st.session_state:
            st.session_state.calc_service = CalculationService()
        if 'ai_service' not in st.session_state:
            st.session_state.ai_service = AIService()
        if 'ai_parser' not in st.session_state:
            st.session_state.ai_parser = AIParser()
    except Exception as e:
        st.error(f"Error al inicializar servicios: {str(e)}")
        st.info("Algunas funcionalidades pueden estar limitadas.")
    
    # SECCIÓN 1: DATOS DEL CLIENTE (solo la primera vez)
    if len(st.session_state.completed_items) == 0:
        st.subheader("👤 Datos del Cliente")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            cliente_nombre = st.text_input(
                "Nombre del Cliente",
                key="cliente_nombre"
            )
        
        with col2:
            cliente_email = st.text_input(
                "Email",
                key="cliente_email"
            )
        
        with col3:
            cliente_telefono = st.text_input(
                "Teléfono",
                key="cliente_telefono"
            )
        
        st.markdown("---")
        
        # SECCIÓN 2: DATOS DE ENVÍO (solo la primera vez)
        st.subheader("🚢 Datos de Envío")
        col1, col2 = st.columns(2)
        
        with col1:
            origen = st.selectbox(
                "Puerto de Origen",
                options=["Miami", "Madrid"],
                key="origen"
            )
        
        with col2:
            if origen == "Miami":
                tipo_envio = st.selectbox(
                    "Tipo de Envío",
                    options=["Aéreo", "Marítimo"],
                    key="tipo_envio"
                )
            else:  # Madrid
                tipo_envio = "Aéreo"
                st.selectbox(
                    "Tipo de Envío",
                    options=["Aéreo"],
                    key="tipo_envio_madrid",
                    disabled=True
                )
        
        st.markdown("---")
    else:
        # Recuperar datos guardados
        cliente_nombre = st.session_state.get("cliente_nombre", "")
        cliente_email = st.session_state.get("cliente_email", "")
        cliente_telefono = st.session_state.get("cliente_telefono", "")
        origen = st.session_state.get("origen", "Miami")
        tipo_envio = st.session_state.get("tipo_envio", "Aéreo")
    
    # SECCIÓN 3: ÍTEM ACTUAL
    item_number = len(st.session_state.completed_items) + 1
    st.subheader(f"📦 Ítem #{item_number}")
    
    # Si ya se analizó el ítem actual, mostrar resultado
    if st.session_state.current_item_analyzed and 'current_item_result' in st.session_state:
        render_item_result(st.session_state.current_item_result, item_number)
        
        # Botón para agregar otro ítem
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("➕ AGREGAR OTRO ÍTEM", type="primary", use_container_width=True):
                # Guardar ítem actual en completados
                st.session_state.completed_items.append(st.session_state.current_item_result)
                # Resetear estado
                st.session_state.current_item_analyzed = False
                if 'current_item_result' in st.session_state:
                    del st.session_state.current_item_result
                st.rerun()
        
        st.markdown("---")
        
        # Botón para finalizar cotización
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ FINALIZAR COTIZACIÓN", type="secondary", use_container_width=True):
                # Guardar último ítem
                st.session_state.completed_items.append(st.session_state.current_item_result)
                st.session_state.current_item_analyzed = False
                if 'current_item_result' in st.session_state:
                    del st.session_state.current_item_result
                st.rerun()
    
    else:
        # Mostrar formulario para nuevo ítem
        render_item_form(origen, tipo_envio, item_number)
    
    # SECCIÓN 4: RESUMEN DE ÍTEMS COMPLETADOS
    if len(st.session_state.completed_items) > 0 and not st.session_state.current_item_analyzed:
        st.markdown("---")
        render_summary(st.session_state.completed_items, origen, tipo_envio)


def render_item_form(origen, tipo_envio, item_number):
    """Renderiza el formulario para un ítem"""
    
    # URL Opcional
    st.markdown("### 🔗 Cotización por URL (Opcional)")
    url = st.text_input(
        "Pegue aquí el enlace del producto (opcional)",
        placeholder="https://www.amazon.com/...",
        key=f"url_{item_number}"
    )
    
    st.markdown("---")
    
    # Información del Repuesto
    st.markdown("### 📝 Información del Repuesto")
    
    col1, col2 = st.columns(2)
    
    with col1:
        vehiculo = st.text_input(
            "Vehículo",
            placeholder="Ej: Ford F-150 2020",
            key=f"vehiculo_{item_number}"
        )
        
        repuesto = st.text_input(
            "Repuesto",
            placeholder="Ej: Bomba de agua",
            key=f"repuesto_{item_number}"
        )
    
    with col2:
        cantidad = st.number_input(
            "Cantidad",
            min_value=1,
            value=1,
            step=1,
            key=f"cantidad_{item_number}"
        )
        
        numero_parte = st.text_input(
            "N° Parte",
            placeholder="Ej: 12345-ABC",
            key=f"numero_parte_{item_number}"
        )
    
    st.markdown("---")
    
    # Botón para analizar
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 ANALIZAR CON IA", type="primary", use_container_width=True, key=f"analyze_{item_number}"):
            # Validar campos requeridos
            if not vehiculo or not repuesto:
                st.error("⚠️ Por favor completa al menos Vehículo y Repuesto")
                return
            
            # Validar URL si se proporcionó
            url_valida = False
            if url:
                with st.spinner("Validando URL..."):
                    try:
                        if 'url_validator' in st.session_state:
                            validation_result = st.session_state.url_validator.validate(url)
                            if validation_result['whitelisted']:
                                url_valida = True
                                st.success(f"✅ URL válida: {validation_result['domain']}")
                            else:
                                st.error(f"❌ {validation_result['message']}")
                                return
                        else:
                            st.warning("⚠️ Validador de URL no disponible. Continuando sin validación...")
                            url_valida = True  # Asumir válida si no hay validador
                    except Exception as e:
                        st.error(f"❌ Error al validar URL: {str(e)}")
                        st.info("💡 Continuando sin validación de URL...")
                        url_valida = True  # Continuar de todos modos
            
            # Analizar con IA
            with st.spinner("🤖 Analizando con IA..."):
                try:
                    # Llamar a IA con el método correcto
                    if url_valida and url:
                        ai_result = st.session_state.ai_service.analyze_part_with_url(
                            vehiculo, repuesto, numero_parte, url, origen, tipo_envio
                        )
                    else:
                        ai_result = st.session_state.ai_service.analyze_part_without_url(
                            vehiculo, repuesto, numero_parte, origen, tipo_envio
                        )
                    
                    # Verificar si hubo error
                    if not ai_result.get('success', False):
                        st.error(f"❌ Error en IA: {ai_result.get('error', 'Error desconocido')}")
                        return
                    
                    ai_response = ai_result['response']
                    
                    # Parsear respuesta
                    parsed_data = st.session_state.ai_parser.parse_response(ai_response)
                    
                    # Validar respuesta
                    validation = st.session_state.ai_parser.validate_response(parsed_data)
                    
                    if validation['valid']:
                        # Convertir kg a lb (1 kg = 2.20462 lb)
                        peso_lb = parsed_data['peso_kg'] * 2.20462 if parsed_data['peso_kg'] else 10.0
                        
                        # Convertir cm a pulgadas (1 cm = 0.393701 in)
                        largo_in = parsed_data['dimensiones']['largo_cm'] * 0.393701 if parsed_data['dimensiones']['largo_cm'] else 12.0
                        ancho_in = parsed_data['dimensiones']['ancho_cm'] * 0.393701 if parsed_data['dimensiones']['ancho_cm'] else 12.0
                        alto_in = parsed_data['dimensiones']['alto_cm'] * 0.393701 if parsed_data['dimensiones']['alto_cm'] else 12.0
                        
                        # Calcular peso volumétrico
                        peso_vol = st.session_state.calc_service.calcular_peso_volumetrico(
                            largo_in, ancho_in, alto_in
                        )
                        
                        # Calcular costo de flete
                        costo_flete = st.session_state.calc_service.calcular_costo_flete(
                            peso_lb,
                            peso_vol,
                            origen,
                            tipo_envio
                        )
                        
                        # Guardar resultado
                        st.session_state.current_item_result = {
                            'vehiculo': vehiculo,
                            'repuesto': repuesto,
                            'cantidad': cantidad,
                            'numero_parte': numero_parte,
                            'url': url if url_valida else None,
                            'descripcion': parsed_data['descripcion'],
                            'peso': peso_lb,
                            'dimensiones': f"{largo_in:.1f} x {ancho_in:.1f} x {alto_in:.1f}",
                            'peso_volumetrico': peso_vol,
                            'embalaje': f"{parsed_data['embalaje']['largo_cm']:.0f} x {parsed_data['embalaje']['ancho_cm']:.0f} x {parsed_data['embalaje']['alto_cm']:.0f} cm" if parsed_data['embalaje']['largo_cm'] else 'N/A',
                            'confianza': parsed_data['nivel_confianza'] or 'MEDIA',
                            'costo_flete': costo_flete,
                            'origen': origen,
                            'tipo_envio': tipo_envio,
                            'raw_response': parsed_data['raw_response']
                        }
                        
                        # Mostrar advertencias si las hay
                        if validation['warnings']:
                            for warning in validation['warnings']:
                                st.warning(f"⚠️ {warning}")
                        
                        st.session_state.current_item_analyzed = True
                        st.rerun()
                    else:
                        st.error("❌ No se pudo obtener información completa del repuesto")
                        st.error(f"Campos faltantes: {', '.join(validation['missing_fields'])}")
                        st.info("💡 Intenta agregar más detalles o una URL válida")
                        
                        # Mostrar respuesta cruda para debugging
                        with st.expander("🔍 Ver respuesta de IA (para debugging)"):
                            st.text(parsed_data['raw_response'])
                
                except Exception as e:
                    st.error(f"❌ Error al analizar: {str(e)}")


def render_item_result(item, item_number):
    """Renderiza el resultado de un ítem analizado"""
    
    st.success(f"✅ Ítem #{item_number} analizado exitosamente")
    
    # Información del repuesto
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📦 Información:**")
        st.write(f"**Vehículo:** {item['vehiculo']}")
        st.write(f"**Repuesto:** {item['repuesto']}")
        st.write(f"**Cantidad:** {item['cantidad']}")
        st.write(f"**N° Parte:** {item['numero_parte']}")
        if item['url']:
            st.write(f"**URL:** {item['url']}")
    
    with col2:
        st.markdown("**📊 Análisis IA:**")
        st.write(f"**Descripción:** {item['descripcion']}")
        st.write(f"**Peso:** {item['peso']} lb")
        st.write(f"**Dimensiones:** {item['dimensiones']} in")
        st.write(f"**Peso Vol.:** {item['peso_volumetrico']:.2f}")
        st.write(f"**Embalaje:** {item['embalaje']}")
        st.write(f"**Confianza:** {item['confianza']}")
    
    # Precio
    st.markdown("---")
    st.markdown(f"### 💰 Precio de Flete: **${item['costo_flete']:.2f}**")
    st.caption(f"Origen: {item['origen']} | Tipo: {item['tipo_envio']}")


def render_summary(completed_items, origen, tipo_envio):
    """Renderiza el resumen de todos los ítems completados"""
    
    st.subheader("📊 Resumen de Cotización")
    
    # Tabla de ítems
    st.markdown("### Ítems cotizados:")
    
    total = 0
    for idx, item in enumerate(completed_items, 1):
        with st.expander(f"Ítem #{idx}: {item['repuesto']} - ${item['costo_flete']:.2f}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Vehículo:** {item['vehiculo']}")
                st.write(f"**Repuesto:** {item['repuesto']}")
                st.write(f"**Cantidad:** {item['cantidad']}")
                st.write(f"**N° Parte:** {item['numero_parte']}")
            
            with col2:
                st.write(f"**Peso:** {item['peso']} lb")
                st.write(f"**Dimensiones:** {item['dimensiones']} in")
                st.write(f"**Embalaje:** {item['embalaje']}")
                st.write(f"**Confianza:** {item['confianza']}")
        
        total += item['costo_flete']
    
    # Total
    st.markdown("---")
    st.markdown(f"## 💰 TOTAL DE LA COTIZACIÓN: **${total:.2f}**")
    st.caption(f"Origen: {origen} | Tipo de Envío: {tipo_envio} | Total de ítems: {len(completed_items)}")
    
    # Botones de acción
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 GUARDAR COTIZACIÓN", type="primary", use_container_width=True):
            st.success("✅ Cotización guardada (funcionalidad pendiente)")
    
    with col2:
        if st.button("📄 GENERAR PDF", type="secondary", use_container_width=True):
            st.info("📄 Generación de PDF (funcionalidad pendiente)")
    
    with col3:
        if st.button("🔄 NUEVA COTIZACIÓN", type="secondary", use_container_width=True):
            # Limpiar todo
            st.session_state.completed_items = []
            st.session_state.current_item_analyzed = False
            if 'current_item_result' in st.session_state:
                del st.session_state.current_item_result
            st.rerun()
