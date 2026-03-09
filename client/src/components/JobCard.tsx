import React from 'react';
import type { JobPosting } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './ui/card';
import { Button } from './ui/button';
import { MapPin, Briefcase, Users } from 'lucide-react';

interface JobCardProps {
    job: JobPosting;
    onApply?: (jobId: string) => void;
    isAdmin?: boolean;
}

export default function JobCard({ job, onApply, isAdmin }: JobCardProps) {
    return (
        <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
                <div className="flex justify-between items-start">
                    <div>
                        <CardTitle className="text-xl text-gray-900">{job.title}</CardTitle>
                        <CardDescription className="text-emerald-600 font-medium mt-1">
                            {job.department}
                        </CardDescription>
                    </div>
                    {isAdmin && (
                        <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-semibold">
                            {job.status}
                        </span>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                <div className="flex gap-4 text-sm text-gray-500 mb-4">
                    <div className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        {job.location}
                    </div>
                    <div className="flex items-center gap-1">
                        <Briefcase className="w-4 h-4" />
                        {job.type}
                    </div>
                    {isAdmin && (
                        <div className="flex items-center gap-1">
                            <Users className="w-4 h-4" />
                            {job.applicantsCount} Applicants
                        </div>
                    )}
                </div>
                <p className="text-gray-600 line-clamp-2 text-sm">
                    {job.description}
                </p>
            </CardContent>
            <CardFooter>
                <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={() => onApply && onApply(job.id)}
                >
                    {isAdmin ? 'View Details' : 'Apply Now'}
                </Button>
            </CardFooter>
        </Card>
    );
}
