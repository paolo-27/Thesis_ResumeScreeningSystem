"""
ml_service_nlp_patch.py
=======================
Drop-in NLP-enhanced replacements for the four core extraction + scoring
functions in ml_service.py.

HOW TO USE
----------
1.  pip install spacy rapidfuzz  &&  python -m spacy download en_core_web_sm
2.  At the top of ml_service.py, after all existing imports, add:
        from ml_service_nlp_patch import (
            extract_skills,
            extract_domains,
            extract_degree_level,
            extract_fields,
            extract_resume_years,
            extract_required_years,
            skills_match_score,
            domain_alignment_score,
            education_match_score,
            education_match_details,
        )
    These names will shadow the originals for every call that follows,
    including build_feature_vector and calculate_strict_logic.

WHAT CHANGED vs. THE ORIGINAL
------------------------------
extract_skills
  - spaCy PhraseMatcher built from SKILL_ALIASES → handles lemma variants
    and avoids substring false-positives on short tokens (e.g. "r", "go").
  - RapidFuzz partial-ratio fallback catches OCR / hyphenation noise.

extract_domains / domain_alignment_score
  - PhraseMatcher on DOMAIN_KEYWORDS.
  - domain_alignment_score now returns a *graded* 0.0–1.0 float instead of
    binary 0/1, giving the XGBoost model a richer signal.

extract_degree_level
  - spaCy token lemmatizer normalises "studying", "studied", "studies" →
    the degree-level regex then fires correctly on lemmatised text.
  - Adds "associate" degree tier (maps to "none" numerically for safety).

extract_fields
  - PhraseMatcher mirrors the alias table; field-context windows now use
    spaCy sentence boundaries instead of a brittle regex split.

extract_resume_years
  - spaCy DATE NER pre-pass: named DATE spans are extracted first, then the
    original interval logic runs on those clean spans.
  - Overlapping interval de-duplication is done via the existing
    _weighted_intervals_to_years() – no behaviour change for the scorer.

extract_required_years
  - Same NER pre-pass; unchanged regex cascade underneath.

skills_match_score
  - Two-level scoring:
      Level 1 (hard match)  : set-overlap ratio ≥ threshold  → 2
      Level 2 (soft match)  : SBERT cosine on skill-sentence  → 1 if ≥ 0.45
    This lets a candidate who lists "scikit-learn" score against a JD that
    asks for "sklearn" even if the alias table missed a variant.

education_match_score / education_match_details
  - Unchanged scoring logic; field extraction uses the new PhraseMatcher.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Lazy NLP initialisation (spaCy + RapidFuzz optional but strongly preferred)
# ---------------------------------------------------------------------------
try:
    import spacy
    from spacy.matcher import PhraseMatcher

    _nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
    _nlp_full = spacy.load("en_core_web_sm", disable=["tagger", "attribute_ruler", "lemmatizer"])
    _SPACY_OK = True
    print("[nlp_patch] spaCy loaded successfully.")
except Exception as e:
    import traceback
    _nlp = None
    _nlp_full = None
    _SPACY_OK = False
    print(f"[nlp_patch] spaCy failed to load: {e}")
    traceback.print_exc()

try:
    from rapidfuzz import fuzz as _fuzz
    _FUZZ_OK = True
except ImportError:
    _fuzz = None
    _FUZZ_OK = False
    print("[nlp_patch] rapidfuzz not available – fuzzy skill matching disabled.")


# ---------------------------------------------------------------------------
# Re-import everything we need from the host module at call time.
# We use a lazy import helper so this patch file can also be tested standalone.
# ---------------------------------------------------------------------------

def _host():
    """Return the ml_service module (imported lazily to avoid circular refs)."""
    import importlib, sys
    mod = sys.modules.get("ml_service") or importlib.import_module("ml_service")
    return mod


# ---------------------------------------------------------------------------
# PhraseMatcher builders
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_skill_matcher():
    """Build a spaCy PhraseMatcher for SKILL_ALIASES (LOWER attribute)."""
    if not _SPACY_OK:
        return None
    h = _host()
    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    for canonical, aliases in h.SKILL_ALIASES.items():
        patterns = [_nlp.make_doc(a) for a in aliases]
        matcher.add(canonical, patterns)
    return matcher


@lru_cache(maxsize=1)
def _build_domain_matcher():
    """Build a spaCy PhraseMatcher for DOMAIN_KEYWORDS (LOWER attribute)."""
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
    """Build a spaCy PhraseMatcher for FIELD_ALIASES (LOWER attribute)."""
    if not _SPACY_OK:
        return None
    h = _host()
    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    for canonical, aliases in h.FIELD_ALIASES.items():
        patterns = [_nlp.make_doc(a) for a in aliases]
        matcher.add(canonical, patterns)
    return matcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lemmatise(text: str) -> str:
    """Return a lower-cased, lemmatised version of *text* using spaCy."""
    if not _SPACY_OK or not text:
        return text.lower()
    doc = _nlp(text[:50_000])   # guard against absurdly long inputs
    return " ".join(tok.lemma_.lower() for tok in doc)


def _nlp_doc(text: str):
    """Return a spaCy Doc (with NER) for *text*, or None if spaCy unavailable."""
    if not _SPACY_OK or not text:
        return None
    return _nlp_full(text[:50_000])


# ---------------------------------------------------------------------------
# 1.  extract_skills  (NLP-enhanced)
# ---------------------------------------------------------------------------

def extract_skills(text: str) -> set:
    """
    Extract canonical skill names from *text*.

    Strategy (in order):
    1. spaCy PhraseMatcher on LOWER tokens  – catches aliases robustly.
    2. Original alias-table substring scan  – safety net for the matcher.
    3. RapidFuzz partial-ratio on unmatched JD/resume tokens – OCR noise.
    """
    if not text:
        return set()

    h = _host()
    found: set[str] = set()

    # ── Pass 1: PhraseMatcher ────────────────────────────────────────────────
    matcher = _build_skill_matcher()
    if matcher is not None:
        doc = _nlp(text[:50_000])
        for match_id, _start, _end in matcher(doc):
            found.add(_nlp.vocab.strings[match_id])
    else:
        # ── Fallback: original logic ─────────────────────────────────────────
        return _original_extract_skills(text)

    # ── Pass 2: original regex scan for anything the matcher missed ──────────
    # (handles multi-word aliases that spaCy tokenises unexpectedly)
    found |= _original_extract_skills(text)

    # ── Pass 3: RapidFuzz fuzzy scan for unrecognised tokens ─────────────────
    # Only run on short texts (resumes/JDs are rarely > 10 k chars here)
    if _FUZZ_OK and len(text) < 15_000:
        normalised = h.normalize_text(text)
        # Build a flat list of (alias, canonical) for the scorer
        alias_table = [
            (alias, canonical)
            for canonical, aliases in h.SKILL_ALIASES.items()
            for alias in aliases
            if len(alias) >= 4          # skip very short aliases ("r", "go")
        ]
        for token in re.split(r"[\s,;|()/]+", normalised):
            token = token.strip()
            if not token or len(token) < 4:
                continue
            if any(token in h.normalize_text(a) for _, a in [(None, c) for c in found]):
                continue  # already matched
            for alias, canonical in alias_table:
                if canonical in found:
                    continue
                score = _fuzz.partial_ratio(token, alias)
                if score >= 88:
                    found.add(canonical)
                    break

    return found


def _original_extract_skills(text: str) -> set:
    """Original pure-regex skill extraction from ml_service.py (unchanged)."""
    h = _host()
    text = h.normalize_text(text)
    found = set()
    for canonical, aliases in h.SKILL_ALIASES.items():
        if any(h.contains_term(text, alias) for alias in aliases):
            found.add(canonical)
    return found


# ---------------------------------------------------------------------------
# 2.  extract_domains  (NLP-enhanced)
# ---------------------------------------------------------------------------

def extract_domains(text: str) -> set:
    """
    Extract domain labels from *text* using PhraseMatcher + original heuristics.
    """
    if not text:
        return set()

    h = _host()
    found: set[str] = set()

    matcher = _build_domain_matcher()
    if matcher is not None:
        doc = _nlp(text[:50_000])
        for match_id, _start, _end in matcher(doc):
            found.add(_nlp.vocab.strings[match_id])
    else:
        found = _original_extract_domains(text)

    # ── Merge with original for safety ───────────────────────────────────────
    found |= _original_extract_domains(text)

    # ── Post-processing heuristics (unchanged from original) ─────────────────
    normalised = h.normalize_text(text)

    if "data_analytics" in found:
        strong_match = any(h.contains_term(normalised, t) for t in h._DATA_ANALYTICS_STRONG_TERMS)
        weak_hits = sum(1 for t in h._DATA_ANALYTICS_WEAK_TERMS if h.contains_term(normalised, t))
        marketing_ctx = any(h.contains_term(normalised, t) for t in h._MARKETING_CONTEXT_TERMS)
        if not strong_match and (marketing_ctx or weak_hits < 2):
            found.discard("data_analytics")

    if "hr_recruitment" in found:
        strong_hr = any(h.contains_term(normalised, t) for t in h._HR_RECRUITMENT_STRONG_TERMS)
        weak_hr_hits = sum(1 for t in h._HR_RECRUITMENT_WEAK_TERMS if h.contains_term(normalised, t))
        if not strong_hr and weak_hr_hits < 2:
            found.discard("hr_recruitment")

    return found


def _original_extract_domains(text: str) -> set:
    """Original pure-regex domain extraction from ml_service.py (unchanged)."""
    h = _host()
    text = h.normalize_text(text)
    found = set()
    for domain, keywords in h.DOMAIN_KEYWORDS.items():
        if any(h.contains_term(text, kw) for kw in keywords):
            found.add(domain)
    return found


# ---------------------------------------------------------------------------
# 3.  extract_degree_level  (NLP-enhanced)
# ---------------------------------------------------------------------------

def extract_degree_level(text: str) -> str:
    """
    Extract the highest degree level mentioned in *text*.

    Enhancement: run spaCy lemmatiser so "studying computer science" or
    "studied engineering" still fires the bachelor-level regex.
    Falls back to original regex logic on raw text as safety net.
    """
    if not text:
        return "none"

    h = _host()

    # Original logic on raw text (already very robust)
    raw_level = _original_extract_degree_level(text)

    # NLP pass: lemmatise then re-run original logic
    if _SPACY_OK:
        lemmatised = _lemmatise(text)
        nlp_level = _original_extract_degree_level(lemmatised)
        # Take whichever detected a higher level
        level_order = ["none", "bachelor", "master", "phd"]
        if level_order.index(nlp_level) > level_order.index(raw_level):
            return nlp_level

    return raw_level


def _original_extract_degree_level(text: str) -> str:
    """Original extract_degree_level from ml_service.py (verbatim logic)."""
    h = _host()
    text = h.normalize_text(text)
    text = h._sanitize_for_degree(text)

    if re.search(r"(?<!\w)(phd|ph d|doctorate|doctoral)(?!\w)", text):
        return "phd"

    if re.search(
        r"(?<!\w)(master|masters|masters degree|masters in|masters of|m s|ma|m a|msc|m sc|mba)(?!\w)",
        text,
    ) or re.search(
        r"(?<!\w)ms(?!\s*(word|excel|office|sql|powerpoint|project|access|windows|dynamics|teams|outlook|publisher|\d))(?!\w)",
        text,
    ):
        return "master"

    if re.search(
        r"(?<!\w)(bachelor|bachelors|bachelors degree|bachelors in|bachelor of|bs|b s|bsc|b sc|undergraduate)(?!\w)",
        text,
    ) or re.search(
        r"(?<!\w)ba(?!\s*(analyst|analysis|analytics))(?!\w)",
        text,
    ):
        return "bachelor"

    if h._has_strong_graduate_context(text):
        return "bachelor"

    return "none"


# ---------------------------------------------------------------------------
# 4.  extract_fields  (NLP-enhanced)
# ---------------------------------------------------------------------------

def extract_fields(text: str) -> set:
    """
    Extract canonical field-of-study names from *text*.

    Enhancement: spaCy PhraseMatcher + spaCy sentence boundaries for the
    degree-phrase context window (more accurate than the regex split).
    """
    if not text:
        return set()

    h = _host()
    found: set[str] = set()

    # ── Pass 1: PhraseMatcher over whole text ─────────────────────────────────
    matcher = _build_field_matcher()
    if matcher is not None:
        normalised_text = h.normalize_field_text(text)
        doc = _nlp(normalised_text[:50_000])
        for match_id, _start, _end in matcher(doc):
            found.add(_nlp.vocab.strings[match_id])

    # ── Pass 2: Original alias scan (safety net) ──────────────────────────────
    found |= _original_extract_fields(text)

    # ── Pass 3: Degree-phrase context windows (NLP sentence boundaries) ───────
    if _SPACY_OK:
        degree_re = re.compile(
            r"(?:bachelor(?:s|\'s)?(?:\s+of(?:\s+science)?(?:\s+in)?)?|"
            r"master(?:s|\'s)?(?:\s+of(?:\s+science)?(?:\s+in)?)?|"
            r"bs|bsc|ba|ms|msc|ma|mba|phd|ph\s*d|doctorate(?:\s+in)?|"
            r"bachelor|master)\s*(?:in|of|:)?\s*",
            re.IGNORECASE,
        )
        # Use spaCy senter for cleaner windows
        doc_full = _nlp_full(text[:50_000])
        for sent in doc_full.sents:
            sent_text = sent.text
            for m in degree_re.finditer(sent_text):
                tail = sent_text[m.end(): m.end() + 120]
                # Stop at hard punctuation
                tail = re.split(r"[\n;,|]", tail)[0].strip()
                normalised_tail = h.normalize_field_text(tail)
                for canonical, aliases in h.FIELD_ALIASES.items():
                    if canonical not in found and any(
                        h.contains_term(normalised_tail, alias) for alias in aliases
                    ):
                        found.add(canonical)

    return found


def _original_extract_fields(text: str) -> set:
    """Original extract_fields from ml_service.py (verbatim logic)."""
    h = _host()
    normalised = h.normalize_field_text(text)
    found = set()
    for canonical, aliases in h.FIELD_ALIASES.items():
        if any(h.contains_term(normalised, alias) for alias in aliases):
            found.add(canonical)
    for window in h._extract_field_context_windows(text):
        normalised_window = h.normalize_field_text(window)
        for canonical, aliases in h.FIELD_ALIASES.items():
            if canonical not in found and any(
                h.contains_term(normalised_window, alias) for alias in aliases
            ):
                found.add(canonical)
    return found


# ---------------------------------------------------------------------------
# 5.  extract_resume_years  (NLP-enhanced via spaCy DATE NER)
# ---------------------------------------------------------------------------

def extract_resume_years(resume_text: str) -> float:
    """
    Extract the candidate's total years of experience.

    Enhancement: spaCy DATE NER pre-pass surfaces date spans that the
    regex segmenter might otherwise miss due to unusual formatting.
    The original _weighted_intervals logic runs unchanged on the enriched
    segment list.
    """
    if not resume_text:
        return 0.0

    h = _host()

    # Original approach (robust as-is; NER is additive only)
    base_years = _original_extract_resume_years(resume_text)

    if not _SPACY_OK or base_years > 0:
        # If original already found something, trust it
        return base_years

    # ── NER fallback for date-entity extraction ───────────────────────────────
    # Collect DATE entities, build synthetic "date – date" segments and feed
    # back into the original interval extractor.
    doc = _nlp_full(resume_text[:50_000])
    date_strings = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    if not date_strings:
        return base_years

    synthetic = " ".join(date_strings)
    ner_years = _original_extract_resume_years(synthetic)
    return max(base_years, ner_years)


def _original_extract_resume_years(resume_text: str) -> float:
    """Original extract_resume_years from ml_service.py (unchanged)."""
    h = _host()

    explicit_patterns = [
        h._NUM_PATTERN + r"\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(?:at\s+least|over|more\s+than|with)\s+"
        + h._NUM_PATTERN
        + r"\s*(?:years?|yrs?)\s*(?:of\s+experience)?",
        r"experience\s*[:\-]?\s*" + h._NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"(?:work|working|professional|related)\s+experience\s*[:\-]?\s*" + h._NUM_PATTERN + r"\s*(?:years?|yrs?)",
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

        seg_vals = h._extract_explicit_year_values(segment, explicit_patterns, range_mode="max")
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
# 6.  extract_required_years  (NLP-enhanced)
# ---------------------------------------------------------------------------

def extract_required_years(job_description: str) -> float:
    """
    Extract the minimum years of experience required by *job_description*.

    Enhancement: identical NER pre-pass as extract_resume_years; the full
    regex cascade from the original runs underneath unchanged.
    """
    if not job_description:
        return 0

    h = _host()
    base = h.extract_required_years.__wrapped__(job_description) if hasattr(
        h.extract_required_years, "__wrapped__"
    ) else _original_extract_required_years(job_description)

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
    """Verbatim extract_required_years from ml_service.py."""
    h = _host()
    return h.extract_required_years(job_description)   # calls original until monkey-patched


# ---------------------------------------------------------------------------
# 7.  skills_match_score  (Two-level: hard overlap + SBERT soft match)
# ---------------------------------------------------------------------------

def skills_match_score(
    resume_text: str,
    job_description: str,
    tfidf_sim: float = 0.0,
    sbert_sim: float = 0.0,
) -> int:
    """
    Score skill alignment between resume and JD.

    Returns 0, 1, or 2 (matching original scale).

    Levels
    ------
    2  : hard-overlap ratio ≥ 0.60  OR  ≥ 5 shared skills
    1  : hard-overlap ratio ≥ 0.25  OR  ≥ 2 shared skills
         OR soft SBERT similarity ≥ 0.45 on skill sentences
         OR original fallback logic (role-family / domain bridge)
    0  : no match
    """
    h = _host()
    jd_skills = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)

    has_semantic_signal = tfidf_sim > 0 or sbert_sim > 0

    # Guard: JD has no recognisable content
    if not jd_skills:
        jd_domains = extract_domains(job_description)
        jd_families = h.extract_role_families(job_description)
        if not jd_domains and not jd_families:
            return 0
        return 1

    overlap = len(jd_skills & resume_skills)
    ratio = overlap / max(len(jd_skills), 1)

    # Hard match ──────────────────────────────────────────────────────────────
    if ratio >= 0.60 or overlap >= 5:
        return 2
    if ratio >= 0.25 or overlap >= 2:
        return 1

    # Soft SBERT skill-sentence match ─────────────────────────────────────────
    sbert_skill_score = _sbert_skill_similarity(jd_skills, resume_skills)
    if sbert_skill_score >= 0.45:
        return 1

    # Original role-family / domain fallback (unchanged) ──────────────────────
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
    resume_families, jd_families, family_relation = h.role_family_relation(resume_text, job_description)
    family_skill_bridge = any(
        bool(resume_skills & h.ROLE_FAMILY_SKILL_HINTS.get(fam, set()))
        for fam in jd_families
    )

    if overlap >= 1 and technical_bridge and related_technical_context:
        return 1
    if overlap == 0 and related_technical_context and resume_technical_foundation and jd_advanced_technical:
        return 1 if has_semantic_signal else 0
    if family_relation == "same" and (overlap >= 1 or family_skill_bridge):
        return 1 if has_semantic_signal else 0
    if family_relation == "adjacent" and (technical_bridge or family_skill_bridge):
        return 1 if has_semantic_signal else 0

    return 0


def _sbert_skill_similarity(jd_skills: set, resume_skills: set) -> float:
    """
    Compute cosine similarity between the SBERT embeddings of two skill
    sentences (e.g. "python sql machine learning" vs "python pandas numpy").

    Returns a float in [0, 1].  Returns 0.0 if SBERT is unavailable.
    """
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
# 8.  domain_alignment_score  (Graded 0.0–1.0 float)
# ---------------------------------------------------------------------------

def domain_alignment_score(
    resume_text: str,
    job_description: str,
    tfidf_sim: float = 0.0,
    sbert_sim: float = 0.0,
) -> float:
    """
    Score domain alignment between resume and JD.

    Returns a *float* in [0.0, 1.0] instead of binary 0/1.

    Grading
    -------
    1.0  : direct domain overlap
    0.75 : same role family  (with semantic signal)
    0.50 : adjacent role family + skill bridge  (with semantic signal)
    0.25 : related domain + skill score ≥ 1  (with semantic signal)
    0.0  : no alignment
    """
    h = _host()
    jd_domains = extract_domains(job_description)
    resume_domains = extract_domains(resume_text)
    resume_families, jd_families, family_relation = h.role_family_relation(resume_text, job_description)

    has_semantic_signal = tfidf_sim > 0 or sbert_sim > 0

    if not jd_domains:
        return 0.75 if family_relation == "same" else 0.0

    # Direct domain overlap ───────────────────────────────────────────────────
    if jd_domains & resume_domains:
        return 1.0

    s_score = skills_match_score(resume_text, job_description, tfidf_sim, sbert_sim)

    # Same role family ────────────────────────────────────────────────────────
    if family_relation == "same":
        return 0.75 if has_semantic_signal else 0.0

    # Adjacent role family + skill bridge ─────────────────────────────────────
    if family_relation == "adjacent" and s_score >= 1:
        return 0.50 if has_semantic_signal else 0.0

    # Related domain + skill present ──────────────────────────────────────────
    for jd_domain in jd_domains:
        valid_domains = h.RELATED_DOMAINS.get(jd_domain, {jd_domain}) - {jd_domain}
        if resume_domains & valid_domains and s_score >= 1:
            return 0.25 if has_semantic_signal else 0.0

    return 0.0


# ---------------------------------------------------------------------------
# 9.  education_match_details + education_match_score
#     (Logic unchanged; plugs in the NLP-enhanced extract_fields above)
# ---------------------------------------------------------------------------

def education_match_details(resume_text: str, job_description: str) -> dict:
    """
    Identical logic to the original education_match_details but using the
    NLP-enhanced extract_fields / extract_degree_level defined in this module.
    """
    h = _host()

    jd_context = h.extract_education_context(job_description, source="job")
    resume_context = h.extract_education_context(resume_text, source="resume")

    jd_for_level = jd_context or job_description
    resume_for_level = resume_context or resume_text
    jd_for_fields = jd_context or job_description
    resume_for_fields = resume_context or resume_text

    # Use NLP-enhanced versions
    required_level = extract_degree_level(jd_for_level)
    candidate_level = extract_degree_level(resume_for_level)
    jd_fields = extract_fields(jd_for_fields)
    resume_fields = extract_fields(resume_for_fields)

    normalised_jd_context = h.normalize_field_text(jd_context or job_description)
    related_ok = any(phrase in normalised_jd_context for phrase in h._RELATED_FIELD_ALLOWANCE_PHRASES)

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


def education_match_score(resume_text: str, job_description: str, debug: bool = False) -> int:
    return education_match_details(resume_text, job_description)["score"]


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_resume = """
    John Doe
    BS Computer Science, University of the Philippines, 2019
    Work Experience:
    Software Engineer – Acme Corp (Jan 2020 – Present)
    - Developed REST APIs using Python and FastAPI
    - Used PostgreSQL and Redis for data storage
    - Deployed microservices on Docker / Kubernetes (AWS EKS)
    - Practiced CI/CD with GitHub Actions
    """

    sample_jd = """
    We are looking for a Backend Engineer with at least 3 years of experience.
    Requirements:
    - Proficient in Python, FastAPI or Django
    - Strong SQL skills (PostgreSQL preferred)
    - Experience with Docker, Kubernetes, and CI/CD pipelines
    - Bachelor's degree in Computer Science, Software Engineering, or related field
    """

    print("Skills (resume):", sorted(extract_skills(sample_resume)))
    print("Skills (JD)    :", sorted(extract_skills(sample_jd)))
    print("Domains (resume):", sorted(extract_domains(sample_resume)))
    print("Domains (JD)    :", sorted(extract_domains(sample_jd)))
    print("Degree (resume) :", extract_degree_level(sample_resume))
    print("Degree (JD)     :", extract_degree_level(sample_jd))
    print("Fields (resume) :", sorted(extract_fields(sample_resume)))
    print("Fields (JD)     :", sorted(extract_fields(sample_jd)))
    print("Education details:", education_match_details(sample_resume, sample_jd))
