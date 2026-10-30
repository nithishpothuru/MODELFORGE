import React, { useState, useRef } from 'react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import Input from '../common/Input';
import { uploadProjectFile, quickUnpack } from '../../services/projects';
import { useWorkspace } from '../../context/WorkspaceContext';
import {
  UploadCloud,
  FileArchive,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  ArrowRight,
} from 'lucide-react';

export default function UploadModal({
  isOpen,
  onClose,
  projectId = null,
  projectTitle = '',
  onUploadSuccess,
}) {
  const { triggerRefresh } = useWorkspace();
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [quickTitle, setQuickTitle] = useState('');
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    setUploading(true);
    setError('');
    setProgress(0);

    try {
      let res;
      if (projectId) {
        res = await uploadProjectFile(projectId, file, (percent) => {
          setProgress(percent);
        });
      } else {
        const titleToUse = quickTitle.trim() || file.name.replace(/\.[^/.]+$/, '');
        res = await quickUnpack(file, titleToUse, (percent) => {
          setProgress(percent);
        });
      }

      setResult(res);
      triggerRefresh();
      if (onUploadSuccess) {
        onUploadSuccess(res);
      }
    } catch (err) {
      setError(err.message || 'File upload or extraction failed');
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setProgress(0);
    setError('');
    setResult(null);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        handleReset();
        onClose();
      }}
      title={projectId ? `Upload Files to ${projectTitle || 'Project'}` : 'Quick Model Import & Unpack'}
      subtitle="Upload your ML model repository ZIP or model weight files (.pkl, .onnx, .pt)."
    >
      {result ? (
        <div className="py-4 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mx-auto text-emerald-400">
            <CheckCircle2 size={26} />
          </div>

          <div>
            <h4 className="text-base font-semibold text-white">Upload & Extraction Complete</h4>
            <p className="text-xs text-white/60 mt-1">{result.message}</p>
          </div>

          {result.extracted_files && result.extracted_files.length > 0 && (
            <div className="p-3 bg-white/[0.02] border border-white/10 rounded-lg text-left max-h-40 overflow-y-auto">
              <p className="text-xs font-medium text-white/80 mb-2 flex items-center gap-1.5">
                <FileCode size={13} className="text-[#00D6FF]" />
                <span>Extracted Files ({result.extracted_files.length})</span>
              </p>
              <ul className="space-y-1 text-[11px] font-mono text-white/60">
                {result.extracted_files.slice(0, 10).map((fname, i) => (
                  <li key={i} className="truncate">• {fname}</li>
                ))}
                {result.extracted_files.length > 10 && (
                  <li className="text-white/40">...and {result.extracted_files.length - 10} more files</li>
                )}
              </ul>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                handleReset();
                onClose();
              }}
            >
              Done
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="mf-form-alert mf-form-alert-error" role="alert">
              <AlertTriangle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!projectId && (
            <Input
              label="Project Title"
              type="text"
              value={quickTitle}
              onChange={(e) => setQuickTitle(e.target.value)}
              placeholder="e.g. BERT Sentiment Classifier"
              hint="Leave blank to use the uploaded file name"
            />
          )}

          {/* Drag & Drop Zone */}
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
              accept=".zip,.pkl,.onnx,.pt,.bin,.tar,.gz"
              onChange={handleFileChange}
            />

            {file ? (
              <div className="flex flex-col items-center">
                <FileArchive size={36} className="text-[#00D6FF] mb-2" />
                <span className="text-sm font-medium text-white">{file.name}</span>
                <span className="text-xs text-white/50 mt-1">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB &bull; Click or drag to replace
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <UploadCloud size={38} className="text-[#00D6FF] mb-2" />
                <p className="text-sm font-medium text-white">
                  Drag & drop archive or model file here
                </p>
                <p className="text-xs text-white/50 mt-1">
                  Supported: ZIP archives, .pkl, .onnx, .pt, .bin (up to 100MB)
                </p>
              </div>
            )}
          </div>

          {/* Progress bar */}
          {uploading && (
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-white/60">
                <span>Uploading & Unpacking...</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-[#00D6FF] h-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3">
            <Button
              type="button"
              variant="secondary"
              disabled={uploading}
              onClick={() => {
                handleReset();
                onClose();
              }}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={uploading}
              disabled={!file}
              rightIcon={<ArrowRight size={15} />}
            >
              {projectId ? 'Upload to Project' : 'Unpack and Create'}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

