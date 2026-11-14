# GitHub Repo Health Check

CLI en Python para revisar metadatos básicos de repositorios públicos de GitHub y generar sugerencias concretas para mejorar su presentación.

## Objetivo

Ayudar a desarrolladores a revisar sus repositorios antes de compartirlos en un portafolio o postulación. Los resultados son informativos: no representan una nota absoluta sobre la calidad del código.

## Alcance inicial

La versión 0.1 consultará los repositorios públicos de un usuario u organización. Revisará descripción, licencia, topics, estado archivado y fecha de actualización. Mostrará un resumen en terminal y podrá guardar un informe Markdown. Solo lectura; no requiere token y no analiza repositorios privados.

El alcance completo y los criterios pendientes están en [docs/alcance-inicial.md](docs/alcance-inicial.md).

## Estado

Modelo, cliente HTTP, paginación y errores de API preparados. La siguiente etapa es definir las reglas de revisión y el umbral de actividad reciente.

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

## Principios

- Consultar solo repositorios públicos.
- No guardar ni solicitar tokens para el MVP.
- Mantener el análisis separado de las llamadas HTTP.
- Probar el comportamiento sin depender de la red.
- Explicar las limitaciones de cada indicador.
