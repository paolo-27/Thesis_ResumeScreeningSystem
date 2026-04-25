import type {
    RawInsightsResponse,
    CandidateSummaryData,
    FitLabel,
    RequirementItem,
    RequirementStatus,
    RequirementContext,
    ShapValue,
} from '../types/insights';

// ─── Label translation (SHAP only) ───────────────────────────────────────────

const SHAP_LABEL_MAP: Record<string, string> = {
    'TF-IDF Similarity':      'Keyword Match',
    'SBERT Similarity':       'Meaning Match',
    'Skills Relevance':       'Skills Fit',
    'Years Experience Match': 'Experience Fit',
    'Education Match':        'Education Fit',
    'Domain Alignment':       'Domain Relevance',
};

function translateShapLabel(raw: string): string {
    return SHAP_LABEL_MAP[raw] ?? raw;
}

// ─── Fit label ────────────────────────────────────────────────────────────────

function getFitLabel(probabilityScore: number): FitLabel {
    if (probabilityScore >= 0.7) return 'Strong Fit';
    if (probabilityScore >= 0.4) return 'Potential Fit';
    return 'Low Fit';
}

// ─── Degree level display helpers ────────────────────────────────────────────

const LEVEL_LABELS: Record<string, string> = {
    none:     'Not specified',
    bachelor: "Bachelor's degree",
    master:   "Master's degree",
    phd:      'PhD / Doctorate',
};

function levelLabel(level: string): string {
    return LEVEL_LABELS[level] ?? level;
}

function capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ');
}

// ─── Domain display helpers ───────────────────────────────────────────────────

function formatDomainList(domains: string[]): string {
    if (domains.length === 0) return 'none';
    return domains.slice(0, 3).map(capitalize).join(', ');
}

// ─── Core decision: 4-state status ───────────────────────────────────────────
// Rule: ONLY emit 'gap' when the JD explicitly stated the requirement.
// If not stated → 'not_stated' (neutral). Never turn silence into a gap.

function resolveStatus(
    jdHasRequirement: boolean,
    score: number,
    max: number,
): RequirementStatus {
    if (!jdHasRequirement) return 'not_stated';
    const pct = (score / max) * 100;
    if (pct >= 66) return 'met';
    if (pct >= 33) return 'partial';
    return 'gap';
}

// ─── Requirement breakdown with explanations ──────────────────────────────────

/**
 * Converts a fractional year value into a human-friendly duration string.
 * Examples: 0.5 → "6 months" | 1 → "1 year" | 1.5 → "1 year 6 months" | 2 → "2 years"
 */
function formatYears(years: number): string {
    const totalMonths = Math.round(years * 12);
    const y = Math.floor(totalMonths / 12);
    const m = totalMonths % 12;
    const parts: string[] = [];
    if (y > 0) parts.push(`${y} year${y !== 1 ? 's' : ''}`);
    if (m > 0) parts.push(`${m} month${m !== 1 ? 's' : ''}`);
    return parts.length ? parts.join(' ') : '0 months';
}

