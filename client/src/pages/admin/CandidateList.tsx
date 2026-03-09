import { useState } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { ArrowLeft, Search, FileText, Download, Star, TrendingUp, ArrowUpRight } from 'lucide-react';
import type { Candidate } from "../../types";

interface CandidateListProps {
  jobId: string;
  rank: 'green' | 'yellow' | 'red';
  candidates: Candidate[];
  onResumeSelect: (resumeId: string) => void;
  onBack: () => void;
}

export default function CandidateList({ jobId, rank, candidates, onResumeSelect, onBack }: CandidateListProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const getRankData = () => {
    if (rank === 'green') {
      return { label: 'Top Tier (Top 30%)', color: 'emerald', bg: 'bg-emerald-50', text: 'text-emerald-700' };
    }
    if (rank === 'yellow') {
      return { label: 'Good Fit (Middle 50%)', color: 'yellow', bg: 'bg-yellow-50', text: 'text-yellow-700' };
    }
    return { label: 'Below Threshold (Bottom 20%)', color: 'red', bg: 'bg-red-50', text: 'text-red-700' };
  };

  const rankData = getRankData();

  const filteredCandidates = candidates.filter(candidate =>
    candidate.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // score is 0.0–1.0; convert to 0–100 for threshold comparison
  const getScoreBadgeColor = (score: number) => {
    const pct = score * 100;
    if (pct >= 90) return 'bg-emerald-100 text-emerald-700';
    if (pct >= 80) return 'bg-blue-100 text-blue-700';
    if (pct >= 70) return 'bg-yellow-100 text-yellow-700';
    return 'bg-red-100 text-red-700';
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
          <h1 className="text-gray-900">Ranked Candidates</h1>
          <Badge className={`border-none ${rankData.bg} ${rankData.text}`}>
            {rankData.label}
          </Badge>
        </div>
        <p className="text-gray-500">Review candidates ranked by the XGBoost algorithm</p>
      </div>

      {/* Search and Filters */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <Input
            placeholder="Search candidates by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-12 border-gray-200"
          />
        </div>
        <Button variant="outline" className="h-12">
          <Download className="w-4 h-4 mr-2" />
          Export List
        </Button>
      </div>

      {/* Summary Stats */}
      <Card className="p-6 bg-gradient-to-br border-gray-200 from-gray-50 to-white mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl bg-${rankData.color}-100 flex items-center justify-center`}>
              <TrendingUp className={`w-6 h-6 text-${rankData.color}-600`} />
            </div>
            <div>
              <h3 className="text-gray-900 mb-1">Tier Details</h3>
              <p className="text-sm text-gray-600">
                Average Score: <span className="font-medium">
                  {candidates.length ? Math.round((candidates.reduce((sum, c) => sum + (c.probability_score || 0), 0) / candidates.length) * 100) : 0}%
                </span>
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500 mb-1">Total Candidates</p>
            <p className="text-3xl font-bold text-gray-900">{candidates.length}</p>
          </div>
        </div>
      </Card>

      {/* Candidate Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredCandidates.map((candidate, index) => (
          <Card
            key={candidate.id}
            className="border-gray-200 hover:shadow-lg transition-all duration-200 cursor-pointer group relative overflow-hidden"
            onClick={() => onResumeSelect(candidate.id)}
          >
            {/* Top Rank Badge - mock conditionally to display top ranks visually */}
            {index < 3 && rank === 'green' && (
              <div className="absolute top-0 right-0">
                <div className="bg-yellow-100 text-yellow-700 text-xs font-bold px-3 py-1 rounded-bl-lg flex items-center gap-1">
                  <Star className="w-3 h-3 fill-yellow-500" />
                  Top Match
                </div>
              </div>
            )}

            <div className="p-6">
              <div className="flex items-start justify-between mb-4 mt-2">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center group-hover:bg-emerald-50 transition-colors">
                    <FileText className="w-6 h-6 text-gray-500 group-hover:text-emerald-600" />
                  </div>
                </div>
                <Badge className={getScoreBadgeColor(candidate.probability_score || 0)}>
                  {Math.round((candidate.probability_score || 0) * 100)}% Match
                </Badge>
              </div>

              <h4 className="text-gray-900 mb-1 font-bold group-hover:text-emerald-600 transition-colors truncate">
                {candidate.name}
              </h4>
              <p className="text-sm text-gray-500 mb-4 truncate">{candidate.email}</p>

              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Tier</span>
                  <span className={`font-medium text-${rankData.color}-600 capitalize`}>{rank} Tier</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Applied</span>
                  <span className="text-gray-700">{formatDate(candidate.appliedDate)}</span>
                </div>
              </div>

              <Button
                variant="outline"
                className="w-full group-hover:bg-emerald-50 group-hover:text-emerald-700 group-hover:border-emerald-300"
              >
                View Details
                <ArrowUpRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {filteredCandidates.length === 0 && (
        <Card className="p-12 border-gray-200 border-dashed">
          <div className="text-center">
            <Search className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-gray-900 mb-2">No candidates found</h3>
            <p className="text-gray-500">Try adjusting your search query</p>
          </div>
        </Card>
      )}
    </div>
  );
}
