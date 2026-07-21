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
import { setup2FA, verifySetup2FA, disable2FA } from "../services/authService";
import { QRCodeSVG } from "qrcode.react";
import { useAuth } from "../context/AuthContext";

export default function SettingsPage() {
  const darkMode = useUIStore((state) => state.darkMode);
  const setDarkMode = useUIStore((state) => state.setDarkMode);
  const { user } = useAuth();
  const [setup2FAData, setSetup2FAData] = useState(null);
  const [totpCode, setTotpCode] = useState("");
  const [isSettingUp2FA, setIsSettingUp2FA] = useState(false);

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

        {/* AI Model Credentials Link Banner */}
        <div className="glass-card p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-bold shrink-0">
              <Key size={20} />
            </div>
            <div>
              <h3 className="font-bold text-sm text-foreground">AI Model & Provider API Credentials</h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Manage AES-256 encrypted API keys for OpenAI, Groq, OpenRouter, Anthropic, Gemini & HuggingFace in your Models Hub.
              </p>
            </div>
          </div>
          <button 
            type="button"
            onClick={() => navigate("/models")}
            className="px-4 py-2.5 bg-primary text-primary-foreground hover:bg-primary/90 transition-colors rounded-xl text-xs font-semibold shrink-0"
          >
            Manage Credentials in Models Hub
          </button>
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
                if (settings?.two_factor_enabled) {
                   try {
                     await disable2FA(user.id);
                     await updateSettingsMutation.mutateAsync({ two_factor_enabled: false });
                     toast.success("2FA Disabled");
                   } catch (e) {
                     toast.error("Failed to disable 2FA");
                   }
                } else {
                   try {
                     const data = await setup2FA(user.id);
                     setSetup2FAData(data);
                     setIsSettingUp2FA(true);
                   } catch (e) {
                     toast.error("Failed to setup 2FA");
                   }
                }
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
      {isSettingUp2FA && setup2FAData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border p-8 rounded-3xl max-w-sm w-full">
            <h2 className="text-xl font-bold mb-4">Set up 2FA</h2>
            <p className="text-sm text-muted-foreground mb-6">Scan the QR code below with your Authenticator app (like Google Authenticator or Authy).</p>
            <div className="bg-white p-4 rounded-xl flex justify-center mb-6">
              <QRCodeSVG value={setup2FAData.provisioning_uri} size={200} />
            </div>
            <input
              type="text"
              placeholder="6-digit code"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              className="w-full border border-border rounded-xl p-3 bg-background text-center tracking-[0.5em] text-lg font-bold mb-4 focus:ring-2 focus:ring-primary focus:outline-none"
            />
            <div className="flex gap-4">
              <button onClick={() => setIsSettingUp2FA(false)} className="flex-1 py-3 border border-border rounded-xl hover:bg-muted">Cancel</button>
              <button 
                onClick={async () => {
                  try {
                    await verifySetup2FA({ user_id: user.id, totp_code: totpCode });
                    await updateSettingsMutation.mutateAsync({ two_factor_enabled: true });
                    toast.success("2FA Enabled!");
                    setIsSettingUp2FA(false);
                    setTotpCode("");
                  } catch (e) {
                    toast.error("Invalid code");
                  }
                }}
                className="flex-1 py-3 btn-primary text-white rounded-xl"
              >
                Verify
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
