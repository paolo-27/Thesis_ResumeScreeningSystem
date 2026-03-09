export interface Resume {
    id: string;
    name: string;
    score: number;
    status: 'Pending' | 'Shortlisted' | 'Rejected' | string;
    role?: string;
    appliedDate?: string;
    matchScore?: number;
    experience?: string;
    education?: string;
    skills?: string[];
    email?: string;
    phone?: string;
    location?: string;
    about?: string;
    avatar?: string;
    fileSize?: string;
}

export interface Job {
    id: string;
    title: string;
    department: string;
    location: string;
    type: string;
    status: 'Active' | 'Draft' | 'Closed' | string;
    applicants: number;
    postedDate: string;
    description?: string;
}

export interface User {
    id: string;
    name: string;
    email: string;
    role: string;
    avatar?: string;
}

export interface JobPosting {
    id: string;
    title: string;
    department: string;
    location: string;
    type: string;
    status: 'Active' | 'Draft' | 'Closed' | string;
    applicantsCount: number;
    postedDate: string;
    description: string;
    requirements?: string[];
}

export type GYRTier = 'Green' | 'Yellow' | 'Red';

export interface Candidate {
    id: string;
    name: string;
    email: string;
    phone?: string;
    applied_job_id: string;
    probability_score: number;
    gyr_tier: GYRTier;
    match_score?: number;
    status: 'Pending' | 'Shortlisted' | 'Rejected' | string;
    resume_url?: string;
    appliedDate: string;
    experience?: string;
    education?: string;
    skills?: string[];
}
