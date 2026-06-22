import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldAlert, Users, Database, Globe, Bot, ShieldCheck, Activity, Briefcase, Lock, X, Calendar as CalendarIcon, LogOut } from 'lucide-react';
import AdminCalendar from './components/AdminCalendar';
import { toast } from 'sonner';

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function LoadingSkeleton({ className }) {
  return <div className={`animate-pulse bg-muted rounded-md ${className}`}></div>;
}

async function fetchAdminStats(user) {
  const res = await fetch(`${API_URL}/admin/stats?user_id=${user.id}`);
  if (!res.ok) throw new Error("Failed to load admin stats");
  return res.json();
}

async function fetchAdminUsers(user) {
  const res = await fetch(`${API_URL}/admin/users?user_id=${user.id}`);
  if (!res.ok) throw new Error("Failed to load admin users");
  return res.json();
}

async function fetchAdminWorkspaces(user) {
  const res = await fetch(`${API_URL}/admin/workspaces?user_id=${user.id}`);
  if (!res.ok) throw new Error("Failed to load admin workspaces");
  return res.json();
}

async function fetchAdminDemoRequests(user) {
  const res = await fetch(`${API_URL}/admin/demo-requests?user_id=${user.id}`);
  if (!res.ok) throw new Error("Failed to load admin demo requests");
  return res.json();
}

async function fetchScheduledDemoRequests(user) {
  const res = await fetch(`${API_URL}/admin/demo-requests/scheduled?user_id=${user.id}`);
  if (!res.ok) throw new Error("Failed to load scheduled demo requests");
  return res.json();
}

