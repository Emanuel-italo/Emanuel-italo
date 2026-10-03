from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FD = "/tmp/package/files/bricolage-grotesque-latin-{}-normal.woff"
fonts = {w: TTFont(FD.format(w)) for w in (400, 500, 700, 800)}

# ---------- paleta ----------
BG = "#1C2C6E"      # azul planta baixa
GRID = "#2B3F8C"
INK = "#F4F6FF"     # porcelana
SUB = "#B7C4F4"
TOP, LEFT, RIGHT = "#F4F6FF", "#C9D2F5", "#93A2E0"
AMB_T, AMB_L, AMB_R = "#FFD25A", "#F2AE2E", "#D48913"
SLOT = "#0F1A4A"


def text_path(txt, weight, size, x, y, fill, matrix=None, tracking=0):
    """Converte texto em <path> (não depende de fonte instalada no visitante)."""
    f = fonts[weight]
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    upm = f["head"].unitsPerEm
    s = size / upm
    pen = SVGPathPen(gs)
    cx = 0
    for ch in txt:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        tp = TransformPen(pen, (s, 0, 0, -s, cx, 0))
        gs[g].draw(tp)
        cx += f["hmtx"][g][0] * s + tracking
    d = pen.getCommands()
    tr = f'translate({x:.2f},{y:.2f})'
    if matrix:
        tr = f'matrix({",".join(f"{v:.4f}" for v in matrix)})'
    return f'<path transform="{tr}" fill="{fill}" d="{d}"/>', cx


def text_width(txt, weight, size, tracking=0):
    return text_path(txt, weight, size, 0, 0, "#000", tracking=tracking)[1]


# ---------- projeção isométrica 2:1 ----------
class Iso:
    def __init__(self, a, ox, oy):
        self.a, self.ox, self.oy = a, ox, oy

    def p(self, x, y, z):
        a = self.a
        return (self.ox + (x - y) * a, self.oy + (x + y) * a / 2 - z * a)

    def poly(self, pts, fill, extra=""):
        s = " ".join(f"{u:.1f},{v:.1f}" for u, v in (self.p(*q) for q in pts))
        return f'<polygon points="{s}" fill="{fill}" {extra}/>'

    def box(self, x, y, z, dx, dy, dz, top, left, right, extra=""):
        X, Y, Z = x + dx, y + dy, z + dz
        return "".join([
            self.poly([(x, Y, z), (X, Y, z), (X, Y, Z), (x, Y, Z)], left, extra),
            self.poly([(X, y, z), (X, Y, z), (X, Y, Z), (X, y, Z)], right, extra),
            self.poly([(x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)], top, extra),
        ])


def iso_grid_pattern(a, color, pid):
    w, h = 2 * a, a
    return (f'<pattern id="{pid}" width="{w}" height="{h}" patternUnits="userSpaceOnUse">'
            f'<path d="M0 0L{w} {h}M0 {h}L{w} 0" stroke="{color}" stroke-width="1" fill="none"/>'
            f'</pattern>')


