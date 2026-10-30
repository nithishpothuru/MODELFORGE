import React, { useState } from 'react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import { AlertTriangle, Trash2 } from 'lucide-react';
import { deleteProject } from '../../services/projects';
import { useWorkspace } from '../../context/WorkspaceContext';

export default function DeleteProjectModal({
  isOpen,
  onClose,
  project,
  onSuccess,
}) {
  const { triggerRefresh } = useWorkspace();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');

  if (!project) return null;

  const handleDelete = async () => {
    if (deleting) return;
    setDeleting(true);
    setError('');

    try {
      await deleteProject(project.id);
      triggerRefresh();
      if (onSuccess) {
        onSuccess(project.id);
      }
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to delete service. Please try again.');
    } finally {
      setDeleting(false);
    }
  };

  const handleClose = () => {
    if (deleting) return; // Prevent dismissing while request is in progress
    setError('');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Delete Project?"
      maxWidth="max-w-[420px]"
      showClose={!deleting}
    >
      <div className="space-y-4">
        {/* Warning Icon & Confirmation Text */}
        <div className="flex items-start gap-3.5 pt-1">
          <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/25 flex items-center justify-center text-red-400 shrink-0 mt-0.5">
            <AlertTriangle size={20} />
          </div>
          <div className="space-y-1 min-w-0">
            <p className="text-xs text-white/80 leading-relaxed">
              Are you sure you want to delete{' '}
              <strong className="text-white font-semibold break-words">
                "{project.title}"
              </strong>
              ? This action cannot be undone.
            </p>
            <p className="text-[11px] text-white/45 leading-relaxed">
              All associated model weights, container runtimes, AST inspection reports, and prediction endpoints will be permanently removed.
            </p>
          </div>
        </div>

        {/* Error Alert Display */}
        {error && (
          <div className="mf-form-alert mf-form-alert-error" role="alert">
            <AlertTriangle size={15} className="shrink-0" />
            <span className="text-xs leading-normal">{error}</span>
          </div>
        )}

        {/* Action Buttons Footer */}
        <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-3 pt-4 border-t border-white/10">
          <Button
            type="button"
            variant="secondary"
            size="md"
            disabled={deleting}
            onClick={handleClose}
            className="w-full sm:w-auto min-w-[90px] h-[42px]"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="danger"
            size="md"
            loading={deleting}
            disabled={deleting}
            onClick={handleDelete}
            leftIcon={!deleting && <Trash2 size={15} />}
            className="w-full sm:w-auto h-[42px] mf-btn-destructive"
          >
            Delete Project
          </Button>
        </div>
      </div>
    </Modal>
  );
}

