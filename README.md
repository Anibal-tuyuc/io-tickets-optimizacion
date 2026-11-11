# Optimizador de Tickets y Acompañamiento Docente

**Universidad Mariano Gálvez de Guatemala** — Investigación de Operaciones, Sexto Semestre
Proyecto final: asignación equitativa de tickets HelpDesk y programación de supervisión docente.

[![CI](https://github.com/Anibal-tuyuc/io-tickets-optimizacion/actions/workflows/ci.yml/badge.svg)](https://github.com/Anibal-tuyuc/io-tickets-optimizacion/actions/workflows/ci.yml)

---

## Arranque rápido con Docker

Una sola orden levanta el backend, el frontend compilado y la base de prueba:

```bash
docker compose up --build
```

Abrir **http://localhost:8080** · API en `/docs`

El puerto se cambia con `IO_PORT=9000 docker compose up`.

---

## Qué hace

| Requerimiento del enunciado | Dónde está |
| :--- | :--- |
| Ingesta del `Control.xlsx` | `backend/app/etl/` |
| Sugerencia de gestor para ticket nuevo | Pestaña **Mesa de entrada** |
| Altas de gestores y vacaciones (Regla 1) | Pestaña **Equipo** |
| Simulador de cambio de docente (Regla 2) | Pestaña **Simulador** |
| Calendario sin colisiones (Regla 4) | Pestaña **Calendario** |
| Prioridad y antigüedad (Regla 5) | Función objetivo en `engine/assignment_solver.py` |
| Dashboard con KPIs y filtros | Pestaña **Tablero** |
| Auditoría de la base de origen | Pestaña **Calidad de datos** |

---

## Arranque en desarrollo

Requiere Python 3.11+ y Node 18+.

### 1. Backend (puerto 8000)

```bash
cd backend
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Documentación interactiva de la API: http://127.0.0.1:8000/docs

### 2. Frontend (puerto 5173)

```bash
cd frontend
npm run dev
```

Abrir http://localhost:5173

> El proxy de Vite redirige `/api` al backend. No hay que configurar CORS ni variables de entorno.

### 3. Reiniciar la demo

Botón **Reiniciar demo** en la barra lateral, o `POST /demo/reset`.
Restaura el estado original del Excel: imprescindible antes de grabar el video.

---

## Estructura

```
backend/
  app/
    core/          configuración, parámetros del modelo, calendario hábil GT
    etl/           lector del Excel (una config por hoja) + caché
    models/        entidades tipadas del dominio
    engine/        pesos, verificador, solver de tickets, solver de calendario, SLA
    api/           routers FastAPI + esquemas Pydantic
    services/      estado mutable de la demo + orquestador
  tests/           34 pruebas, incluidas las 3 pruebas obligatorias
frontend/
  src/
    api/           cliente tipado
    components/    UI compartida (semáforos, KPIs, paneles)
    views/         las 6 vistas
data/
  cache/           dataset normalizado y diagnóstico de calidad
  results/         capturas y salidas de las pruebas
```

---

## Pruebas

```bash
cd backend
../.venv/Scripts/python.exe -m pytest tests -q
```

Cubren:
- **Prueba 1**: desbalance inicial, optimización, cero colisiones, cobertura 100% de obligatorias.
- **Prueba 2**: vacaciones, redistribución, día saturado declarado.
- **Prueba 3**: cambio de docente, contraste rojo/verde, recálculo de peso.

Y además las invariantes críticas del modelo: ningún gestor con dos sesiones el mismo día, ninguna sesión supervisada fuera de su fecha real, ninguna sesión de Ruta B supervisada.

---

## Decisiones de modelado relevantes

1. **El Excel se abre en solo lectura.** Nunca se sobrescribe.
2. **Carga ponderada**, no conteo de tickets:
   `W = 0.60·PesoDocente + 0.35·FactorModalidad·Sesiones + 0.05·ln(1+Participantes)`
3. **Días hábiles reales** (con asuetos de Guatemala), no el conteo del Excel, que ignora asuetos e incluye ambos extremos. Ambas versiones están implementadas y cotejadas contra el archivo.
4. **Días infeasibles se declaran**, no se maquillan. Hay días con más sesiones obligatorias que gestores; el sistema los reporta como *día saturado* con su causa.
5. **El verificador es independiente del solver.** No comparte código con el modelo que valida.
6. **Reasignación acotada** (6 movimientos por defecto): bajar el ratio de 2.03 a 1.01 sin reorganizar la cartera completa.

---

## Resultados sobre los datos de prueba

| Métrica | Antes | Después |
| :--- | ---: | ---: |
| Ratio de desbalance (máx/mín) | 2.03× | 1.01× |
| Rango de carga (unidades) | 12.43 | 0.13 |
| Tickets reasignados | — | 6 de 44 |
| Colisiones diarias | 24 días | 0 |
| Cobertura de obligatorias | — | 100% |

Con el Gestor 1 de vacaciones el 13-oct queda infeasible (5 sesiones obligatorias, 4 gestores). Es un hecho del dataset, no un fallo: el sistema lo demuestra y lo reporta.

---

## Documentación

| Documento | Contenido |
| :--- | :--- |
| [`docs/informe_tecnico.pdf`](docs/pdf/informe_tecnico.pdf) | Informe técnico completo (29 páginas): análisis, modelo matemático, manual, pruebas y bitácora de IA |
| [`docs/guion_video.md`](docs/guion_video.md) | Guion del video explicativo, con minutaje y defensa anticipada de preguntas |
| [`docs/pdf/guion_video.pdf`](docs/pdf/guion_video.pdf) | El mismo guion en PDF |

---

## Estructura del repositorio

```
backend/     API FastAPI, ETL, motor de optimización y pruebas
frontend/    Interfaz React + TypeScript
data/source/ Excel de control (solo lectura)
```

---

## Docker

La imagen es multi-etapa: compila el frontend con Node y lo sirve desde FastAPI con Python 3.12 slim. Pesa **603 MB**, corre como usuario sin privilegios y expone un `HEALTHCHECK` contra `/health`.

```bash
docker build -t io-tickets-optimizacion .
docker run -p 8080:8000 io-tickets-optimizacion
```

El Excel se incluye en la imagen (`data/source/`) y la ruta se resuelve por la variable `IO_SOURCE_XLSX`, así que el contenedor funciona sin depender de rutas del equipo de desarrollo.
