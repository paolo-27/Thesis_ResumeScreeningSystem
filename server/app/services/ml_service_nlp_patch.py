"""
ml_service_nlp_patch.py
=======================
Drop-in NLP-enhanced replacements for the core extraction + scoring
functions in ml_service.py.

BUGS FIXED IN THIS VERSION
---------------------------
Bug 1 – Skill false positives (JD getting azure, fastapi, laravel, gcp, etc.)
  contains_term() matched substrings inside longer words.
  "excellent" triggered "excel", etc.
  Fix: strict word-boundary matching + minimum alias length of 4 chars.
  Skills in _STRONG_EVIDENCE_REQUIRED now require a technical context
  keyword in the same sentence before being accepted.

Bug 2 – "Education" section header extracted as a field of study.
  Fix: hard blocklist of section-header words that are never fields.

Bug 3 – Resume degree "none" despite "Bachelor of Science in Marketing".
  PDF extraction splits degree keywords across lines.
  Fix: _join_split_lines() merges lines that end with a preposition
  before any extraction runs.

Bug 4 – _original_extract_required_years recursion.
  Old version called h.extract_required_years() which is now patched.
  Fix: inline implementation that never calls back into the host module.
"""

from __future__ import annotations

import re
from functools import lru_cache

# ---------------------------------------------------------------------------
# Lazy NLP initialisation
# ---------------------------------------------------------------------------
try:
    import spacy
    from spacy.matcher import PhraseMatcher

    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    _nlp_full = spacy.load("en_core_web_sm", disable=["tagger", "attribute_ruler", "lemmatizer"])
    _SPACY_OK = True
    print("[nlp_patch] spaCy loaded successfully.")
except Exception as _spacy_err:
    import traceback as _tb
    _nlp = None
    _nlp_full = None
    _SPACY_OK = False
    print(f"[nlp_patch] spaCy failed to load: {_spacy_err}")
    _tb.print_exc()

try:
    from rapidfuzz import fuzz as _fuzz
    _FUZZ_OK = True
except ImportError:
    _fuzz = None
    _FUZZ_OK = False
    print("[nlp_patch] rapidfuzz not available – fuzzy skill matching disabled.")


# ---------------------------------------------------------------------------
# Lazy host module reference
# ---------------------------------------------------------------------------
def _host():
    import importlib, sys
    return sys.modules.get("ml_service") or importlib.import_module("ml_service")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Words that appear as section headers and must NEVER be treated as fields
_FIELD_HEADER_BLOCKLIST = {
    "education", "experience", "skills", "references", "contact",
    "language", "languages", "summary", "objective", "profile",
    "work", "employment", "certifications", "achievements", "awards",
    "interests", "hobbies", "projects", "volunteer", "activities",
    "overview", "requirements", "responsibilities", "qualifications",
    "key", "about", "introduction", "highlights", "competencies",
}

# Skills that are commonly false-positive matched from generic office text.
# These require at least one explicit technical context keyword nearby.
_STRONG_EVIDENCE_REQUIRED = {
    "excel",             # "excellent" → false hit
    "word",              # "microsoft word" vs any sentence with "word"
    "access",            # "access to" vs "microsoft access"
    "integrity",         # common adjective
    "communication",     # common noun
    "leadership",        # common noun
    "cash handling",     # only valid in retail/finance JDs
    "accounting",        # needs financial context
    "laravel",           # PHP framework — needs dev context
    "azure",             # cloud — needs tech context
    "gcp",               # cloud — needs tech context
    "cybersecurity",     # needs security context
    "fastapi",           # needs Python/API context
    "feature engineering",  # needs ML context
}

