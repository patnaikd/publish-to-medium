#!/usr/bin/env python3
"""Publish a markdown file to Medium as an unlisted post using browser automation."""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import markdown as md_lib
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Persistent browser profile so login is remembered across runs
PROFILE_DIR = Path.home() / ".publish-to-medium-profile"
MEDIUM_NEW_STORY = "https://medium.com/new-story"

# Maps resolved markdown file paths to the Medium post last published from them,
# so republishing reopens and updates that same post instead of creating a new one.
MAPPINGS_FILE = PROFILE_DIR / "mappings.json"


def load_mappings() -> dict:
    try:
        return json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_mapping(filepath: str, entry: dict) -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    mappings = load_mappings()
    mappings[filepath] = entry
    MAPPINGS_FILE.write_text(json.dumps(mappings, indent=2), encoding="utf-8")


def extract_post_id(url: str) -> str | None:
    marker = "/p/"
    idx = url.find(marker)
    if idx == -1:
        return None
    rest = url[idx + len(marker):]
    return rest.split("/")[0].split("?")[0] or None


def extract_title(content: str, filepath: str) -> tuple[str, str]:
    """Return (title, body). Strips the first H1 from body if used as title."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            title = line.strip()[2:].strip()
            body = "\n".join(lines[:i] + lines[i + 1:]).strip()
            return title, body
    title = Path(filepath).stem.replace("-", " ").replace("_", " ").title()
    return title, content.strip()


def to_html(markdown_text: str) -> str:
    return md_lib.markdown(markdown_text, extensions=["extra", "fenced_code", "tables"])


async def ensure_logged_in(page):
    await page.goto("https://medium.com", wait_until="domcontentloaded")
    try:
        await page.wait_for_selector('a[href*="/new-story"]', timeout=6000)
        logger.info("Logged in to Medium")
        return
    except PlaywrightTimeoutError:
        pass

    logger.info("Please sign in to Medium in the browser window that just opened...")
    logger.info("Waiting up to 3 minutes for login...")
    try:
        await page.wait_for_selector('a[href*="/new-story"]', timeout=180_000)
        logger.info("Login detected — session will be reused for future runs")
    except PlaywrightTimeoutError:
        logger.error("Login timed out. Please try again.")
        sys.exit(1)


async def fill_title(page, title: str, clear: bool = False):
    selectors = [
        'h3[placeholder="Title"]',
        'p[data-placeholder="Title"]',
        '[data-testid="storyTitle"]',
        'div[role="textbox"]:first-of-type',
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            await el.wait_for(state="visible", timeout=3000)
            await el.click()
            if clear:
                await page.keyboard.press("Meta+a")
                await page.keyboard.press("Backspace")
            await page.keyboard.type(title, delay=30)
            logger.info("Title entered")
            return
        except Exception:
            continue
    logger.warning("Title field not found via selectors — typing directly")
    if clear:
        await page.keyboard.press("Meta+a")
        await page.keyboard.press("Backspace")
    await page.keyboard.type(title, delay=30)


async def paste_body(page, html: str, clear: bool = False):
    # Press Enter after title to move cursor to body
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(500)

    if clear:
        await page.keyboard.press("Meta+a")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(300)

    # Write HTML to clipboard via JS, then paste
    await page.evaluate("""
        async (html) => {
            await navigator.clipboard.write([
                new ClipboardItem({
                    'text/html': new Blob([html], { type: 'text/html' }),
                    'text/plain': new Blob([html], { type: 'text/plain' }),
                })
            ]);
        }
    """, html)

    await page.keyboard.press("Meta+v")  # Cmd+V on macOS
    await page.wait_for_timeout(1500)
    logger.info("Body pasted")


async def publish_unlisted(page) -> str:
    # Click the Publish button in the toolbar
    try:
        btn = page.locator('button:has-text("Publish")').first
        await btn.wait_for(state="visible", timeout=10_000)
        await btn.click()
        logger.info("Publish panel opened")
    except PlaywrightTimeoutError:
        logger.error("Could not find Publish button")
        sys.exit(1)

    await page.wait_for_timeout(1500)

    # Select "Unlisted" visibility
    unlisted_selectors = [
        'label:has-text("Unlisted")',
        'button:has-text("Unlisted")',
        'input[value="unlisted"]',
        '[data-testid="unlisted"]',
        'span:has-text("Unlisted")',
    ]
    unlisted_set = False
    for sel in unlisted_selectors:
        try:
            el = page.locator(sel).first
            await el.wait_for(state="visible", timeout=2000)
            await el.click()
            logger.info("Visibility set to Unlisted")
            unlisted_set = True
            break
        except Exception:
            continue

    if not unlisted_set:
        logger.warning("Could not find Unlisted option — publishing with default visibility")

    await page.wait_for_timeout(500)

    # Click the final publish confirm button (wording differs when updating
    # an already-published story vs. publishing a new one)
    confirm_selectors = [
        'button:has-text("Publish now")',
        'button:has-text("Publish story")',
        'button:has-text("Update")',
        'button:has-text("Publish")',
    ]
    for sel in confirm_selectors:
        try:
            btn = page.locator(sel).last
            await btn.wait_for(state="visible", timeout=3000)
            await btn.click()
            logger.info("Confirmed publish")
            break
        except Exception:
            continue

    # Wait for redirect to published post URL
    try:
        await page.wait_for_url("**/p/**", timeout=15_000)
    except PlaywrightTimeoutError:
        pass

    return page.url


async def main_async(filepath: str, force_new: bool = False):
    start = time.perf_counter()

    filepath = os.path.expanduser(filepath)
    if not os.path.isfile(filepath):
        logger.error("File not found: %s", filepath)
        sys.exit(1)

    resolved_path = str(Path(filepath).resolve())

    content = Path(filepath).read_text(encoding="utf-8")
    if not content.strip():
        logger.error("File is empty: %s", filepath)
        sys.exit(1)

    title, body = extract_title(content, filepath)
    html_body = to_html(body)
    logger.info("Title: %s", title)
    logger.info("Body: %d chars markdown → %d chars HTML", len(body), len(html_body))

    existing = None if force_new else load_mappings().get(resolved_path)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            channel="chromium",
            viewport={"width": 1280, "height": 900},
            permissions=["clipboard-read", "clipboard-write"],
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        await ensure_logged_in(page)

        if existing:
            logger.info("Found previous post for this file (%s) — reopening to update", existing["url"])
            await page.goto(existing["edit_url"], wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await fill_title(page, title, clear=True)
            await paste_body(page, html_body, clear=True)
        else:
            logger.info("Forcing new story" if force_new else "No previous post found — creating new story")
            await page.goto(MEDIUM_NEW_STORY, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await fill_title(page, title)
            await paste_body(page, html_body)

        post_url = await publish_unlisted(page)

        await context.close()

    post_id = extract_post_id(post_url)
    save_mapping(resolved_path, {
        "post_id": post_id,
        "url": post_url,
        "edit_url": f"https://medium.com/p/{post_id}/edit" if post_id else None,
        "title": title,
        "published_at": datetime.now(timezone.utc).isoformat(),
    })
    if not post_id:
        logger.warning("Could not determine post ID from URL — republish won't be available for this file")

    logger.info("Post URL: %s", post_url)
    logger.info("Done in %.1fs", time.perf_counter() - start)
    print(post_url)


def main():
    parser = argparse.ArgumentParser(description="Publish a markdown file to Medium (unlisted).")
    parser.add_argument("file", help="Path to the markdown file to publish")
    parser.add_argument(
        "--new", action="store_true",
        help="Force creating a new post even if this file was published before",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args.file, force_new=args.new))


if __name__ == "__main__":
    main()
