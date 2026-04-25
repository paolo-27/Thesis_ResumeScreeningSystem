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
        # 1. Force known section headers onto their own lines FIRST.
        #    This splits "...standards.Job DescriptionManages..." correctly
        #    even when there are no newlines in the source text.
        for phrase in self._SECTION_BREAK_PHRASES:
            # Case-insensitive, word-boundary aware.
            escaped = re.escape(phrase)
            text = re.sub(rf'(?i)(?<!\n)({escaped})', r'\n\1\n', text)

        # 2. Split on bullet characters so each bullet becomes its own line.
        #    Must happen before the hard-wrap healer.
        text = re.sub(
            r'\s*[\u2022\u2023\u25E6\u2043\u2219\xb7]\s*',
            '\n\u2022 ',
            text
        )

        # 3. Heal genuine broken hard-wraps (mid-sentence line breaks where
        #    the previous line ends with a letter/comma and the next line
        #    starts with a lowercase letter).  This must come AFTER step 1
        #    and 2 so we don't rejoin section headers or bullets.
        text = re.sub(r'([a-zA-Z,])\n\s*([a-z])', r'\1 \2', text)

        # 4. Force the remaining embedded-header patterns onto new lines
        #    (handles curly-quote variants not caught by the phrase list).
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

        # ── States ────────────────────────────────────────────────────────────
        # DESCRIPTION  – company intro / no section header yet
        # DUTIES       – explicit responsibilities section; bullets → description
        # REQUIREMENTS – qualifications section; bullets → requirements_raw
        # IGNORE       – boilerplate; everything discarded
        #
        # We start in DESCRIPTION.  Bullets in DESCRIPTION state also go to
        # description_lines so headerless JDs (Globe-style) work correctly.
        # ──────────────────────────────────────────────────────────────────────
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
            r"we'?re looking for",
            r'we are looking for',
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
            ends_with_punctuation = bool(re.search(r'[,.;]$', header_check))
            is_potential_header = (
                len(header_check) < 80
                and not is_bullet
                and not ends_with_punctuation
            )

            state_changed = False

            if is_potential_header:
                if any(re.search(p, header_check) for p in ignore_triggers):
                    current_state = 'IGNORE'
                    state_changed = True
                elif (any(re.search(p, header_check) for p in req_triggers)
                      or any(re.search(p, header_check) for p in pref_triggers)):
                    current_state = 'REQUIREMENTS'
                    state_changed = True
                elif any(re.search(p, header_check) for p in duties_triggers):
                    current_state = 'DUTIES'
                    state_changed = True

            # Always skip the header line itself.
            if state_changed:
                continue

            # ── Route content ─────────────────────────────────────────────────
            if current_state in ('DESCRIPTION', 'DUTIES'):
                clean = _STRIP_BULLET_RE.sub('', line).strip()
                if clean:
                    description_lines.append(clean)

            elif current_state == 'REQUIREMENTS':
                if line.strip().endswith(':'):
                    continue
                if is_bullet or len(line) > 20:
                    requirements_raw.append(line)

            # IGNORE: discard.

        # ── Deduplicate and clean requirements ────────────────────────────────
        parsed_reqs: List[str] = []
        for req in requirements_raw:
            clean_req = _STRIP_BULLET_RE.sub('', req).strip()
            if clean_req and len(clean_req) > 5 and clean_req not in parsed_reqs:
                parsed_reqs.append(clean_req)

        return '\n'.join(description_lines), parsed_reqs


parser_instance = JobDescriptionParser()


def parse_job_description(description: str) -> Dict[str, Any]:
    return parser_instance.parse(description)