# Technical context keywords that validate strong-evidence skills
_TECH_CONTEXT_KEYWORDS = {
    "microsoft", "office suite", "spreadsheet", "database", "server",
    "cloud", "platform", "framework", "php", "python", "api", "devops",
    "software", "application", "system", "network", "security", "finance",
    "bookkeeping", "payroll", "invoice", "retail", "machine learning",
    "data", "pipeline", "engineering", "backend", "frontend", "developer",
    "programming", "web", "infrastructure", "deployment", "repository",
}


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _join_split_lines(text: str) -> str:
    """
    Join lines that were split mid-phrase by a PDF extractor.
    e.g. "Bachelor of Science in\nMarketing" becomes one line.
    """
    lines = text.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append("")
            continue
        # If the previous line ends with a preposition/conjunction, merge
        if result and re.search(
            r"\b(in|of|and|or|the|a|an|for|with|at|by)\s*$",
            result[-1],
            re.IGNORECASE,
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


def _has_tech_context(text: str) -> bool:
    """Return True if text contains at least one technical context keyword."""
    lower = text.lower()
    return any(kw in lower for kw in _TECH_CONTEXT_KEYWORDS)


def _strict_word_match(text: str, term: str) -> bool:
    """
    True if *term* appears in *text* as a whole word/phrase,
    not as a substring of a longer word.
    """
    pattern = r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])"
    return bool(re.search(pattern, text.lower()))


# ---------------------------------------------------------------------------
# PhraseMatcher builders
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_skill_matcher():
    if not _SPACY_OK:
        return None
    h = _host()
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
    h = _host()
    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    for domain, keywords in h.DOMAIN_KEYWORDS.items():
        patterns = [_nlp.make_doc(kw) for kw in keywords]
        matcher.add(domain, patterns)
    return matcher


@lru_cache(maxsize=1)
def _build_field_matcher():
    if not _SPACY_OK:
        return None
    h = _host()
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


# ---------------------------------------------------------------------------
# 1. extract_skills  (fixed)
# ---------------------------------------------------------------------------

def extract_skills(text: str) -> set:
    """
    Extract canonical skill names from *text* with false-positive guards.

    Guards applied:
    - Strict word-boundary matching (no substring hits inside longer words).
    - Aliases shorter than 4 chars are skipped.
    - Skills in _STRONG_EVIDENCE_REQUIRED require a technical context keyword
      in the same sentence before being accepted.
    """
    if not text:
        return set()

    h = _host()
    text = _join_split_lines(text)
    normalised = h.normalize_text(text)
    found: set[str] = set()

    # Split into sentences for per-skill context checking
    sentences = re.split(r"[.!?\n]", normalised)

    for canonical, aliases in h.SKILL_ALIASES.items():
        matched = False
        for alias in aliases:
            if len(alias) < 4:
                continue

            if not _strict_word_match(normalised, alias):
                continue

            # Strong-evidence skills need tech context in the same sentence
            if canonical in _STRONG_EVIDENCE_REQUIRED:
                containing = [s for s in sentences if _strict_word_match(s, alias)]
                if not containing or not any(_has_tech_context(s) for s in containing):
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
            if len(alias) >= 5 and canonical not in found
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
                            _has_tech_context(s) for s in containing
                        ):
                            continue
                    found.add(canonical)
                    break

    return found


# ---------------------------------------------------------------------------
# 2. extract_domains
# ---------------------------------------------------------------------------

def extract_domains(text: str) -> set:
    if not text:
        return set()

    h = _host()
    text = _join_split_lines(text)
    found: set[str] = set()

    matcher = _build_domain_matcher()
    if matcher is not None:
        doc = _nlp(text[:50_000])
        for match_id, _start, _end in matcher(doc):
            found.add(_nlp.vocab.strings[match_id])

    # Original regex scan as safety net
    normalised = h.normalize_text(text)
    for domain, keywords in h.DOMAIN_KEYWORDS.items():
        if any(h.contains_term(normalised, kw) for kw in keywords):
            found.add(domain)

    # Post-processing heuristics
    if "data_analytics" in found:
        strong_match = any(
            h.contains_term(normalised, t) for t in h._DATA_ANALYTICS_STRONG_TERMS
        )
        weak_hits = sum(
            1 for t in h._DATA_ANALYTICS_WEAK_TERMS
            if h.contains_term(normalised, t)
        )
        marketing_ctx = any(
            h.contains_term(normalised, t) for t in h._MARKETING_CONTEXT_TERMS
        )
        if not strong_match and (marketing_ctx or weak_hits < 2):
            found.discard("data_analytics")

    if "hr_recruitment" in found:
        strong_hr = any(
            h.contains_term(normalised, t) for t in h._HR_RECRUITMENT_STRONG_TERMS
        )
        weak_hr_hits = sum(
            1 for t in h._HR_RECRUITMENT_WEAK_TERMS
            if h.contains_term(normalised, t)
        )
        if not strong_hr and weak_hr_hits < 2:
            found.discard("hr_recruitment")

    return found


