"""Parámetros del modelo de Investigación de Operaciones.

Estos valores están alineados con la sección 3 del PLAN_TRABAJO.md y con la
formulación del informe. Cambiarlos aquí cambia el comportamiento del motor
completo; no hay constantes de negocio dispersas en el código.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ----------------------------------------------------------- regla 2: docentes
PESO_DOCENTE: dict[str, float] = {
    "Interno": 1.0,
    "Cooperante": 1.8,
    "Externo": 3.5,
}

# Días hábiles mínimos requeridos antes del inicio del evento.
# Se toma el extremo ALTO del rango sugerido (conservador: si cabe con el
# extremo alto, cabe con el bajo).
REQ_DIAS_HABILES: dict[str, int] = {
    "Interno": 8,       # 5 a 8 días hábiles
    "Cooperante": 15,   # 10 a 15 días hábiles
    "Externo": 30,      # 20 a 30 días hábiles
}

# ------------------------------------------------------- regla 3: modalidades
FACTOR_MODALIDAD: dict[str, float] = {
    "Presencial": 1.00,
    "Mixto": 1.10,
    "Virtual Sincrónico": 0.90,
    "Virtual Asincrónico": 0.12,  # Ruta B: traslado a DFV, casi sin carga operativa
}

MODALIDADES_RUTA_A = ("Presencial", "Virtual Sincrónico", "Mixto")
MODALIDAD_RUTA_B = "Virtual Asincrónico"

# ------------------------------------------------------- regla 5: prioridades
# Mayor peso = se atiende antes (se usa en el criterio de antigüedad).
PESO_PRIORIDAD: dict[str, float] = {
    "Urgente": 4.0,
    "Alta": 2.5,
    "Media": 1.5,
    "Baja": 1.0,
}

# Días abiertos tolerados antes de penalizar por antigüedad.
SLO_DIAS_POR_PRIORIDAD: dict[str, int] = {
    "Urgente": 2,
    "Alta": 5,
    "Media": 10,
    "Baja": 20,
}

# Orden canónico para desempates.
ORDEN_PRIORIDAD = ("Urgente", "Alta", "Media", "Baja")

# ------------------------------------------------------------- regla 4: muestreo
THETA_MUESTREO_DEFAULT = 0.25  # 25% mínimo de sesiones regulares
THETA_MUESTREO_MIN = 0.0
THETA_MUESTREO_MAX = 1.0

# -------------------------------------------------- pesos de la función objetivo
W_EQUIDAD = 1.0        # w1: minimizar (C_max - C_min)
W_PLAZO = 3.0          # w2: penalizar retraso respecto a la fecha de inicio
W_DIA_SATURADO = 50.0  # w3: penalizar días donde no alcanzan los gestores
W_ANTIGUEDAD = 0.8     # w4: penalizar tickets viejos sin atender


@dataclass(frozen=True)
class PesosCarga:
    """Coeficientes de la fórmula de carga ponderada W_i."""

    alpha_docente: float = 0.60
    beta_sesiones: float = 0.35
    gamma_participantes: float = 0.05

    def validar(self) -> None:
        for nombre, valor in (
            ("alpha_docente", self.alpha_docente),
            ("beta_sesiones", self.beta_sesiones),
            ("gamma_participantes", self.gamma_participantes),
        ):
            if valor < 0:
                raise ValueError(f"{nombre} no puede ser negativo (recibido {valor})")


@dataclass(frozen=True)
class ParametrosOptimizacion:
    """Parámetros ajustables desde la UI en tiempo de ejecución."""

    theta_muestreo: float = THETA_MUESTREO_DEFAULT
    semilla: int = 20261008
    pesos_carga: PesosCarga = field(default_factory=PesosCarga)
    w_equidad: float = W_EQUIDAD
    w_plazo: float = W_PLAZO
    w_dia_saturado: float = W_DIA_SATURADO
    w_antiguedad: float = W_ANTIGUEDAD

    def validar(self) -> None:
        if not (THETA_MUESTREO_MIN <= self.theta_muestreo <= THETA_MUESTREO_MAX):
            raise ValueError(
                f"theta_muestreo debe estar en [0, 1] (recibido {self.theta_muestreo})"
            )
        self.pesos_carga.validar()
