import React, { useState, useEffect } from 'react';
import VeridianLogo from '../admin/auth/VeridianLogo';
import { JobCard } from '../../components/applicant/JobCard';
import { JobDetailsDialog } from '../../components/applicant/JobDetailsDialog';
import type { JobPosting } from '../../types';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { LogIn, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../../lib/axios';

interface MappedJob {
    id: string;
    title: string;
    company: string;
    location: string;
    type: string;
    salary: string;
    posted: string;
    description: string;
    requirements: string[];
    responsibilities: string[];
}

export default function ApplicantLanding() {
    const [searchQuery, setSearchQuery] = useState("");
    const [jobs, setJobs] = useState<MappedJob[]>([]);
    const [selectedJob, setSelectedJob] = useState<MappedJob | null>(null);
    const [isDialogOpen, setIsDialogOpen] = useState(false);

    useEffect(() => {
        api.get('/api/jobs')
            .then(res => {
                const mappedJobs = res.data.map((job: any) => ({
                    id: job.id,
                    title: job.title,
                    company: "Veridian Innovations Inc.",
                    location: job.location,
                    type: job.type,
                    salary: "Competitive",
                    posted: new Date(job.postedDate).toLocaleDateString(),
                    description: job.description || "No description provided.",
                    requirements: job.requirements ? [job.requirements] : [],
                    responsibilities: []
                }));
                // Filter out closed/draft jobs if necessary, for now returning all active
                setJobs(mappedJobs.filter((j: any) => j.status !== 'Closed'));
            })
            .catch(err => console.error("Error fetching jobs:", err));
    }, []);

    const filteredJobs = jobs.filter(
        (job) =>
            job.title
                .toLowerCase()
                .includes(searchQuery.toLowerCase()) ||
            job.company
                .toLowerCase()
                .includes(searchQuery.toLowerCase()) ||
            job.location
                .toLowerCase()
                .includes(searchQuery.toLowerCase()),
    );

    const handleJobClick = (job: MappedJob) => {
        setSelectedJob(job);
        setIsDialogOpen(true);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-50 font-sans flex flex-col">
            {/* Header */}
            <header className="bg-gradient-to-r from-emerald-600 to-teal-600 shadow-lg sticky top-0 z-10 w-full">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <VeridianLogo white className="h-10" />
                            <div className="hidden sm:block border-l border-emerald-400 pl-4 h-8">
                                <span className="text-emerald-50 text-sm font-medium tracking-wide">
                                    Job Portal
                                </span>
                            </div>
                        </div>

                    </div>
                    <div className="mt-8 text-center sm:text-left sm:ml-12 lg:ml-2">
                        <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2">
                            Join Our Mission
                        </h1>
                        <p className="text-emerald-50 max-w-2xl text-lg">
                            Discover opportunities to build innovative solutions that change the way companies hire.
                        </p>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12">
                {/* Search Section */}
                <div className="mb-8">
                    <div className="relative max-w-2xl mx-auto sm:mx-0">
                        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                        <Input
                            type="text"
                            placeholder="Search jobs by title, company, or location..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-12 py-6 bg-white shadow-sm border-emerald-200 focus:border-emerald-500 focus:ring-emerald-500 text-lg rounded-xl"
                        />
                    </div>
                </div>

                {/* Job Count */}
                <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <h2 className="text-xl font-semibold text-gray-800">
                            Open Positions
                        </h2>
                        <Badge
                            variant="secondary"
                            className="bg-emerald-100 text-emerald-800 px-3 py-1 text-sm font-medium rounded-full"
                        >
                            {filteredJobs.length} {filteredJobs.length === 1 ? 'Job' : 'Jobs'}
                        </Badge>
                    </div>
                </div>

                {/* Job Listings */}
                {filteredJobs.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {filteredJobs.map((job) => (
                            <JobCard
                                key={job.id}
                                job={job}
                                onClick={() => handleJobClick(job)}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-20 bg-white rounded-2xl shadow-sm border border-emerald-50">
                        <p className="text-gray-500 text-lg">
                            No jobs found matching your search criteria.
                        </p>
                    </div>
                )}
            </main>

            {/* Application Modal via Job Details Dialog */}
            <JobDetailsDialog
                job={selectedJob}
                open={isDialogOpen}
                onOpenChange={setIsDialogOpen}
            />
        </div>
    );
}
