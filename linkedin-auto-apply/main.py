"""
main.py — Entry point for LinkedIn Auto-Apply Bot (Free version with Gemini).
"""

import asyncio
import sys
from logger import get_logger, init_csv
from playwright_bot import LinkedInBot

log = get_logger("main")


def check_env() -> bool:
    import os
    missing = []
    if not os.getenv("LINKEDIN_EMAIL"):
        missing.append("LINKEDIN_EMAIL")
    if not os.getenv("LINKEDIN_PASSWORD"):
        missing.append("LINKEDIN_PASSWORD")

    if missing:
        log.error(f"Missing required environment variables: {', '.join(missing)}")
        log.error("Edit your .env file — see README.md")
        return False

    # Gemini key is optional — bot works without it using rule-based scoring
    gemini = os.getenv("GEMINI_API_KEY", "")
    if not gemini or gemini == "paste-your-free-gemini-key-here":
        log.warning("No GEMINI_API_KEY set — using built-in rule-based job scoring.")
        log.warning("Get a FREE key at: https://aistudio.google.com/app/apikey")
    else:
        log.info("✓ Gemini AI enabled for job scoring and cover letters.")

    return True


async def main() -> None:
    log.info("=" * 60)
    log.info("  LinkedIn Auto-Apply Bot — Free Edition")
    log.info("  AI: Google Gemini (free) or rule-based fallback")
    log.info("=" * 60)

    if not check_env():
        sys.exit(1)

    init_csv()
    bot = LinkedInBot()

    try:
        await bot.run()
    except KeyboardInterrupt:
        log.info("\nInterrupted by user.")
        await bot.stop()
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        await bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