# ---------------------------------------------------------------------------
# 3. extract_degree_level  (fixed: multiline PDF handling)
# ---------------------------------------------------------------------------

def extract_degree_level(text: str) -> str:
    if not text:
        return "none"

    # Fix multiline splits before scanning
    text = _join_split_lines(text)
    raw_level = _original_extract_degree_level(text)

    if _SPACY_OK:
        lemmatised = _lemmatise(text)
        nlp_level = _original_extract_degree_level(lemmatised)
        level_order = ["none", "bachelor", "master", "phd"]
        if level_order.index(nlp_level) > level_order.index(raw_level):
            return nlp_level

    return raw_level


def _original_extract_degree_level(text: str) -> str:
    h = _host()
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


# ---------------------------------------------------------------------------
# 4. extract_fields  (fixed: section header blocklist)
# ---------------------------------------------------------------------------

def extract_fields(text: str) -> set:
    if not text:
        return set()

    h = _host()
    text = _join_split_lines(text)
    found: set[str] = set()

    # PhraseMatcher pass (blocklist applied at matcher build time)
    matcher = _build_field_matcher()
    if matcher is not None:
        normalised_text = h.normalize_field_text(text)
        doc = _nlp(normalised_text[:50_000])
        for match_id, _start, _end in matcher(doc):
            canonical = _nlp.vocab.strings[match_id]
            if canonical.lower() not in _FIELD_HEADER_BLOCKLIST:
                found.add(canonical)

    # Original alias scan with blocklist guard
    normalised = h.normalize_field_text(text)
    for canonical, aliases in h.FIELD_ALIASES.items():
        if canonical.lower() in _FIELD_HEADER_BLOCKLIST:
            continue
        if any(
            h.contains_term(normalised, alias)
            for alias in aliases
            if alias.lower() not in _FIELD_HEADER_BLOCKLIST
        ):
            found.add(canonical)

    # Degree-phrase context windows — only extract field AFTER a degree keyword
    degree_re = re.compile(
        r"(?:bachelor(?:s|\'s)?(?:\s+of(?:\s+science)?(?:\s+in)?)?|"
        r"master(?:s|\'s)?(?:\s+of(?:\s+science)?(?:\s+in)?)?|"
        r"bs|bsc|ba|ms|msc|ma|mba|phd|ph\s*d|doctorate(?:\s+in)?|"
        r"bachelor|master)\s*(?:in|of|:)?\s*",
        re.IGNORECASE,
    )
    for segment in re.split(r"[\n\r]{1,2}", text):
        for m in degree_re.finditer(segment):
            tail = segment[m.end(): m.end() + 120]
            tail = re.split(r"[,|;]", tail)[0].strip()
            if not tail or tail.lower() in _FIELD_HEADER_BLOCKLIST:
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

    # Final guard: strip anything that's purely a section header word
    return {f for f in found if f.lower() not in _FIELD_HEADER_BLOCKLIST}


# ---------------------------------------------------------------------------
# 5. extract_resume_years
# ---------------------------------------------------------------------------

def extract_resume_years(resume_text: str) -> float:
    if not resume_text:
        return 0.0

    resume_text = _join_split_lines(resume_text)
    base_years = _original_extract_resume_years(resume_text)

    if not _SPACY_OK or base_years > 0:
        return base_years

    # NER fallback
    doc = _nlp_full(resume_text[:50_000])
    date_strings = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    if not date_strings:
        return base_years

    synthetic = " ".join(date_strings)
    return max(base_years, _original_extract_resume_years(synthetic))


