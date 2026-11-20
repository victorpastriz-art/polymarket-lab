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
