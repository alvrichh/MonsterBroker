# MonsterBroker AI Review Guide

Memoria persistente para las revisiones automáticas de este repositorio.
Léela antes de comentar commits o pull requests.

## Identidad del proyecto

- Repositorio: `alvrichh/MonsterBroker`
- Propósito: bot de trading cripto en papel, panel web3 y radar de noticias.
  Proyecto de aprendizaje de Álvaro Rodríguez Molina; evolución del
  prototipo estático de 2021.
- Stack: backend Python 3.12 + FastAPI; frontend React 19 + Vite + JSX +
  SCSS. Claude (SDK `anthropic`) opcional para revisar señales y resumir
  noticias.

## Dirección de diseño

- Oscuro por defecto, herencia del prototipo: navy profundo, acento naranja,
  glow rosa en hover. Modo claro disponible.
- Sensación de terminal financiera premium: datos densos pero legibles,
  tipografía mono para cifras, tarjetas con cristal y profundidad suave.
- Móvil impecable: el panel y el radar deben funcionar a 390 px.

## Arquitectura

- `backend/app/api/` expone la API bajo `/api`. Los routers no contienen
  lógica: delegan en `agent/`, `services/`, `news/`, `onchain/`.
- `strategies/` y `tools/indicators.py` son funciones puras sobre listas de
  floats. Deben seguir testeables sin red.
- El agente guarda su estado en `backend/data/paper/state.json`. El radar
  escribe `backend/data/news/*.json` y `docs/news/*.md`.
- `frontend/src/lib/api.js` es el único sitio que hace `fetch` a la API.
- Tema y acento viven en `<html data-theme data-accent>`, fijados antes del
  primer paint por el script de `index.html`.

## Prioridades de revisión

1. **Seguridad financiera:** cualquier cambio que permita órdenes reales,
   lea claves fuera de `config.py` o relaje `PAPER_TRADING` es bloqueante.
2. Secretos: nada de claves, tokens ni `.env` en el diff.
3. Regresiones en la API: cambios de forma en respuestas sin actualizar
   `api/schemas/` y el frontend.
4. Robustez sin red / sin claves: el backend debe arrancar y los tests pasar
   con todas las variables vacías.
5. Móvil y accesibilidad en el frontend: focus visible, botones semánticos,
   contraste en ambos temas.
6. Workflows: `daily-news.yml` solo puede commitear `backend/data/news` y
   `docs/news`.

## Reglas de contenido

- No inventar rendimientos, backtests ni afirmaciones de rentabilidad.
- Las noticias son datos de terceros con enlace a la fuente; no se reescriben
  como opinión propia.

## Formato de salida

En español, directo y crítico. Máximo 5 bullets, el riesgo mayor primero,
con archivos/funciones exactos. Separar problemas reales de mejoras
opcionales. Si no hay nada relevante, decirlo y explicar qué se comprobó.
