import React, { useState, useEffect } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import {
  Briefcase,
  Users,
  TrendingUp,
  Clock,
  ArrowUpRight,
  FileText,
  CheckCircle2
} from 'lucide-react';
import { Progress } from '../../components/ui/progress';
import { useNavigate } from 'react-router-dom';
import type { JobPosting } from '../../types';
import api from '../../lib/axios';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    activeJobs: 0,
    totalCandidates: 0,
    averageMatchScore: 0,
    pendingReviews: 0
  });
  const [recentJobs, setRecentJobs] = useState<JobPosting[]>([]);
  const [jobStats, setJobStats] = useState<Record<string, { total: number; green: number; yellow: number; red: number }>>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [jobsRes, candidatesRes] = await Promise.all([
          api.get('/api/jobs'),
          api.get('/api/candidates')
        ]);

        const jobs = jobsRes.data;
        const candidates = candidatesRes.data;

        const activeJobs = jobs.filter((j: any) => j.status === 'Active').length;
        const totalCandidates = candidates.length;

        let avgScore = 0;
        if (totalCandidates > 0) {
          // Normalise each score: if stored as 0–1, use as-is; if somehow stored
          // as 0–100, divide back down. Then clamp to [0, 1] to be safe.
          const normalise = (s: number) => {
            const v = s > 1 ? s / 100 : s;   // handle legacy percentage values
            return Math.min(1, Math.max(0, v)); // clamp to [0, 1]
          };
          const totalScore = candidates.reduce(
            (acc: number, c: any) => acc + normalise(c.probability_score || 0),
            0
          );
          avgScore = Math.round((totalScore / totalCandidates) * 100);
        }

        // Backend sets status = 'Pending' on new applications (not 'Applied')
        const pendingReviews = candidates.filter((c: any) => c.status === 'Pending').length;

        // Sort jobs by postedDate descending and take top 4 to match design
        const sortedJobs = [...jobs].sort((a: any, b: any) =>
          new Date(b.postedDate).getTime() - new Date(a.postedDate).getTime()
        ).slice(0, 4);

        setStats({ activeJobs, totalCandidates, averageMatchScore: avgScore, pendingReviews });
        setRecentJobs(sortedJobs);

        // Fetch live per-job stats for the dashboard cards
        const statsEntries = await Promise.all(
          sortedJobs.map(async (job: any) => {
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
        console.error("Error fetching dashboard data:", error);
      }
    };

    fetchData();
    // Poll every 3 seconds for real-time updates
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const statsCards = [
    {
      title: 'Active Jobs',
      value: stats.activeJobs.toString(),
      change: 'Live from API',
      icon: Briefcase,
      color: 'emerald'
    },
    {
      title: 'Total Candidates',
      value: stats.totalCandidates.toString(),
      change: 'Live from API',
      icon: Users,
      color: 'blue'
    },
    {
      title: 'Avg. Match Score',
      value: `${stats.averageMatchScore}%`,
      change: 'Live from API',
      icon: TrendingUp,
      color: 'purple'
    },
    {
      title: 'Pending Reviews',
      value: stats.pendingReviews.toString(),
      change: 'Requires attention',
      icon: Clock,
      color: 'orange'
    }
  ];

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-gray-900 mb-2">Dashboard Overview</h1>
        <p className="text-gray-500">Welcome back! Here's what's happening with your recruitment.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statsCards.map((stat) => {
          // If the stat is Total Candidates and it's 0, we'll conditionally change its value or appearance
          const isZeroCandidates = stat.title === 'Total Candidates' && stats.totalCandidates === 0;

          return (
            <Card key={stat.title} className={`p-6 border-gray-200 transition-all ${isZeroCandidates ? 'opacity-50 grayscale' : 'hover:shadow-lg'}`}>
              <div className="flex items-start justify-between mb-4">
                <div className={`w-12 h-12 rounded-xl bg-${stat.color}-100 flex items-center justify-center`}>
                  <stat.icon className={`w-6 h-6 text-${stat.color}-600`} />
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">{stat.title}</p>
                <p className="text-gray-900 mb-1 font-bold text-2xl">
                  {isZeroCandidates ? '-' : stat.value}
                </p>
                <p className="text-xs text-gray-400">{isZeroCandidates ? 'No candidates yet' : stat.change}</p>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Recent Jobs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card className="border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-gray-900 mb-1 font-bold">Recent Job Postings</h3>
                  <p className="text-sm text-gray-500">Track your active job openings and candidate progress</p>
                </div>
              </div>
            </div>
            <div className="divide-y divide-gray-200">
              {recentJobs.length === 0 && <div className="p-6 text-gray-500 text-center">No active jobs found.</div>}
              {recentJobs.map((job: any) => {
                const jobStat = jobStats[job.id] ?? { total: 0, green: 0, yellow: 0, red: 0 };
                const candidatesCount = jobStat.total;
                const matchedCount = jobStat.green;

                return (
                  <div key={job.id} className="p-6 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <h4 className="text-gray-900 mb-1 font-medium">{job.title}</h4>
                        <p className="text-sm text-gray-500">{job.department} • Posted {new Date(job.postedDate).toLocaleDateString()}</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate('/admin/candidates')}
                        className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                      >
                        View Details
                        <ArrowUpRight className="w-4 h-4 ml-1" />
                      </Button>
                    </div>
                    <div className="flex items-center gap-6 text-sm">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-600">{candidatesCount} candidates</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                        <span className="text-gray-600">{matchedCount} matched</span>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                        <span>Match Rate</span>
                        <span>{candidatesCount > 0 ? Math.round((matchedCount / candidatesCount) * 100) : 0}%</span>
                      </div>
                      <Progress value={candidatesCount > 0 ? (matchedCount / candidatesCount) * 100 : 0} className="h-2" />
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="space-y-6">
          <Card className="p-6 border-gray-200 bg-gradient-to-br from-emerald-50 to-emerald-100/50">
            <FileText className="w-10 h-10 text-emerald-600 mb-4" />
            <h3 className="text-gray-900 mb-2 font-bold">Create New Job</h3>
            <p className="text-sm text-gray-600 mb-4">Start screening candidates for a new position</p>
            <Button
              className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={() => navigate('/admin/jobs')}
            >
              Create Job Posting
            </Button>
          </Card>

          <Card className="p-6 border-gray-200">
            <h3 className="text-gray-900 mb-4 font-bold">Recent Activity</h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900">Backend API Connected</p>
                  <p className="text-xs text-gray-500">Live system status</p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
