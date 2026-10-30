import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Box, CornerDownLeft, X } from 'lucide-react';
import { listProjects } from '../../services/projects';
import Badge from '../common/Badge';

export default function SearchModal({ isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const navigate = useNavigate();
  const inputRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setSelectedIndex(0);
      return;
    }

    setLoading(true);
    listProjects()
      .then((data) => {
        setProjects(data || []);
      })
      .catch((err) => {
        console.warn('Failed to load projects for search:', err);
      })
      .finally(() => {
        setLoading(false);
      });

    setTimeout(() => {
      inputRef.current?.focus();
    }, 50);
  }, [isOpen]);

  const filteredProjects = projects.filter((p) => {
    const q = query.toLowerCase().trim();
    if (!q) return true;
    return (
      (p.title && p.title.toLowerCase().includes(q)) ||
      (p.framework && p.framework.toLowerCase().includes(q)) ||
      (p.description && p.description.toLowerCase().includes(q)) ||
      (p.id && p.id.toLowerCase().includes(q))
    );
  });

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredProjects.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredProjects.length) % Math.max(1, filteredProjects.length));
    } else if (e.key === 'Enter') {
      if (filteredProjects[selectedIndex]) {
        e.preventDefault();
        onClose();
        navigate(`/dashboard/projects/${filteredProjects[selectedIndex].id}`);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="mf-search-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div className="mf-search-container">
        {/* Input row */}
        <div className="mf-search-input-row">
          <Search size={18} className="text-[#00D6FF] shrink-0" />
          <input
            ref={inputRef}
            type="text"
            className="mf-search-input"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search projects by name, framework, or model ID..."
            aria-label="Search projects"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="text-white/40 hover:text-white"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Results list */}
        <div className="mf-search-results">
          {loading ? (
            <div className="py-8 text-center text-xs text-white/50">
              Loading projects from backend...
            </div>
          ) : filteredProjects.length === 0 ? (
            <div className="py-8 text-center text-xs text-white/40">
              {query ? `No projects matching "${query}"` : 'No projects found in this workspace'}
            </div>
          ) : (
            filteredProjects.map((project, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={project.id}
                  className={`search-result-item ${isSelected ? 'is-selected' : ''}`}
                  onClick={() => {
                    onClose();
                    navigate(`/dashboard/projects/${project.id}`);
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <div className="result-icon">
                    <Box size={16} className="text-[#00D6FF]" />
                  </div>
                  <div className="result-info">
                    <div className="flex items-center gap-2">
                      <span className="result-title">{project.title}</span>
                      <Badge status={project.status} size="xs" />
                    </div>
                    <span className="result-meta">
                      {project.framework || 'Custom ML'} &bull; v{project.version || '1.0.0'} &bull; ID: {project.id.slice(0, 8)}...
                    </span>
                  </div>
                  <div className="result-action">
                    <CornerDownLeft size={14} className="text-white/40" />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="mf-search-footer">
          <div className="flex items-center gap-2">
            <span className="kbd">↑</span>
            <span className="kbd">↓</span>
            <span>to navigate</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="kbd">↵</span>
            <span>to open</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="kbd">ESC</span>
            <span>to close</span>
          </div>
        </div>
      </div>
    </div>
  );
}
