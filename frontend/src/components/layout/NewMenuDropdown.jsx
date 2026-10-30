import React, { useEffect, useRef } from 'react';
import { Box, UploadCloud, Building2 } from 'lucide-react';

export default function NewMenuDropdown({
  isOpen,
  onClose,
  onOpenCreateProject,
  onOpenQuickUnpack,
  onOpenNewWorkspace,
}) {
  const dropdownRef = useRef(null);

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
    <div ref={dropdownRef} className="mf-new-dropdown" role="menu">
      <button
        type="button"
        className="dropdown-menu-item"
        onClick={() => {
          onClose();
          onOpenCreateProject();
        }}
        role="menuitem"
      >
        <Box size={16} className="item-icon text-[#00D6FF]" />
        <div>
          <span className="font-medium">New Project</span>
          <p className="text-[11px] text-white/50">Register model metadata and start deployment</p>
        </div>
      </button>

      <button
        type="button"
        className="dropdown-menu-item"
        onClick={() => {
          onClose();
          onOpenQuickUnpack();
        }}
        role="menuitem"
      >
        <UploadCloud size={16} className="item-icon text-[#00AFFF]" />
        <div>
          <span className="font-medium">Quick Unpack Model</span>
          <p className="text-[11px] text-white/50">Upload ZIP archive directly into a new project</p>
        </div>
      </button>

      <div className="dropdown-divider" />

      <button
        type="button"
        className="dropdown-menu-item"
        onClick={() => {
          onClose();
          onOpenNewWorkspace();
        }}
        role="menuitem"
      >
        <Building2 size={16} className="item-icon text-white/60" />
        <div>
          <span className="font-medium">New Workspace</span>
          <p className="text-[11px] text-white/50">Create an isolated organization workspace</p>
        </div>
      </button>
    </div>
  );
}

