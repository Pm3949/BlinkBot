import { createBrowserRouter } from "react-router-dom";

import AppShell from "./AppShell";
import ProtectedRoute from "../ProtectedRoute";
import PublicRoute from "../PublicRoute";
import RoleRoute from "../components/guards/RoleRoute";
import PermissionRoute from "../components/guards/PermissionRoute";

import DashboardPage from "../pages/DashboardPage";
import LoginPage from "../pages/LoginPage";
import PlaygroundPage from "../pages/PlaygroundPage";
import ProjectDetailsPage from "../pages/ProjectDetailsPage";
import KnowledgeBasePage from "../pages/KnowledgeBasePage";
import ChatPage from "../pages/ChatPage";
import ChatbotsPage from "../pages/ChatbotsPage";
import ChatbotEditorPage from "../pages/ChatbotEditorPage";

import AnalyticsPage from "../pages/AnalyticsPage";
import SettingsPage from "../pages/SettingsPage";
import TeamPage from "../pages/TeamPage";
import BillingPage from "../pages/BillingPage";
import LandingPage from "../pages/LandingPage";
import UserGuidePage from "../pages/UserGuidePage";
import TermsPage from "../pages/TermsPage";

export const router = createBrowserRouter([
  // ── Public routes ───────────────────────────────────────────────
  {
    path: "/",
    element: (
      <PublicRoute>
        <LandingPage />
      </PublicRoute>
    ),
  },
  {
    path: "/login",
    element: (
      <PublicRoute>
        <LoginPage />
      </PublicRoute>
    ),
  },
  {
    path: "/user-guide",
    element: <UserGuidePage />,
  },
  {
    path: "/terms",
    element: <TermsPage />,
  },

  // ── Protected shell (all app pages live here) ────────────────────
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      // ── Open to all authenticated users ──────────────────────────
      {
        path: "dashboard",
        element: <DashboardPage />,
      },
      {
        path: "chat",
        element: <ChatPage />,
      },
      {
        path: "analytics",
        element: <AnalyticsPage />,
      },
      {
        path: "settings",
        element: <SettingsPage />,
      },

      // ── Feature-permission guarded routes ─────────────────────────
      {
        path: "playground",
        element: (
          <PermissionRoute permission="canManageAgents" label="Playground">
            <PlaygroundPage />
          </PermissionRoute>
        ),
      },
      {
        path: "playground/project/:projectId",
        element: (
          <PermissionRoute permission="canManageAgents" label="Agent Network">
            <ProjectDetailsPage />
          </PermissionRoute>
        ),
      },
      {
        path: "chatbots",
        element: <ChatbotsPage />,
      },
      {
        path: "chatbots/:chatbotId",
        element: (
          <PermissionRoute permission="canManageAgents" label="Chatbot Editor">
            <ChatbotEditorPage />
          </PermissionRoute>
        ),
      },
      {
        path: "knowledge",
        element: (
          <PermissionRoute permission="canManageDatabase" label="Knowledge Base">
            <KnowledgeBasePage />
          </PermissionRoute>
        ),
      },


      // ── Admin-only routes ─────────────────────────────────────────
      {
        path: "team",
        element: (
          <RoleRoute requiredRole="Admin">
            <TeamPage />
          </RoleRoute>
        ),
      },
      {
        path: "billing",
        element: (
          <RoleRoute requiredRole="Admin">
            <BillingPage />
          </RoleRoute>
        ),
      },
    ],
  },
]);
