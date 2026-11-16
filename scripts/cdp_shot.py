"""Screenshot a page in the already-running capture Chrome, over raw CDP.

    python scripts/cdp_shot.py <url> <out.png> [--wait 8] [--height 1100]

Start the browser with scripts/start-chrome.bat and sign in once. No credential
passes through this script; it reuses a tab in a browser you signed in to.

Refuses to write the file if the page is a sign-in screen, or if the account ID
survives redaction. Both have shipped as published mistakes elsewhere.
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
import urllib.request

import websocket

PORT_DEFAULT = 9223
LOGIN_HINTS = ("signin.aws", "Sign in", "awsapps.com/start/#/?tab=accounts")


def account_id(profile: str) -> str | None:
    try:
        r = subprocess.run(["aws", "sts", "get-caller-identity", "--profile", profile,
                            "--query", "Account", "--output", "text"],
                           capture_output=True, text=True, timeout=60)
        v = r.stdout.strip()
        return v if re.fullmatch(r"\d{12}", v) else None
    except Exception:
        return None


def page_target(port: int) -> str:
    targets = json.loads(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/json", timeout=10).read())
    pages = [t for t in targets if t.get("type") == "page"
             and not t.get("url", "").startswith("chrome://")]
    if not pages:
        sys.exit(f"No usable tab on port {port}. Run scripts/start-chrome.bat")
    return pages[0]["webSocketDebuggerUrl"]


class CDP:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=120)
        self.n = 0

    def call(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True)
        return r.get("result", {}).get("value")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    ap.add_argument("--wait", type=int, default=9)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=1100)
    ap.add_argument("--profile", default="preethi-portfolio")
    args = ap.parse_args()

    acct = account_id(args.profile)
    c = CDP(page_target(args.port))
    c.call("Page.enable")
    c.call("Emulation.setDeviceMetricsOverride", width=args.width,
           height=args.height, deviceScaleFactor=1, mobile=False)
    c.call("Page.navigate", url=args.url)
    time.sleep(args.wait)

    cur = c.js("location.href") or ""
    title = c.js("document.title") or ""
    if any(h.lower() in (cur + title).lower() for h in LOGIN_HINTS):
        print(f"FAIL: landed on a sign-in page ({cur[:80]}). Sign in and retry.")
        return 2

    # Dismiss first-run tooltips and dismissible banners; they cover content.
    c.js("""
    (() => {
      let n = 0;
      document.querySelectorAll(
        '[data-testid="tooltip-dismiss"],[aria-label="Close"],[aria-label="Dismiss"],'
        + 'button[class*="dismiss"],[data-analytics*="dismiss"]'
      ).forEach(b => { try { b.click(); n++; } catch (e) {} });
      // Product-tour popovers ignore their own dismiss buttons; drop the node.
      document.querySelectorAll(
        '[role="tooltip"],[class*="tutorial"],[class*="walkthrough"],[class*="hotspot"],'
        + '[data-testid*="tutorial"],[id*="tutorial"]'
      ).forEach(e => { try { e.remove(); n++; } catch (err) {} });
      // Modal dialogs sit above everything; close them before anything else.
      document.querySelectorAll('[role="dialog"] button, [class*="modal"] button')
        .forEach(b => {
          const t = (b.textContent || "").trim().toLowerCase();
          if (t === "cancel" || t === "close" || t === "ok" || t === "dismiss") {
            try { b.click(); n++; } catch (e) {}
          }
        });
      document.querySelectorAll('[role="dialog"],[class*="awsui_dialog"]')
        .forEach(e => { try { e.remove(); n++; } catch (e2) {} });

      // Last resort: find the tour popover by its copy and drop its container.
      const marker = "You can access all AWS services here";
      document.querySelectorAll("div,section").forEach(e => {
        try {
          if (e.textContent && e.textContent.includes(marker)
              && e.textContent.length < 400) { e.remove(); n++; }
        } catch (err) {}
      });
      return n;
    })()""")
    time.sleep(1.5)

    # Replace the account ID in visible text, then confirm it is gone.
    if acct:
        c.js(f"""
        (() => {{
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          const hits = [];
          while (w.nextNode()) if (w.currentNode.nodeValue.includes("{acct}")) hits.push(w.currentNode);
          hits.forEach(n => n.nodeValue = n.nodeValue.replaceAll("{acct}", "<account-id>"));
          return hits.length;
        }})()""")
        if acct in (c.js("document.body.innerText") or ""):
            print("FAIL: account ID still visible after redaction; refusing to write")
            return 3

    data = c.call("Page.captureScreenshot", format="png")["data"]
    with open(args.out, "wb") as fh:
        fh.write(base64.b64decode(data))
    print(f"saved {args.out}  ({title[:60]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
