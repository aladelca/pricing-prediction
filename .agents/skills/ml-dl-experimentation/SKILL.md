---
name: ml-dl-experimentation
description: Ejecutar experimentacion notebook-first para modelos tabulares de machine learning y deep learning. Usar cuando Codex deba crear un notebook en `notebook/`, cargar un dataset, hacer feature engineering extenso, comparar boosters con predominancia en CatBoost, probar redes neuronales en PyTorch con `mps`, validar con 5 folds, reportar siempre las metricas elegidas y declarar el modelo ganador de cada corrida o nueva iteracion.
---

# ML/DL Experimentation

Crear experimentos reproducibles para datos tabulares con un flujo centrado en notebooks. Empezar cada tarea creando un notebook en `notebook/`, registrar la metrica objetivo desde el inicio, iterar con varias corridas y dejar siempre identificado el modelo ganador.

## Inicio obligatorio

1. Crear `notebook/` si no existe.
2. Generar el notebook base con el script del skill.
3. Cargar el dataset y definir problema, target y metrica primaria.
4. Construir una linea base reproducible.
5. Hacer feature engineering extenso antes de concluir que el modelo ya esta listo.
6. Ejecutar varias corridas para intentar mejorar la mejor metrica disponible.
7. Cerrar el notebook con el leaderboard, las metricas elegidas y el modelo ganador.

Usar este comando como punto de partida:

```bash
python3 .agents/skills/ml-dl-experimentation/scripts/create_experiment_notebook.py \
  --slug house-prices \
  --metric rmse \
  --metric mae \
  --problem-type regression \
  --mode both
```

## Reglas no negociables

- Guardar todos los notebooks del trabajo en `notebook/`. No usar otras carpetas para notebooks de experimentacion.
- Definir al menos una metrica primaria y, cuando aporte contexto, una o mas metricas secundarias.
- Reportar siempre las metricas elegidas en cada corrida, no solo en el resultado final.
- Usar validacion con 5 folds en todas las comparaciones. Preferir `KFold(n_splits=5, shuffle=True, random_state=42)` y documentar cualquier excepcion.
- Generar varias corridas por iteracion para intentar superar el mejor score actual.
- Declarar siempre el modelo ganador al cierre de la corrida, con su familia, metrica principal y configuracion clave.
- Mantener semillas fijas y notas breves sobre decisiones de preprocessing, features y tuning.

## Flujo para boosting

- Empezar por una baseline simple para tener una referencia.
- Priorizar CatBoost como primer candidato fuerte para modelos tabulares.
- Probar despues variantes o comparativos con otros boosters solo si agregan valor real, por ejemplo XGBoost o LightGBM.
- Hacer feature engineering antes y entre corridas:
  - tratamiento de nulos
  - codificacion de categoricas
  - agregaciones
  - ratios
  - interacciones
  - fechas, ventanas, lags o rolling features cuando el dataset lo permita
- Registrar por corrida:
  - nombre del experimento
  - features usadas
  - hiperparametros
  - metrica media de CV
  - dispersion entre folds
  - observaciones clave

## Flujo para deep learning

- Usar PyTorch para todas las redes neuronales.
- Seleccionar `mps` como dispositivo por defecto cuando este disponible.
- Si `mps` no esta disponible, dejarlo documentado en el notebook antes de usar otro dispositivo.
- Mantener la comparacion con los boosters en el mismo esquema de 5 folds cuando sea viable para el problema.
- Reportar arquitectura, tamaño de embeddings o capas, funcion de perdida, optimizador, scheduler y estrategia de regularizacion.
- Guardar observaciones de entrenamiento: overfitting, estabilidad, early stopping y sensibilidad a features o batch size.

## Criterio de cierre por notebook

- El notebook debe terminar con una tabla de experimentos ordenada por la metrica principal.
- El resumen final debe decir explicitamente:
  - problema y dataset usados
  - metrica primaria y metricas secundarias
  - mejor score medio de CV y dispersion
  - modelo ganador
  - por que gano
  - siguientes pruebas recomendadas
- Si no hubo mejora material, escribirlo de forma explicita y dejar la mejor baseline como referencia vigente.

Usar este formato minimo para el cierre:

```text
Winner model: <nombre del experimento>
Family: <catboost|xgboost|lightgbm|pytorch|otro>
Primary metric: <metrica> = <valor medio CV>
Secondary metrics: <lista o n/a>
CV detail: <media +/- std o lista por fold>
Key features: <bloques de features mas utiles>
Key params: <hiperparametros mas relevantes>
Notebook: notebook/<archivo>.ipynb
Next iteration: <siguiente mejor apuesta>
```

## Uso del script

El script `scripts/create_experiment_notebook.py` crea un notebook base con las secciones que este skill espera. Genera un archivo `.ipynb` dentro de `notebook/`, crea la carpeta si no existe y deja celdas listas para:

- contexto del experimento
- setup reproducible
- carga de dataset
- baseline
- feature engineering
- corridas CatBoost
- corridas de boosters alternativos
- corridas PyTorch con `mps`
- leaderboard
- resumen del modelo ganador

Parametros utiles:

- `--slug`: nombre corto del experimento
- `--metric`: repetir para varias metricas
- `--problem-type`: `regression`, `classification` o `ranking`
- `--mode`: `boosting`, `pytorch` o `both`
- `--dataset-path`: ruta del dataset cuando ya se conoce
- `--target-column`: target cuando ya se conoce
- `--output`: ruta explicita del notebook; debe quedar en `notebook/`

## Entregables minimos

Antes de dar por terminada una experimentacion, entregar todo esto:

- Un notebook en `notebook/`.
- La lista de metricas elegidas.
- Un leaderboard de experimentos.
- El modelo ganador claramente identificado.
- Los proximos experimentos con mas probabilidad de mejora.
