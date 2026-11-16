"""Render LinkedIn cover photos (1584x396) in the site palette.

    python scripts/make_banner.py <outdir>

LinkedIn overlays the profile photo across the lower-left, and crops the sides
on mobile, so nothing important goes in the left third or the bottom strip.
"""
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

W, H = 1584, 396

SHELL = """<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,200;0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,300&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1584px;height:396px;background:#f6f2ec;overflow:hidden;
     font-family:Newsreader,Georgia,serif;font-optical-sizing:auto;
     color:#2d2823;-webkit-font-smoothing:antialiased;position:relative}}
/* the profile photo sits here; keep it empty */
.safe{{position:absolute;left:0;bottom:0;width:430px;height:260px}}
{css}
</style></head><body>{body}</body></html>"""


BANNERS = {
"01-line": dict(css="""
.inner{position:absolute;right:88px;top:50%;transform:translateY(-50%);
       text-align:right;max-width:980px}
h1{font-size:46px;font-weight:300;letter-spacing:-.015em;line-height:1.2;
   margin-bottom:14px}
p{font-size:21px;font-style:italic;color:#6f665c}
.rule{height:1px;background:#ddd3c4;margin:22px 0 18px;margin-left:auto;width:200px}
.url{font-size:17px;letter-spacing:.14em;text-transform:uppercase;color:#9a9084}
""", body="""
<div class="inner">
  <h1>Data engineer &mdash; building on AWS, in public</h1>
  <p>One lab a week, for a year. Terraform, tested, written up.</p>
  <div class="rule"></div>
  <div class="url">preethi-somaraju.github.io</div>
</div>
"""),

"02-grid": dict(css="""
.inner{position:absolute;right:80px;top:64px;text-align:right}
h1{font-size:34px;font-weight:300;letter-spacing:-.01em;margin-bottom:8px}
p{font-size:18px;font-style:italic;color:#6f665c;margin-bottom:26px}
.weeks{display:grid;grid-template-columns:repeat(26,1fr);gap:6px;width:900px;
       margin-left:auto}
.wk{aspect-ratio:1;border-radius:2px;background:#e7dfd2}
.wk.done{background:#9c6f4f}
.wk.next{background:transparent;border:1.5px dashed #9c6f4f}
.cap{margin-top:16px;font-size:15px;letter-spacing:.14em;text-transform:uppercase;
     color:#9a9084}
""", body="""
<div class="inner">
  <h1>52 weeks of AWS data engineering labs</h1>
  <p>Built, tested and written up &mdash; one a week.</p>
  <div class="weeks">%%WEEKS%%</div>
  <div class="cap">preethi-somaraju.github.io</div>
</div>
"""),

"03-pipeline": dict(css="""
.inner{position:absolute;right:80px;top:50%;transform:translateY(-50%);width:1020px}
h1{font-size:34px;font-weight:300;text-align:right;margin-bottom:34px;
   letter-spacing:-.01em}
.rail{position:relative;height:60px}
.rail::before{content:"";position:absolute;top:13px;left:40px;right:10px;height:1px;
  background:#d8cdbd}
.node{position:absolute;top:0;text-align:center;transform:translateX(-50%)}
.dot{width:11px;height:11px;border-radius:50%;background:#cbbda9;margin:8px auto 10px}
.node.on .dot{background:#9c6f4f;width:14px;height:14px;margin-top:6px}
.node span{font-size:14px;color:#8a8073;letter-spacing:.1em;text-transform:uppercase;
  display:block}
.node.on span{color:#6f665c}
.url{position:absolute;right:0;bottom:-34px;font-size:15px;letter-spacing:.14em;
     text-transform:uppercase;color:#9a9084}
""", body="""
<div class="inner">
  <h1>Data engineer &mdash; Houston, Texas</h1>
  <div class="rail">
    <div class="node" style="left:8%"><div class="dot"></div><span>Qualcomm</span></div>
    <div class="node" style="left:33%"><div class="dot"></div><span>Azure</span></div>
    <div class="node" style="left:58%"><div class="dot"></div><span>Consulting</span></div>
    <div class="node on" style="left:88%"><div class="dot"></div><span>AWS, in public</span></div>
    <div class="url">preethi-somaraju.github.io</div>
  </div>
</div>
"""),
}


def weeks():
    out = []
    for i in range(1, 53):
        cls = "wk done" if i == 1 else "wk next" if i == 2 else "wk"
        out.append(f'<div class="{cls}"></div>')
    return "".join(out)


def main() -> int:
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.gettempdir())

    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, spec in BANNERS.items():
            body = spec["body"].replace("%%WEEKS%%", weeks())
            html = SHELL.format(css=spec["css"], body='<div class="safe"></div>' + body)
            f = tmp / f"banner-{name}.html"
            f.write_text(html, encoding="utf-8")
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.goto(f.as_uri())
            pg.wait_for_timeout(2200)
            pg.screenshot(path=str(outdir / f"linkedin-banner-{name}.png"))
            print(f"wrote linkedin-banner-{name}.png")
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
