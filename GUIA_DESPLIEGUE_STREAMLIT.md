# 🚀 Guía de Despliegue en Streamlit Cloud

## Resumen
Esta guía te ayudará a desplegar LogiPartVE Pro v7.0 en Streamlit Cloud para que esté disponible 24/7 sin hibernación, igual que tu v6.2.2.

---

## 📋 Requisitos Previos

1. **Cuenta de GitHub** (si no tienes, créala gratis en https://github.com)
2. **Cuenta de Streamlit Cloud** (si no tienes, créala gratis en https://share.streamlit.io)
3. El código de la aplicación (ya está listo en este proyecto)

---

## 🎯 Opción 1: Despliegue Rápido (Recomendado)

### Paso 1: Subir el código a GitHub

**A. Si ya tienes un repositorio GitHub para LogiPartVE:**

1. Ve a tu repositorio en GitHub
2. Crea una nueva rama llamada `v7.0` o reemplaza el código existente
3. Sube todos los archivos de la carpeta `logipartve_v7/`

**B. Si NO tienes repositorio GitHub:**

1. Ve a https://github.com/new
2. Nombre del repositorio: `logipartve-v7`
3. Descripción: "LogiPartVE Pro v7.0 - Sistema de Cotización de Autopartes"
4. Selecciona: **Private** (para mantenerlo privado)
5. Haz clic en "Create repository"
6. Sigue las instrucciones para subir el código (ver abajo)

### Paso 2: Subir archivos a GitHub

**Opción A - Usando GitHub Web (Más fácil):**

1. En tu repositorio nuevo, haz clic en "uploading an existing file"
2. Arrastra todos los archivos de la carpeta `logipartve_v7/`
3. Escribe un mensaje: "Initial commit - LogiPartVE v7.0"
4. Haz clic en "Commit changes"

**Opción B - Usando Git en terminal:**

```bash
# Inicializar Git en el proyecto
cd /home/ubuntu/logipartve_v7
git init
git add .
git commit -m "Initial commit - LogiPartVE v7.0"

# Conectar con tu repositorio GitHub
git remote add origin https://github.com/TU_USUARIO/logipartve-v7.git
git branch -M main
git push -u origin main
```

### Paso 3: Desplegar en Streamlit Cloud

1. Ve a https://share.streamlit.io
2. Haz clic en "New app"
3. Conecta tu cuenta de GitHub (si no lo has hecho)
4. Selecciona:
   - **Repository:** `TU_USUARIO/logipartve-v7`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Haz clic en "Deploy!"
6. Espera 2-3 minutos mientras se despliega

### Paso 4: ¡Listo!

Tu aplicación estará disponible en:
```
https://logipartve-v7-XXXXXX.streamlit.app
```

Puedes personalizar la URL en la configuración de Streamlit Cloud.

---

## 🎯 Opción 2: Despliegue desde ZIP (Alternativa)

Si prefieres no usar Git, puedes:

1. Descargar el archivo `logipartve_v7_deploy.zip`
2. Extraer el contenido en tu computadora
3. Subir los archivos a GitHub usando la interfaz web
4. Seguir el Paso 3 de la Opción 1

---

## ⚙️ Configuración Adicional (Opcional)

### Personalizar la URL

1. En Streamlit Cloud, ve a tu app
2. Haz clic en "Settings" → "General"
3. Cambia el nombre de la app a: `logipartve-v7`
4. Tu URL será: `https://logipartve-v7.streamlit.app`

### Configurar Variables de Entorno (Si necesitas)

1. En Streamlit Cloud, ve a "Settings" → "Secrets"
2. Agrega cualquier variable sensible aquí (no necesario por ahora)

---

## 🔐 Seguridad

**Importante:** La base de datos SQLite se incluye en el repositorio con el usuario admin predeterminado. Para producción, considera:

1. Cambiar la contraseña del admin después del primer despliegue
2. Migrar a PostgreSQL para mayor seguridad y rendimiento
3. Usar variables de entorno para datos sensibles

---

## 🆚 Comparación con v6.2.2

| Característica | v6.2.2 | v7.0 |
|----------------|--------|------|
| Hosting | Streamlit Cloud | Streamlit Cloud |
| Disponibilidad | 24/7 | 24/7 |
| Autenticación | Básica | Multi-usuario con roles |
| Panel Admin | No | ✅ Completo |
| Base de Datos | SQLite | SQLite (migrable a PostgreSQL) |
| Responsive | Sí | ✅ Mejorado |

---

## 🐛 Solución de Problemas

### Error: "Module not found"
- Verifica que `requirements.txt` esté en la raíz del repositorio
- Asegúrate de que todas las dependencias estén listadas

### Error: "Database locked"
- Esto puede pasar con SQLite en producción
- Solución: Migrar a PostgreSQL (te puedo ayudar)

### La app no carga
- Revisa los logs en Streamlit Cloud
- Verifica que `app.py` esté en la raíz del repositorio

---

## 📞 Soporte

Si tienes problemas durante el despliegue, puedes:

1. Revisar los logs en Streamlit Cloud
2. Consultar la documentación: https://docs.streamlit.io/streamlit-community-cloud
3. Pedirme ayuda con los errores específicos

---

## 🎉 Próximos Pasos

Una vez desplegada la v7.0:

1. Cambiar la contraseña del admin
2. Crear usuarios analistas
3. Configurar las variables del sistema
4. ¡Comenzar a usar el Panel de Administración!
5. Continuar con la Fase 3: Panel de Analista

---

**¡Éxito con tu despliegue!** 🚀

LogiPartVE Pro v7.0 © 2026
