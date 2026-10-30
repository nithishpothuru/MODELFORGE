import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Check, CreditCard, Settings, Plus, Building2 } from 'lucide-react';
import { useWorkspace } from '../../context/WorkspaceContext';

export default function WorkspaceDropdown({ isOpen, onClose, onOpenNewWorkspaceModal }) {
  const dropdownRef = useRef(null);
  const { currentWorkspace, workspaces, setCurrentWorkspace } = useWorkspace();

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onClose();
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div ref={dropdownRef} className="mf-workspace-dropdown" role="menu" aria-label="Workspaces">
      {/* Current Workspace Identity */}
      <div className="dropdown-section-header">Workspaces</div>
      
      <div className="workspaces-list">
        {workspaces.map((ws) => {
          const isSelected = ws.id === currentWorkspace.id;
          return (
            <button
              key={ws.id}
              type="button"
              className={`workspace-item ${isSelected ? 'is-selected' : ''}`}
              onClick={() => {
                setCurrentWorkspace(ws);
                onClose();
              }}
              role="menuitem"
            >
              <div className="workspace-icon">
                <Building2 size={14} className="text-[#00D6FF]" />
              </div>
              <div className="workspace-info">
                <span className="workspace-name">{ws.name}</span>
                <span className="workspace-role">{ws.role || 'Personal'}</span>
              </div>
              {isSelected && <Check size={14} className="text-[#00D6FF] ml-auto shrink-0" />}
            </button>
          );
        })}
      </div>

      <div className="dropdown-divider" />

      {/* 2. Billing */}
      <Link
        to="/dashboard/billing"
        className="dropdown-menu-item"
        onClick={onClose}
        role="menuitem"
      >
        <CreditCard size={15} className="item-icon" />
        <span>Billing</span>
      </Link>

      {/* 3. Workspace Settings */}
      <Link
        to="/dashboard/settings"
        className="dropdown-menu-item"
        onClick={onClose}
        role="menuitem"
      >
        <Settings size={15} className="item-icon" />
        <span>Workspace Settings</span>
      </Link>

      {/* 4. Divider */}
      <div className="dropdown-divider" />

      {/* 5. + New Workspace */}
      <button
        type="button"
        className="dropdown-menu-item item-create"
        onClick={() => {
          onClose();
          onOpenNewWorkspaceModal();
        }}
        role="menuitem"
      >
        <Plus size={15} className="item-icon text-[#00D6FF]" />
        <span>New Workspace</span>
      </button>
    </div>
  );
}
