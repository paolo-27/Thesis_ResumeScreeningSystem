import React, { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { renderAsync } from 'docx-preview';
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
    Share2,
    ChevronLeft,
    ChevronRight,
    ZoomIn,
    ZoomOut,
    Loader2,
    AlertCircle,
} from 'lucide-react';
import type { Candidate } from '../../types';
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

// ─── PDF viewer sub-component ────────────────────────────────────────────────
function PdfViewer({ url }: { url: string }) {
    const [numPages, setNumPages] = useState<number>(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [scale, setScale] = useState(1.2);
    const [pdfError, setPdfError] = useState<string | null>(null);

    return (
        <div className="flex flex-col h-full">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b border-gray-200 flex-shrink-0">
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage <= 1}
                        className="h-7 px-2"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <span className="text-sm text-gray-600 min-w-[80px] text-center">
                        {numPages > 0 ? `${currentPage} / ${numPages}` : '—'}
                    </span>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))}
                        disabled={currentPage >= numPages}
                        className="h-7 px-2"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </Button>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setScale(s => Math.max(0.5, +(s - 0.2).toFixed(1)))}
                        className="h-7 px-2"
                    >
                        <ZoomOut className="w-4 h-4" />
                    </Button>
                    <span className="text-sm text-gray-600 min-w-[45px] text-center">
                        {Math.round(scale * 100)}%
                    </span>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setScale(s => Math.min(3, +(s + 0.2).toFixed(1)))}
                        className="h-7 px-2"
                    >
                        <ZoomIn className="w-4 h-4" />
                    </Button>
                </div>
            </div>

            {/* PDF canvas area */}
            <div className="flex-1 overflow-auto flex justify-center bg-gray-200 py-4">
                {pdfError ? (
                    <div className="flex flex-col items-center justify-center text-center p-8">
                        <AlertCircle className="w-10 h-10 text-red-400 mb-3" />
                        <p className="text-red-600 font-medium mb-1">Failed to load PDF</p>
                        <p className="text-gray-500 text-sm">{pdfError}</p>
                    </div>
                ) : (
                    <Document
                        file={url}
                        onLoadSuccess={({ numPages }) => {
                            setNumPages(numPages);
                            setCurrentPage(1);
                        }}
                        onLoadError={(err) => setPdfError(err.message)}
                        loading={
                            <div className="flex flex-col items-center justify-center py-20 gap-3">
                                <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
                                <span className="text-gray-500 text-sm">Loading PDF…</span>
                            </div>
                        }
                    >
                        <Page
                            pageNumber={currentPage}
                            scale={scale}
                            className="shadow-lg"
                            renderAnnotationLayer
                            renderTextLayer
                        />
                    </Document>
                )}
            </div>
        </div>
    );
}

// ─── DOCX viewer sub-component ───────────────────────────────────────────────
function DocxViewer({ url }: { url: string }) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [docxError, setDocxError] = useState<string | null>(null);
    const [docxLoading, setDocxLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;

        async function loadDocx() {
            try {
                const res = await fetch(url);
                if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                const buffer = await res.arrayBuffer();
                if (cancelled || !containerRef.current) return;

                // Clear previous render
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
                if (!cancelled) setDocxLoading(false);
            } catch (err: unknown) {
                if (!cancelled) {
                    setDocxError(err instanceof Error ? err.message : 'Unknown error');
                    setDocxLoading(false);
                }
            }
        }

        loadDocx();
        return () => { cancelled = true; };
    }, [url]);

    return (
        <div className="flex-1 overflow-auto bg-gray-200 py-4 px-4">
            {docxLoading && !docxError && (
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                    <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
                    <span className="text-gray-500 text-sm">Loading document…</span>
                </div>
            )}
            {docxError && (
                <div className="flex flex-col items-center justify-center text-center p-8">
                    <AlertCircle className="w-10 h-10 text-red-400 mb-3" />
                    <p className="text-red-600 font-medium mb-1">Failed to load document</p>
                    <p className="text-gray-500 text-sm">{docxError}</p>
                </div>
            )}
            {/* docx-preview renders into this div */}
            <div
                ref={containerRef}
                className={`docx-container mx-auto ${docxLoading ? 'hidden' : ''}`}
            />
        </div>
    );
}

