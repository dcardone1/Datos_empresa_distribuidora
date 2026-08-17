# Dataset sintético — Distribuidora de bebidas con flota propia

Pipeline en Python que genera un dataset relacional realista de una empresa
de distribución de bebidas con flota propia, para practicar análisis de
datos (EDA, estimación de costos, consumo de insumos, mantenimiento
predictivo, etc.).

## Versiones de python y librerías
python                    3.12.11
pandas                    2.3.3
numpy                     2.3.1
faker                     40.36.0 

## Cómo correrlo

```bash
pip install pandas numpy faker
python3 run_all.py
```

Esto corre las 5 etapas en orden y deja los CSV en `data/`. Después podés
correr `python3 06_validar_dataset.py` para chequear integridad referencial
y consistencia general.

También podés correr cada script por separado (`01_...py`, `02_...py`, etc.)
si querés inspeccionar resultados intermedios — de hecho es lo recomendable
la primera vez que lo revises, para entender qué hace cada etapa antes de
tocar `config.py`.

## Estructura del pipeline

| Script | Genera |
|---|---|
| `config.py` | Todos los parámetros ajustables (nada de "números mágicos" en el resto del código) |
| `01_generar_catalogos.py` | Depositos, Modelos_Vehiculo, Zonas, Productos, Insumos |
| `02_generar_flota_clientes.py` | Vehiculos, Choferes, Clientes |
| `03_generar_pedidos.py` | Pedidos, Detalle_Pedido, tabla de inflación trimestral |
| `04_generar_viajes.py` | Viajes, Viaje_Pedido (y recalcula `vehiculos.km_actual`) |
| `05_generar_combustible_mantenimiento.py` | Combustible, Mantenimiento, Detalle_Mantenimiento, Historial_Estado_Vehiculo (y recalcula `vehiculos.estado_actual`) |
| `run_all.py` | Corre las 5 etapas en orden |
| `06_validar_dataset.py` | Valida integridad referencial y consistencia (no genera datos) |

El orden importa: cada script depende de los CSV que dejó el anterior.

## Decisiones de diseño / supuestos (importante para tu análisis)

- **Período**: 2022-01-01 a 2024-12-31 (3 años).
- **Depósitos**: Buenos Aires, Córdoba, Mendoza.
- **Inflación**: los precios de productos (`Detalle_Pedido.precio_unitario`)
  y el precio del gasoil (`Combustible.precio_litro`) NO son fijos: se
  recalculan por trimestre con una tasa aleatoria (5-15% para productos,
  6-16% para combustible). La tabla `data/inflacion_trimestral.csv` queda
  guardada como referencia para que puedas deflactar si lo necesitás.
- **Estacionalidad**: la demanda tiene un pico en verano (dic-feb) y un
  valle en invierno (jun-jul), vía `config.ESTACIONALIDAD_MENSUAL`.
- **Antigüedad de flota**: bimodal a propósito (35% "casi nueva" 0-2 años,
  65% "vieja" 8-12 años) — no una distribución pareja, para simular
  renovación de flota por tandas.
- **Km de arrastre**: los vehículos que ya operaban antes de 2022-01-01
  arrancan el período con un odómetro estimado según su antigüedad
  (`vehiculos.km_inicial_periodo`), no en cero. Los vehículos incorporados
  durante el período sí arrancan en 0.
- **Utilización de flota**: el tamaño de flota y el volumen de pedidos
  están calibrados para que casi ningún vehículo quede ocioso en días
  hábiles (activo caro = se usa). En esta corrida da ~215 viajes/año por
  vehículo. Si ajustás `CLIENTES_POR_DEPOSITO`, `FRECUENCIA_PEDIDO_DIAS` o
  `VEHICULOS_POR_DEPOSITO` en `config.py`, este balance se puede romper —
  volvé a correr `06_validar_dataset.py` y mirá viajes/vehículo después de
  cualquier cambio grande.
- **Mantenimiento preventivo**: disparado por umbrales de km (aceite
  10.000km, frenos 30.000km, cubiertas 45.000km, correa de distribución
  80.000km), no por fecha. Se calculan interpolando la traza de km de cada
  vehículo, así que los eventos caen en fechas realistas según cuánto
  circuló.
- **Mantenimiento correctivo**: proceso de Poisson por vehículo, con tasa
  anual creciente según antigüedad (no depende de un chofer en particular
  ni de la zona, para simplificar).
- **Calidad de datos deliberadamente imperfecta** (a propósito, no bugs):
  - ~12% de los vehículos tiene `km_actual` desactualizado (más bajo que
    el real), con su `fecha_ultima_actualizacion_km` vieja.
  - ~15% de los motivos en `Historial_Estado_Vehiculo` tiene variantes de
    formato (mayúsculas, abreviaturas, espacios de más) simulando carga
    manual inconsistente.
  - ~3% de las cargas de combustible son outliers (volumen muy chico o muy
    grande).
  - Hay eventos de `Historial_Estado_Vehiculo` sin `Mantenimiento` asociado
    (ej. "esperando repuesto", "accidente menor") — ruido operativo real.
  - ~5% de los pedidos "entregado" puede quedar sin viaje asociado en
    `Viaje_Pedido` (no se consiguió vehículo/chofer libre ese día) — está
    documentado en el propio código de `04_generar_viajes.py`.
- **Simplificación consciente**: la asignación de vehículo/chofer a un
  viaje NO tiene en cuenta si el vehículo estaba en ese momento
  "en_taller" según `Historial_Estado_Vehiculo` (ese historial se calcula
  recién en el script 5, después de los viajes). Puede haber alguna
  inconsistencia puntual entre ambas tablas — es una limitación conocida,
  no arreglada a propósito porque también es una forma de ruido realista
  (sistemas que no siempre están 100% sincronizados entre sí).

## Diccionario de datos (resumen)

14 tablas + 1 tabla de apoyo (`inflacion_trimestral.csv`, no forma parte
del modelo relacional, es solo referencia):

**Catálogo**: `depositos`, `modelos_vehiculo`, `zonas`, `productos`, `insumos`

**Comercial**: `clientes`, `pedidos`, `detalle_pedido`

**Flota**: `vehiculos`, `choferes`, `historial_estado_vehiculo`

**Operación**: `viajes`, `viaje_pedido`

**Costos/mantenimiento**: `combustible`, `mantenimiento`, `detalle_mantenimiento`

Cada script tiene comentarios en el código explicando campo por campo y la
lógica de cada regla de negocio — la idea es que se lea como una bitácora
de decisiones, no solo como código.

## Ajustar el dataset

Todo lo que probablemente quieras cambiar está en `config.py`: fechas,
cantidad de depósitos/vehículos/clientes, umbrales de mantenimiento,
rangos de inflación, probabilidades de ruido, etc. Después de cualquier
cambio, corré `run_all.py` de nuevo (es reproducible gracias a
`config.SEED`, así que si no cambiás nada da exactamente el mismo dataset).
