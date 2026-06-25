"""
utils.py — Shared utility helpers: delays, CAPTCHA detection, retries, etc.
"""

import asyncio
import random
import re
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from playwright.async_api import Page

from config import DELAY_SHORT, DELAY_MEDIUM, DELAY_LONG, DELAY_PAGE, MAX_RETRIES, RETRY_DELAY
from logger import log

T = TypeVar("T")

# ─── Human-Like Delays ────────────────────────────────────────────────────────

async def short_delay() -> None:
    await asyncio.sleep(random.uniform(*DELAY_SHORT))

async def medium_delay() -> None:
    await asyncio.sleep(random.uniform(*DELAY_MEDIUM))

async def long_delay() -> None:
    await asyncio.sleep(random.uniform(*DELAY_LONG))

async def page_delay() -> None:
    await asyncio.sleep(random.uniform(*DELAY_PAGE))


# ─── Human-Like Typing ────────────────────────────────────────────────────────

async def human_type(page: Page, selector: str, text: str) -> None:
    """Click a field and type character-by-character with random delays."""
    await page.click(selector)
    await short_delay()
    await page.fill(selector, "")  # clear first
    for char in text:
        await page.type(selector, char, delay=random.uniform(40, 120))
    await short_delay()


# ─── Random Scrolling ─────────────────────────────────────────────────────────

async def random_scroll(page: Page, times: int = 3) -> None:
    """Scroll the page randomly to mimic human reading."""
    for _ in range(times):
        direction = random.choice([1, -1])
        amount = random.randint(200, 600)
        await page.evaluate(f"window.scrollBy(0, {direction * amount})")
        await short_delay()


async def scroll_to_bottom(page: Page) -> None:
    """Gradually scroll to the bottom of the page."""
    total = await page.evaluate("document.body.scrollHeight")
    current = 0
    step = random.randint(300, 600)
    while current < total:
        current = min(current + step, total)
        await page.evaluate(f"window.scrollTo(0, {current})")
        await asyncio.sleep(random.uniform(0.2, 0.6))


# ─── CAPTCHA Detection ────────────────────────────────────────────────────────

CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "#captcha-challenge",
    ".captcha",
    "[data-sitekey]",
    "text=verify you're human",
    "text=security check",
    "text=are you a robot",
]

async def detect_captcha(page: Page) -> bool:
    """Return True if a CAPTCHA is detected on the current page."""
    for sel in CAPTCHA_SELECTORS:
        try:
            elem = page.locator(sel).first
            if await elem.is_visible(timeout=1000):
                log.warning(f"CAPTCHA detected: {sel}")
                return True
        except Exception:
            pass
    return False


async def wait_for_captcha_resolution(page: Page, timeout: int = 120) -> bool:
    """Pause and poll until CAPTCHA disappears (user solves it manually)."""
    log.warning("⚠  CAPTCHA detected — please solve it manually in the browser.")
    start = time.time()
    while time.time() - start < timeout:
        await asyncio.sleep(3)
        if not await detect_captcha(page):
            log.info("✓ CAPTCHA resolved.")
            return True
    log.error("✗ CAPTCHA not solved within timeout.")
    return False


# ─── Retry Decorator ─────────────────────────────────────────────────────────

def async_retry(
    retries: int = MAX_RETRIES,
    delay: float = RETRY_DELAY,
    exceptions: tuple = (Exception,),
):
    """Decorator: retry an async function up to `retries` times."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[Exception] = None
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    log.warning(
                        f"[Retry {attempt}/{retries}] {func.__name__} failed: {e}"
                    )
                    if attempt < retries:
                        await asyncio.sleep(delay * attempt)
            raise last_exc  # type: ignore
        return wrapper
    return decorator


# ─── Text Utilities ───────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


def extract_salary(text: str) -> str:
    """Try to pull a salary range string from job description text."""
    pattern = r"(?:₹|INR|Rs\.?|LPA|lpa)[\s\d,\.\-–toTO\s]+"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return clean_text(match.group())
    return "N/A"


def extract_experience_required(text: str) -> Optional[int]:
    """Extract the minimum years of experience mentioned."""
    patterns = [
        r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?experience",
        r"minimum\s*(\d+)\s*(?:years?|yrs?)",
        r"at\s*least\s*(\d+)\s*(?:years?|yrs?)",
        r"(\d+)\s*-\s*\d+\s*(?:years?|yrs?)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def contains_skip_keyword(text: str, keywords: list[str]) -> Optional[str]:
    """Return the first matching skip keyword found in text, else None."""
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            return kw
    return None


def pluralize(n: int, word: str) -> str:
    return f"{n} {word}{'s' if n != 1 else ''}"
