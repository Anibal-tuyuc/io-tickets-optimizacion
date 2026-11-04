/** Cliente de la API.
 *
 *  - Desarrollo: Vite hace proxy de `/api` -> http://127.0.0.1:8000
 *  - Producción (Docker): el backend sirve la SPA y la API en la misma raíz,
 *    así que `VITE_API_BASE` se compila como cadena vacía.
 */
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiError extends Error {
  status: number;
  constructor(mensaje: string, status: number) {
    super(mensaje);
    this.status = status;
  }
}

async function peticion<T>(
  ruta: string,
  opciones: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${ruta}`, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  if (!res.ok) {
    let detalle = `Error ${res.status}`;
    try {
      const cuerpo = await res.json();
      detalle = typeof cuerpo.detail === "string" ? cuerpo.detail : JSON.stringify(cuerpo.detail);
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(detalle, res.status);
  }
  return res.json() as Promise<T>;
}

const post = <T>(ruta: string, cuerpo?: unknown) =>
  peticion<T>(ruta, { method: "POST", body: cuerpo ? JSON.stringify(cuerpo) : undefined });
const patch = <T>(ruta: string, cuerpo: unknown) =>
  peticion<T>(ruta, { method: "PATCH", body: JSON.stringify(cuerpo) });
const del = <T>(ruta: string) => peticion<T>(ruta, { method: "DELETE" });

// ------------------------------------------------------------------ tipos
export type Severidad = "VERDE" | "AMBAR" | "ROJO" | "SIN_FECHA";

export interface GestorEstado {
  nombre: string;
  estado: "Activo" | "Vacaciones" | "Inactivo";
  vacaciones_desde: string | null;
  vacaciones_hasta: string | null;
  tickets: number;
  carga: number;
  sesiones: number;
  disponible_hoy: boolean;
}

export interface EstadoRecursos {
  gestores: GestorEstado[];
  fecha_corte: string;
  n_gestores_activos: number;
}

export interface Ticket {
  ticket_id: string;
  estado: string;
  prioridad: string;
  modalidad: string;
  evento: string;
  dependencia: string;
  gestor: string;
  fecha_ingreso: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  tipo_docente: string;
  observacion: string;
  grupos: number;
  sesiones_por_grupo: number;
  total_sesiones: number;
  dias_abiertos: number;
  dias_habiles_restantes: number | null;
  req_dias_habiles: number;
  severidad: Severidad;
  es_ruta_b: boolean;
  obligatorio: boolean;
  peso: number;
}

export interface CargaGestor {
  gestor: string;
  tickets: number;
  carga_total: number;
  sesiones: number;
  dias_con_sesion: number;
  tickets_obligatorios: number;
  tickets_ruta_b: number;
}

export interface Movimiento {
  ticket_id: string;
  de: string;
  a: string;
  peso: number;
  prioridad: string;
}

export interface SesionCalendario {
  sesion_id: string;
  ticket_id: string;
  evento: string;
  grupo: number;
  numero_sesion: number;
  fecha: string;
  hora_inicio: string | null;
  hora_fin: string | null;
  gestor: string;
  gestor_dueno: string;
  es_apoyo: boolean;
  obligatoria: boolean;
  modalidad: string;
}

export interface DiaCalendario {
  fecha: string;
  sesiones: SesionCalendario[];
  saturado: boolean;
}

export interface Calendario {
  dias: DiaCalendario[];
  dias_saturados: { fecha: string; sesiones: string[] }[];
  cobertura_pct: number;
  obligatorias_cubiertas: number;
  obligatorias_totales: number;
  regulares_cubiertas: number;
  regulares_totales: number;
  colisiones: number;
  violaciones: string[];
}

export interface AlertaPlazo {
  ticket_id: string;
  evento: string;
  gestor: string;
  prioridad: string;
  tipo_docente: string;
  fecha_inicio: string | null;
  disponibles: number | null;
  requeridos: number;
  holgura: number | null;
  severidad: Severidad;
  mensaje: string;
}

export interface DiaCapacidad {
  fecha: string;
  total_sesiones: number;
  obligatorias: number;
  gestores_disponibles: number;
  gestores_ausentes?: string[];
  faltan_gestores: number;
  factible: boolean;
  sesiones: string[];
  sesiones_obligatorias: string[];
}

export interface ResultadoOptimizacion {
  comparativa: {
    antes: CargaGestor[];
    despues: CargaGestor[];
    metricas_antes: Record<string, number>;
    metricas_despues: Record<string, number>;
  };
  movimientos: Movimiento[];
  calendario: Calendario | null;
  alertas_plazo: AlertaPlazo[];
  diagnostico_capacidad: DiaCapacidad[];
}

export interface Dashboard {
  kpis: Record<string, number>;
  cargas: CargaGestor[];
  tickets_por_prioridad: Record<string, number>;
  tickets_por_modalidad: Record<string, number>;
  tickets_por_tipo_docente: Record<string, number>;
  tickets_por_estado: Record<string, number>;
  alertas_plazo: AlertaPlazo[];
  ruta_b: { tickets: number; carga_liberada: number; ids: string[] };
}

export interface Diagnostico {
  archivo: string;
  hojas_leidas: string[];
  tickets_totales: number;
  tickets_abiertos: number;
  sesiones_totales: number;
  sesiones_fechadas: number;
  grupos: number;
  docentes: number;
  resumen: Record<string, number>;
  incidencias: {
    tipo: string;
    gravedad: string;
    descripcion: string;
    referencia: string | null;
    accion_tomada: string;
  }[];
}

export interface Sugerencia {
  peso_ticket: number;
  sugerencias: {
    gestor: string;
    carga_actual: number;
    carga_resultante: number;
    delta: number;
    recomendado: boolean;
  }[];
}

export interface TicketCreado {
  ticket_id: string;
  gestor: string;
  evento: string;
  total_sesiones: number;
}

export interface SimulacionDocente {
  ticket_id: string;
  gestor: string;
  peso_antes: number;
  peso_despues: number;
  delta_peso: number;
  carga_actual: number;
  carga_simulada: number;
  plazo: {
    antes: EvaluacionPlazo;
    despues: EvaluacionPlazo;
    deterioro: boolean;
    mejora: boolean;
    delta_dias_requeridos: number;
    delta_holgura: number | null;
  };
}

export interface EvaluacionPlazo {
  ticket_id: string;
  tipo_docente: string;
  requiere_dias: number;
  disponibles: number | null;
  holgura: number | null;
  severidad: string;
  mensaje: string;
}

// ---------------------------------------------------------------- métodos
export const api = {
  health: () => peticion<{ ok: boolean; version: string }>("/health"),

  dashboard: () => peticion<Dashboard>("/dashboard"),
  diagnostico: () => peticion<Diagnostico>("/diagnostico"),
  reset: () => post<{ ok: boolean; mensaje: string }>("/demo/reset"),

  tickets: (estado?: string) =>
    peticion<Ticket[]>(`/tickets${estado ? `?estado=${encodeURIComponent(estado)}` : ""}`),
  sugerirGestor: (datos: Record<string, unknown>) => post<Sugerencia>("/tickets/nuevo", datos),
  crearTicket: (datos: Record<string, unknown>, gestor?: string) =>
    post<TicketCreado>(
      `/tickets${gestor ? `?gestor=${encodeURIComponent(gestor)}` : ""}`,
      datos,
    ),
  asignarTicket: (ticketId: string, gestor: string) =>
    post<{ ok: boolean }>(`/tickets/${ticketId}/asignar?gestor=${encodeURIComponent(gestor)}`),
  cambioDocente: (ticketId: string, nuevoTipo: string, aplicar = false) =>
    post<SimulacionDocente>(`/tickets/${ticketId}/cambio-docente`, {
      ticket_id: ticketId,
      nuevo_tipo: nuevoTipo,
      aplicar,
    }),

  recursos: () => peticion<EstadoRecursos>("/recursos"),
  agregarGestor: (nombre: string) => post<EstadoRecursos>("/recursos", { nombre }),
  actualizarGestor: (nombre: string, cuerpo: Record<string, unknown>) =>
    patch<EstadoRecursos>(`/recursos/${encodeURIComponent(nombre)}`, cuerpo),
  vacaciones: (gestor: string, desde: string, hasta: string) =>
    post<EstadoRecursos>("/recursos/vacaciones", { gestor, desde, hasta }),
  inhabilitar: (nombre: string) => del<EstadoRecursos>(`/recursos/${encodeURIComponent(nombre)}`),

  optimizar: (opciones: {
    theta_muestreo?: number;
    semilla?: number;
    max_movimientos?: number;
    reasignar_tickets?: boolean;
    generar_calendario?: boolean;
  }) => post<ResultadoOptimizacion>("/optimizar", opciones),
  capacidad: () => peticion<DiaCapacidad[]>("/optimizar/capacidad"),
};
