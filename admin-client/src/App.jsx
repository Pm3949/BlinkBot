import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldAlert, Users, Database, Globe, Bot, ShieldCheck, Activity, Briefcase, Lock, X, Calendar as CalendarIcon, LogOut, Plus, Trash2, Edit, CreditCard } from 'lucide-react';
import AdminCalendar from './components/AdminCalendar';
import { toast } from 'sonner';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell } from 'recharts';

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function LoadingSkeleton({ className }) {
  return <div className={`animate-pulse bg-muted rounded-md ${className}`}></div>;
}

async function fetchAdminStats(user) {
  const token = localStorage.getItem('adminToken');
  const res = await fetch(`${API_URL}/admin/stats?user_id=${user.id}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to load admin stats");
  return res.json();
}

async function fetchAdminUsers(user) {
  const token = localStorage.getItem('adminToken');
  const res = await fetch(`${API_URL}/admin/users?user_id=${user.id}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to load admin users");
  return res.json();
}

async function fetchAdminWorkspaces(user) {
  const token = localStorage.getItem('adminToken');
  const res = await fetch(`${API_URL}/admin/workspaces?user_id=${user.id}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to load admin workspaces");
  return res.json();
}

async function fetchAdminDemoRequests(user) {
  const token = localStorage.getItem('adminToken');
  const res = await fetch(`${API_URL}/admin/demo-requests?user_id=${user.id}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
  if (!res.ok) throw new Error("Failed to load admin demo requests");
  return res.json();
}

async function fetchScheduledDemoRequests(user) {
  const token = localStorage.getItem('adminToken');
  const res = await fetch(`${API_URL}/admin/demo-requests/scheduled?user_id=${user.id}`, {
    headers: { "Authorization": `Bearer ${token}` }
  });
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

  const { data: transactionsData, isLoading: transactionsLoading } = useQuery({
    queryKey: ['adminTransactions'],
    queryFn: async () => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/transactions`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load admin transactions");
      return res.json();
    },
    enabled: !!currentUser,
  });

  const [financeInterval, setFinanceInterval] = useState('monthly');
  const [expenseModalOpen, setExpenseModalOpen] = useState(false);
  const [expenseAmount, setExpenseAmount] = useState('');
  const [expenseDesc, setExpenseDesc] = useState('');
  const [expenseCategory, setExpenseCategory] = useState('Hosting');

  const { data: financesData, isLoading: financesLoading, refetch: refetchFinances } = useQuery({
    queryKey: ['adminFinances', financeInterval],
    queryFn: async () => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/finances?interval=${financeInterval}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load admin finances");
      return res.json();
    },
    enabled: !!currentUser,
  });

  const createExpenseMutation = useMutation({
    mutationFn: async (payload) => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/expenses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to record expense");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Platform expense recorded successfully!");
      setExpenseModalOpen(false);
      setExpenseAmount('');
      setExpenseDesc('');
      refetchFinances();
    },
    onError: (err) => toast.error(err.message)
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
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/users/${targetUserId}/subscription`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
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
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/users/${targetUserId}/super_admin`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
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
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/demo-requests/${requestId}/status`, {
        method: "PATCH",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
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
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/admin/demo-requests/${requestId}/schedule`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
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

  const [expandedTransactions, setExpandedTransactions] = useState({});

  const toggleExpand = (id) => {
    setExpandedTransactions(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-8">
      <div className="max-w-7xl mx-auto space-y-8 pb-10">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <ShieldCheck className="text-primary w-8 h-8" />
              Super Admin Portal
            </h1>
            <p className="text-muted-foreground mt-2">Manage the entire platform across all users and workspaces.</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{currentUser.email}</span>
            <button onClick={handleLogout} className="flex items-center gap-1.5 px-3 py-1.5 bg-muted hover:bg-muted/80 rounded-lg text-sm font-medium transition">
              <LogOut size={16} /> Logout
            </button>
          </div>
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
          <button 
            className={`px-4 py-2 font-semibold text-sm flex items-center gap-1 ${activeTab === 'models' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('models')}
          >
            <Bot size={16} /> System Models
          </button>
          <button 
            className={`px-4 py-2 font-semibold text-sm flex items-center gap-1 ${activeTab === 'analytics' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('analytics')}
          >
            <Activity size={16} className="text-amber-500" /> Usage Analytics
          </button>
          <button 
            className={`px-4 py-2 font-semibold text-sm flex items-center gap-1 ${activeTab === 'transactions' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('transactions')}
          >
            <CreditCard size={16} /> Transactions
          </button>
          <button 
            className={`px-4 py-2 font-semibold text-sm flex items-center gap-1 ${activeTab === 'finance' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            onClick={() => setActiveTab('finance')}
          >
            <Briefcase size={16} className="text-emerald-500" /> Finance Dashboard
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

        {activeTab === 'models' && (
          <SystemModels 
            currentUser={currentUser}
            requirePassword={requirePassword}
          />
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-8 animate-fadeIn">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold">Global Platform Usage</h2>
                <p className="text-sm text-muted-foreground mt-1">Telemetry analytics across all wallets, tokens, models, and providers.</p>
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
              {/* Global Model Usage (Bar Chart) */}
              <div className="border border-border/50 bg-card rounded-xl p-6 shadow-sm">
                <h3 className="text-base font-bold mb-6 flex items-center gap-2">
                  <Bot size={16} className="text-primary" /> Wallet Credit Burn by Model ID (All-Time)
                </h3>
                {stats?.globalModelUsage?.length > 0 ? (
                  <div className="h-80 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats.globalModelUsage}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                        <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                        <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                        <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                        <Bar dataKey="credits" fill="#6366f1" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-80 flex items-center justify-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                    No system model usage telemetry recorded.
                  </div>
                )}
              </div>

              {/* Global API Provider Usage (Pie Chart) */}
              <div className="border border-border/50 bg-card rounded-xl p-6 shadow-sm flex flex-col justify-between">
                <div>
                  <h3 className="text-base font-bold mb-6 flex items-center gap-2">
                    <Globe size={16} className="text-emerald-500" /> Share of Credit Usage by Provider
                  </h3>
                  {stats?.globalProviderUsage?.length > 0 ? (
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={stats.globalProviderUsage}
                            cx="50%"
                            cy="50%"
                            innerRadius={60}
                            outerRadius={80}
                            paddingAngle={5}
                            dataKey="credits"
                          >
                            {stats.globalProviderUsage.map((entry, index) => {
                              const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#a855f7', '#3b82f6'];
                              return <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />;
                            })}
                          </Pie>
                          <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="h-64 flex items-center justify-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                      No provider credit usage statistics available.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'transactions' && (
          <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
            <div className="p-6 border-b border-border/50 flex items-center justify-between bg-muted/10">
              <div>
                <h2 className="text-xl font-bold">Platform Transactions</h2>
                <p className="text-sm text-muted-foreground mt-1">Audit log of all payments, subscription checkouts, and wallet recharges across the platform.</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground uppercase text-[10px] tracking-wider font-bold bg-muted/5">
                    <th className="px-6 py-4">Invoice Number</th>
                    <th className="px-6 py-4">User</th>
                    <th className="px-6 py-4">Description</th>
                    <th className="px-6 py-4">Amount</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Date</th>
                    <th className="px-6 py-4 text-right">Receipt</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {transactionsLoading ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground font-semibold">Loading transactions...</td>
                    </tr>
                  ) : !transactionsData?.transactions || transactionsData.transactions.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground font-semibold">No platform transactions found.</td>
                    </tr>
                  ) : (
                    transactionsData.transactions.map((tx) => (
                      <React.Fragment key={tx.id}>
                        <tr 
                          onClick={() => toggleExpand(tx.id)}
                          className="hover:bg-muted/10 transition-colors cursor-pointer"
                        >
                          <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                            <div className="font-mono text-xs font-semibold">{tx.invoice_number}</div>
                            {tx.metadata?.razorpay_payment_id && (
                              <div className="font-mono text-[10px] text-muted-foreground mt-0.5 flex items-center gap-1">
                                <span>TxID: {tx.metadata.razorpay_payment_id}</span>
                                <button
                                  onClick={() => {
                                    navigator.clipboard.writeText(tx.metadata.razorpay_payment_id);
                                    toast.success("Transaction ID copied!");
                                  }}
                                  className="text-muted-foreground hover:text-primary transition"
                                >
                                  <svg xmlns="http://www.w3.org/2000/svg" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></svg>
                                </button>
                              </div>
                            )}
                          </td>
                          <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center gap-1.5">
                              <span className="font-medium text-xs truncate max-w-[150px]" title={tx.user_email}>{tx.user_email}</span>
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(tx.user_email);
                                  toast.success("Email copied!");
                                }}
                                className="text-muted-foreground hover:text-primary transition shrink-0"
                                title="Copy Email"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></svg>
                              </button>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-xs font-semibold">{tx.description}</td>
                          <td className="px-6 py-4 font-bold text-xs">₹{tx.amount_inr.toFixed(2)}</td>
                          <td className="px-6 py-4">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              tx.status === 'Paid'
                                ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                                : 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                            }`}>
                              {tx.status}
                            </span>
                          </td>
                          <td className="px-6 py-4 text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(tx.created_at).toLocaleDateString(undefined, {
                              year: 'numeric', month: 'short', day: 'numeric',
                              hour: '2-digit', minute: '2-digit'
                            })}
                          </td>
                          <td className="px-6 py-4 text-right" onClick={e => e.stopPropagation()}>
                            <button
                              onClick={async () => {
                                try {
                                  toast.info("Downloading PDF receipt...");
                                  const token = localStorage.getItem('adminToken');
                                  const response = await fetch(`${API_URL}/api/billing/invoice/${tx.id}/download`, {
                                    headers: { "Authorization": `Bearer ${token}` }
                                  });
                                  if (!response.ok) throw new Error("Receipt download failed");
                                  const blob = await response.blob();
                                  const url = window.URL.createObjectURL(blob);
                                  const a = document.createElement("a");
                                  a.href = url;
                                  a.download = `invoice-${tx.invoice_number}.pdf`;
                                  document.body.appendChild(a);
                                  a.click();
                                  document.body.removeChild(a);
                                  toast.success("Receipt downloaded successfully!");
                                } catch (err) {
                                  toast.error(err.message || "Failed to download receipt");
                                }
                              }}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold rounded-lg transition"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                              Receipt
                            </button>
                          </td>
                        </tr>
                        {expandedTransactions[tx.id] && (
                          <tr className="bg-muted/10">
                            <td colSpan={7} className="px-8 py-4 border-t border-b border-border/40">
                              <div className="space-y-2">
                                <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                  <span>Razorpay API Metadata Payload</span>
                                </div>
                                <pre className="text-[10px] bg-muted/20 border border-border/40 p-4 rounded-xl font-mono overflow-x-auto text-muted-foreground whitespace-pre-wrap max-w-full">
                                  {JSON.stringify(tx.metadata, null, 2)}
                                </pre>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'finance' && (
          <div className="space-y-8 animate-fadeIn">
            {/* Financial Overview stats */}
            <div className="flex justify-between items-center bg-card border border-border/50 p-6 rounded-xl shadow-sm">
              <div>
                <h2 className="text-xl font-bold">Platform Finances</h2>
                <p className="text-xs text-muted-foreground mt-0.5">Aggregate breakdown of organic checkout sales vs manual platform expenses.</p>
              </div>
              <div className="flex items-center gap-3">
                <select
                  value={financeInterval}
                  onChange={(e) => setFinanceInterval(e.target.value)}
                  className="bg-muted border border-border rounded-lg text-xs font-bold px-3 py-2"
                >
                  <option value="monthly">Monthly Intervals</option>
                  <option value="yearly">Yearly Intervals</option>
                </select>
                <button
                  onClick={() => setExpenseModalOpen(true)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg transition shadow-md shadow-emerald-500/10"
                >
                  <Plus size={14} /> Record Expense
                </button>
              </div>
            </div>

            {financesLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2, 3].map(i => <LoadingSkeleton key={i} className="h-32" />)}
              </div>
            ) : (
              <>
                {/* Financial KPI stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="glass-card p-6 border border-border/50 flex items-center gap-4">
                    <div className="p-4 rounded-xl bg-indigo-500/10 text-indigo-500">
                      <CreditCard className="w-8 h-8" />
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Total Revenue (Organic Invoices)</p>
                      <h3 className="text-3xl font-extrabold text-foreground mt-1">₹{(financesData?.report?.totalRevenue || 0).toLocaleString()}</h3>
                    </div>
                  </div>
                  <div className="glass-card p-6 border border-border/50 flex items-center gap-4">
                    <div className="p-4 rounded-xl bg-red-500/10 text-red-500">
                      <Briefcase className="w-8 h-8" />
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Total Platform Expenses (Manual)</p>
                      <h3 className="text-3xl font-extrabold text-foreground mt-1">₹{(financesData?.report?.totalExpenses || 0).toLocaleString()}</h3>
                    </div>
                  </div>
                  <div className="glass-card p-6 border border-border/50 flex items-center gap-4">
                    <div className="p-4 rounded-xl bg-emerald-500/10 text-emerald-500">
                      <Activity className="w-8 h-8" />
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Net Profit / Margin</p>
                      <h3 className="text-3xl font-extrabold text-foreground mt-1 flex items-baseline gap-2">
                        <span>₹{(financesData?.report?.netProfit || 0).toLocaleString()}</span>
                        <span className="text-xs font-semibold text-muted-foreground">
                          ({financesData?.report?.totalRevenue > 0 ? ((financesData.report.netProfit / financesData.report.totalRevenue) * 100).toFixed(0) : 0}%)
                        </span>
                      </h3>
                    </div>
                  </div>
                </div>

                <div className="grid lg:grid-cols-3 gap-8">
                  {/* Revenue vs Expenses Line/Bar Chart */}
                  <div className="lg:col-span-2 border border-border/50 bg-card rounded-xl p-6 shadow-sm">
                    <h3 className="text-base font-bold mb-6 flex items-center gap-2">
                      <Activity size={16} className="text-primary" /> Revenue vs Spends Trend
                    </h3>
                    {financesData?.report?.series?.length > 0 ? (
                      <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={financesData.report.series}>
                            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                            <XAxis dataKey="period" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                            <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
                            <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }} />
                            <Legend />
                            <Bar dataKey="revenue" name="Revenue (₹)" fill="#6366f1" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="expenses" name="Expenses (₹)" fill="#ef4444" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ) : (
                      <div className="h-80 flex items-center justify-center text-muted-foreground border-2 border-dashed border-border rounded-xl">
                        No financial transactions recorded for this range.
                      </div>
                    )}
                  </div>

                  {/* Manual expenses summary */}
                  <div className="lg:col-span-1 border border-border/50 bg-card rounded-xl p-6 shadow-sm flex flex-col justify-between h-full">
                    <div>
                      <h3 className="text-base font-bold mb-4">Manual Spends Log</h3>
                      <div className="divide-y divide-border/50 max-h-80 overflow-y-auto pr-1">
                        {!financesData?.expenses || financesData.expenses.length === 0 ? (
                          <div className="text-center py-12 text-muted-foreground text-xs">No manual platform spends recorded.</div>
                        ) : (
                          financesData.expenses.map((exp) => (
                            <div key={exp.id} className="py-3 flex justify-between items-start text-xs">
                              <div>
                                <div className="font-semibold text-foreground">{exp.description}</div>
                                <div className="text-[10px] text-muted-foreground mt-0.5 flex items-center gap-1.5">
                                  <span className="bg-muted px-1.5 py-0.5 rounded text-foreground font-bold">{exp.category}</span>
                                  <span>{new Date(exp.created_at).toLocaleDateString()}</span>
                                </div>
                              </div>
                              <div className="font-bold text-red-400">-₹{exp.amount_inr.toFixed(0)}</div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}

            {/* Expense record modal */}
            {expenseModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
                <div className="bg-card border border-border/50 p-6 rounded-xl w-full max-w-sm shadow-2xl relative">
                  <button
                    onClick={() => setExpenseModalOpen(false)}
                    className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
                  >
                    <X size={20} />
                  </button>
                  <h3 className="text-lg font-bold mb-4">Record Platform Expense</h3>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      createExpenseMutation.mutate({
                        amount_inr: parseFloat(expenseAmount),
                        description: expenseDesc,
                        category: expenseCategory
                      });
                    }}
                    className="space-y-4 text-xs font-medium"
                  >
                    <div>
                      <label className="block mb-1 text-muted-foreground">Amount (INR)</label>
                      <input
                        type="number" required min="1" placeholder="5000"
                        value={expenseAmount} onChange={e => setExpenseAmount(e.target.value)}
                        className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm font-bold"
                      />
                    </div>
                    <div>
                      <label className="block mb-1 text-muted-foreground">Description</label>
                      <input
                        type="text" required placeholder="AWS EC2 hosting invoice"
                        value={expenseDesc} onChange={e => setExpenseDesc(e.target.value)}
                        className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block mb-1 text-muted-foreground">Category</label>
                      <select
                        value={expenseCategory} onChange={e => setExpenseCategory(e.target.value)}
                        className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm font-bold"
                      >
                        <option value="Hosting">Hosting / Servers</option>
                        <option value="API Cost">LLM API Invoices</option>
                        <option value="Marketing">Marketing / ADS</option>
                        <option value="Salary">Developer Salaries</option>
                        <option value="Other">Other Expenses</option>
                      </select>
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <button
                        type="button" onClick={() => setExpenseModalOpen(false)}
                        className="px-4 py-2 rounded-lg bg-muted hover:bg-muted/80 text-sm font-bold transition"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit" disabled={createExpenseMutation.isPending}
                        className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold transition disabled:opacity-50"
                      >
                        {createExpenseMutation.isPending ? "Recording..." : "Record Expense"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
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


function SystemModels({ currentUser, requirePassword }) {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState(null);

  // Form states
  const [modelId, setModelId] = useState("");
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("openai");
  const [category, setCategory] = useState("chat");
  const [badge, setBadge] = useState("");
  const [inputCost, setInputCost] = useState(0.0);
  const [outputCost, setOutputCost] = useState(0.0);
  const [creditsPer1k, setCreditsPer1k] = useState(0.0);
  const [requiresKey, setRequiresKey] = useState(false);
  const [baseUrl, setBaseUrl] = useState("");
  const [isActive, setIsActive] = useState(true);

  const { data: modelsData, isLoading, refetch } = useQuery({
    queryKey: ['adminModels'],
    queryFn: async () => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/api/models/all`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Failed to load models");
      return res.json();
    },
    enabled: !!currentUser
  });

  const createModelMutation = useMutation({
    mutationFn: async (newModel) => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/api/models`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(newModel)
      });
      if (!res.ok) throw new Error("Failed to create model");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Model created successfully!");
      setModalOpen(false);
      refetch();
    },
    onError: (err) => toast.error(err.message)
  });

  const updateModelMutation = useMutation({
    mutationFn: async ({ id, updateData }) => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/api/models/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(updateData)
      });
      if (!res.ok) throw new Error("Failed to update model");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Model updated successfully!");
      setModalOpen(false);
      refetch();
    },
    onError: (err) => toast.error(err.message)
  });

  const deleteModelMutation = useMutation({
    mutationFn: async (id) => {
      const token = localStorage.getItem('adminToken');
      const res = await fetch(`${API_URL}/api/models/${id}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error("Failed to delete model");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Model deleted successfully!");
      refetch();
    },
    onError: (err) => toast.error(err.message)
  });

  const openAddModal = () => {
    setEditingModel(null);
    setModelId("");
    setName("");
    setProvider("openai");
    setCategory("chat");
    setBadge("");
    setInputCost(0.0);
    setOutputCost(0.0);
    setCreditsPer1k(0.0);
    setRequiresKey(false);
    setBaseUrl("");
    setIsActive(true);
    setModalOpen(true);
  };

  const openEditModal = (model) => {
    setEditingModel(model);
    setModelId(model.model_id || model.id || "");
    setName(model.name || "");
    setProvider(model.provider || "openai");
    setCategory(model.category || "chat");
    setBadge(model.badge || "");
    setInputCost(model.input_cost_per_1m || 0.0);
    setOutputCost(model.output_cost_per_1m || 0.0);
    setCreditsPer1k(model.credits_per_1k_tokens || 0.0);
    setRequiresKey(model.requires_key || false);
    setBaseUrl(model.base_url || "");
    setIsActive(model.is_active !== false);
    setModalOpen(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      provider,
      model_id: modelId,
      name,
      category,
      badge,
      input_cost_per_1m: parseFloat(inputCost),
      output_cost_per_1m: parseFloat(outputCost),
      credits_per_1k_tokens: parseFloat(creditsPer1k),
      requires_key: false,
      base_url: baseUrl,
      is_active: isActive,
      is_system: true
    };

    if (editingModel) {
      updateModelMutation.mutate({ id: editingModel.id, updateData: payload });
    } else {
      createModelMutation.mutate(payload);
    }
  };

  return (
    <div className="border border-border/50 rounded-xl overflow-hidden bg-card">
      <div className="p-6 border-b border-border/50 flex items-center justify-between">
        <h2 className="text-xl font-bold">System AI Models</h2>
        <button
          onClick={openAddModal}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-primary hover:bg-primary/80 text-primary-foreground text-xs font-semibold rounded-lg transition"
        >
          <Plus size={14} /> Add Model
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase text-muted-foreground bg-muted/50 border-b border-border/50">
            <tr>
              <th className="px-6 py-4">Model Details</th>
              <th className="px-6 py-4">Provider</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Badge / Category</th>
              <th className="px-6 py-4">Input / Output Cost</th>
              <th className="px-6 py-4">Credits / 1k tokens</th>
              <th className="px-6 py-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={7} className="p-6"><LoadingSkeleton className="h-12 w-full" /></td></tr>
            )}
            {modelsData?.models?.map((m) => (
              <tr key={m.id} className="border-b border-border/50 hover:bg-muted/20">
                <td className="px-6 py-4">
                  <div className="font-medium text-foreground">{m.name}</div>
                  <div className="text-xs text-muted-foreground font-mono">{m.model_id || m.id}</div>
                </td>
                <td className="px-6 py-4 font-semibold capitalize text-muted-foreground">
                  {m.provider}
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${m.is_active ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                    {m.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex gap-1.5 flex-wrap">
                    <span className="bg-muted px-2 py-0.5 rounded text-xs text-muted-foreground font-bold uppercase">{m.category || "chat"}</span>
                    {m.badge && <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-xs font-bold uppercase">{m.badge}</span>}
                  </div>
                </td>
                <td className="px-6 py-4 text-xs font-mono text-muted-foreground">
                  <div>In: ${m.input_cost_per_1m?.toFixed(2) || "0.00"}/1M</div>
                  <div>Out: ${m.output_cost_per_1m?.toFixed(2) || "0.00"}/1M</div>
                </td>
                <td className="px-6 py-4 font-mono font-bold text-foreground">
                  {m.credits_per_1k_tokens || "0.0000"}
                </td>
                <td className="px-6 py-4 flex items-center gap-2">
                  <button
                    onClick={() => openEditModal(m)}
                    className="p-1.5 bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground rounded transition"
                    title="Edit Model"
                  >
                    <Edit size={14} />
                  </button>
                  <button
                    onClick={() => requirePassword((pwd) => deleteModelMutation.mutate(m.id))}
                    className="p-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded transition"
                    title="Delete Model"
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
          <div className="bg-card border border-border/50 p-6 rounded-xl w-full max-w-lg shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button 
              onClick={() => setModalOpen(false)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X size={20} />
            </button>
            <h3 className="text-lg font-bold mb-4">{editingModel ? "Edit System Model" : "Add System Model"}</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1">Model Name</label>
                  <input
                    type="text" required placeholder="GPT-4o (Premium)"
                    value={name} onChange={e => setName(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Model ID</label>
                  <input
                    type="text" required placeholder="gpt-4o"
                    value={modelId} onChange={e => setModelId(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1">Provider</label>
                  <select
                    value={provider} onChange={e => setProvider(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="openai">OpenAI</option>
                    <option value="groq">Groq</option>
                    <option value="gemini">Gemini</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="huggingface">HuggingFace</option>
                    <option value="custom_openai">Custom Endpoint</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Category</label>
                  <select
                    value={category} onChange={e => setCategory(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="chat">Chat / LLM</option>
                    <option value="embedding">Embedding</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1">Badge</label>
                  <input
                    type="text" placeholder="PRO or FAST"
                    value={badge} onChange={e => setBadge(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Credits per 1k Tokens</label>
                  <input
                    type="number" step="0.0001" placeholder="0.015"
                    value={creditsPer1k} onChange={e => setCreditsPer1k(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium mb-1">Input Cost ($ / 1M tokens)</label>
                  <input
                    type="number" step="0.0001" placeholder="2.50"
                    value={inputCost} onChange={e => setInputCost(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Output Cost ($ / 1M tokens)</label>
                  <input
                    type="number" step="0.0001" placeholder="10.00"
                    value={outputCost} onChange={e => setOutputCost(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm font-mono"
                  />
                </div>
              </div>

              {/* Live Margin & Profit Estimator */}
              {(() => {
                const creds = parseFloat(creditsPer1k) || 0;
                const inCostUsd = parseFloat(inputCost) || 0;
                const outCostUsd = parseFloat(outputCost) || 0;
                
                // Conversions
                const USD_TO_INR = 84; 
                
                // Sale price: 10 Credits = 1 INR. 1k tokens to 1M tokens = 1000x multiplier.
                // Sale price per 1M tokens = (credits_per_1k * 1000) / 10 = credits_per_1k * 100
                const salePriceInrPer1M = creds * 100;
                
                // Average cost per 1M tokens in USD
                const avgCostUsdPer1M = (inCostUsd + outCostUsd) / 2;
                const avgCostInrPer1M = avgCostUsdPer1M * USD_TO_INR;
                
                // Margin details
                const profitInr = salePriceInrPer1M - avgCostInrPer1M;
                const marginPct = avgCostInrPer1M > 0 ? (profitInr / avgCostInrPer1M) * 100 : 0;
                
                return (
                  <div className="bg-primary/5 border border-primary/20 rounded-xl p-3.5 space-y-2 text-xs">
                    <div className="font-semibold text-primary uppercase tracking-wider text-[10px]">
                      📊 Live Profit Estimator
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-muted-foreground">
                      <div>User Price (Sale):</div>
                      <div className="text-right font-semibold text-foreground">
                        ₹{salePriceInrPer1M.toFixed(2)} INR / 1M tokens
                      </div>
                      <div>Your Cost (Breakeven):</div>
                      <div className="text-right font-semibold text-foreground">
                        ₹{avgCostInrPer1M.toFixed(2)} INR / 1M tokens (~${avgCostUsdPer1M.toFixed(2)})
                      </div>
                      <div className="border-t border-border mt-1 pt-1 font-bold text-foreground">
                        Estimated Markup:
                      </div>
                      <div className={`border-t border-border mt-1 pt-1 text-right font-extrabold ${profitInr >= 0 ? "text-emerald-500" : "text-red-400"}`}>
                        {profitInr >= 0 ? "+" : ""}₹{profitInr.toFixed(2)} INR ({marginPct.toFixed(0)}% markup)
                      </div>
                    </div>
                  </div>
                );
              })()}


              {provider === "custom_openai" && (
                <div>
                  <label className="block text-xs font-medium mb-1">Custom Base URL</label>
                  <input
                    type="text" placeholder="https://api.together.xyz/v1"
                    value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
                    className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              )}

              <div className="flex gap-6 items-center pt-2">
                <label className="flex items-center gap-2 text-xs font-medium">
                  <input
                    type="checkbox"
                    checked={isActive} onChange={e => setIsActive(e.target.checked)}
                    className="rounded border-border text-primary focus:ring-primary/50"
                  />
                  Active in Selection
                </label>
              </div>

              <div className="flex justify-end gap-2 mt-6">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-muted hover:bg-muted/80 font-medium text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/95 text-primary-foreground font-medium text-sm"
                >
                  {editingModel ? "Update Model" : "Create Model"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

