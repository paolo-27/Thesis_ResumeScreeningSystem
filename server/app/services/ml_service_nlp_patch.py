"""
ml_service_nlp_patch.py
=======================
Drop-in NLP-enhanced replacements for the core extraction + scoring
functions in ml_service.py.

ALL FIXES IN THIS VERSION
--------------------------
Fix 1 – Relevance gate (TF-IDF + SBERT threshold before any scoring)
Fix 2 – Hard skills vs soft skills separation
Fix 3 – Field extraction only from degree-phrase context windows
Fix 4 – Fake / lorem ipsum resume guard
Fix 5 – Improved keyword stuffing detector:
         - Per-section TTR (worst section wins, not whole-document average)
           Prevents filler summary from masking a stuffed experience section
         - Consecutive repeat ratio (independent signal, no threshold combo needed)
           "React React React" → ratio ~0.73 → flagged immediately
         - Both signals checked independently — either one alone is enough
"""

from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

# ---------------------------------------------------------------------------
# Lazy NLP initialisation
# ---------------------------------------------------------------------------
try:
    import spacy
    from spacy.matcher import PhraseMatcher

    _nlp      = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    _nlp_full = spacy.load("en_core_web_sm", disable=["tagger", "attribute_ruler", "lemmatizer"])
    _SPACY_OK = True
    print("[nlp_patch] spaCy loaded successfully.")
except Exception as _spacy_err:
    import traceback as _tb
    _nlp = _nlp_full = None
    _SPACY_OK = False
    print(f"[nlp_patch] spaCy failed to load: {_spacy_err}")
    _tb.print_exc()

try:
    from rapidfuzz import fuzz as _fuzz
    _FUZZ_OK = True
except ImportError:
    _fuzz    = None
    _FUZZ_OK = False
    print("[nlp_patch] rapidfuzz not available – fuzzy skill matching disabled.")


# ---------------------------------------------------------------------------
# Lazy host module reference
# ---------------------------------------------------------------------------
def _host():
    import importlib, sys
    return sys.modules.get("ml_service") or importlib.import_module("ml_service")


# ===========================================================================
# FIX 1 – RELEVANCE GATE
# ===========================================================================

def _relevance_gate(tfidf_sim: float, sbert_sim: float) -> str:
    """
    Returns 'reject', 'weak', or 'normal'.
    reject : sbert < 0.15 AND tfidf < 0.05  → all scores = 0
    weak   : sbert < 0.25 AND tfidf < 0.10  → scores capped
    normal : anything else                   → full scoring
    """
    if sbert_sim < 0.15 and tfidf_sim < 0.05:
        return "reject"
    if sbert_sim < 0.25 and tfidf_sim < 0.10:
        return "weak"
    return "normal"


# ===========================================================================
# FIX 2 – HARD vs SOFT SKILL SEPARATION
# ===========================================================================

_SOFT_SKILLS = {
    # These never count toward skills_match_score — too generic or purely behavioural
    "leadership", "communication", "problem solving", "customer service",
    "scheduling", "team management", "compliance", "training",
    "time management", "integrity", "cash handling", "inventory management",
    "negotiation", "people management", "cross-functional",
}

_STRONG_EVIDENCE_REQUIRED = {
    "excel", "word", "access", "accounting", "bookkeeping", "laravel",
    "azure", "gcp", "cybersecurity", "fastapi",
    "feature engineering", "marketing", "sales",
}

