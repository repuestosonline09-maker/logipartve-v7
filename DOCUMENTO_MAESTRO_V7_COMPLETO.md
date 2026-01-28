# 📋 DOCUMENTO MAESTRO - LogiPartVE Pro v7.0

## 🎯 HOJA DE RUTA DEFINITIVA

**Fecha de creación:** 27 de Enero de 2026  
**Versión:** 1.0 - Consolidación Completa  
**Estado:** Documento de Referencia Oficial

---

## 📊 RESUMEN EJECUTIVO

Este documento consolida TODOS los requerimientos, funcionalidades, decisiones y tareas discutidas para el desarrollo de LogiPartVE Pro v7.0, organizadas por prioridad y orden de ejecución.

**Objetivo Principal:** Crear una aplicación empresarial de cotización de repuestos que combine:
- La funcionalidad de IA robusta de v6.2.2
- Una arquitectura empresarial multi-usuario
- Gestión administrativa completa
- Historial y reportes avanzados

---

## ✅ ESTADO ACTUAL (27/01/2026)

### COMPLETADO ✅

**Fase 1: Sistema de Autenticación (COMPLETA)**
- ✅ Login con usuario y contraseña
- ✅ Hasheo de contraseñas con bcrypt
- ✅ Roles de usuario (Admin/Analista)
- ✅ Sesión persistente
- ✅ Protección de rutas por rol
- ✅ Diseño responsive del login
- ✅ Logo oficial de LogiPartVE optimizado (60px móvil, 120px desktop)

**Fase 2: Panel de Administración (COMPLETA)**
- ✅ Gestión de Usuarios (crear, editar, cambiar contraseña, eliminar)
- ✅ Lista de usuarios con detalles
- ✅ Configuración del Sistema:
  - ✅ Diferencial de Cambio Diario (25%)
  - ✅ Impuesto Empresa Americana (7%)
  - ✅ IVA Venezuela (16%)
  - ✅ Manejo Nacional ($18)
  - ✅ Factores de Ganancia (1.4285, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10)
  - ✅ Opciones de Garantías (15 días, 30 días, 45 días, 3 meses, 6 meses)
  - ✅ Términos y Condiciones (editable)
- ✅ Reportes y Estadísticas básicas
- ✅ Base de Datos SQLite con 7 tablas

**Infraestructura:**
- ✅ Repositorio GitHub: `logipartve-v7`
- ✅ Despliegue en Streamlit Cloud: https://logipartve-v7.streamlit.app/
- ✅ Disponible 24/7 sin hibernación
- ✅ Actualizaciones automáticas desde GitHub

### PENDIENTE ⏳

**Fase 3: Panel de Analista + Integración de IA (EN PROGRESO)**
**Fase 4: Gestión de URLs Permitidas**
**Fase 5: Historial y Generación de PDF**
**Fase 6: Búsqueda y Filtros Avanzados**
**Fase 7: Reportes Avanzados**

---

## 🚨 PRIORIDAD CRÍTICA - TAREAS INMEDIATAS

### 1. AGREGAR TARIFAS DE FLETE AL PANEL DE ADMIN ⚠️ URGENTE

**Problema:** v7.0 NO tiene gestión de tarifas de flete, pero v6.2.2 SÍ la tiene en el sidebar.

**Solución:** Agregar sección "Tarifas de Flete" en Panel de Admin → Configuración del Sistema

**Campos requeridos:**
- Miami Aéreo ($/lb): $9 por defecto
- Miami Marítimo ($/ft³): $40 por defecto
- Madrid Aéreo ($/kg): $25 por defecto

**Tabla de BD:** Crear tabla `tarifas_flete` o agregar a tabla `configuracion`

**Estimación:** 30 minutos

---

## 📋 PLAN DE TRABAJO DETALLADO

### FASE 3: PANEL DE ANALISTA + INTEGRACIÓN DE IA

**Prioridad:** 🔴 ALTA - CRÍTICA  
**Duración estimada:** 4-6 horas  
**Dependencias:** Tarifas de flete agregadas

#### 3.1. Crear Servicios Base (2 horas)

**3.1.1. Servicio de Validación de URLs** (`/services/url_validator.py`)

