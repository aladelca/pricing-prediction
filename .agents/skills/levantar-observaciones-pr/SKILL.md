---
name: levantar-observaciones-pr
description: Leer comentarios y code reviews de un pull request, analizarlos de punta a punta, responder cada observacion y levantarla con cambios minimos y poco invasivos. Usar cuando el usuario pida revisar feedback de un PR, responder comentarios de GitHub, implementar observaciones sin cambiar la logica existente, o cerrar hilos de review de forma segura.
---

# Levantar Observaciones de PR

Este skill resuelve feedback de un pull request de extremo a extremo:

1. Lee el contexto completo del PR.
2. Agrupa comentarios y code reviews por observacion real.
3. Implementa el cambio mas pequeno que resuelve el punto.
4. Valida que la logica existente siga intacta.
5. Deja respuestas listas o publicadas por hilo, segun lo que pidio el usuario.

Usa este skill cuando el review ya existe y el trabajo consiste en procesar ese
feedback. No lo uses para abrir el PR o hacer self-review inicial; para eso ya
existe el workflow de `feature-pr-review-gate`.

## Objetivo operativo

- Resolver todas las observaciones accionables del PR sin meter refactors oportunistas.
- Mantener contratos, firmas publicas, flujos y comportamiento observable salvo que la observacion demuestre un bug real.
- Responder cada comentario con evidencia: que cambio, donde cambio y por que el ajuste fue el minimo necesario.

## Workflow

### 1. Resolver el PR y leerlo completo

- Si el usuario no dio numero de PR, inferirlo desde la rama actual con `gh pr status` o pedirlo si no hay forma segura de deducirlo.
- Leer:
  - descripcion del PR
  - diff y archivos cambiados
  - reviews generales
  - comentarios inline
  - estado de checks y decision de review
- No trabajar solo con el ultimo comentario ni con una captura parcial del review.
- Leer `references/github-pr-workflow.md` para los comandos de `gh` ya validados.

### 2. Construir un inventario de observaciones

Crear una lista de trabajo por observacion, no por evento. Cada item debe quedar con:

- `thread/comment id`
- reviewer
- archivo y linea actual si aplica
- resumen del problema
- clasificacion: `correctness`, `regression-risk`, `readability`, `test-gap`, `naming`, `question`, `non-actionable`
- accion elegida: `code-change`, `test-only`, `reply-only`, `needs-decision`

Reglas:

- Deduplicar comentarios repetidos entre review body, inline comments y replies.
- Si el hilo esta `outdated`, revisar igual si la preocupacion sigue aplicando al codigo actual.
- Si aparece trabajo nuevo fuera de alcance, crear issue en `bd` en vez de mezclarlo silenciosamente con el PR.

### 3. Decidir antes de tocar codigo

Antes de editar:

- Verificar si la observacion realmente requiere cambio de comportamiento o solo claridad.
- Si el comentario pide un cambio funcional que altera la logica, no hacerlo sin explicitarlo. Eso ya no es una correccion poco invasiva.
- Si el comentario se resuelve mejor con una prueba, una condicion mas precisa, una validacion extra o una respuesta tecnica, elegir esa salida antes que refactorizar.
- Si la observacion es incorrecta o ya esta cubierta, responder con evidencia y no fuerces un cambio cosmetico.

### 4. Implementar la solucion menos invasiva

Preferir, en este orden:

1. Guard clause, null check o condicion mas precisa.
2. Ajuste local en la misma funcion o modulo.
3. Prueba puntual que capture el caso observado.
4. Comentario tecnico corto solo si elimina ambiguedad real.
5. Extraccion pequena de helper privado si reduce duplicacion creada por la correccion.

Evitar por defecto:

- renames amplios
- mover logica entre capas
- cambiar firmas publicas
- reordenar archivos o imports sin necesidad
- cambiar estilos o formato fuera del area tocada
- mezclar varias observaciones en un solo cambio dificil de revisar

### 5. Validar que el fix no cambio la logica

- Ejecutar pruebas, linters o checks del alcance mas pequeno posible sobre los archivos tocados.
- Revisar el diff final para asegurar que solo cambiaron lineas necesarias.
- Si agregaste un test, confirmar que falla antes del fix o que al menos cubre el caso reportado de forma directa.
- Si no puedes validar localmente, decirlo de forma explicita antes de responder en el PR.

### 6. Responder comentarios

- Por defecto, redactar respuestas en el mensaje final y solo publicarlas en GitHub si el usuario lo pidio.
- Si el usuario pidio publicar respuestas y `gh` tiene auth valida, responder sobre el comentario padre del hilo usando el endpoint indicado en la referencia.
- No respondas a replies de replies.
- Cada respuesta debe ser corta y util:
  - que se cambio o por que no se cambio
  - archivo o test afectado
  - confirmacion de que se mantuvo la logica, o aclaracion de que el comentario implicaria cambiar comportamiento

### 7. Cerrar la vuelta

Entregar:

- observaciones resueltas
- observaciones respondidas sin cambio
- observaciones bloqueadas o que requieren decision
- comandos de validacion ejecutados
- riesgos residuales si quedaron

## Heuristicas de respuesta

Usa estas formas de decision:

- `Implemented`: cuando hubo cambio de codigo o test pequeno y verificable.
- `Clarified`: cuando el codigo ya era correcto y la mejor respuesta es explicar con evidencia.
- `Deferred`: cuando la observacion pide cambiar comportamiento, contrato o alcance; no la absorbas sin confirmacion.

## Referencias

- `references/github-pr-workflow.md`: comandos de `gh` para leer comentarios, inspeccionar threads y responderlos.
