"""
Panel de Analista - LogiPartVE Pro v7.0
Interfaz principal para generar cotizaciones de repuestos
"""
import streamlit as st
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.url_validator import URLValidator
from services.calculation_service import CalculationService
from services.ai_service import AIService
from services.ai_parser import AIParser


def render_analyst_panel():
    """Renderiza el panel de analista para generar cotizaciones"""
    
    st.title("📋 Panel de Analista")
    st.markdown("---")
    
    # Inicializar servicios
    if 'url_validator' not in st.session_state:
        st.session_state.url_validator = URLValidator()
    if 'calc_service' not in st.session_state:
        st.session_state.calc_service = CalculationService()
    if 'ai_service' not in st.session_state:
        st.session_state.ai_service = AIService()
    if 'ai_parser' not in st.session_state:
        st.session_state.ai_parser = AIParser()
    
    # Inicializar estado de ítems
    if 'items' not in st.session_state:
        st.session_state.items = []
    
    # SECCIÓN 1: DATOS DEL CLIENTE
    st.subheader("👤 Datos del Cliente")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        cliente_nombre = st.text_input("Nombre del Cliente", key="cliente_nombre")
    with col2:
        cliente_email = st.text_input("Email", key="cliente_email")
    with col3:
        cliente_telefono = st.text_input("Teléfono", key="cliente_telefono")
    
    st.markdown("---")
    
    # SECCIÓN 2: DATOS DE ENVÍO
    st.subheader("🚢 Datos de Envío")
    col1, col2 = st.columns(2)
    
    with col1:
        origen = st.selectbox(
            "Puerto de Origen",
            ["Miami", "Madrid", "Dubai"],
            key="origen_envio"
        )
    with col2:
        tipo_envio = st.selectbox(
            "Tipo de Envío",
            ["Aéreo", "Marítimo"],
            key="tipo_envio"
        )
    
    st.markdown("---")
    
    # SECCIÓN 3: ÍTEMS DE COTIZACIÓN
    st.subheader("📦 Ítems de la Cotización")
    
    # Botón para agregar nuevo ítem
    if st.button("➕ Agregar Nuevo Ítem", type="primary"):
        st.session_state.items.append({
            'id': len(st.session_state.items),
            'vehiculo': '',
            'repuesto': '',
            'numero_parte': '',
            'url': '',
            'cantidad': 1,
            'analizado': False,
            'resultado': None
        })
        st.rerun()
    
    # Renderizar cada ítem
    if len(st.session_state.items) == 0:
        st.info("👆 Haz clic en 'Agregar Nuevo Ítem' para comenzar")
    else:
        for idx, item in enumerate(st.session_state.items):
            render_item_form(idx, item, origen, tipo_envio)
    
    st.markdown("---")
    
    # SECCIÓN 4: RESUMEN Y TOTALES
    if len(st.session_state.items) > 0:
        render_summary()
    
    # SECCIÓN 5: ACCIONES
    if len(st.session_state.items) > 0:
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🗑️ Limpiar Todo", type="secondary"):
                st.session_state.items = []
                st.rerun()
        
        with col2:
            if st.button("💾 Guardar Cotización", type="primary"):
                st.info("Funcionalidad de guardado en desarrollo (Fase 4)")
        
        with col3:
            if st.button("📄 Generar PDF", type="primary"):
                st.info("Funcionalidad de PDF en desarrollo (Fase 5)")


