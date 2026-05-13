# ─────────────────────────────────────────────────────────────────────────────
# MÓDULO: cliente_manager.py
# Gestión completa de la base de datos de clientes de LogiPartVE
# Compatible con PostgreSQL (producción) y SQLite (desarrollo local)
# ─────────────────────────────────────────────────────────────────────────────
"""
Funciones:
  - init_clientes_table()        → Crea la tabla si no existe
  - es_nombre_real(texto)        → True si el texto es un nombre (solo letras)
  - normalizar(texto)            → Elimina acentos para comparación
  - buscar_clientes(query)       → Búsqueda por nombre/apellido sin distinción de acentos
  - guardar_o_actualizar(datos)  → Crea o actualiza un cliente
  - get_todos_los_clientes()     → Lista completa para el panel admin
  - get_cliente_por_id(id)       → Un cliente por su ID
  - actualizar_cliente(id, datos)→ Edita un cliente existente
  - eliminar_cliente(id)         → Elimina un cliente
  - detectar_duplicados()        → Clientes con misma cédula Y mismo teléfono
"""

import unicodedata
import re
from database.db_manager import DBManager


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 0: UTILIDAD INTERNA — Acceso a filas compatible PG + SQLite
# ─────────────────────────────────────────────────────────────────────────────

def _row(row, key: str, index: int):
    """
    Accede a un campo de una fila de BD de forma compatible con:
    - PostgreSQL (psycopg2 RealDictRow) → acceso por nombre: row[key]
    - SQLite (sqlite3.Row / tuple)       → acceso por índice: row[index]

    Uso: _row(row, 'nombre', 1)
    """
    try:
        # Intenta acceso por nombre (PostgreSQL RealDictRow o sqlite3.Row con factory)
        return row[key]
    except (KeyError, TypeError, IndexError):
        pass
    try:
        # Fallback: acceso por índice (tuple, list, sqlite3.Row sin factory)
        return row[index]
    except (IndexError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 1: INICIALIZACIÓN DE TABLA
# ─────────────────────────────────────────────────────────────────────────────

def init_clientes_table():
    """
    Crea la tabla 'clientes' si no existe.
    Compatible con PostgreSQL y SQLite.
    Operación idempotente: seguro llamarla múltiples veces.
    """
    is_postgres = DBManager.USE_POSTGRES
    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()

        if is_postgres:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id             SERIAL PRIMARY KEY,
                    nombre         TEXT NOT NULL,
                    telefono       TEXT,
                    direccion      TEXT,
                    ci_rif         TEXT,
                    creado_en      TIMESTAMP DEFAULT NOW(),
                    actualizado_en TIMESTAMP DEFAULT NOW()
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes (nombre)"
            )
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre         TEXT NOT NULL,
                    telefono       TEXT,
                    direccion      TEXT,
                    ci_rif         TEXT,
                    creado_en      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes (nombre)"
            )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error creando tabla clientes: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 2: UTILIDADES DE TEXTO
# ─────────────────────────────────────────────────────────────────────────────

def normalizar(texto: str) -> str:
    """
    Convierte texto a minúsculas y elimina acentos/diacríticos.
    Ej: 'María González' → 'maria gonzalez'
    """
    if not texto:
        return ''
    texto = texto.strip().lower()
    # Descomponer caracteres Unicode y eliminar marcas diacríticas
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def es_nombre_real(texto: str) -> bool:
    """
    Retorna True si el texto parece un nombre real (solo letras, espacios y
    caracteres latinos). Retorna False si contiene números, @ u otros símbolos
    que indiquen un alias, teléfono o identificador.

    Ejemplos:
      'María González' → True
      '04121234567'    → False
      '@instagram_user'→ False
      'Luis Cumana'    → True
    """
    if not texto or len(texto.strip()) < 2:
        return False
    texto = texto.strip()
    # Rechazar si contiene dígitos o símbolos típicos de alias/teléfono
    if re.search(r'[\d@#$%&*_/\\|<>{}[\]()=+]', texto):
        return False
    # Debe tener al menos 2 letras
    letras = re.findall(r'[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]', texto)
    return len(letras) >= 2


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3: BÚSQUEDA DE CLIENTES (AUTOCOMPLETADO)
# ─────────────────────────────────────────────────────────────────────────────

