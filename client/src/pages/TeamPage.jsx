import React from 'react';
import TeamWorkspaceDashboard from '../components/team/TeamWorkspaceDashboard';

// Access control is handled at the route level via RoleRoute in routes.jsx
export default function TeamPage() {
  return (
    <div className="w-full h-full pb-8">
      <TeamWorkspaceDashboard />
    </div>
  );
}
