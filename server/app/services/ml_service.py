import os
import re
import joblib
import numpy as np
import shap

# --- SHAP / XGBoost 3.0+ compatibility patch ---
try:
    import shap.explainers._tree
    _original_decode = shap.explainers._tree.decode_ubjson_buffer
    def _patched_decode(fd):
        jmodel = _original_decode(fd)
        try:
            bs = jmodel.get("learner", {}).get("learner_model_param", {}).get("base_score")
            if isinstance(bs, str) and bs.startswith("[") and bs.endswith("]"):
                jmodel["learner"]["learner_model_param"]["base_score"] = bs[1:-1]
        except Exception:
            pass
        return jmodel
    shap.explainers._tree.decode_ubjson_buffer = _patched_decode
except AttributeError:
    pass

from xgboost import XGBClassifier
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from datetime import date

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(BASE_DIR, "model")

vectorizer_path = os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl")
classifier_path = os.path.join(MODEL_DIR, "trained_xgb_model.json")

# ---------------------------------------------------------------------------
# Load models globally (once on startup)
# ---------------------------------------------------------------------------
try:
    hf_repo_id = os.environ.get("HF_MODEL_REPO_ID")
    if hf_repo_id:
        from huggingface_hub import hf_hub_download
        repo_type = os.environ.get("HF_MODEL_REPO_TYPE", "space")
        os.makedirs(MODEL_DIR, exist_ok=True)
        if not os.path.exists(vectorizer_path):
            print(f"[ml_service] Downloading vectorizer from {hf_repo_id} ({repo_type})...")
            hf_hub_download(repo_id=hf_repo_id, filename="tfidf_vectorizer.pkl", repo_type=repo_type, local_dir=MODEL_DIR)
        if not os.path.exists(classifier_path):
            print(f"[ml_service] Downloading classifier from {hf_repo_id} ({repo_type})...")
            hf_hub_download(repo_id=hf_repo_id, filename="trained_xgb_model.json", repo_type=repo_type, local_dir=MODEL_DIR)

    # 1. TF-IDF vectorizer (sklearn, joblib)
    vectorizer = joblib.load(vectorizer_path)
    print(f"[ml_service] TF-IDF vectorizer loaded | vocab={len(vectorizer.vocabulary_)} features")

    # 2. XGBoost classifier (native XGBoost JSON format)
    classifier = XGBClassifier()
    classifier.load_model(classifier_path)
    print(f"[ml_service] XGBoost classifier loaded | expects {classifier.n_features_in_} features")

    # 3. SBERT model (all-MiniLM-L6-v2 → 384-dim embeddings)
    sbert = SentenceTransformer("all-MiniLM-L6-v2")
    print("[ml_service] SBERT model loaded")

    models_loaded = True
    print("[ml_service] All models loaded successfully!")
except Exception as e:
    print(f"[ml_service] Error loading models: {e}")
    models_loaded = False
    
# SHAP explainer — lazily initialised on first use and cached
_shap_explainer = None

def _get_shap_explainer():
    global _shap_explainer
    if _shap_explainer is None and models_loaded:
        _shap_explainer = shap.TreeExplainer(classifier)
    return _shap_explainer


# ---------------------------------------------------------------------------
# Feature engineering — must exactly match what was used during training
#
# Feature vector layout (6 dims):
#   [0] TF-IDF cosine similarity
#   [1] SBERT cosine similarity
#   [2] Skills Relevance   (0-2)
#   [3] Years Experience   (0-3)
#   [4] Education Match    (0-2)
#   [5] Domain Alignment   (0-1)
# ---------------------------------------------------------------------------

DEGREE_LEVELS = {
    "none": 0,
    "bachelor": 1,
    "master": 2,
    "phd": 3,
}

_MS_STOPWORDS = [
    "ms office",
    "ms word",
    "ms excel",
    "ms powerpoint",
    "ms project",
    "ms sql",
    "ms access",
    "ms dynamics",
    "ms windows",
    "ms teams",
    "ms outlook",
    "ms publisher",
]

_BA_STOPWORDS = [
    "business analyst",
    "business analysis",
    "business analytics",
]

# ---------------------------------------------------------------------------
# FIELD_ALIASES – maps a canonical field name to all surface-form aliases.
# Aliases must survive normalize_field_text (dots stripped, lower-cased,
# extra whitespace collapsed).  Do NOT include the dot form; write without
# dots so they match the pre-processed text.
# ---------------------------------------------------------------------------
FIELD_ALIASES = {
    # ── Technology / Computing ──────────────────────────────────────────
    "computer science": [
        "computer science",
        "com sci",
        "comp sci",
        "bs cs",
        "bscs",
        "bscsce",         # some Philippine transcripts
    ],
    "information technology": [
        "information technology",
        "information tech",
        "bs it",
        "bsit",
    ],
    "software engineering": [
        "software engineering",
        "software development",
        "software systems",
    ],
    "data science": [
        "data science",
        "data analytics",
    ],
    "computer engineering": [
        "computer engineering",
        "comp eng",
        "computer eng",
        "cpe",
    ],
    "information systems": [
        "information systems",
        "management information systems",
        "bs is",
        "bsis",
        "mis",
    ],
    "statistics": [
        "statistics",
        "statistical science",
        "applied statistics",
    ],
    "mathematics": [
        "mathematics",
        "math",
        "applied mathematics",
        "computational mathematics",
    ],
    "cybersecurity": [
        "cybersecurity",
        "cyber security",
        "information security",
        "infosec",
        "network security",
        "security engineering",
    ],
    "cloud computing": [
        "cloud computing",
        "cloud engineering",
        "cloud architecture",
    ],
    # ── Engineering (non-CS) ────────────────────────────────────────────
    "mechanical engineering": [
        "mechanical engineering",
        "mechanical eng",
        "me engineering",
    ],
    "civil engineering": [
        "civil engineering",
        "civil eng",
    ],
    "electrical engineering": [
        "electrical engineering",
        "electrical eng",
        "electronics engineering",
        "electronics and communications engineering",
        "ece",
    ],
    "industrial engineering": [
        "industrial engineering",
        "industrial eng",
    ],
    "chemical engineering": [
        "chemical engineering",
        "chemical eng",
    ],
    "aerospace engineering": [
        "aerospace engineering",
        "aeronautical engineering",
    ],
    "biomedical engineering": [
        "biomedical engineering",
        "biomedical eng",
        "biomed engineering",
    ],
    # ── Natural Sciences ────────────────────────────────────────────────
    "biology": [
        "biology",
        "biological science",
        "biological sciences",
        "biology science",
        "bs biology",
    ],
    "chemistry": [
        "chemistry",
        "bs chemistry",
        "applied chemistry",
    ],
    "physics": [
        "physics",
        "applied physics",
        "bs physics",
    ],
    "environmental science": [
        "environmental science",
        "environmental studies",
        "earth science",
    ],
    # ── Business / Finance ──────────────────────────────────────────────
    "accounting": [
        "accounting",
        "accountancy",
        "bs accountancy",
        "bs accounting",
    ],
    "finance": [
        "finance",
        "financial management",
        "bs finance",
        "bs in finance",
    ],
    "business administration": [
        "business administration",
        "business management",
        "business studies",
        "bba",
        "mba",
        "bs business",
        "bachelor of business",
        "bachelor of business administration",
    ],
    "economics": [
        "economics",
        "bs economics",
        "applied economics",
    ],
    "marketing": [
        "marketing",
        "bs marketing",
        "digital marketing",
        "marketing management",
    ],
    # ── Social Sciences / Humanities ────────────────────────────────────
    "human resources": [
        "human resources",
        "human resource management",
        "hr management",
        "bs hrm",
        "organizational behavior",
        "organizational behaviour",
    ],
    "psychology": [
        "psychology",
        "behavioral science",
        "behavioural science",
        "bs psychology",
    ],
    "sociology": [
        "sociology",
        "social science",
        "social sciences",
    ],
    "political science": [
        "political science",
        "political studies",
        "government",
    ],
    "communications": [
        "communications",
        "communication studies",
        "communication arts",
        "journalism",
        "media studies",
        "mass communication",
        "broadcast communication",
    ],
    # ── Health / Medicine ───────────────────────────────────────────────
    "nursing": [
        "nursing",
        "bsn",
        "bs nursing",
        "registered nurse",
    ],
    "medicine": [
        "medicine",
        "medical doctor",
        "doctor of medicine",
        "mbbs",
        "md",
    ],
    "pharmacy": [
        "pharmacy",
        "pharmacology",
        "bs pharmacy",
    ],
    "public health": [
        "public health",
        "community health",
        "epidemiology",
        "mph",
    ],
    # ── Education ───────────────────────────────────────────────────────
    "education": [
        "education",
        "educational studies",
        "teaching",
        "bachelor of education",
        "bed",
    ],
    # ── Law ─────────────────────────────────────────────────────────────
    "law": [
        "law",
        "legal studies",
        "bachelor of laws",
        "juris doctor",
        "llb",
        "jd",
    ],
    # ── Arts / Design ───────────────────────────────────────────────────
    "architecture": [
        "architecture",
        "architectural engineering",
    ],
    "arts": [
        "arts",
        "fine arts",
        "liberal arts",
        "humanities",
    ],
    # ── Sales & Marketing ────────────────────────────────────────────────────
    "marketing":            ["marketing", "marketing management", "marketing communications"],
    "business administration": ["business administration", "bsa", "bba", "business management",
                                "business studies", "commerce", "bs business administration"],
    "economics":            ["economics", "economic"],
    "entrepreneurship":     ["entrepreneurship", "entrepreneurial management", "business entrepreneurship"],
    "communications":       ["communications", "communication arts", "mass communication",
                             "journalism", "public relations", "media studies"],
    "advertising":          ["advertising", "advertising and public relations"],
 
    # ── Finance & Accounting ─────────────────────────────────────────────────
    "finance":              ["finance", "financial management", "bs finance",
                             "banking and finance", "corporate finance"],
    "accounting":           ["accounting", "accountancy", "bs accountancy",
                             "accounting technology", "management accounting"],
    "banking":              ["banking", "banking and finance", "banking and financial management"],
 
    # ── Administrative ───────────────────────────────────────────────────────
    "office administration":["office administration", "business administration",
                             "administrative management", "secretarial science",
                             "office management"],
    "public administration":["public administration", "government", "political science",
                             "public management"],
 
    # ── Management ──────────────────────────────────────────────────────────
    "management":           ["management", "business management", "general management",
                             "operations management", "organizational management"],
    "human resources":      ["human resources", "human resource management", "hrm",
                             "industrial relations", "labor relations",
                             "personnel management"],
 
    # ── Customer Service / Hospitality ──────────────────────────────────────
    "hospitality management":["hospitality management", "hotel and restaurant management",
                              "hrm", "tourism management", "hospitality and tourism",
                              "hotel management", "tourism"],
    "tourism":              ["tourism", "travel management", "travel and tourism"],
}

RELATED_FIELDS = {
    "computer science": {
        "computer science",
        "information technology",
        "software engineering",
        "data science",
        "computer engineering",
        "information systems",
        "cloud computing",
    },
    "information technology": {
        "information technology",
        "computer science",
        "software engineering",
        "computer engineering",
        "information systems",
        "cloud computing",
        "cybersecurity",
    },
    "software engineering": {
        "software engineering",
        "computer science",
        "information technology",
        "computer engineering",
        "cloud computing",
    },
    "data science": {
        "data science",
        "computer science",
        "statistics",
        "mathematics",
        "software engineering",
        "information technology",
    },
    "computer engineering": {
        "computer engineering",
        "computer science",
        "information technology",
        "software engineering",
    },
    "information systems": {
        "information systems",
        "information technology",
        "computer science",
        "software engineering",
        "business administration",
    },
    "statistics": {
        "statistics",
        "mathematics",
        "data science",
        "economics",
        "finance",
    },
    "mathematics": {
        "mathematics",
        "statistics",
        "data science",
        "computer science",
        "economics",
        "finance",
    },
    "cybersecurity": {
        "cybersecurity",
        "information technology",
        "computer science",
        "computer engineering",
        "information systems",
    },
    "cloud computing": {
        "cloud computing",
        "computer science",
        "software engineering",
        "information technology",
        "computer engineering",
    },
    "accounting": {
        "accounting",
        "finance",
        "business administration",
        "economics",
    },
    "finance": {
        "finance",
        "accounting",
        "business administration",
        "economics",
        "mathematics",
        "statistics",
    },
    "business administration": {
        "business administration",
        "accounting",
        "finance",
        "economics",
        "marketing",
        "human resources",
        "information systems",
    },
    "economics": {
        "economics",
        "finance",
        "business administration",
        "statistics",
        "mathematics",
    },
    "marketing": {
        "marketing",
        "business administration",
        "economics",
    },
    "human resources": {
        "human resources",
        "business administration",
        "psychology",
    },
    "psychology": {
        "psychology",
        "human resources",
        "business administration",
    },
}

