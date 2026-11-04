import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  type EstadoRecursos,
  type ResultadoOptimizacion,
  type Severidad,
} from "../api/client";
import {
  Aviso,
  COLOR,
  Cargando,
  Kpi,
  Panel,
  Semaforo,
  colorGestor,
  fecha,
  numero,
} from "../components/ui";

const TOOLTIP = {
  contentStyle: {
    background: "#121821",
    border: "1px solid #223047",
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: "#e6edf6", fontWeight: 600 },
};

export default function Recursos() {
  const [estado, setEstado] = useState<EstadoRecursos | null>(null);
  const [resultado, setResultado] = useState<ResultadoOptimizacion | null>(null);
  const [nuevo, setNuevo] = useState("");
  const [vac, setVac] = useState({ gestor: "", desde: "", hasta: "" });
  const [mensaje, setMensaje] = useState<{ tono: "ok" | "error" | "warn"; texto: string } | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [theta, setTheta] = useState(0.25);
  const [maxMov, setMaxMov] = useState(6);

  const cargar = useCallback(async () => {
    setEstado(await api.recursos());
  }, []);

  useEffect(() => {
    cargar().catch((e) => setMensaje({ tono: "error", texto: String(e.message) }));
  }, [cargar]);

  const ejecutar = async (fn: () => Promise<unknown>, exito: string) => {
    setOcupado(true);
    setMensaje(null);
    try {
      await fn();
      await cargar();
      setMensaje({ tono: "ok", texto: exito });
    } catch (e) {
      setMensaje({ tono: "error", texto: e instanceof Error ? e.message : String(e) });
    } finally {
      setOcupado(false);
    }
  };

  const optimizar = async () => {
    setOcupado(true);
    setMensaje(null);
    try {
      const r = await api.optimizar({
        theta_muestreo: theta,
        max_movimientos: maxMov,
      });
      setResultado(r);
      await cargar();
      setMensaje({
        tono: "ok",
        texto: `Optimización aplicada: ${r.movimientos.length} tickets reasignados, ${r.calendario?.colisiones ?? 0} colisiones en el calendario.`,
      });
    } catch (e) {
      setMensaje({ tono: "error", texto: e instanceof Error ? e.message : String(e) });
    } finally {
      setOcupado(false);
    }
  };

  if (!estado) return <Cargando texto="Cargando recursos…" />;

  const nombres = estado.gestores.map((g) => g.nombre);
  const activos = estado.gestores.filter((g) => g.estado === "Activo");
  const media =
    activos.reduce((a, g) => a + g.carga, 0) / (activos.length || 1);

  const datosGrafico = estado.gestores.map((g) => ({
    gestor: g.nombre,
    carga: Number(g.carga.toFixed(2)),
    estado: g.estado,
  }));

  return (
    <div className="space-y-4">
      {mensaje && (
        <Aviso tono={mensaje.tono} titulo={mensaje.tono === "ok" ? "Listo" : "Atención"}>
          {mensaje.texto}
        </Aviso>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi titulo="Gestores activos" valor={estado.n_gestores_activos} detalle={`de ${estado.gestores.length} registrados`} />
        <Kpi titulo="Carga media" valor={numero(media, 2)} detalle="unidades ponderadas" />
        <Kpi
          titulo="Tickets asignados"
          valor={estado.gestores.reduce((a, g) => a + g.tickets, 0)}
          detalle="en tickets abiertos"
        />
        <Kpi titulo="Fecha de corte" valor={fecha(estado.fecha_corte)} detalle="día de simulación" />
      </div>

      <Panel
        titulo="Carga por gestor"
        descripcion="La línea punteada es la media del equipo. Las barras grises son gestores no activos."
        acciones={
          <button className="btn btn-primario" onClick={optimizar} disabled={ocupado}>
            {ocupado ? "Optimizando…" : "Optimizar y rebalancear"}
          </button>
        }
      >
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={datosGrafico} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid stroke="#1d2735" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="gestor" stroke={COLOR.gris} tick={{ fill: "#93a4bd", fontSize: 12 }} />
              <YAxis stroke={COLOR.gris} tick={{ fill: "#93a4bd", fontSize: 12 }} />
              <Tooltip {...TOOLTIP} />
              <ReferenceLine
                y={media}
                stroke={COLOR.ambar}
                strokeDasharray="4 4"
                label={{ value: "media", fill: COLOR.ambar, fontSize: 11, position: "insideTopRight" }}
              />
              <Bar dataKey="carga" name="Carga W" radius={[4, 4, 0, 0]} maxBarSize={56}>
                {datosGrafico.map((d) => (
                  <Cell
                    key={d.gestor}
                    fill={d.estado === "Activo" ? colorGestor(d.gestor, nombres) : "#3e4c61"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label className="etiqueta" htmlFor="theta">Muestreo regular (θ)</label>
            <input
              id="theta"
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={theta}
              onChange={(e) => setTheta(Number(e.target.value))}
              className="w-40"
            />
            <span className="ml-2 text-xs tabular-nums" style={{ color: "var(--texto-suave)" }}>
              {Math.round(theta * 100)}%
            </span>
          </div>
          <div>
            <label className="etiqueta" htmlFor="mov">Máximo de reasignaciones</label>
            <input
              id="mov"
              type="number"
              min={0}
              max={44}
              value={maxMov}
              onChange={(e) => setMaxMov(Number(e.target.value))}
              className="campo w-24"
            />
          </div>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel titulo="Equipo" descripcion="Altas, bajas y vacaciones (Regla 1)">
          <div className="overflow-x-auto">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Gestor</th>
                  <th>Estado</th>
                  <th className="text-right">Tickets</th>
                  <th className="text-right">Carga</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {estado.gestores.map((g) => (
                  <tr key={g.nombre}>
                    <td className="font-medium">
                      <span
                        className="mr-2 inline-block h-2 w-2 rounded-full align-middle"
                        style={{
                          background:
                            g.estado === "Activo" ? colorGestor(g.nombre, nombres) : "#3e4c61",
                        }}
                      />
                      {g.nombre}
                    </td>
                    <td>
                      <span
                        className="chip"
                        style={{
                          color:
                            g.estado === "Activo"
                              ? COLOR.verde
                              : g.estado === "Vacaciones"
                                ? COLOR.ambar
                                : COLOR.gris,
                          borderColor: "var(--borde)",
                        }}
                      >
                        {g.estado}
                      </span>
                      {g.estado === "Vacaciones" && g.vacaciones_desde && (
                        <span className="ml-1 text-[11px]" style={{ color: "var(--texto-suave)" }}>
                          {fecha(g.vacaciones_desde)}–{fecha(g.vacaciones_hasta)}
                        </span>
                      )}
                    </td>
                    <td className="text-right tabular-nums">{g.tickets}</td>
                    <td className="text-right tabular-nums">{numero(g.carga, 2)}</td>
                    <td className="text-right">
                      {g.estado === "Activo" ? (
                        <button
                          className="btn btn-peligro px-2 py-1 text-xs"
                          disabled={ocupado}
                          onClick={() =>
                            ejecutar(
                              () => api.inhabilitar(g.nombre),
                              `${g.nombre} marcado como inactivo.`,
                            )
                          }
                        >
                          Inhabilitar
                        </button>
                      ) : (
                        <button
                          className="btn px-2 py-1 text-xs"
                          disabled={ocupado}
                          onClick={() =>
                            ejecutar(
                              () => api.actualizarGestor(g.nombre, { nombre: g.nombre, estado: "Activo" }),
                              `${g.nombre} reactivado.`,
                            )
                          }
                        >
                          Reactivar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 space-y-3 border-t pt-4" style={{ borderColor: "var(--borde)" }}>
            <div>
              <label className="etiqueta" htmlFor="nuevo">Alta de gestor</label>
              <div className="flex gap-2">
                <input
                  id="nuevo"
                  className="campo"
                  placeholder="Nombre del nuevo gestor"
                  value={nuevo}
                  onChange={(e) => setNuevo(e.target.value)}
                />
                <button
                  className="btn"
                  disabled={ocupado || !nuevo.trim()}
                  onClick={() =>
                    ejecutar(async () => {
                      await api.agregarGestor(nuevo.trim());
                      setNuevo("");
                    }, "Gestor agregado al equipo.")
                  }
                >
                  Agregar
                </button>
              </div>
            </div>
          </div>
        </Panel>

        <Panel titulo="Vacaciones" descripcion="Baja temporal con bloqueo de calendario">
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="etiqueta" htmlFor="vg">Gestor</label>
              <select
                id="vg"
                className="campo"
                value={vac.gestor}
                onChange={(e) => setVac({ ...vac, gestor: e.target.value })}
              >
                <option value="">Seleccione…</option>
                {estado.gestores.map((g) => (
                  <option key={g.nombre} value={g.nombre}>{g.nombre}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="etiqueta" htmlFor="vd">Desde</label>
              <input
                id="vd"
                type="date"
                className="campo"
                value={vac.desde}
                onChange={(e) => setVac({ ...vac, desde: e.target.value })}
              />
            </div>
            <div>
              <label className="etiqueta" htmlFor="vh">Hasta</label>
              <input
                id="vh"
                type="date"
                className="campo"
                value={vac.hasta}
                onChange={(e) => setVac({ ...vac, hasta: e.target.value })}
              />
            </div>
          </div>
          <button
            className="btn mt-3 w-full"
            disabled={ocupado || !vac.gestor || !vac.desde || !vac.hasta}
            onClick={() =>
              ejecutar(
                () => api.vacaciones(vac.gestor, vac.desde, vac.hasta),
                `${vac.gestor} queda de vacaciones: se bloquean sus fechas y se habilita el rebalanceo.`,
              )
            }
          >
            Registrar vacaciones y rebalancear
          </button>

          <div className="mt-4">
            <Aviso tono="warn" titulo="Nota metodológica">
              Con un gestor menos, hay días donde las sesiones obligatorias superan a los
              gestores disponibles. El sistema lo reporta como <strong>día saturado</strong> en
              lugar de forzar una asignación imposible: en ese caso se requiere apoyo externo.
            </Aviso>
          </div>

          <div className="mt-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--texto-suave)" }}>
              Diagnóstico previo de capacidad
            </h3>
            <DiasSaturados dias={resultado?.diagnostico_capacidad ?? []} />
          </div>
        </Panel>
      </div>

      {resultado && <ResumenOptimizacion r={resultado} />}
    </div>
  );
}

function DiasSaturados({ dias }: { dias: ResultadoOptimizacion["diagnostico_capacidad"] }) {
  if (!dias.length) {
    return (
      <p className="text-xs" style={{ color: "var(--texto-suave)" }}>
        Sin días infeasibles con la dotación actual.
      </p>
    );
  }
  return (
    <div className="space-y-1.5">
      {dias.slice(0, 8).map((d) => (
        <div
          key={d.fecha}
          className="flex items-center justify-between rounded-lg px-2.5 py-1.5 text-xs"
          style={{ background: "rgba(240,89,92,.08)", border: "1px solid rgba(240,89,92,.25)" }}
        >
          <span className="font-medium">{fecha(d.fecha)}</span>
          <span style={{ color: "var(--texto-suave)" }}>
            {d.total_sesiones} sesiones ({d.obligatorias} oblig.) · {d.gestores_disponibles} gestores
            {d.gestores_ausentes?.length ? ` · ausentes: ${d.gestores_ausentes.join(", ")}` : ""}
          </span>
          <span style={{ color: COLOR.rojo }}>faltan {d.faltan_gestores}</span>
        </div>
      ))}
    </div>
  );
}

function ResumenOptimizacion({ r }: { r: ResultadoOptimizacion }) {
  const { metricas_antes: a, metricas_despues: d } = r.comparativa;
  return (
    <Panel
      titulo="Resultado de la optimización"
      descripcion="Comparación antes / después y verificación independiente del calendario"
    >
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi titulo="Ratio de desbalance" valor={`${numero(a.ratio, 2)} → ${numero(d.ratio, 2)}`} color={COLOR.verde} />
        <Kpi titulo="Rango (máx − mín)" valor={`${numero(a.rango, 2)} → ${numero(d.rango, 2)}`} />
        <Kpi titulo="Reasignaciones" valor={r.movimientos.length} detalle="tickets que cambian de gestor" />
        <Kpi
          titulo="Colisiones en calendario"
          valor={r.calendario?.colisiones ?? 0}
          color={COLOR.verde}
          detalle="verificación independiente"
        />
      </div>

      {r.movimientos.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="tabla">
            <thead>
              <tr>
                <th>Ticket</th>
                <th>Origen</th>
                <th />
                <th>Destino</th>
                <th className="text-right">Peso</th>
                <th>Prioridad</th>
              </tr>
            </thead>
            <tbody>
              {r.movimientos.map((m) => (
                <tr key={m.ticket_id}>
                  <td className="font-mono text-xs">{m.ticket_id}</td>
                  <td>{m.de}</td>
                  <td style={{ color: "var(--texto-suave)" }}>→</td>
                  <td className="font-medium">{m.a}</td>
                  <td className="text-right tabular-nums">{numero(m.peso, 2)}</td>
                  <td>
                    <Semaforo
                      nivel={
                        (m.prioridad === "Urgente"
                          ? "ROJO"
                          : m.prioridad === "Alta"
                            ? "AMBAR"
                            : "VERDE") as Severidad
                      }
                      texto={m.prioridad}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {r.calendario && r.calendario.violaciones.length > 0 && (
        <div className="mt-4">
          <Aviso tono="warn" titulo="Infactibilidades declaradas">
            <ul className="mt-1 list-inside list-disc space-y-0.5">
              {r.calendario.violaciones.map((v) => (
                <li key={v}>{v}</li>
              ))}
            </ul>
          </Aviso>
        </div>
      )}
    </Panel>
  );
}
