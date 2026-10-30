import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import Input from '../components/common/Input';
import {
  Users,
  UserPlus,
  Shield,
  Plus,
  Info,
  Calendar,
  UserCheck,
  Mail,
  Copy,
  Check,
} from 'lucide-react';

export default function Teams() {
  const { user } = useAuth();

  const [createTeamModalOpen, setCreateTeamModalOpen] = useState(false);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [newTeamName, setNewTeamName] = useState('');
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('Member');
  const [notice, setNotice] = useState('');
  const [copiedEmail, setCopiedEmail] = useState(false);

  // Initial team state representing the current authenticated developer in the workspace
  const [teams, setTeams] = useState([
    {
      id: 'team_core',
      name: 'Core ML Engineering',
      description: 'Primary model research and deployment group',
      membersCount: 1,
      createdAt: '2025-01-15',
    },
  ]);

  const members = [
    {
      id: 'mem_1',
      name: user?.user_metadata?.name || 'Workspace Lead',
      email: user?.email || 'developer@modelforge.dev',
      role: 'Owner',
      status: 'active',
      joinedAt: 'Today',
    },
  ];

  const handleCreateTeam = (e) => {
    e.preventDefault();
    if (!newTeamName.trim()) return;

    const newTeam = {
      id: 'team_' + Math.random().toString(36).substring(2, 9),
      name: newTeamName.trim(),
      description: 'Collaborative ML project team',
      membersCount: 1,
      createdAt: new Date().toISOString().split('T')[0],
    };

    setTeams([...teams, newTeam]);
    setNewTeamName('');
    setCreateTeamModalOpen(false);
    setNotice(
      `Team "${newTeam.name}" created in local workspace session. Backend persistence is pending teams schema migration.`
    );
  };

  const handleInvite = (e) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;

    setInviteModalOpen(false);
    setNotice(
      `Invitation to ${inviteEmail} (${inviteRole}) queued. Backend email dispatch service is in preview mode.`
    );
    setInviteEmail('');
  };

  const handleCopyEmail = (email) => {
    navigator.clipboard.writeText(email).then(() => {
      setCopiedEmail(true);
      setTimeout(() => setCopiedEmail(false), 2000);
    });
  };

  return (
    <div className="mf-teams-page space-y-6">
      {/* 1. Page Header */}
      <div className="mf-page-header">
        <div className="mf-header-text-group">
          <h1 className="mf-page-title">Teams</h1>
          <p className="mf-page-subtitle">
            Manage organization teams, invite ML engineers, and configure workspace role permissions.
          </p>
        </div>

        <div className="mf-header-actions">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setInviteModalOpen(true)}
            leftIcon={<UserPlus size={14} className="text-[#00D6FF]" />}
          >
            Invite Member
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => setCreateTeamModalOpen(true)}
            leftIcon={<Plus size={14} />}
          >
            Create Team
          </Button>
        </div>
      </div>

      {/* 2. Standardized Information Banner */}
      <div className="mf-notice-banner" role="region" aria-label="System notice">
        <div className="notice-icon-box">
          <Info size={16} className="text-[#00D6FF]" />
        </div>
        <div className="notice-content">
          <h4 className="notice-heading">Workspace & Team Integration Notice</h4>
          <p className="notice-description">
            The ModelForge API currently operates with single-workspace project schemas. Multi-tenant team roles and SMTP invitations are active in this workspace view and will automatically sync once team persistence is migrated on the backend database.
          </p>
        </div>
      </div>

      {notice && (
        <div className="mf-form-alert mf-form-alert-success justify-between" role="status">
          <span>{notice}</span>
          <button
            type="button"
            className="text-white/60 hover:text-white p-1"
            onClick={() => setNotice('')}
            aria-label="Dismiss notice"
          >
            ✕
          </button>
        </div>
      )}

      {/* 3. Team Section */}
      <section className="space-y-3">
        <div className="mf-section-header">
          <h2 className="mf-section-title">Teams</h2>
          <span className="mf-section-badge font-mono">
            {teams.length} {teams.length === 1 ? 'team' : 'teams'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {teams.map((team) => (
            <div key={team.id} className="mf-team-card">
              <div className="team-card-header">
                <div className="team-icon-box">
                  <Users size={18} className="text-[#00D6FF]" />
                </div>
                <div className="team-info min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="team-name truncate" title={team.name}>{team.name}</h3>
                    <span className="team-badge font-mono">team</span>
                  </div>
                  <p className="team-desc">{team.description}</p>
                </div>
              </div>

              <div className="team-card-footer">
                <div className="flex items-center gap-1.5 text-white/60">
                  <UserCheck size={13} className="text-[#00D6FF]" />
                  <span>{team.membersCount} {team.membersCount === 1 ? 'member' : 'members'}</span>
                </div>
                <div className="flex items-center gap-1.5 text-white/40 font-mono text-[11px]">
                  <Calendar size={13} />
                  <span>Created {team.createdAt}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Members Section: Distinct Columns Table */}
      <section className="space-y-3">
        <div className="mf-section-header">
          <h2 className="mf-section-title">Workspace Members</h2>
          <span className="mf-section-badge font-mono">
            {members.length} {members.length === 1 ? 'member' : 'members'}
          </span>
        </div>

        <div className="mf-table-wrapper">
          <table className="mf-table" aria-label="Workspace Members">
            <thead>
              <tr>
                <th style={{ minWidth: 180 }}>Member</th>
                <th style={{ minWidth: 220 }}>Email</th>
                <th style={{ minWidth: 120 }}>Role</th>
                <th style={{ minWidth: 110 }}>Status</th>
                <th style={{ minWidth: 120 }} className="text-right">Joined</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr key={member.id}>
                  {/* Column 1: Member Name & Avatar */}
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full bg-[#00D6FF]/20 text-[#00D6FF] flex items-center justify-center font-bold text-xs shrink-0">
                        {member.name.charAt(0).toUpperCase()}
                      </div>
                      <span className="font-medium text-white truncate max-w-[160px]" title={member.name}>
                        {member.name}
                      </span>
                    </div>
                  </td>

                  {/* Column 2: Distinct Email Address */}
                  <td>
                    <div className="flex items-center gap-1.5 font-mono text-xs text-white/70">
                      <Mail size={13} className="text-white/40 shrink-0" />
                      <span className="truncate max-w-[200px]" title={member.email}>
                        {member.email}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCopyEmail(member.email)}
                        className="p-1 rounded text-white/40 hover:text-white hover:bg-white/10"
                        title="Copy email address"
                        aria-label="Copy email address"
                      >
                        {copiedEmail ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                      </button>
                    </div>
                  </td>

                  {/* Column 3: Distinct Role */}
                  <td>
                    <span className="inline-flex items-center gap-1.5 text-xs text-[#00D6FF] font-medium">
                      <Shield size={13} className="shrink-0" />
                      <span>{member.role}</span>
                    </span>
                  </td>

                  {/* Column 4: Distinct Status Badge */}
                  <td>
                    <Badge status="passed" size="xs">Active</Badge>
                  </td>

                  {/* Column 5: Joined Date */}
                  <td className="text-right text-white/50 font-mono text-xs">
                    {member.joinedAt}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Create Team Modal */}
      <Modal
        isOpen={createTeamModalOpen}
        onClose={() => setCreateTeamModalOpen(false)}
        title="Create Team"
        subtitle="Group developers, data scientists and deployments."
      >
        <form onSubmit={handleCreateTeam} className="space-y-4">
          <Input
            label="Team Name"
            value={newTeamName}
            onChange={(e) => setNewTeamName(e.target.value)}
            placeholder="e.g. Computer Vision Research"
            required
            autoFocus
          />

          <div className="flex justify-end gap-3 pt-3 border-t border-white/5">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setCreateTeamModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Create Team
            </Button>
          </div>
        </form>
      </Modal>

      {/* Invite Member Modal */}
      <Modal
        isOpen={inviteModalOpen}
        onClose={() => setInviteModalOpen(false)}
        title="Invite Member to Workspace"
      >
        <form onSubmit={handleInvite} className="space-y-4">
          <Input
            label="Email Address"
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="engineer@modelforge.dev"
            required
            autoFocus
          />

          <div className="mf-input-group">
            <label className="mf-input-label">Role</label>
            <select
              className="mf-input-field mf-select"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
            >
              <option value="Admin" className="bg-[#080A0D]">Admin</option>
              <option value="Member" className="bg-[#080A0D]">Member</option>
              <option value="Viewer" className="bg-[#080A0D]">Viewer</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-white/5">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setInviteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary">
              Queue Invite
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
