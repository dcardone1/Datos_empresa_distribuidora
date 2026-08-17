"""
04_generar_viajes.py
======================
Genera Viajes y Viaje_Pedido.

Lógica:
1. Se agrupan los pedidos "entregado" por (depósito, zona, fecha de entrega
   estimada) -> cada grupo es un viaje candidato (reparto por zona).
2. Si un grupo supera la cantidad máxima de paradas por viaje, se parte en
   más de un viaje ese mismo día/zona.
3. Los grupos se procesan en orden CRONOLÓGICO para poder:
   a) acumular el km recorrido de cada vehículo de forma consistente
      (el km_inicial de un viaje es el km_final del viaje anterior de
      ese vehículo), arrancando desde vehiculo.km_inicial_periodo.
   b) evitar asignar el mismo vehículo o chofer a dos viajes el mismo día.
4. Solo se consideran vehículos activos en la fecha del viaje (entre
   fecha_alta y fecha_baja).

Nota: esta etapa todavía no tiene en cuenta el estado_actual del vehículo
(fuera de servicio por mantenimiento), porque el mantenimiento se calcula
recién en el script 5 a partir del km acumulado acá. Es una simplificación
consciente: en el dataset final puede haber alguna inconsistencia menor
entre Historial_Estado_Vehiculo y Viajes, lo cual es intencional (ruido
realista) más que un bug a corregir.

Salida: data/viajes.csv, viaje_pedido.csv
        (también reescribe data/vehiculos.csv con el km_actual final)
"""

import pandas as pd
from datetime import datetime, timedelta

import config as cfg


def elegir_disponible(candidatos: list, usados_hoy: set):
    """Elige un elemento al azar entre los candidatos que no fueron usados hoy."""
    libres = [c for c in candidatos if c not in usados_hoy]
    if not libres:
        return None
    idx = cfg.RNG.integers(0, len(libres))
    return libres[idx]


