import { useState } from "react";
import { Link } from "react-router-dom";
import KPIGrid from "../components/dashboard/KPIGrid";
import QuickActions from "../components/dashboard/QuickActions";
import RecentAgents from "../components/dashboard/RecentAgents";
import ActivityFeed from "../components/dashboard/ActivityFeed";
import { useAuth } from "../context/AuthContext";
import { useAgents, useAgentProjects } from "../hooks/useAgents";
import { useChat } from "../hooks/useChat";
import { useAnalytics } from "../hooks/useAnalytics";


import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { useUIStore } from "../store/useUIStore";
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend 
} from "recharts";
import { Bot, MessageSquare, ShieldCheck, Activity, Globe, MessageCircle } from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { sessions = [] } = useChat();
  const [activeTab, setActiveTab] = useState("widget"); // 'widget' or 'internal'

  const setCreateAgentWizardOpen = useUIStore(
    (state) => state.setCreateAgentWizardOpen,
  );
  
  const {
    data: agents = [],
    isLoading: isLoadingAgents,
  } = useAgents(activeWorkspaceId, true);
  
  const {
    data: projects = [],
  } = useAgentProjects(activeWorkspaceId);

  const {
    data: analyticsData,
    isLoading: isLoadingAnalytics,
  } = useAnalytics();

  const totalMessages = sessions.reduce(
    (count, session) => count + (session.messages?.length || 0),
    0,
  );

  const greeting = () => {
    const hr = new Date().getHours();
    if (hr < 12) return "Good morning";
    if (hr < 17) return "Good afternoon";
    return "Good evening";
  };

  // Extract values from analytics API, or fallback to local states
  const metrics = analyticsData?.metrics || {};
  const internalSeries = analyticsData?.internalSeries || [];
  const widgetSeries = analyticsData?.widgetSeries || [];
  const recentQuestions = analyticsData?.recentQuestions || [];

  const totalAgents = metrics.totalAgents ?? agents.length;
  const storageUsedMB = metrics.storageUsedMB ?? 0;
  const totalWidgetMessages = metrics.totalWidgetMessages ?? 0;
  const totalDocs = metrics.totalDocuments ?? 0;

  return (
    <div className="space-y-8 max-w-[1500px] mx-auto pb-10">
      {/* Premium Greeting Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border border-primary/20 p-6 md:p-8">
        <div className="absolute top-0 right-0 -translate-y-12 translate-x-12 w-64 h-64 bg-primary/5 rounded-full blur-3xl" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-primary font-semibold text-sm">
              <ShieldCheck size={16} />
              <span>Workspace Active</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-foreground mt-2 tracking-tight">
              {greeting()}, {user?.email?.split("@")[0] || "Builder"}!
            </h1>
            <p className="text-muted-foreground text-sm mt-1 max-w-xl">
              Welcome back to your BlinkBot developer hub. Check your agent activity and public widget analytics below.
            </p>
          </div>
          <Link
            to="/studio"
            className="self-start md:self-auto bg-primary hover:bg-primary-hover text-white font-semibold text-sm px-5 py-2.5 rounded-full shadow-lg hover:shadow-primary/20 transition-all cursor-pointer flex items-center gap-2"
          >
            <Bot size={16} />
            Create New Agent
          </Link>
        </div>
      </div>

      {/* Upgraded KPI Grid */}
      <KPIGrid
        activeAgentsCount={totalAgents}
        conversationsCount={sessions.length}
        messagesCount={totalMessages}
        networksCount={projects.length}
        documentsCount={totalDocs}
        storageUsedMB={storageUsedMB}
        widgetMessagesCount={totalWidgetMessages}
        isLoadingAgents={isLoadingAgents || isLoadingAnalytics}
        internalSeries={internalSeries}
        widgetSeries={widgetSeries}
      />

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Main Charts & Traffic Panel */}
        <div className="lg:col-span-2 space-y-8">
          <div className="glass-card p-6 border border-border/50">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="font-bold text-lg text-foreground flex items-center gap-2">
                  <Activity className="text-primary w-5 h-5" /> Usage & Traffic
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">Performance statistics over the last 30 days</p>
              </div>

              {/* Tabs */}
              <div className="flex bg-muted/50 p-1 rounded-full border border-border">
                <button
                  onClick={() => setActiveTab("widget")}
                  className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all flex items-center gap-1.5 ${
                    activeTab === "widget"
                      ? "bg-primary text-white shadow-md"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Globe size={13} />
                  Widget API
                </button>
                <button
                  onClick={() => setActiveTab("internal")}
                  className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all flex items-center gap-1.5 ${
                    activeTab === "internal"
                      ? "bg-primary text-white shadow-md"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <MessageCircle size={13} />
                  Internal App
                </button>
              </div>
            </div>

            {/* Recharts chart render */}
            {isLoadingAnalytics ? (
              <div className="h-72 w-full">
                <LoadingSkeleton count={1} className="h-full rounded-2xl" />
              </div>
            ) : activeTab === "widget" ? (
              widgetSeries.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={widgetSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                      <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '12px' }}
                        itemStyle={{ color: 'hsl(var(--foreground))' }}
                      />
                      <Line type="monotone" dataKey="messages" name="Widget Messages" stroke="var(--primary)" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 6 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-72 flex items-center justify-center text-muted-foreground border border-dashed border-border rounded-2xl">
                  No widget message data available for the last 30 days.
                </div>
              )
            ) : (
              internalSeries.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={internalSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                      <XAxis dataKey="date" stroke="hsl(var(--muted-foreground))" fontSize={11} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} allowDecimals={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '12px' }}
                        cursor={{ fill: 'hsl(var(--muted))', opacity: 0.2 }}
                      />
                      <Bar dataKey="messages" name="Internal Chats" fill="var(--primary)" radius={[4, 4, 0, 0]} opacity={0.85} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-72 flex items-center justify-center text-muted-foreground border border-dashed border-border rounded-2xl">
                  No internal message data available for the last 30 days.
                </div>
              )
            )}
          </div>

          {/* Recent Activity (ActivityFeed) */}
          <ActivityFeed
            agents={agents}
            sessions={sessions}
          />
        </div>

        {/* Sidebar panel containing Quick Shortcuts and Recent Agents */}
        <div className="space-y-8 lg:col-span-1">
          <QuickActions
            onCreateAgent={() => setCreateAgentWizardOpen(true)}
          />
          <RecentAgents
            agents={agents}
            isLoading={isLoadingAgents}
          />
        </div>
      </div>

    </div>
  );
}
