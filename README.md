# LogiPartVE Pro v7.0

Sistema profesional de cotización de autopartes con autenticación multi-usuario, gestión administrativa y generación de documentos en formato dual (PDF + JPEG).

## 🚀 Estado del Proyecto

**Fase 1:** ✅ Completada - Sistema de autenticación
**Fase 2:** ✅ Completada - Panel de Administración
**Fase 3:** 🔄 Pendiente - Panel de Analista
**Fase 4:** ⏳ Pendiente - Motor de Cálculo de Precios
**Fase 5:** ⏳ Pendiente - Generador de Documentos

---

## 📋 Características Implementadas

### Fase 1: Sistema de Autenticación
- Login seguro con bcrypt
- Gestión de sesiones con Streamlit
- Roles: Administrador y Analista
- Header con logo responsive
- Footer con copyright
- Diseño responsive para todos los dispositivos

### Fase 2: Panel de Administración
- **Gestión de Usuarios:**
  - Crear nuevos usuarios (analistas/admins)
  - Editar información de usuarios
  - Cambiar contraseñas
  - Eliminar usuarios
  - Listar todos los usuarios con detalles
  
- **Configuración del Sistema:**
  - Diferencial de cambio diario (%)
  - Impuesto empresa americana (%)
  - IVA Venezuela (%)
  - Manejo nacional (USD)
  - Factores de ganancia editables
  - Opciones de garantías personalizables
  - Términos y condiciones editables
  
- **Reportes y Estadísticas:**
  - Estadísticas generales del sistema
  - Reportes por período
  - Productividad por analista
  - Registro de actividad del sistema

---

## 🛠️ Tecnologías

- **Framework:** Streamlit (Python 3.11)
- **Base de Datos:** SQLite (migrable a PostgreSQL)
- **Autenticación:** bcrypt
- **Diseño:** CSS responsive personalizado
- **Generación de Documentos:** ReportLab (PDF) + Pillow (JPEG) - Fase 5

---

## 📦 Instalación

### Requisitos
- Python 3.11+
- pip3

### Pasos

1. **Instalar dependencias:**
```bash
sudo pip3 install streamlit bcrypt pillow reportlab
```

2. **Iniciar la aplicación:**
```bash
cd /home/ubuntu/logipartve_v7
streamlit run app.py
```

3. **Acceder a la aplicación:**
- Abrir navegador en: `http://localhost:8501`

---

## 👤 Credenciales de Acceso

### Usuario Administrador
- **Usuario:** admin
- **Contraseña:** admin123
- **Permisos:** Acceso completo al panel de administración

### Usuario Analista (Ejemplo)
- **Usuario:** analista1
- **Contraseña:** carlos123
- **Permisos:** Crear y gestionar cotizaciones (Fase 3)

---

## 📁 Estructura del Proyecto

```
logipartve_v7/
├── app.py                          # Aplicación principal
├── assets/
│   └── logo.png                    # Logo del sistema
├── components/
│   └── header.py                   # Componente de header
├── database/
│   ├── db_manager.py               # Gestor de base de datos
│   └── logipartve.db               # Base de datos SQLite
├── services/
│   └── auth_manager.py             # Gestor de autenticación
├── views/
│   ├── login_view.py               # Vista de login
│   └── admin_panel.py              # Panel de administración
├── README.md                       # Este archivo
├── FASE2_PRUEBAS_COMPLETAS.md     # Documentación de pruebas
└── RESPONSIVE_DESIGN_REQUIREMENT.md # Requisitos de diseño responsive
```

---

## 🗄️ Base de Datos

### Tablas Implementadas

1. **users** - Usuarios del sistema
2. **system_config** - Configuraciones del sistema
3. **quotes** - Cotizaciones (Fase 3)
4. **quote_items** - Items de cotizaciones (Fase 3)
5. **pages** - Páginas de proveedores (Fase 3)
6. **cache** - Caché de repuestos (Fase 3)
7. **activity_logs** - Registro de actividades

---

## 📱 Diseño Responsive

El sistema es completamente responsive y se adapta a:

- 📱 **Móviles:** 320px - 767px
- 📱 **Tablets:** 768px - 1024px
- 💻 **Laptops:** 1025px - 1919px
- 🖥️ **Desktop:** 1920px+
- 📺 **TV:** 2560px+

---

## 🔐 Seguridad

- Contraseñas hasheadas con bcrypt
- Verificación de roles para acceso a funciones
- Protección del usuario admin principal
- Registro de todas las acciones administrativas
- Validación de entrada en formularios

---

## 📈 Próximas Fases

### Fase 3: Panel de Analista (Estimado: 4-5 días)
- Formulario de datos del cliente
- Gestión de items ilimitados
- Auto-detección de origen (Miami/Madrid)
- Sistema de caché de repuestos
- Cálculo automático de precios
- Vista previa de cotización

### Fase 4: Motor de Cálculo de Precios (Estimado: 3-4 días)
- Traducción de fórmulas Excel a Python
- Variables editables por admin
- Cálculo dinámico de precios
- Aplicación de factores de ganancia
- Inclusión opcional de IVA

### Fase 5: Generador de Documentos (Estimado: 4-5 días)
- Generación de PDF para email
- Generación de JPEG 1080x1920 para WhatsApp/Instagram
- Diseño profesional responsive
- Inclusión de logo y datos de la empresa
- Términos y condiciones personalizables

---

## 📞 Soporte

Para reportar problemas o sugerencias, contactar al equipo de desarrollo.

---

## 📄 Licencia

LogiPartVE Pro v7.0 © 2026 - Todos los derechos reservados
