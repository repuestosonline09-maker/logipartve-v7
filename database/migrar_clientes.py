# ─────────────────────────────────────────────────────────────────────────────
# MÓDULO: migrar_clientes.py
# Migración única de clientes históricos desde la tabla 'quotes' → 'clientes'
# ─────────────────────────────────────────────────────────────────────────────
"""
Lógica de migración:
  1. Lee todas las cotizaciones que tengan los 4 campos completos:
       client_name, client_phone, client_address, client_cedula
  2. Filtra solo las que tienen nombre real (sin números ni alias).
  3. Agrupa por nombre normalizado (sin acentos, sin mayúsculas).
  4. De cada grupo, toma la cotización MÁS RECIENTE (datos más actualizados).
  5. Inserta un solo registro por cliente en la tabla 'clientes'.
  6. Retorna un reporte detallado del resultado.

Esta función es idempotente: si se llama más de una vez, no crea duplicados
porque verifica si el cliente ya existe antes de insertar.
"""

from database.db_manager import DBManager
from database.cliente_manager import (
    init_clientes_table, normalizar, es_nombre_real
)


def migrar_clientes_desde_quotes() -> dict:
    """
    Ejecuta la migración completa de clientes históricos.

    Retorna dict con:
      'migrados':  int  — clientes nuevos insertados
      'omitidos':  int  — cotizaciones saltadas por datos incompletos o alias
      'ya_existian': int — clientes que ya estaban en la tabla (no duplicados)
      'errores':   int  — filas con error inesperado
      'detalle':   list — lista de mensajes para mostrar en el reporte
    """
    reporte = {
        'migrados':    0,
        'omitidos':    0,
        'ya_existian': 0,
        'errores':     0,
        'detalle':     []
    }

    is_postgres = DBManager.USE_POSTGRES

    # ── PASO 1: Asegurar que la tabla clientes existe ─────────────────────────
    init_clientes_table()

    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()

        # ── PASO 2: Leer cotizaciones con los 4 campos completos ──────────────
        if is_postgres:
            cursor.execute("""
                SELECT id, client_name, client_phone, client_address,
                       client_cedula, created_at
                FROM quotes
                WHERE client_name    IS NOT NULL AND TRIM(client_name)    != ''
                  AND client_phone   IS NOT NULL AND TRIM(client_phone)   != ''
                  AND client_address IS NOT NULL AND TRIM(client_address) != ''
                  AND client_cedula  IS NOT NULL AND TRIM(client_cedula)  != ''
                ORDER BY created_at ASC
            """)
        else:
            cursor.execute("""
                SELECT id, client_name, client_phone, client_address,
                       client_cedula, created_at
                FROM quotes
                WHERE client_name    IS NOT NULL AND TRIM(client_name)    != ''
                  AND client_phone   IS NOT NULL AND TRIM(client_phone)   != ''
                  AND client_address IS NOT NULL AND TRIM(client_address) != ''
                  AND client_cedula  IS NOT NULL AND TRIM(client_cedula)  != ''
                ORDER BY created_at ASC
            """)

        filas = cursor.fetchall()
        total_candidatos = len(filas)
        reporte['detalle'].append(
            f"📋 Cotizaciones con los 4 campos completos: {total_candidatos}"
        )

        # ── PASO 3: Filtrar nombres reales y agrupar por nombre normalizado ───
        # Estructura: { nombre_norm: {datos más recientes} }
        grupos = {}

        for fila in filas:
            quote_id, nombre, telefono, direccion, ci_rif, created_at = (
                fila[0], fila[1], fila[2], fila[3], fila[4], fila[5]
            )

            nombre = (nombre or '').strip()
            telefono  = (telefono  or '').strip()
            direccion = (direccion or '').strip()
            ci_rif    = (ci_rif    or '').strip()

            # Filtrar nombres que no son reales (números, alias, etc.)
            if not es_nombre_real(nombre):
                reporte['omitidos'] += 1
                reporte['detalle'].append(
                    f"  ⏭️  Omitido (alias/número): '{nombre}'"
                )
                continue

            nombre_norm = normalizar(nombre)

            # Guardar la cotización más reciente por cliente
            # Como ordenamos por created_at ASC, cada nueva fila sobreescribe
            # la anterior → al final tenemos la MÁS RECIENTE de cada cliente
            grupos[nombre_norm] = {
                'nombre':    nombre,
                'telefono':  telefono,
                'direccion': direccion,
                'ci_rif':    ci_rif,
            }

        reporte['detalle'].append(
            f"👥 Clientes únicos con nombre real: {len(grupos)}"
        )

        # ── PASO 4: Cargar clientes ya existentes en la tabla clientes ────────
        cursor.execute(
            "SELECT nombre FROM clientes"
        )
        existentes_rows = cursor.fetchall()
        existentes_norm = {normalizar(r[0] or '') for r in existentes_rows}

        # ── PASO 5: Insertar los que no existen aún ───────────────────────────
        for nombre_norm, datos in grupos.items():
            if nombre_norm in existentes_norm:
                reporte['ya_existian'] += 1
                reporte['detalle'].append(
                    f"  ✅ Ya existe: '{datos['nombre']}'"
                )
                continue

            try:
                if is_postgres:
                    cursor.execute(
                        """
                        INSERT INTO clientes (nombre, telefono, direccion, ci_rif)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (datos['nombre'], datos['telefono'],
                         datos['direccion'], datos['ci_rif'])
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO clientes (nombre, telefono, direccion, ci_rif)
                        VALUES (?, ?, ?, ?)
                        """,
                        (datos['nombre'], datos['telefono'],
                         datos['direccion'], datos['ci_rif'])
                    )
                reporte['migrados'] += 1
                reporte['detalle'].append(
                    f"  ➕ Migrado: '{datos['nombre']}' | "
                    f"Tel: {datos['telefono']} | CI: {datos['ci_rif']}"
                )
            except Exception as e_ins:
                reporte['errores'] += 1
                reporte['detalle'].append(
                    f"  ❌ Error insertando '{datos['nombre']}': {e_ins}"
                )

        conn.commit()
        cursor.close()
        conn.close()

        reporte['detalle'].append(
            f"\n📊 RESUMEN FINAL:\n"
            f"   ➕ Migrados:      {reporte['migrados']}\n"
            f"   ✅ Ya existían:   {reporte['ya_existian']}\n"
            f"   ⏭️  Omitidos:      {reporte['omitidos']}\n"
            f"   ❌ Errores:       {reporte['errores']}"
        )
        return reporte

    except Exception as e:
        reporte['errores'] += 1
        reporte['detalle'].append(f"❌ Error general en migración: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return reporte
