#!/usr/bin/env python3
"""Publish a markdown file to Medium as an unlisted post using browser automation."""

import argparse
import asyncio
import logging
import os
import sys
import time
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


async def fill_title(page, title: str):
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
            await page.keyboard.type(title, delay=30)
            logger.info("Title entered")
            return
        except Exception:
            continue
    logger.warning("Title field not found via selectors — typing directly")
    await page.keyboard.type(title, delay=30)


async def paste_body(page, html: str):
    # Press Enter after title to move cursor to body
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(500)

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

    # Click the final publish confirm button
    confirm_selectors = [
        'button:has-text("Publish now")',
        'button:has-text("Publish story")',
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


async def main_async(filepath: str):
    start = time.perf_counter()

    filepath = os.path.expanduser(filepath)
    if not os.path.isfile(filepath):
        logger.error("File not found: %s", filepath)
        sys.exit(1)

    content = Path(filepath).read_text(encoding="utf-8")
    if not content.strip():
        logger.error("File is empty: %s", filepath)
        sys.exit(1)

    title, body = extract_title(content, filepath)
    html_body = to_html(body)
    logger.info("Title: %s", title)
    logger.info("Body: %d chars markdown → %d chars HTML", len(body), len(html_body))

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

        logger.info("Opening new story editor...")
        await page.goto(MEDIUM_NEW_STORY, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        await fill_title(page, title)
        await paste_body(page, html_body)

        post_url = await publish_unlisted(page)

        await context.close()

    logger.info("Post URL: %s", post_url)
    logger.info("Done in %.1fs", time.perf_counter() - start)
    print(post_url)


def main():
    parser = argparse.ArgumentParser(description="Publish a markdown file to Medium (unlisted).")
    parser.add_argument("file", help="Path to the markdown file to publish")
    args = parser.parse_args()
    asyncio.run(main_async(args.file))


if __name__ == "__main__":
    main()
