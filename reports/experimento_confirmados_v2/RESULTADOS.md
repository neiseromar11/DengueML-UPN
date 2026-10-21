# Resultado del experimento v2

Ejecutado el 20 de octubre de 2026. Resultado: **no cumple los criterios de reemplazo**.
El dashboard, su modelo, sus datos activos y los módulos fuente permanecen intactos:
se comprobaron las huellas de 20 archivos protegidos antes y después.

## Diseño ejecutado

49 orígenes externos; ocho orígenes internos por selección. Se compararon modelos
directos Poisson y de dos etapas, con profundidades 2 y 3. Cada horizonte tiene su
propio ajuste y solo admite etiquetas conocidas al origen. Las predicciones
externas abarcan pasos 2, 3 y 4, desde 2023-SE02 hasta 2026-SE39.
Hay 2,058 objetivos por método. Se seleccionó dos etapas con profundidad 3 en 25
orígenes, dos etapas con profundidad 2 en 15, directo con profundidad 3 en ocho
y directo con profundidad 2 en uno.

No se incorporó clima ni se cambiaron los parámetros tras observar resultados.
Es una evaluación retrospectiva exploratoria, no un periodo totalmente nuevo:
2025–2026 ya se había inspeccionado en v1. Cada origen se reentrena con datos
disponibles hasta ese momento.

## Comparación principal

| Método | MAE | Sensibilidad de presencia | Tasa de falsos positivos |
|---|---:|---:|---:|
| Reglas actuales, reentrenadas | 4.9054 | 63.34 % | 4.78 % |
| Última semana | 5.0214 | 70.78 % | 12.14 % |
| Referencia elegida internamente | 5.2614 | 60.98 % | 10.48 % |
| Candidato elegido internamente | 5.3774 | 77.68 % | 23.03 % |
| Promedio de cuatro semanas | 6.5508 | 74.77 % | 14.27 % |
| Siempre cero | 7.4261 | 0.00 % | 0.00 % |
| Referencia de 52 semanas | 11.3226 | 32.85 % | 20.04 % |

MAE menor es mejor. Presencia real significa al menos un caso; presencia predicha
significa conteo esperado >=0.5. No son alertas de brote ni categorías sanitarias.
La tasa de falsos positivos divide por los objetivos sin casos, no por todas las
predicciones positivas. La sensibilidad no equivale a precisión global.

El candidato identifica 428 de los 551 objetivos positivos, frente a 349 del
comparador con reglas; pero genera 347 falsos positivos frente a 72. Su MAE en
objetivos positivos también empeora: 18.5259 frente a 17.8582.

No cumple mejora global de 2 %, no empeorar horizontes, no empeorar error positivo,
ni el equilibrio predefinido entre sensibilidad y falsos positivos. Sí se entrega
el desglose completo de distritos y años, incluidos deterioros.

## Incertidumbre y supuestos

1,491 de los 2,058 objetivos (72.45 %) son vacíos tratados provisionalmente como
cero registros. Esto NO demuestra cobertura de vigilancia ni valida esa imputación.
La comparación es condicional a la misma hipótesis aplicada a todos los métodos.

El intervalo de remuestreo por bloques para la diferencia de MAE candidato menos
reglas actuales es aproximadamente [-0.0898, 1.0713]. Incluye cero: no se acredita
una diferencia concluyente con ese procedimiento. El deterioro puntual tampoco
demuestra superioridad universal del comparador. Estos intervalos no cubren el
sesgo por datos faltantes o revisiones de la fuente.

El MAE no es comparable directamente con el resumen final v1 de 2025–2026:
v2 incluye además 2023–2024, con niveles de casos distintos.

## Decisión y artefactos

No publicar ni sustituir el modelo original. El Excel sirve como fuente candidata
para investigación; que un candidato falle no invalida el archivo. Permanecen
pendientes la semántica de vacíos y la consolidación de la fuente.

Se conservan predicciones internas y externas, selecciones por origen, tiempos,
métricas globales y por horizonte/distrito/año, intervalos y huellas de integridad.
El protocolo original no se altera; esta nota registra su ejecución.
El script es `scripts/experimento_confirmados_v2.py` y evita sobrescribir resultados.

No se ajustó otro modelo al ver este resultado. Cualquier nuevo experimento debe
declarar qué hipótesis cambia y reconocer que estos periodos ya fueron examinados.
