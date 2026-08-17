"""
06_validar_dataset.py
=======================
No forma parte del pipeline de generación en sí, sino un chequeo posterior
de integridad referencial y consistencia general. Útil para correr después
de cada corrida (o cada vez que ajustes config.py) y confirmar que no se
rompió nada.

Uso:
    python3 06_validar_dataset.py
"""

import pandas as pd
import config as cfg


def cargar_todo():
    d = cfg.OUTPUT_DIR
    return {
        "depositos": pd.read_csv(f"{d}/depositos.csv"),
        "modelos_vehiculo": pd.read_csv(f"{d}/modelos_vehiculo.csv"),
        "zonas": pd.read_csv(f"{d}/zonas.csv"),
        "productos": pd.read_csv(f"{d}/productos.csv"),
        "insumos": pd.read_csv(f"{d}/insumos.csv"),
        "vehiculos": pd.read_csv(f"{d}/vehiculos.csv"),
        "choferes": pd.read_csv(f"{d}/choferes.csv"),
        "clientes": pd.read_csv(f"{d}/clientes.csv"),
        "pedidos": pd.read_csv(f"{d}/pedidos.csv"),
        "detalle_pedido": pd.read_csv(f"{d}/detalle_pedido.csv"),
        "viajes": pd.read_csv(f"{d}/viajes.csv"),
        "viaje_pedido": pd.read_csv(f"{d}/viaje_pedido.csv"),
        "combustible": pd.read_csv(f"{d}/combustible.csv"),
        "mantenimiento": pd.read_csv(f"{d}/mantenimiento.csv"),
        "detalle_mantenimiento": pd.read_csv(f"{d}/detalle_mantenimiento.csv"),
        "historial_estado_vehiculo": pd.read_csv(f"{d}/historial_estado_vehiculo.csv"),
    }


def check(nombre, condicion_ok, detalle=""):
    estado = "OK " if condicion_ok else "FALLA"
    print(f"[{estado}] {nombre}" + (f" — {detalle}" if detalle and not condicion_ok else ""))
    return condicion_ok


def fk_huerfanas(hijo: pd.DataFrame, col_hijo: str, padre: pd.DataFrame, col_padre: str) -> int:
    return hijo[~hijo[col_hijo].isin(padre[col_padre])].shape[0]


