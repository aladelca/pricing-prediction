---
name: plan-feature-implementation
description: Crear planes de implementacion detallados para features y guardarlos como archivos Markdown en /plans. Usar cuando Codex deba implementar una funcionalidad nueva, definir alcance tecnico, mapear archivos a crear o modificar, listar pruebas, o preparar validaciones con Ruff y mypy antes de escribir codigo. Tambien usar para pedidos como "haz un plan", "planifica este feature", "scope this implementation" o "before coding".
---

# Plan Feature Implementation

Crear o actualizar un plan de implementacion detallado en `/plans` antes de tocar codigo. Resolver dudas con evidencia del repositorio, configuracion, pruebas, issues y documentacion; no asumir contratos, nombres de archivos ni comportamientos.

## Workflow

1. Resolver el pedido antes de planificar

- Extraer objetivo, restricciones, resultado esperado, alcance tecnico y criterios de exito.
- Inspeccionar los archivos, configuraciones, issues `bd`, tests, comandos y skills relevantes.
- Confirmar stack, entry points, dependencias, convenciones de nombres y comandos reales del proyecto.
- Si falta un dato critico que no puede inferirse con evidencia suficiente, formular una pregunta corta y concreta. No cerrar el plan con supuestos riesgosos.

2. Crear o ubicar el archivo del plan

- Crear `/plans` si no existe.
- Reutilizar el plan existente si el feature ya tiene un archivo activo.
- Si no existe, crear `plans/YYYYMMDD-HHMM-<feature-slug>.md`.
- Usar un `slug` corto en kebab-case que describa el feature.

3. Construir el contexto tecnico

- Documentar el comportamiento actual y la brecha contra el comportamiento deseado.
- Registrar los archivos inspeccionados que explican la implementacion.
- Nombrar rutas, modulos, clases, funciones, comandos, tablas, endpoints, selectores o contratos relevantes.
- Identificar dependencias cruzadas: migraciones, seeds, feature flags, env vars, cron jobs, scrapers, pipelines o docs.

4. Delimitar el alcance

- Separar explicitamente `In scope` y `Out of scope`.
- Anotar riesgos, restricciones, dependencias y decisiones ya resueltas.
- Si una decision aun esta abierta pero no bloquea el trabajo, registrar opciones y criterio recomendado.

5. Mapear los archivos del cambio

- Enumerar todos los archivos a crear, modificar o eliminar.
- Para cada archivo, indicar accion, motivo, entidades afectadas y expectativa del cambio.
- Preferir paths exactos y simbolos concretos sobre descripciones vagas.
- Si un archivo importante se deja intacto, explicitarlo solo cuando esa decision evite confusion.

6. Desglosar la implementacion

- Ordenar los pasos para que el trabajo pueda ejecutarse sin redescubrir contexto.
- Incluir cambios de dominio, scraping, API, UI, persistencia, jobs, docs o tooling segun corresponda.
- Senalar puntos de compatibilidad, migracion de datos, rollback y observabilidad cuando existan.
- Mantener el plan como documento vivo: actualizarlo si el contexto cambia durante la implementacion.

7. Definir pruebas y validaciones

- Incluir las pruebas necesarias para cubrir comportamiento nuevo, regresiones y casos borde.
- Nombrar el tipo de prueba y el archivo objetivo cuando ya se conozca.
- Incluir comandos ejecutables desde la raiz del repo.
- Incluir siempre las validaciones de Python aplicables al alcance del cambio:
  - `ruff format --check <paths>` o el runner real del repo
  - `ruff check <paths>` o el runner real del repo
  - `mypy <paths>` o el runner real del repo
- Incluir el comando de tests del proyecto o, si aun no existe, el trabajo necesario para dejarlo definido.
- Si el repo no tiene configuracion para Ruff o mypy y el feature toca Python, agregar al plan los archivos y pasos necesarios para introducir o ajustar esa configuracion.

## Quality Bar

- Redactar el plan con suficiente detalle para implementar el feature sin volver a explorar el repo completo.
- Escribir `None` en preguntas abiertas o blockers cuando ya no existan.
- Evitar bullets como "actualizar backend" o "agregar tests"; especificar modulo, simbolo, archivo y objetivo.
- Incluir solo contexto accionable; no convertir el plan en una bitacora de pensamiento.
- Confirmar que el plan termina con una ruta clara hacia codigo, tests, `ruff` y `mypy`.

## Template

- Leer `references/plan-template.md` y reutilizar esa estructura como base.
- Adaptar secciones solo cuando el tipo de feature lo requiera, sin perder detalle operativo.