function buildRequirementBreakdown(
    raw: RawInsightsResponse,
): RequirementItem[] {
    const s = raw.structured_scores;
    const ctx = raw.requirement_context;

    // ── Skills ────────────────────────────────────────────────────────────────
    const skillsStatus = resolveStatus(ctx.skills.jd_has_requirement, s.skills, 2);
    const skillsPct = ctx.skills.jd_has_requirement ? Math.round((s.skills / 2) * 100) : 0;

    let skillsExplanation: string;
    if (!ctx.skills.jd_has_requirement) {
        skillsExplanation = 'No specific skills were listed in the job description.';
    } else if (ctx.skills.jd_skill_count === 0) {
        skillsExplanation = 'No recognisable skill keywords detected in the job description.';
    } else {
        const sample = ctx.skills.jd_skills_sample.slice(0, 4).join(', ');
        skillsExplanation =
            `Resume matches ${ctx.skills.resume_skill_count} of ${ctx.skills.jd_skill_count} ` +
            `required skills (e.g. ${sample}).`;
    }

    // ── Experience ────────────────────────────────────────────────────────────
    const expStatus = resolveStatus(ctx.experience.jd_has_requirement, s.experience, 3);
    const expPct = ctx.experience.jd_has_requirement
        ? Math.round((s.experience / 3) * 100)
        : 0;

    let expExplanation: string;
    if (!ctx.experience.jd_has_requirement) {
        expExplanation = 'No minimum years of experience explicitly stated in the job description.';
    } else {
        const req = ctx.experience.required_years;
        const cand = ctx.experience.candidate_years;
        expExplanation =
            `Job requires ${formatYears(req)}. ` +
            `Resume indicates approximately ${formatYears(cand)} of experience.`;
    }

    // ── Education ─────────────────────────────────────────────────────────────
    const eduStatus = resolveStatus(ctx.education.jd_has_requirement, s.education, 2);
    const eduPct = ctx.education.jd_has_requirement
        ? Math.round((s.education / 2) * 100)
        : 0;

    let eduExplanation: string;
    if (!ctx.education.jd_has_requirement) {
        eduExplanation = 'No explicit education level or field requirement detected in the job description.';
    } else {
        const reqLevel = levelLabel(ctx.education.required_level);
        const fields = ctx.education.jd_fields.slice(0, 2).join(', ');
        const resumeLevel = levelLabel(ctx.education.resume_level);
        const resumeFields = ctx.education.resume_fields.slice(0, 2).join(', ');

        const jdPart = fields ? `${reqLevel} in ${fields}` : reqLevel;
        const resumePart = resumeFields
            ? `${resumeLevel} in ${resumeFields}`
            : resumeLevel;
        eduExplanation = `Job requires ${jdPart}. Resume shows ${resumePart}.`;
    }

    // ── Domain ────────────────────────────────────────────────────────────────
    const domainStatus = resolveStatus(ctx.domain.jd_has_requirement, s.domain, 1);
    const domainPct = ctx.domain.jd_has_requirement
        ? Math.round(s.domain * 100)
        : 0;

    let domainExplanation: string;
    if (!ctx.domain.jd_has_requirement) {
        domainExplanation = 'No specific industry or domain signals detected in the job description.';
    } else {
        const jdDomains = formatDomainList(ctx.domain.jd_domains);
        const resumeDomains = formatDomainList(ctx.domain.resume_domains);
        if (domainStatus === 'met') {
            domainExplanation = `Job targets ${jdDomains}. Resume shows matching domain experience in ${resumeDomains}.`;
        } else {
            domainExplanation =
                `Job targets ${jdDomains}. ` +
                (ctx.domain.resume_domains.length
                    ? `Resume shows ${resumeDomains}, which may not align closely.`
                    : 'No matching domain experience detected on resume.');
        }
    }

    return [
        {
            label: 'Skills Fit',
            rawScore: s.skills,
            maxScore: 2,
            percentage: skillsPct,
            status: skillsStatus,
            explanation: skillsExplanation,
        },
        {
            label: 'Experience Fit',
            rawScore: s.experience,
            maxScore: 3,
            percentage: expPct,
            status: expStatus,
            explanation: expExplanation,
        },
        {
            label: 'Education Fit',
            rawScore: s.education,
            maxScore: 2,
            percentage: eduPct,
            status: eduStatus,
            explanation: eduExplanation,
        },
        {
            label: 'Domain Relevance',
            rawScore: s.domain,
            maxScore: 1,
            percentage: domainPct,
            status: domainStatus,
            explanation: domainExplanation,
        },
    ];
}

// ─── Strengths and gaps ───────────────────────────────────────────────────────
// RULES:
//  - A strength is emitted only when the JD stated the requirement AND
//    the candidate meets/exceeds it.
//  - A gap is emitted only when the JD stated the requirement AND
//    the candidate clearly fails it.
//  - 'not_stated' items contribute NEITHER strengths NOR gaps.
//  - SHAP values are NEVER used here.