# =====================================================================
# HEADER: esteira de automação
# =====================================================================
def header():
    W, H = 1200, 420
    iso = Iso(30, 650, 130)
    out = []

    BELT_Y0, BELT_Y1, BZ = 0.0, 2.0, 0.45
    BX0, BX1 = -1.0, 15.0
    MX0, MX1, MY0, MY1, MZ = 5.5, 9.0, -0.7, 2.7, 3.4

    # trilho / esteira
    out.append(iso.box(BX0, BELT_Y0, 0, BX1 - BX0, BELT_Y1 - BELT_Y0, BZ, "#3A4FA6", "#22337A", "#2A3C8A"))
    # faixas da esteira em movimento (recortadas no topo)
    top_pts = [iso.p(BX0, BELT_Y0, BZ), iso.p(BX1, BELT_Y0, BZ), iso.p(BX1, BELT_Y1, BZ), iso.p(BX0, BELT_Y1, BZ)]
    out.append('<clipPath id="beltTop"><polygon points="' + " ".join(f"{u:.1f},{v:.1f}" for u, v in top_pts) + '"/></clipPath>')
    stripes = []
    step = 0.9
    x = BX0 - 2 * step
    while x < BX1 + step:
        a1, a2 = iso.p(x, BELT_Y0, BZ), iso.p(x, BELT_Y1, BZ)
        stripes.append(f'<line x1="{a1[0]:.1f}" y1="{a1[1]:.1f}" x2="{a2[0]:.1f}" y2="{a2[1]:.1f}"/>')
        x += step
    sdx, sdy = step * iso.a, step * iso.a / 2
    out.append(f'<g clip-path="url(#beltTop)"><g class="belt" stroke="#4E64BD" stroke-width="3">{"".join(stripes)}</g></g>')

    SPEED = 2.0      # unidades por segundo
    T = 8.4          # ciclo
    N = 3
    ux, uy = iso.a, iso.a / 2  # deslocamento de tela por unidade em x

    css = [f"""
    .belt{{animation:belt {step/SPEED:.3f}s linear infinite}}
    @keyframes belt{{from{{transform:translate(0,0)}}to{{transform:translate({sdx:.2f}px,{sdy:.2f}px)}}}}
    .lamp{{animation:lamp {T/N:.2f}s steps(1) infinite;opacity:.25}}
    @keyframes lamp{{0%{{opacity:.25}}45%{{opacity:1}}70%{{opacity:.25}}}}
    """]

    # ---- entradas: papéis (desenhados ANTES da máquina) ----
    in_x0, in_x1 = -1.6, 7.0
    t_in = (in_x1 - in_x0) / SPEED
    p_in = t_in / T * 100
    css.append(f"""
    @keyframes paper{{
      0%{{transform:translate({in_x0*ux:.1f}px,{in_x0*uy:.1f}px);opacity:0}}
      4%{{opacity:1}}
      {p_in:.2f}%{{transform:translate({in_x1*ux:.1f}px,{in_x1*uy:.1f}px);opacity:1}}
      {p_in+0.01:.2f}%,100%{{transform:translate({in_x1*ux:.1f}px,{in_x1*uy:.1f}px);opacity:0}}
    }}""")

    def paper(i):
        g = []
        g.append(iso.box(0, 0.35, BZ, 1.3, 1.3, 0.07, "#FFFFFF", "#D4DAF2", "#B9C2E8"))
        for k in range(4):
            yy = 0.6 + k * 0.22
            ln = 0.9 if k < 3 else 0.55
            a1, a2 = iso.p(0.2, yy, BZ + 0.071), iso.p(0.2 + ln, yy, BZ + 0.071)
            g.append(f'<line x1="{a1[0]:.1f}" y1="{a1[1]:.1f}" x2="{a2[0]:.1f}" y2="{a2[1]:.1f}" stroke="#9AA6D6" stroke-width="1.6" stroke-linecap="round"/>')
        return f'<g class="pp p{i}" style="animation:paper {T}s linear infinite;animation-delay:-{i*T/N:.2f}s">{"".join(g)}</g>'

    # ---- saídas: cubos (desenhados DEPOIS da máquina, recortados na boca) ----
    out_x0, out_x1 = 7.9, 14.6
    gap = 0.35
    t_start = t_in + gap
    p_s = t_start / T * 100
    p_e = (t_start + (out_x1 - out_x0) / SPEED) / T * 100
    css.append(f"""
    @keyframes cube{{
      0%,{p_s-0.01:.2f}%{{transform:translate({out_x0*ux:.1f}px,{out_x0*uy:.1f}px);opacity:0}}
      {p_s:.2f}%{{transform:translate({out_x0*ux:.1f}px,{out_x0*uy:.1f}px);opacity:1}}
      {p_e-4:.2f}%{{opacity:1}}
      {p_e:.2f}%,100%{{transform:translate({out_x1*ux:.1f}px,{out_x1*uy:.1f}px);opacity:0}}
    }}""")
    if p_e > 100:
        raise SystemExit(f"ciclo curto demais: {p_e}")

    def cube(i):
        return (f'<g style="animation:cube {T}s linear infinite;animation-delay:-{i*T/N:.2f}s">'
                + iso.box(0, 0.45, BZ, 1.1, 1.1, 1.1, AMB_T, AMB_L, AMB_R) + "</g>")

    out.append("".join(paper(i) for i in range(N)))

    # máquina
    out.append(iso.box(MX0, MY0, 0, MX1 - MX0, MY1 - MY0, MZ, TOP, LEFT, RIGHT))
    # tampa superior com recuo
    out.append(iso.box(MX0 + 0.5, MY0 + 0.5, MZ, MX1 - MX0 - 1.0, MY1 - MY0 - 1.0, 0.35, "#FFFFFF", "#DCE2FA", "#AEBBEA"))
    # boca de saída na face frontal-direita
    out.append(iso.poly([(MX1, 0.25, BZ), (MX1, 1.75, BZ), (MX1, 1.75, BZ + 1.45), (MX1, 0.25, BZ + 1.45)], SLOT))
    # painel na face frontal-esquerda: três lâmpadas
    for k in range(3):
        cxp, cyp = iso.p(MX0 + 0.9 + k * 0.75, MY1, 2.55)
        out.append(f'<ellipse cx="{cxp:.1f}" cy="{cyp:.1f}" rx="7" ry="8" fill="{SLOT}"/>')
        out.append(f'<ellipse class="lamp" style="animation-delay:{k*0.18:.2f}s" cx="{cxp:.1f}" cy="{cyp:.1f}" rx="4.6" ry="5.4" fill="{AMB_T}"/>')
    # ranhuras de ventilação
    for k in range(4):
        a1, a2 = iso.p(MX0 + 0.8, MY1, 1.6 - k * 0.28), iso.p(MX1 - 0.8, MY1, 1.6 - k * 0.28)
        out.append(f'<line x1="{a1[0]:.1f}" y1="{a1[1]:.1f}" x2="{a2[0]:.1f}" y2="{a2[1]:.1f}" stroke="#A7B3E6" stroke-width="2.4" stroke-linecap="round"/>')

    mouth = [iso.p(MX1, 0.25, BZ - 0.1), iso.p(MX1, 1.75, BZ - 0.1), iso.p(MX1, 1.75, BZ + 1.45),
             iso.p(MX1, 0.25, BZ + 1.45), iso.p(30, 0.25, BZ + 1.45), iso.p(30, 1.75, BZ + 1.45),
             iso.p(30, 1.75, BZ - 0.1)]
    # recorte: tudo à frente do plano da boca (x >= MX1) dentro da faixa da esteira
    reg = [iso.p(MX1, 0.25, BZ + 1.45), iso.p(30, 0.25, BZ + 1.45), iso.p(30, 1.75, BZ + 1.45),
           iso.p(30, 1.75, BZ - 0.1), iso.p(MX1, 1.75, BZ - 0.1), iso.p(MX1, 1.75, BZ + 1.45)]
    out.append('<clipPath id="exit"><polygon points="' + " ".join(f"{u:.1f},{v:.1f}" for u, v in reg) + '"/></clipPath>')
    out.append('<g clip-path="url(#exit)">' + "".join(cube(i) for i in range(N)) + "</g>")

    # ---- texto ----
    txt = []
    p, _ = text_path("Emanuel", 800, 92, 64, 150, INK, tracking=-2)
    txt.append(p)
    p, _ = text_path("Italo", 800, 92, 64, 238, INK, tracking=-2)
    txt.append(p)
    p, _ = text_path("Transformo processo manual em", 400, 24, 66, 296, SUB)
    txt.append(p)
    p, _ = text_path("sistema que roda sozinho.", 400, 24, 66, 328, SUB)
    txt.append(p)
    p, _ = text_path("Automação e IA no Bradesco  /  ADS na FIAP", 500, 15, 66, 374, "#8496DA", tracking=0.4)
    txt.append(p)

    css.append("""
    @media (prefers-reduced-motion: reduce){
      .belt,.lamp,g[style]{animation:none!important}
      .lamp{opacity:1}
    }""")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Emanuel Italo, automação e IA">
