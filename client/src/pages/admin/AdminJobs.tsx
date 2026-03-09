import React, { useState } from 'react';
import { Card } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { AlertCircle, CheckCircle2, Briefcase, ArrowLeft } from 'lucide-react';
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
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await api.post('/api/jobs/', {
        title: jobTitle,
        department,
        location,
        type: employmentType,
        description: jobDescription,
        status: 'Active',
        postedDate: new Date().toISOString()
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
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="jobDescription" className="text-gray-700">
                Job Description <span className="text-red-500">*</span>
              </Label>
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

            <div className="flex gap-4 pt-4">
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