**Funcionalidades:**
- Validar URL contra lista blanca (25 páginas + fridayparts.com)
- Expandir URLs acortadas (a.co, amzn.to, ebay.to, bit.ly, etc.)
- Detectar puerto de salida automáticamente (Miami/Madrid)
- Caché de URLs expandidas
- Timeout de 5 segundos

**Migrar de v6.2.2:**
- Función `expandir_url_acortada()` (líneas 179-206)
- Función `validar_url_soportada()` (líneas 220-240)
- Diccionario `PAGINAS_SOPORTADAS` (líneas 148-177)

**3.1.2. Servicio de IA** (`/services/ai_service.py`)

**Funcionalidades:**
- Integración con Gemini 2.0 Flash
- Prompts de IA entrenados (CON URL y SIN URL)
- Validación de compatibilidad vehículo-repuesto
- Validación de número de parte
- Categorización de repuestos (9 categorías)
- Diseño de embalaje reforzado
- Cálculo de peso total (neto + embalaje 30-40%)
- Análisis logístico

**Migrar de v6.2.2:**
- Prompts completos (líneas 380-654) - **NO MODIFICAR**
- Integración con Gemini (líneas 656-665)
- Manejo de errores

**Categorías de Repuestos:**
1. Motores y Transmisiones (pesados, frágiles)
2. Piezas de Suspensión (medianas, robustas)
3. Sistemas de Frenos (pequeñas, críticas)
4. Componentes Eléctricos (pequeños, delicados)
5. Piezas de Carrocería (grandes, ligeras)
6. Accesorios de Interior (medianos, frágiles)
7. Sistemas de Escape (largos, pesados)
8. Filtros y Fluidos (pequeños, líquidos)
9. Neumáticos y Llantas (grandes, pesados)

**3.1.3. Servicio de Cálculo** (`/services/calculation_service.py`)

**Funcionalidades:**
- Cálculo de peso volumétrico: vol_cm3 / 5000
- Cálculo de flete por origen y tipo:
  - **Miami Marítimo:** Facturable en ft³ (vol_cm3 / 28316.8) × tarifa
  - **Miami Aéreo:** Facturable en lb (max(peso_real, peso_vol) × 2.20462) × tarifa
  - **Madrid Aéreo:** Facturable en kg (max(peso_real, peso_vol)) × tarifa
- Tarifa mínima: $25 USD
- Leer tarifas desde base de datos

**Migrar de v6.2.2:**
- Función `calcular_logistica()` (líneas 286-333) - **MANTENER FÓRMULAS EXACTAS**

**3.1.4. Servicio de Parsing de IA** (`/services/ai_parser.py`)

**Funcionalidades:**
- Extraer datos de respuesta de IA
- Parsing de formato estructurado:
  ```
  URL_DATOS_EXTRAIDOS: [descripción]
  VALIDACION_NUMERO_PARTE: [comparación]
  AUDITORIA_COMPATIBILIDAD: [análisis técnico]
  ESTRATEGIA_LOGISTICA: [estrategia]
  VALORES: Largo:[X], Ancho:[Y], Alto:[Z], PesoTotalBruto:[W]
  ```
- Extracción con regex
- Validaciones de seguridad:
  - Dimensiones mínimas: 3 cm
  - Dimensiones máximas: 300 cm
  - Proporción máxima: 50:1 (evita cajas ultra-planas)

**Migrar de v6.2.2:**
- Función de extracción (líneas 673-743)
- Validaciones (líneas 699-707)

#### 3.2. Crear Vista de Cotización (2 horas)

**3.2.1. Formulario de Cotización** (`/views/quotation_view.py`)

**Secciones:**

**A. Datos del Cliente** (Nuevo - No existe en v6.2.2)
- Nombre del Cliente (text input)
- Teléfono (text input)
- Email (text input, opcional)

**B. Cotización por URL (Opcional)**
- Campo: URL del producto (text input)
- Placeholder: "https://www.amazon.com/..."
- Botón de ayuda con lista de páginas soportadas
- Auto-detección de puerto de salida

**C. Información del Repuesto**
- Vehículo (text input)
- Repuesto (text input)
- Cantidad (number input, default: 1)
- N° Parte (text input)
- Origen (dropdown: Miami/Madrid) - Auto-detectado si hay URL
- Envío (dropdown: Aéreo/Marítimo)

