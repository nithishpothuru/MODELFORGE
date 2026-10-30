import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  FolderGit2,
  Users,
  CreditCard,
  Settings,
  ScrollText,
  Activity,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from 'lucide-react';
import { useWorkspace } from '../../context/WorkspaceContext';

export default function Sidebar({ mobileOpen = false, onCloseMobile = () => {} }) {
  const {
    sidebarCollapsed,
    toggleSidebar,
    setChangelogOpen,
    setStatusOpen,
  } = useWorkspace();

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="mf-sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={`mf-sidebar ${sidebarCollapsed ? 'is-collapsed' : ''} ${
          mobileOpen ? 'is-mobile-open' : ''
        }`}
        aria-label="Sidebar Navigation"
      >
        {/* Mobile close button */}
        {mobileOpen && (
          <div className="mobile-close-row">
            <button
              type="button"
              onClick={onCloseMobile}
              className="text-white/60 hover:text-white p-2"
              aria-label="Close sidebar"
            >
              <X size={18} />
            </button>
          </div>
        )}

        {/* Primary Navigation Items: Projects & Teams ONLY */}
        <div className="sidebar-group primary-nav">
          <NavLink
            to="/dashboard/projects"
            onClick={onCloseMobile}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'is-active' : ''}`
            }
            title={sidebarCollapsed ? 'Projects' : undefined}
          >
            <FolderGit2 size={16} className="nav-icon" />
            <span className="nav-text">Projects</span>
          </NavLink>

          <NavLink
            to="/dashboard/teams"
            onClick={onCloseMobile}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'is-active' : ''}`
            }
            title={sidebarCollapsed ? 'Teams' : undefined}
          >
            <Users size={16} className="nav-icon" />
            <span className="nav-text">Teams</span>
          </NavLink>
        </div>

        {/* Section Label: WORKSPACE */}
        <div className="sidebar-section-divider">
          {!sidebarCollapsed && <span className="section-label">WORKSPACE</span>}
        </div>

        {/* Under WORKSPACE: Billing & Settings */}
        <div className="sidebar-group workspace-nav">
          <NavLink
            to="/dashboard/billing"
            onClick={onCloseMobile}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'is-active' : ''}`
            }
            title={sidebarCollapsed ? 'Billing' : undefined}
          >
            <CreditCard size={16} className="nav-icon" />
            <span className="nav-text">Billing</span>
          </NavLink>

          <NavLink
            to="/dashboard/settings"
            onClick={onCloseMobile}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'is-active' : ''}`
            }
            title={sidebarCollapsed ? 'Settings' : undefined}
          >
            <Settings size={16} className="nav-icon" />
            <span className="nav-text">Settings</span>
          </NavLink>
        </div>

        {/* Spacer */}
        <div className="sidebar-spacer" />

        {/* Bottom items: Changelog, Status, Collapse */}
        <div className="sidebar-group bottom-nav">
          <button
            type="button"
            className="sidebar-link btn-bottom"
            onClick={() => {
              setChangelogOpen(true);
              onCloseMobile();
            }}
            title={sidebarCollapsed ? 'Changelog' : undefined}
          >
            <ScrollText size={16} className="nav-icon" />
            <span className="nav-text">Changelog</span>
          </button>

          <button
            type="button"
            className="sidebar-link btn-bottom"
            onClick={() => {
              setStatusOpen(true);
              onCloseMobile();
            }}
            title={sidebarCollapsed ? 'Status' : undefined}
          >
            <Activity size={16} className="nav-icon" />
            <span className="nav-text">Status</span>
          </button>

          <button
            type="button"
            className="sidebar-link btn-bottom btn-collapse"
            onClick={toggleSidebar}
            title={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            aria-label={sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {sidebarCollapsed ? (
              <PanelLeftOpen size={16} className="nav-icon" />
            ) : (
              <PanelLeftClose size={16} className="nav-icon" />
            )}
            <span className="nav-text">Collapse</span>
          </button>
        </div>
      </aside>
    </>
  );
}

