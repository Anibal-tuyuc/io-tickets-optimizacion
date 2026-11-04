import { useEffect, useMemo, useState } from "react";
import { api, type Sugerencia, type Ticket } from "../api/client";
import {
  Aviso,
  COLOR,
  Panel,
  Semaforo,
  numero,
} from "../components/ui";
import type { Severidad } from "../api/client";

const VACIO = {
  evento: "",
  dependencia: "",
  prioridad: "Media",
  modalidad: "Presencial",
  tipo_docente: "Interno",
  fecha_inicio: "",
  grupos_programados: 1,
  sesiones_por_grupo: 1,
  obligatorio: false,
};

export default function MesaEntrada() {
  const [form, setForm] = useState({ ...VACIO });
  const [sugerencia, setSugerencia] = useState<Sugerencia | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [prioridadFiltro, setPrioridadFiltro] = useState("");
  const [ok, setOk] = useState<string | null>(null);

  const cargar = () =>
    api.tickets("Abierto").then(setTickets).catch((e) => setError(String(e.message)));

  useEffect(() => {
    cargar();
  }, []);

  const evaluar = async () => {
    setOcupado(true);
    setError(null);
    try {
      const r = await api.sugerirGestor({
        ...form,
        fecha_inicio: form.fecha_inicio || null,
      });
      setSugerencia(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  const crearYAsignar = async (gestor: string) => {
    setOcupado(true);
    setError(null);
    try {
      const creado = await api.crearTicket(
        { ...form, fecha_inicio: form.fecha_inicio || null },
        gestor,
      );
      await cargar();
      setSugerencia(null);
      setForm({ ...VACIO });
      setOk(
        `Ticket ${creado.ticket_id} registrado y asignado a ${gestor} ` +
          `(${creado.total_sesiones} sesiones programadas).`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOcupado(false);
    }
  };

  const filtrados = useMemo(
    () =>
      tickets.filter(
        (t) =>
          (!prioridadFiltro || t.prioridad === prioridadFiltro) &&
          (!busqueda ||
            t.ticket_id.toLowerCase().includes(busqueda.toLowerCase()) ||
            t.evento.toLowerCase().includes(busqueda.toLowerCase())),
      ),
    [tickets, prioridadFiltro, busqueda],
  );

  return (
    <div className="space-y-4">
      {error && <Aviso tono="error">{error}</Aviso>}
      {ok && <Aviso tono="ok" titulo="Registrado">{ok}</Aviso>}

      <div className="grid gap-4 lg:grid-cols-5">
        <Panel
          className="lg:col-span-2"
          titulo="Nuevo ticket"
          descripcion="Registre la solicitud y el sistema sugiere a quién asignarla"
        >
          <div className="space-y-3">
            <div>
              <label className="etiqueta" htmlFor="evento">Evento formativo</label>
              <input
                id="evento"
                className="campo"
                value={form.evento}
                onChange={(e) => setForm({ ...form, evento: e.target.value })}
                placeholder="Ej. Capacitación en protección de datos"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="etiqueta" htmlFor="prioridad">Prioridad</label>
                <select
                  id="prioridad"
                  className="campo"
                  value={form.prioridad}
                  onChange={(e) => setForm({ ...form, prioridad: e.target.value })}
                >
                  {["Urgente", "Alta", "Media", "Baja"].map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="etiqueta" htmlFor="modalidad">Modalidad</label>
                <select
                  id="modalidad"
                  className="campo"
                  value={form.modalidad}
                  onChange={(e) => setForm({ ...form, modalidad: e.target.value })}
                >
                  {["Presencial", "Virtual Sincrónico", "Virtual Asincrónico", "Mixto"].map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="etiqueta" htmlFor="tdoc">Tipo de docente</label>
                <select
                  id="tdoc"
                  className="campo"
                  value={form.tipo_docente}
                  onChange={(e) => setForm({ ...form, tipo_docente: e.target.value })}
                >
                  {["Interno", "Cooperante", "Externo"].map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="etiqueta" htmlFor="finicio">Inicio</label>
                <input
                  id="finicio"
                  type="date"
                  className="campo"
                  value={form.fecha_inicio}
                  onChange={(e) => setForm({ ...form, fecha_inicio: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="etiqueta" htmlFor="grupos">Grupos</label>
                <input
                  id="grupos"
                  type="number"
                  min={1}
                  className="campo"
                  value={form.grupos_programados}
                  onChange={(e) => setForm({ ...form, grupos_programados: Number(e.target.value) })}
                />
              </div>
              <div>
                <label className="etiqueta" htmlFor="spg">Sesiones por grupo</label>
                <input
                  id="spg"
                  type="number"
                  min={1}
                  className="campo"
                  value={form.sesiones_por_grupo}
                  onChange={(e) => setForm({ ...form, sesiones_por_grupo: Number(e.target.value) })}
                />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.obligatorio}
                onChange={(e) => setForm({ ...form, obligatorio: e.target.checked })}
              />
              Requiere observación obligatoria (docente nuevo / tema nuevo)
            </label>

            <button
              className="btn btn-primario w-full"
              onClick={evaluar}
              disabled={ocupado || !form.evento.trim()}
            >
              {ocupado ? "Evaluando…" : "Sugerir gestor"}
            </button>

            {sugerencia && (
              <div className="space-y-2 border-t pt-3" style={{ borderColor: "var(--borde)" }}>
                <div className="text-xs" style={{ color: "var(--texto-suave)" }}>
                  Peso del ticket: <strong style={{ color: "var(--texto)" }}>{numero(sugerencia.peso_ticket, 2)}</strong>
                </div>
                {sugerencia.sugerencias.map((s) => (
                  <div
                    key={s.gestor}
                    className="flex items-center justify-between rounded-lg px-3 py-2"
                    style={{
                      background: s.recomendado ? "rgba(53,196,138,.10)" : "var(--panel-alto)",
                      border: `1px solid ${s.recomendado ? "rgba(53,196,138,.35)" : "var(--borde)"}`,
                    }}
                  >
                    <div>
                      <div className="text-sm font-medium">
                        {s.gestor}
                        {s.recomendado && (
                          <span className="ml-2 text-[11px]" style={{ color: COLOR.verde }}>
                            recomendado
                          </span>
                        )}
                      </div>
                      <div className="text-[11px]" style={{ color: "var(--texto-suave)" }}>
                        {numero(s.carga_actual, 2)} → {numero(s.carga_resultante, 2)}
                      </div>
                    </div>
                    <button
                      className="btn px-2 py-1 text-xs"
                      onClick={() => crearYAsignar(s.gestor)}
                      disabled={ocupado}
                    >
                      Crear y asignar
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Panel>

        <Panel
          className="lg:col-span-3"
          titulo="Tickets abiertos"
          descripcion={`${tickets.length} tickets activos — ordenados por antigüedad y urgencia`}
          acciones={
            <>
              <input
                className="campo w-40"
                placeholder="Buscar…"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
              />
              <select
                className="campo w-32"
                value={prioridadFiltro}
                onChange={(e) => setPrioridadFiltro(e.target.value)}
              >
                <option value="">Prioridad</option>
                {["Urgente", "Alta", "Media", "Baja"].map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </>
          }
        >
          <div className="max-h-[620px] overflow-auto">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Ticket</th>
                  <th>Evento</th>
                  <th>Gestor</th>
                  <th className="text-right">Ses.</th>
                  <th className="text-right">W</th>
                  <th>Plazo</th>
                </tr>
              </thead>
              <tbody>
                {filtrados.map((t) => (
                  <tr key={t.ticket_id}>
                    <td className="whitespace-nowrap font-mono text-xs">{t.ticket_id}</td>
                    <td>
                      <div className="max-w-[220px] truncate">{t.evento}</div>
                      <div className="text-[11px]" style={{ color: "var(--texto-suave)" }}>
                        {t.modalidad} · {t.tipo_docente}
                        {t.es_ruta_b && <span style={{ color: COLOR.violeta }}> · DFV</span>}
                      </div>
                    </td>
                    <td className="whitespace-nowrap text-xs">{t.gestor}</td>
                    <td className="text-right tabular-nums">{t.total_sesiones}</td>
                    <td className="text-right tabular-nums">{numero(t.peso, 2)}</td>
                    <td>
                      <Semaforo
                        nivel={t.severidad as Severidad}
                        texto={
                          t.dias_habiles_restantes === null
                            ? "sin fecha"
                            : `${t.dias_habiles_restantes} d`
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>

      <Panel titulo="Trazabilidad del cálculo" descripcion="Cómo se compone la carga de un ticket">
        <div className="grid gap-3 text-xs sm:grid-cols-3">
          <Formula
            titulo="Peso del docente"
            detalle="Interno 1.0 · Cooperante 1.8 · Externo 3.5"
            peso="α = 0.60"
          />
          <Formula
            titulo="Sesiones × modalidad"
            detalle="Asincrónico 0.12 · Sincrónico 0.90 · Presencial 1.00"
            peso="β = 0.35"
          />
          <Formula
            titulo="Participantes"
            detalle="ln(1 + participantes) — satura el efecto de grupos grandes"
            peso="γ = 0.05"
          />
        </div>
      </Panel>
    </div>
  );
}

function Formula({ titulo, detalle, peso }: { titulo: string; detalle: string; peso: string }) {
  return (
    <div className="panel-alto p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="font-semibold">{titulo}</span>
        <span className="font-mono text-[11px]" style={{ color: COLOR.acento }}>{peso}</span>
      </div>
      <p style={{ color: "var(--texto-suave)" }}>{detalle}</p>
    </div>
  );
}

