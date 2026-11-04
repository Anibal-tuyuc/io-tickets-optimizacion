import { useMemo, useState } from "react";
import { api, type Calendario as Cal, type ResultadoOptimizacion } from "../api/client";
import {
  Aviso,
  COLOR,
  Cargando,
  Panel,
  colorGestor,
  fecha,
  numero,
} from "../components/ui";

export default function Calendario() {
  const [resultado, setResultado] = useState<ResultadoOptimizacion | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gestorFiltro, setGestorFiltro] = useState("");

  const generar = async () => {
    setCargando(true);
    setError(null);
    try {
      const r = await api.optimizar({ generar_calendario: true, reasignar_tickets: false, max_movimientos: 0 });
      setResultado(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCargando(false);
    }
  };

  const cal: Cal | null = resultado?.calendario ?? null;
  const gestores = useMemo(() => {
    if (!cal) return [];
    const s = new Set<string>();
    cal.dias.forEach((d) => d.sesiones.forEach((x) => s.add(x.gestor)));
    return [...s].sort();
  }, [cal]);

  return (
    <div className="space-y-4">
      <Panel
        titulo="Calendario de acompañamiento docente"
        descripcion="100% de las sesiones obligatorias + muestreo configurable de las regulares, con un máximo de 1 supervisión por gestor y día."
        acciones={
          <>
            <select
              className="campo w-auto"
              value={gestorFiltro}
              onChange={(e) => setGestorFiltro(e.target.value)}
            >
              <option value="">Todos los gestores</option>
              {gestores.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
            <button className="btn btn-primario" onClick={generar} disabled={cargando}>
              {cargando ? "Programando…" : "Generar calendario"}
            </button>
          </>
        }
      >
        {error && <Aviso tono="error">{error}</Aviso>}
        {!cal && !error && (
          <p className="text-sm" style={{ color: "var(--texto-suave)" }}>
            Genere el calendario para ver la programación resultante del modelo.
          </p>
        )}

        {cal && (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Metrica
              titulo="Cobertura obligatoria"
              valor={`${cal.obligatorias_cubiertas}/${cal.obligatorias_totales}`}
              nota="debe ser 100%"
              ok={cal.obligatorias_cubiertas === cal.obligatorias_totales}
            />
            <Metrica
              titulo="Muestreo regular"
              valor={`${cal.regulares_cubiertas}/${cal.regulares_totales}`}
              nota={`${cal.cobertura_pct}% del total`}
              ok
            />
            <Metrica
              titulo="Colisiones diarias"
              valor={cal.colisiones}
              nota="verificación independiente"
              ok={cal.colisiones === 0}
            />
            <Metrica
              titulo="Días saturados"
              valor={cal.dias_saturados.length}
              nota="requieren apoyo externo"
              ok={cal.dias_saturados.length === 0}
            />
          </div>
        )}
      </Panel>

      {cal && cal.violaciones.length > 0 && (
        <Aviso tono="warn" titulo="Infactibilidades declaradas (no se ocultan)">
          <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs">
            {cal.violaciones.map((v) => (
              <li key={v}>{v}</li>
            ))}
          </ul>
        </Aviso>
      )}

      {cal && (
        <Panel titulo="Agenda por día" descripcion="Cada fila es un día con sesiones supervisadas">
          <div className="max-h-[560px] overflow-y-auto">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Gestor</th>
                  <th>Ticket</th>
                  <th>Sesión</th>
                  <th>Horario</th>
                  <th>Tipo</th>
                  <th>Modalidad</th>
                </tr>
              </thead>
              <tbody>
                {cal.dias
                  .flatMap((d) =>
                    d.sesiones
                      .filter((s) => !gestorFiltro || s.gestor === gestorFiltro)
                      .map((s) => ({ ...s, saturado: d.saturado })),
                  )
                  .map((s) => (
                    <tr key={s.sesion_id}>
                      <td className="whitespace-nowrap tabular-nums">
                        {fecha(s.fecha)}
                        {s.saturado && <span className="ml-1" style={{ color: COLOR.rojo }}>●</span>}
                      </td>
                      <td>
                        <span
                          className="mr-1.5 inline-block h-2 w-2 rounded-full align-middle"
                          style={{ background: colorGestor(s.gestor, gestores) }}
                        />
                        {s.gestor}
                        {s.es_apoyo && (
                          <span className="ml-1 text-[11px]" style={{ color: COLOR.violeta }}>
                            (apoyo)
                          </span>
                        )}
                      </td>
                      <td className="font-mono text-xs">{s.ticket_id}</td>
                      <td className="text-xs">
                        G{s.grupo} · S{s.numero_sesion}
                      </td>
                      <td className="whitespace-nowrap text-xs tabular-nums" style={{ color: "var(--texto-suave)" }}>
                        {s.hora_inicio ?? "—"}–{s.hora_fin ?? "—"}
                      </td>
                      <td>
                        <span
                          className="chip text-[11px]"
                          style={{
                            color: s.obligatoria ? COLOR.ambar : "var(--texto-suave)",
                            borderColor: s.obligatoria ? "rgba(240,180,41,.4)" : "var(--borde)",
                          }}
                        >
                          {s.obligatoria ? "Obligatoria" : "Muestreo"}
                        </span>
                      </td>
                      <td className="text-xs" style={{ color: "var(--texto-suave)" }}>
                        {s.modalidad}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {cal && cal.dias_saturados.length > 0 && (
        <Panel titulo="Días que exceden la capacidad del equipo">
          <div className="space-y-1.5">
            {cal.dias_saturados.map((d) => (
              <div
                key={d.fecha}
                className="rounded-lg px-3 py-2 text-xs"
                style={{ background: "rgba(240,89,92,.08)", border: "1px solid rgba(240,89,92,.25)" }}
              >
                <span className="font-semibold">{fecha(d.fecha)}</span>
                <span className="ml-2" style={{ color: "var(--texto-suave)" }}>
                  {d.sesiones.length} sesión(es) obligatoria(s) sin gestor disponible:
                </span>
                <div className="mt-1 font-mono text-[11px]" style={{ color: "var(--texto-suave)" }}>
                  {d.sesiones.join(" · ")}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {cargando && <Cargando texto="Resolviendo el modelo de calendario…" />}
    </div>
  );
}

function Metrica({
  titulo,
  valor,
  nota,
  ok,
}: {
  titulo: string;
  valor: string | number;
  nota: string;
  ok: boolean;
}) {
  return (
    <div className="panel-alto p-3">
      <div className="text-[11px] uppercase tracking-wide" style={{ color: "var(--texto-suave)" }}>
        {titulo}
      </div>
      <div
        className="text-xl font-semibold tabular-nums"
        style={{ color: ok ? COLOR.verde : COLOR.rojo }}
      >
        {typeof valor === "number" ? numero(valor, 0) : valor}
      </div>
      <div className="text-[11px]" style={{ color: "var(--texto-suave)" }}>
        {nota}
      </div>
    </div>
  );
}