def main():
    t = cargar_todo()
    todo_ok = True

    print("--- Integridad referencial (FKs) ---")
    fks = [
        ("zonas.deposito_id -> depositos", t["zonas"], "deposito_id", t["depositos"], "deposito_id"),
        ("vehiculos.modelo_id -> modelos_vehiculo", t["vehiculos"], "modelo_id", t["modelos_vehiculo"], "modelo_id"),
        ("vehiculos.deposito_id -> depositos", t["vehiculos"], "deposito_id", t["depositos"], "deposito_id"),
        ("choferes.deposito_id -> depositos", t["choferes"], "deposito_id", t["depositos"], "deposito_id"),
        ("clientes.zona_id -> zonas", t["clientes"], "zona_id", t["zonas"], "zona_id"),
        ("pedidos.cliente_id -> clientes", t["pedidos"], "cliente_id", t["clientes"], "cliente_id"),
        ("detalle_pedido.pedido_id -> pedidos", t["detalle_pedido"], "pedido_id", t["pedidos"], "pedido_id"),
        ("detalle_pedido.producto_id -> productos", t["detalle_pedido"], "producto_id", t["productos"], "producto_id"),
        ("viajes.vehiculo_id -> vehiculos", t["viajes"], "vehiculo_id", t["vehiculos"], "vehiculo_id"),
        ("viajes.chofer_id -> choferes", t["viajes"], "chofer_id", t["choferes"], "chofer_id"),
        ("viajes.zona_id -> zonas", t["viajes"], "zona_id", t["zonas"], "zona_id"),
        ("viaje_pedido.viaje_id -> viajes", t["viaje_pedido"], "viaje_id", t["viajes"], "viaje_id"),
        ("viaje_pedido.pedido_id -> pedidos", t["viaje_pedido"], "pedido_id", t["pedidos"], "pedido_id"),
        ("combustible.vehiculo_id -> vehiculos", t["combustible"], "vehiculo_id", t["vehiculos"], "vehiculo_id"),
        ("mantenimiento.vehiculo_id -> vehiculos", t["mantenimiento"], "vehiculo_id", t["vehiculos"], "vehiculo_id"),
        ("detalle_mantenimiento.mantenimiento_id -> mantenimiento", t["detalle_mantenimiento"], "mantenimiento_id", t["mantenimiento"], "mantenimiento_id"),
        ("detalle_mantenimiento.insumo_id -> insumos", t["detalle_mantenimiento"], "insumo_id", t["insumos"], "insumo_id"),
        ("historial_estado_vehiculo.vehiculo_id -> vehiculos", t["historial_estado_vehiculo"], "vehiculo_id", t["vehiculos"], "vehiculo_id"),
    ]
    for nombre, hijo, col_hijo, padre, col_padre in fks:
        n_huerfanas = fk_huerfanas(hijo, col_hijo, padre, col_padre)
        ok = check(nombre, n_huerfanas == 0, f"{n_huerfanas} filas huérfanas")
        todo_ok = todo_ok and ok

    print("\n--- Consistencia de negocio ---")

    # cada pedido "entregado" con viaje asociado debería tener 1 sola aparición en viaje_pedido
    dup = t["viaje_pedido"]["pedido_id"].duplicated().sum()
    todo_ok &= check("Ningún pedido aparece en más de un viaje", dup == 0, f"{dup} duplicados")

    # viajes: km_final siempre >= km_inicial
    km_invalido = (t["viajes"]["km_final"] < t["viajes"]["km_inicial"]).sum()
    todo_ok &= check("viajes.km_final >= km_inicial siempre", km_invalido == 0, f"{km_invalido} viajes inválidos")

    # fechas de pedido dentro del período de simulación
    fechas_pedido = pd.to_datetime(t["pedidos"]["fecha_pedido"])
    fuera_rango = ((fechas_pedido < cfg.FECHA_INICIO) | (fechas_pedido > cfg.FECHA_FIN)).sum()
    todo_ok &= check("Fechas de pedido dentro del período simulado", fuera_rango == 0, f"{fuera_rango} fuera de rango")

    # cantidades y precios positivos
    cant_invalida = (t["detalle_pedido"]["cantidad"] <= 0).sum()
    todo_ok &= check("Cantidades de detalle_pedido > 0", cant_invalida == 0, f"{cant_invalida} filas")
    precio_invalido = (t["detalle_pedido"]["precio_unitario"] <= 0).sum()
    todo_ok &= check("Precios unitarios > 0", precio_invalido == 0, f"{precio_invalido} filas")

    # litros de combustible dentro de un rango físicamente posible (incluso con outliers)
    litros_invalidos = (t["combustible"]["litros"] <= 0).sum()
    todo_ok &= check("Litros de combustible > 0", litros_invalidos == 0, f"{litros_invalidos} filas")

    # costos de mantenimiento no negativos
    costo_invalido = (t["mantenimiento"]["costo_mano_obra"] < 0).sum()
    todo_ok &= check("Costos de mano de obra >= 0", costo_invalido == 0, f"{costo_invalido} filas")

    # todo vehículo tiene al menos un depósito válido, y sus fechas alta<baja si aplica
    veh = t["vehiculos"]
    con_baja = veh.dropna(subset=["fecha_baja"])
    orden_fechas_mal = (pd.to_datetime(con_baja["fecha_baja"]) <= pd.to_datetime(con_baja["fecha_alta"])).sum()
    todo_ok &= check("fecha_baja posterior a fecha_alta (cuando existe)", orden_fechas_mal == 0, f"{orden_fechas_mal} filas")

    print("\n--- Resumen general (para tener una foto rápida) ---")
    for nombre, df in t.items():
        print(f"  {nombre:30s} {len(df):>8,d} filas")

    print(f"\n{'✅ Dataset consistente' if todo_ok else '⚠️  Hay inconsistencias para revisar'}")


if __name__ == "__main__":
    main()
