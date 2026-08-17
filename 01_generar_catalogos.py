"""
01_generar_catalogos.py
========================
Genera las tablas "catálogo": Depositos, Modelos_Vehiculo, Zonas,
Productos e Insumos. Son la base sobre la que se apoya todo lo demás
(no cambian en el tiempo, o cambian muy poco).

Salida: data/depositos.csv, modelos_vehiculo.csv, zonas.csv,
        productos.csv, insumos.csv
"""

import os
import pandas as pd
from faker import Faker

import config as cfg

fake = Faker("es_AR")
Faker.seed(cfg.SEED)


def generar_depositos() -> pd.DataFrame:
    """Un depósito por localidad definida en config."""
    filas = []
    for i, dep in enumerate(cfg.DEPOSITOS, start=1):
        filas.append({
            "deposito_id": i,
            "nombre": dep["nombre"],
            "localidad": dep["localidad"],
        })
    return pd.DataFrame(filas)


def generar_modelos_vehiculo() -> pd.DataFrame:
    """Catálogo técnico: uno por modelo definido en config (no por unidad física)."""
    filas = []
    for i, m in enumerate(cfg.MODELOS_VEHICULO, start=1):
        fila = {"modelo_id": i, **m}
        filas.append(fila)
    return pd.DataFrame(filas)


def generar_zonas(depositos: pd.DataFrame) -> pd.DataFrame:
    """
    Entre 3 y 5 zonas de reparto por depósito, usando nombres de barrios
    reales/plausibles de cada localidad (definidos en config.BARRIOS_POR_DEPOSITO).
    """
    filas = []
    zona_id = 1
    for _, dep in depositos.iterrows():
        n_zonas = int(cfg.RNG.integers(cfg.ZONAS_POR_DEPOSITO[0], cfg.ZONAS_POR_DEPOSITO[1] + 1))
        barrios_disponibles = cfg.BARRIOS_POR_DEPOSITO[dep["nombre"]].copy()
        cfg.RNG.shuffle(barrios_disponibles)
        seleccionados = barrios_disponibles[:n_zonas]
        for nombre in seleccionados:
            filas.append({
                "zona_id": zona_id,
                "nombre": nombre,
                "deposito_id": dep["deposito_id"],
            })
            zona_id += 1
    return pd.DataFrame(filas)


def generar_productos() -> pd.DataFrame:
    """
    Catálogo de bebidas. precio_base es el precio de referencia al inicio
    del período (2022-01-01); el precio real que se usa en cada pedido se
    calcula después aplicando la inflación acumulada (ver 03_generar_pedidos.py).

    El peso se deriva del volumen (densidad ~1.0-1.03 kg/L para estas bebidas,
    más un plus de packaging), en vez de sortearse de forma independiente,
    para que peso y volumen sean físicamente consistentes entre sí.
    """
    filas = []
    categorias = list(cfg.CATEGORIAS_PRODUCTO.keys())
    nombres_por_categoria = {
        "gaseosa": ["Cola", "Cola Zero", "Lima Limón", "Naranja", "Pomelo", "Tónica"],
        "cerveza": ["Rubia", "Rubia Sin Alcohol", "IPA", "Negra", "Roja"],
        "agua": ["Agua Mineral Sin Gas", "Agua Mineral Con Gas", "Agua Saborizada"],
        "jugo": ["Jugo de Naranja", "Jugo Multifruta", "Jugo de Manzana"],
        "isotonica": ["Isotónica Limón", "Isotónica Naranja"],
    }
    # presentacion -> (volumen_unitario_l, unidades_por_bulto, es_pack)
    presentaciones = {
        "retornable 1L": (1.0, 1),
        "no retornable 1.5L": (1.5, 1),
        "no retornable 2.25L": (2.25, 1),
        "lata 354ml": (0.354, 1),
        "pack x6 500ml": (0.5, 6),
        "botella 600ml": (0.6, 1),
    }

    producto_id = 1
    while producto_id <= cfg.CANTIDAD_PRODUCTOS:
        categoria = fake.random_element(categorias)
        nombre_base = fake.random_element(nombres_por_categoria[categoria])
        presentacion = fake.random_element(list(presentaciones.keys()))
        vol_unitario, unidades = presentaciones[presentacion]
        rangos = cfg.CATEGORIAS_PRODUCTO[categoria]

        volumen_total_l = round(vol_unitario * unidades, 3)
        # Densidad realista + packaging (vidrio/plástico/lata aporta algo de peso extra)
        densidad = cfg.RNG.uniform(1.0, 1.05)
        peso_packaging = 0.03 * unidades if "lata" in presentacion else 0.08 * unidades
        peso = round(volumen_total_l * densidad + peso_packaging, 2)

        precio_base = round(cfg.RNG.uniform(*rangos["precio_base"]) * unidades, -1)

        filas.append({
            "producto_id": producto_id,
            "nombre": f"{nombre_base} {presentacion}",
            "categoria": categoria,
            "presentacion": presentacion,
            "peso_kg": peso,
            "volumen_l": volumen_total_l,
            "precio_base": precio_base,
        })
        producto_id += 1

    return pd.DataFrame(filas)


def generar_insumos() -> pd.DataFrame:
    filas = []
    for i, ins in enumerate(cfg.INSUMOS, start=1):
        filas.append({"insumo_id": i, **ins})
    return pd.DataFrame(filas)


def main():
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    depositos = generar_depositos()
    modelos = generar_modelos_vehiculo()
    zonas = generar_zonas(depositos)
    productos = generar_productos()
    insumos = generar_insumos()

    depositos.to_csv(f"{cfg.OUTPUT_DIR}/depositos.csv", index=False)
    modelos.to_csv(f"{cfg.OUTPUT_DIR}/modelos_vehiculo.csv", index=False)
    zonas.to_csv(f"{cfg.OUTPUT_DIR}/zonas.csv", index=False)
    productos.to_csv(f"{cfg.OUTPUT_DIR}/productos.csv", index=False)
    insumos.to_csv(f"{cfg.OUTPUT_DIR}/insumos.csv", index=False)

    print(f"Depositos: {len(depositos)}")
    print(f"Modelos_Vehiculo: {len(modelos)}")
    print(f"Zonas: {len(zonas)}")
    print(f"Productos: {len(productos)}")
    print(f"Insumos: {len(insumos)}")


if __name__ == "__main__":
    main()
