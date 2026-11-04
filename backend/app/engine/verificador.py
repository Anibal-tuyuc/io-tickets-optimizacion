"""Verificador independiente del calendario de supervisión.

REGLA DE ORO DEL PROYECTO: este módulo NUNCA importa el solver.

El solver construye un plan; este módulo, escrito por separado y sin conocer el
modelo, recibe el plan y lista cada violación. Si el solver tuviera un error de
modelado (por ejemplo, olvidar que una sesión solo puede supervisarse el día en
que realmente ocurre), el verificador lo detecta en lugar de confirmarlo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.domain import Dataset, EstadoTicket, Sesion, Ticket


@dataclass(slots=True)
class PlanSupervision:
    """Resultado del calendario: qué sesión supervisa quién y en qué día."""

    # (gestor, fecha ISO) -> lista de sesion_id
    asignaciones: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    # sesiones que quedaron sin cobertura y por qué
    sin_cobertura: dict[str, str] = field(default_factory=dict)
    # días con más sesiones obligatorias que gestores disponibles
    dias_saturados: dict[str, list[str]] = field(default_factory=dict)
    # días en que se recurrió a un gestor de apoyo (no dueño del ticket)
    apoyos: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Violacion:
    regla: str
    detalle: str
    severidad: str = "alta"

    def __str__(self) -> str:
        return f"[{self.regla}] {self.detalle}"


@dataclass(slots=True)
class ReporteVerificacion:
    violaciones: list[Violacion] = field(default_factory=list)
    sesiones_esperadas: int = 0
    sesiones_cubiertas: int = 0
    sesiones_obligatorias: int = 0
    obligatorias_cubiertas: int = 0
    regulares_totales: int = 0
    regulares_cubiertas: int = 0
    dias_con_colision: int = 0
    detalle_colisiones: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violaciones

    @property
    def cobertura_pct(self) -> float:
        if not self.sesiones_esperadas:
            return 0.0
        return round(self.sesiones_cubiertas / self.sesiones_esperadas * 100, 2)

    def resumen(self) -> dict:
        return {
            "ok": self.ok,
            "violaciones": len(self.violaciones),
            "sesiones_esperadas": self.sesiones_esperadas,
            "sesiones_cubiertas": self.sesiones_cubiertas,
            "sesiones_obligatorias": self.sesiones_obligatorias,
            "obligatorias_cubiertas": self.obligatorias_cubiertas,
            "regulares_totales": self.regulares_totales,
            "regulares_cubiertas": self.regulares_cubiertas,
            "cobertura_pct": self.cobertura_pct,
            "dias_con_colision": self.dias_con_colision,
            "detalle_colisiones": self.detalle_colisiones[:20],
            "detalle_violaciones": [str(v) for v in self.violaciones[:20]],
        }


class VerificadorCalendario:
    """Comprueba un plan contra las reglas duras de la Regla 4."""

    def __init__(self, ds: Dataset, theta_minimo: float = 0.25) -> None:
        self.ds = ds
        self.theta_minimo = theta_minimo
        self.sesiones: dict[str, Sesion] = {s.sesion_id: s for s in ds.sesiones}
        self.tickets: dict[str, Ticket] = {t.ticket_id: t for t in ds.tickets}

    # ------------------------------------------------------------------ API
    def verificar(
        self,
        plan: PlanSupervision,
        sesiones_esperadas: set[str] | None = None,
    ) -> ReporteVerificacion:
        """Valida el plan.

        `sesiones_esperadas` es el universo que el plan *debía* cubrir. Si no se
        pasa, se usa el de las sesiones de tickets abiertos en Ruta A.
        """
        rep = ReporteVerificacion()
        esperadas = sesiones_esperadas if sesiones_esperadas is not None else self._universo_esperado()

        rep.sesiones_esperadas = len(esperadas)
        obligatorias = {s for s in esperadas if self.sesiones[s].obligatoria}
        regulares = esperadas - obligatorias
        rep.sesiones_obligatorias = len(obligatorias)
        rep.regulares_totales = len(regulares)

        # 1. índice inverso: sesión -> (gestor, fecha)
        cubierta: dict[str, tuple[str, str]] = {}
        for (gestor, fecha_iso), lista in plan.asignaciones.items():
            for sid in lista:
                if sid in cubierta:
                    rep.violaciones.append(
                        Violacion(
                            "sesion_duplicada",
                            f"La sesión {sid} fue asignada más de una vez "
                            f"(ya estaba con {cubierta[sid][0]}).",
                        )
                    )
                cubierta[sid] = (gestor, fecha_iso)

        # 2. cobertura de obligatorias
        faltan_ob = obligatorias - set(cubierta)
        for sid in sorted(faltan_ob):
            razón = plan.sin_cobertura.get(sid, "sin asignación")
            rep.violaciones.append(
                Violacion(
                    "obligatoria_no_cubierta",
                    f"Sesión obligatoria {sid} sin supervisión ({razón}).",
                )
            )

        # 3. muestreo mínimo de regulares, por gestor dueño del ticket
        theta_ok = self._verificar_muestreo(regulares, cubierta, plan)
        rep.violaciones.extend(theta_ok)

        # 4. día correcto: una sesión solo puede cubrirse en su fecha real
        for sid, (gestor, fecha_iso) in cubierta.items():
            sesion = self.sesiones.get(sid)
            if sesion is None:
                rep.violaciones.append(
                    Violacion("sesion_inexistente", f"{sid} no existe en el dataset.")
                )
                continue
            try:
                misma_fecha = sesion.fecha.isoformat() == fecha_iso
            except (AttributeError, ValueError):
                misma_fecha = False
            if not misma_fecha:
                rep.violaciones.append(
                    Violacion(
                        "fecha_incorrecta",
                        f"{sid} agendada el {fecha_iso} pero ocurre el {sesion.fecha}.",
                    )
                )
            if sesion.modalidad is not None and sesion.modalidad.value == "Virtual Asincrónico":
                rep.violaciones.append(
                    Violacion(
                        "ruta_b_supervisada",
                        f"{sid} pertenece a Ruta B (DFV) y no debe supervisarse.",
                    )
                )

        # 5. una sesión por gestor por día (regla dura)
        por_gestor_dia: dict[tuple[str, str], list[str]] = {}
        for (gestor, fecha_iso), lista in plan.asignaciones.items():
            por_gestor_dia.setdefault((gestor, fecha_iso), []).extend(lista)

        for (gestor, fecha_iso), lista in sorted(por_gestor_dia.items()):
            if len(lista) > 1:
                rep.dias_con_colision += 1
                detalle = (
                    f"{fecha_iso} — {gestor} tiene {len(lista)} sesiones: "
                    + ", ".join(sorted(lista))
                )
                rep.detalle_colisiones.append(detalle)
                rep.violaciones.append(Violacion("colision_diaria", detalle))

        # 6. gestor inhabilitado no puede supervisar
        for gestor, fecha_iso in por_gestor_dia:
            g = next((x for x in self.ds.gestores if x.nombre == gestor), None)
            if g is None:
                continue
            from datetime import date as _date

            if not g.disponible_en(_date.fromisoformat(fecha_iso)):
                rep.violaciones.append(
                    Violacion(
                        "gestor_no_disponible",
                        f"{gestor} está en {g.estado.value} y tiene sesiones el {fecha_iso}.",
                    )
                )

        # 7. solo el gestor dueño del ticket, salvo apoyo declarado
        for sid, (gestor, fecha_iso) in cubierta.items():
            sesion = self.sesiones.get(sid)
            if sesion is None:
                continue
            if sesion.gestor and sesion.gestor != gestor and sid not in plan.apoyos:
                rep.violaciones.append(
                    Violacion(
                        "gestor_ajeno_sin_apoyo",
                        f"{sid} pertenece a {sesion.gestor} pero la cubre {gestor} "
                        "sin registrarse como apoyo.",
                    )
                )

        # 8. métricas
        rep.sesiones_cubiertas = len(set(cubierta) & esperadas)
        rep.obligatorias_cubiertas = len(obligatorias & set(cubierta))
        rep.regulares_cubiertas = len(regulares & set(cubierta))
        return rep

    # ------------------------------------------------------------- internos
    def _universo_esperado(self) -> set[str]:
        """Sesiones que exigen supervisión: tickets abiertos de Ruta A."""
        abiertos = {
            t.ticket_id
            for t in self.ds.tickets
            if t.estado is EstadoTicket.ABIERTO
        }
        return {
            s.sesion_id
            for s in self.ds.sesiones
            if s.ticket_id in abiertos and s.modalidad is not None
            and s.modalidad.value != "Virtual Asincrónico"
        }

    def _verificar_muestreo(
        self,
        regulares: set[str],
        cubierta: dict[str, tuple[str, str]],
        plan: PlanSupervision,
    ) -> list[Violacion]:
        """El muestreo se exige por gestor dueño, no en agregado global.

        La restricción del enunciado sumaba sobre todos los gestores, lo que la
        vuelve trivialmente satisfacible. Aquí se verifica por gestor.
        """
        out: list[Violacion] = []
        por_gestor: dict[str, int] = {}
        cubiertas_por_gestor: dict[str, int] = {}

        for sid in regulares:
            sesion = self.sesiones[sid]
            dueño = sesion.gestor
            por_gestor[dueño] = por_gestor.get(dueño, 0) + 1
            if sid in cubierta:
                cubiertas_por_gestor[dueño] = cubiertas_por_gestor.get(dueño, 0) + 1

        # Un gestor sin sesiones regulares no tiene exigencia de muestreo.

        theta = self.theta_minimo
        for gestor, total in por_gestor.items():
            # ceil(theta * total) sin errores de coma flotante
            minimo = int(theta * total + 0.999999)
            cubiertas = cubiertas_por_gestor.get(gestor, 0)
            if cubiertas < minimo:
                out.append(
                    Violacion(
                        "muestreo_insuficiente",
                        f"{gestor}: {cubiertas} de {total} sesiones regulares cubiertas "
                        f"(mínimo {minimo} al 25%).",
                        severidad="media",
                    )
                )
        return out
