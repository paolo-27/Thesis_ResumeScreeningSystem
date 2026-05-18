import React, { useState } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { AlertCircle, CheckCircle2, Briefcase, ArrowLeft, Users, HelpCircle, Brain, Zap, BookOpen, Clock, GraduationCap, Layers } from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import api from '../../lib/axios';

export default function AdminJobs() {
  const navigate = useNavigate();
  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [department, setDepartment] = useState('');
  const [location, setLocation] = useState('');
  const [employmentType, setEmploymentType] = useState('');
  const [shortlistQuota, setShortlistQuota] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showGuide, setShowGuide] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const quotaValue = shortlistQuota.trim() !== '' ? parseInt(shortlistQuota, 10) : null;
      await api.post('/api/jobs/', {
        title: jobTitle,
        department,
        location,
        type: employmentType,
        description: jobDescription,
        status: 'Active',
        postedDate: new Date().toISOString(),
        shortlist_quota: quotaValue,
      });

      toast.success(`Job posting "${jobTitle}" has been published successfully!`);
      navigate('/admin/candidates');
    } catch (error) {
      console.error('Error creating job:', error);
      toast.error('Failed to create job posting. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <Button
          variant="ghost"
          onClick={() => navigate('/admin/candidates')}
          className="mb-4 text-gray-600 hover:text-gray-900 -ml-3"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Candidates
        </Button>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Job Posting</h1>
        <p className="text-gray-500">Post a new job opening and receive applications online</p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="p-8 border-gray-200">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-lg bg-emerald-100 flex items-center justify-center">
              <Briefcase className="w-6 h-6 text-emerald-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900">Job Information</h3>
          </div>

          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="jobTitle" className="text-gray-700">
                  Job Title <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="jobTitle"
                  placeholder="e.g., Senior Frontend Developer"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  className="border-gray-200 focus:border-emerald-500 focus:ring-emerald-500"
                  required
                  maxLength={60}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="department" className="text-gray-700">
                  Department <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="department"
                  placeholder="e.g., Engineering"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="border-gray-200 focus:border-emerald-500 focus:ring-emerald-500"
                  required
                  maxLength={20}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="location" className="text-gray-700">
                  Location <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="location"
                  placeholder="e.g., Remote, New York, etc."
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="border-gray-200 focus:border-emerald-500 focus:ring-emerald-500"
                  required
                  maxLength={20}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="employmentType" className="text-gray-700">
                  Employment Type <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="employmentType"
                  placeholder="e.g., Full-time, Part-time, Contract"
                  value={employmentType}
                  onChange={(e) => setEmploymentType(e.target.value)}
                  className="border-gray-200 focus:border-emerald-500 focus:ring-emerald-500"
                  required
                  maxLength={20}
                />
              </div>
            </div>

            {/* Shortlist Quota */}
            <div className="space-y-2">
              <Label htmlFor="shortlistQuota" className="text-gray-700 flex items-center gap-2">
                <Users className="w-4 h-4 text-emerald-600" />
                Shortlist Quota
                <span className="text-xs text-gray-400 font-normal ml-1">(optional)</span>
              </Label>
              <Input
                id="shortlistQuota"
                type="number"
                min="1"
                placeholder="e.g., 10 — leave blank for no limit"
                value={shortlistQuota}
                onChange={(e) => setShortlistQuota(e.target.value)}
                className="border-gray-200 focus:border-emerald-500 focus:ring-emerald-500"
              />
              <p className="text-xs text-gray-400">
                Set a maximum number of candidates that can be shortlisted for this job. A notification will appear once the quota is reached.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="jobDescription" className="text-gray-700">
                  Job Description &amp; Job Requirements <span className="text-red-500">*</span>
                </Label>
                <button
                  type="button"
                  onClick={() => setShowGuide(true)}
                  className="text-emerald-500 hover:text-emerald-700 transition-colors flex-shrink-0"
                  title="Writing guide for better AI matching"
                >
                  <HelpCircle className="w-4 h-4" />
                </button>
              </div>
              <Textarea
                id="jobDescription"
                placeholder="Enter the job description, required skills, qualifications, and responsibilities..."
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                className="min-h-[250px] border-gray-200 focus:border-emerald-500 focus:ring-emerald-500 resize-none"
                required
              />
              <p className="text-xs text-gray-500">
                Provide a detailed description to help attract the right candidates
              </p>
            </div>

            {/* AI Writing Guide Modal */}
            <Dialog open={showGuide} onOpenChange={setShowGuide}>
              <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-gray-900 text-xl">
                    <Brain className="w-5 h-5 text-emerald-600" />
                    How to Write a Job Description for Better AI Matching
                  </DialogTitle>
                </DialogHeader>
                <p className="text-sm text-gray-500 -mt-2 mb-4">
                  The AI ranks candidates using <strong>6 predictors</strong> extracted directly from your job description. The more clearly you write each one, the more accurately the system can screen and rank applicants.
                </p>
                <div className="space-y-4">
                  <div className="flex gap-3 p-4 rounded-lg bg-emerald-50 border border-emerald-100">
                    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-emerald-600 flex items-center justify-center">
                      <Zap className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 mb-0.5">1. Keyword Relevance <span className="text-xs font-normal text-emerald-600 ml-1">(TF-IDF Match)</span></p>
                      <p className="text-sm text-gray-600">The AI scans your description for job-specific terms that also appear in the candidate's resume. <strong>If the description is too vague</strong> (e.g., "handles various tasks"), the system cannot find matching keywords and will score all resumes equally low — making it harder to separate strong from weak candidates.</p>
                      <p className="text-xs text-emerald-700 mt-1.5 font-medium">✦ Tip: Use specific job titles, tools, and action verbs (e.g., "manage inventory using SAP", "develop REST APIs in Python").</p>
                    </div>
                  </div>
                  <div className="flex gap-3 p-4 rounded-lg bg-blue-50 border border-blue-100">
                    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
                      <Brain className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 mb-0.5">2. Semantic Similarity <span className="text-xs font-normal text-blue-600 ml-1">(AI Deep Understanding)</span></p>
                      <p className="text-sm text-gray-600">Beyond keywords, the AI reads the overall meaning and context of your description and compares it to the resume. <strong>If the description is too short or lacks context</strong>, the AI cannot build a meaningful understanding of the role and may match unqualified candidates.</p>
                      <p className="text-xs text-blue-700 mt-1.5 font-medium">✦ Tip: Write at least 3–5 sentences describing the role's purpose, environment, and key outcomes expected.</p>
                    </div>
                  </div>
                  <div className="flex gap-3 p-4 rounded-lg bg-violet-50 border border-violet-100">
                    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-violet-600 flex items-center justify-center">
                      <Layers className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 mb-0.5">3. Skills Relevance <span className="text-xs font-normal text-violet-600 ml-1">(Scored 0–2)</span></p>
                      <p className="text-sm text-gray-600">The AI counts how many required skills from your description appear in the candidate's resume. <strong>If no specific skills are listed</strong>, this score defaults to zero for all candidates — removing one of the strongest signals for shortlisting.</p>
                      <p className="text-xs text-violet-700 mt-1.5 font-medium">✦ Tip: List at least 4–6 concrete skills (e.g., "Proficient in Excel, QuickBooks, and financial reporting").</p>
                    </div>
                  </div>
                  <div className="flex gap-3 p-4 rounded-lg bg-amber-50 border border-amber-100">
                    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-amber-500 flex items-center justify-center">
                      <Clock className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 mb-0.5">4. Years of Experience <span className="text-xs font-normal text-amber-600 ml-1">(Scored 0–3)</span></p>
                      <p className="text-sm text-gray-600">The AI extracts the minimum years of experience required and compares it to the candidate's resume. <strong>If no experience requirement is mentioned</strong>, every candidate — from fresh graduate to senior — receives the same score on this predictor.</p>
                      <p className="text-xs text-amber-700 mt-1.5 font-medium">✦ Tip: State clearly, e.g., "At least 2 years of experience in sales" or "Minimum 1 year in a supervisory role".</p>
                    </div>
                  </div>
                  <div className="flex gap-3 p-4 rounded-lg bg-rose-50 border border-rose-100">
                    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-rose-600 flex items-center justify-center">
                      <GraduationCap className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 mb-0.5">5. Education Match <span className="text-xs font-normal text-rose-600 ml-1">(Scored 0–2)</span></p>
                      <p className="text-sm text-gray-600">The AI checks whether the candidate's degree or field of study matches what's required. <strong>Without a clear education requirement</strong>, candidates with unrelated degrees will not be penalized and may rank equally with ideal candidates.</p>
                      <p className="text-xs text-rose-700 mt-1.5 font-medium">✦ Tip: Include the minimum degree and preferred field (e.g., "Bachelor's degree in Accounting, Finance, or a related field").</p>
                    </div>
                  </div>
                  <div className="flex gap-3 p-4 rounded-lg bg-teal-50 border border-teal-100">
                    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-teal-600 flex items-center justify-center">
                      <BookOpen className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900 mb-0.5">6. Domain Alignment <span className="text-xs font-normal text-teal-600 ml-1">(Scored 0–1)</span></p>
                      <p className="text-sm text-gray-600">The AI determines whether the candidate's background belongs to the same domain as the job (e.g., Tech, Finance, Healthcare). <strong>Without domain context</strong>, candidates from entirely unrelated fields may pass undetected.</p>
                      <p className="text-xs text-teal-700 mt-1.5 font-medium">✦ Tip: Mention the industry or function (e.g., "role within our IT department", "position in our Finance &amp; Accounting team").</p>
                    </div>
                  </div>
                </div>
                <div className="mt-4 p-3 rounded-lg bg-gray-50 border border-gray-200">
                  <p className="text-xs text-gray-500 text-center">
                    A complete job description with all 6 elements gives the AI the full picture leading to sharper rankings and fewer manual reviews.
                  </p>
                </div>
                <div className="mt-4 flex justify-end">
                  <Button onClick={() => setShowGuide(false)} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                    Got it, thanks!
                  </Button>
                </div>
              </DialogContent>
            </Dialog>

            <Card className="p-4 border-gray-200 bg-gradient-to-br from-blue-50 to-blue-100/50">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="text-gray-900 font-medium mb-1">How it works</h4>
                  <p className="text-sm text-gray-600">
                    Once you publish this job posting, it will be available online for candidates to apply.
                    Received applications will automatically be analyzed and ranked using our XGBoost AI algorithm.
                  </p>
                </div>
              </div>
            </Card>


            <div className="flex flex-col sm:flex-row gap-4 pt-4">
              <Button
                type="submit"
                className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                disabled={isSubmitting}
              >
                <CheckCircle2 className="w-4 h-4 mr-2" />
                {isSubmitting ? 'Publishing...' : 'Publish Job Posting'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setJobTitle('');
                  setJobDescription('');
                  setDepartment('');
                  setLocation('');
                  setEmploymentType('');
                  setShortlistQuota('');
                }}
                disabled={isSubmitting}
              >
                Reset Form
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  );
}
