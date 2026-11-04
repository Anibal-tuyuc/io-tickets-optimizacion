import { useEffect, useState } from "react";
import { api } from "./api/client";
import Calendario from "./views/Calendario";
import CalidadDatos from "./views/CalidadDatos";
import Dashboard from "./views/Dashboard";
import MesaEntrada from "./views/MesaEntrada";
import Recursos from "./views/Recursos";
import Simulador from "./views/Simulador";
import { Aviso, COLOR } from "./components/ui";

type Vista = "dashboard" | "entrada" | "recursos" | "simulador" | "calendario" | "calidad";

const MENU: { id: Vista; titulo: string; descripcion: string; icono: string }[] = [
  { id: "dashboard", titulo: "Tablero", descripcion: "Indicadores y desbalance", icono: "◧" },
  { id: "entrada", titulo: "Mesa de entrada", descripcion: "Nuevo ticket y asignación", icono: "✚" },
  { id: "recursos", titulo: "Equipo", descripcion: "Altas, bajas y vacaciones", icono: "◇" },
  { id: "simulador", titulo: "Simulador", descripcion: "Cambio de tipo de docente", icono: "⇄" },
  { id: "calendario", titulo: "Calendario", descripcion: "Acompañamiento sin choques", icono: "▤" },
  { id: "calidad", titulo: "Calidad de datos", descripcion: "Auditoría de la base", icono: "⚑" },
];

export default function App() {
  const [vista, setVista] = useState<Vista>("dashboard");
  const [salud, setSalud] = useState<{ ok: boolean; version: string } | null>(null);
  const [sinApi, setSinApi] = useState(false);
  const [reiniciando, setReiniciando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    api
      .health()
      .then(setSalud)
      .catch(() => setSinApi(true));
  }, []);

  const reiniciar = async () => {
    setReiniciando(true);
    try {
      const r = await api.reset();
      setAviso(r.mensaje);
      setVista("dashboard");
      // recarga completa: garantiza que todas las vistas relean el estado limpio
      setTimeout(() => window.location.reload(), 900);
    } catch (e) {
      setAviso(e instanceof Error ? e.message : String(e));
    } finally {
      setReiniciando(false);
    }
  };

  const actual = MENU.find((m) => m.id === vista)!;

  return (
    <div className="flex min-h-screen">
      <aside
        className="hidden w-64 shrink-0 flex-col border-r p-4 md:flex"
        style={{ borderColor: "var(--borde)", background: "#0e141d" }}
      >
        <div className="mb-6">
          <div className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: COLOR.acento }}>
            Investigación de Operaciones
          </div>
          <h1 className="mt-1 text-sm font-semibold leading-snug">
            Optimizador de Tickets y Acompañamiento Docente
          </h1>
          <div className="mt-1 text-[11px]" style={{ color: "var(--texto-suave)" }}>
            Universidad Mariano Gálvez
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          {MENU.map((m) => {
            const activa = m.id === vista;
            return (
              <button
                key={m.id}
                onClick={() => setVista(m.id)}
                className="flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition"
                style={{
                  background: activa ? "rgba(79,157,255,.10)" : "transparent",
                  border: `1px solid ${activa ? "rgba(79,157,255,.35)" : "transparent"}`,
                }}
              >
                <span style={{ color: activa ? COLOR.acento : "var(--texto-suave)" }}>{m.icono}</span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium" style={{ color: activa ? "var(--texto)" : "var(--texto-suave)" }}>
                    {m.titulo}
                  </span>
                  <span className="block truncate text-[11px]" style={{ color: "var(--texto-suave)" }}>
                    {m.descripcion}
                  </span>
                </span>
              </button>
            );
          })}
        </nav>

        <div className="mt-4 border-t pt-3" style={{ borderColor: "var(--borde)" }}>
          <button className="btn w-full" onClick={reiniciar} disabled={reiniciando}>
            {reiniciando ? "Reiniciando…" : "Reiniciar demo"}
          </button>
          <p className="mt-2 text-[11px] leading-relaxed" style={{ color: "var(--texto-suave)" }}>
            Restaura el estado original del Excel antes de grabar.
          </p>
          <div className="mt-3 flex items-center gap-1.5 text-[11px]" style={{ color: "var(--texto-suave)" }}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: 99,
                background: sinApi ? COLOR.rojo : COLOR.verde,
                display: "inline-block",
              }}
            />
            {sinApi ? "API sin conexión" : `API v${salud?.version ?? "…"}`}
          </div>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <header
          className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3"
          style={{ borderColor: "var(--borde)" }}
        >
          <div>
            <h2 className="text-base font-semibold">{actual.titulo}</h2>
            <p className="text-xs" style={{ color: "var(--texto-suave)" }}>
              {actual.descripcion}
            </p>
          </div>
          <div className="flex gap-1 md:hidden">
            {MENU.map((m) => (
              <button
                key={m.id}
                onClick={() => setVista(m.id)}
                className="btn px-2 py-1 text-xs"
                style={{
                  borderColor: m.id === vista ? COLOR.acento : "var(--borde)",
                  color: m.id === vista ? COLOR.acento : "var(--texto-suave)",
                }}
                title={m.titulo}
              >
                {m.icono}
              </button>
            ))}
          </div>
        </header>

        <div className="p-4">
          {sinApi && (
            <div className="mb-4">
              <Aviso tono="error" titulo="No hay conexión con la API">
                Inicie el backend con <code>uvicorn app.main:app --port 8000</code> desde la carpeta
                <code> backend/</code>.
              </Aviso>
            </div>
          )}
          {aviso && (
            <div className="mb-4">
              <Aviso tono="ok">{aviso}</Aviso>
            </div>
          )}

          {vista === "dashboard" && <Dashboard />}
          {vista === "entrada" && <MesaEntrada />}
          {vista === "recursos" && <Recursos />}
          {vista === "simulador" && <Simulador />}
          {vista === "calendario" && <Calendario />}
          {vista === "calidad" && <CalidadDatos />}
        </div>
      </main>
    </div>
  );
}
