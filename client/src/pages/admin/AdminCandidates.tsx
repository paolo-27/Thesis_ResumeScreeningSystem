import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { Candidate, JobPosting } from '../../types';
import api from '../../lib/axios';

import RankingSystem from './RankingSystem';
import CandidateList from './CandidateList';
import ShortlistedCandidates from './ShortlistedCandidates';
import RejectedCandidates from './RejectedCandidates';
import AdminResumeViewer from './AdminResumeViewer';
import { Card } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '../../components/ui/alert-dialog';
import { Search, Briefcase, Calendar, Users, TrendingUp, ArrowRight, Trash2, Plus } from 'lucide-react';
import { toast } from 'sonner';

type ViewType = 'green' | 'yellow' | 'red' | 'shortlisted' | 'rejected' | null;

export default function AdminCandidates() {
    const location = useLocation();
    const navigate = useNavigate();

    // Parse jobId from query params if any
    const searchParams = new URLSearchParams(location.search);
    const initialJobId = searchParams.get('jobId');

    const [selectedJobId, setSelectedJobId] = useState<string | null>(initialJobId);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedView, setSelectedView] = useState<ViewType>(null);
    const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);

    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [jobs, setJobs] = useState<JobPosting[]>([]);
    const [jobStats, setJobStats] = useState<Record<string, { total: number; green: number; yellow: number; red: number }>>({});

    // Delete dialog state
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [jobToDelete, setJobToDelete] = useState<string | null>(null);

    // Define fetchData BEFORE the useEffect that references it.
    // (const arrow functions are NOT hoisted — they must be declared first.)
    const fetchData = async () => {
        try {
            const [candidatesRes, jobsRes] = await Promise.all([
                api.get('/api/candidates'),
                api.get('/api/jobs')
            ]);
            setCandidates(candidatesRes.data);
            const fetchedJobs: JobPosting[] = jobsRes.data;
            setJobs(fetchedJobs);

            // Fetch live GYR stats for every job in parallel
            const statsEntries = await Promise.all(
                fetchedJobs.map(async (job) => {
                    try {
                        const statsRes = await api.get(`/api/jobs/${job.id}/stats`);
                        return [job.id, statsRes.data] as const;
                    } catch {
                        return [job.id, { total: 0, green: 0, yellow: 0, red: 0 }] as const;
                    }
                })
            );
            setJobStats(Object.fromEntries(statsEntries));
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    };

    // Sync state with URL whenever the location changes (covers both fresh
    // mounts and in-place navigation when React Router keeps this component alive).
    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const jobId = params.get('jobId');
        setSelectedJobId(jobId);
        setSelectedView(null);
        setSelectedResumeId(null);
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [location.search]);

    const handleViewSelect = (view: ViewType) => {
        setSelectedView(view);
        setSelectedResumeId(null);
    };

    const handleResumeSelect = (id: string) => {
        setSelectedResumeId(id);
    };

    const handleBack = () => {
        if (selectedResumeId) {
            setSelectedResumeId(null);
        } else if (selectedView) {
            setSelectedView(null);
        } else if (selectedJobId) {
            setSelectedJobId(null);
            navigate('/admin/candidates'); // Clear the URL param
        }
    };

    const handleResumeAction = async (action: 'shortlist' | 'reject') => {
        if (!selectedResumeId) return;
        const newStatus = action === 'shortlist' ? 'Shortlisted' : 'Rejected';
        try {
            await api.patch(`/api/candidates/${selectedResumeId}`, { status: newStatus });
            setCandidates(prev => prev.map(c => c.id === selectedResumeId ? { ...c, status: newStatus } : c));
            setSelectedResumeId(null);
        } catch (error) {
            console.error('Error updating candidate:', error);
        }
    };

    const handleDeleteClick = (jobId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setJobToDelete(jobId);
        setDeleteDialogOpen(true);
    };

    const handleDeleteConfirm = () => {
        if (jobToDelete) {
            api.delete(`/api/jobs/${jobToDelete}`)
                .then(() => {
                    const deletedJob = jobs.find(job => job.id === jobToDelete);
                    toast.success(`Job posting "${deletedJob?.title}" has been deleted successfully`);
                    fetchData();
                })
                .catch(() => toast.error('Failed to delete job posting'))
                .finally(() => {
                    setDeleteDialogOpen(false);
                    setJobToDelete(null);
                });
        }
    };

    const handleDeleteCancel = () => {
        setDeleteDialogOpen(false);
        setJobToDelete(null);
    };

    const formatDate = (dateString: string) => {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now.getTime() - date.getTime());
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
        return `${Math.floor(diffDays / 30)} months ago`;
    };

    const filteredJobs = jobs.filter(job =>
        job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        job.department.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // ── Nested views: resume viewer, candidate list, ranking system ────────────

    const job = jobs.find(j => j.id === selectedJobId);
    const jobCandidates = candidates.filter(
        c => c.applied_job_id === selectedJobId || c.applied_job_id === String(selectedJobId)
    );

    if (selectedJobId && selectedResumeId) {
        return (
            <AdminResumeViewer
                candidateId={selectedResumeId}
                onBack={handleBack}
                onAction={handleResumeAction}
            />
        );
    }

    if (selectedJobId && selectedView) {
        if (selectedView === 'shortlisted') {
            return (
                <ShortlistedCandidates
                    jobId={selectedJobId}
                    candidates={jobCandidates.filter(c => c.status === 'Shortlisted')}
                    onResumeSelect={handleResumeSelect}
                    onBack={handleBack}
                />
            );
        }

        if (selectedView === 'rejected') {
            return (
                <RejectedCandidates
                    jobId={selectedJobId}
                    candidates={jobCandidates.filter(c => c.status === 'Rejected')}
                    onResumeSelect={handleResumeSelect}
                    onBack={handleBack}
                />
            );
        }

        // green, yellow, red tier mappings
        const tierCandidates = jobCandidates.filter(c => {
            if (c.gyr_tier) {
                if (selectedView === 'green') return c.gyr_tier === 'Green';
                if (selectedView === 'yellow') return c.gyr_tier === 'Yellow';
                return c.gyr_tier === 'Red';
            }
            const score = c.probability_score || 0;
            if (selectedView === 'green') return score >= 0.7;
            if (selectedView === 'yellow') return score >= 0.4 && score < 0.7;
            return score < 0.4;
        });

        return (
            <CandidateList
                jobId={selectedJobId}
                rank={selectedView}
                candidates={tierCandidates}
                onResumeSelect={handleResumeSelect}
                onBack={handleBack}
            />
        );
    }

    if (selectedJobId) {
        return (
            <RankingSystem
                job={job}
                candidates={jobCandidates}
                onViewSelect={handleViewSelect}
                onBack={handleBack}
            />
        );
    }

    // ── Top-level: Manage Job Postings ─────────────────────────────────────────

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-gray-900 mb-2 font-bold text-3xl">Candidates</h1>
                    <p className="text-gray-500">Manage job postings and review active roles.</p>
                </div>
                <Button
                    className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-2"
                    onClick={() => navigate('/admin/jobs')}
                >
                    <Plus className="w-4 h-4" />
                    Create Job
                </Button>
            </div>

            {/* Search Bar */}
            <div className="mb-6">
                <div className="relative max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <Input
                        placeholder="Search job postings..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10 h-12 border-gray-200"
                    />
                </div>
            </div>

            {/* Job Postings Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredJobs.map((job) => {
                    const stats = jobStats[job.id] ?? { total: 0, green: 0, yellow: 0, red: 0 };
                    const { total: candidatesCount, green: greenCount, yellow: yellowCount, red: redCount } = stats;

                    return (
                        <Card key={job.id} className="border-gray-200 hover:shadow-lg transition-all duration-200 cursor-pointer group relative">
                            <div className="p-6">
                                <div className="flex items-start justify-between mb-4 gap-4">
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-gray-900 font-bold mb-1 group-hover:text-emerald-600 transition-colors">
                                            {job.title}
                                        </h3>
                                        <p className="text-sm text-gray-500">{job.department}</p>
                                    </div>
                                    <div className="flex items-start gap-2 flex-shrink-0 pt-0.5">
                                        <Badge
                                            variant="secondary"
                                            className={`h-fit ${job.status === 'Active' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-700'}`}
                                        >
                                            {job.status}
                                        </Badge>
                                        <button
                                            onClick={(e) => handleDeleteClick(job.id, e)}
                                            className="text-red-500 hover:text-red-700 transition-colors p-1 rounded hover:bg-red-50 flex-shrink-0 -mt-1"
                                            title="Delete job posting"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
                                    <Calendar className="w-4 h-4" />
                                    <span>Posted {formatDate(job.postedDate)}</span>
                                </div>

                                <div className="flex items-center gap-2 text-sm text-gray-600 mb-4">
                                    <Users className="w-4 h-4" />
                                    <span>{candidatesCount} candidates screened</span>
                                </div>

                                {/* GYR Ranking Distribution */}
                                <div className="space-y-2 mb-4">
                                    <div className="flex items-center justify-between text-sm">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                                            <span className="text-gray-600">Top 30%</span>
                                        </div>
                                        <span className="text-gray-900">{greenCount}</span>
                                    </div>
                                    <div className="flex items-center justify-between text-sm">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                                            <span className="text-gray-600">Middle 50%</span>
                                        </div>
                                        <span className="text-gray-900">{yellowCount}</span>
                                    </div>
                                    <div className="flex items-center justify-between text-sm">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-red-500"></div>
                                            <span className="text-gray-600">Bottom 20%</span>
                                        </div>
                                        <span className="text-gray-900">{redCount}</span>
                                    </div>
                                </div>

                                <Button
                                    onClick={() => {
                                        setSelectedJobId(job.id);
                                        navigate(`/admin/candidates?jobId=${job.id}`);
                                    }}
                                    className="w-full bg-emerald-600 hover:bg-emerald-700 group-hover:bg-emerald-700 text-white"
                                >
                                    View Rankings
                                    <ArrowRight className="w-4 h-4 ml-2" />
                                </Button>
                            </div>
                        </Card>
                    );
                })}
            </div>

            {filteredJobs.length === 0 && (
                <Card className="p-12 border-gray-200 border-dashed">
                    <div className="text-center">
                        <Briefcase className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                        <h3 className="text-gray-900 mb-2">No job postings found</h3>
                        <p className="text-gray-500 mb-4">
                            {searchQuery ? 'Try adjusting your search query' : 'Create your first job posting to get started.'}
                        </p>
                        {!searchQuery && (
                            <Button
                                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                                onClick={() => navigate('/admin/jobs')}
                            >
                                <Plus className="w-4 h-4 mr-2" />
                                Create Job Posting
                            </Button>
                        )}
                    </div>
                </Card>
            )}

            {/* Delete Confirmation Dialog */}
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete Job Posting</AlertDialogTitle>
                        <AlertDialogDescription>
                            Are you sure you want to delete this job posting? This action cannot be undone.
                            All candidate data associated with this job will also be removed.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={handleDeleteCancel}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDeleteConfirm}
                            className="bg-red-600 hover:bg-red-700 text-white"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
