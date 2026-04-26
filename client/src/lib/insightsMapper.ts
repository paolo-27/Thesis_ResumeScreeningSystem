import type {
    RawInsightsResponse,
    CandidateSummaryData,
    FitLabel,
    ShapValue,
    WaterfallNode,
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

// ─── Insight Maker ────────────────────────────────────────────────────────────

function buildInsightStory(shapValues: ShapValue[], scale: number): string {
    const impacts = shapValues.map(sv => ({
        label: translateShapLabel(sv.label),
        impact: sv.value * scale * 100
    }));

    const topPos = impacts.filter(v => v.impact > 0).sort((a, b) => b.impact - a.impact);
    const topNeg = impacts.filter(v => v.impact < 0).sort((a, b) => a.impact - b.impact); // most negative first

    if (topPos.length === 0 && topNeg.length === 0) {
        return "The AI model evaluated the candidate based on multiple factors without identifying any single dominant driver.";
    }

    const p = topPos[0];
    const n = topNeg[0];

    // Case 1: Both positive and negative drivers exist
    if (p && n) {
        if (Math.abs(p.impact) > Math.abs(n.impact)) {
            return `The model predicts a higher likelihood of success driven predominantly by ${p.label}, which decisively outweighs lower alignment in ${n.label}.`;
        } else {
            return `While ${p.label} contributes positively, internal scoring reflects a lower fit primarily due to significant gaps in ${n.label}.`;
        }
    }

    // Case 2: Only positive drivers
    if (p) {
        return `The model decisively identified that the candidate's ${p.label} is the strongest predictor of success for this role.`;
    }

    // Case 3: Only negative drivers (or neutral ones)
    if (n) {
        return `The AI model identified ${n.label} as the primary factor significantly reducing the candidate's overall fit score.`;
    }

    return "Objective feature analysis is complete.";
}

// ─── Waterfall Data ───────────────────────────────────────────────────────────

function buildWaterfallData(raw: RawInsightsResponse, finalScore: number, scale: number): WaterfallNode[] {
    const data: WaterfallNode[] = [];
    const basePct = raw.base_value * 100;
    const finalPct = finalScore * 100;
    
    let currentPct = basePct;
    
    data.push({
        name: 'Base AI Score',
        value: basePct,
        range: [0, basePct],
        isTotal: true
    });
    
    for (const item of raw.shap_values) {
        const impact = item.value * 100 * scale;
        // Skip extremely small noise
        if (Math.abs(impact) < 0.05) continue; 
        
        const nextPct = currentPct + impact;
        data.push({
            name: translateShapLabel(item.label),
            value: impact,
            range: [Math.min(currentPct, nextPct), Math.max(currentPct, nextPct)]
        });
        
        currentPct = nextPct;
    }
    
    data.push({
        name: 'Final Match Score',
        value: finalPct,
        range: [0, finalPct],
        isTotal: true
    });
    
    return data;
}

// ─── SHAP model explanation ───────────────────────────────────────────────────

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

export function mapInsightsToUI(
    raw: RawInsightsResponse,
    probabilityScore: number,
): CandidateSummaryData {
    const basePct = raw.base_value * 100;
    const finalPct = probabilityScore * 100;
    
    // Calculate scaling factor once to ensure consistency between chart and narrative
    const totalImpactNeeded = finalPct - basePct;
    const rawShapSum = raw.shap_values.reduce((sum, item) => sum + item.value, 0);
    const scale = rawShapSum !== 0 ? totalImpactNeeded / (rawShapSum * 100) : 1;

    return {
        fitLabel: getFitLabel(probabilityScore),
        fitScore: Math.round(probabilityScore * 100 * 10) / 10,
        baseValue: Math.round(raw.base_value * 100 * 10) / 10,
        waterfallData: buildWaterfallData(raw, probabilityScore, scale),
        insightStory: buildInsightStory(raw.shap_values, scale),
        modelExplanation: buildModelExplanation(raw),
    };
}
