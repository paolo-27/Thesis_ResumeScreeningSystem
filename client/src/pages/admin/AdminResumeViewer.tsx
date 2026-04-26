import React, { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { renderAsync } from 'docx-preview';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from 'recharts';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
    ArrowLeft,
    Download,
    Star,
    FileText,
    Calendar,
    ThumbsUp,
    ThumbsDown,
    ChevronLeft,
    ChevronRight,
    ZoomIn,
    ZoomOut,
    Maximize2,
    Loader2,
    AlertCircle,
    BarChart2,
    X,
} from 'lucide-react';
import type { Candidate } from '../../types';
import type { RawInsightsResponse, CandidateSummaryData } from '../../types/insights';
import { mapInsightsToUI } from '../../lib/insightsMapper';
import api from '../../lib/axios';

// Configure pdf.js worker (bundled with react-pdf / pdfjs-dist)
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
).toString();

interface AdminResumeViewerProps {
    candidateId: string;
    onBack: () => void;
    onAction?: (action: 'shortlist' | 'reject') => void;
}

// ─── Shared Toolbar Components ──────────────────────────────────────────────
interface ViewerToolbarProps {
    currentPage: number;
    numPages: number;
    onPageChange: (page: number) => void;
    scale: number;
    onScaleChange: (scale: number) => void;
    showPagination?: boolean;
}

function ViewerToolbar({
    currentPage,
    numPages,
    onPageChange,
    scale,
    onScaleChange,
    showPagination = true
}: ViewerToolbarProps) {
    return (
        <div className="flex items-center justify-between px-2 sm:px-4 py-2 bg-gray-100 border-b border-gray-200 flex-shrink-0 z-30">
            <div className="flex items-center gap-1 sm:gap-2">
                {showPagination && (
                    <>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onPageChange(Math.max(1, currentPage - 1))}
                            disabled={currentPage <= 1 || numPages === 0}
                            className="h-8 w-8 sm:w-auto sm:px-2 p-0"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </Button>
                        <span className="text-[10px] sm:text-sm text-gray-600 min-w-[50px] sm:min-w-[80px] text-center">
                            {numPages > 0 ? `${currentPage} / ${numPages}` : '—'}
                        </span>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onPageChange(Math.min(numPages, currentPage + 1))}
                            disabled={currentPage >= numPages || numPages === 0}
                            className="h-8 w-8 sm:w-auto sm:px-2 p-0"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </Button>
                    </>
                )}
            </div>
            <div className="flex items-center gap-1 sm:gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onScaleChange(Math.max(0.5, +(scale - 0.2).toFixed(1)))}
                    className="h-8 w-8 sm:w-auto sm:px-2 p-0"
                >
                    <ZoomOut className="w-4 h-4" />
                </Button>
                <span className="text-[10px] sm:text-sm text-gray-600 min-w-[30px] sm:min-w-[45px] text-center">
                    {Math.round(scale * 100)}%
                </span>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onScaleChange(Math.min(3, +(scale + 0.2).toFixed(1)))}
                    className="h-8 w-8 sm:w-auto sm:px-2 p-0"
                >
                    <ZoomIn className="w-4 h-4" />
                </Button>
            </div>
        </div>
    );
}

// ─── PDF viewer sub-component ────────────────────────────────────────────────
// ─── PDF viewer sub-component ────────────────────────────────────────────────
interface DocViewerProps {
    url: string;
    scale: number;
    currentPage: number;
    onLoadSuccess: (numPages: number) => void;
}