def buscar_clientes(query: str, limite: int = 10) -> list:
    """
    Busca clientes cuyo nombre contenga el texto 'query'.
    - Insensible a acentos: 'Maria' encuentra 'María'
    - Busca en nombre completo (nombre y apellido)
    - Requiere al menos 3 caracteres para buscar.
    - Retorna lista de dicts con: id, nombre, telefono, direccion, ci_rif
    """
    if not query or len(query.strip()) < 3:
        return []

    query_norm = normalizar(query)
    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nombre, telefono, direccion, ci_rif FROM clientes ORDER BY nombre ASC LIMIT 500"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        resultados = []
        for row in rows:
            nombre_val = _row(row, 'nombre', 1) or ''
            nombre_norm = normalizar(nombre_val)
            if query_norm in nombre_norm:
                resultados.append({
                    'id':        _row(row, 'id', 0),
                    'nombre':    nombre_val,
                    'telefono':  _row(row, 'telefono', 2) or '',
                    'direccion': _row(row, 'direccion', 3) or '',
                    'ci_rif':    _row(row, 'ci_rif', 4) or '',
                })
            if len(resultados) >= limite:
                break

        return resultados

    except Exception as e:
        print(f"❌ Error buscando clientes: {e}")
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return []


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 4: GUARDAR O ACTUALIZAR CLIENTE
# ─────────────────────────────────────────────────────────────────────────────

def guardar_o_actualizar(datos: dict) -> dict:
    """
    Guarda un cliente nuevo o actualiza uno existente.

    Lógica:
    1. Si el nombre no es real (tiene números, @, etc.) → no hace nada.
    2. Busca si ya existe un cliente con el mismo nombre normalizado.
       - Si existe → actualiza teléfono, dirección y ci_rif (solo si los nuevos
         valores no están vacíos, para no borrar datos existentes).
       - Si no existe → crea un registro nuevo.

    Retorna dict con:
      'accion': 'creado' | 'actualizado' | 'ignorado' | 'error'
      'cliente_id': int | None
      'mensaje': str
    """
    nombre = (datos.get('nombre') or '').strip()

    if not es_nombre_real(nombre):
        return {
            'accion': 'ignorado',
            'cliente_id': None,
            'mensaje': 'Nombre no válido para guardar en base de datos de clientes.'
        }

    telefono  = (datos.get('telefono')  or '').strip()
    direccion = (datos.get('direccion') or '').strip()
    ci_rif    = (datos.get('ci_rif')    or '').strip()
    nombre_norm = normalizar(nombre)
    is_postgres = DBManager.USE_POSTGRES

    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()

        # Buscar cliente existente por nombre normalizado
        cursor.execute(
            "SELECT id, nombre, telefono, direccion, ci_rif FROM clientes ORDER BY nombre ASC LIMIT 500"
        )
        rows = cursor.fetchall()

        cliente_existente = None
        for row in rows:
            nombre_bd = _row(row, 'nombre', 1) or ''
            if normalizar(nombre_bd) == nombre_norm:
                cliente_existente = {
                    'id':        _row(row, 'id', 0),
                    'nombre':    nombre_bd,
                    'telefono':  _row(row, 'telefono', 2) or '',
                    'direccion': _row(row, 'direccion', 3) or '',
                    'ci_rif':    _row(row, 'ci_rif', 4) or '',
                }
                break

        if cliente_existente:
            # Actualizar solo los campos que traen datos nuevos
            nuevo_tel = telefono  if telefono  else cliente_existente['telefono']
            nuevo_dir = direccion if direccion else cliente_existente['direccion']
            nuevo_ci  = ci_rif    if ci_rif    else cliente_existente['ci_rif']

            if is_postgres:
                cursor.execute(
                    """
                    UPDATE clientes
                    SET telefono = %s, direccion = %s, ci_rif = %s,
                        actualizado_en = NOW()
                    WHERE id = %s
                    """,
                    (nuevo_tel, nuevo_dir, nuevo_ci, cliente_existente['id'])
                )
            else:
                cursor.execute(
                    """
                    UPDATE clientes
                    SET telefono = ?, direccion = ?, ci_rif = ?,
                        actualizado_en = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (nuevo_tel, nuevo_dir, nuevo_ci, cliente_existente['id'])
                )

            conn.commit()
            cursor.close()
            conn.close()
            return {
                'accion': 'actualizado',
                'cliente_id': cliente_existente['id'],
                'mensaje': f'Cliente "{nombre}" actualizado correctamente.'
            }

        else:
            # Crear nuevo cliente
            if is_postgres:
                cursor.execute(
                    """
                    INSERT INTO clientes (nombre, telefono, direccion, ci_rif)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (nombre, telefono, direccion, ci_rif)
                )
                nuevo_id_row = cursor.fetchone()
                nuevo_id = _row(nuevo_id_row, 'id', 0)
            else:
                cursor.execute(
                    """
                    INSERT INTO clientes (nombre, telefono, direccion, ci_rif)
                    VALUES (?, ?, ?, ?)
                    """,
                    (nombre, telefono, direccion, ci_rif)
                )
                nuevo_id = cursor.lastrowid

            conn.commit()
            cursor.close()
            conn.close()
            return {
                'accion': 'creado',
                'cliente_id': nuevo_id,
                'mensaje': f'Cliente "{nombre}" registrado en la base de datos.'
            }

    except Exception as e:
        print(f"❌ Error guardando cliente: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return {
            'accion': 'error',
            'cliente_id': None,
            'mensaje': f'Error al guardar cliente: {str(e)}'
        }


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 5: CONSULTAS PARA PANEL ADMIN
# ─────────────────────────────────────────────────────────────────────────────

