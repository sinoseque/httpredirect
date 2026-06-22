---
name: publish-gh
description: Publicar rama feature a Docker Hub via merge local a main. Commitea cambios, actualiza CHANGELOG, pushea, mergea a main y activa el CI workflow.
license: MIT
compatibility: opencode
---

## Qué hace

1. **Pregunta la versión nueva** (ej: `1.4.0`) mostrando la última versión en `CHANGELOG.md` como referencia.
2. **Genera entrada de CHANGELOG** automáticamente: usa `git log` desde el último tag o versión en CHANGELOG, agrupa commits por tipo (`feat` → `Added`, `fix` → `Fixed`, `refactor`/`docs` → `Changed`, `chore` → `Internal`).
3. **Muestra el draft** al usuario y pide confirmación. Si no acepta, permite editar el texto antes de continuar.
4. **Actualiza `CHANGELOG.md`** insertando la nueva sección tras la cabecera `# Changelog`.
5. **`git add -A`** y **`git commit -m "<nombre_rama_completo>"`** (ej: `feature/refactor`).
6. **`git push origin <rama>`**
7. **Merge local a main**: `git checkout main`, `git merge <rama>`, `git push origin main`.
8. **Vuelve a la rama original** con `git checkout <rama>`.

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
