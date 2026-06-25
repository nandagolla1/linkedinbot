# 💼 LinkedIn Auto-Apply Bot

A production-ready Python automation bot that searches LinkedIn for DevOps Engineer roles, analyses each job with AI, and applies automatically via Easy Apply — with a real-time Streamlit dashboard.

---

## 🗂 Project Structure

```
linkedin-auto-apply/
├── main.py                  # Entry point — run this
├── config.py                # All settings (jobs, locations, filters)
├── playwright_bot.py        # Core Playwright browser automation
├── ai_matcher.py            # Claude AI: JD analysis, scoring, cover letters
├── cover_letter.py          # Cover letter generation & file saving
├── logger.py                # Logging + CSV tracker
├── utils.py                 # Delays, CAPTCHA detection, retries, helpers
├── streamlit_dashboard.py   # Live dashboard
├── requirements.txt
├── .env.example             # Template — copy to .env
├── run_daily.bat            # Windows Task Scheduler script
└── README.md
```

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.12+
- Windows / macOS / Linux
- LinkedIn account
- Anthropic API key → https://console.anthropic.com

### 2. Clone / Download the Project

```bash
cd C:\Users\maith
git clone <repo-url> linkedin-auto-apply
cd linkedin-auto-apply
```

### 3. Create Virtual Environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 5. Configure Credentials

```bash
# Copy the template
copy .env.example .env   # Windows
cp .env.example .env     # macOS / Linux
```

Edit `.env`:

```env
LINKEDIN_EMAIL=nandagolla074@gmail.com
LINKEDIN_PASSWORD=YourLinkedInPassword
ANTHROPIC_API_KEY=sk-ant-api03-...
PHONE=7989853252
RESUME_PATH=C:\Users\maith\Downloads\Golla_Nanda_Kumar_DevSecOps__Resume.pdf
```

### 6. Run the Bot

```bash
python main.py
```

The bot will:
1. Open a Chrome browser (visible by default — set `HEADLESS=True` in `config.py` to hide it)
2. Log in to LinkedIn
3. Search all job titles across all preferred locations
4. Analyse each job with AI
5. Pause before final submission — **press Enter to confirm, or type `skip`**
6. Log every application to `applications.csv`

### 7. Open the Dashboard

In a separate terminal:

```bash
streamlit run streamlit_dashboard.py
```

Opens at http://localhost:8501

---

## 🔧 Customisation Guide

### Update Your Resume

1. Replace the file at the path in `RESUME_PATH` (in `.env` or `config.py`)
2. Ensure it is a `.pdf` file
3. The bot automatically uploads it on every Easy Apply form

### Change Preferred Locations

Edit `config.py`:

```python
LINKEDIN_LOCATIONS = [
    "Hyderabad, Telangana, India",
    "Bengaluru, Karnataka, India",
    "Pune, Maharashtra, India",
    "Mumbai, Maharashtra, India",   # ← add new
]
```

Also update `PREFERRED_LOCATIONS` (plain names used for skip logic).

### Add New Job Titles

Edit `config.py`:

```python
JOB_TITLES = [
    "DevOps Engineer",
    "MLOps Engineer",       # ← add new
    "Cloud DevOps Engineer", # ← add new
    ...
]
```

### Adjust Compatibility Score Threshold

```python
MIN_COMPATIBILITY_SCORE = 75   # Change in config.py
```

### Change Date Filter

```python
DATE_POSTED_FILTER = "r86400"    # Past 24 hours
DATE_POSTED_FILTER = "r604800"   # Past week (default)
DATE_POSTED_FILTER = "r2592000"  # Past month
```

### Run in Headless Mode (no visible browser)

```python
HEADLESS = True   # in config.py
```

---

## 🕐 Run Daily (Windows Task Scheduler)

1. Edit `run_daily.bat` — update `PROJECT_DIR` to your path
2. Open Task Scheduler (`Win + R` → `taskschd.msc`)
3. **Create Basic Task**
   - Trigger: Daily, 9:00 AM
   - Action: Start a program → `C:\Users\maith\linkedin-auto-apply\run_daily.bat`
4. The bot output is appended to `scheduler.log`

### Run Daily (macOS/Linux cron)

```bash
crontab -e
# Run at 9 AM every day
0 9 * * * cd /home/user/linkedin-auto-apply && .venv/bin/python main.py >> scheduler.log 2>&1
```

---

## 🤖 AI Features

| Feature | Description |
|---|---|
| JD Analysis | Reads the full job description and extracts key requirements |
| Compatibility Score | 0–100 score comparing JD requirements to your profile |
| Cover Letter | Personalised 3-paragraph letter for each job |
| Question Answering | Answers standard Easy Apply questions automatically |
| Skill Gap Detection | Highlights skills in JD that you don't have |
| Company Type Detection | Identifies product companies vs consultancies |

---

## 📊 Dashboard Features

- Jobs Found / Applied / Skipped / Errors
- Apply rate and average compatibility score
- Score distribution histogram
- Daily applications timeline
- Top skip reasons
- Location breakdown
- Filterable full applications table
- CSV download

---

## 🛡 Safety Features

- Pauses before every final submission (user confirms with Enter)
- CAPTCHA detection with manual-solve prompt
- Human-like typing delays and random scrolling
- Session persistence (no re-login each run)
- Skip keywords to avoid consultancies / contracts
- Applicant count filter (skips over-applied jobs)
- Retry logic on network failures
- Full error screenshots saved to `screenshots/`

---

## 📁 Output Files

| File | Contents |
|---|---|
| `applications.csv` | All jobs: company, role, status, score, URL, date |
| `bot.log` | Full debug log |
| `session.json` | Saved browser session (no repeated login) |
| `cover_letters/` | All generated cover letters as `.txt` files |
| `screenshots/` | Error screenshots for debugging |

---

## ❓ Troubleshooting

**Login fails every time**
→ Check `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` in `.env`
→ Delete `session.json` and retry

**CAPTCHA appears**
→ The bot will pause and ask you to solve it manually in the browser
→ Once solved, press nothing — it automatically continues

**Resume not uploading**
→ Ensure `RESUME_PATH` points to an existing `.pdf` file
→ Check file permissions

**No jobs found**
→ LinkedIn may have changed its HTML selectors
→ Run with `HEADLESS=False` and watch what happens
→ Check `bot.log` for details

**AI scoring is off**
→ Check that `ANTHROPIC_API_KEY` is valid and has credits
→ Adjust `MIN_COMPATIBILITY_SCORE` in `config.py`

---

## 📜 Candidate Profile

- **Name:** Golla Nanda Kumar
- **Role:** DevOps / DevSecOps Engineer
- **Experience:** 4.6 years
- **Location:** Hyderabad
- **Phone:** 7989853252
- **Email:** nandagolla074@gmail.com
- **Skills:** AWS, Kubernetes, EKS, Terraform, Jenkins, Docker, Linux, Shell Scripting, Git, GitHub Actions, Helm, ArgoCD, Ansible, Prometheus, Grafana, ELK, SonarQube, DevSecOps

---

## ⚠ Disclaimer

This tool is for personal job searching. Use responsibly and in accordance with LinkedIn's Terms of Service.
