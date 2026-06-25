"""
config.py — Central configuration for LinkedIn Auto-Apply Bot
Uses FREE Google Gemini API — get key at https://aistudio.google.com/app/apikey
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Candidate Profile ────────────────────────────────────────────────────────
CANDIDATE = {
    "name": "Golla Nanda Kumar",
    "email": os.getenv("LINKEDIN_EMAIL", "nandagolla074@gmail.com"),
    "phone": os.getenv("PHONE", "7989853252"),
    "current_location": "Hyderabad",
    "years_of_experience": "4.6",
    "notice_period": "Immediate joiner",
    "work_authorization": "Yes",
    "willing_to_relocate": "Yes",
    "expected_salary": "Negotiable",
    "current_ctc": "",
    "title": "DevOps Engineer",
}

# ─── LinkedIn Credentials ─────────────────────────────────────────────────────
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "nandagolla074@gmail.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# ─── FREE AI — Google Gemini ──────────────────────────────────────────────────
# Get your FREE key (no credit card) at: https://aistudio.google.com/app/apikey
# Free tier: 1500 requests/day, 15 requests/minute — more than enough
# If you leave this blank, the bot uses built-in rule-based scoring (still works!)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "paste-your-free-gemini-key-here")
AI_MODEL       = "gemini-1.5-flash"   # Free, fast model

# ─── Resume ───────────────────────────────────────────────────────────────────
RESUME_PATH = Path(
    os.getenv("RESUME_PATH", "/home/ec2-user/linkedin-auto-apply/resume.pdf")
)

# ─── Job Search Settings ──────────────────────────────────────────────────────
JOB_TITLES = [
    "DevOps Engineer",
    "AWS DevOps Engineer",
    "Cloud Engineer",
    "Platform Engineer",
    "Site Reliability Engineer",
    "DevSecOps Engineer",
    "Infrastructure Engineer",
]

PREFERRED_LOCATIONS = [
    "Hyderabad",
    "Bangalore",
    "Pune",
    "Chennai",
    "Remote",
]

LINKEDIN_LOCATIONS = [
    "Hyderabad, Telangana, India",
    "Bengaluru, Karnataka, India",
    "Pune, Maharashtra, India",
    "Chennai, Tamil Nadu, India",
]

# ─── Filters ─────────────────────────────────────────────────────────────────
DATE_POSTED_FILTER  = "r604800"   # Past week; use "r86400" for past 24 hours
EMPLOYMENT_TYPE     = "F"         # F = Full-time
EASY_APPLY_ONLY     = True
MIN_COMPATIBILITY_SCORE = 70      # Skip jobs below this (lowered since rule-based scoring is conservative)

# ─── Application Rules ────────────────────────────────────────────────────────
MAX_APPLICANTS_SKIP     = 50
MAX_EXPERIENCE_REQUIRED = 6

SKIP_KEYWORDS = [
    "security clearance", "clearance required", "relocation required",
    "visa sponsorship", "us citizen", "contract", "contract to hire",
    "c2c", "corp to corp", "freelance", "internship", "intern",
    "third party", "third-party payroll", "staffing", "consulting firm",
]

COMPANY_AVOID_KEYWORDS = [
    "consulting", "consultancy", "staffing", "manpower",
    "recruitment", "outsourc",
]

# ─── Skills Profile ───────────────────────────────────────────────────────────
CANDIDATE_SKILLS = [
    "AWS", "Kubernetes", "EKS", "Terraform", "Jenkins", "Docker",
    "Linux", "Shell Scripting", "Git", "GitHub Actions", "Helm",
    "ArgoCD", "Ansible", "Prometheus", "Grafana", "ELK", "SonarQube",
    "DevSecOps", "CI/CD", "Infrastructure as Code", "Python", "Bash",
]

# ─── Browser / Bot Settings ───────────────────────────────────────────────────
HEADLESS    = True    # Must be True on EC2 server (no screen)
SLOW_MO     = 50
SESSION_FILE    = "session.json"
SCREENSHOT_DIR  = Path("screenshots")

DELAY_SHORT  = (0.5, 1.5)
DELAY_MEDIUM = (1.5, 3.0)
DELAY_LONG   = (3.0, 6.0)
DELAY_PAGE   = (4.0, 8.0)

# ─── Logging / Output ─────────────────────────────────────────────────────────
LOG_FILE = "bot.log"
CSV_FILE = "applications.csv"

# ─── Retry ────────────────────────────────────────────────────────────────────
MAX_RETRIES = 3
RETRY_DELAY = 5
