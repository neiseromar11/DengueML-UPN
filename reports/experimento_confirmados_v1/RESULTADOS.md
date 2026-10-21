# Experimento provisional con dengue confirmado

## Decisión

No se publica un modelo nuevo. La variante nueva seleccionada en desarrollo
(XGBoost sin las reglas actuales) no supera todas las referencias simples en
el periodo final. La versión con reglas actuales, reentrenada como comparación,
obtiene el mejor MAE final de este experimento. Este hallazgo no autoriza a
seleccionarla retrospectivamente como si hubiera superado el protocolo previo.

Todos los resultados dependen de una hipótesis sin confirmación institucional:
las celdas vacías de casos anteriores al último conteo se interpretan como cero
registros. El 87.06 % de los 966 objetivos del resumen final procede de esa
imputación (841 filas). Por tanto, el resultado es exploratorio.

## Diseño fijado antes de ejecutar

- Objetivo: casos confirmados por distrito y semana, no todos los notificados.
- 14 distritos de DIRIS Lima Centro.
- Histórico para ajuste: desde 2020; se excluyeron 2018–2019 porque no contienen
  ningún conteo informado.
- Selección: 26 orígenes con objetivos entre 2023-SE01 y 2024-SE52.
- Evaluación final: 23 orígenes con objetivos entre 2025-SE01 y 2026-SE39.
  SE40 no forma un bloque final completo de cuatro semanas y no se evaluó.
- En cada origen se reentrena con semanas disponibles hasta ese momento.
  Los bloques futuros no se incorporan a características de ese pronóstico.
  Observaciones de bloques ya transcurridos sí entran en ajustes posteriores:
  es una evaluación con actualización sucesiva, no un modelo congelado dos años.
- Predicciones recursivas de pasos 1–4; selección y resumen principal en pasos
  2–4. No se redondean pronósticos para calcular MAE.
- Tres candidatos nuevos: XGBoost sin reglas, XGBoost cuadrático con variables
  estacionales y distritales, y XGBoost Poisson con esas variables.
- Referencias: siempre cero, último observado, media de cuatro semanas y rezago
  de 52 semanas. Este último no alinea exactamente años con 53 semanas.
- La variante con reglas actuales se reentrena como comparador predefinido:
  no es el archivo del modelo que sirve el dashboard.
- No se incorporó clima: todavía hay problemas de cobertura y disponibilidad.
- Configuraciones y cortes en `protocolo.json`; candidato en
  `seleccion_congelada.json`, guardado antes de evaluar el periodo final.

No se seleccionaron parámetros usando métricas finales. Sin embargo, los datos
2025–2026 ya habían sido inspeccionados durante la auditoría de cobertura:
no se describe este periodo como totalmente desconocido ni como evaluación
prospectiva. Futuras iteraciones deben reconocer que estos resultados ya se vieron.

## Resultados finales, pasos 2–4

MAE en casos por distrito-semana; menor es mejor.

| Método | MAE | RMSE | MAE solo en objetivos positivos |
|---|---:|---:|---:|
| XGBoost con reglas actuales, reentrenado | 0.5866 | 3.8101 | 5.1282 |
| Última semana | 0.7174 | 4.1064 | 5.6364 |
| Promedio de cuatro semanas | 0.8041 | 4.8263 | 6.4250 |
| Siempre cero | 1.0807 | 7.3913 | 9.4909 |
| XGBoost sin reglas, candidato seleccionado | 1.1071 | 4.2841 | 5.0115 |
| Referencia de 52 semanas | 11.5155 | 70.9165 | 62.6818 |

El comparador con reglas reduce el MAE aproximadamente 18.24 % frente a
persistencia en este periodo. No es un porcentaje de precisión.
En desarrollo, su mejora frente a persistencia fue solo aproximadamente 1.17 %,
por debajo del requisito del 2 % incluso antes de comprobar cada horizonte.
El candidato nuevo seleccionado tuvo MAE de desarrollo 8.9346, frente a 8.8288
de persistencia: tampoco había acreditado una mejora previa.

El candidato sin reglas fue evaluado para documentar su generalización, no porque
hubiera cumplido un criterio de publicación. `resultado.json` registra su rechazo.

## Limitaciones que el promedio oculta

De los 966 objetivos finales, 110 tienen casos positivos.
El comparador con reglas predice exactamente cero en 74 de esos 110 objetivos.
No son 110 brotes: son combinaciones de distrito, semana y horizonte.
Este resultado no acredita capacidad de anticipación de brotes.

El candidato sin reglas tiene un error algo menor en las semanas positivas,
pero empeora el MAE global. Eliminar una regla no garantiza mejor desempeño
en todas las situaciones.

El MAE del comparador con reglas cambia de 0.1155 en 2025 a 1.1990 en 2026.
Por ello no debe comunicarse una única cifra como garantía universal.

La métrica `mae_solo_informados` se entrega como análisis de sensibilidad:
excluye los objetivos imputados, pero sus predictores siguen usando la hipótesis
de ceros. Además, ese subconjunto sobrerrepresenta semanas con casos;
no representa por sí solo toda la población de semanas.

## Comprobaciones realizadas

- Objetivos de selección anteriores a los del bloque final.
- Origen anterior a cada objetivo; 14 distritos en cada horizonte y origen.
- Ausencia de claves duplicadas; predicciones finitas.
- Fuente candidata y puntero del modelo activo conservan su huella.
- No se modificó el Excel original, el dashboard ni el modelo publicado.

## Qué sigue

Este experimento ya permite descartar la idea de que eliminar las reglas,
añadir estacionalidad o cambiar la función de pérdida garantiza una mejora.
Una siguiente investigación podría evaluar pronósticos directos por horizonte
y tratamientos explícitos de ocurrencia y cantidad, con clima disponible al
origen cuando su cobertura esté resuelta.

No ajustar esos métodos repetidamente contra este mismo bloque final y
presentarlo después como independiente. Habría que fijar un nuevo protocolo,
usar evaluación temporal anidada o esperar un periodo nuevo reservado.
La interpretación de vacíos sigue pendiente y debe figurar en cualquier
presentación académica.

## Archivos

Los CSV de detalle permiten recalcular los resultados. Se incluyen métricas
por horizonte, distrito y año, además del panel provisional con una columna
que identifica cada objetivo imputado. El script reproducible es
`scripts/experimento_confirmados.py`. Evita sobrescribir esta ejecución.
