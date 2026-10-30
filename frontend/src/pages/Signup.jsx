import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthLayout from '../components/auth/AuthLayout';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { Eye, EyeOff, Mail, Lock, User, ArrowRight, AlertTriangle, CheckCircle } from 'lucide-react';

export default function Signup() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const validate = () => {
    const newErrors = {};

    if (!name.trim()) {
      newErrors.name = 'Full name is required';
    }

    if (!email.trim()) {
      newErrors.email = 'Email address is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters long';
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = 'Confirm your password';
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    setSuccessMsg('');

    if (!validate()) return;

    setLoading(true);
    try {
      const res = await register({ email, password, name });
      if (res?.session) {
        // Direct session confirmed by auth provider
        navigate('/dashboard/projects', { replace: true });
      } else {
        // Email verification required by Supabase Auth configuration
        setSuccessMsg(
          'Account registered successfully! If email verification is enabled on your Supabase project, check your inbox to confirm your address.'
        );
      }
    } catch (err) {
      setServerError(err.message || 'Failed to create account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Get started with ModelForge and deploy your machine learning models."
    >
      {successMsg ? (
        <div className="mf-form-alert mf-form-alert-success text-center py-6 space-y-4" role="alert">
          <CheckCircle size={36} className="mx-auto text-emerald-400" />
          <div className="space-y-1">
            <h3 className="font-semibold text-white text-base">Account Created</h3>
            <p className="text-xs text-white/70 max-w-sm mx-auto">{successMsg}</p>
          </div>
          <div className="pt-2">
            <Link to="/login">
              <Button variant="primary" size="md">
                Proceed to Sign In
              </Button>
            </Link>
          </div>
        </div>
      ) : (
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
            id="signup-name"
            label="Full Name"
            type="text"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (errors.name) setErrors((prev) => ({ ...prev, name: '' }));
            }}
            placeholder="Ada Lovelace"
            required
            autoComplete="name"
            leftIcon={<User size={18} />}
            error={errors.name}
          />

          <Input
            id="signup-email"
            label="Work Email"
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
            id="signup-password"
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (errors.password) setErrors((prev) => ({ ...prev, password: '' }));
            }}
            placeholder="Minimum 8 characters"
            required
            autoComplete="new-password"
            leftIcon={<Lock size={18} />}
            error={errors.password}
            hint="Use at least 8 characters with letters and numbers"
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

          <Input
            id="signup-confirm-password"
            label="Confirm Password"
            type={showConfirmPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: '' }));
            }}
            placeholder="Re-type password"
            required
            autoComplete="new-password"
            leftIcon={<Lock size={18} />}
            error={errors.confirmPassword}
            rightAction={
              <button
                type="button"
                className="mf-password-toggle-btn"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                tabIndex={0}
              >
                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            }
          />

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            disabled={loading}
            className="mf-auth-submit-btn w-full mt-2"
            rightIcon={<ArrowRight size={16} />}
          >
            Create Account
          </Button>

          <div className="mf-auth-switch-prompt">
            <span>Already have an account?</span>{' '}
            <Link to="/login" className="mf-auth-link">
              Sign in
            </Link>
          </div>
        </form>
      )}
    </AuthLayout>
  );
}