export default function App() {
  const queryClient = useQueryClient();
  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem('adminUser');
    return saved ? JSON.parse(saved) : null;
  });

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem('adminUser');
    localStorage.removeItem('adminToken');
  };

  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['adminStats'],
    queryFn: () => fetchAdminStats(currentUser),
    enabled: !!currentUser,
  });

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['adminUsers'],
    queryFn: () => fetchAdminUsers(currentUser),
    enabled: !!currentUser,
  });

  const { data: workspacesData, isLoading: workspacesLoading } = useQuery({
    queryKey: ['adminWorkspaces'],
    queryFn: () => fetchAdminWorkspaces(currentUser),
    enabled: !!currentUser,
  });

  const { data: demoRequestsData, isLoading: demoRequestsLoading } = useQuery({
    queryKey: ['adminDemoRequests'],
    queryFn: () => fetchAdminDemoRequests(currentUser),
    enabled: !!currentUser,
  });

  const [activeTab, setActiveTab] = useState('users');

  const { data: scheduledData, isLoading: scheduledLoading } = useQuery({
    queryKey: ['adminScheduledRequests'],
    queryFn: () => fetchScheduledDemoRequests(currentUser),
    enabled: !!currentUser && activeTab === 'calendar', // optimization
  });
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [actionPassword, setActionPassword] = useState("");
  const [pendingAction, setPendingAction] = useState(null);

  const executePendingAction = (e) => {
    e.preventDefault();
    if (pendingAction && actionPassword) {
      pendingAction(actionPassword);
      setPasswordModalOpen(false);
      setActionPassword("");
      setPendingAction(null);
    }
  };

  const requirePassword = (actionFn) => {
    setPendingAction(() => actionFn);
    setPasswordModalOpen(true);
  };

  const updateSubMutation = useMutation({
    mutationFn: async ({ targetUserId, newPlan, password }) => {
      const res = await fetch(`${API_URL}/admin/users/${targetUserId}/subscription`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan_tier: newPlan, admin_user_id: currentUser.id, admin_action_password: password })
      });
      if (!res.ok) throw new Error("Failed to update subscription");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Subscription updated successfully!");
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
    },
    onError: (err) => toast.error(err.message)
  });

  const updateSuperAdminMutation = useMutation({
    mutationFn: async ({ targetUserId, isSuperAdmin, password }) => {
      const res = await fetch(`${API_URL}/admin/users/${targetUserId}/super_admin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_super_admin: isSuperAdmin, admin_user_id: currentUser.id, admin_action_password: password })
      });
      if (!res.ok) throw new Error("Failed to update super admin status");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Super Admin status updated!");
      queryClient.invalidateQueries({ queryKey: ['adminUsers'] });
    },
    onError: (err) => toast.error(err.message)
  });

  const updateDemoStatusMutation = useMutation({
    mutationFn: async ({ requestId, newStatus, password }) => {
      const res = await fetch(`${API_URL}/admin/demo-requests/${requestId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus, admin_user_id: currentUser.id, admin_action_password: password })
      });
      if (!res.ok) throw new Error("Failed to update status");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Demo request status updated!");
      queryClient.invalidateQueries({ queryKey: ['adminDemoRequests'] });
    },
    onError: (err) => toast.error(err.message)
  });

  const scheduleMeetingMutation = useMutation({
    mutationFn: async ({ requestId, date, time, meeting_link, password }) => {
      const res = await fetch(`${API_URL}/admin/demo-requests/${requestId}/schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date, time, meeting_link, admin_user_id: currentUser.id, admin_action_password: password })
      });
      if (!res.ok) throw new Error("Failed to schedule meeting");
      return res.json();
    },
    onSuccess: (data) => {
      toast.success("Meeting scheduled and email sent!");
      queryClient.invalidateQueries({ queryKey: ['adminDemoRequests'] });
      queryClient.invalidateQueries({ queryKey: ['adminScheduledRequests'] });
    },
    onError: (err) => toast.error(err.message)
  });

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoggingIn(true);
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }
      
      if (data.requires_otp || data.requires_2fa) {
        toast.error("Please verify your account via the main app before accessing the admin portal.");
      } else {
        toast.success("Logged in successfully!");
        setCurrentUser(data.user);
        localStorage.setItem('adminUser', JSON.stringify(data.user));
        localStorage.setItem('adminToken', data.access_token);
      }
    } catch (err) {
      toast.error(err.message);
    }
    setIsLoggingIn(false);
  };

  if (!currentUser) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background p-4">
        <div className="border border-border/50 rounded-xl p-8 max-w-md w-full bg-card shadow-2xl">
          <div className="flex justify-center mb-6">
            <ShieldCheck className="text-primary w-12 h-12" />
          </div>
          <h2 className="text-2xl font-bold text-center mb-2">Admin Portal</h2>
          <p className="text-muted-foreground text-center mb-8 text-sm">Please sign in with your Super Admin credentials</p>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full bg-muted border border-border rounded-lg px-4 py-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full bg-muted border border-border rounded-lg px-4 py-2"
              />
            </div>
            <button
              type="submit"
              disabled={isLoggingIn}
              className="w-full bg-primary text-primary-foreground font-bold py-2 rounded-lg mt-4 disabled:opacity-50"
            >
              {isLoggingIn ? "Signing In..." : "Sign In"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (statsError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen space-y-4 bg-background">
        <ShieldAlert size={48} className="text-red-500" />
        <h2 className="text-2xl font-bold text-foreground">Access Denied</h2>
        <p className="text-muted-foreground">You do not have Super Admin privileges.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-7xl mx-auto space-y-8 pb-10">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <ShieldCheck className="text-primary w-8 h-8" />
            Super Admin Portal
          </h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{currentUser.email}</span>
            <button onClick={handleLogout} className="flex items-center gap-1.5 px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-lg text-sm font-medium transition">
              <LogOut size={16} /> Logout
            </button>
          </div>
        </div>
        <p className="text-muted-foreground mt-2">Manage the entire platform across all users and workspaces.</p>
        </div>

        {/* Global Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard title="Total Users" value={stats?.totalUsers} icon={Users} loading={statsLoading} />
          <StatCard title="Workspaces" value={stats?.totalWorkspaces} icon={Activity} loading={statsLoading} />
          <StatCard title="Total Agents" value={stats?.totalAgents} icon={Bot} loading={statsLoading} />
          <StatCard title="Chatbots" value={stats?.totalChatbots} icon={Globe} loading={statsLoading} />
          <StatCard title="DB Storage" value={stats ? `${stats.totalStorageMB} MB` : null} icon={Database} loading={statsLoading} />
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border/50 mb-6">
          <button 
            className={`px-4 py-2 font-semibold text-sm ${activeTab === 'users' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('users')}
          >
            Users
          </button>
          <button 
            className={`px-4 py-2 font-semibold text-sm ${activeTab === 'workspaces' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('workspaces')}
          >
            Workspaces
          </button>
          <button 
            className={`px-4 py-2 font-semibold text-sm ${activeTab === 'demoRequests' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('demoRequests')}
          >
            Demo Requests
          </button>
          <button 
            className={`px-4 py-2 font-semibold text-sm flex items-center gap-1 ${activeTab === 'calendar' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('calendar')}
          >
            <CalendarIcon size={16} /> Calendar
          </button>
        </div>

        {/* Content based on tab */}
        {activeTab === 'users' && (
          <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="p-6 border-b border-border/50 flex items-center justify-between">
              <h2 className="text-xl font-bold">Platform Users</h2>
              <span className="text-xs font-semibold px-3 py-1 bg-primary/10 text-primary rounded-full">
                {usersData?.users?.length || 0} Registered
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase text-muted-foreground bg-muted/50 border-b border-border/50">
                  <tr>
                    <th className="px-6 py-4">User</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Joined</th>
                    <th className="px-6 py-4">Subscription Plan</th>
                    <th className="px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {usersLoading && (
                    <tr><td colSpan={5} className="p-6"><LoadingSkeleton className="h-12 w-full" /></td></tr>
                  )}
                  {usersData?.users?.map((u) => (
                    <tr key={u.id} className="border-b border-border/50 hover:bg-muted/20">
                      <td className="px-6 py-4 font-medium">
                        {u.email}
                        {u.is_super_admin && <span className="ml-2 text-[10px] bg-red-500/10 text-red-500 px-2 py-0.5 rounded uppercase font-bold">Admin</span>}
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-green-500/10 text-green-500 px-2 py-1 rounded text-xs font-semibold">Active</span>
                      </td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${u.plan_tier === 'Enterprise' ? 'bg-purple-500/20 text-purple-500' :
                            u.plan_tier === 'Pro' ? 'bg-blue-500/20 text-blue-500' :
                              'bg-muted text-muted-foreground'
                          }`}>
                          {u.plan_tier}
                        </span>
                      </td>
                      <td className="px-6 py-4 flex items-center gap-2">
                        <select
                          className="bg-muted border border-border text-xs rounded px-2 py-1 disabled:opacity-50"
                          value={u.plan_tier}
                          disabled={updateSubMutation.isPending}
                          onChange={(e) => requirePassword((pwd) => updateSubMutation.mutate({ targetUserId: u.id, newPlan: e.target.value, password: pwd }))}
                        >
                          <option value="Starter">Starter</option>
                          <option value="Pro">Pro</option>
                          <option value="Enterprise">Enterprise</option>
                        </select>
                        <button
                          disabled={updateSuperAdminMutation.isPending || u.id === currentUser.id}
                          onClick={() => requirePassword((pwd) => updateSuperAdminMutation.mutate({ targetUserId: u.id, isSuperAdmin: !u.is_super_admin, password: pwd }))}
                          className="px-3 py-1 bg-muted hover:bg-muted/80 text-xs font-semibold rounded border border-border disabled:opacity-50"
                        >
                          {u.is_super_admin ? 'Revoke Admin' : 'Make Admin'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'workspaces' && (
          <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="p-6 border-b border-border/50 flex items-center justify-between">
              <h2 className="text-xl font-bold">Workspaces</h2>
              <span className="text-xs font-semibold px-3 py-1 bg-primary/10 text-primary rounded-full">
                {workspacesData?.workspaces?.length || 0} Total
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase text-muted-foreground bg-muted/50 border-b border-border/50">
                  <tr>
                    <th className="px-6 py-4">Name</th>
                    <th className="px-6 py-4">Owner</th>
                    <th className="px-6 py-4">Members</th>
                    <th className="px-6 py-4">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {workspacesLoading && (
                    <tr><td colSpan={4} className="p-6"><LoadingSkeleton className="h-12 w-full" /></td></tr>
                  )}
                  {workspacesData?.workspaces?.map((w) => (
                    <tr key={w.id} className="border-b border-border/50 hover:bg-muted/20">
                      <td className="px-6 py-4 font-medium flex items-center gap-2">
                        <Briefcase size={14} className="text-muted-foreground" />
                        {w.name}
                      </td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {w.owner_email || 'Unknown'}
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 bg-muted rounded text-xs font-semibold">
                          {w.member_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {new Date(w.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'demoRequests' && (
          <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="p-6 border-b border-border/50 flex items-center justify-between">
              <h2 className="text-xl font-bold">Demo Requests</h2>
              <span className="text-xs font-semibold px-3 py-1 bg-primary/10 text-primary rounded-full">
                {demoRequestsData?.requests?.length || 0} Total
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase text-muted-foreground bg-muted/50 border-b border-border/50">
                  <tr>
                    <th className="px-6 py-4">Requester</th>
                    <th className="px-6 py-4">Company</th>
                    <th className="px-6 py-4">Message</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Date</th>
                    <th className="px-6 py-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {demoRequestsLoading && (
                    <tr><td colSpan={6} className="p-6"><LoadingSkeleton className="h-12 w-full" /></td></tr>
                  )}
                  {demoRequestsData?.requests?.map((req) => (
                    <tr key={req.id} className="border-b border-border/50 hover:bg-muted/20">
                      <td className="px-6 py-4">
                        <div className="font-bold">{req.name}</div>
                        <div className="text-muted-foreground text-xs">{req.email}</div>
                      </td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {req.company || '-'}
                      </td>
                      <td className="px-6 py-4 text-muted-foreground max-w-[200px] truncate" title={req.message}>
                        {req.message || '-'}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${
                          req.status === 'completed' ? 'bg-green-500/20 text-green-500' :
                          req.status === 'processing' ? 'bg-blue-500/20 text-blue-500' :
                          'bg-yellow-500/20 text-yellow-500'
                        }`}>
                          {req.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 flex items-center gap-2">
                        <select
                          className="bg-muted border border-border text-xs rounded px-2 py-1 disabled:opacity-50"
                          value={req.status}
                          disabled={updateDemoStatusMutation.isPending}
                          onChange={(e) => requirePassword((pwd) => updateDemoStatusMutation.mutate({ requestId: req.id, newStatus: e.target.value, password: pwd }))}
                        >
                          <option value="pending">Pending</option>
                          <option value="processing">Processing</option>
                          <option value="completed">Completed</option>
                        </select>
                        <ScheduleMeetingButton 
                          requestId={req.id} 
                          requirePassword={requirePassword} 
                          scheduleMeetingMutation={scheduleMeetingMutation} 
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'calendar' && (
          scheduledLoading ? (
            <div className="p-6"><LoadingSkeleton className="h-64 w-full" /></div>
          ) : (
            <AdminCalendar scheduledRequests={scheduledData?.requests || []} />
          )
        )}

      </div>

      {/* Password Modal */}
      {passwordModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="bg-card border border-border/50 p-6 rounded-xl w-full max-w-sm shadow-2xl relative">
            <button 
              onClick={() => { setPasswordModalOpen(false); setActionPassword(""); setPendingAction(null); }}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X size={20} />
            </button>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-500/10 text-red-500 rounded-lg">
                <Lock size={24} />
              </div>
              <h3 className="text-lg font-bold">Action Required</h3>
            </div>
            <p className="text-sm text-muted-foreground mb-4">Please enter your super admin action password to confirm this sensitive operation.</p>
            <form onSubmit={executePendingAction}>
              <input
                type="password"
                required
                autoFocus
                placeholder="Enter Action Password"
                className="w-full bg-muted border border-border rounded-lg px-4 py-2 mb-4"
                value={actionPassword}
                onChange={(e) => setActionPassword(e.target.value)}
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setPasswordModalOpen(false); setActionPassword(""); setPendingAction(null); }}
                  className="px-4 py-2 rounded-lg bg-muted hover:bg-muted/80 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white font-medium"
                >
                  Confirm Action
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value, icon: Icon, loading }) {
  return (
    <div className="p-5 border border-border/50 rounded-xl bg-card">
      <div className="flex items-center gap-3 mb-2 text-muted-foreground">
        <Icon size={18} />
        <span className="text-sm font-medium">{title}</span>
      </div>
      {loading ? (
        <LoadingSkeleton className="h-8 w-20" />
      ) : (
        <h3 className="text-2xl font-extrabold">{value}</h3>
      )}
    </div>
  );
}

function ScheduleMeetingButton({ requestId, requirePassword, scheduleMeetingMutation }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [meetingLink, setMeetingLink] = useState("");

  const handleSchedule = (e) => {
    e.preventDefault();
    setModalOpen(false);
    requirePassword((pwd) => {
      scheduleMeetingMutation.mutate({ requestId, date, time, meeting_link: meetingLink, password: pwd });
    });
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        className="px-3 py-1 bg-primary text-primary-foreground hover:bg-primary/80 text-xs font-semibold rounded border border-primary disabled:opacity-50"
      >
        Schedule
      </button>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="bg-card border border-border/50 p-6 rounded-xl w-full max-w-sm shadow-2xl relative">
            <button 
              onClick={() => setModalOpen(false)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X size={20} />
            </button>
            <h3 className="text-lg font-bold mb-1">Schedule Meeting</h3>
            <p className="text-xs text-muted-foreground mb-4">Provide a meeting link which will be emailed to the user.</p>
            <form onSubmit={handleSchedule} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Date</label>
                <input
                  type="date"
                  required
                  className="w-full bg-muted border border-border rounded-lg px-4 py-2"
                  value={date}
                  onChange={e => setDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Time (e.g. 10:00 AM EST)</label>
                <input
                  type="text"
                  required
                  placeholder="10:00 AM EST"
                  className="w-full bg-muted border border-border rounded-lg px-4 py-2"
                  value={time}
                  onChange={e => setTime(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Meeting Link (e.g. Google Meet, MS Teams, Zoom)</label>
                <input
                  type="url"
                  required
                  placeholder="https://meet.google.com/..."
                  className="w-full bg-muted border border-border rounded-lg px-4 py-2"
                  value={meetingLink}
                  onChange={e => setMeetingLink(e.target.value)}
                />
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-muted hover:bg-muted/80 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground font-medium"
                >
                  Confirm & Send
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
