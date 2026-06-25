"""
playwright_bot.py — Core Playwright automation: login, search, apply.
"""

import asyncio
import json
import os
import random
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PWTimeoutError,
)

from config import (
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    RESUME_PATH,
    HEADLESS,
    SLOW_MO,
    SESSION_FILE,
    SCREENSHOT_DIR,
    JOB_TITLES,
    LINKEDIN_LOCATIONS,
    DATE_POSTED_FILTER,
    EMPLOYMENT_TYPE,
    EASY_APPLY_ONLY,
    MAX_APPLICANTS_SKIP,
    MAX_EXPERIENCE_REQUIRED,
    SKIP_KEYWORDS,
    COMPANY_AVOID_KEYWORDS,
    MIN_COMPATIBILITY_SCORE,
    CANDIDATE,
)
from ai_matcher import analyze_job, answer_question
from cover_letter import get_cover_letter_text
from logger import log, log_application
from utils import (
    short_delay,
    medium_delay,
    long_delay,
    page_delay,
    human_type,
    random_scroll,
    scroll_to_bottom,
    detect_captcha,
    wait_for_captcha_resolution,
    async_retry,
    clean_text,
    extract_salary,
    extract_experience_required,
    contains_skip_keyword,
)

SCREENSHOT_DIR.mkdir(exist_ok=True)
Path("cover_letters").mkdir(exist_ok=True)


