"""Capture AWS Console screenshots for lab write-ups.

Uses a persistent browser profile (playwright_profile/, gitignored) so the
console session survives across runs. Sign in once, headed; every later run is
headless and unattended.

    # first run only - opens a real window, sign in within the wait
    python scripts/capture.py <url> <out.png> --headed --login-wait 180

    # afterwards
    python scripts/capture.py <url> <out.png>

Two guards, both from real failures:
  - the page is checked for a sign-in form before saving, because a lapsed
    session otherwise produces a screenshot of the login page that looks fine
    until someone reads it
  - the account ID is masked, since these are published
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[1]
PROFILE = REPO / "playwright_profile"

# Any of these on the page means we captured a login screen, not the console.
LOGIN_MARKERS = [
    "input[name='username']",
    "input[type='password']",
    "#awsui-input-0",
    "text=Sign in to the AWS Management Console",
    "text=Sign in as IAM user",
]


def account_id(profile: str) -> str | None:
    try:
        r = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--profile", profile,
             "--query", "Account", "--output", "text"],
            capture_output=True, text=True, timeout=60)
        v = r.stdout.strip()
        return v if re.fullmatch(r"\d{12}", v) else None
    except Exception:
        return None


def looks_like_login(page) -> bool:
    for sel in LOGIN_MARKERS:
        try:
            if page.locator(sel).first.is_visible(timeout=800):
                return True
        except Exception:
            continue
    return "signin.aws.amazon.com" in page.url


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--login-wait", type=int, default=0,
                    help="seconds to wait for a manual sign-in before capturing")
    ap.add_argument("--wait-selector")
    ap.add_argument("--wait-ms", type=int, default=2500)
    ap.add_argument("--profile", default="preethi-portfolio")
    ap.add_argument("--full-page", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(exist_ok=True)

    acct = account_id(args.profile)
    if not acct:
        print("WARNING: could not resolve account ID; nothing will be masked")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE),
            headless=not (args.headed or args.login_wait),
            viewport={"width": 1600, "height": 1000},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(args.url, wait_until="domcontentloaded", timeout=90_000)

        if args.login_wait:
            print(f"Sign in now - capturing in {args.login_wait}s")
            page.wait_for_timeout(args.login_wait * 1000)

        if args.wait_selector:
            page.wait_for_selector(args.wait_selector, timeout=60_000)
        page.wait_for_timeout(args.wait_ms)

        if looks_like_login(page):
            print(f"FAIL: landed on a sign-in page, not {args.url}")
            print("      Re-run with --headed --login-wait 180 to refresh the session.")
            ctx.close()
            return 2

        # Mask anything rendering the account ID. Playwright paints these pink.
        masks = []
        if acct:
            for sel in (f"text={acct}", "[data-testid='account-detail-menu']",
                        "[data-testid='awsc-nav-account-menu-button']"):
                try:
                    loc = page.locator(sel)
                    if loc.count():
                        masks.append(loc)
                except Exception:
                    pass

        page.screenshot(path=str(out), full_page=args.full_page,
                        mask=masks, mask_color="#d0d0d0")
        print(f"saved {out}")

        if acct and acct in page.content():
            print("NOTE: account ID present in DOM - verify it is masked in the image")

        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