def get_todos_los_clientes() -> list:
    """Retorna todos los clientes ordenados por nombre para el panel admin."""
    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nombre, telefono, direccion, ci_rif,
                   creado_en, actualizado_en
            FROM clientes
            ORDER BY nombre ASC
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            {
                'id':             _row(row, 'id', 0),
                'nombre':         _row(row, 'nombre', 1) or '',
                'telefono':       _row(row, 'telefono', 2) or '',
                'direccion':      _row(row, 'direccion', 3) or '',
                'ci_rif':         _row(row, 'ci_rif', 4) or '',
                'creado_en':      _row(row, 'creado_en', 5),
                'actualizado_en': _row(row, 'actualizado_en', 6),
            }
            for row in rows
        ]
    except Exception as e:
        print(f"❌ Error obteniendo clientes: {e}")
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return []


def get_cliente_por_id(cliente_id: int) -> dict:
    """Retorna un cliente por su ID."""
    is_postgres = DBManager.USE_POSTGRES
    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        if is_postgres:
            cursor.execute(
                "SELECT id, nombre, telefono, direccion, ci_rif FROM clientes WHERE id = %s",
                (cliente_id,)
            )
        else:
            cursor.execute(
                "SELECT id, nombre, telefono, direccion, ci_rif FROM clientes WHERE id = ?",
                (cliente_id,)
            )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return {
                'id':        _row(row, 'id', 0),
                'nombre':    _row(row, 'nombre', 1) or '',
                'telefono':  _row(row, 'telefono', 2) or '',
                'direccion': _row(row, 'direccion', 3) or '',
                'ci_rif':    _row(row, 'ci_rif', 4) or '',
            }
        return {}
    except Exception as e:
        print(f"❌ Error obteniendo cliente {cliente_id}: {e}")
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return {}


