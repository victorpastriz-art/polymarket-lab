# Polymarket Lab — estudio científico (solo lectura, sin dinero)

Proyecto de investigación sobre la calibración de los mercados de predicción.
Solo **lee datos públicos** (Gamma API y CLOB de Polymarket). No usa cuenta, claves ni wallet, y no opera.

## Hipótesis H2
> "Comprar el resultado barato (1–15 céntimos) en mercados poco seguidos tiene valor esperado positivo"
> (afirmación de @CDanielleD1997 sobre el wallet 0x6e1d…d0f).

La literatura (sesgo favorito-longshot) predice lo contrario. El análisis mide, con costes, el
rendimiento medio por euro de comprar a 1–15 céntimos según el volumen del mercado, la categoría y el
horizonte (168 h, 24 h, 6 h y 1 h antes del cierre).

## Cómo ejecutarlo

### Opción A: tu PC con Windows (necesita internet mientras corre)
```
cd polymarket-lab
py -m pip install -r requirements.txt
py descargar_mercados.py --desde 2024-01
py descargar_precios.py --muestra 20000
py analisis_h2.py
```
Los tres pasos se pueden cortar y relanzar: siguen donde lo dejaron.

### Opción B: GitHub Actions (en la nube, gratis, no depende de tu wifi)
1. Crea un repositorio **privado** en GitHub y sube esta carpeta (incluida `.github/`).
2. Pestaña **Actions** → "Descarga y análisis H2" → **Run workflow**.
3. Al terminar, descarga el artefacto `polymarket-lab-resultados` (CSV y gráfico).

## Archivos
| Archivo | Qué hace |
|---|---|
| `descargar_mercados.py` | Eventos cerrados mes a mes → `data/mercados.csv` (una fila por mercado binario, con el ganador) |
| `descargar_precios.py` | Precio a 168/24/6/1 h del cierre → `data/snapshots.csv` |
| `analisis_h2.py` | Calibración y H2 → `resultados/*.csv` + `h2_grafico.png` |
| `wallets_estudio.csv` | Wallets promocionados y la hipótesis de cada uno |
| `wallets_dexter.csv` | Las 39 menciones de wallets de @DextersSolab (para el estudio de eventos) |

## Cómo leer los resultados
- `calibracion.csv`: si `tasa_acierto` < `precio_medio` en los tramos baratos, los longshots están sobrevalorados.
- `h2_por_volumen.csv` / `h2_por_categoria.csv`: la H2 **solo sobrevive** en un grupo si `rend_ic_bajo > 0`
  con `n_eventos ≥ 30`. Como probamos muchos grupos a la vez, un grupo que pase hay que confirmarlo con
  datos posteriores (fuera de muestra) antes de creérselo.
- Los intervalos de rendimiento se calculan remuestreando **eventos**, no mercados, porque los tramos de un
  mismo evento están correlacionados.

## Limitaciones conocidas
- Coste de compra = precio + 1 céntimo (`--slip`). En contratos de 1–2 céntimos el spread real puede ser
  mayor: repetir con `--slip 0.02`.
- El volumen usado para agrupar es el total final del mercado (en el momento de comprar se conocía menos).
- `prices-history` da el precio de referencia, no la profundidad del libro: no sabemos cuánto se podía
  comprar a ese precio.
- Los nombres de campos de la API pueden cambiar; si un paso da 0 filas, revisar los mensajes HTTP.
- Pruebas hechas con un servidor simulado con el mismo formato que la API; la primera ejecución real es la
  verificación definitiva.
