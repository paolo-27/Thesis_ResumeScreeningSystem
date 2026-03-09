import { useState } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { ArrowLeft, Search, FileText, Download, CheckCircle2, ArrowUpRight, Mail, Calendar } from 'lucide-react';
import type { Candidate } from "../../types";

interface ShortlistedCandidatesProps {
  jobId: string;
  candidates: Candidate[];
  onResumeSelect: (resumeId: string) => void;
  onBack: () => void;
}

export default function ShortlistedCandidates({ jobId, candidates, onResumeSelect, onBack }: ShortlistedCandidatesProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCandidates = candidates.filter(candidate =>
    candidate.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getScoreBadgeColor = (score: number) => {
    if (score >= 90) return 'bg-emerald-100 text-emerald-700';
    if (score >= 80) return 'bg-blue-100 text-blue-700';
    if (score >= 70) return 'bg-yellow-100 text-yellow-700';
    return 'bg-red-100 text-red-700';
  };

  const getRankBadge = (score: number) => {
    if (score >= 80) return { label: 'Top 30%', color: 'bg-emerald-100 text-emerald-700' };
    if (score >= 60) return { label: 'Middle 50%', color: 'bg-yellow-100 text-yellow-700' };
    return { label: 'Bottom 20%', color: 'bg-red-100 text-red-700' };
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Button
          variant="ghost"
          onClick={onBack}
          className="mb-4 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Rankings
        </Button>
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-gray-900 font-bold text-3xl">Shortlisted Candidates</h1>
          <Badge className="bg-blue-100 text-blue-700 border-none font-bold py-1">
            {filteredCandidates.length} Resumes
          </Badge>
        </div>
        <p className="text-gray-500">Candidates you've selected for the next round</p>
      </div>

      {/* Search and Actions */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <Input
            placeholder="Search shortlisted candidates by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-12 border-gray-200"
          />
        </div>
        <Button variant="outline" className="h-12 border-gray-200 text-gray-600 hover:bg-gray-50">
          <Download className="w-4 h-4 mr-2" />
          Export All
        </Button>
        <Button className="h-12 bg-blue-600 hover:bg-blue-700 text-white">
          <Mail className="w-4 h-4 mr-2" />
          Contact All
        </Button>
      </div>

      {/* Summary Card */}
      <Card className="p-6 bg-blue-50 border-blue-200 border mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-600 flex items-center justify-center">
              <CheckCircle2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-gray-900 mb-1 font-bold">Shortlisted Summary</h3>
              <p className="text-sm text-gray-600">
                Average Score: <span className="font-medium">
                  {filteredCandidates.length ? Math.round(filteredCandidates.reduce((sum, c) => sum + (c.probability_score || 0), 0) / filteredCandidates.length) : 0}%
                </span>
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500 mb-1 font-medium">Total Shortlisted</p>
            <p className="text-3xl font-bold text-gray-900">{filteredCandidates.length}</p>
          </div>
        </div>
      </Card>

      {/* Candidate Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredCandidates.map((candidate, index) => {
          const rankBadge = getRankBadge(candidate.probability_score || 0);
          return (
            <Card
              key={candidate.id}
              className="border-gray-200 hover:shadow-lg transition-all duration-200 cursor-pointer group"
              onClick={() => onResumeSelect(candidate.id)}
            >
              <div className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-100 to-blue-200 rounded-lg flex items-center justify-center">
                      <FileText className="w-6 h-6 text-blue-600" />
                    </div>
                    <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-white" />
                    </div>
                  </div>
                  <Badge className={getScoreBadgeColor(candidate.probability_score || 0)}>
                    {Math.round(candidate.probability_score || 0)}%
                  </Badge>
                </div>

                <h4 className="text-gray-900 mb-1 font-bold group-hover:text-blue-600 transition-colors truncate">
                  {candidate.name}
                </h4>
                <p className="text-sm text-gray-500 mb-3 truncate">{candidate.email}</p>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Original Rank</span>
                    <Badge variant="secondary" className={rankBadge.color}>
                      {rankBadge.label}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Applied Date</span>
                    <div className="flex items-center gap-1 text-gray-700 font-medium">
                      <Calendar className="w-4 h-4" />
                      <span>{formatDate(candidate.appliedDate)}</span>
                    </div>
                  </div>
                </div>

                <Button
                  variant="outline"
                  className="w-full text-blue-600 group-hover:bg-blue-50 group-hover:text-blue-700 group-hover:border-blue-300 transition-colors"
                >
                  View Details
                  <ArrowUpRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </Card>
          );
        })}
      </div>

      {filteredCandidates.length === 0 && (
        <Card className="p-12 border-gray-200 border-dashed">
          <div className="text-center">
            <CheckCircle2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-gray-900 font-bold mb-2">No shortlisted candidates yet</h3>
            <p className="text-gray-500 mb-6 max-w-sm mx-auto">Start reviewing candidates and shortlist the ones you want to proceed with</p>
            <Button onClick={onBack} variant="outline" className="border-gray-300">
              Back to Rankings
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