# Per-skill specific context validators — stricter than generic _TECH_CONTEXT_KEYWORDS
# If a skill has an entry here, ONLY these keywords validate it (not the generic set)
_SKILL_SPECIFIC_CONTEXT = {
    "accounting": {
        "accounting", "accounts payable", "accounts receivable",
        "financial reporting", "gaap", "ifrs", "cpa", "auditor",
        "bookkeeper", "general ledger", "tax", "financial statement",
    },
    "bookkeeping": {
        "bookkeeping", "accounts payable", "accounts receivable",
        "general ledger", "financial records", "accounting",
    },
    "marketing": {
        "digital marketing", "seo", "sem", "campaign", "brand strategy",
        "ecommerce", "lead generation", "marketing automation",
        "social media marketing", "content marketing", "marketing manager",
        "marketing coordinator", "marketing specialist",
    },
    "sales": {
        "sales target", "sales pipeline", "sales representative",
        "account executive", "business development", "lead generation",
        "crm", "salesforce", "quota", "revenue target", "sales manager",
    },
    "excel": {
        "microsoft", "office suite", "spreadsheet", "google sheets",
        "pivot table", "vlookup", "excel formula", "data analysis",
        "financial model", "dashboard", "microsoft excel",
    },
    "crm": {
        "crm", "salesforce", "hubspot", "customer relationship",
        "pipeline", "sales", "account management", "lead",
    },
    "salesforce": {
        "salesforce", "sfdc", "crm", "sales cloud", "service cloud",
        "sales", "account management",
    },
    "b2b sales": {
        "b2b", "business to business", "sales", "account", "enterprise",
        "lead generation", "pipeline", "quota",
    },
    "b2c sales": {
        "b2c", "retail", "consumer", "sales", "customer",
    },
    "cold calling": {
        "cold call", "outbound", "sales", "prospecting", "lead generation",
    },
    "pipeline management": {
        "pipeline", "sales", "crm", "lead", "funnel", "revenue",
    },
    "financial modeling": {
        "financial model", "financial analysis", "forecast", "valuation",
        "excel", "investment", "dcf", "finance",
    },
    "budgeting": {
        "budget", "financial planning", "cost", "forecast", "expenditure",
        "finance", "p&l", "profit",
    },
    "tax compliance": {
        "tax", "bir", "vat", "income tax", "tax return", "tax filing",
        "compliance", "taxation",
    },
    "payroll": {
        "payroll", "salary", "compensation", "employee", "wages",
        "hr", "human resources", "payslip",
    },
    "data entry": {
        "data entry", "encoding", "database", "records", "spreadsheet",
        "administrative", "clerical", "data input",
    },
    "calendar management": {
        "calendar", "schedule", "appointment", "meeting", "executive",
        "administrative", "diary",
    },
    "strategic planning": {
        "strategy", "strategic", "planning", "roadmap", "business plan",
        "corporate", "vision", "objectives", "goals",
    },
    "process improvement": {
        "process", "improvement", "lean", "six sigma", "efficiency",
        "optimization", "workflow", "sop", "standard operating",
    },
    "project management": {
        "project", "pmp", "prince2", "agile", "scrum", "waterfall",
        "timeline", "milestone", "deliverable", "stakeholder",
    },
    "operations management": {
        "operations", "operational", "process", "efficiency", "kpi",
        "performance", "management", "department", "team",
    },
    "performance management": {
        "performance", "appraisal", "review", "kra", "kpi", "evaluation",
        "employee performance", "goal setting",
    },
    "call center": {
        "call center", "call centre", "contact center", "bpo",
        "inbound", "outbound", "voice", "customer service",
    },
    "zendesk": {
        "zendesk", "ticketing", "customer support", "helpdesk",
        "support ticket", "service desk",
    },
    "complaint handling": {
        "complaint", "issue resolution", "escalation", "customer service",
        "dispute", "after sales", "customer satisfaction",
    },
    "ecommerce": {
        "ecommerce", "e-commerce", "online store", "shopify",
        "lazada", "shopee", "woocommerce", "online selling",
    },
    "brand management": {
        "brand", "branding", "brand identity", "brand strategy",
        "marketing", "brand equity", "positioning",
    },
    "market research": {
        "market research", "consumer research", "survey",
        "market analysis", "competitor analysis", "insights",
    },
    "email marketing": {
        "email marketing", "email campaign", "mailchimp", "klaviyo",
        "newsletter", "open rate", "click through",
    },
}

_TECH_CONTEXT_KEYWORDS = {
    "microsoft", "office suite", "spreadsheet", "database", "server",
    "cloud", "platform", "framework", "php", "python", "api", "devops",
    "software", "application", "system", "network", "security",
    "machine learning", "pipeline", "engineering", "backend", "frontend",
    "developer", "programming", "web", "infrastructure", "deployment",
    "repository", "digital marketing", "seo", "campaign", "brand strategy",
    "accounts payable", "accounts receivable", "financial reporting",
    "payroll", "general ledger", "financial statement",
}


# ===========================================================================
# FIX 3 – FIELD HEADER BLOCKLIST
# ===========================================================================

_FIELD_HEADER_BLOCKLIST = {
    "education", "experience", "skills", "references", "contact",
    "language", "languages", "summary", "objective", "profile",
    "work", "employment", "certifications", "achievements", "awards",
    "interests", "hobbies", "projects", "volunteer", "activities",
    "overview", "requirements", "responsibilities", "qualifications",
    "key", "about", "introduction", "highlights", "competencies",
}


# ===========================================================================
# FIX 4 – FAKE / LOREM IPSUM GUARD
# ===========================================================================

_LOREM_IPSUM_SIGNALS = {
    "lorem ipsum", "dolor sit amet", "consectetur adipiscing",
    "praesent rutrum", "sed sodales", "rhoncus lacinia",
    "proin justo", "cras facilisis", "tincidunt pharetra",
    "mollis laoreet", "volutpat", "reallygreatsite.com",
    "anywhere st", "123-456-7890",
}

_MIN_REAL_WORD_COUNT = 40

