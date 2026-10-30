import React, { useState } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import {
  Building2,
  Save,
  CheckCircle2,
  AlertTriangle,
  Sliders,
  Trash2,
} from 'lucide-react';

export default function WorkspaceSettings() {
  const { currentWorkspace, setCurrentWorkspace } = useWorkspace();

  const [name, setName] = useState(currentWorkspace.name || 'My Workspace');
  const [slug, setSlug] = useState('my-workspace');
  const [defaultPython, setDefaultPython] = useState('3.11');
  const [ciTimeout, setCiTimeout] = useState('180');
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSave = (e) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) {
      setError('Workspace name cannot be empty');
      return;
    }

    // Update in workspace context
    setCurrentWorkspace({
      ...currentWorkspace,
      name: name.trim(),
    });

    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
    }, 4000);
  };

  const handleReset = () => {
    setName(currentWorkspace.name || 'My Workspace');
    setSlug('my-workspace');
    setDefaultPython('3.11');
    setCiTimeout('180');
    setError('');
  };

  return (
    <div className="mf-workspace-settings-page space-y-6 max-w-4xl">
      {/* 1. Header */}
      <div className="mf-page-header">
        <div className="mf-header-text-group">
          <h1 className="mf-page-title">Workspace Settings</h1>
          <p className="mf-page-subtitle">
            Configure workspace profile, default Python build runtimes, and CI pipeline timeouts.
          </p>
        </div>

        <div className="mf-header-actions">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleReset}
          >
            Reset
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={handleSave}
            leftIcon={<Save size={14} />}
          >
            Save Changes
          </Button>
        </div>
      </div>

      {/* 2. Standardized Notice Banner */}
      <div className="mf-notice-banner" role="region" aria-label="Workspace notice">
        <div className="notice-icon-box">
          <Building2 size={16} className="text-[#00D6FF]" />
        </div>
        <div className="notice-content">
          <h4 className="notice-heading">Workspace Scope Notice</h4>
          <p className="notice-description">
            Settings modified here apply to the active workspace ({currentWorkspace.name}). Personal user settings (such as password and profile) are managed under Account Settings.
          </p>
        </div>
      </div>

      {savedSuccess && (
        <div className="mf-form-alert mf-form-alert-success" role="alert">
          <CheckCircle2 size={16} className="shrink-0 text-emerald-400" />
          <span>Workspace preferences updated successfully.</span>
        </div>
      )}

      {error && (
        <div className="mf-form-alert mf-form-alert-error" role="alert">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 3. Form Sections */}
      <form onSubmit={handleSave} className="space-y-6">
        {/* Section A: General Information */}
        <div className="mf-settings-card">
          <h2 className="settings-card-title">
            <Building2 size={16} className="text-[#00D6FF]" />
            <span>General Information</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Workspace Name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <Input
              label="Workspace Slug / Identifier"
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              hint="Used in CLI endpoints and share links"
            />
          </div>
        </div>

        {/* Section B: Runtime Preferences */}
        <div className="mf-settings-card">
          <h2 className="settings-card-title">
            <Sliders size={16} className="text-[#00D6FF]" />
            <span>CI Runtime Defaults</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="mf-input-group">
              <label className="mf-input-label">Default Python Version</label>
              <select
                className="mf-input-field mf-select font-mono"
                value={defaultPython}
                onChange={(e) => setDefaultPython(e.target.value)}
              >
                <option value="3.11" className="bg-[#080A0D]">Python 3.11 (Recommended)</option>
                <option value="3.10" className="bg-[#080A0D]">Python 3.10</option>
                <option value="3.12" className="bg-[#080A0D]">Python 3.12</option>
                <option value="3.9" className="bg-[#080A0D]">Python 3.9</option>
              </select>
            </div>

            <Input
              label="CI Validation Timeout (Seconds)"
              type="number"
              value={ciTimeout}
              onChange={(e) => setCiTimeout(e.target.value)}
              min="30"
              max="600"
              hint="Maximum time allowed for dependency resolution"
            />
          </div>
        </div>

        {/* Section C: Danger Zone */}
        <div className="mf-settings-card is-danger">
          <h2 className="settings-card-title text-red-400">
            <Trash2 size={16} />
            <span>Danger Zone</span>
          </h2>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-white">Delete Workspace</p>
              <p className="text-xs text-white/50 mt-0.5">
                Permanently delete this workspace and all associated machine learning projects.
              </p>
            </div>

            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={() => alert('The default workspace cannot be deleted.')}
            >
              Delete Workspace
            </Button>
          </div>
        </div>

        {/* Bottom Action Row */}
        <div className="flex justify-end gap-3 pt-3 border-t border-white/5">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleReset}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            leftIcon={<Save size={14} />}
          >
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  );
}
