"""Esquemas Pydantic de la API (contratos con el frontend)."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


# ------------------------------------------------------------------- estado


class GestorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    estado: Literal["Activo", "Vacaciones", "Inactivo"] = "Activo"
    vacaciones_desde: date | None = None
    vacaciones_hasta: date | None = None


class GestorOut(BaseModel):
    nombre: str
    estado: str
    vacaciones_desde: date | None = None
    vacaciones_hasta: date | None = None
    tickets: int = 0
    carga: float = 0.0
    sesiones: int = 0
    disponible_hoy: bool = True


class EstadoRecursos(BaseModel):
    gestores: list[GestorOut]
    fecha_corte: date
    n_gestores_activos: int


class VacacionesIn(BaseModel):
    gestor: str
    desde: date
    hasta: date


class CambioDocenteIn(BaseModel):
    ticket_id: str
    nuevo_tipo: Literal["Interno", "Cooperante", "Externo"]
    aplicar: bool = False


class TicketNuevoIn(BaseModel):
    evento: str
    dependencia: str = ""
    prioridad: Literal["Urgente", "Alta", "Media", "Baja"] = "Media"
    modalidad: Literal["Presencial", "Virtual Sincrónico", "Virtual Asincrónico", "Mixto"]
    tipo_docente: Literal["Interno", "Cooperante", "Externo"] = "Interno"
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    grupos_programados: int = Field(default=1, ge=0, le=50)
    sesiones_por_grupo: int = Field(default=1, ge=0, le=50)
    obligatorio: bool = False


class SugerenciaGestor(BaseModel):
    gestor: str
    carga_actual: float
    carga_resultante: float
    delta: float
    recomendado: bool


class TicketOut(BaseModel):
    ticket_id: str
    estado: str
    prioridad: str
    modalidad: str
    evento: str
    dependencia: str
    gestor: str
    fecha_ingreso: date | None
    fecha_inicio: date | None
    fecha_fin: date | None
    tipo_docente: str
    observacion: str
    grupos: int
    sesiones_por_grupo: int
    total_sesiones: int
    dias_abiertos: int
    dias_habiles_restantes: int | None
    req_dias_habiles: int
    severidad: str
    es_ruta_b: bool
    obligatorio: bool
    peso: float = 0.0


# --------------------------------------------------------------- optimización


class OptimizarIn(BaseModel):
    theta_muestreo: float = Field(default=0.25, ge=0, le=1)
    semilla: int = 20261008
    max_movimientos: int = Field(default=6, ge=0, le=50)
    reasignar_tickets: bool = True
    generar_calendario: bool = True


class CargaGestorOut(BaseModel):
    gestor: str
    tickets: int
    carga_total: float
    sesiones: int
    dias_con_sesion: int
    tickets_obligatorios: int
    tickets_ruta_b: int


class ComparativaCargas(BaseModel):
    antes: list[CargaGestorOut]
    despues: list[CargaGestorOut]
    metricas_antes: dict[str, float]
    metricas_despues: dict[str, float]


class MovimientoOut(BaseModel):
    ticket_id: str
    de: str
    a: str
    peso: float
    prioridad: str


class SesionCalendarioOut(BaseModel):
    sesion_id: str
    ticket_id: str
    evento: str
    grupo: int
    numero_sesion: int
    fecha: date
    hora_inicio: str | None
    hora_fin: str | None
    gestor: str
    gestor_dueno: str
    es_apoyo: bool
    obligatoria: bool
    modalidad: str


class DiaCalendarioOut(BaseModel):
    fecha: date
    sesiones: list[SesionCalendarioOut]
    saturado: bool = False


class CalendarioOut(BaseModel):
    dias: list[DiaCalendarioOut]
    dias_saturados: list[dict[str, Any]] = []
    cobertura_pct: float
    obligatorias_cubiertas: int
    obligatorias_totales: int
    regulares_cubiertas: int
    regulares_totales: int
    colisiones: int
    violaciones: list[str] = []


class ResultadoOptimizacion(BaseModel):
    comparativa: ComparativaCargas
    movimientos: list[MovimientoOut]
    calendario: CalendarioOut | None = None
    alertas_plazo: list[dict[str, Any]] = []
    diagnostico_capacidad: list[dict[str, Any]] = []


# -------------------------------------------------------------- diagnóstico


class IncidenciaOut(BaseModel):
    tipo: str
    gravedad: str
    descripcion: str
    referencia: str | None = None
    accion_tomada: str = ""


class DiagnosticoOut(BaseModel):
    archivo: str
    hojas_leidas: list[str]
    tickets_totales: int
    tickets_abiertos: int
    sesiones_totales: int
    sesiones_fechadas: int
    grupos: int
    docentes: int
    resumen: dict[str, int]
    incidencias: list[IncidenciaOut]


class DashboardOut(BaseModel):
    kpis: dict[str, Any]
    cargas: list[CargaGestorOut]
    tickets_por_prioridad: dict[str, int]
    tickets_por_modalidad: dict[str, int]
    tickets_por_tipo_docente: dict[str, int]
    tickets_por_estado: dict[str, int]
    alertas_plazo: list[dict[str, Any]]
    ruta_b: dict[str, Any]
