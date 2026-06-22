---
name: publish-gh
description: Publicar rama feature a Docker Hub via merge local a main. Commitea cambios, actualiza CHANGELOG, pushea, mergea a main y activa el CI workflow.
license: MIT
compatibility: opencode
---

## REGLA CRÍTICA — SIEMPRE PREGUNTAR

**NUNCA ejecutes commit, push, merge, ni ningún cambio sin preguntar primero al usuario y obtener su confirmación explícita.** Cada paso debe ser aprobado antes de ejecutarse. Si el usuario dice "ejecuta" o "si", recién ahí procede.

## Qué hace

1. **Pregunta la versión nueva** (ej: `1.4.0`) mostrando la última versión en `CHANGELOG.md` como referencia.
2. **Genera entrada de CHANGELOG** automáticamente: usa `git log` desde el último tag o versión en CHANGELOG, agrupa commits por tipo (`feat` → `Added`, `fix` → `Fixed`, `refactor`/`docs` → `Changed`, `chore` → `Internal`).
3. **Muestra el draft** al usuario y **pide confirmación explícita**. Si no acepta, permite editar el texto antes de continuar.
4. **Pregunta al usuario si quiere proceder** antes de tocar `CHANGELOG.md`.
5. **Pregunta al usuario si quiere proceder** antes de hacer `git add` y `git commit`.
6. **Pregunta al usuario si quiere proceder** antes de hacer `git push`.
7. **Pregunta al usuario si quiere proceder** antes de hacer el merge a `main` y `push`.
8. **Vuelve a la rama original** con `git checkout <rama>` (este paso no necesita pregunta).

## Notas

- No borra ramas (ni local ni remoto).
- Si `git status` está limpio, pregunta si continuar igual (por si solo se quiere mergear).
- Si hay conflictos en el merge, aborta (`git merge --abort`) y da instrucciones al usuario.
- El CHANGELOG se formatea como las entradas existentes:
  ```markdown
  ## [X.Y.Z] - YYYY-MM-DD

  ### Added
  - ...

  ### Changed
  - ...

  ### Fixed
  - ...

  ### Internal
  - ...
  ```

## Frases que activan esta skill

- "publica en gh"
- "publica en github"
- "publica en docker hub"
- "publish to gh"
- "publish to github"
- "publish to docker hub"
