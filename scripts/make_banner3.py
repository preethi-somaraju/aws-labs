"""More LinkedIn covers — four further directions.

    python scripts/make_banner3.py <outdir>

Lower-left 430x250 stays clear for the profile photo.
"""
import math
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

W, H = 1584, 396

SHELL = """<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,200;0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,300&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1584px;height:396px;overflow:hidden;position:relative;
     font-family:Newsreader,Georgia,serif;font-optical-sizing:auto;
     -webkit-font-smoothing:antialiased}}
svg.bg{{position:absolute;inset:0;width:1584px;height:396px}}
{css}
</style></head><body>{body}</body></html>"""


def series(seed, n=150, amp=52, base=250, drift=-0.42):
    """A plausible-looking metric line."""
    pts = []
    for i in range(n):
        x = i * (W / (n - 1))
        y = (base + drift * i
             + amp * math.sin(i / 9.0 + seed)
             + (amp * 0.45) * math.sin(i / 3.3 + seed * 2))
        pts.append(f"{x:.1f},{max(28, min(372, y)):.1f}")
    return " ".join(pts)


def contours():
    out = []
    for k in range(13):
        pts = []
        for i in range(90):
            x = i * (W / 89)
            y = (118 + k * 26
                 + 34 * math.sin(i / 13.0 + k * 0.42)
                 + 15 * math.sin(i / 5.0 + k))
            pts.append(f"{x:.1f},{y:.1f}")
        op = 0.10 + (k % 4) * 0.055
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" '
                   f'stroke="#c07a46" stroke-width="{1.5 if k % 4 else 2.4}" '
                   f'opacity="{op:.2f}"/>')
    return "".join(out)


