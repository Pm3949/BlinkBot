import React, { useState, useEffect } from "react";
import {
  Building2,
  Key,
  Palette,
  Shield,
  Trash2,
  Save,
} from "lucide-react";
import { useUIStore } from "../store/useUIStore";
import { useUserSettings, useUpdateUserSettings, usePrimaryWorkspace, useUpdateWorkspace } from "../hooks/useSettings";
import { toast } from "sonner";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";

export default function SettingsPage() {
  const darkMode = useUIStore((state) => state.darkMode);
  const setDarkMode = useUIStore((state) => state.setDarkMode);

  const { data: settings, isLoading: loadingSettings } = useUserSettings();
  const { data: workspace, isLoading: loadingWorkspace } = usePrimaryWorkspace();
  
  const updateSettingsMutation = useUpdateUserSettings();
  const updateWorkspaceMutation = useUpdateWorkspace();

  const [workspaceName, setWorkspaceName] = useState("");
  const [apiKeys, setApiKeys] = useState({
    openai_api_key: "",
    groq_api_key: "",
    gemini_api_key: ""
  });

  useEffect(() => {
    if (workspace?.name) setWorkspaceName(workspace.name);
  }, [workspace]);

  useEffect(() => {
    if (settings) {
      setApiKeys({
        openai_api_key: settings.openai_api_key || "",
        groq_api_key: settings.groq_api_key || "",
        gemini_api_key: settings.gemini_api_key || ""
      });
    }
  }, [settings]);

  const handleSaveWorkspace = async () => {
    if (!workspace?.id) return;
    try {
      await updateWorkspaceMutation.mutateAsync({ id: workspace.id, name: workspaceName });
      toast.success("Workspace updated successfully");
    } catch (e) {
      toast.error("Failed to update workspace");
    }
  };

  const handleSaveApiKeys = async () => {
    try {
      await updateSettingsMutation.mutateAsync(apiKeys);
      toast.success("API keys saved successfully");
    } catch (e) {
      toast.error("Failed to save API keys");
    }
  };

  const handleApiKeyChange = (key, value) => {
    setApiKeys(prev => ({ ...prev, [key]: value }));
  };

  if (loadingSettings || loadingWorkspace) {
    return <LoadingSkeleton count={3} className="h-40 mb-4" />;
  }

  return (
    <div className="max-w-6xl">
      <div className="mb-10">
        <h1 className="text-4xl font-bold text-foreground">
          Settings
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage your workspace, API keys and preferences.
        </p>
      </div>

      <div className="space-y-6">
        {/* Workspace */}
        <div className="glass-card p-8">
          <div className="flex items-center gap-3 mb-6">
            <Building2 className="text-primary" />
            <h2 className="text-xl font-semibold text-foreground">
              Workspace
            </h2>
          </div>

          <div className="space-y-4">
            <input
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              className="w-full border border-border rounded-2xl p-4 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Workspace Name"
            />
            <button 
              onClick={handleSaveWorkspace}
              disabled={updateWorkspaceMutation.isPending}
              className="px-5 py-3 btn-primary rounded-2xl flex items-center gap-2 disabled:opacity-50"
            >
              <Save size={16} />
              {updateWorkspaceMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>

        {/* API Keys */}
        <div className="glass-card p-8">
          <div className="flex items-center gap-3 mb-6">
            <Key className="text-primary" />
            <h2 className="text-xl font-semibold text-foreground">
              API Keys
            </h2>
          </div>

          <div className="space-y-4">
            <input
              type="password"
              placeholder="OpenAI API Key"
              value={apiKeys.openai_api_key}
              onChange={(e) => handleApiKeyChange("openai_api_key", e.target.value)}
              className="w-full border border-border rounded-2xl p-4 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <input
              type="password"
              placeholder="Groq API Key"
              value={apiKeys.groq_api_key}
              onChange={(e) => handleApiKeyChange("groq_api_key", e.target.value)}
              className="w-full border border-border rounded-2xl p-4 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <input
              type="password"
              placeholder="Gemini API Key"
              value={apiKeys.gemini_api_key}
              onChange={(e) => handleApiKeyChange("gemini_api_key", e.target.value)}
              className="w-full border border-border rounded-2xl p-4 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <button 
              onClick={handleSaveApiKeys}
              disabled={updateSettingsMutation.isPending}
              className="px-5 py-3 btn-primary rounded-2xl flex items-center gap-2 disabled:opacity-50"
            >
              <Save size={16} />
              {updateSettingsMutation.isPending ? "Saving..." : "Save API Keys"}
            </button>
          </div>
        </div>

        {/* Appearance */}
        <div className="glass-card p-8">
          <div className="flex items-center gap-3 mb-6">
            <Palette className="text-primary" />
            <h2 className="text-xl font-semibold text-foreground">
              Appearance
            </h2>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <button
              onClick={() => setDarkMode(false)}
              className={`border rounded-2xl p-6 font-medium text-foreground ${
                !darkMode
                  ? "border-primary bg-primary/10"
                  : "border-border"
              }`}
            >
              Light
            </button>
            <button
              onClick={() => setDarkMode(true)}
              className={`border rounded-2xl p-6 font-medium text-foreground ${
                darkMode
                  ? "border-primary bg-primary/10"
                  : "border-border"
              }`}
            >
              Dark
            </button>
            <button
              onClick={() => {
                const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)").matches;
                setDarkMode(Boolean(prefersDark));
              }}
              className="border border-border rounded-2xl p-6 font-medium text-foreground hover:bg-muted"
            >
              System
            </button>
          </div>
        </div>

        {/* Security */}
        <div className="glass-card p-8">
          <div className="flex items-center gap-3 mb-6">
            <Shield className="text-primary" />
            <h2 className="text-xl font-semibold text-foreground">
              Security
            </h2>
          </div>

          <div className="flex justify-between items-center border border-border rounded-2xl p-5">
            <div>
              <div className="font-medium text-foreground">
                Two Factor Authentication
              </div>
              <div className="text-sm text-muted-foreground">
                Add an extra layer of security
              </div>
            </div>
            <button 
              className={`px-4 py-2 rounded-xl text-white ${settings?.two_factor_enabled ? 'bg-green-600 hover:bg-green-700' : 'btn-primary'}`}
              onClick={async () => {
                await updateSettingsMutation.mutateAsync({ two_factor_enabled: !settings?.two_factor_enabled });
                toast.success(settings?.two_factor_enabled ? "2FA Disabled" : "2FA Enabled");
              }}
            >
              {settings?.two_factor_enabled ? "Enabled" : "Enable"}
            </button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-red-50 border border-red-200 rounded-3xl p-8 dark:bg-red-500/10 dark:border-red-500/30">
          <div className="flex items-center gap-3 mb-6">
            <Trash2 className="text-red-600" />
            <h2 className="text-xl font-semibold text-red-600">
              Danger Zone
            </h2>
          </div>

          <div className="flex justify-between items-center">
            <div>
              <div className="font-medium text-foreground">
                Delete Workspace
              </div>
              <div className="text-sm text-muted-foreground">
                This action cannot be undone.
              </div>
            </div>
            <button className="px-5 py-3 rounded-2xl bg-red-600 text-white hover:bg-red-700">
              Delete Workspace
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
