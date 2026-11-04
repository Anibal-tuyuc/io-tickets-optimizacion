import { useEffect, useMemo, useState } from "react";
import {
  api,
  type Severidad,
  type SimulacionDocente,
  type Ticket,
} from "../api/client";
import {
  Aviso,
  COLOR,
  Cargando,
  Kpi,
  Panel,
  Semaforo,
  fecha,
  numero,
} from "../components/ui";

const TIPOS = ["Interno", "Cooperante", "Externo"] as const;
const REQUERIDOS: Record<string, number> = { Interno: 8, Cooperante: 15, Externo: 30 };

export default function Simulador() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [seleccion, setSeleccion] = useState<string>("");
  const [tipo, setTipo] = useState<string>("Externo");
  const [sim, setSim] = useState<SimulacionDocente | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [filtro, setFiltro] = useState("Interno");

  useEffect(() => {
    api
      .tickets("Abierto")
      .then((t) => {
        setTickets(t);
        const primero = t.find((x) => x.severidad === "AMBAR") ?? t[0];
        if (primero) setSeleccion(primero.ticket_id);
      })
      .catch((e) => setError(String(e.message)));
  }, []);

  const ticket = useMemo(
    () => tickets.find((t) => t.ticket_id === seleccion),
    [tickets, seleccion],
  );

  const simular = async () => {
    if (!seleccion) return;
    setOcupado(true);
    setError(null);
    try {
      const r = await api.cambioDocente(seleccion, tipo, false);
      setSim(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  const aplicar = async () => {
    if (!seleccion) return;
    setOcupado(true);
    setError(null);
    try {
      const r = await api.cambioDocente(seleccion, tipo, true);
      setSim(r);
      const actualizados = await api.tickets("Abierto");
      setTickets(actualizados);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  if (!tickets.length) return error ? <Aviso tono="error">{error}</Aviso> : <Cargando texto="Cargando tickets…" />;

  const listado = tickets.filter((t) => filtro === "Todos" || t.tipo_docente === filtro);

  return (
    <div className="space-y-4">
      {error && <Aviso tono="error" titulo="Error">{error}</Aviso>}

      <Panel
        titulo="Simulador de cambio dinámico de docente"
        descripcion="Regla 2: cambio en la mitad de la gestión. Recalcula peso, carga y plazo administrativo."
        acciones={
          <>
            <button className="btn" onClick={simular} disabled={ocupado || !seleccion}>
              Simular impacto
            </button>
            <button className="btn btn-primario" onClick={aplicar} disabled={ocupado || !seleccion}>
              Aplicar cambio
            </button>
          </>
        }
      >
        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <label className="etiqueta" htmlFor="filtro">Filtrar por tipo actual</label>
            <select id="filtro" className="campo" value={filtro} onChange={(e) => setFiltro(e.target.value)}>
              {["Todos", ...TIPOS].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="etiqueta" htmlFor="ticket">Ticket activo</label>
            <select
              id="ticket"
              className="campo"
              value={seleccion}
              onChange={(e) => setSeleccion(e.target.value)}
            >
              {listado.map((t) => (
                <option key={t.ticket_id} value={t.ticket_id}>
                  {t.ticket_id} — {t.evento} ({t.tipo_docente}, {t.severidad})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="etiqueta" htmlFor="tipo">Nuevo tipo de docente</label>
            <select id="tipo" className="campo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
              {TIPOS.map((t) => (
                <option key={t} value={t}>
                  {t} — {REQUERIDOS[t]} días hábiles
                </option>
              ))}
            </select>
          </div>
        </div>

        {ticket && (
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            <Dato etiqueta="Estado actual" valor={ticket.tipo_docente} />
            <Dato etiqueta="Inicio" valor={fecha(ticket.fecha_inicio)} />
            <Dato etiqueta="Días hábiles restantes" valor={ticket.dias_habiles_restantes ?? "—"} />
            <Dato etiqueta="Sesiones" valor={ticket.total_sesiones} />
          </div>
        )}
      </Panel>

      {sim && (
        <>
          <div className={`grid grid-cols-2 gap-3 lg:grid-cols-4`}>
            <Kpi
              titulo="Plazo — antes"
              valor={sim.plazo.antes.severidad}
              detalle={`holgura ${sim.plazo.antes.holgura ?? "—"} d`}
              color={colorSev(sim.plazo.antes.severidad)}
            />
            <Kpi
              titulo="Plazo — después"
              valor={sim.plazo.despues.severidad}
              detalle={`holgura ${sim.plazo.despues.holgura ?? "—"} d`}
              color={colorSev(sim.plazo.despues.severidad)}
            />
            <Kpi
              titulo="Peso del ticket"
              valor={`${numero(sim.peso_antes, 1)} → ${numero(sim.peso_despues, 1)}`}
              detalle={`Δ ${numero(sim.delta_peso, 1)}`}
            />
            <Kpi
              titulo={`Carga de ${sim.gestor}`}
              valor={`${numero(sim.carga_actual, 1)} → ${numero(sim.carga_simulada, 1)}`}
              detalle={sim.carga_simulada > sim.carga_actual ? "sube" : "sin cambio"}
            />
          </div>

          <Panel titulo="Lectura del resultado">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Semaforo nivel={sim.plazo.antes.severidad as Severidad} />
                <span style={{ color: "var(--texto-suave)" }}>→</span>
                <Semaforo nivel={sim.plazo.despues.severidad as Severidad} />
                <span style={{ color: "var(--texto-suave)" }}>
                  +{sim.plazo.delta_dias_requeridos} días hábiles exigidos por el nuevo tipo
                </span>
              </div>

              <Aviso
                tono={
                  sim.plazo.deterioro ? "error" : sim.plazo.mejora ? "ok" : "warn"
                }
                titulo={
                  sim.plazo.deterioro
                    ? "Cambio inviable en el plazo actual"
                    : sim.plazo.mejora
                      ? "El cambio libera margen"
                      : "El cambio no altera el semáforo"
                }
              >
                {sim.plazo.despues.mensaje}
              </Aviso>

              <div className="grid gap-2 sm:grid-cols-2">
                <Explicacion
                  titulo="Por qué sube el peso"
                  texto="La contratación externa añade verificación presupuestaria, requisición, especificaciones técnicas, cotizaciones, opinión técnica y adjudicación. El peso base pasa de 1.0 a 3.5."
                />
                <Explicacion
                  titulo="Qué debe decidir la Mesa de Entrada"
                  texto={
                    sim.plazo.deterioro
                      ? "Reprogramar la fecha de inicio o adelantar la requisición de compras; el margen actual no alcanza."
                      : "El cambio puede aplicarse sin riesgo administrativo."
                  }
                />
              </div>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string | number }) {
  return (
    <div className="panel-alto px-2.5 py-2">
      <div className="text-[11px] uppercase tracking-wide" style={{ color: "var(--texto-suave)" }}>
        {etiqueta}
      </div>
      <div className="text-sm font-medium">{valor}</div>
    </div>
  );
}

function Explicacion({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <div className="panel-alto p-3">
      <div className="mb-1 text-xs font-semibold">{titulo}</div>
      <p className="text-xs leading-relaxed" style={{ color: "var(--texto-suave)" }}>
        {texto}
      </p>
    </div>
  );
}

function colorSev(s: string): string {
  return s === "ROJO"
    ? COLOR.rojo
    : s === "AMBAR"
      ? COLOR.ambar
      : s === "VERDE"
        ? COLOR.verde
        : COLOR.gris;
}
