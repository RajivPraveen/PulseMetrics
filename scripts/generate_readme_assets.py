"""Capture README previews from the running dashboard, so the README shows the real product.

Start the dashboard first (``make up`` or ``streamlit run dashboard/app.py``), then run
``python scripts/generate_readme_assets.py``. It signs in with the admin account from ``.env``
and writes one screenshot per page to ``assets/previews/``. Requires the optional ``docs``
dependencies and a browser for Playwright (``playwright install chromium``).
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = [("executive", "Business overview"), ("acquisition", "Getting customers"),
         ("engagement", "Product usage"), ("retention", "Keeping customers"),
         ("experimentation", "Onboarding test")]


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=os.getenv("PULSE_DASHBOARD_URL", "http://localhost:8501"))
    parser.add_argument("--out", type=Path, default=ROOT / "assets/previews")
    parser.add_argument("--channel", default=None, help='use an installed browser, e.g. "chrome"')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=args.channel)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1.25)
        page.goto(args.url, wait_until="networkidle")
        page.get_by_role("textbox", name="Username").fill(os.environ["PULSE_ADMIN_USER"])
        page.get_by_role("textbox", name="Password").fill(os.environ["PULSE_ADMIN_PASSWORD"])
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_selector('[data-testid="stSidebar"] [role="radiogroup"]', timeout=30_000)
        for name, label in PAGES:
            page.locator('[data-testid="stSidebar"] label').filter(has_text=label).first.click()
            page.wait_for_timeout(3500)
            if page.locator('[data-testid="stException"]').count():
                raise RuntimeError(f"The {label} page shows an error; fix it before capturing previews")
            page.screenshot(path=str(args.out / f"{name}.png"))
            print(args.out / f"{name}.png")
        browser.close()
    (args.out / "snapshot.json").write_text(json.dumps({
        "generated_from": "screenshots of the running dashboard",
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pages": [label for _, label in PAGES],
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
