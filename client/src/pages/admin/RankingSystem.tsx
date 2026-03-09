import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  Award,
  AlertCircle,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Progress } from "../../components/ui/progress";
import type { Candidate, JobPosting } from "../../types";

interface RankingSystemProps {
  job?: JobPosting;
  candidates: Candidate[];
  onViewSelect: (
    view:
      | "green"
      | "yellow"
      | "red"
      | "shortlisted"
      | "rejected",
  ) => void;
  onBack: () => void;
}

export default function RankingSystem({
  job,
  candidates,
  onViewSelect,
  onBack,
}: RankingSystemProps) {

  // Use gyr_tier from backend as source of truth; fallback to 0.0–1.0 thresholds
  const greenCount = candidates.filter(c => c.gyr_tier === 'Green' || (!c.gyr_tier && (c.probability_score || 0) >= 0.7)).length;
  const yellowCount = candidates.filter(c => c.gyr_tier === 'Yellow' || (!c.gyr_tier && (c.probability_score || 0) >= 0.4 && (c.probability_score || 0) < 0.7)).length;
  const redCount = candidates.filter(c => c.gyr_tier === 'Red' || (!c.gyr_tier && (c.probability_score || 0) < 0.4)).length;

  const total = candidates.length || 1; // prevent divide by zero

  // probability_score is 0.0–1.0; multiply by 100 for percentage display
  const avgScore = candidates.length > 0
    ? Math.round((candidates.reduce((sum, c) => sum + (c.probability_score || 0), 0) / candidates.length) * 100)
    : 0;

  const jobData = {
    title: job?.title || 'Loading...',
    department: job?.department || '-',
    totalCandidates: candidates.length,
    rankings: {
      green: {
        count: greenCount,
        percentage: Math.round((greenCount / total) * 100),
        // probability_score is 0.0–1.0; filter on 0.8 threshold, then * 100 for display
        avgScore: greenCount > 0 ? Math.round((candidates.filter(c => (c.probability_score || 0) >= 0.7).reduce((a, c) => a + (c.probability_score || 0), 0) / greenCount) * 100) : 0,
        label: "Top Tier",
        description: "Exceptional matches with strong alignment to requirements",
      },
      yellow: {
        count: yellowCount,
        percentage: Math.round((yellowCount / total) * 100),
        avgScore: yellowCount > 0 ? Math.round((candidates.filter(c => (c.probability_score || 0) >= 0.4 && (c.probability_score || 0) < 0.7).reduce((a, c) => a + (c.probability_score || 0), 0) / yellowCount) * 100) : 0,
        label: "Good Fit",
        description: "Solid candidates with most required qualifications",
      },
      red: {
        count: redCount,
        percentage: Math.round((redCount / total) * 100),
        avgScore: redCount > 0 ? Math.round((candidates.filter(c => (c.probability_score || 0) < 0.4).reduce((a, c) => a + (c.probability_score || 0), 0) / redCount) * 100) : 0,
        label: "Below Threshold",
        description: "Limited alignment with position requirements",
      },
    },
  };

  const shortlistedCount = candidates.filter(c => c.status === 'Shortlisted').length;
  const rejectedCount = candidates.filter(c => c.status === 'Rejected').length;

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
          Back to Job Postings
        </Button>
        <h1 className="text-gray-900 mb-2">{jobData.title}</h1>
        <p className="text-gray-500">
          {jobData.department} • {jobData.totalCandidates}{" "}
          candidates ranked by XGBoost algorithm
        </p>
      </div>

      {/* Overview Stats */}
      <Card className="p-6 border-gray-200 mb-8 bg-gradient-to-br from-emerald-50 to-emerald-100/50">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-600 flex items-center justify-center flex-shrink-0">
            <Award className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-gray-900 mb-2">
              Ranking Overview
            </h3>
            <p className="text-gray-600 mb-4">
              Candidates have been analyzed and ranked using our
              XGBoost machine learning algorithm. The ranking
              considers skills match, experience level,
              education, and role requirements.
            </p>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-500 mb-1">
                  Total Screened
                </p>
                <p className="text-gray-900">
                  {jobData.totalCandidates} resumes
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">
                  Avg. Match Score
                </p>
                <p className="text-gray-900">{avgScore}%</p>
              </div>
              <div>
                <p className="text-sm text-gray-500 mb-1">
                  Top Candidates
                </p>
                <p className="text-gray-900">
                  {jobData.rankings.green.count} qualified
                </p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Ranking Tiers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Green - Top 30% */}
        <Card className="border-2 border-emerald-500 hover:shadow-xl transition-all duration-200 cursor-pointer group overflow-hidden flex flex-col">
          <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 p-6 text-white">
            <div className="flex items-start justify-between mb-4">
              <div className="w-14 h-14 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <TrendingUp className="w-7 h-7" />
              </div>
              <div className="text-right">
                <p className="text-emerald-100 text-sm mb-1">
                  Top Tier
                </p>
                <p className="text-3xl">
                  {jobData.rankings.green.count}
                </p>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-emerald-100">
                  Percentage
                </span>
                <span>
                  {jobData.rankings.green.percentage}%
                </span>
              </div>
              <Progress
                value={jobData.rankings.green.percentage}
                className="h-2 bg-emerald-300"
              />
              <div className="flex items-center justify-between text-sm pt-2">
                <span className="text-emerald-100">
                  Avg. Score
                </span>
                <span className="text-lg">
                  {jobData.rankings.green.avgScore}%
                </span>
              </div>
            </div>
          </div>
          <div className="p-6 bg-white flex flex-col flex-1">
            <h4 className="text-gray-900 mb-2">
              {jobData.rankings.green.label}
            </h4>
            <p className="text-sm text-gray-600 mb-4 flex-1">
              {jobData.rankings.green.description}
            </p>
            <Button
              onClick={() => onViewSelect("green")}
              className="w-full bg-emerald-600 hover:bg-emerald-700 group-hover:bg-emerald-700 text-white"
            >
              <Users className="w-4 h-4 mr-2" />
              View Candidates
            </Button>
          </div>
        </Card>

        {/* Yellow - Middle 50% */}
        <Card className="border-2 border-yellow-500 hover:shadow-xl transition-all duration-200 cursor-pointer group overflow-hidden flex flex-col">
          <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 p-6 text-white">
            <div className="flex items-start justify-between mb-4">
              <div className="w-14 h-14 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <Minus className="w-7 h-7" />
              </div>
              <div className="text-right">
                <p className="text-yellow-100 text-sm mb-1">
                  Good Fit
                </p>
                <p className="text-3xl">
                  {jobData.rankings.yellow.count}
                </p>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-yellow-100">
                  Percentage
                </span>
                <span>
                  {jobData.rankings.yellow.percentage}%
                </span>
              </div>
              <Progress
                value={jobData.rankings.yellow.percentage}
                className="h-2 bg-yellow-300"
              />
              <div className="flex items-center justify-between text-sm pt-2">
                <span className="text-yellow-100">
                  Avg. Score
                </span>
                <span className="text-lg">
                  {jobData.rankings.yellow.avgScore}%
                </span>
              </div>
            </div>
          </div>
          <div className="p-6 bg-white flex flex-col flex-1">
            <h4 className="text-gray-900 mb-2">
              {jobData.rankings.yellow.label}
            </h4>
            <p className="text-sm text-gray-600 mb-4 flex-1">
              {jobData.rankings.yellow.description}
            </p>
            <Button
              onClick={() => onViewSelect("yellow")}
              className="w-full bg-yellow-600 hover:bg-yellow-700 group-hover:bg-yellow-700 text-white"
            >
              <Users className="w-4 h-4 mr-2" />
              View Candidates
            </Button>
          </div>
        </Card>

        {/* Red - Bottom 20% */}
        <Card className="border-2 border-red-500 hover:shadow-xl transition-all duration-200 cursor-pointer group overflow-hidden flex flex-col">
          <div className="bg-gradient-to-br from-red-500 to-red-600 p-6 text-white">
            <div className="flex items-start justify-between mb-4">
              <div className="w-14 h-14 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <TrendingDown className="w-7 h-7" />
              </div>
              <div className="text-right">
                <p className="text-red-100 text-sm mb-1">
                  Below Threshold
                </p>
                <p className="text-3xl">
                  {jobData.rankings.red.count}
                </p>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-red-100">Percentage</span>
                <span>{jobData.rankings.red.percentage}%</span>
              </div>
              <Progress
                value={jobData.rankings.red.percentage}
                className="h-2 bg-red-300"
              />
              <div className="flex items-center justify-between text-sm pt-2">
                <span className="text-red-100">Avg. Score</span>
                <span className="text-lg">
                  {jobData.rankings.red.avgScore}%
                </span>
              </div>
            </div>
          </div>
          <div className="p-6 bg-white flex flex-col flex-1">
            <h4 className="text-gray-900 mb-2">
              {jobData.rankings.red.label}
            </h4>
            <p className="text-sm text-gray-600 mb-4 flex-1">
              {jobData.rankings.red.description}
            </p>
            <Button
              onClick={() => onViewSelect("red")}
              className="w-full bg-red-600 hover:bg-red-700 group-hover:bg-red-700 text-white"
            >
              <Users className="w-4 h-4 mr-2" />
              View Candidates
            </Button>
          </div>
        </Card>
      </div>

      {/* Shortlisted and Rejected Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Shortlisted */}
        <Card className="border-2 border-blue-300 hover:shadow-xl transition-all duration-200 cursor-pointer group overflow-hidden flex flex-col">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 p-6 text-white">
            <div className="flex items-start justify-between mb-4">
              <div className="w-14 h-14 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <div className="text-right">
                <p className="text-blue-100 text-sm mb-1">
                  Shortlisted
                </p>
                <p className="text-3xl">{shortlistedCount}</p>
              </div>
            </div>
            <p className="text-sm text-blue-100">
              Candidates selected for next round
            </p>
          </div>
          <div className="p-6 bg-white flex flex-col flex-1">
            <h4 className="text-gray-900 mb-2">
              Shortlisted Candidates
            </h4>
            <p className="text-sm text-gray-600 mb-4 flex-1">
              Review candidates you've marked as potential hires
            </p>
            <Button
              onClick={() => onViewSelect("shortlisted")}
              className="w-full bg-blue-600 hover:bg-blue-700 group-hover:bg-blue-700 text-white"
            >
              <CheckCircle2 className="w-4 h-4 mr-2" />
              View Shortlisted
            </Button>
          </div>
        </Card>

        {/* Rejected */}
        <Card className="border-2 border-gray-300 hover:shadow-xl transition-all duration-200 cursor-pointer group overflow-hidden flex flex-col">
          <div className="bg-gradient-to-br from-gray-500 to-gray-600 p-6 text-white">
            <div className="flex items-start justify-between mb-4">
              <div className="w-14 h-14 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <XCircle className="w-7 h-7" />
              </div>
              <div className="text-right">
                <p className="text-gray-100 text-sm mb-1">
                  Rejected
                </p>
                <p className="text-3xl">{rejectedCount}</p>
              </div>
            </div>
            <p className="text-sm text-gray-100">
              Candidates not selected for this role
            </p>
          </div>
          <div className="p-6 bg-white flex flex-col flex-1">
            <h4 className="text-gray-900 mb-2">
              Rejected Candidates
            </h4>
            <p className="text-sm text-gray-600 mb-4 flex-1">
              Review candidates you've decided not to proceed
              with
            </p>
            <Button
              onClick={() => onViewSelect("rejected")}
              className="w-full bg-gray-600 hover:bg-gray-700 group-hover:bg-gray-700 text-white"
            >
              <XCircle className="w-4 h-4 mr-2" />
              View Rejected
            </Button>
          </div>
        </Card>
      </div>

      {/* Info Alert */}
      <Card className="p-6 border-gray-200 bg-blue-50">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-gray-900 mb-1">
              How Rankings Work
            </h4>
            <p className="text-sm text-gray-600">
              Our XGBoost algorithm analyzes multiple factors
              including technical skills, years of experience,
              educational background, and keyword matching
              against your job description. Candidates are
              automatically ranked and categorized to help you
              focus on the most promising applicants first.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}