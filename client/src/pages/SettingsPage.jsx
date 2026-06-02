import {
  Building2,
  Key,
  Palette,
  Shield,
  Trash2,
  Save,
} from "lucide-react";
import { useUIStore } from "../store/useUIStore";

export default function SettingsPage() {
  const darkMode = useUIStore((state) => state.darkMode);
  const setDarkMode = useUIStore((state) => state.setDarkMode);

  return (
<div className="p-10 max-w-6xl">
      <div className="mb-10">
        <h1 className="text-4xl font-bold text-slate-900">
          Settings
        </h1>

        <p className="text-slate-500 mt-2">
          Manage your workspace, API keys and preferences.
        </p>
      </div>

      <div className="space-y-6">
        {/* Workspace */}

        <div className="bg-white border border-slate-200 rounded-3xl p-8">


          <div className="flex items-center gap-3 mb-6">
            <Building2 className="text-indigo-600" />
            <h2 className="text-xl font-semibold">
              Workspace
            </h2>
          </div>

          <div className="space-y-4">
            <input
              className="w-full border border-slate-200 rounded-2xl p-4"
              defaultValue="RagMate Workspace"
            />

            <button className="px-5 py-3 bg-indigo-600 text-white rounded-2xl flex items-center gap-2">
              <Save size={16} />
              Save Changes
            </button>
          </div>
        </div>

        {/* API Keys */}

        <div className="bg-white border border-slate-200 rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <Key className="text-indigo-600" />
            <h2 className="text-xl font-semibold">
              API Keys
            </h2>

          </div>

          <div className="space-y-4">
            <input
              placeholder="OpenAI API Key"
              className="w-full border border-slate-200 rounded-2xl p-4"
            />

            <input
              placeholder="Groq API Key"
              className="w-full border border-slate-200 rounded-2xl p-4"
            />

            <input
              placeholder="Gemini API Key"
              className="w-full border border-slate-200 rounded-2xl p-4"
            />
          </div>

        </div>

        {/* Appearance */}

        <div className="bg-white border border-slate-200 rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <Palette className="text-indigo-600" />
            <h2 className="text-xl font-semibold">
              Appearance
            </h2>

          </div>

          <div className="grid grid-cols-3 gap-4">
            <button
              onClick={() => setDarkMode(false)}
              className={`border rounded-2xl p-6 ${
                !darkMode
                  ? "border-indigo-500 bg-indigo-50"
                  : "border-slate-200"
              }`}
            >
              Light
            </button>


            <button
              onClick={() => setDarkMode(true)}
              className={`border rounded-2xl p-6 ${
                darkMode
                  ? "border-indigo-500 bg-indigo-50"
                  : "border-slate-200"
              }`}
            >
              Dark
            </button>


            <button
              onClick={() => {
                const prefersDark =
                  window.matchMedia?.(
                    "(prefers-color-scheme: dark)",
                  ).matches;
                setDarkMode(Boolean(prefersDark));
              }}
              className="border border-slate-200 rounded-2xl p-6"
            >
              System
            </button>

          </div>
        </div>

        {/* Security */}

        <div className="bg-white border border-slate-200 rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <Shield className="text-indigo-600" />
            <h2 className="text-xl font-semibold">
              Security
            </h2>

          </div>

          <div className="flex justify-between items-center border border-slate-200 rounded-2xl p-5">
            <div>
              <div className="font-medium">
                Two Factor Authentication
              </div>

              <div className="text-sm text-slate-500">
                Add an extra layer of security
              </div>
            </div>


            <button className="px-4 py-2 rounded-xl bg-indigo-600 text-white">
              Enable
            </button>
          </div>
        </div>

        {/* Danger Zone */}

        <div className="bg-red-50 border border-red-200 rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <Trash2 className="text-red-600" />
            <h2 className="text-xl font-semibold text-red-600">
              Danger Zone
            </h2>

          </div>

          <div className="flex justify-between items-center">
            <div>
              <div className="font-medium">
                Delete Workspace
              </div>

              <div className="text-sm text-slate-500">
                This action cannot be undone.
              </div>

            </div>

            <button className="px-5 py-3 rounded-2xl bg-red-600 text-white">
              Delete Workspace
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

