# Estudio de rachas de la H4: por qué gana o pierde según la época

# H4-24h

## 1. Buena racha (ene-ago 2026) vs mala racha (sep-nov 2026), muestra de confirmación

| periodo      |   apuestas | aciertos   | por_dolar   | ganancia   |
|:-------------|-----------:|:-----------|:------------|:-----------|
| 2024-2025    |        870 | 60.6%      | -2.9%       | -250 $     |
| ene-ago 2026 |       3178 | 62.0%      | +0.5%       | +162 $     |
| sep-nov 2026 |       1933 | 63.7%      | +2.4%       | +472 $     |

Categorías que más pierden en sep-nov 2026 (ganancia en $ de cada periodo):

| cat       | ene-ago 2026   | sep-nov 2026   | cambio   |   ene-ago 2026 (apuestas) |   sep-nov 2026 (apuestas) |
|:----------|:---------------|:---------------|:---------|--------------------------:|--------------------------:|
| Crypto    | +13 $          | -243 $         | -257 $   |                       569 |                       215 |
| Tennis    | -337 $         | -99 $          | +238 $   |                       247 |                       138 |
| NVDA      | -182 $         | -97 $          | +86 $    |                       247 |                        82 |
| Brazil    | +0 $           | -75 $          | -75 $    |                         0 |                        43 |
| AMZN      | +72 $          | -62 $          | -135 $   |                       221 |                        75 |
| NFL (All) | +37 $          | -43 $          | -81 $    |                        13 |                        19 |
| MSFT      | -147 $         | -35 $          | +112 $   |                       224 |                        90 |
| Trump     | -47 $          | -30 $          | +18 $    |                        72 |                        43 |
| Esports   | -140 $         | -24 $          | +116 $   |                       305 |                        85 |
| XRP       | +61 $          | -16 $          | -77 $    |                       105 |                        27 |

Composición: % de apuestas por tramo de precio en cada periodo:

| periodo      |   [0.5, 0.6) |   [0.6, 0.7) |   [0.7, 0.85) |
|:-------------|-------------:|-------------:|--------------:|
| 2024-2025    |         54.9 |         15.2 |          29.9 |
| ene-ago 2026 |         56.8 |         17.4 |          25.8 |
| sep-nov 2026 |         55.3 |         16.8 |          27.9 |

## 2. ¿Se repite en las dos muestras? (por dólar)

Por tramo_precio:

| tramo_precio   |   apuestas_descubrimiento | por_dolar_descubrimiento   |   apuestas_confirmacion | por_dolar_confirmacion   | mismo_signo   |
|:---------------|--------------------------:|:---------------------------|------------------------:|:-------------------------|:--------------|
| [0.5, 0.6)     |                      2678 | +1.5%                      |                    3353 | -0.6%                    | False         |
| [0.6, 0.7)     |                      1005 | +2.8%                      |                    1010 | +5.0%                    | True          |
| [0.7, 0.85)    |                      1570 | +0.7%                      |                    1618 | +0.4%                    | True          |

Por tramo_volumen:

| tramo_volumen   |   apuestas_descubrimiento | por_dolar_descubrimiento   |   apuestas_confirmacion | por_dolar_confirmacion   | mismo_signo   |
|:----------------|--------------------------:|:---------------------------|------------------------:|:-------------------------|:--------------|
| 100k-1M $       |                       275 | -5.9%                      |                     284 | -1.3%                    | True          |
| 10k-100k $      |                      1040 | -1.8%                      |                    1215 | -3.8%                    | True          |
| <10k $          |                      3893 | +3.2%                      |                    4427 | +2.1%                    | True          |

Por cat:

| cat       |   apuestas_descubrimiento | por_dolar_descubrimiento   |   apuestas_confirmacion | por_dolar_confirmacion   | mismo_signo   |
|:----------|--------------------------:|:---------------------------|------------------------:|:-------------------------|:--------------|
| Crypto    |                       634 | -4.8%                      |                     954 | -4.7%                    | True          |
| Culture   |                       182 | +6.1%                      |                     143 | +9.0%                    | True          |
| Esports   |                       258 | -2.6%                      |                     400 | -5.0%                    | True          |
| Finance   |                       336 | +2.6%                      |                     400 | +6.4%                    | True          |
| Formula 1 |                       157 | +16.0%                     |                     191 | +16.9%                   | True          |
| Politics  |                       135 | +9.3%                      |                     136 | -0.4%                    | False         |
| Soccer    |                       123 | +2.0%                      |                     141 | +7.2%                    | True          |
| Solana    |                       117 | +1.9%                      |                     153 | +0.8%                    | True          |
| Sports    |                       394 | +8.0%                      |                     599 | +8.8%                    | True          |
| Tennis    |                       257 | -5.5%                      |                     385 | -11.3%                   | True          |
| Trump     |                       323 | +0.3%                      |                     169 | -3.2%                    | False         |
| Weather   |                       274 | +8.0%                      |                     383 | +8.9%                    | True          |
| XRP       |                       130 | +11.9%                     |                     203 | +0.7%                    | True          |