def render_item_form(idx, item, origen, tipo_envio):
    """Renderiza el formulario para un ítem individual"""
    
    with st.expander(f"📦 Ítem #{idx + 1}", expanded=not item['analizado']):
        col1, col2 = st.columns([5, 1])
        
        with col2:
            if st.button("🗑️", key=f"delete_{idx}", help="Eliminar ítem"):
                st.session_state.items.pop(idx)
                st.rerun()
        
        # Formulario de entrada
        col1, col2 = st.columns(2)
        
        with col1:
            vehiculo = st.text_input(
                "Vehículo",
                value=item['vehiculo'],
                key=f"vehiculo_{idx}",
                placeholder="Ej: TOYOTA COROLLA 2020"
            )
            repuesto = st.text_input(
                "Repuesto",
                value=item['repuesto'],
                key=f"repuesto_{idx}",
                placeholder="Ej: FILTRO DE ACEITE"
            )
        
        with col2:
            numero_parte = st.text_input(
                "Número de Parte",
                value=item['numero_parte'],
                key=f"numero_parte_{idx}",
                placeholder="Ej: 90915-YZZD2"
            )
            cantidad = st.number_input(
                "Cantidad",
                min_value=1,
                value=item['cantidad'],
                key=f"cantidad_{idx}"
            )
        
        url = st.text_input(
            "URL del Producto (Opcional)",
            value=item['url'],
            key=f"url_{idx}",
            placeholder="https://www.amazon.com/..."
        )
        
        # Validar URL si se proporciona
        if url:
            validation = st.session_state.url_validator.validate(url)
            if not validation['whitelisted']:
                st.warning(f"⚠️ {validation['message']}")
        
        # Botón para analizar
        if st.button(f"🚀 Analizar con IA", key=f"analyze_{idx}", type="primary"):
            if not vehiculo or not repuesto or not numero_parte:
                st.error("❌ Por favor completa los campos: Vehículo, Repuesto y Número de Parte")
            else:
                analyze_item(idx, vehiculo, repuesto, numero_parte, url, cantidad, origen, tipo_envio)
        
        # Mostrar resultados si ya fue analizado
        if item['analizado'] and item['resultado']:
            render_item_results(item['resultado'])


def analyze_item(idx, vehiculo, repuesto, numero_parte, url, cantidad, origen, tipo_envio):
    """Analiza un ítem usando los servicios de IA"""
    
    with st.spinner("🔍 Analizando con IA..."):
        # Llamar al servicio de IA
        if url:
            result = st.session_state.ai_service.analyze_part_with_url(
                vehiculo, repuesto, numero_parte, url, origen, tipo_envio
            )
        else:
            result = st.session_state.ai_service.analyze_part_without_url(
                vehiculo, repuesto, numero_parte, origen, tipo_envio
            )
        
        if not result['success']:
            st.error(f"❌ Error: {result.get('error', 'Error desconocido')}")
            return
        
        # Parsear la respuesta
        parsed_data = st.session_state.ai_parser.parse_response(result['response'])
        
        # Validar respuesta
        validation = st.session_state.ai_parser.validate_response(parsed_data)
        
        # Calcular costos si tenemos datos
        if parsed_data['peso_kg'] and all(parsed_data['embalaje'].values()):
            peso_vol = st.session_state.calc_service.calculate_volumetric_weight(
                parsed_data['embalaje']['largo_cm'],
                parsed_data['embalaje']['ancho_cm'],
                parsed_data['embalaje']['alto_cm']
            )
            
            freight_calc = st.session_state.calc_service.calculate_freight_cost(
                origen,
                tipo_envio,
                parsed_data['peso_kg'],
                peso_vol,
                parsed_data['embalaje']['largo_cm'],
                parsed_data['embalaje']['ancho_cm'],
                parsed_data['embalaje']['alto_cm']
            )
            
            parsed_data['peso_volumetrico'] = peso_vol
            parsed_data['freight_cost'] = freight_calc.get('freight_cost', 0)
            parsed_data['freight_details'] = freight_calc
        
        # Guardar resultado
        st.session_state.items[idx]['vehiculo'] = vehiculo
        st.session_state.items[idx]['repuesto'] = repuesto
        st.session_state.items[idx]['numero_parte'] = numero_parte
        st.session_state.items[idx]['url'] = url
        st.session_state.items[idx]['cantidad'] = cantidad
        st.session_state.items[idx]['analizado'] = True
        st.session_state.items[idx]['resultado'] = {
            'parsed_data': parsed_data,
            'validation': validation,
            'ai_provider': result['provider'],
            'raw_response': result['response']
        }
        
        st.rerun()


