"""
cover_letter.py — Cover letter generation and file output utilities.
"""

from pathlib import Path
from datetime import datetime

from ai_matcher import generate_cover_letter
from logger import log


def create_cover_letter(
    job_title: str,
    company: str,
    job_description: str,
    matched_skills: list[str],
    output_dir: str = "cover_letters",
) -> str:
    """
    Generate a cover letter and save it to a .txt file.
    Returns the file path as a string.
    """
    Path(output_dir).mkdir(exist_ok=True)

    letter = generate_cover_letter(job_title, company, job_description, matched_skills)

    # Sanitise filename
    safe_company = "".join(c if c.isalnum() or c in "-_" else "_" for c in company)
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in job_title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{safe_company}_{safe_title}_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(letter)

    log.info(f"Cover letter saved: {filename}")
    return filename


def get_cover_letter_text(
    job_title: str,
    company: str,
    job_description: str,
    matched_skills: list[str],
) -> str:
    """Return cover letter text without saving to disk."""
    return generate_cover_letter(job_title, company, job_description, matched_skills)