def armar_grupos_de_viaje(pedidos: pd.DataFrame, clientes: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve un DataFrame con una fila por viaje candidato:
    deposito_id, zona_id, fecha, lista de pedido_ids.
    """
    ped = pedidos[pedidos["estado"] == "entregado"].merge(
        clientes[["cliente_id", "zona_id"]], on="cliente_id", how="left"
    ).merge(
        cfg_zonas_deposito(), on="zona_id", how="left"
    )

    grupos = []
    llave_cols = ["deposito_id", "zona_id", "fecha_entrega_estimada"]
    for llave, sub in ped.groupby(llave_cols):
        deposito_id, zona_id, fecha = llave
        pedido_ids = sub["pedido_id"].tolist()
        cfg.RNG.shuffle(pedido_ids)

        # partir en sub-viajes si hay demasiadas paradas para un solo camión
        max_paradas = cfg.PARADAS_POR_VIAJE[1]
        for i in range(0, len(pedido_ids), max_paradas):
            chunk = pedido_ids[i:i + max_paradas]
            grupos.append({
                "deposito_id": deposito_id,
                "zona_id": zona_id,
                "fecha": fecha,
                "pedido_ids": chunk,
            })

    df = pd.DataFrame(grupos)
    df["fecha_dt"] = pd.to_datetime(df["fecha"])
    return df.sort_values("fecha_dt").reset_index(drop=True)


def cfg_zonas_deposito():
    zonas = pd.read_csv(f"{cfg.OUTPUT_DIR}/zonas.csv")
    return zonas[["zona_id", "deposito_id"]]


def generar_viajes_y_detalle(grupos: pd.DataFrame, vehiculos: pd.DataFrame,
                              choferes: pd.DataFrame, pedidos: pd.DataFrame):
    viajes = []
    viaje_pedido = []
    viaje_id = 1

    # Estado mutable que se va actualizando a medida que "avanza" el tiempo
    km_acumulado = dict(zip(vehiculos["vehiculo_id"], vehiculos["km_inicial_periodo"]))
    vehiculos_por_deposito = {
        dep_id: sub["vehiculo_id"].tolist()
        for dep_id, sub in vehiculos.groupby("deposito_id")
    }
    choferes_por_deposito = {
        dep_id: sub["chofer_id"].tolist()
        for dep_id, sub in choferes.groupby("deposito_id")
    }
    vehiculos_idx = vehiculos.set_index("vehiculo_id")

    dia_actual = None
    usados_hoy_vehiculo = set()
    usados_hoy_chofer = set()

    pedidos_horas = pedidos.set_index("pedido_id")

    for _, grupo in grupos.iterrows():
        fecha_dt = grupo["fecha_dt"]

        # al cambiar de día, se liberan los vehículos/choferes usados
        if dia_actual != fecha_dt:
            dia_actual = fecha_dt
            usados_hoy_vehiculo = set()
            usados_hoy_chofer = set()

        dep_id = grupo["deposito_id"]
        candidatos_vehiculo = [
            v for v in vehiculos_por_deposito.get(dep_id, [])
            if _vehiculo_activo(vehiculos_idx.loc[v], fecha_dt)
        ]
        vehiculo_id = elegir_disponible(candidatos_vehiculo, usados_hoy_vehiculo)
        chofer_id = elegir_disponible(choferes_por_deposito.get(dep_id, []), usados_hoy_chofer)

        if vehiculo_id is None or chofer_id is None:
            # No hay flota/choferes libres ese día para esa zona: se descarta
            # este viaje candidato (en la realidad, se reprogramaría; para
            # simplificar el dataset lo omitimos, y ese pequeño % de pedidos
            # queda sin viaje asociado, lo cual también es realista).
            continue

        usados_hoy_vehiculo.add(vehiculo_id)
        usados_hoy_chofer.add(chofer_id)

        n_paradas = len(grupo["pedido_ids"])
        km_recorridos = round(
            cfg.RNG.uniform(8, 18)  # tramo depósito -> zona (ida)
            + n_paradas * cfg.RNG.uniform(*cfg.KM_POR_PARADA_RANGO)
            + cfg.RNG.uniform(8, 18),  # vuelta al depósito
            1
        )

        km_inicial = km_acumulado[vehiculo_id]
        km_final = round(km_inicial + km_recorridos, 1)
        km_acumulado[vehiculo_id] = km_final

        hora_salida = f"{int(cfg.RNG.integers(6, 9)):02d}:{int(cfg.RNG.integers(0, 59)):02d}"
        duracion_horas = 1 + n_paradas * cfg.RNG.uniform(0.3, 0.6)
        hora_salida_dt = datetime.strptime(hora_salida, "%H:%M")
        hora_llegada_dt = hora_salida_dt + timedelta(hours=duracion_horas)
        hora_llegada = hora_llegada_dt.strftime("%H:%M")

        viajes.append({
            "viaje_id": viaje_id,
            "vehiculo_id": int(vehiculo_id),
            "chofer_id": int(chofer_id),
            "zona_id": int(grupo["zona_id"]),
            "fecha": grupo["fecha"],
            "km_inicial": km_inicial,
            "km_final": km_final,
            "hora_salida": hora_salida,
            "hora_llegada": hora_llegada,
        })

        # orden de parada: aleatorio pero estable para este viaje
        orden = list(range(1, n_paradas + 1))
        for pos, pedido_id in zip(orden, grupo["pedido_ids"]):
            # hora de entrega real: se reparte a lo largo de la ventana del viaje,
            # con algo de ruido (entregas que se adelantan o retrasan un poco)
            fraccion = pos / n_paradas
            minutos_viaje = duracion_horas * 60 * fraccion
            hora_entrega_dt = hora_salida_dt + timedelta(
                minutes=minutos_viaje + cfg.RNG.uniform(-15, 20))
            viaje_pedido.append({
                "viaje_id": viaje_id,
                "pedido_id": int(pedido_id),
                "orden_parada": pos,
                "hora_entrega_real": hora_entrega_dt.strftime("%H:%M"),
            })

        viaje_id += 1

    vehiculos = vehiculos.copy()
    vehiculos["km_actual"] = vehiculos["vehiculo_id"].map(km_acumulado)
    return pd.DataFrame(viajes), pd.DataFrame(viaje_pedido), vehiculos


def _vehiculo_activo(vehiculo_row, fecha_dt) -> bool:
    fecha_alta = pd.to_datetime(vehiculo_row["fecha_alta"])
    fecha_baja = vehiculo_row["fecha_baja"]
    if fecha_dt < fecha_alta:
        return False
    if pd.notna(fecha_baja) and fecha_dt > pd.to_datetime(fecha_baja):
        return False
    return True


def aplicar_ruido_km_actual(vehiculos: pd.DataFrame) -> pd.DataFrame:
    """
    Simula que en un % de los vehículos el km_actual registrado en el
    sistema está desactualizado (no refleja el último viaje real), como
    pasaría en una empresa que carga esto a mano de vez en cuando.
    """
    vehiculos = vehiculos.copy()
    fechas_actualizacion = []
    for _, row in vehiculos.iterrows():
        if cfg.RNG.random() < cfg.PROB_KM_ACTUAL_DESACTUALIZADO:
            # el km "oficial" queda un poco atrás del real, y la fecha de
            # actualización es antigua
            desfasaje = cfg.RNG.uniform(0.85, 0.97)
            vehiculos.loc[row.name, "km_actual"] = round(row["km_actual"] * desfasaje)
            dias_atras = int(cfg.RNG.integers(30, 200))
            fechas_actualizacion.append(
                (datetime.strptime(cfg.FECHA_FIN, "%Y-%m-%d") - timedelta(days=dias_atras)
                 ).strftime("%Y-%m-%d"))
        else:
            fechas_actualizacion.append(cfg.FECHA_FIN)
    vehiculos["fecha_ultima_actualizacion_km"] = fechas_actualizacion
    return vehiculos


def main():
    pedidos = pd.read_csv(f"{cfg.OUTPUT_DIR}/pedidos.csv")
    clientes = pd.read_csv(f"{cfg.OUTPUT_DIR}/clientes.csv")
    vehiculos = pd.read_csv(f"{cfg.OUTPUT_DIR}/vehiculos.csv")
    choferes = pd.read_csv(f"{cfg.OUTPUT_DIR}/choferes.csv")

    grupos = armar_grupos_de_viaje(pedidos, clientes)
    viajes, viaje_pedido, vehiculos = generar_viajes_y_detalle(grupos, vehiculos, choferes, pedidos)
    vehiculos = aplicar_ruido_km_actual(vehiculos)

    viajes.to_csv(f"{cfg.OUTPUT_DIR}/viajes.csv", index=False)
    viaje_pedido.to_csv(f"{cfg.OUTPUT_DIR}/viaje_pedido.csv", index=False)
    vehiculos.to_csv(f"{cfg.OUTPUT_DIR}/vehiculos.csv", index=False)  # se reescribe con km_actual final

    pct_pedidos_con_viaje = viaje_pedido["pedido_id"].nunique() / (
        pedidos["estado"].eq("entregado").sum())

    print(f"Viajes: {len(viajes)}")
    print(f"Viaje_Pedido: {len(viaje_pedido)}")
    print(f"% de pedidos entregados que quedaron con viaje asociado: {pct_pedidos_con_viaje:.1%}")
    print(vehiculos[["vehiculo_id", "km_inicial_periodo", "km_actual"]].describe())


if __name__ == "__main__":
    main()
