"""Convierte los documentos Markdown a PDF usando Chromium (Playwright).

Uso:
    python docs/build_pdf.py

Genera en docs/:
    informe_tecnico.pdf
    guion_video.pdf
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
SALIDA = DOCS / "pdf"

CSS = """
@page {
  size: A4;
  margin: 22mm 18mm 20mm 18mm;
  @bottom-center {
    content: counter(page) " / " counter(pages);
    font-family: "Segoe UI", sans-serif;
    font-size: 8pt;
    color: #7c8798;
  }
  @top-right {
    content: string(doc-title);
    font-family: "Segoe UI", sans-serif;
    font-size: 7.5pt;
    color: #a0aab8;
  }
}

html { font-size: 10pt; }
body {
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  line-height: 1.55;
  color: #1c2530;
  hyphens: auto;
}

/* --- portada del informe --- */
h1:first-of-type {
  string-set: doc-title content();
  font-size: 19pt;
  line-height: 1.25;
  color: #0d1b2a;
  border: none;
  padding: 0;
  margin: 0 0 4mm 0;
}

h1 {
  string-set: doc-title content();
  font-size: 15pt;
  color: #0d1b2a;
  border-bottom: 2.5px solid #2f6fb3;
  padding-bottom: 2mm;
  margin: 9mm 0 4mm 0;
  page-break-after: avoid;
  page-break-before: auto;
}

/* cada sección de primer nivel empieza en página nueva, salvo la primera */
h1:not(:first-of-type) { page-break-before: always; }

h2 {
  font-size: 12pt;
  color: #1b3a5c;
  margin: 6mm 0 2.5mm 0;
  page-break-after: avoid;
}

h3 {
  font-size: 10.5pt;
  color: #2f6fb3;
  margin: 4.5mm 0 2mm 0;
  page-break-after: avoid;
}

p { margin: 0 0 2.4mm 0; text-align: justify; }

hr {
  border: none;
  border-top: 1px solid #dde3ea;
  margin: 5mm 0;
}

/* --- tablas --- */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0 4mm 0;
  font-size: 8.6pt;
  page-break-inside: avoid;
}
thead { background: #eef3f9; }
th {
  text-align: left;
  font-weight: 600;
  color: #1b3a5c;
  padding: 1.7mm 2mm;
  border-bottom: 1.5px solid #b9c9da;
}
td {
  padding: 1.5mm 2mm;
  border-bottom: 0.6px solid #e3e8ee;
  vertical-align: top;
}
tbody tr:nth-child(even) { background: #fafbfd; }
td:first-child, th:first-child { padding-left: 2.2mm; }

/* --- código --- */
code {
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 8.6pt;
  background: #f1f4f8;
  padding: 0.3mm 1.2mm;
  border-radius: 2px;
  color: #1b3a5c;
}

pre {
  background: #f6f8fb;
  border-left: 3px solid #2f6fb3;
  border-radius: 0 3px 3px 0;
  padding: 2.5mm 3mm;
  margin: 2.5mm 0 4mm 0;
  overflow-wrap: break-word;
  white-space: pre-wrap;
  page-break-inside: avoid;
  font-size: 8.4pt;
  line-height: 1.45;
}

pre code {
  background: none;
  padding: 0;
  color: #14283d;
}

/* --- citas: en el guion es el texto hablado --- */
blockquote {
  margin: 2mm 0 3.5mm 0;
  padding: 2.5mm 3.5mm;
  background: #fdf8ec;
  border-left: 3px solid #d9a520;
  border-radius: 0 3px 3px 0;
  font-size: 9.6pt;
  page-break-inside: avoid;
}
blockquote p { margin: 0 0 1.6mm 0; text-align: left; }
blockquote p:last-child { margin-bottom: 0; }
blockquote strong { color: #7a4d00; }

/* --- listas --- */
ul, ol { margin: 0 0 3mm 0; padding-left: 6mm; }
li { margin-bottom: 1mm; }

strong { color: #0d1b2a; }

a { color: #2f6fb3; text-decoration: none; }

/* índice */
h2#índice + ol, h1 + p { page-break-inside: avoid; }

/* evita huérfanos */
p, li { orphans: 2; widows: 2; }
"""


def md_a_html(texto: str, titulo: str) -> str:
    cuerpo = markdown.markdown(
        texto,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "nl2br"],
        extension_configs={"toc": {"permalink": False}},
    )
    # nl2br convierte cada salto en <br>; dentro de bloques de código es inocuo,
    # en párrafos de prosa no lo queremos. Se limpia en el post-proceso.
    cuerpo = re.sub(r"</p>\s*<p>", "</p>\n<p>", cuerpo)
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{titulo}</title>
<style>{CSS}</style>
</head>
<body>
{cuerpo}
</body>
</html>"""


def construir(nombre_md: str, nombre_pdf: str, titulo: str) -> Path:
    origen = DOCS / nombre_md
    texto = origen.read_text(encoding="utf-8")
    # nl2br inserta <br> en cada salto; se desactiva quitándolo de extensiones
    html = md_a_html(texto.replace("nl2br", ""), titulo)

    SALIDA.mkdir(exist_ok=True)
    destino = SALIDA / nombre_pdf

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page()
        pagina.set_content(html, wait_until="load")
        pagina.emulate_media(media="print")
        pagina.pdf(
            path=str(destino),
            format="A4",
            print_background=True,
            display_header_footer=False,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        navegador.close()

    return destino


if __name__ == "__main__":
    sys.path.insert(0, str(DOCS))
    objetivos = [
        ("informe_tecnico.md", "informe_tecnico.pdf", "Informe Técnico — Optimizador de Acompañamiento Docente"),
        ("guion_video.md", "guion_video.pdf", "Guion del Video Explicativo"),
    ]
    for md, pdf, titulo in objetivos:
        ruta = construir(md, pdf, titulo)
        kb = ruta.stat().st_size / 1024
        print(f"OK  {ruta.name}  ({kb:.0f} KB)")
