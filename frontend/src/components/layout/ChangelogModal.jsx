import React from 'react';
import Modal from '../common/Modal';
import Badge from '../common/Badge';
import { Check, GitCommit } from 'lucide-react';

export default function ChangelogModal({ isOpen, onClose }) {
  const releases = [
    {
      version: 'v0.1.0',
      date: 'Latest Release',
      title: 'ModelForge Core Platform Launch',
      highlights: [
        'Automated CI Pipeline: Deep AST inspection of Python codebase for ML frameworks.',
        'ZIP Extraction Engine with safe path resolution and recursive archive handling.',
        'Deterministic Requirements Resolver and isolated environment verification.',
        'ModelForge Render-inspired dark SaaS workspace with unified ModelForge cyan design tokens.',
        'Scrollytelling interactive landing page with Frame 240 3D emblem integration.',
      ],
    },
    {
      version: 'v0.0.9',
      date: 'Foundation',
      title: 'FastAPI Backend & Project Service',
      highlights: [
        'High-performance REST API for project management and model storage.',
        'Supabase Storage & database client integration layer.',
        'Validation report JSON schemas and diagnostic logging.',
      ],
    },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Platform Changelog"
      subtitle="Recent updates, releases and feature improvements across ModelForge."
      maxWidth="max-w-xl"
    >
      <div className="space-y-6">
        {releases.map((release) => (
          <div key={release.version} className="border-b border-white/10 pb-5 last:border-b-0 last:pb-0">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <GitCommit size={16} className="text-[#00D6FF]" />
                <span className="font-mono text-sm font-semibold text-white">{release.version}</span>
                <span className="text-xs text-white/50">{release.title}</span>
              </div>
              <Badge status="info" size="xs">{release.date}</Badge>
            </div>

            <ul className="space-y-2 mt-3">
              {release.highlights.map((highlight, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-white/70">
                  <Check size={14} className="text-[#00D6FF] shrink-0 mt-0.5" />
                  <span>{highlight}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Modal>
  );
}
