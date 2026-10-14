"""Generate the three architecture .drawio files. Usage: python docs/architecture/generate.py docs/architecture"""
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

OUT = Path(sys.argv[1])
FONT = "Helvetica"
INK, MUTED, EDGE = "#13202E", "#5B6875", "#46525F"
C = {"cpu": "#1F5FAD", "gpu": "#6B3FB5", "decide": "#D17F00", "data": "#00796B", "out": "#2E7D32",
     "kpi": "#0F2540"}


def lbl(title, sub=""):
    s = f"<b style='font-size:17px'>{title}</b>"
    if sub:
        s += f"<br><span style='font-size:13px;opacity:0.9'>{sub}</span>"
    return s


class D:
    def __init__(self, name, w, h):
        self.name, self.w, self.h, self.cells, self.n = name, w, h, [], 0
        self.zones = []

    def _id(self):
        self.n += 1
        return f"c{self.n}"

    def v(self, value, x, y, w, h, style, zone=False):
        i, parent = self._id(), "1"
        for zi, zx, zy, zw, zh in self.zones:
            if not zone and zx <= x and zy <= y and x + w <= zx + zw and y + h <= zy + zh:
                parent, x, y = zi, x - zx, y - zy
        if zone:
            self.zones.append((i, x, y, w, h))
        self.cells.append(f'<mxCell id="{i}" value={quoteattr(value)} style="{style}" vertex="1" parent="{parent}">'
                          f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return i

    def box(self, role, title, sub, x, y, w=190, h=100):
        st = (f"rounded=1;arcSize=12;whiteSpace=wrap;html=1;fillColor={C[role]};strokeColor=none;"
              f"fontFamily={FONT};fontColor=#FFFFFF;align=center;verticalAlign=middle;spacing=10;shadow=1;")
        return self.v(lbl(title, sub), x, y, w, h, st)

    def cyl(self, title, sub, x, y, w=170, h=110, role="data"):
        st = (f"shape=cylinder3;boundedLbl=1;size=14;whiteSpace=wrap;html=1;fillColor={C[role]};"
              f"strokeColor=none;fontFamily={FONT};fontColor=#FFFFFF;spacing=6;shadow=1;")
        return self.v(lbl(title, sub), x, y, w, h, st)

    def doc(self, title, sub, x, y, w=170, h=110):
        st = (f"shape=document;boundedLbl=1;size=0.16;whiteSpace=wrap;html=1;fillColor={C['out']};"
              f"strokeColor=none;fontFamily={FONT};fontColor=#FFFFFF;spacing=6;shadow=1;")
        return self.v(lbl(title, sub), x, y, w, h, st)

    def zone(self, title, x, y, w, h):
        st = (f"rounded=1;arcSize=4;html=1;fillColor=#F4F6F9;strokeColor=#D9DEE4;fontFamily={FONT};"
              f"fontSize=13;fontStyle=1;fontColor={MUTED};align=left;verticalAlign=top;spacingLeft=16;"
              f"spacingTop=10;container=1;pointerEvents=0;collapsible=0;")
        return self.v(title.upper(), x, y, w, h, st, zone=True)

    def text(self, value, x, y, w, h, size=13, color=INK, align="left", bold=False):
        st = (f"text;html=1;whiteSpace=wrap;fontFamily={FONT};fontSize={size};fontColor={color};"
              f"align={align};verticalAlign=middle;" + ("fontStyle=1;" if bold else ""))
        return self.v(value, x, y, w, h, st)

    def kpi(self, big, small, x, y, w, h=84):
        st = (f"rounded=1;arcSize=14;whiteSpace=wrap;html=1;fillColor={C['kpi']};strokeColor=none;"
              f"fontFamily={FONT};fontColor=#FFFFFF;align=center;verticalAlign=middle;")
        return self.v(f"<b style='font-size:30px'>{big}</b><br>"
                      f"<span style='font-size:14px;color:#AFC2D8'>{small}</span>", x, y, w, h, st)

    def e(self, s, t, label="", ex=None, ey=None, nx=None, ny=None, dashed=False, pts=(), bold=True):
        i = self._id()
        st = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
              f"endArrow=block;endFill=1;endSize=9;strokeWidth=2.5;strokeColor={EDGE};fontFamily={FONT};"
              f"fontSize=14;fontColor={INK};labelBackgroundColor=#FFFFFF;" + ("fontStyle=1;" if bold else ""))
        if ex is not None:
            st += f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;"
        if nx is not None:
            st += f"entryX={nx};entryY={ny};entryDx=0;entryDy=0;"
        if dashed:
            st += "dashed=1;dashPattern=8 5;"
        geo = '<mxGeometry relative="1" as="geometry">'
        if pts:
            geo += '<Array as="points">' + "".join(f'<mxPoint x="{a}" y="{b}"/>' for a, b in pts) + "</Array>"
        geo += "</mxGeometry>"
        self.cells.append(f'<mxCell id="{i}" value={quoteattr(label)} style="{st}" edge="1" parent="1" '
                          f'source="{s}" target="{t}">{geo}</mxCell>')

    def legend(self, x, y, items):
        for k, (role, name) in enumerate(items):
            self.v("", x + 160 * k, y + 6, 22, 22, f"rounded=1;arcSize=20;html=1;fillColor={C[role]};strokeColor=none;")
            self.text(name, x + 160 * k + 30, y, 120, 34, size=14, color=MUTED)

    def header(self, title, sub):
        self.text(title, 40, 22, self.w - 80, 40, size=30, bold=True)
        self.text(sub, 40, 64, self.w - 80, 26, size=16, color=MUTED)

    def save(self):
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="drawio" version="26.0.0">'
               f'<diagram name="{self.name}" id="{self.name}"><mxGraphModel dx="{self.w}" dy="{self.h}" grid="1" '
               f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
               f'pageWidth="{self.w}" pageHeight="{self.h}" background="#FFFFFF" math="0" shadow="0"><root>'
               '<mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(self.cells) +
               "</root></mxGraphModel></diagram></mxfile>\n")
        (OUT / f"{self.name}.drawio").write_text(xml)