def _original_extract_resume_years(resume_text: str) -> float:
    h = _host()

    explicit_patterns = [
        h._NUM_PATTERN + r"\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(?:at\s+least|over|more\s+than|with)\s+"
        + h._NUM_PATTERN
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

    explicit_values = []
    weighted_intervals = []
    segments = h.experience_segments(resume_text)

    for index, segment in enumerate(segments):
        context = h._segment_context_window(segments, index)
        weight = h._experience_segment_weight(segment, context=context)
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
    explicit_years = max(explicit_values) if explicit_values else 0

    if explicit_years or interval_years:
        return max(explicit_years, interval_years)

    return h._estimate_implicit_resume_years(resume_text)


# ---------------------------------------------------------------------------
# 6. extract_required_years  (recursion fixed)
# ---------------------------------------------------------------------------

def extract_required_years(job_description: str) -> float:
    if not job_description:
        return 0.0

    job_description = _join_split_lines(job_description)
    base = _original_extract_required_years(job_description)

    if base > 0 or not _SPACY_OK:
        return base

    # NER fallback
    doc = _nlp_full(job_description[:50_000])
    date_strings = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    if not date_strings:
        return base

    synthetic = " ".join(date_strings)
    return _original_extract_required_years(synthetic) or base


def _original_extract_required_years(job_description: str) -> float:
    """
    Inline implementation — does NOT call h.extract_required_years()
    to avoid infinite recursion since that name is now patched.
    """
    h = _host()

    explicit_patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(?:at\s+least|over|more\s+than|minimum(?:\s+of)?|with)\s+"
        r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:relevant\s+)?"
        r"(?:work\s+)?experience",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:in\s+)?(?:the\s+)?"
        r"(?:industry|field|role|position)",
        r"(\d+(?:\.\d+)?)\s*[-\u2013]\s*\d+\s*(?:years?|yrs?)\s+"
        r"(?:of\s+)?experience",
        r"(\d+)\+\s*(?:years?|yrs?)",
    ]

    values = h._extract_explicit_year_values(
        job_description, explicit_patterns, range_mode="min"
    )
    return float(min(values)) if values else 0.0


# ---------------------------------------------------------------------------
# 7. skills_match_score
# ---------------------------------------------------------------------------

def skills_match_score(
    resume_text: str,
    job_description: str,
    tfidf_sim: float = 0.0,
    sbert_sim: float = 0.0,
) -> int:
    h = _host()
    jd_skills = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)
    has_semantic_signal = tfidf_sim > 0 or sbert_sim > 0

    if not jd_skills:
        jd_domains = extract_domains(job_description)
        jd_families = h.extract_role_families(job_description)
        if not jd_domains and not jd_families:
            return 0
        return 1

    overlap = len(jd_skills & resume_skills)
    ratio = overlap / max(len(jd_skills), 1)

    if ratio >= 0.60 or overlap >= 5:
        return 2
    if ratio >= 0.25 or overlap >= 2:
        return 1

    sbert_skill_score = _sbert_skill_similarity(jd_skills, resume_skills)
    if sbert_skill_score >= 0.45:
        return 1

    # Role-family / domain fallback
    shared_skills = jd_skills & resume_skills
    jd_domains = extract_domains(job_description)
    resume_domains = extract_domains(resume_text)
    technical_bridge = bool(shared_skills & h._TECHNICAL_BRIDGE_SKILLS)
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
    jd_advanced_technical = bool(jd_skills & advanced_technical_jd_skills)
    resume_families, jd_families, family_relation = h.role_family_relation(
        resume_text, job_description
    )
    family_skill_bridge = any(
        bool(resume_skills & h.ROLE_FAMILY_SKILL_HINTS.get(fam, set()))
        for fam in jd_families
    )

    if overlap >= 1 and technical_bridge and related_technical_context:
        return 1
    if (overlap == 0 and related_technical_context
            and resume_technical_foundation and jd_advanced_technical):
        return 1 if has_semantic_signal else 0
    if family_relation == "same" and (overlap >= 1 or family_skill_bridge):
        return 1 if has_semantic_signal else 0
    if family_relation == "adjacent" and (technical_bridge or family_skill_bridge):
        return 1 if has_semantic_signal else 0

    return 0