def _is_fake_resume(text: str) -> bool:
    """True if the resume is a lorem ipsum template or has too little real content."""
    if not text:
        return True
    lower = text.lower()
    if any(signal in lower for signal in _LOREM_IPSUM_SIGNALS):
        return True
    stripped = re.sub(
        r"\b(education|experience|skills|contact|references|language|"
        r"summary|objective|profile|work|employment|certifications)\b",
        "", lower, flags=re.IGNORECASE,
    )
    return len(re.findall(r"[a-z]{3,}", stripped)) < _MIN_REAL_WORD_COUNT


# ===========================================================================
# FIX 5 – IMPROVED KEYWORD STUFFING DETECTOR
# ===========================================================================

# Section header splitter — splits resume into named sections
_SECTION_SPLIT_RE = re.compile(
    r"\n(?:professional\s+)?(?:experience|summary|skills|education|"
    r"projects|certifications|objective|profile|employment|achievements)\b",
    re.IGNORECASE,
)

# Action verbs that signal real work experience descriptions
_ACTION_VERBS_RE = re.compile(
    r"\b(built|developed|designed|led|managed|created|implemented|"
    r"optimized|maintained|deployed|migrated|integrated|architected|"
    r"delivered|improved|reduced|increased|automated|collaborated|"
    r"coordinated|mentored|reviewed|tested|analyzed|researched|"
    r"established|launched|scaled|supported|resolved|handled|"
    r"engineered|refactored|debugged|configured|monitored|executed)\b",
    re.IGNORECASE,
)

# Date pattern — years and month names
_DATE_RE = re.compile(
    r"\b(19|20)\d{2}\b"
    r"|"
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.IGNORECASE,
)

# Max scores allowed for stuffed resumes
_STUFFED_CAPS = {
    "skills": 1,    # partial credit — they listed real skills
    "domain":  0.5, # partial domain credit
    "edu":     0,   # cannot verify education from keyword lists
    "exp":     0,   # cannot verify experience from stuffed text
}


def _type_token_ratio(text: str) -> float:
    """
    Ratio of unique words to total words.
    Legitimate prose: ~0.40–0.70
    Stuffed text:     ~0.10–0.20
    """
    words = re.findall(r"[a-z]{2,}", text.lower())
    if not words:
        return 1.0
    return len(set(words)) / len(words)


def _section_stuffing_score(text: str) -> float:
    """
    Split the resume into sections and return the WORST (lowest) TTR
    found across all sections with enough words to measure.

    This prevents a clean professional summary from masking a
    stuffed experience section when averaging over the whole document.
    """
    sections = _SECTION_SPLIT_RE.split(text)
    if len(sections) <= 1:
        # No sections found — check the whole text
        return _type_token_ratio(text)

    worst_ttr = 1.0
    for section in sections:
        section = section.strip()
        words   = re.findall(r"[a-z]{2,}", section.lower())
        if len(words) < 10:
            # Too short to measure reliably — skip
            continue
        ttr       = len(set(words)) / len(words)
        worst_ttr = min(worst_ttr, ttr)

    return worst_ttr


def _worst_section_consecutive_ratio(text: str) -> float:
    """
    Split the resume into sections and return the WORST (highest) consecutive
    repeat ratio found across all sections with enough words to measure.
    """
    sections = _SECTION_SPLIT_RE.split(text)

    if len(sections) <= 1:
        # Fallback: case-insensitive split on common headers without requiring \n
        sections = re.split(
            r"(?i)\b(professional\s+experience|professional\s+summary|"
            r"work\s+experience|skills|education|projects|certifications|"
            r"summary|objective|employment|achievements)\b",
            text,
        )

    if len(sections) <= 1:
        # Last resort: split on double newlines
        sections = re.split(r"\n\s*\n", text)

    worst_ratio = 0.0
    for section in sections:
        section = section.strip()
        words   = re.findall(r"[a-z]{2,}", section.lower())
        if len(words) < 5:
            continue
        repeats = sum(1 for i in range(1, len(words)) if words[i] == words[i - 1])
        ratio   = repeats / (len(words) - 1)
        worst_ratio = max(worst_ratio, ratio)

    return worst_ratio


def _consecutive_repeat_ratio(text: str) -> float:
    """
    Fraction of consecutive word pairs that are the same word.
    Whole-document version — used as fallback.
    """
    words = re.findall(r"[a-z]{2,}", text.lower())
    if len(words) < 2:
        return 0.0
    repeats = sum(1 for i in range(1, len(words)) if words[i] == words[i - 1])
    return repeats / (len(words) - 1)


def _has_work_history(text: str) -> bool:
    """
    True if the resume has at least 2 date references AND 2 action verbs.
    Both are required — a list of dates with no verbs is not work history.
    """
    date_hits   = len(_DATE_RE.findall(text))
    action_hits = len(_ACTION_VERBS_RE.findall(text))
    return date_hits >= 2 and action_hits >= 2


