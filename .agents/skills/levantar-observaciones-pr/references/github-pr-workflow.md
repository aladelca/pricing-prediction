# GitHub PR Workflow

Usa estos comandos para trabajar un PR completo sin perder contexto.

## 1. Resolver el PR objetivo

```bash
gh pr status
gh pr view <pr> --json number,title,body,baseRefName,headRefName,reviewDecision,statusCheckRollup,files,reviews,comments
gh pr view <pr> --comments
gh pr diff <pr>
```

Notas:

- `reviews` trae reviews generales y su estado.
- `comments` en `gh pr view` cubre conversacion general del PR.
- Los comentarios inline de codigo salen por separado con la API de review comments.

## 2. Listar comentarios inline de codigo

```bash
gh api repos/{owner}/{repo}/pulls/<pr>/comments --paginate
```

Para quedarte solo con comentarios padre del hilo:

```bash
gh api repos/{owner}/{repo}/pulls/<pr>/comments --paginate \
  --jq '.[] | select(.in_reply_to_id == null) | {id, path, line, user: .user.login, body, created_at, html_url}'
```

## 3. Ver estado de threads y comentarios outdated

`reviewThreads` da `isResolved` e `isOutdated`. `databaseId` sirve como `comment_id` para el endpoint REST de replies.

```bash
gh api graphql \
  -F owner='{owner}' \
  -F name='{repo}' \
  -F number=<pr> \
  -f query='
    query($owner:String!, $name:String!, $number:Int!) {
      repository(owner:$owner, name:$name) {
        pullRequest(number:$number) {
          reviewThreads(first: 100) {
            nodes {
              isResolved
              isOutdated
              comments(first: 100) {
                nodes {
                  id
                  databaseId
                  body
                  path
                  line
                  author { login }
                }
              }
            }
          }
        }
      }
    }
  '
```

## 4. Publicar respuestas

Responder un comentario inline padre:

```bash
gh api repos/{owner}/{repo}/pulls/<pr>/comments/<comment_id>/replies \
  -f body='Implemented with a local guard. Behavior stays the same for valid inputs.'
```

Publicar una respuesta general en la conversacion del PR:

```bash
gh pr comment <pr> --body 'Addressed the requested changes in the latest commit. I kept the existing behavior and only tightened validation around the reported edge case.'
```

## 5. Plantillas utiles

Implementado:

```text
Implemented in <file>. I kept the existing behavior and only added the smallest change needed to cover the reported case.
```

Sin cambio:

```text
I reviewed this path and kept the implementation as-is. The current logic already guarantees <property>, so I did not introduce a behavior change.
```

Requiere decision:

```text
This feedback implies a behavior change rather than a local fix. I have not changed the logic without confirmation so we can decide the intended contract first.
```