// ─── Main component ──────────────────────────────────────────────────────────
export default function AdminResumeViewer({ candidateId, onBack, onAction }: AdminResumeViewerProps) {
    const [candidate, setCandidate] = useState<Candidate | null>(null);
    const [loading, setLoading] = useState(true);

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

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-emerald-600 mr-3" />
                <p className="text-gray-500">Loading candidate data…</p>
            </div>
        );
    }

    if (!candidate) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
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

    // Build the resume URL pointing at our new backend endpoint
    const resumeUrl = `${api.defaults.baseURL ?? ''}/api/candidates/${candidateId}/resume`;

    // Determine file type from the stored filename/path
    const resumeFilename = candidate.resume_url ?? '';
    const isPdf = resumeFilename.toLowerCase().endsWith('.pdf');
    const isDocx = resumeFilename.toLowerCase().endsWith('.docx');
    const hasResume = isPdf || isDocx;

    // Strip the '<candidate_id>_' prefix so we show the original filename
    const storedBasename = resumeFilename.split('/').pop() ?? '';
    const originalFilename = storedBasename.includes('_')
        ? storedBasename.split('_').slice(1).join('_')
        : storedBasename;

    const handleDownload = () => {
        const a = document.createElement('a');
        a.href = resumeUrl;
        a.download = originalFilename || 'resume';
        a.click();
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-8 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Button
                                variant="ghost"
                                onClick={onBack}
                                className="text-gray-600 hover:text-gray-900"
                            >
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back
                            </Button>
                            <div className="h-8 w-px bg-gray-300" />
                            <div className="flex items-center gap-3">
                                <FileText className="w-5 h-5 text-gray-600" />
                                <h2 className="text-gray-900">
                                    {originalFilename || `${candidate.name}_Resume`}
                                </h2>
                                <Badge className={`${rankColor.bg} ${rankColor.text}`}>
                                    {(candidate.probability_score * 100).toFixed(2)}% • {rankColor.badge}
                                </Badge>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" onClick={handleDownload} disabled={!hasResume}>
                                <Download className="w-4 h-4 mr-2" />
                                Download
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto p-8">
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {/* Sidebar */}
                    <div className="lg:col-span-1 space-y-4">
                        <Card className="p-6 border-gray-200">
                            <h3 className="text-gray-900 mb-4">Resume Details</h3>
                            <div className="space-y-3">
                                <div>
                                    <p className="text-xs text-gray-500 mb-1">Candidate Name</p>
                                    <span className="text-sm text-gray-900">{candidate.name}</span>
                                </div>
                                <div>
                                    <p className="text-xs text-gray-500 mb-1">Email</p>
                                    <span className="text-sm text-gray-900">{candidate.email}</span>
                                </div>
                                {candidate.phone && (
                                    <div>
                                        <p className="text-xs text-gray-500 mb-1">Phone</p>
                                        <span className="text-sm text-gray-900">{candidate.phone}</span>
                                    </div>
                                )}
                                <div className="pt-2 border-t border-gray-100">
                                    <p className="text-xs text-gray-500 mb-1">Match Score</p>
                                    <div className="flex items-center gap-2">
                                        <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                                        <span className="text-gray-900">
                                            {(candidate.probability_score * 100).toFixed(2)}%
                                        </span>
                                    </div>
                                </div>
                                <div>
                                    <p className="text-xs text-gray-500 mb-1">Uploaded</p>
                                    <div className="flex items-center gap-2">
                                        <Calendar className="w-4 h-4 text-gray-400" />
                                        <span className="text-sm text-gray-900">
                                            {new Date(candidate.appliedDate).toLocaleDateString('en-US', {
                                                month: 'long',
                                                day: 'numeric',
                                                year: 'numeric',
                                            })}
                                        </span>
                                    </div>
                                </div>
                                <div>
                                    <p className="text-xs text-gray-500 mb-1">Ranking Tier</p>
                                    <Badge className={`${rankColor.bg} ${rankColor.text}`}>
                                        {candidate.gyr_tier}
                                    </Badge>
                                </div>
                                {hasResume && (
                                    <div>
                                        <p className="text-xs text-gray-500 mb-1">File Type</p>
                                        <Badge className="bg-gray-100 text-gray-700">
                                            {isPdf ? 'PDF' : 'DOCX'}
                                        </Badge>
                                    </div>
                                )}
                            </div>
                        </Card>

                        {!isRejected && (
                            <Card className="p-6 border-gray-200">
                                <h3 className="text-gray-900 mb-4">Actions</h3>
                                <div className="space-y-2">
                                    {!isShortlisted && (
                                        <Button
                                            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                                            onClick={() => onAction?.('shortlist')}
                                        >
                                            <ThumbsUp className="w-4 h-4 mr-2" />
                                            Shortlist
                                        </Button>
                                    )}
                                    {!isShortlisted && (
                                        <Button
                                            variant="outline"
                                            className="w-full hover:bg-red-50 hover:text-red-600 hover:border-red-200"
                                            onClick={() => onAction?.('reject')}
                                        >
                                            <ThumbsDown className="w-4 h-4 mr-2" />
                                            Reject
                                        </Button>
                                    )}
                                </div>
                            </Card>
                        )}

                        {isRejected && (
                            <Card className="p-6 border-gray-200 bg-gray-50">
                                <h3 className="text-gray-900 mb-2">Rejected Candidate</h3>
                                <p className="text-sm text-gray-600">
                                    This candidate has been rejected for this position.
                                </p>
                            </Card>
                        )}
                    </div>

                    {/* Main Content — Resume Viewer */}
                    <div className="lg:col-span-3">
                        <Card className="border-gray-200 overflow-hidden flex flex-col" style={{ height: 'calc(100vh - 200px)' }}>
                            {isPdf && <PdfViewer url={resumeUrl} />}
                            {isDocx && <DocxViewer url={resumeUrl} />}
                            {!hasResume && (
                                <div className="flex-1 flex items-center justify-center bg-gray-100">
                                    <div className="text-center p-12">
                                        <div className="w-24 h-24 bg-white rounded-2xl shadow-lg flex items-center justify-center mx-auto mb-6">
                                            <FileText className="w-12 h-12 text-gray-400" />
                                        </div>
                                        <h3 className="text-gray-900 mb-2">No Resume Available</h3>
                                        <p className="text-gray-500 max-w-md">
                                            No resume file was found for this candidate.
                                            The file may not have been uploaded or is in an unsupported format.
                                        </p>
                                    </div>
                                </div>
                            )}
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
}