class LinkedInBot:
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.stats = {
            "found": 0,
            "applied": 0,
            "skipped": 0,
            "errors": 0,
        }

    # ─── Browser / Session ────────────────────────────────────────────────────

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        storage_state = SESSION_FILE if Path(SESSION_FILE).exists() else None

        self.context = await self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )
        self.page = await self.context.new_page()

        # Anti-detection scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)

        log.info("Browser started.")

    async def save_session(self) -> None:
        if self.context:
            await self.context.storage_state(path=SESSION_FILE)
            log.info("Session saved.")

    async def stop(self) -> None:
        await self.save_session()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        log.info("Browser closed.")

    async def screenshot(self, name: str) -> None:
        if self.page:
            path = SCREENSHOT_DIR / f"{name}.png"
            await self.page.screenshot(path=str(path), full_page=False)

    # ─── Login ────────────────────────────────────────────────────────────────

    async def is_logged_in(self) -> bool:
        try:
            await self.page.goto("https://www.linkedin.com/feed/", timeout=15000)
            await page_delay()
            url = self.page.url
            return "feed" in url or "mynetwork" in url
        except Exception:
            return False

    @async_retry(retries=3, delay=5)
    async def login(self) -> bool:
        if await self.is_logged_in():
            log.info("Already logged in via saved session.")
            return True

        log.info("Logging in to LinkedIn...")
        await self.page.goto("https://www.linkedin.com/login", timeout=20000)
        await page_delay()

        if await detect_captcha(self.page):
            await wait_for_captcha_resolution(self.page)

        await human_type(self.page, "#username", LINKEDIN_EMAIL)
        await short_delay()
        await human_type(self.page, "#password", LINKEDIN_PASSWORD)
        await medium_delay()

        await self.page.click("button[type='submit']")
        await page_delay()

        if await detect_captcha(self.page):
            solved = await wait_for_captcha_resolution(self.page)
            if not solved:
                return False
            await page_delay()

        if "feed" in self.page.url or "checkpoint" not in self.page.url:
            log.info("✓ Login successful.")
            await self.save_session()
            return True

        log.error(f"✗ Login failed. Current URL: {self.page.url}")
        await self.screenshot("login_failure")
        return False

    # ─── Job Search ───────────────────────────────────────────────────────────

    def _build_search_url(self, job_title: str, location: str) -> str:
        from urllib.parse import quote
        base = "https://www.linkedin.com/jobs/search/?"
        params = {
            "keywords": job_title,
            "location": location,
            "f_TPR": DATE_POSTED_FILTER,
            "f_JT": EMPLOYMENT_TYPE,
            "f_WT": "1,2,3",  # on-site, remote, hybrid
        }
        if EASY_APPLY_ONLY:
            params["f_LF"] = "f_AL"  # Easy Apply filter
        query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        return base + query

    async def get_job_links(self, job_title: str, location: str) -> list[str]:
        """Return a list of job detail URLs from one search results page."""
        url = self._build_search_url(job_title, location)
        log.info(f"Searching: {job_title} @ {location}")
        await self.page.goto(url, timeout=20000)
        await page_delay()

        if await detect_captcha(self.page):
            await wait_for_captcha_resolution(self.page)

        await scroll_to_bottom(self.page)
        await medium_delay()

        # Collect job card links
        links: list[str] = []
        cards = await self.page.query_selector_all("a.job-card-container__link")
        for card in cards:
            href = await card.get_attribute("href")
            if href and "/jobs/view/" in href:
                full = "https://www.linkedin.com" + href.split("?")[0]
                if full not in links:
                    links.append(full)

        log.info(f"  Found {len(links)} jobs for '{job_title}' in {location}")
        return links

    # ─── Job Detail Extraction ────────────────────────────────────────────────

    async def extract_job_details(self) -> dict:
        """Extract key metadata from the currently open job detail page."""
        await medium_delay()
        await random_scroll(self.page, 2)

        async def safe_text(selector: str) -> str:
            try:
                elem = self.page.locator(selector).first
                text = await elem.inner_text(timeout=3000)
                return clean_text(text)
            except Exception:
                return ""

        title = await safe_text("h1.t-24")
        company = await safe_text("a.app-aware-link span[aria-hidden='true']")
        location = await safe_text(".job-details-jobs-unified-top-card__bullet")
        applicants_text = await safe_text(
            ".jobs-unified-top-card__applicant-count, "
            ".job-details-jobs-unified-top-card__applicant-count"
        )

        # Expand "See more" in description
        try:
            see_more = self.page.locator("button[aria-label*='more'], .jobs-description__footer-button").first
            if await see_more.is_visible(timeout=2000):
                await see_more.click()
                await short_delay()
        except Exception:
            pass

        description = await safe_text(".jobs-description__content, .jobs-box__html-content")

        # Parse applicant count
        applicants = 0
        import re
        m = re.search(r"(\d+)", applicants_text.replace(",", ""))
        if m:
            applicants = int(m.group(1))

        # Check Easy Apply button
        has_easy_apply = False
        try:
            btn = self.page.locator(
                "button.jobs-apply-button, "
                "button[aria-label*='Easy Apply'], "
                "span:text('Easy Apply')"
            ).first
            if await btn.is_visible(timeout=2000):
                has_easy_apply = True
        except Exception:
            pass

        return {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "applicants": applicants,
            "has_easy_apply": has_easy_apply,
            "salary": extract_salary(description),
            "url": self.page.url,
        }

    # ─── Pre-Application Screening ────────────────────────────────────────────

    def should_skip(self, job: dict, analysis: dict) -> tuple[bool, str]:
        """Return (True, reason) if the job should be skipped."""

        if not job["has_easy_apply"]:
            return True, "No Easy Apply"

        if job["applicants"] > MAX_APPLICANTS_SKIP:
            return True, f"Too many applicants ({job['applicants']})"

        skip_kw = contains_skip_keyword(
            job["description"] + job["title"], SKIP_KEYWORDS
        )
        if skip_kw:
            return True, f"Skip keyword: {skip_kw}"

        avoid_kw = contains_skip_keyword(job["company"], COMPANY_AVOID_KEYWORDS)
        if avoid_kw:
            return True, f"Avoid company type: {avoid_kw}"

        if analysis.get("requires_clearance"):
            return True, "Requires security clearance"

        if analysis.get("requires_sponsorship"):
            return True, "Requires visa sponsorship"

        if analysis.get("is_contract"):
            return True, "Contract position"

        if analysis.get("is_consultancy") and not analysis.get("is_product_company"):
            return True, "Consultancy / staffing firm"

        req_exp = analysis.get("required_experience")
        if req_exp and req_exp > MAX_EXPERIENCE_REQUIRED:
            return True, f"Requires {req_exp}+ years (max {MAX_EXPERIENCE_REQUIRED})"

        if analysis.get("score", 0) < MIN_COMPATIBILITY_SCORE:
            return True, f"Low compatibility score ({analysis.get('score')})"

        return False, ""

    # ─── Easy Apply Flow ─────────────────────────────────────────────────────

    async def click_easy_apply(self) -> bool:
        """Click the Easy Apply button. Returns True if modal opened."""
        try:
            btn = self.page.locator(
                "button.jobs-apply-button:has-text('Easy Apply'), "
                "button[aria-label*='Easy Apply']"
            ).first
            await btn.click(timeout=5000)
            await medium_delay()
            return True
        except Exception as e:
            log.warning(f"Could not click Easy Apply: {e}")
            return False

    async def fill_text_field(self, label_text: str, answer: str) -> bool:
        """Find a form field by its label and fill it."""
        try:
            # Try aria-label match
            field = self.page.locator(
                f"input[aria-label*='{label_text}' i], "
                f"textarea[aria-label*='{label_text}' i]"
            ).first
            if await field.is_visible(timeout=2000):
                await field.click()
                await field.fill("")
                await field.type(answer, delay=random.uniform(40, 100))
                return True
        except Exception:
            pass

        try:
            # Try label element lookup
            label = self.page.locator(f"label:has-text('{label_text}')").first
            field_id = await label.get_attribute("for")
            if field_id:
                field = self.page.locator(f"#{field_id}").first
                await field.click()
                await field.fill("")
                await field.type(answer, delay=random.uniform(40, 100))
                return True
        except Exception:
            pass

        return False

    async def handle_form_questions(self, job_description: str) -> None:
        """Auto-fill all visible form questions on the current step."""
        # Text inputs
        inputs = await self.page.query_selector_all(
            ".jobs-easy-apply-form-element input, "
            ".jobs-easy-apply-form-element textarea"
        )
        for inp in inputs:
            try:
                label_text = ""
                # Get associated label
                inp_id = await inp.get_attribute("id")
                aria_label = await inp.get_attribute("aria-label") or ""
                placeholder = await inp.get_attribute("placeholder") or ""
                label_text = aria_label or placeholder

                if inp_id:
                    label_el = await self.page.query_selector(f"label[for='{inp_id}']")
                    if label_el:
                        label_text = await label_el.inner_text()

                if not label_text:
                    continue

                label_clean = clean_text(label_text)
                answer = answer_question(label_clean, job_description)

                current_val = await inp.input_value()
                if not current_val:  # Don't overwrite pre-filled fields
                    await inp.click()
                    await inp.fill("")
                    await inp.type(answer, delay=random.uniform(40, 100))
                    await short_delay()
            except Exception as e:
                log.debug(f"Question fill error: {e}")

        # Select dropdowns
        selects = await self.page.query_selector_all(
            ".jobs-easy-apply-form-element select"
        )
        for sel in selects:
            try:
                aria_label = await sel.get_attribute("aria-label") or ""
                options = await sel.query_selector_all("option")
                opt_texts = [await o.inner_text() for o in options]

                # Pick best matching option
                answer = answer_question(aria_label, job_description)
                best = None
                for opt in opt_texts:
                    if answer.lower() in opt.lower() or opt.lower() in answer.lower():
                        best = opt
                        break
                if not best and opt_texts:
                    best = opt_texts[-1]  # pick last (often "Yes")
                if best:
                    await sel.select_option(label=best)
                    await short_delay()
            except Exception as e:
                log.debug(f"Select error: {e}")

        # Radio buttons
        radios = await self.page.query_selector_all(
            ".jobs-easy-apply-form-element input[type='radio']"
        )
        for radio in radios:
            try:
                label_el = await radio.query_selector("xpath=following-sibling::label")
                if not label_el:
                    radio_id = await radio.get_attribute("id")
                    if radio_id:
                        label_el = await self.page.query_selector(f"label[for='{radio_id}']")
                if label_el:
                    label_text = clean_text(await label_el.inner_text())
                    # Prefer "Yes" options
                    if label_text.lower() in ("yes", "true", "1"):
                        await radio.click()
                        await short_delay()
            except Exception as e:
                log.debug(f"Radio error: {e}")

    async def upload_resume(self) -> bool:
        """Locate the resume upload button and upload the file."""
        if not RESUME_PATH.exists():
            log.warning(f"Resume not found at {RESUME_PATH}")
            return False
        try:
            upload_input = self.page.locator(
                "input[type='file'][accept*='pdf'], "
                "input[type='file'][name*='resume'], "
                "input[type='file'][name*='cv']"
            ).first
            if await upload_input.is_visible(timeout=3000):
                await upload_input.set_input_files(str(RESUME_PATH))
                await medium_delay()
                log.info("✓ Resume uploaded.")
                return True
        except Exception as e:
            log.warning(f"Resume upload failed: {e}")
        return False

    async def fill_cover_letter(self, cover_letter: str) -> bool:
        """Paste cover letter into the cover letter textarea if present."""
        try:
            ta = self.page.locator(
                "textarea[aria-label*='cover letter' i], "
                "textarea[name*='cover' i]"
            ).first
            if await ta.is_visible(timeout=2000):
                await ta.click()
                await ta.fill(cover_letter[:2000])
                await short_delay()
                return True
        except Exception:
            pass
        return False

    async def navigate_easy_apply_modal(
        self, job: dict, cover_letter: str
    ) -> bool:
        """
        Step through the Easy Apply modal, filling every step,
        pausing before final submit.
        Returns True if submitted successfully.
        """
        max_steps = 10
        for step in range(max_steps):
            await medium_delay()

            # Detect if modal is still open
            modal = self.page.locator(".jobs-easy-apply-modal, .artdeco-modal").first
            if not await modal.is_visible(timeout=3000):
                log.info("Modal closed (possibly submitted).")
                return True

            # Fill any visible questions
            await self.handle_form_questions(job["description"])

            # Upload resume if applicable
            await self.upload_resume()

            # Paste cover letter if field present
            await self.fill_cover_letter(cover_letter)

            # Determine available buttons
            next_btn = self.page.locator("button:has-text('Next'), button:has-text('Continue')").last
            review_btn = self.page.locator("button:has-text('Review')").last
            submit_btn = self.page.locator("button:has-text('Submit application'), button:has-text('Submit')").last

            if await submit_btn.is_visible(timeout=1500):
                # ── PAUSE FOR USER CONFIRMATION ──
                log.info("=" * 60)
                log.info(f"  READY TO SUBMIT: {job['title']} @ {job['company']}")
                log.info(f"  URL: {job['url']}")
                log.info("=" * 60)
                confirm = input("\n  Press ENTER to submit, or type 'skip' to skip: ").strip().lower()
                if confirm == "skip":
                    log.info("User skipped submission.")
                    await self._close_modal()
                    return False
                await submit_btn.click()
                await page_delay()
                log.info("✓ Application submitted!")
                return True

            elif await review_btn.is_visible(timeout=1500):
                await review_btn.click()
            elif await next_btn.is_visible(timeout=1500):
                await next_btn.click()
            else:
                log.warning(f"No navigation button found at step {step}")
                await self.screenshot(f"modal_stuck_{step}")
                break

        return False

    async def _close_modal(self) -> None:
        try:
            dismiss = self.page.locator(
                "button[aria-label='Dismiss'], button:has-text('Discard')"
            ).first
            if await dismiss.is_visible(timeout=2000):
                await dismiss.click()
                await medium_delay()
                # Confirm discard
                discard = self.page.locator("button:has-text('Discard')").last
                if await discard.is_visible(timeout=2000):
                    await discard.click()
                    await short_delay()
        except Exception:
            pass

    # ─── Main Application Flow ────────────────────────────────────────────────

    async def apply_to_job(self, url: str) -> None:
        """Full workflow for a single job URL."""
        try:
            await self.page.goto(url, timeout=20000)
            await page_delay()

            if await detect_captcha(self.page):
                await wait_for_captcha_resolution(self.page)

            job = await self.extract_job_details()
            job["url"] = url
            self.stats["found"] += 1

            log.info(f"\n{'─'*60}")
            log.info(f"  {job['title']} @ {job['company']}")
            log.info(f"  Location: {job['location']} | Applicants: {job['applicants']}")

            # AI analysis
            log.info("  Analyzing with AI...")
            analysis = analyze_job(job["title"], job["company"], job["description"])
            score = analysis.get("score", 0)
            log.info(f"  Compatibility score: {score}/100")
            if analysis.get("missing_skills"):
                log.info(f"  Missing: {', '.join(analysis['missing_skills'][:5])}")

            # Screening decision
            skip, reason = self.should_skip(job, analysis)
            if skip:
                log.info(f"  ⏭  SKIPPED — {reason}")
                self.stats["skipped"] += 1
                log_application(
                    company=job["company"],
                    role=job["title"],
                    location=job["location"],
                    url=url,
                    status="Skipped",
                    compatibility_score=score,
                    salary=job["salary"],
                    skip_reason=reason,
                )
                return

            # Generate cover letter
            cover_letter = get_cover_letter_text(
                job["title"],
                job["company"],
                job["description"],
                analysis.get("matched_skills", []),
            )

            # Open Easy Apply modal
            if not await self.click_easy_apply():
                log.warning("  Could not open Easy Apply modal.")
                self.stats["skipped"] += 1
                log_application(
                    company=job["company"],
                    role=job["title"],
                    location=job["location"],
                    url=url,
                    status="Skipped",
                    compatibility_score=score,
                    skip_reason="Could not open Easy Apply",
                )
                return

            submitted = await self.navigate_easy_apply_modal(job, cover_letter)

            if submitted:
                self.stats["applied"] += 1
                log_application(
                    company=job["company"],
                    role=job["title"],
                    location=job["location"],
                    url=url,
                    status="Applied",
                    compatibility_score=score,
                    salary=job["salary"],
                    cover_letter_used=True,
                )
                log.info(f"  ✅  APPLIED — score={score}")
            else:
                self.stats["skipped"] += 1
                log_application(
                    company=job["company"],
                    role=job["title"],
                    location=job["location"],
                    url=url,
                    status="Skipped",
                    compatibility_score=score,
                    skip_reason="User cancelled or submission failed",
                )

        except Exception as e:
            log.error(f"Error applying to {url}: {e}", exc_info=True)
            self.stats["errors"] += 1
            await self.screenshot(f"error_{hash(url) % 10000}")

    # ─── Run All Searches ─────────────────────────────────────────────────────

    async def run(self) -> None:
        await self.start()

        try:
            if not await self.login():
                log.error("Login failed. Exiting.")
                return

            all_links: list[str] = []
            seen: set[str] = set()

            for title in JOB_TITLES:
                for location in LINKEDIN_LOCATIONS:
                    links = await self.get_job_links(title, location)
                    for link in links:
                        if link not in seen:
                            seen.add(link)
                            all_links.append(link)
                    await long_delay()

            log.info(f"\n{'='*60}")
            log.info(f"  Total unique jobs found: {len(all_links)}")
            log.info(f"{'='*60}")

            for i, link in enumerate(all_links, 1):
                log.info(f"\nJob {i}/{len(all_links)}")
                await self.apply_to_job(link)
                await long_delay()

        finally:
            await self.stop()
            log.info("\n" + "="*60)
            log.info(f"  Session complete:")
            log.info(f"  Found:   {self.stats['found']}")
            log.info(f"  Applied: {self.stats['applied']}")
            log.info(f"  Skipped: {self.stats['skipped']}")
            log.info(f"  Errors:  {self.stats['errors']}")
            log.info("="*60)
