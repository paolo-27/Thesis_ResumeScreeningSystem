/**
 * UserManagement page – Admin-only.
 * Lists all users and allows creating, deactivating, reactivating,
 * and resetting passwords for HR accounts.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  UserCog, Plus, Power, PowerOff, Loader2, AlertCircle, CheckCircle,
  RefreshCw, Shield, ShieldOff, X, KeyRound,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';

interface UserRow {
  id: string;
  employee_number: string;
  name: string;
  email: string;
  phone?: string;
  role: string;
  is_active: number;
  force_reset: number;
  created_at: string;
}

interface CreateForm {
  employee_number: string;
  password: string;
  name: string;
  email: string;
  phone: string;
  company: string;
  location: string;
  role: 'Admin' | 'HR';
}

const EMPTY_FORM: CreateForm = {
  employee_number: '', password: '', name: '', email: '',
  phone: '', company: '', location: '', role: 'HR',
};

export default function UserManagement() {
  const { user, token, isAdmin } = useAuth();
  const navigate = useNavigate();

  const [users, setUsers]             = useState<UserRow[]>([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [form, setForm]               = useState<CreateForm>(EMPTY_FORM);
  const [creating, setCreating]       = useState(false);
  const [createError, setCreateError] = useState('');
  const [actionUserId, setActionUserId] = useState<string | null>(null);

  // Password reset modal state
  const [resetTarget, setResetTarget]       = useState<UserRow | null>(null);
  const [newPassword, setNewPassword]       = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetting, setResetting]           = useState(false);
  const [resetError, setResetError]         = useState('');
  const [resetSuccess, setResetSuccess]     = useState('');

  // Guard: redirect non-admins
  useEffect(() => {
    if (!isAdmin) navigate('/admin', { replace: true });
  }, [isAdmin, navigate]);

  const fetchUsers = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const res = await fetch('/api/auth/users', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error();
      setUsers(await res.json());
    } catch {
      setError('Failed to load users.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  async function createUser(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true); setCreateError('');
    try {
      const res = await fetch('/api/auth/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed');
      }
      setShowCreateModal(false);
      setForm(EMPTY_FORM);
      fetchUsers();
    } catch (err: any) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(emp_num: string, activate: boolean) {
    setActionUserId(emp_num);
    try {
      const action = activate ? 'reactivate' : 'deactivate';
      await fetch(`/api/auth/users/${emp_num}/${action}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchUsers();
    } finally {
      setActionUserId(null);
    }
  }

  async function resetPassword(e: React.FormEvent) {
    e.preventDefault();
    setResetError(''); setResetSuccess('');
    if (newPassword !== confirmPassword) { setResetError("Passwords don't match"); return; }
    if (newPassword.length < 6) { setResetError('Password must be at least 6 characters'); return; }

    setResetting(true);
    try {
      const res = await fetch(`/api/auth/users/${resetTarget!.employee_number}/reset-password`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ new_password: newPassword }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Reset failed');
      }
      setResetSuccess(`Password for ${resetTarget!.name} has been reset.`);
      setNewPassword(''); setConfirmPassword('');
      setTimeout(() => { setResetTarget(null); setResetSuccess(''); }, 2000);
    } catch (err: any) {
      setResetError(err.message);
    } finally {
      setResetting(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <p className="text-sm text-gray-500 mt-1">Manage internal HR accounts and access levels</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchUsers} className="gap-2">
            <RefreshCw className="w-4 h-4" /> Refresh
          </Button>
          <Button onClick={() => setShowCreateModal(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white gap-2">
            <Plus className="w-4 h-4" /> Add User
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm mb-4">
          <AlertCircle className="w-4 h-4" /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-emerald-500" /></div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {['Employee #', 'Name', 'Email', 'Role', 'Status', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-gray-50/50 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-600 text-xs">{u.employee_number}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {u.name}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border
                      ${u.role === 'Admin'
                        ? 'bg-purple-50 text-purple-700 border-purple-200'
                        : 'bg-blue-50 text-blue-700 border-blue-200'}`}>
                      {u.role === 'Admin' ? <Shield className="w-3 h-3" /> : <UserCog className="w-3 h-3" />}
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border
                      ${u.is_active === 1
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-gray-100 text-gray-500 border-gray-200'}`}>
                      {u.is_active === 1
                        ? <><CheckCircle className="w-3 h-3" /> Active</>
                        : <><ShieldOff className="w-3 h-3" /> Inactive</>}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {/* Deactivate / Reactivate */}
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={actionUserId === u.employee_number || u.employee_number === user?.employee_number}
                        onClick={() => toggleActive(u.employee_number, u.is_active !== 1)}
                        className={`gap-1 text-xs ${u.is_active === 1
                          ? 'text-red-600 border-red-200 hover:bg-red-50'
                          : 'text-emerald-600 border-emerald-200 hover:bg-emerald-50'}`}
                      >
                        {actionUserId === u.employee_number
                          ? <Loader2 className="w-3 h-3 animate-spin" />
                          : u.is_active === 1
                            ? <><PowerOff className="w-3 h-3" /> Deactivate</>
                            : <><Power className="w-3 h-3" /> Reactivate</>
                        }
                      </Button>

                      {/* Reset Password — available for all OTHER users (including other Admins) */}
                      {u.employee_number !== user?.employee_number && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => { setResetTarget(u); setResetError(''); setResetSuccess(''); }}
                          className="gap-1 text-xs text-orange-600 border-orange-200 hover:bg-orange-50"
                        >
                          <KeyRound className="w-3 h-3" /> Reset Password
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-400">No users found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Create User Modal ── */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 m-4">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-lg text-gray-900 flex items-center gap-2">
                <Plus className="w-5 h-5 text-emerald-600" /> Add New User
              </h2>
              <button onClick={() => { setShowCreateModal(false); setCreateError(''); }} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={createUser} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1 col-span-2">
                  <Label>Employee Number</Label>
                  <Input value={form.employee_number} onChange={e => setForm(f => ({ ...f, employee_number: e.target.value }))} placeholder="EMP-001" required />
                </div>
                <div className="space-y-1">
                  <Label>Full Name</Label>
                  <Input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="First Last" required />
                </div>
                <div className="space-y-1">
                  <Label>Role</Label>
                  <select
                    value={form.role}
                    onChange={e => setForm(f => ({ ...f, role: e.target.value as 'Admin' | 'HR' }))}
                    className="w-full h-10 rounded-md border border-gray-200 px-3 text-sm bg-white"
                  >
                    <option value="HR">HR</option>
                    <option value="Admin">Admin</option>
                  </select>
                </div>
                <div className="space-y-1 col-span-2">
                  <Label>Email</Label>
                  <Input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} placeholder="user@company.com" required />
                </div>
                <div className="space-y-1 col-span-2">
                  <Label>Temporary Password</Label>
                  <Input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="Min. 6 characters" required />
                </div>
              </div>
              {createError && (
                <p className="flex items-center gap-1 text-sm text-red-600"><AlertCircle className="w-4 h-4" />{createError}</p>
              )}
              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => { setShowCreateModal(false); setCreateError(''); }}>Cancel</Button>
                <Button type="submit" disabled={creating} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                  {creating ? <><Loader2 className="w-4 h-4 animate-spin mr-1" /> Creating...</> : 'Create User'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Reset Password Modal (Admin-only) ── */}
      {resetTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 m-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg text-gray-900 flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-orange-500" /> Reset Password
              </h2>
              <button onClick={() => setResetTarget(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Set a new password for <strong className="text-gray-700">{resetTarget.name}</strong>{' '}
              <span className="font-mono text-xs text-gray-400">({resetTarget.employee_number})</span>
            </p>
            {resetSuccess ? (
              <div className="flex items-center gap-2 text-emerald-600 py-4 justify-center">
                <CheckCircle className="w-5 h-5" /> {resetSuccess}
              </div>
            ) : (
              <form onSubmit={resetPassword} className="space-y-3">
                <div className="space-y-1">
                  <Label>New Password</Label>
                  <Input
                    type="password"
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    placeholder="Min. 6 characters"
                    required
                  />
                </div>
                <div className="space-y-1">
                  <Label>Confirm Password</Label>
                  <Input
                    type="password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="Repeat new password"
                    required
                  />
                </div>
                {resetError && (
                  <p className="flex items-center gap-1 text-sm text-red-600">
                    <AlertCircle className="w-4 h-4" />{resetError}
                  </p>
                )}
                <div className="flex justify-end gap-2 pt-1">
                  <Button type="button" variant="outline" onClick={() => setResetTarget(null)}>Cancel</Button>
                  <Button type="submit" disabled={resetting} className="bg-orange-500 hover:bg-orange-600 text-white">
                    {resetting
                      ? <><Loader2 className="w-4 h-4 animate-spin mr-1" /> Resetting...</>
                      : <><KeyRound className="w-4 h-4 mr-1" /> Reset Password</>}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
