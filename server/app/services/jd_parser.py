import re
from typing import Dict, Any, List, Tuple


class JobDescriptionParser:
    def parse(self, text: str) -> Dict[str, Any]:
        if not text:
            return {
                "salary": None,
                "cleanedDescription": "",
                "parsedRequirements": []
            }

        text = self._normalize_text(text)
        salary = self._extract_salary(text)
        cleaned_description, parsed_requirements = self._state_machine_parse(text)

        return {
            "salary": salary,
            "cleanedDescription": cleaned_description,
            "parsedRequirements": parsed_requirements
        }

    # ── Known section header keywords used for forced line-breaking ──────────
    # Order matters: longer / more specific phrases first.
    _SECTION_BREAK_PHRASES = [
        # Duties / responsibilities
        "What You'll Do",
        "What You Will Do",
        "What the Role Entails",
        "Key Responsibilities",
        "Core Responsibilities",
        "Job Description",
        "Responsibilities",
        "Accountabilities",
        "Role Definition",
        "Your Role",
        # Requirements / qualifications
        "What We Ask of You",
        "What You Will Need",
        "Who We're Looking For",
        "We're Looking For",
        "We are Looking For",
        "Qualifications",
        "Requirements",
        "Required Skills",
        "Key Skills",
        "Who You Are",
        "Must Have",
        # Preferred
        "Nice to Have",
        "Bonus Points",
        "Preferred Skills",
        "Preferred Qualifications",
        "It is a Plus",
        # Ignore / boilerplate
        "Equal Opportunity Employer",
        "Equal Employment Opportunity",
        "Make Your Passion",
        "About Us",
        "What We Offer",
        "Benefits",
        "Why Join",
        "What's on Offer",
        "What's in it for You",
        "Globe's Diversity",
        "Globe's Hiring",
    ]

    def _normalize_text(self, text: str) -> str:
        # 0. Normalise curly/smart apostrophes to straight ones so the
        #    phrase list (straight apostrophes) matches consistently.
        text = text.replace('\u2019', "'").replace('\u2018', "'")

        # 1. Force known section headers onto their own lines FIRST.
        for phrase in self._SECTION_BREAK_PHRASES:
            escaped = re.escape(phrase)
            text = re.sub(rf'(?i)(?<!\n)({escaped})', r'\n\1\n', text)

        # 2. Split numbered list items (e.g. "1. STORE CREW") onto their own lines.
        text = re.sub(r'(?<!\d)(?<!\n)([1-9]\d?\.\s+[A-Z])', r'\n\1', text)

        # 3. Split on bullet characters so each becomes its own line.
        text = re.sub(
            r'\s*[\u2022\u2023\u25E6\u2043\u2219\xb7]\s*',
            '\n\u2022 ',
            text
        )

        # 4. Heal genuine broken hard-wraps AFTER steps 1-3.
        text = re.sub(r'([a-zA-Z,])\n\s*([a-z])', r'\1 \2', text)

        # 4. Force remaining curly-quote embedded-header variants onto new lines.
        embedded_headers = [
            r'what the role entails',
            r'what we ask of you',
            r'it is a plus if you have',
            r"what[\u2019']?s in it for you\??",
            r"what[\u2019']?s on offer",
            r'the successful applicant',
        ]
        for header in embedded_headers:
            text = re.sub(rf'(?i)({header})', r'\n\1\n', text)

        return text

    def _extract_salary(self, text: str) -> str:
        patterns = [
            r'(?i)(?:salary|compensation|pay|rate)\s*:?\s*(?:range(?:s)?\s*(?:is|are)?\s*)?(?:PHP|P|\u20b1|Php)?\s*(\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?\s*(?:-|to|\u2013|\u2014)\s*(?:PHP|P|\u20b1|Php)?\s*\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?)',
            r'(?i)(?:PHP|P|\u20b1|Php)\s*(\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?(?:\s*(?:-|to|\u2013|\u2014)\s*(?:PHP|P|\u20b1|Php)?\s*\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?)?)',
            r'(?i)(?:salary|compensation|pay|rate)\s*:?\s*(?:range\s*is\s*)?(?:PHP|P|\u20b1|Php)?\s*(\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                val = match.group(1).strip()
                if (not val.upper().startswith('PHP')
                        and not val.upper().startswith('P')
                        and not val.startswith('\u20b1')):
                    val = "PHP " + val
                return val
        return None

    def _state_machine_parse(self, text: str) -> Tuple[str, List[str]]:
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        description_lines: List[str] = []
        requirements_raw: List[str] = []

        # ── States ─────────────────────────────────────────────────────────────
        # DESCRIPTION  – company intro / announcement text
        # DUTIES       – explicit responsibilities section; all content → description
        # REQUIREMENTS – qualifications section; bullets → requirements_raw
        # IGNORE       – boilerplate; everything discarded
        #
        # Key design decisions:
        #   • "Who We're Looking For" is a DUTIES trigger, NOT a req trigger.
        #     It introduces role titles + their duties (Alfamart pattern), not
        #     a list of candidate qualifications.
        #   • Numbered items (1. STORE CREW) are role titles inside a duties
        #     section — they go to description_lines, not requirements.
        #   • Only a dedicated "Qualifications:" or "Requirements:" sub-header
        #     (or similar) switches the state to REQUIREMENTS.
        #   • Bullets in DESCRIPTION state go to description_lines so that
        #     headerless JDs (Globe-style) still work correctly.
        # ───────────────────────────────────────────────────────────────────────
        current_state = 'DESCRIPTION'

        duties_triggers = [
            r'responsibilities',
            r'what you.*(?:will\s+)?do',
            r'accountabilities',
            r'kpis',
            r'role definition',
            r'job description',
            r'core responsibilities',
            r'what the role entails',
            r'your role',
            r'\bthe role\b',
            r'key responsibilities',
            r'\bduties\b',
            # "Who We're Looking For" / "We're Looking For" introduces role
            # titles in job-fair style JDs.  It is NOT a qualifications header.
            r"who we'?re looking for",
            r"who we are looking for",
        ]

        req_triggers = [
            r'required.*skills',
            r'qualifications',
            r'\brequirements\b',
            r'what you will need',
            r'who you are',
            r'key skills',
            r'successful applicant',
            r'what we ask of you',
            r'what we need',
            r'\bmust have\b',
        ]

        pref_triggers = [
            r'preferred.*skills',
            r'preferred.*capabilities',
            r'preferred.*qualifications',
            r'bonus points',
            r'nice to have',
            r'it is a plus',
        ]

        ignore_triggers = [
            r'why\s+\w',
            r'\bbenefits\b',
            r'\bperks\b',
            r'what we offer',
            r'about us',
            r'equal opportunity',
            r'equal employment',
            r"what[\u2019']?s on offer",
            r"what[\u2019']?s in it for you",
            r'make your passion',
            r"globe[\u2019']?s diversity",
            r"globe[\u2019']?s hiring",
        ]

        _BULLET_RE = re.compile(
            r'^[\u2022\u2023\u25E6\u2043\u2219\-*]|\d+\.'
        )
        _STRIP_BULLET_RE = re.compile(
            r'^[\u2022\u2023\u25E6\u2043\u2219\-*]\s*|^\d+\.\s*'
        )

        for line in lines:
            lower_line = line.lower()
            header_check = re.sub(r'[*_#:]', '', lower_line).strip()

            is_bullet = bool(_BULLET_RE.match(line))
            # Numbered items like "1. STORE CREW" are role titles, not bullets
            # in the traditional sense — but _BULLET_RE matches them.
            # We detect them separately so we can route them correctly.
            is_numbered = bool(re.match(r'^\d+\.', line))
            ends_with_punctuation = bool(re.search(r'[,.;]$', header_check))
            is_potential_header = (
                len(header_check) < 80
                and not is_bullet
                and not ends_with_punctuation
            )

            state_changed = False

            if is_potential_header:
                # Check ignore first (highest priority — discard boilerplate).
                if any(re.search(p, header_check) for p in ignore_triggers):
                    current_state = 'IGNORE'
                    state_changed = True
                # Requirements / qualifications headers.
                elif (any(re.search(p, header_check) for p in req_triggers)
                      or any(re.search(p, header_check) for p in pref_triggers)):
                    current_state = 'REQUIREMENTS'
                    state_changed = True
                # Duties / responsibilities headers (including "Who We're Looking For").
                elif any(re.search(p, header_check) for p in duties_triggers):
                    current_state = 'DUTIES'
                    state_changed = True

            # Always skip the header line itself.
            if state_changed:
                continue

            # ── Route content ───────────────────────────────────────────────────
            if current_state in ('DESCRIPTION', 'DUTIES'):
                # Numbered items (role titles like "1. STORE CREW") and bullets
                # under a duties section are all job description content.
                clean = _STRIP_BULLET_RE.sub('', line).strip()
                # Skip lines that are only punctuation/colons — these are
                # normalization artifacts from section header splitting.
                if clean and clean not in (':', '-', '|', '/'):
                    description_lines.append(clean)

            elif current_state == 'REQUIREMENTS':
                # Skip sub-header lines that end with a colon.
                if line.strip().endswith(':'):
                    continue
                # Numbered items inside a requirements section should NOT be
                # treated as requirements — they are likely role titles that
                # appeared before the Qualifications header.  Only plain
                # bullets and long prose lines are genuine requirements.
                if is_numbered:
                    # Treat numbered role titles as description even if we're
                    # technically in REQUIREMENTS state (handles edge cases where
                    # the section header order is ambiguous).
                    clean = _STRIP_BULLET_RE.sub('', line).strip()
                    if clean:
                        description_lines.append(clean)
                elif is_bullet or len(line) > 20:
                    requirements_raw.append(line)

            # IGNORE: discard silently.

        # ── Deduplicate and clean requirements ──────────────────────────────────
        parsed_reqs: List[str] = []
        for req in requirements_raw:
            clean_req = _STRIP_BULLET_RE.sub('', req).strip()
            if clean_req and len(clean_req) > 5 and clean_req not in parsed_reqs:
                parsed_reqs.append(clean_req)

        return '\n'.join(description_lines), parsed_reqs


parser_instance = JobDescriptionParser()


def parse_job_description(description: str) -> Dict[str, Any]:
    return parser_instance.parse(description)