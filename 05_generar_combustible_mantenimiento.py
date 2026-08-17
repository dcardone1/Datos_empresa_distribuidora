"""
05_generar_combustible_mantenimiento.py
=========================================
Genera Combustible, Mantenimiento, Detalle_Mantenimiento e
Historial_Estado_Vehiculo. También recalcula Vehiculos.estado_actual
al final, en base al último evento de historial de cada vehículo.

Lógica principal:
- Se reconstruye, por vehículo, la "traza" de kilometraje en el tiempo
  (checkpoints fecha->km, a partir de Viajes + el km inicial del período).
- COMBUSTIBLE: se recorre la traza acumulando km desde la última carga;
  cuando se alcanza una fracción del tanque, se genera una carga.
- MANTENIMIENTO PREVENTIVO: se calculan los múltiplos de cada umbral de km
  (aceite cada 10.000km, etc.) que la traza cruza, y se interpola la fecha
  exacta de cruce -> ahí se genera el evento.
- MANTENIMIENTO CORRECTIVO: proceso de Poisson por vehículo, con una tasa
  anual que aumenta con la antigüedad del vehículo (más viejo -> más fallas).
- HISTORIAL_ESTADO_VEHICULO: cada evento de mantenimiento deja al vehículo
  "en_taller" un rango de días; además se agregan eventos de baja SIN
  mantenimiento asociado (ruido operativo real), con motivos en texto libre
  que a veces se cargan de forma inconsistente (ruido de calidad de datos).

Salida: data/combustible.csv, mantenimiento.csv, detalle_mantenimiento.csv,
        historial_estado_vehiculo.csv
        (reescribe también data/vehiculos.csv con estado_actual final)
"""

import pandas as pd
from datetime import datetime, timedelta

import config as cfg

FECHA_INICIO = datetime.strptime(cfg.FECHA_INICIO, "%Y-%m-%d")
FECHA_FIN = datetime.strptime(cfg.FECHA_FIN, "%Y-%m-%d")


# ---------------------------------------------------------------------------
# Utilidades de traza de kilometraje
# ---------------------------------------------------------------------------

def construir_trazas_km(vehiculos: pd.DataFrame, viajes: pd.DataFrame) -> dict:
    """
    Para cada vehículo arma una lista ordenada de checkpoints (fecha, km):
    empieza en (fecha_alta o inicio de período, km_inicial_periodo) y sigue
    con el km_final de cada uno de sus viajes, en orden cronológico.
    """
    trazas = {}
    viajes = viajes.copy()
    viajes["fecha_dt"] = pd.to_datetime(viajes["fecha"])

    for _, veh in vehiculos.iterrows():
        vid = veh["vehiculo_id"]
        fecha_inicio_traza = max(pd.to_datetime(veh["fecha_alta"]), FECHA_INICIO)
        checkpoints = [(fecha_inicio_traza, float(veh["km_inicial_periodo"]))]

        viajes_veh = viajes[viajes["vehiculo_id"] == vid].sort_values("fecha_dt")
        for _, v in viajes_veh.iterrows():
            checkpoints.append((v["fecha_dt"], float(v["km_final"])))

        trazas[vid] = checkpoints

    return trazas


def interpolar_fecha_para_km(checkpoints: list, km_objetivo: float):
    """Dada una traza [(fecha, km), ...] ordenada, interpola la fecha en la
    que el km acumulado cruza km_objetivo. Si el objetivo está fuera de
    rango, devuelve None."""
    if km_objetivo < checkpoints[0][1] or km_objetivo > checkpoints[-1][1]:
        return None
    for (f1, k1), (f2, k2) in zip(checkpoints[:-1], checkpoints[1:]):
        if k1 <= km_objetivo <= k2:
            if k2 == k1:
                return f1
            frac = (km_objetivo - k1) / (k2 - k1)
            dias = (f2 - f1).days * frac
            return f1 + timedelta(days=dias)
    return None


def km_en_fecha(checkpoints: list, fecha) -> float:
    """Interpola el km acumulado en una fecha dada (para eventos correctivos)."""
    if fecha <= checkpoints[0][0]:
        return checkpoints[0][1]
    if fecha >= checkpoints[-1][0]:
        return checkpoints[-1][1]
    for (f1, k1), (f2, k2) in zip(checkpoints[:-1], checkpoints[1:]):
        if f1 <= fecha <= f2:
            if f2 == f1:
                return k1
            frac = (fecha - f1).days / (f2 - f1).days
            return k1 + (k2 - k1) * frac
    return checkpoints[-1][1]


# ---------------------------------------------------------------------------
# Combustible
# ---------------------------------------------------------------------------

