"""
logger.py — Structured logging and CSV tracking for all applications.
"""

import csv
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import LOG_FILE, CSV_FILE

# ─── Console + File Logger ────────────────────────────────────────────────────
def get_logger(name: str = "linkedin_bot") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


log = get_logger()

# ─── CSV Application Tracker ─────────────────────────────────────────────────
CSV_HEADERS = [
    "date_applied",
    "company",
    "role",
    "location",
    "salary",
    "url",
    "status",
    "compatibility_score",
    "skip_reason",
    "cover_letter_used",
]


def init_csv() -> None:
    """Create CSV with headers if it doesn't exist."""
    p = Path(CSV_FILE)
    if not p.exists():
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
        log.info(f"Created {CSV_FILE}")


def log_application(
    company: str,
    role: str,
    location: str,
    url: str,
    status: str,
    compatibility_score: int = 0,
    salary: str = "N/A",
    skip_reason: str = "",
    cover_letter_used: bool = False,
) -> None:
    """Append one application row to the CSV."""
    init_csv()
    row = {
        "date_applied": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "company": company,
        "role": role,
        "location": location,
        "salary": salary,
        "url": url,
        "status": status,
        "compatibility_score": compatibility_score,
        "skip_reason": skip_reason,
        "cover_letter_used": cover_letter_used,
    }
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow(row)
    log.info(f"[CSV] {status} | {company} | {role} | score={compatibility_score}")


def load_applications() -> list[dict]:
    """Return all rows from the CSV as a list of dicts."""
    init_csv()
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))
