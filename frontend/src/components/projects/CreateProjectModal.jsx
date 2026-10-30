import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Modal from '../common/Modal';
import Input from '../common/Input';
import Button from '../common/Button';
import { createProject } from '../../services/projects';
import { useWorkspace } from '../../context/WorkspaceContext';
import { Box, Tag, AlertCircle } from 'lucide-react';

const FRAMEWORKS = [
  'PyTorch',
  'Scikit-learn',
  'TensorFlow',
  'ONNX',
  'HuggingFace',
  'XGBoost / LightGBM',
  'Custom Python ML',
];

export default function CreateProjectModal({ isOpen, onClose, onCreated }) {
  const navigate = useNavigate();
  const { triggerRefresh } = useWorkspace();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [framework, setFramework] = useState('PyTorch');
  const [version, setVersion] = useState('1.0.0');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!title.trim()) {
      setError('Project name is required');
      return;
    }

    setLoading(true);
    try {
      const created = await createProject({
        title: title.trim(),
        description: description.trim() || null,
        framework,
        version: version.trim() || '1.0.0',
      });

      triggerRefresh();
      onClose();
      if (onCreated) {
        onCreated(created);
      } else {
        navigate(`/dashboard/projects/${created.id}`);
      }
    } catch (err) {
      setError(err.message || 'Failed to create project on backend');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Model Project"
      subtitle="Define model metadata and prepare it for automated CI extraction and containerization."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="mf-form-alert mf-form-alert-error" role="alert">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <Input
          id="create-project-title"
          label="Project / Model Name"
          type="text"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            if (error) setError('');
          }}
          placeholder="e.g. Vision Transformer Inference"
          required
          leftIcon={<Box size={16} />}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="mf-input-group">
            <label className="mf-input-label">Framework</label>
            <div className="relative">
              <select
                className="mf-input-field mf-select"
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
              >
                {FRAMEWORKS.map((fw) => (
                  <option key={fw} value={fw} className="bg-[#080A0D] text-white">
                    {fw}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Input
            label="Version Tag"
            type="text"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="1.0.0"
            leftIcon={<Tag size={16} />}
          />
        </div>

        <div className="mf-input-group">
          <label className="mf-input-label">Description (Optional)</label>
          <textarea
            className="mf-input-field mf-textarea"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Brief overview of model input, task, or performance specifications..."
          />
        </div>

        <div className="flex justify-end gap-3 pt-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={loading}>
            Create Project
          </Button>
        </div>
      </form>
    </Modal>
  );
}