def render_item_results(resultado):
    """Renderiza los resultados del análisis de un ítem"""
    
    st.markdown("### 📊 Resultados del Análisis")
    
    parsed = resultado['parsed_data']
    validation = resultado['validation']
    
    # Proveedor de IA
    provider_emoji = "🤖" if resultado['ai_provider'] == 'gemini' else "🧠"
    st.caption(f"{provider_emoji} Analizado con: {resultado['ai_provider'].upper()}")
    
    # Advertencias
    if validation['warnings']:
        for warning in validation['warnings']:
            st.warning(f"⚠️ {warning}")
    
    # Datos principales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Peso Real", f"{parsed['peso_kg'] or 0} kg")
    with col2:
        st.metric("Peso Volumétrico", f"{parsed.get('peso_volumetrico', 0):.2f} kg")
    with col3:
        if 'freight_cost' in parsed:
            st.metric("Costo Flete", f"${parsed['freight_cost']:.2f}")
    
    # Descripción
    if parsed['descripcion']:
        st.text_area("Descripción", parsed['descripcion'], height=100, disabled=True)
    
    # Dimensiones
    col1, col2 = st.columns(2)
    
    with col1:
        if any(parsed['dimensiones'].values()):
            st.write("**Dimensiones del Producto:**")
            st.write(f"📏 {parsed['dimensiones']['largo_cm']} × {parsed['dimensiones']['ancho_cm']} × {parsed['dimensiones']['alto_cm']} cm")
    
    with col2:
        if any(parsed['embalaje'].values()):
            st.write("**Dimensiones del Embalaje:**")
            st.write(f"📦 {parsed['embalaje']['largo_cm']} × {parsed['embalaje']['ancho_cm']} × {parsed['embalaje']['alto_cm']} cm")
    
    # Números de parte alternativos
    if parsed['numeros_parte_alternativos']:
        st.write("**Números de Parte Alternativos:**")
        st.write(", ".join(parsed['numeros_parte_alternativos']))
    
    # Nivel de confianza
    if parsed['nivel_confianza']:
        confidence_color = {
            'ALTA': '🟢',
            'MEDIA': '🟡',
            'BAJA': '🔴'
        }
        st.write(f"**Nivel de Confianza:** {confidence_color.get(parsed['nivel_confianza'], '⚪')} {parsed['nivel_confianza']}")
    
    # Sitios consultados
    if parsed['sitios_consultados']:
        st.write("**Sitios Consultados:**")
        st.write(", ".join(parsed['sitios_consultados']))
    
    # Ver respuesta completa
    with st.expander("Ver Respuesta Completa de la IA"):
        st.text(resultado['raw_response'])


def render_summary():
    """Renderiza el resumen de la cotización"""
    
    st.subheader("📊 Resumen de la Cotización")
    
    total_items = len(st.session_state.items)
    items_analizados = sum(1 for item in st.session_state.items if item['analizado'])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Ítems", total_items)
    
    with col2:
        st.metric("Analizados", items_analizados)
    
    # Calcular totales
    total_peso = 0
    total_flete = 0
    
    for item in st.session_state.items:
        if item['analizado'] and item['resultado']:
            parsed = item['resultado']['parsed_data']
            cantidad = item['cantidad']
            
            if parsed['peso_kg']:
                total_peso += parsed['peso_kg'] * cantidad
            
            if 'freight_cost' in parsed:
                total_flete += parsed['freight_cost'] * cantidad
    
    with col3:
        st.metric("Peso Total", f"{total_peso:.2f} kg")
    
    with col4:
        st.metric("Flete Total", f"${total_flete:.2f}")
    
    # Barra de progreso
    if total_items > 0:
        progreso = items_analizados / total_items
        st.progress(progreso, text=f"Progreso: {items_analizados}/{total_items} ítems analizados")
