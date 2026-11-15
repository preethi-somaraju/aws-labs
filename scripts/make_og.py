"""Render a 1200x630 Open Graph card to PNG.

LinkedIn, Slack and X show a grey placeholder when a page has no og:image, so
every published page needs one.

    python scripts/make_og.py "Lab 01 - Account foundations" out.png \
        --kicker "AWS data engineering labs" --sub "week 1 of 52"
"""
import argparse
import html
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

TEMPLATE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ width: 1200px; height: 630px; background: #fff; display: flex;
         font-family: "Amazon Ember","Helvetica Neue",Helvetica,Arial,sans-serif; }}
  .bar {{ width: 14px; background: #ff9900; }}
  .inner {{ flex: 1; padding: 72px 80px; display: flex; flex-direction: column;
           justify-content: space-between; }}
  .kicker {{ font-size: 24px; font-weight: 700; color: #ff9900;
            text-transform: uppercase; letter-spacing: 1.5px; }}
  h1 {{ font-size: {size}px; line-height: 1.15; color: #232f3e; font-weight: 700; }}
  .sub {{ font-size: 26px; color: #5f6b7a; margin-top: 18px; }}
  .foot {{ font-size: 24px; color: #5f6b7a; display: flex;
          justify-content: space-between; border-top: 1px solid #d5dbdb;
          padding-top: 22px; }}
  .foot b {{ color: #232f3e; }}
</style></head><body>
  <div class="bar"></div>
  <div class="inner">
    <div class="kicker">{kicker}</div>
    <div>
      <h1>{title}</h1>
      {sub}
    </div>
    <div class="foot"><span><b>Preethi Somaraju</b> &middot; Data engineer</span>
      <span>preethi-somaraju.github.io</span></div>
  </div>
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("title")
    ap.add_argument("out")
    ap.add_argument("--kicker", default="AWS data engineering labs")
    ap.add_argument("--sub", default="")
    args = ap.parse_args()

    size = 68 if len(args.title) < 46 else 56 if len(args.title) < 70 else 46
    doc = TEMPLATE.format(
        title=html.escape(args.title), kicker=html.escape(args.kicker),
        sub=f'<div class="sub">{html.escape(args.sub)}</div>' if args.sub else "",
        size=size)

    tmp = Path(tempfile.gettempdir()) / "og-card.html"
    tmp.write_text(doc, encoding="utf-8")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630})
        pg.goto(tmp.as_uri())
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(out))
        b.close()
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
