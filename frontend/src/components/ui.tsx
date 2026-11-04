import type { ReactNode } from "react";
import type { Severidad } from "../api/client";

export const COLOR = {
  acento: "#4f9dff",
  verde: "#35c48a",
  ambar: "#f0b429",
  rojo: "#f0595c",
  violeta: "#a78bfa",
  cian: "#22d3ee",
  gris: "#64748b",
  borde: "#223047",
  panel: "#121821",
};

export const PALETA_GESTORES = [
  "#4f9dff",
  "#35c48a",
  "#f0b429",
  "#a78bfa",
  "#22d3ee",
  "#f472b6",
  "#fb923c",
  "#a3e635",
];

export function colorGestor(nombre: string, lista: string[]): string {
  const i = lista.indexOf(nombre);
  return i >= 0 ? PALETA_GESTORES[i % PALETA_GESTORES.length] : COLOR.gris;
}

const MAPA_SEV: Record<Severidad, { color: string; fondo: string; texto: string }> = {
  VERDE: { color: COLOR.verde, fondo: "rgba(53,196,138,.12)", texto: "En plazo" },
  AMBAR: { color: COLOR.ambar, fondo: "rgba(240,180,41,.12)", texto: "Margen ajustado" },
  ROJO: { color: COLOR.rojo, fondo: "rgba(240,89,92,.12)", texto: "Retraso" },
  SIN_FECHA: { color: COLOR.gris, fondo: "rgba(100,116,139,.12)", texto: "Sin fecha" },
};

export function Semaforo({ nivel, texto }: { nivel: Severidad; texto?: string }) {
  const s = MAPA_SEV[nivel] ?? MAPA_SEV.SIN_FECHA;
  return (
    <span className="chip" style={{ color: s.color, background: s.fondo, borderColor: `${s.color}44` }}>
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: 999,
          background: s.color,
          display: "inline-block",
        }}
      />
      {texto ?? s.texto}
    </span>
  );
}

export function Kpi({
  titulo,
  valor,
  detalle,
  color,
}: {
  titulo: string;
  valor: string | number;
  detalle?: string;
  color?: string;
}) {
  return (
    <div className="panel p-4">
      <div className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--texto-suave)" }}>
        {titulo}
      </div>
      <div className="mt-1 text-2xl font-semibold" style={{ color: color ?? "var(--texto)" }}>
        {valor}
      </div>
      {detalle && (
        <div className="mt-0.5 text-xs" style={{ color: "var(--texto-suave)" }}>
          {detalle}
        </div>
      )}
    </div>
  );
}

export function Panel({
  titulo,
  descripcion,
  acciones,
  children,
  className = "",
}: {
  titulo?: string;
  descripcion?: string;
  acciones?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {(titulo || acciones) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3" style={{ borderColor: "var(--borde)" }}>
          <div>
            {titulo && <h2 className="text-sm font-semibold">{titulo}</h2>}
            {descripcion && (
              <p className="mt-0.5 text-xs" style={{ color: "var(--texto-suave)" }}>
                {descripcion}
              </p>
            )}
          </div>
          {acciones && <div className="flex flex-wrap items-center gap-2">{acciones}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Aviso({
  tono = "info",
  titulo,
  children,
}: {
  tono?: "info" | "ok" | "warn" | "error";
  titulo?: string;
  children: ReactNode;
}) {
  const mapa = {
    info: { c: COLOR.acento, bg: "rgba(79,157,255,.08)" },
    ok: { c: COLOR.verde, bg: "rgba(53,196,138,.08)" },
    warn: { c: COLOR.ambar, bg: "rgba(240,180,41,.08)" },
    error: { c: COLOR.rojo, bg: "rgba(240,89,92,.08)" },
  }[tono];

  return (
    <div
      className="rounded-lg border px-3 py-2 text-sm"
      style={{ borderColor: `${mapa.c}44`, background: mapa.bg }}
    >
      {titulo && <div className="font-semibold" style={{ color: mapa.c }}>{titulo}</div>}
      <div style={{ color: "var(--texto-suave)" }}>{children}</div>
    </div>
  );
}

export function Cargando({ texto = "Cargando…" }: { texto?: string }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm" style={{ color: "var(--texto-suave)" }}>
      <span
        className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
        aria-hidden
      />
      {texto}
    </div>
  );
}

export function Vacio({ children }: { children: ReactNode }) {
  return (
    <div className="py-8 text-center text-sm" style={{ color: "var(--texto-suave)" }}>
      {children}
    </div>
  );
}

export function numero(n: number | null | undefined, decimales = 2): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("es-GT", {
    minimumFractionDigits: decimales,
    maximumFractionDigits: decimales,
  });
}

export function fecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}
