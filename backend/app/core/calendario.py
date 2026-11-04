"""Calendario de días hábiles de Guatemala.

Replica el NETWORKDAYS del Excel original: lunes a viernes, excluyendo asuetos.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

import holidays as holidays_lib

_PAIS = "GT"


@lru_cache(maxsize=8)
def _asueto_set(years: tuple[int, ...]) -> frozenset[date]:
    feriados = holidays_lib.country_holidays(_PAIS, years=list(years))
    return frozenset(feriados.keys())


def es_habil(dia: date) -> bool:
    if dia.weekday() >= 5:  # sábado=5, domingo=6
        return False
    return dia not in _asueto_set((dia.year,))


def dias_habiles_entre(desde: date, hasta: date) -> int:
    """Días hábiles en el intervalo (desde, hasta].

    Equivale a NETWORKDAYS(desde, hasta) - 1, es decir, cuenta los días
    disponibles *antes* del inicio del evento. Si `hasta` es anterior a `desde`
    devuelve un número negativo, igual que el NETWORKDAYS del Excel cuando la
    fecha de inicio ya pasó.
    """
    if desde == hasta:
        return 0

    signo = 1
    a, b = desde, hasta
    if b < a:
        signo = -1
        a, b = b, a

    total = 0
    cursor = a + timedelta(days=1) if signo == 1 else a
    fin = b
    while cursor <= fin:
        if es_habil(cursor):
            total += 1
        cursor += timedelta(days=1)
    return total * signo


def dias_habiles_desde_hoy(hasta: date, hoy: date) -> int:
    """Azúcar sintáctico para el cálculo de plazo: hábiles de hoy a `hasta`."""
    return dias_habiles_entre(hoy, hasta)


def rango_habil(desde: date, hasta: date) -> list[date]:
    """Lista de días hábiles cerrados en [desde, hasta]."""
    out: list[date] = []
    cursor = desde
    while cursor <= hasta:
        if es_habil(cursor):
            out.append(cursor)
        cursor += timedelta(days=1)
    return out


# --------------------------------------------------------- compatibilidad Excel


def dias_habiles_excel(desde: date, hasta: date) -> int:
    """Réplica exacta del cálculo de la hoja `GestionDocente`.

    La hoja no usa NETWORKDAYS real: cuenta **lunes a viernes incluyendo ambos
    extremos** y **no descuenta asuetos**. Se verificó contra las 106 filas del
    archivo (104 coinciden; las 2 restantes tienen fechas invertidas en origen).

    Se conserva para poder auditar contra el archivo original. El modelo usa
    `dias_habiles_entre` (con asuetos), que es la definición correcta.
    """
    if hasta == desde:
        return 1
    if hasta < desde:
        return -dias_habiles_excel(hasta, desde)

    total = 0
    cursor = desde
    while cursor <= hasta:
        if cursor.weekday() < 5:
            total += 1
        cursor += timedelta(days=1)
    return total
