"""
ai_matcher.py — FREE AI using Google Gemini API (free tier: 1500 req/day).
No credit card required. Get key at: https://aistudio.google.com/app/apikey
"""

import json
import re
from typing import Optional

import google.generativeai as genai

from config import (
    GEMINI_API_KEY,
    AI_MODEL,
    CANDIDATE,
    CANDIDATE_SKILLS,
    MIN_COMPATIBILITY_SCORE,
)
from logger import log

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(AI_MODEL)

# ─── Resume Summary ───────────────────────────────────────────────────────────
RESUME_SUMMARY = """
Name: Golla Nanda Kumar
Title: DevOps / DevSecOps Engineer
Experience: 4.6 years
Location: Hyderabad, India

Core Skills:
- Cloud: AWS (EC2, EKS, ECS, RDS, S3, IAM, VPC, Route53, CloudWatch, CloudFormation)
- Container Orchestration: Kubernetes, EKS, Helm, ArgoCD
- IaC: Terraform, Ansible, CloudFormation
- CI/CD: Jenkins, GitHub Actions, GitLab CI
- Containers: Docker, Docker Compose
- Security: SonarQube, SAST/DAST, DevSecOps pipelines, Trivy, OWASP
- Monitoring: Prometheus, Grafana, ELK Stack (Elasticsearch, Logstash, Kibana)
- OS: Linux (RHEL, Ubuntu, Amazon Linux), Shell Scripting
- Version Control: Git, GitHub, GitLab, Bitbucket

Key Achievements:
- Migrated monolithic apps to microservices on EKS, reducing deployment time by 60%
- Built GitOps pipelines with ArgoCD reducing manual interventions by 80%
- Implemented DevSecOps practices cutting vulnerabilities by 45%
- Designed multi-region AWS infrastructure with 99.95% uptime SLA
- Reduced cloud costs by 30% through rightsizing and auto-scaling optimization
""".strip()


# ─── Helper: call Gemini API ──────────────────────────────────────────────────

def _call_gemini(prompt: str, max_tokens: int = 1500) -> str:
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3,
            ),
        )
        return response.text.strip()
    except Exception as e:
        log.error(f"Gemini API error: {e}")
        return ""


# ─── Rule-based fallback scorer (works with zero API calls) ──────────────────

def _rule_based_score(job_title: str, job_description: str) -> dict:
    """
    Fast keyword-based scoring when AI is unavailable.
    Returns same structure as the AI analysis dict.
    """
    text = (job_title + " " + job_description).lower()

    matched = [s for s in CANDIDATE_SKILLS if s.lower() in text]
    missing = [s for s in CANDIDATE_SKILLS if s.lower() not in text]

    # Base score from skill match ratio
    ratio = len(matched) / max(len(CANDIDATE_SKILLS), 1)
    score = int(40 + ratio * 50)  # 40–90 range

    # Bonus for key title words
    for kw in ["devops", "devsecops", "platform", "sre", "cloud", "aws"]:
        if kw in text:
            score = min(score + 3, 100)

    consultancy_words = ["consulting", "staffing", "c2c", "corp to corp", "third party",
                         "contract", "freelance", "recruitment"]
    is_consultancy = any(w in text for w in consultancy_words)

    clearance_words = ["security clearance", "clearance required", "us citizen only"]
    requires_clearance = any(w in text for w in clearance_words)

    sponsorship_words = ["sponsorship", "visa required", "work permit"]
    requires_sponsorship = any(w in text for w in sponsorship_words)

    contract_words = ["contract to hire", "c2h", "6 month contract", "12 month contract"]
    is_contract = any(w in text for w in contract_words)

    recommendation = "apply" if score >= MIN_COMPATIBILITY_SCORE and not is_consultancy else "skip"
    skip_reason = ""
    if is_consultancy:
        skip_reason = "Consultancy detected"
    elif score < MIN_COMPATIBILITY_SCORE:
        skip_reason = f"Low score ({score})"

    import re as _re
    exp_match = _re.search(r"(\d+)\+?\s*(?:years?|yrs?)", job_description, _re.IGNORECASE)
    req_exp = int(exp_match.group(1)) if exp_match else None

    salary_match = _re.search(r"(?:₹|INR|Rs\.?|LPA)[^\n]{0,30}", job_description, _re.IGNORECASE)
    salary = salary_match.group().strip() if salary_match else "N/A"

    return {
        "score": score,
        "matched_skills": matched[:10],
        "missing_skills": missing[:8],
        "required_experience": req_exp,
        "is_product_company": not is_consultancy,
        "is_consultancy": is_consultancy,
        "requires_clearance": requires_clearance,
        "requires_sponsorship": requires_sponsorship,
        "is_contract": is_contract,
        "salary": salary,
        "summary": f"{job_title} role requiring {', '.join(matched[:3])}.",
        "recommendation": recommendation,
        "skip_reason": skip_reason,
    }


# ─── 1. Job Analysis & Compatibility Score ────────────────────────────────────