function PdfViewer({ url, scale, currentPage, onLoadSuccess }: DocViewerProps) {
    const [pdfError, setPdfError] = useState<string | null>(null);
    const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);

    useEffect(() => {
        let isCancelled = false;
        api.get(url, { responseType: 'blob' })
            .then(res => {
                if (!isCancelled) setPdfBlob(res.data);
            })
            .catch(err => {
                if (!isCancelled) setPdfError(err.message || 'Failed to fetch PDF');
            });
        return () => { isCancelled = true; };
    }, [url]);

    return (
        <div className="flex-1 overflow-auto flex justify-center py-4 bg-gray-200">
            {pdfError ? (
                <div className="flex flex-col items-center justify-center text-center p-8 bg-white m-4 rounded-lg shadow-sm">
                    <AlertCircle className="w-10 h-10 text-red-400 mb-3" />
                    <p className="text-red-600 font-medium mb-1">Failed to load PDF</p>
                    <p className="text-gray-500 text-sm">{pdfError}</p>
                </div>
            ) : !pdfBlob ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3 w-full h-full">
                    <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
                    <span className="text-gray-500 text-sm">Fetching PDF securely…</span>
                </div>
            ) : (
                <Document
                    file={pdfBlob}
                    onLoadSuccess={({ numPages }) => onLoadSuccess(numPages)}
                    onLoadError={(err) => setPdfError(err.message)}
                    loading={
                        <div className="flex flex-col items-center justify-center py-20 gap-3">
                            <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
                            <span className="text-gray-500 text-sm">Rendering PDF…</span>
                        </div>
                    }
                >
                    <div className="shadow-lg mb-4">
                        <Page
                            pageNumber={currentPage}
                            scale={scale}
                            renderAnnotationLayer
                            renderTextLayer
                        />
                    </div>
                </Document>
            )}
        </div>
    );
}


// SHAP Explainer Modal removed as requested — insights are directly in the Waterfall now.

// Status pill removed (no longer used in UI)