## 3. Filtros diseñados en una muestra y probados en la otra

| diseñado_en    | probado_en     | filtro                                            |   apuestas | por_dolar   | ic_bajo   | ic_alto   | ganancia   |
|:---------------|:---------------|:--------------------------------------------------|-----------:|:------------|:----------|:----------|:-----------|
| descubrimiento | confirmacion   | Sin filtro                                        |       5981 | +0.6%       | -1.4%     | +2.7%     | +384 $     |
| descubrimiento | confirmacion   | Solo categorías positivas en descubrimiento       |       2591 | +6.3%       | +3.4%     | +9.2%     | +1643 $    |
| descubrimiento | confirmacion   | Solo tramos de precio positivos en descubrimiento |       5981 | +0.6%       | -1.4%     | +2.7%     | +384 $     |
| descubrimiento | confirmacion   | Filtro de momento (60 días, solo pasado)          |       2516 | +3.2%       | +0.1%     | +6.1%     | +798 $     |
| confirmacion   | descubrimiento | Sin filtro                                        |       5253 | +1.5%       | -0.7%     | +3.6%     | +800 $     |
| confirmacion   | descubrimiento | Solo categorías positivas en confirmacion         |       1713 | +6.9%       | +3.3%     | +10.2%    | +1180 $    |
| confirmacion   | descubrimiento | Solo tramos de precio positivos en confirmacion   |       2575 | +1.5%       | -0.6%     | +3.9%     | +399 $     |
| confirmacion   | descubrimiento | Filtro de momento (60 días, solo pasado)          |       1817 | +1.8%       | -1.8%     | +5.8%     | +329 $     |

Lectura: un filtro solo vale si mejora el resultado en la muestra donde NO se diseñó y el intervalo de confianza deja de incluir el 0. El filtro de momento no se diseña con ninguna muestra (solo mira el pasado), así que su resultado vale en las dos.

# H4-4h

## 1. Buena racha (ene-ago 2026) vs mala racha (sep-nov 2026), muestra de confirmación

| periodo      |   apuestas | aciertos   | por_dolar   | ganancia   |
|:-------------|-----------:|:-----------|:------------|:-----------|
| 2024-2025    |        877 | 61.7%      | -0.3%       | -28 $      |
| ene-ago 2026 |       4338 | 61.1%      | +2.7%       | +1193 $    |
| sep-nov 2026 |       2763 | 57.2%      | -3.6%       | -1002 $    |

Categorías que más pierden en sep-nov 2026 (ganancia en $ de cada periodo):

| cat        | ene-ago 2026   | sep-nov 2026   | cambio   |   ene-ago 2026 (apuestas) |   sep-nov 2026 (apuestas) |
|:-----------|:---------------|:---------------|:---------|--------------------------:|--------------------------:|
| Tennis     | +17 $          | -581 $         | -598 $   |                       631 |                       482 |
| Finance    | +336 $         | -355 $         | -691 $   |                       187 |                       349 |
| Esports    | -264 $         | -236 $         | +29 $    |                       530 |                       169 |
| Up or Down | +334 $         | -194 $         | -528 $   |                       738 |                       345 |
| Crypto     | +70 $          | -155 $         | -225 $   |                       588 |                       224 |
| NVDA       | -187 $         | -124 $         | +63 $    |                       229 |                        70 |
| MSFT       | +312 $         | -98 $          | -411 $   |                       212 |                        79 |
| PPA        | -20 $          | -96 $          | -76 $    |                         2 |                        75 |
| Brazil     | +0 $           | -16 $          | -16 $    |                         0 |                        37 |
| AI         | +18 $          | -14 $          | -32 $    |                        14 |                        25 |

Composición: % de apuestas por tramo de precio en cada periodo:

| periodo      |   [0.5, 0.6) |   [0.6, 0.7) |   [0.7, 0.85) |
|:-------------|-------------:|-------------:|--------------:|
| 2024-2025    |         55.3 |         18.4 |          26.3 |
| ene-ago 2026 |         65   |         14.8 |          20.2 |
| sep-nov 2026 |         68.2 |         12.2 |          19.7 |

## 2. ¿Se repite en las dos muestras? (por dólar)