def analyze_job(job_title: str, company: str, job_description: str) -> dict:
    """Analyse JD against candidate profile. Falls back to rule-based if API fails."""

    if not GEMINI_API_KEY or GEMINI_API_KEY == "paste-your-free-gemini-key-here":
        log.info("  No Gemini key — using rule-based scorer")
        return _rule_based_score(job_title, job_description)

    prompt = f"""
You are an expert ATS recruiter. Analyze this job description against the candidate profile.
Return ONLY a valid JSON object — no markdown, no explanation.

Candidate Profile:
{RESUME_SUMMARY}

Job Title: {job_title}
Company: {company}

Job Description:
{job_description[:3500]}

Return JSON with these exact keys:
- score (int 0-100): overall compatibility
- matched_skills (list of strings): candidate skills that match JD
- missing_skills (list of strings): JD skills not in candidate profile
- required_experience (int or null): minimum years asked for
- is_product_company (bool): true if product company or MNC
- is_consultancy (bool): true if staffing/consulting firm
- requires_clearance (bool): true if security clearance required
- requires_sponsorship (bool): true if visa sponsorship mentioned
- is_contract (bool): true if contract/C2C position
- salary (string): salary range if mentioned else "N/A"
- summary (string): 1-sentence JD summary
- recommendation (string): "apply" or "skip"
- skip_reason (string): reason if skip, else empty string

Return ONLY the JSON object.
"""
    raw = _call_gemini(prompt, max_tokens=800)

    # Strip markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")

    try:
        result = json.loads(raw)
        return result
    except json.JSONDecodeError:
        log.warning("Gemini JSON parse failed — using rule-based fallback")
        return _rule_based_score(job_title, job_description)


# ─── 2. Cover Letter Generator ────────────────────────────────────────────────

def generate_cover_letter(
    job_title: str,
    company: str,
    job_description: str,
    matched_skills: list,
) -> str:
    """Generate cover letter. Falls back to a template if no API key."""

    template = (
        f"Dear Hiring Manager,\n\n"
        f"I am excited to apply for the {job_title} position at {company}. "
        f"With 4.6 years of hands-on DevOps and DevSecOps experience, I have built and scaled "
        f"cloud-native infrastructure on AWS using Kubernetes, Terraform, Jenkins, and ArgoCD — "
        f"driving a 60% reduction in deployment time and 30% savings in cloud costs.\n\n"
        f"My expertise closely aligns with your requirements: {', '.join((matched_skills or CANDIDATE_SKILLS)[:5])}. "
        f"I have a strong track record of implementing GitOps workflows, DevSecOps pipelines with SonarQube and Trivy, "
        f"and building monitoring stacks with Prometheus, Grafana, and the ELK Stack.\n\n"
        f"I would welcome the opportunity to contribute to your team. "
        f"Thank you for considering my application.\n\n"
        f"Sincerely,\nGolla Nanda Kumar\n+91-7989853252 | nandagolla074@gmail.com"
    )

    if not GEMINI_API_KEY or GEMINI_API_KEY == "paste-your-free-gemini-key-here":
        log.info("  No Gemini key — using cover letter template")
        return template

    prompt = f"""
Write a professional cover letter for this job application. Max 220 words, 3 paragraphs.

Candidate: Golla Nanda Kumar — DevOps Engineer, 4.6 years experience
Target Role: {job_title} at {company}
Matched Skills: {', '.join((matched_skills or [])[:8])}

Job Description excerpt:
{job_description[:1500]}

Rules:
- Start with "Dear Hiring Manager,"
- Para 1: One specific achievement with a number
- Para 2: 3 skills matching the JD
- Para 3: Call to action
- End with: Sincerely,\\nGolla Nanda Kumar\\n+91-7989853252 | nandagolla074@gmail.com
- No clichés like "I am writing to express my interest"
- No address block or date
"""
    letter = _call_gemini(prompt, max_tokens=500)
    return letter if letter else template


# ─── 3. Answer Form Questions ─────────────────────────────────────────────────

def answer_question(question: str, job_context: str = "") -> str:
    """Rule-based fast answers. Gemini only for unknown questions."""
    q_lower = question.lower()

    # Fast rule-based answers — no API call needed
    rules = [
        (["year", "experience", "how many", "total exp"],       CANDIDATE["years_of_experience"]),
        (["notice period", "notice", "available", "join"],       CANDIDATE["notice_period"]),
        (["current location", "where are you", "city", "based"], CANDIDATE["current_location"]),
        (["work authoriz", "authorized", "visa", "sponsor"],     CANDIDATE["work_authorization"]),
        (["relocat"],                                             CANDIDATE["willing_to_relocate"]),
        (["expected salary", "salary expect", "ctc expect"],     CANDIDATE["expected_salary"]),
        (["current ctc", "current salary", "current comp"],      CANDIDATE["current_ctc"] or "Open to discussion"),
        (["phone", "contact", "mobile"],                         CANDIDATE["phone"]),
        (["email"],                                               CANDIDATE["email"]),
        (["name"],                                                CANDIDATE["name"]),
        (["fresher", "experienced"],                              "Experienced"),
        (["highest qualification", "degree", "education"],       "Bachelor of Technology"),
        (["willing to work night", "shift"],                      "Yes"),
        (["immediate", "can you join"],                          "Yes, immediate joiner"),
    ]

    for keywords, answer in rules:
        if any(kw in q_lower for kw in keywords):
            return answer

    # Only call Gemini for truly unknown questions
    if not GEMINI_API_KEY or GEMINI_API_KEY == "paste-your-free-gemini-key-here":
        return "Yes"

    prompt = f"""
You are answering a job application question on behalf of this candidate:
{RESUME_SUMMARY}

Question: {question}

Give a direct answer in 1-2 sentences. Start with Yes or No if it's a yes/no question.
"""
    answer = _call_gemini(prompt, max_tokens=150)
    return answer if answer else "Yes"


# ─── 4. Detect Missing Skills ─────────────────────────────────────────────────

def detect_skill_gaps(job_description: str) -> list:
    text = job_description.lower()
    return [s for s in CANDIDATE_SKILLS if s.lower() not in text]
