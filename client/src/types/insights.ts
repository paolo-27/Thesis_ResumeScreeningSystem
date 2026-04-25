// ─── Raw backend response ─────────────────────────────────────────────────────

/** One SHAP feature group as returned by /api/candidates/:id/insights */
export interface ShapValue {
  /** Raw backend label, e.g. "Skills Relevance" */
  label: string;
  /** Summed absolute SHAP contribution for this feature group */
  value: number;
}

/**
 * Structured rule-based scores from the 6-dim feature vector.
 * Ranges: skills 0–2 | experience 0–3 | education 0–2 | domain 0–1
 * These are NOT SHAP values — they are hard-logic outputs.
 */
export interface StructuredScores {
  skills: number;
  experience: number;
  education: number;
  domain: number;
}

// ─── Requirement context (per-dimension JD detection metadata) ────────────────
// Each context block tells the frontend WHETHER the JD stated a requirement,
// and what evidence exists on both sides — so the mapper can choose between
// 'gap' (requirement stated, candidate fails) and 'not_stated' (JD is silent).

export interface SkillsContext {
  /** True when the JD lists any recognisable skill keywords */
  jd_has_requirement: boolean;
  jd_skill_count: number;
  /** How many JD skills appear in the resume */
  resume_skill_count: number;
  /** Up to 8 skills found in JD, for display in explanation */
  jd_skills_sample: string[];
}

export interface ExperienceContext {
  /** True only when a numeric year requirement was extracted from the JD */
  jd_has_requirement: boolean;
  required_years: number;
  candidate_years: number;
}

export interface EducationContext {
  /** True when JD names a degree level OR specific field(s) */
  jd_has_requirement: boolean;
  required_level: string;  // "none" | "bachelor" | "master" | "phd"
  jd_fields: string[];
  resume_level: string;
  resume_fields: string[];
}

export interface DomainContext {
  /** True when JD signals a recognisable job domain */
  jd_has_requirement: boolean;
  jd_domains: string[];
  resume_domains: string[];
}

export interface RequirementContext {
  skills: SkillsContext;
  experience: ExperienceContext;
  education: EducationContext;
  domain: DomainContext;
}

/** Full shape of /api/candidates/:id/insights */
export interface RawInsightsResponse {
  base_value: number;
  /** SHAP feature importance contribution values */
  shap_values: ShapValue[];
  tfidf_sim: number;
  sbert_sim: number;
  /** Rule-based structured scores (primary match data) */
  structured_scores: StructuredScores;
  /** JD detection metadata — used to distinguish "not stated" from "gap" */
  requirement_context: RequirementContext;
}

// ─── Transformed HR-friendly UI data ─────────────────────────────────────────

export type FitLabel = 'Strong Fit' | 'Potential Fit' | 'Low Fit';

/**
 * 4-state requirement status.
 * 'not_stated' — JD did not explicitly state this requirement.
 *                Never rendered as a "Gap"; uses neutral wording.
 * 'gap'        — JD stated the requirement AND candidate does not meet it.
 * 'partial'    — JD stated the requirement AND candidate partially meets it.
 * 'met'        — JD stated the requirement AND candidate meets/exceeds it.
 */
export type RequirementStatus = 'met' | 'partial' | 'gap' | 'not_stated';

/** One row in the requirement breakdown panel */
export interface RequirementItem {
  /** HR-friendly label, e.g. "Skills Fit" */
  label: string;
  rawScore: number;
  maxScore: number;
  /** Normalised 0–100 for progress bar; 0 when not_stated */
  percentage: number;
  status: RequirementStatus;
  /** Safe, human-readable explanation shown below the progress bar */
  explanation: string;
}

/**
 * SHAP-based model explanation.
 * ONLY shown in the technical sub-modal — never in the HR summary.
 */
export interface ModelExplanation {
  keywordMatch: number;
  meaningMatch: number;
  shapValues: ShapValue[];
}

export interface WaterfallNode {
  name: string;
  value: number; // impact
  range?: [number, number]; // [start, end] for Recharts floating bars
  isTotal?: boolean; // used for the base or final score bars
}

/**
 * Fully transformed HR-friendly data produced by mapInsightsToUI().
 */
export interface CandidateSummaryData {
  fitLabel: FitLabel;
  fitScore: number;
  
  // Waterfall plot data corresponding to base + features = final
  baseValue: number;
  waterfallData: WaterfallNode[];
  
  // The dynamically generated English explanation describing the chart
  insightStory: string;
  
  modelExplanation: ModelExplanation;
}
