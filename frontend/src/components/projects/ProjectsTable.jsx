import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Badge from '../common/Badge';
import DeleteProjectModal from './DeleteProjectModal';
import {
  Box,
  Layers,
  Clock,
  MoreVertical,
  ExternalLink,
  Upload,
  Trash2,
  Copy,
  Check,
  Container,
} from 'lucide-react';

export default function ProjectsTable({ projects, onOpenUpload, onDeleteSuccess }) {
  const navigate = useNavigate();

  const [activeMenuId, setActiveMenuId] = useState(null);
  const [deleteTargetProject, setDeleteTargetProject] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  // Close active dropdown menu when clicking outside or pressing Escape
  useEffect(() => {
    if (!activeMenuId) return;

    const handleClickOutside = (e) => {
      if (!e.target.closest('.project-menu-container')) {
        setActiveMenuId(null);
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setActiveMenuId(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeMenuId]);

  const handleCopyUrl = (e, url, id) => {
    e.stopPropagation();
    navigator.clipboard.writeText(url).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  if (!projects || projects.length === 0) {
    return null;
  }

  return (
    <div className="mf-projects-table-wrapper">
      <table className="mf-projects-table" aria-label="Projects and Services">
        <thead>
          <tr>
            <th className="th-service">Project / Service</th>
            <th className="th-framework">Framework</th>
            <th className="th-status">Status</th>
            <th className="th-deployment">Deployment Info</th>
            <th className="th-updated">Last Updated</th>
            <th className="th-actions text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {projects.map((project, idx) => {
            const isDeployed =
              project.status === 'deployed' || project.status === 'running';
            const isSuspended =
              project.status === 'suspended' || project.status === 'stopped';

            const deployUrl = project.metadata?.deployment_url || null;

            const formattedDate = project.updated_at || project.created_at
              ? new Date(project.updated_at || project.created_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })
              : 'Recently';

            const menuOpen = activeMenuId === project.id;
            const isNearBottom = idx >= projects.length - 2 && projects.length > 2;

            return (
              <tr
                key={project.id}
                className="mf-table-row"
                onClick={() => navigate(`/dashboard/projects/${project.id}`)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') navigate(`/dashboard/projects/${project.id}`);
                }}
              >
                {/* Project / Service */}
                <td className="td-service">
                  <div className="flex items-center gap-3">
                    <div className="service-icon">
                      <Box size={16} className="text-[#00D6FF]" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="service-title truncate" title={project.title}>
                          {project.title}
                        </span>
                        <span className="service-version font-mono">v{project.version || '1.0.0'}</span>
                      </div>
                      <span className="service-id font-mono">ID: {project.id.slice(0, 8)}...</span>
                    </div>
                  </div>
                </td>

                {/* Framework */}
                <td className="td-framework">
                  <div className="flex items-center gap-1.5 font-mono text-xs text-white/80">
                    <Layers size={13} className="text-[#00D6FF] shrink-0" />
                    <span>{project.framework || 'Custom ML'}</span>
                    {project.python_version && (
                      <span className="text-white/40 text-[11px]">({project.python_version})</span>
                    )}
                  </div>
                </td>

                {/* Status */}
                <td className="td-status">
                  <Badge status={project.status} size="xs" />
                </td>

                {/* Deployment Info */}
                <td className="td-deployment">
                  {isDeployed && deployUrl ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-[#00D6FF] truncate max-w-[200px]" title={deployUrl}>
                        {deployUrl}
                      </span>
                      <button
                        type="button"
                        className="p-1 rounded text-white/50 hover:text-white hover:bg-white/10"
                        onClick={(e) => handleCopyUrl(e, deployUrl, project.id)}
                        title="Copy API URL"
                        aria-label="Copy API URL"
                      >
                        {copiedId === project.id ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                      </button>
                    </div>
                  ) : isDeployed ? (
                    <span className="text-xs text-emerald-400/90 font-mono flex items-center gap-1">
                      <Container size={13} />
                      <span>Running Container</span>
                    </span>
                  ) : isSuspended ? (
                    <span className="text-xs text-white/40 font-mono">Service Inactive</span>
                  ) : project.status === 'validated' ? (
                    <span className="text-xs text-[#00D6FF]/80 font-mono">Validated &bull; Ready</span>
                  ) : project.status === 'uploaded' ? (
                    <span className="text-xs text-white/50 font-mono">Files Extracted</span>
                  ) : (
                    <span className="text-xs text-white/40 font-mono">Package Setup</span>
                  )}
                </td>

                {/* Last Updated */}
                <td className="td-updated">
                  <div className="flex items-center gap-1.5 text-xs text-white/50 font-mono">
                    <Clock size={12} className="text-white/30" />
                    <span>{formattedDate}</span>
                  </div>
                </td>

                {/* Actions Menu */}
                <td className="td-actions text-right" onClick={(e) => e.stopPropagation()}>
                  <div className="relative inline-block text-left project-menu-container">
                    <button
                      type="button"
                      className="card-menu-btn"
                      onClick={() => setActiveMenuId(menuOpen ? null : project.id)}
                      aria-label="Actions"
                      aria-expanded={menuOpen}
                      aria-haspopup="true"
                    >
                      <MoreVertical size={15} />
                    </button>

                    {menuOpen && (
                      <div
                        className={`card-dropdown-menu ${isNearBottom ? 'menu-dropup' : ''}`}
                        role="menu"
                        aria-orientation="vertical"
                      >
                        <button
                          type="button"
                          className="dropdown-menu-item"
                          onClick={() => {
                            setActiveMenuId(null);
                            navigate(`/dashboard/projects/${project.id}`);
                          }}
                          role="menuitem"
                        >
                          <ExternalLink size={14} className="item-icon" />
                          <span>Open Details</span>
                        </button>

                        <button
                          type="button"
                          className="dropdown-menu-item"
                          onClick={() => {
                            setActiveMenuId(null);
                            onOpenUpload(project);
                          }}
                          role="menuitem"
                        >
                          <Upload size={14} className="item-icon text-[#00D6FF]" />
                          <span>Upload Archive</span>
                        </button>

                        <div className="dropdown-divider" />

                        <button
                          type="button"
                          className="dropdown-menu-item item-danger"
                          onClick={() => {
                            setActiveMenuId(null);
                            setDeleteTargetProject(project);
                          }}
                          role="menuitem"
                        >
                          <Trash2 size={14} className="item-icon text-red-400" />
                          <span>Delete Service</span>
                        </button>
                      </div>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Professional Centered Delete Confirmation Dialog */}
      {deleteTargetProject && (
        <DeleteProjectModal
          isOpen={Boolean(deleteTargetProject)}
          onClose={() => setDeleteTargetProject(null)}
          project={deleteTargetProject}
          onSuccess={(deletedId) => {
            setDeleteTargetProject(null);
            if (onDeleteSuccess) {
              onDeleteSuccess(deletedId);
            }
          }}
        />
      )}
    </div>
  );
}
