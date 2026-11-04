from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import EstadoRecursos, GestorIn, VacacionesIn
from app.services.orquestador import Orquestador
from app.services.state import gestor_estado

router = APIRouter(prefix="/recursos", tags=["recursos"])


@router.get("", response_model=EstadoRecursos)
def estado_recursos() -> dict:
    return Orquestador(gestor_estado.get()).recursos()


@router.post("")
def agregar_gestor(datos: GestorIn) -> dict:
    """Alta de un gestor (Regla 1: contratación de un 6.º o 7.º gestor)."""
    try:
        g = gestor_estado.agregar_gestor(datos.nombre)
        if datos.estado != "Activo":
            gestor_estado.actualizar_gestor(
                g.nombre, datos.estado, datos.vacaciones_desde, datos.vacaciones_hasta
            )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Orquestador(gestor_estado.get()).recursos()


@router.patch("/{nombre}")
def actualizar_gestor(nombre: str, datos: GestorIn) -> dict:
    try:
        gestor_estado.actualizar_gestor(
            nombre,
            datos.estado if datos.estado else None,
            datos.vacaciones_desde,
            datos.vacaciones_hasta,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Orquestador(gestor_estado.get()).recursos()


@router.post("/vacaciones")
def registrar_vacaciones(datos: VacacionesIn) -> dict:
    """Baja temporal: bloquea al gestor y habilita el rebalanceo."""
    try:
        gestor_estado.actualizar_gestor(datos.gestor, "Vacaciones", datos.desde, datos.hasta)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Orquestador(gestor_estado.get()).recursos()


@router.delete("/{nombre}")
def desactivar_gestor(nombre: str) -> dict:
    try:
        gestor_estado.actualizar_gestor(nombre, "Inactivo")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Orquestador(gestor_estado.get()).recursos()