def construir_tabla_inflacion_combustible() -> pd.DataFrame:
    filas = []
    factor = 1.0
    fecha_trimestre = datetime(FECHA_INICIO.year, ((FECHA_INICIO.month - 1) // 3) * 3 + 1, 1)
    while fecha_trimestre <= FECHA_FIN:
        tasa = cfg.RNG.uniform(*cfg.INFLACION_COMBUSTIBLE_TRIMESTRAL)
        factor *= (1 + tasa)
        filas.append({"trimestre_inicio": fecha_trimestre, "factor_acumulado": factor})
        mes = fecha_trimestre.month + 3
        anio = fecha_trimestre.year + (mes - 1) // 12
        mes = (mes - 1) % 12 + 1
        fecha_trimestre = datetime(anio, mes, 1)
    return pd.DataFrame(filas)


def precio_diesel_en(fecha, tabla_inflacion_comb: pd.DataFrame) -> float:
    idx = (tabla_inflacion_comb["trimestre_inicio"] <= fecha).sum() - 1
    idx = max(idx, 0)
    factor = tabla_inflacion_comb.iloc[idx]["factor_acumulado"]
    return cfg.PRECIO_DIESEL_INICIAL * factor


def generar_combustible(vehiculos: pd.DataFrame, modelos: pd.DataFrame,
                         trazas: dict, tabla_inflacion_comb: pd.DataFrame) -> pd.DataFrame:
    modelos_idx = modelos.set_index("modelo_id")
    filas = []
    carga_id = 1

    for _, veh in vehiculos.iterrows():
        vid = veh["vehiculo_id"]
        modelo = modelos_idx.loc[veh["modelo_id"]]
        consumo_teorico = modelo["consumo_teorico_l_100km"]
        capacidad_tanque = modelo["capacidad_tanque_l"]

        checkpoints = trazas[vid]
        km_desde_ultima_carga = 0.0
        fraccion_objetivo = cfg.RNG.uniform(*cfg.FRACCION_TANQUE_ENTRE_CARGAS)
        litros_objetivo = capacidad_tanque * fraccion_objetivo

        for (f1, k1), (f2, k2) in zip(checkpoints[:-1], checkpoints[1:]):
            tramo_km = k2 - k1
            if tramo_km <= 0:
                continue
            km_desde_ultima_carga += tramo_km
            litros_estimados = km_desde_ultima_carga * consumo_teorico / 100 * cfg.RNG.uniform(0.92, 1.12)

            if litros_estimados >= litros_objetivo:
                # se carga combustible en f2 (fecha del checkpoint que gatilla la carga)
                litros = round(litros_estimados, 1)
                es_outlier = cfg.RNG.random() < cfg.PROB_OUTLIER_COMBUSTIBLE
                if es_outlier:
                    litros = round(litros * cfg.RNG.choice([0.3, 2.2, 2.6]), 1)

                precio_litro = round(precio_diesel_en(f2, tabla_inflacion_comb) *
                                      cfg.RNG.uniform(0.96, 1.04), 1)

                filas.append({
                    "carga_id": carga_id,
                    "vehiculo_id": int(vid),
                    "fecha": f2.strftime("%Y-%m-%d"),
                    "litros": litros,
                    "precio_litro": precio_litro,
                    "km_odometro": round(k2, 1),
                })
                carga_id += 1

                km_desde_ultima_carga = 0.0
                fraccion_objetivo = cfg.RNG.uniform(*cfg.FRACCION_TANQUE_ENTRE_CARGAS)
                litros_objetivo = capacidad_tanque * fraccion_objetivo

    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Mantenimiento preventivo
# ---------------------------------------------------------------------------

def generar_mantenimiento_preventivo(vehiculos: pd.DataFrame, trazas: dict,
                                      tabla_inflacion_gral: pd.DataFrame) -> list:
    """Devuelve una lista de dicts de eventos de mantenimiento preventivo."""
    eventos = []

    for _, veh in vehiculos.iterrows():
        vid = veh["vehiculo_id"]
        checkpoints = trazas[vid]
        km_inicial_periodo = checkpoints[0][1]
        km_final_periodo = checkpoints[-1][1]

        for tipo, umbral in cfg.UMBRALES_PREVENTIVO_KM.items():
            # primer múltiplo del umbral que cae DESPUÉS del km inicial del período
            primer_multiplo = (int(km_inicial_periodo // umbral) + 1) * umbral
            km_objetivo = primer_multiplo
            while km_objetivo <= km_final_periodo:
                fecha_evento = interpolar_fecha_para_km(checkpoints, km_objetivo)
                if fecha_evento is not None:
                    eventos.append({
                        "vehiculo_id": int(vid),
                        "fecha": fecha_evento,
                        "tipo": "preventivo",
                        "subtipo": tipo,
                        "km_odometro": round(km_objetivo, 1),
                    })
                km_objetivo += umbral

    return eventos


# ---------------------------------------------------------------------------
# Mantenimiento correctivo
# ---------------------------------------------------------------------------

def generar_mantenimiento_correctivo(vehiculos: pd.DataFrame, trazas: dict) -> list:
    """Proceso de Poisson por vehículo: más eventos cuanto más viejo y más
    usado (más km) es el vehículo."""
    eventos = []

    for _, veh in vehiculos.iterrows():
        vid = veh["vehiculo_id"]
        checkpoints = trazas[vid]
        fecha_inicio_v = checkpoints[0][0]
        fecha_fin_v = min(pd.to_datetime(veh["fecha_baja"]) if pd.notna(veh["fecha_baja"]) else FECHA_FIN,
                           FECHA_FIN)
        anios_activo = max((fecha_fin_v - fecha_inicio_v).days / 365, 0)
        if anios_activo <= 0:
            continue

        edad_al_inicio_periodo = max((FECHA_INICIO - pd.to_datetime(veh["fecha_alta"])).days / 365, 0)
        factor_edad = 1 + edad_al_inicio_periodo * 0.13
        tasa_anual = cfg.TASA_BASE_CORRECTIVO_ANUAL * factor_edad

        n_eventos = cfg.RNG.poisson(tasa_anual * anios_activo)
        for _ in range(int(n_eventos)):
            dias_offset = int(cfg.RNG.integers(0, max((fecha_fin_v - fecha_inicio_v).days, 1)))
            fecha_evento = fecha_inicio_v + timedelta(days=dias_offset)
            km_evento = km_en_fecha(checkpoints, fecha_evento)
            eventos.append({
                "vehiculo_id": int(vid),
                "fecha": fecha_evento,
                "tipo": "correctivo",
                "subtipo": None,
                "km_odometro": round(km_evento, 1),
            })

    return eventos


# ---------------------------------------------------------------------------
# Ensamblado de Mantenimiento + Detalle_Mantenimiento
# ---------------------------------------------------------------------------

def ensamblar_mantenimiento(eventos: list, insumos: pd.DataFrame,
                             tabla_inflacion_gral: pd.DataFrame):
    insumos_idx = insumos.set_index("nombre")
    mantenimiento = []
    detalle = []
    mantenimiento_id = 1
    detalle_id = 1

    eventos_ordenados = sorted(eventos, key=lambda e: (e["vehiculo_id"], e["fecha"]))

    for ev in eventos_ordenados:
        if ev["tipo"] == "preventivo":
            nombres_insumo = cfg.INSUMOS_POR_TIPO_PREVENTIVO[ev["subtipo"]]
            costo_mo = round(cfg.RNG.uniform(*cfg.COSTO_MANO_OBRA_PREVENTIVO[ev["subtipo"]]))
        else:
            k = int(cfg.RNG.integers(1, 3))
            nombres_insumo = list(cfg.RNG.choice(cfg.INSUMOS_CORRECTIVO_POSIBLES, size=k, replace=False))
            costo_mo = round(cfg.RNG.uniform(*cfg.COSTO_MANO_OBRA_CORRECTIVO))

        factor_inf = factor_inflacion_en_fecha(ev["fecha"], tabla_inflacion_gral)

        mantenimiento.append({
            "mantenimiento_id": mantenimiento_id,
            "vehiculo_id": ev["vehiculo_id"],
            "fecha": ev["fecha"].strftime("%Y-%m-%d"),
            "tipo": ev["tipo"],
            # subtipo es informativo (no estaba en el modelo original a nivel
            # tabla, pero es útil para describir el service y para armar el
            # motivo del historial de estado; para EDA de "tipo" alcanza con
            # preventivo/correctivo, subtipo da detalle adicional opcional).
            "subtipo": ev["subtipo"],
            "km_odometro": ev["km_odometro"],
            "taller": str(cfg.RNG.choice(cfg.TALLERES)),
            "costo_mano_obra": round(costo_mo * factor_inf),
        })

        for nombre_insumo in nombres_insumo:
            insumo = insumos_idx.loc[nombre_insumo]
            cantidad = _cantidad_para_insumo(nombre_insumo, ev["subtipo"])
            costo_unit = insumo["costo_unitario_referencia"] * factor_inf * cfg.RNG.uniform(0.95, 1.08)
            detalle.append({
                "mantenimiento_id": mantenimiento_id,
                "insumo_id": int(insumo["insumo_id"]),
                "cantidad": cantidad,
                "costo_total": round(cantidad * costo_unit),
            })
            detalle_id += 1

        mantenimiento_id += 1

    return pd.DataFrame(mantenimiento), pd.DataFrame(detalle)


def _cantidad_para_insumo(nombre_insumo: str, subtipo) -> float:
    if "Aceite de motor" in nombre_insumo:
        return float(cfg.RNG.integers(8, 15))  # litros
    if "Cubierta" in nombre_insumo:
        return float(cfg.RNG.choice([2, 4, 6]))  # se cambian de a pares/eje
    if "Líquido refrigerante" in nombre_insumo:
        return float(cfg.RNG.integers(3, 8))
    return 1.0  # filtros, juegos de pastillas, kits, baterías, etc: 1 unidad


def factor_inflacion_en_fecha(fecha, tabla_inflacion_gral: pd.DataFrame) -> float:
    trimestres = pd.to_datetime(tabla_inflacion_gral["trimestre_inicio"])
    idx = (trimestres <= fecha).sum() - 1
    idx = max(idx, 0)
    return float(tabla_inflacion_gral.iloc[idx]["factor_acumulado"])


# ---------------------------------------------------------------------------
# Historial de estado del vehículo
# ---------------------------------------------------------------------------

def perturbar_texto(texto: str) -> str:
    """Simula inconsistencias de carga manual: mayúsculas, abreviaturas,
    espacios de más, etc. Ruido de calidad de datos deliberado."""
    opcion = cfg.RNG.integers(0, 4)
    if opcion == 0:
        return texto.upper()
    if opcion == 1:
        return texto.replace("Reparación", "Reparac.").replace("Service", "Serv.")
    if opcion == 2:
        return f"  {texto.lower()}  "
    return texto[:1].lower() + texto[1:]


def generar_historial_estado(mantenimiento: pd.DataFrame, vehiculos: pd.DataFrame) -> pd.DataFrame:
    filas = []
    historial_id = 1

    mant_por_vehiculo = mantenimiento.copy()
    mant_por_vehiculo["fecha_dt"] = pd.to_datetime(mant_por_vehiculo["fecha"])

    for _, mant in mant_por_vehiculo.iterrows():
        dur_rango = cfg.DURACION_FUERA_SERVICIO_DIAS[mant["tipo"]]
        duracion = int(cfg.RNG.integers(dur_rango[0], dur_rango[1] + 1))
        fecha_desde = mant["fecha_dt"]
        fecha_hasta = fecha_desde + timedelta(days=duracion)

        if mant["tipo"] == "preventivo":
            subtipo_legible = cfg.NOMBRES_LEGIBLES_TIPO.get(mant.get("subtipo"), "Service programado")
            motivo = f"Service programado - {subtipo_legible}"
        else:
            motivo = "Reparación correctiva en taller"

        if cfg.RNG.random() < cfg.PROB_MOTIVO_INCONSISTENTE:
            motivo = perturbar_texto(motivo)

        filas.append({
            "historial_id": historial_id,
            "vehiculo_id": int(mant["vehiculo_id"]),
            "fecha_desde": fecha_desde.strftime("%Y-%m-%d"),
            "fecha_hasta": fecha_hasta.strftime("%Y-%m-%d") if fecha_hasta < FECHA_FIN else None,
            "estado": "en_taller",
            "motivo": motivo,
        })
        historial_id += 1

    # eventos de baja SIN mantenimiento asociado (ruido operativo)
    for _, veh in vehiculos.iterrows():
        fecha_inicio_v = max(pd.to_datetime(veh["fecha_alta"]), FECHA_INICIO)
        fecha_fin_v = min(pd.to_datetime(veh["fecha_baja"]) if pd.notna(veh["fecha_baja"]) else FECHA_FIN,
                           FECHA_FIN)
        anios_activo = max((fecha_fin_v - fecha_inicio_v).days / 365, 0)
        n_eventos = cfg.RNG.poisson(cfg.PROB_ESTADO_ALEATORIO_EXTRA * anios_activo * 4)

        for _ in range(int(n_eventos)):
            dias_offset = int(cfg.RNG.integers(0, max((fecha_fin_v - fecha_inicio_v).days, 1)))
            fecha_desde = fecha_inicio_v + timedelta(days=dias_offset)
            dur_rango = cfg.DURACION_FUERA_SERVICIO_DIAS["otro"]
            duracion = int(cfg.RNG.integers(dur_rango[0], dur_rango[1] + 1))
            fecha_hasta = fecha_desde + timedelta(days=duracion)

            motivo = str(cfg.RNG.choice(cfg.MOTIVOS_ESTADO_EXTRA))
            if cfg.RNG.random() < cfg.PROB_MOTIVO_INCONSISTENTE:
                motivo = perturbar_texto(motivo)

            filas.append({
                "historial_id": historial_id,
                "vehiculo_id": int(veh["vehiculo_id"]),
                "fecha_desde": fecha_desde.strftime("%Y-%m-%d"),
                "fecha_hasta": fecha_hasta.strftime("%Y-%m-%d") if fecha_hasta < FECHA_FIN else None,
                "estado": "fuera_de_servicio",
                "motivo": motivo,
            })
            historial_id += 1

    df = pd.DataFrame(filas)
    return df.sort_values(["vehiculo_id", "fecha_desde"]).reset_index(drop=True)


def recalcular_estado_actual(vehiculos: pd.DataFrame, historial: pd.DataFrame) -> pd.DataFrame:
    """estado_actual = estado del último evento vigente (fecha_hasta nula o
    posterior al fin del período); si no tiene eventos vigentes, operativo."""
    vehiculos = vehiculos.copy()
    hist = historial.copy()
    hist["fecha_desde_dt"] = pd.to_datetime(hist["fecha_desde"])

    estado_final = {}
    for vid, sub in hist.groupby("vehiculo_id"):
        vigentes = sub[sub["fecha_hasta"].isna()]
        if len(vigentes) > 0:
            ultimo = vigentes.sort_values("fecha_desde_dt").iloc[-1]
            estado_final[vid] = ultimo["estado"]

    vehiculos["estado_actual"] = vehiculos["vehiculo_id"].map(
        lambda v: estado_final.get(v, "operativo"))
    return vehiculos


def main():
    vehiculos = pd.read_csv(f"{cfg.OUTPUT_DIR}/vehiculos.csv")
    modelos = pd.read_csv(f"{cfg.OUTPUT_DIR}/modelos_vehiculo.csv")
    viajes = pd.read_csv(f"{cfg.OUTPUT_DIR}/viajes.csv")
    insumos = pd.read_csv(f"{cfg.OUTPUT_DIR}/insumos.csv")
    tabla_inflacion_gral = pd.read_csv(f"{cfg.OUTPUT_DIR}/inflacion_trimestral.csv")
    tabla_inflacion_gral["trimestre_inicio"] = pd.to_datetime(tabla_inflacion_gral["trimestre_inicio"])

    trazas = construir_trazas_km(vehiculos, viajes)

    # --- Combustible ---
    tabla_inflacion_comb = construir_tabla_inflacion_combustible()
    combustible = generar_combustible(vehiculos, modelos, trazas, tabla_inflacion_comb)

    # --- Mantenimiento (preventivo + correctivo) ---
    eventos_preventivo = generar_mantenimiento_preventivo(vehiculos, trazas, tabla_inflacion_gral)
    eventos_correctivo = generar_mantenimiento_correctivo(vehiculos, trazas)
    mantenimiento, detalle_mantenimiento = ensamblar_mantenimiento(
        eventos_preventivo + eventos_correctivo, insumos, tabla_inflacion_gral)

    # --- Historial de estado + recálculo de estado_actual ---
    historial = generar_historial_estado(mantenimiento, vehiculos)
    vehiculos = recalcular_estado_actual(vehiculos, historial)

    combustible.to_csv(f"{cfg.OUTPUT_DIR}/combustible.csv", index=False)
    mantenimiento.to_csv(f"{cfg.OUTPUT_DIR}/mantenimiento.csv", index=False)
    detalle_mantenimiento.to_csv(f"{cfg.OUTPUT_DIR}/detalle_mantenimiento.csv", index=False)
    historial.to_csv(f"{cfg.OUTPUT_DIR}/historial_estado_vehiculo.csv", index=False)
    vehiculos.to_csv(f"{cfg.OUTPUT_DIR}/vehiculos.csv", index=False)

    print(f"Combustible: {len(combustible)} cargas")
    print(f"Mantenimiento: {len(mantenimiento)} eventos "
          f"({(mantenimiento['tipo'] == 'preventivo').sum()} preventivos, "
          f"{(mantenimiento['tipo'] == 'correctivo').sum()} correctivos)")
    print(f"Detalle_Mantenimiento: {len(detalle_mantenimiento)} líneas")
    print(f"Historial_Estado_Vehiculo: {len(historial)} eventos")
    print(vehiculos["estado_actual"].value_counts())


if __name__ == "__main__":
    main()
