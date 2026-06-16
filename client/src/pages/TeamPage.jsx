import React, { useState } from 'react';
import TeamWorkspaceDashboard from '../components/team/TeamWorkspaceDashboard';
import FeedbackInbox from '../components/team/FeedbackInbox';
import { Users, Inbox } from 'lucide-react';

// Access control is handled at the route level via RoleRoute in routes.jsx
export default function TeamPage() {
  const [activeTab, setActiveTab] = useState('members');

  return (
    <div className="w-full h-full pb-8">
      <div className="flex border-b border-border mb-4">
        <button
          onClick={() => setActiveTab('members')}
          className={`flex items-center gap-2 px-6 py-4 font-semibold text-sm transition-colors border-b-2 ${
            activeTab === 'members'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted'
          }`}
        >
          <Users size={16} />
          Team Members & Permissions
        </button>
        <button
          onClick={() => setActiveTab('inbox')}
          className={`flex items-center gap-2 px-6 py-4 font-semibold text-sm transition-colors border-b-2 ${
            activeTab === 'inbox'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted'
          }`}
        >
          <Inbox size={16} />
          Knowledge Gaps Inbox
        </button>
      </div>

      <div className="mt-2">
        {activeTab === 'members' && <TeamWorkspaceDashboard />}
        {activeTab === 'inbox' && <FeedbackInbox />}
      </div>
    </div>
  );
}
