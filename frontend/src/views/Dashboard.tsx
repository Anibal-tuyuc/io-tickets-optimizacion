import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type Dashboard as DatosDashboard, type Severidad } from "../api/client";
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

export default function Dashboard() {
  const [datos, setDatos] = useState<DatosDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    api
      .dashboard()
      .then(setDatos)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setCargando(false));
  }, []);

  const gestores = useMemo(
    () => datos?.cargas.map((c) => c.gestor) ?? [],
    [datos],
  );

  if (cargando) return <Cargando texto="Calculando tablero…" />;
  if (error) return <Aviso tono="error" titulo="No se pudo cargar el tablero">{error}</Aviso>;
  if (!datos) return null;

  const k = datos.kpis;

  // El gráfico central del proyecto: tickets nominales vs carga real.
  const comparativa = datos.cargas.map((c) => ({
    gestor: c.gestor,
    tickets: c.tickets,
    carga: Number(c.carga_total.toFixed(2)),
    sesiones: c.sesiones,
  }));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi titulo="Tickets abiertos" valor={k.tickets_abiertos} detalle={`${k.tickets_totales} en el histórico`} />
        <Kpi
          titulo="Desbalance de carga"
          valor={`${numero(k.ratio_desbalance, 2)}×`}
          detalle="máx / mín entre gestores"
          color={k.ratio_desbalance > 1.5 ? COLOR.rojo : k.ratio_desbalance > 1.2 ? COLOR.ambar : COLOR.verde}
        />
        <Kpi
          titulo="Eventos en DFV"
          valor={k.eventos_ruta_b}
          detalle={`${numero(datos.ruta_b.carga_liberada, 1)} de carga liberada`}
          color={COLOR.violeta}
        />
        <Kpi
          titulo="Alertas de contratación"
          valor={k.alertas_contratacion}
          detalle="externos sin margen suficiente"
          color={COLOR.rojo}
        />
      </div>

      <Panel
        titulo="Carga ponderada vs. cantidad nominal de tickets"
        descripcion="Mismo número de tickets no significa la misma carga: el peso incorpora tipo de docente, modalidad y sesiones."
      >
        <div style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={comparativa} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid stroke="#1d2735" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="gestor" stroke={COLOR.gris} tick={{ fill: "#93a4bd", fontSize: 12 }} />
              <YAxis yAxisId="izq" stroke={COLOR.gris} tick={{ fill: "#93a4bd", fontSize: 12 }} />
              <YAxis
                yAxisId="der"
                orientation="right"
                stroke={COLOR.gris}
                tick={{ fill: "#93a4bd", fontSize: 12 }}
              />
              <Tooltip {...TOOLTIP} />
              <Legend wrapperStyle={{ fontSize: 12, color: "#93a4bd" }} />
              <Bar yAxisId="izq" dataKey="tickets" name="Tickets (nominal)" radius={[4, 4, 0, 0]} maxBarSize={44} fill={COLOR.gris}>
                {comparativa.map((c) => (
                  <Cell key={c.gestor} fill="#3e4c61" />
                ))}
              </Bar>
              <Bar yAxisId="der" dataKey="carga" name="Carga ponderada (W)" radius={[4, 4, 0, 0]} maxBarSize={44}>
                {comparativa.map((c) => (
                  <Cell key={c.gestor} fill={colorGestor(c.gestor, gestores)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-5">
          {datos.cargas.map((c) => (
            <div key={c.gestor} className="panel-alto p-2">
              <div className="flex items-center gap-1.5">
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 99,
                    background: colorGestor(c.gestor, gestores),
                    display: "inline-block",
                  }}
                />
                <span className="font-medium">{c.gestor}</span>
              </div>
              <div style={{ color: "var(--texto-suave)" }}>
                {c.tickets} tickets · {numero(c.carga_total, 2)} W
              </div>
              <div style={{ color: "var(--texto-suave)" }}>{c.sesiones} sesiones</div>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel titulo="Composición de la demanda" descripcion="Tickets abiertos por dimensión">
          <div className="space-y-4">
            <Distribucion titulo="Prioridad" datos={datos.tickets_por_prioridad} colores={[COLOR.rojo, "#fb923c", COLOR.ambar, COLOR.gris]} />
            <Distribucion titulo="Modalidad" datos={datos.tickets_por_modalidad} colores={[COLOR.acento, COLOR.cian, COLOR.violeta, "#a3e635"]} />
            <Distribucion titulo="Tipo de docente" datos={datos.tickets_por_tipo_docente} colores={[COLOR.verde, COLOR.ambar, COLOR.rojo]} />
          </div>
        </Panel>

        <Panel
          titulo="Alertas de plazo administrativo"
          descripcion="Días hábiles restantes frente a lo que exige el tipo de docente"
        >
          <div className="max-h-[320px] space-y-1.5 overflow-y-auto pr-1">
            {datos.alertas_plazo.slice(0, 20).map((a) => (
              <div
                key={a.ticket_id}
                className="flex items-center justify-between gap-2 rounded-lg px-2.5 py-2"
                style={{ background: "var(--panel-alto)" }}
              >
                <div className="min-w-0">
                  <div className="truncate text-xs font-medium">
                    {a.ticket_id} · {a.evento}
                  </div>
                  <div className="text-[11px]" style={{ color: "var(--texto-suave)" }}>
                    {a.tipo_docente} · {a.gestor} · inicio {fecha(a.fecha_inicio)}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-xs tabular-nums" style={{ color: "var(--texto-suave)" }}>
                    {a.disponibles ?? "—"} / {a.requeridos}
                  </span>
                  <Semaforo nivel={a.severidad as Severidad} />
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Aviso tono="info" titulo="Ruta B — eventos trasladados al DFV">
        {datos.ruta_b.tickets} eventos asincrónicos no bloquean calendario de supervisión ni
        generan seguimiento diario. Sin la Regla 3, inflarían artificialmente la carga de sus
        gestores en {numero(datos.ruta_b.carga_liberada, 1)} unidades.
      </Aviso>
    </div>
  );
}

function Distribucion({
  titulo,
  datos,
  colores,
}: {
  titulo: string;
  datos: Record<string, number>;
  colores: string[];
}) {
  const total = Object.values(datos).reduce((a, b) => a + b, 0) || 1;
  return (
    <div>
      <div className="mb-1 text-xs font-medium" style={{ color: "var(--texto-suave)" }}>
        {titulo}
      </div>
      <div className="space-y-1">
        {Object.entries(datos)
          .sort((a, b) => b[1] - a[1])
          .map(([nombre, valor], i) => (
            <div key={nombre} className="flex items-center gap-2 text-xs">
              <span className="w-36 shrink-0 truncate">{nombre}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: "#1a2333" }}>
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(valor / total) * 100}%`,
                    background: colores[i % colores.length],
                  }}
                />
              </div>
              <span className="w-8 shrink-0 text-right tabular-nums" style={{ color: "var(--texto-suave)" }}>
                {valor}
              </span>
            </div>
          ))}
      </div>
    </div>
  );
}
