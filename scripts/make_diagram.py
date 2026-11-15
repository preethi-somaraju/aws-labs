"""Build an inline SVG architecture diagram from official AWS icons.

Each lab defines a spec (nodes, edges, optional group boxes) and this emits a
self-contained SVG: icons embedded as <symbol>, no external requests, readable
on a light or dark page.

    python scripts/make_diagram.py <spec.json> <out.svg>

Spec shape:
  {
    "width": 820, "height": 360,
    "groups": [{"x":..,"y":..,"w":..,"h":..,"label":"AWS account"}],
    "nodes":  [{"id":"s3","icon":"s3","x":..,"y":..,
                "label":"Amazon S3","sub":"state bucket"}],
    "edges":  [{"from":"tf","to":"s3","label":"state object"}]
  }

Node x,y is the icon's top-left. Edges route straight between node centres and
are clipped to the icon box, so nodes should be laid out on a loose grid.
"""
import json
import re
import sys
from pathlib import Path

ICONS = Path(__file__).resolve().parents[1] / "assets" / "aws-icons"
ICON = 48          # rendered icon size
LABEL_GAP = 14     # icon bottom to first label baseline


def symbol(name: str) -> str:
    """Icon file as a <symbol>, keeping its own 0 0 64 64 coordinate space."""
    src = (ICONS / f"{name}.svg").read_text(encoding="utf-8")
    inner = re.sub(r"^.*?<svg[^>]*>", "", src, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, flags=re.S)
    inner = re.sub(r"<title>.*?</title>", "", inner, flags=re.S)
    return f'<symbol id="i-{name}" viewBox="0 0 64 64">{inner}</symbol>'


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build(spec: dict) -> str:
    w, h = spec.get("width", 820), spec.get("height", 360)
    nodes = {n["id"]: n for n in spec["nodes"]}
    used = sorted({n["icon"] for n in spec["nodes"] if n.get("icon")})

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="100%" role="img" aria-label="{esc(spec.get("title", "Architecture diagram"))}" '
        'font-family="Amazon Ember, Helvetica Neue, Arial, sans-serif">',
        "<defs>",
        *[symbol(i) for i in used],
        '<marker id="arw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#5f6b7a"/></marker>',
        "</defs>",
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
    ]

    for g in spec.get("groups", []):
        out.append(
            f'<rect x="{g["x"]}" y="{g["y"]}" width="{g["w"]}" height="{g["h"]}" rx="6" '
            f'fill="#fafafa" stroke="{g.get("stroke", "#879196")}" stroke-width="1" '
            f'stroke-dasharray="{g.get("dash", "4 3")}"/>'
        )
        out.append(
            f'<text x="{g["x"] + 10}" y="{g["y"] + 18}" font-size="11" font-weight="600" '
            f'fill="#5f6b7a" letter-spacing="0.4">{esc(g["label"]).upper()}</text>'
        )

    # Edges first so icons sit on top of the lines.
    for e in spec.get("edges", []):
        a, b = nodes[e["from"]], nodes[e["to"]]
        ax, ay = a["x"] + ICON / 2, a["y"] + ICON / 2
        bx, by = b["x"] + ICON / 2, b["y"] + ICON / 2
        pad = ICON / 2 + 6
        dx, dy = bx - ax, by - ay
        dist = max((dx * dx + dy * dy) ** 0.5, 1)
        x1, y1 = ax + dx / dist * pad, ay + dy / dist * pad
        x2, y2 = bx - dx / dist * pad, by - dy / dist * pad
        dash = ' stroke-dasharray="4 3"' if e.get("dashed") else ""
        out.append(
            f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="#5f6b7a" stroke-width="1.5" marker-end="url(#arw)"{dash}/>'
        )
        if e.get("label"):
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - 6
            label = esc(e["label"])
            out.append(
                f'<rect x="{mx - len(label) * 3.1:.0f}" y="{my - 10:.0f}" '
                f'width="{len(label) * 6.2:.0f}" height="15" rx="2" fill="#ffffff"/>'
                f'<text x="{mx:.0f}" y="{my:.0f}" font-size="10.5" fill="#5f6b7a" '
                f'text-anchor="middle">{label}</text>'
            )

    for n in spec["nodes"]:
        cx = n["x"] + ICON / 2
        if n.get("icon"):
            out.append(
                f'<use href="#i-{n["icon"]}" x="{n["x"]}" y="{n["y"]}" '
                f'width="{ICON}" height="{ICON}"/>'
            )
        else:
            out.append(
                f'<rect x="{n["x"]}" y="{n["y"]}" width="{ICON}" height="{ICON}" rx="4" '
                'fill="#ffffff" stroke="#232f3e" stroke-width="1.5"/>'
            )
        y = n["y"] + ICON + LABEL_GAP
        out.append(
            f'<text x="{cx:.0f}" y="{y}" font-size="12" font-weight="600" fill="#232f3e" '
            f'text-anchor="middle">{esc(n["label"])}</text>'
        )
        for i, line in enumerate(n.get("sub", "").split("\n") if n.get("sub") else []):
            out.append(
                f'<text x="{cx:.0f}" y="{y + 14 + i * 12}" font-size="10.5" fill="#5f6b7a" '
                f'text-anchor="middle">{esc(line)}</text>'
            )

    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    missing = [n["icon"] for n in spec["nodes"]
               if n.get("icon") and not (ICONS / f"{n['icon']}.svg").exists()]
    if missing:
        print(f"FAIL: no icon for {missing}. Add it to assets/aws-icons/")
        return 2
    Path(sys.argv[2]).write_text(build(spec), encoding="utf-8")
    print(f"wrote {sys.argv[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
