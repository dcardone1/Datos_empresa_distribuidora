"""
config.py
=========
Parámetros centrales del dataset de logística (distribuidora de bebidas).
Todo lo que quieras ajustar (fechas, cantidad de depósitos, flota, etc.)
se cambia acá, sin tocar la lógica de los scripts de generación.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Semilla global: fija la aleatoriedad para que el dataset sea reproducible.
# Si querés una corrida distinta cada vez, comentá esta línea.
# ---------------------------------------------------------------------------
SEED = 42
RNG = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Período de simulación
# ---------------------------------------------------------------------------
FECHA_INICIO = "2022-01-01"
FECHA_FIN = "2024-12-31"

# ---------------------------------------------------------------------------
# Depósitos
# ---------------------------------------------------------------------------
DEPOSITOS = [
    {"nombre": "Buenos Aires", "localidad": "San Martín, Buenos Aires"},
    {"nombre": "Córdoba", "localidad": "Córdoba Capital"},
    {"nombre": "Mendoza", "localidad": "Guaymallén, Mendoza"},
]

ZONAS_POR_DEPOSITO = (3, 5)  # rango (min, max) de zonas por depósito

# Nombres de zonas/barrios plausibles por depósito (se usan hasta completar
# la cantidad sorteada; si hace falta más de los listados, se combinan con
# un sufijo numérico).
BARRIOS_POR_DEPOSITO = {
    "Buenos Aires": ["San Martín Centro", "Villa Ballester", "José León Suárez",
                      "Chilavert", "Billinghurst", "San Andrés"],
    "Córdoba": ["Nueva Córdoba", "Alberdi", "Cerro de las Rosas", "Güemes",
                "General Paz", "Villa Belgrano"],
    "Mendoza": ["Guaymallén Centro", "Las Heras", "Godoy Cruz", "Dorrego",
                "Villa Nueva", "San José"],
}

# ---------------------------------------------------------------------------
# Flota
# ---------------------------------------------------------------------------
VEHICULOS_POR_DEPOSITO = (8, 14)  # rango por depósito (flota ajustada para uso casi diario)
FACTOR_CHOFERES = 1.2  # choferes = vehículos * este factor

# Catálogo de modelos técnicos (Modelos_Vehiculo).
# consumo_teorico_l_100km es el dato "de fábrica" contra el que después
# se puede comparar el consumo real observado.
MODELOS_VEHICULO = [
    {"marca": "Mercedes-Benz", "modelo": "Accelo 1016", "tipo": "camión",
     "potencia_hp": 160, "cilindrada_cc": 4249, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 150,
     "tara_kg": 3900, "capacidad_carga_kg": 6500, "capacidad_carga_m3": 22,
     "configuracion_eje": "4x2", "consumo_teorico_l_100km": 22},
    {"marca": "Iveco", "modelo": "Daily 70C17", "tipo": "camión",
     "potencia_hp": 170, "cilindrada_cc": 2998, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 100,
     "tara_kg": 2600, "capacidad_carga_kg": 4200, "capacidad_carga_m3": 16,
     "configuracion_eje": "4x2", "consumo_teorico_l_100km": 15},
    {"marca": "Ford", "modelo": "Cargo 1119", "tipo": "camión",
     "potencia_hp": 190, "cilindrada_cc": 3922, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 160,
     "tara_kg": 4300, "capacidad_carga_kg": 7100, "capacidad_carga_m3": 24,
     "configuracion_eje": "4x2", "consumo_teorico_l_100km": 24},
    {"marca": "Volkswagen", "modelo": "Delivery Express 9.170", "tipo": "camión",
     "potencia_hp": 170, "cilindrada_cc": 4600, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 140,
     "tara_kg": 3700, "capacidad_carga_kg": 5700, "capacidad_carga_m3": 20,
     "configuracion_eje": "4x2", "consumo_teorico_l_100km": 20},
    {"marca": "Iveco", "modelo": "Tector 170E22", "tipo": "camión",
     "potencia_hp": 220, "cilindrada_cc": 5880, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 200,
     "tara_kg": 5200, "capacidad_carga_kg": 9500, "capacidad_carga_m3": 30,
     "configuracion_eje": "6x2", "consumo_teorico_l_100km": 28},
    {"marca": "Mercedes-Benz", "modelo": "Atego 1719", "tipo": "camión",
     "potencia_hp": 190, "cilindrada_cc": 4801, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 200,
     "tara_kg": 5400, "capacidad_carga_kg": 10200, "capacidad_carga_m3": 32,
     "configuracion_eje": "6x2", "consumo_teorico_l_100km": 27},
    {"marca": "Fiat", "modelo": "Ducato Cargo", "tipo": "camioneta",
     "potencia_hp": 140, "cilindrada_cc": 2287, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 90,
     "tara_kg": 1900, "capacidad_carga_kg": 1500, "capacidad_carga_m3": 10,
     "configuracion_eje": "4x2", "consumo_teorico_l_100km": 11},
    {"marca": "Renault", "modelo": "Master Furgón", "tipo": "camioneta",
     "potencia_hp": 135, "cilindrada_cc": 2298, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 80,
     "tara_kg": 1850, "capacidad_carga_kg": 1400, "capacidad_carga_m3": 9,
     "configuracion_eje": "4x2", "consumo_teorico_l_100km": 10.5},
    {"marca": "Volkswagen", "modelo": "Delivery Express 6.160", "tipo": "camión",
     "potencia_hp": 160, "cilindrada_cc": 3800, "transmision": "manual_5",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 120,
     "tara_kg": 3200, "capacidad_carga_kg": 4600, "capacidad_carga_m3": 18,
     "configuracion_eje": "4x2", "consumo_teorico_l_100km": 18},
    {"marca": "Iveco", "modelo": "Daily 35S14", "tipo": "camioneta",
     "potencia_hp": 146, "cilindrada_cc": 2998, "transmision": "manual_6",
     "tipo_combustible": "diesel", "capacidad_tanque_l": 90,
     "tara_kg": 2100, "capacidad_carga_kg": 1700, "capacidad_carga_m3": 11,
     "configuracion_eje": "4x2", "consumo_teorico_l_100km": 12.5},
]

# Antigüedad de la flota: bimodal (renovación por tandas), no uniforme.
# Con probabilidad PROB_FLOTA_NUEVA el vehículo es "casi nuevo" (0-2 años
# al momento de alta), si no, es de la tanda vieja (8-12 años).
PROB_FLOTA_NUEVA = 0.35
EDAD_NUEVA_ANIOS = (0, 2)
EDAD_VIEJA_ANIOS = (8, 12)

# Km recorridos promedio por año para un camión de reparto (varía por unidad
# dentro de este rango). Se usa para estimar el kilometraje "de arrastre"
# que ya tenía un vehículo viejo antes de que arranque el período simulado.
KM_PROMEDIO_ANUAL_RANGO = (30_000, 55_000)

# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
CLIENTES_POR_DEPOSITO = (350, 550)
TIPOS_CLIENTE = ["kiosco", "supermercado", "bar_restaurante", "mayorista", "autoservicio"]
# Peso relativo de cada tipo en la cartera de clientes (no todos igual de comunes)
PESOS_TIPOS_CLIENTE = [0.35, 0.15, 0.20, 0.08, 0.22]

# Frecuencia de pedido base (en días) por tipo de cliente.
# Un supermercado pide seguido, un kiosco espacia más.
# Recalibrado al alza (pedidos más frecuentes) para que el volumen de
# reparto alcance a mantener ocupada casi todos los días hábiles a una
# flota más chica (ver VEHICULOS_POR_DEPOSITO): un camión es un activo
# caro que no conviene tener parado.
FRECUENCIA_PEDIDO_DIAS = {
    "kiosco": 10,
    "supermercado": 4,
    "bar_restaurante": 6,
    "mayorista": 3,
    "autoservicio": 7,
}

# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------
CANTIDAD_PRODUCTOS = 26

CATEGORIAS_PRODUCTO = {
    "gaseosa": {"peso_kg": (0.35, 2.3), "volumen_l": (0.354, 2.25), "precio_base": (900, 2600)},
    "cerveza": {"peso_kg": (0.35, 1.0), "volumen_l": (0.34, 1.0), "precio_base": (700, 2200)},
    "agua": {"peso_kg": (0.5, 6.3), "volumen_l": (0.5, 6.0), "precio_base": (500, 2100)},
    "jugo": {"peso_kg": (0.2, 1.0), "volumen_l": (0.2, 1.0), "precio_base": (600, 1800)},
    "isotonica": {"peso_kg": (0.5, 0.6), "volumen_l": (0.5, 0.6), "precio_base": (900, 1600)},
}

# ---------------------------------------------------------------------------
# Inflación trimestral aplicada a precios de productos (Detalle_Pedido usa
# el precio vigente al momento del pedido, no un precio fijo).
# ---------------------------------------------------------------------------
INFLACION_TRIMESTRAL_RANGO = (0.05, 0.15)  # entre 5% y 15% por trimestre

# ---------------------------------------------------------------------------
# Estacionalidad de demanda: multiplicador por mes (1-12).
# Pico en verano (dic-feb), valle en invierno (jun-jul), Argentina.
# ---------------------------------------------------------------------------
ESTACIONALIDAD_MENSUAL = {
    1: 1.35, 2: 1.30, 3: 1.10, 4: 0.95, 5: 0.85, 6: 0.75,
    7: 0.78, 8: 0.85, 9: 0.95, 10: 1.05, 11: 1.15, 12: 1.40,
}

# ---------------------------------------------------------------------------
# Viajes / capacidad de reparto
# ---------------------------------------------------------------------------
PARADAS_POR_VIAJE = (4, 12)  # cuántos pedidos entran en un viaje típico
KM_POR_PARADA_RANGO = (3, 14)  # km recorridos entre una parada y otra (zona urbana/periurbana)
DIAS_ENTRE_PEDIDO_Y_ENTREGA = (1, 3)

# ---------------------------------------------------------------------------
# Combustible: se recarga aprox. cada vez que se consume un % del tanque.
# ---------------------------------------------------------------------------
FRACCION_TANQUE_ENTRE_CARGAS = (0.55, 0.85)
PRECIO_DIESEL_INICIAL = 350  # $/litro al inicio del período (referencia)
INFLACION_COMBUSTIBLE_TRIMESTRAL = (0.06, 0.16)  # el combustible suele subir más que el IPC general

# ---------------------------------------------------------------------------
# Mantenimiento: umbrales de km para servicios preventivos.
# ---------------------------------------------------------------------------
UMBRALES_PREVENTIVO_KM = {
    "cambio_aceite_filtro": 10_000,
    "frenos": 30_000,
    "cubiertas": 45_000,
    "correa_distribucion": 80_000,
}

# Costo de mano de obra por tipo de service (rango $)
COSTO_MANO_OBRA_PREVENTIVO = {
    "cambio_aceite_filtro": (15_000, 30_000),
    "frenos": (25_000, 50_000),
    "cubiertas": (10_000, 20_000),
    "correa_distribucion": (40_000, 80_000),
}
COSTO_MANO_OBRA_CORRECTIVO = (20_000, 150_000)

# Tasa base (eventos/año) de mantenimiento correctivo para un vehículo
# "promedio" (0 años, 0 km). Se ajusta por antigüedad y km recorridos.
TASA_BASE_CORRECTIVO_ANUAL = 0.8

# Duración típica (días) que un vehículo queda fuera de servicio por tipo de evento
DURACION_FUERA_SERVICIO_DIAS = {
    "preventivo": (1, 2),
    "correctivo": (1, 6),
    "otro": (1, 10),  # ej. "esperando repuesto", accidente menor
}

# ---------------------------------------------------------------------------
# Insumos / repuestos (catálogo)
# ---------------------------------------------------------------------------
INSUMOS = [
    {"nombre": "Aceite de motor 15W40 (litro)", "unidad_medida": "litro", "costo_unitario_referencia": 4500},
    {"nombre": "Filtro de aceite", "unidad_medida": "unidad", "costo_unitario_referencia": 8000},
    {"nombre": "Filtro de aire", "unidad_medida": "unidad", "costo_unitario_referencia": 12000},
    {"nombre": "Filtro de gasoil", "unidad_medida": "unidad", "costo_unitario_referencia": 9500},
    {"nombre": "Cubierta 215/75 R17.5", "unidad_medida": "unidad", "costo_unitario_referencia": 180000},
    {"nombre": "Pastillas de freno (juego)", "unidad_medida": "juego", "costo_unitario_referencia": 65000},
    {"nombre": "Discos de freno (par)", "unidad_medida": "par", "costo_unitario_referencia": 95000},
    {"nombre": "Correa de distribución (kit)", "unidad_medida": "kit", "costo_unitario_referencia": 220000},
    {"nombre": "Batería 12V 150Ah", "unidad_medida": "unidad", "costo_unitario_referencia": 150000},
    {"nombre": "Amortiguador", "unidad_medida": "unidad", "costo_unitario_referencia": 85000},
    {"nombre": "Correa de alternador", "unidad_medida": "unidad", "costo_unitario_referencia": 25000},
    {"nombre": "Líquido refrigerante (litro)", "unidad_medida": "litro", "costo_unitario_referencia": 6000},
]

# ---------------------------------------------------------------------------
# Ruido / calidad de datos deliberada
# ---------------------------------------------------------------------------
PROB_KM_ACTUAL_DESACTUALIZADO = 0.12  # % de vehículos con km_actual "viejo"
PROB_MOTIVO_INCONSISTENTE = 0.15      # % de historial con motivo con variantes/typos
PROB_OUTLIER_COMBUSTIBLE = 0.03       # % de cargas con volumen atípico
PROB_ESTADO_ALEATORIO_EXTRA = 0.08    # % de eventos de estado sin mantenimiento asociado, por año de vehículo activo

# Insumos típicos asociados a cada tipo de service preventivo (nombres tal
# cual figuran en config.INSUMOS). Se usan para armar Detalle_Mantenimiento.
INSUMOS_POR_TIPO_PREVENTIVO = {
    "cambio_aceite_filtro": ["Aceite de motor 15W40 (litro)", "Filtro de aceite"],
    "frenos": ["Pastillas de freno (juego)"],
    "cubiertas": ["Cubierta 215/75 R17.5"],
    "correa_distribucion": ["Correa de distribución (kit)", "Líquido refrigerante (litro)"],
}
NOMBRES_LEGIBLES_TIPO = {
    "cambio_aceite_filtro": "Cambio de aceite y filtro",
    "frenos": "Service de frenos",
    "cubiertas": "Cambio de cubiertas",
    "correa_distribucion": "Cambio de correa de distribución",
}

TALLERES = [
    "Taller Mecánico San Martín", "Service Oficial Iveco", "Taller Rodríguez Hnos.",
    "Gomería y Mecánica El Rápido", "Taller Central de Flota", "Frenos y Embragues Sur",
    "Taller Mecánico La Ruta", "Service Oficial Mercedes-Benz", "Taller Diesel Norte",
]

# Motivos de baja/parada NO asociados a un evento de Mantenimiento registrado
# (ruido operativo real: cosas que pasan y no siempre quedan bien documentadas)
MOTIVOS_ESTADO_EXTRA = [
    "Esperando repuesto",
    "Accidente menor en ruta",
    "Rotura de parabrisas",
    "Faltante de neumático de auxilio",
    "Revisión técnica vencida",
    "Vehículo prestado a otra sucursal",
    "Pinchadura en ruta",
    "Falla eléctrica menor",
]

INSUMOS_CORRECTIVO_POSIBLES = [
    "Batería 12V 150Ah", "Amortiguador", "Correa de alternador",
    "Filtro de gasoil", "Filtro de aire", "Discos de freno (par)",
    "Líquido refrigerante (litro)",
]

# ---------------------------------------------------------------------------
# Salida
# ---------------------------------------------------------------------------
OUTPUT_DIR = "data"