# ---------------------------------------------------------------- 1. system architecture
d = D("system-architecture", 2120, 800)
d.header("Business entity resolution", "Batch pipeline · test-set scale")
for k, (a, b) in enumerate([("1.73M", "query records (S1)"), ("9.97M", "pool records (S2 + S3)"),
                            ("10¹³ → 10⁷", "candidate pairs"), ("0.984", "public F0.5")]):
    d.kpi(a, b, 40 + k * 515, 110, 490)

lz = d.zone("Lexical path", 490, 230, 1110, 180)
d.zone("Dense path", 490, 490, 1110, 180)
s1 = d.cyl("S1", "1.73M", 40, 300)
pool = d.cyl("Pool", "9.97M", 40, 470)
nrm = d.box("cpu", "Normalize", "9 Indic scripts", 270, 400, 170, 100)
idx = d.box("cpu", "Inverted index", "10 key families", 520, 290, 170)
rr = d.box("cpu", "Re-ranker", "LightGBM", 810, 290, 170)
ce = d.box("gpu", "Cross-encoder", "LoRA · 568M", 1105, 290, 170)
clf = d.box("cpu", "Pair classifier", "LightGBM · 85 feat.", 1400, 290, 170)
bi = d.box("gpu", "Bi-encoder kNN", "e5 · 118M", 520, 550)
cp = d.box("gpu", "Copy expansion", "kNN of accepted", 960, 550)
gt = d.box("decide", "Cross-encoder gate", "p ≥ 0.995", 1390, 550)
own = d.box("decide", "One-owner", "1 S1 per record", 1680, 400, 170, 120)
out = d.doc("Matches", "5.8M pairs", 1910, 405, 170, 110)

d.e(s1, nrm, ex=1, ey=0.5, nx=0, ny=0.3)
d.e(pool, nrm, ex=1, ey=0.5, nx=0, ny=0.7)
d.e(nrm, idx, ex=0.5, ey=0, nx=0, ny=0.5)
d.e(nrm, bi, ex=0.5, ey=1, nx=0, ny=0.5)
d.e(idx, rr, "290 per S1", ex=1, ey=0.5, nx=0, ny=0.5)
d.e(rr, ce, "6.1 per S1", ex=1, ey=0.5, nx=0, ny=0.5)
d.e(ce, clf, ex=1, ey=0.5, nx=0, ny=0.5)
d.e(bi, cp, ex=1, ey=0.5, nx=0, ny=0.5)
d.e(cp, gt, ex=1, ey=0.5, nx=0, ny=0.5)
d.e(clf, cp, "seeds", ex=0.5, ey=1, nx=0.5, ny=0, dashed=True, pts=[(1485, 450), (1055, 450)])
d.e(clf, own, "p ≥ 0.73", ex=1, ey=0.5, nx=0.5, ny=0)
d.e(gt, own, ex=1, ey=0.5, nx=0.5, ny=1)
d.e(own, out, ex=1, ey=0.5, nx=0, ny=0.5)
d.legend(40, 730, [("cpu", "CPU"), ("gpu", "GPU"), ("decide", "Decision"), ("data", "Data"), ("out", "Output")])
d.save()

