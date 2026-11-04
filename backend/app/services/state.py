"""Estado mutable de la sesión de trabajo.

El Excel de origen es inmutable. Todo cambio del usuario (alta de gestor,
vacaciones, cambio de tipo de docente, tickets nuevos, reasignaciones) vive
aquí, en un único objeto en memoria con reinicio explícito. Así la demo del
video siempre arranca desde el mismo punto con un clic.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date

from app.core.config import SIMULATION_DATE
from app.etl.loader import load_dataset
from app.models.domain import (
    Dataset,
    EstadoGestor,
    EstadoTicket,
    Gestor,
    Prioridad,
    Ticket,
    TipoDocente,
    TipoObservacion,
)


@dataclass
class EstadoApp:
    ds: Dataset
    gestores: list[Gestor] = field(default_factory=list)
    tickets: list[Ticket] = field(default_factory=list)
    hoy: date = field(default_factory=lambda: date.fromisoformat(SIMULATION_DATE))
    asignacion_manual: dict[str, str] = field(default_factory=dict)
    ultima_optimizacion: dict | None = None
    contador_tickets: int = 0

    def tickets_para_optimizar(self) -> list[Ticket]:
        """Tickets abiertos: el universo del problema de asignación."""
        return [t for t in self.tickets if t.estado is EstadoTicket.ABIERTO]


class GestorEstado:
    """Contenedor thread-safe del estado de la aplicación."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._estado = self._nuevo_estado()

    # ------------------------------------------------------------- ciclo
    def _nuevo_estado(self) -> EstadoApp:
        ds = load_dataset()
        return EstadoApp(
            ds=ds,
            gestores=deepcopy(ds.gestores),
            tickets=deepcopy(ds.tickets),
        )

    def get(self) -> EstadoApp:
        return self._estado

    def reset(self) -> EstadoApp:
        with self._lock:
            self._estado = self._nuevo_estado()
            return self._estado

    # --------------------------------------------------------- gestores
    def agregar_gestor(self, nombre: str) -> Gestor:
        with self._lock:
            nombre = nombre.strip()
            if not nombre:
                raise ValueError("El nombre del gestor no puede estar vacío.")
            if any(g.nombre.lower() == nombre.lower() for g in self._estado.gestores):
                raise ValueError(f"Ya existe un gestor llamado {nombre}.")
            g = Gestor(gestor_id=nombre, nombre=nombre)
            self._estado.gestores.append(g)
            return g

    def actualizar_gestor(
        self,
        nombre: str,
        estado: str | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> Gestor:
        with self._lock:
            g = next((x for x in self._estado.gestores if x.nombre == nombre), None)
            if g is None:
                raise KeyError(f"No existe el gestor {nombre}.")
            if estado is not None:
                g.estado = EstadoGestor(estado)
            if g.estado is EstadoGestor.VACACIONES:
                if desde is None or hasta is None:
                    raise ValueError("Las vacaciones requieren fecha de inicio y de fin.")
                if hasta < desde:
                    raise ValueError("La fecha de fin no puede ser anterior al inicio.")
                g.vacaciones_desde, g.vacaciones_hasta = desde, hasta
            else:
                g.vacaciones_desde = g.vacaciones_hasta = None
            return g

    def eliminar_gestor(self, nombre: str) -> None:
        with self._lock:
            self._estado.gestores = [g for g in self._estado.gestores if g.nombre != nombre]

    # ---------------------------------------------------------- tickets
    def cambiar_tipo_docente(self, ticket_id: str, nuevo_tipo: str) -> Ticket:
        with self._lock:
            t = next((x for x in self._estado.tickets if x.ticket_id == ticket_id), None)
            if t is None:
                raise KeyError(f"No existe el ticket {ticket_id}.")
            t.tipo_docente = TipoDocente(nuevo_tipo)
            # si pasa a externo, la complejidad administrativa es máxima
            if t.tipo_docente is TipoDocente.EXTERNO:
                t.observacion_raw = "CAMBIO DINÁMICO: Interno a Externo"
            return t

    def crear_ticket(self, datos: dict) -> Ticket:
        with self._lock:
            self._estado.contador_tickets += 1
            numero = 6500 + self._estado.contador_tickets
            ticket_id = f"{numero}-PNEW-26"
            grupos = int(datos.get("grupos_programados", 1))
            spg = int(datos.get("sesiones_por_grupo", 1))
            t = Ticket(
                ticket_id=ticket_id,
                estado=EstadoTicket.ABIERTO,
                prioridad=Prioridad(datos.get("prioridad", "Media")),
                modalidad=datos["modalidad"],
                evento=datos.get("evento", "Nuevo evento"),
                dependencia=datos.get("dependencia", ""),
                gestor="",
                fecha_ingreso=self._estado.hoy,
                fecha_asignacion=self._estado.hoy,
                fecha_inicio=datos.get("fecha_inicio"),
                fecha_fin=datos.get("fecha_fin"),
                tipo_docente=TipoDocente(datos.get("tipo_docente", "Interno")),
                observacion=(
                    TipoObservacion.OBLIGATORIO_TEMA_NUEVO
                    if datos.get("obligatorio")
                    else TipoObservacion.REGULAR_MUESTREO
                ),
                observacion_raw=(
                    "OBLIGATORIO - Tema Nuevo" if datos.get("obligatorio")
                    else "REGULAR - Muestreo Aleatorio"
                ),
                grupos_programados=grupos,
                sesiones_por_grupo=spg,
                total_sesiones=grupos * spg,
            )
            self._estado.tickets.append(t)
            return t

    def asignar_ticket(self, ticket_id: str, gestor: str) -> None:
        with self._lock:
            self._estado.asignacion_manual[ticket_id] = gestor
            for t in self._estado.tickets:
                if t.ticket_id == ticket_id:
                    t.gestor = gestor
                    break

    def tickets_para_optimizar(self) -> list[Ticket]:
        return [t for t in self._estado.tickets if t.estado is EstadoTicket.ABIERTO]


gestor_estado = GestorEstado()
