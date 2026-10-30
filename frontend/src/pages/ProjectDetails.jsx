import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  getProject,
  validateProject,
  getProjectValidation,
  updateProject,
} from '../services/projects';
import ValidationReportView from '../components/projects/ValidationReportView';
import DeploymentView from '../components/projects/DeploymentView';
import UploadModal from '../components/projects/UploadModal';
import DeleteProjectModal from '../components/projects/DeleteProjectModal';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import Input from '../components/common/Input';
import {
  ArrowLeft,
  Box,
  Play,
  Upload,
  RefreshCw,
  Trash2,
  Edit2,
  FileCode,
  Layers,
  Calendar,
  AlertTriangle,
  Container,
  Activity,
  Copy,
  Check,
} from 'lucide-react';

const FRAMEWORKS = [
  'PyTorch',
  'Scikit-learn',
  'TensorFlow',
  'ONNX',
  'HuggingFace',
  'Custom Python ML',
];

export default function ProjectDetails() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [validationReport, setValidationReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState('');
  const [validationError, setValidationError] = useState('');
  const [idCopied, setIdCopied] = useState(false);

  // Active tab: 'validation' | 'files' | 'deployment'
  const [activeTab, setActiveTab] = useState('validation');

  // Modals state
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  // Edit form state
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editFramework, setEditFramework] = useState('PyTorch');
  const [editVersion, setEditVersion] = useState('1.0.0');
  const [savingEdit, setSavingEdit] = useState(false);

  const fetchProjectData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getProject(projectId);
      setProject(data);
      setEditTitle(data.title || '');
      setEditDesc(data.description || '');
      setEditFramework(data.framework || 'PyTorch');
      setEditVersion(data.version || '1.0.0');

      if (data.validation_report) {
        setValidationReport(data.validation_report);
      } else {
        try {
          const report = await getProjectValidation(projectId);
          setValidationReport(report);
        } catch {
          // No validation report yet, non-fatal
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchProjectData();
  }, [fetchProjectData]);

  const handleCopyId = () => {
    if (!project?.id) return;
    navigator.clipboard.writeText(project.id).then(() => {
      setIdCopied(true);
      setTimeout(() => setIdCopied(false), 2000);
    });
  };

  const handleRunValidation = async () => {
    setValidating(true);
    setValidationError('');
    try {
      const report = await validateProject(projectId);
      setValidationReport(report);
      setActiveTab('validation');
      await fetchProjectData();
    } catch (err) {
      setValidationError(err.message || 'Validation failed. Ensure project files are uploaded.');
    } finally {
      setValidating(false);
    }
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    setSavingEdit(true);
    try {
      const updated = await updateProject(projectId, {
        title: editTitle.trim(),
        description: editDesc.trim() || null,
        framework: editFramework,
        version: editVersion.trim() || '1.0.0',
      });
      setProject(updated);
      setEditModalOpen(false);
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    } finally {
      setSavingEdit(false);
    }
  };

  if (loading && !project) {
    return (
      <div className="py-20 text-center space-y-3">
        <RefreshCw size={26} className="animate-spin mx-auto text-[#00D6FF]" />
        <p className="text-sm text-white/50">Loading project metadata from backend...</p>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="p-12 text-center space-y-4 max-w-lg mx-auto">
        <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center mx-auto text-red-400">
          <AlertTriangle size={24} />
        </div>
        <h2 className="text-lg font-bold text-white">Project Not Found</h2>
        <p className="text-xs text-white/60 leading-relaxed">
          {error || 'The requested project could not be loaded or may have been deleted.'}
        </p>
        <Link to="/dashboard/projects">
          <Button variant="secondary" size="sm" leftIcon={<ArrowLeft size={14} />}>
            Back to Projects
          </Button>
        </Link>
      </div>
    );
  }

  const extractedFiles =
    project.metadata?.extracted_files ||
    project.metadata?.supabase_extracted_files ||
    [];

  const isDeployed =
    project.status === 'deployed' || project.status === 'running';
  const isSuspended =
    project.status === 'suspended' || project.status === 'stopped';

  const formattedDate = project.created_at
    ? new Date(project.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : 'Not specified';

  return (
    <div className="mf-project-details-page space-y-7">
      {/* ====================================================================
          A. PAGE HEADER NAVIGATION & ACTIONS
          ==================================================================== */}
      <div className="mf-details-nav-row">
        <Link to="/dashboard/projects" className="mf-details-back-link">
          <ArrowLeft size={15} />
          <span>Back to Projects</span>
        </Link>

        {/* Edit and Delete Buttons (No broken three-dot menu!) */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setEditModalOpen(true)}
            leftIcon={<Edit2 size={13} />}
          >
            Edit Details
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => setDeleteModalOpen(true)}
            leftIcon={<Trash2 size={13} />}
          >
            Delete Service
          </Button>
        </div>
      </div>

      {/* ====================================================================
          B & C. PROJECT OVERVIEW CARD & PRIMARY ACTIONS
          ==================================================================== */}
      <div className="mf-details-overview-card">
        {/* Header Row: Title & Primary Actions */}
        <div className="mf-details-header-row">
          <div className="mf-details-title-group">
            <div className="mf-details-icon-box">
              <Box size={24} />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="mf-details-title">{project.title}</h1>
                <Badge status={project.status} size="sm" />
              </div>
              <p className="mf-details-description">
                {project.description || 'No description provided for this machine learning deployment.'}
              </p>
            </div>
          </div>

          {/* Primary Actions: Upload Archive & Run CI Validation */}
          <div className="mf-details-actions-group">
            <Button
              variant="secondary"
              size="md"
              onClick={() => setUploadModalOpen(true)}
              leftIcon={<Upload size={15} className="text-[#00D6FF]" />}
            >
              Upload Archive
            </Button>

            <Button
              variant="primary"
              size="md"
              loading={validating}
              disabled={validating}
              onClick={handleRunValidation}
              leftIcon={!validating && <Play size={15} />}
            >
              Run CI Validation
            </Button>
          </div>
        </div>

        {/* Clean Two-Column Metadata Layout on Desktop */}
        <div className="mf-details-meta-grid">
          {/* Property 1: Project Name */}
          <div className="mf-meta-cell">
            <span className="mf-meta-label">Project Name</span>
            <span className="mf-meta-value font-medium">{project.title}</span>
          </div>

          {/* Property 2: Status */}
          <div className="mf-meta-cell">
            <span className="mf-meta-label">Deployment Status</span>
            <div className="mf-meta-value">
              <Badge status={project.status} size="xs" />
              <span className="text-xs text-white/50">
                {isDeployed ? 'Serving active inference traffic' : isSuspended ? 'Temporarily suspended' : 'Build & container verification'}
              </span>
            </div>
          </div>

          {/* Property 3: Framework */}
          <div className="mf-meta-cell">
            <span className="mf-meta-label">ML Framework</span>
            <span className="mf-meta-value font-mono">
              <Layers size={14} className="text-[#00D6FF]" />
              <span>{project.framework || 'Custom Python ML'}</span>
              {project.python_version && (
                <span className="text-white/40 text-xs">({project.python_version})</span>
              )}
            </span>
          </div>

          {/* Property 4: Version Tag */}
          <div className="mf-meta-cell">
            <span className="mf-meta-label">Version Tag</span>
            <span className="mf-meta-value font-mono text-[#00D6FF]">
              v{project.version || '1.0.0'}
            </span>
          </div>

          {/* Property 5: Created Date */}
          <div className="mf-meta-cell">
            <span className="mf-meta-label">Created Date</span>
            <span className="mf-meta-value font-mono text-white/80">
              <Calendar size={13} className="text-white/40" />
              <span>{formattedDate}</span>
            </span>
          </div>

          {/* Property 6: Project ID (Truncated with full copy-to-clipboard) */}
          <div className="mf-meta-cell">
            <span className="mf-meta-label">Project Identifier</span>
            <div className="mf-meta-value font-mono">
              <span className="text-white/70" title={project.id}>
                {project.id.length > 20
                  ? `${project.id.slice(0, 10)}...${project.id.slice(-6)}`
                  : project.id}
              </span>
              <button
                type="button"
                className="mf-id-copy-btn"
                onClick={handleCopyId}
                aria-label="Copy Project ID"
                title="Copy Project ID to clipboard"
              >
                {idCopied ? (
                  <>
                    <Check size={12} className="text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Validation Error Alert Banner if validation failed */}
      {validationError && (
        <div className="mf-form-alert mf-form-alert-error" role="alert">
          <AlertTriangle size={16} className="shrink-0" />
          <div className="flex-1 text-xs">
            <p className="font-semibold text-white">Validation Notice</p>
            <p className="text-white/80 mt-0.5">{validationError}</p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRunValidation}
            disabled={validating}
          >
            Retry
          </Button>
        </div>
      )}

      {/* ====================================================================
          D. DEPLOYMENT PIPELINE OVERVIEW
          ==================================================================== */}
      <section className="mf-pipeline-section">
        <div className="space-y-0.5">
          <h2 className="text-base font-bold text-white tracking-tight">Deployment Pipeline</h2>
          <p className="text-xs text-white/50">
            Real-time stage verification across AST syntax validation, archive extraction, and container deployment.
          </p>
        </div>

        <div className="mf-pipeline-grid">
          {/* Stage 1: CI Validation */}
          <div
            className={`mf-pipeline-card ${
              validating ? 'is-active' : validationReport?.status === 'passed' ? 'is-passed' : ''
            }`}
          >
            <div className="mf-pipeline-card-top">
              <span className="mf-pipeline-stage-badge">Stage 1</span>
              <Badge
                status={validating ? 'validating' : validationReport ? validationReport.status : 'pending'}
                size="xs"
              >
                {validating ? 'Analyzing...' : validationReport?.status || 'Pending'}
              </Badge>
            </div>

            <div className="mf-pipeline-icon-title">
              <div className="p-2 rounded-lg bg-white/5 border border-white/10 text-[#00D6FF]">
                <Activity size={18} className={validating ? 'animate-spin' : ''} />
              </div>
              <h3 className="mf-pipeline-card-title">CI Code Validation</h3>
            </div>

            <p className="mf-pipeline-card-desc">
              {validationReport
                ? `AST verified: ${validationReport.syntax_validation?.valid_files || 0} valid Python files, ${validationReport.dependency_resolution?.resolved_packages?.length || 0} resolved packages.`
                : 'Inspects Python syntax trees, checks imports, and resolves lockfile dependencies.'}
            </p>
          </div>

          {/* Stage 2: File Analysis & Extraction */}
          <div
            className={`mf-pipeline-card ${extractedFiles.length > 0 ? 'is-passed' : ''}`}
          >
            <div className="mf-pipeline-card-top">
              <span className="mf-pipeline-stage-badge">Stage 2</span>
              <Badge
                status={extractedFiles.length > 0 ? 'uploaded' : 'pending'}
                size="xs"
              >
                {extractedFiles.length > 0 ? 'Extracted' : 'Awaiting Archive'}
              </Badge>
            </div>

            <div className="mf-pipeline-icon-title">
              <div className="p-2 rounded-lg bg-white/5 border border-white/10 text-[#00D6FF]">
                <FileCode size={18} />
              </div>
              <h3 className="mf-pipeline-card-title">Archive & Extraction</h3>
            </div>

            <p className="mf-pipeline-card-desc">
              {extractedFiles.length > 0
                ? `${extractedFiles.length} files uncompressed and sanitized in workspace storage.`
                : 'Upload your model weights or repository ZIP to trigger automated archive unpack.'}
            </p>
          </div>

          {/* Stage 3: Container Deployment */}
          <div
            className={`mf-pipeline-card ${isDeployed ? 'is-passed' : ''}`}
          >
            <div className="mf-pipeline-card-top">
              <span className="mf-pipeline-stage-badge">Stage 3</span>
              <Badge
                status={isDeployed ? 'deployed' : isSuspended ? 'suspended' : 'pending'}
                size="xs"
              >
                {isDeployed ? 'Running' : isSuspended ? 'Suspended' : 'Engine Standby'}
              </Badge>
            </div>

            <div className="mf-pipeline-icon-title">
              <div className="p-2 rounded-lg bg-white/5 border border-white/10 text-[#00D6FF]">
                <Container size={18} />
              </div>
              <h3 className="mf-pipeline-card-title">Container Deployment</h3>
            </div>

            <p className="mf-pipeline-card-desc">
              {isDeployed
                ? 'Container running with dedicated port binding and health check endpoint active.'
                : 'Builds multi-stage container and registers dynamic reverse proxy route for prediction requests.'}
            </p>
          </div>
        </div>
      </section>

      {/* ====================================================================
          E & F. CI VALIDATION REPORT & PROJECT INFORMATION TABS
          ==================================================================== */}
      <section className="space-y-4">
        {/* Navigation Tabs Bar */}
        <div className="mf-details-tabs-bar" role="tablist" aria-label="Project details sections">
          <button
            type="button"
            className={`mf-details-tab-btn ${activeTab === 'validation' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('validation')}
            role="tab"
            aria-selected={activeTab === 'validation'}
          >
            <Activity size={15} />
            <span>CI Validation Report</span>
            {validationReport && (
              <Badge status={validationReport.status} size="xs" />
            )}
          </button>

          <button
            type="button"
            className={`mf-details-tab-btn ${activeTab === 'files' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('files')}
            role="tab"
            aria-selected={activeTab === 'files'}
          >
            <FileCode size={15} />
            <span>Extracted Files</span>
            {extractedFiles.length > 0 && (
              <span className="text-xs text-white/40 font-mono">({extractedFiles.length})</span>
            )}
          </button>

          <button
            type="button"
            className={`mf-details-tab-btn ${activeTab === 'deployment' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('deployment')}
            role="tab"
            aria-selected={activeTab === 'deployment'}
          >
            <Container size={15} />
            <span>Container Deployment</span>
          </button>
        </div>

        {/* Tab Content Display */}
        <div>
          {/* TAB 1: CI VALIDATION REPORT */}
          {activeTab === 'validation' && (
            <div>
              {validationReport ? (
                <ValidationReportView report={validationReport} />
              ) : (
                <div className="p-12 text-center border border-white/10 rounded-2xl bg-[#080A0D] space-y-4">
                  <div className="w-12 h-12 rounded-full bg-[#00D6FF]/10 border border-[#00D6FF]/25 flex items-center justify-center mx-auto text-[#00D6FF]">
                    <Activity size={24} />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-base font-semibold text-white">No CI Validation Report Yet</h3>
                    <p className="text-xs text-white/50 max-w-md mx-auto leading-relaxed">
                      Run the ModelForge CI validation pipeline to inspect your codebase, analyze syntax, resolve requirements, and verify entry points.
                    </p>
                  </div>
                  <div className="pt-2">
                    <Button
                      variant="primary"
                      size="md"
                      loading={validating}
                      disabled={validating}
                      onClick={handleRunValidation}
                      leftIcon={!validating && <Play size={15} />}
                    >
                      Run CI Validation Pipeline
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: EXTRACTED FILES MANIFEST */}
          {activeTab === 'files' && (
            <div className="space-y-4">
              <div className="p-5 rounded-xl border border-white/10 bg-[#080A0D] space-y-3">
                <h3 className="text-sm font-semibold text-white">Project File Manifest</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
                  <div className="p-3 bg-black/50 border border-white/5 rounded-lg space-y-1">
                    <span className="text-white/40 block text-[11px] uppercase tracking-wider">Main Entry Point</span>
                    <span className="text-[#00D6FF] font-medium truncate block">
                      {project.main_file || validationReport?.entry_point_validation?.detected_entry_point || 'main.py (auto-detected)'}
                    </span>
                  </div>
                  <div className="p-3 bg-black/50 border border-white/5 rounded-lg space-y-1">
                    <span className="text-white/40 block text-[11px] uppercase tracking-wider">Requirements Manifest</span>
                    <span className="text-white font-medium truncate block">
                      {project.requirements_file || 'requirements.txt (auto-detected)'}
                    </span>
                  </div>
                </div>
              </div>

              {extractedFiles.length > 0 ? (
                <div className="p-5 rounded-xl border border-white/10 bg-[#080A0D] space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-white/80 uppercase tracking-wider">
                      Extracted Files ({extractedFiles.length})
                    </h4>
                    <span className="text-[11px] text-white/40 font-mono">Ready for compilation</span>
                  </div>
                  <div className="max-h-80 overflow-y-auto space-y-1.5 pr-1 font-mono text-xs">
                    {extractedFiles.map((fname, i) => (
                      <div
                        key={i}
                        className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex items-center gap-2.5 text-white/80 hover:bg-white/[0.03] transition-colors"
                      >
                        <FileCode size={14} className="text-[#00D6FF] shrink-0" />
                        <span className="truncate">{fname}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-10 text-center border border-white/10 rounded-xl bg-[#080A0D] space-y-3">
                  <p className="text-xs text-white/50">No files extracted for this project yet.</p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setUploadModalOpen(true)}
                    leftIcon={<Upload size={14} className="text-[#00D6FF]" />}
                  >
                    Upload Model Archive
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: CONTAINER DEPLOYMENT */}
          {activeTab === 'deployment' && (
            <DeploymentView project={project} />
          )}
        </div>
      </section>

      {/* ====================================================================
          MODALS: UPLOAD, EDIT, DELETE
          ==================================================================== */}
      {/* Upload Modal */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        projectId={project.id}
        projectTitle={project.title}
        onUploadSuccess={() => {
          fetchProjectData();
        }}
      />

      {/* Edit Project Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit Project Details"
        subtitle="Update project metadata, version tag, and machine learning framework."
      >
        <form onSubmit={handleSaveEdit} className="space-y-4">
          <Input
            id="edit-project-title"
            label="Project Title"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            required
            placeholder="e.g. Vision Transformer Inference"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="mf-input-group">
              <label htmlFor="edit-project-framework" className="mf-input-label">
                ML Framework / Runtime
              </label>
              <div className="mf-input-wrapper">
                <select
                  id="edit-project-framework"
                  className="mf-input-field mf-select"
                  value={editFramework}
                  onChange={(e) => setEditFramework(e.target.value)}
                >
                  {FRAMEWORKS.map((fw) => (
                    <option key={fw} value={fw} className="bg-[#080A0D]">
                      {fw}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <Input
              id="edit-project-version"
              label="Version Tag"
              value={editVersion}
              onChange={(e) => setEditVersion(e.target.value)}
              placeholder="1.0.0"
            />
          </div>

          <div className="mf-input-group">
            <label htmlFor="edit-project-description" className="mf-input-label">
              Description (Optional)
            </label>
            <div className="mf-input-wrapper">
              <textarea
                id="edit-project-description"
                className="mf-input-field mf-textarea"
                rows={3}
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                placeholder="Describe model architecture or checkpoint specifications..."
              />
            </div>
          </div>

          <div className="flex justify-end items-center gap-3 pt-4 border-t border-white/10">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setEditModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={savingEdit}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && (
        <DeleteProjectModal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          project={project}
          onSuccess={() => {
            navigate('/dashboard/projects', { replace: true });
          }}
        />
      )}
    </div>
  );
}
