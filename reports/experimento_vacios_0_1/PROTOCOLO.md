# Sensibilidad a los vacíos de Casos: 0 versus 1

Solicitud del usuario, 20 de octubre de 2026. Experimento aislado.

Se sustituyen SOLO los valores ausentes de casos por 0 o por 1. Se conservan los ceros explícitos y todos los otros valores registrados. Cada escenario modifica el historial de entrenamiento y las características derivadas de ese historial; se reentrena desde cero. No se altera el Excel ni el panel original.

Se mantiene el diseño climático v3: 49 cortes, 14 distritos, horizontes 2/3/4, modelo Poisson directo de profundidad 2 y 150 árboles con los mismos parámetros, variables y sustituciones territoriales. Dos modelos por escenario: con y sin clima. Sin optimización posterior. Se recalculan persistencia, promedio de cuatro semanas y constantes 0/1 para cada escenario; no se reutilizan controles entrenados con otros supuestos.

Evaluación principal: solo objetivos con Casos explícitamente informado en el Excel, idénticos entre escenarios. Incluye ceros explícitos. Se reporta por separado la evaluación de todo el panel con objetivos imputados, denominada supuestos: esas métricas no validan la verdad de los valores imputados ni deben compararse como si el objetivo fuera idéntico.

No inferir que un vacío equivale a un caso aunque mejore el MAE. El subconjunto informado puede estar sesgado y no representa necesariamente todas las semanas. Los cortes ya son conocidos: análisis exploratorio de sensibilidad, sin publicación ni afirmación prospectiva.

Se auditan las celdas rellenadas y se comparan huellas de archivos protegidos. Se exige que el escenario 0 reproduzca las predicciones climáticas v3 y que ambos escenarios tengan exactamente los mismos objetivos informados.
