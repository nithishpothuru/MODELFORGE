import React, { useState, useEffect } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import { listProjects } from '../services/projects';
import ProjectsTable from '../components/projects/ProjectsTable';
import UploadModal from '../components/projects/UploadModal';
import { Skeleton } from '../components/common/LoadingSkeleton';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Input from '../components/common/Input';
import {
  Plus,
  UserPlus,
  Search,
  RefreshCw,
  AlertTriangle,
  Info,
  Container,
  PauseCircle,
  ArrowRight,
} from 'lucide-react';

export default function Projects() {
  const {
    refreshTrigger,
    triggerRefresh,
    setNewProjectModalOpen,
  } = useWorkspace();

  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchFilter, setSearchFilter] = useState('');

  // Selected project for standalone upload modal
  const [uploadTargetProject, setUploadTargetProject] = useState(null);

  // Team Invite modal state
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('Member');
  const [inviteSubmitted, setInviteSubmitted] = useState(false);

  const fetchProjects = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listProjects();
      setProjects(data || []);
    } catch (err) {
      setError(
        err.message ||
          'Failed to connect to ModelForge API at http://127.0.0.1:8000. Ensure the FastAPI backend is running.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [refreshTrigger]);

  // Filter projects based on search query
  const filteredProjects = projects.filter((p) => {
    if (!searchFilter.trim()) return true;
    const term = searchFilter.toLowerCase();
    return (
      (p.title && p.title.toLowerCase().includes(term)) ||
      (p.framework && p.framework.toLowerCase().includes(term)) ||
      (p.status && p.status.toLowerCase().includes(term)) ||
      (p.id && p.id.toLowerCase().includes(term))
    );
  });

  // Section A: Deployed Projects (Confirmed running / deployed)
  const deployedProjects = filteredProjects.filter(
    (p) => p.status === 'deployed' || p.status === 'running'
  );

  // Section B: Suspended Projects (Confirmed suspended / stopped)
  const suspendedProjects = filteredProjects.filter(
    (p) => p.status === 'suspended' || p.status === 'stopped'
  );

  // Active / Packaging & Validated Services (created, uploaded, validating, validated, etc.)
  const activeServices = filteredProjects.filter(
    (p) =>
      p.status !== 'deployed' &&
      p.status !== 'running' &&
      p.status !== 'suspended' &&
      p.status !== 'stopped'
  );

  const handleInviteSubmit = (e) => {
    e.preventDefault();
    if (!inviteEmail) return;
    setInviteSubmitted(true);
  };

  return (
    <div className="mf-overview-page space-y-6">
      {/* 1. Overview Header */}
      <div className="mf-page-header mf-overview-header">
        <div className="mf-header-text-group header-text-group">
          <h1 className="mf-page-title overview-title">Overview</h1>
          <p className="mf-page-subtitle overview-subtitle">
            Deploy machine learning model containers, monitor automated CI pipelines, and manage cloud endpoints.
          </p>
        </div>

        <div className="mf-header-actions header-actions-group">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setInviteModalOpen(true)}
            leftIcon={<UserPlus size={14} className="text-[#00D6FF]" />}
          >
            Invite your team
          </Button>

          {/* Prominent Deploy New Project Entry Point */}
          <Button
            variant="primary"
            size="sm"
            onClick={() => setNewProjectModalOpen(true)}
            leftIcon={<Plus size={14} />}
          >
            Deploy New Project
          </Button>
        </div>
      </div>

      {/* 2. API Connection Error Banner */}
      {error && (
        <div className="mf-form-alert mf-form-alert-error" role="alert">
          <AlertTriangle size={18} className="shrink-0 text-red-400 mt-0.5" />
          <div className="flex-1 text-xs">
            <p className="font-semibold text-white">Connection to ModelForge API Failed</p>
            <p className="text-white/70 mt-0.5">{error}</p>
          </div>
          <Button variant="secondary" size="sm" onClick={fetchProjects} className="shrink-0">
            Retry Connection
          </Button>
        </div>
      )}

      {/* 3. Toolbar Row: Projects Heading + Search Filter + Refresh Button */}
      <div className="mf-projects-toolbar">
        <div className="toolbar-left">
          <h2 className="projects-heading">Projects</h2>
          <span className="projects-count-badge font-mono">
            {projects.length} {projects.length === 1 ? 'service' : 'services'}
          </span>
        </div>

        <div className="toolbar-right">
          <div className="search-input-wrapper">
            <Search size={14} className="search-field-icon" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Filter by name, framework, or status..."
              className="toolbar-search-input"
              aria-label="Filter projects"
            />
          </div>

          <button
            type="button"
            onClick={fetchProjects}
            className="toolbar-refresh-btn"
            title="Refresh projects list"
            aria-label="Refresh projects"
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* 4. Dashed-Outline "Deploy a New Project" Entry Point Card */}
      <div
        className="mf-deploy-hero-card"
        onClick={() => setNewProjectModalOpen(true)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') setNewProjectModalOpen(true);
        }}
      >
        <div className="deploy-hero-left">
          <div className="deploy-hero-icon-box">
            <Plus size={20} className="text-[#00D6FF]" />
          </div>
          <div>
            <h3 className="deploy-hero-title">Deploy a New Project</h3>
            <p className="deploy-hero-desc">
              Package model weights (.pkl, .onnx, .pt) or repository ZIP into an isolated production container with automated AST inspection.
            </p>
          </div>
        </div>
        <div className="deploy-hero-right">
          <span className="deploy-hero-action">
            <span>Start Deployment</span>
            <ArrowRight size={14} />
          </span>
        </div>
      </div>

      {/* Loading Skeletons */}
      {loading && projects.length === 0 && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl border border-white/5 bg-[#080A0D] space-y-3">
            <Skeleton height="20px" width="30%" />
            <Skeleton height="40px" width="100%" />
            <Skeleton height="40px" width="100%" />
          </div>
        </div>
      )}

      {/* SECTION A — DEPLOYED PROJECTS (Section 6 requirement) */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="section-title text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#10B981]" />
            <span>Deployed</span>
            <span className="text-xs text-white/40 font-mono font-normal">
              ({deployedProjects.length})
            </span>
          </h3>
        </div>

        {deployedProjects.length > 0 ? (
          <ProjectsTable
            projects={deployedProjects}
            onOpenUpload={(proj) => setUploadTargetProject(proj)}
            onDeleteSuccess={() => triggerRefresh()}
          />
        ) : (
          <div className="mf-subtle-empty-state">
            <Container size={22} className="text-white/30 mb-1.5" />
            <p className="empty-state-title">Your deployed services will appear here.</p>
            <p className="empty-state-subtitle">
              Once container runtime daemon is active, validated models will run with live public prediction endpoints.
            </p>
          </div>
        )}
      </section>

      {/* ACTIVE / VALIDATED SERVICES (Models in packaging & CI validation) */}
      {activeServices.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="section-title text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#00D6FF] shadow-[0_0_8px_#00D6FF]" />
              <span>Services in Packaging & Validation</span>
              <span className="text-xs text-white/40 font-mono font-normal">
                ({activeServices.length})
              </span>
            </h3>
          </div>

          <ProjectsTable
            projects={activeServices}
            onOpenUpload={(proj) => setUploadTargetProject(proj)}
            onDeleteSuccess={() => triggerRefresh()}
          />
        </section>
      )}

      {/* SECTION B — SUSPENDED PROJECTS (Section 6 requirement) */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="section-title text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
            <PauseCircle size={14} className="text-white/40" />
            <span>Suspended</span>
            <span className="text-xs text-white/40 font-mono font-normal">
              ({suspendedProjects.length})
            </span>
          </h3>
        </div>

        {suspendedProjects.length > 0 ? (
          <ProjectsTable
            projects={suspendedProjects}
            onOpenUpload={(proj) => setUploadTargetProject(proj)}
            onDeleteSuccess={() => triggerRefresh()}
          />
        ) : (
          <div className="mf-subtle-empty-state">
            <PauseCircle size={22} className="text-white/30 mb-1.5" />
            <p className="empty-state-title">You don't have any suspended services.</p>
            <p className="empty-state-subtitle">
              Services that are temporarily paused or scaled down will be cataloged here for immediate resume.
            </p>
          </div>
        )}
      </section>

      {/* Standalone Upload Modal */}
      {uploadTargetProject && (
        <UploadModal
          isOpen={Boolean(uploadTargetProject)}
          onClose={() => setUploadTargetProject(null)}
          projectId={uploadTargetProject.id}
          projectTitle={uploadTargetProject.title}
          onUploadSuccess={() => {
            triggerRefresh();
          }}
        />
      )}

      {/* Invite Team Modal */}
      <Modal
        isOpen={inviteModalOpen}
        onClose={() => {
          setInviteModalOpen(false);
          setInviteSubmitted(false);
          setInviteEmail('');
        }}
        title="Invite Team Members"
        subtitle="Collaborate on machine learning models, CI pipelines, and deployments."
      >
        {inviteSubmitted ? (
          <div className="space-y-4 py-3 text-center">
            <div className="p-3 bg-white/[0.02] border border-white/10 rounded-lg text-xs text-white/70">
              <p className="font-medium text-white mb-1">Invitation Queued</p>
              <p>
                An invitation has been registered for <span className="text-[#00D6FF]">{inviteEmail}</span> as {inviteRole}. Note: Backend invitation mailer is in preview mode.
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setInviteModalOpen(false);
                setInviteSubmitted(false);
                setInviteEmail('');
              }}
            >
              Done
            </Button>
          </div>
        ) : (
          <form onSubmit={handleInviteSubmit} className="space-y-4">
            <div className="p-3 rounded-lg border border-white/10 bg-white/[0.02] flex items-start gap-2.5 text-xs text-white/60">
              <Info size={16} className="text-[#00D6FF] shrink-0 mt-0.5" />
              <span>
                Backend email delivery will be dispatched through your workspace notification service once configured.
              </span>
            </div>

            <Input
              id="invite-email"
              label="Email Address"
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="colleague@modelforge.dev"
              required
            />

            <div className="mf-input-group">
              <label className="mf-input-label">Workspace Role</label>
              <select
                className="mf-input-field mf-select"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
              >
                <option value="Admin" className="bg-[#080A0D]">Admin (Full manage access)</option>
                <option value="Member" className="bg-[#080A0D]">Member (Deploy and validate)</option>
                <option value="Viewer" className="bg-[#080A0D]">Viewer (Read only)</option>
              </select>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-white/5">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setInviteModalOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" variant="primary">
                Send Invitation
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
