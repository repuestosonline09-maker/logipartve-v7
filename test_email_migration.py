#!/usr/bin/env python3
"""
Script de prueba para verificar la migración automática de la columna 'email'
"""

from database.db_manager import DBManager

print("=" * 60)
print("PRUEBA DE MIGRACIÓN AUTOMÁTICA - COLUMNA EMAIL")
print("=" * 60)

# 1. Inicializar base de datos (ejecuta migración automática)
print("\n1. Inicializando base de datos...")
DBManager.init_database()
print("✅ Base de datos inicializada")

# 2. Verificar que la columna email existe
print("\n2. Verificando columna 'email' en tabla 'users'...")
conn = DBManager.get_connection()
cursor = conn.cursor()

if DBManager.USE_POSTGRES:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='email'
    """)
    result = cursor.fetchone()
    if result:
        print("✅ Columna 'email' existe en PostgreSQL")
    else:
        print("❌ Columna 'email' NO existe en PostgreSQL")
else:
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'email' in columns:
        print("✅ Columna 'email' existe en SQLite")
    else:
        print("❌ Columna 'email' NO existe en SQLite")

# 3. Obtener usuario admin
print("\n3. Obteniendo usuario 'admin'...")
admin = DBManager.get_user_by_username('admin')
if admin:
    print(f"✅ Usuario admin encontrado:")
    print(f"   - ID: {admin['id']}")
    print(f"   - Username: {admin['username']}")
    print(f"   - Full Name: {admin['full_name']}")
    print(f"   - Email: {admin.get('email', 'Sin email')}")
    print(f"   - Role: {admin['role']}")
else:
    print("❌ Usuario admin no encontrado")

# 4. Probar update_user con email
print("\n4. Probando update_user() con email...")
if admin:
    success = DBManager.update_user(
        admin['id'], 
        'Administrador Principal', 
        'admin', 
        'admin@logipartve.com'
    )
    if success:
        print("✅ Usuario actualizado exitosamente")
        
        # Verificar que se guardó
        admin_updated = DBManager.get_user_by_id(admin['id'])
        print(f"   - Nuevo nombre: {admin_updated['full_name']}")
        print(f"   - Nuevo email: {admin_updated.get('email', 'Sin email')}")
    else:
        print("❌ Error al actualizar usuario")

cursor.close()
conn.close()

print("\n" + "=" * 60)
print("PRUEBA COMPLETADA")
print("=" * 60)
