import {
  Bot,
  Database,
  MessageSquare,
  Brain,
} from "lucide-react";

import KPICard from "./KPICard";

export default function KPIGrid({
  activeAgentsCount = 0,
  conversationsCount = 0,
  messagesCount = 0,
  notesCount = 0,
  isLoadingAgents = false,
}) {
  return (
    <div className="grid lg:grid-cols-4 gap-6">
      <KPICard
        title="Active Agents"
        value={
          isLoadingAgents
            ? "..."
            : activeAgentsCount.toLocaleString()
        }
        change="Live"
        icon={Bot}
      />

      <KPICard
        title="Conversations"
        value={conversationsCount.toLocaleString()}
        change={`${messagesCount.toLocaleString()} messages`}
        icon={Database}
      />

      <KPICard
        title="Saved Notes"
        value={notesCount.toLocaleString()}
        change="Local workspace"
        icon={MessageSquare}
      />

      <KPICard
        title="Knowledge"
        value={activeAgentsCount > 0 ? "Ready" : "Setup"}
        change={activeAgentsCount > 0 ? "Agents available" : "Create an agent"}
        icon={Brain}
      />
    </div>
  );
}