def actualizar_cliente(cliente_id: int, datos: dict) -> bool:
    """Actualiza todos los campos de un cliente. Usado desde el panel admin."""
    is_postgres = DBManager.USE_POSTGRES
    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        if is_postgres:
            cursor.execute(
                """
                UPDATE clientes
                SET nombre = %s, telefono = %s, direccion = %s, ci_rif = %s,
                    actualizado_en = NOW()
                WHERE id = %s
                """,
                (
                    (datos.get('nombre')    or '').strip(),
                    (datos.get('telefono')  or '').strip(),
                    (datos.get('direccion') or '').strip(),
                    (datos.get('ci_rif')    or '').strip(),
                    cliente_id
                )
            )
        else:
            cursor.execute(
                """
                UPDATE clientes
                SET nombre = ?, telefono = ?, direccion = ?, ci_rif = ?,
                    actualizado_en = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    (datos.get('nombre')    or '').strip(),
                    (datos.get('telefono')  or '').strip(),
                    (datos.get('direccion') or '').strip(),
                    (datos.get('ci_rif')    or '').strip(),
                    cliente_id
                )
            )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error actualizando cliente {cliente_id}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return False


def eliminar_cliente(cliente_id: int) -> bool:
    """Elimina un cliente por su ID."""
    is_postgres = DBManager.USE_POSTGRES
    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        if is_postgres:
            cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        else:
            cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error eliminando cliente {cliente_id}: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 6: DETECCIÓN DE DUPLICADOS
# ─────────────────────────────────────────────────────────────────────────────

def detectar_duplicados() -> list:
    """
    Detecta clientes duplicados: misma cédula (ci_rif) Y mismo teléfono.
    Solo se consideran duplicados si ambos campos coinciden y no están vacíos.

    Retorna lista de grupos, cada grupo es una lista de clientes duplicados.
    Ej: [ [cliente_A, cliente_B], [cliente_C, cliente_D, cliente_E] ]
    """
    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nombre, telefono, direccion, ci_rif
            FROM clientes
            WHERE ci_rif IS NOT NULL AND ci_rif != ''
              AND telefono IS NOT NULL AND telefono != ''
            ORDER BY ci_rif, telefono, nombre
            """
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Agrupar por (ci_rif normalizado, telefono normalizado)
        grupos = {}
        for row in rows:
            ci_val  = _row(row, 'ci_rif', 4) or ''
            tel_val = _row(row, 'telefono', 2) or ''
            clave = (normalizar(ci_val), normalizar(tel_val))
            if clave not in grupos:
                grupos[clave] = []
            grupos[clave].append({
                'id':        _row(row, 'id', 0),
                'nombre':    _row(row, 'nombre', 1) or '',
                'telefono':  tel_val,
                'direccion': _row(row, 'direccion', 3) or '',
                'ci_rif':    ci_val,
            })

        # Solo retornar grupos con más de 1 cliente
        return [grupo for grupo in grupos.values() if len(grupo) > 1]

    except Exception as e:
        print(f"❌ Error detectando duplicados: {e}")
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        return []


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 7: SINCRONIZACIÓN CLIENTE → COTIZACIÓN
# ─────────────────────────────────────────────────────────────────────────────

def sincronizar_datos_cliente_en_cotizacion(quote: dict) -> dict:
    """
    Enriquece los datos de una cotización con la información más actualizada
    del directorio de clientes (tabla 'clientes').

    Lógica:
    - Busca en 'clientes' un registro cuyo nombre normalizado coincida con
      el nombre del cliente de la cotización.
    - Si lo encuentra, completa los campos vacíos (client_cedula, client_address,
      client_phone, client_email) con los valores del directorio.
    - Si los campos ya tienen valor en la cotización, NO los sobreescribe.
    - También actualiza la tabla 'quotes' en BD para que la cotización quede
      sincronizada de forma permanente.
    - Retorna el dict 'quote' enriquecido (nunca falla: en caso de error
      devuelve el quote original sin modificar).

    Args:
        quote: dict con los datos de la cotización (resultado de get_quote_by_id)

    Returns:
        dict con los datos de la cotización, potencialmente enriquecidos.
    """
    if not quote:
        return quote

    nombre_cot = (quote.get('client_name') or '').strip()
    if not nombre_cot or len(nombre_cot) < 3:
        return quote

    # Campos que pueden sincronizarse desde el directorio
    CAMPOS_SYNC = [
        ('ci_rif',    'client_cedula'),   # (campo en clientes, campo en quotes)
        ('direccion', 'client_address'),
        ('telefono',  'client_phone'),
    ]

    conn = None
    try:
        conn = DBManager.get_connection()
        cursor = conn.cursor()
        is_postgres = DBManager.USE_POSTGRES

        # Buscar cliente por nombre normalizado
        cursor.execute(
            "SELECT id, nombre, telefono, direccion, ci_rif FROM clientes ORDER BY nombre ASC LIMIT 500"
        )
        rows = cursor.fetchall()

        nombre_norm = normalizar(nombre_cot)
        cliente_encontrado = None
        for row in rows:
            nombre_val = _row(row, 'nombre', 1) or ''
            if normalizar(nombre_val) == nombre_norm:
                cliente_encontrado = {
                    'id':        _row(row, 'id', 0),
                    'nombre':    nombre_val,
                    'telefono':  _row(row, 'telefono', 2) or '',
                    'direccion': _row(row, 'direccion', 3) or '',
                    'ci_rif':    _row(row, 'ci_rif', 4) or '',
                }
                break

        if not cliente_encontrado:
            cursor.close()
            conn.close()
            return quote

        # Determinar qué campos necesitan actualizarse en la cotización
        campos_a_actualizar = {}
        for campo_cli, campo_quote in CAMPOS_SYNC:
            valor_cli   = (cliente_encontrado.get(campo_cli) or '').strip()
            valor_quote = (quote.get(campo_quote) or '').strip()
            # Solo actualizar si el directorio tiene el dato y la cotización no lo tiene
            if valor_cli and not valor_quote:
                campos_a_actualizar[campo_quote] = valor_cli

        if not campos_a_actualizar:
            cursor.close()
            conn.close()
            return quote  # Nada que sincronizar

        # Actualizar la cotización en BD
        quote_id = quote.get('id')
        if quote_id:
            set_clauses = ', '.join(
                f"{col} = {'%s' if is_postgres else '?'}"
                for col in campos_a_actualizar.keys()
            )
            valores = list(campos_a_actualizar.values()) + [quote_id]
            sql = f"UPDATE quotes SET {set_clauses} WHERE id = {'%s' if is_postgres else '?'}"
            cursor.execute(sql, valores)
            conn.commit()
            print(f"✅ Cotización ID={quote_id} sincronizada con cliente '{nombre_cot}': {list(campos_a_actualizar.keys())}")

        cursor.close()
        conn.close()

        # Enriquecer el dict en memoria para que la validación lo vea de inmediato
        quote = dict(quote)
        for campo_quote, valor in campos_a_actualizar.items():
            quote[campo_quote] = valor

        return quote

    except Exception as e:
        print(f"⚠️ Error en sincronizar_datos_cliente_en_cotizacion: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return quote  # Devolver el original sin modificar
