#!/usr/bin/env python3
# Script de prueba rápida de los métodos agregados a DBManager

from database.db_manager import DBManager

print("🧪 Probando métodos agregados a DBManager...\n")

# Inicializar base de datos
print("1. Inicializando base de datos...")
DBManager.init_database()
print("✅ Base de datos inicializada\n")

# Probar get_all_users
print("2. Probando get_all_users()...")
users = DBManager.get_all_users()
print(f"✅ Encontrados {len(users)} usuarios\n")

# Probar get_user_by_id (si hay usuarios)
if users:
    print("3. Probando get_user_by_id()...")
    user = DBManager.get_user_by_id(users[0]['id'])
    if user:
        print(f"✅ Usuario encontrado: {user['username']}\n")
    else:
        print("❌ Error al obtener usuario por ID\n")

# Probar get_all_config
print("4. Probando get_all_config()...")
config = DBManager.get_all_config()
print(f"✅ Configuraciones encontradas: {len(config)}\n")

# Probar get_all_freight_rates
print("5. Probando get_all_freight_rates()...")
rates = DBManager.get_all_freight_rates()
print(f"✅ Tarifas encontradas: {len(rates)}\n")

# Probar get_quote_stats
print("6. Probando get_quote_stats()...")
stats = DBManager.get_quote_stats()
print(f"✅ Estadísticas: {stats}\n")

# Probar get_recent_activities
print("7. Probando get_recent_activities()...")
activities = DBManager.get_recent_activities(5)
print(f"✅ Actividades recientes: {len(activities)}\n")

print("🎉 Todas las pruebas completadas exitosamente!")
