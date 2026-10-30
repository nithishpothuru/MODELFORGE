import React, { useState } from 'react';
import Modal from '../common/Modal';
import Input from '../common/Input';
import Button from '../common/Button';
import { useWorkspace } from '../../context/WorkspaceContext';
import { Building2, Info } from 'lucide-react';

export default function NewWorkspaceModal({ isOpen, onClose }) {
  const { createWorkspace, setCurrentWorkspace } = useWorkspace();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) {
      setError('Workspace name is required');
      return;
    }

    setLoading(true);
    try {
      const newWs = createWorkspace(name);
      setCurrentWorkspace(newWs);
      setName('');
      setDescription('');
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to create workspace');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Workspace"
      subtitle="Organize team members, ML models, and container deployments."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="bg-white/[0.02] border border-white/10 rounded-lg p-3 flex gap-2.5 items-start text-xs text-white/60">
          <Info size={16} className="text-[#00D6FF] shrink-0 mt-0.5" />
          <span>
            Workspace creation creates an isolated space for models. Note: backend multi-tenant API is pending; this workspace will be available in your current session.
          </span>
        </div>

        <Input
          id="workspace-name"
          label="Workspace Name"
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (error) setError('');
          }}
          placeholder="e.g. Acme Robotics ML"
          required
          leftIcon={<Building2 size={16} />}
          error={error}
        />

        <div className="mf-input-group">
          <label htmlFor="workspace-description" className="mf-input-label">Description (Optional)</label>
          <div className="mf-input-wrapper">
            <textarea
              id="workspace-description"
              className="mf-input-field mf-textarea"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this workspace's machine learning purpose..."
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={loading}>
            Create Workspace
          </Button>
        </div>
      </form>
    </Modal>
  );
}

