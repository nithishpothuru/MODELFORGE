import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useWorkspace } from '../../context/WorkspaceContext';
import WorkspaceDropdown from './WorkspaceDropdown';
import NewMenuDropdown from './NewMenuDropdown';
import AccountMenu from './AccountMenu';
import logoFrame240 from '../../assets/sections/logo_frame240.png';
import {
  ChevronDown,
  Search,
  Plus,
  HelpCircle,
  Sparkles,
  Building2,
  Menu,
} from 'lucide-react';

export default function TopNavBar({
  onOpenCreateProject,
  onOpenQuickUnpack,
  onOpenNewWorkspace,
  onToggleMobileSidebar,
}) {
  const { user } = useAuth();
  const {
    currentWorkspace,
    setSearchOpen,
  } = useWorkspace();

  const location = useLocation();

  const [workspaceDropdownOpen, setWorkspaceDropdownOpen] = useState(false);
  const [newMenuOpen, setNewMenuOpen] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);

  // Derive breadcrumb / title from location pathname
  const getBreadcrumb = () => {
    const path = location.pathname;
    if (path.includes('/dashboard/projects/')) {
      return 'Projects / Details';
    }
    if (path.includes('/dashboard/projects')) {
      return 'Projects';
    }
    if (path.includes('/dashboard/teams')) {
      return 'Teams';
    }
    if (path.includes('/dashboard/billing')) {
      return 'Billing';
    }
    if (path.includes('/dashboard/settings')) {
      return 'Workspace Settings';
    }
    return 'Dashboard';
  };

  const displayName = user?.user_metadata?.name || user?.email?.split('@')[0] || 'Developer';
  const initial = displayName.charAt(0).toUpperCase();

  const isMac = typeof window !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.userAgent);

  return (
    <header className="mf-top-nav">
      <div className="top-nav-left">
        {/* Mobile toggle button */}
        <button
          type="button"
          className="mobile-nav-toggle"
          onClick={onToggleMobileSidebar}
          aria-label="Toggle mobile sidebar"
        >
          <Menu size={18} />
        </button>

        {/* 1. ModelForge Brand Logo */}
        <Link to="/dashboard/projects" className="nav-brand-link" title="ModelForge Home">
          <img src={logoFrame240} alt="ModelForge" className="nav-brand-logo-img" />
          <span className="nav-brand-text">
            Model<span className="text-[#00D6FF]">Forge</span>
          </span>
        </Link>

        {/* Thin vertical separator */}
        <div className="nav-separator" />

        {/* 2. Workspace Selector with Dropdown */}
        <div className="relative">
          <button
            type="button"
            className="workspace-selector-btn"
            onClick={() => {
              setWorkspaceDropdownOpen(!workspaceDropdownOpen);
              setNewMenuOpen(false);
              setAccountMenuOpen(false);
            }}
            aria-expanded={workspaceDropdownOpen}
            aria-haspopup="true"
          >
            <div className="workspace-avatar">
              <Building2 size={13} className="text-[#00D6FF]" />
            </div>
            <span className="workspace-label">{currentWorkspace.name}</span>
            <ChevronDown size={14} className="text-white/40 ml-1 chevron-icon" />
          </button>

          <WorkspaceDropdown
            isOpen={workspaceDropdownOpen}
            onClose={() => setWorkspaceDropdownOpen(false)}
            onOpenNewWorkspaceModal={onOpenNewWorkspace}
          />
        </div>

        {/* Thin vertical separator */}
        <div className="nav-separator" />

        {/* 3. Current page title / breadcrumb */}
        <div className="nav-breadcrumb">
          <span className="breadcrumb-current">{getBreadcrumb()}</span>
        </div>
      </div>

      <div className="top-nav-right">
        {/* 4. Search control with keyboard shortcut hint */}
        <button
          type="button"
          className="nav-search-btn"
          onClick={() => setSearchOpen(true)}
          aria-label="Search projects"
        >
          <Search size={14} className="search-icon" />
          <span className="search-placeholder">Search projects...</span>
          <span className="search-kbd">{isMac ? '⌘K' : 'Ctrl K'}</span>
        </button>

        {/* Thin vertical separator */}
        <div className="nav-separator" />

        {/* 5. "+ New" button */}
        <div className="relative">
          <button
            type="button"
            className="btn-nav-new"
            onClick={() => {
              setNewMenuOpen(!newMenuOpen);
              setWorkspaceDropdownOpen(false);
              setAccountMenuOpen(false);
            }}
            aria-expanded={newMenuOpen}
            aria-haspopup="true"
          >
            <Plus size={14} />
            <span>New</span>
          </button>

          <NewMenuDropdown
            isOpen={newMenuOpen}
            onClose={() => setNewMenuOpen(false)}
            onOpenCreateProject={onOpenCreateProject}
            onOpenQuickUnpack={onOpenQuickUnpack}
            onOpenNewWorkspace={onOpenNewWorkspace}
          />
        </div>

        {/* 6. Upgrade button */}
        <Link to="/dashboard/billing" className="btn-nav-upgrade">
          <Sparkles size={13} className="text-[#00D6FF]" />
          <span>Upgrade</span>
        </Link>

        {/* 7. Help icon */}
        <a
          href="http://localhost:8000/api/v1/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="nav-icon-btn"
          title="FastAPI Interactive Documentation"
          aria-label="Help and Documentation"
        >
          <HelpCircle size={16} />
        </a>

        {/* Thin vertical separator */}
        <div className="nav-separator" />

        {/* 8. User avatar / account menu */}
        <div className="relative">
          <button
            type="button"
            className="user-avatar-btn"
            onClick={() => {
              setAccountMenuOpen(!accountMenuOpen);
              setWorkspaceDropdownOpen(false);
              setNewMenuOpen(false);
            }}
            aria-expanded={accountMenuOpen}
            aria-haspopup="true"
            aria-label="User account menu"
          >
            <span className="avatar-letter">{initial}</span>
          </button>

          <AccountMenu
            isOpen={accountMenuOpen}
            onClose={() => setAccountMenuOpen(false)}
          />
        </div>
      </div>
    </header>
  );
}
