"""Pruebas de la ingesta: estructura, integridad y auditoría de datos."""

from __future__ import annotations

from datetime import date

from app.core.calendario import dias_habiles_entre, dias_habiles_excel
from app.models.domain import EstadoTicket, Modalidad, TipoDocente


def test_carga_completa(ds):
    assert len(ds.tickets) == 112
    assert len(ds.tickets_abiertos) == 44
    assert len(ds.sesiones) == 361
    assert len(ds.gestores) == 5
    assert len(ds.grupos) == 334


def test_ids_de_sesion_unicos(ds):
    ids = [s.sesion_id for s in ds.sesiones]
    assert len(ids) == len(set(ids)), "Hay sesiones con el mismo identificador."


def test_todo_ticket_tiene_gestor(ds):
    assert all(t.gestor for t in ds.tickets)


def test_estados_validos(ds):
    assert all(isinstance(t.estado, EstadoTicket) for t in ds.tickets)
    assert all(isinstance(t.modalidad, Modalidad) for t in ds.tickets)
    assert all(isinstance(t.tipo_docente, TipoDocente) for t in ds.tickets)


def test_observaciones_clasificadas(ds):
    desdeñadas = [t for t in ds.tickets if t.observacion.value == "DESCONOCIDA"]
    assert not desdeñadas, f"Tickets sin clasificar: {[t.ticket_id for t in desdeñadas]}"


def test_categorias_de_observacion(ds):
    """Las seis categorías del Excel deben clasificarse y todas aparecer."""
    from collections import Counter

    from app.models.domain import TipoObservacion

    c = Counter(t.observacion for t in ds.tickets)
    assert sum(v for k, v in c.items() if k.es_obligatoria) > 0
    assert c[TipoObservacion.RUTA_B_DFV] > 0
    assert c[TipoObservacion.REGULAR_MUESTREO] > 0
    assert c[TipoObservacion.CAMBIO_DINAMICO] > 0
    # los tres criterios de obligatoriedad están representados
    assert c[TipoObservacion.OBLIGATORIO_DOCENTE_NUEVO] > 0
    assert c[TipoObservacion.OBLIGATORIO_PRIMERA_VEZ] > 0
    assert c[TipoObservacion.OBLIGATORIO_TEMA_NUEVO] > 0


def test_sesiones_heredan_gestor_y_modalidad(ds):
    """La hoja Sesiones no trae gestor: debe venir del cruce con Registro."""
    con_gestor = [s for s in ds.sesiones if s.gestor]
    assert len(con_gestor) == len(ds.sesiones)
    assert all(s.modalidad is not None for s in ds.sesiones)


def test_obligatoriedad_coherente(ds):
    tickets = ds.tickets_por_id
    for s in ds.sesiones:
        t = tickets[s.ticket_id]
        assert s.obligatoria == t.requiere_supervision_obligatoria


def test_incidencias_detectadas(ds):
    tipos = {i.tipo for i in ds.diagnostico.incidencias}
    # La base real trae estos defectos; el ETL debe reportarlos, no ocultarlos.
    assert "sesion_fecha_invalida" in tipos
    assert "abierto_sin_fecha" in tipos
    assert "ticket_duplicado" in tipos
    assert "sesion_reprogramada" in tipos
    assert "inconsistencia_entre_hojas" in tipos


def test_ninguna_fecha_fuera_de_rango(ds):
    for t in ds.tickets:
        if t.fecha_inicio:
            assert date(2025, 1, 1) <= t.fecha_inicio <= date(2027, 12, 31)


def test_dias_habiles_con_asueto():
    # 20 de octubre de 2026 es Día de la Revolución en Guatemala.
    assert dias_habiles_entre(date(2026, 10, 19), date(2026, 10, 21)) == 1
    # El método del Excel no descuenta asuetos.
    assert dias_habiles_excel(date(2026, 10, 19), date(2026, 10, 21)) == 3


def test_dias_habiles_negativos():
    # Hacia atrás desde el 20-oct: 19, 16, 15, 14, 13, 12 -> 6 hábiles
    # (el 20 es asueto y no se cuenta; el 10 y 11 son fin de semana).
    assert dias_habiles_entre(date(2026, 10, 20), date(2026, 10, 10)) == -6