def _is_stuffed_resume(text: str) -> bool:
    """
    Returns True if the resume appears to be keyword-stuffed.

    THREE signals checked — any one can flag:

    Signal A: worst section TTR < 0.25 AND no real work history
      Catches stuffed sections hidden by a clean summary.
      Requires BOTH conditions to avoid penalising short legitimate resumes.

    Signal B: worst SECTION consecutive repeat ratio >= 0.25
      Catches "React React React" concentrated in one section.
      Per-section so the experience spam isn't diluted by the summary.

    Signal C: whole-doc consecutive repeat ratio >= 0.30
      Safety net for resumes with no section headers where
      spam is spread across the whole document.
    """
    worst_ttr          = _section_stuffing_score(text)
    worst_sec_consec   = _worst_section_consecutive_ratio(text)
    whole_doc_consec   = _consecutive_repeat_ratio(text)
    has_history        = _has_work_history(text)

    # Signal A: low section TTR + no history
    if worst_ttr < 0.25 and not has_history:
        return True

    # Signal B: high consecutive repeat in a specific section
    if worst_sec_consec >= 0.25:
        return True

    # Signal C: whole-doc consecutive repeat fallback
    if whole_doc_consec >= 0.30:
        return True

    return False


# ===========================================================================
# TEXT HELPERS
# ===========================================================================

def _join_split_lines(text: str) -> str:
    """Join lines split mid-phrase by PDF extraction."""
    lines  = text.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append("")
            continue
        if result and re.search(
            r"\b(in|of|and|or|the|a|an|for|with|at|by)\s*$",
            result[-1], re.IGNORECASE,
        ):
            result[-1] = result[-1].rstrip() + " " + stripped
        else:
            result.append(stripped)
    return "\n".join(result)


def _lemmatise(text: str) -> str:
    if not _SPACY_OK or not text:
        return text.lower()
    doc = _nlp(text[:50_000])
    return " ".join(tok.lemma_.lower() for tok in doc)


def _has_tech_context(sentence: str, skill: str = None) -> bool:
    """
    Returns True if sentence contains a validating context keyword.
    If skill has a specific context validator, use that instead of the
    generic _TECH_CONTEXT_KEYWORDS — prevents broad matches like "budget"
    validating "accounting" or "communications" validating "marketing".
    """
    lower = sentence.lower()
    if skill and skill in _SKILL_SPECIFIC_CONTEXT:
        return any(kw in lower for kw in _SKILL_SPECIFIC_CONTEXT[skill])
    return any(kw in lower for kw in _TECH_CONTEXT_KEYWORDS)


def _strict_word_match(text: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])"
    return bool(re.search(pattern, text.lower()))


# ===========================================================================
# PhraseMatcher builders
# ===========================================================================

@lru_cache(maxsize=1)
def _build_skill_matcher():
    if not _SPACY_OK:
        return None
    h       = _host()
    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    for canonical, aliases in h.SKILL_ALIASES.items():
        patterns = [_nlp.make_doc(a) for a in aliases if len(a) >= 4]
        if patterns:
            matcher.add(canonical, patterns)
    return matcher


@lru_cache(maxsize=1)
def _build_domain_matcher():
    if not _SPACY_OK:
        return None
    h       = _host()
    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    for domain, keywords in h.DOMAIN_KEYWORDS.items():
        patterns = [_nlp.make_doc(kw) for kw in keywords]
        matcher.add(domain, patterns)
    return matcher


@lru_cache(maxsize=1)
def _build_field_matcher():
    if not _SPACY_OK:
        return None
    h       = _host()
    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    for canonical, aliases in h.FIELD_ALIASES.items():
        if canonical.lower() in _FIELD_HEADER_BLOCKLIST:
            continue
        patterns = [
            _nlp.make_doc(a) for a in aliases
            if a.lower() not in _FIELD_HEADER_BLOCKLIST
        ]
        if patterns:
            matcher.add(canonical, patterns)
    return matcher


# ===========================================================================
# 1. extract_skills
# ===========================================================================

