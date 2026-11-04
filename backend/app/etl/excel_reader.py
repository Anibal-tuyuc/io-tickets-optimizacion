"""Lector de la base de datos de prueba `Control.xlsx`.

El archivo original se abre SIEMPRE en modo lectura; nunca se sobrescribe.

Cada hoja tiene su propio encabezado desplazado, así que se describe cada una
en `SHEET_CONFIG`. Ese es el único lugar del proyecto donde aparecen los
nombres exactos de columna del Excel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd

from app.core.calendario import dias_habiles_entre, dias_habiles_excel
from app.core.config import SIMULATION_DATE, SOURCE_XLSX
from app.core.model_params import REQ_DIAS_HABILES
from app.models.domain import (
    DiagnosticoDatos,
    Docente,
    EstadoTicket,
    Gestor,
    Grupo,
    Incidencia,
    Modalidad,
    Prioridad,
    Severidad,
    Sesion,
    Ticket,
    TipoDocente,
    TipoObservacion,
)

# --------------------------------------------------------------------- config


@dataclass(frozen=True)
class SheetConfig:
    name: str
    header_row: int          # fila (1-indexed) donde están los títulos
    drop_first_col: bool = False  # Registro tiene la columna A vacía


SHEET_CONFIG: dict[str, SheetConfig] = {
    "Registro": SheetConfig("Registro", header_row=7, drop_first_col=True),
    "GestionDocente": SheetConfig("GestionDocente", header_row=7),
    "EjecucionXGrupos": SheetConfig("EjecucionXGrupos", header_row=4),
    "Sesiones": SheetConfig("Sesiones", header_row=4),
    "Docentes": SheetConfig("Docentes", header_row=4),
    "DB_Docentes": SheetConfig("DB_Docentes", header_row=1),
    "Listas": SheetConfig("Listas", header_row=1),
}

# Rango razonable de fechas. Fuera de aquí hay basura (2006, 2027).
FECHA_MIN = date(2025, 1, 1)
FECHA_MAX = date(2027, 12, 31)


# ------------------------------------------------------------------ helpers


def _es_nulo(valor: object) -> bool:
    """Detecta None, NaN y NaT (NaT es subclase de datetime y se cuela fácil)."""
    if valor is None or valor is pd.NaT:
        return True
    if isinstance(valor, float) and pd.isna(valor):
        return True
    try:
        resultado = pd.isna(valor)
    except (TypeError, ValueError):
        return False
    return bool(resultado) if isinstance(resultado, bool) else False


def _norm(texto: object) -> str:
    """Normaliza texto para comparaciones tolerantes a tildes/espacios."""
    if _es_nulo(texto):
        return ""
    return " ".join(str(texto).split()).strip()


def _to_date(valor: object) -> date | None:
    """Convierte a date aceptando datetime, date, texto y el número de serie Excel."""
    if _es_nulo(valor):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        # Serie de fechas de Excel (1900 system). 45.000 ≈ 2023. Descarta horas sueltas.
        if 20000 < float(valor) < 80000:
            try:
                return (datetime(1899, 12, 30) + pd.Timedelta(days=float(valor))).date()
            except (OverflowError, ValueError):
                return None
        return None
    texto = _norm(valor)
    if not texto:
        return None
    # Formatos vistos en la base: 2026-10-08, 6/10/26 8:57, 19/011/2026 (inválido)
    parsed = pd.to_datetime(texto, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def _to_int(valor: object, default: int = 0) -> int:
    if _es_nulo(valor):
        return default
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return default


def _to_float(valor: object) -> float | None:
    if _es_nulo(valor):
        return None
    try:
        return float(str(valor).replace(",", "").replace("Q", "").strip())
    except (TypeError, ValueError):
        return None


def _to_time(valor: object) -> time | None:
    if _es_nulo(valor):
        return None
    if isinstance(valor, time):
        return valor
    if isinstance(valor, datetime):
        return valor.time()
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        # Fracción de día de Excel
        frac = float(valor)
        if 0 <= frac < 1:
            segundos = int(round(frac * 86400))
            return time(segundos // 3600 % 24, segundos % 3600 // 60, segundos % 60)
        return None
    try:
        return time.fromisoformat(_norm(valor))
    except ValueError:
        return None


def _fecha_valida(d: date | None) -> bool:
    return d is not None and FECHA_MIN <= d <= FECHA_MAX


def _mapear_observacion(texto: str) -> TipoObservacion:
    t = texto.upper()
    if not t:
        return TipoObservacion.DESCONOCIDA
    if "DFV" in t or "RUTA B" in t:
        return TipoObservacion.RUTA_B_DFV
    if "CAMBIO" in t and "DIN" in t:
        return TipoObservacion.CAMBIO_DINAMICO
    if "REGULAR" in t or "MUESTREO" in t:
        return TipoObservacion.REGULAR_MUESTREO
    if "OBLIGATORIO" in t or "OBLIGATORIA" in t:
        if "DOCENTE NUEVO" in t:
            return TipoObservacion.OBLIGATORIO_DOCENTE_NUEVO
        if "PRIMERA VEZ" in t or "PRIMERA" in t:
            return TipoObservacion.OBLIGATORIO_PRIMERA_VEZ
        if "TEMA NUEVO" in t:
            return TipoObservacion.OBLIGATORIO_TEMA_NUEVO
    return TipoObservacion.DESCONOCIDA


def _mapear_modalidad(texto: str) -> Modalidad:
    t = texto.upper()
    if "ASINC" in t:
        return Modalidad.VIRTUAL_ASINCRONICO
    if "SINC" in t:
        return Modalidad.VIRTUAL_SINCRONICO
    if "MIXTO" in t or "MIXTA" in t:
        return Modalidad.MIXTO
    return Modalidad.PRESENCIAL


def _mapear_prioridad(texto: str) -> Prioridad:
    t = texto.upper()
    if t.startswith("URG"):
        return Prioridad.URGENTE
    if t.startswith("ALT"):
        return Prioridad.ALTA
    if t.startswith("MED"):
        return Prioridad.MEDIA
    return Prioridad.BAJA


def _mapear_tipo_docente(texto: str) -> TipoDocente:
    t = texto.upper()
    if "COOP" in t:
        return TipoDocente.COOPERANTE
    if "EXTERN" in t or "EXTERNO" in t:
        return TipoDocente.EXTERNO
    return TipoDocente.INTERNO


# ------------------------------------------------------------------- lectura


class ExcelReader:
    """Lee y normaliza las hojas del archivo de control."""

    def __init__(self, ruta: Path | str | None = None) -> None:
        self.ruta = Path(ruta or SOURCE_XLSX)
        if not self.ruta.exists():
            raise FileNotFoundError(f"No se encontró el archivo base: {self.ruta}")
        self.diagnostico = DiagnosticoDatos(archivo=str(self.ruta))

    # -------------------------------------------------------------- helpers
    def _sheet(self, archivo: pd.ExcelFile, nombre: str) -> pd.DataFrame:
        cfg = SHEET_CONFIG[nombre]
        df = pd.read_excel(archivo, sheet_name=cfg.name, header=cfg.header_row - 1)
        if cfg.drop_first_col and len(df.columns) > 0:
            df = df.iloc[:, 1:]
        df.columns = [_norm(c) for c in df.columns]
        self.diagnostico.hojas_leidas.append(nombre)
        return df

    @staticmethod
    def _col(df: pd.DataFrame, *candidatos: str) -> str | None:
        """Busca la primera columna cuyo nombre empiece por alguno de los candidatos."""
        for cand in candidatos:
            for col in df.columns:
                if col.lower().startswith(cand.lower()):
                    return col
        return None

    # ---------------------------------------------------------------- carga
    def leer(self) -> tuple[list[Ticket], list[Sesion], list[Grupo], list[Docente], list[Gestor]]:
        """Lee todas las hojas y devuelve las entidades normalizadas."""
        with pd.ExcelFile(self.ruta, engine="openpyxl") as archivo:
            reg = self._sheet(archivo, "Registro")
            ses = self._sheet(archivo, "Sesiones")
            ges = self._sheet(archivo, "GestionDocente")
            gru = self._sheet(archivo, "EjecucionXGrupos")
            doc = self._sheet(archivo, "Docentes")
            dbd = self._sheet(archivo, "DB_Docentes")

        tickets = self._leer_tickets(reg)
        self._cruzar_gestion_docente(ges, tickets)
        gestores = self._leer_gestores(tickets)
        sesiones = self._leer_sesiones(ses, tickets)
        grupos = self._leer_grupos(gru)
        docentes = self._leer_docentes(doc, dbd)

        self.diagnostico.tickets_totales = len(tickets)
        self.diagnostico.tickets_abiertos = sum(
            1 for t in tickets if t.estado is EstadoTicket.ABIERTO
        )
        self.diagnostico.sesiones_totales = len(sesiones)
        self.diagnostico.sesiones_fechadas = sum(1 for s in sesiones if s.fecha)
        self.diagnostico.grupos = len(grupos)
        self.diagnostico.docentes = len(docentes)
        return tickets, sesiones, grupos, docentes, gestores

    # -------------------------------------------------------------- tickets
    def _leer_tickets(self, df: pd.DataFrame) -> list[Ticket]:
        c_id = self._col(df, "Ticket")
        c_estado = self._col(df, "Estado")
        c_prior = self._col(df, "Prioridad")
        c_mod = self._col(df, "Tipo de evento")
        c_evento = self._col(df, "Evento Formativo")
        c_dep = self._col(df, "Dependencia")
        c_gestor = self._col(df, "Asignado a")
        c_ing = self._col(df, "Fecha de ingreso")
        c_asig = self._col(df, "Fecha de Asignaci")
        c_ini = self._col(df, "Inicio del Evento")
        c_fin = self._col(df, "Fin del Evento")
        c_tdoc = self._col(df, "Tipo docente")
        c_obs = self._col(df, "Observaciones")
        c_grp = self._col(df, "Grupos programados")
        c_spg = self._col(df, "Sesiones por grupo")
        c_tot = self._col(df, "Total de sesiones")
        c_costo = self._col(df, "Costo Docente")
        c_req = self._col(df, "Requisici")
        c_link = self._col(df, "Link del Ticket")

        faltantes = [n for n, c in [("Ticket #", c_id), ("Estado", c_estado)] if c is None]
        if faltantes:
            raise ValueError(f"Registro: faltan columnas obligatorias {faltantes}")

        hoy = date.fromisoformat(SIMULATION_DATE)
        tickets: list[Ticket] = []
        vistos: set[str] = set()

        for _, fila in df.iterrows():
            ticket_id = _norm(fila.get(c_id))
            if not ticket_id or ticket_id.upper().startswith("TICKET"):
                continue
            if ticket_id in vistos:
                self.diagnostico.agregar(
                    Incidencia(
                        tipo="ticket_duplicado",
                        gravedad="media",
                        descripcion="El ticket aparece más de una vez en el Registro.",
                        referencia=ticket_id,
                        accion_tomada="Se conserva la primera aparición.",
                    )
                )
                continue
            vistos.add(ticket_id)

            estado_txt = _norm(fila.get(c_estado)).upper()
            estado = (
                EstadoTicket.ABIERTO if estado_txt.startswith("ABIER")
                else EstadoTicket.CANCELADO if estado_txt.startswith("CANCEL")
                else EstadoTicket.RESUELTO
            )

            obs_raw = _norm(fila.get(c_obs)) if c_obs else ""
            observacion = _mapear_observacion(obs_raw)

            fecha_ini_raw = fila.get(c_ini) if c_ini else None
            fecha_fin_raw = fila.get(c_fin) if c_fin else None
            fecha_ini = _to_date(fecha_ini_raw)
            fecha_fin = _to_date(fecha_fin_raw)

            if not _es_nulo(fecha_ini_raw) and fecha_ini is None:
                self.diagnostico.agregar(
                    Incidencia(
                        tipo="fecha_invalida",
                        gravedad="media",
                        descripcion=f"Fecha de inicio no interpretable: {fecha_ini_raw!r}.",
                        referencia=ticket_id,
                        accion_tomada="Se marca el ticket como SIN_FECHA; no participa en el calendario.",
                    )
                )
            elif fecha_ini is not None and not _fecha_valida(fecha_ini):
                self.diagnostico.agregar(
                    Incidencia(
                        tipo="fecha_fuera_de_rango",
                        gravedad="media",
                        descripcion=f"Fecha de inicio fuera del horizonte 2025-2027: {fecha_ini}.",
                        referencia=ticket_id,
                        accion_tomada="Se descarta la fecha.",
                    )
                )
                fecha_ini = None
                fecha_fin = None

            fecha_ing = _to_date(fila.get(c_ing)) if c_ing else None
            fecha_asig = _to_date(fila.get(c_asig)) if c_asig else None

            if estado is EstadoTicket.ABIERTO and fecha_ini is None:
                self.diagnostico.agregar(
                    Incidencia(
                        tipo="abierto_sin_fecha",
                        gravedad="alta",
                        descripcion="Ticket abierto sin fecha de inicio: no se puede programar ni calcular plazo.",
                        referencia=ticket_id,
                        accion_tomada="Se incluye en el balance de carga pero excluido del calendario.",
                    )
                )

            tipo_docente = _mapear_tipo_docente(_norm(fila.get(c_tdoc)) if c_tdoc else "")
            req_dias = REQ_DIAS_HABILES[tipo_docente.value]

            dias_hab: int | None = None
            dias_hab_totales: int | None = None
            dias_hab_totales_correcto: int | None = None
            severidad = Severidad.SIN_FECHA
            if fecha_ini is not None:
                dias_hab = dias_habiles_entre(hoy, fecha_ini)
                if fecha_asig is not None:
                    # Método del Excel (auditable) y método correcto (con asuetos):
                    dias_hab_totales = dias_habiles_excel(fecha_asig, fecha_ini)
                    dias_hab_totales_correcto = dias_habiles_entre(fecha_asig, fecha_ini)
                severidad = self._severidad(dias_hab, req_dias)

            dias_abiertos = (
                max(0, (hoy - fecha_ing).days) if fecha_ing is not None else 0
            )

            tickets.append(
                Ticket(
                    ticket_id=ticket_id,
                    estado=estado,
                    prioridad=_mapear_prioridad(_norm(fila.get(c_prior)) if c_prior else ""),
                    modalidad=_mapear_modalidad(_norm(fila.get(c_mod)) if c_mod else ""),
                    evento=_norm(fila.get(c_evento)) if c_evento else "",
                    dependencia=_norm(fila.get(c_dep)) if c_dep else "",
                    gestor=_norm(fila.get(c_gestor)) if c_gestor else "",
                    fecha_ingreso=fecha_ing,
                    fecha_asignacion=fecha_asig,
                    fecha_inicio=fecha_ini,
                    fecha_fin=fecha_fin,
                    tipo_docente=tipo_docente,
                    observacion=observacion,
                    observacion_raw=obs_raw,
                    grupos_programados=_to_int(fila.get(c_grp)) if c_grp else 0,
                    sesiones_por_grupo=_to_int(fila.get(c_spg)) if c_spg else 0,
                    total_sesiones=_to_int(fila.get(c_tot)) if c_tot else 0,
                    costo_docente=_to_float(fila.get(c_costo)) if c_costo else None,
                    requisicion=_norm(fila.get(c_req)) if c_req else None,
                    link=_norm(fila.get(c_link)) if c_link else None,
                    dias_abiertos=dias_abiertos,
                    req_dias_habiles=req_dias,
                    dias_habiles_totales=dias_hab_totales,
                    dias_habiles_totales_correcto=dias_hab_totales_correcto,
                    dias_habiles_restantes=dias_hab,
                    severidad=severidad,
                )
            )

        # Tickets legados: abiertos desde antes del horizonte de gestión.
        for t in tickets:
            if (
                t.estado is EstadoTicket.ABIERTO
                and t.fecha_ingreso is not None
                and t.fecha_ingreso.year < 2026
            ):
                self.diagnostico.agregar(
                    Incidencia(
                        tipo="ticket_legado",
                        gravedad="baja",
                        descripcion=f"Ticket abierto desde {t.fecha_ingreso}: posible registro histórico no depurado.",
                        referencia=t.ticket_id,
                        accion_tomada="Se incluye, marcado para revisión.",
                    )
                )
        return tickets

    def _cruzar_gestion_docente(
        self, df: pd.DataFrame, tickets: list[Ticket]
    ) -> None:
        """Contrasta la hoja GestionDocente contra el Registro.

        Detecta inconsistencias entre hojas (fechas de inicio distintas, años
        mal tecleados) que de otro modo pasarían desapercibidas.
        """
        c_ticket = self._col(df, "Ticket")
        c_asig = self._col(df, "Fecha de asignaci")
        c_ini = self._col(df, "Fecha de inicio")
        c_dias = self._col(df, "Dias h")
        if not c_ticket:
            return

        indice = {t.ticket_id: t for t in tickets}
        for _, fila in df.iterrows():
            tid = _norm(fila.get(c_ticket))
            ticket = indice.get(tid)
            if ticket is None:
                continue

            ini_hoja = _to_date(fila.get(c_ini)) if c_ini else None
            if (
                ini_hoja is not None
                and ticket.fecha_inicio is not None
                and ini_hoja != ticket.fecha_inicio
            ):
                self.diagnostico.agregar(
                    Incidencia(
                        tipo="inconsistencia_entre_hojas",
                        gravedad="media",
                        descripcion=(
                            f"Fecha de inicio difiere: Registro={ticket.fecha_inicio} "
                            f"vs GestionDocente={ini_hoja}."
                        ),
                        referencia=tid,
                        accion_tomada="Se usa la del Registro como fuente de verdad.",
                    )
                )

            asig_hoja = _to_date(fila.get(c_asig)) if c_asig else None
            if asig_hoja is not None and asig_hoja.year not in (2025, 2026, 2027):
                self.diagnostico.agregar(
                    Incidencia(
                        tipo="fecha_imposible",
                        gravedad="alta",
                        descripcion=f"Fecha de asignación imposible: {asig_hoja}.",
                        referencia=tid,
                        accion_tomada="Se ignora la fecha y se reporta para corrección manual.",
                    )
                )

            dias_hoja = _to_int(fila.get(c_dias), default=-1) if c_dias else -1
            if dias_hoja >= 0 and ticket.dias_habiles_totales is not None:
                if dias_hoja != ticket.dias_habiles_totales:
                    self.diagnostico.agregar(
                        Incidencia(
                            tipo="dias_habiles_discrepantes",
                            gravedad="baja",
                            descripcion=(
                                f"GestionDocente registra {dias_hoja} días hábiles; "
                                f"recalculado {ticket.dias_habiles_totales}. "
                                "Causado por fechas inconsistentes entre hojas."
                            ),
                            referencia=tid,
                            accion_tomada="Prevalece el recálculo desde el Registro.",
                        )
                    )

    @staticmethod
    def _severidad(dias_hab: int, req: int) -> Severidad:
        if dias_hab < req:
            return Severidad.ROJO
        holgura = dias_hab - req
        if holgura <= max(2, int(req * 0.25)):
            return Severidad.AMBAR
        return Severidad.VERDE

    # ------------------------------------------------------------- gestores
    def _leer_gestores(self, tickets: list[Ticket]) -> list[Gestor]:
        nombres = sorted({t.gestor for t in tickets if t.gestor})
        return [Gestor(gestor_id=n, nombre=n) for n in nombres]

    # ------------------------------------------------------------- sesiones
    def _leer_sesiones(self, df: pd.DataFrame, tickets: list[Ticket]) -> list[Sesion]:
        c_ticket = self._col(df, "No. Solicitud")
        c_grupo = self._col(df, "Grupo")
        c_sesion = self._col(df, "Sesi")
        c_fecha = self._col(df, "Fecha")
        c_ini = self._col(df, "Hora de inicio")
        c_fin = self._col(df, "Hora de fin")
        c_cod = self._col(df, "Codigo")
        c_obs = self._col(df, "Observaciones")

        indice = {t.ticket_id: t for t in tickets}
        sesiones: list[Sesion] = []
        sin_fecha = 0
        invalidas = 0

        for _, fila in df.iterrows():
            ticket_id = _norm(fila.get(c_ticket)) if c_ticket else ""
            if not ticket_id:
                continue
            grupo = _to_int(fila.get(c_grupo)) if c_grupo else 0
            num = _to_int(fila.get(c_sesion)) if c_sesion else 0
            fecha_raw = fila.get(c_fecha) if c_fecha else None
            fecha = _to_date(fecha_raw)

            if fecha is None:
                sin_fecha += 1
                if fecha_raw not in (None, "") and _norm(fecha_raw):
                    invalidas += 1
                    self.diagnostico.agregar(
                        Incidencia(
                            tipo="sesion_fecha_invalida",
                            gravedad="media",
                            descripcion=f"Sesión con fecha no interpretable: {_norm(fecha_raw)!r}.",
                            referencia=f"{ticket_id} g{grupo} s{num}",
                            accion_tomada="La sesión se conserva sin fecha; no entra al calendario.",
                        )
                    )
                continue

            if not _fecha_valida(fecha):
                invalidas += 1
                continue

            ticket = indice.get(ticket_id)
            sesiones.append(
                Sesion(
                    # La fecha forma parte de la clave: hay sesiones reprogramadas
                    # que comparten ticket/grupo/número pero ocurren en días
                    # distintos. Sin la fecha, ambas colapsan en una sola.
                    sesion_id=f"{ticket_id}|g{grupo}|s{num}|{fecha.isoformat()}",
                    ticket_id=ticket_id,
                    grupo=grupo,
                    numero_sesion=num,
                    fecha=fecha,
                    hora_inicio=_to_time(fila.get(c_ini)) if c_ini else None,
                    hora_fin=_to_time(fila.get(c_fin)) if c_fin else None,
                    codigo=_norm(fila.get(c_cod)) or None if c_cod else None,
                    gestor=ticket.gestor if ticket else "",
                    modalidad=ticket.modalidad if ticket else None,
                    obligatoria=(
                        ticket.requiere_supervision_obligatoria if ticket else False
                    ),
                    observacion_raw=ticket.observacion_raw if ticket else "",
                )
            )

        # Sesiones reprogramadas: misma clave lógica con otra fecha
        claves = [(s.ticket_id, s.grupo, s.numero_sesion) for s in sesiones]
        repetidas = {k for k in claves if claves.count(k) > 1}
        for k in sorted(repetidas):
            self.diagnostico.agregar(
                Incidencia(
                    tipo="sesion_reprogramada",
                    gravedad="baja",
                    descripcion=(
                        "La sesión aparece con más de una fecha (reprogramación o "
                        "registro duplicado)."
                    ),
                    referencia=f"{k[0]} g{k[1]} s{k[2]}",
                    accion_tomada="Se tratan como sesiones distintas, una por fecha.",
                )
            )

        if sin_fecha:
            self.diagnostico.agregar(
                Incidencia(
                    tipo="sesiones_sin_fecha",
                    gravedad="baja",
                    descripcion=f"{sin_fecha} sesiones sin fecha (modalidades asincrónicas o datos pendientes).",
                    accion_tomada="Excluidas del calendario de supervisión.",
                )
            )
        return sesiones

    # --------------------------------------------------------------- grupos
    def _leer_grupos(self, df: pd.DataFrame) -> list[Grupo]:
        c_ticket = self._col(df, "No. Solicitud")
        c_gestor = self._col(df, "Asignado a")
        c_grupo = self._col(df, "Grupo")
        c_ini = self._col(df, "Fecha Inicio")
        c_fin = self._col(df, "Fecha Fin")
        c_estado = self._col(df, "Estado")
        c_nomb = self._col(df, "Nombramiento")
        c_sol = self._col(df, "Cantidad de Participantes solicit")
        c_nom = self._col(df, "Cantidad de Participantes nombrad")
        c_evento = self._col(df, "Evento Formativo")

        out: list[Grupo] = []
        for _, fila in df.iterrows():
            ticket_id = _norm(fila.get(c_ticket)) if c_ticket else ""
            if not ticket_id:
                continue
            out.append(
                Grupo(
                    ticket_id=ticket_id,
                    grupo=_to_int(fila.get(c_grupo)) if c_grupo else 0,
                    gestor=_norm(fila.get(c_gestor)) if c_gestor else "",
                    fecha_inicio=_to_date(fila.get(c_ini)) if c_ini else None,
                    fecha_fin=_to_date(fila.get(c_fin)) if c_fin else None,
                    estado=_norm(fila.get(c_estado)) if c_estado else "",
                    nombramiento=_norm(fila.get(c_nomb)) or None if c_nomb else None,
                    participantes_solicitados=_to_int(fila.get(c_sol)) if c_sol else None,
                    participantes_nombrados=_to_int(fila.get(c_nom)) if c_nom else None,
                    evento=_norm(fila.get(c_evento)) if c_evento else "",
                )
            )
        return out

    # ------------------------------------------------------------- docentes
    def _leer_docentes(self, df: pd.DataFrame, dbd: pd.DataFrame) -> list[Docente]:
        c_ticket = self._col(df, "No. Solicitud")
        c_doc = self._col(df, "Docente")
        c_id = self._col(df, "NIT/DPI")
        c_horas = self._col(df, "Horas de docencia")
        c_grupo = self._col(df, "Grupo")
        c_ses = self._col(df, "Sesiones")

        # catálogo de tipo de docente
        c_dbd_nit = self._col(dbd, "NIT docente")
        c_dbd_tipo = self._col(dbd, "Interno / Externo")
        catalogo: dict[str, str] = {}
        if c_dbd_nit and c_dbd_tipo:
            for _, fila in dbd.iterrows():
                nit = _norm(fila.get(c_dbd_nit))
                if nit:
                    catalogo[nit] = _norm(fila.get(c_dbd_tipo))

        out: list[Docente] = []
        for _, fila in df.iterrows():
            ticket_id = _norm(fila.get(c_ticket)) if c_ticket else ""
            nombre = _norm(fila.get(c_doc)) if c_doc else ""
            if not ticket_id or not nombre:
                continue
            ident = _norm(fila.get(c_id)) or None if c_id else None
            tipo_txt = catalogo.get(ident or "", "").upper()
            tipo = (
                "Externo" if "EXTERN" in tipo_txt
                else "Interno" if "INTERN" in tipo_txt
                else None
            )
            out.append(
                Docente(
                    ticket_id=ticket_id,
                    docente=nombre,
                    identificacion=ident,
                    horas=_to_float(fila.get(c_horas)) if c_horas else None,
                    grupo=_to_int(fila.get(c_grupo)) or None if c_grupo else None,
                    sesiones=_to_int(fila.get(c_ses)) or None if c_ses else None,
                    tipo=tipo,
                )
            )
        return out
