import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import TopNavBar from './TopNavBar';
import Sidebar from './Sidebar';
import SearchModal from './SearchModal';
import ChangelogModal from './ChangelogModal';
import StatusModal from './StatusModal';
import NewWorkspaceModal from '../workspace/NewWorkspaceModal';
import DeployWorkflowModal from '../projects/DeployWorkflowModal';
import UploadModal from '../projects/UploadModal';
import { useWorkspace } from '../../context/WorkspaceContext';

export default function DashboardLayout() {
  const {
    searchOpen,
    setSearchOpen,
    changelogOpen,
    setChangelogOpen,
    statusOpen,
    setStatusOpen,
    newProjectModalOpen,
    setNewProjectModalOpen,
  } = useWorkspace();

  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [newWorkspaceModalOpen, setNewWorkspaceModalOpen] = useState(false);
  const [quickUnpackModalOpen, setQuickUnpackModalOpen] = useState(false);

  return (
    <div className="mf-dashboard-root">
      {/* Fixed-Height Top Navigation */}
      <TopNavBar
        onOpenCreateProject={() => setNewProjectModalOpen(true)}
        onOpenQuickUnpack={() => setQuickUnpackModalOpen(true)}
        onOpenNewWorkspace={() => setNewWorkspaceModalOpen(true)}
        onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)}
      />

      <div className="mf-dashboard-body">
        {/* Persistent Left Sidebar */}
        <Sidebar
          mobileOpen={mobileSidebarOpen}
          onCloseMobile={() => setMobileSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <main className="mf-main-content">
          <Outlet />
        </main>
      </div>

      {/* Global Modals */}
      <SearchModal
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
      />

      <ChangelogModal
        isOpen={changelogOpen}
        onClose={() => setChangelogOpen(false)}
      />

      <StatusModal
        isOpen={statusOpen}
        onClose={() => setStatusOpen(false)}
      />

      <NewWorkspaceModal
        isOpen={newWorkspaceModalOpen}
        onClose={() => setNewWorkspaceModalOpen(false)}
      />

      <DeployWorkflowModal
        isOpen={newProjectModalOpen}
        onClose={() => setNewProjectModalOpen(false)}
      />

      <UploadModal
        isOpen={quickUnpackModalOpen}
        onClose={() => setQuickUnpackModalOpen(false)}
      />
    </div>
  );
}