def extract_skills(text: str) -> set:
    """
    Extract canonical HARD skill names only.
    Soft skills never count. Strong-evidence skills require tech context nearby.
    """
    if not text:
        return set()

    h          = _host()
    text       = _join_split_lines(text)
    normalised = h.normalize_text(text)
    sentences  = re.split(r"[.!?\n]", normalised)
    found: set[str] = set()

    for canonical, aliases in h.SKILL_ALIASES.items():
        if canonical in _SOFT_SKILLS:
            continue
        matched = False
        for alias in aliases:
            if len(alias) < 4:
                continue
            if not _strict_word_match(normalised, alias):
                continue
            if canonical in _STRONG_EVIDENCE_REQUIRED:
                containing = [s for s in sentences if _strict_word_match(s, alias)]
                # Pass skill name so skill-specific context validator is used
                if not containing or not any(
                    _has_tech_context(s, skill=canonical) for s in containing
                ):
                    continue
            matched = True
            break
        if matched:
            found.add(canonical)

    # RapidFuzz pass for OCR/typo variants
    if _FUZZ_OK and len(text) < 15_000:
        alias_table = [
            (alias, canonical)
            for canonical, aliases in h.SKILL_ALIASES.items()
            for alias in aliases
            if len(alias) >= 5
            and canonical not in found
            and canonical not in _SOFT_SKILLS
        ]
        for token in re.split(r"[\s,;|()/\-]+", normalised):
            token = token.strip()
            if not token or len(token) < 5:
                continue
            for alias, canonical in alias_table:
                if canonical in found:
                    continue
                if _fuzz.ratio(token, alias) >= 90:
                    if canonical in _STRONG_EVIDENCE_REQUIRED:
                        containing = [s for s in sentences if token in s]
                        if not containing or not any(
                            _has_tech_context(s, skill=canonical) for s in containing
                        ):
                            continue
                    found.add(canonical)
                    break

    return found


# ===========================================================================
# 2. extract_domains
# ===========================================================================

def extract_domains(text: str) -> set:
    if not text:
        return set()

    h     = _host()
    text  = _join_split_lines(text)
    found: set[str] = set()

    matcher = _build_domain_matcher()
    if matcher is not None:
        doc = _nlp(text[:50_000])
        for match_id, _s, _e in matcher(doc):
            found.add(_nlp.vocab.strings[match_id])

    normalised = h.normalize_text(text)
    for domain, keywords in h.DOMAIN_KEYWORDS.items():
        if any(h.contains_term(normalised, kw) for kw in keywords):
            found.add(domain)

    if "data_analytics" in found:
        strong = any(h.contains_term(normalised, t) for t in h._DATA_ANALYTICS_STRONG_TERMS)
        weak   = sum(1 for t in h._DATA_ANALYTICS_WEAK_TERMS if h.contains_term(normalised, t))
        mktg   = any(h.contains_term(normalised, t) for t in h._MARKETING_CONTEXT_TERMS)
        if not strong and (mktg or weak < 2):
            found.discard("data_analytics")

    if "hr_recruitment" in found:
        strong_hr = any(h.contains_term(normalised, t) for t in h._HR_RECRUITMENT_STRONG_TERMS)
        weak_hr   = sum(1 for t in h._HR_RECRUITMENT_WEAK_TERMS if h.contains_term(normalised, t))
        if not strong_hr and weak_hr < 2:
            found.discard("hr_recruitment")

    return found


# ===========================================================================
# 3. extract_degree_level
# ===========================================================================

def extract_degree_level(text: str) -> str:
    if not text:
        return "none"
    text      = _join_split_lines(text)
    raw_level = _original_extract_degree_level(text)
    if _SPACY_OK:
        nlp_level   = _original_extract_degree_level(_lemmatise(text))
        level_order = ["none", "bachelor", "master", "phd"]
        if level_order.index(nlp_level) > level_order.index(raw_level):
            return nlp_level
    return raw_level


def _original_extract_degree_level(text: str) -> str:
    h    = _host()
    text = h.normalize_text(text)
    text = h._sanitize_for_degree(text)

    if re.search(r"(?<![a-z])(phd|ph d|doctorate|doctoral)(?![a-z])", text):
        return "phd"
    if re.search(
        r"(?<![a-z])(master|masters|masters degree|masters in|masters of|"
        r"m s|ma|m a|msc|m sc|mba)(?![a-z])", text,
    ) or re.search(
        r"(?<![a-z])ms(?!\s*(word|excel|office|sql|powerpoint|project|"
        r"access|windows|dynamics|teams|outlook|publisher|\d))(?![a-z])", text,
    ):
        return "master"
    if re.search(
        r"(?<![a-z])(bachelor|bachelors|bachelors degree|bachelors in|"
        r"bachelor of|bs|b s|bsc|b sc|undergraduate)(?![a-z])", text,
    ) or re.search(
        r"(?<![a-z])ba(?!\s*(analyst|analysis|analytics))(?![a-z])", text,
    ):
        return "bachelor"
    if h._has_strong_graduate_context(text):
        return "bachelor"
    return "none"


# ===========================================================================
# 4. extract_fields  (degree-phrase context windows only)
# ===========================================================================

_DEGREE_CONTEXT_RE = re.compile(
    r"(?:bachelor(?:s|\'s)?(?:\s+of(?:\s+science)?(?:\s+in)?)?|"
    r"master(?:s|\'s)?(?:\s+of(?:\s+science)?(?:\s+in)?)?|"
    r"bs|bsc|ba|ms|msc|ma|mba|phd|ph\s*d|doctorate(?:\s+in)?|"
    r"bachelor|master|degree\s+in|studied)\s*(?:in|of|:)?\s*",
    re.IGNORECASE,
)

