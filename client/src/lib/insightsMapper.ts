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

function buildInsightStory(shapValues: ShapValue[]): string {
    const sorted = [...shapValues].sort((a, b) => b.value - a.value);
    const topPos = sorted.filter(v => v.value > 0);
    const topNeg = sorted.filter(v => v.value < 0).reverse(); // largest negative first

    if (topPos.length === 0 && topNeg.length === 0) {
        return "The AI model evaluated the candidate based on multiple factors without identifying any single dominant driver.";
    }

    if (topPos.length > 0 && topNeg.length > 0) {
        const p = topPos[0];
        const n = topNeg[0];
        
        // Decisive/Objective tone as requested
        return `The model predicts a higher likelihood of success driven predominantly by ${translateShapLabel(p.label)}, which decisively outweighs lower alignment in ${translateShapLabel(n.label)}.`;
    }

    if (topPos.length > 0) {
        return `The model decisively identified that the candidate's ${translateShapLabel(topPos[0].label)} is a highly strong predictor of success for this role.`;
    }

    if (topNeg.length > 0) {
        return `The AI model identified ${translateShapLabel(topNeg[0].label)} as the primary factor significantly reducing the candidate's overall fit score.`;
    }

    return "Objective feature analysis is complete.";
}

// ─── Waterfall Data ───────────────────────────────────────────────────────────

function buildWaterfallData(raw: RawInsightsResponse, finalScore: number): WaterfallNode[] {
    const data: WaterfallNode[] = [];
    let currentPct = raw.base_value * 100;
    
    data.push({
        name: 'Base AI Score',
        value: currentPct,
        range: [0, currentPct], // Base starts from 0 to its value
        isTotal: true
    });
    
    for (const item of raw.shap_values) {
        const impact = item.value * 100;
        // Skip extremely small noise to keep chart clean
        if (Math.abs(impact) < 0.1) continue; 
        
        data.push({
            name: translateShapLabel(item.label),
            value: impact,
            range: [currentPct, currentPct + impact]
        });
        
        currentPct += impact;
    }
    
    data.push({
        name: 'Final Match Score',
        value: finalScore * 100,
        range: [0, finalScore * 100], // Final score bar goes from 0
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
    return {
        fitLabel: getFitLabel(probabilityScore),
        fitScore: Math.round(probabilityScore * 100 * 10) / 10,
        baseValue: Math.round(raw.base_value * 100 * 10) / 10,
        waterfallData: buildWaterfallData(raw, probabilityScore),
        insightStory: buildInsightStory(raw.shap_values),
        modelExplanation: buildModelExplanation(raw),
    };
}
