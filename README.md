# GitHub Repo Health Check

CLI en Python para revisar metadatos básicos de repositorios públicos de GitHub y generar sugerencias concretas para mejorar su presentación.

## Objetivo

Ayudar a desarrolladores a revisar sus repositorios antes de compartirlos en un portafolio o postulación. Los resultados son informativos: no representan una nota absoluta sobre la calidad del código.

## Alcance inicial

La versión 0.1 consultará los repositorios públicos de un usuario u organización. Revisará descripción, licencia, topics, estado archivado y fecha de actualización. Mostrará un resumen en terminal y podrá guardar un informe Markdown. Solo lectura; no requiere token y no analiza repositorios privados.

El alcance completo y los criterios pendientes están en [docs/alcance-inicial.md](docs/alcance-inicial.md).

## Estado

CLI, reglas de revisión, informe Markdown y manejo de errores implementados. Las pruebas usan respuestas simuladas y no requieren conexión a GitHub.

## Herramientas previstas

Python 3.11 o superior, httpx para HTTP, pytest para pruebas y ruff para formato y lint.

## Desarrollo

Crear y activar un entorno virtual, instalar el proyecto y sus herramientas:

    py -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -e ".[dev]"

Comandos de calidad previstos:

    pytest
    ruff check .
    ruff format --check .

## Uso

Revisa los repositorios públicos de un usuario:

    repo-health octocat

Para una organización, indica `--organization`. Para guardar un informe Markdown,
añade `--output informe.md`:

    repo-health octocat --output informe.md
    repo-health mi-organizacion --organization --output informe.md

El informe incluye la fecha de generación, un resumen por severidad y las sugerencias
de cada repositorio. Los hallazgos son informativos y no representan una puntuación.

## Principios

- Consultar solo repositorios públicos.
- No guardar ni solicitar tokens para el MVP.
- Mantener el análisis separado de las llamadas HTTP.
- Probar el comportamiento sin depender de la red.
- Explicar las limitaciones de cada indicador.
