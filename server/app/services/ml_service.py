import os
import joblib
import numpy as np
import shap
from xgboost import XGBClassifier
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(BASE_DIR, "model")

vectorizer_path = os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl")
classifier_path = os.path.join(MODEL_DIR, "xgb_classifier_optimal.json")

# ---------------------------------------------------------------------------
# Load models globally (once on startup)
# ---------------------------------------------------------------------------
try:
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
# Feature vector layout (770 dims):
#   [0:384]   SBERT embedding of the resume
#   [384:768] SBERT embedding of the job description
#   [768]     TF-IDF cosine similarity between resume and job description
#   [769]     SBERT cosine similarity between resume and job description
# ---------------------------------------------------------------------------

def build_feature_vector(resume_text: str, job_description: str) -> np.ndarray:
    """
    Constructs the 770-dimensional feature array the XGBoost model was trained on.
    """
    # --- SBERT embeddings (384-dim each) ---
    resume_emb = sbert.encode([resume_text])[0]           # shape (384,)
    job_emb    = sbert.encode([job_description])[0]       # shape (384,)

    # --- TF-IDF cosine similarity (1 scalar) ---
    resume_tfidf = vectorizer.transform([resume_text])    # sparse (1, vocab)
    job_tfidf    = vectorizer.transform([job_description])
    tfidf_cos    = cosine_similarity(resume_tfidf, job_tfidf)[0][0]  # scalar

    # --- SBERT cosine similarity (1 scalar) ---
    sbert_cos = cosine_similarity(
        resume_emb.reshape(1, -1), job_emb.reshape(1, -1)
    )[0][0]
    print(f"DEBUG MATH -> TF-IDF Sim: {tfidf_cos:.4f} | SBERT Sim: {sbert_cos:.4f}")

    # --- Concatenate → (770,) ---
    features = np.concatenate([job_emb, resume_emb, [tfidf_cos, sbert_cos]])
    return features.reshape(1, -1)


def predict_resume_tier(resume_text: str, job_description: str) -> tuple[float, str]:
    """
    Predicts the GYR tier for a candidate by comparing their resume against the
    job description using the trained 770-feature XGBoost model.

    Args:
        resume_text:     Extracted plain text from the uploaded PDF/DOCX.
        job_description: Plain text of the job posting description.

    Returns:
        (probability_score [0–1], tier ['Green' | 'Yellow' | 'Red'])
    """
    if not models_loaded:
        print("[ml_service] Models not loaded, returning fallback Red.")
        return 0.0, "Red"

    if not resume_text.strip():
        print("[ml_service] Empty resume text, returning fallback Red.")
        return 0.0, "Red"

    # Use the job description if provided; fall back to a generic placeholder
    # so the function never crashes even if the caller omits it.
    effective_job = job_description.strip() if job_description and job_description.strip() else "job position"

    try:
        feature_vec = build_feature_vector(resume_text, effective_job)

        probabilities = classifier.predict_proba(feature_vec)
        # Class index 1 = "hired / shortlist" class
        prob_score = float(probabilities[0][1])

        # GYR tier thresholds
        if prob_score >= 0.7:
            tier = "Green"
        elif prob_score >= 0.4:
            tier = "Yellow"
        else:
            tier = "Red"

        print(f"[ml_service] Score={prob_score:.4f} Tier={tier}")
        return prob_score, tier

    except Exception as e:
        print(f"[ml_service] Prediction error: {e}")
        return 0.0, "Red"


# ---------------------------------------------------------------------------
# Insights — SHAP values + raw similarity scores
#
# Feature vector layout (770 dims):
#   [0:384]   SBERT embedding of the job description
#   [384:768] SBERT embedding of the resume
#   [768]     TF-IDF cosine similarity
#   [769]     SBERT cosine similarity
# ---------------------------------------------------------------------------

_FEATURE_GROUPS = [
    {"label": "Job Description Embedding", "start": 0,   "end": 384},
    {"label": "Resume Embedding",          "start": 384, "end": 768},
    {"label": "TF-IDF Similarity",         "start": 768, "end": 769},
    {"label": "SBERT Similarity",          "start": 769, "end": 770},
]


def get_candidate_insights(resume_text: str, job_description: str) -> dict:
    """
    Returns SHAP-based feature importance and raw similarity scores.

    Returns:
        {
          "shap_values": [
              {"label": str, "value": float},  # summed |shap| per group
              ...
          ],
          "tfidf_sim": float,   # raw TF-IDF cosine similarity [0-1]
          "sbert_sim": float,   # raw SBERT cosine similarity [0-1]
        }
    """
    if not models_loaded:
        return {"shap_values": [], "tfidf_sim": 0.0, "sbert_sim": 0.0}

    effective_job = job_description.strip() if job_description and job_description.strip() else "job position"

    feature_vec = build_feature_vector(resume_text, effective_job)  # shape (1, 770)

    # Extract raw scalar similarity scores from the feature vector
    tfidf_sim = float(feature_vec[0, 768])
    sbert_sim  = float(feature_vec[0, 769])

    # Compute SHAP values: shape (1, 770) for class-1 (positive / shortlist)
    explainer = _get_shap_explainer()
    shap_vals = explainer.shap_values(feature_vec)   # ndarray (1, 770) or list

    # shap_values() may return a list [class0_vals, class1_vals] for binary classifiers
    if isinstance(shap_vals, list):
        shap_array = np.array(shap_vals[1])[0]  # class-1 SHAP, shape (770,)
    else:
        shap_array = np.array(shap_vals)[0]      # shape (770,)

    # Aggregate into human-readable groups (sum of absolute SHAP contributions)
    grouped = []
    for grp in _FEATURE_GROUPS:
        segment = shap_array[grp["start"]:grp["end"]]
        grouped.append({
            "label": grp["label"],
            "value": round(float(np.sum(np.abs(segment))), 6),
        })

    print(f"[ml_service] Insights computed | tfidf={tfidf_sim:.4f} sbert={sbert_sim:.4f} shap_groups={grouped}")
    return {
        "shap_values": grouped,
        "tfidf_sim": round(tfidf_sim, 6),
        "sbert_sim": round(sbert_sim, 6),
    }