# ---------------------------------------------------------------- 2. compute and data plane
d = D("compute-and-data-plane", 1880, 820)
d.header("Compute and data plane", "Out-of-core CPU · stateless GPU jobs · checkpoint per chunk")
d.zone("CPU host", 40, 120, 520, 620)
d.zone("Storage", 680, 120, 400, 620)
gz = d.zone("GPU jobs · A100 / H200 / T4", 1200, 120, 640, 620)
W, X = 440, 80
c1 = d.box("cpu", "Ingest + normalize", "1M-row chunks", X, 180, W, 90)
c2 = d.box("cpu", "Index build", "map → 64 shards → reduce", X, 320, W, 90)
c3 = d.box("cpu", "Candidate retrieval", "mmap postings", X, 460, W, 90)
c4 = d.box("cpu", "LightGBM", "3.9M training rows", X, 600, W, 90)
pq_ = d.cyl("Parquet", "13 GB", 790, 175, 180, 120)
hf = d.cyl("HF dataset", "pairs · scores", 790, 380, 180, 120)
git = d.cyl("Git LFS", "models", 790, 585, 180, 120)
g1 = d.box("gpu", "Cross-encoder scoring", "7.3K pairs/s · H200", 1240, 180, 560, 90)
g2 = d.box("gpu", "kNN retrieval", "20K records/s · H200", 1240, 320, 560, 90)
g3 = d.box("gpu", "Distillation", "7 min · A100", 1240, 460, 560, 90)
g4 = d.box("gpu", "LoRA fine-tune", "6.5 h · T4", 1240, 600, 560, 90)
for a, b in [(c1, c2), (c2, c3), (c3, c4)]:
    d.e(a, b, ex=0.5, ey=1, nx=0.5, ny=0)
d.e(c1, pq_, "write", ex=1, ey=0.5, nx=0, ny=0.4)
d.e(pq_, hf, "upload", ex=0.5, ey=1, nx=0.5, ny=0)
d.e(hf, gz, "inputs", ex=1, ey=0.3, nx=0, ny=0.4677)
d.e(gz, hf, "chunks", ex=0, ey=0.5806, nx=1, ny=0.7)
d.e(hf, c4, "scores", ex=0, ey=0.75, nx=1, ny=0.3)
d.e(c4, git, "models", ex=1, ey=0.7, nx=0, ny=0.5)
d.legend(40, 760, [("cpu", "CPU"), ("gpu", "GPU"), ("data", "Storage")])
d.save()

# ---------------------------------------------------------------- 3. training and evaluation
d = D("training-and-evaluation", 1910, 760)
d.header("Training and evaluation", "No S1 in two fits · pool never split · no test labels")
sz = d.zone("Disjoint S1 slices", 1000, 120, 430, 520)
ts = d.cyl("Train S1", "2.21M", 40, 220, 180, 120)
sp = d.box("cpu", "Split", "80 / 20 · stratified", 300, 230, 190, 100)
tr = d.box("cpu", "Train S1", "1.77M", 580, 230, 190, 100)
pl = d.cyl("Pool", "10.3M · never split", 580, 380, 190, 120)
va = d.box("decide", "Validation S1", "441K · score only", 580, 550, 190, 100)
a1 = d.box("cpu", "Blocking + re-ranker", "110K S1", 1040, 175, 350, 90)
a2 = d.box("gpu", "Cross-encoder ep. 1", "180K S1", 1040, 290, 350, 90)
a3 = d.box("gpu", "Cross-encoder ep. 2", "fold 0", 1040, 405, 350, 90)
a4 = d.box("cpu", "Pair classifier", "fold 1", 1040, 520, 350, 90)
pk = d.doc("Model", "matcher.json", 1500, 510, 170, 110)
me = d.cyl("Metrics", "macro F0.5", 1720, 505, 150, 120)
d.e(ts, sp, ex=1, ey=0.5, nx=0, ny=0.5)
d.e(sp, tr, ex=1, ey=0.5, nx=0, ny=0.5)
d.e(sp, va, ex=0.5, ey=1, nx=0, ny=0.5)
d.e(tr, sz, ex=1, ey=0.5, nx=0, ny=0.2115)
d.e(pl, sz, "candidates", ex=1, ey=0.5, nx=0, ny=0.5)
d.e(a4, pk, ex=1, ey=0.5, nx=0, ny=0.5)
d.e(pk, me, ex=1, ey=0.5, nx=0, ny=0.5)
d.e(va, me, "score only", ex=0.5, ey=1, nx=0.5, ny=1, dashed=True, pts=[(675, 690), (1795, 690)])
d.legend(40, 700, [("cpu", "CPU fit"), ("gpu", "GPU fit"), ("decide", "Held out"), ("data", "Data")])
d.save()
