import React, { useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useWorkspace } from '../../context/WorkspaceContext';
import { LogOut, Settings, ExternalLink, Shield } from 'lucide-react';

export default function AccountMenu({ isOpen, onClose }) {
  const menuRef = useRef(null);
  const { user, logout } = useAuth();
  const { currentWorkspace } = useWorkspace();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
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

  const handleSignOut = async () => {
    onClose();
    await logout();
    navigate('/login', { replace: true });
  };

  const displayName = user?.user_metadata?.name || user?.email?.split('@')[0] || 'Developer';
  const email = user?.email || 'developer@modelforge.dev';

  return (
    <div ref={menuRef} className="mf-account-dropdown" role="menu">
      {/* Profile Header */}
      <div className="account-header">
        <div className="avatar-circle">
          {displayName.charAt(0).toUpperCase()}
        </div>
        <div className="account-details">
          <p className="account-name">{displayName}</p>
          <p className="account-email">{email}</p>
          <div className="account-badge">
            <Shield size={11} className="text-[#00D6FF]" />
            <span>{currentWorkspace.name} &bull; Owner</span>
          </div>
        </div>
      </div>

      <div className="dropdown-divider" />

      {/* Workspace Settings */}
      <Link
        to="/dashboard/settings"
        className="dropdown-menu-item"
        onClick={onClose}
        role="menuitem"
      >
        <Settings size={15} className="item-icon" />
        <span>Workspace Settings</span>
      </Link>

      {/* Docs */}
      <a
        href="http://localhost:8000/api/v1/docs"
        target="_blank"
        rel="noopener noreferrer"
        className="dropdown-menu-item"
        onClick={onClose}
        role="menuitem"
      >
        <ExternalLink size={15} className="item-icon" />
        <span>FastAPI Docs</span>
      </a>

      <div className="dropdown-divider" />

      {/* Sign Out */}
      <button
        type="button"
        className="dropdown-menu-item item-danger"
        onClick={handleSignOut}
        role="menuitem"
      >
        <LogOut size={15} className="item-icon text-red-400" />
        <span>Sign Out</span>
      </button>
    </div>
  );
}
