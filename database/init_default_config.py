"""
Módulo para inicializar configuraciones por defecto en la base de datos.
Este módulo se ejecuta automáticamente al iniciar la aplicación para garantizar
que todos los datos necesarios estén disponibles.
"""

from database.db_manager import DBManager


def initialize_default_config():
    """
    Inicializa las configuraciones por defecto si no existen en la base de datos.
    Esta función se ejecuta al iniciar la aplicación.
    """
    
    # Lista completa de países (basada en la configuración del usuario)
    default_paises = "Afganistán,Albania,Alemania,Andorra,Angola,Antigua y Barbuda,Arabia Saudita,Argelia,Argentina,Armenia,Australia,Austria,Azerbaiyán,Bahamas,Bangladés,Barbados,Bareín,Bélgica,Belice,Benín,Bielorrusia,Birmania,Bolivia,Bosnia y Herzegovina,Botsuana,Brasil,Brunéi,Bulgaria,Burkina Faso,Burundi,Bután,Cabo Verde,Camboya,Camerún,Canadá,Catar,Chad,Chile,China,Chipre,Colombia,Comoras,Corea del Norte,Corea del Sur,Costa de Marfil,Costa Rica,Croacia,Cuba,Dinamarca,Dominica,Ecuador,Egipto,El Salvador,Emiratos Árabes Unidos,Eritrea,Eslovaquia,Eslovenia,España,Estados Unidos,Estonia,Esuatini,Etiopía,Filipinas,Finlandia,Fiyi,Francia,Gabón,Gambia,Georgia,Ghana,Granada,Grecia,Guatemala,Guinea,Guinea-Bisáu,Guinea Ecuatorial,Guyana,Haití,Honduras,Hungría,India,Indonesia,Irak,Irán,Irlanda,Islandia,Islas Marshall,Islas Salomón,Israel,Italia,Jamaica,Japón,Jordania,Kazajistán,Kenia,Kirguistán,Kiribati,Kuwait,Laos,Lesoto,Letonia,Líbano,Liberia,Libia,Liechtenstein,Lituania,Luxemburgo,Macedonia del Norte,Madagascar,Malasia,Malaui,Maldivas,Malí,Malta,Marruecos,Mauricio,Mauritania,México,Micronesia,Moldavia,Mónaco,Mongolia,Montenegro,Mozambique,Namibia,Nauru,Nepal,Nicaragua,Níger,Nigeria,Noruega,Nueva Zelanda,Omán,Países Bajos,Pakistán,Palaos,Palestina,Panamá,Papúa Nueva Guinea,Paraguay,Perú,Polonia,Portugal,Reino Unido,República Centroafricana,República Checa,República del Congo,República Democrática del Congo,República Dominicana,Ruanda,Rumania,Rusia,Samoa,San Cristóbal y Nieves,San Marino,San Vicente y las Granadinas,Santa Lucía,Santo Tomé y Príncipe,Senegal,Serbia,Seychelles,Sierra Leona,Singapur,Siria,Somalia,Sri Lanka,Suazilandia,Sudáfrica,Sudán,Sudán del Sur,Suecia,Suiza,Surinam,Tailandia,Tanzania,Tayikistán,Timor Oriental,Togo,Tonga,Trinidad y Tobago,Túnez,Turkmenistán,Turquía,Tuvalu,Ucrania,Uganda,Uruguay,Uzbekistán,Vanuatu,Vaticano,Venezuela,Vietnam,Yemen,Yibuti,Zambia,Zimbabue"
    
    # Opciones de manejo por defecto
    default_manejo = "0,15,18,25"
    
    # Tipos de envío por defecto
    default_tipos_envio = "AEREO,MARITIMO,TERRESTRE"
    
    # Tiempos de entrega por defecto
    default_tiempos_entrega = "02 A 05 DIAS,08 A 12 DIAS,12 A 15 DIAS,15 A 20 DIAS,20 A 30 DIAS"
    
    # Garantías por defecto
    default_garantias = "15 DIAS,30 DIAS,45 DIAS,3 MESES,6 MESES,1 AÑO"
    
    # Impuesto internacional por defecto
    default_impuesto = "0,25,30,35,40,45,50"
    
    # Factores de utilidad por defecto
    default_utilidad = "1.4285,1.35,1.30,1.25,1.20,1.15,1.10,0"
    
    # Términos y condiciones por defecto
    default_terms = """1.- Cotización válida por 24 horas.
2.- Los montos expresados son en dólares (USD) a tasa BCV.
3.- La Garantía está en cada ítem (aplican condiciones)."""
    
    # Configuraciones a inicializar
    configs = [
        ('paises_origen', default_paises, 'Países de origen/localización disponibles'),
        ('manejo_options', default_manejo, 'Opciones de MANEJO en dólares'),
        ('tipos_envio', default_tipos_envio, 'Tipos de envío disponibles'),
        ('tiempos_entrega', default_tiempos_entrega, 'Tiempos de entrega disponibles'),
        ('garantias', default_garantias, 'Opciones de garantía disponibles'),
        ('impuesto_internacional', default_impuesto, 'Opciones de impuesto internacional (%)'),
        ('utilidad_factors', default_utilidad, 'Factores de utilidad para cálculo de precios'),
        ('terms_conditions', default_terms, 'Términos y condiciones de cotización'),
        ('tax_percentage', '7.0', 'Porcentaje de impuesto (%)'),
        ('diferencial', '45.0', 'Diferencial de cambio (%)'),
        ('iva_venezuela', '16.0', 'IVA de Venezuela (%)'),
    ]
    
    print("🔧 Inicializando configuraciones por defecto...")
    
    for key, value, description in configs:
        # Verificar si la configuración ya existe
        existing_value = DBManager.get_config(key)
        
        if existing_value is None:
            # No existe, crear con valor por defecto
            success = DBManager.set_config(key, value, description, updated_by=1)
            if success:
                print(f"✅ Configuración '{key}' inicializada")
            else:
                print(f"❌ Error al inicializar '{key}'")
        else:
            print(f"ℹ️  Configuración '{key}' ya existe (valor: {existing_value[:50]}...)")
    
    print("✅ Inicialización de configuraciones completada")


if __name__ == "__main__":
    # Permitir ejecutar este script directamente para pruebas
    initialize_default_config()