BANNERS = {
# ---- 7. metric lines as artwork --------------------------------------
"07-metrics": dict(css="""
body{background:#14181d}
.veil{position:absolute;inset:0;
  background:linear-gradient(92deg,rgba(20,24,29,.98) 33%,rgba(20,24,29,.55) 70%,rgba(20,24,29,.25) 100%)}
.inner{position:absolute;left:470px;top:50%;transform:translateY(-50%);z-index:4}
h1{font-size:48px;font-weight:300;color:#eef2f6;letter-spacing:-.015em;
   line-height:1.14;margin-bottom:12px}
h1 em{font-style:normal;color:#e09a5a}
p{font-size:20px;font-style:italic;color:#8e9aa6}
.url{margin-top:20px;font-size:14px;letter-spacing:.2em;text-transform:uppercase;
     color:#6a7682}
""", body=f"""
<svg class="bg" viewBox="0 0 {W} {H}" preserveAspectRatio="none">
  <polyline points="{series(0.4)}" fill="none" stroke="#e09a5a" stroke-width="2.4" opacity=".85"/>
  <polyline points="{series(2.1, amp=38, base=215, drift=-.2)}" fill="none" stroke="#5f8fb0" stroke-width="2" opacity=".6"/>
  <polyline points="{series(4.3, amp=26, base=300, drift=.18)}" fill="none" stroke="#7fae8a" stroke-width="1.8" opacity=".45"/>
</svg><div class="veil"></div>
<div class="inner">
  <h1>Data engineer &mdash; <em>building on AWS</em></h1>
  <p>Pipelines, lakes, and the infrastructure underneath.</p>
  <div class="url">preethi-somaraju.github.io</div>
</div>
"""),

# ---- 8. contour lines, warm paper ------------------------------------
"08-contour": dict(css="""
body{background:#f6f2ec}
.veil{position:absolute;inset:0;
  background:linear-gradient(90deg,rgba(246,242,236,.99) 30%,rgba(246,242,236,.72) 62%,rgba(246,242,236,.45) 100%)}
.inner{position:absolute;left:470px;top:50%;transform:translateY(-50%);z-index:4}
h1{font-size:46px;font-weight:300;color:#2d2823;letter-spacing:-.015em;
   line-height:1.16;margin-bottom:12px}
h1 em{font-style:normal;color:#9c6f4f}
p{font-size:20px;font-style:italic;color:#6f665c}
.url{margin-top:20px;font-size:14px;letter-spacing:.2em;text-transform:uppercase;
     color:#9a9084}
""", body=f"""
<svg class="bg" viewBox="0 0 {W} {H}" preserveAspectRatio="none">{contours()}</svg>
<div class="veil"></div>
<div class="inner">
  <h1>Data engineer &mdash; <em>Houston, Texas</em></h1>
  <p>Ten years moving data to where decisions get made.</p>
  <div class="url">preethi-somaraju.github.io</div>
</div>
"""),

# ---- 9. the query, as the banner -------------------------------------
"09-query": dict(css="""
body{background:#101418;display:flex;align-items:center}
.chrome{position:absolute;left:460px;top:48px;right:70px;bottom:48px;
  background:#171c22;border:1px solid #273039;border-radius:8px;overflow:hidden}
.bar{height:34px;background:#1e252c;display:flex;align-items:center;gap:7px;
     padding:0 14px;border-bottom:1px solid #273039}
.d{width:10px;height:10px;border-radius:50%}
.bar span{margin-left:8px;font-family:"JetBrains Mono",monospace;font-size:12px;
          color:#7b8894}
.sql{padding:18px 22px;font-family:"JetBrains Mono",monospace;font-size:16px;
     line-height:1.75;color:#c6d0da}
.kw{color:#e0795a}.st{color:#86b98a}.cm{color:#5f6b77}
.res{padding:4px 22px 0;font-family:"JetBrains Mono",monospace;font-size:12.5px;
     color:#6b7884}
.name{position:absolute;left:470px;top:-2px;z-index:5}
""", body="""
<div class="chrome">
  <div class="bar"><i class="d" style="background:#ff5f57"></i>
    <i class="d" style="background:#febc2e"></i>
    <i class="d" style="background:#28c840"></i>
    <span>preethi — athena</span></div>
  <div class="sql">
<span class="cm">-- data engineer, Houston TX &mdash; building on AWS</span><br>
<span class="kw">SELECT</span> role, cloud, status<br>
<span class="kw">FROM</span> preethi.profile<br>
<span class="kw">WHERE</span> open_to_work = <span class="st">true</span>;
  </div>
  <div class="res">1 row &middot; 0.31s &middot; preethi-somaraju.github.io</div>
</div>
"""),

# ---- 10. the numeral ---------------------------------------------------
"10-numeral": dict(css="""
body{background:#1d1814}
.fifty{position:absolute;right:52px;top:50%;transform:translateY(-52%);
  font-size:290px;font-weight:200;color:#2b231c;line-height:.8;letter-spacing:-.04em}
.inner{position:absolute;left:470px;top:50%;transform:translateY(-50%);z-index:4;
       max-width:760px}
h1{font-size:44px;font-weight:300;color:#f4ece2;letter-spacing:-.015em;
   line-height:1.16;margin-bottom:12px}
h1 em{font-style:normal;color:#d08b55}
p{font-size:20px;font-style:italic;color:#9e9085}
.url{margin-top:20px;font-size:14px;letter-spacing:.2em;text-transform:uppercase;
     color:#766a60}
""", body="""
<div class="fifty">52</div>
<div class="inner">
  <h1>Fifty-two weeks of <em>AWS data engineering</em></h1>
  <p>One lab a week. Terraform, tested, written up &mdash; including what broke.</p>
  <div class="url">preethi-somaraju.github.io</div>
</div>
"""),
}


def main() -> int:
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.gettempdir())
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, spec in BANNERS.items():
            f = tmp / f"b3-{name}.html"
            f.write_text(SHELL.format(css=spec["css"], body=spec["body"]),
                         encoding="utf-8")
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.goto(f.as_uri())
            pg.wait_for_timeout(2300)
            pg.screenshot(path=str(outdir / f"linkedin-banner-{name}.png"))
            print(f"wrote linkedin-banner-{name}.png")
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
