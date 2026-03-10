# Plan Template

Usar esta estructura como base para cada plan en `/plans`. Mantener titulos claros, paths exactos y comandos ejecutables desde la raiz del repo.

```md
# <Feature title>

## Goal

- <Resultado tecnico y funcional esperado>

## Request Snapshot

- User request: "<prompt o resumen fiel del pedido>"
- Owner or issue: `<bd-id>` o `None`
- Plan file: `plans/YYYYMMDD-HHMM-<feature-slug>.md`

## Current State

- <Como funciona hoy el area afectada>
- <Archivos, simbolos y contratos revisados>
- <Limitaciones o deuda tecnica relevante>

## Findings

- <Hallazgo confirmado con evidencia>
- <Hallazgo confirmado con evidencia>

## Scope

### In scope

- <Trabajo incluido>

### Out of scope

- <Trabajo excluido de manera explicita>

## File Plan

| Path | Action | Details |
| --- | --- | --- |
| `path/to/file.py` | modify | Ajustar `symbol_name` para soportar `<cambio>` |
| `path/to/new_file.py` | create | Implementar `<responsabilidad>` |

## Data and Contract Changes

- <Schemas, payloads, selectors, CLI args, env vars, feature flags, migrations o `None`>

## Implementation Steps

1. <Primer cambio con dependencia explicita>
2. <Segundo cambio>
3. <Paso de integracion, wiring o rollout>

## Tests

- Unit: `tests/...` cubrir `<caso>`
- Integration: `tests/...` validar `<flujo>`
- Regression: `<escenario>` o `None`

## Validation

- Format: `<runner> ruff format --check <paths>`
- Lint: `<runner> ruff check <paths>`
- Types: `<runner> mypy <paths>`
- Tests: `<runner> pytest <paths>` o el comando real del proyecto

## Risks and Mitigations

- <Riesgo> -> <Mitigacion>

## Open Questions

- None

## Acceptance Criteria

- <Resultado verificable 1>
- <Resultado verificable 2>

## Definition of Done

- <Codigo implementado>
- <Tests agregados o actualizados>
- <Ruff y mypy en verde>
- <Plan actualizado si cambio el alcance>
```

## Checklist

- Resolver dudas importantes antes de cerrar el plan.
- Referenciar paths exactos, no areas abstractas.
- Incluir todos los archivos a crear o modificar.
- Incluir tests nuevos o ajustes sobre tests existentes.
- Incluir `ruff format --check`, `ruff check` y `mypy`.
- Ajustar el runner real del repo: `uv run`, `poetry run`, `pipenv run`, `python -m`, etc.
- Dejar `Open Questions` en `None` cuando no haya bloqueos reales.