def extract_fields(text: str) -> set:
    if not text:
        return set()

    h    = _host()
    text = _join_split_lines(text)
    found: set[str] = set()

    for segment in re.split(r"[\n\r]{1,2}", text):
        for m in _DEGREE_CONTEXT_RE.finditer(segment):
            tail = segment[m.end(): m.end() + 150]
            tail = re.split(r"[,|;\n]", tail)[0].strip()
            if not tail or tail.lower().strip() in _FIELD_HEADER_BLOCKLIST:
                continue
            normalised_tail = h.normalize_field_text(tail)
            for canonical, aliases in h.FIELD_ALIASES.items():
                if canonical.lower() in _FIELD_HEADER_BLOCKLIST:
                    continue
                if canonical not in found and any(
                    h.contains_term(normalised_tail, alias)
                    for alias in aliases
                    if alias.lower() not in _FIELD_HEADER_BLOCKLIST
                ):
                    found.add(canonical)

    return found


# ===========================================================================
# 5. extract_resume_years
# ===========================================================================

def extract_resume_years(resume_text: str) -> float:
    if not resume_text:
        return 0.0
    resume_text = _join_split_lines(resume_text)
    base        = _original_extract_resume_years(resume_text)
    if not _SPACY_OK or base > 0:
        return base
    doc   = _nlp_full(resume_text[:50_000])
    dates = [e.text for e in doc.ents if e.label_ == "DATE"]
    if not dates:
        return base
    return max(base, _original_extract_resume_years(" ".join(dates)))


def _original_extract_resume_years(resume_text: str) -> float:
    h = _host()

    # Education section keywords — segments near these should be zero-weighted
    _EDU_CONTEXT_TERMS = {
        "bachelor", "master", "phd", "doctorate", "doctoral", "degree",
        "graduate", "graduated", "university", "college", "school",
        "gpa", "coursework", "thesis", "information technology",
        "computer science", "engineering", "b s", "bs", "bsc", "ms", "msc",
        "associate", "diploma", "certification course",
    }

    _WORK_OVERRIDE_TERMS = {
        "experience", "work history", "professional experience",
        "employment", "career", "present", "current", "company",
        "developer", "engineer", "analyst", "manager", "specialist",
        # Protect explicit year-quantity mentions (e.g. "5+ Years Experience" in header)
        "years", "yrs", "yr",
        # Protect job-title lines that may sit near edu context in the lookback window
        "lead", "senior", "junior", "intern", "coordinator", "director",
    }

    explicit_patterns = [
        h._NUM_PATTERN + r"\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(?:at\s+least|over|more\s+than|with)\s+" + h._NUM_PATTERN
        + r"\s*(?:years?|yrs?)\s*(?:of\s+experience)?",
        r"experience\s*[:\-]?\s*" + h._NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"(?:work|working|professional|related)\s+experience\s*[:\-]?\s*"
        + h._NUM_PATTERN + r"\s*(?:years?|yrs?)",
        rf"experience[^.\n]{{0,40}}?{h._NUM_PATTERN}\s*(?:years?|yrs?)",
        h._NUM_PATTERN + r"\s*(?:years?|yrs?)\b[^.\n]{0,40}?experience",
        r"worked\s+for\s+" + h._NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"professional\s+experience\s+(?:of\s+)?" + h._NUM_PATTERN + r"\s*(?:years?|yrs?)",
        h._NUM_PATTERN + r"\s*(?:years?|yrs?)\s+(?:in|with|of)",
    ]

    explicit_values    = []
    weighted_intervals = []
    segments = h.experience_segments(resume_text)

    for index, segment in enumerate(segments):
        # Look back 1 segment only — a wider window causes the EDUCATION section
        # (which typically appears at the bottom of the resume) to bleed into
        # the context check for work-experience date segments above it, wrongly
        # zeroing out calculated years (e.g. when "Computer Science" or "Bachelor"
        # appears in the lookback of a "June 2018 – December 2020" work segment).
        lookback_start   = max(0, index - 1)
        wide_context     = " ".join(segments[lookback_start: index + 1]).lower()

        # If education keyword in wide context AND no work override → skip
        if any(term in wide_context for term in _EDU_CONTEXT_TERMS):
            if not any(term in wide_context for term in _WORK_OVERRIDE_TERMS):
                continue

        context = h._segment_context_window(segments, index)
        weight  = h._experience_segment_weight(segment, context=context)
        if weight <= 0:
            continue

        seg_vals = h._extract_explicit_year_values(
            segment, explicit_patterns, range_mode="max"
        )
        seg_vals.extend(h._extract_explicit_duration_years(segment))
        explicit_values.extend(v * weight for v in seg_vals)

        for interval in h._extract_date_intervals_from_segment(segment):
            weighted_intervals.append((interval, weight))

    interval_years = h._weighted_intervals_to_years(weighted_intervals)
    explicit_years  = max(explicit_values) if explicit_values else 0

    if explicit_years or interval_years:
        return max(explicit_years, interval_years)

    return h._estimate_implicit_resume_years(resume_text)


