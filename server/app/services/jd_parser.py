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

    def _normalize_text(self, text: str) -> str:
        # 1. Heal broken hard-wraps first so we don't chop words in half.
        text = re.sub(r'([a-zA-Z,])\n\s*([a-z])', r'\1 \2', text)
        
        # 2. FORCE EMBEDDED HEADERS ONTO NEW LINES.
        # This breaks apart paragraphs where the employer smashed the header 
        # and the requirements into the exact same sentence.
        embedded_headers = [
            r'what the role entails', 
            r'what we ask of you', 
            r'it is a plus if you have', 
            r'what[\'’]?s in it for you\??',
            r'the successful applicant', 
            r'what[\'’]?s on offer'
        ]
        for header in embedded_headers:
            # Inject a newline before and after the matched header
            text = re.sub(rf'(?i)({header})', r'\n\1\n', text)
            
        # 3. Convert inline horizontal separators ( - or • ) into actual new vertical bullets.
        text = re.sub(r'\s+[•]\s+', '\n- ', text)
        
        return text

    def _extract_salary(self, text: str) -> str:
        patterns = [
            # 1. Salary keyword + optional PHP + Range
            r'(?i)(?:salary|compensation|pay|rate)\s*:?\s*(?:range(?:s)?\s*(?:is|are)?\s*)?(?:PHP|P|₱|Php)?\s*(\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?\s*(?:-|to|–|—)\s*(?:PHP|P|₱|Php)?\s*\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?)',
            # 2. PHP symbol + Range or Single Number (e.g., PHP 80,000 - PHP 100,000 or PHP 80,000)
            r'(?i)(?:PHP|P|₱|Php)\s*(\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?(?:\s*(?:-|to|–|—)\s*(?:PHP|P|₱|Php)?\s*\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?)?)',
            # 3. Salary keyword + optional PHP + Single Number
            r'(?i)(?:salary|compensation|pay|rate)\s*:?\s*(?:range\s*is\s*)?(?:PHP|P|₱|Php)?\s*(\d{2,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:k|K)?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                val = match.group(1).strip()
                if not val.upper().startswith('PHP') and not val.upper().startswith('P') and not val.startswith('₱'):
                    val = "PHP " + val
                return val
        return None

    def _state_machine_parse(self, text: str) -> Tuple[str, List[str]]:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        description_lines = []
        requirements_raw = []
        
        current_state = 'DESCRIPTION'
        
        req_triggers = [
            r'required.*skills', r'qualifications', r'requirements', 
            r'what you will need', r'who you are', r'key skills', 
            r'successful applicant', r'what we ask of you'
        ]
        pref_triggers = [
            r'preferred.*skills', r'preferred.*capabilities', 
            r'preferred.*qualifications', r'bonus points', r'nice to have',
            r'it is a plus'
        ]
        ignore_triggers = [
            r'why\s+.*', r'benefits', r'perks', r'what we offer', 
            r'about us', r'equal opportunity', r'what[\'’]?s on offer',
            r'what[\'’]?s in it for you'
        ]
        desc_triggers = [
            r'responsibilities', r'what you.*do', r'accountabilities', 
            r'kpis', r'role definition', r'job description', r'core responsibilities',
            r'what the role entails'
        ]

        for line in lines:
            lower_line = line.lower()
            header_check = re.sub(r'[*_#:]', '', lower_line).strip()
            
            is_bullet = bool(re.match(r'^[-•*\u2022\u2023\u25E6\u2043\u2219]|\d+\.', line))
            ends_with_punctuation = bool(re.search(r'[,.;]$', header_check))
            
            is_potential_header = (len(header_check) < 75 and not is_bullet and not ends_with_punctuation)
            
            state_changed = False
            
            if is_potential_header:
                if any(re.search(p, header_check) for p in ignore_triggers):
                    current_state = 'IGNORE'
                    state_changed = True
                elif any(re.search(p, header_check) for p in req_triggers) or any(re.search(p, header_check) for p in pref_triggers):
                    current_state = 'REQUIREMENTS'
                    state_changed = True
                elif any(re.search(p, header_check) for p in desc_triggers):
                    current_state = 'DESCRIPTION'
                    state_changed = True
            
            if state_changed:
                continue 
            
            if current_state == 'DESCRIPTION':
                clean_desc_line = re.sub(r'^[-•*\u2022\u2023\u25E6\u2043\u2219]\s*|^\d+\.\s*', '', line).strip()
                if clean_desc_line:
                    description_lines.append(clean_desc_line)
                    
            elif current_state == 'REQUIREMENTS':
                if line.strip().endswith(':'):
                    continue
                    
                if is_bullet or len(line) > 20:
                    requirements_raw.append(line)
                    
        parsed_reqs = []
        for req in requirements_raw:
            clean_req = re.sub(r'^[-•*\u2022\u2023\u25E6\u2043\u2219]\s*|^\d+\.\s*', '', req).strip()
            if clean_req and len(clean_req) > 5 and clean_req not in parsed_reqs:
                parsed_reqs.append(clean_req)
                
        return '\n'.join(description_lines), parsed_reqs

parser_instance = JobDescriptionParser()

def parse_job_description(description: str) -> Dict[str, Any]:
    return parser_instance.parse(description)