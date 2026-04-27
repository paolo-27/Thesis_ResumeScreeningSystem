import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../lib/axios';
import {
  User, Mail, Phone, Building2, MapPin, Save, Loader2,
  CheckCircle, AlertCircle, Briefcase, FileText, Shield,
} from 'lucide-react';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Button } from '../../components/ui/button';

const AVATAR_COLORS = [
  '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b',
  '#ef4444', '#06b6d4', '#ec4899',
];

export default function ProfilePage() {
  const { user, token, updateUser } = useAuth();

  // Form state
  const [name, setName]         = useState(user?.name || '');
  const [email, setEmail]       = useState(user?.email || '');
  const [phone, setPhone]       = useState(user?.phone || '');
  const [company, setCompany]   = useState(user?.company || '');
  const [location, setLocation] = useState(user?.location || '');
  const [avatarColor, setAvatarColor] = useState(user?.avatar_color || '#10b981');

  // Account stats
  const [jobsPosted, setJobsPosted]     = useState<number | null>(null);
  const [resumesCount, setResumesCount] = useState<number | null>(null);

  // Status
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'ok' | 'error'>('idle');

  // Fetch strictly personal stats once
  useEffect(() => {
    if (!token) return;

    api.get('/api/auth/me/stats')
      .then(r => {
        const data = r.data;
        setJobsPosted(data.jobs_posted || 0);
        setResumesCount(data.resumes_screened || 0);
      })
      .catch((err) => {
        console.error("Failed to load personal stats", err);
        setJobsPosted(0);
        setResumesCount(0);
      });
  }, [token]);

  const initials = name
    ? name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
    : '?';

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSaveStatus('saving');
    try {
      const res = await api.patch('/api/auth/me', { name, email, phone, company, location, avatar_color: avatarColor });
      const updated = res.data;
      updateUser(updated);
      setSaveStatus('ok');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Profile Settings</h1>
        <p className="text-sm text-gray-500 mt-0.5">Manage your account information and preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Left Column ── */}
        <div className="space-y-5">

          {/* Avatar Card */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6 flex flex-col items-center text-center">
            {/* Big avatar circle */}
            <div
              className="w-24 h-24 rounded-full flex items-center justify-center text-white text-3xl font-bold shadow mb-3"
              style={{ backgroundColor: avatarColor }}
            >
              {initials}
            </div>
            <p className="font-semibold text-gray-900 text-lg leading-tight">{user?.name}</p>
            <p className="text-sm text-gray-500 mt-0.5">{user?.role === 'Admin' ? 'Administrator' : 'HR Manager'}</p>

            {/* Color swatches = "Change Avatar" */}
            <div className="mt-4 w-full">
              <p className="text-xs text-gray-400 mb-2">Change Avatar Color</p>
              <div className="flex justify-center gap-2 flex-wrap">
                {AVATAR_COLORS.map(c => (
                  <button
                    key={c}
                    onClick={() => setAvatarColor(c)}
                    className={`w-7 h-7 rounded-full border-2 transition-transform hover:scale-110
                      ${avatarColor === c ? 'border-gray-700 scale-110' : 'border-transparent'}`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Account Status Card */}
          <div className="bg-emerald-50 rounded-2xl border border-emerald-200 p-5">
            <p className="text-sm font-semibold text-gray-700 mb-4">Account Status</p>
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="flex items-center gap-2 text-gray-500">
                  <Briefcase className="w-4 h-4 text-emerald-600" /> Jobs Posted
                </span>
                <span className="font-semibold text-gray-800">
                  {jobsPosted === null ? '—' : jobsPosted}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="flex items-center gap-2 text-gray-500">
                  <FileText className="w-4 h-4 text-emerald-600" /> Resumes Screened
                </span>
                <span className="font-semibold text-gray-800">
                  {resumesCount === null ? '—' : resumesCount}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ── Right Column ── */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-5">Personal Information</h2>

            <form onSubmit={saveProfile} className="space-y-4">
              {/* Row 1: Full Name + Role */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label htmlFor="p-name" className="flex items-center gap-1.5 text-xs text-gray-500">
                    <User className="w-3.5 h-3.5" /> Full Name
                  </Label>
                  <Input
                    id="p-name"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    maxLength={60}
                    placeholder="Your full name"
                    className="h-10 text-sm border-gray-200"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Shield className="w-3.5 h-3.5" /> Role
                  </Label>
                  <Input
                    value={user?.role === 'Admin' ? 'Administrator' : 'HR Manager'}
                    disabled
                    className="h-10 text-sm bg-gray-50 cursor-not-allowed border-gray-200 text-gray-500"
                  />
                </div>
              </div>

              {/* Row 2: Email */}
              <div className="space-y-1">
                <Label htmlFor="p-email" className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Mail className="w-3.5 h-3.5" /> Email Address
                </Label>
                <Input
                  id="p-email"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  maxLength={60}
                  placeholder="your@email.com"
                  className="h-10 text-sm border-gray-200"
                />
              </div>

              {/* Row 3: Phone */}
              <div className="space-y-1">
                <Label htmlFor="p-phone" className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Phone className="w-3.5 h-3.5" /> Phone Number
                </Label>
                <Input
                  id="p-phone"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  placeholder="09974184582"
                  className="h-10 text-sm border-gray-200"
                />
              </div>

              {/* Row 4: Company */}
              <div className="space-y-1">
                <Label htmlFor="p-company" className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Building2 className="w-3.5 h-3.5" /> Company Name
                </Label>
                <Input
                  id="p-company"
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                  placeholder="CvSU - CCAT"
                  className="h-10 text-sm border-gray-200"
                />
              </div>

              {/* Row 5: Location */}
              <div className="space-y-1">
                <Label htmlFor="p-location" className="flex items-center gap-1.5 text-xs text-gray-500">
                  <MapPin className="w-3.5 h-3.5" /> Location
                </Label>
                <Input
                  id="p-location"
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  placeholder="Rosario, Cavite"
                  className="h-10 text-sm border-gray-200"
                />
              </div>

              {/* Save Button Row */}
              <div className="flex items-center justify-between pt-2">
                <div>
                  {saveStatus === 'ok' && (
                    <span className="flex items-center gap-1 text-emerald-600 text-sm">
                      <CheckCircle className="w-4 h-4" /> Changes saved!
                    </span>
                  )}
                  {saveStatus === 'error' && (
                    <span className="flex items-center gap-1 text-red-600 text-sm">
                      <AlertCircle className="w-4 h-4" /> Save failed.
                    </span>
                  )}
                </div>
                <Button
                  type="submit"
                  disabled={saveStatus === 'saving'}
                  className="w-full mt-2 bg-emerald-600 hover:bg-emerald-700 text-white h-11"
                >
                  {saveStatus === 'saving'
                    ? <><Loader2 className="w-4 h-4 animate-spin mr-2" /> Saving...</>
                    : <><Save className="w-4 h-4 mr-2" /> Save Changes</>
                  }
                </Button>
              </div>
            </form>
          </div>
        </div>

      </div>
    </div>
  );
}
