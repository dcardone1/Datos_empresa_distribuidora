"""
02_generar_flota_clientes.py
=============================
Genera Vehiculos, Choferes y Clientes.

Los vehículos se asignan a un depósito y un modelo técnico, con una
antigüedad bimodal (tanda de flota nueva vs. tanda vieja, simulando
renovaciones parciales típicas de una empresa real).

Los clientes se distribuyen de forma NO uniforme entre las zonas de su
depósito (algunas zonas concentran más comercios que otras).

Salida: data/vehiculos.csv, choferes.csv, clientes.csv
"""

import pandas as pd
from datetime import datetime, timedelta
from faker import Faker

import config as cfg

fake = Faker("es_AR")
Faker.seed(cfg.SEED + 1)

FECHA_INICIO = datetime.strptime(cfg.FECHA_INICIO, "%Y-%m-%d")
FECHA_FIN = datetime.strptime(cfg.FECHA_FIN, "%Y-%m-%d")


def fecha_aleatoria_entre(inicio: datetime, fin: datetime) -> datetime:
    dias = (fin - inicio).days
    return inicio + timedelta(days=int(cfg.RNG.integers(0, max(dias, 1))))


def generar_vehiculos(depositos: pd.DataFrame, modelos: pd.DataFrame) -> pd.DataFrame:
    filas = []
    vehiculo_id = 1
    patentes_usadas = set()

    for _, dep in depositos.iterrows():
        n_vehiculos = int(cfg.RNG.integers(cfg.VEHICULOS_POR_DEPOSITO[0],
                                            cfg.VEHICULOS_POR_DEPOSITO[1] + 1))
        for _ in range(n_vehiculos):
            modelo = modelos.sample(random_state=int(cfg.RNG.integers(0, 1_000_000))).iloc[0]

            # Antigüedad bimodal: flota "nueva" vs. flota "vieja"
            es_nueva = cfg.RNG.random() < cfg.PROB_FLOTA_NUEVA
            rango_edad = cfg.EDAD_NUEVA_ANIOS if es_nueva else cfg.EDAD_VIEJA_ANIOS
            edad_anios = cfg.RNG.uniform(*rango_edad)

            # fecha_alta: cuándo se incorporó el vehículo a la flota. Puede ser
            # antes del período de análisis (vehículo ya operaba) o durante el
            # período (incorporación de una unidad nueva).
            fecha_compra = FECHA_FIN - timedelta(days=int(edad_anios * 365))
            fecha_alta = max(fecha_compra, FECHA_INICIO - timedelta(days=365 * 3))
            # Si la fecha de alta calculada cae después del inicio del período
            # y antes del fin, se respeta tal cual (entra "nuevo" a mitad de camino)
            if fecha_alta > FECHA_FIN:
                fecha_alta = FECHA_INICIO

            # Patente estilo argentino (AA123BB), sin repetir
            patente = fake.license_plate()
            while patente in patentes_usadas:
                patente = fake.license_plate()
            patentes_usadas.add(patente)

            # Un pequeño % de la flota se da de baja antes del fin del período
            fecha_baja = None
            if cfg.RNG.random() < 0.05:
                dias_restantes = (FECHA_FIN - max(fecha_alta, FECHA_INICIO)).days
                if dias_restantes > 30:
                    fecha_baja = max(fecha_alta, FECHA_INICIO) + timedelta(
                        days=int(cfg.RNG.integers(30, dias_restantes)))

            # Km "de arrastre": si el vehículo ya operaba antes del inicio del
            # período (fecha_alta anterior a FECHA_INICIO), estimamos cuánto
            # tenía acumulado a esa fecha según su antigüedad. Si es una
            # incorporación nueva durante el período, arranca en 0 (0km de agencia).
            tasa_km_anual = cfg.RNG.uniform(*cfg.KM_PROMEDIO_ANUAL_RANGO)
            if fecha_alta < FECHA_INICIO:
                anios_previos_al_inicio = (FECHA_INICIO - fecha_alta).days / 365
                km_inicial_periodo = round(anios_previos_al_inicio * tasa_km_anual
                                            * cfg.RNG.uniform(0.85, 1.15))
            else:
                km_inicial_periodo = 0.0

            filas.append({
                "vehiculo_id": vehiculo_id,
                "patente": patente,
                "modelo_id": int(modelo["modelo_id"]),
                "deposito_id": int(dep["deposito_id"]),
                "km_inicial_periodo": km_inicial_periodo,  # odómetro al 2022-01-01 (o al alta)
                "km_actual": km_inicial_periodo,  # se recalcula al final, tras generar Viajes
                "fecha_ultima_actualizacion_km": None,
                "estado_actual": "operativo",  # se recalcula tras Historial_Estado_Vehiculo
                "fecha_alta": fecha_alta.strftime("%Y-%m-%d"),
                "fecha_baja": fecha_baja.strftime("%Y-%m-%d") if fecha_baja else None,
            })
            vehiculo_id += 1

    return pd.DataFrame(filas)