// ─── HR Candidate Summary modal ───────────────────────────────────────────────
function InsightsModal({
    data,
    loading,
    error,
    onClose,
}: {
    data: CandidateSummaryData | null;
    loading: boolean;
    error: string | null;
    onClose: () => void;
}) {
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [onClose]);

    const fitColors: Record<string, string> = {
        'Strong Fit': 'bg-emerald-100 text-emerald-800 border-emerald-200',
        'Potential Fit': 'bg-yellow-100 text-yellow-800 border-yellow-200',
        'Low Fit': 'bg-red-100 text-red-800 border-red-200',
    };
    const fitDot: Record<string, string> = {
        'Strong Fit': 'bg-emerald-500',
        'Potential Fit': 'bg-yellow-500',
        'Low Fit': 'bg-red-500',
    };

    return (
        <>
            <div
                className="fixed inset-0 z-50 flex items-center justify-center"
                style={{ backdropFilter: 'blur(4px)', backgroundColor: 'rgba(0,0,0,0.55)' }}
                onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
            >
                <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden flex flex-col max-h-[90vh]">

                    {/* ── Header ── */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 flex-shrink-0">
                        <div className="flex items-center gap-2">
                            <FileText className="w-5 h-5 text-emerald-600" />
                            <h2 className="text-gray-900 font-semibold">Candidate Summary</h2>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-700 transition-colors rounded-full p-1 hover:bg-gray-100"
                            aria-label="Close"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* ── Body ── */}
                    <div className="overflow-y-auto flex-1 px-6 py-5 space-y-5">

                        {/* Loading */}
                        {loading && (
                            <div className="flex flex-col items-center justify-center py-16 gap-3">
                                <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
                                <span className="text-gray-500 text-sm">Analysing resume against job requirements…</span>
                            </div>
                        )}

                        {/* Error */}
                        {error && !loading && (
                            <div className="flex flex-col items-center justify-center py-10 gap-3">
                                <AlertCircle className="w-8 h-8 text-red-400" />
                                <p className="text-red-600 font-medium text-sm">{error}</p>
                            </div>
                        )}

                        {data && !loading && (
                            <>
                                {/* ── Overall Fit card ── */}
                                <div className="flex flex-col gap-5">
                                    <div className="relative rounded-xl border border-gray-200 bg-gray-50 p-5">

                                        <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Overall Assessment</p>
                                        <div className="flex items-center gap-3">
                                            <span className={`inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full border ${fitColors[data.fitLabel] ?? 'bg-gray-100 text-gray-700'
                                                }`}>
                                                <span className={`w-2 h-2 rounded-full ${fitDot[data.fitLabel]}`} />
                                                {data.fitLabel}
                                            </span>
                                            <span className="text-2xl font-bold text-gray-900">{data.fitScore.toFixed(1)}%</span>
                                            <span className="text-xs text-gray-400">match probability</span>
                                        </div>
                                    </div>

                                    {/* ── The Individual Story (Waterfall) ── */}
                                    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                                        <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
                                            <BarChart2 className="w-4 h-4 text-emerald-600" />
                                            Prediction Breakdown
                                        </h3>

                                        <div className="h-64 w-full mb-2">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart
                                                    data={data.waterfallData}
                                                    layout="vertical"
                                                    margin={{ top: 0, right: 30, left: 10, bottom: 0 }}
                                                >
                                                    <XAxis type="number" domain={[0, 100]} hide />
                                                    <YAxis
                                                        type="category"
                                                        dataKey="name"
                                                        width={110}
                                                        tick={{ fontSize: 11, fill: '#4b5563' }}
                                                        axisLine={false}
                                                        tickLine={false}
                                                    />
                                                    <Tooltip
                                                        formatter={(value: any, name: any, props: any) => {
                                                            if (props.payload.isTotal) return [`${props.payload.value.toFixed(1)}%`, 'Score'];
                                                            const prefix = props.payload.value > 0 ? '+' : '';
                                                            return [`${prefix}${props.payload.value.toFixed(1)}%`, 'Impact'];
                                                        }}
                                                        contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                                        cursor={{ fill: '#f3f4f6' }}
                                                    />
                                                    <Bar dataKey="range" isAnimationActive={false} radius={[0, 2, 2, 0]}>
                                                        {data.waterfallData.map((entry, index) => {
                                                            if (entry.isTotal) return <Cell key={`cell-${index}`} fill="#94a3b8" />; // slate-400
                                                            return <Cell key={`cell-${index}`} fill={entry.value > 0 ? "#10b981" : "#ef4444"} />; // emerald-500 / red-500
                                                        })}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>

                                        {/* ── Insight Maker ── */}
                                        <div className="mt-4 pt-4 border-t border-gray-100">
                                            <p className="text-[13px] text-gray-700 font-medium leading-relaxed">
                                                {data.insightStory}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
}

// ─── DOCX viewer sub-component ───────────────────────────────────────────────
function DocxViewer({ url, scale, onLoadSuccess }: Omit<DocViewerProps, 'currentPage'>) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [docxError, setDocxError] = useState<string | null>(null);
    const [docxLoading, setDocxLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;

        async function loadDocx() {
            try {
                const res = await api.get(url, { responseType: 'arraybuffer' });
                if (cancelled || !containerRef.current) return;

                const buffer = res.data;
                containerRef.current.innerHTML = '';

                await renderAsync(buffer, containerRef.current, undefined, {
                    className: 'docx-render',
                    inWrapper: true,
                    ignoreWidth: false,
                    ignoreHeight: false,
                    ignoreFonts: false,
                    breakPages: true,
                    ignoreLastRenderedPageBreak: true,
                    experimental: false,
                    trimXmlDeclaration: true,
                    useBase64URL: false,
                    renderChanges: false,
                    renderHeaders: true,
                    renderFooters: true,
                    renderFootnotes: true,
                    renderEndnotes: true,
                    debug: false,
                });
                if (!cancelled) {
                    onLoadSuccess(1); // DOCX is usually 1 continuous view here
                    setDocxLoading(false);
                }
            } catch (err: unknown) {
                if (!cancelled) {
                    setDocxError(err instanceof Error ? err.message : 'Unknown error');
                    setDocxLoading(false);
                }
            }
        }

        loadDocx();
        return () => { cancelled = true; };
    }, [url, onLoadSuccess]);

    return (
        <div className="flex-1 overflow-auto py-4 px-2 sm:px-4 flex justify-center bg-gray-200">
            {docxLoading && !docxError && (
                <div className="flex flex-col items-center justify-center py-20 gap-3 w-full">
                    <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
                    <span className="text-gray-500 text-sm">Loading document…</span>
                </div>
            )}
            {docxError && (
                <div className="flex flex-col items-center justify-center text-center p-8 w-full bg-white m-4 rounded-lg shadow-sm">
                    <AlertCircle className="w-10 h-10 text-red-400 mb-3" />
                    <p className="text-red-600 font-medium mb-1">Failed to load document</p>
                    <p className="text-gray-500 text-sm">{docxError}</p>
                </div>
            )}
            <div 
                className="origin-top shadow-lg bg-white transition-transform duration-200"
                style={{ 
                    transform: `scale(${scale})`,
                    width: 'min-content',
                    minWidth: '100%'
                }}
            >
                <div
                    ref={containerRef}
                    className={`docx-container mx-auto p-4 sm:p-8 ${docxLoading ? 'hidden' : ''}`}
                />
            </div>
        </div>
    );
}

