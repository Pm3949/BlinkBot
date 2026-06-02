import { createBrowserRouter } from "react-router-dom";

import AppShell from "./AppShell";
import ProtectedRoute from "../ProtectedRoute";
import PublicRoute from "../PublicRoute";

import DashboardPage from "../pages/DashboardPage";
import LoginPage from "../pages/LoginPage";
import AgentsPage from "../pages/AgentsPage";
import KnowledgeBasePage from "../pages/KnowledgeBasePage";
import ChatPage from "../pages/ChatPage";
import NotesPage from "../pages/NotesPage";
import AnalyticsPage from "../pages/AnalyticsPage";
import SettingsPage from "../pages/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <PublicRoute>
        <LoginPage />
      </PublicRoute>
    ),
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: "agents",
        element: <AgentsPage />,
      },
      {
        path: "knowledge",
        element: <KnowledgeBasePage />,
      },
      {
        path: "chat",
        element: <ChatPage />,
      },
      {
        path: "notes",
        element: <NotesPage />,
      },
      {
        path: "analytics",
        element: <AnalyticsPage />,
      },
      {
        path: "settings",
        element: <SettingsPage />,
      },
    ],
  },
]);