def generar_choferes(depositos: pd.DataFrame, vehiculos: pd.DataFrame) -> pd.DataFrame:
    filas = []
    chofer_id = 1
    categorias_licencia = ["C1", "C2", "C3", "D1"]

    for _, dep in depositos.iterrows():
        n_vehiculos_dep = len(vehiculos[vehiculos["deposito_id"] == dep["deposito_id"]])
        n_choferes = max(1, round(n_vehiculos_dep * cfg.FACTOR_CHOFERES))
        for _ in range(n_choferes):
            fecha_ingreso = fecha_aleatoria_entre(
                FECHA_INICIO - timedelta(days=365 * 5), FECHA_FIN - timedelta(days=30))
            filas.append({
                "chofer_id": chofer_id,
                "nombre": fake.name(),
                "fecha_ingreso": fecha_ingreso.strftime("%Y-%m-%d"),
                "categoria_licencia": fake.random_element(categorias_licencia),
                "deposito_id": int(dep["deposito_id"]),
            })
            chofer_id += 1

    return pd.DataFrame(filas)


def generar_clientes(depositos: pd.DataFrame, zonas: pd.DataFrame) -> pd.DataFrame:
    filas = []
    cliente_id = 1
    tipos_nombre = {
        "kiosco": ["Kiosco", "Maxikiosco"],
        "supermercado": ["Supermercado", "Autoservicio Mayorista"],
        "bar_restaurante": ["Bar", "Restaurante", "Pizzería", "Parrilla"],
        "mayorista": ["Distribuidora", "Mayorista"],
        "autoservicio": ["Almacén", "Despensa", "Autoservicio"],
    }

    for _, dep in depositos.iterrows():
        zonas_dep = zonas[zonas["deposito_id"] == dep["deposito_id"]].reset_index(drop=True)
        n_clientes = int(cfg.RNG.integers(cfg.CLIENTES_POR_DEPOSITO[0],
                                           cfg.CLIENTES_POR_DEPOSITO[1] + 1))

        # Distribución NO uniforme de clientes entre zonas: se sortean pesos
        # aleatorios (Dirichlet) para que algunas zonas concentren más clientes.
        pesos_zona = cfg.RNG.dirichlet(alpha=[1.5] * len(zonas_dep))

        for _ in range(n_clientes):
            zona = zonas_dep.iloc[cfg.RNG.choice(len(zonas_dep), p=pesos_zona)]
            tipo = str(cfg.RNG.choice(cfg.TIPOS_CLIENTE, p=cfg.PESOS_TIPOS_CLIENTE))
            prefijo = fake.random_element(tipos_nombre[tipo])
            fecha_alta = fecha_aleatoria_entre(
                FECHA_INICIO - timedelta(days=365 * 2), FECHA_FIN - timedelta(days=15))

            filas.append({
                "cliente_id": cliente_id,
                "nombre": f"{prefijo} {fake.last_name()}",
                "tipo_cliente": tipo,
                "zona_id": int(zona["zona_id"]),
                "fecha_alta": fecha_alta.strftime("%Y-%m-%d"),
            })
            cliente_id += 1

    return pd.DataFrame(filas)


def main():
    depositos = pd.read_csv(f"{cfg.OUTPUT_DIR}/depositos.csv")
    modelos = pd.read_csv(f"{cfg.OUTPUT_DIR}/modelos_vehiculo.csv")
    zonas = pd.read_csv(f"{cfg.OUTPUT_DIR}/zonas.csv")

    vehiculos = generar_vehiculos(depositos, modelos)
    choferes = generar_choferes(depositos, vehiculos)
    clientes = generar_clientes(depositos, zonas)

    vehiculos.to_csv(f"{cfg.OUTPUT_DIR}/vehiculos.csv", index=False)
    choferes.to_csv(f"{cfg.OUTPUT_DIR}/choferes.csv", index=False)
    clientes.to_csv(f"{cfg.OUTPUT_DIR}/clientes.csv", index=False)

    print(f"Vehiculos: {len(vehiculos)}")
    print(f"Choferes: {len(choferes)}")
    print(f"Clientes: {len(clientes)}")
    print(clientes["tipo_cliente"].value_counts())


if __name__ == "__main__":
    main()