<title>Emanuel Italo</title>
<style>{"".join(css)}</style>
<defs>{iso_grid_pattern(28, GRID, "g")}
<linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="{BG}"/><stop offset=".45" stop-color="{BG}" stop-opacity=".2"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#g)" opacity=".55"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#fade)"/>
{"".join(out)}
{"".join(txt)}
</svg>'''
    return svg


# =====================================================================
# STACK: teclas isométricas
# =====================================================================
def stack():
    keys = ["Python", "Java", "Spring\nBoot", "Angular", "SQL",
            "Docker", "RPA", "LLM +\nRAG", "Power\nPlatform", "ESP32"]
    W, H = 1200, 400
    a = 30
    iso = Iso(a, 0, 0)
    K, GAP, KZ = 2.6, 0.45, 0.7
    cols, rows = 5, 2
    # centraliza
    pts = [iso.p(c * (K + GAP), r * (K + GAP), 0) for c in range(cols + 1) for r in range(rows + 1)]
    minx = min(p[0] for p in pts) - a * K
    maxx = max(p[0] for p in pts) + a * K
    iso.ox = (W - (maxx - minx)) / 2 - minx + 150
    iso.oy = 78

    css = []
    parts = []
    n = len(keys)
    T = n * 0.9
    order = sorted(range(n), key=lambda i: divmod(i, cols)[0] + divmod(i, cols)[1])
    for idx in order:
        r, c = divmod(idx, cols)
        x0, y0 = c * (K + GAP), r * (K + GAP)
        base = iso.box(x0, y0, 0, K, K, 0.25, "#24357F", "#15225C", "#1A2968")
        # tecla: corpo + topo recuado
        body = iso.box(x0 + 0.1, y0 + 0.1, 0.25, K - 0.2, K - 0.2, KZ, TOP, LEFT, RIGHT)
        hl = iso.box(x0 + 0.1, y0 + 0.1, 0.25, K - 0.2, K - 0.2, KZ, AMB_T, AMB_L, AMB_R)
        # rótulo no plano do topo (aceita 2 linhas)
        lines = keys[idx].split("\n")
        size = 22
        lh = size * 1.08
        widths = [text_width(l, 700, size) for l in lines]
        maxw = (K - 0.7) * a
        scale = min(1.0, maxw / max(widths))
        k = scale / a
        ox, oy = iso.p(x0 + K / 2, y0 + K / 2, 0.25 + KZ)
        m = (k * a, k * a / 2, -k * a, k * a / 2, ox, oy)
        inner = []
        for li, (l, wl) in enumerate(zip(lines, widths)):
            by = (li - (len(lines) - 1) / 2) * lh + size * 0.36
            pth, _ = text_path(l, 700, size, -wl / 2, by, BG)
            inner.append(pth)
        label = f'<g transform="matrix({",".join(f"{v:.4f}" for v in m)})">{"".join(inner)}</g>'
        delay = idx * T / n
        css.append(f".k{idx} .hl{{animation:hl {T:.1f}s linear infinite;animation-delay:{delay:.2f}s}}"
                   f".k{idx} .cap{{animation:press {T:.1f}s linear infinite;animation-delay:{delay:.2f}s}}")
        parts.append(f'<g class="k{idx}">{base}<g class="cap"><g>{body}</g><g class="hl" opacity="0">{hl}</g>{label}</g></g>')

    frac = 100 / n
    css.insert(0, f"""
    @keyframes press{{0%{{transform:translate(0,0)}}{frac*0.15:.2f}%,{frac*0.7:.2f}%{{transform:translate(0,{0.3*a:.1f}px)}}{frac*0.9:.2f}%,100%{{transform:translate(0,0)}}}}
    @keyframes hl{{0%{{opacity:0}}{frac*0.1:.2f}%,{frac*0.75:.2f}%{{opacity:1}}{frac*0.85:.2f}%,100%{{opacity:0}}}}
    @media (prefers-reduced-motion: reduce){{.cap,.hl{{animation:none!important}}}}
    """)

    title, _ = text_path("No meu teclado", 700, 30, 64, 150, INK, tracking=-0.5)
    s1, _ = text_path("O que eu uso para colocar", 400, 18, 64, 186, SUB)
    s2, _ = text_path("automação em produção.", 400, 18, 64, 210, SUB)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Stack: {", ".join(keys)}">
<title>Stack de Emanuel Italo</title>
<style>{"".join(css)}</style>
<defs>{iso_grid_pattern(30, GRID, "g2")}</defs>
<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#g2)" opacity=".45"/>
{"".join(parts)}
{title}{s1}{s2}
</svg>'''


import os
os.makedirs("/mnt/user-data/outputs/Emanuel-italo/assets", exist_ok=True)
open("/mnt/user-data/outputs/Emanuel-italo/assets/header.svg", "w").write(header())
open("/mnt/user-data/outputs/Emanuel-italo/assets/stack.svg", "w").write(stack())
print("ok")
