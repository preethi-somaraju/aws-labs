"""LinkedIn covers with presence — dark grounds, real material, filled frames.

    python scripts/make_banner2.py <outdir>

A banner competes against LinkedIn's white chrome at small size, so these use a
deep ground and a full-bleed visual rather than the restraint that suits the
website. Lower-left stays clear for the profile photo.
"""
import pathlib
import re
import sys
import tempfile

from playwright.sync_api import sync_playwright

W, H = 1584, 396
ICONS = pathlib.Path(__file__).resolve().parents[1] / "assets" / "aws-icons"


def symbol(name):
    src = (ICONS / f"{name}.svg").read_text(encoding="utf-8")
    inner = re.sub(r"^.*?<svg[^>]*>", "", src, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, flags=re.S)
    inner = re.sub(r"<title>.*?</title>", "", inner, flags=re.S)
    return f'<symbol id="i-{name}" viewBox="0 0 64 64">{inner}</symbol>'


SHELL = """<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,200;0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,300&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1584px;height:396px;overflow:hidden;position:relative;
     font-family:Newsreader,Georgia,serif;font-optical-sizing:auto;
     -webkit-font-smoothing:antialiased}}
.safe{{position:absolute;left:0;bottom:0;width:430px;height:250px;z-index:5}}
{css}
</style></head><body><div class="safe"></div>{body}</body></html>"""


TERRAFORM = """resource "aws_s3_bucket" "lake" {
  bucket = "preethi-data-lake"
}

resource "aws_glue_catalog_database" "raw" {
  name = "raw"
}

resource "aws_athena_workgroup" "analytics" {
  name = "analytics"
  configuration {
    enforce_workgroup_configuration = true
    result_configuration {
      output_location = "s3://${aws_s3_bucket.lake.id}/results/"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}"""


BANNERS = {
# ---- 1. deep ink, terraform as texture, type over it -------------------
"04-code": dict(css="""
body{background:#171412}
pre{position:absolute;inset:0;padding:26px 40px;margin:0;
    font-family:"JetBrains Mono",monospace;font-size:14.5px;line-height:1.55;
    color:#6f5f52;opacity:.42;white-space:pre-wrap;column-count:2;column-gap:60px}
.veil{position:absolute;inset:0;
      background:linear-gradient(100deg,rgba(23,20,18,.97) 32%,rgba(23,20,18,.62) 72%,rgba(23,20,18,.9) 100%)}
.inner{position:absolute;left:470px;top:50%;transform:translateY(-50%);z-index:4}
h1{font-size:50px;font-weight:300;color:#f3ece3;letter-spacing:-.015em;
   line-height:1.14;margin-bottom:14px}
h1 em{font-style:normal;color:#d08b55}
p{font-size:21px;font-style:italic;color:#9c9086}
.url{margin-top:22px;font-size:15px;letter-spacing:.2em;text-transform:uppercase;
     color:#6f655d}
""", body=f"""
<pre>{TERRAFORM}</pre><div class="veil"></div>
<div class="inner">
  <h1>Data engineer &mdash; <em>building on AWS</em></h1>
  <p>One lab a week, for a year. Terraform, tested, written up.</p>
  <div class="url">preethi-somaraju.github.io</div>
</div>
"""),

# ---- 2. the pipeline, with real AWS icons, on ink ----------------------
"05-arch": dict(css="""
body{background:#1b2026;
     background-image:radial-gradient(circle at 78% 42%,rgba(208,139,85,.14),transparent 58%)}
.inner{position:absolute;left:460px;top:50%;transform:translateY(-50%);
       width:1050px}
h1{font-size:34px;font-weight:300;color:#eef1f4;letter-spacing:-.01em;
   margin-bottom:6px}
.sub{font-size:18px;font-style:italic;color:#8d98a3;margin-bottom:30px}
.flow{display:flex;align-items:center;gap:0}
.step{text-align:center;width:112px}
.step svg{width:46px;height:46px;display:block;margin:0 auto 10px}
.step span{font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:#93a0ad}
.link{flex:1;height:1px;background:linear-gradient(90deg,#39424c,#5a6672);
      margin-bottom:26px}
.url{margin-top:26px;font-size:14px;letter-spacing:.2em;text-transform:uppercase;
     color:#6d7a87}
""", body="""
<svg width="0" height="0" style="position:absolute"><defs>%%DEFS%%</defs></svg>
<div class="inner">
  <h1>Data engineer &mdash; Houston, Texas</h1>
  <p class="sub">Ingestion, lakes, and the infrastructure underneath.</p>
  <div class="flow">
    <div class="step"><svg><use href="#i-kinesis"/></svg><span>Ingest</span></div>
    <div class="link"></div>
    <div class="step"><svg><use href="#i-s3"/></svg><span>Lake</span></div>
    <div class="link"></div>
    <div class="step"><svg><use href="#i-glue"/></svg><span>Transform</span></div>
    <div class="link"></div>
    <div class="step"><svg><use href="#i-athena"/></svg><span>Query</span></div>
    <div class="link"></div>
    <div class="step"><svg><use href="#i-redshift"/></svg><span>Serve</span></div>
  </div>
  <div class="url">preethi-somaraju.github.io</div>
</div>
"""),

# ---- 3. full-bleed 52 grid as the artwork itself -----------------------
"06-grid": dict(css="""
body{background:#17130f}
.field{position:absolute;inset:0;display:grid;
       grid-template-columns:repeat(26,1fr);grid-template-rows:repeat(2,1fr);
       gap:10px;padding:46px}
.wk{border-radius:3px;background:#2a221c}
.wk.done{background:#d08b55}
.wk.next{background:transparent;border:2px dashed #7d5a3e}
.veil{position:absolute;inset:0;
      background:linear-gradient(95deg,rgba(23,19,15,.97) 36%,rgba(23,19,15,.55) 66%,rgba(23,19,15,.2) 100%)}
.inner{position:absolute;left:470px;top:50%;transform:translateY(-50%);z-index:4;
       max-width:700px}
h1{font-size:44px;font-weight:300;letter-spacing:-.015em;
   line-height:1.16;margin-bottom:12px;color:#f6efe6}
h1 em{font-style:normal;color:#d08b55}
p{font-size:20px;font-style:italic;color:#a2958a}
.url{margin-top:22px;font-size:15px;letter-spacing:.2em;text-transform:uppercase;
     color:#7a6d62}
""", body="""
<div class="field">%%WEEKS%%</div><div class="veil"></div>
<div class="inner">
  <h1>52 weeks of <em>AWS data engineering</em></h1>
  <p>Built, tested and written up &mdash; one lab a week.</p>
  <div class="url">preethi-somaraju.github.io</div>
</div>
"""),
}


def weeks():
    return "".join(
        f'<div class="{"wk done" if i == 1 else "wk next" if i == 2 else "wk"}"></div>'
        for i in range(1, 53))


def main() -> int:
    outdir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.gettempdir())
    defs = "".join(symbol(n) for n in
                   ["kinesis", "s3", "glue", "athena", "redshift"])

    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, spec in BANNERS.items():
            body = spec["body"].replace("%%WEEKS%%", weeks()).replace("%%DEFS%%", defs)
            f = tmp / f"b2-{name}.html"
            f.write_text(SHELL.format(css=spec["css"], body=body), encoding="utf-8")
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.goto(f.as_uri())
            pg.wait_for_timeout(2400)
            pg.screenshot(path=str(outdir / f"linkedin-banner-{name}.png"))
            print(f"wrote linkedin-banner-{name}.png")
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
