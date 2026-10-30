import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Badge from '../common/Badge';
import DeleteProjectModal from './DeleteProjectModal';
import {
  Box,
  MoreVertical,
  Trash2,
  Upload,
  ExternalLink,
  Clock,
  Layers,
  ArrowUpRight,
} from 'lucide-react';

export default function ProjectCard({ project, onOpenUpload, onDeleteSuccess }) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    if (!menuOpen) return;

    const handleClickOutside = (e) => {
      if (!e.target.closest('.card-menu-container')) {
        setMenuOpen(false);
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [menuOpen]);

  const formattedDate = project.created_at
    ? new Date(project.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      })
    : null;

  return (
    <>
      <div
        className="mf-project-card"
        onClick={() => navigate(`/dashboard/projects/${project.id}`)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            navigate(`/dashboard/projects/${project.id}`);
          }
        }}
      >
        <div className="card-top-row">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="project-type-icon">
              <Box size={16} className="text-[#00D6FF]" />
            </div>
            <div className="min-w-0">
              <h3 className="project-card-title truncate" title={project.title}>
                {project.title}
              </h3>
              <span className="project-card-version">v{project.version || '1.0.0'}</span>
            </div>
          </div>

          {/* Status Badge */}
          <div className="flex items-center gap-2 shrink-0">
            <Badge status={project.status} size="xs" />

            {/* More options menu */}
            <div
              className="relative card-menu-container"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                className="card-menu-btn"
                onClick={() => setMenuOpen(!menuOpen)}
                aria-label="Project actions"
                aria-expanded={menuOpen}
                aria-haspopup="true"
              >
                <MoreVertical size={15} />
              </button>

              {menuOpen && (
                <div className="card-dropdown-menu" role="menu">
                  <button
                    type="button"
                    className="dropdown-menu-item"
                    onClick={() => {
                      setMenuOpen(false);
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
                      setMenuOpen(false);
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
                      setMenuOpen(false);
                      setDeleteModalOpen(true);
                    }}
                    role="menuitem"
                  >
                    <Trash2 size={14} className="item-icon text-red-400" />
                    <span>Delete Service</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {project.description && (
          <p className="project-card-description">{project.description}</p>
        )}

        <div className="card-bottom-row">
          <div className="flex items-center gap-3 text-xs text-white/50">
            {project.framework && (
              <span className="flex items-center gap-1 font-mono">
                <Layers size={13} className="text-[#00D6FF]" />
                <span>{project.framework}</span>
              </span>
            )}

            {project.python_version && (
              <span className="font-mono text-white/40">
                py{project.python_version}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs text-white/40">
            {formattedDate && (
              <span className="flex items-center gap-1">
                <Clock size={12} />
                <span>{formattedDate}</span>
              </span>
            )}
            <ArrowUpRight size={14} className="text-white/20 group-hover:text-[#00D6FF] transition-colors" />
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && (
        <DeleteProjectModal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          project={project}
          onSuccess={(deletedId) => {
            setDeleteModalOpen(false);
            if (onDeleteSuccess) {
              onDeleteSuccess(deletedId);
            }
          }}
        />
      )}
    </>
  );
}
