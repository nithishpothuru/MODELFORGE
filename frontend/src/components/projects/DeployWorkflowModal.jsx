import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Modal from '../common/Modal';
import Input from '../common/Input';
import Button from '../common/Button';
import Badge from '../common/Badge';
import { createProject, uploadProjectFile, validateProject } from '../../services/projects';
import { useWorkspace } from '../../context/WorkspaceContext';
import {
  Box,
  UploadCloud,
  FileArchive,
  Activity,
  Container,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  X,
  Package,
  Terminal,
  ExternalLink,
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

const STEPS = [
  { id: 'info', label: 'Project Info' },
  { id: 'upload', label: 'Upload Files' },
  { id: 'validate', label: 'CI Validation' },
  { id: 'deploy', label: 'Deployment' },
];

export default function DeployWorkflowModal({ isOpen, onClose }) {
  const navigate = useNavigate();
  const { triggerRefresh } = useWorkspace();
  const fileInputRef = useRef(null);

  // Workflow Step: 'info' | 'upload' | 'validate' | 'deploy'
  const [currentStep, setCurrentStep] = useState('info');

  // Step A: Project Info
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [framework, setFramework] = useState('PyTorch');
  const [version, setVersion] = useState('1.0.0');
  const [infoError, setInfoError] = useState('');
  const [creatingProject, setCreatingProject] = useState(false);
  const [createdProject, setCreatedProject] = useState(null);

  // Step B: Upload
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadResult, setUploadResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  // Step C: Validation
  const [validating, setValidating] = useState(false);
  const [validationReport, setValidationReport] = useState(null);
  const [validationError, setValidationError] = useState('');

  // Reset modal state
  const handleReset = () => {
    setCurrentStep('info');
    setTitle('');
    setDescription('');
    setFramework('PyTorch');
    setVersion('1.0.0');
    setInfoError('');
    setCreatingProject(false);
    setCreatedProject(null);

    setFile(null);
    setUploadProgress(0);
    setUploading(false);
    setUploadError('');
    setUploadResult(null);

    setValidating(false);
    setValidationReport(null);
    setValidationError('');
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  // STEP A SUBMIT: Create Project
  const handleStepASubmit = async (e) => {
    e.preventDefault();
    setInfoError('');

    if (!title.trim()) {
      setInfoError('Project name is required');
      return;
    }

    setCreatingProject(true);
    try {
      const proj = await createProject({
        title: title.trim(),
        description: description.trim() || null,
        framework,
        version: version.trim() || '1.0.0',
      });
      setCreatedProject(proj);
      triggerRefresh();
      setCurrentStep('upload');
    } catch (err) {
      setInfoError(err.message || 'Failed to register project on backend.');
    } finally {
      setCreatingProject(false);
    }
  };

  // STEP B: Handle File selection & Drop
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setUploadError('');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setUploadError('');
    }
  };

  // STEP B SUBMIT: Upload file to created project
  const handleStepBSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setUploadError('Please select a project ZIP or model weight file to upload.');
      return;
    }
    if (!createdProject?.id) {
      setUploadError('Project session expired. Please restart the deployment workflow.');
      return;
    }

    setUploading(true);
    setUploadError('');
    setUploadProgress(0);

    try {
      const res = await uploadProjectFile(createdProject.id, file, (percent) => {
        setUploadProgress(percent);
      });
      setUploadResult(res);
      triggerRefresh();

      // Automatically run CI Validation next
      setCurrentStep('validate');
      runCIValidation(createdProject.id);
    } catch (err) {
      setUploadError(err.message || 'File upload or extraction failed.');
    } finally {
      setUploading(false);
    }
  };

  // STEP C: Run CI Validation
  const runCIValidation = async (projId) => {
    setValidating(true);
    setValidationError('');
    try {
      const report = await validateProject(projId);
      setValidationReport(report);
      triggerRefresh();
    } catch (err) {
      setValidationError(
        err.message ||
          'Validation pipeline failed. Check that archive contents include valid Python entry scripts.'
      );
    } finally {
      setValidating(false);
    }
  };

  const handleFinish = () => {
    const targetId = createdProject?.id;
    handleClose();
    if (targetId) {
      navigate(`/dashboard/projects/${targetId}`);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Deploy New Project"
      subtitle="Package, validate and deploy your machine learning model."
      maxWidth="max-w-[860px]"
    >
      <div className="space-y-6">
        {/* Horizontal Deployment Stepper */}
        <div className="mf-stepper-container" role="progressbar" aria-label="Deployment steps">
          {STEPS.map((step, idx) => {
            const stepOrder = ['info', 'upload', 'validate', 'deploy'];
            const currentIndex = stepOrder.indexOf(currentStep);
            const isCompleted = idx < currentIndex;
            const isActive = idx === currentIndex;

            return (
              <React.Fragment key={step.id}>
                <div
                  className={`mf-stepper-item ${isActive ? 'is-active' : ''} ${
                    isCompleted ? 'is-completed' : ''
                  }`}
                  aria-current={isActive ? 'step' : undefined}
                >
                  <div className="stepper-circle">
                    {isCompleted ? <Check size={14} /> : idx + 1}
                  </div>
                  <span className="stepper-label">{step.label}</span>
                </div>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`mf-stepper-line ${
                      idx < currentIndex ? 'is-completed' : ''
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* ==================================================================
            STEP A: PROJECT INFORMATION
            ================================================================== */}
        {currentStep === 'info' && (
          <form onSubmit={handleStepASubmit} className="space-y-5">
            {infoError && (
              <div className="mf-form-alert mf-form-alert-error" role="alert">
                <AlertTriangle size={16} className="shrink-0" />
                <span>{infoError}</span>
              </div>
            )}

            <Input
              id="deploy-project-title"
              label="Project / Service Name"
              type="text"
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                if (infoError) setInfoError('');
              }}
              placeholder="e.g. Vision Transformer Inference"
              required
              leftIcon={<Box size={16} />}
              hint="Unique identifier for your model deployment on ModelForge"
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="mf-input-group">
                <label htmlFor="deploy-framework" className="mf-input-label">
                  ML Framework / Runtime <span className="text-[#00D6FF]">*</span>
                </label>
                <div className="mf-input-wrapper">
                  <select
                    id="deploy-framework"
                    className="mf-input-field mf-select"
                    value={framework}
                    onChange={(e) => setFramework(e.target.value)}
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
                id="deploy-version"
                label="Version Tag"
                type="text"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                placeholder="1.0.0"
              />
            </div>

            <div className="mf-input-group">
              <label htmlFor="deploy-description" className="mf-input-label">
                Description (Optional)
              </label>
              <div className="mf-input-wrapper">
                <textarea
                  id="deploy-description"
                  className="mf-input-field mf-textarea"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe your model architecture, inference inputs, or intended use..."
                />
              </div>
            </div>

            <div className="flex justify-end items-center gap-3 pt-4 border-t border-white/10">
              <Button type="button" variant="secondary" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={creatingProject}
                rightIcon={<ArrowRight size={15} />}
              >
                Continue to Upload
              </Button>
            </div>
          </form>
        )}

        {/* ==================================================================
            STEP B: UPLOAD PROJECT FILES
            ================================================================== */}
        {currentStep === 'upload' && (
          <form onSubmit={handleStepBSubmit} className="space-y-4">
            <div className="p-3 bg-white/[0.02] border border-white/10 rounded-lg flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Box size={16} className="text-[#00D6FF]" />
                <span className="font-semibold text-white">{createdProject?.title}</span>
                <span className="text-white/40 font-mono">({framework} v{version})</span>
              </div>
              <Badge status="created" size="xs">Step 2 of 4</Badge>
            </div>

            {uploadError && (
              <div className="mf-form-alert mf-form-alert-error" role="alert">
                <AlertTriangle size={16} className="shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            {/* Drag & Drop Area */}
            <div
              className={`mf-dropzone ${dragActive ? 'is-active' : ''} ${file ? 'has-file' : ''}`}
              onDragEnter={() => setDragActive(true)}
              onDragLeave={() => setDragActive(false)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".zip,.pkl,.onnx,.pt,.bin"
                onChange={handleFileChange}
              />

              {file ? (
                <div className="flex flex-col items-center">
                  <FileArchive size={36} className="text-[#00D6FF] mb-2" />
                  <span className="text-sm font-semibold text-white">{file.name}</span>
                  <span className="text-xs text-white/50 mt-1">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB &bull; Ready to upload
                  </span>
                  <button
                    type="button"
                    className="text-xs text-red-400 hover:underline mt-2 flex items-center gap-1"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                  >
                    <X size={12} /> Remove file
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <UploadCloud size={40} className="text-[#00D6FF] mb-2" />
                  <p className="text-sm font-semibold text-white">
                    Drag and drop model archive or browse files
                  </p>
                  <p className="text-xs text-white/50 mt-1 max-w-sm">
                    Recommended: <strong>.zip</strong> containing Python inference scripts & weights. Also supports standalone weight files (<strong>.pkl, .onnx, .pt, .bin</strong>).
                  </p>
                  <div className="mt-3">
                    <span className="px-3 py-1.5 bg-white/10 hover:bg-white/15 text-white text-xs font-medium rounded-lg transition-colors">
                      Browse Files
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Upload Progress */}
            {uploading && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-white/60">
                  <span>Uploading to ModelForge Storage & Extracting...</span>
                  <span className="font-mono text-[#00D6FF]">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-[#00D6FF] h-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex justify-between items-center pt-4 border-t border-white/10">
              <Button
                type="button"
                variant="secondary"
                disabled={uploading}
                onClick={() => setCurrentStep('info')}
                leftIcon={<ArrowLeft size={14} />}
              >
                Back
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={uploading}
                disabled={!file}
                rightIcon={<ArrowRight size={15} />}
              >
                Upload & Extract Files
              </Button>
            </div>
          </form>
        )}

        {/* ==================================================================
            STEP C: ANALYSIS & VALIDATION
            ================================================================== */}
        {currentStep === 'validate' && (
          <div className="space-y-4">
            <div className="p-3 bg-white/[0.02] border border-white/10 rounded-lg flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-[#00D6FF]" />
                <span className="font-semibold text-white">CI Code & Dependency Validation</span>
                {uploadResult?.file_count && (
                  <span className="text-white/40 font-mono">({uploadResult.file_count} files extracted)</span>
                )}
              </div>
              <Badge status={validating ? 'validating' : validationReport?.status || 'pending'} size="xs">
                {validating ? 'Analyzing...' : validationReport?.status || 'Ready'}
              </Badge>
            </div>

            {validationError && (
              <div className="mf-form-alert mf-form-alert-error" role="alert">
                <AlertTriangle size={16} className="shrink-0" />
                <div className="flex-1 text-xs">
                  <p className="font-medium text-white">Validation Pipeline Alert</p>
                  <p className="text-white/70 mt-0.5">{validationError}</p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => runCIValidation(createdProject.id)}
                >
                  Retry
                </Button>
              </div>
            )}

            {validating && (
              <div className="py-8 text-center space-y-3">
                <div className="w-10 h-10 rounded-full bg-[#00D6FF]/10 border border-[#00D6FF]/30 flex items-center justify-center mx-auto text-[#00D6FF] animate-pulse">
                  <Activity size={20} className="animate-spin" />
                </div>
                <p className="text-sm font-medium text-white">
                  Executing AST Inspection & Dependency Resolution...
                </p>
                <p className="text-xs text-white/50 max-w-sm mx-auto">
                  Parsing Python source files, checking imports, and resolving pinned requirements in an isolated sandbox.
                </p>
              </div>
            )}

            {!validating && validationReport && (
              <div className="space-y-4">
                {/* Highlights grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 rounded-lg border border-white/10 bg-black/40">
                    <span className="text-white/40 block mb-1">Python Version:</span>
                    <span className="text-white font-mono font-bold">
                      {validationReport.python_version?.version || '3.11'}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border border-white/10 bg-black/40">
                    <span className="text-white/40 block mb-1">Syntax Validation:</span>
                    <span className="text-emerald-400 font-medium">
                      {validationReport.syntax_validation?.valid_files || 0} /{' '}
                      {validationReport.syntax_validation?.total_files || 0} Files Valid
                    </span>
                  </div>

                  <div className="p-3 rounded-lg border border-white/10 bg-black/40">
                    <span className="text-white/40 block mb-1">Main Entry Point:</span>
                    <span className="text-[#00D6FF] font-mono truncate block">
                      {validationReport.entry_point_validation?.detected_entry_point || 'main.py'}
                    </span>
                  </div>
                </div>

                {/* Resolved packages preview */}
                <div className="p-3 rounded-lg border border-white/10 bg-black/30 space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-white/80">
                    <span className="flex items-center gap-1.5">
                      <Package size={14} className="text-[#00D6FF]" />
                      <span>Resolved Dependencies ({validationReport.dependency_resolution?.resolved_packages?.length || 0})</span>
                    </span>
                    <span className="text-[11px] font-mono text-[#00D6FF]">requirements-resolved.txt generated</span>
                  </div>

                  {validationReport.dependency_resolution?.resolved_packages?.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                      {validationReport.dependency_resolution.resolved_packages.map((pkg, i) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[11px] font-mono text-white/80">
                          {pkg.name}=={pkg.version}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-white/40 italic">
                      Zero external dependencies required.
                    </p>
                  )}
                </div>
              </div>
            )}

            <div className="flex justify-between items-center pt-4 border-t border-white/10">
              <Button
                type="button"
                variant="secondary"
                disabled={validating}
                onClick={() => setCurrentStep('upload')}
                leftIcon={<ArrowLeft size={14} />}
              >
                Back to Upload
              </Button>
              <Button
                type="button"
                variant="primary"
                disabled={validating || !validationReport}
                onClick={() => setCurrentStep('deploy')}
                rightIcon={<ArrowRight size={15} />}
              >
                Proceed to Deployment
              </Button>
            </div>
          </div>
        )}

        {/* ==================================================================
            STEP D: DEPLOYMENT
            ================================================================== */}
        {currentStep === 'deploy' && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] flex items-start gap-3">
              <div className="p-2 rounded-lg bg-[#00D6FF]/10 border border-[#00D6FF]/20 text-[#00D6FF] shrink-0 mt-0.5">
                <Container size={22} />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold text-white text-sm">
                    Container Build & Runtime Pipeline
                  </h4>
                  <Badge status="pending" size="xs">Engine Standby</Badge>
                </div>
                <p className="text-xs text-white/70">
                  Model code, dependencies, and entry points have been successfully inspected and verified. Container image build and public prediction URL generation are queued for backend daemon integration.
                </p>
              </div>
            </div>

            {/* Target Dockerfile Preview */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-white/60">
                <span className="flex items-center gap-1.5 font-mono">
                  <Terminal size={13} />
                  <span>Generated Multi-Stage Dockerfile</span>
                </span>
                <span className="text-[11px] text-[#00D6FF] font-mono">Ready for runner</span>
              </div>
              <pre className="p-3 bg-black/80 border border-white/10 rounded-lg text-xs font-mono text-white/70 overflow-x-auto max-h-40">
{`FROM python:${validationReport?.python_version?.version || '3.11'}-slim AS builder
WORKDIR /app
COPY requirements-resolved.txt .
RUN pip install --no-cache-dir --user -r requirements-resolved.txt

FROM python:${validationReport?.python_version?.version || '3.11'}-slim AS runner
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . .
EXPOSE 8000
CMD ["uvicorn", "${validationReport?.entry_point_validation?.detected_entry_point ? validationReport.entry_point_validation.detected_entry_point.replace('.py', '') : 'main'}:app", "--host", "0.0.0.0", "--port", "8000"]`}
              </pre>
            </div>

            <div className="flex justify-end items-center gap-3 pt-4 border-t border-white/10">
              <Button type="button" variant="secondary" onClick={handleClose}>
                Close
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={handleFinish}
                rightIcon={<ExternalLink size={14} />}
              >
                Open Project Details
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