// ─── Main component ──────────────────────────────────────────────────────────
export default function AdminResumeViewer({ candidateId, onBack, onAction }: AdminResumeViewerProps) {
    const [candidate, setCandidate] = useState<Candidate | null>(null);
    const [loading, setLoading] = useState(true);
    const [insightsOpen, setInsightsOpen] = useState(false);
    const [insightsData, setInsightsData] = useState<CandidateSummaryData | null>(null);
    const [insightsLoading, setInsightsLoading] = useState(false);
    const [insightsError, setInsightsError] = useState<string | null>(null);

    useEffect(() => {
        api.get('/api/candidates')
            .then(res => {
                const found = res.data.find((c: Candidate) => c.id === candidateId);
                setCandidate(found || null);
                setLoading(false);
            })
            .catch(err => {
                console.error('Error fetching candidate:', err);
                setLoading(false);
            });
    }, [candidateId]);

    const handleViewInsights = async () => {
        setInsightsOpen(true);
        // Only fetch if we don't already have data cached for this candidate
        if (insightsData) return;
        setInsightsLoading(true);
        setInsightsError(null);
        try {
            const res = await api.get(`/api/candidates/${candidateId}/insights`);
            const raw = res.data as RawInsightsResponse;
            // Map raw backend response → HR-friendly UI data using the transformation layer
            const probabilityScore = candidate?.probability_score ?? 0;
            setInsightsData(mapInsightsToUI(raw, probabilityScore));
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Failed to load insights';
            setInsightsError(msg);
        } finally {
            setInsightsLoading(false);
        }
    };

    const [numPages, setNumPages] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [scale, setScale] = useState(1.0);

    // Layout Hijack: Disable parent main scroll and enable internal scroll for "Locked Header" feel
    useEffect(() => {
        const parentMain = document.querySelector('main');
        if (parentMain) {
            const originalOverflow = parentMain.style.overflow;
            parentMain.style.overflow = 'hidden';
            return () => { parentMain.style.overflow = originalOverflow; };
        }
    }, []);

    if (loading) {
        return (
            <div className="h-full bg-gray-50 flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-emerald-600 mr-3" />
                <p className="text-gray-500">Loading candidate data…</p>
            </div>
        );
    }

    if (!candidate) {
        return (
            <div className="h-full bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-gray-500 mb-4">Candidate not found</p>
                    <Button onClick={onBack}>Go Back</Button>
                </div>
            </div>
        );
    }

    const getViewColor = () => {
        if (candidate.gyr_tier === 'Green') return { bg: 'bg-emerald-100', text: 'text-emerald-700', badge: 'Top 30%' };
        if (candidate.gyr_tier === 'Yellow') return { bg: 'bg-yellow-100', text: 'text-yellow-700', badge: 'Middle 50%' };
        if (candidate.gyr_tier === 'Red') return { bg: 'bg-red-100', text: 'text-red-700', badge: 'Bottom 20%' };
        if (candidate.status === 'Shortlisted') return { bg: 'bg-blue-100', text: 'text-blue-700', badge: 'Shortlisted' };
        return { bg: 'bg-gray-100', text: 'text-gray-700', badge: 'Rejected' };
    };

    const rankColor = getViewColor();
    const isShortlisted = candidate.status === 'Shortlisted';
    const isRejected = candidate.status === 'Rejected';

    const resumeUrl = `/api/candidates/${candidateId}/resume`;
    const resumeFilename = candidate.resume_url ?? '';
    const isPdf = resumeFilename.toLowerCase().endsWith('.pdf');
    const isDocx = resumeFilename.toLowerCase().endsWith('.docx');
    const hasResume = isPdf || isDocx;

    const storedBasename = resumeFilename.split('/').pop() ?? '';
    const originalFilename = storedBasename.includes('_')
        ? storedBasename.split('_').slice(1).join('_')
        : storedBasename;

    const handleDownload = async () => {
        try {
            const res = await api.get(`/api/candidates/${candidateId}/resume`, { responseType: 'blob' });
            const blobUrl = window.URL.createObjectURL(new Blob([res.data]));
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = originalFilename || 'resume';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(blobUrl);
        } catch (error) {
            console.error('Download failed', error);
        }
    };

    return (
        <div className="bg-gray-50 h-full flex flex-col -m-4 md:-m-8 overflow-hidden">
            {/* LOCKED COMPOSITE HEADER */}
            <div className="flex-shrink-0 z-[50] shadow-md border-b border-gray-200">
                {/* Row 1: Back + Actions */}
                <div className="bg-white">
                    <div className="max-w-7xl mx-auto px-4 sm:px-8 py-3 sm:py-4">
                        <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 min-w-0">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={onBack}
                                    className="text-gray-600 hover:text-gray-900 flex-shrink-0 px-2 sm:px-3"
                                >
                                    <ArrowLeft className="w-4 h-4" />
                                    <span className="hidden sm:inline ml-1">Back</span>
                                </Button>
                                <div className="hidden sm:block h-8 w-px bg-gray-300 flex-shrink-0" />
                                <div className="flex items-center gap-2 min-w-0">
                                    <FileText className="w-4 h-4 text-gray-600 flex-shrink-0 hidden sm:block" />
                                    <h2 className="text-gray-900 font-bold truncate text-sm sm:text-base max-w-[140px] sm:max-w-[400px]">
                                        {originalFilename || `${candidate.name}_Resume`}
                                    </h2>
                                </div>
                            </div>
                            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleDownload}
                                    disabled={!hasResume}
                                    className="px-2 sm:px-3 h-9"
                                >
                                    <Download className="w-4 h-4" />
                                    <span className="hidden sm:inline ml-1">Download</span>
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={handleViewInsights}
                                    className="border-emerald-200 text-emerald-700 hover:bg-emerald-50 px-2 sm:px-3 h-9"
                                >
                                    <BarChart2 className="w-4 h-4" />
                                    <span className="hidden sm:inline ml-1 text-xs">Insights</span>
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
                {/* Row 2: Shared Document Toolbar (Zoom/Pages) */}
                <ViewerToolbar 
                    currentPage={currentPage}
                    numPages={numPages}
                    onPageChange={setCurrentPage}
                    scale={scale}
                    onScaleChange={setScale}
                    showPagination={isPdf}
                />
            </div>

            {/* SCROLLABLE CONTENT BODY */}
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-7xl mx-auto p-4 sm:p-8 space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-6">
                        <div className="order-1 lg:order-2 lg:col-span-3">
                            <Card
                                className="border-gray-200 overflow-hidden flex flex-col shadow-sm bg-white"
                                style={{ height: 'calc(100vh - 200px)', minHeight: '600px' }}
                            >
                                {isPdf && (
                                    <PdfViewer 
                                        url={resumeUrl} 
                                        scale={scale} 
                                        currentPage={currentPage} 
                                        onLoadSuccess={setNumPages} 
                                    />
                                )}
                                {isDocx && (
                                    <DocxViewer 
                                        url={resumeUrl} 
                                        scale={scale} 
                                        onLoadSuccess={setNumPages} 
                                    />
                                )}
                                {!hasResume && (
                                    <div className="flex-1 flex items-center justify-center bg-gray-100">
                                        <div className="text-center p-8">
                                            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                                            <h3 className="text-gray-900 mb-2">No Resume Available</h3>
                                        </div>
                                    </div>
                                )}
                            </Card>
                        </div>



                    {/* Sidebar — shown below PDF on mobile */}
                    <div className="order-2 lg:order-1 lg:col-span-1 space-y-4">
                        <Card className="p-6 border-gray-200 shadow-sm">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-gray-900 font-semibold">Resume Details</h3>
                                <Badge className={`${rankColor.bg} ${rankColor.text} text-[10px]`}>
                                    {(candidate.probability_score * 100).toFixed(1)}% • {rankColor.badge}
                                </Badge>
                            </div>
                            <div className="space-y-4">
                                <div>
                                    <p className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">Candidate</p>
                                    <span className="text-sm text-gray-900 block font-medium">{candidate.name}</span>
                                </div>
                                <div>
                                    <p className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">Email</p>
                                    <span className="text-xs text-gray-900 block break-all">{candidate.email}</span>
                                </div>
                                {candidate.phone && (
                                    <div>
                                        <p className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">Phone</p>
                                        <span className="text-sm text-gray-900 block">{candidate.phone}</span>
                                    </div>
                                )}
                                <div className="pt-3 border-t border-gray-100">
                                    <p className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">Ranking Tier</p>
                                    <Badge className={`${rankColor.bg} ${rankColor.text} text-[10px]`}>
                                        {candidate.gyr_tier} Tier
                                    </Badge>
                                </div>
                                <div className="pt-3 border-t border-gray-100">
                                    <p className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">Applied Date</p>
                                    <div className="flex items-center gap-2">
                                        <Calendar className="w-3.5 h-3.5 text-gray-400" />
                                        <span className="text-xs text-gray-700">
                                            {new Date(candidate.appliedDate).toLocaleDateString()}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </Card>

                        {/* Actions section inside sidebar */}
                        {!isRejected && (
                            <Card className="p-6 border-gray-200 shadow-sm">
                                <h3 className="text-gray-900 font-semibold mb-4">Decision</h3>
                                <div className="space-y-3">
                                    {!isShortlisted && (
                                        <Button
                                            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm h-10"
                                            onClick={() => onAction?.('shortlist')}
                                        >
                                            <ThumbsUp className="w-4 h-4 mr-2" />
                                            Shortlist
                                        </Button>
                                    )}
                                    {!isShortlisted && (
                                        <Button
                                            variant="outline"
                                            className="w-full hover:bg-red-50 hover:text-red-600 hover:border-red-200 h-10"
                                            onClick={() => onAction?.('reject')}
                                        >
                                            <ThumbsDown className="w-4 h-4 mr-2" />
                                            Reject
                                        </Button>
                                    )}
                                    {(isShortlisted || isRejected) && (
                                        <div className="text-center py-2 px-3 rounded-lg bg-gray-50 border border-gray-100 italic text-sm text-gray-500">
                                            {isShortlisted ? 'Already Shortlisted' : 'Candidate Rejected'}
                                        </div>
                                    )}
                                </div>
                            </Card>
                        )}
                    </div>
                </div>
            </div>
        </div>

            {/* Insights modal */}
            {insightsOpen && (
                <InsightsModal
                    data={insightsData}
                    loading={insightsLoading}
                    error={insightsError}
                    onClose={() => setInsightsOpen(false)}
                />
            )}
        </div>
    );
}