CLEARLY_ALIGNED_FIELDS = {
    "computer science": {
        "software engineering",
        "computer engineering",
    },
    "information technology": {
        "information systems",
        "cybersecurity",
    },
    "software engineering": {
        "computer science",
        "computer engineering",
    },
    "data science": {
        "statistics",
        "mathematics",
    },
    "computer engineering": {
        "computer science",
        "software engineering",
    },
    "information systems": {
        "information technology",
    },
    "statistics": {
        "mathematics",
        "data science",
    },
    "mathematics": {
        "statistics",
        "data science",
    },
    "cybersecurity": {
        "information technology",
    },
    "cloud computing": {
        "information technology",
        "software engineering",
    },
    "accounting": {
        "finance",
    },
    "finance": {
        "accounting",
        "economics",
    },
    "business administration": {
        "marketing",
        "human resources",
    },
    "economics": {
        "finance",
    },
    "marketing": {
        "business administration",
    },
    "human resources": {
        "psychology",
        "business administration",
    },
    "psychology": {
        "human resources",
    },
}

SKILL_ALIASES = {
    "python": ["python"],
    "java": ["java"],
    "javascript": ["javascript", "js"],
    "typescript": ["typescript"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "c sharp"],
    "php": ["php"],
    "ruby": ["ruby"],
    "r": ["r programming", "rstudio"],
    "numpy": ["numpy"],
    "pandas": ["pandas"],
    "statistics": ["statistics", "statistical analysis"],
    "scala": ["scala"],
    "go": ["golang", "go lang"],
    "swift": ["swift"],
    "kotlin": ["kotlin"],
    "rust": ["rust"],
    "shell scripting": ["bash", "shell script", "shell scripting", "powershell"],
    "sql": ["sql"],
    "mysql": ["mysql"],
    "postgresql": ["postgresql", "postgres", "postgre sql"],
    "mongodb": ["mongodb", "mongo db"],
    "nosql": ["nosql", "no sql"],
    "oracle db": ["oracle database", "oracle db", "pl/sql"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search"],
    "cassandra": ["cassandra", "apache cassandra"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "react": ["react", "reactjs", "react js"],
    "angular": ["angular", "angularjs", "angular js"],
    "vue": ["vue", "vuejs", "vue js"],
    "node": ["nodejs", "node js", "node.js", "node"],
    "express": ["express", "expressjs", "express js"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi", "fast api"],
    "spring": ["spring", "spring boot"],
    "laravel": ["laravel"],
    "asp.net": ["asp.net", "asp net", "asp net core", "dotnet", "dot net"],
    "git": ["git", "github", "gitlab"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "jenkins": ["jenkins"],
    "ansible": ["ansible"],
    "terraform": ["terraform"],
    "ci/cd": [
        "ci/cd",
        "continuous integration",
        "continuous deployment",
        "github actions",
    ],
    "devops": ["devops", "dev ops"],
    "agile": ["agile"],
    "scrum": ["scrum"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "spark": ["apache spark", "pyspark", "spark"],
    "hadoop": ["hadoop", "apache hadoop", "hdfs", "hive", "hbase"],
    "kafka": ["kafka", "apache kafka"],
    "snowflake": ["snowflake"],
    "redshift": ["redshift", "amazon redshift"],
    "bigquery": ["bigquery", "big query", "google bigquery"],
    "etl": ["etl", "elt", "data pipeline", "data ingestion"],
    "airflow": ["airflow", "apache airflow"],
    "dbt": ["dbt", "data build tool"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch", "torch"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "xgboost": ["xgboost", "xg boost"],
    "nlp": ["nlp", "natural language processing"],
    "machine learning": ["machine learning"],
    "feature engineering": ["feature engineering", "feature selection"],
    "mlops": ["mlops", "ml ops", "model deployment", "model serving"],
    "deep learning": ["deep learning"],
    "computer vision": ["computer vision"],
    "llm": ["llm", "large language model"],
    "generative ai": ["generative ai", "gen ai", "chatgpt", "openai"],
    "data analysis": ["data analysis", "data analytics"],
    "data science": ["data science"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau"],
    "excel": ["excel", "microsoft excel", "ms excel"],
    "looker": ["looker"],
    "salesforce": ["salesforce", "sfdc"],
    "sap": ["sap", "sap erp", "sap s/4hana", "sap hana"],
    "oracle erp": ["oracle erp", "oracle financials", "oracle fusion"],
    "google analytics": ["google analytics", "ga4"],
    "figma": ["figma"],
    "photoshop": ["photoshop", "adobe photoshop"],
    "illustrator": ["illustrator", "adobe illustrator"],
    "jira": ["jira"],
    "confluence": ["confluence"],
    "accounting": ["accounting", "accounts payable", "accounts receivable", "bookkeeping"],
    "gaap": ["gaap", "generally accepted accounting principles", "ifrs"],
    "financial modeling": ["financial modeling", "financial analysis", "financial reporting"],
    "cpa": ["cpa", "certified public accountant"],
    "sales": ["sales", "business development", "lead generation", "account management"],
    "marketing": ["marketing", "digital marketing", "seo", "sem", "content marketing", "social media"],
    "linux": ["linux", "unix"],
    "networking": ["networking", "tcp/ip", "dns", "vpn", "firewall"],
    "rest api": ["rest api", "restful api", "restful services"],
    "microservices": ["microservices", "micro services"],
    "cybersecurity": ["cybersecurity", "cyber security", "information security"],
    "penetration testing": ["penetration testing", "pen testing", "ethical hacking"],
    # ── Soft / operational skills (retail, supervisory, service roles) ──────────
    "leadership": ["leadership", "team leadership", "people management", "staff management"],
    "communication": ["communication skills", "interpersonal skills", "verbal communication", "written communication"],
    "problem solving": ["problem-solving", "problem solving", "analytical thinking", "critical thinking"],
    "customer service": ["customer service", "customer handling", "customer relations", "customer satisfaction"],
    "cash handling": ["cash handling", "cash management", "cashiering", "pos", "point of sale"],
    "scheduling": ["scheduling", "shift scheduling", "workforce scheduling", "shift management"],
    "team management": ["team management", "team performance", "supervise", "supervision", "delegate", "delegation"],
    "compliance": ["compliance", "safety regulations", "safety compliance", "regulatory compliance"],
    "inventory management": ["inventory management", "stock management", "inventory control"],
    "training": ["training", "coaching", "mentoring", "onboarding"],
    "time management": ["time management", "multitasking", "prioritization"],
    "integrity": ["integrity", "trustworthy", "reliable", "accountability"],
        # ── Sales ────────────────────────────────────────────────────────────────
    "crm":                  ["crm", "customer relationship management"],
    "salesforce":           ["salesforce", "sfdc", "salesforce crm"],
    "hubspot":              ["hubspot", "hub spot"],
    "cold calling":         ["cold calling", "cold call", "outbound calling"],
    "negotiation":          ["negotiation", "contract negotiation", "deal closing"],
    "pipeline management":  ["sales pipeline", "pipeline management", "pipeline tracking"],
    "account management":   ["account management", "key account management", "kam"],
    "b2b sales":            ["b2b sales", "b2b", "business to business sales"],
    "b2c sales":            ["b2c sales", "b2c", "business to consumer sales"],
    "sales forecasting":    ["sales forecasting", "revenue forecasting", "sales projection"],
    "territory management": ["territory management", "territory sales", "area sales"],
 
    # ── Marketing ────────────────────────────────────────────────────────────
    "google ads":           ["google ads", "google adwords", "ppc", "pay per click"],
    "facebook ads":         ["facebook ads", "meta ads", "fb ads", "social media ads"],
    "email marketing":      ["email marketing", "mailchimp", "klaviyo", "email campaign"],
    "content marketing":    ["content marketing", "content strategy", "content creation"],
    "social media":         ["social media", "social media management", "social media marketing"],
    "seo":                  ["seo", "search engine optimization"],
    "sem":                  ["sem", "search engine marketing"],
    "brand management":     ["brand management", "brand strategy", "brand identity"],
    "market research":      ["market research", "market analysis", "consumer research"],
    "copywriting":          ["copywriting", "copy writing", "ad copy", "content writing"],
    "google analytics":     ["google analytics", "ga4", "google analytics 4"],
    "marketing automation": ["marketing automation", "hubspot marketing", "marketo", "pardot"],
    "ecommerce":            ["ecommerce", "e-commerce", "shopify", "woocommerce", "lazada", "shopee"],
    "influencer marketing": ["influencer marketing", "influencer relations"],
    "event marketing":      ["event marketing", "event management", "events coordination"],
    # ── Finance ──────────────────────────────────────────────────────────────
    "financial modeling":   ["financial modeling", "financial model", "financial analysis"],
    "financial reporting":  ["financial reporting", "financial statements", "financial report"],
    "budgeting":            ["budgeting", "budget planning", "budget management", "budget preparation"],
    "forecasting":          ["forecasting", "financial forecast", "revenue forecast"],
    "gaap":                 ["gaap", "generally accepted accounting principles"],
    "ifrs":                 ["ifrs", "international financial reporting standards"],
    "cpa":                  ["cpa", "certified public accountant"],
    "quickbooks":           ["quickbooks", "quick books", "qbo"],
    "xero":                 ["xero", "xero accounting"],
    "accounts payable":     ["accounts payable", "ap", "vendor payments"],
    "accounts receivable":  ["accounts receivable", "ar", "collections"],
    "tax compliance":       ["tax compliance", "tax preparation", "tax filing", "bir", "vat"],
    "internal audit":       ["internal audit", "internal auditing", "audit"],
    "risk management":      ["risk management", "risk assessment", "enterprise risk"],
    "treasury":             ["treasury", "cash management", "liquidity management"],
    "payroll":              ["payroll", "payroll processing", "payroll management"],
    "cost accounting":      ["cost accounting", "cost analysis", "cost control", "standard costing"],
    "investment analysis":  ["investment analysis", "portfolio management", "equity research"],
    "banking":              ["banking", "bank operations", "retail banking", "corporate banking"],
 
    # ── Administrative ───────────────────────────────────────────────────────
    "microsoft office":     ["microsoft office", "ms office", "office suite", "microsoft 365"],
    "microsoft word":       ["microsoft word", "ms word"],
    "microsoft excel":      ["microsoft excel", "ms excel", "excel"],
    "google workspace":     ["google workspace", "google docs", "google sheets", "gsuite", "g suite"],
    "data entry":           ["data entry", "data encoding", "data input", "data management"],
    "records management":   ["records management", "filing", "document management", "document control"],
    "calendar management":  ["calendar management", "scheduling", "appointment setting", "diary management"],
    "travel coordination":  ["travel coordination", "travel arrangements", "travel management"],
    "office management":    ["office management", "office administration", "office coordination"],
    "report writing":       ["report writing", "report preparation", "business writing"],
    "minute taking":        ["minute taking", "minutes of meeting", "meeting minutes"],
    "correspondence":       ["correspondence", "business correspondence", "email management"],
    "procurement admin":    ["purchase orders", "po processing", "vendor coordination", "purchasing"],
    "receptionist":         ["receptionist", "front desk", "front office"],
 
    # ── Business Management / Strategy ──────────────────────────────────────
    "strategic planning":   ["strategic planning", "business strategy", "corporate strategy"],
    "business development": ["business development", "biz dev", "new business"],
    "stakeholder management": ["stakeholder management", "stakeholder engagement"],
    "change management":    ["change management", "organizational change", "transformation"],
    "business analysis":    ["business analysis", "business analyst", "requirements gathering"],
    "process improvement":  ["process improvement", "business process improvement", "lean", "six sigma"],
    "kpi management":       ["kpi", "key performance indicators", "performance metrics", "okr"],
    "vendor management":    ["vendor management", "supplier management", "third party management"],
    "contract management":  ["contract management", "contract review", "contract administration"],
    "consulting":           ["consulting", "management consulting", "business consulting"],
    "p&l management":       ["p&l", "profit and loss", "income statement management"],
    # ── Customer Service ────────────────────────────────────────────────────
    "zendesk":              ["zendesk", "zen desk"],
    "freshdesk":            ["freshdesk", "fresh desk"],
    "live chat":            ["live chat", "chat support", "online chat"],
    "call center":          ["call center", "call centre", "contact center", "bpo"],
    "complaint handling":   ["complaint handling", "complaint resolution", "issue resolution"],
    "after sales":          ["after sales", "after-sales support", "post sales"],
    "ticketing system":     ["ticketing system", "ticket management", "service ticket"],
    "voice support":        ["voice support", "inbound calls", "outbound calls", "telephone support"],
    "technical support":    ["technical support", "tech support", "it helpdesk"],
    "chat support":         ["chat support", "email support", "non-voice support"],
    # ── Management / Leadership ──────────────────────────────────────────────
    "people management":    ["people management", "team leadership", "staff management", "people leader"],
    "performance management": ["performance management", "performance review", "appraisal", "kra"],
    "workforce planning":   ["workforce planning", "headcount planning", "capacity planning"],
    "budget management":    ["budget management", "cost management", "expense management"],
    "operations management":["operations management", "operational excellence", "ops management"],
    "project management":   ["project management", "project planning", "pmp", "prince2"],
    "program management":   ["program management", "program coordinator", "program director"],
    "cross-functional":     ["cross-functional", "cross functional", "cross-team collaboration"],
    "executive management": ["general manager", "chief executive", "ceo", "coo", "director"],
    # ── Retail Operations ─────────────────────────────────────────────────────
    "cash handling":        ["cash handling", "cash management", "cashiering", "cash register", "cashiering", "cashier"],
    "point of sale":        ["point of sale", "pos system", "pos software", "pos operations"],
    "inventory":            ["inventory management", "stock management", "inventory control", "stocktaking", "stock control"],
    "loss prevention":      ["loss prevention", "shrinkage control", "anti-shoplifting", "security procedures"],
    "store operations":     ["store operations", "retail operations", "shop operations", "operations management"],
    "visual merchandising":  ["visual merchandising", "display setup", "window display", "planogram"],
    "stock replenishment":  ["stock replenishment", "restocking", "stock movement"],
    "shift management":     ["shift management", "shift scheduling", "shift handover"],
    "store opening":        ["store opening", "store closing", "opening procedures", "closing procedures"],
    "safety compliance":    ["safety compliance", "store safety", "workplace safety", "emergency procedures"],
    "merchandising":        ["merchandising", "product placement", "display maintenance"],
    "shelf management":     ["shelf management", "shelf stocking", "facing", "fronting"],
    "till management":      ["till management", "till balancing", "cash reconciliation"],
    "customer assistance":  ["customer assistance", "customer support", "in-store assistance"],
    "retail security":      ["retail security", "security protocols", "theft prevention"],
    "operational standards":["operational standards", "quality standards", "store standards"],
    "store audit":          ["store audit", "operational audit", "compliance check"],
    "stock accuracy":       ["stock accuracy", "inventory accuracy", "cycle counting"],
    "retail display":       ["retail display", "product display", "promotional display"],
}

DOMAIN_KEYWORDS = {
    "software_engineering": {
        "software engineer",
        "software developer",
        "backend",
        "frontend",
        "full stack",
        "full-stack",
        "web development",
        "application development",
        "mobile developer",
        "ios developer",
        "android developer",
    },
    "admin_operations": {
        "administrative coordinator",
        "administrative assistant",
        "office coordinator",
        "office manager",
        "executive assistant",
        "clerical",
        "office administration",
        "front desk",
        "receptionist",
        "office operations",
        },
    "data_science": {
        "data science",
        "machine learning",
        "nlp",
        "natural language processing",
        "artificial intelligence",
        "deep learning",
        "predictive modeling",
        "feature engineering",
        "computer vision",
        "mlops",
    },
    "data_analytics": {
        "data analyst",
        "business intelligence",
        "dashboard",
        "reporting",
        "tableau",
        "power bi",
        "powerbi",
        "analytics",
        "data visualization",
        "looker",
        "excel",
    },
    "data_engineering": {
        "data engineer",
        "data pipeline",
        "etl",
        "elt",
        "spark",
        "hadoop",
        "kafka",
        "snowflake",
        "redshift",
        "bigquery",
        "airflow",
        "data warehouse",
        "data lake",
        "data ingestion",
    },
    "it_support": {
        "technical support",
        "help desk",
        "it support",
        "system administration",
        "network administration",
        "desktop support",
        "service desk",
        "troubleshooting",
        "network engineer",
    },
    "cybersecurity": {
        "cybersecurity",
        "cyber security",
        "information security",
        "infosec",
        "penetration testing",
        "pen testing",
        "vulnerability assessment",
        "soc",
        "threat intelligence",
        "ethical hacking",
        "network security",
    },
    "devops_cloud": {
        "devops",
        "cloud engineer",
        "cloud architect",
        "site reliability",
        "devsecops",
        "platform engineer",
        "infrastructure",
        "kubernetes",
        "docker",
        "terraform",
        "ansible",
        "ci/cd",
        "continuous integration",
    },
    "finance": {
        "finance",
        "banking",
        "fraud detection",
        "financial analysis",
        "risk management",
        "accounting",
        "gaap",
        "ifrs",
        "cpa",
        "financial reporting",
        "accounts payable",
        "accounts receivable",
        "auditor",
        "tax",
        "controller",
        "treasury",
    },
    "sales_marketing": {
        "sales representative",
        "sales associate",
        "sales executive",
        "sales manager",
        "account executive",
        "account manager",
        "business development",
        "lead generation",
        "sales operations",
        "inside sales",
        "outside sales",
        "field sales",
        "territory sales",
        "b2b sales",
        "b2c sales",
        "sales coordinator",
        # Marketing
        "marketing",
        "digital marketing",
        "marketing manager",
        "marketing coordinator",
        "marketing specialist",
        "brand manager",
        "content marketer",
        "seo specialist",
        "social media manager",
        "email marketing",
        "campaign manager",
        "ecommerce",
        "market research",
        "marketing analyst",
        "growth hacker",
        "product marketing",
    },
    "hr_recruitment": {
        "human resources",
        "recruitment",
        "talent acquisition",
        "sourcing",
        "screening",
        "hr manager",
        "people operations",
        "workforce",
        "compensation and benefits",
        "payroll",
    },
    "product_management": {
        "product manager",
        "product owner",
        "product management",
        "roadmap",
        "user stories",
        "agile",
        "scrum",
    },
    "design_creative": {
        "graphic designer",
        "graphic design",
        "visual design",
        "brand design",
        "branding",
        "typography",
        "illustrator",
        "photoshop",
        "figma",
        "creative design",
        "art direction",
        "ui design",
        "ux design",
    },
    "retail_operations": {
        "retail",
        "store operations",
        "shift supervisor",
        "shift manager",
        "store manager",
        "floor manager",
        "store crew",
        "daily operations",
        "cash handling",
        "safety regulations",
        "team performance",
        "crew",
        "branch operations",
        "convenience store",
        "supermarket",
        "fast food",
        "food service",
        "restaurant",
        "cashier",
        "customer issues",
        "shifting schedules",
        "shifting schedule",
    },
        "admin_operations": {
        "administrative coordinator",
        "administrative assistant",
        "admin coordinator",
        "admin assistant",
        "office coordinator",
        "office administrator",
        "office manager",
        "executive assistant",
        "personal assistant",
        "administrative officer",
        "administrative staff",
        "clerical",
        "clerical staff",
        "front desk",
        "receptionist",
        "secretary",
        "data entry",
        "records management",
        "document control",
    },
    "customer_service": {
        "customer service",
        "customer service representative",
        "customer support",
        "customer success",
        "customer experience",
        "call center",
        "contact center",
        "bpo",
        "help desk",
        "client relations",
        "client services",
        "after sales",
        "service advisor",
        "technical support representative",
        "chat support",
        "voice support",
        "non-voice support",
    },
    "management": {
        "general manager",
        "operations manager",
        "department manager",
        "branch manager",
        "area manager",
        "regional manager",
        "senior manager",
        "director",
        "vp",
        "vice president",
        "chief operating officer",
        "chief executive",
        "managing director",
        "team leader",
        "team manager",
        "supervisor",
        "department head",
        "division head",
        "people manager",
        "program director",
    },
    "finance_accounting": {
        "finance",
        "financial analyst",
        "financial controller",
        "finance manager",
        "accounting",
        "accountant",
        "bookkeeper",
        "cpa",
        "auditor",
        "tax specialist",
        "tax accountant",
        "billing specialist",
        "accounts payable",
        "accounts receivable",
        "payroll specialist",
        "treasury analyst",
        "budget analyst",
        "cost accountant",
        "investment analyst",
        "banking",
        "credit analyst",
        "financial reporting",
        "gaap",
        "ifrs",
    },
    "business_management": {
        "business analyst",
        "business development manager",
        "strategy manager",
        "management consultant",
        "operations analyst",
        "process improvement",
        "project manager",
        "program manager",
        "supply chain manager",
        "procurement manager",
        "vendor management",
        "change management",
        "strategic planning",
        "corporate strategy",
        "general management",
    },
}

_DATA_ANALYTICS_STRONG_TERMS = {
    "data analyst",
    "business intelligence",
    "tableau",
    "power bi",
    "powerbi",
    "looker",
    "data visualization",
    "analytics engineer",
}

_DATA_ANALYTICS_WEAK_TERMS = {
    "analytics",
    "dashboard",
    "reporting",
    "excel",
    "kpi",
    "metrics",
}

_MARKETING_CONTEXT_TERMS = {
    "marketing",
    "digital marketing",
    "seo",
    "sem",
    "social media",
    "brand",
    "campaign",
    "creative",
    "graphic designer",
}

_HR_RECRUITMENT_STRONG_TERMS = {
    "human resources",
    "recruitment",
    "talent acquisition",
    "sourcing",
    "hr manager",
    "people operations",
    "compensation and benefits",
    "payroll",
}

_HR_RECRUITMENT_WEAK_TERMS = {
    "screening",
    "workforce",
}

_TECHNICAL_DOMAINS = {
    "software_engineering",
    "data_science",
    "data_analytics",
    "data_engineering",
    "devops_cloud",
    "cybersecurity",
    "it_support",
}

_TECHNICAL_BRIDGE_SKILLS = {
    "python",
    "sql",
    "statistics",
    "machine learning",
    "scikit-learn",
    "xgboost",
    "pandas",
    "numpy",
    "nlp",
}

RELATED_DOMAINS = {
    "software_engineering": {"software_engineering", "devops_cloud", "data_engineering", "data_science"},
    "data_science": {"data_science", "data_analytics", "data_engineering", "software_engineering", "devops_cloud"},
    "data_analytics": {"data_analytics", "data_science", "data_engineering"},
    "data_engineering": {"data_engineering", "data_science", "software_engineering", "devops_cloud"},
    "it_support": {"it_support", "devops_cloud"},
    "cybersecurity": {"cybersecurity", "it_support"},
    "devops_cloud": {"devops_cloud", "software_engineering", "data_engineering", "data_science", "it_support"},
    "finance": {"finance", "finance_accounting", "business_management"},
    "sales_marketing": {"sales_marketing", "customer_service"},
    "hr_recruitment": {"hr_recruitment"},
    "product_management": {"product_management", "software_engineering"},
    "design_creative": {"design_creative"},
    "admin_operations": {"admin_operations", "operations_product"},
    "retail_operations": {"retail_operations"},
    "admin_operations":   {"admin_operations", "customer_service", "management"},
    "customer_service":   {"customer_service", "admin_operations", "retail_operations", "sales_marketing"},
    "management":         {"management", "business_management", "operations_product", "admin_operations"},
    "finance_accounting": {"finance_accounting", "finance", "business_management"},
    "business_management":{"business_management", "management", "operations_product", "finance_accounting"},
}

ROLE_FAMILY_DOMAIN_MAP = {
    "software_backend":   {"software_engineering", "devops_cloud"},
    "data_ml":            {"data_science", "data_analytics", "data_engineering"},
    "design_creative":    {"design_creative"},
    "hr_recruiting":      {"hr_recruitment"},
    "marketing_business": {"sales_marketing"},
    "sales":              {"sales_marketing"},
    "finance_accounting": {"finance", "finance_accounting"},
    "operations_product": {"product_management", "business_management"},
    "it_security":        {"it_support", "cybersecurity"},
    "retail_ops":         {"retail_operations"},
    "admin_ops":          {"admin_operations"},
    "customer_service":   {"customer_service"},
    "management":         {"management", "business_management"},
}

ROLE_FAMILY_KEYWORDS = {
    "software_backend": {
        "software engineer",
        "backend engineer",
        "backend developer",
        "python developer",
        "api developer",
        "qa engineer",
        "quality assurance engineer",
        "quality assurance analyst",
        "test engineer",
        "automation engineer",
        "site reliability engineer",
        "platform engineer",
        "systems engineer",
        "rest api",
        "microservices",
        "full stack",
    },
    "data_ml": {
        "machine learning",
        "data science",
        "data scientist",
        "data analyst",
        "data engineer",
        "business intelligence",
        "bi analyst",
        "bi developer",
        "reporting analyst",
        "analytics engineer",
        "data visualization",
        "tableau",
        "power bi",
        "feature engineering",
        "predictive model",
        "analytics",
    },
    "design_creative": {
        "graphic designer",
        "graphic design",
        "visual design",
        "brand design",
        "figma",
        "illustrator",
        "photoshop",
        "creative",
        "ui designer",
        "ux designer",
        "ui ux designer",
        "multimedia designer",
        "video editor",
        "motion graphics",
    },
    "hr_recruiting": {
        "human resources",
        "recruitment",
        "recruiter",
        "talent acquisition",
        "sourcing",
        "screening",
        "people operations",
        "hr generalist",
        "hr specialist",
        "people partner",
        "payroll specialist",
        "compensation and benefits",
    },
    "marketing_business": {
        "marketing",
        "digital marketing",
        "seo",
        "sem",
        "campaign",
        "business development",
        "brand manager",
        "sales",
        "sale lead",
        "sale pitch",
        "sales pitch",
        "hotel sales",
        "hospitality sales",
        "ecommerce",
        "account manager",
        "account executive",
        "sales representative",
        "customer success manager",
        "customer success specialist",
        "social media manager",
        "content writer",
        "copywriter",
        "marketing coordinator",
        "marketing specialist",
        "marketing analyst",
        "digital marketing specialist",
        "seo specialist",
        "sem specialist",
        "social media specialist",
        "content creator",
        "brand coordinator",
        "market research analyst",
        "email marketing specialist",
        "growth marketer",
        "product marketing manager",
        "communications specialist",
        "public relations",
        "pr specialist",
    },
    "finance_accounting": {
        "finance",
        "financial analysis",
        "accounting",
        "bookkeeping",
        "bookkeeper",
        "financial statement",
        "cash flow",
        "accounts payable",
        "accounts receivable",
        "auditor",
        "tax",
        "billing",
        "financial controller",
        "cost accountant",
        "billing specialist",
        "accounts assistant",
        "finance analyst",
        "finance manager",
        "financial controller",
        "treasury analyst",
        "budget analyst",
        "credit analyst",
        "investment analyst",
        "risk analyst",
        "cpa",
        "external auditor",
        "internal auditor",
        "payroll officer",
        "payroll manager",
        "cost analyst",
        "management accountant",
        "finance officer",
    },
    "operations_product": {
        "product manager",
        "product owner",
        "product management",
        "roadmap",
        "user stories",
        "scrum",
        "operations",
        "program manager",
        "project manager",
        "project coordinator",
        "program coordinator",
        "operations analyst",
        "operations coordinator",
        "business analyst",
        "business system analyst",
        "business systems analyst",
        "bsa trainee",
        "functional requirement",
        "customer business requirement",
        "supply chain analyst",
        "procurement specialist",
        "compliance officer",
        "risk analyst",
        "hospitality",
        "culinary",
        "catering",
        "kitchen",
        "kitchen staff",
        "cook",
        "chef",
        "cook helper",
        "waiter",
        "server",
        "restaurant",
        "food safety",
        "food costing",
        "inventory",
        "haccp",
        "office administrator",
        "administrative assistant",
        "administrative coordinator",
        "office coordinator",
        "admin coordinator",
        "administrative officer",
        "executive assistant",
        "office manager",
        "customer service representative",
        "customer support specialist",
        "administrative coordinator",
        "administrative officer",
        "executive assistant",
        "personal assistant",
        "office coordinator",
        "office manager",
        "front desk officer",
        "receptionist",
        "secretary",
        "data entry specialist",
        "records officer",
        "document controller",
        "general affairs",
        
    },
    "retail_ops": {
        "shift supervisor",
        "store supervisor",
        "shift manager",
        "store manager",
        "floor manager",
        "store crew",
        "crew member",
        "retail staff",
        "retail associate",
        "cashier",
        "branch operations",
        "daily operations",
        "cash handling",
        "safety regulations",
        "team performance",
        "shifting schedule",
        "shifting schedules",
        "convenience store",
        "supermarket",
        "fast food",
        "food service",
        "restaurant manager",
    },
    "it_security": {
        "cybersecurity",
        "security analyst",
        "information security",
        "it support",
        "system administration",
        "network administration",
        "troubleshooting",
        "help desk",
        "technical support specialist",
        "service desk analyst",
        "desktop support",
        "network engineer",
        "security operations center",
        "soc analyst",
        "helpdesk",
    },
    "sales": {
        "sales representative",
        "sales associate",
        "sales executive",
        "sales manager",
        "inside sales representative",
        "outside sales representative",
        "field sales representative",
        "territory sales manager",
        "account executive",
        "account manager",
        "key account manager",
        "sales coordinator",
        "sales analyst",
        "sales operations",
        "sales development representative",
        "sdr",
        "business development representative",
        "bdr",
        "pre-sales",
        "solution sales",
        "retail sales associate",
    },
    "admin_ops": {
        "administrative coordinator",
        "administrative assistant",
        "admin coordinator",
        "admin assistant",
        "admin officer",
        "administrative officer",
        "office coordinator",
        "office administrator",
        "office manager",
        "executive assistant",
        "personal assistant",
        "front desk officer",
        "receptionist",
        "secretary",
        "data entry clerk",
        "data entry specialist",
        "records officer",
        "document controller",
        "clerical staff",
        "general clerk",
        "encoder",
    },
    "customer_service": {
        "customer service representative",
        "customer service associate",
        "customer support representative",
        "customer success manager",
        "customer success specialist",
        "client relations officer",
        "client services associate",
        "call center agent",
        "contact center agent",
        "bpo agent",
        "technical support representative",
        "chat support agent",
        "voice agent",
        "non-voice agent",
        "email support specialist",
        "service advisor",
        "after sales specialist",
        "customer experience specialist",
    },
    "management": {
        "general manager",
        "operations manager",
        "branch manager",
        "area manager",
        "regional manager",
        "department manager",
        "department head",
        "division head",
        "senior manager",
        "director",
        "vice president",
        "vp",
        "chief operating officer",
        "coo",
        "chief executive officer",
        "ceo",
        "managing director",
        "team leader",
        "team manager",
        "supervisor",
        "program director",
        "country manager",
    },
    "business_management": {
        "business analyst",
        "business development manager",
        "management consultant",
        "strategy manager",
        "strategic planning manager",
        "operations analyst",
        "process improvement specialist",
        "project manager",
        "program manager",
        "supply chain manager",
        "procurement manager",
        "logistics manager",
        "change management specialist",
        "corporate strategy",
        "business transformation",
        "business process analyst",
    },
}

ROLE_FAMILY_SKILL_HINTS = {
    "software_backend": {
        "python", "fastapi", "flask", "docker", "kubernetes", "rest api", "postgresql",
        "ci/cd", "jenkins", "pytest", "selenium", "playwright",
    },
    "data_ml": {
        "python", "sql", "pandas", "numpy", "machine learning", "scikit-learn", "xgboost", "nlp",
        "tableau", "power bi", "business intelligence", "data visualization",
    },
    "design_creative": {"figma", "photoshop", "illustrator", "typography", "after effects", "premiere pro"},
    "hr_recruiting": {"sourcing", "screening", "ats", "interviewing", "onboarding", "payroll"},
    "marketing_business": {
        "seo", "sem", "google analytics", "lead generation", "marketing automation",
        "crm", "salesforce", "social media", "content marketing", "copywriting",
        "sales", "sale", "ecommerce", "hospitality sales", "google ads", "facebook ads", "email marketing", "content marketing",
        "social media", "brand management", "market research", "copywriting",
        "google analytics", "marketing automation", "ecommerce",
        "influencer marketing", "event marketing",
    },
    "finance_accounting": {
        "financial reporting", "gaap", "ifrs", "tax", "excel", "quickbooks",
        "bookkeeping", "budgeting", "forecasting", "billing",
        "financial statement", "cash flow", "accounts payable", "accounts receivable","financial modeling", "financial reporting", "budgeting", "forecasting",
        "gaap", "ifrs", "cpa", "quickbooks", "xero", "tax compliance",
        "internal audit", "risk management", "treasury", "payroll",
        "cost accounting", "investment analysis", "banking",
    },
    "operations_product": {
        "agile", "scrum", "roadmap", "stakeholder management", "jira",
        "project coordination", "vendor management", "supply chain", "procurement",
        "customer support", "service operations", "business analysis",
        "business systems analysis", "functional requirements", "culinary", "cooking",
        "kitchen", "restaurant", "food safety", "food costing", "inventory", "haccp",
        "waiter", "server", "hospitality", "catering",
    },
    "it_security": {
        "cybersecurity", "networking", "troubleshooting", "system administration",
        "helpdesk", "service desk", "active directory", "windows server",
        "network security", "siem", "incident response",
    },
    "retail_ops": {
        "cash handling", "customer service", "scheduling", "team management",
        "compliance", "inventory management", "leadership", "communication",
        "problem solving", "training", "integrity",
    },
    "sales": {
        "crm", "salesforce", "hubspot", "cold calling", "negotiation",
        "pipeline management", "account management", "b2b sales", "b2c sales",
        "sales forecasting", "territory management", "lead generation",
        "business development", "customer service",
    },
    "admin_ops": {
        "microsoft office", "microsoft word", "microsoft excel", "google workspace",
        "data entry", "records management", "calendar management",
        "travel coordination", "office management", "report writing",
        "minute taking", "correspondence", "receptionist",
    },
    "customer_service": {
        "zendesk", "freshdesk", "live chat", "call center", "complaint handling",
        "after sales", "ticketing system", "voice support", "technical support",
        "chat support", "crm", "customer service",
    },
    "management": {
        "people management", "performance management", "workforce planning",
        "budget management", "operations management", "project management",
        "strategic planning", "stakeholder management", "cross-functional",
        "change management", "p&l management", "kpi management",
    },
    "business_management": {
        "strategic planning", "business development", "stakeholder management",
        "business analysis", "process improvement", "kpi management",
        "vendor management", "contract management", "project management",
        "program management", "consulting", "change management",
    },
}

ROLE_FAMILY_ADJACENCY = {
    "software_backend": {"data_ml", "operations_product", "it_security"},
    "data_ml": {"software_backend", "operations_product"},
    "design_creative": {"marketing_business", "operations_product"},
    "hr_recruiting": {"marketing_business", "operations_product"},
    "marketing_business": {"design_creative", "hr_recruiting", "finance_accounting", "operations_product", "retail_ops"},
    "finance_accounting": {"marketing_business", "operations_product"},
    "operations_product": {
        "software_backend",
        "data_ml",
        "design_creative",
        "hr_recruiting",
        "marketing_business",
        "finance_accounting",
        "it_security",
        "retail_ops",
    },
    "it_security": {"software_backend", "operations_product"},
    "retail_ops": {"operations_product", "marketing_business", "finance_accounting"},
}

_WORD_TO_NUM = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

_NUM_PATTERN = r"(\d+|" + "|".join(_WORD_TO_NUM.keys()) + r")"
_YEAR_PATTERN = r"(?:19\d{2}|20\d{2})"
_MONTH_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)

_MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_EDUCATION_ANCHORS = (
    "bachelor",
    "master",
    "doctoral",
    "doctorate",
    "phd",
    "degree",
    "undergraduate",
    "postgraduate",
    "university",
    "college",
    "school",
    "faculty",
    "coursework",
)

_RESUME_DATE_EXCLUSION_TERMS = {
    "bachelor",
    "master",
    "phd",
    "doctorate",
    "doctoral",
    "degree",
    "graduate",
    "graduated",
    "university",
    "college",
    "school",
    "gpa",
    "coursework",
    "thesis",
}

_RELATED_FIELD_ALLOWANCE_PHRASES = (
    "related field",
    "related discipline",
    "related degree",
    "relevant field",
    "closely related field",
    "similar field",
    "equivalent field",
    "or equivalent",
    "equivalent experience",
    "any field",
)

_GRADUATE_FALSE_POSITIVES = {
    "graduate student",
    "graduate students",
    "graduate school",
    "graduate studies",
    "graduate trainee",
    "graduate trainees",
    "graduate training",
    "graduate program",
    "graduate programme",
    "graduate certificate",
    "training graduate",
}

_RESUME_PARTIAL_EXPERIENCE_TERMS = {
    "intern",
    "internship",
    "trainee",
    "traineeship",
    "apprentice",
    "apprenticeship",
    "fellowship",
    "co-op",
    "co op",
}

_RESUME_ZERO_WEIGHT_EXPERIENCE_TERMS = {
    "academic project",
    "student project",
    "course project",
    "class project",
    "capstone",
    "thesis project",
    "research project",
    "training program",
    "training programme",
    "bootcamp",
    "coursework",
    "practicum",
}

_EXPERIENCE_SECTION_ANCHORS = (
    "work history",
    "professional experience",
    "work experience",
    "employment history",
    "employment",
    "career history",
    "experience",
)

_WORK_HISTORY_CONTEXT_TERMS = {
    "experience",
    "work history",
    "professional experience",
    "employment history",
    "employment",
    "career history",
    "present",
    "current",
    "company",
    "responsible",
    "manager",
    "engineer",
    "developer",
    "analyst",
    "specialist",
    "coordinator",
}

_IMPLICIT_EXPERIENCE_ANCHOR_TERMS = {
    "work history",
    "professional experience",
    "employment history",
    "career history",
    "current company name",
    "company name",
    "continued",
    "responsibility include",
    "responsibilities include",
}

_IMPLICIT_EXPERIENCE_ACTION_TERMS = {
    "managed",
    "supervised",
    "led",
    "developed",
    "implemented",
    "oversaw",
    "coordinated",
    "analyzed",
    "designed",
    "delivered",
    "maintained",
}

_IMPLICIT_EXPERIENCE_QUALITY_TERMS = {
    "extensive",
    "seasoned",
    "progressive",
    "track record",
    "diverse",
    "broad experience",
    "solid background",
}

_NUMERIC_MONTH_YEAR_PATTERN = rf"(?:0?[1-9]|1[0-2])\s*/\s*{_YEAR_PATTERN}"

CURRENT_DATE = date.today()
CURRENT_YEAR = CURRENT_DATE.year
CURRENT_MONTH = CURRENT_DATE.month


def normalize_text(text):
    text = "" if pd.isna(text) else str(text).lower()
    text = text.replace("&", " and ")
    text = text.replace("’", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("'", "")
    text = text.replace(".", " ")
    text = re.sub(r"[/,;|()\\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_field_text(text):
    text = "" if pd.isna(text) else str(text).lower()
    text = text.replace("&", " and ")
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"(?<=[a-z0-9])\.(?=[a-z0-9])", "", text)
    text = text.replace(".", " ")
    text = re.sub(r"'s\b", "s", text)
    text = re.sub(r"[/,;|()\\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_experience_text(text):
    text = "" if pd.isna(text) else str(text).lower()
    text = text.replace("’", "'")
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("\t", " ")
    text = re.sub(r"[|,;]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def raw_segments(text):
    raw = "" if pd.isna(text) else str(text).lower()
    raw = raw.replace("’", "'")
    raw = raw.replace("–", "-").replace("—", "-")
    raw = raw.replace("•", "\n").replace("|", "\n")
    raw = re.sub(r"[ \t]+", " ", raw)

    segments = []
    for block in re.split(r"[\r\n]+", raw):
        block = block.strip()
        if not block:
            continue
        for part in re.split(r"(?<=[.;])\s+", block):
            part = part.strip()
            if part:
                segments.append(part)
    return segments


def _normalize_broken_experience_ranges(text):
    text = normalize_experience_text(text)

    # Repair OCR/cleaning damage like "one two year work experience"
    # into a form that the year extractor can understand.
    text = re.sub(
        rf"\b({_NUM_PATTERN})\s+({_NUM_PATTERN})\s+(?=(?:years?|yrs?)\s+(?:of\s+)?(?:work|working|related|professional)?\s*experience\b)",
        r"\1 to \2 ",
        text,
    )
    text = re.sub(
        rf"\b({_NUM_PATTERN})\s+({_NUM_PATTERN})\s+(?=(?:years?|yrs?)\b[^.\n]{{0,20}}\bexperience\b)",
        r"\1 to \2 ",
        text,
    )
    return text


def experience_segments(text):
    raw = "" if pd.isna(text) else str(text).lower()
    raw = raw.replace("'", "'")
    raw = raw.replace("\u2013", "-").replace("\u2014", "-")
    raw = raw.replace("\u2022", "\n")
    raw = raw.replace("|", "\n")
    raw = raw.replace("*", "\n")

    # Restore boundaries before experience headers and common date ranges.
    raw = re.sub(
        rf"(?<!\n)\b({'|'.join(re.escape(anchor) for anchor in _EXPERIENCE_SECTION_ANCHORS)})\b\s*:?",
        lambda match: f"\n{match.group(1)}: ",
        raw,
    )
    raw = re.sub(
        rf"(?<=[a-z])(?={_NUMERIC_MONTH_YEAR_PATTERN}\s*(?:to|-)\s*(?:{_NUMERIC_MONTH_YEAR_PATTERN}|present|current|now))",
        "\n",
        raw,
    )
    raw = re.sub(
        rf"(?<=[a-z])(?={_MONTH_PATTERN}\s+{_YEAR_PATTERN}\s*(?:to|-)\s*(?:{_MONTH_PATTERN}\s+{_YEAR_PATTERN}|present|current|now))",
        "\n",
        raw,
    )
    raw = re.sub(
        rf"(?<=[a-z])(?={_YEAR_PATTERN}\s*(?:to|-)\s*(?:{_YEAR_PATTERN}|present|current|now))",
        "\n",
        raw,
    )
    raw = re.sub(r"[ \t]+", " ", raw)

    segments = []
    for block in re.split(r"[\r\n]+", raw):
        block = block.strip()
        if not block:
            continue
        for part in re.split(r"(?<=[.;])\s+", block):
            part = part.strip()
            if part:
                segments.append(part)
    return segments


def contains_term(text, term):
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def _sanitize_for_degree(text):
    for phrase in _MS_STOPWORDS:
        text = text.replace(phrase, " ")
    for phrase in _BA_STOPWORDS:
        text = text.replace(phrase, " ")
    return text


def _to_int(value):
    normalized = str(value).strip().lower()
    if normalized in _WORD_TO_NUM:
        return _WORD_TO_NUM[normalized]
    return int(normalized) if normalized.isdigit() else 0


def _looks_like_education_segment(segment):
    normalized = normalize_text(segment)
    if not normalized:
        return False

    if any(anchor in normalized for anchor in _EDUCATION_ANCHORS):
        return True

    if _has_strong_graduate_context(normalized):
        return True

    return re.search(
        r"(?<!\w)(bs|b s|bsc|b sc|ba|b a|ms|m s|msc|m sc|ma|m a|mba|phd|ph d)(?!\w)",
        normalized,
    ) is not None


_BARE_DEGREE_ABBREV_RE = re.compile(
    r"^(?:bs|b\.?s\.?|bsc|b\.?sc\.?|ba|b\.?a\.?|ms|m\.?s\.?|msc|m\.?sc\.?|ma|m\.?a\.?|mba|phd|ph\.?d\.?)\s*$",
    re.IGNORECASE,
)


def extract_education_context(text, source="resume"):
    segments = raw_segments(text)
    selected = []
    skip_next = False

    for segment in segments:
        if skip_next:
            selected.append(normalize_field_text(segment))
            skip_next = False
            continue

        if _looks_like_education_segment(segment):
            normalized_segment = normalize_field_text(segment).strip()
            selected.append(normalized_segment)
            if _BARE_DEGREE_ABBREV_RE.match(normalized_segment):
                skip_next = True

    if selected:
        return " ".join(selected)

    if source == "job":
        normalized = normalize_field_text(text)
        if any(phrase in normalized for phrase in ("degree in", "related field", "equivalent field", "or equivalent")):
            return normalized
        if _has_strong_graduate_context(normalize_text(text)):
            return normalized

    return ""


def _has_strong_graduate_context(text):
    text = normalize_text(text)
    if not text:
        return False

    if any(phrase in text for phrase in _GRADUATE_FALSE_POSITIVES):
        return False

    fields_present = bool(extract_fields(text))

    if re.search(r"(?<!\w)(college|university)\s+graduate(?!\w)", text):
        return True

    if re.search(r"(?<!\w)(degree in|degree holder|college degree|university degree)(?!\w)", text):
        return fields_present or bool(re.search(r"(?<!\w)(college|university)(?!\w)", text))

    if re.search(r"(?<!\w)(graduate|graduated)\s+(?:of|with|in)\b", text):
        return fields_present or "degree" in text

    if re.search(r"(?<!\w)graduated\s+from\s+(?:a\s+)?(?:college|university)\b", text):
        return fields_present or "degree" in text

    return False


def extract_degree_level(text):
    text = normalize_text(text)
    text = _sanitize_for_degree(text)

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

    if _has_strong_graduate_context(text):
        return "bachelor"

    return "none"


_DEGREE_PHRASE_RE = re.compile(
    r"(?:bachelor(?:s|'s)?(?:\s+of(?:\s+science)?(?:\s+in)?)?|master(?:s|'s)?(?:\s+of(?:\s+science)?(?:\s+in)?)?|bs|bsc|ba|ms|msc|ma|mba|phd|ph\s*d|doctorate(?:\s+in)?|bachelor|master)\s*(?:in|of|:)?\s*",
    re.IGNORECASE,
)


def _extract_field_context_windows(raw_text):
    windows = []
    raw_text = "" if pd.isna(raw_text) else str(raw_text)

    for match in _DEGREE_PHRASE_RE.finditer(raw_text):
        tail = raw_text[match.end() : match.end() + 80]
        tail = re.split(r"[\n;,\|]|(?<=[a-z])\.\s", tail)[0]
        windows.append(tail.strip())

    return windows


def extract_fields(text):
    normalized_text = normalize_field_text(text)
    found = set()

    for canonical, aliases in FIELD_ALIASES.items():
        if any(contains_term(normalized_text, alias) for alias in aliases):
            found.add(canonical)

    for window in _extract_field_context_windows(text):
        normalized_window = normalize_field_text(window)
        for canonical, aliases in FIELD_ALIASES.items():
            if canonical not in found and any(contains_term(normalized_window, alias) for alias in aliases):
                found.add(canonical)
    return found


def _field_match_type(jd_fields, resume_fields):
    if not jd_fields or not resume_fields:
        return "none"

    if jd_fields.intersection(resume_fields):
        return "exact"

    for jd_field in jd_fields:
        aligned_fields = CLEARLY_ALIGNED_FIELDS.get(jd_field, set())
        if resume_fields.intersection(aligned_fields):
            return "aligned"

    for jd_field in jd_fields:
        valid_fields = RELATED_FIELDS.get(jd_field, {jd_field})
        if resume_fields.intersection(valid_fields):
            return "related"

    return "none"


def education_match_details(resume_text, job_description):
    jd_context = extract_education_context(job_description, source="job")
    resume_context = extract_education_context(resume_text, source="resume")

    jd_for_level = jd_context or job_description
    resume_for_level = resume_context or resume_text
    jd_for_fields = jd_context or job_description
    resume_for_fields = resume_context or resume_text

    required_level = extract_degree_level(jd_for_level)
    candidate_level = extract_degree_level(resume_for_level)
    jd_fields = extract_fields(jd_for_fields)
    resume_fields = extract_fields(resume_for_fields)

    normalized_jd_context = normalize_field_text(jd_context or job_description)
    related_ok = any(phrase in normalized_jd_context for phrase in _RELATED_FIELD_ALLOWANCE_PHRASES)

    req_level_num = DEGREE_LEVELS[required_level]
    cand_level_num = DEGREE_LEVELS[candidate_level]

    score = 0
    match_type = "none"

    if req_level_num == 0:
        return {
            "jd_context": jd_context,
            "resume_context": resume_context,
            "required_level": required_level,
            "candidate_level": candidate_level,
            "jd_fields": jd_fields,
            "resume_fields": resume_fields,
            "match_type": match_type,
            "related_phrase_ok": related_ok,
            "score": score,
        }

    if cand_level_num == 0 or cand_level_num < req_level_num:
        return {
            "jd_context": jd_context,
            "resume_context": resume_context,
            "required_level": required_level,
            "candidate_level": candidate_level,
            "jd_fields": jd_fields,
            "resume_fields": resume_fields,
            "match_type": match_type,
            "related_phrase_ok": related_ok,
            "score": score,
        }

    if not jd_fields:
        score = 1
        return {
            "jd_context": jd_context,
            "resume_context": resume_context,
            "required_level": required_level,
            "candidate_level": candidate_level,
            "jd_fields": jd_fields,
            "resume_fields": resume_fields,
            "match_type": match_type,
            "related_phrase_ok": related_ok,
            "score": score,
        }

    match_type = _field_match_type(jd_fields, resume_fields)

    if match_type in {"exact", "aligned"}:
        score = 2
    elif match_type == "related":
        if related_ok or cand_level_num > req_level_num:
            score = 1

    return {
        "jd_context": jd_context,
        "resume_context": resume_context,
        "required_level": required_level,
        "candidate_level": candidate_level,
        "jd_fields": jd_fields,
        "resume_fields": resume_fields,
        "match_type": match_type,
        "related_phrase_ok": related_ok,
        "score": score,
    }


def education_match_score(resume_text, job_description, debug=False):
    return education_match_details(resume_text, job_description)["score"]


def _month_to_int(token):
    if not token:
        return None
    return _MONTH_MAP.get(token.strip().lower())


def _interval_to_months(interval):
    start_year, start_month, end_year, end_month = interval
    return (end_year - start_year) * 12 + (end_month - start_month) + 1


def _merge_intervals(intervals):
    if not intervals:
        return []

    month_intervals = []
    for start_year, start_month, end_year, end_month in intervals:
        start_index = start_year * 12 + start_month
        end_index = end_year * 12 + end_month
        if end_index < start_index:
            continue
        month_intervals.append((start_index, end_index))

    if not month_intervals:
        return []

    month_intervals.sort()
    merged = [list(month_intervals[0])]

    for start_index, end_index in month_intervals[1:]:
        if start_index <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end_index)
        else:
            merged.append([start_index, end_index])

    return merged


def _merged_intervals_to_years(intervals):
    merged = _merge_intervals(intervals)
    total_months = sum(end_index - start_index + 1 for start_index, end_index in merged)
    return total_months // 12


def _build_interval(start_year, start_month, end_year, end_month):
    if not (1950 <= start_year <= CURRENT_YEAR + 1):
        return None
    if not (1950 <= end_year <= CURRENT_YEAR + 1):
        return None
    if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
        return None
    if (end_year, end_month) < (start_year, start_month):
        return None
    if _interval_to_months((start_year, start_month, end_year, end_month)) > 12 * 45:
        return None
    return (start_year, start_month, end_year, end_month)


def _extract_date_intervals_from_segment(segment):
    segment = normalize_experience_text(segment)
    intervals = []

    month_year_range = re.finditer(
        rf"{_MONTH_PATTERN}\s+{_YEAR_PATTERN}\s*(?:to|-)\s*(?:{_MONTH_PATTERN}\s+{_YEAR_PATTERN}|present|current|now)",
        segment,
    )
    for match in month_year_range:
        full = match.group(0)
        parts = re.match(
            rf"({_MONTH_PATTERN})\s+({_YEAR_PATTERN})\s*(?:to|-)\s*(?:(present|current|now)|({_MONTH_PATTERN})\s+({_YEAR_PATTERN}))",
            full,
        )
        if not parts:
            continue

        start_month = _month_to_int(parts.group(1))
        start_year = int(parts.group(2))

        if parts.group(3):
            end_month = CURRENT_MONTH
            end_year = CURRENT_YEAR
        else:
            end_month = _month_to_int(parts.group(4))
            end_year = int(parts.group(5))

        interval = _build_interval(start_year, start_month, end_year, end_month)
        if interval:
            intervals.append(interval)

    # Numeric MM/YYYY spans  e.g. "01/2022 - 03/2024" or "09/2020 to present"
    numeric_month_year_range = re.finditer(
        rf"{_NUMERIC_MONTH_YEAR_PATTERN}\s*(?:to|-)\s*(?:{_NUMERIC_MONTH_YEAR_PATTERN}|present|current|now)",
        segment,
    )
    for match in numeric_month_year_range:
        full = match.group(0)
        parts = re.match(
            rf"((?:0?[1-9]|1[0-2]))\s*/\s*({_YEAR_PATTERN})\s*(?:to|-)\s*(?:(present|current|now)|((?:0?[1-9]|1[0-2]))\s*/\s*({_YEAR_PATTERN}))",
            full,
        )
        if not parts:
            continue

        start_month = int(parts.group(1))
        start_year = int(parts.group(2))

        if parts.group(3):
            end_month = CURRENT_MONTH
            end_year = CURRENT_YEAR
        else:
            end_month = int(parts.group(4))
            end_year = int(parts.group(5))

        interval = _build_interval(start_year, start_month, end_year, end_month)
        if interval:
            intervals.append(interval)

    year_range = re.finditer(
        rf"(?<!\d){_YEAR_PATTERN}\s*(?:to|-)\s*(?:{_YEAR_PATTERN}|present|current|now)(?!\d)",
        segment,
    )
    for match in year_range:
        full = match.group(0)
        parts = re.match(
            rf"({_YEAR_PATTERN})\s*(?:to|-)\s*(({_YEAR_PATTERN})|present|current|now)",
            full,
        )
        if not parts:
            continue

        start_year = int(parts.group(1))
        if parts.group(2) in {"present", "current", "now"}:
            end_year = CURRENT_YEAR
            end_month = CURRENT_MONTH
        else:
            end_year = int(parts.group(3))
            end_month = 1

        interval = _build_interval(start_year, 1, end_year, end_month)
        if interval:
            intervals.append(interval)

    since_year = re.finditer(rf"since\s+({_YEAR_PATTERN})", segment)
    for match in since_year:
        start_year = int(match.group(1))
        interval = _build_interval(start_year, 1, CURRENT_YEAR, CURRENT_MONTH)
        if interval:
            intervals.append(interval)

    since_month_year = re.finditer(rf"since\s+({_MONTH_PATTERN})\s+({_YEAR_PATTERN})", segment)
    for match in since_month_year:
        start_month = _month_to_int(match.group(1))
        start_year = int(match.group(2))
        interval = _build_interval(start_year, start_month, CURRENT_YEAR, CURRENT_MONTH)
        if interval:
            intervals.append(interval)

    # Numeric month/year since e.g. "since 03/2021"
    since_numeric_month_year = re.finditer(rf"since\s+((?:0?[1-9]|1[0-2]))\s*/\s*({_YEAR_PATTERN})", segment)
    for match in since_numeric_month_year:
        start_month = int(match.group(1))
        start_year = int(match.group(2))
        interval = _build_interval(start_year, start_month, CURRENT_YEAR, CURRENT_MONTH)
        if interval:
            intervals.append(interval)

    return intervals


def _segment_context_window(segments, index, lookback=1):
    start = max(0, index - lookback)
    return " ".join(segments[start : index + 1])


def _has_experience_duration_signal(text):
    normalized = normalize_experience_text(text)
    if not normalized:
        return False

    return bool(
        _extract_date_intervals_from_segment(normalized)
        or re.search(rf"\b{_NUM_PATTERN}\s*(?:years?|yrs?|months?|mos?)\b", normalized)
    )


def _experience_segment_weight(segment, context=None):
    normalized_segment = normalize_text(segment)
    normalized_context = normalize_text(context or segment)
    has_work_context = any(term in normalized_context for term in _WORK_HISTORY_CONTEXT_TERMS)
    has_duration_signal = _has_experience_duration_signal(context or segment)

    if any(term in normalized_segment for term in _RESUME_DATE_EXCLUSION_TERMS):
        if not (has_work_context or has_duration_signal):
            return 0.0
        return 0.5

    if any(term in normalized_context for term in _RESUME_ZERO_WEIGHT_EXPERIENCE_TERMS):
        return 0.0

    if any(term in normalized_context for term in _RESUME_PARTIAL_EXPERIENCE_TERMS):
        return 0.5

    return 1.0


def _weighted_intervals_to_years(weighted_intervals):
    month_weights = {}

    for interval, weight in weighted_intervals:
        if weight <= 0:
            continue

        start_year, start_month, end_year, end_month = interval
        start_index = start_year * 12 + start_month
        end_index = end_year * 12 + end_month

        for month_index in range(start_index, end_index + 1):
            month_weights[month_index] = max(month_weights.get(month_index, 0.0), weight)

    total_weighted_months = sum(month_weights.values())
    return round(total_weighted_months / 12, 1)


def _extract_explicit_year_values(text, patterns, range_mode="single"):
    text = normalize_experience_text(text)
    values = []

    for pattern in patterns:
        for match in re.findall(pattern, text):
            if isinstance(match, tuple):
                numbers = [_to_int(value) for value in match if value]
                valid = [number for number in numbers if 0 < number <= 45]
                if not valid:
                    continue
                if range_mode == "min":
                    values.append(min(valid))
                elif range_mode == "max":
                    values.append(max(valid))
            else:
                number = _to_int(match)
                if 0 < number <= 45:
                    values.append(number)

    return values


def extract_required_years(job_description):
    normalized_job_description = _normalize_broken_experience_ranges(job_description)

    range_patterns = [
        _NUM_PATTERN + r"\s*(?:-|to)\s*" + _NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"(?:at\s+least|least|minimum(?:\s+of)?|minimum|required|min(?:imum)?(?:\s+of)?)\s+"
        + _NUM_PATTERN
        + r"\s+to\s+"
        + _NUM_PATTERN
        + r"\s*(?:years?|yrs?)",
    ]
    minimum_patterns = [
        _NUM_PATTERN + r"\+\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(?:at\s+least|least|minimum(?:\s+of)?|minimum|required|min(?:imum)?(?:\s+of)?)\s+"
        + _NUM_PATTERN
        + r"\s*(?:years?|yrs?)\s*(?:of\s+)?(?:work|working|related|professional)?\s*experience?",
        _NUM_PATTERN + r"\s*(?:years?|yrs?)\s+(?:minimum|min(?:imum)?|required)",
        r"required\s+(?:experience\s+(?:of\s+)?)?"
        + _NUM_PATTERN
        + r"\s*(?:years?|yrs?)",
        r"minimum\s+(?:experience\s+(?:of\s+)?)?"
        + _NUM_PATTERN
        + r"\s*(?:years?|yrs?)",
    ]
    generic_patterns = [
        _NUM_PATTERN + r"\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"with\s+" + _NUM_PATTERN + r"\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"experience\s*[:\-]?\s*" + _NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"(?:work|working|professional|related)\s+experience\s*[:\-]?\s*" + _NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"worked\s+for\s+" + _NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"professional\s+experience\s+(?:of\s+)?"
        + _NUM_PATTERN
        + r"\s*(?:years?|yrs?)",
        r"(?:over|more\s+than)\s+" + _NUM_PATTERN + r"\s*(?:years?|yrs?)",
    ]

    range_values = _extract_explicit_year_values(normalized_job_description, range_patterns, range_mode="min")
    scrubbed_text = normalize_experience_text(normalized_job_description)
    for pattern in range_patterns:
        scrubbed_text = re.sub(pattern, " ", scrubbed_text)
    minimum_values = _extract_explicit_year_values(scrubbed_text, minimum_patterns, range_mode="single")
    generic_values = _extract_explicit_year_values(scrubbed_text, generic_patterns, range_mode="single")

    if range_values or minimum_values:
        return min(range_values + minimum_values)

    if generic_values:
        return max(generic_values)

    # ── Month-only JD requirements (e.g. "at least 6 months of management experience") ──
    # These are converted to fractional years so jd_has_requirement fires correctly.
    month_req_patterns = [
        r"(?:at\s+least|minimum(?:\s+of)?|least|min(?:imum)?)\s+"
        + _NUM_PATTERN
        + r"\s*(?:months?|mos?)\s+(?:of\s+)?(?:\w+\s+)*?experience",
        _NUM_PATTERN + r"\s*(?:months?|mos?)\s+(?:of\s+)?experience",
        r"experience\s*[:\-]?\s*" + _NUM_PATTERN + r"\s*(?:months?|mos?)",
    ]
    month_values_raw = _extract_explicit_year_values(
        normalize_experience_text(normalized_job_description),
        month_req_patterns,
        range_mode="single",
    )
    if month_values_raw:
        # Convert months → fractional years (e.g. 6 months → 0.5)
        return round(min(month_values_raw) / 12, 2)

    return 0


def _extract_explicit_duration_years(text):
    """Extract year-equivalents from month-based or mixed year+month durations."""
    text = normalize_experience_text(text)
    values = []

    mixed_duration_patterns = [
        rf"{_NUM_PATTERN}\s*(?:years?|yrs?)\s*(?:and\s*)?{_NUM_PATTERN}\s*(?:months?|mos?)",
        rf"experience[^.\n]{{0,40}}?{_NUM_PATTERN}\s*(?:years?|yrs?)\s*(?:and\s*)?{_NUM_PATTERN}\s*(?:months?|mos?)",
        rf"{_NUM_PATTERN}\s*(?:years?|yrs?)\s*(?:and\s*)?{_NUM_PATTERN}\s*(?:months?|mos?)\b[^.\n]{{0,40}}?experience",
    ]
    for pattern in mixed_duration_patterns:
        for years_value, months_value in re.findall(pattern, text):
            years_num = _to_int(years_value)
            months_num = _to_int(months_value)
            if 0 <= years_num <= 45 and 0 < months_num <= 120:
                values.append(round(years_num + (months_num / 12), 1))

    month_only_patterns = [
        rf"{_NUM_PATTERN}\s*(?:months?|mos?)\s+(?:of\s+)?experience",
        rf"experience[^.\n]{{0,40}}?{_NUM_PATTERN}\s*(?:months?|mos?)",
        rf"{_NUM_PATTERN}\s*(?:months?|mos?)\b[^.\n]{{0,40}}?experience",
    ]
    for pattern in month_only_patterns:
        for match in re.findall(pattern, text):
            month_value = match[0] if isinstance(match, tuple) else match
            months_num = _to_int(month_value)
            if 0 < months_num <= 540:
                values.append(round(months_num / 12, 1))

    return values


def _estimate_implicit_resume_years(resume_text):
    """Conservative fallback for heavily-cleaned resumes with no explicit dates."""
    normalized = normalize_experience_text(resume_text)
    if not normalized or len(normalized) < 700:
        return 0.0

    if _has_experience_duration_signal(normalized):
        return 0.0

    anchor_hits = sum(1 for term in _IMPLICIT_EXPERIENCE_ANCHOR_TERMS if contains_term(normalized, term))
    action_hits = sum(1 for term in _IMPLICIT_EXPERIENCE_ACTION_TERMS if contains_term(normalized, term))
    quality_hits = sum(1 for term in _IMPLICIT_EXPERIENCE_QUALITY_TERMS if contains_term(normalized, term))
    role_hits = sum(
        1
        for term in {"manager", "engineer", "developer", "analyst", "specialist", "accountant", "coordinator"}
        if contains_term(normalized, term)
    )
    experience_mentions = len(re.findall(r"\bexperience\b", normalized))

    if anchor_hits >= 2 and (action_hits >= 2 or quality_hits >= 1 or role_hits >= 2 or experience_mentions >= 3):
        return 2.0

    if anchor_hits >= 1 and (action_hits >= 2 or quality_hits >= 1 or (role_hits >= 1 and experience_mentions >= 2)):
        return 1.0

    return 0.0


def extract_resume_years(resume_text):
    explicit_patterns = [
        _NUM_PATTERN + r"\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"(?:at\s+least|over|more\s+than|with)\s+"
        + _NUM_PATTERN
        + r"\s*(?:years?|yrs?)\s*(?:of\s+experience)?",
        r"experience\s*[:\-]?\s*" + _NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"(?:work|working|professional|related)\s+experience\s*[:\-]?\s*" + _NUM_PATTERN + r"\s*(?:years?|yrs?)",
        rf"experience[^.\n]{{0,40}}?{_NUM_PATTERN}\s*(?:years?|yrs?)",
        _NUM_PATTERN + r"\s*(?:years?|yrs?)\b[^.\n]{0,40}?experience",
        r"worked\s+for\s+" + _NUM_PATTERN + r"\s*(?:years?|yrs?)",
        r"professional\s+experience\s+(?:of\s+)?"
        + _NUM_PATTERN
        + r"\s*(?:years?|yrs?)",
        _NUM_PATTERN + r"\s*(?:years?|yrs?)\s+(?:in|with|of)",
    ]

    explicit_values = []
    weighted_intervals = []
    segments = experience_segments(resume_text)

    for index, segment in enumerate(segments):
        context = _segment_context_window(segments, index)
        weight = _experience_segment_weight(segment, context=context)
        if weight <= 0:
            continue

        segment_values = _extract_explicit_year_values(segment, explicit_patterns, range_mode="max")
        segment_values.extend(_extract_explicit_duration_years(segment))
        explicit_values.extend(value * weight for value in segment_values)

        for interval in _extract_date_intervals_from_segment(segment):
            weighted_intervals.append((interval, weight))

    interval_years = _weighted_intervals_to_years(weighted_intervals)
    explicit_years = max(explicit_values) if explicit_values else 0

    if explicit_years or interval_years:
        return max(explicit_years, interval_years)

    return _estimate_implicit_resume_years(resume_text)


def experience_match_score(resume_text, job_description):
    required_years = extract_required_years(job_description)
    candidate_years = extract_resume_years(resume_text)

    if required_years == 0:
        return 0

    if candidate_years >= required_years + 2:
        return 3
    if candidate_years >= required_years:
        return 2
    if candidate_years >= max(1, required_years - 1):
        return 1
    return 0


def extract_skills(text):
    text = normalize_text(text)
    found = set()

    for canonical, aliases in SKILL_ALIASES.items():
        if any(contains_term(text, alias) for alias in aliases):
            found.add(canonical)

    return found


def extract_role_families(text):
    normalized = normalize_text(text)
    found = set()

    if not normalized:
        return found

    found_domains = extract_domains(normalized)
    found_skills = extract_skills(normalized)

    for family, domains in ROLE_FAMILY_DOMAIN_MAP.items():
        if found_domains.intersection(domains):
            found.add(family)
            continue

        keywords = ROLE_FAMILY_KEYWORDS.get(family, set())
        if any(contains_term(normalized, keyword) for keyword in keywords):
            found.add(family)
            continue

        skill_hints = ROLE_FAMILY_SKILL_HINTS.get(family, set())
        if found_skills.intersection(skill_hints):
            found.add(family)

    return found


def role_family_relation(resume_text, job_description):
    resume_families = extract_role_families(resume_text)
    jd_families = extract_role_families(job_description)

    if not resume_families or not jd_families:
        return resume_families, jd_families, "unknown"

    if resume_families.intersection(jd_families):
        return resume_families, jd_families, "same"

    for jd_family in jd_families:
        adjacent = ROLE_FAMILY_ADJACENCY.get(jd_family, set())
        if resume_families.intersection(adjacent):
            return resume_families, jd_families, "adjacent"

    return resume_families, jd_families, "unrelated"


def skills_match_score(resume_text, job_description, tfidf_sim=0.0, sbert_sim=0.0):
    jd_skills = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)
 
    has_semantic_signal = tfidf_sim > 0 or sbert_sim > 0
 
    if not jd_skills:
        # Only give benefit of the doubt if the JD looks like real human text.
        # A garbage/random string should return 0, not 1.
        jd_domains = extract_domains(job_description)
        jd_families = extract_role_families(job_description)
        if not jd_domains and not jd_families:
            return 0  # JD has no recognizable content at all
        return 1  # Real JD, just no explicit skills listed
 
    overlap = len(jd_skills.intersection(resume_skills))
    ratio = overlap / max(len(jd_skills), 1)
 
    if ratio >= 0.60 or overlap >= 5:
        return 2
    if ratio >= 0.25 or overlap >= 2:
        return 1
 
    shared_skills = jd_skills.intersection(resume_skills)
    jd_domains = extract_domains(job_description)
    resume_domains = extract_domains(resume_text)
    technical_bridge = bool(shared_skills.intersection(_TECHNICAL_BRIDGE_SKILLS))
    related_technical_context = bool(jd_domains.intersection(_TECHNICAL_DOMAINS)) and bool(
        resume_domains.intersection(_TECHNICAL_DOMAINS)
    )
    technical_foundation_skills = {
        "python", "sql", "numpy", "pandas", "statistics",
        "rest api", "docker", "kubernetes", "fastapi", "flask", "postgresql",
    }
    advanced_technical_jd_skills = {
        "machine learning", "scikit-learn", "xgboost", "nlp",
        "deep learning", "feature engineering", "mlops", "data science",
    }
    resume_technical_foundation = bool(resume_skills.intersection(technical_foundation_skills))
    jd_advanced_technical = bool(jd_skills.intersection(advanced_technical_jd_skills))
    resume_families, jd_families, family_relation = role_family_relation(resume_text, job_description)
    family_skill_bridge = False
    for family in jd_families:
        family_skill_bridge = family_skill_bridge or bool(
            resume_skills.intersection(ROLE_FAMILY_SKILL_HINTS.get(family, set()))
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

def extract_domains(text):
    text = normalize_text(text)
    found = set()

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(contains_term(text, keyword) for keyword in keywords):
            found.add(domain)

    if "data_analytics" in found:
        strong_match = any(contains_term(text, term) for term in _DATA_ANALYTICS_STRONG_TERMS)
        weak_hits = sum(1 for term in _DATA_ANALYTICS_WEAK_TERMS if contains_term(text, term))
        marketing_context = any(contains_term(text, term) for term in _MARKETING_CONTEXT_TERMS)

        if not strong_match and (marketing_context or weak_hits < 2):
            found.discard("data_analytics")

    if "hr_recruitment" in found:
        strong_hr = any(contains_term(text, term) for term in _HR_RECRUITMENT_STRONG_TERMS)
        weak_hr_hits = sum(1 for term in _HR_RECRUITMENT_WEAK_TERMS if contains_term(text, term))

        if not strong_hr and weak_hr_hits < 2:
            found.discard("hr_recruitment")

    return found


def domain_alignment_score(resume_text, job_description, tfidf_sim=0.0, sbert_sim=0.0):
    jd_domains = extract_domains(job_description)
    resume_domains = extract_domains(resume_text)
    resume_families, jd_families, family_relation = role_family_relation(resume_text, job_description)

    has_semantic_signal = tfidf_sim > 0 or sbert_sim > 0

    if not jd_domains:
        return 1 if family_relation == "same" else 0

    if jd_domains.intersection(resume_domains):
        return 1

    skills_score = skills_match_score(resume_text, job_description, tfidf_sim, sbert_sim)

    if family_relation == "same":
        return 1 if has_semantic_signal else 0

    if family_relation == "adjacent" and skills_score >= 1:
        return 1 if has_semantic_signal else 0

    for jd_domain in jd_domains:
        valid_domains = RELATED_DOMAINS.get(jd_domain, {jd_domain}) - {jd_domain}
        if resume_domains.intersection(valid_domains) and skills_score >= 1:
            return 1 if has_semantic_signal else 0

    return 0


def build_debug_snapshot(resume_text, job_description):
    education_details = education_match_details(resume_text, job_description)

    return {
        "required_years": extract_required_years(job_description),
        "candidate_years": extract_resume_years(resume_text),
        "jd_degree_level": education_details["required_level"],
        "resume_degree_level": education_details["candidate_level"],
        "jd_fields": sorted(education_details["jd_fields"]),
        "resume_fields": sorted(education_details["resume_fields"]),
        "education_match_type": education_details["match_type"],
        "education_related_phrase_ok": education_details["related_phrase_ok"],
        "education_score": education_details["score"],
        "jd_skills": sorted(extract_skills(job_description)),
        "resume_skills": sorted(extract_skills(resume_text)),
        "jd_domains": sorted(extract_domains(job_description)),
        "resume_domains": sorted(extract_domains(resume_text)),
        "jd_role_families": sorted(extract_role_families(job_description)),
        "resume_role_families": sorted(extract_role_families(resume_text)),
    }
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ── NLP patch: shadows the extraction/scoring functions defined above ──
try:
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
    print("[ml_service] NLP patch loaded successfully.")
except ImportError as e:
    print(f"[ml_service] NLP patch not found, using original extractors. ({e})")

def print_debug_samples(df, limit=3):
    print("\n--- DEBUG SAMPLE INSPECTION ---")

    for sample_index, row in enumerate(df.head(limit).itertuples(index=False), start=1):
        job_description = getattr(row, "job_description_text", getattr(row, "job_description", ""))
        snapshot = build_debug_snapshot(row.resume_text, job_description)
        scores = calculate_strict_logic(row.resume_text, job_description)

        print(f"\nSample #{sample_index}")
        print(f"Required Years: {snapshot['required_years']} | Candidate Years: {snapshot['candidate_years']}")
        print(
            "JD Degree/Fields: "
            f"{snapshot['jd_degree_level']} / {snapshot['jd_fields']}"
        )
        print(
            "Resume Degree/Fields: "
            f"{snapshot['resume_degree_level']} / {snapshot['resume_fields']}"
        )
        print(
            "Education Match: "
            f"type={snapshot['education_match_type']} "
            f"related_phrase_ok={snapshot['education_related_phrase_ok']} "
            f"score={snapshot['education_score']}"
        )
        print(f"JD Skills: {snapshot['jd_skills'][:12]}")
        print(f"Resume Skills: {snapshot['resume_skills'][:12]}")
        print(f"JD Domains: {snapshot['jd_domains']}")
        print(f"Resume Domains: {snapshot['resume_domains']}")
        print(f"Scores -> Skills: {scores[0]}, Exp: {scores[1]}, Edu: {scores[2]}, Domain: {scores[3]}")

    print("\n-------------------------------\n")
    

def calculate_strict_logic(resume_text, job_description, tfidf_sim=0.0, sbert_sim=0.0):
    """
    Deterministic recruiter-style scoring for the 4 hard-logic columns.
    tfidf_sim and sbert_sim gate family-based fallback scoring in skills and domain.
    """
    edu_score = education_match_score(resume_text, job_description, tfidf_sim, sbert_sim)
    exp_score = experience_match_score(resume_text, job_description)
    skills_score = skills_match_score(resume_text, job_description, tfidf_sim, sbert_sim)
    domain_score = domain_alignment_score(resume_text, job_description, tfidf_sim, sbert_sim)

    jd_has_target_signal = bool(extract_skills(job_description) or extract_domains(job_description))

    if jd_has_target_signal and skills_score == 0 and domain_score == 0:
        exp_score = 0
        edu_score = 0

    return skills_score, exp_score, edu_score, domain_score

def build_feature_vector(
    resume_text: str,
    job_description: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Constructs the 6-dimensional feature array using strict logic scoring.

    Returns:
        (features, resume_emb, job_emb)
          features   – shape (1, 6) array ready for XGBoost
          resume_emb – 384-dim SBERT embedding of the resume
          job_emb    – 384-dim SBERT embedding of the job description
    """
    # --- 1. Calculate Mathematical Similarities First ---
    resume_emb = sbert.encode([resume_text])[0]
    job_emb    = sbert.encode([job_description])[0]

    resume_tfidf = vectorizer.transform([resume_text])
    job_tfidf    = vectorizer.transform([job_description])

    tfidf_cos = float(cosine_similarity(resume_tfidf, job_tfidf)[0][0])
    sbert_cos = float(cosine_similarity(resume_emb.reshape(1, -1), job_emb.reshape(1, -1))[0][0])

    # --- 2. Calculate the Hard Logic based on text and math ---
    skills_val, exp_val, edu_val, domain_val = calculate_strict_logic(
        resume_text, job_description, tfidf_cos, sbert_cos
    )

    snapshot = build_debug_snapshot(resume_text, job_description)

    print(f"\n--- DEBUG PIPELINE ---")
    print(f"Required Years: {snapshot['required_years']} | Candidate Years: {snapshot['candidate_years']}")
    print(f"JD Degree/Fields: {snapshot['jd_degree_level']} / {snapshot['jd_fields']}")
    print(f"Resume Degree/Fields: {snapshot['resume_degree_level']} / {snapshot['resume_fields']}")
    print(f"JD Skills: {snapshot['jd_skills'][:12]}")
    print(f"Resume Skills: {snapshot['resume_skills'][:12]}")
    print(f"JD Domains: {snapshot['jd_domains']}")
    print(f"Resume Domains: {snapshot['resume_domains']}")
    print(f"TF-IDF: {tfidf_cos:.4f} | SBERT: {sbert_cos:.4f}")
    print(f"Logic Scored -> Skills: {skills_val}, Exp: {exp_val}, Edu: {edu_val}, Domain: {domain_val}")
    print(f"----------------------\n")

    # --- 3. Concatenate → (6,) ---
    # MUST MATCH TRAINING DATASET COLUMN ORDER:
    # [TF-IDF, SBERT, Skills, Exp, Edu, Domain]
    features = np.array([
        tfidf_cos,
        sbert_cos,
        skills_val,
        exp_val,
        edu_val,
        domain_val
    ])

    return features.reshape(1, -1), resume_emb, job_emb

def predict_resume_tier(resume_text: str, job_description: str) -> tuple[float, str]:
    """
    Scores a resume against a job description.

    Returns:
        (probability_score, gyr_tier)

    This is the *legacy* signature kept for backward compatibility.
    New code should call predict_resume_tier_with_embedding() to also
    receive the SBERT embedding for storage in the vector DB.
    """
    prob_score, tier, _ = predict_resume_tier_with_embedding(resume_text, job_description)
    return prob_score, tier


def predict_resume_tier_with_embedding(
    resume_text: str,
    job_description: str,
) -> tuple[float, str, list[float]]:
    """
    Scores a resume against a job description AND returns the SBERT embedding.

    Returns:
        (probability_score, gyr_tier, resume_embedding)
          probability_score – float in [0, 1]; XGBoost "hire" probability
          gyr_tier          – 'Green' | 'Yellow' | 'Red'
          resume_embedding  – list[float] of length 384 (SBERT all-MiniLM-L6-v2)
                              for storing in the pgvector `embedding` column.
                              Returns an empty list on error/fallback.
    """
    _EMPTY_EMB: list[float] = []

    if not models_loaded:
        print("[ml_service] Models not loaded, returning fallback Red.")
        return 0.0, "Red", _EMPTY_EMB

    if not resume_text.strip():
        print("[ml_service] Empty resume text, returning fallback Red.")
        return 0.0, "Red", _EMPTY_EMB

    effective_job = job_description.strip() if job_description and job_description.strip() else "job position"

    try:
        feature_vec, resume_emb, _ = build_feature_vector(resume_text, effective_job)

        probabilities = classifier.predict_proba(feature_vec)
        prob_score = float(probabilities[0][1])

        # ── Post-model penalty for stuffed/low-substance resumes ──────────────────
        # XGBoost was trained before stuffing detection existed, so high TF-IDF/SBERT
        # from keyword spam still inflates its output. We apply a rule-based penalty
        # AFTER the model scores, using the same feature vector it already computed.
        skills_val  = float(feature_vec[0, 2])  # 0-2
        exp_val     = float(feature_vec[0, 3])  # 0-3
        edu_val     = float(feature_vec[0, 4])  # 0-2
        domain_val  = float(feature_vec[0, 5])  # 0-1

        # Penalty 1: stuffed resume (skills capped at 1, domain capped at 0.5)
        # Signature: skills <= 1 AND domain <= 0.5 AND exp == 0 AND edu == 0
        # AND high semantic similarity (meaning the model was fooled by keyword spam)
        tfidf_val  = float(feature_vec[0, 0])
        sbert_val  = float(feature_vec[0, 1])
        is_stuffed_signal = (
            skills_val <= 1.0
            and domain_val <= 0.5
            and exp_val == 0
            and edu_val == 0
            and sbert_val >= 0.60
            and tfidf_val >= 0.50
        )
        if is_stuffed_signal:
            prob_score = prob_score * 0.20
            print(f"[ml_service] Stuffing penalty applied → score={prob_score:.4f}")

        # Penalty 2: zero experience AND zero education AND JD had no requirements
        # This catches cases where JD stated nothing, so exp/edu are 0 for everyone.
        # In this case we penalise based on how weak the hard-logic scores are.
        hard_logic_total = skills_val + domain_val  # max possible = 3.0
        if exp_val == 0 and edu_val == 0 and hard_logic_total <= 1.5:
            penalty_factor = 0.5 + (hard_logic_total / 3.0) * 0.3  # 0.50 to 0.65
            prob_score = prob_score * penalty_factor
            print(f"[ml_service] Weak hard-logic penalty applied → score={prob_score:.4f}")

        # ── Realistic Score Dampening ──────────────────────────────────────────────
        # No candidate is a mathematically "perfect" 100% match in reality.
        # We dampen the final score slightly so the absolute maximum is ~98%.
        # This prevents setting false expectations for hiring managers.
        # Scores below 35% are not reduced further.
        if prob_score >= 0.35:
            prob_score = prob_score * 0.94
            prob_score = max(0.0, min(0.94, prob_score))
        else:
            prob_score = max(0.0, min(1.0, prob_score))
        # ── End post-model penalty ─────────────────────────────────────────────────

        # GYR tier thresholds
        if prob_score >= 0.7:
            tier = "Green"
        elif prob_score >= 0.4:
            tier = "Yellow"
        else:
            tier = "Red"

        print(f"[ml_service] Score={prob_score:.4f} Tier={tier}")
        return prob_score, tier, resume_emb.tolist()

    except Exception as e:
        print(f"[ml_service] Prediction error: {e}")
        return 0.0, "Red", _EMPTY_EMB


# ---------------------------------------------------------------------------
# Insights — SHAP values + raw similarity scores
#
# Feature vector layout (6 dims):
#   [0] TF-IDF Similarity
#   [1] SBERT Similarity
#   [2] Skills Relevance
#   [3] Years Experience Match
#   [4] Education Match
#   [5] Domain Alignment
# ---------------------------------------------------------------------------

_FEATURE_GROUPS = [
    {"label": "TF-IDF Similarity",      "start": 0, "end": 1},
    {"label": "SBERT Similarity",       "start": 1, "end": 2},
    {"label": "Skills Relevance",       "start": 2, "end": 3},
    {"label": "Years Experience Match", "start": 3, "end": 4},
    {"label": "Education Match",        "start": 4, "end": 5},
    {"label": "Domain Alignment",       "start": 5, "end": 6},
]

def get_candidate_insights(resume_text: str, job_description: str) -> dict:
    if not models_loaded:
        return {
            "shap_values": [], "tfidf_sim": 0.0, "sbert_sim": 0.0,
            "structured_scores": {"skills": 0, "experience": 0, "education": 0, "domain": 0},
            "requirement_context": {
                "skills":     {"jd_has_requirement": False, "jd_skill_count": 0, "resume_skill_count": 0, "jd_skills_sample": []},
                "experience": {"jd_has_requirement": False, "required_years": 0, "candidate_years": 0.0},
                "education":  {"jd_has_requirement": False, "required_level": "none", "jd_fields": [], "resume_level": "none", "resume_fields": []},
                "domain":     {"jd_has_requirement": False, "jd_domains": [], "resume_domains": []},
            },
        }

    effective_job = job_description.strip() if job_description and job_description.strip() else "job position"

    feature_vec, _, _ = build_feature_vector(resume_text, effective_job)

    # Extract raw scalar similarity scores (Indexes 0 and 1 now!)
    tfidf_sim = float(feature_vec[0, 0])
    sbert_sim = float(feature_vec[0, 1])

    explainer = _get_shap_explainer()
    shap_vals = explainer.shap_values(feature_vec)

    if isinstance(shap_vals, list):
        shap_array = np.array(shap_vals[1])[0] 
    else:
        shap_array = np.array(shap_vals)[0]    

    grouped = []
    for grp in _FEATURE_GROUPS:
        segment = shap_array[grp["start"]:grp["end"]]
        # We need signed values for a waterfall chart to show positive/negative impact
        grouped.append({
            "label": grp["label"],
            "value": round(float(np.sum(segment)), 6),
        })

    # Extract base expected value for the waterfall plot
    exp_val = explainer.expected_value
    if isinstance(exp_val, list) or isinstance(exp_val, np.ndarray):
        base_logit = float(exp_val[1]) if len(exp_val) > 1 else float(exp_val[0])
    else:
        base_logit = float(exp_val)
    
    # Convert logit to probability space so the waterfall is consistent with final score
    base_value = 1.0 / (1.0 + np.exp(-base_logit))

    # Extract structured dimension scores from the feature vector
    # Feature vector layout: [0]=tfidf, [1]=sbert, [2]=skills(0-2), [3]=exp(0-3), [4]=edu(0-2), [5]=domain(0-1)
    structured_scores = {
        "skills":     round(float(feature_vec[0, 2]), 6),
        "experience": round(float(feature_vec[0, 3]), 6),
        "education":  round(float(feature_vec[0, 4]), 6),
        "domain":     round(float(feature_vec[0, 5]), 6),
    }

    # ── Requirement context ───────────────────────────────────────────────────
    # Surfaces JD detection metadata so the frontend knows WHY a score is 0:
    # "JD never stated this requirement" vs "candidate failed the requirement".
    # All helpers used here are already called during scoring — no new ML logic.

    jd_skills      = extract_skills(effective_job)
    resume_skills  = extract_skills(resume_text)
    jd_skill_overlap = len(jd_skills.intersection(resume_skills))

    required_years  = extract_required_years(effective_job)
    candidate_years = float(extract_resume_years(resume_text))

    edu_details    = education_match_details(resume_text, effective_job)

    jd_domains     = extract_domains(effective_job)
    resume_domains = extract_domains(resume_text)

    requirement_context = {
        "skills": {
            "jd_has_requirement": bool(jd_skills),
            "jd_skill_count":     len(jd_skills),
            "resume_skill_count": jd_skill_overlap,
            "jd_skills_sample":   sorted(jd_skills)[:8],
        },
        "experience": {
            "jd_has_requirement": required_years > 0,
            "required_years":     required_years,
            "candidate_years":    round(candidate_years, 1),
        },
        "education": {
            "jd_has_requirement": (
                edu_details.get("required_level", "none") not in ("none", "")
                or bool(edu_details.get("jd_fields", []))
            ),
            "required_level": edu_details.get("required_level", "none"),
            "jd_fields":      sorted(edu_details.get("jd_fields", [])),
            "resume_level":   edu_details.get("candidate_level", "none"),
            "resume_fields":  sorted(edu_details.get("resume_fields", [])),
        },
        "domain": {
            "jd_has_requirement": bool(jd_domains),
            "jd_domains":         sorted(jd_domains),
            "resume_domains":     sorted(resume_domains),
        },
    }

    print(f"[ml_service] Insights computed | tfidf={tfidf_sim:.4f} sbert={sbert_sim:.4f} | scores={structured_scores}")
    return {
        "base_value":          round(base_value, 6),
        "shap_values":         grouped,
        "tfidf_sim":           round(tfidf_sim, 6),
        "sbert_sim":           round(sbert_sim, 6),
        "structured_scores":   structured_scores,
        "requirement_context": requirement_context,
    }