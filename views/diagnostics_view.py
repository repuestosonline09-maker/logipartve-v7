"""
Vista de Diagnóstico del Sistema
Muestra información sobre la configuración de la base de datos
"""

import streamlit as st
import os
from database.db_manager import DBManager

def show_diagnostics():
    """Muestra información de diagnóstico del sistema."""
    
    st.title("🔍 Diagnóstico del Sistema")
    
    st.markdown("---")
    
    # Información de Base de Datos
    st.subheader("📊 Estado de la Base de Datos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Tipo de Base de Datos", 
                 "PostgreSQL" if DBManager.USE_POSTGRES else "SQLite")
    
    with col2:
        database_url = os.getenv("DATABASE_URL")
        st.metric("DATABASE_URL Detectado", 
                 "✅ Sí" if database_url else "❌ No")
    
    # Detalles
    st.markdown("---")
    st.subheader("📋 Detalles de Configuración")
    
    if DBManager.USE_POSTGRES:
        st.success("✅ **Usando PostgreSQL** (Base de datos permanente en Railway)")
        if database_url:
            # Mostrar solo los primeros 30 caracteres de la URL por seguridad
            masked_url = database_url[:30] + "..." if len(database_url) > 30 else database_url
            st.info(f"🔗 **URL de conexión:** `{masked_url}`")
    else:
        st.warning("⚠️ **Usando SQLite** (Base de datos temporal - se borra al reiniciar)")
        st.info(f"📁 **Ruta:** `{DBManager.DB_PATH}`")
        
        if not database_url:
            st.error("""
            ❌ **Problema Detectado:** La variable `DATABASE_URL` no está configurada.
            
            **Solución:**
            1. Ve a Railway → Tu Proyecto → Variables
            2. Verifica que exista la variable `DATABASE_URL`
            3. Si no existe, agrégala con la URL de tu base de datos PostgreSQL
            4. Reinicia el servicio
            """)
    
    # Probar conexión
    st.markdown("---")
    st.subheader("🔌 Prueba de Conexión")
    
    if st.button("🧪 Probar Conexión a la Base de Datos"):
        try:
            conn = DBManager.get_connection()
            
            if DBManager.USE_POSTGRES:
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                st.success(f"✅ **Conexión exitosa a PostgreSQL**\n\n`{version[:50]}...`")
            else:
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version();")
                version = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                st.success(f"✅ **Conexión exitosa a SQLite**\n\nVersión: `{version}`")
                
        except Exception as e:
            st.error(f"❌ **Error al conectar:**\n\n```\n{str(e)}\n```")
    
    # Variables de entorno
    st.markdown("---")
    st.subheader("🔐 Variables de Entorno")
    
    with st.expander("Ver todas las variables de entorno (sin valores)"):
        env_vars = list(os.environ.keys())
        env_vars.sort()
        
        # Filtrar variables relacionadas con base de datos
        db_vars = [var for var in env_vars if any(keyword in var.upper() for keyword in 
                   ['DATABASE', 'POSTGRES', 'PG', 'DB', 'SQL'])]
        
        if db_vars:
            st.write("**Variables relacionadas con base de datos:**")
            for var in db_vars:
                st.code(var)
        else:
            st.warning("No se encontraron variables relacionadas con base de datos")
        
        st.write(f"\n**Total de variables de entorno:** {len(env_vars)}")
    
    # Información del sistema
    st.markdown("---")
    st.subheader("💻 Información del Sistema")
    
    import sys
    import platform
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    with col2:
        st.metric("Sistema", platform.system())
    
    with col3:
        st.metric("Arquitectura", platform.machine())