Por tramo_precio:

| tramo_precio   |   apuestas_descubrimiento | por_dolar_descubrimiento   |   apuestas_confirmacion | por_dolar_confirmacion   | mismo_signo   |
|:---------------|--------------------------:|:---------------------------|------------------------:|:-------------------------|:--------------|
| [0.5, 0.6)     |                      4013 | +1.3%                      |                    5187 | +0.3%                    | True          |
| [0.6, 0.7)     |                      1109 | +4.5%                      |                    1139 | +0.3%                    | True          |
| [0.7, 0.85)    |                      1610 | -1.6%                      |                    1652 | -0.0%                    | True          |

Por tramo_volumen:

| tramo_volumen   |   apuestas_descubrimiento | por_dolar_descubrimiento   |   apuestas_confirmacion | por_dolar_confirmacion   | mismo_signo   |
|:----------------|--------------------------:|:---------------------------|------------------------:|:-------------------------|:--------------|
| 100k-1M $       |                       281 | -7.8%                      |                     291 | -5.7%                    | True          |
| 10k-100k $      |                      1085 | -4.7%                      |                    1277 | -3.3%                    | True          |
| <10k $          |                      5326 | +2.8%                      |                    6364 | +1.1%                    | True          |

Por cat:

| cat        |   apuestas_descubrimiento | por_dolar_descubrimiento   |   apuestas_confirmacion | por_dolar_confirmacion   | mismo_signo   |
|:-----------|--------------------------:|:---------------------------|------------------------:|:-------------------------|:--------------|
| Crypto     |                       634 | -5.8%                      |                     979 | -3.1%                    | True          |
| Culture    |                       154 | +3.3%                      |                     112 | +12.7%                   | True          |
| Esports    |                       506 | -8.5%                      |                     724 | -7.1%                    | True          |
| Finance    |                       423 | +7.2%                      |                     539 | -0.2%                    | False         |
| Formula 1  |                       152 | +23.2%                     |                     198 | +27.4%                   | True          |
| NFL (All)  |                       104 | +8.4%                      |                     120 | +2.9%                    | True          |
| Politics   |                       123 | -2.9%                      |                     117 | -4.4%                    | True          |
| Soccer     |                       138 | +7.4%                      |                     150 | +10.0%                   | True          |
| Sports     |                       497 | +5.5%                      |                     721 | -1.8%                    | False         |
| Tennis     |                       754 | -6.2%                      |                    1114 | -5.0%                    | True          |
| Trump      |                       371 | +0.8%                      |                     154 | -6.5%                    | False         |
| Up or Down |                       735 | +2.5%                      |                    1106 | +1.1%                    | True          |
| Weather    |                       195 | +5.4%                      |                     268 | +9.8%                    | True          |

## 3. Filtros diseñados en una muestra y probados en la otra

| diseñado_en    | probado_en     | filtro                                            |   apuestas | por_dolar   | ic_bajo   | ic_alto   | ganancia   |
|:---------------|:---------------|:--------------------------------------------------|-----------:|:------------|:----------|:----------|:-----------|
| descubrimiento | confirmacion   | Sin filtro                                        |       7978 | +0.2%       | -1.7%     | +2.0%     | +163 $     |
| descubrimiento | confirmacion   | Solo categorías positivas en descubrimiento       |       3476 | +3.0%       | +0.3%     | +5.9%     | +1054 $    |
| descubrimiento | confirmacion   | Solo tramos de precio positivos en descubrimiento |       6326 | +0.3%       | -1.9%     | +2.5%     | +167 $     |
| descubrimiento | confirmacion   | Filtro de momento (60 días, solo pasado)          |       3029 | +4.9%       | +1.9%     | +8.0%     | +1499 $    |
| confirmacion   | descubrimiento | Sin filtro                                        |       6732 | +1.1%       | -0.9%     | +3.1%     | +748 $     |
| confirmacion   | descubrimiento | Solo categorías positivas en confirmacion         |       1630 | +5.0%       | +0.9%     | +9.1%     | +820 $     |
| confirmacion   | descubrimiento | Solo tramos de precio positivos en confirmacion   |       5122 | +2.0%       | -0.4%     | +4.4%     | +1009 $    |
| confirmacion   | descubrimiento | Filtro de momento (60 días, solo pasado)          |       2501 | +3.8%       | +0.6%     | +7.1%     | +951 $     |

Lectura: un filtro solo vale si mejora el resultado en la muestra donde NO se diseñó y el intervalo de confianza deja de incluir el 0. El filtro de momento no se diseña con ninguna muestra (solo mira el pasado), así que su resultado vale en las dos.