def extract_required_years(job_description: str) -> float:
    if not job_description:
        return 0.0
    job_description = _join_split_lines(job_description)
    base = _original_extract_required_years(job_description)
    if base > 0 or not _SPACY_OK:
        return base
    doc   = _nlp_full(job_description[:50_000])
    dates = [e.text for e in doc.ents if e.label_ == "DATE"]
    if not dates:
        return base
    return _original_extract_required_years(" ".join(dates)) or base


def _original_extract_required_years(job_description: str) -> float:
    """Inline — never calls h.extract_required_years() to avoid recursion."""
    h = _host()
    explicit_patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(?:at\s+least|over|more\s+than|minimum(?:\s+of)?|with)\s+(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:relevant\s+)?(?:work\s+)?experience",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:in\s+)?(?:the\s+)?(?:industry|field|role|position)",
        r"(\d+(?:\.\d+)?)\s*[-\u2013]\s*\d+\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(\d+)\+\s*(?:years?|yrs?)",
    ]
    values = h._extract_explicit_year_values(job_description, explicit_patterns, range_mode="min")
    return float(min(values)) if values else 0.0


# ===========================================================================
# 7. skills_match_score  (all fixes applied)
# ===========================================================================

def skills_match_score(
    resume_text: str,
    job_description: str,
    tfidf_sim: float = 0.0,
    sbert_sim: float = 0.0,
) -> int:
    if _is_fake_resume(resume_text):
        return 0

    gate = _relevance_gate(tfidf_sim, sbert_sim)
    if gate == "reject":
        return 0

    stuffed = _is_stuffed_resume(resume_text)
    cap     = _STUFFED_CAPS["skills"] if stuffed else 2

    h             = _host()
    jd_skills     = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)
    has_semantic_signal = tfidf_sim > 0 or sbert_sim > 0

    if not jd_skills:
        jd_domains  = extract_domains(job_description)
        jd_families = h.extract_role_families(job_description)
        raw = 1 if (jd_domains or jd_families) else 0
        raw = min(raw, cap)
        return min(raw, 1) if gate == "weak" else raw

    overlap = len(jd_skills & resume_skills)
    ratio   = overlap / max(len(jd_skills), 1)

    if ratio >= 0.60 or overlap >= 5:
        raw = 2
    elif ratio >= 0.25 or overlap >= 2:
        raw = 1
    elif _sbert_skill_similarity(jd_skills, resume_skills) >= 0.45:
        raw = 1
    else:
        shared_skills  = jd_skills & resume_skills
        jd_domains     = extract_domains(job_description)
        resume_domains = extract_domains(resume_text)
        technical_bridge          = bool(shared_skills & h._TECHNICAL_BRIDGE_SKILLS)
        related_technical_context = (
            bool(jd_domains & h._TECHNICAL_DOMAINS)
            and bool(resume_domains & h._TECHNICAL_DOMAINS)
        )
        technical_foundation_skills = {
            "python", "sql", "numpy", "pandas", "statistics",
            "rest api", "docker", "kubernetes", "fastapi", "flask", "postgresql",
        }
        advanced_technical_jd_skills = {
            "machine learning", "scikit-learn", "xgboost", "nlp",
            "deep learning", "feature engineering", "mlops", "data science",
        }
        resume_technical_foundation = bool(resume_skills & technical_foundation_skills)
        jd_advanced_technical       = bool(jd_skills     & advanced_technical_jd_skills)
        _, jd_families, family_relation = h.role_family_relation(resume_text, job_description)
        family_skill_bridge = any(
            bool(resume_skills & h.ROLE_FAMILY_SKILL_HINTS.get(fam, set()))
            for fam in jd_families
        )
        if overlap >= 1 and technical_bridge and related_technical_context:
            raw = 1
        elif (overlap == 0 and related_technical_context
              and resume_technical_foundation and jd_advanced_technical):
            raw = 1 if has_semantic_signal else 0
        elif family_relation == "same" and (overlap >= 1 or family_skill_bridge):
            raw = 1 if has_semantic_signal else 0
        elif family_relation == "adjacent" and (technical_bridge or family_skill_bridge):
            raw = 1 if has_semantic_signal else 0
        else:
            raw = 0

    raw = min(raw, cap)
    return min(raw, 1) if gate == "weak" else raw


