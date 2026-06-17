import {
  Bot,
  Database,
  Network,
  Brain,
} from "lucide-react";

import KPICard from "./KPICard";

export default function KPIGrid({
  activeAgentsCount = 0,
  conversationsCount = 0,
  messagesCount = 0,
  networksCount = 0,
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
        title="Networks"
        value={networksCount.toLocaleString()}
        change="Multi-agent systems"
        icon={Network}
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
