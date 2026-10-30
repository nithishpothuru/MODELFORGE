import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthLayout from '../components/auth/AuthLayout';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import { Eye, EyeOff, Mail, Lock, ArrowRight, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, resetPassword, isSupabaseConfigured } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [loading, setLoading] = useState(false);

  // Forgot password modal state
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);

  const validate = () => {
    const newErrors = {};
    if (!email.trim()) {
      newErrors.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');

    if (!validate()) return;

    setLoading(true);
    try {
      await login({ email, password, rememberMe });
      const destination = location.state?.from?.pathname || '/dashboard/projects';
      navigate(destination, { replace: true });
    } catch (err) {
      setServerError(err.message || 'Invalid credentials or authentication error.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetSubmit = async (e) => {
    e.preventDefault();
    setResetError('');

    if (!resetEmail.trim()) {
      setResetError('Please enter your registered email address.');
      return;
    }

    if (!isSupabaseConfigured) {
      setResetError(
        'Password recovery requires Supabase Auth configuration (VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY). Please contact your workspace administrator.'
      );
      return;
    }

    setResetLoading(true);
    try {
      await resetPassword(resetEmail);
      setResetSuccess(true);
    } catch (err) {
      setResetError(err.message || 'Failed to dispatch password recovery email.');
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your ModelForge workspace to build, validate and deploy models."
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        {serverError && (
          <div className="mf-form-alert mf-form-alert-error" role="alert">
            <AlertTriangle size={16} className="shrink-0" />
            <div className="alert-content">
              <span>{serverError}</span>
            </div>
          </div>
        )}

        <Input
          id="login-email"
          label="Email Address"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
          }}
          placeholder="developer@modelforge.dev"
          required
          autoComplete="email"
          leftIcon={<Mail size={18} />}
          error={errors.email}
        />

        <Input
          id="login-password"
          label="Password"
          type={showPassword ? 'text' : 'password'}
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (errors.password) setErrors((prev) => ({ ...prev, password: '' }));
          }}
          placeholder="••••••••••••"
          required
          autoComplete="current-password"
          leftIcon={<Lock size={18} />}
          error={errors.password}
          rightAction={
            <button
              type="button"
              className="mf-password-toggle-btn"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              tabIndex={0}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          }
        />

        {/* Dedicated, non-overlapping horizontal options row */}
        <div className="mf-auth-options-row">
          <label className="mf-checkbox-label">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="mf-checkbox"
            />
            <span>Remember Me</span>
          </label>

          <button
            type="button"
            className="mf-forgot-password-link"
            onClick={() => {
              setForgotModalOpen(true);
              setResetEmail(email.trim() || '');
              setResetError('');
              setResetSuccess(false);
            }}
          >
            Forgot Password?
          </button>
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          loading={loading}
          disabled={loading}
          className="mf-auth-submit-btn w-full mt-2"
          rightIcon={<ArrowRight size={16} />}
        >
          Sign In to Workspace
        </Button>

        <div className="mf-auth-switch-prompt">
          <span>Don't have an account?</span>{' '}
          <Link to="/signup" className="mf-auth-link">
            Create an account
          </Link>
        </div>
      </form>

      {/* Password Recovery Modal */}
      <Modal
        isOpen={forgotModalOpen}
        onClose={() => {
          setForgotModalOpen(false);
          setResetSuccess(false);
          setResetError('');
        }}
        title="Reset Password"
        subtitle="Enter your account email to receive password recovery instructions."
        maxWidth="max-w-md"
      >
        {resetSuccess ? (
          <div className="space-y-4 py-2 text-center">
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-xs flex items-center gap-2 text-left">
              <CheckCircle2 size={18} className="shrink-0" />
              <span>
                Recovery instructions dispatched. If an account is registered with{' '}
                <strong className="text-white">{resetEmail}</strong>, check your inbox.
              </span>
            </div>
            <div className="pt-2 flex justify-end">
              <Button
                variant="primary"
                size="md"
                onClick={() => {
                  setForgotModalOpen(false);
                  setResetSuccess(false);
                }}
              >
                Back to Sign In
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleResetSubmit} className="space-y-4">
            {resetError && (
              <div className="mf-form-alert mf-form-alert-error" role="alert">
                <AlertTriangle size={16} className="shrink-0" />
                <span>{resetError}</span>
              </div>
            )}

            <Input
              id="reset-email"
              label="Account Email"
              type="email"
              value={resetEmail}
              onChange={(e) => setResetEmail(e.target.value)}
              placeholder="developer@modelforge.dev"
              required
              leftIcon={<Mail size={16} />}
              hint="We will send a secure password reset link to this address"
            />

            <div className="flex justify-end items-center gap-3 pt-4 border-t border-white/10">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setForgotModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={resetLoading}
                disabled={resetLoading}
              >
                Send Recovery Link
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </AuthLayout>
  );
}
