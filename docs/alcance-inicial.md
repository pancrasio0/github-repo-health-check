# Alcance del producto — versión inicial

## Problema

Al preparar un perfil de GitHub o presentar proyectos, cuesta detectar de forma rápida qué repositorios públicos tienen metadatos incompletos o poco claros. La herramienta dará una revisión inicial y sugerencias accionables, para ayudar a priorizar mejoras; no asignará una nota absoluta ni decidirá si un proyecto es bueno o malo.

## Usuario objetivo

Desarrolladores que mantienen repositorios públicos en GitHub y quieren revisar cómo se presentan antes de compartirlos en un portafolio, una postulación laboral o con colaboradores.

## Entrada

La persona usuaria ejecuta el CLI indicando el nombre de usuario u organización de GitHub. La versión inicial consulta únicamente los repositorios públicos que esa cuenta puede mostrar públicamente. No se solicita token ni se admite acceso a repositorios privados.

## Salida

- Resumen en terminal con la cantidad de repositorios revisados y los hallazgos agrupados por severidad.
- Cada hallazgo explica el dato observado y ofrece una sugerencia concreta.
- Opción para escribir un informe Markdown con fecha de generación, resumen y detalle por repositorio.
- Los resultados son sugerencias informativas; la actividad o ausencia de campos no constituye por sí sola una evaluación de calidad.

## Alcance de la versión 0.1

1. Consultar repositorios públicos de un usuario u organización mediante la API REST de GitHub.
2. Recorrer correctamente las páginas de resultados.
3. Revisar descripción, licencia, topics, estado archivado y fecha de actualización.
4. Mostrar resultados en terminal y exportarlos a Markdown.
5. Presentar mensajes entendibles para usuario inexistente, errores de red, respuestas inválidas y límites de solicitudes.
6. Probar las reglas y errores con respuestas simuladas, sin depender de Internet.

## Reglas de revisión

- Descripción ausente o vacía: severidad media, con sugerencia para explicar el propósito del repositorio.
- Licencia ausente: severidad media, con sugerencia para aclarar los términos de reutilización.
- Topics ausentes: severidad baja, con sugerencia para mejorar la descripción y el descubrimiento.
- Repositorio archivado: hallazgo informativo; archivar intencionalmente no es un problema.
- Sin actualizaciones por más de 365 días: hallazgo informativo; poca actividad no significa mala calidad.
- Si no hay fecha de actualización o no incluye zona horaria, no se evalúa actividad.
- No se calcula una puntuación global.

## Límites y exclusiones

- Solo lectura: no se crean, editan ni eliminan recursos en GitHub.
- Sin autenticación, tokens ni repositorios privados en el MVP.
- Sin aplicación web, base de datos, análisis de código, puntuación global ni recomendaciones generadas por IA.
- No se considerará automáticamente negativo que un repositorio esté archivado o tenga poca actividad; se informará el dato con contexto.
- No se publicarán datos del informe automáticamente.

## Criterio de éxito

Una persona puede instalar el CLI siguiendo el README, analizar los repositorios públicos de una cuenta, entender cada sugerencia y guardar un informe Markdown. Las pruebas se ejecutan sin red.

## Pendientes para las siguientes sesiones

- Ampliar las pruebas de reglas y casos límite.
