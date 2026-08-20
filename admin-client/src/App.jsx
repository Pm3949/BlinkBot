import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldAlert, Users, Database, Globe, Bot, ShieldCheck, Activity, Briefcase, Lock, X, Calendar as CalendarIcon, LogOut, Plus, Trash2, Edit, CreditCard } from 'lucide-react';
import AdminCalendar from './components/AdminCalendar';
import { toast } from 'sonner';

// Custom sub-components
import Sidebar from './components/dashboard/Sidebar';
import StatCard from './components/dashboard/StatCard';
import WorkspacesTab from './components/dashboard/WorkspacesTab';
import UsersTab from './components/dashboard/UsersTab';
import DemoRequestsTab from './components/dashboard/DemoRequestsTab';
import SystemModelsTab from './components/dashboard/SystemModelsTab';
import AnalyticsTab from './components/dashboard/AnalyticsTab';
import TransactionsTab from './components/dashboard/TransactionsTab';
import FinanceTab from './components/dashboard/FinanceTab';
import PasswordModal from './components/dashboard/PasswordModal';
import LoginView from './components/dashboard/LoginView';
import BlogsTab from './components/dashboard/BlogsTab';

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function LoadingSkeleton({ className }) {
  return <div className={`animate-pulse bg-slate-200 dark:bg-slate-800 rounded-md ${className}`}></div>;
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

  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('adminTheme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('adminTheme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('adminTheme', 'light');
    }
  }, [isDarkMode]);

  const [workspaceSearch, setWorkspaceSearch] = useState('');
  const [userSearch, setUserSearch] = useState('');
  const [activeTab, setActiveTab] = useState('workspaces');

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

  const { data: scheduledData, isLoading: scheduledLoading } = useQuery({
    queryKey: ['adminScheduledRequests'],
    queryFn: () => fetchScheduledDemoRequests(currentUser),
    enabled: !!currentUser && activeTab === 'calendar',
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
    onSuccess: () => {
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
      <LoginView 
        email={email}
        setEmail={setEmail}
        password={password}
        setPassword={setPassword}
        isLoggingIn={isLoggingIn}
        handleLogin={handleLogin}
      />
    );
  }

  if (statsError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen space-y-4 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
        <ShieldAlert size={48} className="text-red-500" />
        <h2 className="text-2xl font-bold">Access Denied</h2>
        <p className="text-slate-500 dark:text-slate-400">You do not have Super Admin privileges.</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans transition-colors duration-200">
      {/* Sidebar Navigation */}
      <Sidebar 
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentUser={currentUser}
        handleLogout={handleLogout}
        isDarkMode={isDarkMode}
        setIsDarkMode={setIsDarkMode}
      />

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 overflow-y-auto p-8 lg:p-10 space-y-8 pb-16">
        {/* Page Title & Description */}
        <div className="flex justify-between items-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-xl shadow-sm">
          <div>
            <h1 className="text-2xl font-bold tracking-tight capitalize text-slate-900 dark:text-slate-100">
              {activeTab === 'demoRequests' ? 'Demo Requests' : activeTab === 'models' ? 'System AI Models' : activeTab === 'analytics' ? 'Usage Analytics' : activeTab === 'finance' ? 'Platform Finances' : activeTab}
            </h1>
            <p className="text-slate-500 dark:text-slate-400 text-sm mt-0.5 font-medium">
              {activeTab === 'workspaces' && 'Manage and monitor all custom RAG user workspaces.'}
              {activeTab === 'users' && 'Manage registered platform users and subscription levels.'}
              {activeTab === 'demoRequests' && 'Schedule and manage platform pilot demo requests.'}
              {activeTab === 'calendar' && 'Scheduled pilot onboarding and demo sessions.'}
              {activeTab === 'models' && 'Manage configuration and credit rates of system models.'}
              {activeTab === 'analytics' && 'Global token consumption and provider usage metrics.'}
              {activeTab === 'transactions' && 'Audit logs of payment transactions and subscription invoices.'}
              {activeTab === 'finance' && 'Organic billing invoicing vs manual platform expenses.'}
            </p>
          </div>
        </div>

        {/* Global Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard title="Total Users" value={stats?.totalUsers} icon={Users} loading={statsLoading} />
          <StatCard title="Workspaces" value={stats?.totalWorkspaces} icon={Activity} loading={statsLoading} />
          <StatCard title="Total Agents" value={stats?.totalAgents} icon={Bot} loading={statsLoading} />
          <StatCard title="Chatbots" value={stats?.totalChatbots} icon={Globe} loading={statsLoading} />
          <StatCard title="DB Storage" value={stats ? `${stats.totalStorageMB} MB` : null} icon={Database} loading={statsLoading} />
        </div>

        {/* Dynamic section content */}
        {activeTab === 'workspaces' && (
          <WorkspacesTab 
            workspacesData={workspacesData}
            workspacesLoading={workspacesLoading}
            workspaceSearch={workspaceSearch}
            setWorkspaceSearch={setWorkspaceSearch}
          />
        )}

        {activeTab === 'users' && (
          <UsersTab 
            usersData={usersData}
            usersLoading={usersLoading}
            userSearch={userSearch}
            setUserSearch={setUserSearch}
            updateSubMutation={updateSubMutation}
            updateSuperAdminMutation={updateSuperAdminMutation}
            currentUser={currentUser}
            requirePassword={requirePassword}
          />
        )}

        {activeTab === 'demoRequests' && (
          <DemoRequestsTab 
            demoRequestsData={demoRequestsData}
            demoRequestsLoading={demoRequestsLoading}
            updateDemoStatusMutation={updateDemoStatusMutation}
            requirePassword={requirePassword}
            scheduleMeetingMutation={scheduleMeetingMutation}
          />
        )}

        {activeTab === 'calendar' && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm">
            {scheduledLoading ? (
              <LoadingSkeleton className="h-64 w-full" />
            ) : (
              <AdminCalendar scheduledRequests={scheduledData?.requests || []} />
            )}
          </div>
        )}

        {activeTab === 'models' && (
          <SystemModelsTab 
            currentUser={currentUser}
            requirePassword={requirePassword}
            API_URL={API_URL}
          />
        )}

        {activeTab === 'analytics' && (
          <AnalyticsTab stats={stats} />
        )}

        {activeTab === 'transactions' && (
          <TransactionsTab 
            transactionsData={transactionsData}
            transactionsLoading={transactionsLoading}
            API_URL={API_URL}
          />
        )}

        {activeTab === 'finance' && (
          <FinanceTab API_URL={API_URL} />
        )}

        {activeTab === 'blogs' && (
          <BlogsTab />
        )}
      </main>

      {/* Password Challenge Modal */}
      <PasswordModal 
        passwordModalOpen={passwordModalOpen}
        setPasswordModalOpen={setPasswordModalOpen}
        actionPassword={actionPassword}
        setActionPassword={setActionPassword}
        executePendingAction={executePendingAction}
        setPendingAction={setPendingAction}
      />
    </div>
  );
}
