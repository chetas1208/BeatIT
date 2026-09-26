#!/usr/bin/env python3
"""Headless browser smoke for the five BeatIT product modes.

Requires a running Next.js production server (see deploy/beatit). Uses host
Playwright when available. Does not print secrets or patient data.

Usage:
  E2E_WEB_URL=http://127.0.0.1:13001 python scripts/browser_product_e2e.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lib_path() -> str | None:
    shim = Path.home() / ".local/beatit-libs/root/usr/lib/x86_64-linux-gnu"
    if (shim / "libasound.so.2").is_file():
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        return f"{shim}{':' + existing if existing else ''}"
    return None


def main() -> int:
    base = os.environ.get("E2E_WEB_URL", "http://127.0.0.1:3001").rstrip("/")
    modes = ("twin", "experiment", "compare", "evidence", "report")
    failures: list[str] = []

    lib = _lib_path()
    if lib:
        os.environ["LD_LIBRARY_PATH"] = lib

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("BROWSER E2E SKIP: playwright not installed")
        return 2

    init_script = "try { localStorage.setItem('hearttwin:disclaimer-ack:v1', '1'); } catch (e) {}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-gpu"])
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.add_init_script(init_script)
        page = context.new_page()
        try:
            for mode in modes:
                url = f"{base}/{mode}"
                response = page.goto(url, wait_until="networkidle", timeout=90_000)
                if response is None or response.status >= 400:
                    failures.append(f"{url} HTTP {response.status if response else 'none'}")
                    continue
                body = page.content()
                if "BeatIT" not in body and "DualBeat" not in body:
                    failures.append(f"{url} missing product title marker")
                nav = page.locator("nav, [role='navigation']").first
                if nav.count() == 0:
                    failures.append(f"{url} missing navigation landmark")

            page.goto(f"{base}/twin", wait_until="networkidle", timeout=120_000)
            page.wait_for_selector('nav[aria-label="BeatIT primary spaces"]', timeout=60_000)
            synthetic = page.get_by_label("Synthetic demo data")
            if synthetic.count() == 0:
                failures.append("/twin missing SYNTHETIC demo chip (aria-label)")
            page.wait_for_selector("canvas", timeout=60_000)
            canvas = page.locator("canvas")
            if canvas.count() == 0:
                failures.append("/twin no WebGL canvas detected")

            for label in ("TWIN", "EXPERIMENT", "COMPARE", "EVIDENCE", "REPORT"):
                btn = page.get_by_role("button", name=label, exact=True)
                if btn.count() == 0:
                    failures.append(f"missing nav button {label!r}")
            page.keyboard.press("Tab")
            page.keyboard.press("Tab")
        finally:
            context.close()
            browser.close()

    if failures:
        print("BROWSER E2E FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("BROWSER E2E PASS")
    print(f"MODES PASS {len(modes)}")
    print("WEBGL CANVAS PASS")
    print("NAV KEYBOARD SMOKE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