**D. Botones de Acción**
- 🚀 GENERAR AUDITORÍA Y CONSOLIDACIÓN (principal)
- ➕ AGREGAR OTRO ITEM (secundario)
- 💾 GUARDAR COTIZACIÓN (secundario)
- 🗑️ NUEVA COTIZACIÓN (secundario)

**E. Resultados de IA**
- Caja de mensaje con URL_DATOS_EXTRAIDOS
- Caja de mensaje con VALIDACION_NUMERO_PARTE
- Caja de mensaje con AUDITORIA_COMPATIBILIDAD
- Caja de mensaje con ESTRATEGIA_LOGISTICA
- Caja de resultado con dimensiones y costo

**F. Calculadora Manual (Expandible)**
- Origen (dropdown: Miami/Madrid)
- Envío (dropdown: Aéreo/Marítimo)
- Largo (cm) (number input)
- Ancho (cm) (number input)
- Alto (cm) (number input)
- Peso Total (kg) (number input)
- Botón: 🧮 CALCULAR MANUALMENTE
- Botón: 🗑️ LIMPIAR

**Migrar de v6.2.2:**
- Estructura completa del formulario (líneas 342-778)
- Cajas de mensajes coloreadas (CSS líneas 16-142)
- Prevención de auto-scroll (JavaScript líneas 16-142)

#### 3.3. Integrar con Base de Datos (1 hora)

**3.3.1. Guardar Items de Cotización**

**Tabla:** `cotizacion_items`

**Campos:**
- id (INTEGER PRIMARY KEY)
- cotizacion_id (INTEGER, FK a cotizaciones)
- vehiculo (TEXT)
- repuesto (TEXT)
- numero_parte (TEXT)
- cantidad (INTEGER)
- url_producto (TEXT, nullable)
- origen (TEXT: 'Miami'/'Madrid')
- tipo_envio (TEXT: 'Aéreo'/'Marítimo')
- largo_cm (REAL)
- ancho_cm (REAL)
- alto_cm (REAL)
- peso_kg (REAL)
- peso_volumetrico_kg (REAL)
- costo_flete_usd (REAL)
- validacion_numero_parte (TEXT, nullable)
- auditoria_compatibilidad (TEXT, nullable)
- estrategia_logistica (TEXT, nullable)
- fecha_creacion (TIMESTAMP)

**3.3.2. Guardar Cotización Completa**

**Tabla:** `cotizaciones`

**Campos:**
- id (INTEGER PRIMARY KEY)
- numero_cotizacion (TEXT UNIQUE) - Formato: ANA001-0001 (analista + contador)
- analista_id (INTEGER, FK a usuarios)
- cliente_nombre (TEXT)
- cliente_telefono (TEXT)
- cliente_email (TEXT, nullable)
- estado (TEXT: 'borrador'/'enviada'/'aprobada'/'rechazada')
- total_items (INTEGER)
- total_flete_usd (REAL)
- total_general_usd (REAL)
- fecha_creacion (TIMESTAMP)
- fecha_modificacion (TIMESTAMP)

#### 3.4. Crear Sistema de Items Dinámicos (1 hora)

**Funcionalidad:** Permitir agregar múltiples items a una cotización

**Implementación:**
- Usar `st.session_state.items` como lista de items
- Botón "➕ AGREGAR OTRO ITEM" agrega item actual a la lista
- Mostrar tabla con items agregados
- Permitir eliminar items de la lista
- Botón "💾 GUARDAR COTIZACIÓN" guarda todos los items en BD

**Campos por Item:**
- Vehículo
- Repuesto
- N° Parte
- Cantidad
- Origen
- Envío
- Dimensiones (L x An x Al)
- Peso
- Costo Flete

---

### FASE 4: GESTIÓN DE URLs PERMITIDAS

**Prioridad:** 🟡 MEDIA  
**Duración estimada:** 2 horas  
**Dependencias:** Fase 3 completada

#### 4.1. Crear Tabla de Base de Datos

**Tabla:** `urls_permitidas`

