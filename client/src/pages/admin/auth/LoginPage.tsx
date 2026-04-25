import { useState } from 'react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Eye, EyeOff, Zap, Brain, TrendingUp, Lock, Loader2, AlertCircle } from 'lucide-react';
import VeridianLogo from './VeridianLogo';
import { useAuth } from '../../../contexts/AuthContext';

interface LoginPageProps {
  onLogin: () => void;
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const { login, isLoading } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [employeeNumber, setEmployeeNumber] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(employeeNumber, password, rememberMe);
      onLogin();
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-blue-50 flex">
      {/* Left Side - Login Form */}
      <div className="w-full lg:w-5/12 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <div className="mb-2">
              <VeridianLogo className="h-10" />
            </div>
            <p className="text-gray-500 text-sm">The ML-Based Resume Ranking System</p>
          </div>

          <div className="bg-white rounded-2xl shadow-xl shadow-emerald-100/50 p-8 border border-emerald-100">
            <div className="mb-6">
              <h2 className="text-gray-900 mb-1">Welcome Back</h2>
              <p className="text-sm text-gray-500">Please enter your credentials to login</p>
            </div>

            {error && (
              <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="employee_number" className="text-gray-700">Employee Number</Label>
                <Input
                  id="employee_number"
                  type="text"
                  placeholder="Enter your employee number"
                  value={employeeNumber}
                  onChange={(e) => setEmployeeNumber(e.target.value)}
                  className="h-11 border-gray-200 focus:border-emerald-500 focus:ring-emerald-500"
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-gray-700">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="h-11 pr-10 border-gray-200 focus:border-emerald-500 focus:ring-emerald-500"
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center text-sm">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                  />
                  <span className="text-gray-600">Remember me</span>
                </label>
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full h-11 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white"
              >
                {isLoading ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Signing in...</>
                ) : (
                  <><Lock className="w-4 h-4 mr-2" /> Sign In</>
                )}
              </Button>
            </form>
          </div>
        </div>
      </div>

      {/* Right Side - Features */}
      <div className="hidden lg:flex lg:w-7/12 bg-gradient-to-br from-emerald-600 to-emerald-700 p-12 items-center justify-center relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmZmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDE2YzAtMi4yMSAxLjc5LTQgNC00czQgMS43OSA0IDQtMS43OSA0LTQgNC00LTEuNzktNC00em0wIDI0YzAtMi4yMSAxLjc5LTQgNC00czQgMS43OSA0IDQtMS43OSA0LTQgNC00LTEuNzktNC00ek0xMiAxNmMwLTIuMjEgMS43OS00IDQtNHM0IDEuNzkgNCA0LTEuNzkgNC00IDQtNC0xLjc5LTQtNHptMCAyNGMwLTIuMjEgMS43OS00IDQtNHM0IDEuNzkgNCA0LTEuNzkgNC00IDQtNC0xLjc5LTQtNHoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-50"></div>

        <div className="relative z-10 max-w-xl text-white">
          <div className="mb-12">
            <VeridianLogo className="h-16 mb-4" white />
            <h2 className="text-white mb-3">ML-Based Resume Ranking System</h2>
            <p className="text-emerald-100 text-lg">Transform your recruitment process with intelligent resume matching and data-driven insights.</p>
          </div>

          <div className="space-y-6">
            <div className="flex gap-4">
              <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
                <Brain className="w-6 h-6 text-emerald-200" />
              </div>
              <div>
                <h3 className="text-white mb-1">Intelligent Resume Matching</h3>
                <p className="text-emerald-100 text-sm">Find candidates who truly match your job criteria with ML-based analysis.</p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
                <Zap className="w-6 h-6 text-emerald-200" />
              </div>
              <div>
                <h3 className="text-white mb-1">Boost Efficiency</h3>
                <p className="text-emerald-100 text-sm">Save hours of manual screening with automated candidate ranking.</p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="w-12 h-12 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-6 h-6 text-emerald-200" />
              </div>
              <div>
                <h3 className="text-white mb-1">Data-Driven Decisions</h3>
                <p className="text-emerald-100 text-sm">Make fair, unbiased hiring decisions backed by comprehensive analytics.</p>
              </div>
            </div>
          </div>

          <div className="mt-12 p-6 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20">
            <div className="flex items-center gap-3">
              <div className="flex -space-x-2">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-300 to-emerald-400 border-2 border-white"></div>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-300 to-blue-400 border-2 border-white"></div>
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-300 to-purple-400 border-2 border-white"></div>
              </div>
              <div>
                <p className="text-white">Automated Screening System</p>
                <p className="text-emerald-200 text-sm">Secure • Role-Based • Auditable</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}