import KPIGrid from "../components/dashboard/KPIGrid";
import QuickActions from "../components/dashboard/QuickActions";
import RecentAgents from "../components/dashboard/RecentAgents";
import ActivityFeed from "../components/dashboard/ActivityFeed";
import { useAuth } from "../context/AuthContext";
import { useAgents } from "../hooks/useAgents";
import { useChat } from "../hooks/useChat";
import { useNotes } from "../hooks/useNotes";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { useUIStore } from "../store/useUIStore";

export default function DashboardPage() {
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { sessions = [] } = useChat();
  const { notes = [] } = useNotes();
  const setCreateAgentWizardOpen = useUIStore(
    (state) => state.setCreateAgentWizardOpen,
  );
  const {
    data: agents = [],
    isLoading: isLoadingAgents,
  } = useAgents(activeWorkspaceId);
  const totalMessages = sessions.reduce(
    (count, session) => count + session.messages.length,
    0,
  );

  return (
    <>
      {isLoadingAgents && (
        <div className="mb-8">
          <LoadingSkeleton
            count={1}
            className="h-32"
          />
        </div>
      )}

      <KPIGrid
        activeAgentsCount={agents.length}
        conversationsCount={sessions.length}
        messagesCount={totalMessages}
        notesCount={notes.length}
        isLoadingAgents={isLoadingAgents}
      />

      <div className="grid lg:grid-cols-3 gap-6 mt-8">
        <div className="lg:col-span-2">
          <QuickActions
            onCreateAgent={() => setCreateAgentWizardOpen(true)}
          />
        </div>

        <RecentAgents
          agents={agents}
          isLoading={isLoadingAgents}
        />
      </div>

      <div className="mt-8">
        <ActivityFeed
          agents={agents}
          sessions={sessions}
          notes={notes}
        />
      </div>
    </>
  );
}