```sql
CREATE TABLE urls_permitidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dominio TEXT NOT NULL UNIQUE,
    puerto_salida TEXT NOT NULL,  -- 'Miami' o 'Madrid'
    es_url_acortada BOOLEAN DEFAULT 0,
    activa BOOLEAN DEFAULT 1,
    prioridad TEXT DEFAULT 'Media',  -- 'Alta', 'Media', 'Baja'
    notas TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4.2. Importar URLs de v6.2.2

**Miami (15 páginas):**
1. amazon.com
2. a.co (acortada)
3. amzn.to (acortada)
4. ebay.com
5. ebay.us (acortada)
6. rockauto.com
7. partsouq.com
8. sparekorea.com
9. toyotapartsdeal.com
10. fordpartsgiant.com
11. gmpartsgiant.com
12. kiapartsnow.com
13. hyundaipartsdeal.com
14. vw.oempartsonline.com
15. fridayparts.com

**Madrid (10 páginas):**
1. ebay.es
2. ebay.to (acortada)
3. recambioscoches.es
4. autodoc.es
5. b-parts.com
6. desguacegomez.com
7. ovoko.es
8. es.aliexpress.com
9. ecooparts.com
10. amzn.eu (acortada)

#### 4.3. Crear Interfaz en Panel de Admin

**Ubicación:** Panel de Administración → Nueva tab "🌐 URLs Permitidas"

**Funcionalidades:**
- Listar todas las URLs con detalles
- Agregar nueva URL (dominio, puerto, es_acortada, prioridad, notas)
- Editar URL existente
- Activar/Desactivar URL (no eliminar, solo marcar como inactiva)
- Filtrar por puerto (Miami/Madrid)
- Filtrar por estado (Activa/Inactiva)

#### 4.4. Actualizar URLValidator

Modificar `/services/url_validator.py` para leer URLs desde base de datos en lugar de diccionario hardcodeado.

---

### FASE 5: HISTORIAL Y GENERACIÓN DE PDF

**Prioridad:** 🟡 MEDIA  
**Duración estimada:** 3-4 horas  
**Dependencias:** Fase 3 completada

#### 5.1. Crear Vista de Historial

**Ubicación:** Nueva opción en menú principal "📊 Mis Cotizaciones"

**Funcionalidades:**
- Listar cotizaciones del analista actual (o todas si es admin)
- Filtros:
  - Por estado (borrador/enviada/aprobada/rechazada)
  - Por fecha (rango)
  - Por cliente (nombre o teléfono)
  - Por N° cotizacion
- Búsqueda por texto (cliente, N° parte, vehículo)
- Ordenar por fecha (más reciente primero)
- Paginación (20 cotizaciones por página)

**Acciones por Cotización:**
- Ver detalles
- Editar (solo si estado = borrador)
- Generar PDF
- Duplicar
- Cambiar estado
- Eliminar (solo admin)

#### 5.2. Crear Generador de PDF

**Librería:** ReportLab (ya instalada)

**Estructura del PDF:**

**Página 1: Portada**
- Logo de LogiPartVE (centrado, grande)
- Título: "COTIZACIÓN DE REPUESTOS"
- N° Cotización: ANA001-0001
- Fecha: 27/01/2026
- Analista: Carlos Rodríguez

**Página 2: Datos del Cliente**
- Nombre del Cliente
- Teléfono
- Email

**Página 3+: Items de la Cotización**

Tabla con columnas:
- N°
- Vehículo
- Repuesto
- N° Parte
- Cantidad
- Origen
- Envío
- Dimensiones (L x An x Al cm)
- Peso (kg)
- Costo Flete (USD)

**Última Página: Totales y Términos**
- Total Items: X
- Total Flete: $XXX USD
- Total General: $XXX USD
- Términos y Condiciones (desde configuración)
- Footer: "LogiPartVE Pro v7.0 © 2026"

#### 5.3. Crear Sistema de Numeración Automática

**Formato:** `{INICIALES_ANALISTA}{CONTADOR}-{NUMERO_SECUENCIAL}`

**Ejemplo:** 
- Analista: Carlos Rodríguez → CR
- Contador de analista: 001
- Número secuencial: 0001
- Resultado: CR001-0001

**Implementación:**
- Agregar campo `contador_cotizaciones` a tabla `usuarios`
- Incrementar automáticamente al crear nueva cotización
- Generar número único combinando iniciales + contador + secuencial

---

### FASE 6: BÚSQUEDA Y FILTROS AVANZADOS

**Prioridad:** 🟢 BAJA  
**Duración estimada:** 2 horas  
**Dependencias:** Fase 5 completada

#### 6.1. Búsqueda Global

**Funcionalidad:** Buscar en todas las cotizaciones por cualquier campo

**Campos de búsqueda:**
- N° Cotización
- Cliente (nombre, teléfono, email)
- Vehículo
- Repuesto
- N° Parte
- Analista

**Implementación:**
- Input de búsqueda en parte superior
- Búsqueda en tiempo real (al escribir)
- Resaltar coincidencias en resultados

#### 6.2. Filtros Avanzados

**Filtros disponibles:**
- Rango de fechas (desde - hasta)
- Estado (borrador/enviada/aprobada/rechazada)
- Analista (solo admin)
- Origen (Miami/Madrid)
- Tipo de envío (Aéreo/Marítimo)
- Rango de monto (desde - hasta USD)

**Implementación:**
- Panel lateral con filtros
- Aplicar múltiples filtros simultáneamente
- Botón "Limpiar filtros"
- Guardar filtros favoritos

#### 6.3. Exportar a Excel

**Funcionalidad:** Exportar resultados de búsqueda/filtros a Excel

**Formato:**
- Hoja 1: Resumen de cotizaciones
- Hoja 2: Detalle de items
- Hoja 3: Estadísticas

**Librería:** openpyxl (ya instalada)

---

### FASE 7: REPORTES AVANZADOS

**Prioridad:** 🟢 BAJA  
**Duración estimada:** 3-4 horas  
**Dependencias:** Fase 5 completada

#### 7.1. Dashboard de Estadísticas

**Ubicación:** Panel de Administración → Reportes y Estadísticas (mejorado)

**Métricas:**
- Total de cotizaciones (por período)
- Total de items cotizados
- Monto total cotizado (USD)
- Cotizaciones por estado (gráfico de pastel)
- Cotizaciones por analista (gráfico de barras)
- Cotizaciones por origen (Miami vs Madrid)
- Cotizaciones por tipo de envío (Aéreo vs Marítimo)
- Tendencia de cotizaciones (gráfico de línea)

#### 7.2. Reportes de Productividad

**Por Analista:**
- Número de cotizaciones creadas
- Número de items cotizados
- Monto total cotizado
- Promedio de items por cotización
- Tasa de conversión (enviadas/aprobadas)
- Tiempo promedio de respuesta

**Por Período:**
- Cotizaciones por día/semana/mes
- Items más cotizados (top 10)
- Vehículos más cotizados (top 10)
- Repuestos más cotizados (top 10)
- Origen más usado (Miami vs Madrid)
- Tipo de envío más usado (Aéreo vs Marítimo)

#### 7.3. Gráficos Interactivos

**Librería:** Plotly (ya instalada)

**Gráficos:**
- Línea: Tendencia de cotizaciones en el tiempo
- Barras: Cotizaciones por analista
- Pastel: Cotizaciones por estado
- Barras horizontales: Top 10 repuestos cotizados
- Área: Monto total cotizado en el tiempo

---

## 🎨 MEJORAS DE UI/UX

### Diseño Responsive

**Prioridad:** 🟡 MEDIA  
**Estado:** Parcialmente implementado

**Pendiente:**
- Optimizar formulario de cotización para móvil
- Optimizar tabla de items para móvil
- Optimizar historial de cotizaciones para móvil

### Cajas de Mensajes Coloreadas

**Prioridad:** 🟡 MEDIA  
**Estado:** Pendiente

**Tipos:**
- `.estrategia` - Fondo azul claro
- `.warning` - Fondo amarillo claro
- `.success` - Fondo verde claro
- `.error` - Fondo rojo claro

**Migrar de v6.2.2:** CSS líneas 16-142

### Prevención de Auto-Scroll

**Prioridad:** 🟢 BAJA  
**Estado:** Pendiente

**Funcionalidad:** Evitar que la página haga scroll automático al actualizar

**Migrar de v6.2.2:** JavaScript líneas 16-142

---

## 🔧 CONFIGURACIONES Y VARIABLES

### Variables de Cálculo (Configurables en Panel de Admin)

**Tasas e Impuestos:**
- ✅ Diferencial de Cambio Diario: 25% (Y30 del Excel)
- ✅ Impuesto Empresa Americana: 7% (TAX del Excel)
- ✅ IVA Venezuela: 16%

**Costos y Márgenes:**
- ✅ Manejo Nacional: $18 USD
- ✅ Factores de Ganancia: 1.4285, 1.35, 1.30, 1.25, 1.20, 1.15, 1.10

**Tarifas de Flete:** ⚠️ PENDIENTE AGREGAR
- ⏳ Miami Aéreo: $9/lb
- ⏳ Miami Marítimo: $40/ft³
- ⏳ Madrid Aéreo: $25/kg

**Garantías:**
- ✅ 15 días, 30 días, 45 días, 3 meses, 6 meses

**Términos y Condiciones:**
- ✅ Texto editable en Panel de Admin

---

## 📐 FÓRMULAS DE CÁLCULO

### Peso Volumétrico

```
peso_volumetrico_kg = (largo_cm × ancho_cm × alto_cm) / 5000
```

### Costo de Flete

**Miami Marítimo:**
```
volumen_ft3 = volumen_cm3 / 28316.8
facturable = volumen_ft3
costo = facturable × tarifa_mia_maritimo
costo_final = max(costo, 25)  # Mínimo $25
```

**Miami Aéreo:**
```
peso_facturable_lb = max(peso_real_kg, peso_volumetrico_kg) × 2.20462
costo = peso_facturable_lb × tarifa_mia_aereo
costo_final = max(costo, 25)  # Mínimo $25
```

**Madrid Aéreo:**
```
peso_facturable_kg = max(peso_real_kg, peso_volumetrico_kg)
costo = peso_facturable_kg × tarifa_mad_aereo
costo_final = max(costo, 25)  # Mínimo $25
```

### Precio de Venta

**Precio en Dólares (USD):**
```
precio_usd = costo_item + flete + manejo + impuestos + margen
```

**Precio en Bolívares (Bs) - Solo para referencia interna:**
```
precio_bs = precio_usd × tasa_bcv × (1 + diferencial_cambio/100)
```

**Nota:** El PDF final solo muestra precio en USD

---

## 🗄️ ESTRUCTURA DE BASE DE DATOS

### Tablas Existentes (v7.0)

1. **usuarios** - Gestión de usuarios y autenticación
2. **configuracion** - Variables de configuración del sistema
3. **garantias** - Opciones de garantía disponibles
4. **terminos_condiciones** - Términos y condiciones editables
5. **sesiones** - Sesiones de usuario activas
6. **logs** - Registro de actividad del sistema
7. **reportes** - Reportes generados

### Tablas a Crear (Fase 3-5)

8. **tarifas_flete** - Tarifas de flete por origen y tipo
   - id, origen, tipo_envio, tarifa_usd, unidad, fecha_modificacion

9. **urls_permitidas** - Lista blanca de URLs para IA
   - id, dominio, puerto_salida, es_url_acortada, activa, prioridad, notas, fecha_creacion

10. **cotizaciones** - Cotizaciones creadas
    - id, numero_cotizacion, analista_id, cliente_nombre, cliente_telefono, cliente_email, estado, total_items, total_flete_usd, total_general_usd, fecha_creacion, fecha_modificacion

11. **cotizacion_items** - Items de cada cotización
    - id, cotizacion_id, vehiculo, repuesto, numero_parte, cantidad, url_producto, origen, tipo_envio, largo_cm, ancho_cm, alto_cm, peso_kg, peso_volumetrico_kg, costo_flete_usd, validacion_numero_parte, auditoria_compatibilidad, estrategia_logistica, fecha_creacion

12. **cache_repuestos** - Caché de repuestos consultados
    - id, numero_parte, vehiculo, repuesto, largo_cm, ancho_cm, alto_cm, peso_kg, url_fuente, fecha_creacion, fecha_ultimo_uso

---

## 📝 NOTAS IMPORTANTES

### Migración de v6.2.2

**LO QUE SE DEBE MIGRAR EXACTAMENTE:**
1. ✅ Prompts de IA (líneas 380-654) - **NO MODIFICAR**
2. ✅ Fórmulas de cálculo (líneas 286-333) - **MANTENER EXACTAS**
3. ✅ Validación de URLs (líneas 148-240)
4. ✅ Expansión de URLs acortadas (líneas 179-206)
5. ✅ Extracción de datos de IA (líneas 673-743)
6. ✅ CSS de cajas de mensajes (líneas 16-142)
7. ✅ JavaScript de prevención de scroll (líneas 16-142)

**LO QUE SE DEBE MEJORAR:**
1. ⚡ Modularizar código (servicios separados)
2. ⚡ Agregar autenticación multi-usuario
3. ⚡ Agregar base de datos (guardar cotizaciones)
4. ⚡ Agregar historial y búsqueda
5. ⚡ Agregar generación de PDF
6. ⚡ Agregar reportes y estadísticas
7. ⚡ Hacer configuración editable desde UI

### Metodología de Fallback

**Si no se encuentran dimensiones/peso en URL:**
1. NO aproximar valores
2. Aplicar inmediatamente "cotización clásica" (metodología estándar)
3. Usar datos validados en lugar de aproximaciones

### Validaciones de Seguridad

**Dimensiones:**
- Mínimo: 3 cm por lado
- Máximo: 300 cm por lado
- Proporción máxima: 50:1 (evita cajas ultra-planas)

**Alertas:**
- Dimensiones fuera de rango
- Proporciones sospechosas
- Peso volumétrico muy diferente al peso real

---

## 🎯 ORDEN DE EJECUCIÓN RECOMENDADO

### HOY (27/01/2026) - Sesión Actual

**1. AGREGAR TARIFAS DE FLETE** ⚠️ URGENTE (30 min)
   - Crear tabla `tarifas_flete`
   - Agregar sección en Panel de Admin
   - Insertar valores por defecto
   - Probar y desplegar

**2. CREAR SERVICIOS BASE** (2 horas)
   - URLValidator
   - AIService
   - CalculationService
   - AIParser

**3. CREAR FORMULARIO DE COTIZACIÓN** (2 horas)
   - Vista básica
   - Integración con servicios
   - Cajas de mensajes
   - Calculadora manual

**TOTAL HOY:** 4.5 horas

### MAÑANA (28/01/2026)

**4. INTEGRAR CON BASE DE DATOS** (1 hora)
   - Crear tablas cotizaciones y cotizacion_items
   - Guardar cotizaciones
   - Sistema de numeración automática

**5. SISTEMA DE ITEMS DINÁMICOS** (1 hora)
   - Agregar múltiples items
   - Tabla de items
   - Eliminar items

**6. PRUEBAS Y AJUSTES** (1 hora)
   - Probar flujo completo
   - Ajustar UI
   - Corregir bugs

**TOTAL MAÑANA:** 3 horas

### PRÓXIMA SEMANA

**7. GESTIÓN DE URLs PERMITIDAS** (2 horas)
**8. HISTORIAL Y PDF** (4 horas)
**9. BÚSQUEDA Y FILTROS** (2 horas)
**10. REPORTES AVANZADOS** (4 horas)

**TOTAL PRÓXIMA SEMANA:** 12 horas

---

## ✅ CHECKLIST DE VERIFICACIÓN

### Antes de Desplegar

- [ ] Todas las tarifas configuradas correctamente
- [ ] URLs permitidas importadas
- [ ] Prompts de IA migrados sin modificar
- [ ] Fórmulas de cálculo exactas
- [ ] Validaciones de seguridad implementadas
- [ ] Base de datos con todas las tablas
- [ ] Diseño responsive en móvil
- [ ] Logo optimizado y visible
- [ ] Términos y condiciones actualizados
- [ ] Pruebas de flujo completo

### Antes de Entregar al Usuario

- [ ] Manual de usuario creado
- [ ] Guía de administración creada
- [ ] Video tutorial grabado
- [ ] Credenciales de admin entregadas
- [ ] Backup de base de datos configurado
- [ ] Monitoreo de errores configurado
- [ ] Soporte técnico definido

---

## 📞 CONTACTO Y SOPORTE

**Desarrollador:** Manus AI  
**Usuario:** Eduardo Soto (repuestosonline09-maker)  
**Repositorio:** https://github.com/repuestosonline09-maker/logipartve-v7  
**Aplicación:** https://logipartve-v7.streamlit.app/  

---

**Documento actualizado:** 27 de Enero de 2026  
**Próxima revisión:** Después de completar Fase 3  

LogiPartVE Pro v7.0 © 2026
