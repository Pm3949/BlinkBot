import { createBrowserRouter } from "react-router-dom";

import AppShell from "./AppShell";
import ProtectedRoute from "../ProtectedRoute";
import PublicRoute from "../PublicRoute";
import RoleRoute from "../components/guards/RoleRoute";
import PermissionRoute from "../components/guards/PermissionRoute";

import DashboardPage from "../pages/DashboardPage";
import LoginPage from "../pages/LoginPage";
import StudioPage from "../pages/StudioPage";
import ProjectDetailsPage from "../pages/ProjectDetailsPage";
import AgentSettingsPage from "../pages/AgentSettingsPage";

import ChatPage from "../pages/ChatPage";
import ChatbotsPage from "../pages/ChatbotsPage";
import ChatbotEditorPage from "../pages/ChatbotEditorPage";

import AnalyticsPage from "../pages/AnalyticsPage";
import SettingsPage from "../pages/SettingsPage";
import ModelsPage from "../pages/ModelsPage";
import TeamPage from "../pages/TeamPage";
import BillingPage from "../pages/BillingPage";
import LandingPage from "../pages/LandingPage";
import UserGuidePage from "../pages/UserGuidePage";
import TermsPage from "../pages/TermsPage";
import AboutPage from "../pages/AboutPage";
import BlogPage from "../pages/BlogPage";

import GoogleCallback from "../pages/GoogleCallback";

import RouteErrorFallback from "./RouteErrorFallback";

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
    path: "/auth/callback",
    element: <GoogleCallback />,
  },
  {
    path: "/user-guide",
    element: <UserGuidePage />,
  },
  {
    path: "/terms",
    element: <TermsPage />,
  },
  {
    path: "/about",
    element: <AboutPage />,
  },
  {
    path: "/blog",
    element: <BlogPage />,
  },

  // ── Protected shell (all app pages live here) ────────────────────
  {
    path: "/",
    errorElement: <RouteErrorFallback />,
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
        path: "models",
        element: (
          <PermissionRoute permission="canManageModels" label="Models">
            <ModelsPage />
          </PermissionRoute>
        ),
      },
      {
        path: "settings",
        element: (
          <RoleRoute requiredRole="Owner">
            <SettingsPage />
          </RoleRoute>
        ),
      },

      // ── Feature-permission guarded routes ─────────────────────────
      {
        path: "studio",
        element: (
          <PermissionRoute permission="canManageStudio" label="Studio">
            <StudioPage />
          </PermissionRoute>
        ),
      },
      {
        path: "studio/project/:projectId",
        element: (
          <PermissionRoute permission="canManageStudio" label="Agent Network">
            <ProjectDetailsPage />
          </PermissionRoute>
        ),
      },
      {
        path: "agent/:agentId/settings",
        element: (
          <PermissionRoute permission="canManageStudio" label="Agent Settings">
            <AgentSettingsPage />
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
          <PermissionRoute permission="canManageStudio" label="Chatbot Editor">
            <ChatbotEditorPage />
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
