# H4 — Reglas preregistradas del paper trading (fijadas el 20-nov-2026, antes de ver datos nuevos)

**Hipótesis H4.** Comprar el lado favorito cuando cotiza entre 50 y 85 céntimos, unas 24 h antes del
cierre previsto del mercado, tiene rendimiento positivo después de pagar el precio real del libro.

**De dónde sale.** Backtest de la ejecución 44624425236 (unos 22.800 mercados, de ene-2024 a nov-2026):
+5,2% por apuesta en el tramo de 50–70 céntimos y +6,8% en el de 70–85, con 1 céntimo de coste supuesto.
Se probaron muchos grupos a la vez, así que **puede ser un falso positivo**. Por eso se valida aquí, solo con
mercados futuros.

## Reglas (no se cambian durante la prueba)
1. **Universo:** mercados binarios abiertos de Polymarket cuya fecha de fin prevista esté entre **21 y 24 h**
   después del momento del escaneo. Cada 3 h hay un escaneo, así que cada mercado se evalúa una sola vez.
2. **Señal:** se mira el lado con mayor precio. Se "compra" si su **mejor precio de venta (ask) real del libro**
   está entre **0,50 y 0,85**.
3. **Liquidez mínima:** a ese ask tiene que haber al menos **20 $** disponibles. Si no, no se entra (y se anota
   el motivo).
4. **Tamaño:** 10 $ ficticios por operación, al precio ask. Sin comisiones adicionales: Polymarket no cobra en la
   mayoría de mercados, y donde cobra el ask ya es el coste real de un tomador.
5. **Correlación:** como máximo **1 operación por evento** (la del mercado con más volumen).
6. **Límite:** como máximo 60 operaciones por escaneo, eligiendo por volumen.
7. **Salida:** se mantiene hasta la resolución. Gana 10/precio $ si acierta y pierde 10 $ si falla. Los mercados
   anulados o 50-50 se cuentan aparte y no entran en el resultado.

## Criterio de evaluación (decidido antes de empezar)
- **No se mira el veredicto antes de 200 operaciones resueltas y 30 días.**
- **Éxito:** rendimiento medio por $ > 0 **y** límite inferior del IC 95% (bootstrap por evento) > 0.
- **Fracaso:** IC 95% entero por debajo de 0, o rendimiento medio ≤ 0 tras 400 operaciones.
- Entre medias: no concluyente, se sigue recogiendo.
- Además se compara con lo esperado por el backtest (+5% a +7%). Si sale claramente por debajo, la ventaja
  del backtest era en buena parte coste mal estimado.

## Lo que esta prueba NO es
Dinero ficticio. No hay cuenta, ni wallet, ni órdenes reales: solo se leen datos públicos.

---

## Enmienda 1 — 20-nov-2026, 20:05 hora de Madrid (antes de que se resolviera ninguna operación)
Motivo: aumentar el número de apuestas para reducir el margen de error, y añadir carteras de comparación.
Se escribe antes de conocer ningún resultado del paper trading.

1. **H4-24h:** el límite por escaneo sube de 60 a **250** (en el primer escaneo se llenó el tope). Todo lo demás igual.
2. **Nuevas carteras**, mismas reglas de precio real, liquidez mínima de 20 $, 10 $ por apuesta y una
   operación por evento en cada cartera:
   - **H4-4h:** igual que H4-24h, pero en mercados que cierran en **2–5 h**. Se evalúa con el mismo
     criterio que H4-24h, por separado.
   - **H2-control:** el lado **más barato** si su ask está entre **0,01 y 0,15**, a 21–24 h del cierre. Es un
     control negativo: el backtest predice pérdidas. No se evalúa como estrategia.
   - **Azar:** un lado elegido al azar (fijo por mercado) si su ask está entre 0,02 y 0,98, a 21–24 h. Es la
     línea base. La H4 solo aporta algo si supera claramente al azar.
3. **Tamaño de muestra:** con una ventaja real de +6% hacen falta unas 600 apuestas resueltas para que el
   IC 95% excluya el 0, y unas 1.100 para detectarla con un 80% de probabilidad. El veredicto mínimo
   (200 resueltas y 30 días) se mantiene, pero se espera "no concluyente" hasta acercarse a esas cifras.

---

## Enmienda 2 — 21-nov-2026, 12:40 hora de Madrid (antes de ninguna operación de las carteras nuevas)
Motivo: el estudio de rachas (`resultados/regimenes.md`) encontró categorías que pierden con la H4 en las
**dos** muestras históricas independientes (Tennis, Esports, Crypto, Up or Down). Un filtro de categorías
diseñado en una muestra mejoró el resultado en la otra, en las dos direcciones. Se prueba hacia el futuro.

**Nuevas carteras** (idénticas a la H4 en todo lo demás: ask real 0,50–0,85, liquidez de 20 $, 10 $ por
apuesta, una por evento, hasta 250 por escaneo):
- **H5-24h:** como H4-24h, pero sin mercados cuya categoría sea **Tennis, Esports, Crypto o Up or Down**.
- **H5-4h:** como H4-4h, con la misma exclusión.

**Categoría** = la `category` del mercado o, si no tiene, la del evento o, si tampoco, la **primera
etiqueta** del evento en la API de Polymarket. Es la misma definición que en el histórico.

**Evaluación:** el mismo criterio que la H4 (200 resueltas y 30 días como mínimo; éxito si el IC 95% queda
por encima de 0). Además, H5 tiene que superar a la H4 del mismo horizonte. El histórico esperaba entre
+3% y +7% por dólar. Como el filtro se eligió mirando datos de 2024–2026, solo el resultado hacia adelante
lo valida.

### Enmienda 2b — 21-nov-2026, 13:00 hora de Madrid (corrección antes de ninguna resolución de H5)
En el primer escaneo, la API devolvió "Sports" como primera etiqueta de los eventos de tenis (y de otros
deportes). Así, el filtro "por primera etiqueta" no excluía Tennis/Esports, y las 266 apuestas H5 salieron
todas como "Sports". Esas 266 apuestas se **anulan y se borran**: ninguna se había resuelto todavía.
Desde ahora un mercado queda **fuera de H5 si su categoría o CUALQUIERA de las etiquetas de su evento** es
Tennis, Esports, Crypto o Up or Down. Esto es algo más estricto que en el histórico (donde contaba la primera
etiqueta), pero es lo que el estudio pretendía excluir. Las etiquetas de cada apuesta quedan guardadas
en la columna `etiquetas`.
