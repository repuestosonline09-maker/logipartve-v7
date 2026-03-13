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
    
    # ─── HERRAMIENTA DE REPARACIÓN DE IVA ───────────────────────────────────────
    st.markdown("---")
    st.subheader("🔧 Herramienta de Reparación de IVA")
    st.info("Esta herramienta permite aplicar el IVA 16% a los ítems de una cotización que fue guardada sin IVA por un bug anterior.")

    quote_number_fix = st.text_input("Número de cotización a reparar (ej: 2026-30093-A):", key="fix_iva_quote")
    iva_pct_fix = st.number_input("Porcentaje de IVA a aplicar:", min_value=0.0, max_value=100.0, value=16.0, step=0.5, key="fix_iva_pct")

    if st.button("🔧 Aplicar IVA a la cotización", key="btn_fix_iva"):
        if not quote_number_fix.strip():
            st.error("Ingresa el número de cotización.")
        else:
            try:
                conn = DBManager.get_connection()
                cursor = conn.cursor()

                # Obtener los ítems actuales
                if DBManager.USE_POSTGRES:
                    cursor.execute("""
                        SELECT id, precio_unitario, cantidad, precio_total
                        FROM quote_items
                        WHERE quote_number = %s
                    """, (quote_number_fix.strip(),))
                else:
                    cursor.execute("""
                        SELECT id, precio_unitario, cantidad, precio_total
                        FROM quote_items
                        WHERE quote_number = ?
                    """, (quote_number_fix.strip(),))

                items = cursor.fetchall()

                if not items:
                    st.error(f"No se encontraron ítems para la cotización {quote_number_fix}")
                else:
                    updated = 0
                    total_iva = 0.0
                    details = []

                    for item in items:
                        item_id = item[0]
                        precio_unit = float(item[1])
                        cantidad = int(item[2])
                        precio_total = float(item[3])

                        # Calcular IVA: el precio_total ya es el precio sin IVA
                        iva_valor = round(precio_total * (iva_pct_fix / 100.0), 2)
                        total_iva += iva_valor

                        if DBManager.USE_POSTGRES:
                            cursor.execute("""
                                UPDATE quote_items
                                SET aplicar_iva = TRUE,
                                    iva_porcentaje = %s,
                                    iva_valor = %s
                                WHERE id = %s
                            """, (iva_pct_fix, iva_valor, item_id))
                        else:
                            cursor.execute("""
                                UPDATE quote_items
                                SET aplicar_iva = 1,
                                    iva_porcentaje = ?,
                                    iva_valor = ?
                                WHERE id = ?
                            """, (iva_pct_fix, iva_valor, item_id))

                        details.append(f"  Ítem ID {item_id}: precio_total=${precio_total:.2f} → IVA={iva_pct_fix}% = ${iva_valor:.2f}")
                        updated += 1

                    conn.commit()
                    cursor.close()
                    conn.close()

                    st.success(f"✅ Se actualizaron {updated} ítems con IVA {iva_pct_fix}%.")
                    st.info(f"💰 IVA total calculado: **${total_iva:.2f}**")
                    for d in details:
                        st.code(d)

            except Exception as e:
                st.error(f"❌ Error al reparar IVA: {str(e)}")

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
