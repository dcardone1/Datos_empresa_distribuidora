"""
03_generar_pedidos.py
=======================
Genera Pedidos y Detalle_Pedido.

Reglas de negocio aplicadas:
- Cada cliente pide con una frecuencia base según su tipo (kiosco, super, etc.),
  con ruido individual (cada cliente es un poco más o menos regular).
- La cantidad de pedidos por mes se modula con estacionalidad (pico en
  verano dic-feb, valle en invierno jun-jul), definida en config.ESTACIONALIDAD_MENSUAL.
- El precio de cada línea de pedido (Detalle_Pedido.precio_unitario) NO es
  fijo: se calcula aplicando la inflación trimestral acumulada desde el
  inicio del período hasta la fecha del pedido, más un pequeño ruido.
  Esto es clave para que el análisis de "costo/ingreso en el tiempo" sea
  realista y no un valor plano.

Salida: data/pedidos.csv, detalle_pedido.csv, inflacion_trimestral.csv
        (esta última se guarda como referencia/documentación para el análisis)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import config as cfg

FECHA_INICIO = datetime.strptime(cfg.FECHA_INICIO, "%Y-%m-%d")
FECHA_FIN = datetime.strptime(cfg.FECHA_FIN, "%Y-%m-%d")


def construir_tabla_inflacion() -> pd.DataFrame:
    """
    Arma una tabla de factores de inflación acumulada por trimestre calendario,
    sorteando una tasa distinta para cada trimestre dentro del rango definido
    en config.INFLACION_TRIMESTRAL_RANGO.
    """
    filas = []
    factor_acumulado = 1.0
    fecha_trimestre = datetime(FECHA_INICIO.year, ((FECHA_INICIO.month - 1) // 3) * 3 + 1, 1)

    while fecha_trimestre <= FECHA_FIN:
        tasa = cfg.RNG.uniform(*cfg.INFLACION_TRIMESTRAL_RANGO)
        factor_acumulado *= (1 + tasa)
        filas.append({
            "trimestre_inicio": fecha_trimestre.strftime("%Y-%m-%d"),
            "tasa_trimestral": round(tasa, 4),
            "factor_acumulado": round(factor_acumulado, 4),
        })
        # avanzar 3 meses
        mes = fecha_trimestre.month + 3
        anio = fecha_trimestre.year + (mes - 1) // 12
        mes = (mes - 1) % 12 + 1
        fecha_trimestre = datetime(anio, mes, 1)

    return pd.DataFrame(filas)


def factor_inflacion_en(fecha: datetime, tabla_inflacion: pd.DataFrame) -> float:
    """Devuelve el factor acumulado vigente para una fecha dada."""
    trimestres = pd.to_datetime(tabla_inflacion["trimestre_inicio"])
    idx = (trimestres <= fecha).sum() - 1
    idx = max(idx, 0)
    return float(tabla_inflacion.iloc[idx]["factor_acumulado"])


def generar_fechas_pedido(cliente_fecha_alta: datetime, frecuencia_dias: float) -> list:
    """
    Genera fechas de pedido para un cliente desde su alta (o inicio del
    período, lo que sea más tarde) hasta el fin del período, espaciadas por
    la frecuencia base +/- ruido individual, y filtradas por estacionalidad:
    en meses de baja demanda, se salta el pedido con cierta probabilidad.
    """
    inicio = max(cliente_fecha_alta, FECHA_INICIO)
    fechas = []
    fecha_actual = inicio + timedelta(days=int(cfg.RNG.integers(0, int(frecuencia_dias))))

    # Ruido individual: este cliente es un poco más o menos regular que el promedio
    factor_regularidad = cfg.RNG.uniform(0.8, 1.25)

    while fecha_actual <= FECHA_FIN:
        mult_estacional = cfg.ESTACIONALIDAD_MENSUAL[fecha_actual.month]
        # En temporada alta el cliente tiende a pedir un poco más seguido
        # (probabilidad de "saltear" este ciclo baja); en temporada baja, sube.
        prob_saltear = max(0.0, 1 - mult_estacional / 1.4) * 0.5
        if cfg.RNG.random() > prob_saltear:
            fechas.append(fecha_actual)

        siguiente_frecuencia = frecuencia_dias * factor_regularidad / mult_estacional
        siguiente_frecuencia *= cfg.RNG.uniform(0.85, 1.15)  # ruido adicional
        fecha_actual = fecha_actual + timedelta(days=max(2, int(siguiente_frecuencia)))

    return fechas


def generar_pedidos_y_detalle(clientes: pd.DataFrame, productos: pd.DataFrame,
                               tabla_inflacion: pd.DataFrame):
    pedidos = []
    detalle = []
    pedido_id = 1

    # Productos "de temporada": suben más en verano (bebidas frías)
    categorias_verano = {"gaseosa", "cerveza", "agua", "isotonica"}

    # --- Pre-extracción a arrays de NumPy ---------------------------------
    # Iterar sobre un DataFrame de pandas fila por fila (o llamar
    # DataFrame.sample() miles de veces) es muy lento en Python puro.
    # Con ~200k+ pedidos en este dataset, conviene trabajar con arrays
    # de NumPy en el loop caliente y recién armar el DataFrame al final.
    prod_ids = productos["producto_id"].to_numpy()
    prod_precio_base = productos["precio_base"].to_numpy()
    prod_categoria = productos["categoria"].to_numpy()
    n_productos_total = len(productos)
    indices_productos = np.arange(n_productos_total)

    factor_volumen_por_tipo = {"kiosco": 1.0, "autoservicio": 1.3, "bar_restaurante": 1.6,
                                "supermercado": 3.0, "mayorista": 4.5}

    # tabla de inflación como arrays para el lookup rápido (mismo criterio
    # que factor_inflacion_en, pero evitando reconstruir Series cada vez)
    trimestres_np = pd.to_datetime(tabla_inflacion["trimestre_inicio"]).to_numpy()
    factores_np = tabla_inflacion["factor_acumulado"].to_numpy()

    def factor_inflacion_rapido(fecha_np):
        idx = np.searchsorted(trimestres_np, fecha_np, side="right") - 1
        idx = max(idx, 0)
        return factores_np[idx]

    for _, cliente in clientes.iterrows():
        fecha_alta = datetime.strptime(cliente["fecha_alta"], "%Y-%m-%d")
        frecuencia = cfg.FRECUENCIA_PEDIDO_DIAS[cliente["tipo_cliente"]]
        fechas_pedido = generar_fechas_pedido(fecha_alta, frecuencia)
        factor_volumen = factor_volumen_por_tipo[cliente["tipo_cliente"]]
        cliente_id = int(cliente["cliente_id"])

        for fecha_pedido in fechas_pedido:
            dias_entrega = int(cfg.RNG.integers(*cfg.DIAS_ENTRE_PEDIDO_Y_ENTREGA))
            fecha_entrega_estimada = fecha_pedido + timedelta(days=dias_entrega)

            r = cfg.RNG.random()
            if fecha_entrega_estimada > FECHA_FIN:
                estado = "pendiente"
            elif r < 0.03:
                estado = "cancelado"
            else:
                estado = "entregado"

            pedidos.append((pedido_id, cliente_id, fecha_pedido.strftime("%Y-%m-%d"),
                             fecha_entrega_estimada.strftime("%Y-%m-%d"), estado))

            # --- Detalle del pedido ---
            n_lineas = int(cfg.RNG.integers(2, 7))
            idx_sel = cfg.RNG.choice(indices_productos, size=min(n_lineas, n_productos_total),
                                      replace=False)

            factor_inflacion = factor_inflacion_rapido(np.datetime64(fecha_pedido.date()))
            mult_estacional_mes = cfg.ESTACIONALIDAD_MENSUAL[fecha_pedido.month]

            for idx in idx_sel:
                cantidad_base = cfg.RNG.integers(3, 15)
                boost_verano = max(1.0, mult_estacional_mes) if prod_categoria[idx] in categorias_verano else 1.0
                cantidad = max(1, round(cantidad_base * factor_volumen * boost_verano))

                precio_unitario = round(prod_precio_base[idx] * factor_inflacion *
                                         cfg.RNG.uniform(0.97, 1.03), -1)

                detalle.append((pedido_id, int(prod_ids[idx]), int(cantidad), precio_unitario))

            pedido_id += 1

    columnas_pedidos = ["pedido_id", "cliente_id", "fecha_pedido", "fecha_entrega_estimada", "estado"]
    columnas_detalle = ["pedido_id", "producto_id", "cantidad", "precio_unitario"]
    return (pd.DataFrame(pedidos, columns=columnas_pedidos),
            pd.DataFrame(detalle, columns=columnas_detalle))


def main():
    clientes = pd.read_csv(f"{cfg.OUTPUT_DIR}/clientes.csv")
    productos = pd.read_csv(f"{cfg.OUTPUT_DIR}/productos.csv")

    tabla_inflacion = construir_tabla_inflacion()
    pedidos, detalle = generar_pedidos_y_detalle(clientes, productos, tabla_inflacion)

    tabla_inflacion.to_csv(f"{cfg.OUTPUT_DIR}/inflacion_trimestral.csv", index=False)
    pedidos.to_csv(f"{cfg.OUTPUT_DIR}/pedidos.csv", index=False)
    detalle.to_csv(f"{cfg.OUTPUT_DIR}/detalle_pedido.csv", index=False)

    print(f"Pedidos: {len(pedidos)}")
    print(f"Detalle_Pedido: {len(detalle)}")
    print(pedidos["estado"].value_counts())
    print("\nInflación acumulada final:", tabla_inflacion["factor_acumulado"].iloc[-1])
    print("\nPedidos por mes (para chequear estacionalidad):")
    pedidos_tmp = pedidos.copy()
    pedidos_tmp["mes"] = pd.to_datetime(pedidos_tmp["fecha_pedido"]).dt.month
    print(pedidos_tmp.groupby("mes").size())


if __name__ == "__main__":
    main()
