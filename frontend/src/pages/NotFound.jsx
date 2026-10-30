import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/common/Button';
import { ArrowLeft, Box } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center p-6 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[#00D6FF]/10 border border-[#00D6FF]/30 flex items-center justify-center text-[#00D6FF] mb-4">
        <Box size={32} />
      </div>
      <h1 className="text-4xl font-extrabold text-white">404</h1>
      <p className="text-sm text-white/60 mt-2 max-w-sm">
        The destination you are looking for does not exist or has been moved.
      </p>
      <div className="mt-6 flex gap-3">
        <Link to="/">
          <Button variant="secondary" size="md" leftIcon={<ArrowLeft size={16} />}>
            Home
          </Button>
        </Link>
        <Link to="/dashboard/projects">
          <Button variant="primary" size="md">
            Go to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}

