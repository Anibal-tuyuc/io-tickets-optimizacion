"""Modelos de dominio normalizados.

Ningún módulo fuera de `etl` debe tocar pandas ni nombres de columna del Excel.
Todo el resto del sistema consume estas estructuras tipadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from enum import Enum
from typing import Literal

# ------------------------------------------------------------------ enums


class EstadoTicket(str, Enum):
    ABIERTO = "Abierto"
    RESUELTO = "Resuelto"
    CANCELADO = "Cancelado"


class Prioridad(str, Enum):
    URGENTE = "Urgente"
    ALTA = "Alta"
    MEDIA = "Media"
    BAJA = "Baja"


class Modalidad(str, Enum):
    PRESENCIAL = "Presencial"
    VIRTUAL_SINCRONICO = "Virtual Sincrónico"
    VIRTUAL_ASINCRONICO = "Virtual Asincrónico"
    MIXTO = "Mixto"


class TipoDocente(str, Enum):
    INTERNO = "Interno"
    COOPERANTE = "Cooperante"
    EXTERNO = "Externo"


class TipoObservacion(str, Enum):
    """Interpretación de la columna `Observaciones` del Registro."""

    OBLIGATORIO_DOCENTE_NUEVO = "OBLIGATORIO - Docente Nuevo"
    OBLIGATORIO_PRIMERA_VEZ = "OBLIGATORIO - Primera Vez"
    OBLIGATORIO_TEMA_NUEVO = "OBLIGATORIO - Tema Nuevo"
    REGULAR_MUESTREO = "REGULAR - Muestreo Aleatorio"
    RUTA_B_DFV = "TRASLADO A DFV - Ruta B"
    CAMBIO_DINAMICO = "CAMBIO DINÁMICO: Interno a Externo"
    DESCONOCIDA = "DESCONOCIDA"

    @property
    def es_obligatoria(self) -> bool:
        return self in (
            TipoObservacion.OBLIGATORIO_DOCENTE_NUEVO,
            TipoObservacion.OBLIGATORIO_PRIMERA_VEZ,
            TipoObservacion.OBLIGATORIO_TEMA_NUEVO,
        )

    @property
    def es_ruta_b(self) -> bool:
        return self is TipoObservacion.RUTA_B_DFV


class EstadoGestor(str, Enum):
    ACTIVO = "Activo"
    VACACIONES = "Vacaciones"
    INACTIVO = "Inactivo"


class Severidad(str, Enum):
    """Semáforo de plazo administrativo (regla 2)."""

    VERDE = "VERDE"      # margen holgado
    AMBAR = "AMBAR"      # queda poco margen (<= 25% de holgura)
    ROJO = "ROJO"        # retraso inminente o ya insuficiente
    SIN_FECHA = "SIN_FECHA"


class EstadoSesion(str, Enum):
    CUBIERTA = "Cubierta"
    NO_CUBIERTA = "No cubierta"
    DIA_SATURADO = "Día saturado"
    FUERA_DE_RUTA = "Fuera de Ruta A"


# ------------------------------------------------------------------ entidades


@dataclass(slots=True)
class Ticket:
    ticket_id: str
    estado: EstadoTicket
    prioridad: Prioridad
    modalidad: Modalidad
    evento: str
    dependencia: str
    gestor: str
    fecha_ingreso: date | None
    fecha_asignacion: date | None
    fecha_inicio: date | None
    fecha_fin: date | None
    tipo_docente: TipoDocente
    observacion: TipoObservacion
    observacion_raw: str
    grupos_programados: int
    sesiones_por_grupo: int
    total_sesiones: int
    costo_docente: float | None = None
    requisicion: str | None = None
    link: str | None = None

    # derivados que rellena el ETL
    dias_abiertos: int = 0
    req_dias_habiles: int = 0
    # Hábitles de la fecha de asignación al inicio (equivale al NETWORKDAYS del
    # Excel en la hoja GestionDocente: capacidad total de la ventana).
    dias_habiles_totales: int | None = None
    # Misma ventana pero descontando asuetos (definición correcta, la del modelo).
    dias_habiles_totales_correcto: int | None = None
    # Hábitles desde el corte de simulación al inicio: margen real que queda.
    dias_habiles_restantes: int | None = None
    severidad: Severidad = Severidad.SIN_FECHA

    @property
    def es_ruta_b(self) -> bool:
        return self.modalidad is Modalidad.VIRTUAL_ASINCRONICO

    @property
    def es_ruta_a(self) -> bool:
        return not self.es_ruta_b

    @property
    def requiere_supervision_obligatoria(self) -> bool:
        return self.observacion.es_obligatoria


@dataclass(slots=True, frozen=True)
class Sesion:
    sesion_id: str          # clave estable: ticket|grupo|sesion
    ticket_id: str
    grupo: int
    numero_sesion: int
    fecha: date
    hora_inicio: time | None
    hora_fin: time | None
    codigo: str | None = None

    # se rellenan al enriquecer con el Registro
    gestor: str = ""
    modalidad: Modalidad | None = None
    obligatoria: bool = False
    observacion_raw: str = ""


@dataclass(slots=True)
class Grupo:
    ticket_id: str
    grupo: int
    gestor: str
    fecha_inicio: date | None
    fecha_fin: date | None
    estado: str
    nombramiento: str | None
    participantes_solicitados: int | None
    participantes_nombrados: int | None
    evento: str


@dataclass(slots=True)
class Docente:
    ticket_id: str
    docente: str
    identificacion: str | None
    horas: float | None
    grupo: int | None
    sesiones: int | None
    tipo: Literal["Interno", "Externo"] | None = None


@dataclass(slots=True)
class Gestor:
    gestor_id: str
    nombre: str
    estado: EstadoGestor = EstadoGestor.ACTIVO
    vacaciones_desde: date | None = None
    vacaciones_hasta: date | None = None

    def disponible_en(self, dia: date) -> bool:
        if self.estado is EstadoGestor.INACTIVO:
            return False
        if self.estado is EstadoGestor.VACACIONES:
            if self.vacaciones_desde and self.vacaciones_hasta:
                return not (self.vacaciones_desde <= dia <= self.vacaciones_hasta)
            return False
        return True


# ------------------------------------------------------------------ calidad


@dataclass(slots=True)
class Incidencia:
    """Un problema detectado en la base de datos de origen."""

    tipo: str
    gravedad: Literal["alta", "media", "baja"]
    descripcion: str
    referencia: str | None = None
    accion_tomada: str = ""


@dataclass(slots=True)
class DiagnosticoDatos:
    archivo: str = ""
    hojas_leidas: list[str] = field(default_factory=list)
    tickets_totales: int = 0
    tickets_abiertos: int = 0
    sesiones_totales: int = 0
    sesiones_fechadas: int = 0
    sesiones_abiertos_fechadas: int = 0
    grupos: int = 0
    docentes: int = 0
    incidencias: list[Incidencia] = field(default_factory=list)

    def agregar(self, incidencia: Incidencia) -> None:
        self.incidencias.append(incidencia)

    @property
    def resumen(self) -> dict[str, int]:
        return {
            "incidencias_alta": sum(1 for i in self.incidencias if i.gravedad == "alta"),
            "incidencias_media": sum(1 for i in self.incidencias if i.gravedad == "media"),
            "incidencias_baja": sum(1 for i in self.incidencias if i.gravedad == "baja"),
        }


@dataclass(slots=True)
class Dataset:
    """Resultado completo del ETL."""

    tickets: list[Ticket]
    sesiones: list[Sesion]
    grupos: list[Grupo]
    docentes: list[Docente]
    gestores: list[Gestor]
    diagnostico: DiagnosticoDatos
    fuente: str = ""

    @property
    def tickets_abiertos(self) -> list[Ticket]:
        return [t for t in self.tickets if t.estado is EstadoTicket.ABIERTO]

    @property
    def tickets_por_id(self) -> dict[str, Ticket]:
        return {t.ticket_id: t for t in self.tickets}

    @property
    def sesiones_por_ticket(self) -> dict[str, list[Sesion]]:
        out: dict[str, list[Sesion]] = {}
        for s in self.sesiones:
            out.setdefault(s.ticket_id, []).append(s)
        return out