def _sbert_skill_similarity(jd_skills: set, resume_skills: set) -> float:
    if not jd_skills or not resume_skills:
        return 0.0
    try:
        h = _host()
        if not getattr(h, "models_loaded", False):
            return 0.0
        jd_sentence = " ".join(sorted(jd_skills))
        res_sentence = " ".join(sorted(resume_skills))
        jd_emb = h.sbert.encode([jd_sentence])[0]
        res_emb = h.sbert.encode([res_sentence])[0]
        from sklearn.metrics.pairwise import cosine_similarity as _cos
        return float(_cos(jd_emb.reshape(1, -1), res_emb.reshape(1, -1))[0][0])
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# 8. domain_alignment_score  (graded float)
# ---------------------------------------------------------------------------

def domain_alignment_score(
    resume_text: str,
    job_description: str,
    tfidf_sim: float = 0.0,
    sbert_sim: float = 0.0,
) -> float:
    h = _host()
    jd_domains = extract_domains(job_description)
    resume_domains = extract_domains(resume_text)
    resume_families, jd_families, family_relation = h.role_family_relation(
        resume_text, job_description
    )
    has_semantic_signal = tfidf_sim > 0 or sbert_sim > 0

    if not jd_domains:
        return 0.75 if family_relation == "same" else 0.0
    if jd_domains & resume_domains:
        return 1.0

    s_score = skills_match_score(resume_text, job_description, tfidf_sim, sbert_sim)

    if family_relation == "same":
        return 0.75 if has_semantic_signal else 0.0
    if family_relation == "adjacent" and s_score >= 1:
        return 0.50 if has_semantic_signal else 0.0
    for jd_domain in jd_domains:
        valid_domains = h.RELATED_DOMAINS.get(jd_domain, {jd_domain}) - {jd_domain}
        if resume_domains & valid_domains and s_score >= 1:
            return 0.25 if has_semantic_signal else 0.0

    return 0.0


# ---------------------------------------------------------------------------
# 9. education_match_details + education_match_score
# ---------------------------------------------------------------------------

def education_match_details(resume_text: str, job_description: str) -> dict:
    h = _host()

    jd_context = h.extract_education_context(job_description, source="job")
    resume_context = h.extract_education_context(resume_text, source="resume")

    jd_for_level = jd_context or job_description
    resume_for_level = resume_context or resume_text
    jd_for_fields = jd_context or job_description
    resume_for_fields = resume_context or resume_text

    required_level = extract_degree_level(jd_for_level)
    candidate_level = extract_degree_level(resume_for_level)
    jd_fields = extract_fields(jd_for_fields)
    resume_fields = extract_fields(resume_for_fields)

    normalised_jd_context = h.normalize_field_text(jd_context or job_description)
    related_ok = any(
        phrase in normalised_jd_context
        for phrase in h._RELATED_FIELD_ALLOWANCE_PHRASES
    )

    req_level_num = h.DEGREE_LEVELS[required_level]
    cand_level_num = h.DEGREE_LEVELS[candidate_level]

    score = 0
    match_type = "none"

    base_result = dict(
        jd_context=jd_context,
        resume_context=resume_context,
        required_level=required_level,
        candidate_level=candidate_level,
        jd_fields=jd_fields,
        resume_fields=resume_fields,
        match_type=match_type,
        related_phrase_ok=related_ok,
        score=score,
    )

    if req_level_num == 0:
        return base_result
    if cand_level_num == 0 or cand_level_num < req_level_num:
        return base_result
    if not jd_fields:
        base_result["score"] = 1
        return base_result

    match_type = h._field_match_type(jd_fields, resume_fields)
    base_result["match_type"] = match_type

    if match_type in {"exact", "aligned"}:
        score = 2
    elif match_type == "related":
        if related_ok or cand_level_num > req_level_num:
            score = 1

    base_result["score"] = score
    return base_result


def education_match_score(
    resume_text: str, job_description: str, debug: bool = False
) -> int:
    return education_match_details(resume_text, job_description)["score"]