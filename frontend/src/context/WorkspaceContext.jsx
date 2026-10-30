import React, { createContext, useContext, useState, useEffect } from 'react';

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [currentWorkspace, setCurrentWorkspace] = useState({
    id: 'ws_default',
    name: 'My Workspace',
    role: 'Owner',
    tier: 'Developer',
  });

  const [workspaces, setWorkspaces] = useState([
    {
      id: 'ws_default',
      name: 'My Workspace',
      role: 'Owner',
      isCurrent: true,
    },
  ]);

  const [searchOpen, setSearchOpen] = useState(false);
  const [changelogOpen, setChangelogOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [newProjectModalOpen, setNewProjectModalOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem('modelforge_sidebar_collapsed') === 'true';
  });

  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const triggerRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const toggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('modelforge_sidebar_collapsed', String(next));
      return next;
    });
  };

  // Global keyboard shortcut for search (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const createWorkspace = (name) => {
    const newWs = {
      id: 'ws_' + Math.random().toString(36).substring(2, 9),
      name: name.trim(),
      role: 'Owner',
      isCurrent: false,
    };
    setWorkspaces((prev) => [...prev, newWs]);
    return newWs;
  };

  const value = {
    currentWorkspace,
    setCurrentWorkspace,
    workspaces,
    createWorkspace,
    searchOpen,
    setSearchOpen,
    changelogOpen,
    setChangelogOpen,
    statusOpen,
    setStatusOpen,
    newProjectModalOpen,
    setNewProjectModalOpen,
    sidebarCollapsed,
    toggleSidebar,
    refreshTrigger,
    triggerRefresh,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}