def _sbert_skill_similarity(jd_skills: set, resume_skills: set) -> float:
    if not jd_skills or not resume_skills:
        return 0.0
    try:
        h = _host()
        if not getattr(h, "models_loaded", False):
            return 0.0
        from sklearn.metrics.pairwise import cosine_similarity as _cos
        jd_emb  = h.sbert.encode([" ".join(sorted(jd_skills))])[0]
        res_emb = h.sbert.encode([" ".join(sorted(resume_skills))])[0]
        return float(_cos(jd_emb.reshape(1, -1), res_emb.reshape(1, -1))[0][0])
    except Exception:
        return 0.0


# ===========================================================================
# 8. domain_alignment_score  (all fixes applied, graded float)
# ===========================================================================

def domain_alignment_score(
    resume_text: str,
    job_description: str,
    tfidf_sim: float = 0.0,
    sbert_sim: float = 0.0,
) -> float:
    if _is_fake_resume(resume_text):
        return 0.0

    gate = _relevance_gate(tfidf_sim, sbert_sim)
    if gate == "reject":
        return 0.0

    stuffed = _is_stuffed_resume(resume_text)
    cap     = _STUFFED_CAPS["domain"] if stuffed else 1.0

    h              = _host()
    jd_domains     = extract_domains(job_description)
    resume_domains = extract_domains(resume_text)
    _, _, family_relation = h.role_family_relation(resume_text, job_description)
    has_semantic_signal   = tfidf_sim > 0 or sbert_sim > 0

    if not jd_domains:
        raw = 0.75 if family_relation == "same" else 0.0
    elif jd_domains & resume_domains:
        raw = 1.0
    else:
        s_score = skills_match_score(resume_text, job_description, tfidf_sim, sbert_sim)
        if family_relation == "same":
            raw = 0.75 if has_semantic_signal else 0.0
        elif family_relation == "adjacent" and s_score >= 1:
            raw = 0.50 if has_semantic_signal else 0.0
        else:
            raw = 0.0
            for jd_domain in jd_domains:
                valid = h.RELATED_DOMAINS.get(jd_domain, {jd_domain}) - {jd_domain}
                if resume_domains & valid and s_score >= 1:
                    raw = 0.25 if has_semantic_signal else 0.0
                    break

    raw = min(raw, cap)
    return min(raw, 0.5) if gate == "weak" else raw


# ===========================================================================
# 9. education_match_details + education_match_score  (all fixes applied)
# ===========================================================================

def education_match_details(
    resume_text: str,
    job_description: str,
    tfidf_sim: float = 0.0,
    sbert_sim: float = 0.0,
) -> dict:
    h = _host()

    jd_context     = h.extract_education_context(job_description, source="job")
    resume_context = h.extract_education_context(resume_text,     source="resume")

    required_level  = extract_degree_level(jd_context    or job_description)
    candidate_level = extract_degree_level(resume_context or resume_text)
    jd_fields       = extract_fields(jd_context    or job_description)
    resume_fields   = extract_fields(resume_context or resume_text)

    normalised_jd = h.normalize_field_text(jd_context or job_description)
    related_ok    = any(p in normalised_jd for p in h._RELATED_FIELD_ALLOWANCE_PHRASES)

    req_level_num  = h.DEGREE_LEVELS[required_level]
    cand_level_num = h.DEGREE_LEVELS[candidate_level]
    score      = 0
    match_type = "none"

    base_result = dict(
        jd_context=jd_context, resume_context=resume_context,
        required_level=required_level, candidate_level=candidate_level,
        jd_fields=jd_fields, resume_fields=resume_fields,
        match_type=match_type, related_phrase_ok=related_ok, score=score,
    )

    if _is_fake_resume(resume_text) or _is_stuffed_resume(resume_text):
        return base_result

    gate = _relevance_gate(tfidf_sim, sbert_sim)
    if gate == "reject":
        return base_result

    if req_level_num == 0:
        return base_result
    if cand_level_num == 0 or cand_level_num < req_level_num:
        return base_result
    if not jd_fields:
        raw = 1
        base_result["score"] = min(raw, 1) if gate == "weak" else raw
        return base_result

    match_type = h._field_match_type(jd_fields, resume_fields)
    base_result["match_type"] = match_type

    if match_type in {"exact", "aligned"}:
        score = 2
    elif match_type == "related":
        if related_ok or cand_level_num > req_level_num:
            score = 1

    base_result["score"] = min(score, 1) if gate == "weak" else score
    return base_result


def education_match_score(
    resume_text: str,
    job_description: str,
    tfidf_sim: float = 0.0,
    sbert_sim: float = 0.0,
    debug: bool = False,
) -> int:
    return education_match_details(
        resume_text, job_description, tfidf_sim, sbert_sim
    )["score"]