function buildStrengthsAndGaps(
    raw: RawInsightsResponse,
): { strengths: string[]; gaps: string[] } {
    const strengths: string[] = [];
    const gaps: string[] = [];
    const s = raw.structured_scores;
    const ctx: RequirementContext = raw.requirement_context;

    // ── Skills ────────────────────────────────────────────────────────────────
    if (ctx.skills.jd_has_requirement) {
        if (s.skills >= 1) {
            const n = ctx.skills.resume_skill_count;
            const total = ctx.skills.jd_skill_count;
            strengths.push(
                total > 0
                    ? `Covers ${n} of ${total} required skills listed in the job description`
                    : 'Skills are relevant to the role',
            );
        } else {
            const sample = ctx.skills.jd_skills_sample.slice(0, 3).join(', ');
            gaps.push(
                sample
                    ? `Missing most required skills (e.g. ${sample})`
                    : 'Significant skill gaps compared to the job description',
            );
        }
    }
    // If !jd_has_requirement → no strength or gap emitted

    // ── Experience ────────────────────────────────────────────────────────────
    if (ctx.experience.jd_has_requirement) {
        if (s.experience >= 2) {
            const req = ctx.experience.required_years;
            const cand = ctx.experience.candidate_years;
            strengths.push(
                `Meets the ${formatYears(req)} experience requirement (≈${formatYears(cand)} detected)`,
            );
        } else if (s.experience < 1) {
            const req = ctx.experience.required_years;
            const cand = ctx.experience.candidate_years;
            gaps.push(
                `Falls short of the stated ${formatYears(req)} experience requirement (≈${formatYears(cand)} detected)`,
            );
        }
        // s.experience === 1 → partial, no strong statement in either direction
    }
    // If !jd_has_requirement → no gap emitted regardless of score

    // ── Education ─────────────────────────────────────────────────────────────
    if (ctx.education.jd_has_requirement) {
        if (s.education >= 1) {
            const level = levelLabel(ctx.education.required_level);
            strengths.push(`Education aligns with the stated requirement (${level})`);
        } else {
            const level = levelLabel(ctx.education.required_level);
            gaps.push(`Education may not satisfy the stated requirement (${level})`);
        }
    }
    // If !jd_has_requirement → no gap about education emitted

    // ── Domain ────────────────────────────────────────────────────────────────
    if (ctx.domain.jd_has_requirement) {
        if (s.domain >= 0.5) {
            const d = formatDomainList(ctx.domain.jd_domains);
            strengths.push(`Industry/domain experience aligns with the role (${d})`);
        } else {
            const d = formatDomainList(ctx.domain.jd_domains);
            gaps.push(`Limited domain experience relevant to ${d}`);
        }
    }
    // If !jd_has_requirement → no gap emitted

    // ── Similarity scores (always available, no JD-detection gate needed) ─────
    const tfidf = raw.tfidf_sim;
    if (tfidf >= 0.15) {
        strengths.push('Resume language closely mirrors the job description keywords');
    } else if (tfidf < 0.05) {
        gaps.push('Very low keyword overlap with the job description');
    }

    const sbert = raw.sbert_sim;
    if (sbert >= 0.5) {
        strengths.push('Overall semantic alignment with the role is strong');
    } else if (sbert < 0.3) {
        gaps.push('Overall resume context is not closely aligned with this role');
    }

    return { strengths, gaps };
}

// ─── SHAP model explanation ───────────────────────────────────────────────────
// Isolated — rendered only in the SHAP sub-modal, never in the HR summary.

function buildModelExplanation(raw: RawInsightsResponse) {
    const translatedShap: ShapValue[] = raw.shap_values.map((sv) => ({
        label: translateShapLabel(sv.label),
        value: sv.value,
    }));
    return {
        keywordMatch: Math.round(raw.tfidf_sim * 100 * 10) / 10,
        meaningMatch: Math.round(raw.sbert_sim * 100 * 10) / 10,
        shapValues: translatedShap,
    };
}

// ─── Public mapper ────────────────────────────────────────────────────────────

/**
 * Maps the raw backend /insights response into HR-friendly UI data.
 *
 * @param raw              Full response from /api/candidates/:id/insights
 * @param probabilityScore Candidate.probability_score (0–1)
 *
 * Design guarantees:
 *  - Gaps are emitted ONLY when the JD explicitly stated the requirement.
 *  - 'not_stated' items appear in the breakdown with neutral explanations.
 *  - SHAP values are isolated in modelExplanation and never influence
 *    fitLabel, strengths, gaps, or requirementBreakdown.
 *  - Missing certainty is NEVER turned into a hard Gap.
 */
export function mapInsightsToUI(
    raw: RawInsightsResponse,
    probabilityScore: number,
): CandidateSummaryData {
    const { strengths, gaps } = buildStrengthsAndGaps(raw);

    return {
        fitLabel: getFitLabel(probabilityScore),
        fitScore: Math.round(probabilityScore * 100 * 10) / 10,
        strengths,
        gaps,
        requirementBreakdown: buildRequirementBreakdown(raw),
        modelExplanation: buildModelExplanation(raw),
    };
}
